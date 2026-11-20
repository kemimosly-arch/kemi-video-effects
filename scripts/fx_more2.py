# Pack 4: colour, light and frame effects, by @kemifrank__ (Nov 2026). Executed inside fx.py after fx_more.py.

def bg_only(c, new, k):
    """Replace the background with `new` (float image) at strength k, keeping the person untouched."""
    m = c.m[..., None]
    c.img[:] = c.img * (1 - k * (1 - m)) + new * (k * (1 - m))


@effect('vhs', 'a retro VHS look: scanlines, colour bleed and a REC timestamp')
def fx_vhs(c, e):
    k = ramp(c, e, 0.15, 0.15)
    img = c.img
    sh = max(2, c.W // 180)
    out = img.copy(); out[..., 0] = np.roll(img[..., 0], sh, axis=1); out[..., 2] = np.roll(img[..., 2], -sh, axis=1)
    out = grade(out, 'warm') * 0.92 + 0.04
    lines = (np.arange(c.H) % 4 < 2).astype(np.float32)[:, None, None] * 0.12
    wob = int(math.sin(c.lt * 7) * c.W * 0.004)
    out = np.roll(out, wob, axis=1) * (1 - lines)
    c.img[:] = img * (1 - k) + np.clip(out, 0, 1) * k
    if int(c.lt * 2) % 2 == 0:
        rec = cached(e, 'r', lambda: text_img('● REC', c.W * 0.05, 'mono', (255, 70, 70), shadow=4))
        place(c, rec, c.W * 0.06 + rec.width / 2, c.H * 0.05, 1, 0, k)
    ts = text_img(f"PLAY  00:{int(c.t) // 60:02d}:{int(c.t) % 60:02d}", c.W * 0.04, 'mono', (240, 240, 240), shadow=4)
    place(c, ts, c.W * 0.94 - ts.width / 2, c.H * 0.95, 1, 0, k)


@effect('light-leak', 'a warm film light leak washes across the frame')
def fx_light_leak(c, e):
    xx, yy = grid(c); p = c.lt / e.d
    cx = c.W * (-0.3 + 1.6 * p); cy = c.H * (0.2 + 0.2 * math.sin(p * 3))
    d = ((xx - cx) / (c.W * 0.55)) ** 2 + ((yy - cy) / (c.H * 0.45)) ** 2
    leak = np.exp(-d * 1.6)[..., None] * np.float32(rgb(e.o.get('color'), (255, 150, 60))) / 255
    k = math.sin(math.pi * clamp(p)) * 0.9
    c.img[:] = 1 - (1 - c.img) * (1 - leak * k)


@effect('film-burn', 'an orange film-burn flash, great as a transition')
def fx_film_burn(c, e):
    xx, yy = grid(c); p = clamp(c.lt / e.d)
    r = random.Random(int(c.lt * 12))
    blobs = np.zeros((c.H, c.W), np.float32)
    for j in range(4):
        bx, by = c.W * (0.05 + 0.9 * ((j * 0.37 + p) % 1)), c.H * r.choice((r.uniform(0.0, 0.15), r.uniform(0.55, 1.0)))
        blobs += np.exp(-(((xx - bx) / (c.W * 0.35)) ** 2 + ((yy - by) / (c.H * 0.25)) ** 2) * 2)
    blobs = np.clip(blobs, 0, 1) * math.sin(math.pi * p)
    burn = np.stack([blobs, blobs ** 1.6 * 0.75, blobs ** 3 * 0.35], -1)
    c.img[:] = 1 - (1 - c.img) * (1 - np.clip(burn * 0.85, 0, 0.85))


@effect('bw-pop', 'the room turns black and white while you stay in full colour')
def fx_bw_pop(c, e):
    bg_only(c, grade(c.img.copy(), 'bw'), ramp(c, e, 0.3, 0.25))


@effect('color-room', 'your background turns one bold colour while you stay natural')
def fx_color_room(c, e):
    col = np.float32(rgb(e.o.get('color'), (255, 120, 180))) / 255
    lum = (c.img @ np.float32([0.299, 0.587, 0.114]))[..., None]
    duo = np.clip(lum * 1.15, 0, 1) * col + (1 - np.clip(lum * 1.15, 0, 1)) * col * 0.25
    bg_only(c, duo, ramp(c, e, 0.3, 0.25))


@effect('bokeh', 'soft glowing bokeh lights drift behind you')
def fx_bokeh(c, e):
    cols = [(255, 214, 140), (255, 170, 200), (200, 180, 255), (255, 240, 200)]
    def setup():
        r = random.Random(8); return [(r.uniform(0, 1), r.uniform(0, 1), r.uniform(0.04, 0.11), r.choice(cols), r.uniform(0.2, 0.6), r.uniform(0, 6)) for _ in range(26)]
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for x, y, s, col, sp, ph in cached(e, 'b', setup):
        R = c.W * s; px = x * c.W + math.sin(c.lt * sp + ph) * c.W * 0.03; py = (y - c.lt * sp * 0.04) % 1 * c.H
        d.ellipse([px - R, py - R, px + R, py + R], fill=col + (70,), outline=col + (120,), width=3)
    lay = lay.filter(ImageFilter.GaussianBlur(c.W * 0.006))
    c.img *= (1 - 0.25 * ramp(c, e, 0.3, 0.25) * (1 - c.m))[..., None]
    comp(c, to_np(lay), 0, 0, ramp(c, e, 0.4, 0.3), behind=True)


@effect('dream-glow', 'a soft, dreamy glow with lifted haze')
def fx_dream_glow(c, e):
    k = ramp(c, e, 0.35, 0.3)
    small = cv2.resize(c.img, (c.W // 4, c.H // 4)); bl = cv2.resize(cv2.GaussianBlur(small, (0, 0), 8), (c.W, c.H))
    glow = 1 - (1 - c.img) * (1 - bl * 0.55)
    glow = glow * 0.94 + np.float32([0.06, 0.04, 0.07])
    c.img[:] = c.img * (1 - k) + np.clip(glow, 0, 1) * k


@effect('strobe', 'quick white flashes on the beat')
def fx_strobe(c, e):
    n = int(e.o.get('count', 3)); p = c.lt / e.d * n
    ph = p - int(p)
    if int(p) < n and ph < 0.22: c.img[:] = c.img + (1 - c.img) * (1 - ph / 0.22) * 0.85


@effect('duotone', 'the whole frame becomes a two-colour poster look')
def fx_duotone(c, e):
    a = np.float32(rgb(e.o.get('dark'), (40, 20, 90))) / 255; b = np.float32(rgb(e.o.get('color'), (255, 150, 200))) / 255
    lum = np.clip((c.img @ np.float32([0.299, 0.587, 0.114])) * 1.1, 0, 1)[..., None]
    k = ramp(c, e, 0.25, 0.2); c.img[:] = c.img * (1 - k) + (a * (1 - lum) + b * lum) * k


@effect('portrait-blur', 'portrait mode: the background melts into soft blur')
def fx_portrait_blur(c, e):
    small = cv2.resize(c.img, (c.W // 4, c.H // 4)); bl = cv2.resize(cv2.GaussianBlur(small, (0, 0), 5), (c.W, c.H))
    bg_only(c, bl, ramp(c, e, 0.4, 0.3))


@effect('rgb-glitch', 'a digital RGB-split glitch with tearing bands')
def fx_rgb_glitch(c, e):
    r = random.Random(int(c.t * 20)); amt = (0.6 + 0.4 * math.sin(c.lt * 25)) * ramp(c, e, 0.05, 0.1)
    if r.random() < 0.35: return
    s = int(c.W * 0.02 * amt)
    out = c.img.copy(); out[..., 0] = np.roll(c.img[..., 0], s, 1); out[..., 2] = np.roll(c.img[..., 2], -s, 1)
    for _ in range(r.randint(2, 6)):
        y0 = r.randint(0, c.H - 40); h = r.randint(10, int(c.H * 0.05)); out[y0:y0 + h] = np.roll(out[y0:y0 + h], r.randint(-c.W // 8, c.W // 8), 1)
    c.img[:] = out


@effect('shake', 'a short handheld camera shake for impact (no zoom)')
def fx_shake(c, e):
    a = float(e.o.get('amount', 1.0)) * c.W * 0.012 * math.exp(-c.lt * 3) * clamp(c.lt / 0.03)
    dx, dy = a * math.sin(c.lt * 47), a * math.cos(c.lt * 39)
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    c.img = cv2.warpAffine(c.img, M, (c.W, c.H), borderMode=cv2.BORDER_REFLECT); c.m = cv2.warpAffine(c.m, M, (c.W, c.H))
    c.fx += dx; c.fy += dy


@effect('flash', 'a clean white flash, the classic cut transition')
def fx_flash(c, e):
    k = math.exp(-c.lt * 9) if c.lt > 0.03 else c.lt / 0.03
    col = np.float32(rgb(e.o.get('color'), (255, 255, 255))) / 255
    c.img[:] = c.img * (1 - k) + col * k


def frame_around(c, inset, scale_k):
    """Shrink the picture into a smaller rectangle; returns (x0, y0, w, h) of where it went."""
    s = 1 - (1 - inset) * scale_k
    w, h = int(c.W * s), int(c.H * s)
    small = cv2.resize(c.img, (w, h), interpolation=cv2.INTER_AREA)
    msmall = cv2.resize(c.m, (w, h))
    x0, y0 = (c.W - w) // 2, (c.H - h) // 2
    return small, msmall, x0, y0, w, h


@effect('polaroid', 'your shot shrinks into a tilted polaroid photo with a handwritten caption')
def fx_polaroid(c, e):
    k = ease_out(c.lt / 0.35) * fade(c, e, 0.25)
    if k <= 0.001: return
    s = 1 - 0.3 * k; w, h = int(c.W * s * 0.86), int(c.W * s * 0.86 * 1.15)
    crop_h = int(c.W * 1.15); y0 = int(clamp(c.fy - crop_h * 0.42, 0, c.H - crop_h))
    pic = cv2.resize(c.img[y0:y0 + crop_h], (w, h), interpolation=cv2.INTER_AREA)
    pad = int(w * 0.06)
    card_ = Image.new('RGBA', (w + pad * 2, h + pad * 2 + int(w * 0.22)), (252, 250, 245, 255))
    card_.paste(Image.fromarray((np.clip(pic, 0, 1) * 255).astype(np.uint8)), (pad, pad))
    ImageDraw.Draw(card_).text((card_.width / 2, h + pad + w * 0.12), e.o.get('text', 'core memory'), font=font(fk(e, 'caveat'), w * 0.1), fill=(40, 40, 50, 255), anchor='mm')
    bg = cv2.GaussianBlur(cv2.resize(c.img, (c.W // 6, c.H // 6)), (0, 0), 4)
    bgc = np.float32(rgb(e.o.get('color'), (238, 226, 210))) / 255
    c.img[:] = c.img * (1 - k) + (cv2.resize(bg, (c.W, c.H)) * 0.4 + bgc * 0.6) * k
    place(c, shadowed(card_, 20, 12, 120), c.W / 2, c.H * 0.46, 1, -5 * k)


@effect('phone-frame', 'you shrink into a phone screen, like a reel inside a reel')
def fx_phone_frame(c, e):
    k = ease_out(c.lt / 0.4) * fade(c, e, 0.25)
    if k <= 0.001: return
    small, ms, x0, y0, w, h = frame_around(c, 0.7, k)
    bgc = np.float32(rgb(e.o.get('color'), (240, 228, 214))) / 255
    out = np.empty_like(c.img); out[:] = bgc
    bez = int(c.W * 0.025 * k) + 1
    out[max(0, y0 - bez):y0 + h + bez, max(0, x0 - bez):x0 + w + bez] = 0.06
    out[y0:y0 + h, x0:x0 + w] = small
    c.img = out; c.m = np.zeros_like(c.m); c.m[y0:y0 + h, x0:x0 + w] = ms
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0 + w * 0.35, y0 + h * 0.012, x0 + w * 0.65, y0 + h * 0.035], h * 0.02, fill=(10, 10, 12, 255))
    if e.o.get('text'):
        t = text_img(e.o['text'], c.W * 0.07, fk(e, 'fredoka'), (40, 30, 30)); lay.alpha_composite(t, (int(c.W / 2 - t.width / 2), int(max(0, y0 - t.height - c.H * 0.01))))
    comp(c, to_np(lay), 0, 0, k)


@effect('window-frame', 'you appear inside a desktop app window with traffic-light buttons')
def fx_window_frame(c, e):
    k = ease_out(c.lt / 0.4) * fade(c, e, 0.25)
    if k <= 0.001: return
    small, ms, x0, y0, w, h = frame_around(c, 0.82, k)
    bgc = np.float32(rgb(e.o.get('color'), (30, 26, 40))) / 255
    out = np.empty_like(c.img); out[:] = bgc; bar = int(c.H * 0.035 * k) + 1
    out[y0 - bar:y0, x0:x0 + w] = np.float32([0.93, 0.92, 0.94]); out[y0:y0 + h, x0:x0 + w] = small
    c.img = out; c.m = np.zeros_like(c.m); c.m[y0:y0 + h, x0:x0 + w] = ms
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); r = bar * 0.22
    for j, col in enumerate(((255, 95, 87), (255, 189, 46), (40, 200, 64))):
        cx = x0 + bar * 0.6 + j * bar * 0.7; d.ellipse([cx - r, y0 - bar / 2 - r, cx + r, y0 - bar / 2 + r], fill=col + (255,))
    d.text((c.W / 2, y0 - bar / 2), e.o.get('text', 'my-edit.mp4'), font=font('uim', bar * 0.45), fill=(60, 60, 70, 255), anchor='mm')
    comp(c, to_np(lay), 0, 0, k)


@effect('film-strip', 'film-strip borders with sprocket holes roll down the sides')
def fx_film_strip(c, e):
    k = ramp(c, e, 0.3, 0.25); bw = int(c.W * 0.075)
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rectangle([0, 0, bw, c.H], fill=(12, 12, 14, 255)); d.rectangle([c.W - bw, 0, c.W, c.H], fill=(12, 12, 14, 255))
    step = bw * 1.2; off = (c.lt * c.H * 0.25) % step
    y = -step + off
    while y < c.H:
        for x in (bw * 0.25, c.W - bw * 0.75):
            d.rounded_rectangle([x, y, x + bw * 0.5, y + bw * 0.6], bw * 0.08, fill=(240, 236, 228, 255))
        y += step
    c.img[:] = c.img * (1 - 0.15 * k) + grade(c.img.copy(), 'warm') * 0.15 * k
    comp(c, to_np(lay), 0, 0, k)


@effect('cinema-bars', 'cinema bars slide in with a title, like a movie trailer')
def fx_cinema_bars(c, e):
    k = ease_inout(c.lt / 0.4) * fade(c, e, 0.3); bar = int(c.H * 0.13 * k)
    if bar > 0: c.img[:bar] *= 0.0; c.img[c.H - bar:] *= 0.0
    if e.o.get('text', 'CHAPTER ONE') and k > 0.5:
        t = cached(e, 't', lambda: text_img(e.o.get('text', 'CHAPTER ONE'), c.W * 0.06, fk(e, 'dmserif'), (240, 232, 220)))
        place(c, t, c.W / 2, c.H - bar / 2, 1, 0, clamp((k - 0.5) * 2))


@effect('grid-split', 'your shot multiplies into a 3x3 grid, then snaps back')
def fx_grid_split(c, e):
    n = int(e.o.get('count', 3)); p = clamp(c.lt / e.d)
    k = ease_inout(p / 0.25) if p < 0.5 else ease_inout((1 - p) / 0.25)
    if k <= 0.01: return
    tile = cv2.resize(c.img, (c.W // n, c.H // n), interpolation=cv2.INTER_AREA)
    looks = ('pop', 'bw', 'warm', 'cool', 'moody')
    g = np.zeros_like(c.img)
    for i in range(n):
        for j in range(n):
            t = tile if (i * n + j) == n * n // 2 else grade(tile.copy(), looks[(i * n + j) % 5])
            g[i * (c.H // n):(i + 1) * (c.H // n), j * (c.W // n):(j + 1) * (c.W // n)] = t
    c.img[:] = c.img * (1 - k) + g * k
