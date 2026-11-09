"""The editing pipeline behind the app: one function per step, each calling the repo's own scripts.

Order: cut pauses -> transcribe -> plan effects -> effects -> colour grade -> captions -> sound effects -> clean audio.
"""
import json, os, re, shutil, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'scripts')
PY = sys.executable
sys.path.insert(0, SCRIPTS)

# Effects the planner may use, with the kind of moment each one suits.
# None of them moves the camera unless the user turns zooms on.
EFFECTS = {
    'backdrop-word':      'A giant keyword drops in behind your head',
    'red-collage':        'Black and white you, a big red word, three lines slam in',
    'reel-cloud':         'Your clips float around your head under a boxed headline',
    'orbit':              'Your clips circle your head',
    'phone-fan':          'Your clips fan out like phones under a headline',
    'liquid-glass-graph': 'A glass card with a graph that counts up to a number',
    'checklist':          'A task list under your chin ticks off step by step',
    'headline-wall':      'Headline cards pile up behind your head',
    'glass-widgets':      'Frosted glass widgets float around your head',
    'led-sign':           'Lights dim and an LED sign glows behind you',
    'spotlight':          'Lights drop, you stay lit, a word glows behind you',
    'comment-box':        'A comment types a word and gets a reply (great for CTAs)',
}
ZOOM_FX = {'lean-in': 'A quick punch-in on one word', 'slow-push': 'A slow cinematic push-in'}

STOP = set("""a an the and or but so to of in on at for with from by as is are was were be been being it its it's this that
these those i i'm you you're your we our they their he she his her him them me my do does did have has had will would
can could should just like really very not no yes if then than when what how which who why where there here about into
out up down over under also only even more most some any all each let's gonna get got go going um uh okay oh yeah
thing things stuff anything something everything nothing take give way know think say said look see come use make want need right now today""".split())


