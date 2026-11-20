#!/usr/bin/env python3
"""clean.py - cut filler words, stutters, mistakes and retakes, keep only the clean take.

  python3 scripts/clean.py input.mp4 clean.mp4                 # cut + render
  python3 scripts/clean.py input.mp4 clean.mp4 --dry-run       # just print the review list
  python3 scripts/clean.py input.mp4 clean.mp4 --aggressive    # also cut "you know", "I mean", "basically"...
  python3 scripts/clean.py input.mp4 clean.mp4 --keep 12-14    # never cut word numbers 12..14 (from the review list)
  python3 scripts/clean.py input.mp4 clean.mp4 --cut 40-44     # force-cut word numbers 40..44

What it removes
  fillers    um, uh, er, ah, hmm, mm (always); you know, I mean, basically, literally,
             kind of, sort of, like-as-filler (with --aggressive)
  stutters   "I I think", "the- the", cut-off half words ("rea- really")
  retakes    a sentence you started, stopped and said again: the LAST take is kept
  false starts  a phrase that is the start of the next phrase ("So today I" ... "So today I'm going to")
  noise      voiced sounds Whisper did not write down (an "mmm" or breath-um) between words
  pauses     gaps longer than --max-gap are tightened

Outputs
  clean.mp4                 the cleaned video
  clean.words.json          word timings remapped to the cleaned video (feed to captions.py --words)
  clean.review.txt          every cut with the reason, so you can check nothing good was lost
"""
import argparse, difflib, json, os, re, subprocess, sys
import numpy as np

HARD_FILLERS = {'um', 'umm', 'uh', 'uhh', 'uhm', 'er', 'erm', 'ah', 'ahh', 'hmm', 'hm', 'mm', 'mmm', 'eh'}
SOFT_FILLERS = [('you', 'know'), ('i', 'mean'), ('basically',), ('literally',), ('kind', 'of'),
                ('sort', 'of'), ('you', 'see'), ('right',), ('okay', 'so'), ('so', 'yeah')]
VERBATIM_PROMPT = ("Umm, so, uh, I- I was like, you know, um, gonna, uh... Hmm. Uh, yeah. "
                   "So, um, I mean, I- I think, uh, right.")


def norm(w):
    return re.sub(r"[^a-z0-9']", '', w.lower().replace('’', "'"))


# ---------------------------------------------------------------- audio / transcript
def load_audio(src, sr=16000):
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768


def speech_chunks(audio, sr=16000, min_pause=0.28, max_len=12.0):
    """Split speech at pauses so Whisper hears every take separately (it otherwise merges a
    false start and its retake into one tidy sentence and hides the mistake)."""
    db = energy_track(audio, sr)
    speech = db[db > np.percentile(db, 60)]
    thr = max(np.percentile(db, 15) + 8, (np.median(speech) if len(speech) else -20) - 24)
    quiet = db < thr
    chunks, start, run = [], None, 0
    for f, q in enumerate(quiet):
        if not q:
            if start is None:
                start = f
            run = 0
        elif start is not None:
            run += 1
            if run * 0.01 >= min_pause or (f - start) * 0.01 > max_len:
                chunks.append((start * 0.01, (f - run + 1) * 0.01)); start, run = None, 0
    if start is not None:
        chunks.append((start * 0.01, len(quiet) * 0.01))
    return [(max(0, a - 0.12), b + 0.12) for a, b in chunks if b - a > 0.08]


def transcribe(audio, lang=None, sr=16000):
    from faster_whisper import WhisperModel
    m = WhisperModel(os.environ.get('WHISPER_MODEL', 'small'), device='cpu', compute_type='int8')
    lang = lang or os.environ.get('WHISPER_LANG', 'en')
    out = []
    chunks = speech_chunks(audio, sr)
    for k, (a, b) in enumerate(chunks):
        print(f'\r  chunk {k + 1}/{len(chunks)}', end='', flush=True)
        clip = audio[int(a * sr):int(b * sr)]
        segs, _ = m.transcribe(clip, word_timestamps=True, vad_filter=False, language=lang, beam_size=5,
                               condition_on_previous_text=False, initial_prompt=VERBATIM_PROMPT)
        for s in segs:
            for x in (s.words or []):
                t = x.word.strip()
                if t and re.search(r'\w', t):
                    out.append({'w': t, 's': round(a + x.start, 3), 'e': round(a + min(x.end, b - a), 3)})
    print()
    return out


def energy_track(audio, sr=16000, hop=0.01):
    n = int(sr * hop)
    k = len(audio) // n
    rms = np.sqrt((audio[:k * n].reshape(k, n) ** 2).mean(1) + 1e-10)
    return 20 * np.log10(rms + 1e-9)


