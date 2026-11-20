"""For the eye while drawing: each test frame's 4x shape (smooth light, before reduction) above its
1x frame, both shown big.    python3 look.py OUT.png [FRAME NAME ...]
Or ours beside SL's man at 8x:                python3 look.py --compare OUT.png [FRAME NAME ...]
Or each frame's proportions:                  python3 look.py --measure"""
import sys, os
import numpy as np
from PIL import Image
import rig, paint, poses, sheet


def smooth(p):
    b = rig.body(p)
    dep, nrm, mat, prt, ton = paint.raster(b.rows, b.mats, b.parts)
    v = paint.light(dep, nrm, ton, np.median(paint.project(b.rows)[:, 2]))
    tint = {'skin': (120, 90, 255), 'hair': (90, 70, 50), 'cloth': (230, 120, 40), 'sash': (240, 200, 60),
            'gold': (240, 200, 60), 'leather': (60, 40, 25)}
    o = np.zeros(dep.shape + (4,), np.uint8)
    for k, m in enumerate(paint.MATS):
        sel = (mat == k) & np.isfinite(dep)
        o[sel, :3] = (np.clip(v[sel], 0, 1.2)[:, None] * np.array(tint[m]) / 1.2).astype(np.uint8)
        o[sel, 3] = 255
    return Image.fromarray(o, 'RGBA')


def main(out, names):
    import people_dress as pd
    sel = [(n, p) for n, p in poses.FRAMES if not names or n in names]
    top = pd.strip([smooth(p) for _, p in sel], 16)
    frames = [paint.frame(rig.body(p)) for _, p in sel]
    low = sheet.row(frames, pd.WRPAL, pd.TABLE, 4)
    low = low.resize((low.width * paint.Z, low.height * paint.Z), Image.NEAREST)
    Z = 2
    im = Image.new('RGB', (max(top.width, low.width) * Z, (top.height + low.height + 8) * Z), sheet.GREY)
    a = top.resize((top.width * Z, top.height * Z), Image.NEAREST); im.paste(a, (0, 0), a)
    b = low.resize((low.width * Z, low.height * Z), Image.NEAREST); im.paste(b, (0, (top.height + 8) * Z), b)
    im.save(out); print(out)




def compare(out, names, sl=(0, 2, 12, 4)):
    """Our frames NAMES beside SL's man's walking frames SL, in WR colours at 8x."""
    import people_dress as pd
    frames = dict(sheet.jann())
    walk = pd.body(sheet.SL_MAN)[0]
    im = sheet.row([frames[n] for n in names] + [walk[k] for k in sl], pd.WRPAL, pd.TABLE, 6)
    sheet.on_grey(im, 8).save(out); print(out)


def proportions(name):
    """A frame's measures in 1x rows: crown (the hair's top), head top, chin, crotch (the bottom of
    the hips' cloth), sole; and the widths of the hair, shoulders and sash. To check against SL's."""
    b = rig.body(dict(poses.FRAMES)[name])
    pr = paint.project(b.rows) / paint.Z
    sel = lambda f: [i for i, (m, p) in enumerate(zip(b.mats, b.parts)) if f(m, p)]
    top = lambda ix: min(pr[i, 1] - pr[i, 3] for i in ix)
    bot = lambda ix: max(pr[i, 1] + pr[i, 3] for i in ix)
    wid = lambda ix: max(pr[i, 0] + pr[i, 3] for i in ix) - min(pr[i, 0] - pr[i, 3] for i in ix)
    hair, head = sel(lambda m, p: p == 'hair'), sel(lambda m, p: p == 'head')
    out = dict(crown=top(hair), head_top=top(head), chin=bot(head),
               crotch=bot(sel(lambda m, p: p == 'torso' and m == 'cloth')), sole=bot(sel(lambda m, p: p.startswith('leg'))),
               hair_w=wid(hair), shoulders_w=wid(sel(lambda m, p: p == 'torso' and m == 'skin')),
               sash_w=wid(sel(lambda m, p: m == 'sash')))
    return {k: round(v, 1) for k, v in out.items()}


if __name__ == '__main__':
    if sys.argv[1] == '--measure':
        for n, _ in poses.FRAMES:
            print(n, proportions(n))
    elif sys.argv[1] == '--compare':
        compare(sys.argv[2], sys.argv[3:] or ['standing front', 'standing side', 'walk side 2', 'walk front 1'])
    else:
        main(sys.argv[1], sys.argv[2:])

