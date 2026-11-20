"""Versions of WR figures side by side: one column per OBJEX file, with a party figure for scale.

    compare_versions.py OUT.png "Label=OBJEX" ... -- WR_PICTURE ...
Each cell: front, side and combat frames of that picture in that file, in Tyr's colours at 3x; the
last column is the Obsidian Edition's human man (WR picture 25 in the party build), for scale."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import sl_figures as s
from PIL import Image, ImageDraw

PAL = s.vga(s.load('/tmp/playtest/rav/RGN032.GFF')[1][('PAL ', 50)])
PARTY = '/tmp/playtest/swap1_OBJEX.GFF'


def frames(C, t, p):
    c = C[(t, p)]
    return [s.decode_any(c, f)[2] for f in range(s.frames(c)[0])]


def cell(C, p, Z=3):
    if ('BMP ', p) not in C:
        return None
    w = frames(C, 'BMP ', p)
    fs = [w[0], w[min(2, len(w) - 1)]] + ([frames(C, 'CBMP', p)[0]] if ('CBMP', p) in C else [])
    W = sum(len(f[0]) for f in fs) + 4 * len(fs); H = max(len(f) for f in fs)
    o = Image.new('RGBA', (W, H), (0, 0, 0, 0)); x = 0
    for f in fs:
        for y, r in enumerate(f):
            for i, q in enumerate(r):
                if q is not None:
                    o.putpixel((x + i, H - len(f) + y), tuple(PAL[q]) + (255,))
        x += len(f[0]) + 4
    return o.resize((W * Z, H * Z), Image.NEAREST)


def main():
    a = sys.argv[1:]; out = a[0]; cut = a.index('--')
    cols = [(c.split('=', 1)[0], s.load(c.split('=', 1)[1])[1]) for c in a[1:cut]] + [('party, for scale', s.load(PARTY)[1])]
    pics = [int(x) for x in a[cut + 1:]]
    rows = [[cell(C, 25 if lab.startswith('party') else p) for lab, C in cols] for p in pics]
    cw = [max((r[k].width for r in rows if r[k]), default=40) + 20 for k in range(len(cols))]
    rh = [max(c.height for c in r if c) + 20 for r in rows]
    sh = Image.new('RGB', (sum(cw) + 50, sum(rh) + 22), (52, 52, 52)); d = ImageDraw.Draw(sh)
    x = 50
    for (lab, _), w in zip(cols, cw):
        d.text((x, 4), lab, fill=(255, 255, 255)); x += w
    y = 22
    for p, r, h in zip(pics, rows, rh):
        d.line([(0, y), (sh.width, y)], fill=(90, 90, 90)); d.text((4, y + 4), str(p), fill=(255, 255, 0)); x = 50
        for c, w in zip(r, cw):
            if c:
                sh.paste(c, (x, y + h - 10 - c.height), c)
            x += w
        y += h
    sh.save(out); print(out)


main()
