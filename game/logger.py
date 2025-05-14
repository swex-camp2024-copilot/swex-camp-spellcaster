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

    def log_damage(self, position, amount, target_name):
        self.damage_events.append({
            "turn": self.current_turn,
            "state_index": self.state_index,
            "position": position,
            "amount": amount,
            "target": target_name
        })

    def log_collision(self, position):
        self.collision_events.append({
            "turn": self.current_turn,
            "position": position
        })


    # EVENT LOGS

    def log_event_turn_start(self, turn):
        self.events.append({
            "turn": turn,
            "event": EVENT_TURN_START,
            "details": {}
        })

    def log_event_spell(self, turn, caster, spell_name, target):
        self.events.append({
            "turn": turn,
            "event": EVENT_SPELL_CAST,
            "details": {
                "caster": caster,
                "spell": spell_name,
                "target": target
            }
        })

    def log_event_wizard_damage(self, turn, position, amount, name):
        self.events.append({
            "turn": turn,
            "event": EVENT_DAMAGE,
            "details": {
                "entity": "wizard",
                "position": position,
                "amount": amount,
                "name": name
            }
        })

    def log_event_minion_damage(self, turn, position, amount, minion_id):
        self.events.append({
            "turn": turn,
            "event": EVENT_DAMAGE,
            "details": {
                "entity": "minion",
                "position": position,
                "amount": amount,
                "minion_id": minion_id
            }
        })

    def log_event_wizard_move(self, turn, wiz1: Wizard, wiz1_new_position, wiz2: Wizard, wiz2_new_position):
        self.events.append({
            "turn": turn,
            "event": EVENT_WIZARD_MOVE,
            "details": {
                "wizard1": {
                    "name": wiz1.name,
                    "start_position": wiz1.position,
                    "new_position": wiz1_new_position
                },
                "wizard2": {
                    "name": wiz2.name,
                    "start_position": wiz2.position,
                    "new_position": wiz2_new_position
                }
            }
        })

    def log_event_minion_move(self, turn, minion_id, start_position, new_position):
        self.events.append({
            "turn": turn,
            "event": EVENT_MINION_MOVE,
            "details": {
                "minion_id": minion_id,
                "start_position": start_position,
                "new_position": new_position
            }
        })

    def log_event_collision(self, turn, position, entity1, entity1_bounce_position, entity2, entity2_bounce_position):
        self.events.append({
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
        })

    def log_event_shield_down(self, turn, wizard_name):
        self.events.append({
            "turn": turn,
            "event": EVENT_SHIELD_DOWN,
            "details": {
                "wizard": wizard_name
            }
        })

    def log_event_spawn_artifact(self, turn, artifact):
        self.events.append({
            "turn": turn,
            "event": EVENT_ARTIFACT_SPAWN,
            "details": {
                "type": artifact["spawn"],
                "position": artifact["position"]
            }
        })

    def log_event_artifact_pick_up(self, turn, wizard_name, artifact):
        self.events.append({
            "turn": turn,
            "event": EVENT_ARTIFACT_PICK_UP,
            "details": {
                "wizard": wizard_name,
                "artifact_type": artifact["type"],
                "artifact_position": artifact["position"]
            }
        })

    def get_event_logs(self):
        return self.events
