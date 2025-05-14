import os
import random
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from collections import defaultdict
import torch

from simulator.match import run_match
from bots.ai_bot.ai_bot import AIBot
from bots.sample_bot1.sample_bot_1 import SampleBot1
from bots.sample_bot2.sample_bot_2 import SampleBot2

class TrainingVisualizer:
    def __init__(self):
        self.win_rates = defaultdict(list)
        self.draw_rates = []
        self.exploration_rates = []
        self.episode_rewards = []
        
    def update(self, episode_stats, epsilon, episode_reward):
        # Track win rates for each opponent
        for opponent, results in episode_stats.items():
            self.win_rates[opponent].append(results["DQNWizard"])
        
        # Track draw rates (average across all opponents)
        draw_rate = np.mean([results["Draw"] for results in episode_stats.values()])
        self.draw_rates.append(draw_rate)
        
        # Track exploration rate
        self.exploration_rates.append(epsilon)
        
        # Track episode rewards
        self.episode_rewards.append(episode_reward)
    
    def plot_metrics(self, save_path="plots"):
        # Make save_path relative to the ai_bot folder
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), save_path)
        os.makedirs(save_path, exist_ok=True)
        episodes = range(1, len(next(iter(self.win_rates.values()))) + 1)
        
        # Plot win rates
        plt.figure(figsize=(12, 6))
        for opponent, rates in self.win_rates.items():
            plt.plot(episodes, rates, label=f'{opponent}')
        plt.title('Win Rates vs Different Opponents')
        plt.xlabel('Episode')
        plt.ylabel('Win Rate')
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(save_path, 'win_rates.png'))
        plt.close()
        
        # Plot draw rates
        plt.figure(figsize=(12, 6))
        plt.plot(episodes, self.draw_rates)
        plt.title('Draw Rates Over Time')
        plt.xlabel('Episode')
        plt.ylabel('Draw Rate')
        plt.grid(True)
        plt.savefig(os.path.join(save_path, 'draw_rates.png'))
        plt.close()
        
        # Plot exploration rate
        plt.figure(figsize=(12, 6))
        plt.plot(episodes, self.exploration_rates)
        plt.title('Exploration Rate (Epsilon) Over Time')
        plt.xlabel('Episode')
        plt.ylabel('Epsilon')
        plt.grid(True)
        plt.savefig(os.path.join(save_path, 'exploration_rate.png'))
        plt.close()
        
        # Plot episode rewards
        plt.figure(figsize=(12, 6))
        plt.plot(episodes, self.episode_rewards)
        plt.title('Average Episode Reward Over Time')
        plt.xlabel('Episode')
        plt.ylabel('Average Reward')
        plt.grid(True)
        plt.savefig(os.path.join(save_path, 'episode_rewards.png'))
        plt.close()

class PrioritizedReplay:
    def __init__(self, capacity):
        self.capacity = capacity
        self.memory = []
        self.priorities = []
        
    def add(self, experience, reward):
        if len(self.memory) >= self.capacity:
            # Remove lowest priority experience
            min_priority_idx = np.argmin(self.priorities)
            self.memory.pop(min_priority_idx)
            self.priorities.pop(min_priority_idx)
        
        # Calculate priority based on reward
        priority = abs(reward) + 1.0  # Add 1 to ensure non-zero priority
        
        self.memory.append(experience)
        self.priorities.append(priority)
    
    def sample(self, batch_size):
        if len(self.memory) < batch_size:
            return random.sample(self.memory, len(self.memory))
        
        # Sample based on priorities
        probs = np.array(self.priorities) / sum(self.priorities)
        indices = np.random.choice(len(self.memory), batch_size, p=probs)
        return [self.memory[idx] for idx in indices]