def run(cmd, log):
    """Run a step, streaming its output lines to log()."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
    tail = []
    for line in p.stdout:
        line = line.rstrip()
        if not line: continue
        tail = (tail + [line])[-12:]
        m = re.match(r'\s*([\d.]+)s\s*/\s*([\d.]+)s', line)
        if m: log(f'  {m.group(1)}s / {m.group(2)}s')       # render progress only; technical output stays out of the UI
    if p.wait() != 0:
        raise RuntimeError('Something went wrong while editing. Details:\n' + '\n'.join(t for t in tail if 'Exception ignored' not in t)[-500:])


def probe(src):
    j = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                            'stream=width,height:stream_side_data=rotation:format=duration', '-of', 'json', src]))
    s = j['streams'][0]; w, h = int(s['width']), int(s['height'])
    rot = 0
    for sd in s.get('side_data_list', []) or []:
        rot = int(sd.get('rotation', 0) or 0)
    if abs(rot) in (90, 270): w, h = h, w
    return float(j['format']['duration']), w, h


# ───────── steps ─────────
def normalise(src, dst, max_side=1920):
    """Phone videos come in every shape: re-encode to a clean H.264/AAC file the scripts handle reliably."""
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f"scale='if(gt(iw,ih),min({max_side},iw),-2)':'if(gt(iw,ih),-2,min({max_side},ih))'",
                    '-r', '30', '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', dst], check=True)


def cut_pauses(src, dst, strength, log):
    gap = {'Light': 0.6, 'Medium': 0.45, 'Tight': 0.3}[strength]
    run([PY, '-I', os.path.join(SCRIPTS, 'cuts.py'), 'cut-silence', src, dst, '--threshold', '-32',
         '--min-silence', str(gap), '--padding', '0.1'], log)
    if not os.path.exists(dst): shutil.copy(src, dst)


def transcribe(src, log, fixes='', lang='en'):
    os.environ['WHISPER_LANG'] = lang
    run([PY, '-I', os.path.join(SCRIPTS, 'words.py'), src], log)
    path = os.path.splitext(src)[0] + '.words.json'
    words = json.load(open(path))
    for pair in [p for p in (fixes or '').split(',') if '=' in p]:
        old, new = [x.strip() for x in pair.split('=', 1)]
        for w in words: w['w'] = re.sub(re.escape(old), new, w['w'], flags=re.I)
    json.dump(words, open(path, 'w'))
    return path, words


# ───────── planning: where each effect lands ─────────
def clean(w): return re.sub(r"[^\w'$%,.-]", '', w).strip('.,').lower()

def weak(w):
    c = clean(w)
    return (not c) or c in STOP or "'" in c or len(c) < 3

def sentences(words, gap=0.5):
    """Index ranges of spoken sentences: split on . ! ? or a pause."""
    out, start = [], 0
    for i, w in enumerate(words):
        end = w['w'][-1:] in '.!?' or (i + 1 < len(words) and words[i + 1]['s'] - w['e'] > gap)
        if end or i == len(words) - 1: out.append((start, i + 1)); start = i + 1
    return out

def sentence_of(words, i):
    for a, b in sentences(words):
        if a <= i < b: return [w['w'].strip(' ,.!?"') for w in words[a:b]]
    return [words[i]['w']]

def split_lines(ws, n, per=4):
    """Up to n short lines from a word list, dropping weak words at the edges of each line."""
    ws = [w for w in ws if w]
    if not ws: return [''] * n
    size = max(1, min(per, -(-len(ws) // n)))
    chunks = [ws[k:k + size] for k in range(0, len(ws), size)][:n]
    lines = []
    for c in chunks:
        while len(c) > 1 and weak(c[-1]): c = c[:-1]      # never end a line on a filler word
        while len(c) > 1 and clean(c[0]) in ('and', 'but', 'so', 'or', 'the', 'a', 'an', 'to', 'of'): c = c[1:]
        lines.append(' '.join(c))
    return lines + [''] * (n - len(lines))

def cta_word(words):
    """The keyword in 'comment X' / 'type X' / 'DM me X', if the speaker asks for one."""
    for i, w in enumerate(words[:-1]):
        if clean(w['w']) in ('comment', 'type', 'dm') :
            for j in range(i + 1, min(len(words), i + 4)):
                if not weak(words[j]['w']): return j
    return None

def moments(words, n, dur, min_gap=3.2, avoid=()):
    """Pick n strong moments (a number, a name, a long word, the end of a thought), spread through the video."""
    scored = []
    for i, w in enumerate(words):
        if weak(w['w']) or i in avoid: continue
        c = clean(w['w'])
        sc = len(c) * 0.5
        if any(ch.isdigit() for ch in c): sc += 6
        if w['w'][:1].isupper() and i > 0 and words[i - 1]['w'][-1:] not in '.!?': sc += 3
        if w['w'][-1:] in '.!?': sc += 1.5
        scored.append((sc, i))
    scored.sort(reverse=True)
    picked, seen = [], set()
    for sc, i in scored:
        t = words[i]['s']; c = clean(words[i]['w'])
        if t < 0.8 or t > dur - 2.4 or c in seen: continue
        if all(abs(t - words[j]['s']) >= min_gap for j in picked + list(avoid)): picked.append(i); seen.add(c)
        if len(picked) >= n: break
    return sorted(picked)

def heuristic_plan(words, dur, chosen, n):
    """No AI key needed: put each chosen effect on a strong moment, filling its text from what was said."""
    cta = cta_word(words) if 'comment-box' in chosen else None
    gap = max(2.2, min(3.2, dur / (n + 1)))
    picks = moments(words, n - (1 if cta is not None else 0), dur, gap, avoid=(cta,) if cta is not None else ())
    # lists need real understanding of the script: the built-in planner leaves them to the AI planner
    others = [c for c in chosen if c not in ('comment-box', 'checklist', 'headline-wall')] or ['backdrop-word', 'reel-cloud']
    plan = []; graphs = 0; prev = None; cycle = 0
    for k, i in enumerate(picks):
        w = words[i]; word = clean(w['w']).strip("'.,")
        s = round(max(0, w['s'] - 0.15), 2); e = round(min(dur - 0.1, s + 2.6), 2)
        sent = sentence_of(words, i)
        is_num = any(ch.isdigit() for ch in word)
        if is_num and 'liquid-glass-graph' in chosen and graphs < 2 and prev != 'liquid-glass-graph':
            fx = 'liquid-glass-graph'
        else:
            pool = [c for c in others if c != 'liquid-glass-graph'] or ['backdrop-word']
            fx = pool[cycle % len(pool)]; cycle += 1
            if fx == prev and len(pool) > 1: fx = pool[cycle % len(pool)]; cycle += 1
            if fx in ('red-collage', 'led-sign') and len(word) > 9:
                alt = [c for c in pool if c not in ('red-collage', 'led-sign')]
                fx = alt[0] if alt else 'backdrop-word'
        graphs += fx == 'liquid-glass-graph'; prev = fx
        e_ = {'fx': fx, 'start': s, 'end': e}
        if fx in ('backdrop-word', 'spotlight'): e_['text'] = word.upper()
        elif fx == 'led-sign': e_['text'] = word.upper()
        elif fx == 'red-collage':
            strong = [x.lower() for x in sent if not weak(x) and clean(x) != word][:3]
            e_.update(text=word.upper(), lines='|'.join(strong + [''] * (3 - len(strong))))
        elif fx in ('reel-cloud', 'phone-fan'):
            l1, l2 = split_lines(sent, 2, 4); e_['text'] = f'{l1[:1].upper() + l1[1:]}|{l2}'.rstrip('|')
        elif fx == 'liquid-glass-graph':
            raw = w['w']; money = '$' in raw or '£' in raw or '₦' in raw
            num = re.sub(r'[^\d.kKmM%]', '', raw.replace(',', '')) or '100'
            try:
                v = float(re.sub(r'[^\d.]', '', num))
                if not re.search(r'[kKmM%]', num):
                    num = f'{v / 1e6:.3g}M' if v >= 1e6 else (f'{v / 1e3:.3g}K' if v >= 1e4 else f'{v:g}')
            except ValueError: num = '100'
            after = [x for x in sent[sent.index(w['w'].strip(' ,.!?"')) + 1:] if not weak(x)] if w['w'].strip(' ,.!?"') in sent else []
            label = ' '.join(after[:3]) or 'and counting'
            e_.update(text=(('in ' + raw[0] + ' · ') if money else '') + label, **{'from': '0', 'to': num})
        elif fx == 'checklist':
            steps = split_lines([x for x in sent if not weak(x)] or sent, 3, 3)
            e_.update(title=word.capitalize(), text='|'.join(f'{s_}::step {n_ + 1}' for n_, s_ in enumerate(steps) if s_))
            e_['end'] = round(min(dur - 0.1, s + 3.4), 2)
        elif fx == 'headline-wall':
            heads = split_lines(sent, 4, 4)
            e_.update(text='|'.join(f'{h_[:1].upper() + h_[1:]}::@kemifrank__' for h_ in heads if h_), total=word.upper()[:10], label='')
        elif fx == 'glass-widgets':
            e_.update(look='simple')
        plan.append(e_)
    if cta is not None:
        s = round(max(0, words[cta]['s'] - 0.4), 2)
        plan = [p for p in plan if p['end'] < s - 0.3 or p['start'] > s + 3.0]
        plan.append({'fx': 'comment-box', 'start': s, 'end': round(min(dur - 0.05, s + 3.0), 2), 'text': clean(words[cta]['w']).upper()[:10]})
    return sorted(plan, key=lambda p: p['start'])

def ai_plan(words, dur, chosen, n, key, log):
    """With an Anthropic API key, Claude reads the transcript and places each effect on the right line."""
    transcript = ' '.join(f"[{w['s']:.1f}] {w['w']}" for w in words)
    catalog = '\n'.join(f'- {k}: {EFFECTS[k]}' for k in chosen)
    prompt = f"""You are editing a {dur:.0f}s talking-head reel. Transcript with word start times:
{transcript}

