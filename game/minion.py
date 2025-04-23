class Minion:
    def __init__(self, owner, position):
        self.owner = owner  # Wizard.name
        self.hp = 30
        self.position = position

    def to_dict(self):
        return {
            "owner": self.owner,
            "hp": self.hp,
            "position": self.position
        }

    def is_alive(self):
        return self.hp > 0

    def to_dict(self):
        return {
            "owner": self.owner,
            "hp": self.hp,
            "position": self.position
        }
