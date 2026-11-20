"""python3 walk6.py OUTDIR PICTURE ...   (each PICTURE restyled first: restyle_frames)
The six-beat toward/away walk for each figure: lift, halfway, stride per leg; stride frames made
from the figure's own standing frame (0 toward, 1 away) by moving its legs and arms."""
import json, sys
import os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..'), os.path.join(HERE, '..', '..'), os.path.join(HERE, '..', 'own')]
import moves as L, restyle as R, people_dress as pd, sheet
from PIL import Image
AMP = {2575: 1}                     # the lord's robe: a smaller step

def regions(f):
    ys = [y for y, r in enumerate(f) if any(q is not None for q in r)]
    top, bot = min(ys), max(ys); H = bot - top + 1
    xs = lambda y0, y1: [x for y in range(y0, y1 + 1) for x, q in enumerate(f[y]) if q is not None]
    lx = xs(bot - 3, bot); mid = (min(lx) + max(lx) + 1) // 2
    a0, a1 = top + round(0.38 * H), top + round(0.64 * H)
    ax = xs(a0, a1); minx, maxx = min(ax), max(ax)
    l0 = top + round(0.78 * H)
    return dict(legL=(l0, bot, 0, mid - 1), legR=(l0, bot, mid, len(f[0]) - 1),
                armL=(a0, a1, minx, minx + 2), armR=(a0, a1, maxx - 2, maxx))

def ops(rg, fwd, down, amp):
    """FWD 'L' or 'R': that leg forward; DOWN +1 when forward reads lower on screen (toward), -1 away."""
    back = 'R' if fwd == 'L' else 'L'
    o = []
    for name, dy in (('leg' + fwd, down * amp), ('leg' + back, -down * amp),
                     ('arm' + back, down * amp), ('arm' + fwd, -down * amp)):
        y0, y1, x0, x1 = rg[name]
        if dy < 0 and name.startswith('leg'):
            y0 -= 1                                   # (the leg that shortens: from a row higher)
        o.append((y0, y1, x0, x1, 0, dy))
    return o

def make(pic):
    d = [[[None if q < 0 else int(q) for q in r] for r in __import__('numpy').asarray(f)]
         for f in R.restyle_frames(R.frames(R.B, 'BMP ', pic), pic, False)]; anc = R.anchors(pic, False); amp = AMP.get(pic, 2); P = L.P
    new, an = {}, dict(anc)
    for stand, tag, down, lifts in ((0, 'T', 1, (4, 5)), (1, 'A', -1, (6, 7))):
        rg = regions(d[stand])
        # which leg each lift frame lifts: the side whose lowest pixel is higher
        for lift, key in zip(lifts, ('A', 'B')):
            f = d[lift]; W = len(f[0])
            lifted = 'L' if L.low(f, 0, W // 2 - 1) < L.low(f, W // 2, W - 1) else 'R'
            o = ops(rg, lifted, down, amp)
            new[tag + key] = L.fill_holes(L.apply(d[stand], o))
            new[tag + key + '1'] = L.fill_holes(L.apply(d[stand], [(a, b, c, e, dx, int(dy / 2)) for a, b, c, e, dx, dy in o]))
            for k in (tag + key, tag + key + '1'):
                an[k] = (anc[stand][0] + P, anc[stand][1] + P)
    # head level through the toward walk: the lift frames placed so their tops sit as the stand's
    top = lambda f: min(y for y, r in enumerate(f) if any(q is not None for q in r))
    fixed = dict(an)
    for k in (4, 5):
        fixed[k] = (anc[k][0], top(d[k]) - (top(d[0]) - anc[0][1]))
    return d, new, an, fixed

def show(pic):
    d, new, an, fixed = make(pic)
    fr = {i: f for i, f in enumerate(d)} | new
    rows = [([4, 0, 5, 0], [6, 1, 7, 1], [8, 9, 2, 10, 11, 2], an),
            ([4, 'TA1', 'TA', 5, 'TB1', 'TB'], [6, 'AA1', 'AA', 7, 'AB1', 'AB'], [8, 9, 2, 10, 11, 2], fixed)]
    CW, RH = 40, 42
    def frame(k, Z):
        im = Image.new('RGBA', (CW * 3, RH * 2 + 6), (0, 0, 0, 0))
        for r, (*cyc, a) in enumerate(rows):
            for c, cy in enumerate(cyc):
                key = cy[k % len(cy)]; f = pd.img(fr[key], pd.WRPAL); ax, ay = a[key]
                im.paste(f, (c * CW + 18 - ax, r * (RH + 6) + 38 - ay), f)
        return sheet.on_grey(im, Z).convert('P', palette=Image.ADAPTIVE)
    for Z, name in ((4, '4x'), (2, '2x')):
        pics = [frame(k, Z) for k in range(12)]
        pics[0].save(os.path.join(OUT, f'walk6-{pic}-{name}.gif'), save_all=True, append_images=pics[1:], duration=160, loop=0)
    json.dump({'frames': new, 'anchors': {str(k): v for k, v in fixed.items()}}, open(os.path.join(OUT, f'walk6-{pic}.json'), 'w'))
    return sheet.row([fr[k] for k in (4, 'TA1', 'TA', 5, 'TB1', 'TB', 6, 'AA1', 'AA', 7, 'AB1', 'AB')], pd.WRPAL, None, 4)

if __name__ == '__main__':
    OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
    ims = [show(int(p)) for p in sys.argv[2:]]
    W = max(i.width for i in ims); H = sum(i.height + 6 for i in ims); o = Image.new('RGBA', (W, H), (0, 0, 0, 0)); y = 0
    for i in ims: o.paste(i, (0, y), i); y += i.height + 6
    sheet.on_grey(o, 3).save(os.path.join(OUT, 'walk6-all.png'))
