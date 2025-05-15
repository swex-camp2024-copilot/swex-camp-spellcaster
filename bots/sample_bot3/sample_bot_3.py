import random

from bots.bot_interface import BotInterface


class SampleBot3(BotInterface):
    def __init__(self):
        self._name = "Sample Bot 3"
        self._sprite_path = "assets/wizards/sample_bot3.png"
        self._minion_sprite_path = "assets/minions/minion_3.png"

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
            return max(abs(a[0] - b[0]), abs(a[1] - b[1]))  # Chebyshev

        # 1. Use FIREBALL if opponent is in range
        if cooldowns["fireball"] == 0 and mana >= 30 and dist(self_pos, opp_pos) <= 5:
            spell = {
                "name": "fireball",
                "target": opp_pos
            }

        # 2. Use HEAL if HP is low
        elif hp <= 50 and cooldowns["heal"] == 0 and mana >= 25:
            spell = {"name": "heal"}

        # 3. Use SHIELD if under attack
        elif cooldowns["shield"] == 0 and mana >= 20 and hp <= 70:
            spell = {"name": "shield"}

        # 4. Move toward opponent if no spell is cast
        if not spell:
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