"""
half_time.py — Half time screen.

Shows:
  • Score so far
  • First-half stats: possession, shots, goals
  • Team kit comparison
  • Countdown to second half (or manual continue)
  • Animated slide-in panels
"""

import pygame
import math
from src.core.base_screen import BaseScreen
from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    DARK_BG, GOLD, GOLD_LIGHT, ACCENT_CYAN,
    WHITE, BLACK, GREY_DARK, GREY_MID, GREY_LIGHT,
    STATE_MATCH,
)
from src.screens.team_select import draw_kit


class HalfTimeScreen(BaseScreen):

    def __init__(self, screen, change_state, match_data: dict):
        super().__init__(screen, change_state)
        """
        match_data keys:
          home_team, away_team   — full TEAMS tuples
          home_goals, away_goals — int
          home_poss              — float 0-100
          home_shots, away_shots — int
          first_scorers          — list of str
        """
        self.data      = match_data
        self.time      = 0.0
        self.slide_t   = 0.0       # 0→1 panel slide-in
        self.continue_timer = 12.0  # auto-continue after 12s

        self._init_fonts()
        self._bg = self._build_bg()

    def _init_fonts(self):
        bold = ["impact", "arial black", "bahnschrift", "freesansbold"]
        body = ["segoe ui", "calibri", "ubuntu", "freesans"]
        self.font_huge  = self._best_font(bold, 72, bold=True)
        self.font_lg    = self._best_font(bold, 36, bold=True)
        self.font_md    = self._best_font(body, 24, bold=True)
        self.font_sm    = self._best_font(body, 18)

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
            r = int(5  + t * 8)
            g = int(8  + t * 10)
            b = int(18 + t * 20)
            pygame.draw.line(surf, (r, g, b), (0, y), (self.width, y))
        return surf

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    self._continue_to_second_half()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                btn = pygame.Rect(self.width//2 - 130, self.height - 100, 260, 50)
                if btn.collidepoint(event.pos):
                    self._continue_to_second_half()

    def _continue_to_second_half(self):
        self.change_state(STATE_MATCH)

    def update(self, dt):
        self.time   += dt
        self.slide_t = min(1.0, self.slide_t + dt * 2.5)
        self.continue_timer -= dt
        if self.continue_timer <= 0:
            self._continue_to_second_half()

    def draw(self):
        s  = self.screen
        cx = self.width // 2
        s.blit(self._bg, (0, 0))

        # Scanlines
        for y in range(0, self.height, 3):
            pygame.draw.line(s, (0, 0, 0), (0, y), (self.width, y))

        # ── HALF TIME banner ──
        ease = self._ease_out(self.slide_t)

        banner_y = int(60 - (1 - ease) * 80)
        ht_surf  = self.font_huge.render("HALF TIME", True, GOLD)
        glow     = pygame.Surface(
            (ht_surf.get_width() + 40, ht_surf.get_height() + 20), pygame.SRCALPHA)
        glow.fill((212, 175, 55, 25))
        s.blit(glow, (cx - glow.get_width()//2, banner_y - 10))
        s.blit(ht_surf, ht_surf.get_rect(centerx=cx, top=banner_y))

        # Gold separator
        sep_w = int(500 * ease)
        pygame.draw.rect(s, GOLD,
                         (cx - sep_w//2, banner_y + ht_surf.get_height() + 8, sep_w, 2),
                         border_radius=1)

        # ── Score ──
        d  = self.data
        ht = d["home_team"]
        at = d["away_team"]

        score_y = 165
        # Home kit (small)
        draw_kit(s, cx - 260, score_y - 10, 60, 72, ht[2], ht[3], self.time)
        # Away kit (small)
        draw_kit(s, cx + 200, score_y - 10, 60, 72, at[2], at[3], self.time)

        # Team names
        hn = self.font_md.render(ht[0], True, GOLD)
        an = self.font_md.render(at[0], True, ACCENT_CYAN)
        s.blit(hn, hn.get_rect(right=cx - 80, centery=score_y + 30))
        s.blit(an, an.get_rect(left=cx  + 80, centery=score_y + 30))

        # Score digits
        score_txt = self.font_huge.render(
            f"{d['home_goals']}  —  {d['away_goals']}", True, WHITE)
        s.blit(score_txt, score_txt.get_rect(centerx=cx, centery=score_y + 36))

        # ── Stats panel (slides in from bottom) ──
        panel_y = int(self.height * (1 - ease) + 310 * ease)
        self._draw_stats_panel(s, cx, panel_y)

        # ── Goal scorers ──
        scorers = d.get("first_scorers", [])
        if scorers:
            sc_y = 305
            for line in scorers[:4]:
                sc = self.font_sm.render(f"⚽ {line}", True, GREY_LIGHT)
                s.blit(sc, sc.get_rect(centerx=cx, top=sc_y))
                sc_y += 22

        # ── Continue button ──
        self._draw_continue_btn(s, cx)

    def _draw_stats_panel(self, s, cx, top_y):
        panel_w = 560
        panel_h = 180
        panel   = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((12, 18, 32, 200))
        s.blit(panel, (cx - panel_w//2, top_y))
        pygame.draw.rect(s, GREY_DARK,
                         (cx - panel_w//2, top_y, panel_w, panel_h), 1, border_radius=4)

        d     = self.data
        stats = [
            ("POSSESSION",  f"{int(d['home_poss'])}%",
             f"{int(100 - d['home_poss'])}%", d["home_poss"] / 100),
            ("SHOTS",       str(d.get("home_shots", 0)),
             str(d.get("away_shots", 0)),
             d.get("home_shots", 0) / max(1, d.get("home_shots",0) + d.get("away_shots",0))),
            ("GOALS",       str(d["home_goals"]),
             str(d["away_goals"]),
             d["home_goals"] / max(1, d["home_goals"] + d["away_goals"])),
        ]

        row_h = 52
        for i, (label, home_val, away_val, home_frac) in enumerate(stats):
            y = top_y + 18 + i * row_h

            # Label
            lbl = self.font_sm.render(label, True, GREY_MID)
            s.blit(lbl, lbl.get_rect(centerx=cx, top=y))

            # Compare bar
            bar_w = 260
            bar_x = cx - bar_w // 2
            bar_y = y + 22
            bar_h = 14
            pygame.draw.rect(s, ACCENT_CYAN, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            hw = int(bar_w * home_frac)
            if hw > 0:
                pygame.draw.rect(s, GOLD, (bar_x, bar_y, hw, bar_h), border_radius=3)

            # Values
            hv = self.font_md.render(home_val, True, GOLD)
            av = self.font_md.render(away_val, True, ACCENT_CYAN)
            s.blit(hv, hv.get_rect(right=bar_x - 10, centery=bar_y + bar_h//2))
            s.blit(av, av.get_rect(left=bar_x + bar_w + 10, centery=bar_y + bar_h//2))

    def _draw_continue_btn(self, s, cx):
        btn_w, btn_h = 260, 50
        btn_rect = pygame.Rect(cx - btn_w//2, self.height - 100, btn_w, btn_h)
        hovered  = btn_rect.collidepoint(pygame.mouse.get_pos())
        pulse    = int(20 * math.sin(self.time * 3))
        color    = GOLD_LIGHT if hovered else GOLD

        pygame.draw.rect(s, color, btn_rect, border_radius=8)
        lbl = self.font_md.render("▶  SECOND HALF", True, BLACK)
        s.blit(lbl, lbl.get_rect(center=btn_rect.center))

        # Timer hint
        t_left = max(0, int(self.continue_timer) + 1)
        hint   = self.font_sm.render(
            f"Auto-continues in {t_left}s  •  ENTER or SPACE", True, GREY_MID)
        s.blit(hint, hint.get_rect(centerx=cx, top=self.height - 40))

    @staticmethod
    def _ease_out(t):
        return 1 - (1 - t) ** 3