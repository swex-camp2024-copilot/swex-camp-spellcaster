from simulator.match import run_match
from simulator.visualizer import Visualizer
from bots.sample_bot import SampleBot

bot1 = SampleBot()
bot2 = SampleBot()

winner, logger = run_match(bot1, bot2)
snapshots = logger.get_snapshots()

visualizer = Visualizer(logger)
visualizer.run(snapshots)
