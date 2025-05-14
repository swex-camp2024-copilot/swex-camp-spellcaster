import random
import math
from bots.bot_interface import BotInterface


class RedWizardBot(BotInterface):
    def __init__(self):
        self._name = "Red Wizard Bot"
        self._sprite_path = "assets/wizards/red_wizard.png"
        self._minion_sprite_path = "assets/minions/minion_1.png"
        self.previous_positions = []
        self.target_position = None
        self.retreat_mode = False
        self.consecutive_same_position = 0

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
        board_size = state.get("board_size", 10)

        self_pos = self_data["position"]
        opp_pos = opp_data["position"]
        cooldowns = self_data["cooldowns"]
        mana = self_data["mana"]
        hp = self_data["hp"]

        # Track if we're staying in the same position
        if self.previous_positions and self_pos == self.previous_positions[-1]:
            self.consecutive_same_position += 1
        else:
            self.consecutive_same_position = 0

        # Keep track of our positions for later strategies
        self.previous_positions.append(self_pos)
        if len(self.previous_positions) > 5:
            self.previous_positions.pop(0)

        # Initialize move and spell
        move = [0, 0]
        spell = None

        # Distance calculation helpers
        def chebyshev_dist(a, b):
            return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

        def manhattan_dist(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def euclidean_dist(a, b):
            return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

        # 1. Emergency healing if HP is low
        if hp < 30 and cooldowns["heal"] == 0 and mana >= 25:
            spell = {"name": "heal"}
            # Go into retreat mode
            self.retreat_mode = True

        # 2. Shield activation when exposed or when low on health
        if not self_data["shield_active"] and cooldowns["shield"] == 0 and mana >= 20:
            if hp < 50 or manhattan_dist(self_pos, opp_pos) <= 3:
                spell = {"name": "shield"}

        # 3. Fireball if enemy is in range and we have enough mana
        fireball_range = 5
        if cooldowns["fireball"] == 0 and mana >= 30 and chebyshev_dist(self_pos, opp_pos) <= fireball_range:
            spell = {
                "name": "fireball",
                "target": opp_pos
            }

        # 4. Try to use blink to position strategically
        if cooldowns["blink"] == 0 and mana >= 10:
            blink_distance = 2
            
            # If low HP, blink away from opponent
            if hp < 40 or self.retreat_mode:
                dx = self_pos[0] - opp_pos[0]
                dy = self_pos[1] - opp_pos[1]
                
                # Normalize direction
                mag = max(1, abs(dx) + abs(dy))
                dx = int(round(dx * blink_distance / mag))
                dy = int(round(dy * blink_distance / mag))
                
                target_x = min(max(0, self_pos[0] + dx), board_size - 1)
                target_y = min(max(0, self_pos[1] + dy), board_size - 1)
                
                spell = {
                    "name": "blink",
                    "target": [target_x, target_y]
                }
            # Blink closer to opponent if we're at good health and not in retreat
            elif hp > 60 and manhattan_dist(self_pos, opp_pos) > fireball_range and not self.retreat_mode:
                dx = opp_pos[0] - self_pos[0]
                dy = opp_pos[1] - self_pos[1]
                
                # Normalize direction
                mag = max(1, abs(dx) + abs(dy))
                dx = int(round(dx * blink_distance / mag))
                dy = int(round(dy * blink_distance / mag))
                
                target_x = min(max(0, self_pos[0] + dx), board_size - 1)
                target_y = min(max(0, self_pos[1] + dy), board_size - 1)
                
                spell = {
                    "name": "blink",
                    "target": [target_x, target_y]
                }

        # 5. Try to summon a minion if we have enough mana and no active minion
        own_minions = [m for m in minions if m["owner"] == self_data["name"]]
        if not own_minions and cooldowns["summon"] == 0 and mana >= 50:
            spell = {"name": "summon"}

        # 6. If we can do a melee attack, try to move adjacent to enemy
        if cooldowns["melee_attack"] == 0:
            # If we're already adjacent, attack
            if manhattan_dist(self_pos, opp_pos) == 1:
                spell = {
                    "name": "melee_attack",
                    "target": opp_pos
                }
            # Otherwise, try to move adjacent if we have good health
            elif hp > 50 and not self.retreat_mode:
                dx = opp_pos[0] - self_pos[0]
                dy = opp_pos[1] - self_pos[1]
                
                # Move in the direction of the opponent
                move = [
                    max(-1, min(1, dx)),
                    max(-1, min(1, dy))
                ]        
        # 7. Teleport strategy - use teleport to escape or to get close to artifacts
        if cooldowns["teleport"] == 0 and mana >= 20:
            # Priority 1: Low HP - teleport to health artifact if available
            health_artifacts = [a for a in artifacts if a["type"] == "health"]
            if hp < 40 and health_artifacts:
                # Find nearest health artifact
                nearest_health = min(health_artifacts, key=lambda a: manhattan_dist(self_pos, a["position"]))
                spell = {
                    "name": "teleport",
                    "target": nearest_health["position"]
                }
            # Priority 2: Teleport to any artifact if not in immediate danger
            elif artifacts and hp > 30 and manhattan_dist(self_pos, opp_pos) > 2:
                # Find nearest artifact
                nearest_artifact = min(artifacts, key=lambda a: manhattan_dist(self_pos, a["position"]))
                spell = {
                    "name": "teleport",
                    "target": nearest_artifact["position"]
                }
            # Priority 3: Emergency teleport if opponent is too close and we're weak
            elif hp < 30 and manhattan_dist(self_pos, opp_pos) <= 2:
                # First try to find a health artifact anywhere on the board
                if health_artifacts:
                    # Ideally find one that's far from opponent
                    best_health = max(health_artifacts, 
                                     key=lambda a: manhattan_dist(a["position"], opp_pos))
                    spell = {
                        "name": "teleport",
                        "target": best_health["position"]
                    }
                # If no health artifacts, teleport to a corner opposite of the opponent
                else:
                    corners = [[0, 0], [0, board_size-1], [board_size-1, 0], [board_size-1, board_size-1]]
                    # Find the corner furthest from opponent
                    best_corner = max(corners, key=lambda c: manhattan_dist(c, opp_pos))
                    spell = {
                        "name": "teleport",
                        "target": best_corner
                    }

        # 8. Default movement strategy if no special movement has been decided
        if move == [0, 0]:
            # If we're stuck in the same position for too long, make a random move
            if self.consecutive_same_position >= 3:
                move = [random.randint(-1, 1), random.randint(-1, 1)]
            
            # If we're in retreat mode, move away from opponent
            elif self.retreat_mode:
                dx = self_pos[0] - opp_pos[0]
                dy = self_pos[1] - opp_pos[1]
                
                # Normalize direction
                move = [
                    max(-1, min(1, dx)),
                    max(-1, min(1, dy))
                ]
                
                # If we've recovered enough HP, exit retreat mode
                if hp > 60:
                    self.retreat_mode = False
            
            # Move toward artifacts if they exist and we're not in danger
            elif artifacts and hp > 30:
                nearest_artifact = min(artifacts, key=lambda a: manhattan_dist(self_pos, a["position"]))
                target = nearest_artifact["position"]
                dx = target[0] - self_pos[0]
                dy = target[1] - self_pos[1]
                
                move = [
                    max(-1, min(1, dx)),
                    max(-1, min(1, dy))
                ]
            
            # If no artifact and not retreating, move toward opponent (if we're strong) or away (if we're weak)
            else:
                if hp > opp_data["hp"] or hp > 70:
                    # Move toward opponent
                    dx = opp_pos[0] - self_pos[0]
                    dy = opp_pos[1] - self_pos[1]
                else:
                    # Move away from opponent
                    dx = self_pos[0] - opp_pos[0]
                    dy = self_pos[1] - opp_pos[1]
                
                # Normalize direction
                move = [
                    max(-1, min(1, dx)),
                    max(-1, min(1, dy))
                ]

        return {
            "move": move,
            "spell": spell
        }
