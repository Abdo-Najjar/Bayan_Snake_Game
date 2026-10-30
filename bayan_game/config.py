"""Global constants: screen size, tuning values and file paths."""
import os

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(PACKAGE_DIR)
ASSETS_DIR = os.path.join(PACKAGE_DIR, "assets")
LANG_DIR = os.path.join(ASSETS_DIR, "lang")
SAVE_FILE = os.environ.get("BAYAN_SAVE_FILE", os.path.join(PROJECT_DIR, "save.json"))

DEFAULT_LANGUAGE = "ar"
FALLBACK_LANGUAGE = "en"

# The game is drawn at this logical size and scaled to fit the window/screen.
W, H = 960, 640
TOP = 52            # height of the in-game info bar
FPS = 60

# Bayan
BAYAN_SPEED = 230
BAYAN_RADIUS = 14
DASH_SPEED = 580
DASH_TIME = 0.16
DASH_COOLDOWN = 1.8
SPEED_BOOST = 1.45
SLOW_FACTOR = 0.5       # quicksand and poison
ICE_GRIP = 2.2          # lower = more slippery
START_LIVES = 3
HIT_INVULNERABILITY = 2.0

# Snakes
SNAKE_MAX_SPEED = 205
SNAKE_GROWTH = 1.03     # speed multiplier per collected gem
BOSS_HP = 3
BOSS_CHARGE_SPEED = 480

# Power-ups
POWER_KINDS = ("speed", "shield", "freeze", "ghost")
POWER_DURATION = {"speed": 5.0, "ghost": 4.5, "freeze": 3.5}
POWER_SPAWN_DELAY = (7.0, 12.0)
POWER_LIFETIME = 9.0

# Rewards
COINS_PER_GEM = 2
COINS_PER_STAR = 3
BOSS_COINS = 30

# Snake speed multiplier for each difficulty (index stored in the save file)
DIFFICULTY_SPEED = (0.85, 1.0, 1.15)
DIFFICULTY_KEYS = ("easy", "normal", "hard")
