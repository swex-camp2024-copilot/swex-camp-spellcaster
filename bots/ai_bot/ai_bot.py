import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random
from bots.bot_interface import BotInterface
from game.rules import BOARD_SIZE, SPELLS, DIRECTIONS
import os

class DQN(nn.Module):
    def __init__(self):
        super(DQN, self).__init__()
        # Input features:
        # - Board state (10x10)
        # - Player stats (HP, mana, position)
        # - Opponent stats (HP, mana, position)
        # - Spell cooldowns
        # - Artifacts positions
        input_size = BOARD_SIZE * BOARD_SIZE + 6 + len(SPELLS) + 10  # Flattened board + stats + cooldowns + artifacts
        
        self.network = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, len(DIRECTIONS) * (len(SPELLS) + 1))  # Actions: movement + spell combinations
        )
    
    def forward(self, x):
        return self.network(x)

class ReplayBuffer:
    def __init__(self, capacity=10000):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state):
        self.buffer.append((state, action, reward, next_state))
    
    def sample(self, batch_size):
        return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return len(self.buffer)

class AIBot(BotInterface):
    def __init__(self):
        self._name = "DQNWizard"
        self._sprite_path = "assets/wizards/sample_bot1.png"  # Temporarily using sample_bot1's sprite
        self._minion_sprite_path = "assets/minions/minion_1.png"  # Temporarily using minion_1's sprite
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DQN().to(self.device)
        self.target_model = DQN().to(self.device)
        self.target_model.load_state_dict(self.model.state_dict())
        
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.memory = ReplayBuffer()
        
        self.epsilon = 0.1  # Exploration rate
        self.gamma = 0.99  # Discount factor
        self.batch_size = 32
        
        # Set up model path in the ai_bot folder
        self.model_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(self.model_dir, "ai_bot_model.pth")
        
        # Load pre-trained model if available
        try:
            self.model.load_state_dict(torch.load(self.model_path))
            self.target_model.load_state_dict(self.model.state_dict())
        except:
            print("No pre-trained model found. Starting fresh.")
    
    @property
    def name(self) -> str:
        return self._name

    @property
    def sprite_path(self):
        return self._sprite_path

    @property
    def minion_sprite_path(self):
        return self._minion_sprite_path

    def process_state(self, state):
        # Convert game state to tensor
        board = np.zeros((BOARD_SIZE, BOARD_SIZE))
        
        # Mark player position
        player_pos = state['self']['position']
        board[player_pos[0]][player_pos[1]] = 1
        
        # Mark opponent position
        opp_pos = state['opponent']['position']
        board[opp_pos[0]][opp_pos[1]] = -1
        
        # Mark artifacts
        for artifact in state['artifacts']:
            pos = artifact['position']
            board[pos[0]][pos[1]] = 0.5
        
        # Create feature vector
        features = [
            state['self']['hp'] / 100,
            state['self']['mana'] / 100,
            state['opponent']['hp'] / 100,
            state['opponent']['mana'] / 100,
            player_pos[0] / BOARD_SIZE,
            player_pos[1] / BOARD_SIZE
        ]
        
        # Add spell cooldowns
        for spell in SPELLS:
            features.append(state['self']['cooldowns'].get(spell, 0) / 5)
        
        # Flatten and combine all features
        state_tensor = np.concatenate([
            board.flatten(),
            np.array(features),
            np.zeros(10)  # Reserved for additional features
        ])
        
        return torch.FloatTensor(state_tensor).unsqueeze(0).to(self.device)

    def get_action(self, state_tensor):
        if random.random() < self.epsilon:
            # Random action with strategic bias
            move = random.choice(DIRECTIONS)
            
            # Increase probability of using summon when conditions are favorable
            spells = [None] + list(SPELLS.keys())
            weights = [1.0] * len(spells)  # Default weight
            
            state_dict = self.tensor_to_state(state_tensor)
            if state_dict:
                # Increase weight for summon if conditions are good
                summon_idx = spells.index("summon") if "summon" in spells else -1
                if summon_idx != -1:
                    if (state_dict['self']['mana'] >= 50 and 
                        state_dict['self']['cooldowns']['summon'] == 0):
                        # Count current minions
                        minion_count = len([m for m in state_dict.get('minions', []) 
                                         if m['owner'] == state_dict['self']['name']])
                        if minion_count < 2:  # If we have less than 2 minions
                            weights[summon_idx] = 3.0  # Triple the chance of choosing summon
            
            spell_name = random.choices(spells, weights=weights)[0]
            spell = None if spell_name is None else {"name": spell_name}
            
            # Add target for spells that require it
            if spell and spell_name in ["fireball", "teleport", "blink", "melee_attack"]:
                # For now, target the center of the board as a default
                spell["target"] = [BOARD_SIZE // 2, BOARD_SIZE // 2]
            
            return {'move': list(move), 'spell': spell}
        
        with torch.no_grad():
            q_values = self.model(state_tensor)
            action_idx = q_values.argmax().item()
            
            # Convert action index to move and spell
            move_idx = action_idx % len(DIRECTIONS)
            spell_idx = action_idx // len(DIRECTIONS)
            
            move = DIRECTIONS[move_idx]
            spell_name = None if spell_idx == 0 else list(SPELLS.keys())[spell_idx - 1]
            spell = None if spell_name is None else {"name": spell_name}
            
            # Add target for spells that require it
            if spell and spell_name in ["fireball", "teleport", "blink", "melee_attack"]:
                # For now, target the center of the board as a default
                spell["target"] = [BOARD_SIZE // 2, BOARD_SIZE // 2]
            
            return {'move': list(move), 'spell': spell}

    def calculate_reward(self, state, prev_state):
        if not prev_state:
            return 0
        
        reward = 0
        
        # Reward for damaging opponent
        reward += (prev_state['opponent']['hp'] - state['opponent']['hp']) * 1.0
        
        # Penalty for taking damage
        reward -= (prev_state['self']['hp'] - state['self']['hp']) * 0.8
        
        # Reward for collecting artifacts
        reward += len(prev_state['artifacts']) - len(state['artifacts'])
        
        # Reward for maintaining good position
        player_pos = np.array(state['self']['position'])
        opp_pos = np.array(state['opponent']['position'])
        dist = np.linalg.norm(player_pos - opp_pos)
        
        # Dynamic positioning reward based on available spells and cooldowns
        optimal_dist = 1  # Default to close range
        if state['self']['cooldowns']['fireball'] == 0 and state['self']['mana'] >= 30:
            optimal_dist = 4  # Stay at fireball range if ready to cast
        elif state['self']['cooldowns']['summon'] == 0 and state['self']['mana'] >= 50:
            optimal_dist = 5  # Stay far when ready to summon
            # Extra reward for having mana and cooldown ready for summon
            reward += 0.5
        
        # Penalize staying in the same position
        if np.array_equal(player_pos, np.array(prev_state['self']['position'])):
            reward -= 0.2  # Small penalty for not moving
        
        # Reward for maintaining strategic distance
        position_reward = -abs(dist - optimal_dist) * 0.2
        reward += position_reward
        
        # Reward for effective mana usage
        mana_diff = prev_state['self']['mana'] - state['self']['mana']
        if mana_diff > 0:  # If mana was used
            reward += 0.3  # Encourage spell usage
            # Extra reward for using summon
            if state['self']['cooldowns']['summon'] > prev_state['self']['cooldowns']['summon']:
                reward += 1.5  # Significant bonus for using summon
        
        # Reward for having minions
        prev_minions = [m for m in prev_state.get('minions', []) if m['owner'] == state['self']['name']]
        curr_minions = [m for m in state.get('minions', []) if m['owner'] == state['self']['name']]
        
        # Reward for summoning minions
        if len(curr_minions) > len(prev_minions):
            reward += 2.0  # Major reward for successful summon
        
        # Reward for minion survival and effectiveness
        for minion in curr_minions:
            # Find corresponding minion in previous state
            prev_minion = next((m for m in prev_minions if m['id'] == minion['id']), None)
            if prev_minion:
                # Reward for minion dealing damage
                if prev_minion['hp'] > minion['hp']:
                    reward += 0.5  # Reward for minion being active in combat
                # Reward for minion survival
                reward += 0.1  # Small constant reward for each surviving minion
        
        # Strategic summon timing rewards
        if state['self']['mana'] >= 50 and state['self']['cooldowns']['summon'] == 0:
            # Extra reward for having summon ready when no minions
            if len(curr_minions) == 0:
                reward += 0.8
            # Reward for maintaining minion presence
            elif len(curr_minions) < 2:  # Encourage having multiple minions
                reward += 0.4
        
        return reward

    def decide(self, state):
        state_tensor = self.process_state(state)
        action = self.get_action(state_tensor)
        
        # Store experience for training
        if hasattr(self, 'prev_state') and self.prev_state is not None:
            reward = self.calculate_reward(state, self.prev_state)
            self.memory.push(
                self.process_state(self.prev_state),
                action,
                reward,
                state_tensor
            )
            
            # Train the model if we have enough samples
            if len(self.memory) >= self.batch_size:
                self.train()
        
        self.prev_state = state
        return action

    def train(self):
        if len(self.memory) < self.batch_size:
            return
        
        batch = self.memory.sample(self.batch_size)
        states, actions, rewards, next_states = zip(*batch)
        
        states = torch.cat(states)
        next_states = torch.cat(next_states)
        rewards = torch.FloatTensor(rewards).to(self.device)
        
        # Calculate current Q values
        current_q = self.model(states)
        
        # Calculate next Q values
        with torch.no_grad():
            next_q = self.target_model(next_states)
            max_next_q = next_q.max(1)[0]
            target_q = rewards + self.gamma * max_next_q
        
        # Create a target tensor of the same shape as current_q
        target = current_q.clone()
        # Update only the Q-value for the chosen action
        for i in range(len(batch)):
            action_idx = self.action_to_index(actions[i])
            target[i, action_idx] = target_q[i]
        
        # Update model
        loss = nn.MSELoss()(current_q, target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # Periodically update target network
        if random.random() < 0.01:  # 1% chance each training step
            self.target_model.load_state_dict(self.model.state_dict())
            
            # Save the model
            torch.save(self.model.state_dict(), self.model_path)
    
    def action_to_index(self, action):
        """Convert an action dictionary to its corresponding index."""
        move = action['move']
        spell = action['spell']
        
        # Find move index
        move_idx = DIRECTIONS.index(tuple(move))
        
        # Find spell index
        if spell is None:
            spell_idx = 0
        else:
            spell_idx = list(SPELLS.keys()).index(spell['name']) + 1
        
        # Calculate final index
        return spell_idx * len(DIRECTIONS) + move_idx 

    def tensor_to_state(self, state_tensor):
        """Convert state tensor back to dictionary format for easier processing."""
        try:
            # Extract board state (first BOARD_SIZE * BOARD_SIZE elements)
            board = state_tensor[0, :BOARD_SIZE * BOARD_SIZE].reshape(BOARD_SIZE, BOARD_SIZE)
            
            # Extract player stats (next 6 elements)
            stats_start = BOARD_SIZE * BOARD_SIZE
            self_hp = float(state_tensor[0, stats_start]) * 100
            self_mana = float(state_tensor[0, stats_start + 1]) * 100
            opp_hp = float(state_tensor[0, stats_start + 2]) * 100
            opp_mana = float(state_tensor[0, stats_start + 3]) * 100
            self_pos = [
                int(float(state_tensor[0, stats_start + 4]) * BOARD_SIZE),
                int(float(state_tensor[0, stats_start + 5]) * BOARD_SIZE)
            ]
            
            # Extract cooldowns (next len(SPELLS) elements)
            cooldowns_start = stats_start + 6
            cooldowns = {}
            for i, spell in enumerate(SPELLS.keys()):
                cooldowns[spell] = int(float(state_tensor[0, cooldowns_start + i]) * 5)
            
            return {
                'self': {
                    'hp': self_hp,
                    'mana': self_mana,
                    'position': self_pos,
                    'cooldowns': cooldowns
                },
                'opponent': {
                    'hp': opp_hp,
                    'mana': opp_mana
                },
                'minions': []  # We don't need full minion info for this purpose
            }
        except:
            return None 