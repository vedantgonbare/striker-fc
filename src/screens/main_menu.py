"""
main_menu.py — Animated FIFA-style main menu screen.

Visual design:
  • Dark navy background with a subtle animated pitch pattern
  • Gold animated title "STRIKER FC" with pulsing glow
  • Vertical stack of menu items with hover highlight + slide-in animation
  • Scanline overlay for cinematic feel
  • Floating particle dots that drift slowly (stadium atmosphere)
"""

import pygame
import math
import random
from src.core.base_screen import BaseScreen
from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    DARK_BG, GOLD, GOLD_LIGHT, ACCENT_CYAN,
    GREY_DARK, GREY_MID, GREY_LIGHT, WHITE, BLACK,
    PITCH_GREEN, PITCH_LIGHT,
    STATE_TEAM_SELECT, STATE_SETTINGS, STATE_QUIT,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    return a + (b - a) * t


class Particle:
    """Small floating dot for atmosphere."""
    def __init__(self, w, h):
        self.reset(w, h, first=True)
        self.w = w
        self.h = h

    def reset(self, w, h, first=False):
        self.x   = random.uniform(0, w)
        self.y   = random.uniform(0, h) if first else h + 5
        self.vy  = random.uniform(-0.3, -0.8)
        self.vx  = random.uniform(-0.2, 0.2)
        self.r   = random.uniform(1, 2.5)
        self.alpha = random.randint(30, 100)
        self.color = random.choice([(212, 175, 55), (0, 220, 200), (255, 255, 255)])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y < -10:
            self.reset(self.w, self.h)

    def draw(self, surf):
        s = pygame.Surface((int(self.r * 2 + 2), int(self.r * 2 + 2)), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, self.alpha), (int(self.r + 1), int(self.r + 1)), int(self.r))
        surf.blit(s, (int(self.x - self.r), int(self.y - self.r)))


class MenuItem:
    """A single animated menu button."""
    FONT_SIZE     = 34
    HOVER_COLOR   = GOLD_LIGHT
    NORMAL_COLOR  = (190, 200, 220)
    SELECT_COLOR  = ACCENT_CYAN

    def __init__(self, label: str, state_target: str, x: int, y: int, font: pygame.font.Font):
        self.label        = label
        self.target       = state_target
        self.x            = x
        self.y            = y
        self.font         = font
        self.hovered      = False
        self.selected     = False
        # slide-in animation
        self.offset_x     = -400.0
        self.slide_speed  = 0.12      # lerp factor per frame

    def update(self, dt: float, mouse_pos: tuple):
        # Slide in from left
        self.offset_x = lerp(self.offset_x, 0, self.slide_speed + dt * 2)

        # Hover detection
        rendered = self.font.render(self.label, True, WHITE)
        rx = self.x + self.offset_x
        rect = rendered.get_rect(midleft=(rx, self.y))
        self.hovered = rect.collidepoint(mouse_pos)

    def draw(self, surf: pygame.Surface):
        color = self.HOVER_COLOR if self.hovered else self.NORMAL_COLOR
        rx = int(self.x + self.offset_x)

        # Glow bar on hover
        if self.hovered:
            bar = pygame.Surface((320, 48), pygame.SRCALPHA)
            bar.fill((212, 175, 55, 25))
            surf.blit(bar, (rx - 12, self.y - 24))
            # left accent line
            pygame.draw.rect(surf, GOLD, (rx - 16, self.y - 20, 4, 40), border_radius=2)

        # Label
        text = self.font.render(self.label, True, color)
        surf.blit(text, text.get_rect(midleft=(rx, self.y)))

        # Underline on hover
        if self.hovered:
            tw = text.get_width()
            pygame.draw.rect(surf, GOLD_LIGHT, (rx, self.y + 18, int(tw * 0.9), 2), border_radius=1)


# ── Main Menu Screen ─────────────────────────────────────────────────────────