# ---------------------------------------------------------------- detection
def phrases_of(words, gap=0.35):
    """Split word indices into phrases on pauses and sentence punctuation."""
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and (w['s'] - words[cur[-1]]['e'] > gap):
            out.append(cur); cur = []
        cur.append(i)
        if re.search(r'[.!?]$', w['w']):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def detect(words, aggressive=False):
    cut = {}                                   # word index -> reason
    N = [norm(w['w']) for w in words]

    # fillers
    for i, n in enumerate(N):
        if n in HARD_FILLERS:
            cut[i] = 'filler'
    if aggressive:
        for i in range(len(N)):
            for pat in SOFT_FILLERS:
                if tuple(N[i:i + len(pat)]) == pat:
                    for j in range(i, i + len(pat)):
                        cut.setdefault(j, 'filler: ' + ' '.join(pat))
            # "like" as filler: followed by a comma or another filler, not "like this/that/a"
            if N[i] == 'like' and words[i]['w'].endswith(',') and i + 1 < len(N) and N[i + 1] not in ('this', 'that', 'a', 'the'):
                cut.setdefault(i, 'filler: like')

    # cut-off half words ("rea-", "I-")
    for i, w in enumerate(words):
        if w['w'].rstrip(',').endswith('-') and i + 1 < len(words):
            cut.setdefault(i, 'cut-off word')

    # stutters: same word (or 2-word chunk) said twice in a row, keep the last
    for i in range(len(N) - 1):
        if N[i] and N[i] == N[i + 1] and N[i] not in ('that', 'had', 'very', 'so', 'no', 'bye', 'yeah'):
            cut.setdefault(i, 'stutter')
    for i in range(len(N) - 3):
        if N[i] and N[i:i + 2] == N[i + 2:i + 4]:
            cut.setdefault(i, 'stutter'); cut.setdefault(i + 1, 'stutter')

    # retakes and false starts, phrase level: keep the LAST take
    ph = phrases_of(words)
    def key(p):
        return [N[i] for i in p if i not in cut and N[i] not in HARD_FILLERS and N[i]]
    for a in range(len(ph)):
        ka = key(ph[a])
        if not ka:
            continue
        for b in range(a + 1, min(a + 4, len(ph))):
            kb = key(ph[b])
            if not kb:
                continue
            n = min(3, len(ka), len(kb))
            same_start = n >= 2 and ka[:n] == kb[:n]
            prefix = len(ka) <= len(kb) and kb[:len(ka)] == ka and len(ka) >= 2
            sim = difflib.SequenceMatcher(None, ka, kb[:len(ka) + 2]).ratio()
            if prefix or (same_start and sim > 0.5) or (len(ka) >= 4 and sim > 0.75):
                why = 'false start' if prefix and len(ka) < len(kb) else 'retake (kept the later take)'
                for i in ph[a]:
                    cut.setdefault(i, why)
                # anything said between the two takes is part of the mistake
                for p in ph[a + 1:b]:
                    for i in p:
                        cut.setdefault(i, 'between takes')
                break
    return cut


def build_segments(words, keep, db, total, max_gap=0.3, pad=0.06, noise_db=None):
    """Turn kept words into time ranges. Gaps longer than max_gap are tightened, and voiced
    gaps (sound Whisper did not transcribe, e.g. a quiet 'mmm') are cut out."""
    kw = [words[i] for i in keep]
    if not kw:
        return [], []
    speech = db[db > np.percentile(db, 60)]
    loud = np.median(speech) if len(speech) else -20
    floor = np.percentile(db, 15)
    voiced_thr = noise_db if noise_db is not None else max(floor + 10, loud - 18)
    segs, notes = [], []
    s = max(0.0, kw[0]['s'] - pad)
    for a, b in zip(kw, kw[1:]):
        g0, g1 = a['e'], b['s']
        gap = g1 - g0
        split = gap > max_gap
        if not split and gap > 0.18:
            f0, f1 = int(g0 * 100) + 3, int(g1 * 100) - 3
            if f1 > f0 and (db[f0:f1] > voiced_thr).mean() > 0.6:
                split = True
                notes.append((g0, g1, 'untranscribed sound'))
        if split:
            segs.append((s, min(total, g0 + pad)))
            s = max(0.0, g1 - pad)
            if gap > max_gap:
                notes.append((g0, g1, 'pause %.2fs' % gap))
    segs.append((s, min(total, kw[-1]['e'] + pad + 0.1)))
    # merge overlaps
    out = []
    for a, b in segs:
        if out and a <= out[-1][1] + 0.01:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        elif b - a > 0.05:
            out.append((a, b))
    return out, notes


def remap(words, keep, segs):
    out, acc = [], 0.0
    offs = []
    for a, b in segs:
        offs.append((a, b, acc)); acc += b - a
    for i in keep:
        w = words[i]
        for a, b, o in offs:
            if a - 0.02 <= w['s'] <= b:
                out.append({'w': w['w'], 's': round(o + max(w['s'], a) - a, 3),
                            'e': round(o + min(w['e'], b) - a, 3)})
                break
    return out, acc


