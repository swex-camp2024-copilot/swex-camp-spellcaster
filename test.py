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


def run_round_robin_tournament(headless: bool = False):
    """
    Run a round-robin tournament where each bot plays against all other bots.
    Tracks scores for each bot (wins, draws, losses).
    Returns a dictionary with tournament results.
    
    Args:
        headless (bool): If True, run without visualization
    """
    # Step 1: Find and load all bots
    bots = discover_bots()
    print(f"Found {len(bots)} bots for the round-robin tournament")
    for bot in bots:
        print(f"- {bot.name}")

    # Step 2: Initialize score tracking
    scores = {bot.name: {"wins": 0, "draws": 0, "losses": 0, "points": 0} for bot in bots}
    match_results = []

    pairs = generate_round_robin_pairs(bots)

    # Step 3: Run matches between all pairs of bots
    total_matches = len(pairs)
    match_count = 0

    for bot1, bot2 in pairs:        
        match_count += 1
        # print(f"\nMatch {match_count}/{total_matches}: {bot1.name} vs {bot2.name}")
        # Run the match
        winner, logger = run_match(bot1, bot2)
        turns_fought = logger.get_snapshots()[-1]["turn"]

        # Visualize the match (if not in headless mode)
        if not headless:
            snapshots = logger.get_snapshots()
            visualizer = Visualizer(logger, bot1, bot2)
            visualizer.run(snapshots, True)  # Use fast mode for tournament

        # Record match result
        match_info = {
            "bot1": bot1.name,
            "bot2": bot2.name,
            "winner": winner,
            "turns": turns_fought
        }
        match_results.append(match_info)

        # Update scores
        if winner == "Draw":
            scores[bot1.name]["draws"] += 1
            scores[bot2.name]["draws"] += 1
            scores[bot1.name]["points"] += 1
            scores[bot2.name]["points"] += 1
            # print(f"Match ended in a draw after {turns_fought} turns")
        elif winner == bot1:
            scores[bot1.name]["wins"] += 1
            scores[bot2.name]["losses"] += 1
            scores[bot1.name]["points"] += 3
            # print(f"{bot1.name} won against {bot2.name} after {turns_fought} turns")
        elif winner == bot2:
            scores[bot2.name]["wins"] += 1
            scores[bot1.name]["losses"] += 1
            scores[bot2.name]["points"] += 3
            # print(f"{bot2.name} won against {bot1.name} after {turns_fought} turns")

            ranked_bots = sorted(scores.items(), key=lambda x: (x[1]["points"], x[1]["wins"]), reverse=True)
            # Print final standings
            # print("\n=== Current Standings ===")
            # print(f"{'Rank':<6}{'Bot':<20}{'Points':<8}{'W':<4}{'D':<4}{'L':<4}")
            # print("-" * 46)
            # for rank, (bot_name, score) in enumerate(ranked_bots, 1):
            #     print(
            #         f"{rank:<6}{bot_name:<20}{score['points']:<8}{score['wins']:<4}{score['draws']:<4}{score['losses']:<4}")


    print("FINAL SCORES:")
    # Step 4: Sort bots by points (win=3, draw=1, loss=0)
    ranked_bots = sorted(scores.items(), key=lambda x: (x[1]["points"], x[1]["wins"]), reverse=True)

    # Print final standings
    print("\n=== Final Standings ===")
    print(f"{'Rank':<6}{'Bot':<20}{'Points':<8}{'W':<4}{'D':<4}{'L':<4}")
    print("-" * 46)
    for rank, (bot_name, score) in enumerate(ranked_bots, 1):
        print(f"{rank:<6}{bot_name:<20}{score['points']:<8}{score['wins']:<4}{score['draws']:<4}{score['losses']:<4}")

    # Return tournament results
    tournament_results = {
        "scores": scores,
        "matches": match_results,
        "rankings": ranked_bots
    }

    return tournament_results


def generate_round_robin_pairs(bots: List[BotInterface]) -> List[Tuple[BotInterface, BotInterface]]:
    """
    Generate all possible pairs of bots for a round-robin tournament and shuffle them.
    Each bot will play against every other bot exactly once.

    Args:
        bots: List of bot instances

    Returns:
        A shuffled list of all possible bot pairs
    """
    pairs = []

    # Generate all possible pairs (each bot plays against every other bot once)
    for i in range(len(bots)):
        for j in range(i + 1, len(bots)):
            pairs.append((bots[i], bots[j]))

    # Shuffle the pairs to randomize the match order
    random.shuffle(pairs)

    return pairs

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
    losers_stats = {}  # {bot_name: total_turns_fought}

    while len(bots) > 1:
        print(f"\n=== Round {round_num} ===")
        print(f"{len(bots)} bots competing in this round")        # Run the round and get winners
        winners, round_losers_stats, round_stats = run_tournament_round(bots, round_num, losers_stats, headless=headless)

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


