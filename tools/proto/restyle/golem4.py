"""python3 golem4.py OUTDIR PICTURE ...
Golems (693, 2394): toward and away walk on two stride frames ping-ponged (A B A B). Between
them go passing frames: the standing frame with the leg that swings through lifted 2 pixels and
the arms half way through their swing: A, P1, B, P2."""
import json, sys
import os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..'), os.path.join(HERE, '..', '..'), os.path.join(HERE, '..', 'own')]
import moves as L, people_dress as pd, sheet, walk6 as W6
from _rs import R
from PIL import Image
LAYOUT = {693: dict(T=(0, 3, 4), A=(1, 5, 6), S=[7, 8, 9, 10]), 2394: dict(T=(0, 4, 5), A=(1, 6, 7), S=[8, 9, 10, 11])}

def regions(f):
    rg = W6.regions(f)
    ys = [y for y, r in enumerate(f) if any(q is not None for q in r)]; top, bot = min(ys), max(ys)
    l0 = top + round(0.75 * (bot - top + 1))
    rg['legL'] = (l0, bot) + rg['legL'][2:]; rg['legR'] = (l0, bot) + rg['legR'][2:]
    return rg

def make(pic):
    d = [[[None if q < 0 else int(q) for q in r] for r in __import__('numpy').asarray(f)]
         for f in R.restyle_frames(R.frames(R.B, 'BMP ', pic), pic, False)]; anc = R.anchors(pic, False); P = L.P; lay = LAYOUT[pic]
    new, an = {}, dict(anc)
    for tag, down in (('T', 1), ('A', -1)):
        stand, a, b = lay[tag]; rg = regions(d[stand])
        for src, key in ((a, '1'), (b, '2')):
            f = d[src]; Wd = len(f[0])
            lowL, lowR = L.low(f, 0, Wd // 2 - 1), L.low(f, Wd // 2, Wd - 1)
            # toward: the forward foot is lower; the back one swings through next
            back = ('L' if lowL < lowR else 'R') if down > 0 else ('L' if lowL > lowR else 'R')
            fwd = 'R' if back == 'L' else 'L'
            y0, y1, x0, x1 = rg['leg' + back]
            o = [(y0 - 1, y1, x0, x1, 0, -2), (*rg['arm' + back][:4], 0, down), (*rg['arm' + fwd][:4], 0, -down)]
            new[tag + 'P' + key] = L.fill_holes(L.apply(d[stand], o))
            an[tag + 'P' + key] = (anc[stand][0] + P, anc[stand][1] + P)
    return d, new, an

def show(pic):
    d, new, an = make(pic); lay = LAYOUT[pic]
    fr = {i: f for i, f in enumerate(d)} | new
    T, A = lay['T'], lay['A']
    rows = [([T[1], T[2]], [A[1], A[2]], lay['S']),
            ([T[1], 'TP1', T[2], 'TP2'], [A[1], 'AP1', A[2], 'AP2'], lay['S'])]
    CW, RH = 64, 56
    def frame(k, Z):
        im = Image.new('RGBA', (CW * 3, RH * 2 + 6), (0, 0, 0, 0))
        for r, cyc in enumerate(rows):
            for c, cy in enumerate(cyc):
                key = cy[k % len(cy)]; f = pd.img(fr[key], pd.WRPAL); ax, ay = an[key]
                im.paste(f, (c * CW + 30 - ax, r * (RH + 6) + 50 - ay), f)
        return sheet.on_grey(im, Z).convert('P', palette=Image.ADAPTIVE)
    for Z, name in ((3, '3x'), (2, '2x')):
        pics = [frame(k, Z) for k in range(4)]
        pics[0].save(os.path.join(OUT, f'walk4-{pic}-{name}.gif'), save_all=True, append_images=pics[1:], duration=200, loop=0)
    return sheet.row([fr[k] for k in (T[1], 'TP1', T[2], 'TP2', A[1], 'AP1', A[2], 'AP2')], pd.WRPAL, None, 4)

if __name__ == '__main__':
    OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
    ims = [show(int(p)) for p in sys.argv[2:]]
    Wd = max(i.width for i in ims); H = sum(i.height + 6 for i in ims); o = Image.new('RGBA', (Wd, H)); y = 0
    for i in ims: o.paste(i, (0, y), i); y += i.height + 6
    sheet.on_grey(o, 3).save(os.path.join(OUT, 'golem-frames.png'))
