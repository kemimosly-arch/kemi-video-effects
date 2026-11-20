# Pack 5: phone and app-style cards, by @kemifrank__ (Nov 2026). Generic designs, no real brand logos.

def ui_card(w, h, r=None, fill=(255, 255, 255, 245)):
    return rrect(w, h, r if r is not None else min(w, h) * 0.18, fill)

def chin_y(c, h): return fity(c, min(c.H * 0.84, c.fy + c.fw * 2.3), h)


@effect('notifications', 'phone notifications stack in above your head, one by one')
def fx_notifications(c, e):
    items = words_of(e, 'New follower::@sarah.creates followed you|Payment received::$120 from your shop|Your reel hit 10K views::just now')[:4]
    w = c.W * 0.86; h = c.W * 0.17
    def mk(i, it):
        t, _, sub = it.partition('::'); g = Image.new('RGBA', (int(w), int(h)), (0, 0, 0, 0))
        g.alpha_composite(ui_card(w, h, h * 0.28, (250, 250, 252, 240))); d = ImageDraw.Draw(g)
        ic = h * 0.56; cols = [PINK, MINT, SKY, SUN]
        d.rounded_rectangle([h * 0.22, (h - ic) / 2, h * 0.22 + ic, (h + ic) / 2], ic * 0.24, fill=cols[i % 4] + (255,))
        d.text((h * 0.22 + ic / 2, h / 2), t[:1].upper(), font=font('uib', ic * 0.5), fill=(255, 255, 255, 255), anchor='mm')
        tx = h * 0.22 + ic + h * 0.18
        d.text((tx, h * 0.24), t, font=font('uib', h * 0.2), fill=(20, 20, 24, 255))
        d.text((tx, h * 0.53), sub, font=font('ui', h * 0.17), fill=(90, 90, 100, 255))
        d.text((w - h * 0.25, h * 0.24), 'now', font=font('ui', h * 0.14), fill=(140, 140, 150, 255), anchor='ra')
        return shadowed(g, 16, 8, 90)
    cards = cached(e, 'n', lambda: [mk(i, it) for i, it in enumerate(items)])
    top = c.H * 0.035
    for i, im in enumerate(cards):
        t0 = 0.1 + i * min(0.6, (e.d - 0.6) / max(1, len(cards)))
        k = ease_out((c.lt - t0) / 0.35)
        if k <= 0: continue
        y = top + i * h * 1.12 + im.height / 2 - 16
        place(c, im, c.W / 2, y - (1 - k) * h * 1.2, 1, 0, k * fade(c, e))


@effect('dm-bubbles', 'chat bubbles pop in like a DM conversation beside you')
def fx_dm_bubbles(c, e):
    msgs = words_of(e, 'how did you edit this?|AI did it 😅|teach me pls|link in bio')[:5]
    msgs = [m.encode('ascii', 'ignore').decode().strip() or '...' for m in msgs]
    def mk(i, m):
        f = font('uim', c.W * 0.06); tw = f.getlength(m); p = c.W * 0.045
        mine = i % 2 == 1; fill = (10, 132, 255, 255) if mine else (235, 235, 240, 255)
        b = rrect(tw + p * 2, f.size * 1.9, f.size * 0.95, fill)
        ImageDraw.Draw(b).text((p, f.size * 0.45), m, font=f, fill=(255, 255, 255, 255) if mine else (20, 20, 24, 255))
        return shadowed(b, 10, 5, 70), mine
    bs = cached(e, 'b', lambda: [mk(i, m) for i, m in enumerate(msgs)])
    total = sum(b.height * 0.85 for b, _ in bs); y = fity(c, c.fy + c.fw * 2.4, total) - total / 2
    for i, (b, mine) in enumerate(bs):
        k = pop(c, 0.1 + i * min(0.55, (e.d - 0.5) / len(bs)), 0.3)
        if k <= 0: continue
        x = c.W * 0.92 - b.width / 2 if mine else c.W * 0.08 + b.width / 2
        place(c, b, x, y + b.height * 0.425, 0.6 + 0.4 * k, 0, clamp(k * 2) * fade(c, e))
        y += b.height * 0.85


