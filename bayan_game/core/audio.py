"""Sound effects and background music, generated in code (no audio files needed)."""
import array
import math
import random

import pygame


def _format():
    init = pygame.mixer.get_init()
    if not init or init[1] != -16:
        return None
    return init[0], init[2]   # sample rate, channels


def make_tone(parts, vol=0.3, noise=False):
    """parts: list of (start_freq, end_freq, seconds)."""
    fmt = _format()
    if not fmt:
        return None
    rate, channels = fmt
    buf = array.array("h")
    phase = 0.0
    for f0, f1, dur in parts:
        n = max(1, int(rate * dur))
        for i in range(n):
            env = min(1.0, i / (rate * 0.004)) * (1 - i / n)
            if noise:
                v = random.uniform(-1, 1)
            else:
                phase += 2 * math.pi * (f0 + (f1 - f0) * i / n) / rate
                v = math.sin(phase)
            s = int(32767 * vol * env * v)
            for _ in range(channels):
                buf.append(s)
    return pygame.mixer.Sound(buffer=buf.tobytes())


def make_sounds():
    try:
        return {
            "gem": make_tone([(880, 1320, 0.07), (1320, 1760, 0.08)]),
            "coin": make_tone([(1400, 1400, 0.05), (1900, 1900, 0.1)], 0.2),
            "hit": make_tone([(260, 70, 0.35)], 0.4),
            "dash": make_tone([(500, 250, 0.08)], 0.2),
            "heart": make_tone([(660, 990, 0.1), (990, 1320, 0.1)]),
            "power": make_tone([(500, 900, 0.08), (700, 1200, 0.08), (900, 1600, 0.12)], 0.25),
            "shield": make_tone([(300, 900, 0.15)], 0.3),
            "hiss": make_tone([(0, 0, 0.35)], 0.12, noise=True),
            "boss_hit": make_tone([(150, 40, 0.5)], 0.5),
            "level": make_tone([(523, 523, 0.12), (659, 659, 0.12), (784, 784, 0.12), (1047, 1047, 0.25)]),
            "lose": make_tone([(400, 300, 0.2), (300, 200, 0.2), (200, 100, 0.4)], 0.35),
            "click": make_tone([(900, 700, 0.04)], 0.2),
            "select": make_tone([(700, 1100, 0.08)], 0.25),
            "denied": make_tone([(200, 160, 0.15)], 0.3),
        }
    except Exception:
        return {}


class Sfx:
    """Plays short effects at a shared volume."""

    def __init__(self, volume):
        self.sounds = make_sounds()
        self.set_volume(volume)

    def set_volume(self, v):
        self.volume = v
        for snd in self.sounds.values():
            if snd:
                snd.set_volume(v)

    def play(self, name):
        snd = self.sounds.get(name)
        if snd and self.volume > 0:
            snd.play()


# ---------------------------------------------------------------- music
def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def render_track(melody, bass, step, vol=0.16):
    """melody: one MIDI note per step (0 = rest); bass: one note per two steps."""
    fmt = _format()
    if not fmt:
        return None
    rate, channels = fmt
    n = int(rate * step)
    out = array.array("h")
    for i, m in enumerate(melody):
        b = bass[(i // 2) % len(bass)]
        dm = midi(m) / rate if m else 0
        db = midi(b) / rate if b else 0
        pm = pb = 0.0
        for j in range(n):
            x = j / n
            attack = min(1.0, j / 80)
            v = 0.0
            if dm:
                pm += dm
                fr = pm % 1.0
                v += (4 * abs(fr - 0.5) - 1) * attack * (1 - x) ** 0.6 * 0.7   # triangle wave
            if db:
                pb += db
                v += math.sin(6.2831853 * pb) * attack * (1 - x * 0.5) * 0.5
            s = int(32767 * vol * v)
            for _ in range(channels):
                out.append(s)
    return pygame.mixer.Sound(buffer=out.tobytes())


TRACKS = {
    # calm and happy, C major pentatonic
    "menu": dict(step=0.22, melody=[
        72, 76, 79, 76, 81, 79, 76, 0, 74, 76, 79, 81, 79, 0, 76, 74,
        72, 76, 79, 84, 81, 79, 76, 79, 74, 72, 74, 76, 72, 0, 0, 0],
        bass=[48, 48, 55, 55, 53, 53, 55, 55, 48, 48, 57, 57, 53, 55, 48, 48]),
    # upbeat chase
    "game": dict(step=0.16, melody=[
        79, 0, 79, 81, 79, 76, 72, 0, 74, 76, 79, 76, 74, 72, 74, 0,
        79, 0, 79, 81, 84, 81, 79, 76, 74, 76, 74, 72, 72, 0, 0, 0,
        76, 79, 81, 79, 76, 74, 72, 74, 76, 0, 76, 79, 81, 79, 76, 0,
        84, 0, 81, 0, 79, 76, 74, 76, 72, 74, 76, 74, 72, 0, 0, 0],
        bass=[48, 48, 48, 48, 43, 43, 43, 43, 45, 45, 45, 45, 41, 41, 43, 43]),
    # tense boss fight, A minor
    "boss": dict(step=0.14, melody=[
        69, 0, 69, 72, 69, 0, 67, 69, 72, 74, 72, 69, 67, 0, 64, 0,
        69, 0, 69, 72, 76, 74, 72, 74, 76, 79, 76, 74, 72, 69, 0, 0],
        bass=[45, 45, 45, 45, 41, 41, 43, 43, 45, 45, 45, 45, 41, 43, 40, 40]),
}


class Music:
    """Loops one generated track on a reserved mixer channel."""

    def __init__(self, volume):
        self.volume = volume
        self.cache = {}
        self.current = None
        self.channel = None
        if pygame.mixer.get_init():
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)
            self.channel = pygame.mixer.Channel(0)

    def track(self, name):
        if name not in self.cache:
            try:
                self.cache[name] = render_track(**TRACKS[name])
            except Exception:
                self.cache[name] = None
        return self.cache[name]

    def play(self, name):
        if name == self.current or not self.channel:
            return
        self.current = name
        self.channel.stop()
        snd = self.track(name)
        if snd:
            self.channel.set_volume(self.volume)
            self.channel.play(snd, loops=-1)

    def set_volume(self, v):
        self.volume = v
        if self.channel:
            self.channel.set_volume(v)
