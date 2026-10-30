"""Composes and renders the game's music and ambience loops into WAV files.

Every level gets its own track (key, scale, tempo, instruments and drum style),
and every terrain gets a looping ambience (birds, wind, crickets, lava...).
The melodies are generated from a fixed seed, so rebuilding gives the same result.

Output: bayan_game/assets/music/*.wav and bayan_game/assets/ambience/*.wav
"""
import os
import random
import wave

import numpy as np
from scipy.signal import butter, lfilter

SR = 22050
TAU = 2 * np.pi

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "hijaz": [0, 1, 4, 5, 7, 8, 10],          # Arabic maqam Hijaz flavour
    "harmonic": [0, 2, 3, 5, 7, 8, 11],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
}

DRUMS = {
    # 16 steps per bar. k=kick s=snare h=hat D=doum T=tak b=block c=chime
    "soft": dict(k="x.......x.......", h="..x...x...x...x."),
    "pop": dict(k="x.......x.x.....", s="....x.......x...", h="x.x.x.x.x.x.x.x."),
    "doumbek": dict(D="x.....x.x.......", T="...x......x..x..", h="..x...x.......x."),
    "doumbek2": dict(D="x..x..x.x.......", T="...x.x....x.x.x.", k="x.......x......."),
    "chimes": dict(k="x.......x.......", c="x...x...x...x...", h="......x.......x."),
    "forest": dict(k="x.......x.......", b="..x..x....x..x..", h="x.x.x.x.x.x.x.x."),
    "drive": dict(k="x...x...x...x...", s="....x.......x...", h="xxxxxxxxxxxxxxxx"),
    "boss": dict(k="x..xx..x x..xx.x.".replace(" ", "")[:16], s="....x.......x...", h="x.xxx.xxx.xxx.xx"),
    "march": dict(k="x...x...x...x...", s="....x..x....x.xx", h="x.x.x.x.x.x.x.x."),
}

# One entry per music file. prog = chord roots as scale degrees (one per bar).
TRACKS = {
    "menu": dict(bpm=96, root=60, scale="major", prog=[0, 5, 3, 4, 0, 5, 3, 4], lead="bell",
                 bass="soft", drums="soft", seed=11, density=0.5),
    "tutorial": dict(bpm=100, root=65, scale="major", prog=[0, 3, 4, 0, 5, 3, 4, 0], lead="bell",
                     bass="soft", drums="soft", seed=5, density=0.45),
    "level_1": dict(bpm=112, root=67, scale="major", prog=[0, 4, 5, 3, 0, 4, 3, 4], lead="pluck",
                    bass="bounce", drums="pop", seed=1, density=0.6),
    "level_2": dict(bpm=122, root=62, scale="major", prog=[0, 3, 4, 4, 5, 3, 1, 4], lead="square",
                    bass="bounce", drums="pop", seed=2, density=0.7),
    "level_3": dict(bpm=100, root=62, scale="hijaz", prog=[0, 0, 6, 0, 3, 3, 6, 0], lead="pluck",
                    bass="drone", drums="doumbek", seed=3, density=0.65),
    "level_4": dict(bpm=114, root=64, scale="hijaz", prog=[0, 6, 5, 0, 3, 6, 5, 0], lead="reed",
                    bass="drone", drums="doumbek2", seed=4, density=0.75),
    "level_5": dict(bpm=92, root=65, scale="lydian", prog=[0, 1, 0, 4, 0, 1, 5, 4], lead="bell",
                    bass="soft", drums="chimes", seed=6, density=0.55),
    "level_6": dict(bpm=106, root=60, scale="minor", prog=[0, 5, 2, 6, 0, 5, 3, 4], lead="bell",
                    bass="walk", drums="chimes", seed=7, density=0.65),
    "level_7": dict(bpm=100, root=64, scale="dorian", prog=[0, 3, 0, 3, 6, 3, 4, 0], lead="flute",
                    bass="walk", drums="forest", seed=8, density=0.6),
    "level_8": dict(bpm=120, root=59, scale="minor", prog=[0, 5, 6, 4, 0, 5, 3, 4], lead="flute",
                    bass="eighths", drums="drive", seed=9, density=0.75),
    "level_9": dict(bpm=140, root=57, scale="phrygian", prog=[0, 0, 1, 0, 5, 6, 1, 0], lead="saw",
                    bass="pulse", drums="boss", seed=10, density=0.8),
    "victory": dict(bpm=118, root=60, scale="major", prog=[0, 3, 4, 0, 5, 3, 4, 0], lead="square",
                    bass="bounce", drums="march", seed=12, density=0.7),
}


