import math
import sys
import time
from typing import Dict, List, Tuple, Optional, Any

import pygame

from bots.bot_interface import BotInterface

# Constants
TILE_SIZE = 64
INFO_BAR_HEIGHT = 80
BOTTOM_BAR_HEIGHT = 50
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
HP_BG_COLOR = (100, 100, 100)
HP_COLOR = (0, 255, 0)
MANA_COLOR = (0, 150, 255)
SHIELD_GLOW_COLOR = (100, 200, 255)
HEAL_PARTICLE_COLOR = (180, 255, 180)
TELEPORT_COLOR = (255, 200, 255)
HIT_COLOR = (0, 255, 0)
MISS_COLOR = (255, 0, 0)
FIREBALL_TRAIL_COLOR = (255, 150, 50)

# Asset Paths
DEFAULT_WIZARD_SPRITES = ["assets/wizards/sample_bot1.png", "assets/wizards/sample_bot2.png"]
DEFAULT_MINION_SPRITES = ["assets/minions/minion_1.png", "assets/minions/minion_2.png"]
FIREBALL_SPRITE_PATH = "assets/spells/fireball.png"
HEAL_SPRITE_PATH = "assets/spells/heal.png"
SHIELD_SPRITE_PATH = "assets/spells/shield.png"
EXPLOSION_SPRITE_PATH = "assets/spells/fireball_explosion.png"
MELEE_SPRITE_PATH = "assets/spells/melee.png"

# Animation settings
SPRITE_SCALE = 0.8  # 80% of the tile size
SPRITE_FRAME_DURATION = 200  # ms per frame
SHIELD_EFFECT_DURATION = 2.0  # seconds
SHIELD_PULSE_RATE = 2  # Hz
HEAL_PULSE_RATE = 4  # Hz
HEAL_ALPHA_RATE = 3  # Hz
HEAL_PARTICLE_COUNT = 5
FIREBALL_TRAIL_LENGTH = 5
TELEPORT_PULSE_RATE = 5  # Hz

Position = List[float]  # [x, y]


def load_frames(path: str) -> List[pygame.Surface]:
    """Load sprite frames from a path."""
    return [pygame.image.load(path).convert_alpha()]


