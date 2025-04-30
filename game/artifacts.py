import random
from game.rules import BOARD_SIZE

class ArtifactManager:
    def __init__(self):
        self.artifacts = []  # List of dicts with position and type

    def spawn_random(self, occupied_positions=[], turn=0):
        """
        Spawn a random artifact at a position that is not already occupied.
        Will not spawn artifacts if there are more than 10 occupied positions.

        Args:
            occupied_positions: List of positions that are already occupied

        Returns:
            bool: True if artifact was spawned, False otherwise
        """
        # Convert occupied positions to a set of tuples for faster lookup
        occupied = {tuple(pos) for pos in occupied_positions}

        # Add existing artifact positions
        for artifact in self.artifacts:
            occupied.add(tuple(artifact["position"]))

        # Check if there are more than 10 occupied positions
        if len(occupied) > 10:
            return False

        # Generate all possible positions
        all_positions = [(x, y) for x in range(BOARD_SIZE) for y in range(BOARD_SIZE)]

        # Filter out occupied positions
        free_positions = [pos for pos in all_positions if pos not in occupied]

        if not free_positions:
            return False

        # Choose a random free position
        x, y = random.choice(free_positions)

        artifact_type = random.choice(["health", "mana", "cooldown"])
        self.artifacts.append({
            "type": artifact_type,
            "position": [x, y],
            "spawn_turn": turn
        })
        return True

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
