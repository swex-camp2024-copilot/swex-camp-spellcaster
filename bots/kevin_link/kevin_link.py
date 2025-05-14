import random

from bots.bot_interface import BotInterface


class KevinLink(BotInterface):
    def __init__(self):
        self._name = "Kevin Link"
        self._sprite_path = "assets/wizards/kevin_link.png"
        self._minion_sprite_path = "assets/minions/minion_2.png"
        self._first_round = True
        self._last_artifact_positions = []  # Remember artifact positions
        self._enemy_positions = []  # Track enemy movement patterns
        self._has_summoned = False  # Track if we've summoned a minion

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
        
        # Update tracking data
        self._enemy_positions.append(opp_pos)
        if len(self._enemy_positions) > 5:
            self._enemy_positions = self._enemy_positions[-5:]  # Keep only last 5
        
        # Track artifact positions
        self._last_artifact_positions = [a["position"] for a in artifacts]

        move = [0, 0]
        spell = None

        def dist(a, b):
            return max(abs(a[0] - b[0]), abs(a[1] - b[1]))  # Chebyshev

        def manhattan_dist(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
            
        # Calculate if we can predict opponent's next position
        predicted_position = self._predict_enemy_position(opp_pos)

        # 1. FIRST ROUND STRATEGY - Shield for protection
        if self._first_round and cooldowns["shield"] == 0 and mana >= 20:
            spell = {"name": "shield"}
            self._first_round = False
            return {"move": [0, 0], "spell": spell}
        elif self._first_round:
            self._first_round = False
        
        # 2. DEFENSIVE PRIORITY - Shield when opponent is close and we're vulnerable
        if not self_data.get("shield_active", False) and cooldowns["shield"] == 0 and mana >= 20:
            if dist(self_pos, opp_pos) <= 3 and hp <= 70:  # More aggressive shielding
                spell = {"name": "shield"}
        
        # 3. OFFENSIVE OPPORTUNITY - Fireball at predicted position if available
        if not spell and cooldowns["fireball"] == 0 and mana >= 30:
            if predicted_position and dist(self_pos, predicted_position) <= 5:
                target_pos = predicted_position
            elif dist(self_pos, opp_pos) <= 5:
                target_pos = opp_pos
            else:
                target_pos = None
                
            if target_pos:
                spell = {
                    "name": "fireball",
                    "target": target_pos
                }
        
        # 4. TACTICAL BLINK - Use blink to either escape or get in position
        if not spell and cooldowns["blink"] == 0 and mana >= 10:
            # Blink away if low health and enemy is close
            if hp <= 40 and dist(self_pos, opp_pos) <= 2:
                # Blink away from opponent
                direction = self._direction_away_from(self_pos, opp_pos, 2)
                if direction:
                    spell = {
                        "name": "blink",
                        "target": direction
                    }
            # Blink toward artifact if we need resources
            elif (mana <= 40 or hp <= 60) and artifacts:
                nearest = min(artifacts, key=lambda a: dist(self_pos, a["position"]))
                if dist(self_pos, nearest["position"]) > 2:  # Only blink if it's not too close
                    direction = self._direction_toward(self_pos, nearest["position"], 2)
                    spell = {
                        "name": "blink",
                        "target": direction
                    }
                    
        # 5. MELEE ATTACK if adjacent to enemy
        if not spell:
            enemies = [e for e in minions if e["owner"] != self_data["name"]]
            enemies.append(opp_data)  # Add opponent to potential targets
            
            adjacent_enemies = [e for e in enemies if manhattan_dist(self_pos, e["position"]) == 1]
            if adjacent_enemies and cooldowns["melee_attack"] == 0:
                # Pick the enemy with lowest HP
                target = min(adjacent_enemies, key=lambda e: e["hp"])
                spell = {
                    "name": "melee_attack",
                    "target": target["position"]
                }
        
        # 6. HEALING STRATEGY - More aggressive healing
        if not spell and hp <= 75 and cooldowns["heal"] == 0 and mana >= 25:
            spell = {"name": "heal"}
        
        # 7. SUMMON MINION STRATEGY - Earlier if we have mana to spare
        has_minion = any(m["owner"] == self_data["name"] for m in minions)
        if not spell and not has_minion and cooldowns["summon"] == 0 and mana >= 60:
            spell = {"name": "summon"}
            self._has_summoned = True
            
        # 8. TELEPORT STRATEGY - For resource collection and tactical positioning
        if not spell and cooldowns["teleport"] == 0 and mana >= 40 and artifacts:
            # Teleport when critical or strategic advantage
            critical = mana <= 40 or hp <= 60
            strategic = dist(self_pos, opp_pos) > 7  # Teleport to get back in the fight
            
            if critical or strategic:
                best_artifact = self._choose_best_artifact(artifacts, self_pos, opp_pos, hp, mana)
                spell = {
                    "name": "teleport",
                    "target": best_artifact["position"]
                }
        
        # 9. MOVEMENT STRATEGY - Smart movement based on state
        if not spell:
            # Move toward artifact if needed
            if artifacts and (mana <= 70 or hp <= 70):
                best_artifact = self._choose_best_artifact(artifacts, self_pos, opp_pos, hp, mana)
                move = self.move_toward(self_pos, best_artifact["position"])
            # Maintain optimal combat distance if we have good mana/hp
            elif hp > 60 and mana > 40:
                optimal_distance = 4  # Stay at fireball range but not too close
                current_distance = dist(self_pos, opp_pos)
                
                if current_distance < optimal_distance:
                    # Back away slightly
                    move = self._direction_away_from(self_pos, opp_pos, 1)
                elif current_distance > optimal_distance:
                    # Move closer
                    move = self.move_toward(self_pos, opp_pos)
                else:
                    # Strafe to avoid predictability
                    move = self._strafe_around(self_pos, opp_pos)
            else:
                # Default: move toward opponent
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
        
    def _direction_away_from(self, start, target, distance=1):
        dx = start[0] - target[0]
        dy = start[1] - target[1]
        
        # Normalize direction
        magnitude = max(1, abs(dx) + abs(dy))
        dx = int(round(dx * distance / magnitude))
        dy = int(round(dy * distance / magnitude))
        
        # Ensure we're moving at least 1 square if possible
        if dx == 0 and dy == 0 and distance > 0:
            dx = random.choice([-1, 1])
            
        return [dx, dy]
        
    def _direction_toward(self, start, target, distance=1):
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        
        # Normalize direction
        magnitude = max(1, abs(dx) + abs(dy))
        dx = int(round(dx * distance / magnitude))
        dy = int(round(dy * distance / magnitude))
        
        # Ensure we're moving at least 1 square if possible
        if dx == 0 and dy == 0 and distance > 0:
            dx = random.choice([-1, 1])
            
        return [dx, dy]
    
    def _strafe_around(self, start, target):
        """Move perpendicular to the line between start and target"""
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        
        # Choose perpendicular direction
        if abs(dx) > abs(dy):
            # Move vertically
            return [0, 1 if random.random() > 0.5 else -1]
        else:
            # Move horizontally
            return [1 if random.random() > 0.5 else -1, 0]
    
    def _predict_enemy_position(self, current_pos):
        """Attempt to predict enemy's next position based on past movements"""
        if len(self._enemy_positions) < 3:
            return None
            
        # Look for patterns in last few moves
        last_positions = self._enemy_positions[-3:]
        dx1 = last_positions[1][0] - last_positions[0][0]
        dy1 = last_positions[1][1] - last_positions[0][1]
        dx2 = last_positions[2][0] - last_positions[1][0]
        dy2 = last_positions[2][1] - last_positions[1][1]
        
        # If consistent movement, predict next position
        if dx1 == dx2 and dy1 == dy2:
            predicted_x = current_pos[0] + dx1
            predicted_y = current_pos[1] + dy1
            # Ensure within bounds
            predicted_x = max(0, min(9, predicted_x))
            predicted_y = max(0, min(9, predicted_y))
            return [predicted_x, predicted_y]
        
        return None
        
    def _choose_best_artifact(self, artifacts, self_pos, opp_pos, hp, mana):
        """Choose the best artifact based on need and tactical advantage"""
        # Score each artifact
        scored_artifacts = []
        for artifact in artifacts:
            score = 0
            
            # Distance factor (closer is better)
            distance = max(1, self.manhattan_dist(self_pos, artifact["position"]))
            score -= distance * 2
            
            # Need-based scoring
            if hp <= 40 and artifact["type"] == "health":
                score += 20
            elif mana <= 30 and artifact["type"] == "mana":
                score += 20
            elif artifact["type"] == "cooldown":
                score += 10  # Generally useful
                
            # Tactical positioning (don't get too close to opponent)
            enemy_distance = self.manhattan_dist(artifact["position"], opp_pos)
            if enemy_distance <= 2:
                score -= 15  # Avoid artifacts too close to enemy
                
            scored_artifacts.append((score, artifact))
            
        # Return the highest scored artifact, or closest if all scores are negative
        if scored_artifacts:
            return max(scored_artifacts, key=lambda x: x[0])[1]
        else:
            # Fallback - closest artifact
            return min(artifacts, key=lambda a: self.manhattan_dist(self_pos, a["position"]))
            
    def manhattan_dist(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1]) 