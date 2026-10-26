#!/usr/bin/env python3
"""Color grade your video with one command, by @kemifrank__

Presets:
  moody      – desaturated, teal shadows, warm highlights, gentle contrast
  warm       – golden warm tones, cozy feel
  cool       – blue-tinted, clean and modern
  film       – classic film emulation with lifted blacks and warm mids
  pop        – high saturation, punchy colors
  bw         – black and white with contrast
  vintage    – faded film look with warm tint and grain
  cinematic  – teal-orange Hollywood grade with widescreen bars
  sunset     – golden hour warmth with soft shadows
  editorial  – high contrast, slightly desaturated, magazine look
  neon       – boosted neon colors with crushed blacks
  pastel     – soft, light, dreamy pastels

Usage:
  python grade.py film input.mp4 output.mp4
  python grade.py cinematic input.mp4 output.mp4 --strength 0.8
  python grade.py vintage input.mp4 output.mp4 --grain 0.03
  python grade.py --list
"""
import argparse, json, math, os, subprocess, sys
import numpy as np


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
        yield np.frombuffer(d, np.uint8).reshape(h, w, 3)
    p.stdout.close()
    p.wait()


# ─── grade functions ───
def _lum(img):
    return (img @ np.float32([0.299, 0.587, 0.114]))[..., None]


def grade_moody(img, strength=1.0):
    lum = _lum(img)
    o = lum + (img - lum) * 0.6
    o = np.power(np.clip(o, 1e-6, 1), 1.3) * 0.88
    o = o + (1 - lum) * np.float32([-0.03, 0.035, 0.065]) + lum * np.float32([0.05, 0.015, -0.04])
    o = np.clip((o - 0.42) * 1.12 + 0.42, 0, 1)
    return img * (1 - strength) + o * strength


def grade_warm(img, strength=1.0):
    o = np.clip(img * np.float32([1.1, 1.02, 0.85]) + 0.02, 0, 1)
    # Slightly lift shadows
    o = np.clip(o * 0.92 + 0.06, 0, 1)
    return img * (1 - strength) + o * strength


def grade_cool(img, strength=1.0):
    o = np.clip(img * np.float32([0.88, 0.98, 1.12]), 0, 1)
    o = np.clip((o - 0.5) * 1.05 + 0.5, 0, 1)
    return img * (1 - strength) + o * strength


def grade_film(img, strength=1.0):
    lum = _lum(img)
    # Desaturate slightly
    o = lum + (img - lum) * 0.82
    # Lift blacks, compress highlights
    o = o * 0.85 + 0.06
    # Warm mids
    o = o + lum * np.float32([0.04, 0.02, -0.02])
    # S-curve contrast
    o = np.clip(o, 0, 1)
    o = o * o * (3 - 2 * o)  # smoothstep
    return img * (1 - strength) + o * strength


def grade_pop(img, strength=1.0):
    lum = _lum(img)
    o = lum + (img - lum) * 1.35
    o = np.clip((o - 0.5) * 1.12 + 0.5, 0, 1)
    return img * (1 - strength) + o * strength


def grade_bw(img, strength=1.0):
    lum = _lum(img)
    o = np.clip((lum - 0.5) * 1.25 + 0.5, 0, 1)
    o = np.repeat(o, 3, axis=2)
    return img * (1 - strength) + o * strength


def grade_vintage(img, strength=1.0):
    lum = _lum(img)
    # Fade: lift blacks, pull down whites
    o = img * 0.78 + 0.10
    # Warm yellow-green cast
    o = o + np.float32([0.06, 0.04, -0.03])
    # Desaturate
    o = lum + (o - lum) * 0.7
    o = np.clip(o, 0, 1)
    return img * (1 - strength) + o * strength


def grade_cinematic(img, strength=1.0):
    lum = _lum(img)
    # Teal shadows, orange highlights (classic Hollywood)
    o = img.copy()
    # Shadows: push toward teal
    shadow_mask = np.clip(1 - lum * 2, 0, 1)
    o = o + shadow_mask * np.float32([-0.04, 0.04, 0.08])
    # Highlights: push toward warm orange
    hi_mask = np.clip(lum * 2 - 1, 0, 1)
    o = o + hi_mask * np.float32([0.06, 0.02, -0.05])
    # Contrast
    o = np.clip((o - 0.5) * 1.15 + 0.5, 0, 1)
    # Slight desaturation
    o = lum + (o - lum) * 0.85
    o = np.clip(o, 0, 1)
    return img * (1 - strength) + o * strength


def grade_sunset(img, strength=1.0):
    lum = _lum(img)
    o = img * np.float32([1.15, 1.0, 0.78])
    # Golden glow in highlights
    hi = np.clip(lum * 1.5 - 0.3, 0, 1)
    o = o + hi * np.float32([0.08, 0.04, -0.06])
    # Soft shadows
    o = o * 0.9 + 0.04
    o = np.clip(o, 0, 1)
    return img * (1 - strength) + o * strength


def grade_editorial(img, strength=1.0):
    lum = _lum(img)
    # High contrast, slightly desaturated
    o = lum + (img - lum) * 0.75
    o = np.clip((o - 0.5) * 1.35 + 0.5, 0, 1)
    # Cool neutral tone
    o = o + np.float32([0.0, -0.01, 0.02])
    o = np.clip(o, 0, 1)
    return img * (1 - strength) + o * strength