@effect('search-bar', 'a search bar types your question, with suggestions dropping down')
def fx_search_bar(c, e):
    q = e.o.get('text', 'how to grow on instagram'); w = c.W * 0.86; h = c.W * 0.14
    n = int(len(q) * clamp((c.lt - 0.2) / max(0.4, e.d * 0.45)))
    k = ease_out(c.lt / 0.3); cy = fity(c, c.H * 0.08, h)
    g = ui_card(w, h, h / 2, (255, 255, 255, 250)); d = ImageDraw.Draw(g)
    r = h * 0.18; d.ellipse([h * 0.3, h / 2 - r, h * 0.3 + 2 * r, h / 2 + r], outline=(120, 120, 130, 255), width=5)
    d.line([(h * 0.3 + 1.7 * r, h / 2 + 0.7 * r), (h * 0.3 + 2.5 * r, h / 2 + 1.5 * r)], fill=(120, 120, 130, 255), width=6)
    d.text((h * 0.85, h / 2), q[:n] + ('|' if int(c.lt * 3) % 2 == 0 and n < len(q) else ''), font=font('uim', h * 0.32), fill=(30, 30, 36, 255), anchor='lm')
    place(c, shadowed(g, 16, 8, 100), c.W / 2, cy, 0.9 + 0.1 * k, 0, k * fade(c, e))
    if n >= len(q):
        done_t = 0.2 + max(0.4, e.d * 0.45)
        for j, sug in enumerate(['for beginners', 'in 2026']):
            kk = ease_out((c.lt - done_t - 0.1 - 0.12 * j) / 0.25)
            if kk <= 0: continue
            s = ui_card(w * 0.92, h * 0.72, h * 0.2, (255, 255, 255, 230)); ImageDraw.Draw(s).text((h * 0.5, h * 0.36), q + ' ' + sug, font=font('ui', h * 0.24), fill=(90, 90, 100, 255), anchor='lm')
            place(c, s, c.W / 2, cy + h * 0.95 + j * h * 0.8, 1, 0, kk * fade(c, e))


@effect('poll', 'a poll sticker appears and the votes fill up live')
def fx_poll(c, e):
    q, a, b = (words_of(e, 'Would you try this?|YES|NOT YET') + ['YES', 'NO'])[:3]
    pct = float(e.o.get('to', 78)) / 100; w = c.W * 0.74; rowh = w * 0.15
    k = pop(c, 0, 0.35); fill = ease_out((c.lt - 0.5) / 0.9)
    g = ui_card(w, rowh * 3.4, w * 0.06, (255, 255, 255, 250)); d = ImageDraw.Draw(g)
    d.text((w / 2, rowh * 0.6), q, font=font(fk(e, 'fredoka'), rowh * 0.42), fill=(20, 20, 24, 255), anchor='mm')
    for j, (lab, p) in enumerate(((a, pct), (b, 1 - pct))):
        y = rowh * (1.2 + j * 1.05); x0 = w * 0.07; x1 = w * 0.93
        d.rounded_rectangle([x0, y, x1, y + rowh * 0.85], rowh * 0.42, fill=(240, 240, 244, 255))
        pw = (x1 - x0) * p * fill
        if pw > rowh * 0.4: d.rounded_rectangle([x0, y, x0 + pw, y + rowh * 0.85], rowh * 0.42, fill=(PINK if j == 0 else LILAC) + (255,))
        d.text((x0 + rowh * 0.4, y + rowh * 0.42), lab, font=font('uib', rowh * 0.34), fill=(20, 20, 24, 255), anchor='lm')
        d.text((x1 - rowh * 0.4, y + rowh * 0.42), f'{round(p * 100 * fill)}%', font=font('uib', rowh * 0.34), fill=(20, 20, 24, 255), anchor='rm')
    place(c, shadowed(g, 16, 8, 100), c.W / 2, chin_y(c, g.height), 0.6 + 0.4 * k, -3, clamp(k * 2) * fade(c, e))


