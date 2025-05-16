
import random
from bots.bot_interface import BotInterface


class Rade(BotInterface):
    def __init__(self):
        self._name = "Rade"
        self._sprite_path = "assets/wizards/Rade.png"
        self._minion_sprite_path = "assets/minions/minion_1.png"
        self.priority = ['melee_attack', 'fireball', 'shield', 'summon', 'teleport', 'heal']
        self.params = {'fireball_mana': 40, 'low_hp_threshold': 20, 'teleport_critical_hp': 30, 'summon_minion': True}

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
        artifacts = state.get("artifacts", [])
        minions = state.get("minions", [])

        self_pos = self_data["position"]
        opp_pos = opp_data["position"]
        cooldowns = self_data["cooldowns"]
        mana = self_data["mana"]
        hp = self_data["hp"]

        move = [0, 0]
        spell = None

        def dist(a, b):
            return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

        def manhattan_dist(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        enemies = [e for e in minions if e["owner"] != self_data["name"]]
        enemies.append(opp_data)
        adjacent_enemies = [e for e in enemies if manhattan_dist(self_pos, e["position"]) == 1]

        for s in self.priority:
            if s == "melee_attack" and adjacent_enemies and cooldowns["melee_attack"] == 0:
                target = min(adjacent_enemies, key=lambda e: e["hp"])
                spell = {
                    "name": "melee_attack",
                    "target": target["position"]
                }
            elif s == "fireball" and cooldowns["fireball"] == 0 and mana >= self.params["fireball_mana"] and dist(self_pos, opp_pos) <= 5:
                spell = {
                    "name": "fireball",
                    "target": opp_pos
                }
            elif s == "shield" and hp <= self.params["low_hp_threshold"] and cooldowns["shield"] == 0 and mana >= 20:
                spell = {"name": "shield"}
            elif s == "heal" and hp <= 80 and cooldowns["heal"] == 0 and mana >= 25:
                spell = {"name": "heal"}
            elif s == "summon" and cooldowns["summon"] == 0 and mana >= 50:
                has_minion = any(m["owner"] == self_data["name"] for m in minions)
                if self.params["summon_minion"] and not has_minion:
                    spell = {"name": "summon"}
            elif s == "teleport" and cooldowns["teleport"] == 0 and mana >= 40 and artifacts:
                if mana <= self.params["teleport_critical_hp"] or hp <= self.params["teleport_critical_hp"]:
                    nearest = min(artifacts, key=lambda a: dist(self_pos, a["position"]))
                    spell = {
                        "name": "teleport",
                        "target": nearest["position"]
                    }

            if spell:
                break

        if not spell and artifacts and (mana <= 60 or hp <= 60):
            nearest = min(artifacts, key=lambda a: dist(self_pos, a["position"]))
            move = self.move_toward(self_pos, nearest["position"])
        elif not spell:
            move = self.move_toward(self_pos, opp_pos)

        return {
            "move": move,
            "spell": spell
        }

    def move_toward(self, start, target):
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        step_x = 1 if dx > 0 else -1 if dx < 0 else 0
        step_y = 1 if dy > 0 else -1 if dy < 0 else 0
        return [step_x, step_y]
