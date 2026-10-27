#!/usr/bin/env python3
"""Auto-caption your video with styled subtitles, by @kemifrank__

Styles:
  word-pop   – one word at a time, big and centered, each word pops on screen
  highlight  – full sentence with the current word highlighted in color
  karaoke    – sentence fills in word by word, colored left-to-right
  clean      – simple one-line subtitle at the bottom
  bold-stack – two lines stacked, uppercase, punchy

Usage:
  python captions.py input.mp4 output.mp4 --style highlight
  python captions.py input.mp4 output.mp4 --style word-pop --color "#A855F7"
  python captions.py input.mp4 output.mp4 --style karaoke --position top
  python captions.py input.mp4 output.mp4 --srt existing.srt --style clean
"""
import argparse, json, math, os, subprocess, sys, textwrap
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = {k: os.path.join(ROOT, 'fonts', v) for k, v in {
    'bold': 'ArchivoBlack-Regular.ttf',
    'serif': 'InstrumentSerif-Italic.ttf',
    'mono': 'SpaceMono-Bold.ttf',
    'hand': 'PermanentMarker-Regular.ttf',
    'ui': 'Inter.ttf',
    'anton': 'Anton-Regular.ttf',
    'mont': 'Montserrat.ttf',
}.items()}

# ─── color presets ───
COLORS = {
    'purple': (168, 85, 247),
    'yellow': (250, 204, 21),
    'green':  (34, 197, 94),
    'red':    (239, 68, 68),
    'blue':   (59, 130, 246),
    'pink':   (236, 72, 153),
    'orange': (249, 115, 22),
    'white':  (255, 255, 255),
    'cyan':   (6, 182, 212),
}

_fc = {}
def _font(kind, size):
    k = (kind, int(size))
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONT.get(kind, FONT['bold']), max(8, int(size)))
    return _fc[k]


def parse_color(v, default=(168, 85, 247)):
    if v is None:
        return default
    if v.lower() in COLORS:
        return COLORS[v.lower()]
    v = str(v).lstrip('#')
    if len(v) == 6:
        return tuple(int(v[i:i+2], 16) for i in (0, 2, 4))
    return default


# ─── transcription ───
def transcribe(src):
    """Get word-level timestamps using faster-whisper."""
    words = []
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print('Installing the transcriber (one time, about 1 minute)...', flush=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'faster-whisper'], check=True)
        from faster_whisper import WhisperModel

    model = WhisperModel(os.environ.get('WHISPER_MODEL', 'base'), device='cpu', compute_type='int8')
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    segs, info = model.transcribe(audio, word_timestamps=True, vad_filter=True)
    for s in segs:
        for w in (s.words or []):
            words.append({'w': w.word.strip(), 's': round(w.start, 2), 'e': round(w.end, 2)})
    return words


def load_srt(path):
    """Parse an SRT file into word-level entries (one entry per subtitle block)."""
    blocks = []
    with open(path) as f:
        text = f.read()
    for block in text.strip().split('\n\n'):
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        ts = lines[1]
        start_s, end_s = ts.split(' --> ')
        s = _srt_to_sec(start_s.strip())
        e = _srt_to_sec(end_s.strip())
        txt = ' '.join(lines[2:])
        # Split into words, distribute time evenly
        ww = txt.split()
        if not ww:
            continue
        wd = (e - s) / len(ww)
        for i, word in enumerate(ww):
            blocks.append({'w': word, 's': round(s + i * wd, 2), 'e': round(s + (i + 1) * wd, 2)})
    return blocks


def _srt_to_sec(ts):
    h, m, rest = ts.replace(',', '.').split(':')
    return int(h) * 3600 + int(m) * 60 + float(rest)


# ─── sentence grouping ───
def group_sentences(words, max_words=8, max_gap=1.5):
    """Group words into display sentences based on pauses and length."""
    groups = []
    cur = []
    for w in words:
        if cur and (w['s'] - cur[-1]['e'] > max_gap or len(cur) >= max_words):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