@effect('progress-bar', 'a glossy progress bar fills up with a label and percent')
def fx_progress_bar(c, e):
    lab = e.o.get('text', 'Uploading your glow-up'); to = float(e.o.get('to', 100)); w = c.W * 0.8; h = w * 0.2
    p = ease_inout((c.lt - 0.2) / max(0.6, e.d - 0.6)) * to / 100
    g = glass(c, w, h, h * 0.3, c.W / 2, chin_y(c, h), 0.2, dark=0.3); d = ImageDraw.Draw(g)
    d.text((h * 0.3, h * 0.3), lab, font=font('uim', h * 0.2), fill=(255, 255, 255, 255), anchor='lm')
    d.text((w - h * 0.3, h * 0.3), f'{round(p * 100)}%', font=font('uib', h * 0.2), fill=(255, 255, 255, 255), anchor='rm')
    x0, x1, y0 = h * 0.3, w - h * 0.3, h * 0.58
    d.rounded_rectangle([x0, y0, x1, y0 + h * 0.18], h * 0.09, fill=(255, 255, 255, 70))
    if p > 0.02: d.rounded_rectangle([x0, y0, x0 + (x1 - x0) * p, y0 + h * 0.18], h * 0.09, fill=rgb(e.o.get('color'), MINT) + (255,))
    place(c, g, c.W / 2, chin_y(c, h), 1, 0, ramp(c, e, 0.3, 0.2))


@effect('stat-cards', 'three stat cards pop up in a row under your chin')
def fx_stat_cards(c, e):
    items = words_of(e, '10K::followers|4.9::rating|120::clients')[:3]
    cw = c.W * 0.28; ch = cw * 0.86; cols = [PINK, SUN, MINT]
    for i, it in enumerate(items):
        val, _, lab = it.partition('::')
        def mk(i=i, val=val, lab=lab):
            g = ui_card(cw, ch, cw * 0.14, (255, 255, 255, 245)); d = ImageDraw.Draw(g)
            d.rounded_rectangle([cw * 0.1, cw * 0.1, cw * 0.32, cw * 0.32], cw * 0.06, fill=cols[i] + (255,))
            d.text((cw * 0.1, ch * 0.62), val, font=font(fk(e, 'brico'), cw * 0.26), fill=(20, 20, 24, 255), anchor='lm')
            d.text((cw * 0.1, ch * 0.86), lab, font=font('uim', cw * 0.1), fill=(110, 110, 120, 255), anchor='lm')
            return shadowed(g, 12, 6, 90)
        im = cached(e, ('c', i), mk); k = pop(c, 0.1 + 0.18 * i, 0.32)
        place(c, im, c.W / 2 + (i - 1) * cw * 1.08, chin_y(c, ch) + (1 - k) * ch * 0.6, 0.7 + 0.3 * k, 0, clamp(k * 2) * fade(c, e))


@effect('calendar', 'a calendar page pops in and a date gets circled')
def fx_calendar(c, e):
    month = e.o.get('text', 'DECEMBER'); day = int(e.o.get('day', 12)); w = c.W * 0.62; h = w * 0.95
    def mk():
        g = ui_card(w, h, w * 0.08, (255, 255, 255, 250)); d = ImageDraw.Draw(g)
        d.rounded_rectangle([0, 0, w, h * 0.2], w * 0.08, fill=CORAL + (255,)); d.rectangle([0, h * 0.12, w, h * 0.2], fill=CORAL + (255,))
        d.text((w / 2, h * 0.1), month.upper(), font=font('uib', h * 0.08), fill=(255, 255, 255, 255), anchor='mm')
        cell = w / 7
        for n in range(1, 32):
            r_, col_ = divmod(n + 2, 7)
            d.text((cell * (col_ + 0.5), h * 0.27 + r_ * h * 0.13), str(n), font=font('uim', cell * 0.38), fill=(50, 50, 60, 255), anchor='mm')
        return g
    g = cached(e, 'g', mk).copy(); d = ImageDraw.Draw(g)
    r_, col_ = divmod(day + 2, 7); cell = w / 7; cx, cy = cell * (col_ + 0.5), h * 0.27 + r_ * h * 0.13
    k = ease_inout((c.lt - 0.5) / 0.4)
    if k > 0:
        pts = [(cx + cell * 0.52 * math.cos(a), cy + cell * 0.46 * math.sin(a)) for a in np.linspace(-1.2, -1.2 + 2 * math.pi * 1.1 * k, 40)]
        d.line(pts, fill=(230, 40, 60, 255), width=max(4, int(cell * 0.08)), joint='curve')
    k0 = pop(c, 0, 0.35)
    place(c, shadowed(g, 16, 8, 100), c.W / 2, chin_y(c, h * 0.85), (0.6 + 0.4 * k0) * 0.85, 3, clamp(k0 * 2) * fade(c, e))


