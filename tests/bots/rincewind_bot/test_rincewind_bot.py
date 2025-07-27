import unittest
from unittest.mock import patch
import sys
import os
import random
import math

# Add the project root to Python path to allow importing the bot
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

print("Starting Rincewind Bot tests...")
print(f"Python path: {sys.path}")

from bots.rincewind_bot.rincewind_bot import RincewindBot
print("Successfully imported RincewindBot")


class TestRincewindBot(unittest.TestCase):
    """Test cases for the Rincewind Bot (formerly Red Wizard Bot)."""

    def setUp(self):
        """Set up a new bot instance for each test."""
        self.bot = RincewindBot()

    def test_initialization(self):
        """Test the bot is initialized with the correct name and sprite paths."""
        self.assertEqual(self.bot.name, "Rincewind Bot")
        self.assertEqual(self.bot.sprite_path, "assets/wizards/rincewind.png")
        self.assertEqual(self.bot.minion_sprite_path, "assets/minions/green_minion.png")
        self.assertEqual(self.bot.previous_positions, [])
        self.assertFalse(self.bot.retreat_mode)
        self.assertEqual(self.bot.consecutive_same_position, 0)

    def test_basic_movement_toward_opponent(self):
        """Test basic movement toward opponent when health is good."""
        state = {
            "self": {
                "position": [2, 2],
                "hp": 80,
                "mana": 50,
                "cooldowns": {"fireball": 0, "shield": 0, "heal": 0, 
                             "teleport": 0, "blink": 0, "summon": 0, "melee_attack": 0},
                "shield_active": False,
                "name": "Rincewind Bot"
            },
            "opponent": {
                "position": [5, 5],
                "hp": 70,
                "name": "Enemy Bot"
            },
            "artifacts": [],
            "minions": [
                {
                    "position": [1, 1],  # Not adjacent to bot
                    "owner": "Rincewind Bot",
                    "hp": 10  # Lower HP than opponent
                }
            ],
            "board_size": 10,
            "turn": 1
        }

        decision = self.bot.decide(state)

        # Bot should move toward opponent (positive in both x and y)
        self.assertEqual(decision["move"], [1, 1])

        # Bot will use fireball against opponent if it has enough mana
        # This is the actual behavior of the bot
        self.assertEqual(decision["spell"]["name"], "fireball")

    def test_emergency_healing(self):
        """Test emergency healing when HP is low."""
        state = {
            "self": {
                "position": [2, 2],
                "hp": 20,  # Low HP
                "mana": 50,
                "cooldowns": {"fireball": 0, "shield": 0, "heal": 0, 
                             "teleport": 0, "blink": 0, "summon": 0, "melee_attack": 0},
                "shield_active": False,
                "name": "Rincewind Bot"
            },
            "opponent": {
                "position": [5, 5],
                "hp": 70,
                "name": "Enemy Bot"
            },
            "artifacts": [],
            "minions": [],
            "board_size": 10,
            "turn": 1
        }

        decision = self.bot.decide(state)

        # Bot should cast heal
        self.assertEqual(decision["spell"]["name"], "heal")
        # The bot should enter retreat mode
        self.assertTrue(self.bot.retreat_mode)

    def test_attack_adjacent_enemy_minion(self):
        """Test that the bot prioritizes attacking adjacent enemy minions."""
        state = {
            "self": {
                "position": [2, 2],
                "hp": 80,
                "mana": 10,
                "cooldowns": {"fireball": 0, "shield": 0, "heal": 0, 
                             "teleport": 0, "blink": 0, "summon": 0, "melee_attack": 0},
                "shield_active": False,
                "name": "Rincewind Bot"
            },
            "opponent": {
                "position": [5, 5],  # Far away
                "hp": 70,
                "name": "Enemy Bot"
            },
            "artifacts": [],
            "minions": [
                {
                    "position": [2, 3],  # Adjacent to bot
                    "owner": "Enemy Bot",
                    "hp": 20
                }
            ],
            "board_size": 10,
            "turn": 1
        }

        decision = self.bot.decide(state)

        # Bot should attack the adjacent minion
        self.assertEqual(decision["spell"]["name"], "melee_attack")
        self.assertEqual(decision["spell"]["target"], [2, 3])

    def test_prioritize_minion_over_opponent(self):
        """Test that bot prioritizes attacking minion when both minion and opponent are adjacent."""
        state = {
            "self": {
                "position": [2, 2],
                "hp": 80,
                "mana": 50,
                "cooldowns": {"fireball": 0, "shield": 0, "heal": 0, 
                             "teleport": 0, "blink": 0, "summon": 0, "melee_attack": 0},
                "shield_active": True,
                "name": "Rincewind Bot"
            },
            "opponent": {
                "position": [2, 3],  # Adjacent to bot
                "hp": 70,
                "name": "Enemy Bot"
            },
            "artifacts": [],
            "minions": [
                {
                    "position": [3, 2],  # Also adjacent to bot
                    "owner": "Enemy Bot",
                    "hp": 10  # Lower HP than opponent
                },
                {
                    "position": [1, 1],  # Not adjacent to bot
                    "owner": "Rincewind Bot",
                    "hp": 10  # Lower HP than opponent
                }
            ],
            "board_size": 10,
            "turn": 1
        }

        decision = self.bot.decide(state)

        # Bot should attack the weaker minion instead of opponent
        self.assertEqual(decision["spell"]["name"], "melee_attack")
        self.assertEqual(decision["spell"]["target"], [3, 2])

    def test_attack_with_shield_active(self):
        """Test aggressive behavior when shield is active."""
        state = {
            "self": {
                "position": [2, 2],
                "hp": 80,
                "mana": 50,
                "cooldowns": {"fireball": 0, "shield": 0, "heal": 0, 
                             "teleport": 0, "blink": 0, "summon": 0, "melee_attack": 0},
                "shield_active": True,  # Shield is active
                "name": "Rincewind Bot"
            },
            "opponent": {
                "position": [2, 3],  # Adjacent to bot
                "hp": 70,
                "name": "Enemy Bot"
            },
            "artifacts": [],
            "minions": [
                {
                    "position": [1, 1],  # Not adjacent to bot
                    "owner": "Rincewind Bot",
                    "hp": 10  # Lower HP than opponent
                }
            ],
            "board_size": 10,
            "turn": 1
        }

        decision = self.bot.decide(state)

        # Bot should attack opponent when shield is active
        self.assertEqual(decision["spell"]["name"], "melee_attack")
        self.assertEqual(decision["spell"]["target"], [2, 3])
        # Bot should move toward opponent to maintain melee range
        self.assertEqual(decision["move"], [0, 1])

    def test_fireball_targeting_multiple_enemies(self):
        """Test fireball targeting logic when multiple enemies are in range."""
        state = {
            "self": {
                "position": [2, 2],
                "hp": 80,
                "mana": 50,
                "cooldowns": {"fireball": 0, "shield": 0, "heal": 0, 
                             "teleport": 0, "blink": 0, "summon": 0, "melee_attack": 0},
                "shield_active": False,
                "name": "Rincewind Bot"
            },
            "opponent": {
                "position": [6, 6],  # Out of melee range but in fireball range
                "hp": 70,
                "name": "Enemy Bot"
            },
            "artifacts": [],
            "minions": [
                {
                    "position": [6, 5],  # Adjacent to opponent, in fireball range
                    "owner": "Enemy Bot",
                    "hp": 20
                },
                {
                    "position": [6, 7],  # Also adjacent to opponent, in fireball range
                    "owner": "Enemy Bot",
                    "hp": 30
                },
                {
                    "position": [1, 1],  # Not adjacent to bot
                    "owner": "Rincewind Bot",
                    "hp": 10  # Lower HP than opponent
                }
            ],
            "board_size": 10,
            "turn": 1
        }

        decision = self.bot.decide(state)

        # Bot should use fireball targeting the position that can hit multiple enemies
        self.assertEqual(decision["spell"]["name"], "fireball")
        self.assertEqual(decision["spell"]["target"], [6, 6])  # Targeting opponent position to hit all 3

    def test_teleport_to_health_artifact(self):
        """Test teleporting to health artifact when HP is low."""
        state = {
            "self": {
                "position": [2, 2],
                "hp": 30,  # Low HP
                "mana": 50,
                "cooldowns": {"fireball": 0, "shield": 0, "heal": 1, 
                             "teleport": 0, "blink": 0, "summon": 0, "melee_attack": 0},
                "shield_active": False,
                "name": "Rincewind Bot"
            },
            "opponent": {
                "position": [8, 8],  # Far away
                "hp": 70,
                "name": "Enemy Bot"
            },
            "artifacts": [
                {
                    "position": [5, 5],
                    "type": "health"
                }
            ],
            "minions": [],
            "board_size": 10,
            "turn": 1
        }

        decision = self.bot.decide(state)

        # Bot should teleport to the health artifact
        self.assertEqual(decision["spell"]["name"], "teleport")
        self.assertEqual(decision["spell"]["target"], [5, 5])

    def test_retreat_mode_behavior(self):
        """Test behavior when in retreat mode."""
        # First set the bot in retreat mode
        self.bot.retreat_mode = True

        state = {
            "self": {
                "position": [5, 5],
                "hp": 40,  # Recovering HP
                "mana": 50,
                "cooldowns": {"fireball": 0, "shield": 0, "heal": 1, 
                             "teleport": 1, "blink": 1, "summon": 0, "melee_attack": 0},
                "shield_active": False,
                "name": "Rincewind Bot"
            },
            "opponent": {
                "position": [3, 3],  # Closer to origin
                "hp": 70,
                "name": "Enemy Bot"
            },
            "artifacts": [],
            "minions": [],
            "board_size": 10,
            "turn": 1
        }

        decision = self.bot.decide(state)

        # Bot should move away from opponent when in retreat mode
        self.assertEqual(decision["move"], [1, 1])  # Moving away in both dimensions

        # Test that the bot exits retreat mode when HP is high enough
        state["self"]["hp"] = 70  # Higher HP

        decision = self.bot.decide(state)

        # Retreat mode should be turned off
        self.assertFalse(self.bot.retreat_mode)

    def test_consecutive_same_position_handling(self):
        """Test the bot's behavior when stuck in the same position."""
        # Setup the bot as if it's been in the same position for 3 turns
        self.bot.previous_positions = [[3, 3], [3, 3], [3, 3]]
        self.bot.consecutive_same_position = 3

        state = {
            "self": {
                "position": [3, 3],  # Same position as previous turns
                "hp": 80,
                "mana": 50,
                "cooldowns": {"fireball": 1, "shield": 1, "heal": 1, 
                             "teleport": 1, "blink": 1, "summon": 1, "melee_attack": 1},
                "shield_active": False,
                "name": "Rincewind Bot"
            },
            "opponent": {
                "position": [7, 7],
                "hp": 70,
                "name": "Enemy Bot"
            },
            "artifacts": [],
            "minions": [],
            "board_size": 10,
            "turn": 1
        }

        # Use a patch to control the random movement
        with patch('random.randint', return_value=1):
            decision = self.bot.decide(state)

            # Bot should make a random move when stuck
            self.assertEqual(decision["move"], [1, 1])


if __name__ == '__main__':
    unittest.main()