def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def lowpass(x, hz, order=2):
    b, a = butter(order, hz / (SR / 2), "low")
    return lfilter(b, a, x)


def highpass(x, hz, order=2):
    b, a = butter(order, hz / (SR / 2), "high")
    return lfilter(b, a, x)


def bandpass(x, lo, hi, order=2):
    b, a = butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    return lfilter(b, a, x)


def env(n, attack=0.01, release=0.08, decay=None):
    """Attack/release envelope; with decay, the note fades exponentially (plucked sound)."""
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(attack, 1e-4))
    if decay:
        e *= np.exp(-t / decay)
    rel = int(min(n, release * SR))
    if rel > 0:
        e[-rel:] *= np.linspace(1, 0, rel)
    return e


# ================================================================ instruments
def additive(f, t, harmonics):
    out = np.zeros_like(t)
    for k, amp in harmonics:
        if f * k < SR / 2.2:
            out += amp * np.sin(TAU * f * k * t)
    return out


def instrument(name, f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if name == "bell":                     # FM bell
        index = 2.2 * np.exp(-t * 3.5)
        y = np.sin(TAU * f * t + index * np.sin(TAU * f * 3.5 * t)) * env(n, 0.003, 0.05, decay=0.6)
    elif name == "pluck":                  # oud / guitar-like
        harm = [(k, 1 / k) for k in range(1, 10)]
        y = np.zeros(n)
        for k, amp in harm:
            if f * k < SR / 2.2:
                y += amp * np.sin(TAU * f * k * t) * np.exp(-t * (2.5 + k * 1.6))
        y *= env(n, 0.002, 0.04)
    elif name == "square":                 # soft chiptune
        y = additive(f, t, [(k, 1 / k) for k in (1, 3, 5, 7, 9)]) * 0.8 * env(n, 0.005, 0.05, decay=0.5)
    elif name == "saw":
        y = additive(f, t, [(k, 1 / k) for k in range(1, 12)]) * 0.7 * env(n, 0.005, 0.05, decay=0.4)
    elif name == "reed":                   # nasal, ney/mizmar-like
        vib = 1 + 0.006 * np.sin(TAU * 5.5 * t) * np.minimum(1, t * 3)
        y = additive(f, t * vib, [(1, 1), (2, 0.6), (3, 0.5), (4, 0.25), (5, 0.2)]) * 0.6 * env(n, 0.04, 0.08)
    elif name == "flute":
        vib = 1 + 0.005 * np.sin(TAU * 5 * t) * np.minimum(1, t * 2.5)
        breath = lowpass(np.random.default_rng(int(f)).standard_normal(n), 3000) * 0.05
        y = (additive(f, t * vib, [(1, 1), (2, 0.25), (3, 0.08)]) + breath) * env(n, 0.05, 0.08)
    else:                                  # triangle-ish pad
        y = additive(f, t, [(1, 1), (3, 1 / 9), (5, 1 / 25)]) * env(n, 0.08, 0.2)
    return y


def drum(kind, rng):
    if kind == "k":                        # kick
        n = int(0.25 * SR)
        t = np.arange(n) / SR
        f = 45 + 90 * np.exp(-t * 30)
        return np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t * 14) * 0.9
    if kind == "s":                        # snare
        n = int(0.18 * SR)
        t = np.arange(n) / SR
        noise = highpass(rng.standard_normal(n), 1200) * np.exp(-t * 22)
        return (noise * 0.45 + np.sin(TAU * 185 * t) * np.exp(-t * 30) * 0.4)
    if kind == "h":                        # hi-hat
        n = int(0.05 * SR)
        t = np.arange(n) / SR
        return highpass(rng.standard_normal(n), 6000) * np.exp(-t * 80) * 0.25
    if kind == "D":                        # doumbek "doum" (low, round)
        n = int(0.3 * SR)
        t = np.arange(n) / SR
        f = 90 + 60 * np.exp(-t * 25)
        return np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t * 9) * 0.8
    if kind == "T":                        # doumbek "tak" (sharp rim)
        n = int(0.08 * SR)
        t = np.arange(n) / SR
        return (bandpass(rng.standard_normal(n), 1500, 5000) * 0.6 + np.sin(TAU * 620 * t) * 0.3) * np.exp(-t * 55)
    if kind == "b":                        # wood block
        n = int(0.08 * SR)
        t = np.arange(n) / SR
        return np.sin(TAU * 820 * t) * np.exp(-t * 50) * 0.4
    if kind == "c":                        # small chime
        n = int(0.5 * SR)
        t = np.arange(n) / SR
        return np.sin(TAU * 2637 * t + 1.5 * np.sin(TAU * 2637 * 1.4 * t) * np.exp(-t * 8)) * np.exp(-t * 7) * 0.12
    return np.zeros(1)