# ─── caption renderers ───
def render_word_pop(t, W, H, words, groups, accent, font_kind, position):
    """One big word at a time, centered, with a pop animation."""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    active = None
    for w in words:
        if w['s'] <= t < w['e']:
            active = w
            break
    if not active:
        return im

    progress = (t - active['s']) / max(0.01, active['e'] - active['s'])
    # Pop scale: quick scale up then settle
    if progress < 0.15:
        scale = 0.5 + 3.3 * progress  # 0.5 -> 1.0
    elif progress > 0.85:
        fade = (1.0 - progress) / 0.15
        scale = 1.0
    else:
        scale = 1.0

    size = int(W * 0.12 * min(scale, 1.15))
    f = _font(font_kind, size)
    txt = active['w'].upper()
    bbox = f.getbbox(txt, stroke_width=4)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    y = int(H * 0.42) if position == 'center' else (int(H * 0.15) if position == 'top' else int(H * 0.72))
    x = (W - tw) // 2

    draw = ImageDraw.Draw(im)
    # Shadow
    draw.text((x + 3, y + 3), txt, font=f, fill=(0, 0, 0, 160), stroke_width=4, stroke_fill=(0, 0, 0, 100))
    # Main text
    draw.text((x, y), txt, font=f, fill=accent + (255,), stroke_width=4, stroke_fill=(0, 0, 0, 220))
    return im


def render_highlight(t, W, H, words, groups, accent, font_kind, position):
    """Full sentence with current word highlighted."""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # Find which group is active
    active_group = None
    active_idx = -1
    for group in groups:
        if group[0]['s'] <= t <= group[-1]['e']:
            active_group = group
            for i, w in enumerate(group):
                if w['s'] <= t < w['e']:
                    active_idx = i
            if active_idx < 0:
                # In gap between words in group, highlight the nearest
                for i, w in enumerate(group):
                    if t < w['s']:
                        active_idx = max(0, i - 1)
                        break
                else:
                    active_idx = len(group) - 1
            break

    if not active_group:
        return im

    size = int(W * 0.065)
    f = _font(font_kind, size)
    y = int(H * 0.45) if position == 'center' else (int(H * 0.12) if position == 'top' else int(H * 0.78))

    # Measure the full sentence
    sentence_words = [w['w'] for w in active_group]
    # Try to fit in two lines max
    full = ' '.join(sentence_words)
    if f.getlength(full) > W * 0.85:
        mid = len(sentence_words) // 2
        lines_text = [' '.join(sentence_words[:mid]), ' '.join(sentence_words[mid:])]
        lines_idx = [list(range(mid)), list(range(mid, len(sentence_words)))]
    else:
        lines_text = [full]
        lines_idx = [list(range(len(sentence_words)))]

    draw = ImageDraw.Draw(im)

    # Draw background pill
    line_h = int(size * 1.5)
    total_h = line_h * len(lines_text) + int(size * 0.6)
    max_w = max(int(f.getlength(l)) for l in lines_text) + int(size * 1.2)
    bg_x = (W - max_w) // 2
    bg_y = y - int(size * 0.3)

    # Dark semi-transparent background
    bg = Image.new('RGBA', (max_w, total_h), (0, 0, 0, 0))
    ImageDraw.Draw(bg).rounded_rectangle([0, 0, max_w - 1, total_h - 1], int(size * 0.4), fill=(0, 0, 0, 160))
    im.alpha_composite(bg, (bg_x, bg_y))

    for li, (line, idxs) in enumerate(zip(lines_text, lines_idx)):
        lw = int(f.getlength(line))
        lx = (W - lw) // 2
        ly = y + li * line_h

        # Draw word by word so we can highlight the active one
        cx = lx
        for wi in idxs:
            word = sentence_words[wi]
            ww = int(f.getlength(word + ' '))
            color = accent + (255,) if wi == active_idx else (255, 255, 255, 255)
            draw.text((cx, ly), word, font=f, fill=color, stroke_width=2, stroke_fill=(0, 0, 0, 180))
            cx += ww

    return im


