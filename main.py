import os
import random
import importlib
import inspect
import sys
import argparse
from typing import List, Tuple, Dict, Optional
from bots.bot_interface import BotInterface
from simulator.match import run_match
from simulator.visualizer import Visualizer


def run_tournament(headless: bool = False):
    """
    Run a tournament with all bots from the bots folder.
    Returns the winner bot instance and tournament statistics.
    
    Args:
        headless (bool): If True, run without visualization
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

            turns_fought = logger.get_snapshots()[-1]["turn"]  # Get the last turn number
            snapshots = logger.get_snapshots()
            
            if not headless:
                visualizer = Visualizer(logger, b1, b2)
                visualizer.run(snapshots, len(bots) > 2)

            draw_counter = 0
            while winner == "Draw":
                draw_counter += 1
                print("Match ended in a draw")
                winner, logger = run_match(b1, b2)

                snapshots = logger.get_snapshots()
                
                if not headless:
                    visualizer = Visualizer(logger, b1, b2)
                    visualizer.run(snapshots, len(bots) > 2)

                if draw_counter > 2:
                    break
                continue


            if(draw_counter <= 2):
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
            else:
                print(f"Too many draws, spell casters {b1.name} and  {b2.name} are disqualified")
                losers_stats[b1.name] = losers_stats.get(b1.name, 0) + turns_fought
                losers_stats[b2.name] = losers_stats.get(b2.name, 0) + turns_fought
                match_info = {
                    "round": round_num,
                    "bot1": b1.name,
                    "bot2": b2.name,
                    "winner": "NONE",
                    "turns": turns_fought
                }
            stats["matches"].append(match_info)

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
    # Skip these files as they're not bot implementations
    skip_files = {"bot_interface.py"}

    for root, dirs, files in os.walk(bots_dir):
        # Skip interface and __pycache__ directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in files:
            # Skip the bot_interface.py file and any __init__ files
            if (file.endswith(".py") and 
                not file.startswith("__") and 
                file not in skip_files):
                
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

def find_bot_by_name(name: str) -> Optional[BotInterface]:
    """
    Find and instantiate a bot by its name.
    Returns None if no bot with the given name is found.
    """
    all_bots = discover_bots()
    for bot in all_bots:
        if bot.name.lower() == name.lower():
            return bot
    return None

def list_available_bots():
    """
    List all available bots in the bots directory.
    """
    bots = discover_bots()
    print(f"Found {len(bots)} bots:")
    for bot in bots:
        print(f"- {bot.name}")
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

def run_single_match(bot1_name: str, bot2_name: str, verbose: bool = False, headless: bool = False, count: int = 1):
    """
    Run matches between two bots with the given names.
    
    Args:
        bot1_name (str): Name of the first bot
        bot2_name (str): Name of the second bot
        verbose (bool): Whether to print detailed match logs
        headless (bool): Whether to run without visualization
        count (int): Number of matches to run
    """
    bot1 = find_bot_by_name(bot1_name)
    bot2 = find_bot_by_name(bot2_name)
    
    if not bot1:
        print(f"Bot '{bot1_name}' not found. Use 'python main.py match list' to see available bots.")
        return
    
    if not bot2:
        print(f"Bot '{bot2_name}' not found. Use 'python main.py match list' to see available bots.")
        return
    
    if count <= 0:
        print("Count must be a positive integer")
        return
        
    # Stats for multiple matches
    stats = {
        "bot1_wins": 0,
        "bot2_wins": 0,
        "draws": 0,
        "total_turns": 0
    }
    
    for match_num in range(1, count + 1):
        if count > 1:
            print(f"\nMatch {match_num}/{count}: {bot1.name} vs {bot2.name}")
        else:
            print(f"Match: {bot1.name} vs {bot2.name}")
            
        winner, logger = run_match(bot1, bot2, verbose=verbose)
        
        turns_fought = logger.get_snapshots()[-1]["turn"]  # Get the last turn number
        stats["total_turns"] += turns_fought
        
        if winner == bot1:
            stats["bot1_wins"] += 1
        elif winner == bot2:
            stats["bot2_wins"] += 1
        else:
            stats["draws"] += 1
        
        # Only visualize if not headless and (single match or last match in a series)
        if not headless and (count == 1 or (match_num == count and count <= 5)):
            snapshots = logger.get_snapshots()
            visualizer = Visualizer(logger, bot1, bot2)
            visualizer.run(snapshots, False)
        
        print(f"Winner: {winner.name if winner != 'Draw' else 'Draw'} after {turns_fought} turns")
    
    # Print stats summary for multiple matches
    if count > 1:
        print("\n" + "="*50)
        print(f"MATCH RESULTS: {bot1.name} vs {bot2.name} ({count} matches)")
        print("="*50)
        bot1_win_pct = (stats["bot1_wins"] / count) * 100
        bot2_win_pct = (stats["bot2_wins"] / count) * 100
        draws_pct = (stats["draws"] / count) * 100
        avg_turns = stats["total_turns"] / count
        
        print(f"{bot1.name}: {stats['bot1_wins']} wins ({bot1_win_pct:.1f}%)")
        print(f"{bot2.name}: {stats['bot2_wins']} wins ({bot2_win_pct:.1f}%)")
        print(f"Draws: {stats['draws']} ({draws_pct:.1f}%)")
        print(f"Average match length: {avg_turns:.1f} turns")

def parse_arguments():
    """
    Parse command line arguments for the application.
    """
    parser = argparse.ArgumentParser(description="Wizard Battle Tournament")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Tournament command
    tournament_parser = subparsers.add_parser("tournament", help="Run a full tournament with all bots")
    tournament_parser.add_argument("--headless", action="store_true", help="Run without visualization")
    
    # Match command
    match_parser = subparsers.add_parser("match", help="Run a single match between two bots or list available bots")
    match_parser.add_argument("bot1", nargs="?", help="Name of the first bot")
    match_parser.add_argument("bot2", nargs="?", help="Name of the second bot")
    match_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed match logs")
    match_parser.add_argument("--headless", action="store_true", help="Run without visualization")
    match_parser.add_argument("--count", "-c", type=int, default=1, help="Number of matches to run")
    
    return parser.parse_args()

# Example usage
if __name__ == "__main__":
    args = parse_arguments()
    
    if args.command == "tournament" or args.command is None:
        # Run the full tournament
        headless = getattr(args, 'headless', False)
        winner, stats = run_tournament(headless=headless)
        print(f"Tournament completed with {len(stats['matches'])} matches across {len(stats['rounds'])} rounds")
    
    elif args.command == "match":
        if args.bot1 == "list" or (args.bot1 is None and args.bot2 is None):
            # List available bots
            list_available_bots()
        elif args.bot1 and args.bot2:
            # Run a match between two specific bots
            headless = getattr(args, 'headless', False)
            count = getattr(args, 'count', 1)
            run_single_match(args.bot1, args.bot2, args.verbose, headless=headless, count=count)
        else:
            print("Please provide two bot names or use 'list' to see available bots.")
            print("Usage: python main.py match <bot1> <bot2> [--headless] [--verbose] [--count N]")
            print("       python main.py match list")