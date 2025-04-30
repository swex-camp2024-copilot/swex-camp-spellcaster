import math

import pygame
import sys
import time

# Constants
TILE_SIZE = 64
INFO_BAR_HEIGHT = 80
BOARD_SIZE = 10
WIDTH = HEIGHT = TILE_SIZE * BOARD_SIZE
FPS = 30
ANIMATION_DURATION = 0.5  # seconds

# Colors
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
BLUE = (100, 150, 255)
RED = (255, 100, 100)
GREEN = (100, 255, 100)
YELLOW = (255, 255, 100)
BLACK = (0, 0, 0)


def load_frames(path):
    return [pygame.image.load(path).convert_alpha()]


class Visualizer:
    def __init__(self, logger):
        pygame.init()
        self.logger = logger
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT + INFO_BAR_HEIGHT+  50))
        pygame.display.set_caption("Spellcasters: Code Duel")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20)
        self.wizard_sprites = {}
        self.load_wizard_sprites()
        self.artifact_sprites = {}
        self.load_artifact_sprites()
        self.minion_sprites = {}
        self.load_minion_sprites()

        original = pygame.image.load("assets/spells/fireball.png").convert_alpha()
        self.fireball_sprite = pygame.transform.smoothscale(original, (32, 32))

    def load_wizard_sprites(self):
        self.wizard_sprites = {
            "Bot1": load_frames("assets/wizards/sample_bot1.png"),
            "Bot2": load_frames("assets/wizards/sample_bot2.png")
        }

    def load_artifact_sprites(self):
        self.artifact_sprites = {
            "health": load_frames("assets/artifacts/health_20.png"),
            "mana": load_frames("assets/artifacts/mana_20.png"),
            "cooldown": load_frames("assets/artifacts/cooldown_1.png")
        }

    def load_minion_sprites(self):
        self.minion_sprites = {
            "Bot1": load_frames("assets/minions/minion_1.png"),
            "Bot2": load_frames("assets/minions/minion_2.png")
        }

    def draw_wizard_info_bar(self, state):
        try:
            assert "self" in state and "opponent" in state, "State must contain 'self' and 'opponent'"
            assert "name" in state["self"] and "hp" in state["self"] and "mana" in state["self"], "Invalid 'self' data"
            assert "name" in state["opponent"] and "hp" in state["opponent"] and "mana" in state[
                "opponent"], "Invalid 'opponent' data"
        except AssertionError as e:
            print(f"Error in draw_wizard_info_bar: {e}")
            return

        pygame.draw.rect(self.screen, BLACK, (0, 0, WIDTH, INFO_BAR_HEIGHT))  # top bar

        padding = 20
        spacing = WIDTH // 2

        for i, key in enumerate(["self", "opponent"]):
            wiz = state[key]
            color = BLUE if wiz["name"] != "Bot2" else RED
            x_offset = i * spacing + padding

            # Name
            name = self.font.render(wiz["name"], True, color)
            self.screen.blit(name, (x_offset, 10))

            # HP Bar
            hp = wiz["hp"]
            pygame.draw.rect(self.screen, (100, 100, 100), (x_offset, 30, 100, 10))  # background
            pygame.draw.rect(self.screen, (0, 255, 0), (x_offset, 30, hp, 10))  # current HP
            hp_text = self.font.render(f"{hp} HP", True, WHITE)
            self.screen.blit(hp_text, (x_offset + 105, 28))

            # Mana Bar
            mana = wiz["mana"]
            pygame.draw.rect(self.screen, (100, 100, 100), (x_offset, 45, 100, 10))
            pygame.draw.rect(self.screen, (0, 150, 255), (x_offset, 45, mana, 10))
            mana_text = self.font.render(f"{mana} MP", True, WHITE)
            self.screen.blit(mana_text, (x_offset + 105, 43))

    def draw_board(self):
        for x in range(0, WIDTH, TILE_SIZE):
            for y in range(0, HEIGHT, TILE_SIZE):
                pygame.draw.rect(self.screen, GRAY, (x, y + INFO_BAR_HEIGHT, TILE_SIZE, TILE_SIZE), 1)

    def draw_unit(self, position, color, symbol, name=None):
        x, y = position
        center = (x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2 + INFO_BAR_HEIGHT)

        if symbol == "W" and name:
            name_text = self.font.render(name, True, color)
            name_rect = name_text.get_rect(center=(center[0], center[1] - TILE_SIZE // 2))
            self.screen.blit(name_text, name_rect)

        if symbol == "W" and name in self.wizard_sprites:
            frames = self.wizard_sprites[name]
            self.draw_sprite(frames, center)
        elif symbol == "A" and name in self.artifact_sprites:
            frames = self.artifact_sprites[name]
            self.draw_sprite(frames, center)
        else:
            pygame.draw.circle(self.screen, color, center, TILE_SIZE // 3)
            text = self.font.render(symbol, True, BLACK)
            text_rect = text.get_rect(center=center)
            self.screen.blit(text, text_rect)

    def draw_sprite(self, frames, center):
        frame = frames[pygame.time.get_ticks() // 200 % len(frames)]
        # Scale the sprite to fit the tile size (slightly smaller for visual clarity)
        sprite_size = int(TILE_SIZE * 0.8)  # 80% of the tile size
        scaled_frame = pygame.transform.scale(frame, (sprite_size, sprite_size))
        frame_rect = scaled_frame.get_rect(center=center)
        self.screen.blit(scaled_frame, frame_rect)

    def draw_info_bar(self, turn):
        pygame.draw.rect(self.screen, BLACK, (0, HEIGHT + INFO_BAR_HEIGHT, WIDTH, 50))
        text = self.font.render(f"Turn {turn + 1}", True, WHITE)
        self.screen.blit(text, (10, HEIGHT + INFO_BAR_HEIGHT + 10))

    def render_frame(self, state, turn, skip_entities=False):
        self.screen.fill(WHITE)
        self.draw_wizard_info_bar(state)
        self.draw_board()

        if not skip_entities:
            for artifact in state.get("artifacts", []):
                if artifact.get("spawn_turn", 0) <= turn:
                    self.draw_unit(artifact["position"], YELLOW, "A", artifact["type"])

            # Minions
            for minion in state.get("minions", []):
                color = RED if minion["owner"] == "Bot2" else BLUE
                self.draw_unit(minion["position"], color, "M")

            # Wizards
            for wiz in ["self", "opponent"]:
                wiz_data = state[wiz]
                color = RED if wiz_data["name"] == "Bot2" else BLUE
                self.draw_unit(wiz_data["position"], color, "W", wiz_data["name"])

        self.draw_info_bar(turn)
        pygame.display.flip()

    def wait_for(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            self.clock.tick(FPS)

    def run(self, states):
        if states:
            initial_state = states[0]
            self.render_frame(initial_state, 0)
            self.wait_for(0.3)

        for turn in range(len(states) - 1):
            curr = states[turn]
            nxt = states[turn + 1]
            self.animate_transition(curr, nxt, turn)

            # Current animation wait
            self.wait_for(ANIMATION_DURATION)

            # Additional 1-second wait after each turn
            self.wait_for(0.3)

        # Pause at the end
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

    def animate_transition(self, curr_state, next_state, turn):
        # First half of animation: movement only
        move_steps = int(FPS * ANIMATION_DURATION / 2)
        damage_this_turn = [d for d in self.logger.damage_events if d["turn"] == turn]

        curr_minions = curr_state.get("minions", [])
        next_minions = next_state.get("minions", [])

        existing_minions = []
        for m in next_minions:
            if any(cm["id"] == m["id"] for cm in curr_minions):
                existing_minions.append(m)

        for frame in range(move_steps):
            progress = frame / move_steps
            self.screen.fill(WHITE)
            self.draw_board()
            self.draw_wizard_info_bar(curr_state)

            # Interpolate wizards
            for wiz_key in ["self", "opponent"]:
                wiz_curr = curr_state[wiz_key]
                wiz_next = next_state[wiz_key]
                color = RED if wiz_curr["name"] == "Bot2" else BLUE
                pos = self.interpolate(wiz_curr["position"], wiz_next["position"], progress)
                self.draw_unit(pos, color, "W", wiz_curr["name"])

            # Interpolate existing minions
            for i in range(min(len(curr_minions), len(existing_minions))):
                curr_m = curr_minions[i]
                next_m = existing_minions[i]
                color = RED if curr_m["owner"] == "Bot2" else BLUE
                pos = self.interpolate(curr_m["position"], next_m["position"], progress)
                self.draw_unit(pos, color, "M")

            # Static artifacts
            for artifact in curr_state.get("artifacts", []):
                self.draw_unit(artifact["position"], YELLOW, "A", artifact["type"])

            self.draw_info_bar(turn + 1)
            pygame.display.flip()
            self.clock.tick(FPS)
            self.handle_events()

        # Second half: spell casting (entities at their final positions)
        spell_steps = int(FPS * ANIMATION_DURATION / 2)
        spell_effects = [s for s in self.logger.spells if s["turn"] == turn]

        for frame in range(spell_steps):
            progress = frame / spell_steps
            self.screen.fill(WHITE)
            self.render_frame(next_state, turn, skip_entities=True)

            # Draw wizards at final positions
            for wiz_key in ["self", "opponent"]:
                wiz_next = next_state[wiz_key]
                color = RED if wiz_next["name"] == "Bot2" else BLUE
                self.draw_unit(wiz_next["position"], color, "W", wiz_next["name"])

            # Draw existing minions
            for m in existing_minions:
                color = RED if m["owner"] == "Bot2" else BLUE
                self.draw_unit(m["position"], color, "M")

            new_minions = [m for m in next_minions if not any(cm["id"] == m["id"] for cm in curr_minions)]

            for m in new_minions:
                color = RED if m["owner"] == "Bot2" else BLUE
                center = self.pixel_center(m["position"])
                # Grow effect
                size = int(TILE_SIZE * 0.6 * progress)  # Start small and grow
                pygame.draw.circle(self.screen, color, center, size)
                if progress > 0.5:  # Show "M" text after halfway through animation
                    text = self.font.render("M", True, BLACK)
                    text_rect = text.get_rect(center=center)
                    self.screen.blit(text, text_rect)

            # Animate spell effects
            for spell in spell_effects:
                caster_name = spell["caster"]
                spell_name = spell["spell"]
                target = spell.get("target")
                hit = spell.get("hit")

                # Use caster's FINAL position
                caster_data = next_state["self"] if next_state["self"]["name"] == caster_name else next_state[
                    "opponent"]
                caster_pos = caster_data["position"]

                if spell_name == "shield":
                    self.draw_shield_effect(caster_pos)
                elif spell_name == "heal":
                    self.draw_heal_effect(caster_pos)
                elif spell_name == "fireball" and target:
                    actual_target = target
                    if hit:
                        # Find opponent wizard position
                        for wiz_key in ["self", "opponent"]:
                            wiz_data = next_state[wiz_key]
                            if wiz_data["name"] != caster_name:  # This is the opponent
                                actual_target = wiz_data["position"]
                                break
                    self.draw_fireball(caster_pos, actual_target, progress)
                    if hit is not None and progress > 0.8:  # Show hit/miss text near the end
                        center = self.pixel_center(actual_target)
                        result_text = "HIT!" if hit else "MISS"
                        color = (0, 255, 0) if hit else (255, 0, 0)
                        result_surface = self.font.render(result_text, True, color)
                        result_rect = result_surface.get_rect(center=(center[0], center[1] - 50))
                        self.screen.blit(result_surface, result_rect)
                elif spell_name == "teleport":
                    self.draw_teleport_pulse(caster_pos)

            for dmg in damage_this_turn:
                center = self.pixel_center(dmg["position"])
                rise = int((1 - progress) * 20)  # float upward
                alpha = int(255 * (1 - progress))  # fade out
                dmg_text = self.font.render(f"-{dmg['amount']}", True, (255, 0, 0))
                dmg_text.set_alpha(alpha)
                self.screen.blit(dmg_text, (center[0] - 10, center[1] - 20 - rise))

            # Static artifacts
            for artifact in curr_state.get("artifacts", []):
                self.draw_unit(artifact["position"], YELLOW, "A", artifact["type"])

            self.draw_info_bar(turn + 1)
            pygame.display.flip()
            self.clock.tick(FPS)
            self.handle_events()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

    def interpolate(self, start, end, progress):
        sx, sy = start
        ex, ey = end
        x = sx + (ex - sx) * progress
        y = sy + (ey - sy) * progress
        return [x, y]

    def draw_shield_effect(self, pos):
        center = self.pixel_center(pos)
        pygame.draw.circle(self.screen, (100, 200, 255), center, TILE_SIZE // 2, 3)

    def draw_heal_effect(self, pos):
        center = self.pixel_center(pos)
        pygame.draw.circle(self.screen, (100, 255, 100), center, TILE_SIZE // 3, 0)

    # def draw_fireball(self, caster_pos, target_pos, progress):
    #     # Interpolate between caster and target
    #     x = caster_pos[0] + (target_pos[0] - caster_pos[0]) * progress
    #     y = caster_pos[1] + (target_pos[1] - caster_pos[1]) * progress
    #     center = self.pixel_center([x, y])
    #     pygame.draw.circle(self.screen, (255, 80, 0), center, 10)

    def draw_fireball(self, caster_pos, target_pos, progress):
        x = caster_pos[0] + (target_pos[0] - caster_pos[0]) * progress
        y = caster_pos[1] + (target_pos[1] - caster_pos[1]) * progress
        center = self.pixel_center([x, y])

        # Compute angle and rotate sprite
        angle = self.angle_between(caster_pos, target_pos) + 90
        rotated = pygame.transform.rotate(self.fireball_sprite, angle)
        rect = rotated.get_rect(center=center)

        self.screen.blit(rotated, rect)

    def angle_between(self, start, end):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        angle_rad = math.atan2(-dy, dx)  # y-axis is inverted in screen coords
        return math.degrees(angle_rad)

    def draw_teleport_pulse(self, pos):
        center = self.pixel_center(pos)
        pygame.draw.circle(self.screen, (255, 200, 255), center, TILE_SIZE // 2, 2)

    def pixel_center(self, pos):
        return (
            int(pos[0] * TILE_SIZE + TILE_SIZE // 2),
            int(pos[1] * TILE_SIZE + TILE_SIZE // 2 + INFO_BAR_HEIGHT)
        )

