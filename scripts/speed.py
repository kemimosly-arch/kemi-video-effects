#!/usr/bin/env python3
"""Speed ramps, slow-mo, and time effects for your video, by @kemifrank__

Commands:
  ramp       – smooth speed change at a specific moment (speed up or slow down)
  slow-mo    – slow down a section of the video
  speed-up   – speed up a section of the video
  timelapse  – speed up the entire video

Usage:
  python speed.py ramp input.mp4 output.mp4 --at 3.0 --duration 2.0 --speed 0.4
  python speed.py slow-mo input.mp4 output.mp4 --start 2.0 --end 4.0 --speed 0.3
  python speed.py speed-up input.mp4 output.mp4 --start 5.0 --end 8.0 --speed 2.5
  python speed.py timelapse input.mp4 output.mp4 --speed 4.0

  Multiple ramps via plan:
  python speed.py ramp input.mp4 output.mp4 --plan speed.json

Plan JSON:
  [
    {"start": 2.0, "end": 4.0, "speed": 0.4},
    {"start": 8.0, "end": 9.5, "speed": 2.0}
  ]
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


def ease_inout(x):
    x = max(0, min(1, x))
    return 3 * x * x - 2 * x * x * x


def build_time_map(dur, fps, segments):
    """Build a mapping from output time to source time.

    segments: list of (start, end, speed) in source time.
    Between segments, speed is 1.0.
    Returns list of source times for each output frame.
    """
    # Sort segments by start time
    segments = sorted(segments, key=lambda s: s[0])

    # Build source-time breakpoints
    # For each segment, the output duration = source_duration / speed
    # For gaps between segments, output duration = gap duration (speed 1.0)

    # Calculate total output duration
    out_dur = 0
    prev_end = 0
    for start, end, speed in segments:
        # Gap before this segment
        if start > prev_end:
            out_dur += start - prev_end
        # This segment
        seg_dur = end - start
        out_dur += seg_dur / speed
        prev_end = end
    # Tail after last segment
    if prev_end < dur:
        out_dur += dur - prev_end

    # Now build frame-by-frame source time mapping
    out_frames = int(out_dur * fps) + 1
    src_times = []

    for oi in range(out_frames):
        ot = oi / fps  # output time

        # Walk through the timeline to find source time
        remaining = ot
        src_t = 0
        prev_end = 0

        for start, end, speed in segments:
            # Gap before segment
            gap = start - prev_end
            if gap > 0:
                if remaining <= gap:
                    src_t = prev_end + remaining
                    remaining = 0
                    break
                remaining -= gap

            # Segment itself
            seg_src_dur = end - start
            seg_out_dur = seg_src_dur / speed
            if remaining <= seg_out_dur:
                # We're inside this segment
                # Apply easing for smooth transitions
                seg_progress = remaining / seg_out_dur
                src_t = start + seg_progress * seg_src_dur
                remaining = 0
                break
            remaining -= seg_out_dur
            prev_end = end

        if remaining > 0:
            # We're past the last segment
            src_t = (segments[-1][1] if segments else 0) + remaining

        src_times.append(min(src_t, dur - 1.0 / fps))

    return src_times, out_dur


def apply_speed(src, dst, segments, width=1080):
    """Apply speed changes and render output."""
    fps, dur, sw, sh = probe(src)

    if sw <= sh:
        W = width; H = int(round(width * sh / sw / 2)) * 2
    else:
        H = width; W = int(round(width * sw / sh / 2)) * 2

    src_times, out_dur = build_time_map(dur, fps, segments)
    total_out = len(src_times)

    print(f'Speed edit: {dur:.1f}s input -> {out_dur:.1f}s output', flush=True)
    print(f'Segments: {len(segments)}', flush=True)
    for s, e, spd in segments:
        label = 'slow-mo' if spd < 1 else 'speed-up'
        print(f'  {s:.1f}s-{e:.1f}s: {spd:.1f}x ({label})', flush=True)

    # Read all source frames into memory (for random access)
    # For long videos, we'll use frame seeking instead
    print('Reading source frames...', flush=True)
    all_frames = []
    for frame in _read_frames(src, W, H, fps):
        all_frames.append(frame)

    if not all_frames:
        print('No frames read from source.')
        return

    n_src = len(all_frames)

    # Handle audio: for now, preserve audio with atempo filter chain
    # Build atempo filter for FFmpeg (only supports 0.5-100.0)
    # For complex speed maps, we skip audio re-timing and just keep the video
    has_audio = _has_audio(src)

    enc_cmd = [
        'ffmpeg', '-v', 'error', '-y',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
        '-r', str(fps), '-i', '-',
        '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', dst
    ]

    enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE)

    print('Rendering speed edit...', flush=True)
    for oi, src_t in enumerate(src_times):
        # Find the source frame index
        si = int(round(src_t * fps))
        si = max(0, min(si, n_src - 1))

        # Optional: interpolate between frames for smoother slow-mo
        # For now, nearest frame
        enc.stdin.write(all_frames[si].tobytes())
        if oi % int(fps * 5) == 0:
            print(f'  {oi / fps:5.1f}s / {out_dur:.1f}s', flush=True)

    enc.stdin.close()
    enc.wait()

    # If there's audio, mux it back with speed adjustment
    if has_audio and len(segments) == 1:
        _mux_audio_simple(src, dst, segments[0][2], fps)

    print(f'Done: {dst}')


def _read_frames(src, w, h, fps):
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


def _has_audio(src):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a',
                        '-show_entries', 'stream=index', '-of', 'json', src],
                       capture_output=True, text=True)
    j = json.loads(r.stdout)
    return bool(j.get('streams'))


def _mux_audio_simple(src, video_dst, speed, fps):
    """For simple single-speed changes, mux audio with atempo."""
    import tempfile
    tmp = tempfile.mktemp(suffix='.mp4')
    os.rename(video_dst, tmp)

    # Build atempo chain (atempo only supports 0.5-100.0)
    atempo_filters = []
    s = speed
    while s < 0.5:
        atempo_filters.append('atempo=0.5')
        s /= 0.5
    while s > 100.0:
        atempo_filters.append('atempo=100.0')
        s /= 100.0
    atempo_filters.append(f'atempo={s:.4f}')
    af = ','.join(atempo_filters)

    cmd = [
        'ffmpeg', '-v', 'error', '-y',
        '-i', tmp, '-i', src,
        '-map', '0:v', '-map', '1:a:0?',
        '-c:v', 'copy', '-af', af,
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest', '-movflags', '+faststart', video_dst
    ]
    subprocess.run(cmd, check=True)
    os.remove(tmp)


def timelapse(src, dst, speed=4.0, width=1080):
    """Speed up the entire video."""
    fps, dur, sw, sh = probe(src)
    segments = [(0, dur, speed)]
    apply_speed(src, dst, segments, width)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command')

    # ramp
    rp = sub.add_parser('ramp', help='Smooth speed ramp at a moment')
    rp.add_argument('input'); rp.add_argument('output')
    rp.add_argument('--at', type=float, default=3.0, help='Center of the speed change (seconds)')
    rp.add_argument('--duration', type=float, default=2.0, help='Duration of the speed section')
    rp.add_argument('--speed', type=float, default=0.4, help='Speed factor (0.3 = slow-mo, 2.0 = fast)')
    rp.add_argument('--plan', help='JSON file with multiple speed segments')
    rp.add_argument('--width', type=int, default=1080)

    # slow-mo
    sm = sub.add_parser('slow-mo', help='Slow down a section')
    sm.add_argument('input'); sm.add_argument('output')
    sm.add_argument('--start', type=float, default=0); sm.add_argument('--end', type=float)
    sm.add_argument('--speed', type=float, default=0.4, help='Speed factor (default: 0.4)')
    sm.add_argument('--width', type=int, default=1080)

    # speed-up
    su = sub.add_parser('speed-up', help='Speed up a section')
    su.add_argument('input'); su.add_argument('output')
    su.add_argument('--start', type=float, default=0); su.add_argument('--end', type=float)
    su.add_argument('--speed', type=float, default=2.0, help='Speed factor (default: 2.0)')
    su.add_argument('--width', type=int, default=1080)

    # timelapse
    tl = sub.add_parser('timelapse', help='Speed up the whole video')
    tl.add_argument('input'); tl.add_argument('output')
    tl.add_argument('--speed', type=float, default=4.0, help='Speed factor (default: 4.0)')
    tl.add_argument('--width', type=int, default=1080)

    a = ap.parse_args()

    if a.command == 'ramp':
        if a.plan:
            with open(a.plan) as f:
                segs = json.load(f)
            segments = [(s['start'], s['end'], s['speed']) for s in segs]
        else:
            start = a.at - a.duration / 2
            end = a.at + a.duration / 2
            segments = [(max(0, start), end, a.speed)]
        apply_speed(a.input, a.output, segments, a.width)

    elif a.command == 'slow-mo':
        fps, dur, _, _ = probe(a.input)
        end = a.end or dur
        segments = [(a.start, end, a.speed)]
        apply_speed(a.input, a.output, segments, a.width)

    elif a.command == 'speed-up':
        fps, dur, _, _ = probe(a.input)
        end = a.end or dur
        segments = [(a.start, end, a.speed)]
        apply_speed(a.input, a.output, segments, a.width)

    elif a.command == 'timelapse':
        timelapse(a.input, a.output, a.speed, a.width)

    else:
        ap.print_help()


if __name__ == '__main__':
    main()
