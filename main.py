import os
import random
import importlib
import inspect
from typing import List, Tuple, Dict, Optional
from bots.bot_interface import BotInterface
from simulator.match import run_match
from simulator.visualizer import Visualizer


def run_tournament():
    """
    Run a tournament with all bots from the bots folder.
    Returns the winner bot instance and tournament statistics.
    """
    # Step 1: Find and load all bots
    bots = discover_bots()
    print(f"Found {len(bots)} bots for the tournament")
    for bot in bots:
        print(f"- {bot.name}")

    # Step 2: Run tournament rounds until we have a winner
    round_num = 1
    stats = {"matches": [], "rounds": []}

    # Keep track of losers and their total turns fought
    losers_stats = {}  # {bot_name: total_turns_fought}

    while len(bots) > 1:
        print(f"\n=== Round {round_num} ===")
        print(f"{len(bots)} bots competing in this round")

        # Create pairs for this round
        pairs, lucky_loser = create_pairs(bots, losers_stats)

        # Store round information
        round_info = {
            "round": round_num,
            "participants": [bot.name for bot in bots],
            "pairs": [(b1.name, b2.name) if b2 else (b1.name, lucky_loser.name if lucky_loser else None) for b1, b2 in pairs],
            "lucky_loser": lucky_loser.name if lucky_loser else None
        }
        stats["rounds"].append(round_info)

        # Run matches and collect winners
        winners = []
        for b1, b2 in pairs:
            if b2 is None:  # Odd number of bots, b1 gets a bye
                winners.append(b1)
                print(f"{b1.name} gets a bye")
                continue

            print(f"Match: {b1.name} vs {b2.name}")
            winner, logger = run_match(b1, b2)
            draw_counter = 0
            while winner == "Draw":
                draw_counter += 1
                print("Match ended in a draw")
                winner, logger = run_match(b1, b2)
                if draw_counter > 2:
                    print("Too many draws, skipping this match")
                    break
                continue

            turns_fought = logger.get_snapshots()[-1]["turn"]  # Get the last turn number

            snapshots = logger.get_snapshots()

            visualizer = Visualizer(logger, b1, b2)
            visualizer.run(snapshots, len(bots) > 2)

            # Update losers stats
            loser = b2 if winner == b1 else b1
            losers_stats[loser.name] = losers_stats.get(loser.name, 0) + turns_fought

            # Store match information
            match_info = {
                "round": round_num,
                "bot1": b1.name,
                "bot2": b2.name,
                "winner": winner,
                "turns": turns_fought
            }
            stats["matches"].append(match_info)

            winners.append(winner)
            print(f"Winner: {winner.name} after {turns_fought} turns")

        # Update bots for next round
        bots = winners
        round_num += 1

    # Tournament complete
    winner = bots[0]
    print(f"\n🏆 Tournament Winner: {winner.name} 🏆")

    return winner, stats

def discover_bots() -> List[BotInterface]:
    """
    Discover and instantiate all bots in the bots directory.
    """
    bots = []
    bots_dir = "bots"

    # Skip these directories as they don't contain bot implementations
    skip_dirs = {"__pycache__", "bot_interface"}

    for root, dirs, files in os.walk(bots_dir):
        # Skip interface and __pycache__ directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                # Construct the module path
                relative_path = os.path.relpath(root, os.getcwd())
                module_path = relative_path.replace(os.sep, ".") + "." + file[:-3]

                try:
                    # Import the module
                    module = importlib.import_module(module_path)

                    # Find classes that inherit from BotInterface
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and
                            issubclass(obj, BotInterface) and
                            obj.__module__ == module_path):

                            # Instantiate the bot and add to the list
                            bot_instance = obj()
                            bots.append(bot_instance)

                except Exception as e:
                    print(f"Error loading bot from {module_path}: {e}")

    return bots

def create_pairs(bots: List[BotInterface], losers_stats: Dict[str, int]) -> Tuple[List[Tuple[BotInterface, Optional[BotInterface]]], Optional[BotInterface]]:
    """
    Create pairs of bots for matches.
    Returns a list of pairs and the lucky loser bot (if needed).
    """
    # Make a copy and shuffle to create random pairs
    random.shuffle(bots)
    pairs = []
    lucky_loser = None

    # If odd number of bots, we need to find a "lucky loser"
    if len(bots) % 2 != 0 and losers_stats:
        # Find losers with the highest number of turns fought
        max_turns = max(losers_stats.values())
        candidates = [name for name, turns in losers_stats.items() if turns == max_turns]

        # Randomly select one if multiple candidates
        lucky_loser_name = random.choice(candidates)

        # Find the bot instance with this name
        for bot in bots:
            if bot.name == lucky_loser_name:
                lucky_loser = bot
                break

    # Create pairs
    for i in range(0, len(bots), 2):
        if i + 1 < len(bots):
            pairs.append((bots[i], bots[i+1]))
        else:
            # This bot doesn't have a pair
            if lucky_loser:
                pairs.append((bots[i], lucky_loser))
            else:
                pairs.append((bots[i], None))  # Gets a bye

    return pairs, lucky_loser

# Example usage
if __name__ == "__main__":
    winner, stats = run_tournament()
    print(f"Tournament completed with {len(stats['matches'])} matches across {len(stats['rounds'])} rounds")