import os
import random
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from collections import defaultdict
import torch
import torch.optim as optim

from simulator.match import run_match
from bots.ai_bot.ai_bot import AIBot
from bots.sample_bot1.sample_bot_1 import SampleBot1
from bots.sample_bot2.sample_bot_2 import SampleBot2
from bots.sample_bot3.sample_bot_3 import SampleBot3
from bots.tactical_bot.tactical_bot import TacticalBot

class TrainingVisualizer:
    def __init__(self):
        self.win_rates = defaultdict(list)
        self.draw_rates = []
        self.exploration_rates = []
        self.episode_rewards = []
        
    def update(self, episode_stats, epsilon, episode_reward):
        # Track win rates for each opponent
        for opponent, results in episode_stats.items():
            # Strip the 'vs_' prefix and normalize tactical bot names
            opponent_name = opponent.replace('vs_', '')
            if 'Tactical' in opponent_name:
                opponent_name = 'TacticalBot'  # Combine all tactical bot variants into one line
            
            # Store AI bot's win rate against this opponent
            self.win_rates[opponent_name].append(results["ai_bot"])
        
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
        
        # Plot win rates
        plt.figure(figsize=(12, 6))
        
        # Get the maximum length of any win rate list
        max_episodes = max(len(rates) for rates in self.win_rates.values())
        episodes = range(1, max_episodes + 1)
        
        for opponent, rates in self.win_rates.items():
            # Pad shorter rate lists with their last value
            if len(rates) < max_episodes:
                rates.extend([rates[-1]] * (max_episodes - len(rates)))
            plt.plot(episodes, rates, label=f'vs {opponent}')
            
        plt.title('AI Bot Win Rates vs Different Opponents')
        plt.xlabel('Episode')
        plt.ylabel('Win Rate')
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(save_path, 'win_rates.png'))
        plt.close()
        
        # Plot draw rates
        plt.figure(figsize=(12, 6))
        draw_episodes = range(1, len(self.draw_rates) + 1)
        plt.plot(draw_episodes, self.draw_rates)
        plt.title('Draw Rates Over Time')
        plt.xlabel('Episode')
        plt.ylabel('Draw Rate')
        plt.grid(True)
        plt.savefig(os.path.join(save_path, 'draw_rates.png'))
        plt.close()
        
        # Plot exploration rate
        plt.figure(figsize=(12, 6))
        exploration_episodes = range(1, len(self.exploration_rates) + 1)
        plt.plot(exploration_episodes, self.exploration_rates)
        plt.title('Exploration Rate (Epsilon) Over Time')
        plt.xlabel('Episode')
        plt.ylabel('Epsilon')
        plt.grid(True)
        plt.savefig(os.path.join(save_path, 'exploration_rate.png'))
        plt.close()
        
        # Plot episode rewards
        plt.figure(figsize=(12, 6))
        reward_episodes = range(1, len(self.episode_rewards) + 1)
        plt.plot(reward_episodes, self.episode_rewards)
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
    
    print(f"\nEvaluating {bot1.name} vs {bot2.name} for {num_matches} matches")
    
    for match_num in range(num_matches):
        winner, logger = run_match(bot1, bot2, max_turns=100)
        results[winner] += 1
        print(f"Match {match_num + 1}: Winner = {winner}")
        
        # Enhanced reward calculation
        snapshots = logger.get_snapshots()
        match_reward = 0
        
        for i in range(len(snapshots)):
            if i > 0:
                current_state = snapshots[i]
                prev_state = snapshots[i-1]
                
                # Base reward from state transition
                match_reward += bot1.calculate_reward(current_state, prev_state)
                
                try:
                    # Calculate rewards based on health changes
                    if current_state['self']['hp'] > prev_state['self']['hp']:
                        match_reward += 0.5  # Reward for healing
                    if current_state['opponent']['hp'] < prev_state['opponent']['hp']:
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
                    continue
        
        total_reward += match_reward
    
    avg_reward = total_reward / num_matches
    
    # Print match summary
    print(f"\nMatch Summary:")
    print(f"{bot1.name} wins: {results[bot1.name]}")
    print(f"{bot2.name} wins: {results[bot2.name]}")
    print(f"Draws: {results['Draw']}")
    print(f"Average reward: {avg_reward:.2f}\n")
    
    # Store results with consistent keys
    return {
        "ai_bot": results[bot1.name] / num_matches,  # Always use bot1's actual win rate
        "opponent": results[bot2.name] / num_matches,
        "Draw": results["Draw"] / num_matches
    }, avg_reward

