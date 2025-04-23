from game.logger import GameLogger
from game.rules import BOARD_SIZE, SPELLS, ARTIFACT_SPAWN_RATE
from game.wizard import Wizard
from game.artifacts import ArtifactManager
from game.minion import Minion


class GameEngine:
    def __init__(self, bot1, bot2):
        self.wizard1 = Wizard("Bot1", [0, 0])
        self.wizard2 = Wizard("Bot2", [9, 9])
        self.bots = [bot1, bot2]
        self.artifacts = ArtifactManager()
        self.turn = 0
        self.log = []
        self.minions = []
        self.logger = GameLogger()

    def run_turn(self):
        self.turn += 1
        self.logger.new_turn(self.turn)

        # Step 1: Artifact spawning
        if self.turn % ARTIFACT_SPAWN_RATE == 0:
            self.artifacts.spawn_random()

        # Step 2: Get bot actions
        actions = [
            self.bots[0].decide(self.build_input(self.wizard1, self.wizard2)),
            self.bots[1].decide(self.build_input(self.wizard2, self.wizard1))
        ]

        # Step 3: Movement
        self.process_movement(self.wizard1, actions[0].get("move"))
        self.process_movement(self.wizard2, actions[1].get("move"))

        # Step 4: Artifact pickup
        self.artifacts.check_pickup(self.wizard1)
        self.artifacts.check_pickup(self.wizard2)

        # Step 5: Spellcasting
        self.process_spell(self.wizard1, self.wizard2, actions[0].get("spell"))
        self.process_spell(self.wizard2, self.wizard1, actions[1].get("spell"))

        #  Step 6: Process minion actions
        self.process_minions()

        # Step 7: Regeneration & cooldowns
        for wiz in [self.wizard1, self.wizard2]:
            wiz.regen_mana()
            wiz.reduce_cooldowns()

        self.logger.log_state(self.build_input(self.wizard1, self.wizard2))

        # Step 8: Victory check
        return self.check_winner()

    def build_input(self, self_wiz, opp_wiz):
        return {
            "turn": self.turn,
            "board_size": BOARD_SIZE,
            "self": self_wiz.to_dict(),
            "opponent": opp_wiz.to_dict(),
            "artifacts": self.artifacts.active_artifacts(),
            "minions": [m.to_dict() for m in self.minions if m.is_alive()]
        }

    def process_movement(self, wizard, move):
        if not move:
            return
        dx, dy = move
        x, y = wizard.position
        new_x, new_y = x + dx, y + dy
        if 0 <= new_x < BOARD_SIZE and 0 <= new_y < BOARD_SIZE:
            wizard.position = [new_x, new_y]
            self.logger.log(f"{wizard.name} moved to {wizard.position}")

    def process_spell(self, caster, target, spell_action):
        if not spell_action:
            return

        spell = spell_action["name"]
        if not caster.can_cast(spell):
            self.logger.log(f"{caster.name} tried to cast {spell} but failed.")
            return

        caster.cast_spell(spell)
        self.logger.log_spell(caster, spell, spell_action.get("target") if spell_action else None)
        self.logger.log(f"{caster.name} cast {spell}")

        if spell == "fireball":
            target_pos = spell_action["target"]
            if self.in_range(caster.position, target_pos,
                             SPELLS["fireball"]["range"]) and target_pos == target.position:
                damage = SPELLS["fireball"]["damage"]
                if target.shield_active:
                    damage = max(0, damage - SPELLS["shield"]["block"])
                    target.shield_active = False
                target.hp -= damage
                self.logger.log(f"{target.name} took {damage} damage (HP: {target.hp})")
        elif spell == "shield":
            caster.shield_active = True
        elif spell == "heal":
            heal = SPELLS["heal"]["heal"]
            caster.hp = min(caster.hp + heal, 100)
            self.logger.log(f"{caster.name} healed {heal} HP (HP: {caster.hp})")
        elif spell == "teleport":
            dest = spell_action["target"]
            if self.is_valid_tile(dest):
                caster.position = dest
                self.logger.log(f"{caster.name} teleported to {dest}")
        elif spell == "blink":
            dest = spell_action["target"]
            if self.in_range(caster.position, dest, SPELLS["blink"]["distance"]) and self.is_valid_tile(dest):
                caster.position = dest
                self.logger.log(f"{caster.name} blinked to {dest}")
        elif spell == "summon":
            # Check if caster already has a minion
            if not any(m.owner == caster.name and m.is_alive() for m in self.minions):
                spawn_pos = self.get_adjacent_free_tile(caster.position)
                if spawn_pos:
                    self.minions.append(Minion(caster.name, spawn_pos))
                    self.logger.log(f"{caster.name} summoned a minion at {spawn_pos}")
                else:
                    self.logger.log(f"{caster.name} tried to summon but no space.")
            else:
                self.logger.log(f"{caster.name} already has a minion.")

    def process_minions(self):
        for minion in self.minions:
            if not minion.is_alive():
                continue

            enemy_targets = [self.wizard1, self.wizard2]
            enemy = next(w for w in enemy_targets if w.name != minion.owner)

            # Find enemy wizard or minion closest to this minion
            targets = [enemy] + [m for m in self.minions if m.owner != minion.owner and m.is_alive()]
            target = min(targets, key=lambda t: self.manhattan_dist(minion.position, t.position))

            # If adjacent → attack
            if self.manhattan_dist(minion.position, target.position) == 1:
                target.hp -= 10
                self.logger.log(
                    f"{minion.owner}'s minion attacked {target.owner if hasattr(target, 'owner') else target.name} for 10 dmg")
            else:
                # Move 1 tile toward target
                dx = target.position[0] - minion.position[0]
                dy = target.position[1] - minion.position[1]
                move_x = 1 if dx > 0 else -1 if dx < 0 else 0
                move_y = 1 if dy > 0 else -1 if dy < 0 else 0
                new_pos = [minion.position[0] + move_x, minion.position[1] + move_y]
                if self.is_valid_tile(new_pos) and not self.tile_occupied(new_pos):
                    minion.position = new_pos
                    self.logger.log(f"{minion.owner}'s minion moved to {new_pos}")

    def check_winner(self):
        if self.wizard1.hp <= 0 and self.wizard2.hp <= 0:
            return "Draw"
        elif self.wizard1.hp <= 0:
            return self.wizard2.name
        elif self.wizard2.hp <= 0:
            return self.wizard1.name
        return None

    def in_range(self, start, end, max_range):
        dx = abs(end[0] - start[0])
        dy = abs(end[1] - start[1])
        return max(dx, dy) <= max_range

    def is_valid_tile(self, pos):
        x, y = pos
        return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE

    def get_adjacent_free_tile(self, pos):
        x, y = pos
        directions = [(-1, -1), (-1, 0), (-1, 1),
                      (0, -1), (0, 1),
                      (1, -1), (1, 0), (1, 1)]
        for dx, dy in directions:
            new_x, new_y = x + dx, y + dy
            if self.is_valid_tile((new_x, new_y)) and not self.tile_occupied([new_x, new_y]):
                return [new_x, new_y]
        return None

    def tile_occupied(self, pos):
        # Check if wizards or minions occupy this tile
        if pos == self.wizard1.position or pos == self.wizard2.position:
            return True
        for m in self.minions:
            if m.is_alive() and m.position == pos:
                return True
        return False

    def manhattan_dist(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

