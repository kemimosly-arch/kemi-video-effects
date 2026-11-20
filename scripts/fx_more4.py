# Pack 6: the "editorial" look (cream + forest green, serif words that blur in, split cards, clean zooms), by @kemifrank__.
# Text markup in these effects: *word* = italic script accent, **word** = big bold word, | = new line.

ED_CREAM, ED_GREEN, ED_TXT = (248, 243, 214), (46, 70, 48), (250, 246, 228)
def ed_theme(e):
    t = e.o.get('theme', 'cream')
    return (ED_CREAM, ED_GREEN) if t == 'cream' else (ED_GREEN, ED_TXT)   # (background, text)


def ed_tokens(text):
    """'you should **NEVER** put *these links*|in your bio' -> lines of (word, kind) with kind n / i / b. Spans can cover several words."""
    lines = []
    for ln in str(text).split('|'):
        toks, mode = [], None
        for w in ln.split():
            if w.startswith('**'): mode = 'b'; w = w[2:]
            elif w.startswith('*'): mode = 'i'; w = w[1:]
            kind = mode or 'n'
            core = w.rstrip('.,!?:;')
            if mode == 'b' and core.endswith('**'): w = core[:-2] + w[len(core):]; mode = None
            elif mode == 'i' and core.endswith('*'): w = core[:-1] + w[len(core):]; mode = None
            if w: toks.append((w, kind))
        if toks: lines.append(toks)
    return lines


ED_KIND = {'n': ('dmserif', 1.0), 'i': ('didonei', 1.5), 'b': ('didoneb', 2.1)}

def ed_tok_img(word, kind, S, fill):
    k, m = ED_KIND[kind]; f = font(k, S * m); asc, desc = f.getmetrics(); pad = int(S * 0.4)
    im = Image.new('RGBA', (int(f.getlength(word)) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad, pad + asc), word, font=f, fill=fill + (255,), anchor='ls')
    return im, pad, asc, desc, f.getlength(word), f.getlength(' ')


def ed_layout(lines, S, fill, maxw):
    """Shrink S until every line fits; returns [(tokens_with_imgs, width, asc, desc)], S."""
    while True:
        out = []
        for toks in lines:
            items = [(w, kd, ed_tok_img(w, kd, S, fill)) for w, kd in toks]
            sp = S * 0.28
            width = sum(it[2][4] for it in items) + sp * (len(items) - 1)
            out.append((items, width, max(it[2][2] for it in items), max(it[2][3] for it in items)))
        if max(o[1] for o in out) <= maxw or S < 16: return out, S
        S = int(S * 0.9)


def ed_draw_text(c, e, text, cx, cy, S, fill, t0=0.0, reveal=None, times=None, key=''):
    """Draw marked-up text centred on (cx, cy). Words blur in one by one."""
    lay_key = ('edl', key, int(S))
    lines, S = cached(e, lay_key, lambda: ed_layout(ed_tokens(text), S, fill, c.W * 0.84))
    n = sum(len(l[0]) for l in lines)
    reveal = reveal if reveal is not None else max(0.3, min(e.d * 0.55, n * 0.22))
    hts = [(a + d) * 0.82 for _, _, a, d in lines]; y = cy - sum(hts) / 2
    idx = 0
    for (items, width, asc, desc), h in zip(lines, hts):
        base = y + asc * 0.9; x = cx - width / 2
        for w, kd, (im, pad, a, d, wl, sp_) in items:
            ti = (times[idx] if times and idx < len(times) else t0 + reveal * idx / max(1, n))
            k = ease_out((c.lt - ti) / 0.35)
            if k > 0:
                im2 = im.filter(ImageFilter.GaussianBlur(S * 0.14 * (1 - k))) if k < 0.98 else im
                comp(c, im2, x - pad, base - pad - a + (1 - k) * S * 0.18, k * fade(c, e, 0.15))
            x += wl + S * 0.28; idx += 1
        y += h


def ed_times(e):
    t = e.o.get('times')
    return [float(x) for x in str(t).split('|')] if t else None


@effect('text-card', 'editorial: a full-screen cream or green card where serif words blur in as you speak')
def fx_text_card(c, e):
    bg, fg = ed_theme(e)
    if e.o.get('theme') != 'clear': c.img[:] = np.float32(bg) / 255; c.m[:] = 0
    ed_draw_text(c, e, e.o.get('text', 'so what is the *fix?*'), c.W / 2, c.H * float(e.o.get('y', 0.48)), c.W * 0.085,
                 fg if e.o.get('theme') != 'clear' else ED_TXT, 0.05, times=ed_times(e))