def run_tournament_round(bots: List[BotInterface], round_num: int, losers_stats: Dict[str, int], headless: bool = False) -> Tuple[List[BotInterface], Dict[str, int], Dict]:
    """
    Run a single tournament round.
    Returns:
        - List of winning bots
        - Updated losers stats
        - Round statistics
    
    Args:
        bots: List of bots for this round
        round_num: Current round number
        losers_stats: Stats from previous rounds
        headless: If True, run without visualization
    """
    # Create pairs for this round
    pairs, odd_bot = create_pairs(bots)

    # If there's an odd bot, it gets a bye
    for b1, b2 in pairs:
        print(f"- {b1.name} vs {b2.name}")

    print("odd bot:", odd_bot.name if odd_bot else "None")

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
    round_stats["round_info"] = round_info    # Run matches and collect winners
    winners = []
    losers = []
    
    for b1, b2 in pairs:
        print(f"Match: {b1.name} vs {b2.name}")
        winner, turns_fought, match_info = run_match_with_retry(b1, b2, round_num, len(bots) > 2, headless=headless)

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
        winner, turns_fought, match_info = run_match_with_retry(odd_bot, lucky_loser, round_num, len(bots) > 2, headless=headless)

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


def run_match_with_retry(b1: BotInterface, b2: BotInterface, round_num: int, fast_mode: bool, headless: bool = False) -> Tuple[BotInterface, int, Dict]:
    """
    Run a match between two bots with retry logic for draws.
    Returns:
        - Winner bot (or "NONE" if both disqualified)
        - Number of turns fought
        - Match info dictionary
    
    Args:
        b1: First bot
        b2: Second bot
        round_num: Current round number
        fast_mode: Whether to use fast mode for visualization
        headless: If True, run without visualization
    """
    winner, logger = run_match(b1, b2)

    turns_fought = logger.get_snapshots()[-1]["turn"]
    
    if not headless:
        snapshots = logger.get_snapshots()
        visualizer = Visualizer(logger, b1, b2)
        visualizer.run(snapshots, fast_mode)

    draw_counter = 0
    while winner == "Draw":
        draw_counter += 1
        print("Match ended in a draw")
        winner, logger = run_match(b1, b2)

        turns_fought = logger.get_snapshots()[-1]["turn"]
        
        if not headless:
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
    # Skip these files as they're not bot implementations
    skip_files = {"bot_interface.py", "train.py", "azure_setup.py", "azure_train.py"}

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
                            if bot_instance.name not in ["Sample Bot 1", "Sample Bot 2", "Sample Bot 3"]:
                                bots.append(bot_instance)

                except Exception as e:
                    print(f"Error loading bot from {module_path}: {e}")

    return bots

def run_multiple_tournaments(runs: int, headless: bool = False) -> Dict[str, int]:
    """
    Run multiple round-robin tournaments and track the overall winners.
    
    Args:
        runs (int): Number of tournaments to run
        headless (bool): If True, run without visualization
        
    Returns:
        Dictionary mapping bot names to number of tournament wins
    """
    tournament_wins = {}
    
    for run in range(1, runs + 1):
        print(f"\n===== TOURNAMENT RUN {run}/{runs} =====\n")
        results = run_round_robin_tournament(headless=headless)
        
        # The winner is the first ranked bot
        winner_name = results["rankings"][0][0]
        tournament_wins[winner_name] = tournament_wins.get(winner_name, 0) + 1
        
        # Print current standings after each tournament
        print("\n=== Current Tournament Win Standings ===")
        for bot_name, wins in sorted(tournament_wins.items(), key=lambda x: x[1], reverse=True):
            print(f"{bot_name}: {wins} tournament win(s)")
    
    return tournament_wins

def parse_arguments():
    """
    Parse command line arguments for the application.
    """
    parser = argparse.ArgumentParser(description="Wizard Battle Test Tournament")
    parser.add_argument("--headless", action="store_true", help="Run without visualization")
    parser.add_argument("--tournamentRuns", type=int, default=1, 
                        help="Number of tournament runs to perform (default: 1)")
    return parser.parse_args()

# Example usage
if __name__ == "__main__":
    args = parse_arguments()
    headless = getattr(args, 'headless', False)
    tournament_runs = getattr(args, 'tournamentRuns', 1)
    
    if tournament_runs <= 1:
        results = run_round_robin_tournament(headless=headless)
        print(f"Tournament completed with {len(results['matches'])} matches")
    else:
        tournament_wins = run_multiple_tournaments(tournament_runs, headless=headless)
        print("\n===== FINAL TOURNAMENT STATISTICS =====")
        print(f"Total tournaments run: {tournament_runs}")
        print("\nFinal Tournament Win Standings:")
        for bot_name, wins in sorted(tournament_wins.items(), key=lambda x: x[1], reverse=True):
            win_percentage = (wins / tournament_runs) * 100
            print(f"{bot_name}: {wins} wins ({win_percentage:.1f}%)")

    # Uncommented for regular tournament if needed
    # winner, stats = run_tournament(headless=headless)
    # print(f"Tournament completed with {len(stats['matches'])} matches across {len(stats['rounds'])} rounds")