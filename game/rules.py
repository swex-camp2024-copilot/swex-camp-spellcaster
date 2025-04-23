BOARD_SIZE = 10
MAX_HP = 100
MAX_MANA = 100
MANA_REGEN = 10
ARTIFACT_SPAWN_RATE = 3  # every X turns

SPELLS = {
    "fireball": {"cost": 30, "cooldown": 2, "damage": 20, "range": 3},
    "shield": {"cost": 20, "cooldown": 3, "block": 20},
    "teleport": {"cost": 40, "cooldown": 4},
    "summon": {"cost": 50, "cooldown": 5},
    "heal": {"cost": 25, "cooldown": 3, "heal": 20},
    "blink": {"cost": 15, "cooldown": 2, "distance": 2},
}