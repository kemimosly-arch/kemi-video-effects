"""Extra caption styles (cute fonts, stickers, neon, marker, typewriter...), by @kemifrank__.

Each style is a small recipe: the font for normal words, the font for the key word, colours, a "treatment"
(outline, sticker, glow, box, marker, 3D shadow) and an entrance animation. They all run through the same
engine as the house style: words appear as they're spoken, the key word is picked automatically,
and the block can sit behind your head.
"""
import math, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _p(n): return os.path.join(ROOT, 'fonts', n)

PRESETS = {
    # name: desc, base font, key font, base colour, key colour, treatment, animation, case, where, size
    'bubbly':      dict(desc='Round white letters with a pink outline, key word in yellow', base='Fredoka.ttf', key='Chewy.ttf',
                        fill=(255, 255, 255), kfill=(255, 222, 89), outline=(240, 90, 160), treat='outline', anim='pop', case='lower', zone='head'),
    'sticker':     dict(desc='Every word on its own little sticker, key word on yellow', base='Sniglet.ttf', key='Sniglet.ttf',
                        fill=(40, 30, 60), kfill=(40, 30, 60), bg=(255, 255, 255), kbg=(255, 222, 89), treat='sticker', anim='pop', case='lower', zone='bottom'),
    'handwritten': dict(desc='Soft handwriting, key word in pink script', base='Caveat.ttf', key='Pacifico.ttf',
                        fill=(255, 255, 255), kfill=(255, 160, 200), treat='shadow', anim='rise', case='lower', zone='head', size=1.25),
    'candy':       dict(desc='Chunky pastel 3D letters', base='Baloo2.ttf', key='Baloo2.ttf',
                        fill=(255, 255, 255), kfill=(255, 196, 230), depth=(186, 140, 255), treat='3d', anim='bounce', case='lower', zone='head'),
    'neon':        dict(desc='Glowing neon tube letters, key word in hot pink', base='Righteous.ttf', key='Righteous.ttf',
                        fill=(225, 255, 255), kfill=(255, 230, 245), glow=(0, 220, 255), kglow=(255, 40, 170), treat='glow', anim='flicker', case='lower', zone='head'),
    'boxed':       dict(desc='White words on black rounded boxes, key word in yellow', base='BricolageGrotesque.ttf', key='BricolageGrotesque.ttf',
                        fill=(255, 255, 255), kfill=(255, 222, 89), box=(14, 14, 16), treat='box', anim='rise', case='lower', zone='bottom', size=0.85),
    'marker':      dict(desc='A yellow highlighter swipes behind the key word', base='Grandstander.ttf', key='Grandstander.ttf',
                        fill=(255, 255, 255), kfill=(30, 24, 20), mark=(255, 222, 89), outline=(30, 24, 20), treat='marker', anim='rise', case='lower', zone='bottom'),
    'typewriter':  dict(desc='Letters type out one by one with a cursor', base='SpaceMono-Bold.ttf', key='SpaceMono-Bold.ttf',
                        fill=(255, 255, 255), kfill=(255, 222, 89), box=(14, 14, 16), treat='box', anim='type', case='lower', zone='bottom', size=0.72),
    'luxe':        dict(desc='Elegant serif with a gold script key word', base='DmSerifDisplay.ttf', key='DancingScript.ttf',
                        fill=(255, 250, 240), kfill=(232, 196, 120), treat='shadow', anim='fade', case='lower', zone='head', size=1.05),
    'retro':       dict(desc='70s chunky letters with a brown drop shadow', base='Shrikhand.ttf', key='Shrikhand.ttf',
                        fill=(255, 238, 205), kfill=(255, 150, 60), depth=(110, 60, 30), treat='3d', anim='pop', case='lower', zone='head'),
    'comic':       dict(desc='Comic-book capitals with a black outline, key word in red', base='Bungee.ttf', key='Bungee.ttf',
                        fill=(255, 222, 0), kfill=(255, 60, 60), outline=(0, 0, 0), depth=(0, 0, 0), treat='outline3d', anim='shake', case='upper', zone='bottom', size=0.85),
    'soft-pill':   dict(desc='Friendly words on a soft pastel pill', base='PlaypenSans.ttf', key='PlaypenSans.ttf',
                        fill=(60, 40, 70), kfill=(220, 70, 140), pill=(255, 236, 246), treat='pill', anim='rise', case='lower', zone='bottom', size=0.85),
    'wavy':        dict(desc='Bouncy letters that gently wave', base='Gluten.ttf', key='Gluten.ttf',
                        fill=(255, 255, 255), kfill=(150, 230, 120), outline=(40, 30, 60), treat='outline', anim='wave', case='lower', zone='head'),
    'serif-mid':   dict(desc='Editorial: elegant serif words blur in at chest height, key word in big italic', base='DmSerifDisplay.ttf', key='PlayfairDisplay-Italic.ttf',
                        fill=(250, 246, 228), kfill=(250, 246, 228), treat='shadow', anim='blur', case='keep', zone='mid', size=0.82),
    'cherry':      dict(desc='Bubble letters in cherry pink with a white outline', base='CherryBombOne.ttf', key='CherryBombOne.ttf',
                        fill=(255, 90, 140), kfill=(255, 255, 255), outline=(255, 255, 255), koutline=(255, 90, 140), treat='outline', anim='pop', case='lower', zone='head'),
}