@effect('serif-words', 'editorial: serif words blur in over your video at chest height (no background)')
def fx_serif_words(c, e):
    cy = c.H * float(e.o['y']) if e.o.get('y') else clamp(c.fy + c.fw * 1.75, c.H * 0.5, c.H * 0.85)
    ed_draw_text(c, e, e.o.get('text', 'you should **NEVER**|put *links*'), c.W / 2, cy, c.W * 0.07,
                 rgb(e.o.get('color'), ED_TXT), 0.05, times=ed_times(e))


def ed_frame_box(c, e, box, k, crop_h=0.62):
    """Shrink the video (cropped around you) into a rounded box. box = (x0, y0, w, h) in pixels. k = 0..1 transition."""
    bx, by, bw, bh = box
    x0, y0 = bx * k, by * k; w = c.W + (bw - c.W) * k; h = c.H + (bh - c.H) * k
    ch = c.H + (c.H * crop_h - c.H) * k; cw = ch * w / h
    cx = clamp(c.fx, cw / 2, c.W - cw / 2); cy = clamp(c.fy + ch * 0.18, ch / 2, c.H - ch / 2)
    src = c.img[int(cy - ch / 2):int(cy + ch / 2), int(cx - cw / 2):int(cx + cw / 2)]
    pic = cv2.resize(src, (max(1, int(w)), max(1, int(h))), interpolation=cv2.INTER_AREA)
    return pic, int(x0), int(y0)


@effect('split-card', 'editorial: a cream/green card on top with a title and list pills, your video in a rounded frame below')
def fx_split_card(c, e):
    bg, fg = ed_theme(e)
    k = ease_inout(c.lt / 0.35) if c.lt < e.d - 0.3 else ease_inout((e.d - c.lt) / 0.3)
    bw, bh = c.W * 0.9, c.H * 0.42; box = ((c.W - bw) / 2, c.H - bh - c.W * 0.05, bw, bh)
    pic, x0, y0 = ed_frame_box(c, e, box, k)
    out = np.empty_like(c.img); out[:] = np.float32(bg) / 255
    r = int(c.W * 0.04 * k) + 1; m = np.zeros(pic.shape[:2], np.uint8)
    cv2.rectangle(m, (r, 0), (pic.shape[1] - r, pic.shape[0]), 255, -1); cv2.rectangle(m, (0, r), (pic.shape[1], pic.shape[0] - r), 255, -1)
    for px, py in ((r, r), (pic.shape[1] - r, r), (r, pic.shape[0] - r), (pic.shape[1] - r, pic.shape[0] - r)): cv2.circle(m, (px, py), r, 255, -1)
    mm = (m.astype(np.float32) / 255)[..., None]
    h_, w_ = min(pic.shape[0], c.H - y0), min(pic.shape[1], c.W - x0)
    out[y0:y0 + h_, x0:x0 + w_] = out[y0:y0 + h_, x0:x0 + w_] * (1 - mm[:h_, :w_]) + pic[:h_, :w_] * mm[:h_, :w_]
    c.img = out; c.m = np.zeros_like(c.m)
    if k < 0.6: return
    top = box[1]
    ed_draw_text(c, e, e.o.get('text', 'The next 10 is for|people who are|*about to buy*'), c.W / 2, top * 0.27, c.W * 0.075, fg, 0.3, times=ed_times(e), key='t')
    items = [s for s in str(e.o.get('items', '')).split('|') if s]
    if not items: return
    S = c.W * 0.05; pill_h = S * 1.85; gap = S * 0.4
    panel_h = len(items) * (pill_h + gap) + gap; py0 = max(top * 0.5, top - panel_h - c.W * 0.05); pw = c.W * 0.86
    kp = ease_out((c.lt - 0.45) / 0.3)
    if kp <= 0: return
    pfill = (ED_GREEN if bg == ED_CREAM else ED_CREAM)
    pan = rrect(pw, panel_h, S * 0.7, pfill + (255,)); comp(c, pan, (c.W - pw) / 2, py0, kp * fade(c, e))
    it_t = [float(x) for x in str(e.o.get('item_times', '')).split('|') if x] or [0.7 + 0.5 * j for j in range(len(items))]
    for j, s in enumerate(items):
        kj = ease_out((c.lt - it_t[min(j, len(it_t) - 1)]) / 0.3)
        if kj <= 0: continue
        def mk(s=s):
            f = font('dmserif', S); tw = min(f.getlength(s), pw * 0.72)
            p = rrect(tw + S * 1.2, pill_h * 0.82, S * 0.4, (bg if bg == ED_CREAM else ED_CREAM) + (255,))
            ImageDraw.Draw(p).text((S * 0.6, pill_h * 0.41), s, font=f, fill=(ED_GREEN if True else fg) + (255,), anchor='lm'); return p
        p = cached(e, ('pill', j), mk); yy = py0 + gap + j * (pill_h + gap)
        dot = rrect(S * 0.6, S * 0.6, S * 0.3, (bg if bg == ED_CREAM else ED_CREAM) + (255,))
        comp(c, dot, (c.W - pw) / 2 + S * 0.5, yy + pill_h * 0.5 - S * 0.3, kj * fade(c, e))
        pi = p.filter(ImageFilter.GaussianBlur(S * 0.2 * (1 - kj))) if kj < 0.98 else p
        comp(c, pi, (c.W - pw) / 2 + S * 1.5, yy + pill_h * 0.09 + (1 - kj) * S * 0.4, kj * fade(c, e))


