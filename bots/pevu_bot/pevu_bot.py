
from bots.bot_interface import BotInterface
from game.rules import SPELLS


class PevuBot(BotInterface):
    def __init__(self):
        # Adding these properties makes the interface clearer
        self._name = "Pevu bot"
        self._sprite_path = "assets/wizards/sample_bot1.png"
        self._minion_sprite_path = "assets/minions/minion_1.png"

    @property
    def name(self):
        return self._name

    @property
    def sprite_path(self):
        return self._sprite_path

    @property
    def minion_sprite_path(self):
        return self._minion_sprite_path

    def decide(self, state):
        self_data = state["self"]
        opp_data = state["opponent"]
        minions = state["minions"]
        turn = state["turn"]
        artifacts = state["artifacts"]

        self_pos = self_data["position"]
        opp_pos = opp_data["position"]
        cooldowns = self_data["cooldowns"]
        mana = self_data["mana"]

        spell = None
        target = None
        move = [0, 0]  # Default no movement

        def dist(a, b):
            return max(abs(a[0] - b[0]), abs(a[1] - b[1]))  # Chebyshev distance

            # Rule: Always teleport to a mana potion artifact if one exists
        mana_artifacts = [artifact for artifact in artifacts if artifact["type"] == "mana"]
        if mana_artifacts and cooldowns["teleport"] == 0 and mana >= SPELLS["teleport"]["cost"]:
            nearest_mana_artifact = min(mana_artifacts, key=lambda a: dist(self_pos, a["position"]))
            spell = {
                "name": "teleport",
                "target": nearest_mana_artifact["position"]
                }
            return {
                "move": move,
                "spell": spell
             }

        # Rule 0: If this is your first turn, summon a minion
        if turn == 1 and cooldowns["summon"] == 0 and mana >= SPELLS["summon"]["cost"]:
            spell = {"name": "summon"}

        # Rule 1: If opponent is in range and their cooldown for fireball is 0, cast spell shield
        elif dist(self_pos, opp_pos) <= SPELLS["fireball"]["range"] and opp_data["cooldowns"]["fireball"] == 0:
            if cooldowns["shield"] == 0 and mana >= SPELLS["shield"]["cost"]:
                spell = {"name": "shield"}

        # Rule 2: If enemy minion is in range and opponent is not, cast fireball at the minion
        elif dist(self_pos, opp_pos) > SPELLS["fireball"]["range"]:
            for minion in minions:
                if dist(self_pos, minion["position"]) <= SPELLS["fireball"]["range"] and not (minion["owner"] == self.name):
                    if cooldowns["fireball"] == 0 and mana >= SPELLS["fireball"]["cost"]:
                        spell = {"name": "fireball", "target": minion["position"]}
                        break

        # Rule 3: If opponent is in range, cast fireball at them
        elif dist(self_pos, opp_pos) <= SPELLS["fireball"]["range"]:
            if cooldowns["fireball"] == 0 and mana >= SPELLS["fireball"]["cost"]:
                spell = {"name": "fireball", "target": opp_pos}

        # Rule 5: If opponent is in range, cast fireball at them
        elif dist(self_pos, opp_pos) <= SPELLS["melee_attack"]["range"]:
            if cooldowns["melee_attack"] == 0:
                spell = {"name": "melee_attack", "target": opp_pos}


        return {
            "move": move,
            "spell": spell
        }