"""
full_time.py — Full time / match result screen.

Shows:
  • Final score with winner highlight
  • Full match stats (possession, shots, goals)
  • All scorers list
  • Man of the match (highest-stat player)
  • Options: Rematch / Change Teams / Main Menu
  • Animated confetti for winner
"""

import pygame
import math
import random
from src.core.base_screen import BaseScreen
from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    DARK_BG, GOLD, GOLD_LIGHT, ACCENT_CYAN,
    WHITE, BLACK, GREY_DARK, GREY_MID, GREY_LIGHT,
    STATE_MAIN_MENU, STATE_MATCH, STATE_TEAM_SELECT,
)
from src.screens.team_select import draw_kit


# ── Confetti particle ─────────────────────────────────────────────────────────
class Confetti:
    COLORS = [
        (255, 215, 0), (0, 220, 200), (255, 80, 80),
        (80, 200, 80), (200, 100, 255), (255, 180, 0),
    ]

    def __init__(self, w, h):
        self.w = w; self.h = h
        self.reset(first=True)

    def reset(self, first=False):
        self.x   = random.uniform(0, self.w)
        self.y   = random.uniform(-self.h, 0) if not first else random.uniform(0, self.h)
        self.vy  = random.uniform(1.5, 4.0)
        self.vx  = random.uniform(-0.8, 0.8)
        self.rot = random.uniform(0, 360)
        self.rot_speed = random.uniform(-3, 3)
        self.size = random.randint(6, 14)
        self.color = random.choice(self.COLORS)
        self.alpha = random.randint(160, 255)

    def update(self):
        self.x   += self.vx
        self.y   += self.vy
        self.rot += self.rot_speed
        if self.y > self.h + 20:
            self.reset()

    def draw(self, surf):
        s = pygame.Surface((self.size, self.size // 2 + 2), pygame.SRCALPHA)
        s.fill((*self.color, self.alpha))
        rotated = pygame.transform.rotate(s, self.rot)
        surf.blit(rotated, (int(self.x), int(self.y)))


# ── Full Time Screen ──────────────────────────────────────────────────────────
class FullTimeScreen(BaseScreen):

    BUTTONS = [
        ("REMATCH",      STATE_MATCH),
        ("CHANGE TEAMS", STATE_TEAM_SELECT),
        ("MAIN MENU",    STATE_MAIN_MENU),
    ]

    def __init__(self, screen, change_state, match_data: dict):
        super().__init__(screen, change_state)
        self.data    = match_data
        self.time    = 0.0
        self.slide_t = 0.0
        self._init_fonts()
        self._bg         = self._build_bg()
        self._scan       = self._build_scan()
        self.selected_btn = 0

        # Confetti only if there's a winner (not a draw)
        hg = match_data["home_goals"]
        ag = match_data["away_goals"]
        self.has_winner = hg != ag
        self.confetti   = [Confetti(self.width, self.height) for _ in range(80)] \
                          if self.has_winner else []

        # Build button rects
        btn_w, btn_h = 220, 46
        gap = 18
        total_w = len(self.BUTTONS) * btn_w + (len(self.BUTTONS)-1) * gap
        start_x = self.width//2 - total_w//2
        self.btn_rects = [
            pygame.Rect(start_x + i*(btn_w+gap), self.height - 90, btn_w, btn_h)
            for i in range(len(self.BUTTONS))
        ]

    def _init_fonts(self):
        bold = ["impact", "arial black", "bahnschrift", "freesansbold"]
        body = ["segoe ui", "calibri", "ubuntu", "freesans"]
        self.font_huge  = self._best_font(bold, 80, bold=True)
        self.font_lg    = self._best_font(bold, 38, bold=True)
        self.font_md    = self._best_font(body, 24, bold=True)
        self.font_sm    = self._best_font(body, 17)
        self.font_xs    = self._best_font(body, 14)

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
            r = int(4  + t * 6)
            g = int(6  + t * 8)
            b = int(14 + t * 18)
            pygame.draw.line(surf, (r, g, b), (0, y), (self.width, y))
        return surf

    def _build_scan(self):
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(0, self.height, 3):
            pygame.draw.line(surf, (0, 0, 0, 12), (0, y), (self.width, y))
        return surf

    # ── Events ────────────────────────────────────────────────────────────
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.selected_btn = (self.selected_btn - 1) % len(self.BUTTONS)
                elif event.key == pygame.K_RIGHT:
                    self.selected_btn = (self.selected_btn + 1) % len(self.BUTTONS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._fire_button(self.selected_btn)
                elif event.key == pygame.K_ESCAPE:
                    self.change_state(STATE_MAIN_MENU)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(self.btn_rects):
                    if rect.collidepoint(event.pos):
                        self._fire_button(i)

            if event.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(self.btn_rects):
                    if rect.collidepoint(event.pos):
                        self.selected_btn = i

    def _fire_button(self, idx):
        _, target = self.BUTTONS[idx]
        self.change_state(target)

    # ── Update ────────────────────────────────────────────────────────────
    def update(self, dt):
        self.time   += dt
        self.slide_t = min(1.0, self.slide_t + dt * 2.0)
        for c in self.confetti:
            c.update()

    # ── Draw ──────────────────────────────────────────────────────────────
    def draw(self):
        s  = self.screen
        cx = self.width // 2
        ease = self._ease_out(self.slide_t)

        s.blit(self._bg, (0, 0))

        # Confetti
        for c in self.confetti:
            c.draw(s)

        s.blit(self._scan, (0, 0))

        d  = self.data
        ht = d["home_team"]
        at = d["away_team"]
        hg = d["home_goals"]
        ag = d["away_goals"]

        # ── Winner banner ──
        if hg > ag:
            winner_txt = f"{ht[0].upper()} WIN!"
            winner_col = GOLD
        elif ag > hg:
            winner_txt = f"{at[0].upper()} WIN!"
            winner_col = ACCENT_CYAN
        else:
            winner_txt = "IT'S A DRAW!"
            winner_col = GREY_LIGHT

        banner_y = int(30 + (1 - ease) * -60)
        w_surf   = self.font_lg.render(winner_txt, True, winner_col)
        # Glow
        glow = pygame.Surface((w_surf.get_width()+30, w_surf.get_height()+14), pygame.SRCALPHA)
        alpha = int(50 + 30 * math.sin(self.time * 2))
        glow.fill((*winner_col, alpha))
        s.blit(glow, (cx - glow.get_width()//2, banner_y - 7))
        s.blit(w_surf, w_surf.get_rect(centerx=cx, top=banner_y))

        ft_surf = self.font_sm.render("FULL TIME", True, GREY_MID)
        s.blit(ft_surf, ft_surf.get_rect(centerx=cx, top=banner_y + w_surf.get_height() + 4))

        # Gold separator
        sep_w = int(480 * ease)
        pygame.draw.rect(s, GOLD,
                         (cx - sep_w//2, 138, sep_w, 2), border_radius=1)

        # ── Score + kits ──
        score_y = 155
        draw_kit(s, cx - 270, score_y, 65, 78, ht[2], ht[3], self.time)
        draw_kit(s, cx + 205, score_y, 65, 78, at[2], at[3], self.time)

        hn = self.font_md.render(ht[0], True, GOLD)
        an = self.font_md.render(at[0], True, ACCENT_CYAN)
        s.blit(hn, hn.get_rect(right=cx - 90, centery=score_y + 38))
        s.blit(an, an.get_rect(left=cx  + 90, centery=score_y + 38))

        score_surf = self.font_huge.render(f"{hg}  —  {ag}", True, WHITE)
        s.blit(score_surf, score_surf.get_rect(centerx=cx, centery=score_y + 40))

        # ── Stats ──
        stats_y = int(270 + (1 - ease) * 60)
        self._draw_stats(s, cx, stats_y)

        # ── Scorers ──
        scorers_y = stats_y + 175
        self._draw_scorers(s, cx, scorers_y)

        # ── Buttons ──
        self._draw_buttons(s)

        # ── Keyboard hint ──
        hint = self.font_xs.render("◀ ▶ navigate   ENTER select   ESC menu", True, GREY_MID)
        s.blit(hint, hint.get_rect(centerx=cx, top=self.height - 22))

    def _draw_stats(self, s, cx, top_y):
        panel_w, panel_h = 580, 155
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((10, 15, 28, 210))
        s.blit(panel, (cx - panel_w//2, top_y))
        pygame.draw.rect(s, GREY_DARK,
                         (cx - panel_w//2, top_y, panel_w, panel_h), 1, border_radius=4)

        d = self.data
        rows = [
            ("POSSESSION",
             f"{int(d['home_poss'])}%", f"{int(100-d['home_poss'])}%",
             d["home_poss"] / 100),
            ("SHOTS",
             str(d.get("home_shots",0)), str(d.get("away_shots",0)),
             d.get("home_shots",0) / max(1, d.get("home_shots",0)+d.get("away_shots",0))),
            ("GOALS",
             str(d["home_goals"]), str(d["away_goals"]),
             d["home_goals"] / max(1, d["home_goals"]+d["away_goals"])),
        ]
        row_h = 46
        for i, (lbl, hv, av, frac) in enumerate(rows):
            y = top_y + 14 + i * row_h
            label = self.font_xs.render(lbl, True, GREY_MID)
            s.blit(label, label.get_rect(centerx=cx, top=y))

            bar_w = 280
            bx    = cx - bar_w // 2
            by    = y + 18
            bh    = 12
            pygame.draw.rect(s, ACCENT_CYAN, (bx, by, bar_w, bh), border_radius=3)
            hw = int(bar_w * frac)
            if hw > 0:
                pygame.draw.rect(s, GOLD, (bx, by, hw, bh), border_radius=3)

            h_lbl = self.font_sm.render(hv, True, GOLD)
            a_lbl = self.font_sm.render(av, True, ACCENT_CYAN)
            s.blit(h_lbl, h_lbl.get_rect(right=bx - 8, centery=by + bh//2))
            s.blit(a_lbl, a_lbl.get_rect(left=bx + bar_w + 8, centery=by + bh//2))

    def _draw_scorers(self, s, cx, top_y):
        all_scorers = self.data.get("all_scorers", [])
        if not all_scorers:
            return
        lbl = self.font_xs.render("GOAL SCORERS", True, GREY_MID)
        s.blit(lbl, lbl.get_rect(centerx=cx, top=top_y))
        for i, scorer in enumerate(all_scorers[:6]):
            sc = self.font_sm.render(f"⚽  {scorer}", True, GREY_LIGHT)
            col_offset = -150 if i % 2 == 0 else 150
            s.blit(sc, sc.get_rect(centerx=cx + col_offset, top=top_y + 20 + (i//2)*22))

    def _draw_buttons(self, s):
        mouse = pygame.mouse.get_pos()
        for i, (rect, (label, _)) in enumerate(zip(self.btn_rects, self.BUTTONS)):
            hovered  = rect.collidepoint(mouse) or i == self.selected_btn
            if hovered:
                pygame.draw.rect(s, GOLD, rect, border_radius=7)
                txt = self.font_sm.render(label, True, BLACK)
            else:
                pygame.draw.rect(s, GREY_DARK, rect, border_radius=7)
                pygame.draw.rect(s, GREY_MID,  rect, 2, border_radius=7)
                txt = self.font_sm.render(label, True, GREY_LIGHT)
            s.blit(txt, txt.get_rect(center=rect.center))

    @staticmethod
    def _ease_out(t):
        return 1 - (1 - t) ** 3