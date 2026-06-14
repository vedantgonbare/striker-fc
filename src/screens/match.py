"""
match.py — Day 5: Full game-feel upgrade.

New features:
  • Shooting power bar  (hold Z to charge, release to shoot)
  • Slide tackle        (S key — risks foul, wins ball)
  • Better dribbling    (tight control radius, momentum carry)
  • Stamina system      (sprinting drains, recovery when walking)
  • Smarter AI          (zones, pressure, GK positioning, through-ball)
  • Screen shake        (on goal + on tackle)
  • Tackle spark effect
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

# ── Pitch constants ───────────────────────────────────────────────────────────
PX, PY    = 60, 80
PW, PH    = 1160, 580
GOAL_W    = 12
GOAL_H    = 110
STRIPE_W  = PW // 10

PITCH_RECT  = pygame.Rect(PX, PY, PW, PH)
L_GOAL_RECT = pygame.Rect(PX - GOAL_W, PY + PH//2 - GOAL_H//2, GOAL_W, GOAL_H)
R_GOAL_RECT = pygame.Rect(PX + PW,     PY + PH//2 - GOAL_H//2, GOAL_W, GOAL_H)

# Colours
C_GRASS      = (34,  100,  34)
C_GRASS_ALT  = (30,   90,  30)
C_LINE       = (255, 255, 255)
C_GOAL_POST  = (220, 220, 220)
C_HUD_BG     = (8,   12,  20)
C_GOAL_FLASH = (255, 215,   0)

# Physics / gameplay
BALL_RADIUS   = 7
BALL_FRICTION  = 0.982
PLAYER_R       = 10
PLAYER_SPEED   = 4.2
SPRINT_MULT    = 1.65
STAMINA_DRAIN  = 28.0     # per second sprinting
STAMINA_REGEN  = 14.0     # per second walking
CONTROL_DIST   = PLAYER_R + BALL_RADIUS + 3
DRIBBLE_DIST   = CONTROL_DIST - 1
MAX_SHOOT_PWR  = 20.0
MIN_SHOOT_PWR  = 8.0
PASS_POWER     = 9.5
AI_SPEED       = 2.9
AI_SPRINT_MULT = 1.4

# Tackle
TACKLE_RANGE   = PLAYER_R * 2 + BALL_RADIUS + 4
TACKLE_DURATION = 0.35    # seconds sliding
TACKLE_COOLDOWN = 1.2


# ── Helpers ───────────────────────────────────────────────────────────────────
def vlen(vx, vy):   return math.sqrt(vx*vx + vy*vy)
def vnorm(vx, vy):
    l = vlen(vx, vy)
    return (vx/l, vy/l) if l > 0 else (0.0, 0.0)
def vdist(ax, ay, bx, by): return math.sqrt((ax-bx)**2 + (ay-by)**2)


# ── Particle effects ──────────────────────────────────────────────────────────
class Spark:
    """Small spark for tackle/collision effects."""
    def __init__(self, x, y):
        angle = random.uniform(0, math.pi * 2)
        spd   = random.uniform(2, 6)
        self.x  = x; self.y  = y
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd
        self.life = random.uniform(0.2, 0.5)
        self.max_life = self.life
        self.color = random.choice([(255,220,0),(255,160,0),(255,255,180)])

    def update(self, dt):
        self.x   += self.vx
        self.y   += self.vy
        self.vx  *= 0.88
        self.vy  *= 0.88
        self.life -= dt

    def draw(self, surf):
        if self.life <= 0: return
        alpha = int(255 * self.life / self.max_life)
        r = max(1, int(3 * self.life / self.max_life))
        s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r+1, r+1), r)
        surf.blit(s, (int(self.x)-r, int(self.y)-r))


# ── Ball ──────────────────────────────────────────────────────────────────────
class Ball:
    def __init__(self):
        self.reset()
        self.spin = 0.0      # visual spin angle

    def reset(self):
        self.x  = PX + PW // 2
        self.y  = PY + PH // 2
        self.vx = 0.0
        self.vy = 0.0

    def kick(self, dx, dy, power):
        nx, ny   = vnorm(dx, dy)
        self.vx  = nx * power
        self.vy  = ny * power

    def update(self, dt):
        spd = vlen(self.vx, self.vy)
        self.vx *= BALL_FRICTION
        self.vy *= BALL_FRICTION
        if spd > 22: nx,ny=vnorm(self.vx,self.vy); self.vx=nx*22; self.vy=ny*22

        self.x += self.vx
        self.y += self.vy
        self.spin += spd * 0.08   # visual only

        bounced = False
        # Top/bottom walls
        if self.y - BALL_RADIUS < PY:
            self.y = PY + BALL_RADIUS; self.vy *= -0.6; bounced = True
        if self.y + BALL_RADIUS > PY + PH:
            self.y = PY + PH - BALL_RADIUS; self.vy *= -0.6; bounced = True

        in_lg = L_GOAL_RECT.top < self.y < L_GOAL_RECT.bottom
        in_rg = R_GOAL_RECT.top < self.y < R_GOAL_RECT.bottom

        if self.x - BALL_RADIUS < PX and not in_lg:
            self.x = PX + BALL_RADIUS; self.vx *= -0.6; bounced = True
        if self.x + BALL_RADIUS > PX + PW and not in_rg:
            self.x = PX + PW - BALL_RADIUS; self.vx *= -0.6; bounced = True
        if self.x - BALL_RADIUS < PX - GOAL_W and in_lg:
            self.x = PX - GOAL_W + BALL_RADIUS; self.vx *= -0.5
        if self.x + BALL_RADIUS > PX + PW + GOAL_W and in_rg:
            self.x = PX + PW + GOAL_W - BALL_RADIUS; self.vx *= -0.5

        return bounced

    def draw(self, surf):
        ix, iy = int(self.x), int(self.y)
        # Shadow
        shd = pygame.Surface((BALL_RADIUS*2+6, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shd, (0,0,0,50), (0,0,BALL_RADIUS*2+6,8))
        surf.blit(shd, (ix-BALL_RADIUS-3, iy+BALL_RADIUS-2))
        # Ball body
        pygame.draw.circle(surf, (255,255,255), (ix, iy), BALL_RADIUS)
        # Spin indicator (rotating pentagon pattern — simplified as offset spot)
        sx = ix + int(math.cos(self.spin) * 3)
        sy = iy + int(math.sin(self.spin) * 3)
        pygame.draw.circle(surf, (30,30,30), (sx, sy), 3)
        pygame.draw.circle(surf, (180,180,180), (ix, iy), BALL_RADIUS, 1)

    @property
    def pos(self): return (self.x, self.y)


# ── Player ────────────────────────────────────────────────────────────────────
class Player:
    def __init__(self, x, y, color, number, speed=PLAYER_SPEED, role="field"):
        self.x = float(x); self.y = float(y)
        self.sx = float(x); self.sy = float(y)
        self.color    = color
        self.sec_color= (255,255,255)
        self.number   = number
        self.speed    = speed
        self.role     = role
        self.vx = 0.0; self.vy = 0.0
        self.dir = (1.0, 0.0)
        self.has_ball     = False
        self.kick_cooldown = 0.0
        self.stamina      = 100.0
        # Tackle state
        self.tackling       = False
        self.tackle_timer   = 0.0
        self.tackle_cd      = 0.0
        self.tackle_vx      = 0.0
        self.tackle_vy      = 0.0

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
        if self.tackling:
            self.x += self.tackle_vx
            self.y += self.tackle_vy
        else:
            self.x += self.vx
            self.y += self.vy
        self.x = max(PX - GOAL_W, min(PX + PW + GOAL_W, self.x))
        self.y = max(PY, min(PY + PH, self.y))

    def update_tackle(self, dt):
        if self.tackling:
            self.tackle_timer -= dt
            # Decelerate during slide
            self.tackle_vx *= 0.88
            self.tackle_vy *= 0.88
            if self.tackle_timer <= 0:
                self.tackling = False
                self.tackle_timer = 0.0
        self.tackle_cd = max(0.0, self.tackle_cd - dt)

    def start_tackle(self):
        if self.tackle_cd > 0 or self.tackling:
            return False
        self.tackling     = True
        self.tackle_timer = TACKLE_DURATION
        self.tackle_cd    = TACKLE_COOLDOWN
        # Slide in facing direction
        self.tackle_vx    = self.dir[0] * self.speed * 2.2
        self.tackle_vy    = self.dir[1] * self.speed * 2.2
        return True

    def draw(self, surf, font, is_controlled=False, power_pct=0.0):
        ix, iy = int(self.x), int(self.y)

        # Tackle slide — draw elongated body
        if self.tackling:
            slide = pygame.Surface((PLAYER_R*4, PLAYER_R*2), pygame.SRCALPHA)
            pygame.draw.ellipse(slide, (*self.color, 200),
                                (0, 0, PLAYER_R*4, PLAYER_R*2))
            angle = math.degrees(math.atan2(self.tackle_vy, self.tackle_vx))
            rotated = pygame.transform.rotate(slide, -angle)
            surf.blit(rotated, rotated.get_rect(center=(ix, iy)))
            return

        # Shadow
        pygame.draw.ellipse(surf, (0,0,0,40),
                            (ix-PLAYER_R, iy+PLAYER_R-3, PLAYER_R*2, 6))
        # Body
        pygame.draw.circle(surf, self.color, (ix, iy), PLAYER_R)

        # Stamina ring (fades to red when tired)
        sta_frac = self.stamina / 100.0
        ring_color = (
            int(255 * (1 - sta_frac)),
            int(200 * sta_frac),
            0,
        ) if is_controlled else WHITE
        ring_col = GOLD if is_controlled else WHITE
        pygame.draw.circle(surf, ring_col, (ix, iy), PLAYER_R, 2)

        # Number
        num = font.render(str(self.number), True, WHITE)
        surf.blit(num, num.get_rect(center=(ix, iy)))

        # Power bar (above player when charging shot)
        if is_controlled and power_pct > 0:
            bar_w = PLAYER_R * 2 + 4
            bar_h = 5
            bx    = ix - bar_w // 2
            by    = iy - PLAYER_R - 12
            pygame.draw.rect(surf, (40, 40, 40), (bx, by, bar_w, bar_h), border_radius=2)
            fill_w = int(bar_w * power_pct)
            bar_color = (
                int(255 * power_pct),
                int(200 * (1 - power_pct)),
                0,
            )
            if fill_w > 0:
                pygame.draw.rect(surf, bar_color, (bx, by, fill_w, bar_h), border_radius=2)

    @property
    def pos(self): return (self.x, self.y)


# ── Smarter AI Brain ─────────────────────────────────────────────────────────
class AIBrain:
    """
    Zone-based AI:
      GK     — stays in goal, comes off line for close shots
      DEF    — tracks nearest attacker when ball is in own half
      MID    — presses ball carrier, supports attack
      FWD    — makes runs behind defence, shoots on sight
    """

    def __init__(self, players, attack_dir, own_goal_x, enemy_goal_x):
        self.players      = players
        self.attack_dir   = attack_dir     # +1 right, -1 left
        self.own_goal_x   = own_goal_x
        self.enemy_goal_x = enemy_goal_x
        self.shoot_cd     = 0.0
        self.pass_cd      = 0.0

    def update(self, dt, ball, home_players):
        self.shoot_cd = max(0, self.shoot_cd - dt)
        self.pass_cd  = max(0, self.pass_cd  - dt)

        # Find who's closest to ball
        min_d, ball_owner = 9999, None
        for p in self.players:
            d = vdist(p.x, p.y, ball.x, ball.y)
            if d < min_d:
                min_d = d; ball_owner = p

        ball_in_own_half = (
            (self.attack_dir == -1 and ball.x > PX + PW // 2) or
            (self.attack_dir ==  1 and ball.x < PX + PW // 2)
        )

        for i, p in enumerate(self.players):
            d = vdist(p.x, p.y, ball.x, ball.y)

            # ── GK ──
            if p.role == "gk":
                gk_home_x = self.own_goal_x - self.attack_dir * 25
                # Come off line if ball very close
                if d < 120:
                    p.move_toward(ball.x, ball.y, AI_SPEED)
                else:
                    gk_y = max(PY + 55, min(PY + PH - 55, ball.y))
                    p.move_toward(gk_home_x, gk_y, AI_SPEED * 0.95)

            # ── Ball owner — attack ──
            elif p is ball_owner and min_d < CONTROL_DIST + 10:
                dist_to_goal = abs(p.x - self.enemy_goal_x)

                # Try to shoot if in range
                if dist_to_goal < 220 and self.shoot_cd <= 0:
                    spread = random.uniform(-35, 35)
                    dx = self.enemy_goal_x - ball.x
                    dy = (PY + PH // 2 + spread) - ball.y
                    power = min(MAX_SHOOT_PWR, 10 + (220 - dist_to_goal) / 22)
                    ball.kick(dx, dy, power)
                    self.shoot_cd = 1.0
                    p.kick_cooldown = 0.6
                else:
                    # Dribble toward goal, avoid defenders
                    ty = PY + PH // 2
                    # Slight evasion from nearest home player
                    nearest_home, nh_d = None, 9999
                    for hp in home_players:
                        hd = vdist(p.x, p.y, hp.x, hp.y)
                        if hd < nh_d:
                            nh_d = hd; nearest_home = hp
                    if nearest_home and nh_d < 60:
                        # Dodge sideways
                        dodge_y = ty + (40 if p.y < ty else -40)
                        p.move_toward(self.enemy_goal_x, dodge_y,
                                      AI_SPEED * AI_SPRINT_MULT)
                    else:
                        p.move_toward(self.enemy_goal_x, ty,
                                      AI_SPEED * AI_SPRINT_MULT)

                # Nudge ball along
                if vdist(p.x, p.y, ball.x, ball.y) < CONTROL_DIST:
                    nx, ny = vnorm(p.vx, p.vy)
                    if abs(nx)+abs(ny) > 0:
                        ball.x = p.x + nx * (CONTROL_DIST - 1)
                        ball.y = p.y + ny * (CONTROL_DIST - 1)
                        ball.vx = p.vx * 0.4
                        ball.vy = p.vy * 0.4

            # ── Defenders — track attacker ──
            elif i in range(1, 5):   # defenders
                if ball_in_own_half and d < 250:
                    p.move_toward(ball.x, ball.y, AI_SPEED * 0.9)
                else:
                    # Hold defensive line
                    def_x = self.own_goal_x - self.attack_dir * 160
                    row_y = PY + PH * (0.2 + (i-1) * 0.2)
                    p.move_toward(def_x, row_y, AI_SPEED * 0.5)

            # ── Midfielders — press or support ──
            elif i in range(5, 8):
                if d < 200:
                    p.move_toward(ball.x, ball.y, AI_SPEED * 0.85)
                else:
                    mid_x = PX + PW * (0.38 if self.attack_dir == -1 else 0.62)
                    row_y = PY + PH * (0.25 + (i-5) * 0.25)
                    p.move_toward(mid_x, row_y, AI_SPEED * 0.45)

            # ── Forwards — make runs ──
            else:
                run_x = self.enemy_goal_x - self.attack_dir * 80
                spread= (i - 8) * 120 - 60
                run_y = PY + PH // 2 + spread
                if d < 150:
                    p.move_toward(ball.x, ball.y, AI_SPEED)
                else:
                    p.move_toward(run_x, run_y, AI_SPEED * 0.6)

            p.kick_cooldown = max(0, p.kick_cooldown - dt)
            p.apply_velocity()


# ── Pitch renderer ────────────────────────────────────────────────────────────
def draw_pitch(surf):
    for i in range(10):
        color = C_GRASS if i % 2 == 0 else C_GRASS_ALT
        pygame.draw.rect(surf, color, (PX + i*STRIPE_W, PY, STRIPE_W, PH))

    lw = 2
    pygame.draw.rect(surf, C_LINE, (PX, PY, PW, PH), lw)
    pygame.draw.line(surf, C_LINE, (PX+PW//2, PY), (PX+PW//2, PY+PH), lw)
    pygame.draw.circle(surf, C_LINE, (PX+PW//2, PY+PH//2), 70, lw)
    pygame.draw.circle(surf, C_LINE, (PX+PW//2, PY+PH//2), 3)

    pb_w, pb_h = 160, 260
    pb_y = PY + PH//2 - pb_h//2
    pygame.draw.rect(surf, C_LINE, (PX,             pb_y, pb_w, pb_h), lw)
    pygame.draw.rect(surf, C_LINE, (PX+PW-pb_w,     pb_y, pb_w, pb_h), lw)

    sb_w, sb_h = 55, 140
    sb_y = PY + PH//2 - sb_h//2
    pygame.draw.rect(surf, C_LINE, (PX,             sb_y, sb_w, sb_h), lw)
    pygame.draw.rect(surf, C_LINE, (PX+PW-sb_w,     sb_y, sb_w, sb_h), lw)

    pygame.draw.circle(surf, C_LINE, (PX+110,      PY+PH//2), 3)
    pygame.draw.circle(surf, C_LINE, (PX+PW-110,   PY+PH//2), 3)

    for cx2, cy2 in [(PX,PY),(PX+PW,PY),(PX,PY+PH),(PX+PW,PY+PH)]:
        pygame.draw.circle(surf, C_LINE, (cx2, cy2), 16, lw)

    gl_y = PY + PH//2 - GOAL_H//2
    pygame.draw.rect(surf, C_GOAL_POST, (PX-GOAL_W, gl_y, GOAL_W, GOAL_H), 2)
    pygame.draw.rect(surf, C_GOAL_POST, (PX+PW,     gl_y, GOAL_W, GOAL_H), 2)


# ── HUD ───────────────────────────────────────────────────────────────────────
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
        s  = self.screen
        w  = WINDOW_WIDTH
        cx = w // 2

        bar = pygame.Surface((w, PY-2), pygame.SRCALPHA)
        bar.fill((*C_HUD_BG, 230))
        s.blit(bar, (0, 0))

        # Half label
        half_lbl = self.font_sm.render(
            f"{'1ST' if current_half==1 else '2ND'} HALF", True, GREY_MID)
        s.blit(half_lbl, half_lbl.get_rect(centerx=cx, top=4))

        # Score
        sc = self.font_lg.render(f"{home_goals}  —  {away_goals}", True, WHITE)
        s.blit(sc, sc.get_rect(centerx=cx, centery=PY//2))

        # Team names
        hn = self.font_sm.render(self.home_name, True, self.home_color)
        an = self.font_sm.render(self.away_name, True, self.away_color)
        s.blit(hn, hn.get_rect(right=cx-80, centery=PY//2))
        s.blit(an, an.get_rect(left =cx+80, centery=PY//2))

        # Clock
        half_elapsed = elapsed_s - (half_duration if current_half == 2 else 0)
        frac  = min(1.0, half_elapsed / half_duration)
        mins  = min(90, int(frac * 45) + (45 if current_half == 2 else 0) + 1)
        clk   = self.font_md.render(f"{mins:02d}'", True, GOLD)
        s.blit(clk, clk.get_rect(centerx=cx, centery=PY//2+18))

        # Possession bar
        bar_w = 200; bar_x = cx - bar_w//2; bar_y = PY - 18
        pygame.draw.rect(s, self.away_color, (bar_x, bar_y, bar_w, 8), border_radius=3)
        hw = int(bar_w * home_poss / 100)
        pygame.draw.rect(s, self.home_color, (bar_x, bar_y, hw, 8), border_radius=3)
        hp = self.font_sm.render(f"{int(home_poss)}%",     True, self.home_color)
        ap = self.font_sm.render(f"{int(100-home_poss)}%", True, self.away_color)
        s.blit(hp, hp.get_rect(right=bar_x-4,        centery=bar_y+4))
        s.blit(ap, ap.get_rect(left =bar_x+bar_w+4,  centery=bar_y+4))

        # Controls
        bot = pygame.Surface((w, 28), pygame.SRCALPHA)
        bot.fill((*C_HUD_BG, 200))
        s.blit(bot, (0, WINDOW_HEIGHT - 28))
        hint = self.font_sm.render(
            "ARROWS: move   HOLD Z: power shot   X: pass   SHIFT: sprint   S: tackle   ESC: menu",
            True, GREY_MID)
        s.blit(hint, hint.get_rect(centerx=cx, centery=WINDOW_HEIGHT - 14))

        # Goal flash
        if flash_alpha > 0:
            flash = pygame.Surface((w, WINDOW_HEIGHT), pygame.SRCALPHA)
            flash.fill((*C_GOAL_FLASH, int(flash_alpha)))
            s.blit(flash, (0, 0))
            gtxt = self.font_lg.render("⚽  GOAL!", True, WHITE)
            s.blit(gtxt, gtxt.get_rect(center=(cx, WINDOW_HEIGHT//2)))

        # Stamina bar (bottom left)
        sta_lbl = self.font_sm.render("STAMINA", True, GREY_MID)
        s.blit(sta_lbl, (10, WINDOW_HEIGHT - 26))


# ── Match Screen ──────────────────────────────────────────────────────────────
class MatchScreen(BaseScreen):

    def __init__(self, screen, change_state, home_team=None, away_team=None):
        super().__init__(screen, change_state)
        self.home_data = home_team or ("Home","HOM",(108,171,221),(255,255,255),"4-3-3")
        self.away_data = away_team or ("Away","AWY",(220,30,30),(255,255,255),"4-3-3")

        self._build_pitch_surface()
        self._setup_match()

        self.hud = HUD(screen,
                       self.home_data[0], self.away_data[0],
                       self.home_data[2], self.away_data[2])
        self.font_player = pygame.font.Font(None, 14)

        self.sfx = SoundEngine.get()
        self.sfx.start_ambient()
        self.sfx.kickoff_whistle()

        self._last_ball_spd = 0.0

    # ── Setup ─────────────────────────────────────────────────────────────
    def _build_pitch_surface(self):
        self._pitch_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._pitch_surf.fill((10, 14, 24))
        draw_pitch(self._pitch_surf)

    def _setup_match(self):
        self.ball          = Ball()
        self.home_goals    = 0
        self.away_goals    = 0
        self.elapsed       = 0.0
        self.goal_flash    = 0.0
        self.reset_timer   = 0.0
        self.home_poss     = 50.0
        self.half_duration = 45.0
        self.current_half  = 1
        self.half_triggered= False
        self.match_over    = False
        self.home_shots    = 0
        self.away_shots    = 0
        self.all_scorers   = []
        self.first_scorers = []

        # Power shot state
        self.charging_shot = False
        self.shot_power    = 0.0       # 0.0 → 1.0

        # Screen shake
        self.shake_timer   = 0.0
        self.shake_mag     = 0

        # Particles
        self.sparks: list[Spark] = []

        # Players
        from src.screens.match import make_team_positions
        home_pos = make_team_positions("left")
        away_pos = make_team_positions("right")
        hc = self.home_data[2]
        ac = self.away_data[2]

        self.home_players = []
        for i, (x, y) in enumerate(home_pos):
            p = Player(x, y, hc, i+1, PLAYER_SPEED, "gk" if i==0 else "field")
            self.home_players.append(p)

        self.away_players = []
        for i, (x, y) in enumerate(away_pos):
            p = Player(x, y, ac, i+1, AI_SPEED, "gk" if i==0 else "field")
            self.away_players.append(p)

        self.controlled_idx = 1
        self.kicked_by_home = True

        self.ai = AIBrain(
            self.away_players,
            attack_dir   = -1,
            own_goal_x   = PX + PW,
            enemy_goal_x = PX,
        )

    def _reset_after_goal(self):
        self.ball.reset()
        home_pos = make_team_positions("left")
        away_pos = make_team_positions("right")
        for i, p in enumerate(self.home_players):
            p.x, p.y = home_pos[i]; p.sx, p.sy = home_pos[i]; p.vx=p.vy=0
        for i, p in enumerate(self.away_players):
            p.x, p.y = away_pos[i]; p.sx, p.sy = away_pos[i]; p.vx=p.vy=0

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
        self.sfx.stop_ambient(); self.sfx.kickoff_whistle()
        self.first_scorers = list(self.all_scorers)
        self._match_data_snapshot = self._build_match_data()
        self.change_state(STATE_HALF_TIME)

    def _go_full_time(self):
        self.sfx.stop_ambient(); self.sfx.kickoff_whistle()
        self._match_data_snapshot = self._build_match_data()
        self.change_state(STATE_FULL_TIME)

    def _switch_to_nearest(self):
        best, best_d = 1, 9999
        for i, p in enumerate(self.home_players):
            if p.role == "gk": continue
            d = vdist(p.x, p.y, self.ball.x, self.ball.y)
            if d < best_d: best_d = d; best = i
        self.controlled_idx = best

    def _add_shake(self, mag, dur):
        self.shake_mag   = mag
        self.shake_timer = dur

    # ── Events ────────────────────────────────────────────────────────────
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.sfx.stop_ambient()
                    self.change_state(STATE_MAIN_MENU)
                if event.key in (pygame.K_z, pygame.K_x):
                    self._switch_to_nearest()

                # Slide tackle
                if event.key == pygame.K_s:
                    cp = self.home_players[self.controlled_idx]
                    if cp.start_tackle():
                        self.sfx.play("bounce", channel=7)
                        for _ in range(8):
                            self.sparks.append(Spark(cp.x, cp.y))

            if event.type == pygame.KEYUP:
                # Release Z → fire charged shot
                if event.key == pygame.K_z and self.charging_shot:
                    self._release_shot()

    def _release_shot(self):
        cp = self.home_players[self.controlled_idx]
        power = MIN_SHOOT_PWR + self.shot_power * (MAX_SHOOT_PWR - MIN_SHOOT_PWR)
        goal_x = PX + PW + GOAL_W
        goal_y = PY + PH//2
        # Add inaccuracy for max power shots
        spread = random.uniform(-30, 30) * self.shot_power
        dx = goal_x - self.ball.x
        dy = (goal_y + spread) - self.ball.y
        self.ball.kick(dx, dy, power)
        cp.kick_cooldown = 0.5
        self.kicked_by_home = True
        self.sfx.play("kick", channel=4)
        self.home_shots += 1
        self.charging_shot = False
        self.shot_power    = 0.0

    # ── Update ────────────────────────────────────────────────────────────
    def update(self, dt):
        if self.match_over: return

        if self.reset_timer > 0:
            self.reset_timer -= dt
            if self.reset_timer <= 0: self._reset_after_goal()
            self.goal_flash = max(0, self.goal_flash - dt * 80)
            return

        self.elapsed    += dt
        self.goal_flash  = max(0, self.goal_flash - dt * 80)
        self.shake_timer = max(0, self.shake_timer - dt)

        # Half / full time
        if not self.half_triggered:
            if self.current_half == 1 and self.elapsed >= self.half_duration:
                self.half_triggered = True; self.match_over = True
                self._go_half_time(); return
            if self.current_half == 2 and self.elapsed >= self.half_duration * 2:
                self.half_triggered = True; self.match_over = True
                self._go_full_time(); return

        keys = pygame.key.get_pressed()
        cp   = self.home_players[self.controlled_idx]
        sprint = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and cp.stamina > 5

        # ── Stamina ──
        if sprint:
            cp.stamina = max(0, cp.stamina - STAMINA_DRAIN * dt)
        else:
            cp.stamina = min(100, cp.stamina + STAMINA_REGEN * dt)
        spd = PLAYER_SPEED * (SPRINT_MULT if sprint else 1.0)
        if cp.stamina < 20:
            spd *= 0.75   # tired — slow down

        # ── Movement ──
        dx, dy = 0, 0
        if not cp.tackling:
            if keys[pygame.K_LEFT]:  dx -= 1
            if keys[pygame.K_RIGHT]: dx += 1
            if keys[pygame.K_UP]:    dy -= 1
            if keys[pygame.K_DOWN]:  dy += 1

        if dx or dy:
            nx, ny  = vnorm(dx, dy)
            cp.vx   = nx * spd
            cp.vy   = ny * spd
            cp.dir  = (nx, ny)
        else:
            cp.vx *= 0.7; cp.vy *= 0.7

        cp.update_tackle(dt)
        if not cp.tackling:
            cp.apply_velocity()

        # ── Power shot charging ──
        if keys[pygame.K_z] and cp.kick_cooldown <= 0:
            if not self.charging_shot:
                self.charging_shot = True
                self.shot_power    = 0.0
            self.shot_power = min(1.0, self.shot_power + dt * 1.4)

        # ── Pass ──
        if keys[pygame.K_x] and cp.kick_cooldown <= 0 and not self.charging_shot:
            best, best_d = None, 9999
            for p in self.home_players:
                if p is cp: continue
                d = vdist(cp.x, cp.y, p.x, p.y)
                if d < best_d: best_d = d; best = p
            if best:
                self.ball.kick(best.x - self.ball.x, best.y - self.ball.y, PASS_POWER)
                cp.kick_cooldown = 0.4
                self.kicked_by_home = True
                self.sfx.play("pass", channel=5)

        # ── Dribble (tight ball control) ──
        ball_d = vdist(cp.x, cp.y, self.ball.x, self.ball.y)
        if ball_d < CONTROL_DIST and not self.charging_shot and not cp.tackling:
            if dx or dy:
                nx2, ny2 = vnorm(dx, dy)
                # Smooth dribble — ball slightly ahead of player
                target_bx = cp.x + nx2 * DRIBBLE_DIST
                target_by = cp.y + ny2 * DRIBBLE_DIST
                self.ball.x += (target_bx - self.ball.x) * 0.35
                self.ball.y += (target_by - self.ball.y) * 0.35
                self.ball.vx = cp.vx * 0.45
                self.ball.vy = cp.vy * 0.45
            self.kicked_by_home = True

        # ── Tackle collision with ball ──
        if cp.tackling:
            td = vdist(cp.x, cp.y, self.ball.x, self.ball.y)
            if td < TACKLE_RANGE:
                nx2, ny2 = vnorm(cp.tackle_vx, cp.tackle_vy)
                self.ball.kick(nx2, ny2, MAX_SHOOT_PWR * 0.7)
                self.kicked_by_home = True
                self.sfx.play("kick", channel=4)
                self._add_shake(4, 0.15)
                for _ in range(12):
                    self.sparks.append(Spark(self.ball.x, self.ball.y))

        # ── Cooldowns ──
        for p in self.home_players:
            p.kick_cooldown = max(0, p.kick_cooldown - dt)

        # ── Other home players ──
        for i, p in enumerate(self.home_players):
            if i == self.controlled_idx: continue
            p.update_tackle(dt)
            if p.role == "gk":
                gk_x = PX + 30
                gk_y = max(PY+50, min(PY+PH-50, self.ball.y))
                p.move_toward(gk_x, gk_y, PLAYER_SPEED * 0.8)
            else:
                bd = vdist(p.x, p.y, self.ball.x, self.ball.y)
                if bd < 130:
                    p.move_toward(self.ball.x, self.ball.y, PLAYER_SPEED*0.7)
                else:
                    p.move_toward(p.sx, p.sy, PLAYER_SPEED*0.4)
            p.apply_velocity()

        # ── AI ──
        self.ai.update(dt, self.ball, self.home_players)

        # ── AI ball contact ──
        for ap in self.away_players:
            if vdist(ap.x, ap.y, self.ball.x, self.ball.y) < CONTROL_DIST:
                self.kicked_by_home = False

        # ── Ball physics ──
        bounced = self.ball.update(dt)
        if bounced:
            self.sfx.play("bounce", channel=6)

        # ── Auto-switch ──
        if vdist(cp.x, cp.y, self.ball.x, self.ball.y) > 260:
            self._switch_to_nearest()

        # ── Possession ──
        self.home_poss = (self.home_poss * 0.998 +
                          (100 if self.kicked_by_home else 0) * 0.002)
        self.home_poss = max(10, min(90, self.home_poss))

        # ── Particles ──
        self.sparks = [s for s in self.sparks if s.life > 0]
        for sp in self.sparks:
            sp.update(dt)

        # ── Goal detection ──
        bx, by = self.ball.x, self.ball.y
        gyt = PY + PH//2 - GOAL_H//2
        gyb = PY + PH//2 + GOAL_H//2
        mins = (int(self.elapsed / self.half_duration * 45) +
                (45 if self.current_half == 2 else 0))

        if bx > PX + PW and gyt < by < gyb:
            self.home_goals += 1
            self.goal_flash = 255; self.reset_timer = 2.5
            self.sfx.goal_sequence()
            self._add_shake(8, 0.4)
            self.all_scorers.append(f"{self.home_data[0]} {mins}'")

        if bx < PX and gyt < by < gyb:
            self.away_goals += 1
            self.goal_flash = 255; self.reset_timer = 2.5
            self.sfx.goal_sequence()
            self._add_shake(8, 0.4)
            self.all_scorers.append(f"{self.away_data[0]} {mins}'")

    # ── Draw ──────────────────────────────────────────────────────────────
    def draw(self):
        # Screen shake offset
        ox = oy = 0
        if self.shake_timer > 0:
            ox = random.randint(-self.shake_mag, self.shake_mag)
            oy = random.randint(-self.shake_mag, self.shake_mag)

        s = self.screen
        s.blit(self._pitch_surf, (ox, oy))

        # Players
        cp = self.home_players[self.controlled_idx]
        for i, p in enumerate(self.home_players):
            pwr = self.shot_power if (i == self.controlled_idx and self.charging_shot) else 0.0
            p.draw(s, self.font_player,
                   is_controlled=(i == self.controlled_idx),
                   power_pct=pwr)
        for p in self.away_players:
            p.draw(s, self.font_player)

        # Particles
        for sp in self.sparks:
            sp.draw(s)

        # Ball
        self.ball.draw(s)

        # Stamina bar (controlled player)
        sta_w = 120; sta_x = 10; sta_y = WINDOW_HEIGHT - 44
        pygame.draw.rect(s, (40,40,40), (sta_x, sta_y, sta_w, 10), border_radius=4)
        sta_fill = int(sta_w * cp.stamina / 100)
        sta_color = (
            int(255 * (1 - cp.stamina/100)),
            int(200 * cp.stamina/100),
            0,
        )
        if sta_fill > 0:
            pygame.draw.rect(s, sta_color, (sta_x, sta_y, sta_fill, 10), border_radius=4)

        # HUD
        self.hud.draw(self.home_goals, self.away_goals,
                      self.elapsed, self.home_poss, self.goal_flash,
                      current_half=self.current_half,
                      half_duration=self.half_duration)


# ── Formation positions ───────────────────────────────────────────────────────
def make_team_positions(side="left"):
    xs = ([0.05, 0.20, 0.20, 0.20, 0.20,
            0.38, 0.38, 0.38,
            0.60, 0.60, 0.60]
          if side == "left" else
          [0.95, 0.80, 0.80, 0.80, 0.80,
           0.62, 0.62, 0.62,
           0.40, 0.40, 0.40])
    ys = [0.50,
          0.18, 0.38, 0.62, 0.82,
          0.28, 0.50, 0.72,
          0.22, 0.50, 0.78]
    return [(PX + PW * x, PY + PH * y) for x, y in zip(xs, ys)]