"""The jann drawn from scratch (rig.py, paint.py, poses.py), set beside WR's and SL's figures.

    python3 sheet.py OUTDIR      jann-sheet.png (4x: WR 2458 | ours | SL's party man, on mid-grey),
                                 jann-compare-3x.png (ours beside SL's man frame for frame, and WR's jann),
                                 jann-walk-1x.png and -2x.png (the walks at the game's size beside SL's
                                 man), jann-walk.gif (both walks playing, ours then SL's, 3x),
                                 jann-sl.png (ours in SL's own palette, before conversion),
                                 jann-frames.json (the frames, SL numbers)
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import people_dress as pd
from PIL import Image, ImageDraw
import rig, paint, poses

GREY = (128, 128, 128)
WR_PIC, SL_MAN = 2458, 300


def jann():
    """[(name, frame)] in SL palette numbers, cropped to one common box."""
    fs = [paint.frame(rig.body(p)) for _, p in poses.FRAMES]
    return list(zip([n for n, _ in poses.FRAMES], paint.crop(fs)))


def row(frames, pal, conv=None, gap=4):
    return pd.strip([pd.img(f, pal, conv) for f in frames], gap)


def on_grey(im, Z):
    im = im.resize((im.width * Z, im.height * Z), Image.NEAREST)
    o = Image.new('RGB', im.size, GREY); o.paste(im, (0, 0), im); return o


def labelled(rows, Z, title):
    """ROWS [(label, strip image)] stacked at Z times on mid-grey, each under its label."""
    ims = [(lab, im.resize((im.width * Z, im.height * Z), Image.NEAREST)) for lab, im in rows]
    W = max(i.width for _, i in ims) + 16; H = sum(i.height + 26 for _, i in ims) + 22
    sh = Image.new('RGB', (W, H), GREY); d = ImageDraw.Draw(sh)
    d.text((8, 4), title, fill=(255, 255, 255)); y = 22
    for lab, im in ims:
        d.text((8, y + 2), lab, fill=(255, 255, 0)); sh.paste(im, (8, y + 18), im); y += im.height + 26
    return sh


def walk_gif(cycles, out, Z=3, ms=160):
    """CYCLES (lists of 4 frames each) played side by side, in WR colours at Z times."""
    W = sum(max(len(f[0]) for f in c) + 6 for c in cycles); H = max(len(f) for c in cycles for f in c)
    pics = []
    for k in range(4):
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); x = 0
        for c in cycles:
            f = pd.img(c[k], pd.WRPAL, pd.TABLE); im.paste(f, (x, H - f.height), f)
            x += max(len(g[0]) for g in c) + 6
        pics.append(on_grey(im, Z).convert('P', palette=Image.ADAPTIVE))
    pics[0].save(out, save_all=True, append_images=pics[1:], duration=ms, loop=0)


def build(outdir):
    js = jann(); ours = [f for _, f in js]
    wr = pd.frames_of(pd.B, 'BMP ', WR_PIC) + pd.frames_of(pd.B, 'CBMP', WR_PIC)
    walk, _, _, _ = pd.body(SL_MAN)
    names = ', '.join(n for n, _ in js)
    sheet = labelled([
        (f'1. WR picture {WR_PIC}: its 14 walking (BMP) and 13 combat (CBMP) frames', row(wr, pd.WRPAL)),
        (f'2. Ours, drawn from scratch, in WR colours (people_dress.TABLE): {names}', row(ours, pd.WRPAL, pd.TABLE)),
        (f'3. SL party man (object {SL_MAN}), his 15 walking frames, in WR colours', row(walk, pd.WRPAL, pd.TABLE)),
    ], 4, 'The jann from scratch: Ravager | ours | Shattered Lands, at 4x')
    sheet.save(os.path.join(outdir, 'jann-sheet.png'))
    # the walks at the game's size: ours (side, toward the viewer) next to SL's man (side, toward)
    k = {n: f for n, f in js}
    side = [k[f'walk side {i}'] for i in range(1, 5)]; front = [k[f'walk front {i}'] for i in range(1, 5)]
    game = [(f'ours: standing, walk side x4, walk toward x4, attack | SL man: standing, walk side x4, toward x4',
             pd.strip([row([k['standing front']] + side + front + [k['attack side']], pd.WRPAL, pd.TABLE),
                       row([walk[0]] + walk[11:15] + walk[3:7], pd.WRPAL, pd.TABLE)], 12))]
    for Z in (1, 2):
        labelled(game, Z, f'{Z}x').save(os.path.join(outdir, f'jann-walk-{Z}x.png'))
    walk_gif([side, front, walk[11:15], walk[3:7]], os.path.join(outdir, 'jann-walk.gif'))
    pairs = [('standing front', 0), ('standing side', 2), ('walk side 1', 11), ('walk side 3', 13), ('walk front 1', 3)]
    labelled([('pairs, ours then SL man: standing front, standing side, walk side 1, walk side 3, '
               'walk toward 1; then WR 2458 front',
               pd.strip([row([k[n], walk[i]], pd.WRPAL, pd.TABLE, 2) for n, i in pairs] + [row(wr[:1], pd.WRPAL)], 10))],
             3, 'Side by side, 3x').save(os.path.join(outdir, 'jann-compare-3x.png'))
    labelled([('ours in SL palette numbers (before conversion)', row(ours, pd.SLPAL)),
              ('SL man, SL palette', row(walk, pd.SLPAL))], 4, 'SL palette').save(os.path.join(outdir, 'jann-sl.png'))
    json.dump({n: f for n, f in js}, open(os.path.join(outdir, 'jann-frames.json'), 'w'))
    print('\n'.join(os.path.join(outdir, f) for f in ('jann-sheet.png', 'jann-compare-3x.png', 'jann-walk-1x.png',
                                                      'jann-walk-2x.png', 'jann-walk.gif', 'jann-sl.png')))


if __name__ == '__main__':
    build(sys.argv[1])
