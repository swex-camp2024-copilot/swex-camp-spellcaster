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
        
        # Calculate input size:
        # Board state (BOARD_SIZE * BOARD_SIZE)
        board_size = BOARD_SIZE * BOARD_SIZE
        
        # Player stats (hp, mana, position_x, position_y)
        player_stats = 4
        
        # Opponent stats (hp, mana, position_x, position_y)
        opponent_stats = 4
        
        # Spell cooldowns (one for each spell)
        spell_cooldowns = len(SPELLS)
        
        # Minion counts (friendly and enemy)
        minion_features = 2
        
        # Calculate total input size
        input_size = (board_size +  # Board state
                     player_stats +  # Player stats
                     opponent_stats +  # Opponent stats
                     spell_cooldowns +  # Spell cooldowns
                     minion_features)  # Minion counts
        
        # Calculate output size
        num_moves = len(DIRECTIONS)
        num_actions = len(SPELLS) + 1  # All spells plus no spell
        output_size = num_moves * num_actions
        
        print(f"Input size: {input_size}, Output size: {output_size}")  # Debug print
        
        self.network = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, output_size)
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
        
        # Set up model path in the ai_bot/models folder
        self.model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
        os.makedirs(self.model_dir, exist_ok=True)
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
        
        # Mark wizard positions (1 for self, -1 for opponent)
        self_pos = state['self']['position']
        opp_pos = state['opponent']['position']
        board[self_pos[0]][self_pos[1]] = 1
        board[opp_pos[0]][opp_pos[1]] = -1
        
        # Mark minions (0.5 for friendly, -0.5 for enemy)
        for minion in state.get('minions', []):
            pos = minion['position']
            value = 0.5 if minion['owner'] == self.name else -0.5
            board[pos[0]][pos[1]] = value
        
        # Mark artifacts (0.25)
        for artifact in state.get('artifacts', []):
            pos = artifact['position']
            board[pos[0]][pos[1]] = 0.25
        
        # Create feature vector
        features = [
            state['self']['hp'] / 100,
            state['self']['mana'] / 100,
            self_pos[0] / BOARD_SIZE,
            self_pos[1] / BOARD_SIZE,
            state['opponent']['hp'] / 100,
            state['opponent']['mana'] / 100,
            opp_pos[0] / BOARD_SIZE,
            opp_pos[1] / BOARD_SIZE,
        ]
        
        # Add spell cooldowns
        for spell in SPELLS:
            features.append(state['self']['cooldowns'].get(spell, 0) / 5)
        
        # Add minion count features
        friendly_minions = len([m for m in state.get('minions', []) if m['owner'] == self.name])
        enemy_minions = len([m for m in state.get('minions', []) if m['owner'] != self.name])
        features.extend([
            friendly_minions / 2,  # Normalize by max minions
            enemy_minions / 2
        ])
        
        # Flatten and combine all features
        state_tensor = np.concatenate([
            board.flatten(),
            np.array(features)
        ])
        
        # Debug print to verify size
        print(f"State tensor size: {state_tensor.shape}")  # Debug print
        
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

    def calculate_reward(self, current_state, prev_state):
        if not prev_state:
            return 0
        
        reward = 0
        
        # Health changes
        health_diff_self = current_state['self']['hp'] - prev_state['self']['hp']
        health_diff_opp = prev_state['opponent']['hp'] - current_state['opponent']['hp']
        reward += health_diff_opp * 1.0  # Reward for damaging opponent
        reward += health_diff_self * 0.8  # Reward for healing/penalty for damage
        
        # Mana efficiency
        mana_used = prev_state['self']['mana'] - current_state['self']['mana']
        if mana_used > 0:
            # Check if the mana usage resulted in opponent damage
            if health_diff_opp > 0:
                reward += 0.5  # Bonus for effective mana use
        
        # Minion management
        curr_friendly_minions = len([m for m in current_state.get('minions', []) if m['owner'] == self.name])
        prev_friendly_minions = len([m for m in prev_state.get('minions', []) if m['owner'] == self.name])
        
        # Reward for summoning minions when we have few
        if curr_friendly_minions > prev_friendly_minions:
            reward += 2.0
        
        # Position control
        curr_pos = np.array(current_state['self']['position'])
        prev_pos = np.array(prev_state['self']['position'])
        opp_pos = np.array(current_state['opponent']['position'])
        
        # Calculate optimal distance based on state
        optimal_dist = 3  # Default medium range
        if current_state['self']['cooldowns'].get('fireball', 0) == 0 and current_state['self']['mana'] >= 30:
            optimal_dist = 4  # Fireball range
        elif curr_friendly_minions > 0:
            optimal_dist = 2  # Closer if we have minions
        
        # Distance management reward
        current_dist = np.linalg.norm(curr_pos - opp_pos)
        distance_reward = -abs(current_dist - optimal_dist) * 0.2
        reward += distance_reward
        
        # Artifact collection
        curr_artifacts = len(current_state.get('artifacts', []))
        prev_artifacts = len(prev_state.get('artifacts', []))
        reward += (prev_artifacts - curr_artifacts) * 2.0  # Good reward for collecting artifacts
        
        # Encourage exploration of the board
        if not np.array_equal(curr_pos, prev_pos):
            reward += 0.1  # Small reward for moving
        
        # Boundary penalty
        if (curr_pos[0] in [0, BOARD_SIZE-1] or curr_pos[1] in [0, BOARD_SIZE-1]):
            reward -= 0.2  # Penalty for being at the edges
        
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
        
        self.prev_state = state
        return action

    def train(self, num_batches=1):
        """Train the model for a specified number of batches."""
        if len(self.memory) < self.batch_size:
            return 0  # Return 0 loss if not enough samples
        
        total_loss = 0
        for _ in range(num_batches):
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
            # Clip gradients to prevent exploding gradients
            torch.nn.utils.clip_grad_value_(self.model.parameters(), 100)
            self.optimizer.step()
            
            total_loss += loss.item()
        
        # Update target network more frequently with soft updates
        for target_param, param in zip(self.target_model.parameters(), self.model.parameters()):
            target_param.data.copy_(0.005 * param.data + 0.995 * target_param.data)
        
        return total_loss / num_batches  # Return average loss

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

    def save_model(self, path=None):
        """Save the model to a specific path or use default path"""
        save_path = path if path is not None else self.model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        torch.save(self.model.state_dict(), save_path)
        
    def load_model(self, path=None):
        """Load the model from a specific path or use default path"""
        load_path = path if path is not None else self.model_path
        self.model.load_state_dict(torch.load(load_path))
        self.target_model.load_state_dict(self.model.state_dict()) 