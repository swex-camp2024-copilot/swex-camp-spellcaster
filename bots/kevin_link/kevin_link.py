import random
import math
from collections import deque

from bots.bot_interface import BotInterface


class KevinLink(BotInterface):
    def __init__(self):
        self._name = "Kevin Link"
        self._sprite_path = "assets/wizards/kevin_link.png"
        self._minion_sprite_path = "assets/minions/minion_2.png"
        self._first_round = True
        self._last_artifact_positions = []  # Remember artifact positions
        self._enemy_positions = deque(maxlen=10)  # Track more enemy positions
        self._has_summoned = False  # Track if we've summoned a minion
        self._turn_count = 0
        self._enemy_hp_history = deque(maxlen=5)  # Track enemy HP changes
        self._self_hp_history = deque(maxlen=5)  # Track own HP changes
        self._last_spell_used = None
        self._enemy_patterns = {
            "aggressive": 0,
            "defensive": 0,
            "resource_focused": 0
        }

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
        self._turn_count += 1
        self_data = state["self"]
        opp_data = state["opponent"]
        artifacts = state.get("artifacts", [])
        minions = state.get("minions", [])

        self_pos = self_data["position"]
        opp_pos = opp_data["position"]
        cooldowns = self_data["cooldowns"]
        mana = self_data["mana"]
        hp = self_data["hp"]
        
        # Update opponent tracking data
        self._enemy_positions.append(opp_pos)
        self._update_enemy_behavior(opp_data, self_data, artifacts, minions)
        
        # Track HP histories
        if len(self._enemy_hp_history) > 0:
            hp_change = opp_data["hp"] - self._enemy_hp_history[-1]
            if hp_change < 0:  # Damage dealt
                self._enemy_patterns["aggressive"] += 1
        self._enemy_hp_history.append(opp_data["hp"])
        self._self_hp_history.append(hp)
        
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
        enemy_behavior = self._get_dominant_enemy_behavior()
        
        # Debug enemy behavior tracking
        # print(f"Enemy behavior: {enemy_behavior}, Turn: {self._turn_count}")
        # print(f"Scores: {self._enemy_patterns}")

        # 1. FIRST ROUND STRATEGY - Shield for protection
        if self._first_round and cooldowns["shield"] == 0 and mana >= 20:
            spell = {"name": "shield"}
            self._first_round = False
            self._last_spell_used = "shield"
            return {"move": [0, 0], "spell": spell}
        elif self._first_round:
            self._first_round = False
            
        # 2. COUNTER-STRATEGY BASED ON ENEMY BEHAVIOR
        if enemy_behavior == "aggressive":
            # Prioritize defense against aggressive opponents
            if not self_data.get("shield_active", False) and cooldowns["shield"] == 0 and mana >= 20:
                if dist(self_pos, opp_pos) <= 5:  # More aggressive shielding
                    spell = {"name": "shield"}
                    self._last_spell_used = "shield"
        
        # 3. DEFENSIVE PRIORITY - Shield when opponent is close and we're vulnerable
        if not spell and not self_data.get("shield_active", False) and cooldowns["shield"] == 0 and mana >= 20:
            if dist(self_pos, opp_pos) <= 3 and hp <= 70:  # More aggressive shielding
                spell = {"name": "shield"}
                self._last_spell_used = "shield"
        
        # 4. OFFENSIVE OPPORTUNITY - Fireball at predicted position if available
        if not spell and cooldowns["fireball"] == 0 and mana >= 30:
            if predicted_position and dist(self_pos, predicted_position) <= 5:
                # Check if there are any minions near the predicted position for splash damage
                nearby_targets = self._count_targets_near_position(predicted_position, minions, 1)
                if nearby_targets >= 1:  # Target has at least one nearby entity for splash
                    target_pos = predicted_position
                else:
                    target_pos = opp_pos if dist(self_pos, opp_pos) <= 5 else None
            elif dist(self_pos, opp_pos) <= 5:
                # Check for splash damage opportunity
                nearby_targets = self._count_targets_near_position(opp_pos, minions, 1)
                target_pos = opp_pos if nearby_targets > 0 else opp_pos
            else:
                target_pos = None
                
            if target_pos:
                spell = {
                    "name": "fireball",
                    "target": target_pos
                }
                self._last_spell_used = "fireball"
        
        # 5. TACTICAL BLINK - Use blink to either escape or get in position
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
                    self._last_spell_used = "blink"
            # Blink toward artifact if we need resources
            elif (mana <= 40 or hp <= 60) and artifacts:
                nearest = min(artifacts, key=lambda a: dist(self_pos, a["position"]))
                if dist(self_pos, nearest["position"]) > 2:  # Only blink if it's not too close
                    direction = self._direction_toward(self_pos, nearest["position"], 2)
                    spell = {
                        "name": "blink",
                        "target": direction
                    }
                    self._last_spell_used = "blink"
                    
        # 6. MELEE ATTACK if adjacent to enemy
        if not spell:
            enemies = [e for e in minions if e["owner"] != self_data["name"]]
            enemies.append(opp_data)  # Add opponent to potential targets
            
            adjacent_enemies = [e for e in enemies if manhattan_dist(self_pos, e["position"]) == 1]
            if adjacent_enemies and cooldowns["melee_attack"] == 0:
                # Pick the enemy with lowest HP or prioritize opponent
                opponent_target = next((e for e in adjacent_enemies if e.get("name", "") == opp_data["name"]), None)
                if opponent_target and opponent_target["hp"] <= 20:  # Finishing blow on opponent
                    target = opponent_target
                else:
                    target = min(adjacent_enemies, key=lambda e: e["hp"])
                    
                spell = {
                    "name": "melee_attack",
                    "target": target["position"]
                }
                self._last_spell_used = "melee_attack"
        
        # 7. HEALING STRATEGY - Adaptive healing based on game state
        if not spell and cooldowns["heal"] == 0 and mana >= 25:
            healing_threshold = 75
            
            # Adjust threshold based on enemy behavior
            if enemy_behavior == "aggressive":
                healing_threshold = 85  # Heal more often against aggressive opponents
            elif enemy_behavior == "defensive":
                healing_threshold = 60  # Can wait longer if enemy is defensive
                
            # Also consider if we're taking consistent damage
            if len(self._self_hp_history) >= 3:
                recent_hp_changes = [self._self_hp_history[i] - self._self_hp_history[i-1] for i in range(1, len(self._self_hp_history))]
                if sum(change for change in recent_hp_changes if change < 0) < -30:  # Taking significant damage
                    healing_threshold = 85  # Heal more aggressively
            
            if hp <= healing_threshold:
                spell = {"name": "heal"}
                self._last_spell_used = "heal"
        
        # 8. SUMMON MINION STRATEGY - Situational summoning
        has_minion = any(m["owner"] == self_data["name"] for m in minions)
        if not spell and not has_minion and cooldowns["summon"] == 0 and mana >= 60:
            # Consider if we're in a good position to summon
            enemy_distance = dist(self_pos, opp_pos)
            enemy_minions = [m for m in minions if m["owner"] != self_data["name"]]
            
            # Summon is more valuable in certain scenarios
            should_summon = (
                (enemy_behavior == "aggressive" and hp > 50) or  # Good when we're healthy against aggression
                (enemy_distance > 3 and not enemy_minions) or  # Good when we have space and enemy has no minions
                (mana >= 80)  # Good when we have excess mana
            )
            
            if should_summon:
                spell = {"name": "summon"}
                self._last_spell_used = "summon"
                self._has_summoned = True
            
        # 9. TELEPORT STRATEGY - For resource collection and tactical positioning
        if not spell and cooldowns["teleport"] == 0 and mana >= 40 and artifacts:
            # Teleport when critical or strategic advantage
            critical = mana <= 40 or hp <= 60
            strategic = (
                dist(self_pos, opp_pos) > 7 or  # Get back to the fight
                (enemy_behavior == "resource_focused" and len(artifacts) > 1)  # Contest resources
            )
            
            if critical or strategic:
                best_artifact = self._choose_best_artifact(artifacts, self_pos, opp_pos, hp, mana, enemy_behavior)
                spell = {
                    "name": "teleport",
                    "target": best_artifact["position"]
                }
                self._last_spell_used = "teleport"
        
        # 10. MOVEMENT STRATEGY - Advanced movement based on state
        if not spell:
            # Adjust movement based on enemy behavior
            if enemy_behavior == "aggressive" and hp < 50:
                # Prioritize evasion and artifacts
                if artifacts:
                    best_artifact = self._choose_best_artifact(artifacts, self_pos, opp_pos, hp, mana, enemy_behavior)
                    move = self.move_toward(self_pos, best_artifact["position"])
                else:
                    # Maintain distance from aggressive opponent
                    move = self._direction_away_from(self_pos, opp_pos, 1)
            elif artifacts and (mana <= 70 or hp <= 70):
                best_artifact = self._choose_best_artifact(artifacts, self_pos, opp_pos, hp, mana, enemy_behavior)
                move = self.move_toward(self_pos, best_artifact["position"])
            # Maintain optimal combat distance if we have good mana/hp
            elif hp > 60 and mana > 40:
                # Adjust optimal distance based on spells available
                fireball_ready = cooldowns["fireball"] <= 1
                optimal_distance = 5 if fireball_ready else 3
                current_distance = dist(self_pos, opp_pos)
                
                if current_distance < optimal_distance - 1:
                    # Back away
                    move = self._direction_away_from(self_pos, opp_pos, 1)
                elif current_distance > optimal_distance + 1:
                    # Move closer
                    move = self.move_toward(self_pos, opp_pos)
                else:
                    # Strafe to avoid predictability
                    move = self._strafe_around(self_pos, opp_pos)
                    
                # If enemy is trying to predict our movement, mix up our patterns
                if len(self._enemy_positions) > 5 and self._is_enemy_tracking_us():
                    move = self._unpredictable_move(self_pos, opp_pos)
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
        """Enhanced prediction of enemy's next position based on past movements"""
        if len(self._enemy_positions) < 4:
            return None
            
        # Look for patterns in last few moves
        last_positions = list(self._enemy_positions)[-4:]
        
        # First try to detect linear movement
        dx1 = last_positions[1][0] - last_positions[0][0]
        dy1 = last_positions[1][1] - last_positions[0][1]
        dx2 = last_positions[2][0] - last_positions[1][0]
        dy2 = last_positions[2][1] - last_positions[1][1]
        dx3 = last_positions[3][0] - last_positions[2][0]
        dy3 = last_positions[3][1] - last_positions[2][1]
        
        # If consistent linear movement (same direction repeatedly)
        if (dx2 == dx1 and dy2 == dy1) or (dx3 == dx2 and dy3 == dy2):
            predicted_x = current_pos[0] + dx3  # Use most recent movement
            predicted_y = current_pos[1] + dy3
            # Ensure within bounds
            predicted_x = max(0, min(9, predicted_x))
            predicted_y = max(0, min(9, predicted_y))
            return [predicted_x, predicted_y]
            
        # Try to detect if they're moving toward an artifact
        from game.rules import BOARD_SIZE
        board_center = BOARD_SIZE // 2
        
        # Check if they're moving toward the center
        if all(self._moving_toward_point(last_positions[i], last_positions[i+1], [board_center, board_center]) 
               for i in range(len(last_positions)-1)):
            # Predict they'll continue toward center
            return self._next_pos_toward_target(current_pos, [board_center, board_center])
            
        # Check if they're moving toward artifacts
        if self._last_artifact_positions:
            for artifact_pos in self._last_artifact_positions:
                if all(self._moving_toward_point(last_positions[i], last_positions[i+1], artifact_pos) 
                       for i in range(len(last_positions)-1)):
                    # Predict they'll continue toward artifact
                    return self._next_pos_toward_target(current_pos, artifact_pos)
        
        return None
        
    def _moving_toward_point(self, pos1, pos2, target):
        """Check if movement from pos1 to pos2 is generally toward target"""
        dist1 = math.sqrt((pos1[0] - target[0])**2 + (pos1[1] - target[1])**2)
        dist2 = math.sqrt((pos2[0] - target[0])**2 + (pos2[1] - target[1])**2)
        return dist2 < dist1
        
    def _next_pos_toward_target(self, current, target):
        """Calculate next position when moving toward a target"""
        move = self.move_toward(current, target)
        return [current[0] + move[0], current[1] + move[1]]
        
    def _choose_best_artifact(self, artifacts, self_pos, opp_pos, hp, mana, enemy_behavior=None):
        """Enhanced artifact selection based on need and tactical advantage"""
        # Score each artifact
        scored_artifacts = []
        for artifact in artifacts:
            score = 0
            
            # Distance factor (closer is better)
            distance = max(1, self.manhattan_dist(self_pos, artifact["position"]))
            score -= distance * 2
            
            # Need-based scoring (adjusted based on enemy behavior)
            if artifact["type"] == "health":
                health_need = max(0, 100 - hp)
                score += health_need // 5  # Up to 20 points for health
                if enemy_behavior == "aggressive":
                    score += 10  # Extra value for health against aggressive opponents
            elif artifact["type"] == "mana":
                mana_need = max(0, 100 - mana)
                score += mana_need // 5  # Up to 20 points for mana
                if enemy_behavior == "resource_focused":
                    score += 10  # More valuable if opponent is resource-focused too
            elif artifact["type"] == "cooldown":
                score += 10  # Generally useful
                
            # Tactical positioning (don't get too close to opponent)
            enemy_distance = self.manhattan_dist(artifact["position"], opp_pos)
            if enemy_distance <= 2:
                risk_factor = -15
                if enemy_behavior == "aggressive":
                    risk_factor = -25  # Even more risky against aggressive opponents
                score += risk_factor
                
            # Contest artifacts that opponent might want
            opp_to_artifact = self.manhattan_dist(opp_pos, artifact["position"])
            if opp_to_artifact < distance:  # Opponent is closer to artifact
                if opp_to_artifact <= 3:  # They're getting close to it
                    score += 5  # Increase priority to contest it
                    
            scored_artifacts.append((score, artifact))
            
        # Return the highest scored artifact, or closest if all scores are negative
        if scored_artifacts:
            return max(scored_artifacts, key=lambda x: x[0])[1]
        else:
            # Fallback - closest artifact
            return min(artifacts, key=lambda a: self.manhattan_dist(self_pos, a["position"]))
            
    def _update_enemy_behavior(self, opp_data, self_data, artifacts, minions):
        """Track and categorize opponent behavior patterns"""
        if len(self._enemy_positions) < 2:
            return
            
        # Check if they're moving toward artifacts
        if artifacts:
            last_pos = self._enemy_positions[-2]
            current_pos = self._enemy_positions[-1]
            
            # Check if they moved closer to any artifact
            for artifact in artifacts:
                dist_before = self.manhattan_dist(last_pos, artifact["position"])
                dist_now = self.manhattan_dist(current_pos, artifact["position"])
                if dist_now < dist_before:
                    self._enemy_patterns["resource_focused"] += 1
                    break
                    
        # Check if they're moving toward or away from us
        if len(self._enemy_positions) >= 2:
            last_pos = self._enemy_positions[-2]
            current_pos = self._enemy_positions[-1]
            our_pos = self_data["position"]
            
            dist_before = self.manhattan_dist(last_pos, our_pos)
            dist_now = self.manhattan_dist(current_pos, our_pos)
            
            if dist_now < dist_before:
                self._enemy_patterns["aggressive"] += 1
            elif dist_now > dist_before:
                self._enemy_patterns["defensive"] += 1
                
    def _get_dominant_enemy_behavior(self):
        """Determine the most common enemy behavior pattern"""
        if sum(self._enemy_patterns.values()) == 0:
            return "unknown"
            
        dominant = max(self._enemy_patterns.items(), key=lambda x: x[1])
        return dominant[0]
        
    def _is_enemy_tracking_us(self):
        """Detect if enemy seems to be tracking and predicting our movements"""
        if len(self._enemy_positions) < 5:
            return False
            
        # Check if enemy consistently moves to intercept us
        intercept_count = 0
        for i in range(len(self._enemy_positions) - 3):
            our_direction = [
                self._enemy_positions[i+1][0] - self._enemy_positions[i][0],
                self._enemy_positions[i+1][1] - self._enemy_positions[i][1]
            ]
            their_direction = [
                self._enemy_positions[i+2][0] - self._enemy_positions[i+1][0],
                self._enemy_positions[i+2][1] - self._enemy_positions[i+1][1]
            ]
            
            # Check if their movement is perpendicular to ours (interception)
            dot_product = our_direction[0] * their_direction[0] + our_direction[1] * their_direction[1]
            if abs(dot_product) < 0.3:  # Near perpendicular
                intercept_count += 1
                
        return intercept_count >= 2
        
    def _unpredictable_move(self, self_pos, opp_pos):
        """Generate an unpredictable movement to confuse tracking"""
        # Options: move toward, away, strafe, or random
        options = [
            self.move_toward(self_pos, opp_pos),
            self._direction_away_from(self_pos, opp_pos),
            self._strafe_around(self_pos, opp_pos),
            [random.choice([-1, 0, 1]), random.choice([-1, 0, 1])]
        ]
        
        # Make sure we don't stand still unless deliberately chosen
        choice = random.choice(options)
        if choice == [0, 0] and random.random() < 0.8:  # 80% chance to avoid standing still
            choice = random.choice([[-1, 0], [1, 0], [0, -1], [0, 1]])
            
        return choice
        
    def _count_targets_near_position(self, position, minions, radius):
        """Count how many targets are within radius of position"""
        count = 0
        for minion in minions:
            if self.manhattan_dist(position, minion["position"]) <= radius:
                count += 1
        return count
        
    def manhattan_dist(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1]) 