#!/usr/bin/env python3
"""Sound effects for your edits, by @kemifrank__

Every sound is synthesized in code (no downloads, no licences to worry about).
They're mixed under your voice, so your audio stays the star.

Commands:
  list      – show every sound and what it's for
  export    – save every sound as a .wav (to use in CapCut too)
  auto      – read an effects plan and add the matching sound to every effect
  add       – add sounds at exact times from a JSON plan

Usage:
  python sfx.py list
  python sfx.py export assets/sfx
  python sfx.py auto video.mp4 out.mp4 --fx-plan plan.json
  python sfx.py auto video.mp4 out.mp4 --fx-plan plan.json --extra extra.json --level 0.8
  python sfx.py add video.mp4 out.mp4 --plan sfx.json

SFX plan JSON (for `add`, or `--extra` with `auto`):
  [
    {"sfx": "whoosh", "at": 19.0},
    {"sfx": "pop", "at": 22.4, "vol": 0.6},
    {"sfx": "typing", "at": 30.0, "dur": 1.5}
  ]
"""
import argparse, json, os, subprocess, sys, wave
import numpy as np
from scipy import signal

SR = 48000
RNG = np.random.default_rng(7)


# ───────── building blocks ─────────
def T(dur): return np.arange(int(dur * SR)) / SR

def noise(dur, seed=None):
    r = np.random.default_rng(seed) if seed is not None else RNG
    return r.standard_normal(int(dur * SR))

def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, min(hi, SR / 2 - 100)], 'bandpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)