class MainMenuScreen(BaseScreen):

    MENU_ITEMS = [
        ("KICK OFF",     STATE_TEAM_SELECT),
        ("TOURNAMENT",   None),           # stub
        ("CAREER MODE",  None),           # stub
        ("SETTINGS",     STATE_SETTINGS),
        ("QUIT",         STATE_QUIT),
    ]

    def __init__(self, screen, change_state):
        super().__init__(screen, change_state)

        # ── Fonts ──
        self._init_fonts()

        # ── Time / animation ──
        self.time      = 0.0          # accumulated seconds
        self.title_scale = 1.0

        # ── Particles ──
        self.particles = [Particle(self.width, self.height) for _ in range(60)]

        # ── Menu items ──
        start_x = 110
        start_y = 310
        gap     = 68
        self.items = [
            MenuItem(label, target, start_x, start_y + i * gap, self.font_menu)
            for i, (label, target) in enumerate(self.MENU_ITEMS)
        ]
        # stagger slide-in
        for i, item in enumerate(self.items):
            item.offset_x = -400 - i * 80

        # ── Static surfaces (drawn once) ──
        self._bg_surf    = self._build_background()
        self._pitch_surf = self._build_pitch_overlay()
        self._scan_surf  = self._build_scanlines()

        # ── Cursor tracking ──
        self.mouse_pos = (0, 0)

    # ── Font init ──────────────────────────────────────────────────────────
    def _init_fonts(self):
        """Try system fonts; fall back gracefully."""
        candidates_title = ["impact", "arial black", "bahnschrift", "freesansbold"]
        candidates_body  = ["segoe ui", "calibri", "ubuntu", "freesans"]

        self.font_title  = self._best_font(candidates_title, 96, bold=True)
        self.font_sub    = self._best_font(candidates_body,  18)
        self.font_menu   = self._best_font(candidates_body,  34, bold=True)
        self.font_small  = self._best_font(candidates_body,  14)

    @staticmethod
    def _best_font(candidates, size, bold=False):
        for name in candidates:
            try:
                f = pygame.font.SysFont(name, size, bold=bold)
                return f
            except Exception:
                continue
        return pygame.font.Font(None, size)

    # ── Static surface builders ───────────────────────────────────────────
    def _build_background(self) -> pygame.Surface:
        surf = pygame.Surface((self.width, self.height))
        # Gradient: top dark navy → bottom slightly lighter
        for y in range(self.height):
            t = y / self.height
            r = int(8  + t * 6)
            g = int(12 + t * 8)
            b = int(20 + t * 15)
            pygame.draw.line(surf, (r, g, b), (0, y), (self.width, y))
        return surf

    def _build_pitch_overlay(self) -> pygame.Surface:
        """Faint pitch lines on the right half for visual depth."""
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Right-side pitch area (perspective-ish rectangle)
        pitch_rect = pygame.Rect(520, 80, 730, 560)
        alpha = 18

        # Fill
        fill = pygame.Surface((pitch_rect.w, pitch_rect.h), pygame.SRCALPHA)
        fill.fill((34, 85, 34, alpha))
        surf.blit(fill, pitch_rect.topleft)

        # Horizontal stripes (alternating light/dark bands)
        stripe_h = 56
        for i in range(10):
            if i % 2 == 0:
                s = pygame.Surface((pitch_rect.w, stripe_h), pygame.SRCALPHA)
                s.fill((40, 100, 40, 12))
                surf.blit(s, (pitch_rect.x, pitch_rect.y + i * stripe_h))

        line_color = (255, 255, 255, 30)

        # Outer boundary
        pygame.draw.rect(surf, line_color, pitch_rect, 2)

        # Centre line (vertical)
        cx = pitch_rect.centerx
        pygame.draw.line(surf, line_color, (cx, pitch_rect.top), (cx, pitch_rect.bottom), 1)

        # Centre circle
        pygame.draw.circle(surf, line_color, pitch_rect.center, 70, 1)
        pygame.draw.circle(surf, line_color, pitch_rect.center, 4)

        # Penalty box left
        pb_w, pb_h = 160, 260
        pb_x = pitch_rect.left
        pb_y = pitch_rect.centery - pb_h // 2
        pygame.draw.rect(surf, line_color, (pb_x, pb_y, pb_w, pb_h), 1)

        # Penalty box right
        pb_x2 = pitch_rect.right - pb_w
        pygame.draw.rect(surf, line_color, (pb_x2, pb_y, pb_w, pb_h), 1)

        # Corner arcs
        r = 18
        corners = [
            (pitch_rect.left,  pitch_rect.top),
            (pitch_rect.right, pitch_rect.top),
            (pitch_rect.left,  pitch_rect.bottom),
            (pitch_rect.right, pitch_rect.bottom),
        ]
        for cx2, cy2 in corners:
            pygame.draw.circle(surf, line_color, (cx2, cy2), r, 1)

        return surf

    def _build_scanlines(self) -> pygame.Surface:
        """Subtle horizontal scanlines for cinematic feel."""
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(0, self.height, 3):
            pygame.draw.line(surf, (0, 0, 0, 18), (0, y), (self.width, y))
        return surf

    # ── Event handling ────────────────────────────────────────────────────
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for item in self.items:
                    if item.hovered and item.target:
                        self.change_state(item.target)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.change_state(STATE_QUIT)

    # ── Update ───────────────────────────────────────────────────────────
    def update(self, dt: float):
        self.time += dt

        # Title pulse
        self.title_scale = 1.0 + 0.012 * math.sin(self.time * 1.8)

        for p in self.particles:
            p.update()

        for item in self.items:
            item.update(dt, self.mouse_pos)

    # ── Draw ─────────────────────────────────────────────────────────────
    def draw(self):
        s = self.screen

        # 1. Background gradient
        s.blit(self._bg_surf, (0, 0))

        # 2. Pitch overlay
        s.blit(self._pitch_surf, (0, 0))

        # 3. Particles
        for p in self.particles:
            p.draw(s)

        # 4. Left panel dark overlay
        panel = pygame.Surface((500, self.height), pygame.SRCALPHA)
        panel.fill((5, 8, 16, 190))
        s.blit(panel, (0, 0))

        # 5. Gold vertical accent bar
        pygame.draw.rect(s, GOLD, (88, 60, 3, self.height - 120), border_radius=2)

        # 6. Animated title
        self._draw_title(s)

        # 7. Menu items
        for item in self.items:
            item.draw(s)

        # 8. Bottom bar
        self._draw_bottom_bar(s)

        # 9. Scanlines (on top of everything)
        s.blit(self._scan_surf, (0, 0))

        # 10. Animated right-side glow
        self._draw_right_glow(s)

    def _draw_title(self, surf: pygame.Surface):
        # Glow layers
        title_text = "STRIKER FC"
        glow_alpha = int(80 + 40 * math.sin(self.time * 2))
        for radius in [28, 18, 10]:
            glow_surf = self.font_title.render(title_text, True, (*GOLD, 0))
            glow_surf = self.font_title.render(title_text, True, GOLD)
            w, h = glow_surf.get_size()
            blurred = pygame.Surface((w + radius * 2, h + radius * 2), pygame.SRCALPHA)
            col = (*GOLD, glow_alpha // (radius // 6 + 1))
            glow_base = self.font_title.render(title_text, True, col[:3])
            glow_base.set_alpha(glow_alpha // (radius // 8 + 1))
            blurred.blit(glow_base, (radius, radius))
            surf.blit(blurred, (100 - radius, 160 - radius))

        # Main title with subtle scale pulse
        title_surf = self.font_title.render(title_text, True, GOLD_LIGHT)
        w, h = title_surf.get_size()
        scaled_w = int(w * self.title_scale)
        scaled_h = int(h * self.title_scale)
        scaled = pygame.transform.smoothscale(title_surf, (scaled_w, scaled_h))
        surf.blit(scaled, (100 - (scaled_w - w) // 2, 160 - (scaled_h - h) // 2))

        # Subtitle
        sub = self.font_sub.render("THE BEAUTIFUL GAME", True, GREY_LIGHT)
        surf.blit(sub, (102, 270))

        # Thin separator line
        pygame.draw.rect(surf, GOLD, (100, 292, 220, 1))

    def _draw_bottom_bar(self, surf: pygame.Surface):
        bar = pygame.Surface((self.width, 36), pygame.SRCALPHA)
        bar.fill((5, 8, 16, 210))
        surf.blit(bar, (0, self.height - 36))

        # Left: controls hint
        hint = self.font_small.render("MOUSE to navigate  •  ESC to quit", True, GREY_MID)
        surf.blit(hint, (16, self.height - 24))

        # Right: version
        ver = self.font_small.render("v0.1.0  ALPHA", True, GREY_MID)
        surf.blit(ver, (self.width - ver.get_width() - 16, self.height - 24))

    def _draw_right_glow(self, surf: pygame.Surface):
        """Animated gold/cyan edge glow on the right side."""
        t = self.time
        alpha = int(30 + 20 * math.sin(t * 0.7))
        glow = pygame.Surface((80, self.height), pygame.SRCALPHA)
        for x in range(80):
            a = int(alpha * (1 - x / 80))
            pygame.draw.line(glow, (*GOLD, a), (x, 0), (x, self.height))
        surf.blit(glow, (self.width - 80, 0))