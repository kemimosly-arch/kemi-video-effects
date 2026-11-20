# Effects 108+: built for wide (16:9 YouTube / landscape) frames, where the space is BESIDE you, not above.
# Loaded into fx.py's globals by the fx_more*.py loader.

def _side_x(c, e, width):
    """Pick the emptier side (away from the face) unless side=left/right is given; return the card's centre x."""
    side = str(e.o.get('side', 'auto')).lower()
    if side == 'auto': side = 'left' if c.fx > c.W * 0.5 else ('right' if c.fx < c.W * 0.42 else 'left')
    m = c.W * 0.035
    if side == 'left':
        x = m + width / 2
        x = min(x, c.fx - c.fw * 0.75 - width / 2) if c.fx - c.fw * 0.75 - width / 2 > width / 2 else x
    else:
        x = c.W - m - width / 2
        x = max(x, c.fx + c.fw * 0.75 + width / 2) if c.fx + c.fw * 0.75 + width / 2 < c.W - width / 2 else x
    return x, side


@effect('side-list', 'wide frames: a list builds beside you, one item as you say it (tools, steps, names)')
def fx_side_list(c, e):
    items = [x for x in str(e.o.get('items', e.o.get('text', 'one|two|three'))).split('|') if x]
    title = e.o.get('title', '')
    look = str(e.o.get('look', 'glass')).lower()          # glass | cream | chat
    U = min(c.W, c.H)
    ph = U * float(e.o.get('size', 0.1)); fs = ph * 0.46
    f = font('uib', fs); ft = font('uib', fs * 0.9)
    num = str(e.o.get('numbers', 'yes')).lower() in ('yes', '1', 'true')
    labels = [(f'{i + 1}  ' if num and look != 'chat' else '') + it for i, it in enumerate(items)]
    maxw = c.W * 0.34
    cw = min(maxw, max(f.getlength(l) for l in labels) + ph * 0.9)
    it_t = [float(x) for x in str(e.o.get('item_times', '')).split('|') if x] or [0.3 + 0.5 * j for j in range(len(items))]
    gap = ph * 0.28
    tot = len(items) * ph + (len(items) - 1) * gap + (ph * 0.9 if title else 0)
    y = clamp_y = max(c.H * 0.08, min(c.H * 0.5 - tot / 2, c.H * 0.86 - tot))
    x, side = _side_x(c, e, cw)
    al = fade(c, e)
    if title:
        k = ease_out(c.lt / 0.3)
        col = (255, 255, 255, 255) if look != 'cream' else (250, 246, 226, 255)
        t_im = text_img(title, fs * 0.95, 'uib', col[:3], shadow=8)
        tx = x - cw / 2 + t_im.width / 2 if side == 'left' else x + cw / 2 - t_im.width / 2
        place(c, t_im, tx, y + ph * 0.35, 1, 0, k * al)
        y += ph * 0.9
    for j, (lab, t0) in enumerate(zip(labels, it_t)):
        k = pop(c, t0, 0.32)
        if k <= 0: y += ph + gap; continue
        def mk(lab=lab, j=j):
            if look == 'chat':
                w_ = f.getlength(lab) + ph * 0.8
                mine = j % 2 == 1
                g = rrect(w_, ph, ph * 0.5, (10, 132, 255, 255) if mine else (238, 238, 243, 255))
                ImageDraw.Draw(g).text((ph * 0.4, ph / 2), lab, font=f, fill=(255, 255, 255, 255) if mine else (20, 20, 24, 255), anchor='lm')
            elif look == 'cream':
                w_ = cw
                g = rrect(w_, ph, ph * 0.5, (248, 243, 214, 250))
                ImageDraw.Draw(g).text((ph * 0.45, ph / 2), lab, font=font('dmserif', fs * 1.08), fill=(46, 70, 48, 255), anchor='lm')
            else:
                w_ = cw
                g = ui_card(w_, ph, ph * 0.32, (22, 20, 28, 215))
                d = ImageDraw.Draw(g)
                if num:
                    n_txt = f'{j + 1}'; d.text((ph * 0.42, ph / 2), n_txt, font=f, fill=(255, 196, 84, 255), anchor='lm')
                    d.text((ph * 0.42 + f.getlength('00  '), ph / 2), items[j], font=f, fill=(255, 255, 255, 255), anchor='lm')
                else:
                    d.text((ph * 0.42, ph / 2), items[j], font=f, fill=(255, 255, 255, 255), anchor='lm')
            return shadowed(g, 14, 6, 90)
        im = cached(e, f'i{j}', mk)
        if look == 'chat':
            cx = (x - cw / 2 + im.width / 2) if (j % 2 == 0) == (side == 'left') else (x + cw / 2 - im.width / 2)
        else:
            cx = x
        slide = (1 - min(1, k)) * ph * (1.2 if side == 'left' else -1.2)
        place(c, im, cx - slide, y + ph / 2, 0.85 + 0.15 * min(1, k), 0, clamp(k * 2) * al)
        y += ph + gap
