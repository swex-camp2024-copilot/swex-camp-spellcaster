import copy

class GameLogger:
    def __init__(self):
        self.turn_logs = []
        self.current_turn = []
        self.snapshots = []   # 💾 new: full board state per turn
        self.spells = []
        self.damage_events = []

    def new_turn(self, turn_num):
        if self.current_turn:
            self.turn_logs.append(self.current_turn)
        self.current_turn = [f"--- Turn {turn_num} ---"]

    def log(self, message):
        self.current_turn.append(message)

    def log_state(self, state_dict):
        self.snapshots.append(copy.deepcopy(state_dict))

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
            "turn": len(self.snapshots),
            "caster": caster.name,
            "spell": spell_name,
            "target": target,
            "hit": hit
        })

    def log_damage(self, position, amount, target_name):
        self.damage_events.append({
            "turn": len(self.snapshots),
            "position": position,
            "amount": amount,
            "target": target_name
        })