def render_karaoke(t, W, H, words, groups, accent, font_kind, position):
    """Sentence fills in colored, word by word."""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    active_group = None
    for group in groups:
        if group[0]['s'] - 0.1 <= t <= group[-1]['e'] + 0.3:
            active_group = group
            break
    if not active_group:
        return im

    size = int(W * 0.06)
    f = _font(font_kind, size)
    y = int(H * 0.45) if position == 'center' else (int(H * 0.12) if position == 'top' else int(H * 0.78))

    sentence_words = [w['w'] for w in active_group]
    full = ' '.join(sentence_words)
    lw = int(f.getlength(full))
    if lw > W * 0.85:
        size = int(size * W * 0.85 / lw)
        f = _font(font_kind, size)
        lw = int(f.getlength(full))

    lx = (W - lw) // 2

    # Background pill
    draw = ImageDraw.Draw(im)
    ph = int(size * 1.8)
    bg = Image.new('RGBA', (lw + int(size * 1.0), ph), (0, 0, 0, 0))
    ImageDraw.Draw(bg).rounded_rectangle([0, 0, bg.width - 1, bg.height - 1], int(size * 0.35), fill=(0, 0, 0, 160))
    im.alpha_composite(bg, (lx - int(size * 0.5), y - int(size * 0.35)))

    cx = lx
    for i, gw in enumerate(active_group):
        word = gw['w']
        ww = int(f.getlength(word + ' '))
        if t >= gw['s']:
            color = accent + (255,)
        else:
            color = (255, 255, 255, 120)
        draw.text((cx, y), word, font=f, fill=color, stroke_width=2, stroke_fill=(0, 0, 0, 180))
        cx += ww

    return im


def render_clean(t, W, H, words, groups, accent, font_kind, position):
    """Simple clean subtitle at the bottom."""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    active_group = None
    for group in groups:
        if group[0]['s'] - 0.1 <= t <= group[-1]['e'] + 0.2:
            active_group = group
            break
    if not active_group:
        return im

    size = int(W * 0.05)
    f = _font(font_kind, size)
    y = int(H * 0.88) if position == 'bottom' else (int(H * 0.08) if position == 'top' else int(H * 0.45))

    sentence = ' '.join(w['w'] for w in active_group)
    lw = int(f.getlength(sentence))
    if lw > W * 0.9:
        size = int(size * W * 0.9 / lw)
        f = _font(font_kind, size)
        lw = int(f.getlength(sentence))

    x = (W - lw) // 2
    draw = ImageDraw.Draw(im)
    draw.text((x, y), sentence, font=f, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 220))
    return im


