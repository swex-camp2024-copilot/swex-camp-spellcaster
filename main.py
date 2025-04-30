from bots.sample_bot.sample_bot import SampleBot
from simulator.match import run_match
from simulator.visualizer import Visualizer

bot1 = SampleBot()
bot2 = SampleBot()

winner, logger = run_match(bot1, bot2)
snapshots = logger.get_snapshots()
print(snapshots)

visualizer = Visualizer(logger)
visualizer.run(snapshots)
