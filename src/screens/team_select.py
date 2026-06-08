"""
team_select.py — Full FIFA-style team selection screen.

Layout:
  LEFT PANEL   — Home team selector (keyboard: A/D to scroll, ENTER to lock)
  CENTRE PANEL — VS display, kit preview comparison, KICK OFF button
  RIGHT PANEL  — Away team selector (keyboard: LEFT/RIGHT to scroll, ENTER to lock)

Mouse: click arrows or team cards directly.
"""

import pygame
import math
from src.core.base_screen import BaseScreen
from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    DARK_BG, GOLD, GOLD_LIGHT, ACCENT_CYAN,
    WHITE, BLACK, GREY_DARK, GREY_MID, GREY_LIGHT,
    STATE_MAIN_MENU, STATE_MATCH,
)
from src.core.sound_engine import SoundEngine

# ── 20 Teams data ─────────────────────────────────────────────────────────────
# Each: (name, short, primary_rgb, secondary_rgb, overall, pace, shoot, pass, defend, formation)
TEAMS = [
    ("Manchester City",  "MCI", (108,171,221), (255,255,255), 88, 84, 85, 90, 82, "4-3-3"),
    ("Real Madrid",      "RMA", (255,255,255), (0,  70, 153), 87, 82, 86, 88, 80, "4-3-3"),
    ("Bayern Munich",    "BAY", (220, 30,  30), (0,  0,  0),  87, 83, 87, 86, 82, "4-2-3-1"),
    ("Liverpool",        "LIV", (200, 16,  46), (240,180, 10), 85, 85, 83, 84, 79, "4-3-3"),
    ("PSG",              "PSG", (0,   35,  97), (237,139, 0),  85, 83, 86, 82, 76, "4-3-3"),
    ("Chelsea",          "CHE", (3,   70, 148), (255,255,255), 82, 80, 79, 82, 80, "3-4-3"),
    ("Arsenal",          "ARS", (239, 41,  41), (255,255,255), 83, 83, 82, 83, 79, "4-3-3"),
    ("Barcelona",        "BAR", (165,  0,  33), (0,  82, 147), 82, 81, 83, 87, 76, "4-3-3"),
    ("Atletico Madrid",  "ATM", (230, 50,  30), (255,255,255), 82, 78, 79, 80, 86, "4-4-2"),
    ("Juventus",         "JUV", (255,255,255), (0,  0,  0),   81, 78, 81, 80, 83, "4-4-2"),
    ("Inter Milan",      "INT", (0,   55, 150), (0,  0,  0),  82, 79, 81, 81, 82, "3-5-2"),
    ("AC Milan",         "ACM", (163,  0,  20), (0,  0,  0),  80, 79, 80, 79, 80, "4-2-3-1"),
    ("Borussia Dortmund","BVB", (255,205,  0),  (0,  0,  0),  80, 84, 80, 79, 76, "4-2-3-1"),
    ("Tottenham",        "TOT", (19,  34,  87), (255,255,255), 78, 80, 78, 78, 76, "4-3-3"),
    ("Manchester Utd",   "MUN", (218, 41,  28), (255,255,255), 78, 78, 78, 77, 77, "4-2-3-1"),
    ("Napoli",           "NAP", (0,  163, 218), (255,255,255), 80, 81, 81, 80, 78, "4-3-3"),
    ("Porto",            "POR", (0,   64, 122), (255,255,255), 78, 79, 77, 78, 79, "4-4-2"),
    ("Ajax",             "AJX", (255,255,255), (210, 35,  42), 77, 82, 77, 79, 75, "4-3-3"),
    ("Benfica",          "BEN", (200, 16,  46), (255,255,255), 77, 79, 77, 77, 77, "4-4-2"),
    ("Celtic",           "CEL", (22, 135,  56), (255,255,255), 74, 78, 73, 75, 74, "4-3-3"),
]

STAT_LABELS = ["OVR", "PAC", "SHO", "PAS", "DEF"]


# ── Kit renderer ──────────────────────────────────────────────────────────────

