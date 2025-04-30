class Minion:
    _id_counter = 0

    def __init__(self, owner, position):
        Minion._id_counter += 1
        self.id = f"{owner}-{Minion._id_counter}"
        self.owner = owner  # Wizard.name
        self.hp = 30
        self.position = position
        self._is_ready = False

    def to_dict(self):
        return {
            "id": self.id,
            "owner": self.owner,
            "hp": self.hp,
            "position": self.position
        }

    def is_alive(self):
        return self.hp > 0

    def is_ready(self):
        return self._is_ready

    def make_ready(self):
        self._is_ready = True