def lp(x, f, order=2):
    sos = signal.butter(order, min(f, SR / 2 - 100), 'lowpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)

def hp(x, f, order=2):
    sos = signal.butter(order, f, 'highpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)

def env(n, attack, decay_tau, sustain=0.0):
    """Exponential envelope: linear attack (s), then exp decay with time-constant decay_tau (s)."""
    t = np.arange(n) / SR; a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * (sustain + (1 - sustain) * np.exp(-np.maximum(0, t - attack) / decay_tau))

def bell(n, peak=0.5, sharp=2.0):
    """Smooth rise and fall, peaking at `peak` (0 to 1) of the length."""
    x = np.linspace(0, 1, n)
    y = np.where(x < peak, (x / peak), (1 - x) / (1 - peak))
    return np.clip(y, 0, 1) ** sharp

def chirp(dur, f0, f1, curve='exp'):
    t = T(dur)
    f = f0 * (f1 / f0) ** (t / dur) if curve == 'exp' else f0 + (f1 - f0) * t / dur
    return np.sin(2 * np.pi * np.cumsum(f) / SR)

def swept_noise(dur, centers, width=0.6, seed=None):
    """Noise whose band centre follows `centers` (array of Hz over time) — the core of every whoosh."""
    x = noise(dur, seed)
    f, tt, Z = signal.stft(x, SR, nperseg=1024)
    c = np.interp(tt, np.linspace(0, dur, len(centers)), centers)
    lf = np.log(np.maximum(f, 20))[:, None]; lc = np.log(c)[None, :]
    Z *= np.exp(-((lf - lc) ** 2) / (2 * width ** 2))
    _, y = signal.istft(Z, SR, nperseg=1024)
    y = y[:len(x)]
    return np.pad(y, (0, len(x) - len(y)))

def stereo(x, pan=0.0):
    """pan: -1 left .. +1 right, scalar or per-sample array."""
    p = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    return np.stack([x * np.cos(p), x * np.sin(p)], 1)

def reverb(st, decay=1.0, mix=0.25, tone=5000):
    n = int(decay * SR); t = np.arange(n) / SR
    out = st.copy()
    tail = np.zeros((len(st) + n - 1, 2))
    for ch in range(2):
        ir = lp(noise(decay, 11 + ch), tone) * np.exp(-t * 6.9 / decay)
        ir /= np.sqrt((ir ** 2).sum()) + 1e-9
        tail[:, ch] = signal.fftconvolve(st[:, ch], ir)
    out = np.pad(out, ((0, n - 1), (0, 0)))
    return out * (1 - mix * 0.5) + tail * mix

def cat(*parts):
    return np.concatenate(parts)

def place(buf, x, at):
    i = int(at * SR)
    if i >= len(buf): return buf
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += x[:m]
    return buf

def blank(dur): return np.zeros((int(dur * SR), 2))

def soft_tail(st, ms=15):
    n = min(len(st), int(ms * SR / 1000)); st[-n:] *= np.linspace(1, 0, n)[:, None]; return st


# ───────── the sounds ─────────
def s_whoosh(dur=0.55, lo=280, hi=2600, seed=1, pan=True):
    n = int(dur * SR); e = bell(n, 0.62, 1.6)
    centers = np.concatenate([np.geomspace(lo, hi, 60), np.geomspace(hi, lo * 1.6, 40)])
    x = swept_noise(dur, centers, 0.55, seed) * e
    x += 0.25 * lp(noise(dur, seed + 5), 400) * e  # body
    st = stereo(x, np.linspace(-0.6, 0.6, n) if pan else 0)
    return reverb(st, 0.6, 0.18)

def s_swoosh(): return s_whoosh(0.3, 700, 5200, 2)
def s_whoosh_long(): return s_whoosh(1.1, 180, 1800, 3)

def s_swipe():
    """Quick UI slide."""
    return s_whoosh(0.18, 1500, 7000, 4, pan=False) * 0.8

def s_pop(f0=1100, f1=330, dur=0.11):
    n = int(dur * SR)
    x = fade_out(chirp(dur, f0, f1) * env(n, 0.002, 0.03), 0.03)
    x += 0.15 * hp(noise(dur, 21), 3000) * env(n, 0.0005, 0.004)
    return reverb(stereo(x), 0.35, 0.12)

def s_tick(): return s_pop(2200, 1100, 0.06) * 0.8

def s_bubble():
    """A softer, rounder pop for things appearing."""
    dur = 0.16; n = int(dur * SR)
    x = chirp(dur, 380, 900) * env(n, 0.004, 0.045)
    return reverb(stereo(x), 0.3, 0.12)

def s_click():
    dur = 0.05; n = int(dur * SR)
    x = hp(noise(dur, 31), 2500) * env(n, 0.0003, 0.0025) * 0.9
    x += np.sin(2 * np.pi * 3200 * T(dur)) * env(n, 0.0005, 0.006) * 0.4
    x += np.sin(2 * np.pi * 180 * T(dur)) * env(n, 0.001, 0.01) * 0.5
    return reverb(stereo(x), 0.25, 0.08)

def fade_out(x, sec):
    n = min(len(x), int(sec * SR)); x = x.copy(); x[-n:] *= np.linspace(1, 0, n) ** 2; return x

def _bell_tone(f0, dur=2.4, bright=1.0, seed=0):
    t = T(dur); n = len(t); x = np.zeros(n)
    for k, (ratio, amp, tau) in enumerate([(1, 1, 0.55), (2.76, 0.45 * bright, 0.22), (5.40, 0.25 * bright, 0.12),
                                           (8.93, 0.12 * bright, 0.07), (2.0, 0.2, 0.4)]):
        x += amp * np.sin(2 * np.pi * f0 * ratio * t + k) * np.exp(-t / tau)
    return fade_out(x * np.clip(t / 0.003, 0, 1), 0.6)

def s_ding():
    return reverb(stereo(_bell_tone(1318.5)), 1.2, 0.3)

def s_chime():
    """Two-note notification."""
    a = _bell_tone(1318.5, 1.6) * 0.8; b = _bell_tone(1975.5, 2.0) * 0.7
    x = np.zeros(int(2.2 * SR)); x[:len(a)] += a; i = int(0.12 * SR); x[i:i + len(b)] += b[:len(x) - i]
    return reverb(stereo(x), 1.0, 0.28)

def s_cash():
    """Ka-ching: a bright bell plus coin jingle."""
    x = np.zeros(int(2.2 * SR))
    x[:int(0.04 * SR)] += hp(noise(0.04, 41), 2000) * env(int(0.04 * SR), 0.0005, 0.006) * 0.6
    b = _bell_tone(1760, 2.0, 1.4); i = int(0.06 * SR); x[i:i + len(b)] += b[:len(x) - i]
    r = np.random.default_rng(42)
    for _ in range(26):
        s = int(r.uniform(0.05, 0.5) * SR); f = r.uniform(4500, 9500); d = 0.08
        g = np.sin(2 * np.pi * f * T(d)) * np.exp(-T(d) / 0.02) * r.uniform(0.1, 0.25)
        x[s:s + len(g)] += g
    return reverb(stereo(x), 0.9, 0.25)

def s_impact():
    """Deep cinematic hit for big words landing."""
    dur = 1.1; n = int(dur * SR); t = T(dur)
    f = 40 + 90 * np.exp(-t / 0.06)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
    hit = lp(noise(dur, 51), 1200) * env(n, 0.001, 0.035) * 0.9
    snap = hp(noise(dur, 52), 3000) * env(n, 0.0005, 0.008) * 0.3
    x = fade_out(np.tanh(1.6 * (sub + hit + snap)), 0.4)
    return reverb(stereo(x), 1.4, 0.3, 3000)

def s_thud():
    """Lighter hit: cards landing, headlines dropping."""
    dur = 0.45; n = int(dur * SR); t = T(dur)
    f = 70 + 120 * np.exp(-t / 0.03)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12) + lp(noise(dur, 61), 900) * env(n, 0.001, 0.02) * 0.5
    return reverb(stereo(fade_out(np.tanh(1.3 * x), 0.15)), 0.6, 0.2, 3000)

def s_stamp():
    dur = 0.5; n = int(dur * SR)
    slap = bp(noise(dur, 71), 600, 5000) * env(n, 0.0008, 0.018)
    x = np.tanh(1.5 * (slap + 0.7 * s_thud()[:n, 0]))
    return reverb(stereo(x), 0.5, 0.18)

def s_riser(dur=1.6):
    n = int(dur * SR); t = T(dur)
    rise = (t / dur) ** 2.2
    x = swept_noise(dur, np.geomspace(250, 7000, 100), 0.5, 81) * rise
    x += 0.35 * chirp(dur, 180, 1400) * rise
    st = stereo(x); st = soft_tail(st, 25)
    return reverb(st, 0.8, 0.2)

def s_shimmer(dur=1.2):
    x = np.zeros(int((dur + 0.4) * SR)); r = np.random.default_rng(91)
    st = np.zeros((len(x), 2))
    for _ in range(int(38 * dur)):
        s = int(r.beta(2, 2.5) * dur * SR); f = r.uniform(2600, 9000); d = 0.25
        g = np.sin(2 * np.pi * f * T(d)) * np.exp(-T(d) / r.uniform(0.04, 0.12)) * r.uniform(0.15, 0.4) * np.clip(T(d) / 0.004, 0, 1)
        st[s:s + len(g)] += stereo(g, r.uniform(-0.8, 0.8))[:len(st) - s]
    return reverb(st, 1.3, 0.4, 8000)

def s_typing(dur=1.2):
    r = np.random.default_rng(101); st = blank(dur + 0.2); t = 0.0
    while t < dur:
        d = 0.03; n = int(d * SR)
        k = bp(noise(d, int(t * 1000)), 1800, 6000) * env(n, 0.0004, 0.003) * r.uniform(0.6, 1.0)
        k += np.sin(2 * np.pi * r.uniform(150, 230) * T(d)) * env(n, 0.001, 0.008) * 0.5
        place(st, stereo(k, r.uniform(-0.3, 0.3)), t)
        t += r.uniform(0.065, 0.14)
    return reverb(st, 0.25, 0.1)

def s_shutter():
    st = blank(0.25)
    for at, g in ((0.0, 1.0), (0.07, 0.8)):
        d = 0.04; n = int(d * SR)
        k = bp(noise(d, int(at * 99) + 3), 800, 7000) * env(n, 0.0005, 0.006) * g
        k += np.sin(2 * np.pi * 420 * T(d)) * env(n, 0.001, 0.008) * 0.3 * g
        place(st, stereo(k), at)
    return reverb(st, 0.3, 0.1)

def s_glitch(dur=0.45):
    r = np.random.default_rng(111); x = np.zeros(int(dur * SR)); i = 0
    while i < len(x):
        n = int(r.uniform(0.012, 0.05) * SR); kind = r.integers(3)
        if kind == 0: seg = signal.square(2 * np.pi * r.uniform(90, 1800) * T(n / SR)) * 0.5
        elif kind == 1: seg = np.round(noise(n / SR, int(i)) * 3) / 3 * 0.5
        else: seg = np.zeros(n)
        x[i:i + n] = seg[:len(x) - i]; i += n
    x = np.round(x * 8) / 8  # bit-crush
    return stereo(lp(x, 7000) * 0.7, np.sign(np.sin(np.arange(len(x)) / 900)) * 0.4)

def s_clunk():
    """Light switch / lights going off."""
    dur = 0.6; n = int(dur * SR); t = T(dur)
    x = hp(noise(dur, 121), 1500) * env(n, 0.0004, 0.004) * 0.8
    x += np.sin(2 * np.pi * (85 + 40 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.09) * 0.9
    x = fade_out(x, 0.1)
    return reverb(stereo(np.tanh(1.4 * x)), 1.0, 0.3, 2500)

def s_buzz(dur=0.8):
    """Neon / LED sign flickering on."""
    t = T(dur); hum = sum(np.sin(2 * np.pi * 100 * h * t) / h for h in (1, 2, 3, 5, 7)) * 0.35
    hum = np.tanh(2 * hum)
    gate = np.ones_like(t); r = np.random.default_rng(131)
    for _ in range(5):
        s = r.uniform(0, 0.3); gate[(t > s) & (t < s + r.uniform(0.02, 0.06))] = 0.1
    e = np.clip(t / 0.01, 0, 1) * np.clip((dur - t) / 0.25, 0, 1)
    return stereo(hum * gate * e * 0.8)

def s_scribble(dur=0.8):
    t = T(dur); r = np.random.default_rng(141)
    am = np.clip(np.sin(2 * np.pi * r.uniform(5, 8) * t + np.cumsum(r.normal(0, 0.02, len(t)))), 0, 1) ** 0.7
    x = bp(noise(dur, 142), 1200, 5000) * am * np.clip((dur - t) / 0.08, 0, 1) * 0.7
    return stereo(x)

def s_scratch():
    """Record scratch: for freeze frames and 'wait, what?' moments."""
    dur = 0.45; t = T(dur)
    speed = np.concatenate([np.linspace(1, -1.4, len(t) // 2), np.linspace(-1.4, 0.8, len(t) - len(t) // 2)])
    phase = np.cumsum(np.abs(speed)) / SR
    x = np.sin(2 * np.pi * 220 * phase * 8) * 0.4 + bp(noise(dur, 151), 400, 4000) * np.abs(speed) * 0.6
    return reverb(stereo(x * np.clip((dur - t) / 0.05, 0, 1)), 0.3, 0.1)

def s_sub(dur=2.4):
    """Low cinematic bass bed: sits under a hook and drops out on the cut."""
    t = T(dur)
    x = np.sin(2 * np.pi * 49 * t) + 0.35 * np.sin(2 * np.pi * 98 * t + 0.5) + 0.12 * np.sin(2 * np.pi * 147 * t)
    x *= 1 + 0.08 * np.sin(2 * np.pi * 0.9 * t)
    e = np.clip(t / 0.12, 0, 1) * np.clip((dur - t) / 0.08, 0, 1)
    x = np.tanh(1.3 * x * e) + 0.04 * lp(noise(dur, 161), 300) * e
    return stereo(x)

def s_heartbeat():
    st = blank(0.9)
    for at, g in ((0, 1), (0.22, 0.7)):
        d = 0.18; t = T(d)
        k = np.sin(2 * np.pi * (55 + 30 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.05) * g
        place(st, stereo(k), at)
    return st


SOUNDS = {
    'whoosh':      (s_whoosh,      'Medium whoosh: camera moves, things flying in', 1.0),
    'swoosh':      (s_swoosh,      'Fast, bright swoosh: cuts, headlines sliding in', 0.9),
    'whoosh-long': (s_whoosh_long, 'Slow whoosh: big transitions, B-roll cutaways', 1.0),
    'swipe':       (s_swipe,       'Quick UI slide: cards and panels', 0.7),
    'pop':         (s_pop,         'Classic pop: text or stickers appearing', 0.8),
    'bubble':      (s_bubble,      'Soft round pop: gentle appearances', 0.8),
    'tick':        (s_tick,        'Small tick: checklist items, counters', 0.7),
    'click':       (s_click,       'UI tap: buttons, toggles, follow', 0.8),
    'ding':        (s_ding,        'Bell ding: done, correct, highlight', 0.6),
    'chime':       (s_chime,       'Two-note notification: comments, messages', 0.6),
    'cash':        (s_cash,        'Ka-ching: money, results, numbers', 0.6),
    'impact':      (s_impact,      'Deep cinematic hit: big words landing, hooks', 0.75),
    'thud':        (s_thud,        'Lighter hit: cards and headlines landing', 0.9),
    'stamp':       (s_stamp,       'Stamp slam', 1.0),
    'riser':       (s_riser,       'Build-up: growth graphs, before a reveal', 0.7),
    'shimmer':     (s_shimmer,     'Sparkles: glow-ups, reveals, magic moments', 0.6),
    'typing':      (s_typing,      'Keyboard typing (use "dur")', 0.6),
    'shutter':     (s_shutter,     'Camera shutter: snapshots, covers, lock-on', 0.8),
    'glitch':      (s_glitch,      'Digital glitch', 0.6),
    'clunk':       (s_clunk,       'Light switch: lights going off', 0.9),
    'buzz':        (s_buzz,        'Neon/LED sign flickering on', 0.5),
    'scribble':    (s_scribble,    'Marker drawing', 0.6),
    'scratch':     (s_scratch,     'Record scratch: freeze frames, "wait, what?"', 0.7),
    'heartbeat':   (s_heartbeat,   'Heartbeat thump: suspense', 0.9),
    'sub':         (s_sub,         'Low bass bed under a hook (use "dur")', 0.55),
}
DUR_SOUNDS = {'typing', 'riser', 'shimmer', 'glitch', 'buzz', 'scribble', 'sub'}

PACKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'sfx', 'packs')

# Designed sounds (CC0, from the uisfx project) for every synthesized cue: softer and more polished.
# 'studio' = tactile, warm restraint; 'cinematic' = deeper, for transitions and big moments.
DESIGNED = {
    'whoosh': 'cinematic/swipe', 'swoosh': 'studio/swipe', 'whoosh-long': 'cinematic/expand', 'swipe': 'studio/swipe',
    'pop': 'studio/press', 'bubble': 'soft/press', 'tick': 'studio/check', 'click': 'studio/select',
    'ding': 'studio/success', 'chime': 'studio/notification', 'cash': 'studio/purchase', 'impact': 'cinematic/snap',
    'thud': 'cinematic/press', 'stamp': 'cinematic/snap', 'riser': 'studio/progress-step', 'shimmer': 'studio/reward',
    'shutter': 'studio/snap', 'glitch': 'studio/error', 'clunk': 'studio/toggle-off', 'buzz': 'studio/toggle-on',
    'scratch': 'studio/back', 'heartbeat': 'cinematic/press', 'sub': None,
    # 'typing' and 'scribble' stay synthesized
}

def is_pack(name): return '/' in name

def load_pack(name):
    path = os.path.join(PACKS, name + '.mp3')
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True)
    if not p.stdout: raise FileNotFoundError(path)
    return np.frombuffer(p.stdout, np.float32).reshape(-1, 2).astype(np.float64)

_cache = {}
def get(name, dur=None):
    key = (name, round(dur, 2) if dur else None)
    if key not in _cache and is_pack(name):
        st = load_pack(name)
        a = np.abs(st).max(1); act = st[a > a.max() * 0.05]
        rms = np.sqrt((act ** 2).mean()) if len(act) else 1
        _cache[key] = st / (rms + 1e-9) * 0.1 * 0.8
    if key not in _cache:
        fn, _, gain = SOUNDS[name]
        st = fn(dur) if (dur and name in DUR_SOUNDS) else fn()
        st = np.asarray(st, np.float64)
        # loudness-match every sound (RMS over its active part), then apply its own gain
        a = np.abs(st).max(1); act = st[a > a.max() * 0.05]
        rms = np.sqrt((act ** 2).mean()) if len(act) else 1
        _cache[key] = st / (rms + 1e-9) * 0.1 * gain
    return _cache[key]


# ───────── effects plan → sounds ─────────
def auto_events(plan):
    """Pick sounds for every effect in an fx.py plan, timed to its animation."""
    ev = []
    def add(name, at, vol=1.0, dur=None): ev.append({'sfx': name, 'at': round(at, 3), 'vol': vol, **({'dur': dur} if dur else {})})
    for e in plan.get('effects', plan if isinstance(plan, list) else []):
        fx = e['fx']; s = float(e['start']); d = float(e['end']) - s
        n_items = len(str(e.get('text', '')).split('|')) if e.get('text') else 0
        if fx in ('backdrop-word', 'pastel-word'):
            add('whoosh', s - 0.1, 0.6); add('impact', s + 0.28, 0.9)
        elif fx in ('red-collage',):
            add('impact', s + 0.1); [add('thud', s + 0.5 + 0.25 * i, 0.6) for i in range(3)]
        elif fx == 'spotlight':
            add('clunk', s + 0.05)
            if e.get('text') or e.get('look') == 'sparkle': add('shimmer', s + 0.2, 0.6)
        elif fx == 'led-sign':
            add('clunk', s + 0.05, 0.8); add('buzz', s + 0.3, 0.5, min(1.5, d - 0.3))
        elif fx in ('lean-in', 'headline-box'):
            add('swoosh', s - 0.05, 0.8)
            if fx == 'headline-box': add('pop', s + 0.25, 0.5)
        elif fx == 'locked-on':
            add('swoosh', s - 0.05, 0.6); add('shutter', s + 0.35, 0.8)
        elif fx == 'slow-push':
            add('riser', s, 0.35, min(d, 3.0))
        elif fx == 'checklist':
            add('swipe', s, 0.7); n = max(1, n_items or 5); span = max(0.4, d - 0.55)
            for i in range(n): add('tick', s + 0.3 + span * (i + 1) / n, 0.8)
        elif fx == 'todo':
            add('bubble', s, 0.7); n = max(1, n_items or 3)
            ts = [float(x) for x in str(e['ticks']).split('|')] if e.get('ticks') else [s + d * (i + 1) / (n + 1) for i in range(n)]
            for t in ts: add('tick', t, 0.8); add('scribble', t, 0.25, 0.2)
        elif fx == 'apple-toggles':
            add('swipe', s, 0.6); n = max(1, n_items or 3)
            ts = [s + float(x) for x in str(e['ticks']).split('|')] if e.get('ticks') else [s + 0.45 + 0.34 * i for i in range(n)]
            for t in ts: add('click', t, 0.9)
        elif fx == 'comment-box':
            word = e.get('text', 'EFFECTS'); t_post = 0.3 + 0.06 * len(word) + 0.1
            add('swipe', s, 0.6); add('typing', s + 0.3, 0.7, 0.06 * len(word)); add('click', s + t_post, 0.8)
            add('pop', s + t_post + 0.25, 0.6); add('chime', s + t_post + 0.4, 0.6)
        elif fx == 'tap':
            at = float(e['at']) if 'at' in e else s + d * 0.45
            add('bubble', s, 0.6); add('click', at, 1.0)
        elif fx == 'reject-stamp':
            add('swoosh', s - 0.05, 0.5); add('stamp', s + 0.15)
        elif fx == 'countdown-flip':
            n0 = int(e.get('from', 3)); seg = d / n0
            for i in range(n0): add('tick', s + i * seg, 0.9)
            add('ding', s + d - 0.05, 0.6)
        elif fx in ('the-bill', 'shortcut-rain'):
            add('typing', s + 0.1, 0.6, min(d - 0.2, 2.0))
        elif fx == 'scribble':
            add('scribble', s + 0.1, 0.7, min(d - 0.1, 1.5))
        elif fx == 'pause-point':
            add('scratch', s, 0.8); add('scribble', s + 0.3, 0.5, 0.6)
        elif fx == 'uninstall':
            add('glitch', s + 0.1, 0.7, min(0.8, d))
        elif fx == 'rabbit-hole':
            add('whoosh-long', s, 0.8)
        elif fx == 'liquid-glass-graph':
            add('swipe', s, 0.6); add('riser', s + 0.1, 0.5, min(1.6, d - 0.4)); add('ding', s + min(1.75, d - 0.3), 0.5)
        elif fx in ('lineup', 'glass-widgets', 'check-pills', 'headline-wall', 'tier-list'):
            n = max(3, min(6, n_items or 5))
            for i in range(n): add('bubble', s + 0.035 * i * (4 if fx != 'lineup' else 1) + 0.05, 0.45)
            if fx == 'tier-list': add('ding', s + d * 0.6, 0.6)
        elif fx in ('noise', 'orbit', 'carousel-spin', 'profile-wall', 'phone-fan'):
            add('whoosh', s, 0.7)
            for i in range(4): add('pop', s + 0.25 + 0.25 * i, 0.35)
        elif fx in ('split-headline', 'broll-split', 'reel-frame', 'swipe'):
            add('whoosh', s - 0.05, 0.7); add('thud', s + 0.35, 0.5)
        elif fx in ('cover-star', 'timeline'):
            add('shutter', s + 0.05, 0.8); add('whoosh', s, 0.4)
        elif fx == 'dot-reveal':
            add('shimmer', s, 0.6, min(1.5, d))
        elif fx == 'match-cut':
            for i in range(8): add('click', s + 0.12 * i, 0.5)
            add('thud', s + 1.0, 0.6)
        elif fx == 'moody':
            pass
        else:
            add('swoosh', s, 0.6)
    return ev


# ───────── mixing ─────────
def load_audio(src):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-vn', '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'],
                       capture_output=True)
    a = np.frombuffer(p.stdout, np.float32).reshape(-1, 2).astype(np.float64) if p.stdout else None
    return a

def duration(src):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src]))