_fc = {}
def F(name, size):
    k = (name, int(size))
    if k not in _fc: _fc[k] = ImageFont.truetype(_p(name), max(8, int(size)))
    return _fc[k]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_back(x, s=1.9): x = clamp(x) - 1; return x * x * ((s + 1) * x + s) + 1


def word_img(text, p, key, S):
    """One word drawn in the style's treatment. Returns (image, baseline offset from top)."""
    fname = p['key'] if key else p['base']
    size = S * (1.3 if key and p['key'] != p['base'] else (1.12 if key else 1.0))
    f = F(fname, size)
    fill = p['kfill'] if key else p['fill']
    treat = p['treat']
    ol = max(3, int(size * 0.085))
    pad = int(size * 0.5)
    asc, desc = f.getmetrics()
    w = int(f.getlength(text)) + 2 * pad; h = asc + desc + 2 * pad
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    org = (pad, pad)
    if treat in ('outline', 'outline3d'):
        oc = (p.get('koutline') if key and p.get('koutline') else p['outline'])
        if treat == 'outline3d':
            off = max(3, int(size * 0.07))
            d.text((org[0] + off, org[1] + off), text, font=f, fill=p['depth'] + (255,), stroke_width=ol, stroke_fill=p['depth'] + (255,))
        d.text(org, text, font=f, fill=fill + (255,), stroke_width=ol, stroke_fill=oc + (255,))
    elif treat == '3d':
        off = max(3, int(size * 0.08))
        for k in range(off, 0, -1):
            d.text((org[0] + k * 0.6, org[1] + k), text, font=f, fill=p['depth'] + (255,))
        d.text(org, text, font=f, fill=fill + (255,))
    elif treat == 'glow':
        gc = p['kglow'] if key else p['glow']
        g = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text(org, text, font=f, fill=gc + (255,), stroke_width=int(size * 0.05))
        g1 = g.filter(ImageFilter.GaussianBlur(size * 0.18)); g2 = g.filter(ImageFilter.GaussianBlur(size * 0.06))
        im = Image.alpha_composite(Image.alpha_composite(Image.alpha_composite(im, g1), g1), g2)
        ImageDraw.Draw(im).text(org, text, font=f, fill=fill + (255,))
    elif treat == 'sticker':
        bg = p['kbg'] if key else p['bg']
        bb = d.textbbox(org, text, font=f)
        px, py = size * 0.22, size * 0.14
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([bb[0] - px, bb[1] - py + 4, bb[2] + px, bb[3] + py + 4], size * 0.28, fill=(0, 0, 0, 90))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(5))); d = ImageDraw.Draw(im)
        d.rounded_rectangle([bb[0] - px, bb[1] - py, bb[2] + px, bb[3] + py], size * 0.28, fill=bg + (255,))
        d.text(org, text, font=f, fill=fill + (255,))
    elif treat == 'marker':
        d.text(org, text, font=f, fill=fill + (255,), stroke_width=0 if key else ol, stroke_fill=p['outline'] + (255,))
    else:  # shadow / box / pill (box and pill backgrounds are drawn per line)
        if treat == 'shadow':
            sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).text((org[0], org[1] + size * 0.04), text, font=f, fill=(0, 0, 0, 170))
            im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(size * 0.07))); d = ImageDraw.Draw(im)
        d.text(org, text, font=f, fill=fill + (255,))
    return im, pad + asc, pad


