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
    segs, info = model.transcribe(src, word_timestamps=True, vad_filter=True)
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


STYLES = {
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
    ap.add_argument('--style', default='highlight', choices=list(STYLES.keys()),
                    help='Caption style (default: highlight)')
    ap.add_argument('--color', default='purple', help='Accent color: name or hex (default: purple)')
    ap.add_argument('--font', default='bold', help='Font: bold, anton, mono, hand, ui (default: bold)')
    ap.add_argument('--position', default='bottom', choices=['top', 'center', 'bottom'],
                    help='Where to place captions (default: bottom)')
    ap.add_argument('--srt', help='Use an existing SRT file instead of transcribing')
    ap.add_argument('--max-words', type=int, default=6, help='Max words per caption group (default: 6)')
    ap.add_argument('--export-srt', action='store_true', help='Also save an SRT file alongside the video')
    ap.add_argument('--width', type=int, default=1080, help='Output width (default: 1080)')
    a = ap.parse_args()

    src = a.input
    accent = parse_color(a.color)
    render_fn = STYLES[a.style]

    # Get words
    if a.srt:
        print(f'Loading subtitles from {a.srt}...', flush=True)
        words = load_srt(a.srt)
    else:
        print('Transcribing audio (this takes a moment)...', flush=True)
        words = transcribe(src)

    if not words:
        print('No speech detected in the video.')
        return

    print(f'Found {len(words)} words.', flush=True)
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
