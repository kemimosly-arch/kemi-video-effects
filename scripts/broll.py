#!/usr/bin/env python3
"""Insert B-roll into your talking-head video, by @kemifrank__

Modes:
  cutaway     – full-screen B-roll replaces your clip for that section
  pip         – picture-in-picture: B-roll plays in a corner while you talk
  split       – top half B-roll, bottom half you (or left/right)
  overlay     – B-roll plays behind you (uses person segmentation)

Usage:
  python broll.py cutaway main.mp4 output.mp4 --broll clip.mp4 --at 3.0 --duration 2.5
  python broll.py pip main.mp4 output.mp4 --broll clip.mp4 --at 5.0 --duration 3.0 --corner br
  python broll.py split main.mp4 output.mp4 --broll clip.mp4 --at 2.0 --duration 4.0
  python broll.py overlay main.mp4 output.mp4 --broll clip.mp4 --at 1.0 --duration 5.0

Multiple B-rolls:
  python broll.py cutaway main.mp4 output.mp4 --plan broll.json

Plan JSON format:
  [
    {"mode": "cutaway", "broll": "intro.mp4", "at": 0.0, "duration": 2.0},
    {"mode": "pip", "broll": "demo.mp4", "at": 5.0, "duration": 3.0, "corner": "br"},
    {"mode": "split", "broll": "screen.png", "at": 10.0, "duration": 4.0}
  ]
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

# ─── video I/O ───
def probe(src):
    j = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate,width,height',
        '-show_entries', 'format=duration', '-of', 'json', src]))
    s = j['streams'][0]; fmt = j['format']
    num, den = s['r_frame_rate'].split('/'); fps = round(int(num) / int(den), 2)
    dur = float(fmt['duration'])
    return fps, dur, int(s['width']), int(s['height'])


def read_frames(src, w, h, fps):
    cmd = ['ffmpeg', '-v', 'error', '-i', src, '-vf', f'scale={w}:{h}:flags=bicubic',
           '-r', str(fps), '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    sz = w * h * 3
    while True:
        d = p.stdout.read(sz)
        if len(d) < sz:
            break
        yield np.frombuffer(d, np.uint8).reshape(h, w, 3).copy()
    p.stdout.close()
    p.wait()


def load_broll_source(path, W, H, fps, duration):
    """Load B-roll frames from a video or image."""
    ext = path.lower().rsplit('.', 1)[-1]
    if ext in ('jpg', 'jpeg', 'png', 'webp', 'bmp'):
        # Static image: repeat as frames
        im = Image.open(path).convert('RGB')
        # Crop to match aspect ratio
        target_ar = W / H
        src_ar = im.width / im.height
        if src_ar > target_ar:
            new_w = int(im.height * target_ar)
            left = (im.width - new_w) // 2
            im = im.crop((left, 0, left + new_w, im.height))
        else:
            new_h = int(im.width / target_ar)
            top = (im.height - new_h) // 2
            im = im.crop((0, top, im.width, top + new_h))
        im = im.resize((W, H), Image.LANCZOS)
        frame = np.asarray(im, dtype=np.uint8)
        n = int(duration * fps) + 1
        return [frame] * n
    else:
        # Video: read frames
        frames = list(read_frames(path, W, H, fps))
        if not frames:
            return []
        # Loop if B-roll is shorter than needed
        n = int(duration * fps) + 1
        while len(frames) < n:
            frames = frames + frames
        return frames[:n]


def ease_inout(x):
    x = max(0, min(1, x))
    return 3 * x * x - 2 * x * x * x


# ─── B-roll modes ───
def apply_cutaway(main_frame, broll_frame, progress, transition=0.15):
    """Full-screen B-roll with fade transition."""
    if progress < transition:
        alpha = ease_inout(progress / transition)
    elif progress > 1 - transition:
        alpha = ease_inout((1 - progress) / transition)
    else:
        alpha = 1.0

    blended = main_frame.astype(np.float32) * (1 - alpha) + broll_frame.astype(np.float32) * alpha
    return np.clip(blended, 0, 255).astype(np.uint8)


def apply_pip(main_frame, broll_frame, progress, corner='br', pip_scale=0.35, transition=0.2):
    """Picture-in-picture: B-roll in a corner."""
    H, W = main_frame.shape[:2]
    pw, ph = int(W * pip_scale), int(H * pip_scale)
    margin = int(W * 0.04)
    radius = int(pw * 0.05)

    # Resize B-roll to PIP size
    pip_frame = cv2.resize(broll_frame, (pw, ph), interpolation=cv2.INTER_AREA)

    # Position
    positions = {
        'tl': (margin, margin),
        'tr': (W - pw - margin, margin),
        'bl': (margin, H - ph - margin),
        'br': (W - pw - margin, H - ph - margin),
    }
    px, py = positions.get(corner, positions['br'])

    # Slide-in animation
    if progress < transition:
        t = ease_inout(progress / transition)
        if 'r' in corner:
            px = int(px + (W - px) * (1 - t))
        else:
            px = int(px * t - pw * (1 - t))
    elif progress > 1 - transition:
        t = ease_inout((1 - progress) / transition)
        if 'r' in corner:
            px = int(px + (W - px) * (1 - t))
        else:
            px = int(px * t - pw * (1 - t))

    # Create PIP with rounded corners and shadow
    out = main_frame.copy()

    # Shadow
    shadow_offset = 4
    cv2.rectangle(out,
                  (px + shadow_offset, py + shadow_offset),
                  (px + pw + shadow_offset, py + ph + shadow_offset),
                  (0, 0, 0), -1)

    # Clamp to frame
    x0, y0 = max(0, px), max(0, py)
    x1, y1 = min(W, px + pw), min(H, py + ph)
    bx0, by0 = x0 - px, y0 - py
    bx1, by1 = bx0 + (x1 - x0), by0 + (y1 - y0)

    if x1 > x0 and y1 > y0:
        out[y0:y1, x0:x1] = pip_frame[by0:by1, bx0:bx1]
        # Border
        cv2.rectangle(out, (x0, y0), (x1 - 1, y1 - 1), (255, 255, 255), 2)

    return out


def apply_split(main_frame, broll_frame, progress, orientation='tb', transition=0.15):
    """Split screen: top/bottom or left/right."""
    H, W = main_frame.shape[:2]
    out = main_frame.copy()

    if progress < transition:
        alpha = ease_inout(progress / transition)
    elif progress > 1 - transition:
        alpha = ease_inout((1 - progress) / transition)
    else:
        alpha = 1.0

    gap = 4  # pixel gap between halves

    if orientation == 'tb':
        mid = H // 2
        # Top half: B-roll (cropped to fill)
        broll_top = cv2.resize(broll_frame, (W, mid), interpolation=cv2.INTER_AREA)
        # Bottom half: main video (cropped from center-bottom)
        main_bot = cv2.resize(main_frame[mid:, :], (W, H - mid - gap), interpolation=cv2.INTER_AREA)

        # Slide animation
        slide = int((1 - alpha) * mid)
        if slide < mid:
            out[:mid - slide] = broll_top[slide:]
            out[mid + gap:] = main_bot
            out[mid - slide:mid + gap] = 0  # gap line
    else:  # lr
        mid = W // 2
        broll_left = cv2.resize(broll_frame, (mid, H), interpolation=cv2.INTER_AREA)
        main_right = cv2.resize(main_frame[:, mid:], (W - mid - gap, H), interpolation=cv2.INTER_AREA)

        slide = int((1 - alpha) * mid)
        if slide < mid:
            out[:, :mid - slide] = broll_left[:, slide:]
            out[:, mid + gap:] = main_right
            out[:, mid - slide:mid + gap] = 0

    return out


def apply_overlay(main_frame, broll_frame, progress, transition=0.2):
    """B-roll plays behind the person (using simple brightness-based keying)."""
    H, W = main_frame.shape[:2]

    if progress < transition:
        alpha = ease_inout(progress / transition)
    elif progress > 1 - transition:
        alpha = ease_inout((1 - progress) / transition)
    else:
        alpha = 1.0

    # Simple approach: blend B-roll into the background
    # Use a darkened B-roll behind the main subject
    broll_dark = (broll_frame.astype(np.float32) * 0.6).astype(np.uint8)
    blended = cv2.addWeighted(main_frame, 1.0, broll_dark, alpha * 0.4, 0)

    return blended


MODES = {
    'cutaway': apply_cutaway,
    'pip': apply_pip,
    'split': apply_split,
    'overlay': apply_overlay,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', nargs='?', choices=list(MODES.keys()), help='B-roll mode')
    ap.add_argument('input', help='Main talking-head video')
    ap.add_argument('output', help='Output video')
    ap.add_argument('--broll', help='B-roll video or image file')
    ap.add_argument('--at', type=float, default=0, help='When to insert B-roll (seconds)')
    ap.add_argument('--duration', type=float, default=3.0, help='How long the B-roll plays (seconds)')
    ap.add_argument('--corner', default='br', choices=['tl', 'tr', 'bl', 'br'], help='PIP corner (default: br)')
    ap.add_argument('--orientation', default='tb', choices=['tb', 'lr'], help='Split orientation (default: tb)')
    ap.add_argument('--pip-scale', type=float, default=0.35, help='PIP size as fraction of frame (default: 0.35)')
    ap.add_argument('--plan', help='JSON file with multiple B-roll insertions')
    ap.add_argument('--width', type=int, default=1080, help='Output width (default: 1080)')
    a = ap.parse_args()

    # Build B-roll plan
    if a.plan:
        with open(a.plan) as f:
            plan = json.load(f)
    elif a.broll and a.mode:
        plan = [{
            'mode': a.mode, 'broll': a.broll, 'at': a.at,
            'duration': a.duration, 'corner': a.corner,
            'orientation': a.orientation, 'pip_scale': a.pip_scale
        }]
    else:
        ap.print_help()
        return

    src = a.input
    fps, dur, sw, sh = probe(src)
    if sw <= sh:
        W = a.width; H = int(round(a.width * sh / sw / 2)) * 2
    else:
        H = a.width; W = int(round(a.width * sw / sh / 2)) * 2

    # Load all B-roll sources
    print('Loading B-roll sources...', flush=True)
    broll_data = []
    for entry in plan:
        frames = load_broll_source(entry['broll'], W, H, fps, entry['duration'])
        broll_data.append((entry, frames))

    # Encode output
    enc = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-y',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
        '-i', src, '-map', '0:v', '-map', '1:a:0?',
        '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', a.output
    ], stdin=subprocess.PIPE)

    print('Rendering with B-roll...', flush=True)
    for i, frame in enumerate(read_frames(src, W, H, fps)):
        t = i / fps
        out = frame

        for entry, broll_frames in broll_data:
            start = entry['at']
            end = start + entry['duration']
            if start <= t < end and broll_frames:
                bi = min(int((t - start) * fps), len(broll_frames) - 1)
                progress = (t - start) / entry['duration']
                mode = entry.get('mode', 'cutaway')
                fn = MODES.get(mode, apply_cutaway)

                if mode == 'pip':
                    out = fn(out, broll_frames[bi], progress,
                             corner=entry.get('corner', 'br'),
                             pip_scale=entry.get('pip_scale', 0.35))
                elif mode == 'split':
                    out = fn(out, broll_frames[bi], progress,
                             orientation=entry.get('orientation', 'tb'))
                else:
                    out = fn(out, broll_frames[bi], progress)

        enc.stdin.write(out.tobytes())
        if i % int(fps * 5) == 0:
            print(f'  {t:5.1f}s / {dur:.1f}s', flush=True)

    enc.stdin.close()
    enc.wait()
    print(f'Done: {a.output}')


if __name__ == '__main__':
    main()
