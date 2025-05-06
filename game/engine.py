from game.logger import GameLogger
from game.rules import BOARD_SIZE, SPELLS, ARTIFACT_SPAWN_RATE, MELEE_DAMAGE
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
        self.log_turn()

        collision_occurred = False

        # Step 1: Artifact spawning
        self.spawn_artifacts()

        # Step 2: Get bot actions and validate them
        actions = self.validate_actions([
            (self.bots[0].decide(self.build_input(self.wizard1, self.wizard2))),
            (self.bots[1].decide(self.build_input(self.wizard2, self.wizard1)))
        ])

        # Step 3: Movement with collision detection
        wiz1_move = actions[0].get("move")
        wiz2_move = actions[1].get("move")

        # Calculate intended positions
        wiz1_next_pos = self.calculate_next_position(self.wizard1, wiz1_move)
        wiz2_next_pos = self.calculate_next_position(self.wizard2, wiz2_move)

        # Check for collision
        if wiz1_next_pos and wiz2_next_pos and wiz1_next_pos == wiz2_next_pos:
            # Handle collision - melee fight
            self.handle_entity_collision(self.wizard1, self.wizard2)
            collision_occurred = True
        else:
            # No collision, process movements normally
            if wiz1_next_pos:
                self.wizard1.position = wiz1_next_pos
                self.logger.log(f"{self.wizard1.name} moved to {self.wizard1.position}")
            if wiz2_next_pos:
                self.wizard2.position = wiz2_next_pos
                self.logger.log(f"{self.wizard2.name} moved to {self.wizard2.position}")

        # Step 4: Artifact pickup
        self.artifacts.check_pickup(self.wizard1)
        self.artifacts.check_pickup(self.wizard2)

        # Step 5: Spellcasting (skip if collision occurred)
        if not collision_occurred:
            self.process_spell(self.wizard1, actions[0].get("spell"))
            self.process_spell(self.wizard2, actions[1].get("spell"))

        # Remaining steps...
        self.process_minions()

        # Regeneration & cooldowns
        for wiz in [self.wizard1, self.wizard2]:
            wiz.regen_mana()
            wiz.reduce_cooldowns()

        self.logger.log_state(self.build_input(self.wizard1, self.wizard2))

        winner = self.check_winner()

        if winner:
            if winner == "Draw":
                self.logger.log("Game Over: It's a Draw!")
            else:
                self.logger.log(f"Game Over: {winner} wins!")

            self.logger.log_state(self.build_input(self.wizard1, self.wizard2))

        return winner

    def spawn_artifacts(self):
        if self.turn % ARTIFACT_SPAWN_RATE == 0:
            occupied_positions = [
                self.wizard1.position,
                self.wizard2.position
            ]
            # Add positions of alive minions
            occupied_positions.extend([m.position for m in self.minions if m.is_alive()])

            self.artifacts.spawn_random(occupied_positions, self.turn)

    def log_turn(self):
        self.logger.log_state(self.build_input(self.wizard1, self.wizard2))
        self.turn += 1
        self.logger.new_turn(self.turn)

    def build_input(self, self_wiz, opp_wiz):
        return {
            "turn": self.turn,
            "board_size": BOARD_SIZE,
            "self": self_wiz.to_dict(),
            "opponent": opp_wiz.to_dict(),
            "artifacts": self.artifacts.active_artifacts(),
            "minions": [m.to_dict() for m in self.minions if m.is_alive()]
        }

    def validate_actions(self, actions):
        for action in actions:
            # Validate "move"
            move = action.get("move")
            if move and isinstance(move, list) and len(move) == 2 and all(isinstance(i, int) for i in move):
                if -1 <= move[0] <= 1 and -1 <= move[1] <= 1:
                    continue
                else:
                    self.logger.log("Invalid move: Out of bounds.")
                    move[0] = 0
                    move[1] = 0
            elif move:
                self.logger.log("Invalid move: Must be an array of two integers.")
                move[0] = 0
                move[1] = 0

        return actions

    def process_movement(self, wizard, move):
        if not move:
            return
        dx, dy = move
        x, y = wizard.position
        new_x, new_y = x + dx, y + dy
        if 0 <= new_x < BOARD_SIZE and 0 <= new_y < BOARD_SIZE:
            wizard.position = [new_x, new_y]
            self.logger.log(f"{wizard.name} moved to {wizard.position}")

    def process_spell(self, caster, spell_action):
        if not spell_action:
            return

        spell = spell_action["name"]
        if not caster.can_cast(spell):
            self.logger.log(f"{caster.name} tried to cast {spell} but failed.")
            return

        # Special handling for melee_attack which requires adjacency check
        if spell == "melee_attack":
            target_pos = spell_action["target"]
            # Check if target is adjacent
            if self.manhattan_dist(caster.position, target_pos) != 1:
                self.logger.log(f"{caster.name} tried melee attack but target is not adjacent.")
                return

        caster.cast_spell(spell)
        self.logger.log(f"{caster.name} cast {spell}")

        hit = False
        if spell == "fireball":
            target_pos = spell_action["target"]
            if self.in_range(caster.position, target_pos, SPELLS["fireball"]["range"]):
                # Check if any entity (wizard or minion) is at target position
                target_entity = self.get_entity_at_position(target_pos)
                if target_entity:
                    damage = SPELLS["fireball"]["damage"]
                    if hasattr(target_entity, "shield_active") and target_entity.shield_active:
                        damage = max(0, damage - SPELLS["shield"]["block"])
                        target_entity.shield_active = False
                    target_entity.hp -= damage
                    hit = True
                    entity_name = target_entity.name if hasattr(target_entity,
                                                                "name") else f"{target_entity.owner}'s minion"
                    self.logger.log_damage(target_pos, damage, entity_name)
                    self.logger.log(f"{entity_name} took {damage} damage (HP: {target_entity.hp})")
                else:
                    self.logger.log(f"{caster.name}'s fireball missed!")
            else:
                self.logger.log(f"{caster.name}'s fireball out of range!")
        elif spell == "melee_attack":
            target_pos = spell_action["target"]
            target_entity = self.get_entity_at_position(target_pos)
            if target_entity:
                damage = SPELLS["melee_attack"]["damage"]
                # Shield doesn't apply to melee attacks
                target_entity.hp -= damage
                hit = True
                entity_name = target_entity.name if hasattr(target_entity,
                                                            "name") else f"{target_entity.owner}'s minion"
                self.logger.log_damage(target_pos, damage, entity_name)
                self.logger.log(
                    f"{entity_name} took {damage} damage from {caster.name}'s melee attack (HP: {target_entity.hp})")
            else:
                self.logger.log(f"{caster.name}'s melee attack missed!")
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

        self.logger.log_spell(caster, spell, spell_action.get("target") if spell_action else None, hit)

    def process_minions(self):
        # Track attempted movement destinations
        intended_positions = {}

        for minion in self.minions:
            if not minion.is_alive():
                continue

            if not minion.is_ready():
                minion.make_ready()
                continue

            enemy_targets = [self.wizard1, self.wizard2]
            enemy = next(w for w in enemy_targets if w.name != minion.owner)

            # Find closest target
            targets = [enemy] + [m for m in self.minions if m.owner != minion.owner and m.is_alive()]
            target = min(targets, key=lambda t: self.manhattan_dist(minion.position, t.position))

            # If adjacent → attack
            if self.manhattan_dist(minion.position, target.position) == 1:
                target.hp -= 10
                self.logger.log_damage(target.position, 10, target.name if hasattr(target, "name") else "Minion")
                self.logger.log(
                    f"{minion.owner}'s minion attacked {target.owner if hasattr(target, 'owner') else target.name} for 10 dmg")
            else:
                # Move 1 tile toward target
                dx = target.position[0] - minion.position[0]
                dy = target.position[1] - minion.position[1]
                move_x = 1 if dx > 0 else -1 if dx < 0 else 0
                move_y = 1 if dy > 0 else -1 if dy < 0 else 0
                new_pos = [minion.position[0] + move_x, minion.position[1] + move_y]

                # Check if valid tile but don't check occupation yet
                if self.is_valid_tile(new_pos):
                    # Store intended position
                    intended_pos_key = f"{new_pos[0]},{new_pos[1]}"

                    # Check if collision will occur
                    if intended_pos_key in intended_positions:
                        # Handle collision between minions
                        other_entity = intended_positions[intended_pos_key]
                        self.handle_entity_collision(minion, other_entity)
                    elif new_pos == self.wizard1.position:
                        # Collision with wizard1
                        self.handle_entity_collision(minion, self.wizard1)
                    elif new_pos == self.wizard2.position:
                        # Collision with wizard2
                        self.handle_entity_collision(minion, self.wizard2)
                    else:
                        # No collision, record intended position
                        intended_positions[intended_pos_key] = minion
                        minion.position = new_pos
                        self.logger.log(f"{minion.owner}'s minion moved to {new_pos}")

    def get_entity_at_position(self, position):
        """Return the entity (wizard or minion) at the given position, or None if empty."""
        if position == self.wizard1.position:
            return self.wizard1
        if position == self.wizard2.position:
            return self.wizard2
        for minion in self.minions:
            if minion.is_alive() and minion.position == position:
                return minion
        return None

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

    def calculate_next_position(self, wizard, move):
        if not move:
            return None

        dx, dy = move
        x, y = wizard.position
        new_x, new_y = x + dx, y + dy

        # Check if move is valid
        if 0 <= new_x < BOARD_SIZE and 0 <= new_y < BOARD_SIZE:
            return [new_x, new_y]
        return None

    def handle_entity_collision(self, entity1, entity2):
        import random

        # Random damage between 0 and MELEE_DAMAGE for both entities
        damage1 = random.randint(0, MELEE_DAMAGE)
        damage2 = random.randint(0, MELEE_DAMAGE)

        # Apply shield protection for wizards
        if hasattr(entity1, "shield_active") and entity1.shield_active:
            damage1 = max(0, damage1 - SPELLS["shield"]["block"])
            entity1.shield_active = False

        if hasattr(entity2, "shield_active") and entity2.shield_active:
            damage2 = max(0, damage2 - SPELLS["shield"]["block"])
            entity2.shield_active = False

        # Apply damage
        entity1.hp -= damage1
        entity2.hp -= damage2

        # Generate names for logging
        name1 = entity1.name if hasattr(entity1, "name") else f"{entity1.owner}'s minion"
        name2 = entity2.name if hasattr(entity2, "name") else f"{entity2.owner}'s minion"

        self.logger.log(f"{name1} and {name2} collided in melee combat!")
        self.logger.log(f"{name1} takes {damage1} damage (HP: {entity1.hp})")
        self.logger.log(f"{name2} takes {damage2} damage (HP: {entity2.hp})")

        # Move entities apart to adjacent tiles
        self.scatter_entities(entity1, entity2)

    def scatter_entities(self, entity1, entity2):
        import random

        # Find random adjacent tiles for both entities
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        random.shuffle(directions)

        # Get all valid adjacent tiles
        valid_tiles = []
        # Use entity1's position as reference since they collided
        for dx, dy in directions:
            new_pos = [entity1.position[0] + dx, entity1.position[1] + dy]
            if self.is_valid_tile(new_pos) and not self.tile_occupied_except([new_pos], [entity1, entity2]):
                valid_tiles.append(new_pos)

        if len(valid_tiles) >= 2:
            # Choose random distinct tiles
            entity1.position = valid_tiles[0]
            entity2.position = valid_tiles[1]

            name1 = entity1.name if hasattr(entity1, "name") else f"{entity1.owner}'s minion"
            name2 = entity2.name if hasattr(entity2, "name") else f"{entity2.owner}'s minion"

            self.logger.log(f"{name1} was pushed to {entity1.position}")
            self.logger.log(f"{name2} was pushed to {entity2.position}")
        else:
            # Not enough space, keep original positions
            self.logger.log("Not enough space to separate entities!")

    def tile_occupied_except(self, pos, exceptions):
        # Check if wizards occupy this tile
        if self.wizard1.position == pos and self.wizard1 not in exceptions:
            return True
        if self.wizard2.position == pos and self.wizard2 not in exceptions:
            return True
        # Check minions
        for m in self.minions:
            if m.is_alive() and m.position == pos and m not in exceptions:
                return True
        return False