# ================================================================ composition
def scale_note(root, scale, degree):
    steps = SCALES[scale]
    octave, idx = divmod(degree, len(steps))
    return root + 12 * octave + steps[idx]


RHYTHMS = [
    [0, 4, 8, 12], [0, 2, 4, 8, 12], [0, 3, 6, 8, 12], [0, 4, 6, 8, 10, 12],
    [0, 2, 4, 6, 8, 12, 14], [0, 6, 8, 12], [0, 4, 8, 10, 12, 14],
]


def compose_melody(spec):
    """Returns (step, length_in_steps, scale_degree) notes over 8 bars of 16 steps.
    Form: A A' B A'' so the tune feels like a song, not random notes."""
    rnd = random.Random(spec["seed"])
    dense = spec["density"]
    pool = [r for r in RHYTHMS if len(r) <= 4 + dense * 5]

    def phrase(bar_chords, start_degree):
        notes, deg = [], start_degree
        for b, chord in enumerate(bar_chords):
            rhythm = rnd.choice(pool)
            for i, step in enumerate(rhythm):
                nxt = rhythm[i + 1] if i + 1 < len(rhythm) else 16
                if step in (0, 8):         # strong beats land on chord tones
                    options = [chord + o for o in (0, 2, 4, 7)]
                    deg = min(options, key=lambda d: abs(d - deg) + rnd.random() * 1.5)
                else:                      # weak beats move by step
                    deg += rnd.choice([-2, -1, -1, 1, 1, 2])
                deg = max(-1, min(10, deg))
                notes.append((b * 16 + step, nxt - step, deg))
        return notes

    prog = spec["prog"]
    a = phrase(prog[0:2], 4)
    a2 = [(s, ln, d) for s, ln, d in a]
    if a2:
        a2[-1] = (a2[-1][0], a2[-1][1], prog[3] + 2)
    b = phrase(prog[4:6], 7)
    end = phrase(prog[6:8], 4)
    if end:
        end[-1] = (end[-1][0], 16 - end[-1][0] % 16, 7)      # end on the tonic
    out = []
    for offset, part in ((0, a), (32, a2), (64, b), (96, end)):
        for s, ln, d in part:
            out.append((s + offset, ln, d))
    return out


