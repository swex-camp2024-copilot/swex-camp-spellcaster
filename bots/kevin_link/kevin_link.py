import random

from bots.bot_interface import BotInterface


class KevinLink(BotInterface):
    def __init__(self):
        self._name = "Kevin Link"
        self._sprite_path = "assets/wizards/kevin_link.png"
        self._minion_sprite_path = "assets/minions/minion_2.png"
        self._first_round = True
        self._enemy_positions = []  # Track enemy movement patterns
        self._last_hp = 100  # Track our last health
        self._turn_count = 0  # Track turn count
        self._under_attack = False  # Flag to indicate if we're under attack
        self._attack_source = None  # Track where attacks are coming from
        self._opponent_shield_active_until = 0  # Track opponent shield duration
        self._last_known_spells = {}  # Track opponent's last known spell cooldowns
        self._minion_health = {}  # Track minion health
        self._damage_taken = 0  # Track damage taken in last 3 turns
        self._last_positions = []  # Track our own positions
        self._opponent_behavior = None  # Will categorize opponent (aggressive, defensive, etc)
        self._early_game = True  # Track game phase
        self._adaptation_turns = 0  # Count turns for adaptation
        self._minion_strategy = "defend"  # Default minion strategy

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
        # Update turn counter and track game phase
        self._turn_count += 1
        if self._turn_count > 10:
            self._early_game = False
            
        # Get state data
        self_data = state["self"]
        opp_data = state["opponent"]
        artifacts = state.get("artifacts", [])
        minions = state.get("minions", [])

        self_pos = self_data["position"]
        opp_pos = opp_data["position"]
        cooldowns = self_data["cooldowns"]
        mana = self_data["mana"]
        hp = self_data["hp"]
        
        # Track our own positions for better pattern detection
        self._last_positions.append(self_pos)
        if len(self._last_positions) > 5:
            self._last_positions = self._last_positions[-5:]
        
        # Track opponent shield status
        if opp_data.get("shield_active", False) and self._opponent_shield_active_until == 0:
            self._opponent_shield_active_until = self._turn_count + 3
        elif not opp_data.get("shield_active", False):
            self._opponent_shield_active_until = 0
            
        # Detect if we're under attack and from where
        if self._last_hp > hp:
            self._under_attack = True
            self._damage_taken += (self._last_hp - hp)
            
            # Try to detect attack source
            distance_to_opponent = self.dist(self_pos, opp_pos)
            if distance_to_opponent <= 5:  # Fireball range
                self._attack_source = opp_pos
            elif distance_to_opponent <= 1:  # Melee range
                self._attack_source = opp_pos
            else:
                # Check for opponent minions
                for minion in minions:
                    if minion["owner"] != self_data["name"]:
                        if self.dist(self_pos, minion["position"]) <= 1:
                            self._attack_source = minion["position"]
        else:
            # Reset attack detection after 3 turns of no damage
            if self._turn_count % 3 == 0:
                self._under_attack = False
                self._damage_taken = 0
            
        self._last_hp = hp
        
        # Update minion health tracking
        own_minions = [m for m in minions if m["owner"] == self_data["name"]]
        for minion in own_minions:
            minion_id = minion["id"]
            self._minion_health[minion_id] = minion["hp"]
        
        # Update tracking data
        self._enemy_positions.append(opp_pos)
        if len(self._enemy_positions) > 10:  # Track more positions for better analysis
            self._enemy_positions = self._enemy_positions[-10:]
            
        # Classify opponent behavior
        self._classify_opponent(opp_data, minions)
            
        # Update adaptation strategy every 5 turns
        if self._turn_count % 5 == 0:
            self._adapt_strategy(opp_data, hp, mana)

        # Initialize decision variables
        move = [0, 0]
        spell = None
            
        # DECISION MAKING PROCESS
        
        # 1. EMERGENCY RESPONSE - Highest priority
        spell = self._emergency_response(self_data, opp_data, cooldowns, mana, hp, self_pos, opp_pos)
        if spell:
            return {"move": [0, 0], "spell": spell}
        
        # 2. OFFENSIVE OPPORTUNITY - High priority if health advantage
        if not spell and hp > opp_data["hp"] + 20:
            spell = self._offensive_opportunity(self_data, opp_data, cooldowns, mana, self_pos, opp_pos)
            
        # 3. RESOURCE ACQUISITION - Critical if low on resources
        if not spell and (hp <= 60 or mana <= 50):
            spell, action = self._resource_strategy(self_data, artifacts, cooldowns, mana, hp, self_pos, opp_pos)
            if action == "move_only":
                move = self._calculate_move_toward_artifact(self_pos, artifacts, opp_pos)
                return {"move": move, "spell": None}
                
        # 4. MINION MANAGEMENT - Strategic advantage
        own_minions = [m for m in minions if m["owner"] == self_data["name"]]
        if not spell and len(own_minions) == 0 and cooldowns["summon"] == 0 and mana >= 60:
            spell = {"name": "summon"}
        
        # 5. POSITIONAL ADVANTAGE - Better combat tactics
        if not spell:
            spell = self._positional_advantage(self_data, opp_data, cooldowns, mana, hp, self_pos, opp_pos)
            
        # 6. MOVEMENT STRATEGY - Better navigation
        if not spell:
            move = self._calculate_move(self_data, opp_data, artifacts, minions, self_pos, opp_pos, hp, mana)
        
        return {
            "move": move,
            "spell": spell
        }
        
    def _emergency_response(self, self_data, opp_data, cooldowns, mana, hp, self_pos, opp_pos):
        """Highest priority - respond to immediate threats"""
        # Critical health shield
        if hp <= 30 and not self_data.get("shield_active", False) and cooldowns["shield"] == 0 and mana >= 20:
            return {"name": "shield"}
            
        # Emergency heal when extremely low
        if hp <= 20 and cooldowns["heal"] == 0 and mana >= 25:
            return {"name": "heal"}
            
        # Counter immediate attack
        if self._under_attack and self._damage_taken >= 15:
            # Shield if not active and available
            if not self_data.get("shield_active", False) and cooldowns["shield"] == 0 and mana >= 20:
                return {"name": "shield"}
                
            # Emergency blink away if very close to opponent
            if self.dist(self_pos, opp_pos) <= 2 and cooldowns["blink"] == 0 and mana >= 10:
                direction = self._safe_retreat_direction(self_pos, opp_pos)
                if direction:
                    return {
                        "name": "blink",
                        "target": direction
                    }
                    
            # Emergency teleport to health if critical
            if hp <= 25 and cooldowns["teleport"] == 0 and mana >= 40:
                health_artifacts = [a for a in self_data.get("artifacts", []) if a["type"] == "health"]
                if health_artifacts:
                    return {
                        "name": "teleport",
                        "target": health_artifacts[0]["position"]
                    }
                    
        return None
        
    def _offensive_opportunity(self, self_data, opp_data, cooldowns, mana, self_pos, opp_pos):
        """Take advantage of offensive opportunities"""
        opponent_shielded = opp_data.get("shield_active", False)
        distance = self.dist(self_pos, opp_pos)
        
        # Fireball when in range and opponent not shielded
        if not opponent_shielded and cooldowns["fireball"] == 0 and mana >= 30 and distance <= 5:
            # Target slightly ahead of opponent's position for better hit rate
            predicted_pos = self._predict_position(opp_pos)
            target = predicted_pos if predicted_pos else opp_pos
            return {
                "name": "fireball",
                "target": target
            }
            
        # Melee attack if adjacent
        if self.manhattan_dist(self_pos, opp_pos) == 1 and cooldowns["melee_attack"] == 0:
            return {
                "name": "melee_attack",
                "target": opp_pos
            }
            
        # Aggressive blink to close distance when healthy
        if distance > 2 and distance <= 5 and not opponent_shielded and cooldowns["blink"] == 0 and mana >= 10:
            direction = self._calculate_interception(self_pos, opp_pos)
            if direction:
                return {
                    "name": "blink",
                    "target": direction
                }
                
        return None
        
    def _resource_strategy(self, self_data, artifacts, cooldowns, mana, hp, self_pos, opp_pos):
        """Optimize resource acquisition"""
        if not artifacts:
            return None, None
            
        # Find best artifact based on need
        best_artifact = self._choose_best_artifact(artifacts, self_pos, opp_pos, hp, mana)
        if not best_artifact:
            return None, None
            
        distance = self.dist(self_pos, best_artifact["position"])
        
        # Critical resource needs
        critical_health = hp <= 30 and best_artifact["type"] == "health"
        critical_mana = mana <= 30 and best_artifact["type"] == "mana"
        
        # Teleport for critical resources or when far away
        if (critical_health or critical_mana or distance >= 5) and cooldowns["teleport"] == 0 and mana >= 40:
            return {
                "name": "teleport",
                "target": best_artifact["position"]
            }, None
            
        # Blink toward resource
        if distance > 1 and cooldowns["blink"] == 0 and mana >= 10:
            direction = self._direction_toward(self_pos, best_artifact["position"], 2)
            if direction:
                return {
                    "name": "blink",
                    "target": direction
                }, None
                
        # Just move toward artifact if no spells available
        return None, "move_only"
        
    def _positional_advantage(self, self_data, opp_data, cooldowns, mana, hp, self_pos, opp_pos):
        """Improve positioning for tactical advantage"""
        distance = self.dist(self_pos, opp_pos)
        opponent_shielded = opp_data.get("shield_active", False)
        
        # Shield when opponent is close and we're not already shielded
        if not self_data.get("shield_active", False) and distance <= 4 and cooldowns["shield"] == 0 and mana >= 20:
            if hp <= 70 or (self._opponent_behavior == "aggressive" and distance <= 3):
                return {"name": "shield"}
                
        # Heal when moderately damaged and not under immediate threat
        if hp <= 65 and distance >= 4 and cooldowns["heal"] == 0 and mana >= 25:
            return {"name": "heal"}
            
        # Blink to optimal combat distance
        optimal_distance = 4  # Good for fireball but not in melee range
        if ((distance < 2 and hp < 60) or (abs(distance - optimal_distance) > 2)) and cooldowns["blink"] == 0 and mana >= 10:
            # Blink to safety if low health, or to optimal combat distance otherwise
            if hp < 60 and distance < 2:
                direction = self._safe_retreat_direction(self_pos, opp_pos)
            else:
                direction = self._direction_to_optimal_distance(self_pos, opp_pos, optimal_distance)
                
            if direction:
                return {
                    "name": "blink",
                    "target": direction
                }
                
        return None
        
    def _calculate_move(self, self_data, opp_data, artifacts, minions, self_pos, opp_pos, hp, mana):
        """Calculate optimal movement based on situation"""
        # Prioritize artifact collection if needed
        if artifacts and (hp <= 70 or mana <= 60):
            return self._calculate_move_toward_artifact(self_pos, artifacts, opp_pos)
            
        # Defensive retreat if low health
        if hp <= 40 and self.dist(self_pos, opp_pos) <= 3:
            return self._safe_retreat_direction(self_pos, opp_pos)
            
        # Manage combat distance based on situation
        optimal_distance = self._calculate_optimal_distance(self_data, opp_data, hp, mana)
        current_distance = self.dist(self_pos, opp_pos)
        
        if abs(current_distance - optimal_distance) > 1:
            # We're not at optimal distance
            if current_distance < optimal_distance:
                # Too close, move away
                return self._direction_away_from(self_pos, opp_pos, 1)
            else:
                # Too far, move closer
                return self.move_toward(self_pos, opp_pos)
        else:
            # At optimal distance, strafe to avoid predictability
            return self._intelligent_strafe(self_pos, opp_pos, minions, artifacts)
            
    def _calculate_move_toward_artifact(self, self_pos, artifacts, opp_pos):
        """Calculate movement toward best artifact"""
        best_artifact = self._choose_best_artifact(artifacts, self_pos, opp_pos, 0, 0)
        if best_artifact:
            return self.move_toward(self_pos, best_artifact["position"])
        return [0, 0]
        
    def _choose_best_artifact(self, artifacts, self_pos, opp_pos, hp, mana):
        """Choose best artifact considering needs and positioning"""
        if not artifacts:
            return None
            
        scored_artifacts = []
        for artifact in artifacts:
            score = 0
            artifact_pos = artifact["position"]
            
            # Distance factor (closer is better)
            distance = max(1, self.dist(self_pos, artifact_pos))
            score -= distance * 2
            
            # Need-based scoring
            if hp <= 50 and artifact["type"] == "health":
                score += 40 - (hp / 2)  # Higher bonus when health is lower
            elif mana <= 40 and artifact["type"] == "mana":
                score += 40 - mana  # Higher bonus when mana is lower
            elif artifact["type"] == "cooldown":
                score += 15  # General value for cooldown reduction
                
            # Strategic positioning
            enemy_distance = self.dist(artifact_pos, opp_pos)
            my_distance = self.dist(self_pos, artifact_pos)
            
            # Risk evaluation - avoid artifacts near enemy
            if enemy_distance <= 2 and my_distance > enemy_distance:
                score -= 30  # Heavily penalize artifacts where enemy will reach first
            elif enemy_distance <= 1:
                score -= 50  # Extremely dangerous to contest
                
            # Opportunity - can we get there first?
            if my_distance < enemy_distance:
                score += 15
                
            scored_artifacts.append((score, artifact))
            
        if scored_artifacts:
            return max(scored_artifacts, key=lambda x: x[0])[1]
        return None
        
    def _classify_opponent(self, opp_data, minions):
        """Classify opponent behavior to adapt strategy"""
        if self._turn_count < 5:
            # Not enough data yet
            return
            
        # Check for aggressive behavior
        if self._damage_taken >= 30 and self._turn_count <= 10:
            self._opponent_behavior = "aggressive"
            return
            
        # Check for defensive behavior (lots of shielding)
        if opp_data.get("shield_active", False) and self._turn_count % 5 == 0:
            # If opponent shields frequently
            self._opponent_behavior = "defensive"
            return
            
        # Check for minion focus
        opp_minions = [m for m in minions if m["owner"] != self._name]
        if len(opp_minions) >= 1 and self._turn_count <= 10:
            self._opponent_behavior = "minion_focused"
            return
            
        # Default to balanced
        self._opponent_behavior = "balanced"
        
    def _adapt_strategy(self, opp_data, hp, mana):
        """Adapt strategy based on opponent behavior and game state"""
        self._adaptation_turns += 1
        
        if self._opponent_behavior == "aggressive":
            # Against aggressive opponents, play defensive
            self._minion_strategy = "defend"
        elif self._opponent_behavior == "defensive":
            # Against defensive opponents, be more aggressive
            self._minion_strategy = "attack"
        elif self._opponent_behavior == "minion_focused":
            # Counter minion strategy
            self._minion_strategy = "counter"
        else:
            # Balanced approach otherwise
            if hp > 70 and mana > 60:
                self._minion_strategy = "attack"
            else:
                self._minion_strategy = "defend"
                
    def _calculate_optimal_distance(self, self_data, opp_data, hp, mana):
        """Calculate optimal distance based on situation"""
        fireball_ready = self_data["cooldowns"]["fireball"] == 0 and mana >= 30
        opp_shielded = opp_data.get("shield_active", False)
        self_shielded = self_data.get("shield_active", False)
        
        if hp <= 30:
            # Very low health, stay far
            return 6
        elif hp <= 50 and not self_shielded:
            # Low health without shield, maintain distance
            return 5
        elif fireball_ready and not opp_shielded:
            # Can use fireball and opponent not shielded
            return 4
        elif self_shielded and hp > 70:
            # We're shielded and healthy, can be aggressive
            return 2
        else:
            # Default moderate distance
            return 4
            
    def _predict_position(self, current_pos, positions=None):
        """Predict future position based on movement patterns"""
        if not positions:
            positions = self._enemy_positions
            
        if len(positions) < 3:
            return None
            
        # Calculate last two movement vectors
        moves = []
        for i in range(len(positions)-1):
            move_x = positions[i+1][0] - positions[i][0]
            move_y = positions[i+1][1] - positions[i][1]
            moves.append((move_x, move_y))
            
        # Look for consistent pattern
        if len(moves) >= 2 and moves[-1] == moves[-2]:
            # Consistent movement detected
            move_x, move_y = moves[-1]
            predicted_x = current_pos[0] + move_x
            predicted_y = current_pos[1] + move_y
            
            # Ensure within bounds
            predicted_x = max(0, min(9, predicted_x))
            predicted_y = max(0, min(9, predicted_y))
            
            return [predicted_x, predicted_y]
            
        return None
        
    def _calculate_interception(self, self_pos, target_pos):
        """Calculate direction to intercept moving target"""
        predicted_pos = self._predict_position(target_pos)
        if predicted_pos:
            return self._direction_toward(self_pos, predicted_pos, 2)
        return self._direction_toward(self_pos, target_pos, 1)
        
    def _safe_retreat_direction(self, self_pos, threat_pos):
        """Calculate safest direction to retreat"""
        # Get basic direction away from threat
        dx = self_pos[0] - threat_pos[0]
        dy = self_pos[1] - threat_pos[1]
        
        # Avoid retreating into corners or edges
        safe_x = max(1, min(8, self_pos[0] + (1 if dx > 0 else -1 if dx < 0 else 0)))
        safe_y = max(1, min(8, self_pos[1] + (1 if dy > 0 else -1 if dy < 0 else 0)))
        
        return [safe_x - self_pos[0], safe_y - self_pos[1]]
        
    def _direction_to_optimal_distance(self, self_pos, target_pos, optimal_distance):
        """Calculate direction to maintain optimal distance"""
        current_distance = self.dist(self_pos, target_pos)
        
        if abs(current_distance - optimal_distance) <= 1:
            # Already at optimal distance, return lateral movement
            return self._intelligent_strafe(self_pos, target_pos, [], [])
            
        if current_distance < optimal_distance:
            # Too close, move away
            return self._direction_away_from(self_pos, target_pos, 1)
        else:
            # Too far, move closer
            return self._direction_toward(self_pos, target_pos, 1)
            
    def _intelligent_strafe(self, self_pos, target_pos, minions, artifacts):
        """Strafe intelligently, avoiding obstacles and seeking advantages"""
        dx = target_pos[0] - self_pos[0]
        dy = target_pos[1] - self_pos[1]
        
        # Calculate perpendicular directions (two options)
        if abs(dx) > abs(dy):
            # More horizontal distance, move vertically
            options = [[0, 1], [0, -1]]
        else:
            # More vertical distance, move horizontally
            options = [[1, 0], [-1, 0]]
            
        # Score each option
        best_score = -1000
        best_option = options[0]
        
        for option in options:
            new_x = self_pos[0] + option[0]
            new_y = self_pos[1] + option[1]
            new_pos = [new_x, new_y]
            
            # Stay in bounds
            if not (0 <= new_x <= 9 and 0 <= new_y <= 9):
                continue
                
            score = 0
            
            # Prefer moves that maintain distance
            current_dist = self.dist(self_pos, target_pos)
            new_dist = self.dist(new_pos, target_pos)
            if abs(new_dist - current_dist) <= 1:
                score += 10
                
            # Avoid minions
            for minion in minions:
                if self.dist(new_pos, minion["position"]) <= 1:
                    score -= 20
                    
            # Bonus for moving toward artifacts
            for artifact in artifacts:
                current_artifact_dist = self.dist(self_pos, artifact["position"])
                new_artifact_dist = self.dist(new_pos, artifact["position"])
                if new_artifact_dist < current_artifact_dist:
                    score += 5
                    
            # Avoid board edges
            if new_x <= 1 or new_x >= 8 or new_y <= 1 or new_y >= 8:
                score -= 5
                
            if score > best_score:
                best_score = score
                best_option = option
                
        return best_option

    def move_toward(self, start, target):
        """Move one step toward target"""
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        
        # Prioritize larger dimension first
        if abs(dx) > abs(dy):
            step_x = 1 if dx > 0 else -1 if dx < 0 else 0
            step_y = 0
        else:
            step_x = 0
            step_y = 1 if dy > 0 else -1 if dy < 0 else 0
            
        # Stay in bounds
        new_x = start[0] + step_x
        new_y = start[1] + step_y
        
        if not (0 <= new_x <= 9 and 0 <= new_y <= 9):
            # Try other axis if this would go out of bounds
            if step_x != 0:
                step_x = 0
                step_y = 1 if dy > 0 else -1 if dy < 0 else 0
            else:
                step_y = 0
                step_x = 1 if dx > 0 else -1 if dx < 0 else 0
                
        return [step_x, step_y]
        
    def _direction_away_from(self, start, target, distance=1):
        """Calculate direction away from target"""
        dx = start[0] - target[0]
        dy = start[1] - target[1]
        
        # Normalize and scale
        magnitude = max(1, abs(dx) + abs(dy))
        dx = int(round(dx * distance / magnitude))
        dy = int(round(dy * distance / magnitude))
        
        # Ensure movement in at least one direction
        if dx == 0 and dy == 0 and distance > 0:
            dx = 1
            
        # Check board boundaries
        new_x = start[0] + dx
        new_y = start[1] + dy
        
        if not (0 <= new_x <= 9 and 0 <= new_y <= 9):
            # Adjust to stay in bounds
            if new_x < 0:
                dx = 0
            elif new_x > 9:
                dx = 0
                
            if new_y < 0:
                dy = 0
            elif new_y > 9:
                dy = 0
                
            # Ensure we're still moving
            if dx == 0 and dy == 0:
                if 0 <= start[0] + 1 <= 9:
                    dx = 1
                elif 0 <= start[0] - 1 <= 9:
                    dx = -1
                    
        return [dx, dy]
        
    def _direction_toward(self, start, target, distance=1):
        """Calculate direction toward target"""
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        
        # Normalize and scale
        magnitude = max(1, abs(dx) + abs(dy))
        dx = int(round(dx * distance / magnitude))
        dy = int(round(dy * distance / magnitude))
        
        # Ensure movement in at least one direction
        if dx == 0 and dy == 0 and distance > 0:
            dx = 1
            
        # Check board boundaries
        new_x = start[0] + dx
        new_y = start[1] + dy
        
        if not (0 <= new_x <= 9 and 0 <= new_y <= 9):
            # Adjust to stay in bounds
            if new_x < 0:
                dx = 0
            elif new_x > 9:
                dx = 0
                
            if new_y < 0:
                dy = 0
            elif new_y > 9:
                dy = 0
                
            # Ensure we're still moving
            if dx == 0 and dy == 0:
                if 0 <= start[0] + 1 <= 9:
                    dx = 1
                elif 0 <= start[0] - 1 <= 9:
                    dx = -1
                    
        return [dx, dy]
        
    def dist(self, a, b):
        """Calculate Chebyshev distance between points"""
        return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
        
    def manhattan_dist(self, a, b):
        """Calculate Manhattan distance between points"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1]) 