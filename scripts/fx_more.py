# More effects for fx.py, by @kemifrank__ (pack 3, Nov 2026).
# This file is executed inside fx.py, so every helper there (place, comp, text_img, glass, pop, fade...) is available.

# cute fonts for any effect's "font" option
FONT.update({k: os.path.join(ROOT, 'fonts', v) for k, v in {
    'fredoka': 'Fredoka.ttf', 'baloo': 'Baloo2.ttf', 'pacifico': 'Pacifico.ttf', 'caveat': 'Caveat.ttf', 'chewy': 'Chewy.ttf',
    'sniglet': 'Sniglet.ttf', 'gochi': 'GochiHand.ttf', 'lobster': 'Lobster.ttf', 'dancing': 'DancingScript.ttf',
    'shrikhand': 'Shrikhand.ttf', 'bungee': 'Bungee.ttf', 'cherry': 'CherryBombOne.ttf', 'gluten': 'Gluten.ttf',
    'grand': 'Grandstander.ttf', 'dmserif': 'DmSerifDisplay.ttf', 'brico': 'BricolageGrotesque.ttf', 'righteous': 'Righteous.ttf',
    'playpen': 'PlaypenSans.ttf'}.items()})
PINK, LILAC, MINT, SUN, CORAL, SKY, CREAMY = (255, 120, 180), (196, 160, 255), (140, 230, 190), (255, 214, 70), (255, 120, 100), (110, 190, 255), (255, 247, 235)
def fk(e, default): return e.o.get('font', default) if e.o.get('font', default) in FONT else default
def words_of(e, default): return [w for w in str(e.o.get('text', default)).split('|') if w]
def above_head(c, k=1.05): return c.fy - c.fw * k
def fity(c, y, h, m=0.03): return clamp(y, h / 2 + c.H * m, c.H - h / 2 - c.H * m)
def fitx(c, x, w, m=0.02): return clamp(x, w / 2 + c.W * m, c.W - w / 2 - c.W * m)


# ---------- typography ----------
@effect('stacked-words', 'three words stack up behind your head, each in a different font')
def fx_stacked_words(c, e):
    ws = words_of(e, 'CREATE|POST|EARN')[:3]
    kinds = ['bungee', 'pacifico', 'shrikhand']
    cols = [CREAMY, rgb(e.o.get('color'), PINK), SUN]
    ims = cached(e, 'ims', lambda: [fit_text(w, c.W * 0.8, kinds[i % 3], start=int(c.W * 0.17), fill=cols[i % 3], shadow=8) for i, w in enumerate(ws)])
    tot = sum(im.height * 0.78 for im in ims); y = max(c.H * 0.02, above_head(c, 0.6) - tot - ims[0].height * 0.22)
    for i, im in enumerate(ims):
        k = pop(c, 0.12 * i, 0.35)
        place(c, im, c.W / 2 + (1 - k) * (c.W * (0.6 if i % 2 else -0.6)), y + im.height * 0.5, 1, 0, clamp(k * 2) * fade(c, e), behind=True)
        y += im.height * 0.78


@effect('word-rain', 'your word rains down behind you in every size')
def fx_word_rain(c, e):
    w = e.o.get('text', 'VIRAL'); col = rgb(e.o.get('color'), CREAMY)
    def setup():
        r = random.Random(3); return [(r.uniform(0.05, 0.95), r.uniform(-0.6, 0), r.uniform(0.06, 0.16), r.uniform(0.5, 1.0), r.uniform(-12, 12)) for _ in range(26)]
    drops = cached(e, 'd', setup)
    for i, (x, y0, s, sp, rot) in enumerate(drops):
        im = cached(e, ('w', round(s, 2)), lambda s=s: text_img(w, c.W * s, fk(e, 'chewy'), col, shadow=4))
        y = (y0 + c.lt * sp * 0.9) * c.H
        place(c, im, x * c.W, y, 1, rot, 0.85 * fade(c, e) * clamp(c.lt / 0.15), behind=True)