class Visualizer:
    def __init__(self, logger: Any, bot1: BotInterface, bot2: BotInterface):
        pygame.init()
        self.logger = logger
        self.bot1 = bot1
        self.bot2 = bot2
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT + INFO_BAR_HEIGHT + BOTTOM_BAR_HEIGHT))
        pygame.display.set_caption("Spellcasters: Code Duel")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20)
        self.wizard_sprites: Dict[str, List[pygame.Surface]] = {}
        self.load_wizard_sprites()
        self.artifact_sprites: Dict[str, List[pygame.Surface]] = {}
        self.load_artifact_sprites()
        self.minion_sprites: Dict[str, List[pygame.Surface]] = {}
        self.load_minion_sprites()
        self.info_bar_state = {}
        self.info_bar_state = {}

        original = pygame.image.load(FIREBALL_SPRITE_PATH).convert_alpha()
        self.fireball_sprite = pygame.transform.smoothscale(original, (32, 32))

        original = pygame.image.load(HEAL_SPRITE_PATH).convert_alpha()
        self.heal_sprite = pygame.transform.smoothscale(original, (TILE_SIZE, TILE_SIZE))

        original = pygame.image.load(SHIELD_SPRITE_PATH).convert_alpha()
        self.shield_sprite = pygame.transform.smoothscale(original, (TILE_SIZE, TILE_SIZE))

        original = pygame.image.load(MELEE_SPRITE_PATH).convert_alpha()
        self.melee_sprite = pygame.transform.smoothscale(original, (TILE_SIZE, TILE_SIZE))

        self.fireball_explosion_sprite = pygame.image.load(EXPLOSION_SPRITE_PATH).convert_alpha()

    def load_wizard_sprites(self) -> None:
        """Load wizard sprites for both bots with fallback to defaults if needed."""
        for bot in [self.bot1, self.bot2]:
            try:
                sprite_path = bot.sprite_path
                if sprite_path not in self.wizard_sprites:
                    frames = load_frames(sprite_path)
                    self.wizard_sprites[bot.name] = frames
            except Exception as e:
                print(f"Error loading sprite for {bot.name}: {e}")
                # Fallback to default sprite
                if bot.name not in self.wizard_sprites:
                    default_sprite = DEFAULT_WIZARD_SPRITES[0] if bot.name == self.bot1.name else DEFAULT_WIZARD_SPRITES[1]
                    frames = load_frames(default_sprite)
                    self.wizard_sprites[bot.name] = frames

    def load_artifact_sprites(self) -> None:
        """Load artifact sprites."""
        self.artifact_sprites = {
            "health": load_frames("assets/artifacts/health_20.png"),
            "mana": load_frames("assets/artifacts/mana_20.png"),
            "cooldown": load_frames("assets/artifacts/cooldown_1.png")
        }

    def load_minion_sprites(self) -> None:
        """Load minion sprites for both bots with fallback to defaults if needed."""
        for bot in [self.bot1, self.bot2]:
            try:
                sprite_path = bot.minion_sprite_path
                if sprite_path not in self.minion_sprites:
                    frames = load_frames(sprite_path)
                    self.minion_sprites[bot.name] = frames
            except Exception as e:
                print(f"Error loading sprite for {bot.name}: {e}")
                # Fallback to default sprite
                if bot.name not in self.minion_sprites:
                    default_sprite = DEFAULT_MINION_SPRITES[0] if bot.name == self.bot1.name else DEFAULT_MINION_SPRITES[1]
                    frames = load_frames(default_sprite)
                    self.minion_sprites[bot.name] = frames

    def draw_wizard_info_bar(self, state: Dict[str, Any] = None) -> None:
        """Draw the top bar with wizard health and mana information."""
        if (state == None):
            state = self.info_bar_state
        try:
            assert "self" in state and "opponent" in state, "State must contain 'self' and 'opponent'"
            assert "name" in state["self"] and "hp" in state["self"] and "mana" in state["self"], "Invalid 'self' data"
            assert "name" in state["opponent"] and "hp" in state["opponent"] and "mana" in state["opponent"], "Invalid 'opponent' data"
        except AssertionError as e:
            print(f"Error in draw_wizard_info_bar: {e}")
            return

        pygame.draw.rect(self.screen, BLACK, (0, 0, WIDTH, INFO_BAR_HEIGHT))  # top bar

        padding = 20
        spacing = WIDTH // 2

        for i, key in enumerate(["self", "opponent"]):
            wiz = state[key]
            color = BLUE if wiz["name"] != self.bot2.name else RED
            x_offset = i * spacing + padding

            # Name
            name = self.font.render(wiz["name"], True, color)
            self.screen.blit(name, (x_offset, 10))

            # HP Bar
            hp = wiz["hp"]
            pygame.draw.rect(self.screen, HP_BG_COLOR, (x_offset, 30, 100, 10))  # background
            pygame.draw.rect(self.screen, HP_COLOR, (x_offset, 30, hp, 10))  # current HP
            hp_text = self.font.render(f"{hp} HP", True, WHITE)
            self.screen.blit(hp_text, (x_offset + 105, 28))

            # Mana Bar
            mana = wiz["mana"]
            pygame.draw.rect(self.screen, HP_BG_COLOR, (x_offset, 45, 100, 10))
            pygame.draw.rect(self.screen, MANA_COLOR, (x_offset, 45, mana, 10))
            mana_text = self.font.render(f"{mana} MP", True, WHITE)
            self.screen.blit(mana_text, (x_offset + 105, 43))

    def draw_board(self) -> None:
        """Draw the game board grid."""
        for x in range(0, WIDTH, TILE_SIZE):
            for y in range(0, HEIGHT, TILE_SIZE):
                pygame.draw.rect(self.screen, GRAY, (x, y + INFO_BAR_HEIGHT, TILE_SIZE, TILE_SIZE), 1)

    def draw_unit(self, position: Position, color: Tuple[int, int, int], symbol: str, name: Optional[str] = None) -> None:
        """Draw a game unit (wizard, minion, artifact) on the board."""
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
        elif symbol == "M" and name in self.minion_sprites:
            frames = self.minion_sprites[name]
            self.draw_sprite(frames, center)
        else:
            pygame.draw.circle(self.screen, color, center, TILE_SIZE // 3)
            text = self.font.render(symbol, True, BLACK)
            text_rect = text.get_rect(center=center)
            self.screen.blit(text, text_rect)

    def draw_sprite(self, frames: List[pygame.Surface], center: Tuple[int, int]) -> None:
        """Draw an animated sprite from frames at the specified position."""
        frame = frames[pygame.time.get_ticks() // SPRITE_FRAME_DURATION % len(frames)]
        # Scale the sprite to fit the tile size (slightly smaller for visual clarity)
        sprite_size = int(TILE_SIZE * SPRITE_SCALE)
        scaled_frame = pygame.transform.scale(frame, (sprite_size, sprite_size))
        frame_rect = scaled_frame.get_rect(center=center)
        self.screen.blit(scaled_frame, frame_rect)

    def draw_info_bar(self, turn: int) -> None:
        """Draw the bottom info bar showing turn number."""
        pygame.draw.rect(self.screen, BLACK, (0, HEIGHT + INFO_BAR_HEIGHT, WIDTH, BOTTOM_BAR_HEIGHT))
        text = self.font.render(f"Turn {turn + 1}", True, WHITE)
        self.screen.blit(text, (10, HEIGHT + INFO_BAR_HEIGHT + 10))

    def render_frame(self, state: Dict[str, Any], turn: int, skip_entities: bool = False) -> None:
        """Render a complete frame with all entities."""
        self.screen.fill(WHITE)
        self.draw_wizard_info_bar()
        self.draw_board()

        if not skip_entities:
            for artifact in state.get("artifacts", []):
                if artifact.get("spawn_turn", 0) <= turn:
                    self.draw_unit(artifact["position"], YELLOW, "A", artifact["type"])

            # Minions
            for minion in state.get("minions", []):
                color = RED if minion["owner"] == self.bot2.name else BLUE
                self.draw_unit(minion["position"], color, "M", minion["owner"])

            # Wizards
            for wiz in ["self", "opponent"]:
                wiz_data = state[wiz]
                color = RED if wiz_data["name"] == self.bot2.name else BLUE
                self.draw_unit(wiz_data["position"], color, "W", wiz_data["name"])
                # Draw shield if active
                self.draw_active_shield(wiz_data, wiz_data["position"])

        self.draw_info_bar(turn)
        pygame.display.flip()

    def wait_for(self, duration: float) -> None:
        """Wait for a specified duration while handling events."""
        start_time = time.time()
        while time.time() - start_time < duration:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            self.clock.tick(FPS)

    def display_end_game_message(self, winner: Optional[str], has_more_matches: bool) -> None:
        """Display the end game message with the winner or draw."""
        # Draw a transparent grey rectangle over the screen
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((50, 50, 50, 180))  # Grey with 180 alpha for transparency
        self.screen.blit(overlay, (0, 0))

        # Determine the message and color
        if winner is None:
            message = "DRAW!"
            color = WHITE
        else:
            message = f"THE WINNER IS {winner.upper()}!"
            color = BLUE if winner == self.bot1.name else RED

        # Render the message
        font = pygame.font.SysFont("arial", 50)
        text_surface = font.render(message, True, color)
        text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        self.screen.blit(text_surface, text_rect)

        # Render the restart button
        button_font = pygame.font.SysFont("arial", 30)
        text = "CONTINUE" if has_more_matches else "EXIT"
        button_text = button_font.render(text, True, WHITE)
        button_rect = button_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
        pygame.draw.rect(self.screen, GRAY, button_rect.inflate(20, 10))
        self.screen.blit(button_text, button_rect)

        pygame.display.flip()

        # Wait for user interaction
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if button_rect.collidepoint(event.pos):
                        return  # Exit the loop to restart the game

    def run(self, states: List[Dict[str, Any]], has_more_matches: bool) -> None:
        """Run the visualization for a sequence of game states."""
        if states:
            initial_state = states[0]
            self.info_bar_state = initial_state
            self.render_frame(initial_state, 0)
            self.wait_for(0.3)

        for state_index in range(len(states) - 1):
            curr = states[state_index]
            nxt = states[state_index + 1]
            self.animate_transition(curr, nxt, state_index)

            # Current animation wait
            self.wait_for(ANIMATION_DURATION)
            self.info_bar_state = nxt
            self.draw_wizard_info_bar()

        # Determine the winner
        final_state = states[-1]
        if final_state["self"]["hp"] > final_state["opponent"]["hp"]:
            winner = final_state["self"]["name"]
        elif final_state["self"]["hp"] < final_state["opponent"]["hp"]:
            winner = final_state["opponent"]["name"]
        else:
            winner = None

        # Display the end game message
        self.display_end_game_message(winner, has_more_matches)

    def animate_transition(self, curr_state: Dict[str, Any], next_state: Dict[str, Any], state_index: int) -> None:
        """Animate the transition between two game states."""
        # First half of animation: movement only
        move_steps = int(FPS * ANIMATION_DURATION / 2)
        damage_this_state = [d for d in self.logger.damage_events if d["state_index"] == state_index]

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
            self.draw_wizard_info_bar()

            # Interpolate wizards
            for wiz_key in ["self", "opponent"]:
                wiz_curr = curr_state[wiz_key]
                wiz_next = next_state[wiz_key]
                color = RED if wiz_curr["name"] == self.bot2.name else BLUE
                pos = self.interpolate(wiz_curr["position"], wiz_next["position"], progress)
                self.draw_unit(pos, color, "W", wiz_curr["name"])
                # Draw shield if active - use current state for first half of animation
                self.draw_active_shield(wiz_curr, pos)

            # Interpolate existing minions
            for i in range(min(len(curr_minions), len(existing_minions))):
                curr_m = curr_minions[i]
                next_m = existing_minions[i]
                color = RED if curr_m["owner"] == self.bot2.name else BLUE
                pos = self.interpolate(curr_m["position"], next_m["position"], progress)
                self.draw_unit(pos, color, "M", curr_m["owner"])

            # Static artifacts
            for artifact in curr_state.get("artifacts", []):
                self.draw_unit(artifact["position"], YELLOW, "A", artifact["type"])

            self.draw_info_bar(curr_state["turn"])
            pygame.display.flip()
            self.clock.tick(FPS)
            self.handle_events()

        # Second half: spell casting (entities at their final positions)
        spell_steps = int(FPS * ANIMATION_DURATION / 2)
        spell_effects = [s for s in self.logger.spells if s["state_index"] == state_index]

        for frame in range(spell_steps):
            progress = frame / spell_steps
            self.screen.fill(WHITE)
            self.render_frame(next_state, curr_state["turn"], skip_entities=True)

            # Draw wizards at final positions
            for wiz_key in ["self", "opponent"]:
                wiz_next = next_state[wiz_key]
                color = RED if wiz_next["name"] == self.bot2.name else BLUE
                self.draw_unit(wiz_next["position"], color, "W", wiz_next["name"])
                # Draw shield if active - use next state for second half of animation
                self.draw_active_shield(wiz_next, wiz_next["position"])

            # Draw existing minions
            for m in existing_minions:
                color = RED if m["owner"] == self.bot2.name else BLUE
                self.draw_unit(m["position"], color, "M", m["owner"])

            new_minions = [m for m in next_minions if not any(cm["id"] == m["id"] for cm in curr_minions)]

            for m in new_minions:
                color = RED if m["owner"] == self.bot2.name else BLUE
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
                caster_data = next_state["self"] if next_state["self"]["name"] == caster_name else next_state["opponent"]
                caster_pos = caster_data["position"]

                if spell_name == "shield":
                    self.draw_shield_effect(caster_pos)
                elif spell_name == "heal":
                    self.draw_heal_effect(caster_pos)
                elif spell_name == "melee_attack":
                    if target:
                        # Calculate progress for attack animation
                        self.draw_melee_attack(target, progress)

                        if progress > 0.8:  # Show hit text near the end of animation
                            center = self.pixel_center(target)
                            result_text = "SWIPE!"
                            color = HIT_COLOR
                            result_surface = self.font.render(result_text, True, color)
                            result_rect = result_surface.get_rect(center=(center[0], center[1] - 50))
                            self.screen.blit(result_surface, result_rect)
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
                        color = HIT_COLOR if hit else MISS_COLOR
                        result_surface = self.font.render(result_text, True, color)
                        result_rect = result_surface.get_rect(center=(center[0], center[1] - 50))
                        self.screen.blit(result_surface, result_rect)
                elif spell_name == "teleport":
                    self.draw_teleport_pulse(caster_pos)

            for dmg in damage_this_state:
                if dmg["cause"] == "melee_attack":
                    position = dmg["position"]
                    self.draw_melee_attack(position, progress)
                center = self.pixel_center(dmg["position"])
                rise = int((1 - progress) * 20)  # float upward
                alpha = int(255 * (1 - progress))  # fade out
                dmg_text = self.font.render(f"-{dmg['amount']}", True, RED)
                dmg_text.set_alpha(alpha)
                self.screen.blit(dmg_text, (center[0] - 10, center[1] - 20 - rise))

            # Static artifacts
            for artifact in curr_state.get("artifacts", []):
                self.draw_unit(artifact["position"], YELLOW, "A", artifact["type"])

            self.draw_info_bar(curr_state["turn"])
            pygame.display.flip()
            self.clock.tick(FPS)
            self.handle_events()

    def handle_events(self) -> None:
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

    def interpolate(self, start: Position, end: Position, progress: float) -> Position:
        """Interpolate between two positions based on progress (0-1)."""
        sx, sy = start
        ex, ey = end
        x = sx + (ex - sx) * progress
        y = sy + (ey - sy) * progress
        return [x, y]

    def pixel_center(self, pos: Position) -> Tuple[int, int]:
        """Convert board position to pixel coordinates."""
        return (
            int(pos[0] * TILE_SIZE + TILE_SIZE // 2),
            int(pos[1] * TILE_SIZE + TILE_SIZE // 2 + INFO_BAR_HEIGHT)
        )

    def draw_shield_effect(self, pos: Position) -> None:
        """Draw shield effect animation."""
        center = self.pixel_center(pos)

        # We want a consistent shield appearance during casting
        scale = 1.0  # Full size immediately
        size = int(TILE_SIZE * scale)
        alpha = 220  # Fairly solid visibility

        # Scale the shield sprite
        scaled = pygame.transform.smoothscale(self.shield_sprite, (size, size))

        # Create a slight glow effect
        glow_surface = pygame.Surface((size * 1.5, size * 1.5), pygame.SRCALPHA)
        glow_radius = int(size * 0.8)  # Consistent radius
        glow_alpha = 120  # Consistent visibility

        # Draw a filled circle with transparency
        pygame.draw.circle(
            glow_surface,
            (*SHIELD_GLOW_COLOR, glow_alpha),  # Light blue with transparency
            (int(size * 1.5 / 2), int(size * 1.5 / 2)),
            glow_radius
        )

        # Draw the glow behind the shield
        glow_rect = glow_surface.get_rect(center=center)
        self.screen.blit(glow_surface, glow_rect)

        # Create a surface for the shield sprite
        sprite_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        sprite_surface.blit(scaled, (0, 0))
        sprite_surface.set_alpha(alpha)

        # Draw the shield sprite on top of the glow
        sprite_rect = sprite_surface.get_rect(center=center)
        self.screen.blit(sprite_surface, sprite_rect)

    def draw_heal_effect(self, pos: Position) -> None:
        """Draw heal effect animation."""
        center = self.pixel_center(pos)

        # Create an animation based on time
        t = pygame.time.get_ticks() / 1000.0  # Time in seconds

        # Create pulsing effect (0.5 to 1.0 scale)
        pulse = 0.5 + 0.5 * math.sin(t * HEAL_PULSE_RATE)

        # Create alpha/opacity effect (128 to 255)
        alpha = int(128 + 127 * math.sin(t * HEAL_ALPHA_RATE))

        # Scale the sprite
        scale = 0.8 + 0.2 * pulse  # Base size plus pulse effect
        size = int(TILE_SIZE * scale)

        # Create a temporary surface with per-pixel alpha
        temp = pygame.Surface((size, size), pygame.SRCALPHA)

        # Scale the heal sprite
        scaled = pygame.transform.smoothscale(self.heal_sprite, (size, size))

        # Set the alpha/transparency
        scaled.set_alpha(alpha)

        # Draw to temp surface
        temp.blit(scaled, (0, 0))

        # Draw temp surface centered on position
        rect = temp.get_rect(center=center)
        self.screen.blit(temp, rect)

        # Draw additional sparkle particles
        for i in range(HEAL_PARTICLE_COUNT):
            angle = t * 3 + (i * math.pi * 2 / HEAL_PARTICLE_COUNT)  # Rotating particles
            distance = TILE_SIZE / 3 * pulse
            particle_x = center[0] + math.cos(angle) * distance
            particle_y = center[1] + math.sin(angle) * distance
            particle_size = 3 + 2 * pulse

            # Small particles around the main sprite
            pygame.draw.circle(
                self.screen,
                (*HEAL_PARTICLE_COLOR, alpha),  # Light green with same alpha
                (int(particle_x), int(particle_y)),
                int(particle_size)
            )

    def draw_fireball_explosion(self, position: Position, progress: float) -> None:
        """Draw fireball explosion effect at the target position."""
        center = self.pixel_center(position)

        # Scale the explosion sprite based on progress (grow and fade out)
        scale = 0.8 + 1 * progress  # Start small and grow
        size = int(TILE_SIZE * scale)
        alpha = int(255 * (1 - progress))  # Fade out as progress increases

        # Scale the explosion sprite
        scaled_explosion = pygame.transform.smoothscale(self.fireball_explosion_sprite, (size, size))
        scaled_explosion.set_alpha(alpha)

        # Draw the explosion sprite centered at the target position
        rect = scaled_explosion.get_rect(center=center)
        self.screen.blit(scaled_explosion, rect)

    def draw_melee_attack(self, position: Position, progress: float) -> None:
        """Draw melee attack animation at the given position."""
        center = self.pixel_center(position)

        # Scale up at beginning, then scale down as the animation progresses
        if progress < 0.5:
            # First half: scale up
            scale = 0.2 + 1.6 * (progress * 2)  # Scale from 0.2 to 1.8
        else:
            # Second half: scale down
            scale = 1.8 - 1.6 * ((progress - 0.5) * 2)  # Scale from 1.8 to 0.2

        size = int(TILE_SIZE * scale)

        # Rotate the sprite a bit for dynamic effect
        angle = progress * 30  # Rotate up to 30 degrees

        # Create a temporary surface with per-pixel alpha
        temp = pygame.Surface((size, size), pygame.SRCALPHA)

        # Scale and rotate the melee sprite
        scaled = pygame.transform.smoothscale(self.melee_sprite, (size, size))
        rotated = pygame.transform.rotate(scaled, angle)

        # Set alpha based on progress (fully opaque in middle, transparent at beginning and end)
        alpha = int(255 * (1 - abs(progress - 0.5) * 2))
        rotated.set_alpha(alpha)

        # Draw to temp surface
        temp_rect = temp.get_rect(center=(temp.get_width() // 2, temp.get_height() // 2))
        temp.blit(rotated, temp_rect)

        # Draw temp surface centered on position
        rect = temp.get_rect(center=center)
        self.screen.blit(temp, rect)

    def draw_fireball(self, caster_pos: Position, target_pos: Position, progress: float) -> None:
        """Draw fireball effect animation."""
        x = caster_pos[0] + (target_pos[0] - caster_pos[0]) * progress
        y = caster_pos[1] + (target_pos[1] - caster_pos[1]) * progress
        center = self.pixel_center([x, y])

        # Compute angle and rotate sprite
        angle = self.angle_between(caster_pos, target_pos) + 90
        rotated = pygame.transform.rotate(self.fireball_sprite, angle)
        rect = rotated.get_rect(center=center)

        self.screen.blit(rotated, rect)

        # Add a trail effect - slightly transparent circles behind the fireball
        trail_length = FIREBALL_TRAIL_LENGTH
        for i in range(1, trail_length + 1):
            trail_progress = max(0.0, progress - i * 0.05)  # Progress for each trail segment
            if trail_progress > 0:
                tx = caster_pos[0] + (target_pos[0] - caster_pos[0]) * trail_progress
                ty = caster_pos[1] + (target_pos[1] - caster_pos[1]) * trail_progress
                trail_center = self.pixel_center([tx, ty])

                # Size and alpha decrease for trail parts farther from the fireball
                size = max(3, 8 - i * 1.5)
                alpha = max(20, 150 - i * 30)  # Gradually decreasing alpha

                # Create a transparent surface for the trail
                trail_surface = pygame.Surface((int(size*2), int(size*2)), pygame.SRCALPHA)
                pygame.draw.circle(
                    trail_surface,
                    (*FIREBALL_TRAIL_COLOR, alpha),  # Orange with fading transparency
                    (int(size), int(size)),
                    int(size)
                )
                trail_rect = trail_surface.get_rect(center=trail_center)
                self.screen.blit(trail_surface, trail_rect)

        # Draw explosion effect if progress is near the end
        if progress > 0.8:
            self.draw_fireball_explosion(target_pos, (progress - 0.8) / 0.2)

    def angle_between(self, start: Position, end: Position) -> float:
        """Calculate the angle between two positions in degrees."""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        angle_rad = math.atan2(-dy, dx)  # y-axis is inverted in screen coords
        return math.degrees(angle_rad)

    def draw_teleport_pulse(self, pos: Position) -> None:
        """Draw teleport effect animation."""
        center = self.pixel_center(pos)

        # Get animation time
        t = pygame.time.get_ticks() / 1000.0  # Time in seconds

        # Create a pulsing circle
        pulse = 0.2 + 0.8 * (1 + math.sin(t * TELEPORT_PULSE_RATE)) / 2  # Oscillate between 0.2 and 1.0
        radius = int(TILE_SIZE * 0.5 * pulse)

        # Fade based on the size
        alpha = int(180 * (1 - pulse))  # More transparent as it expands

        # Create a transparent surface
        glow = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        pygame.draw.circle(
            glow,
            (*TELEPORT_COLOR, alpha),
            (radius, radius),
            radius,
            2  # Line width
        )

        glow_rect = glow.get_rect(center=center)
        self.screen.blit(glow, glow_rect)

        # Add a smaller pulsing circle with reverse timing
        inner_pulse = 0.2 + 0.6 * (1 + math.sin(t * TELEPORT_PULSE_RATE + math.pi)) / 2  # Opposite phase
        inner_radius = int(TILE_SIZE * 0.3 * inner_pulse)
        inner_alpha = int(150 * (1 - inner_pulse))  # More transparent as it expands

        inner_glow = pygame.Surface((inner_radius*2, inner_radius*2), pygame.SRCALPHA)
        pygame.draw.circle(
            inner_glow,
            (*TELEPORT_COLOR, inner_alpha),
            (inner_radius, inner_radius),
            inner_radius,
            1  # Thinner line width
        )

        inner_rect = inner_glow.get_rect(center=center)
        self.screen.blit(inner_glow, inner_rect)

    def draw_active_shield(self, wizard_data: Dict[str, Any], position: Position) -> None:
        """Draw shield effect around a wizard if shield is active."""
        if wizard_data.get("shield_active", False):
            # Convert to pixel coordinates for shield drawing
            pixel_pos = self.pixel_center(position)

            # Use a constant appearance for continuous shield
            size = int(TILE_SIZE * 0.8)  # Fixed size for the shield

            # Draw a constant blue transparent circle around the wizard
            shield_radius = int(TILE_SIZE * 0.6)
            shield_alpha = 120  # Constant transparency value

            # Create a transparent surface for the shield circle
            shield_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                shield_surface,
                (*SHIELD_GLOW_COLOR, shield_alpha),  # Light blue with constant transparency
                (size, size),
                shield_radius,
                3  # Circle thickness
            )

            # Blit the shield surface directly without any time-based modulation
            shield_rect = shield_surface.get_rect(center=pixel_pos)
            self.screen.blit(shield_surface, shield_rect)

            # No longer drawing the shield sprite for active shield status
            # Only the blue circle remains visible


