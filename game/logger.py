import copy

from game.wizard import Wizard


EVENT_TURN_START = "turn_start"
EVENT_SPELL_CAST = "spell_cast"
EVENT_DAMAGE = "damage"
EVENT_WIZARD_MOVE = "wizard_move"
EVENT_MINION_MOVE = "minion_move"
EVENT_COLLISION = "collision"
EVENT_SHIELD_DOWN = "shield_down"
EVENT_ARTIFACT_SPAWN= "artifact_spawn"
EVENT_ARTIFACT_PICK_UP = "artifact_pick_up"

class GameLogger:
    def __init__(self):
        self.turn_logs = []
        self.events = []  # 📝 new: list of events
        self.current_turn = []
        self.snapshots = []   # 💾 new: full board state per turn
        self.spells = []
        self.damage_events = []
        self.collision_events = []
        self.state_index=0

    def new_turn(self, turn_num):
        if self.current_turn:
            self.turn_logs.append(self.current_turn)
        self.current_turn = [f"--- Turn {turn_num} ---"]

    def log(self, message):
        self.current_turn.append(message)

    def log_state(self, state_dict):
        state_dict_copy = copy.deepcopy(state_dict)
        state_dict_copy["state_index"] = self.state_index
        self.snapshots.append(state_dict_copy)
        self.state_index += 1

    def finalize(self):
        if self.current_turn:
            self.turn_logs.append(self.current_turn)

    def print_log(self):
        for turn in self.turn_logs:
            for line in turn:
                print(line)

    def get_log(self):
        return self.turn_logs

    def get_snapshots(self):
        return self.snapshots

    def save_to_file(self, filename="game_log.txt"):
        with open(filename, "w") as f:
            for turn in self.turn_logs:
                for line in turn:
                    f.write(line + "\n")

    def log_spell(self, caster, spell_name, target=None, hit=None):
        self.spells.append({
            "turn": self.current_turn,
            "state_index": self.state_index,
            "caster": caster.name,
            "spell": spell_name,
            "target": target,
            "hit": hit
        })

    def log_damage(self, position, amount, target_name, cause=None):
        self.damage_events.append({
            "turn": self.current_turn,
            "state_index": self.state_index,
            "position": position,
            "amount": amount,
            "target": target_name,
            "cause": cause
        })

    def log_collision(self, position):
        self.collision_events.append({
            "turn": self.current_turn,
            "position": position
        })


    # EVENT LOGS
    
    def _log_event(self, event_data):
        """Print event data to console for debugging"""
        # print(f"Turn {event_data['turn']} | EVENT: {event_data['event']} | {event_data['details']}")

    def log_event_turn_start(self, turn):
        event_data = {
            "turn": turn,
            "event": EVENT_TURN_START,
            "details": {}
        }
        self.events.append(event_data)
        self._log_event(event_data)

    def log_event_spell(self, turn, caster, spell_name, target):
        event_data = {
            "turn": turn,
            "event": EVENT_SPELL_CAST,
            "details": {
                "caster": caster,
                "spell": spell_name,
                "target": target
            }
        }
        self.events.append(event_data)
        self._log_event(event_data)

    def log_event_wizard_damage(self, turn, amount, name, remaining_hp=None):
        event_data = {
            "turn": turn,
            "event": EVENT_DAMAGE,
            "details": {
                "entity": "wizard",
                "amount": amount,
                "name": name,
                "remaining_hp": remaining_hp
            }
        }
        self.events.append(event_data)
        self._log_event(event_data)

    def log_event_minion_damage(self, turn, position, amount, minion_id, remaining_hp=None):
        event_data = {
            "turn": turn,
            "event": EVENT_DAMAGE,
            "details": {
                "entity": "minion",
                "position": position,
                "amount": amount,
                "minion_id": minion_id,
                "remaining_hp": remaining_hp
            }
        }
        self.events.append(event_data)
        self._log_event(event_data)

    def log_event_wizard_move(self, turn, wiz1: Wizard, wiz1_new_position, wiz2: Wizard, wiz2_new_position):
        # Only track wizards that actually move
        details = {}
        
        if wiz1.position != wiz1_new_position:
            details["wizard1"] = {
                "name": wiz1.name,
                "move": str(wiz1.position) + '->' + str(wiz1_new_position)
            }
            
        if wiz2.position != wiz2_new_position:
            details["wizard2"] = {
                "name": wiz2.name,
                "move": str(wiz2.position) + '->' + str(wiz2_new_position)
            }
            
        # Only log the event if at least one wizard moved
        if details:
            event_data = {
                "turn": turn,
                "event": EVENT_WIZARD_MOVE,
                "details": details
            }
            self.events.append(event_data)
            self._log_event(event_data)

    def log_event_minion_move(self, turn, minion_id, start_position, new_position):
        event_data = {
            "turn": turn,
            "event": EVENT_MINION_MOVE,
            "details": {
                "minion_id": minion_id,
                "move": str(start_position) + '->' + str(new_position)
            }
        }
        self.events.append(event_data)
        self._log_event(event_data)

    def log_event_collision(self, turn, position, entity1, entity1_bounce_position, entity2, entity2_bounce_position):
        event_data = {
            "turn": turn,
            "event": EVENT_COLLISION,
            "details": {
                "position": position,
                "entity1_type": "wizard" if hasattr(entity1, "name") else "minion",
                "entity1": entity1.name if hasattr(entity1, "name") else entity1.id,
                "entity1_bounce_position": entity1_bounce_position,
                "entity2_type": "wizard" if hasattr(entity2, "name") else "minion",
                "entity2": entity2.name if hasattr(entity2, "name") else entity2.id,
                "entity2_bounce_position": entity2_bounce_position
            }
        }
        self.events.append(event_data)
        self._log_event(event_data)

    def log_event_shield_down(self, turn, wizard_name):
        event_data = {
            "turn": turn,
            "event": EVENT_SHIELD_DOWN,
            "details": {
                "wizard": wizard_name
            }
        }
        self.events.append(event_data)
        self._log_event(event_data)

    def log_event_spawn_artifact(self, turn, artifact):
        event_data = {
            "turn": turn,
            "event": EVENT_ARTIFACT_SPAWN,
            "details": {
                "type": artifact["type"],
                "position": artifact["position"]
            }
        }
        self.events.append(event_data)
        self._log_event(event_data)

    def log_event_artifact_pick_up(self, turn, wizard_name, artifact):
        event_data = {
            "turn": turn,
            "event": EVENT_ARTIFACT_PICK_UP,
            "details": {
                "wizard": wizard_name,
                "artifact_type": artifact["type"],
                "artifact_position": artifact["position"]
            }
        }
        self.events.append(event_data)
        self._log_event(event_data)

    def get_event_logs(self):
        return self.events
