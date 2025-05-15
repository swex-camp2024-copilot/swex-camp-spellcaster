import random
from enum import Enum
from typing import List, Dict, Any, Tuple
from bots.bot_interface import BotInterface

class CombatState(Enum):
    AGGRESSIVE = "aggressive"    # High HP, good position - attack!
    DEFENSIVE = "defensive"      # Low HP or threatened - protect and heal
    GATHERING = "gathering"      # Low resources - get artifacts
    CONTROLLING = "controlling"  # Control space with minions and spells

class TacticalBot(BotInterface):
    def __init__(self):
        self._name = "Tactical Bot"
        self._sprite_path = "assets/wizards/tactical_bot.png"
        self._minion_sprite_path = "assets/minions/tactical_minion.png"
        
        # State machine settings
        self.state = CombatState.AGGRESSIVE
        self.state_memory = {}  # Remember important info between turns
        
        # Tactical thresholds
        self.LOW_HP = 40
        self.LOW_MANA = 30
        self.CRITICAL_HP = 25
        self.SAFE_DISTANCE = 3
        self.FIREBALL_RANGE = 4
        
    @property
    def name(self):
        return self._name

    @property
    def sprite_path(self):
        return self._sprite_path

    @property
    def minion_sprite_path(self):
        return self._minion_sprite_path

    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Extract state information
        self_data = state["self"]
        opp_data = state["opponent"]
        artifacts = state.get("artifacts", [])
        minions = state.get("minions", [])
        
        # Update state machine
        self.update_combat_state(self_data, opp_data, artifacts, minions)
        
        # Get action based on current state
        move, spell = self.get_state_action(state)
        
        return {
            "move": move,
            "spell": spell
        }
    
    def update_combat_state(self, self_data: Dict[str, Any], opp_data: Dict[str, Any], 
                          artifacts: List[Dict[str, Any]], minions: List[Dict[str, Any]]) -> None:
        """Update the bot's combat state based on game conditions."""
        hp = self_data["hp"]
        mana = self_data["mana"]
        
        # Check if we're threatened
        is_threatened = self.evaluate_threat(self_data, opp_data, minions)
        
        # Determine new state
        if hp <= self.CRITICAL_HP or (is_threatened and hp <= self.LOW_HP):
            self.state = CombatState.DEFENSIVE
        elif mana <= self.LOW_MANA or (hp <= self.LOW_HP and artifacts):
            self.state = CombatState.GATHERING
        elif len([m for m in minions if m["owner"] == self_data["name"]]) > 0:
            self.state = CombatState.CONTROLLING
        else:
            self.state = CombatState.AGGRESSIVE
    
    def evaluate_threat(self, self_data: Dict[str, Any], opp_data: Dict[str, Any], 
                       minions: List[Dict[str, Any]]) -> bool:
        """Evaluate if we're in a threatening situation."""
        self_pos = self_data["position"]
        opp_pos = opp_data["position"]
        
        # Check distance to opponent
        if self.chebyshev_dist(self_pos, opp_pos) <= 2:
            return True
            
        # Check enemy minions
        enemy_minions = [m for m in minions if m["owner"] != self_data["name"]]
        for minion in enemy_minions:
            if self.manhattan_dist(self_pos, minion["position"]) <= 2:
                return True
                
        return False
    
    def get_state_action(self, state: Dict[str, Any]) -> Tuple[List[int], Dict[str, Any]]:
        """Get appropriate action based on current state."""
        if self.state == CombatState.AGGRESSIVE:
            return self.get_aggressive_action(state)
        elif self.state == CombatState.DEFENSIVE:
            return self.get_defensive_action(state)
        elif self.state == CombatState.GATHERING:
            return self.get_gathering_action(state)
        else:  # CONTROLLING
            return self.get_controlling_action(state)
    
    def get_aggressive_action(self, state: Dict[str, Any]) -> Tuple[List[int], Dict[str, Any]]:
        """Get action for aggressive state - focus on dealing damage."""
        self_data = state["self"]
        opp_data = state["opponent"]
        minions = state.get("minions", [])
        
        self_pos = self_data["position"]
        opp_pos = opp_data["position"]
        cooldowns = self_data["cooldowns"]
        mana = self_data["mana"]
        
        spell = None
        move = [0, 0]
        
        # Try to use fireball if in range
        if cooldowns["fireball"] == 0 and mana >= 30:
            dist = self.chebyshev_dist(self_pos, opp_pos)
            if dist <= self.FIREBALL_RANGE:
                return self.move_toward(self_pos, opp_pos), {
                    "name": "fireball",
                    "target": opp_pos
                }
        
        # Try melee attack if adjacent
        enemies = [e for e in minions if e["owner"] != self_data["name"]]
        enemies.append(opp_data)
        adjacent_enemies = [e for e in enemies if self.manhattan_dist(self_pos, e["position"]) == 1]
        
        if adjacent_enemies and cooldowns["melee_attack"] == 0:
            target = min(adjacent_enemies, key=lambda e: e["hp"])
            return [0, 0], {
                "name": "melee_attack",
                "target": target["position"]
            }
        
        # Summon minion if none exists
        if cooldowns["summon"] == 0 and mana >= 50:
            has_minion = any(m["owner"] == self_data["name"] for m in minions)
            if not has_minion:
                return [0, 0], {"name": "summon"}
        
        # Move toward opponent while maintaining ideal range for fireball
        ideal_dist = self.FIREBALL_RANGE - 1
        current_dist = self.chebyshev_dist(self_pos, opp_pos)
        
        if current_dist > ideal_dist:
            move = self.move_toward(self_pos, opp_pos)
        elif current_dist < ideal_dist:
            move = self.move_away(self_pos, opp_pos)
            
        return move, spell
    
    def get_defensive_action(self, state: Dict[str, Any]) -> Tuple[List[int], Dict[str, Any]]:
        """Get action for defensive state - focus on survival."""
        self_data = state["self"]
        opp_data = state["opponent"]
        artifacts = state.get("artifacts", [])
        
        self_pos = self_data["position"]
        opp_pos = opp_data["position"]
        cooldowns = self_data["cooldowns"]
        mana = self_data["mana"]
        hp = self_data["hp"]
        
        # Try to shield if available
        if cooldowns["shield"] == 0 and mana >= 20:
            return [0, 0], {"name": "shield"}
            
        # Try to heal if low HP
        if hp <= self.LOW_HP and cooldowns["heal"] == 0 and mana >= 25:
            return [0, 0], {"name": "heal"}
            
        # Try to teleport to safety if in danger
        if cooldowns["teleport"] == 0 and mana >= 40:
            safe_pos = self.find_safe_position(state)
            if safe_pos:
                return [0, 0], {
                    "name": "teleport",
                    "target": safe_pos
                }
        
        # Move away from opponent
        return self.move_away(self_pos, opp_pos), None
    
    def get_gathering_action(self, state: Dict[str, Any]) -> Tuple[List[int], Dict[str, Any]]:
        """Get action for gathering state - focus on collecting artifacts."""
        self_data = state["self"]
        artifacts = state.get("artifacts", [])
        
        if not artifacts:
            return self.get_defensive_action(state)
            
        self_pos = self_data["position"]
        cooldowns = self_data["cooldowns"]
        mana = self_data["mana"]
        
        # Find nearest artifact
        nearest = min(artifacts, key=lambda a: self.manhattan_dist(self_pos, a["position"]))
        
        # Try to teleport if it's far and we have mana
        if cooldowns["teleport"] == 0 and mana >= 40:
            dist = self.manhattan_dist(self_pos, nearest["position"])
            if dist > 3:
                return [0, 0], {
                    "name": "teleport",
                    "target": nearest["position"]
                }
        
        # Otherwise move toward it
        return self.move_toward(self_pos, nearest["position"]), None
    
    def get_controlling_action(self, state: Dict[str, Any]) -> Tuple[List[int], Dict[str, Any]]:
        """Get action for controlling state - focus on space control with minions."""
        self_data = state["self"]
        opp_data = state["opponent"]
        minions = state.get("minions", [])
        
        self_pos = self_data["position"]
        opp_pos = opp_data["position"]
        cooldowns = self_data["cooldowns"]
        mana = self_data["mana"]
        
        # Try to maintain distance while letting minions do work
        ideal_dist = self.SAFE_DISTANCE
        current_dist = self.chebyshev_dist(self_pos, opp_pos)
        
        # Use fireball if opponent is near our minions
        if cooldowns["fireball"] == 0 and mana >= 30:
            friendly_minions = [m for m in minions if m["owner"] == self_data["name"]]
            for minion in friendly_minions:
                if self.manhattan_dist(minion["position"], opp_pos) <= 2:
                    return [0, 0], {
                        "name": "fireball",
                        "target": opp_pos
                    }
        
        # Move to maintain ideal distance
        if current_dist < ideal_dist:
            return self.move_away(self_pos, opp_pos), None
        elif current_dist > ideal_dist + 1:
            return self.move_toward(self_pos, opp_pos), None
            
        return [0, 0], None
    
    def find_safe_position(self, state: Dict[str, Any]) -> List[int]:
        """Find a safe position to teleport to."""
        self_data = state["self"]
        opp_data = state["opponent"]
        board_size = state["board_size"]
        
        self_pos = self_data["position"]
        opp_pos = opp_data["position"]
        
        # Try corners first
        corners = [[0, 0], [0, board_size-1], [board_size-1, 0], [board_size-1, board_size-1]]
        safe_corners = [c for c in corners if self.manhattan_dist(c, opp_pos) > self.SAFE_DISTANCE]
        
        if safe_corners:
            return min(safe_corners, key=lambda c: self.manhattan_dist(c, self_pos))
        
        # Try edges if no safe corners
        candidates = []
        for x in range(board_size):
            candidates.extend([[x, 0], [x, board_size-1]])
        for y in range(board_size):
            candidates.extend([[0, y], [board_size-1, y]])
            
        safe_spots = [c for c in candidates if self.manhattan_dist(c, opp_pos) > self.SAFE_DISTANCE]
        
        if safe_spots:
            return min(safe_spots, key=lambda c: self.manhattan_dist(c, self_pos))
            
        return None
    
    def move_toward(self, start: List[int], target: List[int]) -> List[int]:
        """Get movement vector toward target."""
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        return [
            1 if dx > 0 else -1 if dx < 0 else 0,
            1 if dy > 0 else -1 if dy < 0 else 0
        ]
    
    def move_away(self, start: List[int], target: List[int]) -> List[int]:
        """Get movement vector away from target."""
        toward = self.move_toward(start, target)
        return [-toward[0], -toward[1]]
    
    @staticmethod
    def manhattan_dist(a: List[int], b: List[int]) -> int:
        """Calculate Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    @staticmethod
    def chebyshev_dist(a: List[int], b: List[int]) -> int:
        """Calculate Chebyshev distance between two points."""
        return max(abs(a[0] - b[0]), abs(a[1] - b[1])) 