#!/usr/bin/env python3
"""Cut dead space, trim, and jump-cut your video, by @kemifrank__

Commands:
  cut-silence   – detect and remove silent gaps (dead space)
  trim          – cut a section of the video
  jump-cut      – remove all pauses for a punchy, fast-paced edit

Usage:
  python cuts.py cut-silence input.mp4 output.mp4
  python cuts.py cut-silence input.mp4 output.mp4 --threshold -35 --min-silence 0.4 --padding 0.08
  python cuts.py trim input.mp4 output.mp4 --start 2.5 --end 10.0
  python cuts.py jump-cut input.mp4 output.mp4 --max-gap 0.25
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


def detect_silence(src, threshold_db=-30, min_silence=0.5):
    """Use FFmpeg silencedetect to find silent sections."""
    cmd = [
        'ffmpeg', '-v', 'error', '-i', src,
        '-af', f'silencedetect=noise={threshold_db}dB:d={min_silence}',
        '-f', 'null', '-'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    stderr = result.stderr

    silences = []
    start = None
    for line in stderr.split('\n'):
        if 'silence_start' in line:
            parts = line.split('silence_start:')
            if len(parts) > 1:
                start = float(parts[1].strip().split()[0])
        elif 'silence_end' in line and start is not None:
            parts = line.split('silence_end:')
            if len(parts) > 1:
                end = float(parts[1].strip().split()[0])
                silences.append((start, end))
                start = None

    return silences


def detect_silence_numpy(src, threshold_db=-30, min_silence=0.5):
    """Fallback: extract audio as PCM and detect silence with numpy."""
    cmd = [
        'ffmpeg', '-v', 'error', '-i', src,
        '-ac', '1', '-ar', '16000', '-f', 's16le', '-acodec', 'pcm_s16le', '-'
    ]
    p = subprocess.run(cmd, capture_output=True)
    if not p.stdout:
        return []

    samples = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    sr = 16000
    threshold = 10 ** (threshold_db / 20.0)

    # Compute RMS in windows
    win = int(sr * 0.02)  # 20ms windows
    n_wins = len(samples) // win
    if n_wins == 0:
        return []

    samples = samples[:n_wins * win].reshape(n_wins, win)
    rms = np.sqrt(np.mean(samples ** 2, axis=1))

    is_silent = rms < threshold
    silences = []
    start = None
    for i, s in enumerate(is_silent):
        t = i * win / sr
        if s and start is None:
            start = t
        elif not s and start is not None:
            end = t
            if end - start >= min_silence:
                silences.append((start, end))
            start = None
    if start is not None:
        end = n_wins * win / sr
        if end - start >= min_silence:
            silences.append((start, end))

    return silences


def cut_silence(src, dst, threshold_db=-30, min_silence=0.5, padding=0.05, max_gap=None):
    """Remove silent sections from the video."""
    fps, dur, w, h = probe(src)

    print(f'Detecting silence (threshold: {threshold_db}dB, min: {min_silence}s)...', flush=True)
    silences = detect_silence(src, threshold_db, min_silence)
    if not silences:
        # Try numpy fallback
        silences = detect_silence_numpy(src, threshold_db, min_silence)

    if not silences:
        print('No significant silence detected. Copying original.')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-c', 'copy', dst], check=True)
        return 0

    # Build keep segments (the parts between silences)
    keeps = []
    prev_end = 0
    for s_start, s_end in silences:
        seg_start = prev_end
        seg_end = s_start + padding
        if seg_end > seg_start + 0.05:
            keeps.append((seg_start, seg_end))
        prev_end = max(prev_end, s_end - padding)

    # Add the tail
    if prev_end < dur - 0.05:
        keeps.append((prev_end, dur))

    if not keeps:
        print('Video is entirely silent.')
        return 0

    removed = dur - sum(e - s for s, e in keeps)
    print(f'Found {len(silences)} silent section(s). Removing {removed:.1f}s of silence.', flush=True)

    # Build FFmpeg filter to concat the kept segments
    _concat_segments(src, dst, keeps, w, h, fps)
    return removed


def jump_cut(src, dst, max_gap=0.25, threshold_db=-28, padding=0.03):
    """Aggressive jump cut: remove all pauses longer than max_gap."""
    return cut_silence(src, dst, threshold_db=threshold_db, min_silence=max_gap, padding=padding)


def trim(src, dst, start=0, end=None):
    """Simple trim: keep only from start to end."""
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', src, '-ss', str(start)]
    if end is not None:
        cmd += ['-to', str(end)]
    cmd += ['-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', dst]
    print(f'Trimming: {start:.1f}s to {end or "end"}...', flush=True)
    subprocess.run(cmd, check=True)
    print(f'Done: {dst}')


def _concat_segments(src, dst, segments, w, h, fps):
    """Concatenate video segments using FFmpeg filter_complex."""
    if len(segments) == 1:
        s, e = segments[0]
        trim(src, dst, s, e)
        return

    # Use a concat file approach for accuracy
    import tempfile
    tmpdir = tempfile.mkdtemp()
    seg_files = []

    print(f'Cutting {len(segments)} segments...', flush=True)
    for i, (s, e) in enumerate(segments):
        seg_path = os.path.join(tmpdir, f'seg{i:04d}.mp4')
        cmd = [
            'ffmpeg', '-v', 'error', '-y', '-i', src,
            '-ss', str(s), '-to', str(e),
            '-c:v', 'libx264', '-crf', '17', '-preset', 'fast', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k',
            '-avoid_negative_ts', 'make_zero', seg_path
        ]
        subprocess.run(cmd, check=True)
        seg_files.append(seg_path)

    # Concat
    list_path = os.path.join(tmpdir, 'list.txt')
    with open(list_path, 'w') as f:
        for p in seg_files:
            f.write(f"file '{p}'\n")

    print('Stitching segments...', flush=True)
    subprocess.run([
        'ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0',
        '-i', list_path, '-c', 'copy', '-movflags', '+faststart', dst
    ], check=True)

    # Clean up temp files
    for p in seg_files:
        os.remove(p)
    os.remove(list_path)
    os.rmdir(tmpdir)

    new_dur = sum(e - s for s, e in segments)
    print(f'Done: {dst} ({new_dur:.1f}s)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command')

    # cut-silence
    cs = sub.add_parser('cut-silence', help='Remove silent gaps from the video')
    cs.add_argument('input', help='Input video')
    cs.add_argument('output', help='Output video')
    cs.add_argument('--threshold', type=float, default=-30, help='Silence threshold in dB (default: -30)')
    cs.add_argument('--min-silence', type=float, default=0.5, help='Minimum silence duration to cut (default: 0.5s)')
    cs.add_argument('--padding', type=float, default=0.05, help='Padding around cuts in seconds (default: 0.05)')

    # jump-cut
    jc = sub.add_parser('jump-cut', help='Aggressive jump cuts: remove all pauses')
    jc.add_argument('input', help='Input video')
    jc.add_argument('output', help='Output video')
    jc.add_argument('--max-gap', type=float, default=0.25, help='Max allowed gap between words (default: 0.25s)')
    jc.add_argument('--threshold', type=float, default=-28, help='Silence threshold in dB (default: -28)')

    # trim
    tr = sub.add_parser('trim', help='Trim the video to a specific section')
    tr.add_argument('input', help='Input video')
    tr.add_argument('output', help='Output video')
    tr.add_argument('--start', type=float, default=0, help='Start time in seconds')
    tr.add_argument('--end', type=float, help='End time in seconds')

    a = ap.parse_args()
    if a.command == 'cut-silence':
        cut_silence(a.input, a.output, a.threshold, a.min_silence, a.padding)
    elif a.command == 'jump-cut':
        jump_cut(a.input, a.output, a.max_gap, a.threshold)
    elif a.command == 'trim':
        trim(a.input, a.output, a.start, a.end)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