@effect('dual-frame', 'editorial: a close-up of you on top and the wide shot below, like two cameras')
def fx_dual_frame(c, e):
    H2 = c.H // 2
    z = float(e.o.get('zoom', 1.35)); cw = c.W / z; ch = H2 / z * 1.0
    cx = clamp(c.fx, cw / 2, c.W - cw / 2); cy = clamp(c.fy + c.fw * 0.15, ch / 2, c.H - ch / 2)
    top = cv2.resize(c.img[int(cy - ch / 2):int(cy + ch / 2), int(cx - cw / 2):int(cx + cw / 2)], (c.W, H2), interpolation=cv2.INTER_CUBIC)
    y0 = int(clamp(c.fy - c.fw * 1.35, 0, c.H - H2))
    bot = c.img[y0:y0 + H2].copy()
    k = ease_out(c.lt / 0.25)
    out = c.img.copy(); out[:H2] = top * k + c.img[:H2] * (1 - k); out[H2:H2 + bot.shape[0]] = bot * k + c.img[H2:H2 + bot.shape[0]] * (1 - k)
    c.img = out; c.m = np.zeros_like(c.m)


@effect('clean-zoom', 'a smooth, eased zoom into your face that holds, drifts slightly, then eases back out')
def fx_clean_zoom(c, e):
    Z = float(e.o.get('zoom', 1.28)); tin = float(e.o.get('ease', 0.45))
    back = str(e.o.get('out', 'true')).lower() not in ('0', 'false', 'no')
    k = 1.0 if tin <= 0 else (lambda x: x * x * x * (x * (x * 6 - 15) + 10))(clamp(c.lt / tin))       # smootherstep
    if back and c.lt > e.d - tin: k = min(k, (lambda x: x * x * x * (x * (x * 6 - 15) + 10))(clamp((e.d - c.lt) / tin)))
    drift = 0.025 * clamp(c.lt / e.d)
    face_cam(c, 1 + (Z - 1) * k + drift * k, float(e.o.get('head_at', 0.4)))


@effect('stat-grid', 'editorial: a green card with a big number counting up over a grid that fills in')
def fx_stat_grid(c, e):
    bg, fg = (ED_GREEN, ED_TXT) if e.o.get('theme', 'green') == 'green' else (ED_CREAM, ED_GREEN)
    c.img[:] = np.float32(bg) / 255; c.m[:] = 0
    to = str(e.o.get('to', '90')); val, suf, dec = num_parts(to)
    p = ease_out((c.lt - 0.2) / max(0.6, e.d * 0.5))
    cols, rows = 9, 6; cell = c.W * 0.075; gx = (c.W - cols * cell) / 2; gy = c.H * 0.4
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    filled = int(cols * rows * p)
    for j in range(cols * rows):
        x, y = gx + (j % cols) * cell, gy + (j // cols) * cell
        d.rounded_rectangle([x + cell * 0.1, y + cell * 0.1, x + cell * 0.9, y + cell * 0.9], cell * 0.12, fill=fg + ((110 if j < filled else 40),))
    comp(c, to_np(lay), 0, 0, fade(c, e))
    num = text_img(f'{val * p:,.{dec}f}{suf}', c.W * 0.3, 'didoneb', fg, shadow=12)
    place(c, num, c.W / 2, gy + rows * cell / 2, 1, 0, clamp(c.lt / 0.15) * fade(c, e))
    if e.o.get('text'): ed_draw_text(c, e, e.o['text'], c.W / 2, gy - c.W * 0.12, c.W * 0.055, fg, 0.0, key='s')


@effect('cta-quote', 'editorial: Comment "WORD" in big serif with a small line underneath, blurring in')
def fx_cta_quote(c, e):
    word = str(e.o.get('text', 'GUIDE')).upper(); sub = e.o.get('sub', '')
    xx, yy = grid(c)
    g = np.clip((yy / c.H - 0.45) / 0.4, 0, 1) * 0.45 * ramp(c, e, 0.3, 0.2)
    c.img *= (1 - g)[..., None]
    txt = f'Comment|**“{word}”**' + (f'|{sub}' if sub else '')
    ed_draw_text(c, e, txt, c.W / 2, c.H * float(e.o.get('y', 0.62)), c.W * 0.058, ED_TXT, 0.05, times=ed_times(e))