def bass_line(spec):
    """(step, length, midi) for 8 bars."""
    out = []
    root = spec["root"] - 24
    for bar, chord in enumerate(spec["prog"]):
        r = scale_note(root, spec["scale"], chord)
        fifth = scale_note(root, spec["scale"], chord + 4)
        third = scale_note(root, spec["scale"], chord + 2)
        b0 = bar * 16
        style = spec["bass"]
        if style == "soft":
            out += [(b0, 14, r)]
        elif style == "drone":
            out += [(b0, 16, scale_note(root, spec["scale"], 0)), (b0 + 8, 8, r)]
        elif style == "bounce":
            out += [(b0, 4, r), (b0 + 4, 4, fifth), (b0 + 8, 4, r), (b0 + 12, 4, fifth)]
        elif style == "walk":
            out += [(b0, 4, r), (b0 + 4, 4, third), (b0 + 8, 4, fifth), (b0 + 12, 4, third)]
        elif style == "eighths":
            out += [(b0 + i, 2, r if i % 4 else r + 12 * (i == 8)) for i in range(0, 16, 2)]
        elif style == "pulse":
            out += [(b0 + i, 1, r) for i in range(16)]
    return out


def place(buf, start, y, gain):
    end = min(len(buf), start + len(y))
    buf[start:end] += y[:end - start] * gain


def render_track(spec):
    step = 60 / spec["bpm"] / 4
    bars = len(spec["prog"])
    loop_len = int(bars * 16 * step * SR)
    buf = np.zeros(loop_len + 3 * SR)
    rng = np.random.default_rng(spec["seed"])

    # pads: soft sustained chords
    pad = np.zeros_like(buf)
    for bar, chord in enumerate(spec["prog"]):
        for o in (0, 2, 4):
            f = midi_hz(scale_note(spec["root"] - 12, spec["scale"], chord + o))
            place(pad, int(bar * 16 * step * SR), instrument("pad", f, 16 * step), 0.09)
    buf += lowpass(pad, 1800)

    # bass
    bass = np.zeros_like(buf)
    for s, ln, note in bass_line(spec):
        y = instrument("pad", midi_hz(note), ln * step * 0.95)
        place(bass, int(s * step * SR), y, 0.35)
    buf += lowpass(bass, 700)

    # lead melody (plus a quiet octave echo for sparkle)
    lead = np.zeros_like(buf)
    for s, ln, deg in compose_melody(spec):
        f = midi_hz(scale_note(spec["root"], spec["scale"], deg))
        y = instrument(spec["lead"], f, max(ln, 2) * step * 1.1)
        place(lead, int(s * step * SR), y, 0.32)
    delay = int(step * 3 * SR)
    echo = np.zeros_like(lead)
    echo[delay:] = lead[:-delay] * 0.28
    buf += lead + lowpass(echo, 2500)

    # drums
    pattern = DRUMS[spec["drums"]]
    for bar in range(bars):
        for kind, steps in pattern.items():
            for i, ch in enumerate(steps):
                if ch == "x":
                    swing = step * 0.12 if i % 2 else 0      # slight groove
                    place(buf, int((bar * 16 + i) * step * SR + swing * SR), drum(kind, rng),
                          0.55 if kind in "kD" else 0.5)

    # wrap the tail (echo, long notes) back to the start so the loop is seamless
    tail = buf[loop_len:]
    buf = buf[:loop_len].copy()
    buf[:len(tail)] += tail[:loop_len]
    return master(buf)


def master(x, peak=0.85):
    x = x - np.mean(x)
    x = np.tanh(x / (np.max(np.abs(x)) + 1e-9) * 1.4)        # gentle limiter
    return x / (np.max(np.abs(x)) + 1e-9) * peak


