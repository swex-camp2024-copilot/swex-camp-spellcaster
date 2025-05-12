from bots.sample_bot.sample_bot_1 import SampleBot1
from bots.sample_bot.sample_bot_2 import SampleBot2
from simulator.match import run_match
from simulator.visualizer import Visualizer

bot1 = SampleBot1()
bot2 = SampleBot2()

winner, logger = run_match(bot1, bot2)
snapshots = logger.get_snapshots()
print(snapshots)

visualizer = Visualizer(logger, bot1, bot2)
visualizer.run(snapshots)