@effect('price-tag', 'a price tag swings in on a string beside you')
def fx_price_tag(c, e):
    txt = e.o.get('text', '$49'); col = rgb(e.o.get('color'), SUN)
    def mk():
        t = text_img(txt, c.W * 0.11, fk(e, 'shrikhand'), (40, 25, 20)); w, h = int(t.width + c.W * 0.12), int(t.height * 1.1)
        g = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
        d.polygon([(0, h / 2), (h * 0.4, 0), (w, 0), (w, h), (h * 0.4, h)], fill=col + (255,))
        d.ellipse([h * 0.25, h / 2 - h * 0.08, h * 0.41, h / 2 + h * 0.08], fill=(255, 255, 255, 255))
        g.alpha_composite(t, (int(h * 0.5), int((h - t.height) / 2))); return shadowed(g, 12, 8, 110)
    im = cached(e, 't', mk); side = 1 if c.fx < c.W / 2 else -1
    swing = 18 * math.sin(c.lt * 6) * math.exp(-c.lt * 2.2); k = ease_out(c.lt / 0.3)
    x = fitx(c, c.fx + side * c.fw * 2.0, im.width * 1.25, 0.06); y = fity(c, c.fy + c.fw * 1.1, im.height) - (1 - k) * c.H * 0.3
    place(c, im, x, y, 1, -6 * side + swing * 0.5, k * fade(c, e))


@effect('before-after', 'a BEFORE / AFTER split with a sliding divider and labels')
def fx_before_after(c, e):
    p = ease_inout((c.lt - 0.2) / max(0.5, e.d - 0.7)); x = int(c.W * (1 - p))
    before = grade(c.img.copy(), e.o.get('grade', 'bw')) * 0.9
    out = c.img.copy(); out[:, :x] = before[:, :x]; c.img[:] = out
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rectangle([x - 3, 0, x + 3, c.H], fill=(255, 255, 255, 255)); d.ellipse([x - 28, c.H / 2 - 28, x + 28, c.H / 2 + 28], fill=(255, 255, 255, 255))
    a, b = (words_of(e, 'BEFORE|AFTER') + ['AFTER'])[:2]
    for lab, xx, show in ((a, c.W * 0.05, x > c.W * 0.3), (b, c.W * 0.95, x < c.W * 0.7)):
        if not show: continue
        t = text_img(lab, c.W * 0.055, 'uib', (20, 20, 24)); pill = rrect(t.width + 30, t.height, t.height / 2, (255, 255, 255, 235)); pill.alpha_composite(t, (15, 0))
        lay.alpha_composite(pill, (int(xx if xx < c.W / 2 else xx - pill.width), int(c.H * 0.06)))
    comp(c, to_np(lay), 0, 0, ramp(c, e, 0.15, 0.2))


@effect('subscribe', 'a red Subscribe button gets clicked, then a bell rings')
def fx_subscribe(c, e):
    at = float(e.o.get('at', 0.9)); clicked = c.lt >= at
    lab = 'Subscribed' if clicked else e.o.get('text', 'Subscribe')
    f = font('uib', c.W * 0.06); bw, bh = f.getlength(lab) + c.W * 0.12, c.W * 0.13
    b = rrect(bw, bh, bh / 2, ((70, 70, 78) if clicked else (230, 33, 23)) + (255,))
    ImageDraw.Draw(b).text((bw / 2, bh / 2), lab, font=f, fill=(255, 255, 255, 255), anchor='mm')
    press = 1 - 0.08 * math.sin(clamp((c.lt - at + 0.1) / 0.2) * math.pi)
    y = chin_y(c, bh); k = pop(c, 0, 0.35)
    place(c, shadowed(b, 14, 8, 110), c.W / 2, y, (0.6 + 0.4 * k) * press, 0, clamp(k * 2) * fade(c, e))
    if at - 0.6 < c.lt < at + 0.4:
        ck = ease_out((c.lt - at + 0.6) / 0.6); cur = cached(e, 'cur', lambda: cursor(c.W * 0.07))
        place(c, cur, c.W / 2 + bw * 0.3 + (1 - ck) * c.W * 0.25, y + bh * 0.3 + (1 - ck) * c.H * 0.08, 1, 0, fade(c, e))
    kb = pop(c, at + 0.35, 0.3)
    if kb > 0:
        s = int(c.W * 0.1); bell = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(bell)
        d.pieslice([s * 0.2, s * 0.12, s * 0.8, s * 0.75], 180, 360, fill=(255, 255, 255, 255)); d.rectangle([s * 0.2, s * 0.43, s * 0.8, s * 0.68], fill=(255, 255, 255, 255))
        d.rectangle([s * 0.12, s * 0.66, s * 0.88, s * 0.74], fill=(255, 255, 255, 255)); d.ellipse([s * 0.42, s * 0.74, s * 0.58, s * 0.88], fill=(255, 255, 255, 255))
        ring = 20 * math.sin((c.lt - at) * 24) * math.exp(-(c.lt - at - 0.35) * 2.5)
        place(c, shadowed(bell, 8, 4, 120), c.W / 2 + bw / 2 + s * 0.8, y, kb, ring, fade(c, e))


