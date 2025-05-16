import random
import os
from bots.bot_interface import BotInterface
from bots.vezr.openai_integration import create_openai_prompt, call_openai_api


class Vezr(BotInterface):
    def __init__(self):
        self._name = "Gandalf the Gray"
        self._sprite_path = "assets/wizards/sample_bot1.png"  # Using sample bot sprite for now
        self._minion_sprite_path = "assets/minions/minion_1.png"  # Using sample minion sprite for now
        
        # Initialize a backup strategy flag in case the API call fails
        self.use_backup_strategy = False
        
        # Check if API key is available, if not, we'll use backup strategy
        if not os.environ.get("OPENAI_API_KEY"):
            print("Warning: OPENAI_API_KEY environment variable is not set")
            print("Gandalf the Gray will use backup strategy instead of OpenAI API")
            self.use_backup_strategy = True

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
        """
        Main decision logic for the Gandalf the Gray bot.
        Uses OpenAI API to determine the best move and spell based on the current game state.
        Falls back to a basic strategy if API call fails or no API key is provided.
        """
        # If we're configured to use the backup strategy or if an API call fails
        if self.use_backup_strategy:
            return self.backup_strategy(state)
        
        try:
            # Create the prompt for the OpenAI API
            prompt = create_openai_prompt(state, self._name)
            
            # Call the OpenAI API with the prompt
            decision = call_openai_api(prompt)
            
            return decision
            
        except Exception as e:
            print(f"Error using OpenAI API: {e}")
            print("Falling back to backup strategy")
            self.use_backup_strategy = True  # Use backup for future turns too
            return self.backup_strategy(state)
    
    def backup_strategy(self, state):
        """
        Basic backup strategy in case the OpenAI API call fails or no API key is provided.
        This implements a simple but effective strategy based on game state.
        """
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
        enemies.append(opp_data)  # Add opponent to potential targets
        
        adjacent_enemies = [e for e in enemies if manhattan_dist(self_pos, e["position"]) == 1]
        if adjacent_enemies and cooldowns["melee_attack"] == 0:
            # Pick the enemy with lowest HP
            target = min(adjacent_enemies, key=lambda e: e["hp"])
            spell = {
                "name": "melee_attack",
                "target": target["position"]
            }
            
        # 1. FIREBALL if in range
        if cooldowns["fireball"] == 0 and mana >= 30 and dist(self_pos, opp_pos) <= 5:
            spell = {
                "name": "fireball",
                "target": opp_pos
            }
            
        # 2. Use SHIELD if low HP
        elif hp <= 40 and cooldowns["shield"] == 0 and mana >= 20:
            spell = { "name": "shield" }
            
        # 3. HEAL if available and HP isn't full
        elif hp <= 80 and cooldowns["heal"] == 0 and mana >= 25:
            spell = { "name": "heal" }
            
        # 4. SUMMON minion if none exists
        elif cooldowns["summon"] == 0 and mana >= 50:
            has_minion = any(m["owner"] == self_data["name"] for m in minions)
            if not has_minion:
                spell = { "name": "summon" }
                
        # 5. TELEPORT onto artifact if low mana/hp
        if not spell and cooldowns["teleport"] == 0 and mana >= 40 and artifacts:
            critical = mana <= 40 or hp <= 60
            if critical:
                # find closest artifact
                nearest = min(artifacts, key=lambda a: dist(self_pos, a["position"]))
                spell = {
                    "name": "teleport",
                    "target": nearest["position"]
                }
                
        # 6. Move toward closest artifact if we need something
        if not spell and artifacts and (mana <= 60 or hp <= 60):
            nearest = min(artifacts, key=lambda a: dist(self_pos, a["position"]))
            move = self.move_toward(self_pos, nearest["position"])
            
        # 7. If nothing else, close the gap toward opponent
        elif not spell:
            move = self.move_toward(self_pos, opp_pos)
            
        return {
            "move": move,
            "spell": spell
        }
        
    def move_toward(self, start, target):
        """Helper function to determine the optimal move direction toward a target."""
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        step_x = 1 if dx > 0 else -1 if dx < 0 else 0
        step_y = 1 if dy > 0 else -1 if dy < 0 else 0
        return [step_x, step_y]