def draw_kit(surf, x, y, w, h, primary, secondary, animated_t=0.0):
    """Draw a stylised football shirt shape."""
    # Shirt body
    body = pygame.Rect(x + w//6, y + h//4, w*2//3, h*3//4)
    pygame.draw.rect(surf, primary, body, border_radius=6)

    # Sleeves
    sleeve_h = h // 5
    pygame.draw.rect(surf, primary,
                     pygame.Rect(x, y + h//4, w//6 + 4, sleeve_h), border_radius=4)
    pygame.draw.rect(surf, primary,
                     pygame.Rect(x + w*5//6 - 4, y + h//4, w//6 + 4, sleeve_h), border_radius=4)

    # Collar
    collar_w = w // 4
    collar_rect = pygame.Rect(x + w//2 - collar_w//2, y + h//4 - 6, collar_w, 14)
    pygame.draw.rect(surf, secondary, collar_rect, border_radius=4)

    # Stripe (secondary colour band down centre)
    stripe_w = max(6, w // 8)
    stripe = pygame.Rect(x + w//2 - stripe_w//2, y + h//4, stripe_w, h*3//4)
    stripe = stripe.clip(body)
    pygame.draw.rect(surf, secondary, stripe)

    # Shimmer highlight (animated)
    shimmer_alpha = int(40 + 30 * math.sin(animated_t * 2))
    shimmer = pygame.Surface((body.width, body.height), pygame.SRCALPHA)
    for i in range(0, body.width // 2, 2):
        a = max(0, shimmer_alpha - i * 3)
        pygame.draw.line(shimmer, (255,255,255,a), (i, 0), (i, body.height))
    surf.blit(shimmer, body.topleft)

    # Outline
    pygame.draw.rect(surf, (0,0,0,80), body, 2, border_radius=6)


# ── Stat bar ──────────────────────────────────────────────────────────────────

def draw_stat_bar(surf, x, y, w, h, value, label, font, bar_color, t=0.0):
    """Draw a labelled animated stat bar."""
    animated_val = min(value, int(value * min(1.0, t * 3)))
    fill_w = int(w * animated_val / 100)

    # Background track
    pygame.draw.rect(surf, (30, 35, 50), (x, y, w, h), border_radius=3)
    # Fill
    if fill_w > 0:
        pygame.draw.rect(surf, bar_color, (x, y, fill_w, h), border_radius=3)
    # Label
    lbl = font.render(label, True, GREY_LIGHT)
    surf.blit(lbl, (x - lbl.get_width() - 6, y - 1))
    # Value
    val_txt = font.render(str(value), True, WHITE)
    surf.blit(val_txt, (x + w + 5, y - 1))


# ── Team panel ────────────────────────────────────────────────────────────────

class TeamPanel:
    """One side (Home or Away) of the team selection screen."""

    ARROW_W = 32

    def __init__(self, screen, x, w, side, font_lg, font_md, font_sm):
        self.screen   = screen
        self.x        = x          # left edge of this panel
        self.w        = w
        self.h        = WINDOW_HEIGHT
        self.side     = side       # "HOME" or "AWAY"
        self.font_lg  = font_lg
        self.font_md  = font_md
        self.font_sm  = font_sm

        self.index    = 0 if side == "HOME" else 3
        self.locked   = False
        self.time     = 0.0
        self.anim_t   = 0.0        # 0→1 slide-in per team change
        self.prev_idx = self.index

        # Arrow rects for click detection
        self.arrow_left  = pygame.Rect(x + 8,       310, self.ARROW_W, 40)
        self.arrow_right = pygame.Rect(x + w - 40,  310, self.ARROW_W, 40)

    @property
    def team(self):
        return TEAMS[self.index]

    def next_team(self):
        if not self.locked:
            self.prev_idx = self.index
            self.index = (self.index + 1) % len(TEAMS)
            self.anim_t = 0.0

    def prev_team(self):
        if not self.locked:
            self.prev_idx = self.index
            self.index = (self.index - 1) % len(TEAMS)
            self.anim_t = 0.0

    def toggle_lock(self):
        self.locked = not self.locked

    def handle_click(self, pos):
        if self.arrow_left.collidepoint(pos):
            self.prev_team()
        elif self.arrow_right.collidepoint(pos):
            self.next_team()

    def update(self, dt):
        self.time  += dt
        self.anim_t = min(1.0, self.anim_t + dt * 4)

    def draw(self):
        s  = self.screen
        cx = self.x + self.w // 2
        t  = self.team

        # Panel background
        panel = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        panel.fill((*DARK_BG, 210))
        s.blit(panel, (self.x, 0))

        # Side label (HOME / AWAY)
        side_color = GOLD if self.side == "HOME" else ACCENT_CYAN
        side_lbl = self.font_sm.render(self.side, True, side_color)
        s.blit(side_lbl, side_lbl.get_rect(centerx=cx, top=18))
        pygame.draw.rect(s, side_color, (self.x + 30, 38, self.w - 60, 2), border_radius=1)

        # Kit (animated slide)
        kit_w, kit_h = 120, 140
        slide_offset = int((1.0 - self.anim_t) * 60)
        kit_x = cx - kit_w // 2
        kit_y = 60 + slide_offset
        draw_kit(s, kit_x, kit_y, kit_w, kit_h, t[2], t[3], self.time)

        # Lock glow
        if self.locked:
            glow = pygame.Surface((kit_w + 20, kit_h + 20), pygame.SRCALPHA)
            alpha = int(60 + 40 * math.sin(self.time * 3))
            pygame.draw.rect(glow, (*side_color, alpha),
                             (0, 0, kit_w+20, kit_h+20), 3, border_radius=8)
            s.blit(glow, (kit_x - 10, kit_y - 10))

        # Team name
        name_surf = self.font_lg.render(t[0], True, WHITE)
        # scale down if too wide
        if name_surf.get_width() > self.w - 20:
            scale = (self.w - 20) / name_surf.get_width()
            name_surf = pygame.transform.smoothscale(
                name_surf,
                (int(name_surf.get_width() * scale), int(name_surf.get_height() * scale))
            )
        s.blit(name_surf, name_surf.get_rect(centerx=cx, top=215))

        # Formation badge
        form_surf = self.font_sm.render(t[9], True, side_color)
        s.blit(form_surf, form_surf.get_rect(centerx=cx, top=252))

        # Arrows
        self._draw_arrow(s, self.arrow_left,  "◀")
        self._draw_arrow(s, self.arrow_right, "▶")

        # Stat bars
        stats    = [t[4], t[5], t[6], t[7], t[8]]   # OVR PAC SHO PAS DEF
        bar_x    = self.x + 70
        bar_w    = self.w - 110
        bar_y    = 290
        bar_gap  = 36
        bar_color = side_color

        for i, (lbl, val) in enumerate(zip(STAT_LABELS, stats)):
            draw_stat_bar(s, bar_x, bar_y + i * bar_gap, bar_w, 14,
                          val, lbl, self.font_sm, bar_color, self.anim_t)

        # Team list (mini scroll)
        self._draw_team_list(s, cx)

        # Lock/Unlock button
        self._draw_lock_btn(s, cx, side_color)

    def _draw_arrow(self, s, rect, symbol):
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        color   = GOLD_LIGHT if hovered else GREY_MID
        lbl = self.font_md.render(symbol, True, color)
        s.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_team_list(self, s, cx):
        """Show 5 teams centred on current index."""
        y_start = 490
        visible = 5
        half    = visible // 2

        for offset in range(-half, half + 1):
            idx  = (self.index + offset) % len(TEAMS)
            team = TEAMS[idx]
            y    = y_start + offset * 30

            if offset == 0:
                # Highlighted row
                pygame.draw.rect(s, GREY_DARK,
                                 (self.x + 10, y - 12, self.w - 20, 26), border_radius=4)
                color = WHITE
            else:
                alpha = max(40, 180 - abs(offset) * 60)
                color = (alpha, alpha, alpha)

            # Kit dot
            dot_x = self.x + 28
            pygame.draw.circle(s, team[2], (dot_x, y + 3), 6)
            pygame.draw.circle(s, team[3], (dot_x, y + 3), 6, 2)

            name = self.font_sm.render(team[0], True, color)
            s.blit(name, (self.x + 40, y - 8))

    def _draw_lock_btn(self, s, cx, color):
        btn_w, btn_h = 140, 36
        btn_rect = pygame.Rect(cx - btn_w // 2, 650, btn_w, btn_h)
        hovered  = btn_rect.collidepoint(pygame.mouse.get_pos())

        if self.locked:
            pygame.draw.rect(s, color, btn_rect, border_radius=6)
            lbl = self.font_sm.render("✓ LOCKED IN", True, BLACK)
        else:
            pygame.draw.rect(s, GREY_DARK, btn_rect, border_radius=6)
            pygame.draw.rect(s, color if hovered else GREY_MID, btn_rect, 2, border_radius=6)
            lbl = self.font_sm.render("LOCK IN", True, color if hovered else GREY_LIGHT)

        s.blit(lbl, lbl.get_rect(center=btn_rect.center))
        return btn_rect


# ── Main Team Select Screen ───────────────────────────────────────────────────

class TeamSelectScreen(BaseScreen):

    def __init__(self, screen, change_state, on_confirm=None):
        super().__init__(screen, change_state)
        self._on_confirm = on_confirm   # callback(home_team, away_team)
        self._init_fonts()
        self.time = 0.0

        panel_w = 360
        self.home_panel = TeamPanel(screen, 0,                   panel_w,
                                    "HOME", self.font_lg, self.font_md, self.font_sm)
        self.away_panel = TeamPanel(screen, WINDOW_WIDTH - panel_w, panel_w,
                                    "AWAY", self.font_lg, self.font_md, self.font_sm)

        self._bg    = self._build_bg()
        self._scan  = self._build_scanlines()

        # Kick off button
        self.kickoff_rect = pygame.Rect(
            WINDOW_WIDTH // 2 - 110, WINDOW_HEIGHT - 80, 220, 50)

    def _init_fonts(self):
        cands_bold = ["impact", "arial black", "bahnschrift", "freesansbold"]
        cands_body = ["segoe ui", "calibri", "ubuntu", "freesans"]
        self.font_lg  = self._best_font(cands_bold, 30, bold=True)
        self.font_md  = self._best_font(cands_body, 30, bold=True)
        self.font_sm  = self._best_font(cands_body, 17)
        self.font_vs  = self._best_font(cands_bold, 72, bold=True)
        self.font_ttl = self._best_font(cands_bold, 22, bold=True)

    @staticmethod
    def _best_font(candidates, size, bold=False):
        for name in candidates:
            try:
                return pygame.font.SysFont(name, size, bold=bold)
            except Exception:
                continue
        return pygame.font.Font(None, size)

    def _build_bg(self):
        surf = pygame.Surface((self.width, self.height))
        for y in range(self.height):
            t = y / self.height
            r = int(8  + t * 5)
            g = int(12 + t * 8)
            b = int(25 + t * 18)
            pygame.draw.line(surf, (r, g, b), (0, y), (self.width, y))
        return surf

    def _build_scanlines(self):
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(0, self.height, 3):
            pygame.draw.line(surf, (0, 0, 0, 14), (0, y), (self.width, y))
        return surf

    # ── Events ───────────────────────────────────────────────────────────────
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                # Home panel: A / D
                if event.key == pygame.K_a:
                    self.home_panel.prev_team()
                elif event.key == pygame.K_d:
                    self.home_panel.next_team()
                elif event.key == pygame.K_q:
                    self.home_panel.toggle_lock()

                # Away panel: LEFT / RIGHT
                elif event.key == pygame.K_LEFT:
                    self.away_panel.prev_team()
                elif event.key == pygame.K_RIGHT:
                    self.away_panel.next_team()
                elif event.key == pygame.K_RSHIFT:
                    self.away_panel.toggle_lock()

                elif event.key == pygame.K_RETURN:
                    if self.home_panel.locked and self.away_panel.locked:
                        self._confirm_and_start()
                elif event.key == pygame.K_ESCAPE:
                    SoundEngine.get().play("ui_select")
                    self.change_state(STATE_MAIN_MENU)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                # Arrow clicks
                self.home_panel.handle_click(pos)
                self.away_panel.handle_click(pos)

                # Lock buttons
                home_btn = pygame.Rect(
                    self.home_panel.x + self.home_panel.w//2 - 70, 650, 140, 36)
                away_btn = pygame.Rect(
                    self.away_panel.x + self.away_panel.w//2 - 70, 650, 140, 36)
                if home_btn.collidepoint(pos):
                    SoundEngine.get().play("ui_select")
                    self.home_panel.toggle_lock()
                if away_btn.collidepoint(pos):
                    SoundEngine.get().play("ui_select")
                    self.away_panel.toggle_lock()

                # Kick off
                if self.kickoff_rect.collidepoint(pos):
                    if self.home_panel.locked and self.away_panel.locked:
                        self._confirm_and_start()

    def _confirm_and_start(self):
        SoundEngine.get().play("whistle", channel=1)
        if self._on_confirm:
            self._on_confirm(
                TEAMS[self.home_panel.index],
                TEAMS[self.away_panel.index],
            )
        self.change_state(STATE_MATCH)

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, dt):
        self.time += dt
        self.home_panel.update(dt)
        self.away_panel.update(dt)

    # ── Draw ─────────────────────────────────────────────────────────────────
    def draw(self):
        s = self.screen
        s.blit(self._bg, (0, 0))

        self.home_panel.draw()
        self.away_panel.draw()

        self._draw_centre(s)
        s.blit(self._scan, (0, 0))

    def _draw_centre(self, s):
        cx = self.width // 2
        panel_w = 360

        # Centre region
        centre_x = panel_w
        centre_w = self.width - panel_w * 2

        # Title
        title = self.font_ttl.render("SELECT YOUR TEAMS", True, GREY_MID)
        s.blit(title, title.get_rect(centerx=cx, top=20))

        # VS text
        vs_alpha = int(180 + 60 * math.sin(self.time * 1.5))
        vs_surf  = self.font_vs.render("VS", True, GOLD)
        vs_surf.set_alpha(vs_alpha)
        s.blit(vs_surf, vs_surf.get_rect(centerx=cx, centery=160))

        # Kit comparison (large, centre)
        ht = self.home_panel.team
        at = self.away_panel.team
        kit_w, kit_h = 90, 110
        gap = 40

        home_kit_x = cx - gap - kit_w
        away_kit_x = cx + gap
        kit_y      = 230

        draw_kit(s, home_kit_x, kit_y, kit_w, kit_h, ht[2], ht[3], self.time)
        draw_kit(s, away_kit_x, kit_y, kit_w, kit_h, at[2], at[3], self.time)

        # Team short names under kits
        hn = self.font_md.render(ht[1], True, GOLD)
        an = self.font_md.render(at[1], True, ACCENT_CYAN)
        s.blit(hn, hn.get_rect(centerx=home_kit_x + kit_w//2, top=kit_y + kit_h + 6))
        s.blit(an, an.get_rect(centerx=away_kit_x + kit_w//2, top=kit_y + kit_h + 6))

        # OVR comparison bar
        self._draw_ovr_compare(s, cx, ht[4], at[4])

        # Controls hint
        hints = [
            ("A / D", "Home team"),
            ("Q",     "Lock Home"),
            ("◀ ▶",   "Away team"),
            ("RSHIFT","Lock Away"),
        ]
        hint_y = 430
        for key, desc in hints:
            key_s  = self.font_sm.render(key, True, GOLD)
            desc_s = self.font_sm.render(desc, True, GREY_MID)
            s.blit(key_s,  key_s.get_rect(right=cx - 6,  top=hint_y))
            s.blit(desc_s, desc_s.get_rect(left=cx + 6,  top=hint_y))
            hint_y += 26

        # Kick off button
        both_locked = self.home_panel.locked and self.away_panel.locked
        self._draw_kickoff_btn(s, cx, both_locked)

    def _draw_ovr_compare(self, s, cx, home_ovr, away_ovr):
        """Horizontal compare bar between two OVR ratings."""
        y    = 395
        total_w = 200
        bar_h   = 18

        lbl = self.font_sm.render("OVR", True, GREY_MID)
        s.blit(lbl, lbl.get_rect(centerx=cx, top=y - 20))

        # Background
        pygame.draw.rect(s, (25, 30, 45),
                         (cx - total_w//2, y, total_w, bar_h), border_radius=4)

        total = home_ovr + away_ovr
        home_w = int(total_w * home_ovr / total)

        # Home side (gold, left)
        if home_w > 0:
            pygame.draw.rect(s, GOLD,
                             (cx - total_w//2, y, home_w, bar_h), border_radius=4)
        # Away side (cyan, right)
        away_w = total_w - home_w
        if away_w > 0:
            pygame.draw.rect(s, ACCENT_CYAN,
                             (cx - total_w//2 + home_w, y, away_w, bar_h), border_radius=4)

        # Numbers
        hn = self.font_sm.render(str(home_ovr), True, GOLD)
        an = self.font_sm.render(str(away_ovr), True, ACCENT_CYAN)
        s.blit(hn, hn.get_rect(right=cx - total_w//2 - 8, centery=y + bar_h//2))
        s.blit(an, an.get_rect(left=cx  + total_w//2 + 8, centery=y + bar_h//2))

    def _draw_kickoff_btn(self, s, cx, active):
        rect    = self.kickoff_rect
        hovered = rect.collidepoint(pygame.mouse.get_pos())

        if active:
            pulse = int(30 * math.sin(self.time * 4))
            color = (
                min(255, GOLD[0] + pulse),
                min(255, GOLD[1] + pulse),
                min(255, GOLD[2] + pulse),
            )
            pygame.draw.rect(s, color, rect, border_radius=8)
            lbl = self.font_md.render("⚽  KICK OFF", True, BLACK)
        else:
            pygame.draw.rect(s, GREY_DARK, rect, border_radius=8)
            pygame.draw.rect(s, GREY_MID,  rect, 2, border_radius=8)
            lbl = self.font_sm.render("Lock both teams to start", True, GREY_MID)

        s.blit(lbl, lbl.get_rect(center=rect.center))