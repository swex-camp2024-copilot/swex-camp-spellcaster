from game.engine import GameEngine

def run_match(bot1, bot2, max_turns=50, verbose=False):
    engine = GameEngine(bot1, bot2)
    winner = None  # ← Important fix

    for _ in range(max_turns):
        winner = engine.run_turn()
        if winner:
            break

    engine.logger.finalize()

    if verbose:
        engine.logger.print_log()

    return winner or "Draw", engine.logger