def create_bot_pool(num_ai_variants=3):
    """Create a pool of bots to train against with different difficulty levels."""
    pool = []
    
    # Create tactical bots with different configurations for each phase
    tactical_easy = TacticalBot()
    tactical_easy._name = "TacticalEasy"  # More exploratory, less aggressive
    
    tactical_medium = TacticalBot()
    tactical_medium._name = "TacticalMedium"  # Balanced configuration
    
    tactical_hard = TacticalBot()
    tactical_hard._name = "TacticalHard"  # Full strength
    
    # Easy bots (more random behavior)
    easy_bot1 = SampleBot1()
    easy_bot1.randomness = 0.3
    easy_bot2 = SampleBot2()
    easy_bot2.randomness = 0.3
    easy_bot3 = SampleBot3()
    easy_bot3.randomness = 0.3
    pool.append(("easy", easy_bot1))
    pool.append(("easy", easy_bot2))
    pool.append(("easy", easy_bot3))
    pool.append(("easy", tactical_easy))  # Add tactical bot to easy pool
    
    # Medium bots (normal behavior)
    pool.append(("medium", SampleBot1()))
    pool.append(("medium", SampleBot2()))
    pool.append(("medium", SampleBot3()))
    pool.append(("medium", tactical_medium))  # Add tactical bot to medium pool
    
    # Hard bots (optimized behavior)
    hard_bot1 = SampleBot1()
    hard_bot1.aggressive = True
    hard_bot2 = SampleBot2()
    hard_bot2.defensive = True
    hard_bot3 = SampleBot3()
    hard_bot3.aggressive = True
    
    pool.append(("hard", hard_bot1))
    pool.append(("hard", hard_bot2))
    pool.append(("hard", hard_bot3))
    pool.append(("hard", tactical_hard))  # Add tactical bot to hard pool
    
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
    # Lower initial epsilon for more focused learning
    main_bot.epsilon = 0.7
    
    visualizer = TrainingVisualizer()
    bot_pool = create_bot_pool()
    
    # Track performance metrics
    performance_history = []
    win_streak = 0
    PERFORMANCE_WINDOW = 20  # Increased from 10
    PROMOTION_THRESHOLD = 0.6  # Win rate needed to advance to next phase
    DEMOTION_THRESHOLD = 0.3  # Win rate that triggers return to previous phase
    
    # Enhanced curriculum phases with longer early training
    curriculum_phases = {
        "beginner": (0, episodes * 0.15),        # 15% - Very basic opponents
        "easy": (episodes * 0.15, episodes * 0.35),    # 20% - Easy opponents
        "medium": (episodes * 0.35, episodes * 0.60),   # 25% - Medium opponents
        "hard": (episodes * 0.60, episodes * 0.85),     # 25% - Hard opponents
        "expert": (episodes * 0.85, episodes)           # 15% - Expert opponents + self-play
    }
    
    # Phase-specific parameters
    phase_params = {
        "beginner": {
            "min_epsilon": 0.4,
            "learning_rate": 0.001,
            "batch_size": 32,
            "training_iterations": 2
        },
        "easy": {
            "min_epsilon": 0.3,
            "learning_rate": 0.0008,
            "batch_size": 48,
            "training_iterations": 3
        },
        "medium": {
            "min_epsilon": 0.2,
            "learning_rate": 0.0005,
            "batch_size": 64,
            "training_iterations": 4
        },
        "hard": {
            "min_epsilon": 0.15,
            "learning_rate": 0.0003,
            "batch_size": 96,
            "training_iterations": 5
        },
        "expert": {
            "min_epsilon": 0.1,
            "learning_rate": 0.0001,
            "batch_size": 128,
            "training_iterations": 6
        }
    }
    
    # Performance thresholds for epsilon adjustment
    EPSILON_ADJUST_THRESHOLDS = {
        "beginner": {"increase": 0.3, "decrease": 0.5},
        "easy": {"increase": 0.35, "decrease": 0.55},
        "medium": {"increase": 0.4, "decrease": 0.6},
        "hard": {"increase": 0.45, "decrease": 0.65},
        "expert": {"increase": 0.5, "decrease": 0.7}
    }
    
    current_phase = "beginner"
    phase_episode_count = 0
    
    for episode in tqdm(range(episodes), desc="Training Progress"):
        episode_stats = {}
        episode_total_reward = 0
        total_loss = 0
        num_training_batches = 0
        
        # Check for phase transition
        for phase, (start, end) in curriculum_phases.items():
            if start <= episode < end:
                if phase != current_phase:
                    print(f"\nTransitioning to {phase} phase")
                    current_phase = phase
                    phase_episode_count = 0
                    
                    # Update learning parameters
                    params = phase_params[phase]
                    main_bot.optimizer = optim.Adam(main_bot.model.parameters(), 
                                                  lr=params["learning_rate"])
                    main_bot.batch_size = params["batch_size"]
                break
        
        phase_episode_count += 1
        
        # Calculate performance metrics
        if len(performance_history) >= PERFORMANCE_WINDOW:
            avg_performance = np.mean(performance_history[-PERFORMANCE_WINDOW:])
            performance_trend = np.mean(performance_history[-PERFORMANCE_WINDOW:]) - \
                              np.mean(performance_history[-2*PERFORMANCE_WINDOW:-PERFORMANCE_WINDOW])
        else:
            avg_performance = 0
            performance_trend = 0
        
        # Select opponents based on phase and performance
        current_opponents = []
        if current_phase == "expert":
            # Mix of hard bots and self-play
            self_play_prob = min(0.6, 0.2 + phase_episode_count / (episodes * 0.15))
            if random.random() < self_play_prob and avg_performance >= 0.4:
                self_play_bot = create_self_play_bot()
                self_play_bot.model.load_state_dict(main_bot.model.state_dict())  # Fixed: use model.load_state_dict
                current_opponents.append((self_play_bot, "self_play"))
            
            # Always include at least one hard bot if self-play wasn't selected
            if not current_opponents:
                hard_bots = [(bot, diff) for diff, bot in bot_pool if diff == "hard"]
                if hard_bots:  # Make sure we have hard bots available
                    # Prioritize tactical bot
                    tactical_bot = next((b for b in hard_bots if "Tactical" in b[0].name), None)
                    if tactical_bot:
                        current_opponents.append(tactical_bot)
                    
                    # If still no opponents, add other hard bots
                    if not current_opponents:
                        other_bots = [b for b in hard_bots if "Tactical" not in b[0].name]
                        if other_bots:
                            current_opponents.extend(random.sample(other_bots, min(2, len(other_bots))))
                
                # Fallback to medium bots if no hard bots available
                if not current_opponents:
                    medium_bots = [(bot, diff) for diff, bot in bot_pool if diff == "medium"]
                    if medium_bots:
                        current_opponents.append(random.choice(medium_bots))
        else:
            # Regular curriculum learning
            phase_bots = [(bot, diff) for diff, bot in bot_pool if diff == current_phase]
            
            # Always try to include tactical bot first
            tactical_bot = next((b for b in phase_bots if "Tactical" in b[0].name), None)
            if tactical_bot:
                current_opponents.append(tactical_bot)
            
            # Add other bots from the current phase
            other_bots = [b for b in phase_bots if "Tactical" not in b[0].name]
            if other_bots:
                current_opponents.extend(random.sample(other_bots, min(2, len(other_bots))))
            
            # Fallback to easier phase if no opponents available
            if not current_opponents:
                previous_phases = ["medium", "easy", "beginner"]
                for prev_phase in previous_phases:
                    if not current_opponents:
                        prev_phase_bots = [(bot, diff) for diff, bot in bot_pool if diff == prev_phase]
                        if prev_phase_bots:
                            current_opponents.append(random.choice(prev_phase_bots))
                            break
        
        # Final fallback: if still no opponents, create a new basic opponent
        if not current_opponents:
            fallback_bot = SampleBot1()
            current_opponents.append((fallback_bot, "beginner"))
            print(f"Warning: Using fallback bot in episode {episode}")
        
        # Training against selected opponents
        for opponent, diff in current_opponents:
            results, avg_reward = evaluate_bot(main_bot, opponent, matches_per_episode)
            episode_stats[f"vs_{opponent.name}"] = results
            episode_total_reward += avg_reward
            
            if diff != "self_play":
                performance_history.append(results["ai_bot"])
            
            # Enhanced training step
            if len(main_bot.memory) >= main_bot.batch_size:
                num_iterations = phase_params[current_phase]["training_iterations"]
                batch_loss = main_bot.train(num_batches=num_iterations)
                total_loss += batch_loss
                num_training_batches += 1
        
        # Adaptive exploration rate adjustment
        avg_win_rate = np.mean([stats["ai_bot"] for stats in episode_stats.values()])
        thresholds = EPSILON_ADJUST_THRESHOLDS[current_phase]
        
        if avg_win_rate < thresholds["increase"]:
            # Poor performance - increase exploration
            increase_factor = 1.2 if performance_trend < 0 else 1.1
            main_bot.epsilon = min(0.9, main_bot.epsilon * increase_factor)
        elif avg_win_rate > thresholds["decrease"]:
            # Good performance - decrease exploration
            if current_phase == "expert":
                decay_rate = 0.995  # Slower decay in expert phase
            else:
                decay_rate = 0.99 if avg_win_rate < 0.7 else 0.985
            
            # Ensure epsilon doesn't go below phase minimum
            main_bot.epsilon = max(phase_params[current_phase]["min_epsilon"], 
                                 main_bot.epsilon * decay_rate)
        
        # Update win streak
        if avg_win_rate > 0.5:
            win_streak += 1
        else:
            win_streak = 0
        
        # Print detailed debugging information
        if (episode + 1) % 10 == 0:
            print(f"\nEpisode {episode + 1}")
            print(f"Current phase: {current_phase}")
            print(f"Average win rate: {avg_win_rate:.3f}")
            print(f"Current epsilon: {main_bot.epsilon:.3f}")
            print(f"Performance trend: {performance_trend:.3f}")
            print(f"Win streak: {win_streak}")
            print(f"Average reward: {episode_total_reward/len(current_opponents):.2f}")
        
        # Update visualizer
        visualizer.update(
            episode_stats,
            main_bot.epsilon,
            episode_total_reward / len(current_opponents)
        )
        
        # Save training stats
        save_training_stats(episode + 1, episode_stats)
        
        # Save model checkpoints
        if (episode + 1) % save_interval == 0:
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                    "models", 
                                    f"ai_bot_episode_{episode + 1}.pth")
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