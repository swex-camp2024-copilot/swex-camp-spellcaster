import random
from bots.bot_interface import BotInterface

class Bot3(BotInterface):
    def __init__(self):
        self._name = "bant Bot"
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

        def manhattan_dist(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        # 0. Use MELEE ATTACK if adjacent to enemy
        enemies = [e for e in minions if e["owner"] != self_data["name"]]
        enemies.append(opp_data)
        adjacent_enemies = [e for e in enemies if manhattan_dist(self_pos, e["position"]) == 1]
        if adjacent_enemies and cooldowns["melee_attack"] == 0:
            target = min(adjacent_enemies, key=lambda e: e["hp"])
            spell = {"name": "melee_attack", "target": target["position"]}

        # 1. FIREBALL if in range
        if not spell and cooldowns["fireball"] == 0 and mana >= 30 and dist(self_pos, opp_pos) <= 5:
            spell = {"name": "fireball", "target": opp_pos}

        # 2. Use SHIELD if low HP
        elif not spell and hp <= 50 and cooldowns["shield"] == 0 and mana >= 20:
            spell = {"name": "shield"}

        # 3. HEAL if available and HP isn't full
        elif not spell and hp <= 50 and cooldowns["heal"] == 0 and mana >= 25:
            spell = {"name": "heal"}

        # 4. SUMMON minion if none exists
        elif not spell and cooldowns["summon"] == 0 and mana >= 50:
            has_minion = any(m["owner"] == self_data["name"] for m in minions)
            if not has_minion:
                spell = {"name": "summon"}

        # 5. TELEPORT onto artifact if low mana/hp
        if not spell and cooldowns["teleport"] == 0 and mana >= 40 and artifacts:
            critical = mana <= 40 or hp <= 60
            if critical:
                nearest = min(artifacts, key=lambda a: dist(self_pos, a["position"]))
                spell = {"name": "teleport", "target": nearest["position"]}

        # 6. Move toward closest artifact if we need something
        if not spell and artifacts and (mana <= 60 or hp <= 60):
            nearest = min(artifacts, key=lambda a: dist(self_pos, a["position"]))
            if(manhattan_dist(nearest["position"], min(enemies, key=lambda e: dist(nearest["position"], e["position"]))["position"]) > 1):
                move = self.move_toward(self_pos, nearest["position"])

        # 7. If nothing else, close the gap toward opponent
        elif not spell:
            move = self.move_toward(self_pos, opp_pos)

        return {"move": move, "spell": spell}

    def move_toward(self, start, target):
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        step_x = 1 if dx > 0 else -1 if dx < 0 else 0
        step_y = 1 if dy > 0 else -1 if dy < 0 else 0
        return [step_x, step_y]