def render_bold_stack(t, W, H, words, groups, accent, font_kind, position):
    """Two-line uppercase stacked text, punchy Instagram style."""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    active_group = None
    active_idx = -1
    for group in groups:
        if group[0]['s'] <= t <= group[-1]['e']:
            active_group = group
            for i, w in enumerate(group):
                if w['s'] <= t < w['e']:
                    active_idx = i
            break
    if not active_group:
        return im

    sentence_words = [w['w'].upper() for w in active_group]
    mid = max(1, len(sentence_words) // 2)
    line1 = ' '.join(sentence_words[:mid])
    line2 = ' '.join(sentence_words[mid:]) if mid < len(sentence_words) else ''

    size = int(W * 0.09)
    f = _font('anton', size)

    y = int(H * 0.40) if position == 'center' else (int(H * 0.12) if position == 'top' else int(H * 0.70))

    draw = ImageDraw.Draw(im)
    for i, line in enumerate([line1, line2]):
        if not line:
            continue
        lw = int(f.getlength(line))
        if lw > W * 0.9:
            s2 = int(size * W * 0.9 / lw)
            f2 = _font('anton', s2)
            lw = int(f2.getlength(line))
            lx = (W - lw) // 2
            ly = y + i * int(s2 * 1.2)
            draw.text((lx + 3, ly + 3), line, font=f2, fill=(0, 0, 0, 180))
            draw.text((lx, ly), line, font=f2, fill=accent + (255,) if i == 0 else (255, 255, 255, 255),
                       stroke_width=3, stroke_fill=(0, 0, 0, 200))
        else:
            lx = (W - lw) // 2
            ly = y + i * int(size * 1.2)
            draw.text((lx + 3, ly + 3), line, font=f, fill=(0, 0, 0, 180))
            draw.text((lx, ly), line, font=f, fill=accent + (255,) if i == 0 else (255, 255, 255, 255),
                       stroke_width=3, stroke_fill=(0, 0, 0, 200))
    return im


# ─── editorial: the house style (by @kemifrank__) ───
# lowercase white sans, the key word in a pale-yellow italic serif on its own line,
# sitting above your head so your head passes in front of the words.
STOP = set("""a an the and or but so to of in on at for with from by as is are was were be been being it its it's this that
these those i i'm im you you're your we we're our they their he she his her him them me my mine yours ours
do does did done have has had will would can could should just like really very not no yes if then than when what how
which who why where there here about into out up down over under again also only even more most some any all each
let's lets gonna wanna get got go going um uh okay ok oh yeah""".split())

EDITORIAL_YELLOW = (248, 232, 142)
SANS_WGHT = 690

def _sans(size):
    k = ('sans', int(size))
    if k not in _fc:
        f = ImageFont.truetype(FONT['ui'], max(8, int(size)))
        try: f.set_variation_by_axes([32, SANS_WGHT])
        except Exception:
            try: f.set_variation_by_axes([SANS_WGHT])
            except Exception: pass
        _fc[k] = f
    return _fc[k]

def _clean(w):
    return w.strip().strip('.,!?;:"“”').lower()

WEAK = set("""here's there's that's what's having using show works work click copy send spend want make take help
tell talk talking first next time thing things stuff way need know think say said look see come give gives use""".split())

def pick_emphasis(group, manual=None, prev=False):
    """(first, last) word indexes to set in yellow serif, or None.
    Used sparingly, like the reference reels: the punchline, a name, a number.
    manual: set of lowercase words the user wants emphasised (always win)."""
    def span(i):
        # a number takes its unit with it: "60 seconds", "1 million"
        if any(ch.isdigit() for ch in group[i]['w']) and i + 1 < len(group) and _clean(group[i + 1]['w']) not in STOP:
            return (i, i + 1)
        return (i, i)
    if manual:
        hits = [i for i, w in enumerate(group) if _clean(w['w']) in manual]
        if hits: return span(hits[-1])
    best, score = None, 0.0
    for i, w in enumerate(group):
        raw = w['w'].strip(); c = _clean(raw)
        if not c or c in STOP or c in WEAK: continue
        sc = len(c) * (0.6 if len(c) >= 5 else 0.3)
        if any(ch.isdigit() for ch in c): sc += 6
        if raw[:1].isupper() and i > 0: sc += 3          # names, brands
        if raw[-1:] in '.!?': sc += 1.5                   # punchline at the end of a thought
        if i == len(group) - 1: sc += 0.8
        if sc > score: best, score = i, sc
    need = 6.5 if prev else 4.8                            # don't stack serif words back to back
    return span(best) if best is not None and score >= need else None

def editorial_groups(words, max_words=5, gap=0.35):
    groups, cur = [], []
    for w in words:
        if cur and (w['s'] - cur[-1]['e'] > gap or len(cur) >= max_words or cur[-1]['w'].strip()[-1:] in '.,!?;:'):
            groups.append(cur); cur = []
        cur.append(w)
    if cur: groups.append(cur)
    return groups

def _wrap(words, f, maxw, space):
    lines, cur, cw = [], [], 0
    for w in words:
        ww = f.getlength(w)
        if cur and cw + space + ww > maxw: lines.append(cur); cur, cw = [], 0
        cw = cw + (space if cur else 0) + ww; cur.append(w)
    if cur: lines.append(cur)
    return lines

def _tracked_width(s, f, tr): return sum(f.getlength(ch) for ch in s) + tr * max(0, len(s) - 1)

def editorial_layout(group, emph, W, size=None, H=None):
    """Lines of (text, kind, word_indexes). kind: 'sans' or 'serif'."""
    words = [w['w'].strip().strip('“”"') for w in group]
    words = [w.rstrip(',;:') for w in words]
    land = H is not None and W > H        # 16:9 YouTube: lower-third band, narrower lines
    MW = W * (0.7 if land else 0.88)
    S = size or int(H * 0.078 if land else W * 0.118)
    while True:
        fs, fz = _sans(S), _font('serif', S * 1.5)
        tr = -S * 0.035; sp = fs.getlength(' ') * 0.85
        if land:
            # one low line (two at most), the yellow serif word sits inline
            fz = _font('serif', S * 1.35)
            items = []
            for i, wd in enumerate(words):
                ser = emph is not None and emph[0] <= i <= emph[1]
                tk = wd.lower().rstrip('.!?') if ser else wd.lower()
                items.append((i, tk, fz.getlength(tk) if ser else _tracked_width(tk, fs, tr), 'serif' if ser else 'sans'))
            width = lambda its: sum(it[2] for it in its) + sp * max(0, len(its) - 1)
            if width(items) <= MW or len(items) == 1: return [('mixed', items)], S, sp, tr
            best = min(range(1, len(items)), key=lambda c: max(width(items[:c]), width(items[c:])))
            if max(width(items[:best]), width(items[best:])) <= MW or S < 40:
                return [('mixed', items[:best]), ('mixed', items[best:])], S, sp, tr
            S = int(S * 0.9); continue
        blocks = []
        if emph is None: blocks.append(('sans', list(range(len(words)))))
        else:
            e0, e1 = emph
            if e0 > 0: blocks.append(('sans', list(range(e0))))
            blocks.append(('serif', list(range(e0, e1 + 1))))
            if e1 < len(words) - 1: blocks.append(('sans', list(range(e1 + 1, len(words)))))
        lines, ok = [], True
        for kind, idx in blocks:
            f = fs if kind == 'sans' else fz
            toks = [words[i].lower() if kind == 'sans' else words[i].lower().rstrip('.!?') for i in idx]
            items = [(j, tk, _tracked_width(tk, f, tr) if kind == 'sans' else f.getlength(tk)) for j, tk in zip(idx, toks)]
            if any(ww > MW * 1.02 for _, _, ww in items): ok = False
            width = lambda its: sum(ww for _, _, ww in its) + sp * max(0, len(its) - 1)
            if width(items) <= MW or len(items) == 1:
                lines.append((kind, items))
            else:
                # balanced two-line split: no lonely last word hiding behind your head
                best = min(range(1, len(items)), key=lambda c: max(width(items[:c]), width(items[c:])))
                if max(width(items[:best]), width(items[best:])) > MW: ok = False
                lines.append((kind, items[:best])); lines.append((kind, items[best:]))
        if ok or S < 50: return lines, S, sp, tr
        S = int(S * 0.88)

def render_editorial_layer(t, W, H, group, emph, anchor_y, size=None, color=EDITORIAL_YELLOW):
    """RGBA text layer. anchor_y = y of the bottom of the text block."""
    lines, S, sp, tr = editorial_layout(group, emph, W, size, H)
    fs, fz = _sans(S), _font('serif', S * 1.5)
    heights = [S * 1.02 if k == 'sans' else (S * 1.42 if k == 'mixed' else S * 1.32) for k, _ in lines]
    fzm = _font('serif', S * 1.35)
    y = max(H * 0.04, anchor_y - sum(heights))   # never off the top of the frame
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for (kind, toks), lh in zip(lines, heights):
        f = fs if kind == 'sans' else fz
        tot = sum(it[2] for it in toks) + sp * (len(toks) - 1)
        x = (W - tot) / 2
        for it in toks:
            j, tk, ww = it[:3]
            w = group[j]
            k = min(1.0, max(0.0, (t - w['s'] + 0.04) / 0.14))      # each word arrives as it's spoken
            if k > 0:
                a = int(255 * k); dy = (1 - k) * S * 0.18
                if kind == 'mixed':
                    base = y + S * 1.1 + dy
                    if it[3] == 'serif': d.text((x, base), tk, font=fzm, fill=color + (a,), anchor='ls')
                    else:
                        cx = x
                        for ch in tk:
                            d.text((cx, base), ch, font=fs, fill=(255, 255, 255, a), anchor='ls'); cx += fs.getlength(ch) + tr
                elif kind == 'sans':
                    cx = x
                    for ch in tk:
                        d.text((cx, y + dy), ch, font=f, fill=(255, 255, 255, a)); cx += f.getlength(ch) + tr
                else:
                    d.text((x, y + dy - S * 0.08), tk, font=f, fill=color + (a,))
            x += ww + sp
        y += lh
    # soft shadow for legibility on any background
    al = np.asarray(im)[..., 3]
    sh = Image.fromarray((al * (0.8 if W > H else 0.55)).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(4, S * 0.09)))
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    out.paste((0, 0, 0, 255), (0, int(S * 0.04)), sh)
    out.alpha_composite(im)
    return out

