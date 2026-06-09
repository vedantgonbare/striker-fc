"""
match.py — Full top-down 2D match screen.

Features:
  • Rendered football pitch with markings
  • Player-controlled team (arrow keys + Z shoot + X pass)
  • Basic AI opponents (chase ball, defend, shoot)
  • Ball physics with friction + wall/goal bounce
  • HUD: scoreboard, match clock, possession
  • Goal detection + celebration flash
  • ESC → back to main menu
"""

import pygame
import math
import random
from src.core.base_screen import BaseScreen
from src.core.sound_engine import SoundEngine
from src.core.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    WHITE, BLACK, GOLD, GOLD_LIGHT, ACCENT_CYAN,
    DARK_BG, GREY_MID, GREY_LIGHT,
    STATE_MAIN_MENU, STATE_HALF_TIME, STATE_FULL_TIME,
)

# ── Pitch constants ────────────────────────────────────────────────────────────
PX, PY       = 60, 80          # pitch top-left
PW, PH       = 1160, 580       # pitch width/height
GOAL_W       = 12              # goal depth (px)
GOAL_H       = 110             # goal mouth height
STRIPE_W     = PW // 10        # grass stripe width

# Derived
PITCH_RECT   = pygame.Rect(PX, PY, PW, PH)
L_GOAL_RECT  = pygame.Rect(PX - GOAL_W, PY + PH//2 - GOAL_H//2, GOAL_W, GOAL_H)
R_GOAL_RECT  = pygame.Rect(PX + PW,     PY + PH//2 - GOAL_H//2, GOAL_W, GOAL_H)

# Colours
C_GRASS      = (34,  100,  34)
C_GRASS_ALT  = (30,   90,  30)
C_LINE       = (255, 255, 255)
C_GOAL_POST  = (220, 220, 220)
C_BALL       = (255, 255, 255)
C_BALL_SPOT  = (30,   30,  30)
C_HUD_BG     = (8,   12,  20)
C_GOAL_FLASH = (255, 215,  0)

BALL_RADIUS  = 7
BALL_FRICTION= 0.982
PLAYER_R     = 10
SPRINT_MULT  = 1.6
KICK_POWER   = 14.0
PASS_POWER   = 9.0
AI_SPEED     = 2.8
PLAYER_SPEED = 4.2
CONTROL_DIST = PLAYER_R + BALL_RADIUS + 2   # px to "own" the ball


# ── Helper ─────────────────────────────────────────────────────────────────────
def vec_len(v):
    return math.sqrt(v[0]**2 + v[1]**2)

def vec_norm(v):
    l = vec_len(v)
    return (v[0]/l, v[1]/l) if l > 0 else (0, 0)

def vec_dist(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)


# ── Ball ───────────────────────────────────────────────────────────────────────
class Ball:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x  = PX + PW // 2
        self.y  = PY + PH // 2
        self.vx = 0.0
        self.vy = 0.0

    def kick(self, dx, dy, power):
        nx, ny = vec_norm((dx, dy))
        self.vx = nx * power
        self.vy = ny * power

    def update(self, dt):
        self.vx *= BALL_FRICTION
        self.vy *= BALL_FRICTION
        spd = vec_len((self.vx, self.vy))
        if spd > 22:
            self.vx = self.vx/spd * 22
            self.vy = self.vy/spd * 22

        self.x += self.vx
        self.y += self.vy

        # Bounce off pitch sides (not goals)
        if self.y - BALL_RADIUS < PY:
            self.y = PY + BALL_RADIUS; self.vy *= -0.6
        if self.y + BALL_RADIUS > PY + PH:
            self.y = PY + PH - BALL_RADIUS; self.vy *= -0.6

        # Left wall (except goal mouth)
        in_left_goal = L_GOAL_RECT.top < self.y < L_GOAL_RECT.bottom
        if self.x - BALL_RADIUS < PX and not in_left_goal:
            self.x = PX + BALL_RADIUS; self.vx *= -0.6

        # Right wall (except goal mouth)
        in_right_goal = R_GOAL_RECT.top < self.y < R_GOAL_RECT.bottom
        if self.x + BALL_RADIUS > PX + PW and not in_right_goal:
            self.x = PX + PW - BALL_RADIUS; self.vx *= -0.6

        # Goal back walls
        if self.x - BALL_RADIUS < PX - GOAL_W and in_left_goal:
            self.x = PX - GOAL_W + BALL_RADIUS; self.vx *= -0.5
        if self.x + BALL_RADIUS > PX + PW + GOAL_W and in_right_goal:
            self.x = PX + PW + GOAL_W - BALL_RADIUS; self.vx *= -0.5

    def draw(self, surf):
        ix, iy = int(self.x), int(self.y)
        # Shadow
        shadow = pygame.Surface((BALL_RADIUS*2+4, BALL_RADIUS*2+4), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0,0,0,60), (0,4, BALL_RADIUS*2+4, BALL_RADIUS))
        surf.blit(shadow, (ix - BALL_RADIUS - 2, iy))
        # Ball
        pygame.draw.circle(surf, C_BALL, (ix, iy), BALL_RADIUS)
        pygame.draw.circle(surf, C_BALL_SPOT, (ix-2, iy-2), 3)
        pygame.draw.circle(surf, (180,180,180), (ix, iy), BALL_RADIUS, 1)

    @property
    def pos(self):
        return (self.x, self.y)


# ── Player ─────────────────────────────────────────────────────────────────────
class Player:
    def __init__(self, x, y, color, number, speed=PLAYER_SPEED, role="field"):
        self.x      = float(x)
        self.y      = float(y)
        self.sx     = float(x)   # start/home position
        self.sy     = float(y)
        self.color  = color
        self.number = number
        self.speed  = speed
        self.role   = role        # "gk" | "field"
        self.vx     = 0.0
        self.vy     = 0.0
        self.has_ball = False
        self.kick_cooldown = 0.0
        self.dir    = (1.0, 0.0)  # facing direction

    def move_toward(self, tx, ty, spd=None):
        spd = spd or self.speed
        dx, dy = tx - self.x, ty - self.y
        dist   = math.sqrt(dx*dx + dy*dy)
        if dist > 1:
            self.vx = dx/dist * spd
            self.vy = dy/dist * spd
            self.dir = (dx/dist, dy/dist)
        else:
            self.vx = self.vy = 0.0

    def apply_velocity(self):
        self.x += self.vx
        self.y += self.vy
        # Clamp to pitch + small margin
        self.x = max(PX - GOAL_W, min(PX + PW + GOAL_W, self.x))
        self.y = max(PY, min(PY + PH, self.y))

    def draw(self, surf, font, is_controlled=False):
        ix, iy = int(self.x), int(self.y)
        # Shadow
        pygame.draw.ellipse(surf, (0,0,0,40),
                            (ix-PLAYER_R, iy+PLAYER_R-3, PLAYER_R*2, 6))
        # Body circle
        pygame.draw.circle(surf, self.color, (ix, iy), PLAYER_R)
        # White ring
        ring_col = GOLD if is_controlled else WHITE
        pygame.draw.circle(surf, ring_col, (ix, iy), PLAYER_R, 2)
        # Number
        num = font.render(str(self.number), True, WHITE)
        surf.blit(num, num.get_rect(center=(ix, iy)))

    @property
    def pos(self):
        return (self.x, self.y)


# ── Formation positions (normalised 0-1, mapped to pitch) ─────────────────────
def make_team_positions(side="left"):
    """Return 11 (x,y) pitch positions for a 4-3-3 layout."""
    cx = PX + PW * (0.08 if side=="left" else 0.92)
    cy = PY + PH // 2
    positions = []
    if side == "left":
        xs = [0.05, 0.20, 0.20, 0.20, 0.20,
              0.38, 0.38, 0.38,
              0.60, 0.60, 0.60]
        ys_by_row = [
            [0.50],
            [0.18, 0.38, 0.62, 0.82],
            [0.28, 0.50, 0.72],
            [0.22, 0.50, 0.78],
        ]
    else:
        xs = [0.95, 0.80, 0.80, 0.80, 0.80,
              0.62, 0.62, 0.62,
              0.40, 0.40, 0.40]
        ys_by_row = [
            [0.50],
            [0.18, 0.38, 0.62, 0.82],
            [0.28, 0.50, 0.72],
            [0.22, 0.50, 0.78],
        ]
    flat_ys = [y for row in ys_by_row for y in row]
    for x_frac, y_frac in zip(xs, flat_ys):
        positions.append((PX + PW * x_frac, PY + PH * y_frac))
    return positions


# ── AI Brain ──────────────────────────────────────────────────────────────────
class AIBrain:
    """Simple rule-based AI for opponent team."""

    def __init__(self, players, attack_dir):
        self.players    = players     # list of Player
        self.attack_dir = attack_dir  # +1 = attack right, -1 = left
        self.shoot_cooldown = 0.0

    def update(self, dt, ball, own_goal_x, enemy_goal_x):
        self.shoot_cooldown = max(0, self.shoot_cooldown - dt)
        ball_owner = None   # which player is closest to ball

        # Find closest player to ball
        min_d = 9999
        for p in self.players:
            d = vec_dist(p.pos, ball.pos)
            if d < min_d:
                min_d = d
                ball_owner = p

        for p in self.players:
            d = vec_dist(p.pos, ball.pos)

            if p is ball_owner and min_d < CONTROL_DIST + 8:
                # Has ball — move toward goal
                goal_y = PY + PH // 2
                tx = enemy_goal_x + self.attack_dir * 40
                p.move_toward(tx, goal_y, AI_SPEED)
                # Shoot if close enough
                if abs(p.x - enemy_goal_x) < 180 and self.shoot_cooldown <= 0:
                    dx = enemy_goal_x - ball.x
                    dy = (PY + PH//2) - ball.y + random.uniform(-30, 30)
                    ball.kick(dx, dy, KICK_POWER * random.uniform(0.7, 1.0))
                    self.shoot_cooldown = 1.2
            elif p.role == "gk":
                # GK stays near own goal, tracks ball vertically
                gk_x = own_goal_x - self.attack_dir * 30
                gk_y = max(PY + 60, min(PY + PH - 60, ball.y))
                p.move_toward(gk_x, gk_y, AI_SPEED * 0.9)
            else:
                # Field players — move toward ball if close, else hold shape
                if d < 160:
                    p.move_toward(ball.x, ball.y, AI_SPEED * 0.85)
                else:
                    p.move_toward(p.sx, p.sy, AI_SPEED * 0.4)

            p.apply_velocity()


# ── Pitch renderer ─────────────────────────────────────────────────────────────
def draw_pitch(surf):
    # Grass stripes
    for i in range(10):
        color = C_GRASS if i % 2 == 0 else C_GRASS_ALT
        pygame.draw.rect(surf, color,
                         (PX + i * STRIPE_W, PY, STRIPE_W, PH))

    lw = 2  # line width

    # Outer boundary
    pygame.draw.rect(surf, C_LINE, PITCH_RECT, lw)

    # Centre line
    pygame.draw.line(surf, C_LINE,
                     (PX + PW//2, PY), (PX + PW//2, PY + PH), lw)

    # Centre circle
    pygame.draw.circle(surf, C_LINE, (PX + PW//2, PY + PH//2), 70, lw)
    pygame.draw.circle(surf, C_LINE, (PX + PW//2, PY + PH//2), 3)

    # Penalty boxes
    pb_w, pb_h = 160, 260
    pb_y       = PY + PH//2 - pb_h//2
    pygame.draw.rect(surf, C_LINE, (PX,              pb_y, pb_w, pb_h), lw)
    pygame.draw.rect(surf, C_LINE, (PX + PW - pb_w,  pb_y, pb_w, pb_h), lw)

    # 6-yard boxes
    sb_w, sb_h = 55, 140
    sb_y       = PY + PH//2 - sb_h//2
    pygame.draw.rect(surf, C_LINE, (PX,              sb_y, sb_w, sb_h), lw)
    pygame.draw.rect(surf, C_LINE, (PX + PW - sb_w,  sb_y, sb_w, sb_h), lw)

    # Penalty spots
    pygame.draw.circle(surf, C_LINE, (PX + 110,      PY + PH//2), 3)
    pygame.draw.circle(surf, C_LINE, (PX + PW - 110, PY + PH//2), 3)

    # Corner arcs
    for cx2, cy2 in [(PX, PY), (PX+PW, PY), (PX, PY+PH), (PX+PW, PY+PH)]:
        pygame.draw.circle(surf, C_LINE, (cx2, cy2), 16, lw)

    # Goals
    gl_y = PY + PH//2 - GOAL_H//2
    pygame.draw.rect(surf, C_GOAL_POST,
                     (PX - GOAL_W, gl_y, GOAL_W, GOAL_H), 2)
    pygame.draw.rect(surf, C_GOAL_POST,
                     (PX + PW, gl_y, GOAL_W, GOAL_H), 2)


# ── HUD ────────────────────────────────────────────────────────────────────────
class HUD:
    def __init__(self, screen, home_name, away_name, home_color, away_color):
        self.screen     = screen
        self.home_name  = home_name
        self.away_name  = away_name
        self.home_color = home_color
        self.away_color = away_color
        self.font_lg    = pygame.font.SysFont("impact", 28, bold=True)
        self.font_sm    = pygame.font.Font(None, 22)
        self.font_md    = pygame.font.Font(None, 26)

    def draw(self, home_goals, away_goals, elapsed_s, home_poss,
             flash_alpha=0, current_half=1, half_duration=45.0):
        s   = self.screen
        w   = WINDOW_WIDTH
        bar = pygame.Surface((w, PY - 2), pygame.SRCALPHA)
        bar.fill((*C_HUD_BG, 230))
        s.blit(bar, (0, 0))

        cx = w // 2

        # Score
        score_txt = f"{home_goals}  —  {away_goals}"
        sc = self.font_lg.render(score_txt, True, WHITE)
        s.blit(sc, sc.get_rect(centerx=cx, centery=PY//2))

        # Team names
        hn = self.font_sm.render(self.home_name, True, self.home_color)
        an = self.font_sm.render(self.away_name, True, self.away_color)
        s.blit(hn, hn.get_rect(right=cx - 80, centery=PY//2))
        s.blit(an, an.get_rect(left =cx + 80, centery=PY//2))

        # Clock — map elapsed to in-game minutes
        half_elapsed = elapsed_s - (half_duration if current_half == 2 else 0)
        frac  = min(1.0, half_elapsed / half_duration)
        mins  = int(frac * 45) + (45 if current_half == 2 else 0) + 1
        mins  = min(mins, 90)
        clk   = self.font_md.render(f"{mins:02d}'", True, GOLD)
        s.blit(clk, clk.get_rect(centerx=cx, centery=PY//2 + 18))

        # Half indicator
        half_lbl = self.font_sm.render(
            f"{'1ST' if current_half == 1 else '2ND'} HALF", True, GREY_MID)
        s.blit(half_lbl, half_lbl.get_rect(centerx=cx, top=4))

        # Possession bar
        bar_w = 200
        bar_x = cx - bar_w // 2
        bar_y = PY - 18
        pygame.draw.rect(s, self.away_color, (bar_x, bar_y, bar_w, 8), border_radius=3)
        hw = int(bar_w * home_poss / 100)
        pygame.draw.rect(s, self.home_color, (bar_x, bar_y, hw, 8), border_radius=3)
        hp = self.font_sm.render(f"{int(home_poss)}%", True, self.home_color)
        ap = self.font_sm.render(f"{int(100-home_poss)}%", True, self.away_color)
        s.blit(hp, hp.get_rect(right=bar_x - 4, centery=bar_y + 4))
        s.blit(ap, ap.get_rect(left=bar_x + bar_w + 4, centery=bar_y + 4))

        # Controls reminder (bottom bar)
        bot = pygame.Surface((w, 28), pygame.SRCALPHA)
        bot.fill((*C_HUD_BG, 200))
        s.blit(bot, (0, WINDOW_HEIGHT - 28))
        hint = self.font_sm.render(
            "ARROWS: move   Z: shoot   X: pass   SHIFT: sprint   ESC: menu", True, GREY_MID)
        s.blit(hint, hint.get_rect(centerx=cx, centery=WINDOW_HEIGHT - 14))

        # Goal flash overlay
        if flash_alpha > 0:
            flash = pygame.Surface((w, WINDOW_HEIGHT), pygame.SRCALPHA)
            flash.fill((*C_GOAL_FLASH, int(flash_alpha)))
            s.blit(flash, (0, 0))
            gtxt = self.font_lg.render("⚽  GOAL!", True, WHITE)
            s.blit(gtxt, gtxt.get_rect(center=(cx, WINDOW_HEIGHT//2)))


# ── Match Screen ───────────────────────────────────────────────────────────────
class MatchScreen(BaseScreen):

    def __init__(self, screen, change_state, home_team=None, away_team=None):
        super().__init__(screen, change_state)

        # Team data (fallback colours if called without team select)
        self.home_data  = home_team or ("Home", "HOM", (108,171,221), (255,255,255), "4-3-3")
        self.away_data  = away_team or ("Away", "AWY", (220, 30,  30), (255,255,255), "4-3-3")

        self._build_pitch_surface()
        self._setup_match()

        self.hud = HUD(screen,
                       self.home_data[0], self.away_data[0],
                       self.home_data[2], self.away_data[2])

        self.font_player = pygame.font.Font(None, 14)

        # ── Sound ──
        self.sfx = SoundEngine.get()
        self.sfx.start_ambient()
        self.sfx.kickoff_whistle()
        self._last_ball_spd = 0.0

    # ── Setup ──────────────────────────────────────────────────────────────
    def _build_pitch_surface(self):
        self._pitch_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._pitch_surf.fill((10, 14, 24))   # out-of-pitch dark border
        draw_pitch(self._pitch_surf)

    def _setup_match(self):
        self.ball         = Ball()
        self.home_goals   = 0
        self.away_goals   = 0
        self.elapsed      = 0.0
        self.goal_flash   = 0.0
        self.reset_timer  = 0.0
        self.home_poss    = 50.0

        # ── Match flow ──
        # Each half = 45 real-seconds (fast arcade pace)
        self.half_duration   = 45.0       # seconds per half
        self.current_half    = 1
        self.half_triggered  = False      # prevent double-trigger
        self.match_over      = False

        # ── Stats tracking ──
        self.home_shots   = 0
        self.away_shots   = 0
        self.all_scorers  = []            # list of "Team name (min')"
        self.first_scorers = []           # first-half scorers only

        # Build players
        home_pos = make_team_positions("left")
        away_pos = make_team_positions("right")
        hc = self.home_data[2]
        ac = self.away_data[2]

        self.home_players = []
        for i, (x, y) in enumerate(home_pos):
            role = "gk" if i == 0 else "field"
            p = Player(x, y, hc, i+1, PLAYER_SPEED, role)
            self.home_players.append(p)

        self.away_players = []
        for i, (x, y) in enumerate(away_pos):
            role = "gk" if i == 0 else "field"
            p = Player(x, y, ac, i+1, AI_SPEED, role)
            self.away_players.append(p)

        # Controlled player = closest field player to ball at start
        self.controlled_idx = 1   # start with player #2 (first field player)

        # AI
        self.ai = AIBrain(self.away_players, attack_dir=-1)

        self.kicked_by_home = True   # possession tracking

    def _reset_after_goal(self):
        self.ball.reset()
        home_pos = make_team_positions("left")
        away_pos = make_team_positions("right")
        for i, p in enumerate(self.home_players):
            p.x, p.y = home_pos[i]; p.sx, p.sy = home_pos[i]
            p.vx = p.vy = 0
        for i, p in enumerate(self.away_players):
            p.x, p.y = away_pos[i]; p.sx, p.sy = away_pos[i]
            p.vx = p.vy = 0

    def _build_match_data(self):
        return {
            "home_team":     self.home_data,
            "away_team":     self.away_data,
            "home_goals":    self.home_goals,
            "away_goals":    self.away_goals,
            "home_poss":     self.home_poss,
            "home_shots":    self.home_shots,
            "away_shots":    self.away_shots,
            "all_scorers":   self.all_scorers,
            "first_scorers": self.first_scorers,
        }

    def _go_half_time(self):
        self.sfx.stop_ambient()
        self.sfx.kickoff_whistle()
        self.first_scorers = list(self.all_scorers)
        # Store data for half time screen, then switch
        from src.screens.half_time import HalfTimeScreen
        # Pass data via change_state callback — game.py stores it
        self._match_data_snapshot = self._build_match_data()
        self.change_state(STATE_HALF_TIME)

    def _go_full_time(self):
        self.sfx.stop_ambient()
        self.sfx.kickoff_whistle()
        self._match_data_snapshot = self._build_match_data()
        self.change_state(STATE_FULL_TIME)

    # ── Nearest player switch ──────────────────────────────────────────────
    def _switch_to_nearest(self):
        best, best_d = 1, 9999
        for i, p in enumerate(self.home_players):
            if p.role == "gk":
                continue
            d = vec_dist(p.pos, self.ball.pos)
            if d < best_d:
                best_d = d; best = i
        self.controlled_idx = best

    # ── Events ────────────────────────────────────────────────────────────
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.sfx.stop_ambient()
                    self.change_state(STATE_MAIN_MENU)
                if event.key in (pygame.K_z, pygame.K_x):
                    self._switch_to_nearest()

    # ── Update ────────────────────────────────────────────────────────────
    def update(self, dt):
        if self.match_over:
            return

        if self.reset_timer > 0:
            self.reset_timer -= dt
            if self.reset_timer <= 0:
                self._reset_after_goal()
            self.goal_flash = max(0, self.goal_flash - dt * 80)
            return

        self.elapsed += dt
        self.goal_flash = max(0, self.goal_flash - dt * 80)

        # ── Half time / Full time triggers ──
        if not self.half_triggered:
            if self.current_half == 1 and self.elapsed >= self.half_duration:
                self.half_triggered = True
                self.match_over     = True
                self._go_half_time()
                return
            if self.current_half == 2 and self.elapsed >= self.half_duration * 2:
                self.half_triggered = True
                self.match_over     = True
                self._go_full_time()
                return

        keys = pygame.key.get_pressed()
        cp   = self.home_players[self.controlled_idx]
        sprint = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        spd  = PLAYER_SPEED * (SPRINT_MULT if sprint else 1.0)

        # ── Player input ──
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_DOWN]:  dy += 1

        if dx != 0 or dy != 0:
            nx, ny = vec_norm((dx, dy))
            cp.vx = nx * spd
            cp.vy = ny * spd
            cp.dir = (nx, ny)
        else:
            cp.vx *= 0.7
            cp.vy *= 0.7

        cp.apply_velocity()

        # ── Ball control / dribble ──
        ball_d = vec_dist(cp.pos, self.ball.pos)
        if ball_d < CONTROL_DIST:
            # Dribble — nudge ball along with player
            if dx != 0 or dy != 0:
                nx, ny = vec_norm((dx, dy))
                self.ball.x = cp.x + nx * (CONTROL_DIST - 1)
                self.ball.y = cp.y + ny * (CONTROL_DIST - 1)
                self.ball.vx = cp.vx * 0.5
                self.ball.vy = cp.vy * 0.5
            self.kicked_by_home = True

        # ── Shoot ──
        if keys[pygame.K_z] and cp.kick_cooldown <= 0:
            goal_x = PX + PW + GOAL_W
            goal_y = PY + PH // 2
            dx_s   = goal_x - self.ball.x
            dy_s   = goal_y - self.ball.y + random.uniform(-20, 20)
            self.ball.kick(dx_s, dy_s, KICK_POWER)
            cp.kick_cooldown = 0.5
            self.kicked_by_home = True
            self.sfx.play("kick", channel=4)
            self.home_shots += 1

        # ── Pass ──
        if keys[pygame.K_x] and cp.kick_cooldown <= 0:
            # Pass to nearest teammate
            best, best_d = None, 9999
            for p in self.home_players:
                if p is cp: continue
                d = vec_dist(cp.pos, p.pos)
                if d < best_d:
                    best_d = d; best = p
            if best:
                dx_p = best.x - self.ball.x
                dy_p = best.y - self.ball.y
                self.ball.kick(dx_p, dy_p, PASS_POWER)
                cp.kick_cooldown = 0.4
                self.kicked_by_home = True
                self.sfx.play("pass", channel=5)

        # Cooldowns
        for p in self.home_players:
            p.kick_cooldown = max(0, p.kick_cooldown - dt)

        # ── AI update ──
        own_goal_x   = PX + PW   # away goal is on the right
        enemy_goal_x = PX        # away attacks left goal
        self.ai.update(dt, self.ball,
                       own_goal_x=own_goal_x,
                       enemy_goal_x=enemy_goal_x)

        # ── AI ball contact ──
        for ap in self.away_players:
            if vec_dist(ap.pos, self.ball.pos) < CONTROL_DIST:
                self.kicked_by_home = False

        # ── Other home players — move toward home positions ──
        for i, p in enumerate(self.home_players):
            if i == self.controlled_idx: continue
            if p.role == "gk":
                gk_x = PX + 30
                gk_y = max(PY + 50, min(PY+PH-50, self.ball.y))
                p.move_toward(gk_x, gk_y, PLAYER_SPEED * 0.8)
            else:
                bd = vec_dist(p.pos, self.ball.pos)
                if bd < 120:
                    p.move_toward(self.ball.x, self.ball.y, PLAYER_SPEED*0.7)
                else:
                    p.move_toward(p.sx, p.sy, PLAYER_SPEED*0.4)
            p.apply_velocity()

        # ── Ball physics ──
        self.ball.update(dt)

        # ── Auto-switch if controlled player far from ball ──
        if vec_dist(cp.pos, self.ball.pos) > 250:
            self._switch_to_nearest()

        # ── Ball bounce sound (wall hits) ──
        cur_spd = math.sqrt(self.ball.vx**2 + self.ball.vy**2)
        if self._last_ball_spd > 6 and cur_spd < self._last_ball_spd * 0.7:
            self.sfx.play("bounce", channel=6)
        self._last_ball_spd = cur_spd

        # ── Possession tracking ──
        if self.kicked_by_home:
            self.home_poss = self.home_poss * 0.998 + 100 * 0.002
        else:
            self.home_poss = self.home_poss * 0.998 + 0   * 0.002
        self.home_poss = max(10, min(90, self.home_poss))

        # ── Goal detection ──
        bx, by = self.ball.x, self.ball.y
        goal_y_top = PY + PH//2 - GOAL_H//2
        goal_y_bot = PY + PH//2 + GOAL_H//2

        # Home scores (ball enters right goal)
        if bx > PX + PW and goal_y_top < by < goal_y_bot:
            self.home_goals += 1
            self.goal_flash  = 255
            self.reset_timer = 2.5
            self.sfx.goal_sequence()
            mins = int(self.elapsed / self.half_duration * 45) + (45 if self.current_half == 2 else 0)
            self.all_scorers.append(f"{self.home_data[0]} {mins}'")

        # Away scores (ball enters left goal)
        if bx < PX and goal_y_top < by < goal_y_bot:
            self.away_goals += 1
            self.goal_flash  = 255
            self.reset_timer = 2.5
            self.sfx.goal_sequence()
            mins = int(self.elapsed / self.half_duration * 45) + (45 if self.current_half == 2 else 0)
            self.all_scorers.append(f"{self.away_data[0]} {mins}'")

    # ── Draw ──────────────────────────────────────────────────────────────
    def draw(self):
        s = self.screen
        s.blit(self._pitch_surf, (0, 0))

        # Players
        for i, p in enumerate(self.home_players):
            p.draw(s, self.font_player, is_controlled=(i == self.controlled_idx))
        for p in self.away_players:
            p.draw(s, self.font_player)

        # Ball
        self.ball.draw(s)

        # HUD
        self.hud.draw(self.home_goals, self.away_goals,
                      self.elapsed, self.home_poss, self.goal_flash,
                      current_half=self.current_half,
                      half_duration=self.half_duration)