@effect('outline-echo', 'a giant word with outline echoes pulsing out behind your head')
def fx_outline_echo(c, e):
    w = e.o.get('text', 'FOCUS'); col = rgb(e.o.get('color'), CREAMY); kind = fk(e, 'bungee')
    size = cached(e, 's', lambda: lines_fit([w], c.W * 0.9, kind, int(c.W * 0.3)))
    def outline_im():
        f = font(kind, size); bb = f.getbbox(w, stroke_width=4); pad = 20
        im = Image.new('RGBA', (bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), w, font=f, fill=(0, 0, 0, 0), stroke_width=max(3, size // 40), stroke_fill=col + (255,))
        return im
    ol = cached(e, 'o', outline_im); solid = cached(e, 'f', lambda: text_img(w, size, kind, col, shadow=8))
    y = fity(c, above_head(c, 0.85), solid.height); al = fade(c, e)
    for j in range(5, 0, -1):
        ph = (c.lt * 1.4 + j / 5) % 1
        place(c, ol, c.W / 2, y - j * size * 0.42 * ease_out(min(1, c.lt / 0.4)), 1, 0, (1 - ph) * 0.8 * al, behind=True)
    place(c, solid, c.W / 2, y, 0.8 + 0.2 * pop(c, 0, 0.35), 0, clamp(c.lt / 0.1) * al, behind=True)


@effect('neon-word', 'a neon tube word flickers on behind your head')
def fx_neon_word(c, e):
    w = e.o.get('text', 'open'); col = rgb(e.o.get('color'), (255, 60, 190))
    im = cached(e, 'w', lambda: fit_text(w, c.W * 0.86, fk(e, 'righteous'), start=int(c.W * 0.24), fill=(255, 240, 250), glow=(col, int(c.W * 0.03))))
    on = 1.0 if c.lt > 0.55 else (0.15 if int(c.lt * 24) % 3 == 1 else 0.95)
    c.img *= (1 - 0.35 * clamp(c.lt / 0.3) * fade(c, e) * (1 - c.m))[..., None]
    place(c, im, c.W / 2, fity(c, above_head(c, 1.0), im.height), 1, 0, on * fade(c, e) * clamp(c.lt / 0.05), behind=True)


@effect('script-word', 'a word writes itself in pretty script behind your head')
def fx_script_word(c, e):
    w = e.o.get('text', 'dreamy'); col = rgb(e.o.get('color'), CREAMY)
    im = cached(e, 'w', lambda: fit_text(w, c.W * 0.88, fk(e, 'pacifico'), start=int(c.W * 0.26), fill=col, shadow=10))
    k = ease_inout(c.lt / 0.8)
    if k <= 0: return
    a = np.asarray(im).copy(); cut = int(a.shape[1] * k)
    a[:, cut:, 3] = 0
    edge = slice(max(0, cut - 30), cut); a[:, edge, 3] = (a[:, edge, 3] * np.linspace(1, 0, cut - max(0, cut - 30))[None, :]).astype(np.uint8)
    place(c, Image.fromarray(a), c.W / 2, fity(c, above_head(c, 1.0), im.height), 1, -4, fade(c, e), behind=True)


@effect('bubble-word', 'a squishy bubble-letter word bounces in behind your head')
def fx_bubble_word(c, e):
    w = e.o.get('text', 'yay!'); col = rgb(e.o.get('color'), (255, 110, 170))
    im = cached(e, 'w', lambda: fit_text(w, c.W * 0.84, fk(e, 'cherry'), start=int(c.W * 0.3), fill=col, stroke=int(c.W * 0.012), stroke_fill=(255, 255, 255), shadow=10))
    lt = c.lt; sq = math.sin(lt * 14) * math.exp(-lt * 5)
    k = ease_back(lt / 0.3)
    im2 = im.resize((max(1, int(im.width * (1 + 0.12 * sq))), max(1, int(im.height * (1 - 0.12 * sq)))), Image.BILINEAR)
    place(c, im2, c.W / 2, fity(c, above_head(c, 1.0), im.height) - (1 - k) * c.H * 0.2, 0.6 + 0.4 * k, 0, fade(c, e), behind=True)


@effect('sticker-word', 'a word slaps on like a sticker beside your face')
def fx_sticker_word(c, e):
    w = e.o.get('text', 'NEW'); bg = rgb(e.o.get('color'), SUN)
    def mk():
        t = text_img(w, c.W * 0.1, fk(e, 'sniglet'), (40, 30, 60)); pad = int(c.W * 0.03)
        s = rrect(t.width + pad * 2, t.height + pad, c.W * 0.04, (255, 255, 255, 255))
        inner = rrect(t.width + pad, t.height, c.W * 0.03, bg + (255,)); s.alpha_composite(inner, (pad // 2, pad // 2)); s.alpha_composite(t, (pad, pad // 2))
        return shadowed(s, 14, 8, 130)
    im = cached(e, 's', mk)
    side = 1 if c.fx < c.W / 2 else -1
    k = pop(c, 0, 0.25)
    x = clamp(c.fx + side * c.fw * 1.9, im.width / 2, c.W - im.width / 2)
    place(c, im, x, c.fy - c.fw * 0.2, 1.6 - 0.6 * k, -12 * side + 4 * (1 - k), clamp(k * 3) * fade(c, e), guard=True)


@effect('letter-drop', 'the letters of a word drop in one by one and bounce')
def fx_letter_drop(c, e):
    w = e.o.get('text', 'HELLO'); col = rgb(e.o.get('color'), CREAMY); kind = fk(e, 'shrikhand')
    size = cached(e, 's', lambda: lines_fit([w], c.W * 0.86, kind, int(c.W * 0.26)))
    ims = cached(e, 'l', lambda: [text_img(ch, size, kind, col, shadow=8) for ch in w])
    widths = [font(kind, size).getlength(ch) for ch in w]; x = c.W / 2 - sum(widths) / 2
    y = fity(c, above_head(c, 1.0), ims[0].height)
    for i, (im, cw) in enumerate(zip(ims, widths)):
        t0 = 0.08 * i
        if c.lt < t0: x += cw; continue
        lt = c.lt - t0; fall = min(1, lt / 0.25)
        dy = -(1 - fall ** 2) * c.H * 0.35 if fall < 1 else -abs(math.sin((lt - 0.25) * 12)) * size * 0.25 * math.exp(-(lt - 0.25) * 6)
        place(c, im, x + cw / 2, y + dy, 1, 0, fade(c, e), behind=True)
        x += cw


@effect('marquee', 'a scrolling ticker band of your text runs behind you')
def fx_marquee(c, e):
    txt = ('  ✦  '.join([e.o.get('text', 'LINK IN BIO')] * 6)).replace('✦', '*')
    col = rgb(e.o.get('color'), SUN); kind = fk(e, 'bungee')
    def band():
        t = text_img(txt, c.W * 0.075, kind, (20, 16, 24)); b = Image.new('RGBA', (t.width, int(t.height * 1.0)), col + (255,))
        b.alpha_composite(t, (0, (b.height - t.height) // 2)); return b
    b = cached(e, 'b', band); k = ease_out(c.lt / 0.3)
    for j, (yy, sp, rot) in enumerate(((max(c.H * 0.06, above_head(c, 0.6)), 1, -6), (min(c.H * 0.82, c.fy + c.fw * 1.7), -1, 5))):
        off = (c.lt * c.W * 0.35 * sp) % (b.width / 6)
        place(c, b, c.W / 2 - off * sp, yy, 1, rot, k * fade(c, e), behind=(j == 0))


@effect('big-number', 'a huge number counts up behind your head')
def fx_big_number(c, e):
    to = str(e.o.get('to', e.o.get('text', '100K'))); pre = ''.join(ch for ch in to[:2] if not ch.isdigit() and ch not in '.,')
    val, suf, dec = num_parts(to[len(pre):])
    v = val * ease_out(c.lt / max(0.4, e.d * 0.6))
    s = f'{pre}{v:,.{dec}f}{suf}'
    col = rgb(e.o.get('color'), CREAMY); kind = fk(e, 'bungee')
    size = cached(e, 's', lambda: lines_fit([to + '0'], c.W * 0.9, kind, int(c.W * 0.32)))
    yb = fity(c, above_head(c, 0.95), size * 1.3)
    place(c, text_img(s, size, kind, col, shadow=10), c.W / 2, yb, 1, 0, clamp(c.lt / 0.1) * fade(c, e), behind=True)
    if e.o.get('label'):
        lab = cached(e, 'lab', lambda: text_img(e.o['label'], c.W * 0.06, 'caveat', rgb(e.o.get('color'), PINK), shadow=6))
        place(c, lab, c.W / 2, max(lab.height / 2, yb - size * 0.75), 1, -3, clamp((c.lt - 0.3) / 0.2) * fade(c, e), behind=True)


@effect('quote-card', 'a glass quote card with your words slides up under your chin')
def fx_quote_card(c, e):
    q = e.o.get('text', 'Done is better than perfect'); who = e.o.get('name', '@kemifrank__')
    w = c.W * 0.84; kind = fk(e, 'dmserif')
    size = cached(e, 's', lambda: int(c.W * 0.06))
    lines = cached(e, 'l', lambda: wrap_words(q, font(kind, size), w - c.W * 0.12))
    h = size * 1.25 * len(lines) + c.W * 0.22
    k = ease_out(c.lt / 0.35); cy = min(c.H * 0.8, c.fy + c.fw * 2.4) + (1 - k) * c.H * 0.15
    g = glass(c, w, h, c.W * 0.05, c.W / 2, cy, 0.18, dark=0.25)
    d = ImageDraw.Draw(g)
    d.text((c.W * 0.06, c.W * 0.0), '“', font=font('dmserif', c.W * 0.16), fill=PINK + (255,))
    for i, ln in enumerate(lines): d.text((c.W * 0.06, c.W * 0.1 + i * size * 1.25), ln, font=font(kind, size), fill=(255, 255, 255, 255))
    d.text((c.W * 0.06, h - c.W * 0.085), '— ' + who, font=font('caveat', c.W * 0.05), fill=SUN + (255,))
    place(c, g, c.W / 2, cy, 1, 0, k * fade(c, e))


def wrap_words(s, f, maxw):
    out, cur = [], ''
    for w in s.split():
        t = (cur + ' ' + w).strip()
        if f.getlength(t) > maxw and cur: out.append(cur); cur = w
        else: cur = t
    return out + ([cur] if cur else [])


@effect('highlight-words', 'three key words pop up around your head in marker boxes')
def fx_highlight_words(c, e):
    ws = words_of(e, 'easy|fast|free')[:3]
    cols = [SUN, PINK, MINT]
    spots = [(-1.7, -0.9, -8), (1.7, -0.5, 7), (-1.5, 1.0, 5)]
    for i, w in enumerate(ws):
        def mk(i=i, w=w):
            t = text_img(w, c.W * 0.075, fk(e, 'grand'), (30, 24, 20)); p = int(c.W * 0.02)
            b = rrect(t.width + p * 2, t.height, c.W * 0.015, cols[i] + (255,)); b.alpha_composite(t, (p, 0)); return shadowed(b, 10, 6, 110)
        im = cached(e, ('h', i), mk); dx, dy, rot = spots[i]
        k = pop(c, 0.15 + 0.25 * i, 0.3)
        x = clamp(c.fx + dx * c.fw, im.width / 2, c.W - im.width / 2)
        place(c, im, x, c.fy + dy * c.fw, 0.5 + 0.5 * k, rot, clamp(k * 2) * fade(c, e), guard=True)


@effect('side-titles', 'tall magazine titles run up both sides of the frame')
def fx_side_titles(c, e):
    ws = words_of(e, 'CREATE|DAILY')
    for j, (w, x, rot) in enumerate(((ws[0], c.W * 0.08, 90), (ws[-1], c.W * 0.92, -90))):
        im = cached(e, ('s', j), lambda w=w: fit_text(w, c.H * 0.7, fk(e, 'anton'), start=int(c.W * 0.14), fill=rgb(e.o.get('color'), CREAMY), shadow=8))
        k = ease_out((c.lt - 0.1 * j) / 0.4)
        place(c, im, x, c.H * 0.5 + (1 - k) * c.H * 0.3 * (1 if j else -1), 1, rot, k * fade(c, e), behind=True)


# ---------- doodles and bubbles ----------
@effect('speech-bubble', 'a comic speech bubble pops out beside your face')
def fx_speech_bubble(c, e):
    txt = e.o.get('text', 'wait for it!')
    side = 1 if c.fx < c.W / 2 else -1
    def mk():
        f = font(fk(e, 'gochi'), c.W * 0.07); lines = wrap_words(txt, f, c.W * 0.42)
        tw = max(f.getlength(l) for l in lines); th = f.size * 1.15 * len(lines)
        w, h = int(tw + c.W * 0.1), int(th + c.W * 0.08)
        im = Image.new('RGBA', (w, h + int(c.W * 0.08)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse([0, 0, w - 1, h], fill=(255, 255, 255, 255), outline=(20, 20, 20, 255), width=5)
        tx = w * (0.25 if side < 0 else 0.75)
        d.polygon([(tx - 30, h - 12), (tx + 30, h - 12), (tx - 40 * side, h + c.W * 0.07)], fill=(255, 255, 255, 255), outline=(20, 20, 20, 255))
        d.line([(tx - 26, h - 9), (tx + 26, h - 9)], fill=(255, 255, 255, 255), width=12)
        for i, l in enumerate(lines): d.text((w / 2, c.W * 0.04 + f.size * 0.55 + i * f.size * 1.15), l, font=f, fill=(20, 20, 20, 255), anchor='mm')
        return shadowed(im, 12, 6, 100)
    im = cached(e, 'b', mk); k = pop(c, 0, 0.3)
    x = fitx(c, c.fx + side * c.fw * 1.55, im.width)
    place(c, im, x, fity(c, c.fy - c.fw * 1.35, im.height), 0.4 + 0.6 * k, 0, clamp(k * 2) * fade(c, e), guard=True)


@effect('thought-bubble', 'a fluffy thought cloud floats above your head')
def fx_thought_bubble(c, e):
    txt = e.o.get('text', 'hmm...')
    def mk():
        f = font(fk(e, 'caveat'), c.W * 0.085); lines = wrap_words(txt, f, c.W * 0.5)
        tw = max(f.getlength(l) for l in lines); th = f.size * 1.1 * len(lines)
        w, h = int(tw + c.W * 0.2), int(th + c.W * 0.16)
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        r = random.Random(4)
        for a in np.linspace(0, 2 * math.pi, 14, endpoint=False):
            cx, cy = w / 2 + (w / 2 - h * 0.28) * math.cos(a), h / 2 + (h / 2 - h * 0.28) * math.sin(a); rr = h * r.uniform(0.24, 0.3)
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 255, 255, 255))
        d.ellipse([h * 0.25, h * 0.2, w - h * 0.25, h * 0.8], fill=(255, 255, 255, 255))
        for i, l in enumerate(lines): d.text((w / 2, h / 2 + (i - (len(lines) - 1) / 2) * f.size * 1.1), l, font=f, fill=(40, 40, 60, 255), anchor='mm')
        return shadowed(im, 14, 6, 90)
    im = cached(e, 'b', mk)
    by = fity(c, c.fy - c.fw * 2.1, im.height)
    for j, s in enumerate((0.035, 0.05)):
        k = pop(c, 0.1 * j, 0.25)
        if k > 0:
            dot = cached(e, ('d', j), lambda s=s: shadowed(rrect(c.W * s, c.W * s, c.W * s / 2, (255, 255, 255, 255)), 6, 3, 90))
            place(c, dot, c.fx + c.fw * (0.55 + 0.25 * j), c.fy - c.fw * (1.0 + 0.3 * j), k, 0, fade(c, e), guard=True)
    k = pop(c, 0.25, 0.35)
    place(c, im, fitx(c, c.fx + c.fw * 0.4 + (c.fw * 1.4 if by > c.fy - c.fw * 1.6 else 0), im.width), by + math.sin(c.lt * 2.5) * c.H * 0.006, 0.5 + 0.5 * k, 0, clamp(k * 2) * fade(c, e), guard=True)


@effect('arrows-in', 'hand-drawn arrows sketch in from both sides, pointing at you')
def fx_arrows_in(c, e):
    col = rgb(e.o.get('color'), SUN) + (255,); wd = max(6, c.W // 120)
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for j, (x0, y0, x1, y1, b) in enumerate(((c.W * 0.06, c.fy - c.fw * 1.6, c.fx - c.fw * 0.85, c.fy - c.fw * 0.2, 0.25),
                                             (c.W * 0.94, c.fy + c.fw * 1.4, c.fx + c.fw * 0.85, c.fy + c.fw * 0.1, 0.25))):
        k = ease_out((c.lt - 0.25 * j) / 0.4)
        if k <= 0: continue
        pts = arrow_pts(x0, y0, x1, y1, b); hand_path(d, pts, col, wd, k)
        if k >= 0.99: arrow_head(d, pts, col, wd, c.W * 0.04)
    comp(c, to_np(lay), 0, 0, fade(c, e))
    if e.o.get('text') and c.lt > 0.5:
        lab = cached(e, 'l', lambda: text_img(e.o['text'], c.W * 0.08, 'caveat', col[:3], shadow=6))
        place(c, lab, c.W * 0.22, c.fy - c.fw * 1.85, 0.7 + 0.3 * pop(c, 0.5), -6, fade(c, e))


@effect('doodle-crown', 'a hand-drawn crown sketches itself onto your head')
def fx_doodle_crown(c, e):
    col = rgb(e.o.get('color'), SUN) + (255,); wd = max(9, c.W // 70)
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    cx, top = c.fx, c.fy - c.fw * 1.05; h = clamp(c.fw * 0.65, 0, max(c.fw * 0.25, top - c.H * 0.02)); w = c.fw * 1.15
    pts = [(cx - w / 2, top), (cx - w / 2 - w * 0.06, top - h), (cx - w / 4, top - h * 0.45), (cx, top - h * 1.15),
           (cx + w / 4, top - h * 0.45), (cx + w / 2 + w * 0.06, top - h), (cx + w / 2, top), (cx - w / 2, top)]
    dense = []
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]): dense += [(xa + (xb - xa) * s, ya + (yb - ya) * s) for s in np.linspace(0, 1, 10)]
    if c.lt > 0.6: d.polygon(pts[:-1], fill=col[:3] + (int(90 * clamp((c.lt - 0.6) / 0.3)),))
    hand_path(d, dense, col, wd, ease_inout(c.lt / 0.6))
    if c.lt > 0.55:
        for (px, py) in (pts[1], pts[3], pts[5]):
            r = c.fw * 0.06 * pop(c, 0.55); d.ellipse([px - r, py - r, px + r, py + r], fill=col)
    comp(c, to_np(lay), 0, 0, fade(c, e))


@effect('sparkles', 'twinkling sparkles dance around your head')
def fx_sparkles(c, e):
    col = rgb(e.o.get('color'), (255, 236, 160))
    def star(s):
        s = int(s); im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); m = s / 2
        d.polygon([(m, 0), (m + s * 0.1, m - s * 0.1), (s, m), (m + s * 0.1, m + s * 0.1), (m, s), (m - s * 0.1, m + s * 0.1), (0, m), (m - s * 0.1, m - s * 0.1)], fill=col + (255,))
        return Image.alpha_composite(im.filter(ImageFilter.GaussianBlur(s * 0.08)), im)
    def setup():
        r = random.Random(11); return [(r.uniform(0, 2 * math.pi), r.uniform(1.2, 2.3), r.uniform(0.05, 0.1), r.uniform(0, 1), r.uniform(1.5, 3)) for _ in range(14)]
    for a, rr, s, ph, sp in cached(e, 'p', setup):
        tw = (math.sin((c.lt * sp + ph) * 2 * math.pi) + 1) / 2
        im = cached(e, ('s', round(s, 3)), lambda s=s: star(c.W * s))
        place(c, im, c.fx + rr * c.fw * math.cos(a + c.lt * 0.3), c.fy + rr * c.fw * 1.1 * math.sin(a + c.lt * 0.3), 0.4 + 0.6 * tw, 0, tw * clamp(c.lt / 0.2) * fade(c, e), guard=True)


@effect('confetti', 'a burst of confetti pops and flutters down')
def fx_confetti(c, e):
    cols = [PINK, SUN, MINT, SKY, LILAC, CORAL]
    def setup():
        r = random.Random(5); return [(r.uniform(-1, 1), r.uniform(-1.5, -0.5), r.choice(cols), r.uniform(0.03, 0.05), r.uniform(0, 6.28), r.uniform(4, 12)) for _ in range(85)]
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    ox, oy = c.W / 2, c.H * 0.55; t = c.lt
    for vx, vy, col, s, ph, spin in cached(e, 'p', setup):
        x = ox + vx * c.W * 0.7 * (1 - math.exp(-t * 3)) + math.sin(t * 3 + ph) * c.W * 0.02
        y = oy + vy * c.H * 0.6 * (1 - math.exp(-t * 3)) + t * t * c.H * 0.25
        w = c.W * s; h = w * 0.55 * abs(math.cos(t * spin + ph)) + 3; a = t * spin * 0.7 + ph
        ca, sa = math.cos(a), math.sin(a)
        d.polygon([(x + ca * dx - sa * dy, y + sa * dx + ca * dy) for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))], fill=col + (255,))
    comp(c, to_np(lay), 0, 0, fade(c, e, 0.4), guard=True)
