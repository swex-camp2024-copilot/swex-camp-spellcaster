import random
from game.rules import BOARD_SIZE

class ArtifactManager:
    def __init__(self):
        self.artifacts = []  # List of dicts with position and type

    def spawn_random(self):
        x, y = random.randint(0, BOARD_SIZE-1), random.randint(0, BOARD_SIZE-1)
        artifact_type = random.choice(["health", "mana", "cooldown"])
        self.artifacts.append({"type": artifact_type, "position": [x, y]})

    def check_pickup(self, wizard):
        for artifact in self.artifacts:
            if artifact["position"] == wizard.position:
                self.apply_effect(wizard, artifact["type"])
                self.artifacts.remove(artifact)
                break

    def apply_effect(self, wizard, kind):
        if kind == "health":
            wizard.hp = min(100, wizard.hp + 20)
        elif kind == "mana":
            wizard.mana = min(100, wizard.mana + 30)
        elif kind == "cooldown":
            for spell in wizard.cooldowns:
                if wizard.cooldowns[spell] > 0:
                    wizard.cooldowns[spell] -= 1

    def active_artifacts(self):
        return self.artifacts