def _case(s, p):
    s = s.strip(' ,;:"“”')
    if p['case'] == 'upper': return s.upper()
    if p['case'] == 'keep': return s
    core = s.strip('.!?')
    return s if (len(core) >= 2 and core.isupper() and core.isalpha()) else s.lower()


def balance(items, n, sp, maxw):
    """Same number of lines, but even widths: no single orphan word on the last line."""
    if n < 2 or n > 3 or len(items) < n: return None
    wid = lambda its: sum(it['w'] for it in its) + sp * max(0, len(its) - 1)
    best, cuts = None, []
    L = len(items)
    if n == 2: cuts = [(c,) for c in range(1, L)]
    else: cuts = [(a, b) for a in range(1, L - 1) for b in range(a + 1, L)]
    for c in cuts:
        bounds = (0,) + c + (L,)
        parts = [items[bounds[k]:bounds[k + 1]] for k in range(n)]
        ws = [wid(pp) for pp in parts]
        if max(ws) > maxw: continue
        # prefer even lines; lightly prefer a top line that is not longer than the next (pyramid reads better)
        score = max(ws) - min(ws) + (0.15 * (ws[0] - ws[1]) if ws[0] > ws[1] else 0)
        if best is None or score < best[0]: best = (score, parts)
    return best[1] if best else None


def layout(group, emph, W, H, p):
    land = W > H
    S = int((H * 0.072 if land else W * 0.09) * p.get('size', 1.0))
    maxw = W * (0.7 if land else 0.8)      # 0.8: clear of the Reels/TikTok side buttons
    while True:
        items = []
        for i, w in enumerate(group):
            key = emph is not None and emph[0] <= i <= emph[1]
            txt = _case(w['w'], p)
            if key: txt = txt.rstrip('.!?')
            fname = p['key'] if key else p['base']
            size = S * (1.3 if key and p['key'] != p['base'] else (1.12 if key else 1.0))
            items.append(dict(i=i, txt=txt, key=key, w=F(fname, size).getlength(txt), asc=F(fname, size).getmetrics()[0],
                              desc=F(fname, size).getmetrics()[1]))
        sp = F(p['base'], S).getlength(' ') * (1.6 if p['treat'] in ('sticker',) else 1.0)
        lines, cur, cw = [], [], 0
        for it in items:
            if cur and cw + sp + it['w'] > maxw: lines.append(cur); cur, cw = [], 0
            cw += (sp if cur else 0) + it['w']; cur.append(it)
        if cur: lines.append(cur)
        lines = balance(items, len(lines), sp, maxw) or lines
        if len(lines) <= 3 or S < 30: return lines, S, sp
        S = int(S * 0.9)