def mix(src, dst, events, level=0.35, style='designed'):
    dur = duration(src)
    voice = load_audio(src)
    n = int(dur * SR) + SR
    if voice is None: voice = np.zeros((n, 2))
    # level relative to the voice: SFX sit under it, never over it
    loud = np.abs(voice).max(1); spoken = voice[loud > loud.max() * 0.1] if loud.max() > 0 else voice
    vrms = np.sqrt((spoken ** 2).mean()) if len(spoken) else 0.1
    bus = np.zeros((max(n, len(voice)), 2))
    for ev in sorted(events, key=lambda e: e['at']):
        name = ev['sfx']
        if style == 'designed' and name in DESIGNED:
            name = DESIGNED[name]
            if name is None: continue
        if not is_pack(name) and name not in SOUNDS: print(f"  skip unknown sound '{name}'"); continue
        st = get(name, ev.get('dur'))
        place(bus, st * float(ev.get('vol', 1.0)), max(0.0, float(ev['at'])))
    bus *= level * (vrms / 0.1)
    out = np.zeros_like(bus); out[:len(voice)] = voice; out += bus
    # gentle limiter so nothing clips
    pk = np.abs(out).max()
    if pk > 0.95: out = np.tanh(out / pk * 1.4) / np.tanh(1.4) * 0.95
    out = out[:int(dur * SR)]
    wav = os.path.splitext(dst)[0] + '.__mix.wav'
    write_wav(wav, out)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], check=True)
    os.remove(wav)
    print(f'Added {len(events)} sound(s). Done: {dst}')

