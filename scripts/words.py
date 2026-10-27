#!/usr/bin/env python3
"""Find when each word is said, so effects can land on the right word.

usage: python words.py input.mp4            -> prints "12.34  word" lines and saves input.words.json
Uses faster-whisper (installed into the skill's .venv on first run). On a Mac with mlx-whisper installed, that is used instead.
"""
import json, os, subprocess, sys

src = sys.argv[1]
out = os.path.splitext(src)[0] + '.words.json'
words = []
try:
    import mlx_whisper
    r = mlx_whisper.transcribe(src, path_or_hf_repo='mlx-community/whisper-large-v3-turbo', word_timestamps=True)
    words = [{'w': w['word'].strip(), 's': round(w['start'], 2), 'e': round(w['end'], 2)} for seg in r['segments'] for w in seg.get('words', [])]
except ImportError:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print('Installing the transcriber (one time, about 1 minute)...', flush=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'faster-whisper'], check=True)
        from faster_whisper import WhisperModel
    model = WhisperModel(os.environ.get('WHISPER_MODEL', 'base'), device='cpu', compute_type='int8')
    import numpy as np  # decode with ffmpeg: works on every phone format (.mov, .mp4, .m4a)
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True).stdout
    segs, _ = model.transcribe(np.frombuffer(pcm, np.int16).astype(np.float32) / 32768, word_timestamps=True, vad_filter=True)
    words = [{'w': w.word.strip(), 's': round(w.start, 2), 'e': round(w.end, 2)} for s in segs for w in (s.words or [])]

json.dump(words, open(out, 'w'), indent=0)
for w in words: print(f"{w['s']:7.2f}  {w['w']}")
print(f'\nSaved {len(words)} words to {out}')
