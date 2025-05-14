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

def evaluate_bot(bot1, bot2, num_matches=10):
    """Run multiple matches between two bots and return win rates and average reward."""
    results = defaultdict(int)
    total_reward = 0
    
    for _ in range(num_matches):
        winner, logger = run_match(bot1, bot2, max_turns=100)
        results[winner] += 1
        
        # Calculate reward from the match
        if hasattr(bot1, 'calculate_reward'):
            snapshots = logger.get_snapshots()
            for i in range(len(snapshots)):
                if i > 0:  # Skip first state as we need previous state for reward calculation
                    total_reward += bot1.calculate_reward(snapshots[i], snapshots[i-1])
    
    avg_reward = total_reward / num_matches
    
    return {
        bot1.name: results[bot1.name] / num_matches,
        bot2.name: results[bot2.name] / num_matches,
        "Draw": results["Draw"] / num_matches
    }, avg_reward

def create_bot_pool(num_ai_variants=3):
    """Create a pool of bots to train against."""
    pool = [
        SampleBot1(),
        SampleBot2(),
    ]
    
    # Add AI bot variants with different exploration rates
    for i in range(num_ai_variants):
        ai_bot = AIBot()
        ai_bot._name = f"AIBot_variant_{i}"
        ai_bot.epsilon = 0.1 + (i * 0.1)  # Different exploration rates
        pool.append(ai_bot)
    
    return pool

def save_training_stats(episode, stats, filename="stats.txt"):
    """Save training statistics to a file."""
    # Make filename relative to the ai_bot folder
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(filename, "a") as f:
        f.write(f"Episode {episode}:\n")
        for bot_name, results in stats.items():
            f.write(f"{bot_name}: {results}\n")
        f.write("\n")

def train_ai_bot(episodes=100, matches_per_episode=10, save_interval=10, plot_interval=10):
    """Main training loop for the AI bot."""
    print("Starting AI bot training...")
    
    # Create main AI bot and visualizer
    main_bot = AIBot()
    visualizer = TrainingVisualizer()
    
    # Create bot pool
    bot_pool = create_bot_pool()
    
    # Training loop
    for episode in tqdm(range(episodes), desc="Training Progress"):
        episode_stats = {}
        episode_total_reward = 0
        
        # Train against each bot in the pool
        for opponent in bot_pool:
            if opponent.name == main_bot.name:
                continue
                
            # Run matches
            results, avg_reward = evaluate_bot(main_bot, opponent, matches_per_episode)
            episode_stats[f"vs_{opponent.name}"] = results
            episode_total_reward += avg_reward
            
            # Print progress
            win_rate = results[main_bot.name]
            print(f"\nEpisode {episode + 1}, vs {opponent.name}:")
            print(f"Win Rate: {win_rate:.2%}")
            print(f"Average Reward: {avg_reward:.2f}")
        
        # Update visualizer
        visualizer.update(
            episode_stats,
            main_bot.epsilon,
            episode_total_reward / len(bot_pool)
        )
        
        # Save training stats
        save_training_stats(episode + 1, episode_stats)
        
        # Save model periodically
        if (episode + 1) % save_interval == 0:
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", f"ai_bot_episode_{episode + 1}.pth")
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            torch.save(main_bot.model.state_dict(), model_path)
            print(f"\nSaved model checkpoint: {model_path}")
        
        # Plot metrics periodically
        if (episode + 1) % plot_interval == 0:
            visualizer.plot_metrics()
            print(f"\nUpdated training plots in 'plots' directory")
        
        # Adjust exploration rate
        main_bot.epsilon = max(0.05, main_bot.epsilon * 0.995)  # Gradually reduce exploration

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Train the AI bot")
    parser.add_argument("--episodes", type=int, default=100, help="Number of training episodes")
    parser.add_argument("--matches", type=int, default=10, help="Matches per episode")
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