def evaluate_bot(bot1, bot2, num_matches=10):
    """Run multiple matches between two bots and return win rates and average reward."""
    results = defaultdict(int)
    total_reward = 0
    
    for _ in range(num_matches):
        winner, logger = run_match(bot1, bot2, max_turns=100)
        results[winner] += 1
        
        # Enhanced reward calculation
        snapshots = logger.get_snapshots()
        match_reward = 0
        
        # Debug: Print first snapshot structure
        if len(snapshots) > 0:
            print("Debug - Snapshot structure:", snapshots[0].keys())
            print("Debug - First snapshot:", snapshots[0])
        
        for i in range(len(snapshots)):
            if i > 0:
                current_state = snapshots[i]
                prev_state = snapshots[i-1]
                
                # Base reward from state transition
                match_reward += bot1.calculate_reward(current_state, prev_state)
                
                try:
                    # Get player indices (bot1 might be player 1 or 2)
                    bot1_idx = 0 if current_state['wizard1']['name'] == bot1.name else 1
                    bot2_idx = 1 - bot1_idx
                    
                    # Get wizard keys based on indices
                    bot1_key = f'wizard{bot1_idx + 1}'
                    bot2_key = f'wizard{bot2_idx + 1}'
                    
                    # Calculate rewards based on health changes
                    if current_state[bot1_key]['health'] > prev_state[bot1_key]['health']:
                        match_reward += 0.5  # Reward for healing
                    if current_state[bot2_key]['health'] < prev_state[bot2_key]['health']:
                        match_reward += 1.0  # Reward for damaging opponent
                    
                    # Winner rewards
                    if winner == bot1.name:
                        match_reward += 10.0  # Large reward for winning
                    elif winner == "Draw":
                        match_reward += 1.0  # Small reward for drawing
                    elif winner == bot2.name:
                        match_reward -= 5.0  # Penalty for losing
                        
                except KeyError as e:
                    print(f"Debug - KeyError accessing state: {e}")
                    print(f"Debug - Current state keys: {current_state.keys()}")
                    print(f"Debug - Previous state keys: {prev_state.keys()}")
                    continue
        
        total_reward += match_reward
    
    avg_reward = total_reward / num_matches
    return {
        bot1.name: results[bot1.name] / num_matches,
        bot2.name: results[bot2.name] / num_matches,
        "Draw": results["Draw"] / num_matches
    }, avg_reward

def create_bot_pool(num_ai_variants=3):
    """Create a pool of bots to train against with different difficulty levels."""
    pool = []
    
    # Easy bots (more random behavior)
    easy_bot1 = SampleBot1()
    easy_bot1.randomness = 0.3
    easy_bot2 = SampleBot2()
    easy_bot2.randomness = 0.3
    pool.append(("easy", easy_bot1))
    pool.append(("easy", easy_bot2))
    
    # Medium bots (normal behavior)
    pool.append(("medium", SampleBot1()))
    pool.append(("medium", SampleBot2()))
    
    # Hard bots (optimized behavior)
    hard_bot1 = SampleBot1()
    hard_bot1.aggressive = True
    hard_bot2 = SampleBot2()
    hard_bot2.defensive = True
    pool.append(("hard", hard_bot1))
    pool.append(("hard", hard_bot2))
    
    return pool

def create_self_play_bot():
    """Create a copy of the AI bot for self-play."""
    self_play_bot = AIBot()
    self_play_bot.name = "SelfPlayBot"
    return self_play_bot

def save_training_stats(episode, stats, filename="stats.txt"):
    """Save training statistics to a file."""
    # Make filename relative to the ai_bot folder
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(filename, "a") as f:
        f.write(f"Episode {episode}:\n")
        for bot_name, results in stats.items():
            f.write(f"{bot_name}: {results}\n")
        f.write("\n")

