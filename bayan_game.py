"""
بيان والحية - Bayan vs the Snake
لعبة pygame: ساعد بيان تجمع الجواهر وتهرب من الحية.

التحكم:
  الأسهم / WASD  -> الحركة
  Space / Shift  -> اندفاع سريع (Dash) - بيان ما بتنمسك وهي مندفعة
  P / Esc        -> إيقاف مؤقت
"""
import array
import math
import os
import random
import sys

import pygame
from pygame import Vector2 as V

# ---------------------------------------------------------------- settings
W, H = 960, 640
TOP = 52            # height of the top info bar
FPS = 60
HERE = os.path.dirname(os.path.abspath(__file__))
HS_FILE = os.path.join(HERE, "highscore.txt")

BAYAN_SPEED = 230
DASH_SPEED = 580
DASH_TIME = 0.16
DASH_COOLDOWN = 1.8
START_LIVES = 3

# Each level: number of snakes, speed, turn rate (rad/s), body length,
# gems needed, rocks on the map, and how far ahead the snake aims.
LEVELS = [
    dict(snakes=1, speed=115, turn=2.2, length=10, gems=5,  rocks=0, predict=0.0),
    dict(snakes=1, speed=135, turn=2.6, length=12, gems=7,  rocks=3, predict=0.0),
    dict(snakes=2, speed=120, turn=2.5, length=12, gems=8,  rocks=4, predict=0.2),
    dict(snakes=2, speed=140, turn=2.9, length=14, gems=10, rocks=5, predict=0.35),
    dict(snakes=3, speed=145, turn=3.1, length=14, gems=12, rocks=6, predict=0.45),
]

SNAKE_COLORS = [
    ((60, 170, 70), (40, 130, 50)),     # green
    ((150, 110, 200), (110, 75, 160)),  # purple
    ((220, 140, 40), (180, 100, 25)),   # orange
]

# ---------------------------------------------------------------- arabic text
try:
    import arabic_reshaper
    try:
        from bidi import get_display
    except ImportError:
        from bidi.algorithm import get_display
    ARABIC = True
except ImportError:
    ARABIC = False


def T(ar, en):
    """Arabic text when the shaping libraries exist, English otherwise."""
    if ARABIC:
        return get_display(arabic_reshaper.reshape(ar))
    return en


def load_font(size, bold=False):
    name = "tahomabd.ttf" if bold else "tahoma.ttf"
    for folder in ("C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts"):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("tahoma,arial,dejavusans", size, bold=bold)


# ---------------------------------------------------------------- sounds
def make_sound(parts, vol=0.3):
    """parts: list of (start_freq, end_freq, seconds). Returns a Sound or None."""
    init = pygame.mixer.get_init()
    if not init or init[1] != -16:
        return None
    rate, _, channels = init
    buf = array.array("h")
    phase = 0.0
    for f0, f1, dur in parts:
        n = max(1, int(rate * dur))
        for i in range(n):
            f = f0 + (f1 - f0) * i / n
            phase += 2 * math.pi * f / rate
            env = min(1.0, i / (rate * 0.004)) * (1 - i / n)
            s = int(32767 * vol * env * math.sin(phase))
            buf.extend([s] * channels)
    return pygame.mixer.Sound(buffer=buf.tobytes())


def make_sounds():
    try:
        return {
            "gem": make_sound([(880, 1320, 0.07), (1320, 1760, 0.08)]),
            "hit": make_sound([(260, 70, 0.35)], 0.4),
            "dash": make_sound([(500, 250, 0.08)], 0.2),
            "heart": make_sound([(660, 990, 0.1), (990, 1320, 0.1)]),
            "level": make_sound([(523, 523, 0.12), (659, 659, 0.12), (784, 784, 0.12), (1047, 1047, 0.25)]),
            "lose": make_sound([(400, 300, 0.2), (300, 200, 0.2), (200, 100, 0.4)], 0.35),
        }
    except Exception:
        return {}


# ---------------------------------------------------------------- helpers
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def angle_diff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