# ---------------------------------------------------------------- render
def render(src, dst, segs, fade=0.012):
    has_v = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=index',
                            '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip() != ''
    parts, labels = [], []
    for k, (a, b) in enumerate(segs):
        d = b - a
        if has_v:
            parts.append(f'[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{k}]')
        parts.append(f'[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,'
                     f'afade=t=in:d={fade},afade=t=out:st={max(0, d - fade):.3f}:d={fade}[a{k}]')
        labels.append((f'[v{k}]' if has_v else '') + f'[a{k}]')
    parts.append(''.join(labels) + f'concat=n={len(segs)}:v={1 if has_v else 0}:a=1' + ('[v][a]' if has_v else '[a]'))
    fc = ';'.join(parts)
    fcp = dst + '.filter.txt'
    open(fcp, 'w').write(fc)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', src, '-filter_complex_script', fcp]
    if has_v:
        cmd += ['-map', '[v]', '-c:v', 'libx264', '-crf', '17', '-preset', 'fast', '-pix_fmt', 'yuv420p']
    cmd += ['-map', '[a]', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', dst]
    subprocess.run(cmd, check=True)
    os.remove(fcp)


def parse_ranges(specs):
    out = set()
    for s in specs or []:
        for part in s.split(','):
            if '-' in part:
                a, b = part.split('-'); out.update(range(int(a), int(b) + 1))
            elif part.strip():
                out.add(int(part))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input'); ap.add_argument('output')
    ap.add_argument('--words', help='use an existing words.json instead of transcribing')
    ap.add_argument('--lang', help='spoken language (default en, or WHISPER_LANG)')
    ap.add_argument('--aggressive', action='store_true', help='also cut soft fillers: you know, I mean, basically...')
    ap.add_argument('--max-gap', type=float, default=0.3, help='longest pause kept between words (s)')
    ap.add_argument('--pad', type=float, default=0.06, help='breathing room kept around each cut (s)')
    ap.add_argument('--no-retakes', action='store_true', help='do not cut retakes / false starts')
    ap.add_argument('--keep', action='append', help='word numbers never to cut, e.g. 12-14')
    ap.add_argument('--cut', action='append', help='word numbers to force-cut, e.g. 40-44')
    ap.add_argument('--dry-run', action='store_true', help='print the review list, do not render')
    a = ap.parse_args()

    audio = load_audio(a.input)
    total = len(audio) / 16000
    db = energy_track(audio)
    if a.words:
        words = json.load(open(a.words))
    else:
        print('Transcribing word by word (verbatim)...', flush=True)
        words = transcribe(audio, a.lang)
    if not words:
        sys.exit('No speech found.')

    cut = detect(words, a.aggressive)
    if a.no_retakes:
        cut = {i: r for i, r in cut.items() if not r.startswith(('retake', 'false start', 'between'))}
    for i in parse_ranges(a.keep):
        cut.pop(i, None)
    for i in parse_ranges(a.cut):
        if 0 <= i < len(words):
            cut[i] = 'cut by you'
    keep = [i for i in range(len(words)) if i not in cut]
    segs, notes = build_segments(words, keep, db, total, a.max_gap, a.pad)

    # review list
    lines = [f'CLEAN CUT REVIEW  {os.path.basename(a.input)}', '']
    i = 0
    while i < len(words):
        if i in cut:
            j = i
            while j + 1 < len(words) and j + 1 in cut and cut[j + 1] == cut[i]:
                j += 1
            txt = ' '.join(words[k]['w'] for k in range(i, j + 1))
            lines.append(f'  CUT  #{i}-{j}  {words[i]["s"]:7.2f}s  [{cut[i]}]  "{txt}"')
            i = j + 1
        else:
            i += 1
    stretched = [i for i in keep if words[i]['e'] - words[i]['s'] > max(0.9, 0.1 * len(words[i]['w']) + 0.5)]
    for i in stretched:
        lines.append(f'  CHECK #{i}  {words[i]["s"]:7.2f}s  "{words[i]["w"]}" lasts {words[i]["e"] - words[i]["s"]:.1f}s, may hide a repeat. Watch it.')
    n_sound = sum(1 for n in notes if n[2] == 'untranscribed sound')
    n_pause = sum(1 for n in notes if n[2].startswith('pause'))
    new_len = sum(b - a for a, b in segs)
    lines += ['', f'  words cut: {len(cut)} of {len(words)}   untranscribed sounds cut: {n_sound}   pauses tightened: {n_pause}',
              f'  length: {total:.1f}s -> {new_len:.1f}s  ({total - new_len:.1f}s removed)', '',
              'CLEAN SCRIPT', '  ' + ' '.join(words[i]['w'] for i in keep), '',
              'Undo a cut:  --keep 12-14     Force a cut:  --cut 40-44']
    review = '\n'.join(lines)
    print(review)
    base = os.path.splitext(a.output)[0]
    open(base + '.review.txt', 'w').write(review + '\n')
    if a.dry_run:
        return
    print(f'\nRendering {len(segs)} segments...', flush=True)
    render(a.input, a.output, segs)
    new_words, _ = remap(words, keep, segs)
    json.dump(new_words, open(base + '.words.json', 'w'))
    print(f'Done: {a.output}\n      {base}.words.json  (use with captions.py --words)\n      {base}.review.txt')


if __name__ == '__main__':
    main()