# effects that draw above your head (captions drop to the bottom while they play)
# and effects that live under your chin (captions keep their spot above your head)
_BELOW_FX = {'checklist', 'liquid-glass-graph'}

def caption_zones(fx_plan_path, bottom_at):
    zones = []   # (start, end, 'bottom'|'head')
    if fx_plan_path:
        plan = json.load(open(fx_plan_path))
        for e in plan.get('effects', []):
            name = e['fx']
            if name in _BELOW_FX and e.get('look') != 'bento': continue
            if name == 'apple-toggles' and e.get('pos') == 'below': continue
            zones.append((float(e['start']) - 0.1, float(e['end']) + 0.1, 'bottom'))
    for rng in (bottom_at or '').split(','):
        if '-' in rng:
            a_, b_ = rng.split('-'); zones.append((float(a_), float(b_), 'bottom'))
    return zones

def run_editorial(a, words):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fx import Tracker   # same face + person tracking the effects use
    src = a.input
    fps, dur, sw, sh = probe(src)
    if sw <= sh: W = a.width; H = int(round(a.width * sh / sw / 2)) * 2
    else: H = a.width; W = int(round(a.width * sw / sh / 2)) * 2
    manual = set(x.strip().lower() for x in (a.emphasis or '').split(',') if x.strip())
    color = parse_color(a.color, EDITORIAL_YELLOW) if a.color != 'purple' else EDITORIAL_YELLOW
    groups = editorial_groups(words, max_words=min(a.max_words, 5))
    emph = []
    for g in groups: emph.append(pick_emphasis(g, manual, prev=bool(emph and emph[-1])))
    zones = caption_zones(a.fx_plan, a.bottom_at)
    aw = 360; ah = int(round(aw * H / W / 2)) * 2
    tr = Tracker(aw, ah); face_s = None; locked = {}

    enc = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-y',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
        '-i', src, '-map', '0:v', '-map', '1:a:0?',
        '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', a.output
    ], stdin=subprocess.PIPE)
    print('Rendering editorial captions...', flush=True)
    for i, frame in enumerate(read_frames(src, W, H, fps)):
        t = i / fps
        small = cv2.resize(frame, (aw, ah), interpolation=cv2.INTER_AREA)
        m, face = tr(small, int(t * 1000))
        if face is not None:
            fx_, fy_, fw_ = face[0] * W / aw, face[1] * H / ah, face[2] * W / aw
            face_s = (fx_, fy_, fw_) if face_s is None else tuple(0.85 * p + 0.15 * q for p, q in zip(face_s, (fx_, fy_, fw_)))
        gi = None
        for k, g in enumerate(groups):
            nxt = groups[k + 1][0]['s'] if k + 1 < len(groups) else g[-1]['e'] + 0.6
            if g[0]['s'] - 0.05 <= t < min(nxt, g[-1]['e'] + 0.6): gi = k; break
        out = frame
        if W > H:   # soft dark fade along the bottom so captions read on any outfit
            if 'fade' not in locked:
                g = np.clip((np.arange(H, dtype=np.float32) / H - 0.68) / 0.32, 0, 1) ** 1.3 * 0.65
                locked['fade'] = (1 - g)[:, None, None]
            out = frame = (frame.astype(np.float32) * locked['fade']).astype(np.uint8)
        if gi is not None:
            zone = 'head'
            for z0, z1, zn in zones:
                if z0 <= t <= z1: zone = zn
            if a.position in ('bottom', 'top', 'center'): zone = a.position
            if W > H and zone == 'head': zone = 'bottom'   # landscape: no room above the head
            key = (gi, zone)
            if key not in locked:      # text stays put for the whole phrase
                if zone == 'head' and face_s is not None:
                    fx_, fy_, fw_ = face_s
                    locked[key] = min(H * 0.6, max(H * 0.17, fy_ - fw_ * 0.98))
                elif zone == 'head': locked[key] = H * 0.36
                elif zone == 'top': locked[key] = H * 0.26
                elif zone == 'center': locked[key] = H * 0.5
                else: locked[key] = H * (0.94 if W > H else 0.9)
            lay = render_editorial_layer(t, W, H, groups[gi], emph[gi], locked[key], color=color)
            ov = np.asarray(lay, np.float32) / 255; al = ov[..., 3:4]
            if zone == 'head' and not a.no_behind:
                mk = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255
                al = al * (1 - mk[..., None])
            base = frame.astype(np.float32) / 255
            out = (np.clip(base * (1 - al) + ov[..., :3] * al, 0, 1) * 255 + 0.5).astype(np.uint8)
        enc.stdin.write(out.tobytes())
        if i % int(fps * 5) == 0: print(f'  {t:5.1f}s / {dur:.1f}s', flush=True)
    enc.stdin.close(); enc.wait()
    print(f'Done: {a.output}')


