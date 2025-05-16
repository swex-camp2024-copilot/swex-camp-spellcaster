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
    losers_stats = {}  # {bot_name: total_turns_fought}

    while len(bots) > 1:
        print(f"\n=== Round {round_num} ===")
        print(f"{len(bots)} bots competing in this round")

        # Run the round and get winners
        winners, round_losers_stats, round_stats = run_tournament_round(bots, round_num, losers_stats)

        # Update losers stats and match statistics
        losers_stats.update(round_losers_stats)
        stats["matches"].extend(round_stats["matches"])
        stats["rounds"].append(round_stats["round_info"])

        # Update bots for next round
        bots = winners
        round_num += 1

    # Tournament complete
    winner = bots[0]
    print(f"\n🏆 Tournament Winner: {winner.name} 🏆")

    return winner, stats


def run_tournament_round(bots: List[BotInterface], round_num: int, losers_stats: Dict[str, int]) -> Tuple[List[BotInterface], Dict[str, int], Dict]:
    """
    Run a single tournament round.
    Returns:
        - List of winning bots
        - Updated losers stats
        - Round statistics
    """
    # Create pairs for this round
    pairs, odd_bot = create_pairs(bots)

    # Initialize round statistics
    round_stats = {"matches": [], "round_info": {}}
    round_losers_stats = {}

    # Store round information
    round_info = {
        "round": round_num,
        "participants": [bot.name for bot in bots],
        "pairs": [(b1.name, b2.name) for b1, b2 in pairs],
        "lucky_loser": None
    }
    round_stats["round_info"] = round_info

    # Run matches and collect winners
    winners = []
    losers = []
    for b1, b2 in pairs:
        print(f"Match: {b1.name} vs {b2.name}")
        winner, turns_fought, match_info = run_match_with_retry(b1, b2, round_num, len(bots) > 2)

        # Store match information
        round_stats["matches"].append(match_info)

        if winner != "NONE":  # If not disqualified
            # Update losers stats
            loser = b2 if winner == b1 else b1
            losers.append(loser)
            round_losers_stats[loser.name] = round_losers_stats.get(loser.name, 0) + turns_fought

            winners.append(winner)
            print(f"Winner: {winner.name} after {turns_fought} turns")
        else:
            # Both bots disqualified due to too many draws
            round_losers_stats[b1.name] = round_losers_stats.get(b1.name, 0) + turns_fought
            round_losers_stats[b2.name] = round_losers_stats.get(b2.name, 0) + turns_fought

    if odd_bot:
        # If there's an odd bot, it gets a bye
        lucky_loser = select_lucky_loser(losers, round_losers_stats)
        round_stats["lucky_loser"] = lucky_loser
        print("The lucky loser is:", lucky_loser.name)

        print(f"Match: {odd_bot.name} vs {lucky_loser.name}")
        winner, turns_fought, match_info = run_match_with_retry(odd_bot, lucky_loser, round_num, len(bots) > 2)

        # Store match information
        round_stats["matches"].append(match_info)

        if winner != "NONE":  # If not disqualified
            # Update losers stats
            loser = lucky_loser if winner == odd_bot else odd_bot
            losers.append(loser)
            round_losers_stats[loser.name] = round_losers_stats.get(loser.name, 0) + turns_fought

            winners.append(winner)
            print(f"Winner: {winner.name} after {turns_fought} turns")
        else:
            # Both bots disqualified due to too many draws
            round_losers_stats[odd_bot.name] = round_losers_stats.get(odd_bot.name, 0) + turns_fought
            round_losers_stats[lucky_loser.name] = round_losers_stats.get(lucky_loser.name, 0) + turns_fought


    return winners, round_losers_stats, round_stats


def run_match_with_retry(b1: BotInterface, b2: BotInterface, round_num: int, fast_mode: bool) -> Tuple[BotInterface, int, Dict]:
    """
    Run a match between two bots with retry logic for draws.
    Returns:
        - Winner bot (or "NONE" if both disqualified)
        - Number of turns fought
        - Match info dictionary
    """
    winner, logger = run_match(b1, b2)

    turns_fought = logger.get_snapshots()[-1]["turn"]
    snapshots = logger.get_snapshots()
    visualizer = Visualizer(logger, b1, b2)
    visualizer.run(snapshots, fast_mode)

    draw_counter = 0
    while winner == "Draw":
        draw_counter += 1
        print("Match ended in a draw")
        winner, logger = run_match(b1, b2)

        snapshots = logger.get_snapshots()
        visualizer = Visualizer(logger, b1, b2)
        visualizer.run(snapshots, fast_mode)

        if draw_counter > 2:
            break

    # Create match info
    match_info = {
        "round": round_num,
        "bot1": b1.name,
        "bot2": b2.name,
        "winner": winner if draw_counter <= 2 else "NONE",
        "turns": turns_fought
    }

    if draw_counter > 2:
        print(f"Too many draws, spell casters {b1.name} and {b2.name} are disqualified")
        return "NONE", turns_fought, match_info

    return winner, turns_fought, match_info


def select_lucky_loser(bots: List[BotInterface], losers_stats: Dict[str, int]) -> Optional[BotInterface]:
    """
    Select a lucky loser bot based on the highest number of turns fought.
    """
    if not losers_stats:
        return None

    # Find losers with the highest number of turns fought
    max_turns = max(losers_stats.values())
    candidates = [name for name, turns in losers_stats.items() if turns == max_turns]

    # Randomly select one if multiple candidates
    lucky_loser_name = random.choice(candidates)

    # Find the bot instance with this name
    for bot in bots:
        if bot.name == lucky_loser_name:
            return bot

    return None


def create_pairs(bots: List[BotInterface]) -> Tuple[List[Tuple[BotInterface, BotInterface]], Optional[BotInterface]]:
    """
    Create pairs of bots for matches.
    Returns a list of pairs and the lucky loser bot (if needed).
    """
    # Make a copy and shuffle to create random pairs
    random.shuffle(bots)
    pairs = []

    odd_bot = None
    # Create pairs
    for i in range(0, len(bots), 2):
        if i + 1 < len(bots):
            pairs.append((bots[i], bots[i+1]))
        else:
            # This bot doesn't have a pair
            odd_bot = bots[i]

    return pairs, odd_bot


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

# Example usage
if __name__ == "__main__":
    winner, stats = run_tournament()
    print(f"Tournament completed with {len(stats['matches'])} matches across {len(stats['rounds'])} rounds")