@effect('like-burst', 'a big heart pops, then little hearts burst and float up')
def fx_like_burst(c, e):
    col = rgb(e.o.get('color'), (255, 48, 90)); big = cached(e, 'h', lambda: shadowed(heart(c.W * 0.3, col), 16, 8, 110))
    k = pop(c, 0, 0.3); out = clamp((0.9 - c.lt) / 0.25)
    cx, cy = c.W / 2, fity(c, c.fy + c.fw * 1.8, big.height)
    if out > 0: place(c, big, cx, cy, 0.4 + 0.7 * k, 0, out * clamp(k * 3))
    def setup():
        r = random.Random(2); return [(r.uniform(-0.35, 0.35), r.uniform(0.8, 1.4), r.uniform(0.04, 0.08), r.uniform(0, 6)) for _ in range(14)]
    for dx, sp, s, ph in cached(e, 'p', setup):
        lt = c.lt - 0.35
        if lt <= 0: continue
        h = cached(e, ('s', round(s, 3)), lambda s=s: heart(c.W * s, col))
        place(c, h, cx + dx * c.W * (0.3 + lt) + math.sin(lt * 4 + ph) * c.W * 0.03, cy - lt * sp * c.H * 0.35, 1, 0, clamp(1 - lt / 1.5) * fade(c, e), guard=True)