Choose exactly {n} moments that deserve emphasis and give each one effect from this list (use variety):
{catalog}

Rules: each effect lasts 2 to 3.5s, effects never overlap and are at least 2.5s apart, none before 0.6s or after {dur - 2.2:.1f}s.
Text must come from what the speaker actually says, short and punchy. Option formats:
backdrop-word/spotlight/led-sign: "text" one word. red-collage: "text" one word, "lines" three short lines joined by |.
reel-cloud/phone-fan: "text" two short lines joined by |. liquid-glass-graph: "text" label, "from", "to" (a number they say).
checklist: "title", "text" 3 steps as "step::meta|step::meta|step::meta". headline-wall: "text" 4 items "headline::meta|...", "total", "label".
comment-box: "text" the keyword they ask people to comment (only if they ask). glass-widgets: no text needed.
Reply with only a JSON array: [{{"fx": "...", "start": 1.2, "end": 3.8, ...options}}]"""
    body = json.dumps({'model': os.environ.get('CLAUDE_MODEL', 'claude-sonnet-5-5'), 'max_tokens': 2000,
                       'messages': [{'role': 'user', 'content': prompt}]}).encode()
    req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=body, headers={
        'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=90) as r:
        text = json.loads(r.read())['content'][0]['text']
    plan = json.loads(text[text.index('['):text.rindex(']') + 1])
    plan = [p for p in plan if p.get('fx') in EFFECTS]
    log(f'Claude placed {len(plan)} effects.')
    return plan

def plan_effects(words, dur, chosen, n, zooms, log):
    chosen = [c for c in chosen if c in EFFECTS] or list(EFFECTS)
    plan = None
    key = os.environ.get('ANTHROPIC_API_KEY')
    if key:
        try: plan = ai_plan(words, dur, chosen, n, key, log)
        except Exception as ex: log(f'AI planner unavailable ({ex.__class__.__name__}), using the built-in planner.')
    if not plan: plan = heuristic_plan(words, dur, chosen, n)
    if zooms:   # quick punch-ins on strong words between effects
        busy = [(p['start'] - 0.4, p['end'] + 0.4) for p in plan]
        for i in moments(words, max(2, n), dur, 2.0):
            t = words[i]['s']
            if not any(a <= t <= b for a, b in busy):
                plan.append({'fx': 'lean-in', 'start': round(t - 0.1, 2), 'end': round(t + 1.1, 2), 'zoom': 1.3})
                busy.append((t - 0.5, t + 1.5))
    plan.sort(key=lambda p: p['start'])
    return {'effects': plan}


# ───────── the whole edit ─────────
def edit(src, work, opts, log):
    """opts: dict from the UI. Returns (output path, summary lines)."""
    os.makedirs(work, exist_ok=True)
    cur = os.path.join(work, 'v0.mp4')
    log('Preparing your video...'); normalise(src, cur)
    dur, w, h = probe(cur)
    summary = []

    if opts['cut_pauses'] != 'Off':
        log('Cutting pauses...'); nxt = os.path.join(work, 'v1_cut.mp4')
        cut_pauses(cur, nxt, opts['cut_pauses'], log)
        d2, _, _ = probe(nxt); summary.append(f'Cut {dur - d2:.1f}s of pauses ({dur:.1f}s → {d2:.1f}s)')
        cur, dur = nxt, d2

    log('Listening to what you say...')
    words_path, words = transcribe(cur, log, opts.get('fixes', ''), opts.get('lang', 'en'))
    if not words: raise RuntimeError('No speech found in this video. The editor needs someone talking.')

    plan_path = os.path.join(work, 'plan.json')
    if opts['n_effects'] > 0 or opts['zooms']:
        log('Choosing where each effect goes...')
        plan = plan_effects(words, dur, opts['effects'], opts['n_effects'] if opts['n_effects'] else 0, opts['zooms'], log)
        if opts['n_effects'] == 0: plan['effects'] = [p for p in plan['effects'] if p['fx'] == 'lean-in']
        json.dump(plan, open(plan_path, 'w'), indent=1)
        if plan['effects']:
            log('Adding effects (the slow part)...'); nxt = os.path.join(work, 'v2_fx.mp4')
            run([PY, '-I', os.path.join(SCRIPTS, 'fx.py'), '--plan', plan_path, cur, nxt], log)
            cur = nxt
            summary.append('Effects: ' + ', '.join(f"{p['fx']} at {p['start']:.1f}s" for p in plan['effects']))
    else:
        json.dump({'effects': []}, open(plan_path, 'w'))

    if opts['grade'] != 'None':
        log(f"Colour grading ({opts['grade']})..."); nxt = os.path.join(work, 'v3_grade.mp4')
        run([PY, '-I', os.path.join(SCRIPTS, 'grade.py'), opts['grade'].lower(), cur, nxt, '--strength', '0.75'], log)
        cur = nxt; summary.append(f"Colour grade: {opts['grade']}")

    if opts['captions'] != 'Off':
        log('Adding captions...'); nxt = os.path.join(work, 'v4_caps.mp4')
        style = {'House style (lowercase + yellow serif)': 'editorial', 'Word pop': 'word-pop', 'Highlight': 'highlight',
                 'Karaoke': 'karaoke', 'Clean subtitle': 'clean', 'Bold stack': 'bold-stack'}[opts['captions']]
        cmd = [PY, '-I', os.path.join(SCRIPTS, 'captions.py'), cur, nxt, '--words', words_path, '--style', style, '--fx-plan', plan_path]
        if style != 'editorial': cmd += ['--position', 'bottom']
        run(cmd, log); cur = nxt; summary.append(f"Captions: {opts['captions']}")

    if opts['sfx'] != 'Off':
        log('Adding sound effects...'); nxt = os.path.join(work, 'v5_sfx.mp4')
        level = {'Subtle': 0.22, 'Balanced': 0.32, 'Punchy': 0.45}[opts['sfx']]
        import sfx as S
        ev = S.auto_events(json.load(open(plan_path)))
        # moderate set: whooshes, typing, ticks and clicks; no pops, bubbles or sparkles
        ev = [e for e in ev if e['sfx'] not in ('pop', 'bubble', 'shimmer', 'impact', 'riser', 'buzz', 'glitch')]
        ev += [{'sfx': 'whoosh', 'at': max(0, p['start'] - 0.15), 'vol': 0.7}
               for p in json.load(open(plan_path))['effects'] if p['fx'] in ('reel-cloud', 'orbit', 'phone-fan', 'headline-wall')]
        json.dump(ev, open(os.path.join(work, 'sfx.json'), 'w'), indent=0)
        S.mix(cur, nxt, ev, level, 'synth')
        cur = nxt; summary.append(f"Sound effects: {opts['sfx'].lower()}")

    out = os.path.join(work, 'edited.mp4')
    if opts['clean_audio']:
        log('Cleaning up the audio...')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', cur, '-c:v', 'copy', '-af',
                        'highpass=f=70,afftdn=nf=-32:nr=6,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2,loudnorm=I=-14:TP=-1.5:LRA=9',
                        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', out], check=True)
        summary.append('Audio cleaned and levelled for social media')
    else:
        shutil.copy(cur, out)
    return out, summary