def write_wav(path, st):
    st = np.clip(st, -1, 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype('<i2').tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')
    sub.add_parser('list', help='Show every sound')
    ex = sub.add_parser('export', help='Save every sound as .wav'); ex.add_argument('folder')
    au = sub.add_parser('auto', help='Add matching sounds to every effect in an fx plan')
    au.add_argument('input'); au.add_argument('output')
    au.add_argument('--fx-plan', required=True, help='The effects plan JSON used with fx.py')
    au.add_argument('--extra', help='Extra sounds JSON (B-roll cuts, zooms, hooks)')
    au.add_argument('--style', default='designed', choices=['designed', 'synth'], help='designed = polished recorded-style pack sounds (default); synth = the original synthesized set')
    au.add_argument('--level', type=float, default=0.35, help='SFX loudness vs your voice (default 0.35; 0.5 = punchier, 0.2 = subtle)')
    au.add_argument('--save-plan', help='Also write the full sound plan to this JSON, so you can tweak it')
    ad = sub.add_parser('add', help='Add sounds at exact times')
    ad.add_argument('input'); ad.add_argument('output'); ad.add_argument('--plan', required=True)
    ad.add_argument('--style', default='designed', choices=['designed', 'synth'], help='designed = polished recorded-style pack sounds (default); synth = the original synthesized set')
    ad.add_argument('--level', type=float, default=0.35)
    a = ap.parse_args()

    if a.cmd == 'list':
        print('Sound effects:\n')
        for k, (_, desc, _) in SOUNDS.items(): print(f'  {k:12s} {desc}' + (f'   (designed: {DESIGNED[k]})' if DESIGNED.get(k) else ''))
        print('\nDesigned packs (use any directly, e.g. "studio/send"):', ', '.join(sorted(d for d in os.listdir(PACKS) if os.path.isdir(os.path.join(PACKS, d)))) if os.path.isdir(PACKS) else 'none')
    elif a.cmd == 'export':
        os.makedirs(a.folder, exist_ok=True)
        for k in SOUNDS:
            st = get(k); st = st / (np.abs(st).max() + 1e-9) * 0.89
            write_wav(os.path.join(a.folder, f'{k}.wav'), st)
        print(f'Saved {len(SOUNDS)} sounds to {a.folder}')
    elif a.cmd == 'auto':
        ev = auto_events(json.load(open(a.fx_plan)))
        if a.extra: ev += json.load(open(a.extra))
        if a.save_plan: json.dump(ev, open(a.save_plan, 'w'), indent=1)
        mix(a.input, a.output, ev, a.level, a.style)
    elif a.cmd == 'add':
        mix(a.input, a.output, json.load(open(a.plan)), a.level, a.style)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