@effect('star-rating', 'five stars fill in one after another with a rating')
def fx_star_rating(c, e):
    n = float(e.o.get('to', 5)); lab = e.o.get('text', '4.9 from 200+ reviews'); s = c.W * 0.13
    def star(fill):
        im = Image.new('RGBA', (int(s), int(s)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        pts = [(s / 2 + s * (0.48 if j % 2 == 0 else 0.2) * math.sin(j * math.pi / 5), s / 2 - s * (0.48 if j % 2 == 0 else 0.2) * math.cos(j * math.pi / 5)) for j in range(10)]
        d.polygon(pts, fill=(255, 196, 0, 255) if fill else (255, 255, 255, 120)); return im
    on, off = cached(e, 'on', lambda: shadowed(star(True), 8, 4, 100)), cached(e, 'off', lambda: star(False))
    y = chin_y(c, s * 2)
    if c.lt > 0.05: place(c, glass(c, s * 5.8, s * 2.1, s * 0.4, c.W / 2, y + s * 0.42, 0.15, dark=0.35), c.W / 2, y + s * 0.42, 1, 0, ramp(c, e, 0.2, 0.2))
    for j in range(5):
        x = c.W / 2 + (j - 2) * s * 1.05; filled = j < n and c.lt > 0.2 + 0.15 * j
        k = pop(c, 0.2 + 0.15 * j, 0.25) if filled else 0
        place(c, off, x, y, 1, 0, ramp(c, e, 0.2, 0.2))
        if filled: place(c, on, x, y, 0.5 + 0.5 * k, 0, fade(c, e))
    if c.lt > 1.0:
        t = cached(e, 't', lambda: text_img(lab, c.W * 0.05, fk(e, 'fredoka'), (255, 255, 255), shadow=6))
        place(c, t, c.W / 2, y + s * 0.95, 1, 0, clamp((c.lt - 1.0) / 0.25) * fade(c, e))


@effect('timer-ring', 'a circular countdown ring ticks down beside you')
def fx_timer_ring(c, e):
    secs = float(e.o.get('from', round(e.d))); s = c.W * 0.34
    left = max(0.0, secs - c.lt * secs / e.d)
    g = Image.new('RGBA', (int(s), int(s)), (0, 0, 0, 0)); d = ImageDraw.Draw(g); w = int(s * 0.09)
    d.ellipse([w, w, s - w, s - w], fill=(20, 20, 26, 200)); d.arc([w, w, s - w, s - w], 0, 360, fill=(255, 255, 255, 60), width=w)
    d.arc([w, w, s - w, s - w], -90, -90 + 360 * left / max(secs, 0.01), fill=rgb(e.o.get('color'), CORAL) + (255,), width=w)
    d.text((s / 2, s / 2), f'{math.ceil(left)}', font=font('uib', s * 0.32), fill=(255, 255, 255, 255), anchor='mm')
    side = 1 if c.fx < c.W / 2 else -1
    place(c, shadowed(g, 12, 6, 100), fitx(c, c.fx + side * c.fw * 2.0, s), fity(c, c.fy - c.fw * 0.3, s), 0.6 + 0.4 * pop(c, 0, 0.3), 0, fade(c, e), guard=True)


@effect('email-pop', 'a new email card slides down with a subject line')
def fx_email_pop(c, e):
    frm, _, subj = e.o.get('text', 'Brand Partnerships::Collab offer for you').partition('::'); w = c.W * 0.86; h = w * 0.3
    def mk():
        g = ui_card(w, h, h * 0.2, (255, 255, 255, 248)); d = ImageDraw.Draw(g); ic = h * 0.42
        d.ellipse([h * 0.2, h * 0.18, h * 0.2 + ic, h * 0.18 + ic], fill=SKY + (255,))
        d.rectangle([h * 0.2 + ic * 0.22, h * 0.18 + ic * 0.32, h * 0.2 + ic * 0.78, h * 0.18 + ic * 0.7], outline=(255, 255, 255, 255), width=4)
        d.line([(h * 0.2 + ic * 0.22, h * 0.18 + ic * 0.32), (h * 0.2 + ic / 2, h * 0.18 + ic * 0.52), (h * 0.2 + ic * 0.78, h * 0.18 + ic * 0.32)], fill=(255, 255, 255, 255), width=4)
        tx = h * 0.3 + ic
        d.text((tx, h * 0.22), frm, font=font('uib', h * 0.15), fill=(20, 20, 24, 255))
        d.text((tx, h * 0.47), subj, font=font('ui', h * 0.13), fill=(70, 70, 80, 255))
        d.text((tx, h * 0.7), 'Hi! We love your content and would like to...', font=font('ui', h * 0.11), fill=(140, 140, 150, 255))
        return shadowed(g, 16, 8, 100)
    im = cached(e, 'm', mk); k = ease_out(c.lt / 0.4)
    place(c, im, c.W / 2, c.H * 0.04 + im.height / 2 - (1 - k) * im.height * 1.2, 1, 0, k * fade(c, e), guard=True)


@effect('quiz-card', 'a quiz card appears and the right answer lights up green')
def fx_quiz_card(c, e):
    parts = words_of(e, 'Best time to post?|9am|6pm|midnight'); q, opts = parts[0], parts[1:4]
    right = int(e.o.get('answer', 2)) - 1; w = c.W * 0.8; rh = w * 0.13
    reveal = c.lt > max(0.8, e.d * 0.55)
    g = glass(c, w, rh * (1.6 + len(opts) * 1.15), w * 0.06, c.W / 2, chin_y(c, rh * 5), 0.2, dark=0.35); d = ImageDraw.Draw(g)
    d.text((w / 2, rh * 0.75), q, font=font(fk(e, 'fredoka'), rh * 0.45), fill=(255, 255, 255, 255), anchor='mm')
    for j, o in enumerate(opts):
        y = rh * (1.5 + j * 1.15); good = reveal and j == right
        d.rounded_rectangle([w * 0.06, y, w * 0.94, y + rh * 0.95], rh * 0.3, fill=(52, 199, 89, 255) if good else (255, 255, 255, 50))
        d.text((w * 0.11, y + rh * 0.47), f'{"ABC"[j]}   {o}', font=font('uim', rh * 0.38), fill=(255, 255, 255, 255), anchor='lm')
        if good: tick(d, w * 0.84, y + rh * 0.25, rh * 0.45)
    place(c, g, c.W / 2, chin_y(c, g.height), 0.85 + 0.15 * pop(c, 0, 0.3), 0, ramp(c, e, 0.25, 0.2))


@effect('money-rain', 'bills and coins rain down behind you')
def fx_money_rain(c, e):
    def bill(s):
        w, h = int(s * 2.1), int(s); im = rrect(w, h, s * 0.08, (120, 190, 110, 255)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([s * 0.08, s * 0.08, w - s * 0.08, h - s * 0.08], s * 0.06, outline=(70, 130, 70, 255), width=max(2, int(s * 0.05)))
        d.ellipse([w / 2 - s * 0.28, h / 2 - s * 0.28, w / 2 + s * 0.28, h / 2 + s * 0.28], outline=(70, 130, 70, 255), width=max(2, int(s * 0.05)))
        d.text((w / 2, h / 2), e.o.get('symbol', '$'), font=font('uib', s * 0.36), fill=(60, 110, 60, 255), anchor='mm'); return im
    def coin(s):
        im = Image.new('RGBA', (int(s), int(s)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse([0, 0, s - 1, s - 1], fill=(250, 200, 60, 255), outline=(200, 150, 30, 255), width=max(2, int(s * 0.08))); return im
    def setup():
        r = random.Random(6); return [(r.uniform(0.03, 0.97), r.uniform(-1.0, 0), r.uniform(0.06, 0.12), r.uniform(0.6, 1.1), r.uniform(0, 6), r.random() < 0.3) for _ in range(30)]
    for x, y0, s, sp, ph, is_coin in cached(e, 'p', setup):
        im = cached(e, ('m', round(s, 3), is_coin), lambda s=s, ic=is_coin: coin(c.W * s * 0.6) if ic else bill(c.W * s))
        place(c, im, x * c.W + math.sin(c.lt * 2 + ph) * c.W * 0.04, (y0 + c.lt * sp * 0.8) * c.H, 1, math.sin(c.lt * 3 + ph) * 35, fade(c, e) * clamp(c.lt / 0.15), behind=True)


@effect('location-pin', 'a map pin drops in with the name of a place')
def fx_location_pin(c, e):
    place_ = e.o.get('text', 'Lagos, Nigeria'); s = c.W * 0.14
    def pin():
        im = Image.new('RGBA', (int(s), int(s * 1.35)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse([0, 0, s - 1, s - 1], fill=CORAL + (255,)); d.polygon([(s * 0.15, s * 0.7), (s * 0.85, s * 0.7), (s / 2, s * 1.33)], fill=CORAL + (255,))
        d.ellipse([s * 0.32, s * 0.32, s * 0.68, s * 0.68], fill=(255, 255, 255, 255)); return shadowed(im, 10, 6, 110)
    p = cached(e, 'p', pin); side = 1 if c.fx < c.W / 2 else -1
    x = fitx(c, c.fx + side * c.fw * 1.9, s * 3); ytgt = fity(c, c.fy - c.fw * 1.3, s * 1.5)
    fall = clamp(c.lt / 0.35); y = ytgt - (1 - fall ** 2) * c.H * 0.4 - (abs(math.sin((c.lt - 0.35) * 10)) * s * 0.25 * math.exp(-(c.lt - 0.35) * 5) if c.lt > 0.35 else 0)
    place(c, p, x, y, 1, 0, fade(c, e), guard=True)
    if c.lt > 0.45:
        t = cached(e, 't', lambda: text_img(place_, c.W * 0.05, fk(e, 'fredoka'), (30, 30, 36)))
        pill = cached(e, 'pl', lambda: shadowed((lambda b: (b.alpha_composite(t, (22, 0)), b)[1])(rrect(t.width + 44, t.height, t.height / 2, (255, 255, 255, 245))), 10, 5, 90))
        place(c, pill, fitx(c, x, pill.width), ytgt + s * 0.95, 0.7 + 0.3 * pop(c, 0.45, 0.25), 0, fade(c, e), guard=True)


@effect('now-playing', 'a music player card with a moving waveform: now playing')
def fx_now_playing(c, e):
    title, _, artist = e.o.get('text', 'main character energy::your playlist').partition('::'); w = c.W * 0.82; h = w * 0.36
    g = glass(c, w, h, h * 0.2, c.W / 2, chin_y(c, h), 0.2, dark=0.35); d = ImageDraw.Draw(g)
    art = h * 0.62; d.rounded_rectangle([h * 0.18, h * 0.19, h * 0.18 + art, h * 0.19 + art], art * 0.15, fill=LILAC + (255,))
    d.text((h * 0.18 + art / 2, h * 0.19 + art / 2), '♪'.encode('ascii', 'ignore').decode() or '~', font=font('uib', art * 0.4), fill=(255, 255, 255, 255), anchor='mm')
    tx = h * 0.35 + art
    d.text((tx, h * 0.24), title, font=font('uib', h * 0.14), fill=(255, 255, 255, 255))
    d.text((tx, h * 0.45), artist, font=font('ui', h * 0.11), fill=(220, 220, 230, 255))
    bars = 22; bw = (w - tx - h * 0.2) / bars
    for j in range(bars):
        a = 0.25 + 0.75 * abs(math.sin(c.lt * 6 + j * 0.7) * math.sin(c.lt * 2.3 + j * 0.31))
        bh = h * 0.2 * a; x = tx + j * bw; yb = h * 0.82
        d.rounded_rectangle([x, yb - bh, x + bw * 0.6, yb], bw * 0.3, fill=(255, 255, 255, 230))
    place(c, g, c.W / 2, chin_y(c, h), 0.9 + 0.1 * pop(c, 0, 0.3), 0, ramp(c, e, 0.3, 0.2))


@effect('sticker-pack', 'cute stickers (heart, star, smiley, "wow") slap on around you one by one')
def fx_sticker_pack(c, e):
    def smiley(s):
        im = Image.new('RGBA', (int(s), int(s)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse([0, 0, s - 1, s - 1], fill=SUN + (255,)); d.ellipse([s * 0.3, s * 0.3, s * 0.4, s * 0.45], fill=(40, 30, 20, 255)); d.ellipse([s * 0.6, s * 0.3, s * 0.7, s * 0.45], fill=(40, 30, 20, 255))
        d.arc([s * 0.25, s * 0.3, s * 0.75, s * 0.75], 20, 160, fill=(40, 30, 20, 255), width=max(3, int(s * 0.06))); return im
    def star(s):
        im = Image.new('RGBA', (int(s), int(s)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.polygon([(s / 2 + s * (0.48 if j % 2 == 0 else 0.22) * math.sin(j * math.pi / 5), s / 2 - s * (0.48 if j % 2 == 0 else 0.22) * math.cos(j * math.pi / 5)) for j in range(10)], fill=LILAC + (255,)); return im
    def word(s): return text_img(e.o.get('text', 'wow!'), s * 0.5, 'cherry', (255, 255, 255), stroke=int(s * 0.05), stroke_fill=PINK)
    def outline(im):
        a = np.asarray(im)[..., 3]; k = max(3, im.width // 18)
        a = np.pad(a, k); dil = cv2.dilate(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
        o = Image.new('RGBA', (im.width + 2 * k, im.height + 2 * k), (255, 255, 255, 255)); o.putalpha(Image.fromarray(dil))
        o.alpha_composite(im, (k, k)); return shadowed(o, 10, 6, 110)
    s = c.W * 0.2
    st = cached(e, 's', lambda: [outline(heart(s, PINK)), outline(star(s)), outline(smiley(s)), outline(word(s * 1.4))])
    spots = [(-1.8, -1.0, -12), (1.8, -0.9, 10), (-1.7, 1.1, 8), (1.6, 1.2, -8)]
    for i, (im, (dx, dy, rot)) in enumerate(zip(st, spots)):
        k = pop(c, 0.1 + 0.22 * i, 0.25)
        if k <= 0: continue
        place(c, im, fitx(c, c.fx + dx * c.fw, im.width), fity(c, c.fy + dy * c.fw, im.height), 1.5 - 0.5 * k, rot, clamp(k * 3) * fade(c, e), guard=True)