class Rock:
    def __init__(self, x, y, r):
        self.pos = V(x, y)
        self.r = r
        # a bumpy outline so rocks don't look like perfect circles
        self.shape = []
        for i in range(10):
            a = i / 10 * 2 * math.pi
            rr = r * random.uniform(0.85, 1.08)
            self.shape.append((math.cos(a) * rr, math.sin(a) * rr))

    def push_out(self, pos, radius):
        d = pos - self.pos
        dist = d.length()
        min_d = self.r + radius
        if dist < min_d:
            if dist == 0:
                d, dist = V(1, 0), 1
            pos.update(self.pos + d / dist * min_d)

    def draw(self, surf):
        x, y = self.pos
        pygame.draw.ellipse(surf, (40, 90, 40), (x - self.r, y + self.r * 0.5, self.r * 2, self.r * 0.8))
        pts = [(x + px, y + py) for px, py in self.shape]
        pygame.draw.polygon(surf, (120, 115, 110), pts)
        pygame.draw.polygon(surf, (80, 75, 72), pts, 3)
        pygame.draw.circle(surf, (160, 155, 150), (int(x - self.r * 0.3), int(y - self.r * 0.3)), max(3, self.r // 4))


# ---------------------------------------------------------------- Bayan
class Bayan:
    R = 14

    def __init__(self, x, y):
        self.pos = V(x, y)
        self.vel = V()
        self.facing = V(1, 0)
        self.dash_t = 0.0
        self.dash_cd = 0.0
        self.invuln = 0.0
        self.walk = 0.0
        self.ghosts = []

    @property
    def dashing(self):
        return self.dash_t > 0

    @property
    def safe(self):
        return self.dashing or self.invuln > 0

    def try_dash(self):
        if self.dash_cd <= 0:
            self.dash_t = DASH_TIME
            self.dash_cd = DASH_COOLDOWN
            return True
        return False

    def update(self, dt, direction, rocks):
        old = V(self.pos)
        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.facing = V(direction)
        if self.dashing:
            move = self.facing * DASH_SPEED
            self.ghosts.append([V(self.pos), 0.25])
        else:
            move = direction * BAYAN_SPEED
        self.pos += move * dt
        self.pos.x = clamp(self.pos.x, self.R, W - self.R)
        self.pos.y = clamp(self.pos.y, TOP + self.R, H - self.R)
        for r in rocks:
            r.push_out(self.pos, self.R)

        self.vel = (self.pos - old) / dt if dt > 0 else V()
        if self.vel.length_squared() > 1:
            self.walk += dt * 14
        self.dash_t = max(0.0, self.dash_t - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.invuln = max(0.0, self.invuln - dt)
        for g in self.ghosts:
            g[1] -= dt
        self.ghosts = [g for g in self.ghosts if g[1] > 0]

    def draw(self, surf, t, label):
        for gpos, life in self.ghosts:
            s = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 150, 200, int(life * 600)), (15, 15), 12)
            surf.blit(s, (gpos.x - 15, gpos.y - 15))

        if self.invuln > 0 and int(t * 14) % 2 == 0:
            return  # blink while protected

        x, y = self.pos
        fx = self.facing.x
        pygame.draw.ellipse(surf, (40, 100, 40), (x - 12, y + 12, 24, 8))

        # legs
        swing = math.sin(self.walk) * 4 if self.vel.length_squared() > 1 else 0
        skin = (255, 214, 170)
        pygame.draw.line(surf, skin, (x - 4, y + 8), (x - 4 + swing, y + 16), 3)
        pygame.draw.line(surf, skin, (x + 4, y + 8), (x + 4 - swing, y + 16), 3)
        pygame.draw.circle(surf, (120, 60, 160), (int(x - 4 + swing), int(y + 17)), 3)
        pygame.draw.circle(surf, (120, 60, 160), (int(x + 4 - swing), int(y + 17)), 3)

        # arms
        pygame.draw.line(surf, skin, (x - 6, y - 3), (x - 11 - swing * 0.5, y + 5), 3)
        pygame.draw.line(surf, skin, (x + 6, y - 3), (x + 11 + swing * 0.5, y + 5), 3)

        # dress
        dress = [(x, y - 9), (x - 12, y + 11), (x + 12, y + 11)]
        pygame.draw.polygon(surf, (255, 105, 180), dress)
        pygame.draw.polygon(surf, (200, 60, 130), dress, 2)
        pygame.draw.line(surf, (255, 255, 255), (x - 9, y + 7), (x + 9, y + 7), 2)

        # ponytail (bounces behind her)
        bounce = math.sin(self.walk * 0.5) * 2
        tail_x = x - (fx if abs(fx) > 0.2 else 0.6) * 11
        pygame.draw.circle(surf, (80, 45, 25), (int(tail_x), int(y - 13 + bounce)), 5)

        # head
        pygame.draw.circle(surf, (80, 45, 25), (int(x), int(y - 17)), 10)
        if self.facing.y < -0.7:
            pass  # looking away: only hair is visible
        else:
            pygame.draw.circle(surf, skin, (int(x + fx * 2), int(y - 14)), 8)
            ex = x + fx * 3
            pygame.draw.circle(surf, (30, 30, 30), (int(ex - 3), int(y - 15)), 2)
            pygame.draw.circle(surf, (30, 30, 30), (int(ex + 3), int(y - 15)), 2)
            pygame.draw.circle(surf, (240, 120, 120), (int(ex - 5), int(y - 11)), 2)
            pygame.draw.circle(surf, (240, 120, 120), (int(ex + 5), int(y - 11)), 2)
            pygame.draw.arc(surf, (150, 50, 50), (ex - 3, y - 14, 6, 5), math.pi + 0.3, 2 * math.pi - 0.3, 1)
        # bow
        pygame.draw.polygon(surf, (230, 40, 80), [(x, y - 26), (x - 6, y - 30), (x - 6, y - 22)])
        pygame.draw.polygon(surf, (230, 40, 80), [(x, y - 26), (x + 6, y - 30), (x + 6, y - 22)])
        pygame.draw.circle(surf, (255, 200, 220), (int(x), int(y - 26)), 2)

        surf.blit(label, label.get_rect(center=(x, y - 40)))


# ---------------------------------------------------------------- Snake
class Snake:
    SPACING = 11

    def __init__(self, pos, cfg, colors, phase):
        self.base_speed = cfg["speed"]
        self.speed = cfg["speed"]
        self.turn = cfg["turn"]
        self.predict = cfg["predict"]
        self.color, self.color2 = colors
        self.phase = phase
        self.head_r = 13
        self.angle = 0.0
        self.sleep = 0.0
        self.body = [V(pos) for _ in range(cfg["length"])]

    @property
    def head(self):
        return self.body[0]

    def place(self, pos, toward):
        for seg in self.body:
            seg.update(pos)
        d = toward - pos
        self.angle = math.atan2(d.y, d.x)

    def grow(self, n=2):
        for _ in range(n):
            self.body.append(V(self.body[-1]))
        self.speed *= 1.03

    def update(self, dt, target_pos, target_vel, rocks, t):
        if self.sleep > 0:
            self.sleep -= dt
            return
        head = self.head
        target = target_pos + target_vel * self.predict
        want = target - head
        if want.length_squared() == 0:
            want = V(1, 0)
        want = want.normalize()

        fwd = V(math.cos(self.angle), math.sin(self.angle))
        # steer around rocks that are in front
        for r in rocks:
            d = head - r.pos
            dist = d.length()
            reach = r.r + 70
            if 0 < dist < reach and fwd.dot(-d) > 0:
                want += d / dist * ((reach - dist) / 70) * 1.6
        # keep away from walls
        m = 45
        if head.x < m: want.x += (m - head.x) / m
        if head.x > W - m: want.x -= (head.x - (W - m)) / m
        if head.y < TOP + m: want.y += (TOP + m - head.y) / m
        if head.y > H - m: want.y -= (head.y - (H - m)) / m

        desired = math.atan2(want.y, want.x)
        diff = angle_diff(desired, self.angle)
        step = self.turn * dt
        self.angle += clamp(diff, -step, step)

        wiggle = math.sin(t * 7 + self.phase) * 0.45
        move_ang = self.angle + wiggle
        head += V(math.cos(move_ang), math.sin(move_ang)) * self.speed * dt
        for r in rocks:
            r.push_out(head, self.head_r)
        head.x = clamp(head.x, self.head_r, W - self.head_r)
        head.y = clamp(head.y, TOP + self.head_r, H - self.head_r)

        # body follows like a chain
        for i in range(1, len(self.body)):
            prev, seg = self.body[i - 1], self.body[i]
            d = seg - prev
            dist = d.length()
            if dist > self.SPACING:
                seg.update(prev + d / dist * self.SPACING)

    def catches(self, bayan):
        return (self.head - bayan.pos).length() < self.head_r + bayan.R - 3

    def draw(self, surf, t):
        n = len(self.body)
        for i in range(n - 1, 0, -1):
            k = i / (n - 1)
            r = self.head_r * (1 - 0.6 * k)
            p = self.body[i]
            col = self.color if i % 2 else self.color2
            pygame.draw.circle(surf, col, (int(p.x), int(p.y)), int(r))
            pygame.draw.circle(surf, (min(255, col[0] + 50), min(255, col[1] + 50), min(255, col[2] + 50)),
                               (int(p.x - r * 0.3), int(p.y - r * 0.3)), max(1, int(r * 0.3)))

        h = self.head
        fwd = V(math.cos(self.angle), math.sin(self.angle))
        side = V(-fwd.y, fwd.x)
        # tongue flicks
        if (t * 2.5 + self.phase) % 1 < 0.35 and self.sleep <= 0:
            base = h + fwd * (self.head_r + 1)
            tip = base + fwd * 10
            pygame.draw.line(surf, (220, 30, 50), base, tip, 2)
            pygame.draw.line(surf, (220, 30, 50), tip, tip + fwd * 5 + side * 4, 2)
            pygame.draw.line(surf, (220, 30, 50), tip, tip + fwd * 5 - side * 4, 2)
        pygame.draw.circle(surf, self.color2, (int(h.x), int(h.y)), self.head_r + 2)
        pygame.draw.circle(surf, self.color, (int(h.x), int(h.y)), self.head_r)
        for s in (1, -1):
            e = h + fwd * 5 + side * 6 * s
            pygame.draw.circle(surf, (255, 240, 120), (int(e.x), int(e.y)), 4)
            if self.sleep > 0:
                pygame.draw.line(surf, (20, 20, 20), (e.x - 3, e.y), (e.x + 3, e.y), 2)  # closed eyes
            else:
                pygame.draw.ellipse(surf, (20, 20, 20), (e.x + fwd.x * 1.5 - 1, e.y + fwd.y * 1.5 - 3, 2, 6))


# ---------------------------------------------------------------- game
class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Bayan vs the Snake - بيان والحية")
        self.clock = pygame.time.Clock()
        self.world = pygame.Surface((W, H))

        self.f_huge = load_font(64, True)
        self.f_big = load_font(40, True)
        self.f_mid = load_font(26, True)
        self.f_small = load_font(20)
        self.f_tiny = load_font(15, True)
        self._cache = {}

        self.sounds = make_sounds()
        self.bg = self.make_background()
        self.highscore = self.load_highscore()
        self.name_label = self.text(T("بيان", "Bayan"), self.f_tiny, (255, 255, 255))

        self.t = 0.0
        self.shake = 0.0
        self.state = "menu"
        self.state_t = 0.0
        self.particles = []
        self.setup_demo()

    # ---------- utilities
    def text(self, s, font, color):
        key = (s, id(font), color)
        if key not in self._cache:
            if len(self._cache) > 300:
                self._cache.clear()
            self._cache[key] = font.render(s, True, color)
        return self._cache[key]

    def draw_text(self, surf, s, font, color, center, shadow=True):
        if shadow:
            sh = self.text(s, font, (20, 20, 20))
            surf.blit(sh, sh.get_rect(center=(center[0] + 2, center[1] + 2)))
        img = self.text(s, font, color)
        surf.blit(img, img.get_rect(center=center))

    def play(self, name):
        snd = self.sounds.get(name)
        if snd:
            snd.play()

    def load_highscore(self):
        try:
            with open(HS_FILE) as f:
                return int(f.read().strip() or 0)
        except (OSError, ValueError):
            return 0

    def save_highscore(self):
        if self.score > self.highscore:
            self.highscore = self.score
            try:
                with open(HS_FILE, "w") as f:
                    f.write(str(self.highscore))
            except OSError:
                pass

    def make_background(self):
        bg = pygame.Surface((W, H))
        bg.fill((110, 190, 90))
        rnd = random.Random(7)
        for _ in range(500):
            x, y = rnd.randrange(W), rnd.randrange(TOP, H)
            c = rnd.choice([(95, 170, 75), (125, 205, 100), (100, 180, 80)])
            pygame.draw.line(bg, c, (x, y), (x + rnd.randint(-3, 3), y - rnd.randint(4, 9)), 2)
        for _ in range(40):
            x, y = rnd.randrange(W), rnd.randrange(TOP + 10, H)
            c = rnd.choice([(255, 255, 255), (255, 230, 80), (255, 150, 200)])
            for a in range(5):
                ang = a / 5 * 2 * math.pi
                pygame.draw.circle(bg, c, (int(x + math.cos(ang) * 3), int(y + math.sin(ang) * 3)), 2)
            pygame.draw.circle(bg, (250, 200, 40), (x, y), 2)
        return bg

    def burst(self, pos, color, n=18, speed=160):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(speed * 0.3, speed)
            self.particles.append([V(pos), V(math.cos(a), math.sin(a)) * s, random.uniform(0.4, 0.8), color])

    def random_free_spot(self, radius, avoid=(), min_dist=0):
        for _ in range(200):
            p = V(random.uniform(40, W - 40), random.uniform(TOP + 40, H - 40))
            if any((p - r.pos).length() < r.r + radius + 8 for r in self.rocks):
                continue
            if any((p - a).length() < min_dist for a in avoid):
                continue
            return p
        return V(W / 2, (TOP + H) / 2)

    # ---------- menu demo (Bayan running in loops, snake chasing)
    def setup_demo(self):
        self.rocks = []
        self.demo_bayan = Bayan(W / 2, 470)
        cfg = dict(LEVELS[0], speed=170, turn=2.4, length=16)
        self.demo_snake = Snake(V(100, 470), cfg, SNAKE_COLORS[0], 0)

    def update_demo(self, dt):
        b = self.demo_bayan
        old = V(b.pos)
        a = self.t * 0.9
        b.pos.update(W / 2 + math.cos(a) * 300, 480 + math.sin(a * 2) * 70)
        b.vel = (b.pos - old) / dt if dt else V()
        if b.vel.length_squared() > 0:
            b.facing = b.vel.normalize()
        b.walk += dt * 14
        self.demo_snake.update(dt, b.pos, V(), [], self.t)

    # ---------- level flow
    def new_game(self):
        self.level_i = 0
        self.score = 0
        self.start_level()

    def start_level(self):
        cfg = LEVELS[self.level_i]
        self.cfg = cfg
        self.lives = START_LIVES
        self.level_start_score = self.score
        self.bayan = Bayan(W / 2, (TOP + H) / 2)
        self.particles = []
        self.rocks = []
        center = V(W / 2, (TOP + H) / 2)
        corners = [V(60, TOP + 60), V(W - 60, TOP + 60), V(60, H - 60), V(W - 60, H - 60)]
        for _ in range(cfg["rocks"]):
            for _ in range(100):
                r = random.randint(22, 38)
                p = V(random.uniform(80, W - 80), random.uniform(TOP + 80, H - 80))
                if (p - center).length() < 140:
                    continue
                if any((p - c).length() < 130 for c in corners):
                    continue
                if any((p - o.pos).length() < r + o.r + 60 for o in self.rocks):
                    continue
                self.rocks.append(Rock(p.x, p.y, r))
                break

        random.shuffle(corners)
        self.snakes = []
        for i in range(cfg["snakes"]):
            s = Snake(corners[i], cfg, SNAKE_COLORS[i % len(SNAKE_COLORS)], i * 2.1)
            s.place(corners[i], center)
            s.sleep = 0.4 * i
            self.snakes.append(s)

        self.collected = 0
        self.goal = cfg["gems"]
        self.heart = None
        self.spawn_gem()
        self.level_time = 0.0
        self.set_state("intro")

    def spawn_gem(self):
        avoid = [self.bayan.pos] + [s.head for s in self.snakes]
        self.gem = self.random_free_spot(14, avoid, 160)

    def set_state(self, s):
        self.state = s
        self.state_t = 0.0

    def caught(self):
        self.lives -= 1
        self.shake = 0.4
        self.burst(self.bayan.pos, (255, 80, 120), 30, 220)
        if self.lives <= 0:
            self.play("lose")
            self.save_highscore()
            self.set_state("game_over")
            return
        self.play("hit")
        self.bayan.invuln = 2.0
        # send snakes back to the corners farthest from Bayan
        corners = [V(60, TOP + 60), V(W - 60, TOP + 60), V(60, H - 60), V(W - 60, H - 60)]
        corners.sort(key=lambda c: -(c - self.bayan.pos).length())
        for i, s in enumerate(self.snakes):
            s.place(corners[i % 4], self.bayan.pos)
            s.sleep = 1.0

    # ---------- per-frame update
    def update(self, dt, direction):
        self.t += dt
        self.state_t += dt
        self.shake = max(0.0, self.shake - dt)

        for p in self.particles:
            p[0] += p[1] * dt
            p[1] *= 0.92
            p[2] -= dt
        self.particles = [p for p in self.particles if p[2] > 0]

        if self.state == "menu":
            self.update_demo(dt)
        elif self.state == "intro":
            if self.state_t >= 3.0:
                self.set_state("play")
        elif self.state == "play":
            self.update_play(dt, direction)
        elif self.state == "level_done":
            if self.state_t >= 3.0:
                self.next_level()

    def update_play(self, dt, direction):
        b = self.bayan
        self.level_time += dt
        b.update(dt, direction, self.rocks)
        for s in self.snakes:
            s.update(dt, b.pos, b.vel, self.rocks, self.t)
            if not b.safe and s.catches(b):
                self.caught()
                return

        if self.gem and (self.gem - b.pos).length() < b.R + 14:
            self.play("gem")
            self.burst(self.gem, (255, 230, 80))
            self.score += 100 * (self.level_i + 1)
            self.collected += 1
            for s in self.snakes:
                s.grow()
            if self.collected >= self.goal:
                self.gem = None
                bonus = max(0, int((self.goal * 8 - self.level_time) * 10))
                self.level_bonus = bonus
                self.score += bonus
                self.save_highscore()
                self.play("level")
                self.burst(b.pos, (255, 255, 255), 40, 260)
                self.set_state("level_done")
                return
            self.spawn_gem()
            if self.heart is None and self.lives < START_LIVES and random.random() < 0.3:
                self.heart = [self.random_free_spot(12, [b.pos], 120), 8.0]

        if self.heart:
            self.heart[1] -= dt
            if (self.heart[0] - b.pos).length() < b.R + 12:
                self.lives = min(START_LIVES, self.lives + 1)
                self.play("heart")
                self.burst(self.heart[0], (255, 80, 120))
                self.heart = None
            elif self.heart[1] <= 0:
                self.heart = None

    def next_level(self):
        self.level_i += 1
        if self.level_i >= len(LEVELS):
            self.save_highscore()
            self.set_state("win")
        else:
            self.start_level()

    # ---------- input
    def handle_key(self, key):
        enter = key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
        if self.state == "menu":
            if enter:
                self.new_game()
            elif key == pygame.K_ESCAPE:
                return False
        elif self.state == "play":
            if key in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT):
                if self.bayan.try_dash():
                    self.play("dash")
            elif key in (pygame.K_p, pygame.K_ESCAPE):
                self.set_state("paused")
        elif self.state == "paused":
            if key in (pygame.K_p, pygame.K_RETURN):
                self.set_state("play")
            elif key in (pygame.K_ESCAPE, pygame.K_m):
                self.save_highscore()
                self.setup_demo()
                self.set_state("menu")
        elif self.state == "level_done":
            if enter and self.state_t > 0.6:
                self.next_level()
        elif self.state == "game_over":
            if self.state_t < 0.8:
                return True
            if enter:  # try the same level again
                self.score = self.level_start_score
                self.start_level()
            elif key in (pygame.K_ESCAPE, pygame.K_m):
                self.setup_demo()
                self.set_state("menu")
        elif self.state == "win":
            if self.state_t > 0.8 and (enter or key == pygame.K_ESCAPE):
                self.setup_demo()
                self.set_state("menu")
        return True

    # ---------- drawing
    def draw_heart(self, surf, x, y, size, color=(235, 50, 80)):
        r = size // 2
        pygame.draw.circle(surf, color, (x - r // 2 - 1, y), r // 2 + 2)
        pygame.draw.circle(surf, color, (x + r // 2 + 1, y), r // 2 + 2)
        pygame.draw.polygon(surf, color, [(x - r - 1, y + 1), (x + r + 1, y + 1), (x, y + r + 4)])

    def draw_gem(self, surf, pos, t, size=12):
        pulse = 1 + math.sin(t * 6) * 0.12
        s = size * pulse
        glow = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 240, 120, 70), (40, 40), int(s * 2.2))
        surf.blit(glow, (pos.x - 40, pos.y - 40))
        a = t * 2
        pts = []
        for i in range(4):
            ang = a + i * math.pi / 2
            rr = s if i % 2 == 0 else s * 0.7
            pts.append((pos.x + math.cos(ang) * rr, pos.y + math.sin(ang) * rr))
        pygame.draw.polygon(surf, (255, 215, 40), pts)
        pygame.draw.polygon(surf, (255, 255, 200), pts, 2)

    def draw_hud(self, surf):
        bar = pygame.Surface((W, TOP), pygame.SRCALPHA)
        bar.fill((20, 40, 25, 210))
        surf.blit(bar, (0, 0))
        # hearts on the left
        for i in range(START_LIVES):
            col = (235, 50, 80) if i < self.lives else (80, 80, 80)
            self.draw_heart(surf, 28 + i * 34, 22, 20, col)
        # dash meter
        b = self.bayan
        ready = 1 - b.dash_cd / DASH_COOLDOWN
        pygame.draw.rect(surf, (60, 60, 60), (130, 17, 110, 16), border_radius=8)
        pygame.draw.rect(surf, (120, 220, 255) if ready >= 1 else (90, 140, 170),
                         (130, 17, int(110 * ready), 16), border_radius=8)
        self.draw_text(surf, T("اندفاع", "Dash"), self.f_tiny, (255, 255, 255), (185, 25), False)
        # gems in the middle
        self.draw_gem(surf, V(W / 2 - 50, 26), self.t, 10)
        self.draw_text(surf, f"{self.collected} / {self.goal}", self.f_mid, (255, 235, 120), (W / 2 + 10, 25))
        # level & score on the right
        self.draw_text(surf, T(f"المرحلة {self.level_i + 1}/{len(LEVELS)}",
                               f"Level {self.level_i + 1}/{len(LEVELS)}"),
                       self.f_small, (255, 255, 255), (W - 90, 25))
        self.draw_text(surf, T(f"النقاط {self.score}", f"Score {self.score}"),
                       self.f_small, (255, 255, 255), (W - 260, 25))

    def overlay(self, surf, alpha=150):
        o = pygame.Surface((W, H), pygame.SRCALPHA)
        o.fill((0, 0, 0, alpha))
        surf.blit(o, (0, 0))

    def draw_particles(self, surf):
        for pos, _, life, col in self.particles:
            pygame.draw.circle(surf, col, (int(pos.x), int(pos.y)), max(1, int(life * 6)))

    def draw(self):
        surf = self.world
        surf.blit(self.bg, (0, 0))

        if self.state == "menu":
            self.draw_menu(surf)
        else:
            for r in self.rocks:
                r.draw(surf)
            if self.gem:
                self.draw_gem(surf, self.gem, self.t)
            if self.heart and (self.heart[1] > 2 or int(self.t * 8) % 2):
                hy = self.heart[0].y + math.sin(self.t * 4) * 3
                self.draw_heart(surf, int(self.heart[0].x), int(hy), 22)
            for s in self.snakes:
                s.draw(surf, self.t)
            if self.state != "game_over":
                self.bayan.draw(surf, self.t, self.name_label)
            self.draw_particles(surf)
            self.draw_hud(surf)
            self.draw_state_overlay(surf)

        off = (0, 0)
        if self.shake > 0:
            m = int(self.shake * 25)
            off = (random.randint(-m, m), random.randint(-m, m))
        self.screen.fill((0, 0, 0))
        self.screen.blit(surf, off)
        pygame.display.flip()

    def draw_menu(self, surf):
        self.demo_snake.draw(surf, self.t)
        self.demo_bayan.draw(surf, self.t, self.name_label)
        self.overlay(surf, 90)
        bob = math.sin(self.t * 2) * 5
        self.draw_text(surf, T("بيان والحية", "Bayan vs the Snake"), self.f_huge, (255, 220, 240), (W / 2, 110 + bob))
        self.draw_text(surf, T("ساعد بيان تجمع الجواهر وتهرب من الحية!",
                               "Help Bayan collect gems and escape the snake!"),
                       self.f_small, (255, 255, 255), (W / 2, 180))
        lines = [
            T("الأسهم أو WASD : الحركة", "Arrows / WASD : move"),
            T("Space : اندفاع سريع - الحية ما بتقدر تمسكها وقتها", "Space : dash - can't be caught while dashing"),
            T("P : إيقاف مؤقت", "P : pause"),
        ]
        for i, line in enumerate(lines):
            self.draw_text(surf, line, self.f_small, (230, 240, 230), (W / 2, 235 + i * 32))
        if int(self.t * 2) % 2 == 0:
            self.draw_text(surf, T("اضغط Enter للبدء", "Press Enter to start"), self.f_mid, (255, 235, 120), (W / 2, 360))
        self.draw_text(surf, T(f"أعلى نتيجة: {self.highscore}", f"High score: {self.highscore}"),
                       self.f_small, (255, 255, 255), (W / 2, 400))

    def draw_state_overlay(self, surf):
        cx, cy = W / 2, (TOP + H) / 2
        if self.state == "intro":
            self.overlay(surf, 110)
            self.draw_text(surf, T(f"المرحلة {self.level_i + 1}", f"Level {self.level_i + 1}"),
                           self.f_huge, (255, 220, 240), (cx, cy - 90))
            n = self.cfg["snakes"]
            info = T(f"اجمعي {self.goal} جواهر  -  عدد الحيات: {n}",
                     f"Collect {self.goal} gems  -  snakes: {n}")
            self.draw_text(surf, info, self.f_mid, (255, 255, 255), (cx, cy - 20))
            if self.cfg["rocks"]:
                self.draw_text(surf, T("انتبهي! في صخور بالطريق", "Watch out for rocks!"),
                               self.f_small, (230, 230, 230), (cx, cy + 20))
            count = 3 - int(self.state_t)
            self.draw_text(surf, str(max(1, count)), self.f_huge, (255, 235, 120), (cx, cy + 90))
        elif self.state == "paused":
            self.overlay(surf)
            self.draw_text(surf, T("إيقاف مؤقت", "Paused"), self.f_big, (255, 255, 255), (cx, cy - 30))
            self.draw_text(surf, T("P للمتابعة  -  Esc للقائمة", "P: resume  -  Esc: menu"),
                           self.f_small, (230, 230, 230), (cx, cy + 25))
        elif self.state == "level_done":
            self.overlay(surf, 120)
            self.draw_text(surf, T("أحسنتِ يا بيان!", "Well done, Bayan!"), self.f_huge, (255, 235, 120), (cx, cy - 60))
            self.draw_text(surf, T(f"مكافأة السرعة: {self.level_bonus}", f"Speed bonus: {self.level_bonus}"),
                           self.f_mid, (255, 255, 255), (cx, cy + 10))
            last = self.level_i + 1 >= len(LEVELS)
            msg = T("Enter للنهاية", "Enter: finish") if last else T("Enter للمرحلة التالية", "Enter: next level")
            self.draw_text(surf, msg, self.f_small, (230, 230, 230), (cx, cy + 60))
        elif self.state == "game_over":
            self.overlay(surf, 160)
            self.draw_text(surf, T("مسكتك الحية!", "The snake caught you!"), self.f_huge, (255, 110, 110), (cx, cy - 80))
            self.draw_text(surf, T(f"النقاط: {self.score}   -   أعلى نتيجة: {self.highscore}",
                                   f"Score: {self.score}   -   High score: {self.highscore}"),
                           self.f_mid, (255, 255, 255), (cx, cy - 10))
            self.draw_text(surf, T("Enter لإعادة المرحلة  -  Esc للقائمة", "Enter: retry level  -  Esc: menu"),
                           self.f_small, (230, 230, 230), (cx, cy + 45))
        elif self.state == "win":
            self.overlay(surf, 140)
            if random.random() < 0.3:
                self.burst(V(random.uniform(100, W - 100), random.uniform(TOP + 50, H - 100)),
                           random.choice([(255, 220, 80), (255, 120, 180), (120, 220, 255)]), 20, 200)
            self.draw_text(surf, T("بيان نجت من كل الحيات!", "Bayan escaped every snake!"),
                           self.f_big, (255, 235, 120), (cx, cy - 70))
            self.draw_text(surf, T(f"النتيجة النهائية: {self.score}", f"Final score: {self.score}"),
                           self.f_mid, (255, 255, 255), (cx, cy - 5))
            if self.score >= self.highscore:
                self.draw_text(surf, T("رقم قياسي جديد!", "New high score!"), self.f_mid, (255, 150, 200), (cx, cy + 40))
            self.draw_text(surf, T("Enter للقائمة", "Enter: menu"), self.f_small, (230, 230, 230), (cx, cy + 90))

    # ---------- main loop
    def read_direction(self):
        k = pygame.key.get_pressed()
        x = (k[pygame.K_RIGHT] or k[pygame.K_d]) - (k[pygame.K_LEFT] or k[pygame.K_a])
        y = (k[pygame.K_DOWN] or k[pygame.K_s]) - (k[pygame.K_UP] or k[pygame.K_w])
        return V(x, y)

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000, 1 / 30)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.KEYDOWN:
                    running = self.handle_key(e.key)
            self.update(dt, self.read_direction())
            self.draw()
        if hasattr(self, "score"):
            self.save_highscore()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
    sys.exit()
