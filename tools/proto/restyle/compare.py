"""python3 compare.py OUTDIR PICTURE ...: the SL party man, the dressed figure and the restyled one
(walk fix, loosened stand) side by side: standing, walking toward, sideways, fighting."""
import json, sys
import os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..'), os.path.join(HERE, '..', '..'), os.path.join(HERE, '..', 'own')]
import walk6 as W, restyle as R, people_dress as pd, sheet, sl_figures as s
from PIL import Image, ImageDraw
DATA = pd.load_data(); SWAP = {2420: 18}
def bottom(f):
    ys = [y for y, r in enumerate(f) if any(q is not None for q in r)]; xs = [x for r in f for x, q in enumerate(r) if q is not None]
    return ((min(xs) + max(xs)) // 2, max(ys))
def sl_set(walk, combat):
    return dict(stand=[walk[0]], toward=walk[3:7], side=walk[11:15], fight=(combat or [])[:6])
def build(pic, Z, out):
    man_w, man_c, _, _ = pd.body(300)
    if pic in SWAP:
        dw, dc, _, _ = pd.body(SWAP[pic])
    else:
        dw, dc, *_ = pd.dressed(str(pic), DATA)
    d, new, an, fixed, lay = W.make(pic); fr = {i: f for i, f in enumerate(d)} | new
    (t1, t2) = lay[0]
    wc = [[[None if q < 0 else int(q) for q in r] for r in __import__('numpy').asarray(f)]
          for f in R.restyle_frames(R.frames(R.B, 'CBMP', pic), pic, True)]
    rows = [('SL party man', sl_set(man_w, man_c), pd.TABLE, None),
            ('dressed (now)', sl_set(dw, dc), pd.TABLE, None),
            ('restyled + walk fix', dict(stand=[fr['ST']], toward=[fr[k] for k in (t1, 'TA1', 'TA', t2, 'TB1', 'TB')],
                                         side=[fr[k] for k in W.SIDE(pic)], fight=wc[:6]), None,
             dict(toward=[fixed[k] for k in (t1, 'TA1', 'TA', t2, 'TB1', 'TB')]))]
    CW, RH = 46, 46; cols = ('stand', 'toward', 'side', 'fight')
    frames = []
    for k in range(12):
        im = Image.new('RGBA', (CW * 4 + 70, RH * 3 + 12), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
        for r, (lab, st, conv, ancs) in enumerate(rows):
            for c, col in enumerate(cols):
                seq = st[col]
                if not seq: continue
                i = k % len(seq); f = seq[i]; img = pd.img(f, pd.WRPAL, conv)
                if ancs and col in ancs:
                    ax, ay = ancs[col][i]
                    ax, ay = ax, ay
                else:
                    ax, ay = bottom(f)
                im.paste(img, (70 + c * CW + CW // 2 - ax, r * (RH + 4) + RH - 4 - ay), img)
        frames.append(im)
    big = []
    for im in frames:
        g = sheet.on_grey(im, Z); dr = ImageDraw.Draw(g)
        for r, (lab, *_) in enumerate(rows): dr.text((4, (r * (RH + 4) + RH // 2) * Z + 10), lab, fill=(255, 255, 0))
        for c, col in enumerate(cols): dr.text(((70 + c * CW + 10) * Z, 2), col, fill=(255, 255, 0))
        big.append(g.convert('P', palette=Image.ADAPTIVE))
    big[0].save(out, save_all=True, append_images=big[1:], duration=160, loop=0)
if __name__ == '__main__':
    o = sys.argv[1]; os.makedirs(o, exist_ok=True)
    for p in sys.argv[2:]:
        for Z in (2, 3): build(int(p), Z, f'{o}/compare-{p}-{Z}x.gif')
        print('done', p)
