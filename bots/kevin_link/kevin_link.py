import random

from bots.bot_interface import BotInterface


class KevinLink(BotInterface):
    def __init__(self):
        self._name = "Kevin Link"
        self._sprite_path = "assets/wizards/kevin_link.png"
        self._minion_sprite_path = "assets/minions/moblin.png"
        self._first_round = True
        self._enemy_positions = []  # Track enemy movement patterns
        self._last_hp = 100  # Track our last health
        self._turn_count = 0  # Track turn count
        self._under_attack = False  # Flag to indicate if we're under attack
        self._attack_source = None  # Track where attacks are coming from
        self._opponent_shield_active_until = 0  # Track opponent shield duration
        self._last_known_spells = {}  # Track opponent's last known spell cooldowns. Format: {"spell_name": last_turn_cast}
        self._minion_health = {}  # Track minion health
        self._damage_taken = 0  # Track damage taken in last 3 turns
        self._last_positions = []  # Track our own positions
        self._early_game = True  # Track game phase
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

        # Update opponent spell tracking based on last turn's events
        # This needs access to the full event log of the PREVIOUS turn, which state usually provides.
        # Assuming state["events"] contains events from the last turn.
        # If not, this part needs to be adjusted based on how game events are passed.
        # For now, we'll assume opp_data might have a "last_spell_cast" field or similar from the game engine.
        # Since the provided state structure doesn't explicitly show opponent's last cast spell,
        # we'll have to manually infer or this feature might be limited.
        # Let's assume for now we can't reliably track opponent cooldowns without more info in 'state'.
        # So, we'll skip populating _last_known_spells for now and focus on other cues for proactive shielding.

        self_pos = self_data["position"]
        opp_pos = opp_data["position"]
        cooldowns = self_data["cooldowns"]
        mana = self_data["mana"]
        hp = self_data["hp"]
        
        # First-Turn Shield: secure early defense
        if self._first_round:
            self._first_round = False
            if cooldowns["shield"] == 0 and mana >= 20:
                return {"move": [0, 0], "spell": {"name": "shield"}}
        
        # Early Artifact Racing: teleport or blink to critical artifacts by turn 3 when health or mana is critical
        if self._turn_count <= 3 and artifacts and (hp <= 60 or mana <= 40):
            best_artifact = self._choose_best_artifact(artifacts, self_pos, opp_pos, hp, mana)
            if best_artifact:
                art_pos = best_artifact["position"]
                art_dist = self.dist(self_pos, art_pos)
                if cooldowns["teleport"] == 0 and mana >= 40 and art_dist > 2:
                    return {"move": [0, 0], "spell": {"name": "teleport", "target": art_pos}}
                if cooldowns["blink"] == 0 and mana >= 10 and art_dist > 1:
                    blink_dir = self._direction_toward(self_pos, art_pos, 2)
                    return {"move": [0, 0], "spell": {"name": "blink", "target": blink_dir}}
        
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

        # Initialize decision variables
        move = [0, 0]
        spell = None
            
        # DECISION MAKING PROCESS
        
        # 1. EMERGENCY RESPONSE - Highest priority
        spell = self._emergency_response(self_data, opp_data, cooldowns, mana, hp, self_pos, opp_pos, minions, artifacts)
        if spell:
            return {"move": [0, 0], "spell": spell}
        
        # 2. OFFENSIVE OPPORTUNITY - High priority if health advantage
        if not spell and hp > opp_data["hp"] + 20:
            spell = self._offensive_opportunity(self_data, opp_data, cooldowns, mana, self_pos, opp_pos)
            
        # 3. RESOURCE ACQUISITION - Critical if low on resources
        if not spell and (hp <= 50 or mana <= 40):
            spell, action = self._resource_strategy(self_data, artifacts, cooldowns, mana, hp, self_pos, opp_pos)
            if action == "move_only":
                move = self._calculate_move_toward_artifact(self_pos, artifacts, opp_pos, hp, mana)
                return {"move": move, "spell": None}
                
        # 4. MINION MANAGEMENT - Strategic advantage
        own_minions = [m for m in minions if m["owner"] == self_data["name"]]
        if not spell and self._turn_count <= 2 and cooldowns["summon"] == 0 and mana >= 50 and len(own_minions) == 0:
            dx = self_pos[0] - opp_pos[0]
            dy = self_pos[1] - opp_pos[1]
            dx_dir = 1 if dx > 0 else -1 if dx < 0 else 1
            dy_dir = 1 if dy > 0 else -1 if dy < 0 else 1
            target_x = max(0, min(9, self_pos[0] + 2 * dx_dir))
            target_y = max(0, min(9, self_pos[1] + 2 * dy_dir))
            # Avoid edges and corners by clamping within 1..8
            target_x = min(max(target_x, 1), 8)
            target_y = min(max(target_y, 1), 8)
            best_pos = [target_x, target_y]
            occupied = [self_pos, opp_pos] + [m["position"] for m in minions]
            if best_pos not in occupied:
                return {"move": [0, 0], "spell": {"name": "summon", "target": best_pos}}
        if not spell and len(own_minions) < 1 and cooldowns["summon"] == 0 and mana >= 60:
            # Attempt to summon minion defensively relative to opponent
            #Simplified summoning logic:
            best_summon_pos = None
            max_dist_from_opp = -1

            # Potential relative positions (dx, dy) from self_pos
            # Favor positions behind or to the sides relative to opponent
            # Vector from self to opponent:
            vec_self_to_opp_x = opp_pos[0] - self_pos[0]
            vec_self_to_opp_y = opp_pos[1] - self_pos[1]

            # Try to summon 1 or 2 steps away, generally opposite to opponent
            potential_offsets = []
            if vec_self_to_opp_x > 0: # Opponent is to the East
                potential_offsets.extend([(-1,0), (-2,0), (-1,1), (-1,-1)])
            elif vec_self_to_opp_x < 0: # Opponent is to the West
                potential_offsets.extend([(1,0), (2,0), (1,1), (1,-1)])
            if vec_self_to_opp_y > 0: # Opponent is to the South
                potential_offsets.extend([(0,-1), (0,-2), (1,-1), (-1,-1)])
            elif vec_self_to_opp_y < 0: # Opponent is to the North
                potential_offsets.extend([(0,1), (0,2), (1,1), (-1,1)])
            
            if not potential_offsets: # If on same tile or no clear direction
                potential_offsets = [(1,0), (-1,0), (0,1), (0,-1), (1,1), (1,-1), (-1,1), (-1,-1)]
            
            random.shuffle(potential_offsets)

            occupied_cells = [self_pos, opp_pos] + [m["position"] for m in minions]

            for dx, dy in potential_offsets:
                target_x = self_pos[0] + dx
                target_y = self_pos[1] + dy

                if 0 <= target_x <= 9 and 0 <= target_y <= 9:
                    target_pos_candidate = [target_x, target_y]
                    if target_pos_candidate not in occupied_cells:
                        # Optional: Prefer spots further from opponent among valid spots
                        dist_to_opp = self.dist(target_pos_candidate, opp_pos)
                        if dist_to_opp > max_dist_from_opp: # Basic preference for safer spots
                            best_summon_pos = target_pos_candidate
                            max_dist_from_opp = dist_to_opp
                        elif best_summon_pos is None: # Take first valid if no preference met
                             best_summon_pos = target_pos_candidate
            
            # Fallback if no ideal spot found from offsets (e.g. very crowded)
            if not best_summon_pos:
                for dx_fallback in [-1, 1, 0, -2, 2]: # Broader search
                    for dy_fallback in [-1, 1, 0, -2, 2]:
                        if dx_fallback == 0 and dy_fallback == 0: continue
                        target_x = self_pos[0] + dx_fallback
                        target_y = self_pos[1] + dy_fallback
                        if 0 <= target_x <= 9 and 0 <= target_y <= 9:
                            target_pos_candidate = [target_x, target_y]
                            if target_pos_candidate not in occupied_cells:
                                best_summon_pos = target_pos_candidate
                                break
                    if best_summon_pos: break
            
            if best_summon_pos:
                spell = {"name": "summon", "target": best_summon_pos}
            else: # Very last resort: try to summon on any adjacent non-self, non-opponent cell
                for offset_x, offset_y in [(0,1), (0,-1), (1,0), (-1,0)]:
                    check_x, check_y = self_pos[0] + offset_x, self_pos[1] + offset_y
                    if 0 <= check_x <= 9 and 0 <= check_y <= 9:
                        if [check_x, check_y] != opp_pos and [check_x, check_y] not in [m["position"] for m in minions]:
                            spell = {"name": "summon", "target": [check_x, check_y]}
                            break
        
        # 5. POSITIONAL ADVANTAGE - Better combat tactics
        if not spell:
            spell = self._positional_advantage(self_data, opp_data, cooldowns, mana, hp, self_pos, opp_pos, minions)
            
        # 6. MOVEMENT STRATEGY - Better navigation
        if not spell:
            move = self._calculate_move(self_data, opp_data, artifacts, minions, self_pos, opp_pos, hp, mana)
        
        return {
            "move": move,
            "spell": spell
        }
        
    def _emergency_response(self, self_data, opp_data, cooldowns, mana, hp, self_pos, opp_pos, minions_list, artifacts):
        """Highest priority - respond to immediate threats"""
        # Critical health shield
        if hp <= 60 and not self_data.get("shield_active", False) and cooldowns["shield"] == 0 and mana >= 20:
            return {"name": "shield"}
            
        # Emergency heal when extremely low
        if hp <= 30 and cooldowns["heal"] == 0 and mana >= 25:
            return {"name": "heal"}
            
        # Counter immediate attack
        if self._under_attack and self._damage_taken >= 15:
            # Shield if not active and available
            if not self_data.get("shield_active", False) and cooldowns["shield"] == 0 and mana >= 20:
                return {"name": "shield"}
                
            # Emergency blink away if very close to opponent
            if self.dist(self_pos, opp_pos) <= 3 and cooldowns["blink"] == 0 and mana >= 10:
                direction = self._safe_retreat_direction(self_pos, opp_pos, all_minions=minions_list, opponent_pos=opp_pos)
                if direction and (direction[0] != 0 or direction[1] != 0): # Ensure there is a direction
                    return {
                        "name": "blink",
                        "target": direction
                    }
                    
            # Emergency teleport to health if critical
            if hp <= 35 and cooldowns["teleport"] == 0 and mana >= 40:
                health_artifacts = [a for a in artifacts if a["type"] == "health"]
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
        
    def _positional_advantage(self, self_data, opp_data, cooldowns, mana, hp, self_pos, opp_pos, minions):
        """Improve positioning for tactical advantage"""
        distance = self.dist(self_pos, opp_pos)
        opponent_shielded = opp_data.get("shield_active", False)
        
        # Shield when opponent is close and we're not already shielded
        if not self_data.get("shield_active", False) and distance <= 4 and cooldowns["shield"] == 0 and mana >= 20:
            if hp <= 70:
                return {"name": "shield"}
            # Proactive shield against likely fireball; reduce frequency to conserve mana
            if distance <= 5 and mana >= 40:
                if random.random() < 0.1: # Shield 10% of the time for unpredictability
                    return {"name": "shield"}
                
        # Heal when moderately damaged and not under immediate threat
        if hp <= 75 and distance >= 4 and cooldowns["heal"] == 0 and mana >= 25:
            return {"name": "heal"}
            
        # Blink to optimal combat distance
        optimal_distance = 5  # Good for fireball and safer combat range
        if ((distance < 2 and hp < 60) or (abs(distance - optimal_distance) > 2)) and cooldowns["blink"] == 0 and mana >= 10:
            # Blink to safety if low health, or to optimal combat distance otherwise
            if hp < 60 and distance < 2:
                direction = self._safe_retreat_direction(self_pos, opp_pos, all_minions=minions, opponent_pos=opp_pos)
            else:
                direction = self._direction_to_optimal_distance(self_data, self_pos, opp_pos, optimal_distance)
                
            if direction and (direction[0] != 0 or direction[1] != 0):
                return {
                    "name": "blink",
                    "target": direction
                }
                
        return None
        
    def _calculate_move(self, self_data, opp_data, artifacts, minions, self_pos, opp_pos, hp, mana):
        """Calculate optimal movement based on situation"""
        # Prioritize artifact collection if needed
        if artifacts and (hp <= 70 or mana <= 60):
            return self._calculate_move_toward_artifact(self_pos, artifacts, opp_pos, hp, mana)
            
        # Defensive retreat if low health
        if hp <= 40 and self.dist(self_pos, opp_pos) <= 3:
            return self._safe_retreat_direction(self_pos, opp_pos, all_minions=minions, opponent_pos=opp_pos)
            
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
            return self._intelligent_strafe(self_data, self_pos, opp_pos, minions, artifacts)
            
    def _calculate_move_toward_artifact(self, self_pos, artifacts, opp_pos, hp=None, mana=None):
        """Calculate movement toward best artifact"""
        if hp is None or mana is None:
            # If hp or mana not provided, use a neutral value for artifact selection
            best_artifact = self._choose_best_artifact(artifacts, self_pos, opp_pos, 0, 0)
        else:
            best_artifact = self._choose_best_artifact(artifacts, self_pos, opp_pos, hp, mana)
            
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
                score += 25  # Increased value for cooldown reduction
                
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
        
    def _calculate_optimal_distance(self, self_data, opp_data, hp, mana):
        """Calculate optimal distance based on situation"""
        fireball_ready = self_data["cooldowns"]["fireball"] == 0 and mana >= 30
        opp_shielded = opp_data.get("shield_active", False)
        self_shielded = self_data.get("shield_active", False)
        
        if hp <= 30:
            # Very low health, stay far
            return 7 # Increased from 6
        elif hp <= 50 and not self_shielded:
            # Low health without shield, maintain distance
            return 6 # Increased from 5
        elif fireball_ready and not opp_shielded:
            # Can use fireball and opponent not shielded
            return 5 # Increased from 4
        elif self_shielded and hp > 70:
            # We're shielded and healthy, can be aggressive
            return 3 # Increased from 2, but still closer
        else:
            # Default moderate distance
            return 5 # Increased from 4
            
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
        
    def _safe_retreat_direction(self, self_pos, primary_threat_pos, all_minions=None, opponent_pos=None):
        """Calculate safest direction to retreat, considering all threats."""
        if all_minions is None:
            all_minions = []
        if opponent_pos is None:
            opponent_pos = primary_threat_pos # Default if not specified separately

        possible_moves = []
        own_minion_positions = [m["position"] for m in all_minions if m["owner"] == self._name]

        # Consider diagonal moves for better escape options
        for dx_option in [-1, 0, 1]:
            for dy_option in [-1, 0, 1]:
                if dx_option == 0 and dy_option == 0:
                    continue  # No movement
                
                new_x = self_pos[0] + dx_option
                new_y = self_pos[1] + dy_option

                # Ensure within bounds
                if not (0 <= new_x <= 9 and 0 <= new_y <= 9):
                    continue
                
                # Avoid moving into own minions
                if [new_x, new_y] in own_minion_positions:
                    continue

                possible_moves.append(([dx_option, dy_option], [new_x, new_y]))

        if not possible_moves:
            return [0,0] # Should not happen if self_pos is valid

        best_move_option = [0,0]
        max_safety_score = -float('inf')

        # Collect all threat positions
        threat_positions = [opponent_pos] + [m["position"] for m in all_minions if m["owner"] != self._name]
        if primary_threat_pos not in threat_positions: # Ensure primary threat is included
             threat_positions.append(primary_threat_pos)

        for move_option, new_pos in possible_moves:
            safety_score = 0
            
            # Primary factor: distance from the main threat
            dist_to_primary_threat = self.dist(new_pos, primary_threat_pos)
            safety_score += dist_to_primary_threat * 4  # Increased weight to prioritize getting away from primary threat

            # Secondary factor: sum of distances to all other threats
            for threat_idx, other_threat_pos in enumerate(threat_positions):
                if other_threat_pos != primary_threat_pos:  # Don't double count primary threat
                    dist_to_other = self.dist(new_pos, other_threat_pos)
                    safety_score += dist_to_other * 1.5  # Increased weight

            # Bonus for moving perpendicular to primary threat
            move_vector = (move_option[0], move_option[1])
            threat_vector = (primary_threat_pos[0] - self_pos[0], primary_threat_pos[1] - self_pos[1])
            
            # Check if vectors are meaningful for perpendicularity analysis
            if threat_vector[0] != 0 or threat_vector[1] != 0:
                # Calculate normalized dot product for perpendicularity check
                # First, get magnitudes
                move_mag = (move_vector[0]**2 + move_vector[1]**2)**0.5
                threat_mag = (threat_vector[0]**2 + threat_vector[1]**2)**0.5
                
                if move_mag > 0 and threat_mag > 0:
                    # Calculate actual dot product
                    dot_product = (move_vector[0] * threat_vector[0] + move_vector[1] * threat_vector[1]) / (move_mag * threat_mag)
                    
                    # If close to perpendicular (dot product near 0)
                    if abs(dot_product) < 0.3:  # More precisely defining "perpendicular"
                        safety_score += 5  # Increased bonus for perpendicular movement
                    # Penalize moving directly toward the threat
                    elif dot_product > 0.7:
                        safety_score -= 10  # Strong penalty for moving toward threat
                    # Bonus for moving away from threat
                    elif dot_product < -0.7:
                        safety_score += 3
            
            # Even stronger penalty for edges and corners
            if new_pos[0] == 0 or new_pos[0] == 9 or new_pos[1] == 0 or new_pos[1] == 9: # Edge
                safety_score -= 10
            if (new_pos[0] == 0 and new_pos[1] == 0) or (new_pos[0] == 0 and new_pos[1] == 9) or \
               (new_pos[0] == 9 and new_pos[1] == 0) or (new_pos[0] == 9 and new_pos[1] == 9): # Corner
                safety_score -= 20
            
            # Add preference for diagonal moves in general (faster escape)
            if move_option[0] != 0 and move_option[1] != 0:
                safety_score += 2
            
            # Avoid repeating recent movement patterns to be less predictable
            if len(self._last_positions) > 1:
                last_move_dx = self_pos[0] - self._last_positions[-1][0]
                last_move_dy = self_pos[1] - self._last_positions[-1][1]
                if move_option[0] == last_move_dx and move_option[1] == last_move_dy:
                    safety_score -= 4  # Increased penalty

            if safety_score > max_safety_score:
                max_safety_score = safety_score
                best_move_option = move_option
            elif safety_score == max_safety_score and random.random() < 0.3:  # Add some randomness for tied options
                best_move_option = move_option
        
        return best_move_option
        
    def _direction_to_optimal_distance(self, self_data, self_pos, target_pos, optimal_distance):
        """Calculate direction to maintain optimal distance"""
        current_distance = self.dist(self_pos, target_pos)
        
        if abs(current_distance - optimal_distance) <= 1:
            # Already at optimal distance, return lateral movement
            return self._intelligent_strafe(self_data, self_pos, target_pos, [], [])
            
        if current_distance < optimal_distance:
            # Too close, move away
            return self._direction_away_from(self_pos, target_pos, 1)
        else:
            # Too far, move closer
            return self._direction_toward(self_pos, target_pos, 1)
            
    def _intelligent_strafe(self, self_data, self_pos, target_pos, minions, artifacts):
        """Strafe intelligently, avoiding obstacles and seeking advantages"""
        dx = target_pos[0] - self_pos[0]
        dy = target_pos[1] - self_pos[1]
        
        # Calculate perpendicular directions (two options)
        # Prefer movement perpendicular to the longest axis of distance
        if abs(dx) > abs(dy):
            # More horizontal distance, so primary strafe is vertical
            options = [[0, 1], [0, -1]]
        elif abs(dy) > abs(dx):
            # More vertical distance, so primary strafe is horizontal
            options = [[1, 0], [-1, 0]]
        else: # Equal distance, can choose either set or mix
            options = [[0, 1], [0, -1], [1, 0], [-1, 0]]
            random.shuffle(options) # Shuffle to break ties randomly
            options = options[:2] # Pick two primary directions
            
        # Score each option
        best_score = -float('inf') # Initialize with negative infinity
        best_options_list = []

        for option in options:
            new_x = self_pos[0] + option[0]
            new_y = self_pos[1] + option[1]
            new_pos = [new_x, new_y]
            
            # Stay in bounds
            if not (0 <= new_x <= 9 and 0 <= new_y <= 9):
                continue
                
            score = 0
            
            # Prefer moves that maintain optimal distance or slightly increase it defensively
            current_target_dist = self.dist(self_pos, target_pos)
            new_target_dist = self.dist(new_pos, target_pos)
            
            # Ideal strafe keeps similar distance or moves slightly away if too close
            if abs(new_target_dist - current_target_dist) <= 1: # Maintains similar distance
                score += 20
            elif new_target_dist > current_target_dist and current_target_dist < 3: # Moves away if very close
                score += 15
            else: # Otherwise, penalize if it significantly changes distance undesirably
                score -= 10

            # Avoid minions
            for minion in minions: # Consider all minions on the field
                if self.dist(new_pos, minion["position"]) <= 1:
                    if minion["owner"] == self._name:
                        score -= 50 # Very strong penalty for moving near OWN minion (potential collision)
                    else:
                        score -= 30 # Strong penalty for moving near opponent minion
                    
            # Bonus for moving toward strategically valuable artifacts
            if artifacts:
                best_artifact = self._choose_best_artifact(artifacts, self_pos, target_pos, self_data["hp"], self_data["mana"]) # Use current HP/Mana
                if best_artifact:
                    current_artifact_dist = self.dist(self_pos, best_artifact["position"])
                    new_artifact_dist = self.dist(new_pos, best_artifact["position"])
                    if new_artifact_dist < current_artifact_dist:
                        score += 10
                    # Slight penalty for moving away from a good artifact if it's close
                    elif new_artifact_dist > current_artifact_dist and current_artifact_dist <= 3:
                        score -= 5
                    
            # Stronger penalty for board edges/corners
            if new_x == 0 or new_x == 9 or new_y == 0 or new_y == 9: # Edge
                score -= 30  # Increased penalty for edges
            if (new_x == 0 and new_y == 0) or (new_x == 0 and new_y == 9) or \
               (new_x == 9 and new_y == 0) or (new_x == 9 and new_y == 9): # Corner
                score -= 50  # Increased penalty for corners
            elif new_x <= 1 or new_x >= 8 or new_y <= 1 or new_y >= 8: # Near Edge
                score -= 20  # Increased penalty for near edges

            # Avoid repeating the exact same strafe move if previous move was also a strafe
            if len(self._last_positions) > 1:
                prev_move_dx = self_pos[0] - self._last_positions[-2][0]
                prev_move_dy = self_pos[1] - self._last_positions[-2][1]
                if option[0] == prev_move_dx and option[1] == prev_move_dy and abs(prev_move_dx) + abs(prev_move_dy) == 1: # Was a 1-step move
                    score -= 15  # Increased penalty for repeating the last 1-step move
            
            if score > best_score:
                best_score = score
                best_options_list = [option]
            elif score == best_score:
                best_options_list.append(option)
        
        if best_options_list:
            return random.choice(best_options_list) # Choose randomly among the best options
            
        # Fallback: if no good options, try to move away from target_pos or a random valid move
        fallback_move = self._direction_away_from(self_pos, target_pos, 1)
        # Check if fallback is valid
        fb_x, fb_y = self_pos[0] + fallback_move[0], self_pos[1] + fallback_move[1]
        if 0 <= fb_x <= 9 and 0 <= fb_y <= 9:
            return fallback_move
        else: # If even fallback is bad, pick any valid adjacent move
            valid_moves = []
            for opt_x, opt_y in [[0,1],[0,-1],[1,0],[-1,0],[1,1],[1,-1],[-1,1],[-1,-1]]:  # Added diagonal moves
                nx, ny = self_pos[0] + opt_x, self_pos[1] + opt_y
                if 0 <= nx <= 9 and 0 <= ny <= 9:
                    valid_moves.append([opt_x, opt_y])
            if valid_moves:
                return random.choice(valid_moves)

        return options[0] # Default if all else fails

    def move_toward(self, start, target, forbidden_cells=None):
        """Move one step toward target, avoiding forbidden_cells"""
        if forbidden_cells is None:
            forbidden_cells = []

        dx = target[0] - start[0]
        dy = target[1] - start[1]
        
        potential_steps = []
        # Prioritize larger dimension first
        if abs(dx) > abs(dy):
            if dx != 0: potential_steps.append((1 if dx > 0 else -1, 0))
            if dy != 0: potential_steps.append((0, 1 if dy > 0 else -1)) # Secondary option
        else:
            if dy != 0: potential_steps.append((0, 1 if dy > 0 else -1))
            if dx != 0: potential_steps.append((1 if dx > 0 else -1, 0)) # Secondary option

        # If no primary/secondary (e.g. already on target axis), add other axis options
        if not potential_steps and dx == 0 and dy !=0:
             potential_steps.extend([(1,0),(-1,0)])
        elif not potential_steps and dy == 0 and dx !=0:
             potential_steps.extend([(0,1),(0,-1)])
        elif not potential_steps and dx==0 and dy==0: # Already at target
            return [0,0]
        
        # Ensure all 4 directions are considered if primary ones are blocked or invalid
        all_directions = [(1,0), (-1,0), (0,1), (0,-1)]
        random.shuffle(all_directions)
        for d in all_directions:
            if d not in potential_steps:
                potential_steps.append(d)

        for step_x, step_y in potential_steps:
            new_x = start[0] + step_x
            new_y = start[1] + step_y
            
            if (0 <= new_x <= 9 and 0 <= new_y <= 9) and [new_x, new_y] not in forbidden_cells:
                return [step_x, step_y]
                
        return [0, 0] # No valid move found
        
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
        """Calculate direction toward target with improved distance handling for blink"""
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        
        # For blink specifically (typically called with distance=2)
        if distance == 2:
            # Use Manhattan distance to maximize blink range usage
            manhattan_dist = abs(dx) + abs(dy)
            
            # If Manhattan distance <= 4 (within blink range), try to get as close as possible
            if manhattan_dist <= 4:
                # Normalize to max absolute component = distance
                max_component = max(abs(dx), abs(dy))
                if max_component > 0:
                    scale_factor = min(2, max_component) / max_component
                    new_dx = int(round(dx * scale_factor))
                    new_dy = int(round(dy * scale_factor))
                    
                    # Ensure we don't exceed blink range (dx + dy <= 4)
                    while abs(new_dx) + abs(new_dy) > 4:
                        if abs(new_dx) > abs(new_dy):
                            new_dx = new_dx - (1 if new_dx > 0 else -1)
                        else:
                            new_dy = new_dy - (1 if new_dy > 0 else -1)
                    
                    # Check if resulting position is in bounds
                    new_x = start[0] + new_dx
                    new_y = start[1] + new_dy
                    
                    if 0 <= new_x <= 9 and 0 <= new_y <= 9:
                        return [new_dx, new_dy]
        
        # Normalize and scale (standard approach for other cases)
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
                dx = -start[0]  # Move to edge
            elif new_x > 9:
                dx = 9 - start[0]  # Move to edge
                
            if new_y < 0:
                dy = -start[1]  # Move to edge
            elif new_y > 9:
                dy = 9 - start[1]  # Move to edge
                
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