def train_ai_bot(episodes=1000, matches_per_episode=20, save_interval=10, plot_interval=10):
    """Main training loop with curriculum learning and self-play."""
    print("Starting AI bot training with curriculum learning and self-play...")
    
    main_bot = AIBot()
    visualizer = TrainingVisualizer()
    bot_pool = create_bot_pool()
    
    # Track performance against sample bots
    performance_history = []
    PERFORMANCE_WINDOW = 10
    SELF_PLAY_THRESHOLD = 0.7
    
    # Curriculum learning phases
    curriculum_phases = {
        "easy": (0, episodes // 4),
        "medium": (episodes // 4, episodes // 2),
        "hard": (episodes // 2, 3 * episodes // 4),
        "self_play": (3 * episodes // 4, episodes)
    }
    
    for episode in tqdm(range(episodes), desc="Training Progress"):
        episode_stats = {}
        episode_total_reward = 0
        total_loss = 0
        num_training_batches = 0
        
        # Determine current phase
        current_phase = None
        for phase, (start, end) in curriculum_phases.items():
            if start <= episode < end:
                current_phase = phase
                break
        
        # Calculate average performance against sample bots
        if len(performance_history) >= PERFORMANCE_WINDOW:
            avg_performance = np.mean(performance_history[-PERFORMANCE_WINDOW:])
        else:
            avg_performance = 0
        
        # Select opponents based on phase and performance
        current_opponents = []
        if current_phase == "self_play" or avg_performance >= SELF_PLAY_THRESHOLD:
            # Mix of sample bots and self-play
            self_play_prob = min(0.8, 0.2 + (episode - curriculum_phases["hard"][1]) / (episodes / 4))
            
            if random.random() < self_play_prob:
                # Create a copy of the current model for self-play
                self_play_bot = create_self_play_bot()
                self_play_bot.load_state_dict(main_bot.state_dict())
                current_opponents.append((self_play_bot, "self_play"))
            else:
                # Add some hard bots to maintain diversity
                current_opponents.extend([(bot, "hard") for diff, bot in bot_pool if diff == "hard"])
        else:
            # Regular curriculum learning
            current_opponents = [(bot, diff) for diff, bot in bot_pool if diff == current_phase]
        
        # Training iterations based on phase
        num_training_iterations = {
            "easy": 2,
            "medium": 4,
            "hard": 6,
            "self_play": 8
        }[current_phase]
        
        # Train against selected opponents
        for opponent, diff in current_opponents:
            results, avg_reward = evaluate_bot(main_bot, opponent, matches_per_episode)
            episode_stats[f"vs_{opponent.name}"] = results
            episode_total_reward += avg_reward
            
            # Track performance against sample bots
            if diff != "self_play":
                performance_history.append(results[main_bot.name])
            
            # Training step
            if len(main_bot.memory) >= main_bot.batch_size:
                batch_loss = main_bot.train(num_batches=num_training_iterations)
                total_loss += batch_loss
                num_training_batches += 1
        
        # Adaptive exploration rate
        avg_win_rate = np.mean([stats[main_bot.name] for stats in episode_stats.values()])
        if avg_win_rate < 0.3:
            main_bot.epsilon = min(0.9, main_bot.epsilon * 1.1)
        else:
            decay_rate = 0.99 if current_phase == "self_play" else 0.995
            main_bot.epsilon = max(0.05, main_bot.epsilon * decay_rate)
        
        # Update visualizer
        visualizer.update(
            episode_stats,
            main_bot.epsilon,
            episode_total_reward / len(current_opponents)
        )
        
        # Save training stats
        save_training_stats(episode + 1, episode_stats)
        
        # Save model periodically
        if (episode + 1) % save_interval == 0:
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", f"ai_bot_episode_{episode + 1}.pth")
            main_bot.save_model(model_path)
            print(f"\nSaved model checkpoint: {model_path}")
            print(f"Current phase: {current_phase}, Average performance: {avg_performance:.2f}")
        
        # Plot metrics periodically
        if (episode + 1) % plot_interval == 0:
            visualizer.plot_metrics()
            print(f"\nUpdated training plots in 'plots' directory")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Train the AI bot")
    parser.add_argument("--episodes", type=int, default=1000, help="Number of training episodes")
    parser.add_argument("--matches", type=int, default=20, help="Matches per episode")
    parser.add_argument("--save-interval", type=int, default=10, help="Episodes between model saves")
    parser.add_argument("--plot-interval", type=int, default=10, help="Episodes between plotting metrics")
    args = parser.parse_args()
    
    try:
        train_ai_bot(
            episodes=args.episodes,
            matches_per_episode=args.matches,
            save_interval=args.save_interval,
            plot_interval=args.plot_interval
        )
    except KeyboardInterrupt:
        print("\nTraining interrupted. Progress has been saved.")

if __name__ == "__main__":
    main() 