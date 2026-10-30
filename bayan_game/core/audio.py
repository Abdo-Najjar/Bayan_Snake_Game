"""Sound effects (generated in code) and music / ambience loops (WAV files in assets)."""
import array
import math
import os
import random

import pygame

from ..config import ASSETS_DIR

MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
AMBIENCE_DIR = os.path.join(ASSETS_DIR, "ambience")
AMBIENCE_LEVEL = 0.55     # ambience sits under the sound effects


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


# ---------------------------------------------------------------- music and ambience
class Music:
    """Streams one music track (pygame.mixer.music) and loops one ambience sound.

    Tracks are assets/music/<name>.wav (or .ogg/.mp3: drop in a file with the same name).
    Ambience loops are assets/ambience/<terrain>.wav.
    """

    FADE_MS = 700

    def __init__(self, volume, ambience_volume=0.8):
        self.volume = volume
        self.ambience_volume = ambience_volume
        self.current = None
        self.current_ambience = None
        self.enabled = pygame.mixer.get_init() is not None
        self.channel = None
        self._ambience_cache = {}
        if self.enabled:
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)
            self.channel = pygame.mixer.Channel(0)

    @staticmethod
    def find(folder, name):
        for ext in (".ogg", ".mp3", ".wav"):
            path = os.path.join(folder, name + ext)
            if os.path.exists(path):
                return path
        return None

    def play(self, name):
        if name == self.current or not self.enabled:
            return
        self.current = name
        path = self.find(MUSIC_DIR, name) if name else None
        if not path:
            pygame.mixer.music.fadeout(self.FADE_MS)
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(-1, fade_ms=self.FADE_MS)
        except pygame.error:
            pass

    def play_ambience(self, terrain):
        if terrain == self.current_ambience or not self.channel:
            return
        self.current_ambience = terrain
        if not terrain:
            self.channel.fadeout(self.FADE_MS)
            return
        snd = self._ambience_cache.get(terrain)
        if snd is None:
            path = self.find(AMBIENCE_DIR, terrain)
            if not path:
                self.channel.fadeout(self.FADE_MS)
                return
            snd = self._ambience_cache[terrain] = pygame.mixer.Sound(path)
        self.channel.set_volume(self.ambience_volume * AMBIENCE_LEVEL)
        self.channel.play(snd, loops=-1, fade_ms=self.FADE_MS)

    def set_volume(self, v):
        self.volume = v
        if self.enabled:
            pygame.mixer.music.set_volume(v)

    def set_ambience_volume(self, v):
        self.ambience_volume = v
        if self.channel:
            self.channel.set_volume(v * AMBIENCE_LEVEL)
