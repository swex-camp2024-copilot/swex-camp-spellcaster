import os

import pygame
import sys
import time

# Constants
TILE_SIZE = 64
INFO_BAR_HEIGHT = 80
BOARD_SIZE = 10
WIDTH = HEIGHT = TILE_SIZE * BOARD_SIZE
FPS = 30
ANIMATION_DURATION = 0.3  # seconds

# Colors
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
BLUE = (100, 150, 255)
RED = (255, 100, 100)
GREEN = (100, 255, 100)
YELLOW = (255, 255, 100)
BLACK = (0, 0, 0)

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

    def load_wizard_sprites(self):
        def load_frames(path):
            return [pygame.image.load(path).convert_alpha()]

        self.wizard_sprites = {
            "Bot1": load_frames("assets/wizards/sample_bot1.png"),
            "Bot2": load_frames("assets/wizards/sample_bot2.png")
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

        if name:
            name_text = self.font.render(name, True, color)
            name_rect = name_text.get_rect(center=(center[0], center[1] - TILE_SIZE // 2))
            self.screen.blit(name_text, name_rect)

        if symbol == "W" and name in self.wizard_sprites:
            frames = self.wizard_sprites[name]
            frame = frames[pygame.time.get_ticks() // 200 % len(frames)]
            # Scale the sprite to fit the tile size (slightly smaller for visual clarity)
            sprite_size = int(TILE_SIZE * 0.8)  # 80% of the tile size
            scaled_frame = pygame.transform.scale(frame, (sprite_size, sprite_size))
            frame_rect = scaled_frame.get_rect(center=center)
            self.screen.blit(scaled_frame, frame_rect)
        else:
            pygame.draw.circle(self.screen, color, center, TILE_SIZE // 3)
            text = self.font.render(symbol, True, BLACK)
            text_rect = text.get_rect(center=center)
            self.screen.blit(text, text_rect)

    def draw_info_bar(self, turn):
        pygame.draw.rect(self.screen, BLACK, (0, HEIGHT + INFO_BAR_HEIGHT, WIDTH, 50))
        text = self.font.render(f"Turn {turn + 1}", True, WHITE)
        self.screen.blit(text, (10, HEIGHT + INFO_BAR_HEIGHT + 10))

    def render_frame(self, state, turn, skip_wizards=False):
        self.screen.fill(WHITE)
        self.draw_wizard_info_bar(state)
        self.draw_board()

        # Artifacts
        for artifact in state.get("artifacts", []):
            self.draw_unit(artifact["position"], YELLOW, "A")

        # Minions
        for minion in state.get("minions", []):
            color = RED if minion["owner"] == "Bot2" else BLUE
            self.draw_unit(minion["position"], color, "M")

        # Wizards
        if (not skip_wizards):
            for wiz in ["self", "opponent"]:
                wiz_data = state[wiz]
                color = RED if wiz_data["name"] == "Bot2" else BLUE
                self.draw_unit(wiz_data["position"], color, "W", wiz_data["name"])

        self.draw_info_bar(turn)
        pygame.display.flip()

    def run(self, states):
        for turn in range(len(states) - 1):
            curr = states[turn]
            nxt = states[turn + 1]
            self.animate_transition(curr, nxt, turn)
            start_time = time.time()

            # Wait or animate
            while time.time() - start_time < ANIMATION_DURATION:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                self.clock.tick(FPS)

        # Pause at the end
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

    def animate_transition(self, curr_state, next_state, turn):
        steps = int(FPS * ANIMATION_DURATION)
        spell_effects = [s for s in self.logger.spells if s["turn"] == turn]
        for frame in range(steps):
            progress = frame / steps
            self.screen.fill(WHITE)
            self.render_frame(curr_state, turn, skip_wizards=True)

            # Interpolate wizards
            for wiz_key in ["self", "opponent"]:
                wiz_curr = curr_state[wiz_key]
                wiz_next = next_state[wiz_key]
                color = RED if wiz_curr["name"] == "Bot2" else BLUE
                pos = self.interpolate(wiz_curr["position"], wiz_next["position"], progress)
                self.draw_unit(pos, color, "W", wiz_curr["name"])

            # Interpolate minions (matched by owner + index)
            curr_minions = curr_state.get("minions", [])
            next_minions = next_state.get("minions", [])

            for i in range(min(len(curr_minions), len(next_minions))):
                curr_m = curr_minions[i]
                next_m = next_minions[i]
                color = RED if curr_m["owner"] == "Bot2" else BLUE
                pos = self.interpolate(curr_m["position"], next_m["position"], progress)
                self.draw_unit(pos, color, "M")

            for spell in spell_effects:
                caster_name = spell["caster"]
                spell_name = spell["spell"]
                target = spell.get("target")

                # Get caster's interpolated position
                caster_data = curr_state["self"] if curr_state["self"]["name"] == caster_name else curr_state[
                    "opponent"]
                caster_pos = self.interpolate(caster_data["position"], caster_data["position"], 1)

                if spell_name == "shield":
                    self.draw_shield_effect(caster_pos)
                elif spell_name == "heal":
                    self.draw_heal_effect(caster_pos)
                elif spell_name == "fireball" and target:
                    self.draw_fireball(caster_pos, target, progress)
                elif spell_name == "teleport":
                    self.draw_teleport_pulse(caster_pos)

            # Static artifacts (no animation)
            for artifact in curr_state.get("artifacts", []):
                self.draw_unit(artifact["position"], YELLOW, "A")

            self.draw_info_bar(turn + 1)
            pygame.display.flip()
            self.clock.tick(FPS)

            # Handle quit during animation
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

    def draw_fireball(self, caster_pos, target_pos, progress):
        # Interpolate between caster and target
        x = caster_pos[0] + (target_pos[0] - caster_pos[0]) * progress
        y = caster_pos[1] + (target_pos[1] - caster_pos[1]) * progress
        center = self.pixel_center([x, y])
        pygame.draw.circle(self.screen, (255, 80, 0), center, 10)

    def draw_teleport_pulse(self, pos):
        center = self.pixel_center(pos)
        pygame.draw.circle(self.screen, (255, 200, 255), center, TILE_SIZE // 2, 2)

    def pixel_center(self, pos):
        return (
            int(pos[0] * TILE_SIZE + TILE_SIZE // 2),
            int(pos[1] * TILE_SIZE + TILE_SIZE // 2)
        )

