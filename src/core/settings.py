"""
settings.py — Global constants and configuration for the entire game.
Edit this file to tune the game without touching logic.
"""

# ── Window ──────────────────────────────────────────────────────────────────
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 720
GAME_TITLE    = "STRIKER FC"
FPS           = 60

# ── Colours (R, G, B) ────────────────────────────────────────────────────────
BLACK         = (0,   0,   0)
WHITE         = (255, 255, 255)
DARK_BG       = (8,   12,  20)          # deep navy — main background
PITCH_GREEN   = (34,  85,  34)
PITCH_LIGHT   = (40,  100, 40)
GOLD          = (212, 175, 55)
GOLD_LIGHT    = (255, 215, 80)
ACCENT_CYAN   = (0,   220, 200)
MENU_OVERLAY  = (8,   12,  20, 200)     # semi-transparent navy
GREY_DARK     = (30,  35,  45)
GREY_MID      = (70,  80,  100)
GREY_LIGHT    = (150, 160, 180)
RED_ACCENT    = (220, 50,  50)

# ── Physics ──────────────────────────────────────────────────────────────────
GRAVITY         = 0.3
BALL_FRICTION   = 0.985
PLAYER_SPEED    = 4.5
PLAYER_SPRINT   = 7.0
BALL_MAX_SPEED  = 18.0

# ── Pitch dimensions (pixels) ────────────────────────────────────────────────
PITCH_X      = 60
PITCH_Y      = 60
PITCH_W      = WINDOW_WIDTH  - 120
PITCH_H      = WINDOW_HEIGHT - 120
GOAL_WIDTH   = 80
GOAL_HEIGHT  = 140

# ── Match ────────────────────────────────────────────────────────────────────
MATCH_DURATION  = 90          # in-game minutes
REAL_SECONDS_PER_MIN = 4      # 1 game-min = 4 real seconds  → 6 min match

# ── Team sizes ───────────────────────────────────────────────────────────────
TEAM_SIZE    = 11
SQUAD_SIZE   = 23

# ── Asset paths ──────────────────────────────────────────────────────────────
FONT_DIR     = "assets/fonts"
IMAGE_DIR    = "assets/images"
SOUND_DIR    = "assets/sounds"
DATA_DIR     = "data"
SAVE_DIR     = "saves"

# ── Game states ──────────────────────────────────────────────────────────────
STATE_MAIN_MENU     = "main_menu"
STATE_TEAM_SELECT   = "team_select"
STATE_MATCH         = "match"
STATE_HALF_TIME     = "half_time"
STATE_FULL_TIME     = "full_time"
STATE_SETTINGS      = "settings"
STATE_QUIT          = "quit"