def render(t, W, H, group, emph, anchor_y, style):
    """RGBA layer for one phrase at time t. anchor_y is the bottom of the block."""
    p = PRESETS[style]
    lines, S, sp = layout(group, emph, W, H, p)
    lh = [max(it['asc'] for it in ln) + max(it['desc'] for it in ln) * 0.55 + S * 0.12 for ln in lines]
    top = max(H * (0.04 if W > H else 0.1), anchor_y - sum(lh))   # 0.1: below the app's top bar
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    y = top
    for ln, h in zip(lines, lh):
        base_y = y + max(it['asc'] for it in ln)
        tot = sum(it['w'] for it in ln) + sp * (len(ln) - 1)
        x0 = (W - tot) / 2
        shown = [it for it in ln if t >= group[it['i']]['s'] - 0.06]
        # line backgrounds for box / pill styles grow as words arrive
        if p['treat'] in ('box', 'pill') and shown:
            last = shown[-1]; xe = x0 + sum(it['w'] for it in ln[:ln.index(last) + 1]) + sp * ln.index(last)
            padx, pady = S * 0.32, S * 0.2
            col = p.get('box', p.get('pill'))
            r = S * (0.25 if p['treat'] == 'box' else 0.6)
            dl.rounded_rectangle([x0 - padx, base_y - S * 0.92 - pady, xe + padx, base_y + S * 0.28 + pady], r,
                                 fill=col + (236 if p['treat'] == 'box' else 245,))
        x = x0
        for it in ln:
            w = group[it['i']]
            lt = t - w['s'] + 0.06
            if lt < 0: x += it['w'] + sp; continue
            txt = it['txt']
            anim = p['anim']
            if anim == 'type':
                n = int(clamp(lt / max(0.05, (w['e'] - w['s']))) * len(txt) + 0.999)
                txt = txt[:max(1, n)]
            im, base_off, pad = word_img(txt, p, it['key'], S)
            sc, dy, rot, al = 1.0, 0.0, 0.0, 1.0
            if anim == 'pop': k = ease_back(lt / 0.22); sc = 0.55 + 0.45 * k; al = clamp(lt / 0.06)
            elif anim == 'rise': k = ease_out(lt / 0.2); dy = (1 - k) * S * 0.35; al = k
            elif anim == 'fade': k = ease_out(lt / 0.35); dy = (1 - k) * S * 0.15; al = k
            elif anim == 'bounce': dy = -abs(math.sin(lt * 9)) * S * 0.28 * math.exp(-lt * 5); al = clamp(lt / 0.06)
            elif anim == 'wave': dy = math.sin(t * 5 + it['i'] * 0.9) * S * 0.07; al = clamp(lt / 0.12); sc = 0.8 + 0.2 * ease_back(lt / 0.2)
            elif anim == 'shake': k = ease_back(lt / 0.18); sc = 0.6 + 0.4 * k; rot = math.sin(lt * 40) * 6 * math.exp(-lt * 8); al = clamp(lt / 0.05)
            elif anim == 'flicker':
                al = 1.0 if lt > 0.3 else (0.25 if int(lt * 30) % 3 == 1 else 1.0) * clamp(lt / 0.05)
            elif anim == 'type': al = 1.0
            elif anim == 'blur': k = ease_out(lt / 0.35); dy = (1 - k) * S * 0.15; al = k
            # the marker swipe sits behind the key word
            if p['treat'] == 'marker' and it['key']:
                k = ease_out(lt / 0.3)
                f = F(p['key'], S * 1.12)
                dl.rounded_rectangle([x - S * 0.12, base_y - S * 0.78, x - S * 0.12 + (it['w'] + S * 0.24) * k, base_y + S * 0.2],
                                     S * 0.12, fill=p['mark'] + (255,))
            if sc != 1.0 or rot:
                cx, cy = im.width / 2, base_off
                im2 = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
                if rot: im2 = im2.rotate(rot, Image.BICUBIC)
                px = x - pad + cx - im2.width / 2 + (it['w'] / 2 - (im.width / 2 - pad))
                py = base_y - base_off * sc + dy
            else:
                im2 = im; px = x - pad; py = base_y - base_off + dy
            if anim == 'blur' and lt < 0.34: im2 = im2.filter(ImageFilter.GaussianBlur(S * 0.14 * (1 - ease_out(lt / 0.35))))
            if al < 1.0:
                a = im2.split()[3].point(lambda v, al=al: int(v * al)); im2 = im2.copy(); im2.putalpha(a)
            lay.alpha_composite(im2, (int(px), int(py)))
            if anim == 'type' and it is shown[-1] and int(t * 2.4) % 2 == 0:
                cxp = x + F(p['base'], S).getlength(txt) + 4
                dl.rectangle([cxp, base_y - S * 0.8, cxp + S * 0.09, base_y + S * 0.12], fill=p['fill'] + (255,))
            x += it['w'] + sp
        y += h
    return lay