STYLES = {
    'editorial': None,
    'word-pop': render_word_pop,
    'highlight': render_highlight,
    'karaoke': render_karaoke,
    'clean': render_clean,
    'bold-stack': render_bold_stack,
}


# ─── video I/O ───
def probe(src):
    j = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate,width,height,nb_frames',
        '-show_entries', 'format=duration', '-of', 'json', src]))
    s = j['streams'][0]; fmt = j['format']
    num, den = s['r_frame_rate'].split('/'); fps = round(int(num) / int(den), 2)
    dur = float(fmt['duration'])
    return fps, dur, int(s['width']), int(s['height'])


def read_frames(src, w, h, fps):
    cmd = ['ffmpeg', '-v', 'error', '-i', src, '-vf', f'scale={w}:{h}:flags=bicubic', '-r', str(fps),
           '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    sz = w * h * 3
    while True:
        d = p.stdout.read(sz)
        if len(d) < sz:
            break
        yield np.frombuffer(d, np.uint8).reshape(h, w, 3)
    p.stdout.close()
    p.wait()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input', help='Input video')
    ap.add_argument('output', help='Output video (or .srt to export subtitles only)')
    ap.add_argument('--style', default='editorial', choices=list(STYLES.keys()),
                    help='Caption style (default: editorial, the house style)')
    ap.add_argument('--color', default='purple', help='Accent color: name or hex (default: purple)')
    ap.add_argument('--font', default='bold', help='Font: bold, anton, mono, hand, ui (default: bold)')
    ap.add_argument('--position', default=None, choices=['head', 'top', 'center', 'bottom'],
                    help='Where to place captions (editorial default: above your head; others: bottom)')
    ap.add_argument('--words', help='Use a words JSON from words.py (fix any misheard words in it first)')
    ap.add_argument('--fix', help='Fix misheard words, e.g. "ChargeGPT=ChatGPT,serve=save"')
    ap.add_argument('--emphasis', help='editorial: words to set in yellow serif, e.g. "claude,edited"')
    ap.add_argument('--fx-plan', help='editorial: the fx.py plan, so captions move out of the way of effects')
    ap.add_argument('--bottom-at', help='editorial: extra time ranges for bottom captions, e.g. "19-21.6,39.6-43"')
    ap.add_argument('--no-behind', action='store_true', help='editorial: keep words in front of your head')
    ap.add_argument('--srt', help='Use an existing SRT file instead of transcribing')
    ap.add_argument('--max-words', type=int, default=6, help='Max words per caption group (default: 6)')
    ap.add_argument('--export-srt', action='store_true', help='Also save an SRT file alongside the video')
    ap.add_argument('--width', type=int, default=1080, help='Output width (default: 1080)')
    a = ap.parse_args()

    src = a.input
    accent = parse_color(a.color)
    render_fn = STYLES[a.style]

    # Get words
    if a.words:
        words = json.load(open(a.words))
    elif a.srt:
        print(f'Loading subtitles from {a.srt}...', flush=True)
        words = load_srt(a.srt)
    else:
        print('Transcribing audio (this takes a moment)...', flush=True)
        words = transcribe(src)

    if not words:
        print('No speech detected in the video.')
        return

    if a.fix:
        for pair in a.fix.split(','):
            if '=' in pair:
                old, new = pair.split('=', 1)
                for w in words: w['w'] = w['w'].replace(old.strip(), new.strip())
    print(f'Found {len(words)} words.', flush=True)
    if a.style == 'editorial':
        if a.position is None: a.position = 'head'
        if a.output.lower().endswith('.srt'):
            _export_srt(a.output, editorial_groups(words)); print(f'Saved {a.output}'); return
        return run_editorial(a, words)
    if a.position in (None, 'head'): a.position = 'bottom'
    groups = group_sentences(words, max_words=a.max_words)

    # Export SRT only?
    if a.output.lower().endswith('.srt'):
        _export_srt(a.output, groups)
        print(f'Saved {a.output}')
        return

    # Export SRT alongside video if requested
    if a.export_srt:
        srt_path = os.path.splitext(a.output)[0] + '.srt'
        _export_srt(srt_path, groups)
        print(f'Saved {srt_path}')

    # Probe video
    fps, dur, sw, sh = probe(src)
    if sw <= sh:
        W = a.width; H = int(round(a.width * sh / sw / 2)) * 2
    else:
        H = a.width; W = int(round(a.width * sw / sh / 2)) * 2

    # Encode
    enc = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-y',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
        '-i', src, '-map', '0:v', '-map', '1:a:0?',
        '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', a.output
    ], stdin=subprocess.PIPE)

    print('Rendering captions...', flush=True)
    total = int(dur * fps)
    for i, frame in enumerate(read_frames(src, W, H, fps)):
        t = i / fps
        # Render caption overlay
        overlay = render_fn(t, W, H, words, groups, accent, a.font, a.position)
        # Composite onto frame
        ov = np.asarray(overlay, dtype=np.float32) / 255.0
        alpha = ov[..., 3:4]
        base = frame.astype(np.float32) / 255.0
        blended = base * (1 - alpha) + ov[..., :3] * alpha
        out = (np.clip(blended, 0, 1) * 255 + 0.5).astype(np.uint8)
        enc.stdin.write(out.tobytes())
        if i % int(fps * 5) == 0:
            print(f'  {t:5.1f}s / {dur:.1f}s', flush=True)

    enc.stdin.close()
    enc.wait()
    print(f'Done: {a.output}')


def _export_srt(path, groups):
    with open(path, 'w') as f:
        for i, group in enumerate(groups):
            s = group[0]['s']
            e = group[-1]['e']
            text = ' '.join(w['w'] for w in group)
            f.write(f"{i + 1}\n{_sec_to_srt(s)} --> {_sec_to_srt(e)}\n{text}\n\n")


def _sec_to_srt(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')


if __name__ == '__main__':
    main()
