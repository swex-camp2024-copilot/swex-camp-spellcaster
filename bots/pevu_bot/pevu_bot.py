from bots.bot_interface import BotInterface
from game.rules import SPELLS, BOARD_SIZE


class PevuBot(BotInterface):
    def __init__(self):
        # Adding these properties makes the interface clearer
        self._name = "Pevu bot"
        self._sprite_path = "assets/wizards/pevu_bot.png"
        self._minion_sprite_path = "assets/minions/minion_pevu.png"

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

        mana_artifacts = [artifact for artifact in artifacts if artifact["type"] == "mana"]

        enemy_minion_exists = False
        for minion in minions:
            if minion["owner"] == self.name: enemy_minion_exists = True

        # Rule 0: If this is your first turn, summon a minion
        if turn == 1 and cooldowns["summon"] == 0 and mana >= SPELLS["summon"]["cost"]:
            spell = {"name": "summon"}

        # Rule 1: If opponent is in range and their cooldown for fireball is 0, cast spell shield
        elif dist(self_pos, opp_pos) <= SPELLS["fireball"]["range"] and opp_data["cooldowns"]["fireball"] == 0 and not self_data.get("shield_active", False):
            if cooldowns["shield"] == 0 and mana >= SPELLS["shield"]["cost"]:
                spell = {"name": "shield"}

        # Rule 2: If enemy minion is in range and opponent is not, cast fireball at the minion
        elif dist(self_pos, opp_pos) > SPELLS["fireball"]["range"] and enemy_minion_exists:
            for minion in minions:
                if dist(self_pos, minion["position"]) <= SPELLS["fireball"]["range"] and not (
                        minion["owner"] == self.name):
                    if cooldowns["fireball"] == 0 and mana >= SPELLS["fireball"]["cost"]:
                        spell = {"name": "fireball", "target": minion["position"]}
                        break

        # Rule 3: If opponent is in range, cast fireball at them
        elif dist(self_pos, opp_pos) <= SPELLS["fireball"]["range"] and cooldowns["fireball"] == 0 and mana >= \
                SPELLS["fireball"]["cost"]:
            spell = {"name": "fireball", "target": opp_pos}

        # Rule 5: If opponent is in range, cast melee attack them
        elif dist(self_pos, opp_pos) <= SPELLS["melee_attack"]["range"] and cooldowns["melee_attack"] == 0:
            spell = {"name": "melee_attack", "target": opp_pos}

        # Rule 6: Summon a minion if opponent is 6 or more fields away and summon cooldown is 0
        elif dist(self_pos, opp_pos) >= 6 and cooldowns["summon"] == 0 and mana >= SPELLS["summon"]["cost"]:
            spell = {"name": "summon"}
            return {
                "move": move,
                "spell": spell
            }
        # Rule 6: attack minion in melee if he is in range
        for minion in minions:
            if minion["owner"] != self.name and dist(self_pos, minion["position"]) <= SPELLS["melee_attack"]["range"]:
                if cooldowns["melee_attack"] == 0:
                    spell = {"name": "melee_attack", "target": minion["position"]}

        # Rule 1: If you have 30 HP more than the opponent and sufficient mana, move towards the opponent
        if self_data["hp"] >= opp_data["hp"] + 30 and mana > 0:
            dx = opp_pos[0] - self_pos[0]
            dy = opp_pos[1] - self_pos[1]
            move = [dx // abs(dx) if dx != 0 else 0, dy // abs(dy) if dy != 0 else 0]

        # Rule 2: If there is an artifact within 5 fields, move towards it
        elif artifacts:
            nearest_artifact = min(artifacts, key=lambda a: dist(self_pos, a["position"]))
            if dist(self_pos, nearest_artifact["position"]) <= 5:
                dx = nearest_artifact["position"][0] - self_pos[0]
                dy = nearest_artifact["position"][1] - self_pos[1]
                move = [dx // abs(dx) if dx != 0 else 0, dy // abs(dy) if dy != 0 else 0]

        # Rule 3: teleport on mana artifact
        elif mana_artifacts and cooldowns["teleport"] == 0 and mana >= SPELLS["teleport"]["cost"]:
            nearest_mana_artifact = min(mana_artifacts, key=lambda a: dist(self_pos, a["position"]))
            spell = {
                "name": "teleport",
                "target": nearest_mana_artifact["position"]
            }
            return {
                "move": move,
                "spell": spell
            }
        # Rule 4: Try to maintain at least 2 fields of distance from enemy minions
        elif any(dist(self_pos, minion["position"]) < 2 for minion in minions if minion["owner"] != self.name):
            for minion in minions:
                if minion["owner"] != self.name and dist(self_pos, minion["position"]) < 2:
                    dx = self_pos[0] - minion["position"][0]
                    dy = self_pos[1] - minion["position"][1]
                    move = [dx // abs(dx) if dx != 0 else 0, dy // abs(dy) if dy != 0 else 0]
                    break

        # Rule 5: If no artifacts exist, move towards the center of the field
        elif not artifacts:
            center = [BOARD_SIZE // 2, BOARD_SIZE // 2]
            dx = center[0] - self_pos[0]
            dy = center[1] - self_pos[1]
            move = [dx // abs(dx) if dx != 0 else 0, dy // abs(dy) if dy != 0 else 0]

        return {
            "move": move,
            "spell": spell
        }