# ================================================================ ambience
def ambience(terrain, seconds=14, seed=0):
    n = int(seconds * SR)
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SR
    out = np.zeros(n + SR)

    def slow_lfo(rate, phase=0.0):
        return 0.5 + 0.5 * np.sin(TAU * rate * t + phase)

    def breeze(lo, hi, gain):
        noise = bandpass(rng.standard_normal(n), lo, hi)
        swell = 0.4 + 0.6 * slow_lfo(1 / seconds) * slow_lfo(2 / seconds, 1.3)  # loops cleanly
        return noise * swell * gain

    if terrain == "grass":
        out[:n] += breeze(200, 900, 0.25)
        for _ in range(9):                 # bird calls: a few quick rising chirps
            start = rng.uniform(0, seconds - 1)
            base = rng.uniform(2400, 3600)
            for c in range(rng.integers(2, 5)):
                dur = rng.uniform(0.05, 0.09)
                m = int(dur * SR)
                tt = np.arange(m) / SR
                f = base + 1400 * tt / dur
                chirp = np.sin(TAU * np.cumsum(f) / SR) * np.sin(np.pi * tt / dur) * 0.35
                place(out, int((start + c * 0.12) * SR), chirp, 1)
    elif terrain == "desert":
        out[:n] += breeze(180, 1100, 0.8)
        out[:n] += breeze(1400, 2600, 0.12) * slow_lfo(3 / seconds)
    elif terrain == "snow":
        out[:n] += breeze(300, 900, 0.55)
        for _ in range(10):                # sparkly ice tinkles
            start = rng.uniform(0, seconds - 1)
            f = rng.uniform(2200, 4200)
            m = int(0.6 * SR)
            tt = np.arange(m) / SR
            place(out, int(start * SR), np.sin(TAU * f * tt) * np.exp(-tt * 9) * 0.12, 1)
    elif terrain == "forest":
        out[:n] += breeze(150, 600, 0.18)
        for voice in range(3):             # crickets: buzzing pulses at ~4.5 kHz
            f = 4300 + voice * 260
            rate = 0.55 + voice * 0.13
            gate = (np.sin(TAU * 32 * t) > 0.3) * (np.sin(TAU * rate * t + voice) > 0.2)
            out[:n] += np.sin(TAU * f * t) * lowpass(gate.astype(float), 200) * 0.07
        for _ in range(2):                 # an owl: hoo-hoo
            start = rng.uniform(1, seconds - 2)
            for h in range(2):
                m = int(0.35 * SR)
                tt = np.arange(m) / SR
                hoot = np.sin(TAU * (410 - 40 * tt) * tt) * np.sin(np.pi * tt / 0.35) * 0.18
                place(out, int((start + h * 0.45) * SR), hoot, 1)
    elif terrain == "lair":
        out[:n] += lowpass(rng.standard_normal(n), 120) * 2.0              # deep rumble
        for _ in range(40):                # lava bubbles
            start = rng.uniform(0, seconds - 0.2)
            m = int(0.07 * SR)
            tt = np.arange(m) / SR
            f = rng.uniform(140, 380) * (1 + 2 * tt)
            place(out, int(start * SR), np.sin(TAU * np.cumsum(f) / SR) * np.sin(np.pi * tt / 0.07) * 0.2, 1)
        for _ in range(60):                # crackles
            start = rng.uniform(0, seconds)
            m = int(0.004 * SR)
            place(out, int(start * SR), highpass(rng.standard_normal(m), 3000) * 0.25, 1)
    tail = out[n:]
    out = out[:n].copy()
    out[:len(tail)] += tail
    return master(out, 0.6)


# ================================================================ files
def write_wav(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = x.copy()
    edge = 96                              # ~4 ms fade at both ends: no click when the loop restarts
    x[:edge] *= np.linspace(0, 1, edge)
    x[-edge:] *= np.linspace(1, 0, edge)
    data = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def build_all(assets_dir):
    for name, spec in TRACKS.items():
        write_wav(os.path.join(assets_dir, "music", f"{name}.wav"), render_track(spec))
    for i, terrain in enumerate(("grass", "desert", "snow", "forest", "lair")):
        write_wav(os.path.join(assets_dir, "ambience", f"{terrain}.wav"), ambience(terrain, seed=i + 1))