def grade_neon(img, strength=1.0):
    lum = _lum(img)
    # Crush blacks
    o = np.clip(img * 1.1 - 0.04, 0, 1)
    # Boost saturation
    o = lum + (o - lum) * 1.6
    # High contrast
    o = np.clip((o - 0.5) * 1.3 + 0.5, 0, 1)
    return img * (1 - strength) + o * strength


def grade_pastel(img, strength=1.0):
    lum = _lum(img)
    # Lift everything, desaturate, soften
    o = img * 0.65 + 0.28
    # Slightly desaturate
    o = lum + (o - lum) * 0.7
    # Gentle pink/lavender cast
    o = o + np.float32([0.03, 0.0, 0.04])
    o = np.clip(o, 0, 1)
    return img * (1 - strength) + o * strength


GRADES = {
    'moody': ('Desaturated, teal shadows, warm highlights', grade_moody),
    'warm': ('Golden warm tones, cozy feel', grade_warm),
    'cool': ('Blue-tinted, clean and modern', grade_cool),
    'film': ('Classic film with lifted blacks and warm mids', grade_film),
    'pop': ('High saturation, punchy colors', grade_pop),
    'bw': ('Black and white with contrast', grade_bw),
    'vintage': ('Faded film look with warm tint', grade_vintage),
    'cinematic': ('Teal-orange Hollywood grade', grade_cinematic),
    'sunset': ('Golden hour warmth', grade_sunset),
    'editorial': ('High contrast, slightly desaturated', grade_editorial),
    'neon': ('Boosted neons with crushed blacks', grade_neon),
    'pastel': ('Soft, light, dreamy pastels', grade_pastel),
}


def add_grain(frame, amount=0.02):
    """Add film grain noise."""
    noise = np.random.normal(0, amount, frame.shape).astype(np.float32)
    return np.clip(frame + noise, 0, 1)


def add_vignette(frame, strength=0.35):
    """Add a vignette (darkened edges)."""
    H, W = frame.shape[:2]
    yy, xx = np.ogrid[0:H, 0:W]
    d = ((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2
    v = np.clip(d, 0, 1).astype(np.float32)
    return frame * (1 - strength * v)[..., None]


def add_letterbox(frame, ratio=2.35):
    """Add cinematic letterbox bars."""
    H, W = frame.shape[:2]
    target_h = int(W / ratio)
    bar = (H - target_h) // 2
    if bar > 0:
        frame[:bar] = 0
        frame[-bar:] = 0
    return frame


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('grade', nargs='?', help='Grade preset name')
    ap.add_argument('input', nargs='?', help='Input video')
    ap.add_argument('output', nargs='?', help='Output video')
    ap.add_argument('--strength', type=float, default=1.0, help='Grade strength 0-1 (default: 1.0)')
    ap.add_argument('--grain', type=float, default=0, help='Film grain amount (default: 0, try 0.02)')
    ap.add_argument('--vignette', type=float, default=0, help='Vignette strength (default: 0, try 0.3)')
    ap.add_argument('--letterbox', type=float, default=0, help='Letterbox aspect ratio (e.g., 2.35 for cinemascope)')
    ap.add_argument('--width', type=int, default=1080, help='Output width (default: 1080)')
    ap.add_argument('--list', action='store_true', help='List all available grades')
    a = ap.parse_args()

    if a.list:
        print('Available color grades:\n')
        for name, (desc, _) in GRADES.items():
            print(f'  {name:12s}  {desc}')
        return

    if not a.grade or not a.input or not a.output:
        ap.print_help()
        return

    if a.grade not in GRADES:
        print(f"Unknown grade '{a.grade}'. Use --list to see options.")
        return

    desc, grade_fn = GRADES[a.grade]
    print(f'Applying "{a.grade}" grade ({desc})...', flush=True)

    fps, dur, sw, sh = probe(a.input)
    if sw <= sh:
        W = a.width; H = int(round(a.width * sh / sw / 2)) * 2
    else:
        H = a.width; W = int(round(a.width * sw / sh / 2)) * 2

    enc = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-y',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
        '-i', a.input, '-map', '0:v', '-map', '1:a:0?',
        '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', a.output
    ], stdin=subprocess.PIPE)

    for i, frame in enumerate(read_frames(a.input, W, H, fps)):
        t = i / fps
        img = frame.astype(np.float32) / 255.0

        # Apply grade
        img = grade_fn(img, a.strength)

        # Optional: grain
        if a.grain > 0:
            img = add_grain(img, a.grain)

        # Optional: vignette
        if a.vignette > 0:
            img = add_vignette(img, a.vignette)

        out = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)

        # Optional: letterbox (after converting to uint8)
        if a.letterbox > 0:
            out = add_letterbox(out, a.letterbox)

        enc.stdin.write(out.tobytes())
        if i % int(fps * 5) == 0:
            print(f'  {t:5.1f}s / {dur:.1f}s', flush=True)

    enc.stdin.close()
    enc.wait()
    print(f'Done: {a.output}')


if __name__ == '__main__':
    main()
