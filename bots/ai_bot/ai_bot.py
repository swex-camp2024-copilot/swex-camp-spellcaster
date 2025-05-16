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
        self.board_size = BOARD_SIZE * BOARD_SIZE
        
        # Player stats (hp, mana, position_x, position_y)
        self.player_stats = 4
        
        # Opponent stats (hp, mana, position_x, position_y)
        self.opponent_stats = 4
        
        # Spell cooldowns (one for each spell)
        self.spell_cooldowns = len(SPELLS)
        
        # Minion features (friendly count, enemy count)
        self.minion_features = 2
        
        # Calculate total input size
        self.input_size = (self.board_size +  # Board state
                     self.player_stats +  # Player stats
                     self.opponent_stats +  # Opponent stats
                     self.spell_cooldowns +  # Spell cooldowns
                     self.minion_features)  # Minion features
        
        # Calculate output size
        num_moves = len(DIRECTIONS)
        num_actions = len(SPELLS) + 1  # All spells plus no spell
        self.output_size = num_moves * num_actions
        
        # Enhanced network architecture with layer normalization and dropout
        self.board_encoder = nn.Sequential(
            nn.Linear(self.board_size, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        self.player_encoder = nn.Sequential(
            nn.Linear(self.player_stats + self.opponent_stats, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        self.spell_encoder = nn.Sequential(
            nn.Linear(self.spell_cooldowns + self.minion_features, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        self.advantage_stream = nn.Sequential(
            nn.Linear(384, 256),  # 256 + 64 + 64 = 384
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Linear(128, self.output_size)
        )
        
        self.value_stream = nn.Sequential(
            nn.Linear(384, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
        
    def forward(self, x):
        # Ensure input is 2D: [batch_size, features]
        if x.dim() == 1:
            x = x.unsqueeze(0)  # Add batch dimension if missing
        
        # Split input into different components
        board_state = x[:, :self.board_size]
        player_state = x[:, self.board_size:self.board_size + self.player_stats + self.opponent_stats]
        spell_state = x[:, self.board_size + self.player_stats + self.opponent_stats:]
        
        # Process each component
        board_features = self.board_encoder(board_state)
        player_features = self.player_encoder(player_state)
        spell_features = self.spell_encoder(spell_state)
        
        # Combine features
        combined = torch.cat([board_features, player_features, spell_features], dim=1)
        
        # Dueling DQN architecture
        advantage = self.advantage_stream(combined)
        value = self.value_stream(combined)
        
        # Combine value and advantage
        q_values = value + (advantage - advantage.mean(dim=1, keepdim=True))
        
        return q_values

class PrioritizedReplayBuffer:
    def __init__(self, capacity=50000):
        self.capacity = capacity
        self.buffer = []
        self.priorities = np.zeros(capacity, dtype=np.float32)
        self.position = 0
        self.alpha = 0.6  # Priority exponent
        self.beta = 0.4   # Importance sampling weight
        self.beta_increment = 0.001
        self.epsilon = 1e-5  # Small constant to prevent zero priorities
        
    def push(self, state, action, reward, next_state, done):
        """Store a transition in the buffer."""
        max_priority = np.max(self.priorities) if self.buffer else 1.0
        
        if len(self.buffer) < self.capacity:
            self.buffer.append((state, action, reward, next_state, done))
        else:
            self.buffer[self.position] = (state, action, reward, next_state, done)
        
        self.priorities[self.position] = max_priority
        self.position = (self.position + 1) % self.capacity
    
    def sample(self, batch_size):
        """Sample a batch of transitions with priorities."""
        if len(self.buffer) < batch_size:
            return None
        
        # Update beta
        self.beta = min(1.0, self.beta + self.beta_increment)
        
        # Calculate sampling probabilities
        priorities = self.priorities[:len(self.buffer)]
        probs = priorities ** self.alpha
        probs /= probs.sum()
        
        # Sample indices based on priorities
        indices = np.random.choice(len(self.buffer), batch_size, p=probs)
        
        # Calculate importance sampling weights
        total = len(self.buffer)
        weights = (total * probs[indices]) ** (-self.beta)
        weights /= weights.max()
        
        # Get samples
        batch = [self.buffer[idx] for idx in indices]
        states, actions, rewards, next_states, dones = zip(*batch)
        
        return (states, actions, rewards, next_states, dones, weights, indices)
    
    def update_priorities(self, indices, td_errors):
        """Update priorities based on TD errors."""
        for idx, td_error in zip(indices, td_errors):
            self.priorities[idx] = abs(td_error) + self.epsilon
    
    def __len__(self):
        return len(self.buffer)

class AIBot(BotInterface):
    def __init__(self):
        super().__init__()
        self._name = "LorenzosAiWizard"
        self._sprite_path = "assets/wizards/ai_bot.png"
        self._minion_sprite_path = "assets/minions/ai_minion.png"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DQN().to(self.device)
        self.target_model = DQN().to(self.device)
        self.target_model.load_state_dict(self.model.state_dict())
        
        # Initialize optimizer with model parameters that require gradients
        self.optimizer = optim.Adam(filter(lambda p: p.requires_grad, self.model.parameters()), lr=0.001)
        self.memory = PrioritizedReplayBuffer()
        
        self.epsilon = 0.1  # Exploration rate
        self.gamma = 0.99  # Discount factor
        self.batch_size = 32
        self.training = True  # Add training flag
        
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
        """Process state with proper tensor creation."""
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
        
        # Create feature vector for player and opponent stats
        player_features = [
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
        spell_features = []
        for spell in SPELLS:
            spell_features.append(state['self']['cooldowns'].get(spell, 0) / 5)
        
        # Add minion count features
        friendly_minions = len([m for m in state.get('minions', []) if m['owner'] == self.name])
        enemy_minions = len([m for m in state.get('minions', []) if m['owner'] != self.name])
        minion_features = [
            friendly_minions / 2,  # Normalize by max minions
            enemy_minions / 2
        ]
        
        # Flatten and combine all features
        state_tensor = np.concatenate([
            board.flatten(),
            np.array(player_features),
            np.array(spell_features),
            np.array(minion_features)
        ])
        
        # Convert to tensor
        tensor = torch.FloatTensor(state_tensor).to(self.device)
        return tensor  # Return flat tensor, batch dimension will be handled in forward()

    def get_action(self, state_tensor):
        # Set training flag to False during action selection
        self.training = False
        if random.random() < self.epsilon:
            # Random action with strategic bias
            move = random.choice(DIRECTIONS)
            
            # Initialize spells and weights
            spells = [None] + list(SPELLS.keys())
            weights = [0.5] * len(spells)  # Lower base weight for no-spell action
            
            state_dict = self.tensor_to_state(state_tensor)
            if state_dict:
                # Count current minions
                friendly_minions = len([m for m in state_dict.get('minions', []) 
                                     if m['owner'] == self.name])
                
                # Base spell weights with summon priority logic
                spell_weights = {
                    "summon": 3.0 if friendly_minions == 0 else 0.2,  # High priority when no minions, very low when we have them
                    "fireball": 2.0,  # High weight for direct damage
                    "melee_attack": 1.5,  # Good weight for melee
                    "heal": 0.8  # Lower weight for healing
                }
                
                for spell_name, weight in spell_weights.items():
                    if spell_name in spells:
                        spell_idx = spells.index(spell_name)
                        # Check mana cost and cooldown
                        if (state_dict['self']['mana'] >= SPELLS[spell_name]['cost'] and 
                            state_dict['self']['cooldowns'][spell_name] == 0):
                            weights[spell_idx] = weight
            
            spell_name = random.choices(spells, weights=weights)[0]
            spell = None if spell_name is None else {"name": spell_name}
            
            # Add intelligent targeting
            if spell and spell_name in ["fireball", "teleport", "blink", "melee_attack"]:
                if state_dict:
                    opp_pos = state_dict['opponent'].get('position', [BOARD_SIZE // 2, BOARD_SIZE // 2])
                    spell["target"] = opp_pos
                else:
                    spell["target"] = [BOARD_SIZE // 2, BOARD_SIZE // 2]
            
            return {'move': list(move), 'spell': spell}
        
        # Set model to evaluation mode for inference
        self.model.eval()
        with torch.no_grad():
            q_values = self.model(state_tensor)
            action_idx = q_values.argmax().item()
            
            # Convert action index to move and spell
            move_idx = action_idx % len(DIRECTIONS)
            spell_idx = action_idx // len(DIRECTIONS)
            
            move = DIRECTIONS[move_idx]
            spell_name = None if spell_idx == 0 else list(SPELLS.keys())[spell_idx - 1]
            spell = None if spell_name is None else {"name": spell_name}
            
            # Add intelligent targeting for spells
            if spell and spell_name in ["fireball", "teleport", "blink", "melee_attack"]:
                state_dict = self.tensor_to_state(state_tensor)
                if state_dict:
                    opp_pos = state_dict['opponent'].get('position', [BOARD_SIZE // 2, BOARD_SIZE // 2])
                    spell["target"] = opp_pos
                else:
                    spell["target"] = [BOARD_SIZE // 2, BOARD_SIZE // 2]
        
        # Set model back to training mode and return action
        self.model.train()
        self.training = True
        return {'move': list(move), 'spell': spell}

    def calculate_reward(self, current_state, prev_state):
        if not prev_state:
            return 0
            
        reward = 0
        
        # Extract current and previous state information
        curr_hp = current_state['self']['hp']
        prev_hp = prev_state['self']['hp']
        curr_opp_hp = current_state['opponent']['hp']
        prev_opp_hp = prev_state['opponent']['hp']
        curr_pos = current_state['self']['position']
        prev_pos = prev_state['self']['position']
        opp_pos = current_state['opponent']['position']
        
        # Calculate distances
        dist_to_opp = np.sqrt((curr_pos[0] - opp_pos[0])**2 + (curr_pos[1] - opp_pos[1])**2)
        prev_dist_to_opp = np.sqrt((prev_pos[0] - opp_pos[0])**2 + (prev_pos[1] - opp_pos[1])**2)
        
        # 1. Win/Loss/Draw Rewards (HIGHEST PRIORITY)
        if curr_opp_hp <= 0:  # Win
            base_win_reward = 200.0  # Massively increased win reward
            # Bonus for winning with high health
            health_bonus = (curr_hp / 100.0) * 100.0  # Increased health bonus
            # Bonus for winning quickly
            mana_efficiency = current_state['self']['mana'] / 100.0
            efficiency_bonus = mana_efficiency * 50.0
            reward += base_win_reward + health_bonus + efficiency_bonus
            return reward  # Return immediately on win to emphasize its importance
        elif curr_hp <= 0:  # Loss
            penalty = -150.0  # Severe loss penalty
            # Small reduction in penalty if dealt significant damage
            if curr_opp_hp < 50:
                penalty *= 0.9
            return penalty  # Return immediately on loss
        elif curr_opp_hp <= 0 and curr_hp <= 0:  # Draw
            return 20.0  # Moderate reward for draw
            
        # 2. Damage Dealing (Second Highest Priority)
        hp_change = curr_hp - prev_hp
        opp_hp_change = curr_opp_hp - prev_opp_hp
        
        # Massive reward for damaging opponent
        if opp_hp_change < 0:  # Dealt damage
            damage_dealt = abs(opp_hp_change)
            efficiency_bonus = 2.0 if hp_change >= 0 else 1.0  # Better reward if no damage taken
            reward += (damage_dealt / 10.0) * efficiency_bonus * 10.0  # Greatly increased damage reward
        
        # Reduced penalty for taking damage to encourage aggressive play
        if hp_change < 0:  # Took damage
            damage_taken = abs(hp_change)
            trade_factor = 0.3 if opp_hp_change < 0 else 0.7  # Much less penalty if traded damage
            reward -= (damage_taken / 10.0) * trade_factor * 2.0
        
        # 3. Positioning (Only if it helps deal damage)
        optimal_dist = 3.0  # Optimal distance for spell casting
        
        # Only reward positioning if it helps maintain damage-dealing range
        if abs(dist_to_opp - optimal_dist) < abs(prev_dist_to_opp - optimal_dist):
            reward += 1.0  # Small reward for better positioning
        
        # 4. Resource Management (Focused on damage output)
        curr_mana = current_state['self']['mana']
        prev_mana = prev_state['self']['mana']
        mana_used = prev_mana - curr_mana
        
        if mana_used > 0:  # Used mana
            if opp_hp_change < 0:  # Mana used resulted in damage
                reward += 3.0  # Reward for effective mana usage
            elif hp_change > 0 and curr_hp < 50:  # Healing when low
                reward += 1.0  # Small reward for necessary healing
        
        # 5. Minion Management (Focused on damage potential)
        curr_friendly_minions = len([m for m in current_state.get('minions', []) if m['owner'] == self.name])
        prev_friendly_minions = len([m for m in prev_state.get('minions', []) if m['owner'] == self.name])
        
        # Reward for having damage-dealing minions
        if curr_friendly_minions > prev_friendly_minions:
            reward += 5.0  # Increased reward for summoning
        elif curr_friendly_minions > 0:  # Keeping minions alive
            reward += 2.0  # Reward for maintaining damage sources
        
        # 6. Tactical Positioning (Minimal impact)
        # Only penalize extremely bad positions
        if curr_pos[0] in [0, BOARD_SIZE-1] and curr_pos[1] in [0, BOARD_SIZE-1]:
            reward -= 1.0  # Reduced penalty for corners
        
        # Penalize staying still only if not dealing damage
        if np.array_equal(curr_pos, prev_pos) and opp_hp_change >= 0:
            reward -= 0.5  # Small penalty for passive play
            
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
                self.process_state(state),
                False
            )
        
        self.prev_state = state
        return action

    def push_experience(self, state, action, reward, next_state, done):
        """Push experience to memory with proper tensor handling."""
        state_tensor = self.process_state(state)
        next_state_tensor = self.process_state(next_state)
        self.memory.push(state_tensor, action, reward, next_state_tensor, done)

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

    def train(self, num_batches=1):
        """Train the model with prioritized experience replay and TD-error clipping."""
        if len(self.memory) < self.batch_size:
            return 0
        
        # Ensure model is in training mode
        self.model.train()
        self.target_model.eval()
        self.training = True
        
        total_loss = 0
        for _ in range(num_batches):
            # Get batch with priorities
            batch = self.memory.sample(self.batch_size)
            if batch is None:
                continue
                
            states, actions, rewards, next_states, dones, weights, indices = batch
            
            # Convert everything to proper tensors with gradients where needed
            # Handle states and next_states which are tuples of tensors
            states_list = []
            next_states_list = []
            
            for state in states:
                if isinstance(state, torch.Tensor):
                    states_list.append(state.view(1, -1))
                else:
                    states_list.append(torch.FloatTensor(state).view(1, -1).to(self.device))
                    
            for next_state in next_states:
                if isinstance(next_state, torch.Tensor):
                    next_states_list.append(next_state.view(1, -1))
                else:
                    next_states_list.append(torch.FloatTensor(next_state).view(1, -1).to(self.device))
            
            # Stack all states and next_states
            states = torch.cat(states_list, dim=0).to(self.device)
            next_states = torch.cat(next_states_list, dim=0).to(self.device)
            
            # Convert other elements to tensors
            rewards = torch.FloatTensor(rewards).to(self.device)
            dones = torch.FloatTensor(dones).to(self.device)
            weights = torch.FloatTensor(weights).to(self.device)
            action_indices = torch.tensor([self.action_to_index(a) for a in actions], 
                                       dtype=torch.long, device=self.device)
            
            # Double DQN: Use main network to select actions, target network to evaluate
            with torch.no_grad():
                next_q_values = self.model(next_states)
                next_actions = next_q_values.max(1)[1]
                next_q_target = self.target_model(next_states)
                next_q_target = next_q_target.gather(1, next_actions.unsqueeze(1)).squeeze(1)
                target_q = rewards + (1 - dones) * self.gamma * next_q_target
            
            # Get current Q values
            current_q = self.model(states)
            current_q = current_q.gather(1, action_indices.unsqueeze(1)).squeeze(1)
            
            # Calculate TD errors for prioritized replay
            with torch.no_grad():
                td_errors = (target_q - current_q).detach()
            
            # Update priorities in replay buffer
            self.memory.update_priorities(indices, td_errors.abs().cpu().numpy())
            
            # Calculate loss with importance sampling weights
            # Use MSE loss directly on the Q-values
            elementwise_loss = 0.5 * (target_q.detach() - current_q) ** 2
            loss = (weights * elementwise_loss).mean()
            
            # Optimize the model
            self.optimizer.zero_grad()
            loss.backward()
            
            # Clip gradients to prevent exploding gradients
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=10.0)
            
            self.optimizer.step()
            total_loss += loss.item()
            
            # Soft update target network
            with torch.no_grad():
                for target_param, param in zip(self.target_model.parameters(), self.model.parameters()):
                    target_param.data.copy_(0.001 * param.data + 0.999 * target_param.data)
        
        self.training = False
        return total_loss / num_batches 