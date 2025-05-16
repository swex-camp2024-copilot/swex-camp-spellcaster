import random

from bots.bot_interface import BotInterface


class Byron(BotInterface):
    def __init__(self):
        # Required properties for the game engine
        self._name = "Byron"
        self._sprite_path = "assets/wizards/byron.png"
        self._minion_sprite_path = "assets/minions/byrons_minion.png"
        # Strategy tracking
        self._previous_states = []  # Track previous states for pattern recognition
        self._opponent_moves = []  # Track opponent's last 5 moves
        self._opponent_spells = []  # Track opponent's last 5 spells
        self._game_phase = "early"

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
        """Main decision function that gets called by the game engine each turn"""
        # Update tracking data
        self._update_tracking(state)
        
        # Analyze current game state
        analysis = self.analyze_game_state(state)
        
        # Use hierarchical decision making based on strategy document
        # 1. Survival Check
        if analysis["resource_status"]["self_hp"] <= 20:
            return self.survival_action(state, analysis)
            
        # 2. Opportunity Assessment - check for kill opportunity
        if self.has_kill_opportunity(state, analysis):
            return self.execute_kill_sequence(state, analysis)
            
        # 3-6. Resource, Position, Spell, Movement based on game phase
        if analysis["game_phase"] == "early":
            return self.early_game_action(state, analysis)
        elif analysis["game_phase"] == "mid":
            return self.mid_game_action(state, analysis)
        else:  # Late game
            return self.late_game_action(state, analysis)

    def _update_tracking(self, state):
        """Update pattern tracking variables"""
        # Track opponent's previous actions if we have previous states
        if self._previous_states:
            prev_state = self._previous_states[-1]
            prev_opp_pos = prev_state["opponent"]["position"]
            curr_opp_pos = state["opponent"]["position"]
            
            # Calculate the move the opponent made
            opp_move = [
                curr_opp_pos[0] - prev_opp_pos[0],
                curr_opp_pos[1] - prev_opp_pos[1]
            ]
            
            # Keep track of last 5 moves
            self._opponent_moves.append(opp_move)
            if len(self._opponent_moves) > 5:
                self._opponent_moves.pop(0)
                
            # Try to determine if opponent cast a spell
            # This is imperfect as we can't directly observe spells
            prev_opp_cooldowns = prev_state["opponent"]["cooldowns"]
            curr_opp_cooldowns = state["opponent"]["cooldowns"]
            
            for spell, cooldown in curr_opp_cooldowns.items():
                if cooldown > prev_opp_cooldowns.get(spell, 0):
                    self._opponent_spells.append(spell)
                    if len(self._opponent_spells) > 5:
                        self._opponent_spells.pop(0)
                    break
        
        # Store current state for future reference
        self._previous_states.append(state)
        if len(self._previous_states) > 5:
            self._previous_states.pop(0)

    def analyze_game_state(self, state):
        """Comprehensive analysis of the current game state"""
        self_info = state["self"]
        opponent_info = state["opponent"]
        artifacts = state.get("artifacts", [])
        minions = state.get("minions", [])
        
        # Calculate distances to key entities
        distances = self.calculate_distances(self_info, opponent_info, artifacts, minions)
        
        # Assess threats
        threats = self.assess_threats(state, self_info, opponent_info, minions, distances)
        
        # Identify opportunities
        opportunities = self.identify_opportunities(state, self_info, opponent_info, artifacts, minions, distances)
        
        # Evaluate resources
        resource_status = self.evaluate_resources(self_info, opponent_info, minions)
        
        # Determine game phase
        game_phase = self.determine_game_phase(state["turn"], self_info, opponent_info)
        self._game_phase = game_phase
        
        # Calculate overall state score
        state_score = self.calculate_state_score(self_info, opponent_info, distances, threats, opportunities, resource_status, minions)
        
        return {
            "distances": distances,
            "threats": threats,
            "opportunities": opportunities,
            "resource_status": resource_status,
            "game_phase": game_phase,
            "state_score": state_score
        }

    def calculate_distances(self, self_info, opponent_info, artifacts, minions):
        """Calculate distances between key entities"""
        self_pos = self_info["position"]
        opp_pos = opponent_info["position"]
        
        # Distance to opponent
        distance_to_opponent = self.chebyshev_dist(self_pos, opp_pos)
        
        # Distance to artifacts
        artifact_distances = [(a, self.chebyshev_dist(self_pos, a["position"])) for a in artifacts]
        
        # Nearest artifact
        nearest_artifact = None
        if artifacts:
            nearest = min(artifacts, key=lambda a: self.chebyshev_dist(self_pos, a["position"]))
            nearest_artifact = {
                "artifact": nearest,
                "distance": self.chebyshev_dist(self_pos, nearest["position"])
            }
        
        # Distance to minions
        minion_distances = []
        for m in minions:
            owner = m["owner"]
            dist_to_minion = self.chebyshev_dist(self_pos, m["position"])
            minion_distances.append({
                "minion": m,
                "distance": dist_to_minion,
                "friendly": owner == self_info["name"]
            })
        
        # Check distance to board center
        center_pos = [4, 4]
        distance_to_center = self.chebyshev_dist(self_pos, center_pos)
        
        return {
            "to_opponent": distance_to_opponent,
            "to_artifacts": artifact_distances,
            "nearest_artifact": nearest_artifact,
            "to_minions": minion_distances,
            "to_center": distance_to_center
        }

    def assess_threats(self, state, self_info, opponent_info, minions, distances):
        """Assess threats to the wizard"""
        self_pos = self_info["position"]
        opp_pos = opponent_info["position"]
        threats = {}
        
        # Check if opponent can cast fireball
        opp_fireball_ready = opponent_info["cooldowns"].get("fireball", 0) == 0 and opponent_info["mana"] >= 30
        in_fireball_range = distances["to_opponent"] <= 5
        threats["fireball_threat"] = opp_fireball_ready and in_fireball_range
        
        # Check if opponent or enemy minion is adjacent (melee threat)
        enemy_minions = [m for m in minions if m["owner"] != self_info["name"]]
        adjacent_enemies = []
        for e in [opponent_info] + enemy_minions:
            if self.manhattan_dist(self_pos, e["position"]) == 1:
                adjacent_enemies.append(e)
        threats["adjacent_enemies"] = adjacent_enemies
        
        # Check if opponent can cast shield
        opp_shield_ready = opponent_info["cooldowns"].get("shield", 0) == 0 and opponent_info["mana"] >= 20
        threats["opponent_can_shield"] = opp_shield_ready
        
        # Check if we're trapped in a corner with opponent nearby
        is_corner = (self_pos[0] in [0, 9] and self_pos[1] in [0, 9])
        opponent_nearby = distances["to_opponent"] <= 3
        threats["corner_trapped"] = is_corner and opponent_nearby
        
        # Calculate danger score for current position (weighted threat assessment)
        in_opponent_melee_range = self.manhattan_dist(self_pos, opp_pos) == 1
        in_opponent_blink_range = distances["to_opponent"] <= 3  # Opponent can blink then melee next turn
        
        # Check if we're in fireball splash range of enemy entities
        in_fireball_splash = False
        for e in enemy_minions + [opponent_info]:
            if self.chebyshev_dist(self_pos, e["position"]) <= 1 and e != opponent_info:
                in_fireball_splash = True
                break
        
        # Calculate collision risk
        collision_risk = self.estimate_collision_risk(state)
        
        # Overall danger score
        threats["danger_score"] = (
            (5 if in_opponent_melee_range else 0) +
            (3 if in_opponent_blink_range else 0) +
            (3 if in_fireball_splash else 0) +
            (4 if threats["corner_trapped"] else 0) +
            (4 if collision_risk > 0.5 else 0)
        )
        
        # Threat from enemy minion
        enemy_minion_threat = 0
        for m in enemy_minions:
            dist = self.manhattan_dist(self_pos, m["position"])
            if dist <= 3:  # Minion can reach us within 3 turns
                enemy_minion_threat += max(0, 4 - dist)  # Higher threat when closer
        
        threats["enemy_minion_threat"] = enemy_minion_threat
        
        return threats

    def identify_opportunities(self, state, self_info, opponent_info, artifacts, minions, distances):
        """Identify opportunities for advantageous actions"""
        self_pos = self_info["position"]
        opp_pos = opponent_info["position"]
        opportunities = {}
        
        # Artifact collection opportunities
        reachable_artifacts = []
        for a in artifacts:
            dist = self.chebyshev_dist(self_pos, a["position"])
            if dist <= 1:  # Can reach in one move
                reachable_artifacts.append(a)
        opportunities["reachable_artifacts"] = reachable_artifacts
        
        # Attack opportunities
        can_fireball = self_info["cooldowns"].get("fireball", 0) == 0 and self_info["mana"] >= 30
        in_fireball_range = distances["to_opponent"] <= 5
        opponent_shielded = opponent_info.get("shield_active", False)
        opportunities["can_fireball_opponent"] = can_fireball and in_fireball_range
        opportunities["fireball_effective"] = opportunities["can_fireball_opponent"] and not opponent_shielded
        
        # Check for enemy minion that could be hit with fireball splash damage
        opportunities["fireball_splash_potential"] = False
        enemy_minions = [m for m in minions if m["owner"] != self_info["name"]]
        for m in enemy_minions:
            if self.chebyshev_dist(opp_pos, m["position"]) <= 1:
                opportunities["fireball_splash_potential"] = True
                break
        
        # Melee attack opportunity
        can_melee = self_info["cooldowns"].get("melee_attack", 0) == 0
        adjacent_to_opponent = self.manhattan_dist(self_pos, opp_pos) == 1
        opportunities["can_melee_opponent"] = can_melee and adjacent_to_opponent
        
        # Shield opportunity
        can_shield = self_info["cooldowns"].get("shield", 0) == 0 and self_info["mana"] >= 20
        shield_active = self_info.get("shield_active", False)
        opponent_can_attack = (
            (opponent_info["cooldowns"].get("fireball", 0) == 0 and opponent_info["mana"] >= 30 and distances["to_opponent"] <= 5) or
            (self.manhattan_dist(self_pos, opp_pos) <= 2)  # Could get in melee range next turn
        )
        opportunities["should_shield"] = can_shield and not shield_active and opponent_can_attack
        
        # Heal opportunity
        can_heal = self_info["cooldowns"].get("heal", 0) == 0 and self_info["mana"] >= 25
        hp_deficit = 100 - self_info["hp"]
        opportunities["should_heal"] = can_heal and hp_deficit >= 15  # Only heal if at least 15 HP can be restored
        
        # Teleport opportunity
        can_teleport = self_info["cooldowns"].get("teleport", 0) == 0 and self_info["mana"] >= 20
        valuable_target = None
        
        if artifacts:
            # Prioritize artifacts based on need
            health_value = 20 * (1 - (self_info["hp"] / 100.0)) * 2  # Value scales with missing health
            mana_value = 30 * (1 - (self_info["mana"] / 100.0)) * 1.5  # Value scales with missing mana
            cooldown_value = 10 * sum(cd for cd in self_info["cooldowns"].values() if cd > 0)  # Value scales with active cooldowns
            
            best_value = -1
            for a in artifacts:
                a_type = a.get("type", "")
                value = 0
                
                if a_type == "health":
                    value = health_value
                elif a_type == "mana":
                    value = mana_value
                elif a_type == "cooldown":
                    value = cooldown_value
                
                # Discount value by proximity (closer artifacts are more valuable)
                dist = self.chebyshev_dist(self_pos, a["position"])
                if dist <= 1:  # Can reach next turn by moving
                    continue  # Skip artifacts we can easily reach
                
                # Teleport is most valuable for distant, high-value artifacts
                adjusted_value = value - (dist * 2)
                
                if adjusted_value > best_value:
                    best_value = adjusted_value
                    valuable_target = a["position"]
                    
        # Also consider teleporting away from danger
        if distances["to_opponent"] <= 2 and self_info["hp"] < 40:
            # Find position furthest from opponent and enemy minions
            max_safety = -1
            safest_pos = None
            
            for x in range(10):
                for y in range(10):
                    pos = [x, y]
                    # Skip current positions of entities
                    if pos == self_pos or pos == opp_pos:
                        continue
                    
                    occupied = False
                    for m in minions:
                        if pos == m["position"]:
                            occupied = True
                            break
                    
                    if occupied:
                        continue
                    
                    # Calculate safety (distance from enemies)
                    safety = self.chebyshev_dist(pos, opp_pos)
                    for m in minions:
                        if m["owner"] != self_info["name"]:  # Enemy minion
                            safety += self.chebyshev_dist(pos, m["position"]) * 0.5
                    
                    if safety > max_safety:
                        max_safety = safety
                        safest_pos = pos
            
            if safest_pos and max_safety > 7:  # Only if significantly safer
                valuable_target = safest_pos
        
        opportunities["teleport_target"] = valuable_target
        
        # Summon opportunity
        can_summon = self_info["cooldowns"].get("summon", 0) == 0 and self_info["mana"] >= 50
        has_own_minion = any(m["owner"] == self_info["name"] for m in minions)
        opportunities["should_summon"] = can_summon and not has_own_minion and self_info["mana"] >= 60  # Ensure enough mana left after summon
        
        # Blink opportunity
        can_blink = self_info["cooldowns"].get("blink", 0) == 0 and self_info["mana"] >= 10
        
        # Blink to collect artifact
        blink_to_artifact = None
        for a in artifacts:
            dist = self.chebyshev_dist(self_pos, a["position"])
            if 1 < dist <= 2:  # Just outside reach but within blink range
                blink_to_artifact = a["position"]
                break
        
        # Blink to escape or approach
        blink_to_escape = None
        blink_to_approach = None
        
        if distances["to_opponent"] <= 2 and self_info["hp"] < 50:
            # Find best escape position
            best_pos = None
            max_dist = -1
            
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    if abs(dx) > 2 or abs(dy) > 2 or (dx == 0 and dy == 0):
                        continue  # Skip invalid blink targets
                    
                    new_x = self_pos[0] + dx
                    new_y = self_pos[1] + dy
                    
                    # Check bounds
                    if new_x < 0 or new_x >= 10 or new_y < 0 or new_y >= 10:
                        continue
                    
                    # Check if occupied
                    occupied = False
                    if [new_x, new_y] == opp_pos:
                        occupied = True
                    
                    for m in minions:
                        if [new_x, new_y] == m["position"]:
                            occupied = True
                            break
                    
                    if occupied:
                        continue
                    
                    # Check if this increases distance
                    new_dist = self.chebyshev_dist([new_x, new_y], opp_pos)
                    if new_dist > distances["to_opponent"] and new_dist > max_dist:
                        max_dist = new_dist
                        best_pos = [new_x, new_y]
            
            blink_to_escape = best_pos
        
        elif distances["to_opponent"] > 2 and self_info["hp"] > 60 and not opponent_info.get("shield_active", False):
            # Blink to approach for attack
            best_pos = None
            target_dist = 1  # Try to get adjacent for melee
            
            if self_info["cooldowns"].get("melee_attack", 0) > 0:
                target_dist = 5  # Or in fireball range if melee on cooldown
            
            min_diff = float('inf')
            
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    if abs(dx) > 2 or abs(dy) > 2 or (dx == 0 and dy == 0):
                        continue  # Skip invalid blink targets
                    
                    new_x = self_pos[0] + dx
                    new_y = self_pos[1] + dy
                    
                    # Check bounds
                    if new_x < 0 or new_x >= 10 or new_y < 0 or new_y >= 10:
                        continue
                    
                    # Check if occupied
                    occupied = False
                    if [new_x, new_y] == opp_pos:
                        occupied = True
                    
                    for m in minions:
                        if [new_x, new_y] == m["position"]:
                            occupied = True
                            break
                    
                    if occupied:
                        continue
                    
                    # Check if this gets closer to target distance
                    new_dist = self.chebyshev_dist([new_x, new_y], opp_pos)
                    diff = abs(new_dist - target_dist)
                    
                    if diff < min_diff:
                        min_diff = diff
                        best_pos = [new_x, new_y]
            
            blink_to_approach = best_pos
            
        opportunities["blink_target"] = blink_to_artifact or blink_to_escape or blink_to_approach
        
        return opportunities

    def evaluate_resources(self, self_info, opponent_info, minions):
        """Evaluate resource status"""
        # Calculate minion advantage
        self_has_minion = any(m["owner"] == self_info["name"] for m in minions)
        opponent_has_minion = any(m["owner"] != self_info["name"] for m in minions)
        
        return {
            "self_hp": self_info["hp"],
            "opponent_hp": opponent_info["hp"],
            "self_mana": self_info["mana"],
            "opponent_mana": opponent_info["mana"],
            "self_has_shield": self_info.get("shield_active", False),
            "opponent_has_shield": opponent_info.get("shield_active", False),
            "self_has_minion": self_has_minion,
            "opponent_has_minion": opponent_has_minion,
            "hp_advantage": self_info["hp"] - opponent_info["hp"],
            "mana_advantage": self_info["mana"] - opponent_info["mana"],
            "minion_advantage": 1 if self_has_minion and not opponent_has_minion else 
                              -1 if not self_has_minion and opponent_has_minion else 0
        }

    def determine_game_phase(self, turn, self_info, opponent_info):
        """Determine the current game phase based on turn number and game state"""
        if turn <= 5:
            return "early"
        elif turn <= 15:
            return "mid"
        else:
            return "late"

    def calculate_state_score(self, self_info, opponent_info, distances, threats, opportunities, resource_status, minions):
        """Calculate overall state score to evaluate position advantage"""
        # Extract key factors
        self_hp = self_info["hp"]
        opponent_hp = opponent_info["hp"]
        self_mana = self_info["mana"]
        opponent_mana = opponent_info["mana"]
        self_has_shield = self_info.get("shield_active", False)
        opponent_has_shield = opponent_info.get("shield_active", False)
        self_has_minion = resource_status["self_has_minion"]
        opponent_has_minion = resource_status["opponent_has_minion"]
        
        # Artifact proximity factor
        nearest_artifact_distance = distances["nearest_artifact"]["distance"] if distances["nearest_artifact"] else 10
        
        # Control center score
        control_center_score = max(0, 5 - distances["to_center"])
        
        # Cooldown advantage
        self_cooldown_sum = sum(cd for cd in self_info["cooldowns"].values())
        opponent_cooldown_sum = sum(cd for cd in opponent_info["cooldowns"].values())
        cooldown_advantage = opponent_cooldown_sum - self_cooldown_sum
        
        # Danger from enemy entities
        min_distance_from_dangerous = float('inf')
        for m in minions:
            if m["owner"] != self_info["name"]:
                dist = self.chebyshev_dist(self_info["position"], m["position"])
                min_distance_from_dangerous = min(min_distance_from_dangerous, dist)
        
        min_distance_from_dangerous = min(min_distance_from_dangerous, distances["to_opponent"])
        
        # Calculate state score using the weighted formula from strategy document
        state_score = (
            2.0 * (self_hp - opponent_hp) +
            0.8 * (self_mana - opponent_mana) +
            15.0 * (1 if self_has_minion else 0) - 15.0 * (1 if opponent_has_minion else 0) +
            5.0 * (1 if self_has_shield else 0) - 5.0 * (1 if opponent_has_shield else 0) -
            3.0 * nearest_artifact_distance -
            1.0 * min_distance_from_dangerous +
            0.5 * control_center_score +
            2.0 * cooldown_advantage
        )
        
        return state_score

    def has_kill_opportunity(self, state, analysis):
        """Check if there's an opportunity to defeat the opponent"""
        self_info = state["self"]
        opponent_info = state["opponent"]
        
        # Check if opponent is low health and we can deal enough damage
        opponent_hp = opponent_info["hp"]
        opponent_shielded = opponent_info.get("shield_active", False)
        
        # Can kill with fireball?
        can_fireball = self_info["cooldowns"].get("fireball", 0) == 0 and self_info["mana"] >= 30
        in_fireball_range = analysis["distances"]["to_opponent"] <= 5
        will_kill_with_fireball = opponent_hp <= (20 if not opponent_shielded else 0)
        
        if can_fireball and in_fireball_range and will_kill_with_fireball:
            return True
            
        # Can kill with melee?
        can_melee = self_info["cooldowns"].get("melee_attack", 0) == 0
        adjacent_to_opponent = analysis["distances"]["to_opponent"] == 1
        will_kill_with_melee = opponent_hp <= 10  # Melee does 10 damage and ignores shield
        
        if can_melee and adjacent_to_opponent and will_kill_with_melee:
            return True
            
        return False

    def execute_kill_sequence(self, state, analysis):
        """Execute optimal sequence to defeat opponent"""
        self_info = state["self"]
        opponent_info = state["opponent"]
        self_pos = self_info["position"]
        opp_pos = opponent_info["position"]
        
        # Try fireball kill if possible
        can_fireball = self_info["cooldowns"].get("fireball", 0) == 0 and self_info["mana"] >= 30
        in_fireball_range = analysis["distances"]["to_opponent"] <= 5
        opponent_shielded = opponent_info.get("shield_active", False)
        will_kill_with_fireball = opponent_info["hp"] <= (20 if not opponent_shielded else 0)
        
        if can_fireball and in_fireball_range and will_kill_with_fireball:
            return {
                "move": [0, 0],  # Don't move, just attack
                "spell": {
                    "name": "fireball",
                    "target": opp_pos
                }
            }
            
        # Try melee kill if possible
        can_melee = self_info["cooldowns"].get("melee_attack", 0) == 0
        adjacent_to_opponent = analysis["distances"]["to_opponent"] == 1
        will_kill_with_melee = opponent_info["hp"] <= 10
        
        if can_melee and adjacent_to_opponent and will_kill_with_melee:
            return {
                "move": [0, 0],  # Don't move, just attack
                "spell": {
                    "name": "melee_attack",
                    "target": opp_pos
                }
            }
            
        # If not in range for kill, try to get in range
        if can_fireball and opponent_info["hp"] <= 20 and not in_fireball_range:
            # Try to blink to get in range
            can_blink = self_info["cooldowns"].get("blink", 0) == 0 and self_info["mana"] >= 10
            
            if can_blink:
                # Find best blink position to get in fireball range
                best_pos = None
                best_dist = float('inf')
                
                for dx in [-2, -1, 0, 1, 2]:
                    for dy in [-2, -1, 0, 1, 2]:
                        if abs(dx) > 2 or abs(dy) > 2 or (dx == 0 and dy == 0):
                            continue
                        
                        new_x = self_pos[0] + dx
                        new_y = self_pos[1] + dy
                        
                        # Check bounds
                        if new_x < 0 or new_x >= 10 or new_y < 0 or new_y >= 10:
                            continue
                        
                        # Check if position is occupied
                        occupied = False
                        if [new_x, new_y] == opp_pos:
                            occupied = True
                        
                        for m in state.get("minions", []):
                            if [new_x, new_y] == m["position"]:
                                occupied = True
                                break
                        
                        if occupied:
                            continue
                        
                        # Check if this gets us in fireball range
                        new_dist = self.chebyshev_dist([new_x, new_y], opp_pos)
                        if new_dist <= 5 and new_dist < best_dist:
                            best_dist = new_dist
                            best_pos = [new_x, new_y]
                
                if best_pos:
                    return {
                        "move": [0, 0],
                        "spell": {
                            "name": "blink",
                            "target": best_pos
                        }
                    }
            
            # If can't blink, try to teleport
            can_teleport = self_info["cooldowns"].get("teleport", 0) == 0 and self_info["mana"] >= 20
            
            if can_teleport:
                # Find best teleport position for fireball
                best_pos = None
                target_dist = 5  # Ideal fireball distance
                min_diff = float('inf')
                
                for x in range(10):
                    for y in range(10):
                        pos = [x, y]
                        # Skip occupied positions
                        if pos == self_pos or pos == opp_pos:
                            continue
                        
                        occupied = False
                        for m in state.get("minions", []):
                            if pos == m["position"]:
                                occupied = True
                                break
                        
                        if occupied:
                            continue
                        
                        dist = self.chebyshev_dist(pos, opp_pos)
                        if dist <= 5:  # In fireball range
                            diff = abs(dist - target_dist)
                            if diff < min_diff:
                                min_diff = diff
                                best_pos = pos
                
                if best_pos:
                    return {
                        "move": [0, 0],
                        "spell": {
                            "name": "teleport",
                            "target": best_pos
                        }
                    }
            
            # If can't blink or teleport, move toward opponent
            return {
                "move": self.move_toward(self_pos, opp_pos),
                "spell": None
            }
        
        # If opponent is low enough for melee kill but not adjacent
        if can_melee and opponent_info["hp"] <= 10 and not adjacent_to_opponent:
            # Try to blink to get adjacent
            can_blink = self_info["cooldowns"].get("blink", 0) == 0 and self_info["mana"] >= 10
            
            if can_blink and analysis["distances"]["to_opponent"] <= 3:
                # Find best blink position to get adjacent
                best_pos = None
                
                for dx in [-2, -1, 0, 1, 2]:
                    for dy in [-2, -1, 0, 1, 2]:
                        if abs(dx) > 2 or abs(dy) > 2 or (dx == 0 and dy == 0):
                            continue
                        
                        new_x = self_pos[0] + dx
                        new_y = self_pos[1] + dy
                        
                        # Check bounds
                        if new_x < 0 or new_x >= 10 or new_y < 0 or new_y >= 10:
                            continue
                        
                        # Check if position is occupied
                        occupied = False
                        if [new_x, new_y] == opp_pos:
                            occupied = True
                        
                        for m in state.get("minions", []):
                            if [new_x, new_y] == m["position"]:
                                occupied = True
                                break
                        
                        if occupied:
                            continue
                        
                        # Check if this gets us adjacent
                        if self.manhattan_dist([new_x, new_y], opp_pos) == 1:
                            best_pos = [new_x, new_y]
                            break
                
                if best_pos:
                    return {
                        "move": [0, 0],
                        "spell": {
                            "name": "blink",
                            "target": best_pos
                        }
                    }
            
            # If can't blink, move toward opponent
            return {
                "move": self.move_toward(self_pos, opp_pos),
                "spell": None
            }
        
        # Default to tactical move if no clear kill path
        return self.tactical_action(state, analysis)

    def survival_action(self, state, analysis):
        """Actions when at critically low HP"""
        self_info = state["self"]
        opponent_info = state["opponent"]
        self_pos = self_info["position"]
        opp_pos = opponent_info["position"]
        
        # Try to heal if possible
        can_heal = self_info["cooldowns"].get("heal", 0) == 0 and self_info["mana"] >= 25
        if can_heal:
            return {
                "move": [0, 0],
                "spell": {"name": "heal"}
            }
        
        # Try to shield if not active
        can_shield = self_info["cooldowns"].get("shield", 0) == 0 and self_info["mana"] >= 20
        shield_active = self_info.get("shield_active", False)
        
        if can_shield and not shield_active:
            return {
                "move": [0, 0],
                "spell": {"name": "shield"}
            }
        
        # Try to teleport to safety
        can_teleport = self_info["cooldowns"].get("teleport", 0) == 0 and self_info["mana"] >= 20
        
        if can_teleport:
            # Find safest position (furthest from opponent and enemy minions)
            best_pos = None
            max_safety = -1
            
            for x in range(10):
                for y in range(10):
                    pos = [x, y]
                    # Skip occupied positions
                    if pos == self_pos or pos == opp_pos:
                        continue
                    
                    occupied = False
                    for m in state.get("minions", []):
                        if pos == m["position"]:
                            occupied = True
                            break
                    
                    if occupied:
                        continue
                    
                    # Calculate safety score
                    safety_score = self.chebyshev_dist(pos, opp_pos)
                    
                    # Add bonus for positions near health artifacts
                    for a in state.get("artifacts", []):
                        if a.get("type") == "health" and self.chebyshev_dist(pos, a["position"]) <= 1:
                            safety_score += 5
                    
                    # Penalize positions near enemy minions
                    for m in state.get("minions", []):
                        if m["owner"] != self_info["name"]:  # Enemy minion
                            minion_dist = self.chebyshev_dist(pos, m["position"])
                            if minion_dist <= 3:
                                safety_score -= (4 - minion_dist) * 2
                    
                    if safety_score > max_safety:
                        max_safety = safety_score
                        best_pos = pos
            
            if best_pos:
                return {
                    "move": [0, 0],
                    "spell": {
                        "name": "teleport",
                        "target": best_pos
                    }
                }
        
        # Try to blink away
        can_blink = self_info["cooldowns"].get("blink", 0) == 0 and self_info["mana"] >= 10
        
        if can_blink:
            # Find best direction to blink away
            best_pos = None
            max_dist = -1
            
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    if abs(dx) > 2 or abs(dy) > 2 or (dx == 0 and dy == 0):
                        continue
                    
                    new_x = self_pos[0] + dx
                    new_y = self_pos[1] + dy
                    
                    # Check bounds
                    if new_x < 0 or new_x >= 10 or new_y < 0 or new_y >= 10:
                        continue
                    
                    # Check if position is occupied
                    occupied = False
                    if [new_x, new_y] == opp_pos:
                        occupied = True
                    
                    for m in state.get("minions", []):
                        if [new_x, new_y] == m["position"]:
                            occupied = True
                            break
                    
                    if occupied:
                        continue
                    
                    # Calculate distance from opponent
                    dist = self.chebyshev_dist([new_x, new_y], opp_pos)
                    if dist > max_dist:
                        max_dist = dist
                        best_pos = [new_x, new_y]
            
            if best_pos and max_dist > analysis["distances"]["to_opponent"]:
                return {
                    "move": [0, 0],
                    "spell": {
                        "name": "blink",
                        "target": best_pos
                    }
                }
        
        # If no survival spells available, try to move to health artifact
        health_artifacts = [a for a in state.get("artifacts", []) if a.get("type") == "health"]
        if health_artifacts:
            nearest = min(health_artifacts, key=lambda a: self.chebyshev_dist(self_pos, a["position"]))
            return {
                "move": self.move_toward(self_pos, nearest["position"]),
                "spell": None
            }
        
        # Last resort: move away from opponent and enemy minions
        best_move = [0, 0]
        max_safety = -1
        
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                
                new_x = self_pos[0] + dx
                new_y = self_pos[1] + dy
                
                # Check bounds
                if new_x < 0 or new_x >= 10 or new_y < 0 or new_y >= 10:
                    continue
                
                # Check if position is occupied
                occupied = False
                if [new_x, new_y] == opp_pos:
                    occupied = True
                
                for m in state.get("minions", []):
                    if [new_x, new_y] == m["position"]:
                        occupied = True
                        break
                
                if occupied:
                    continue
                
                # Calculate safety
                safety = self.chebyshev_dist([new_x, new_y], opp_pos)
                for m in state.get("minions", []):
                    if m["owner"] != self_info["name"]:  # Enemy minion
                        safety += self.chebyshev_dist([new_x, new_y], m["position"]) * 0.5
                
                if safety > max_safety:
                    max_safety = safety
                    best_move = [dx, dy]
        
        return {
            "move": best_move,
            "spell": None
        }

    def early_game_action(self, state, analysis):
        """
        Early game (turns 1-5) prioritizes:
        - Collecting artifacts
        - Establishing board control
        - Conserving mana for critical spells
        - Avoiding early damage
        """
        self_info = state["self"]
        self_pos = self_info["position"]
        
        # Try to shield early if not already done
        can_shield = self_info["cooldowns"].get("shield", 0) == 0 and self_info["mana"] >= 20
        shield_active = self_info.get("shield_active", False)
        
        if can_shield and not shield_active and state["turn"] <= 2:
            return {
                "move": [0, 0],
                "spell": {"name": "shield"}
            }
        
        # Check for artifact collection opportunities
        artifacts = state.get("artifacts", [])
        if artifacts and analysis["distances"]["nearest_artifact"]:
            nearest = analysis["distances"]["nearest_artifact"]["artifact"]
            distance = analysis["distances"]["nearest_artifact"]["distance"]
            
            # If adjacent to artifact, move to collect it
            if distance <= 1:
                return {
                    "move": self.move_toward(self_pos, nearest["position"]),
                    "spell": None
                }
            
            # If artifact is within blink range, consider blinking to it
            elif distance <= 2:
                can_blink = self_info["cooldowns"].get("blink", 0) == 0 and self_info["mana"] >= 10
                
                if can_blink:
                    return {
                        "move": [0, 0],
                        "spell": {
                            "name": "blink",
                            "target": nearest["position"]
                        }
                    }
        
        # If no immediate artifact opportunities, move toward center for better position
        center_pos = [4, 4]
        distance_to_center = analysis["distances"]["to_center"]
        
        if distance_to_center > 2:
            # Try blink to get to center faster
            can_blink = self_info["cooldowns"].get("blink", 0) == 0 and self_info["mana"] >= 10
            
            if can_blink:
                # Calculate blink target toward center
                move_dir = self.move_toward(self_pos, center_pos)
                
                blink_target = [
                    self_pos[0] + move_dir[0] * 2,
                    self_pos[1] + move_dir[1] * 2
                ]
                
                # Ensure target is within bounds
                blink_target[0] = max(0, min(9, blink_target[0]))
                blink_target[1] = max(0, min(9, blink_target[1]))
                
                # Check if position is occupied
                occupied = False
                if blink_target == state["opponent"]["position"]:
                    occupied = True
                
                for m in state.get("minions", []):
                    if blink_target == m["position"]:
                        occupied = True
                        break
                
                if not occupied:
                    return {
                        "move": [0, 0],
                        "spell": {
                            "name": "blink",
                            "target": blink_target
                        }
                    }
            
            # Otherwise just move toward center
            return {
                "move": self.move_toward(self_pos, center_pos),
                "spell": None
            }
        
        # Tactical check for opportunistic attack
        if analysis["opportunities"]["can_fireball_opponent"] and analysis["opportunities"]["fireball_effective"]:
            # Only use fireball if it would be effective (opponent not shielded)
            return {
                "move": [0, 0],
                "spell": {
                    "name": "fireball",
                    "target": state["opponent"]["position"]
                }
            }
        
        # Default to tactical action if no specific early game actions
        return self.tactical_action(state, analysis)
        
        # Tactical check for opportunistic attack
        if analysis["opportunities"]["can_fireball_opponent"] and analysis["opportunities"]["fireball_effective"]:
            # Only use fireball if it would be effective (opponent not shielded)
            return {
                "move": [0, 0],
                "spell": {
                    "name": "fireball",
                    "target": state["opponent"]["position"]
                }
            }
        
        # Default to tactical action if no specific early game actions
        return self.tactical_action(state, analysis)

    def mid_game_action(self, state, analysis):
        """
        Mid game (turns 6-15) prioritizes:
        - Tactical spell usage to gain advantage
        - Summon minion for pressure
        - Control high-value positions
        - Manage cooldowns efficiently
        """
        self_info = state["self"]
        opponent_info = state["opponent"]
        self_pos = self_info["position"]
        opp_pos = opponent_info["position"]
        
        # Check if should use shield defensively
        if analysis["opportunities"]["should_shield"]:
            return {
                "move": [0, 0],
                "spell": {"name": "shield"}
            }
        
        # Consider summoning minion for pressure
        if analysis["opportunities"]["should_summon"]:
            return {
                "move": [0, 0],
                "spell": {"name": "summon"}
            }
        
        # Check for healing opportunity
        if analysis["opportunities"]["should_heal"] and self_info["hp"] <= 60:
            return {
                "move": [0, 0],
                "spell": {"name": "heal"}
            }
        
        # Check for attack opportunities
        if analysis["opportunities"]["can_melee_opponent"]:
            return {
                "move": [0, 0],
                "spell": {
                    "name": "melee_attack",
                    "target": opp_pos
                }
            }
        
        if analysis["opportunities"]["can_fireball_opponent"]:
            # Prioritize fireball if opponent is not shielded or if we can hit multiple targets
            if not opponent_info.get("shield_active", False) or analysis["opportunities"]["fireball_splash_potential"]:
                return {
                    "move": [0, 0],
                    "spell": {
                        "name": "fireball",
                        "target": opp_pos
                    }
                }
        
        # Check for artifact collection opportunities
        if analysis["opportunities"]["reachable_artifacts"]:
            artifact = analysis["opportunities"]["reachable_artifacts"][0]
            return {
                "move": self.move_toward(self_pos, artifact["position"]),
                "spell": None
            }
        
        # Consider teleporting to valuable target
        if analysis["opportunities"]["teleport_target"] and self_info["cooldowns"].get("teleport", 0) == 0 and self_info["mana"] >= 20:
            return {
                "move": [0, 0],
                "spell": {
                    "name": "teleport",
                    "target": analysis["opportunities"]["teleport_target"]
                }
            }
        
        # Consider blinking for tactical advantage
        if analysis["opportunities"]["blink_target"] and self_info["cooldowns"].get("blink", 0) == 0 and self_info["mana"] >= 10:
            return {
                "move": [0, 0],
                "spell": {
                    "name": "blink",
                    "target": analysis["opportunities"]["blink_target"]
                }
            }
        
        # Default to tactical movement
        return self.tactical_action(state, analysis)

    def late_game_action(self, state, analysis):
        """
        Late game (turns 16+) prioritizes:
        - Aggressive damage dealing
        - HP advantage leveraging
        - Predictive movement to counter opponent
        - Use of burst damage combinations
        """
        self_info = state["self"]
        opponent_info = state["opponent"]
        self_pos = self_info["position"]
        opp_pos = opponent_info["position"]
        
        # If we have HP advantage, be aggressive
        hp_advantage = analysis["resource_status"]["hp_advantage"]
        
        if hp_advantage > 30:
            # Aggressive play - try to finish opponent
            
            # Melee if possible
            if analysis["opportunities"]["can_melee_opponent"]:
                return {
                    "move": [0, 0],
                    "spell": {
                        "name": "melee_attack",
                        "target": opp_pos
                    }
                }
            
            # Fireball if in range
            if analysis["opportunities"]["can_fireball_opponent"]:
                return {
                    "move": [0, 0],
                    "spell": {
                        "name": "fireball",
                        "target": opp_pos
                    }
                }
            
            # Try to blink closer for attack
            can_blink = self_info["cooldowns"].get("blink", 0) == 0 and self_info["mana"] >= 10
            if can_blink:
                best_pos = None
                best_dist = float('inf')
                
                # Try to get to melee range if melee is off cooldown
                target_dist = 1 if self_info["cooldowns"].get("melee_attack", 0) == 0 else 5
                
                for dx in [-2, -1, 0, 1, 2]:
                    for dy in [-2, -1, 0, 1, 2]:
                        if abs(dx) > 2 or abs(dy) > 2 or (dx == 0 and dy == 0):
                            continue
                        
                        new_x = self_pos[0] + dx
                        new_y = self_pos[1] + dy
                        
                        # Check bounds and occupancy
                        if (new_x < 0 or new_x >= 10 or new_y < 0 or new_y >= 10 or
                            [new_x, new_y] == opp_pos):
                            continue
                        
                        occupied = False
                        for m in state.get("minions", []):
                            if [new_x, new_y] == m["position"]:
                                occupied = True
                                break
                        
                        if occupied:
                            continue
                        
                        # Calculate how close this gets us to target distance
                        dist_to_opponent = self.chebyshev_dist([new_x, new_y], opp_pos)
                        diff = abs(dist_to_opponent - target_dist)
                        
                        if diff < best_dist:
                            best_dist = diff
                            best_pos = [new_x, new_y]
                
                if best_pos:
                    return {
                        "move": [0, 0],
                        "spell": {
                            "name": "blink",
                            "target": best_pos
                        }
                    }
            
            # Move toward opponent as default aggressive action
            return {
                "move": self.move_toward(self_pos, opp_pos),
                "spell": None
            }
        
        # If we have HP disadvantage, play more carefully
        elif hp_advantage < -10:
            # Defensive tactics
            
            # Shield if threatened
            if analysis["opportunities"]["should_shield"]:
                return {
                    "move": [0, 0],
                    "spell": {"name": "shield"}
                }
            
            # Heal if needed
            if analysis["opportunities"]["should_heal"]:
                return {
                    "move": [0, 0],
                    "spell": {"name": "heal"}
                }
            
            # Use teleport to escape if in danger
            if analysis["threats"]["danger_score"] > 8 and self_info["cooldowns"].get("teleport", 0) == 0 and self_info["mana"] >= 20:
                # Find safest position
                safest_pos = self.find_safest_position(state)
                if safest_pos:
                    return {
                        "move": [0, 0],
                        "spell": {
                            "name": "teleport",
                            "target": safest_pos
                        }
                    }
            
            # Look for artifacts to rebuild resources
            if analysis["opportunities"]["reachable_artifacts"]:
                artifact = analysis["opportunities"]["reachable_artifacts"][0]
                return {
                    "move": self.move_toward(self_pos, artifact["position"]),
                    "spell": None
                }
            
            # Fight from a distance - use fireball if effective
            if analysis["opportunities"]["can_fireball_opponent"] and not opponent_info.get("shield_active", False):
                return {
                    "move": [0, 0],
                    "spell": {
                        "name": "fireball",
                        "target": opp_pos
                    }
                }
                
            # Default defensive action - move away from opponent
            return {
                "move": self.move_away(self_pos, opp_pos),
                "spell": None
            }
        
        # Equal HP situation - balanced approach
        else:
            # Use tactical assessment for decision
            return self.tactical_action(state, analysis)

    def tactical_action(self, state, analysis):
        """
        Make a tactical decision based on current game state when no clear
        high-priority action exists.
        """
        self_info = state["self"]
        opponent_info = state["opponent"]
        self_pos = self_info["position"]
        opp_pos = opponent_info["position"]
        artifacts = state.get("artifacts", [])
        
        # Make decision based on state score and opportunities
        state_score = analysis["state_score"]
        
        # If we have a good position, take offensive action
        if state_score > 20:
            # Offensive tactics
            
            # Check if can use fireball effectively
            if analysis["opportunities"]["can_fireball_opponent"]:
                # Only use if opponent isn't shielded or we can hit multiple targets
                if not opponent_info.get("shield_active", False) or analysis["opportunities"]["fireball_splash_potential"]:
                    return {
                        "move": [0, 0],
                        "spell": {
                            "name": "fireball",
                            "target": opp_pos
                        }
                    }
            
            # Try to summon minion for pressure
            if analysis["opportunities"]["should_summon"]:
                return {
                    "move": [0, 0],
                    "spell": {"name": "summon"}
                }
            
            # Move toward opponent for pressure
            if analysis["distances"]["to_opponent"] > 5:
                # Try to blink closer
                can_blink = self_info["cooldowns"].get("blink", 0) == 0 and self_info["mana"] >= 10
                if can_blink:
                    move_dir = self.move_toward(self_pos, opp_pos)
                    blink_target = [
                        self_pos[0] + move_dir[0] * 2,
                        self_pos[1] + move_dir[1] * 2
                    ]
                    
                    # Ensure target is valid
                    blink_target[0] = max(0, min(9, blink_target[0]))
                    blink_target[1] = max(0, min(9, blink_target[1]))
                    
                    # Check if occupied
                    occupied = False
                    if blink_target == opp_pos:
                        occupied = True
                    
                    for m in state.get("minions", []):
                        if blink_target == m["position"]:
                            occupied = True
                            break
                    
                    if not occupied:
                        return {
                            "move": [0, 0],
                            "spell": {
                                "name": "blink",
                                "target": blink_target
                            }
                        }
                
                # Regular move toward opponent
                return {
                    "move": self.move_toward(self_pos, opp_pos),
                    "spell": None
                }
            
            # If none of the above conditions match, just move toward opponent
            return {
                "move": self.move_toward(self_pos, opp_pos),
                "spell": None
            }
        
        # If we're in a somewhat negative position, be more cautious
        elif state_score < -10:
            # Defensive tactics
            
            # Heal if needed and available
            if analysis["opportunities"]["should_heal"]:
                return {
                    "move": [0, 0],
                    "spell": {"name": "heal"}
                }
            
            # Shield if threatened
            if analysis["opportunities"]["should_shield"]:
                return {
                    "move": [0, 0],
                    "spell": {"name": "shield"}
                }
            
            # Collect artifact if possible
            if analysis["opportunities"]["reachable_artifacts"]:
                artifact = analysis["opportunities"]["reachable_artifacts"][0]
                return {
                    "move": self.move_toward(self_pos, artifact["position"]),
                    "spell": None
                }
            
            # Maintain distance from opponent if they're threatening
            if analysis["threats"]["danger_score"] > 5 and analysis["distances"]["to_opponent"] <= 3:
                # Move away from opponent
                away_move = self.move_away(self_pos, opp_pos)
                return {
                    "move": away_move,
                    "spell": None
                }
            
            # If none of the defensive conditions match, back away from opponent
            return {
                "move": self.move_away(self_pos, opp_pos),
                "spell": None
            }
        
        # Balanced position - focus on resource advantage
        else:
            # Try to collect artifact if nearby
            if analysis["opportunities"]["reachable_artifacts"]:
                artifact = analysis["opportunities"]["reachable_artifacts"][0]
                return {
                    "move": self.move_toward(self_pos, artifact["position"]),
                    "spell": None
                }
            
            # If next turn is artifact spawn turn, move toward center
            if (state["turn"] + 1) % 3 == 0:
                center_pos = [4, 4]
                return {
                    "move": self.move_toward(self_pos, center_pos),
                    "spell": None
                }
            
            # Maintain optimal combat distance (5 for fireball range)
            optimal_dist = 5
            current_dist = analysis["distances"]["to_opponent"]
            
            if abs(current_dist - optimal_dist) > 1:
                if current_dist < optimal_dist:
                    # Move away to optimal range
                    return {
                        "move": self.move_away(self_pos, opp_pos),
                        "spell": None
                    }
                else:
                    # Move closer to optimal range
                    return {
                        "move": self.move_toward(self_pos, opp_pos),
                        "spell": None
                    }
            
            # If already at good range, just hold position
            return {
                "move": [0, 0],
                "spell": None
            }

    def find_safest_position(self, state):
        """Find the safest position on the board to teleport to"""
        self_info = state["self"]
        opponent_info = state["opponent"]
        self_pos = self_info["position"]
        opp_pos = opponent_info["position"]
        minions = state.get("minions", [])
        artifacts = state.get("artifacts", [])
        
        best_pos = None
        best_score = float('-inf')
        
        for x in range(10):
            for y in range(10):
                pos = [x, y]
                # Skip occupied positions
                if pos == self_pos or pos == opp_pos:
                    continue
                
                occupied = False
                for m in minions:
                    if pos == m["position"]:
                        occupied = True
                        break
                
                if occupied:
                    continue
                
                # Calculate safety score
                dist_to_opponent = self.chebyshev_dist(pos, opp_pos)
                
                # Base score on distance from opponent
                score = dist_to_opponent * 2
                
                # Bonus for positions near health artifacts
                for a in artifacts:
                    if a.get("type") == "health":
                        artifact_dist = self.chebyshev_dist(pos, a["position"])
                        if artifact_dist <= 1:
                            score += 5
                    elif a.get("type") == "mana":
                        artifact_dist = self.chebyshev_dist(pos, a["position"])
                        if artifact_dist <= 1:
                            score += 3
                
                # Penalize being close to enemy minions
                for m in minions:
                    if m["owner"] != self_info["name"]:
                        minion_dist = self.chebyshev_dist(pos, m["position"])
                        if minion_dist <= 3:
                            score -= (4 - minion_dist) * 2
                
                # Penalize corner positions (less mobility)
                if (x in [0, 9] and y in [0, 9]):
                    score -= 3
                
                # Slightly favor center area for better mobility
                dist_to_center = max(abs(x - 4.5), abs(y - 4.5))
                score -= dist_to_center * 0.5
                
                if score > best_score:
                    best_score = score
                    best_pos = pos
        
        return best_pos

    def estimate_collision_risk(self, state):
        """
        Estimate the risk of collision with opponent based on
        observed movement patterns.
        """
        # Default risk if no patterns observed
        if not self._opponent_moves:
            return 0.3
        
        self_pos = state["self"]["position"]
        opp_pos = state["opponent"]["position"]
        
        # Calculate Manhattan distance
        distance = self.manhattan_dist(self_pos, opp_pos)
        
        # If not close, no collision risk
        if distance > 2:
            return 0.0
        
        # If adjacent, higher collision risk
        if distance == 1:
            return 0.7
        
        # Check recent movement patterns
        # If opponent consistently moves in our direction, higher risk
        if len(self._opponent_moves) >= 3:
            # Get last three moves
            last_moves = self._opponent_moves[-3:]
            
            # Check if moves are consistent
            moves_toward_us = 0
            for move in last_moves:
                # Calculate relative direction to us
                rel_x = 1 if self_pos[0] > opp_pos[0] else -1 if self_pos[0] < opp_pos[0] else 0
                rel_y = 1 if self_pos[1] > opp_pos[1] else -1 if self_pos[1] < opp_pos[1] else 0
                
                # Check if move was in our direction
                if (move[0] == rel_x or move[1] == rel_y):
                    moves_toward_us += 1
            
            # If majority of moves are toward us, higher risk
            if moves_toward_us >= 2:
                return 0.8
        
        # Default moderate risk
        return 0.4

    def predict_opponent_next_move(self, state):
        """Predict opponent's next move based on patterns"""
        if not self._opponent_moves:
            return None
        
        # If only one pattern observed, assume it may repeat
        if len(self._opponent_moves) == 1:
            return self._opponent_moves[0]
        
        # Check for repeating pattern over last 4 moves
        if len(self._opponent_moves) >= 4:
            last_two = self._opponent_moves[-2:]
            prev_two = self._opponent_moves[-4:-2]
            
            if last_two == prev_two:
                return last_two[0]  # Return first move of pattern
        
        # Calculate most common move direction
        move_counts = {}
        for move in self._opponent_moves:
            move_tuple = (move[0], move[1])
            move_counts[move_tuple] = move_counts.get(move_tuple, 0) + 1
        
        most_common = max(move_counts.items(), key=lambda x: x[1])
        return list(most_common[0])

    # Utility functions
    def manhattan_dist(self, a, b):
        """Calculate Manhattan distance between two points"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def chebyshev_dist(self, a, b):
        """Calculate Chebyshev distance (maximum of |dx| and |dy|)"""
        return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
    
    def move_toward(self, start, target):
        """Calculate movement vector toward target"""
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        
        # Normalize to -1, 0, or 1
        step_x = 1 if dx > 0 else -1 if dx < 0 else 0
        step_y = 1 if dy > 0 else -1 if dy < 0 else 0
        
        return [step_x, step_y]
    
    def move_away(self, start, target):
        """Calculate movement vector away from target"""
        toward = self.move_toward(start, target)
        # Negate the direction
        return [-toward[0], -toward[1]]
    
    def is_valid_position(self, pos, state):
        """Check if a position is valid (within bounds and not occupied)"""
        if pos[0] < 0 or pos[0] >= 10 or pos[1] < 0 or pos[1] >= 10:
            return False
        
        # Check if occupied by wizard
        if pos == state["self"]["position"] or pos == state["opponent"]["position"]:
            return False
        
        # Check if occupied by minion
        for m in state.get("minions", []):
            if pos == m["position"]:
                return False
        
        return True
    
    def get_valid_moves(self, pos, state):
        """Get all valid moves from a position"""
        valid_moves = []
        
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                
                new_pos = [pos[0] + dx, pos[1] + dy]
                if self.is_valid_position(new_pos, state):
                    valid_moves.append([dx, dy])
        
        return valid_moves