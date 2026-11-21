"""Shattered Lands people dressed as their Wake of the Ravager counterparts, the way the Obsidian
Edition makes its half-elves (obsidian-edition/dsloader/halfelf.py) out of the human figures.

What the half-elves teach, and what this follows:
  - Colours are changed palette number for palette number, by hand: each shade of a part has its
    own new shade, light for light and dark for dark, so the shading the artist drew is kept and no
    in-between colour is invented (the earlier passes matched pixels to the nearest colour, which
    made mud and checker noise).
  - The new colours are ones the game's figures already use, so nothing reads as out of place.
  - A part is its colours, and where a colour is shared between parts, its place: the man's hair is
    his browns in the top 6 rows (below them the same browns are his face and tunic), his boots the
    bottom 7 rows; the woman's hair is a flood fill from the crown over her hair's colours.
  - Skin, outlines and everything a part list doesn't name are left alone.
  - Small things that make the look (the wristbands) get their own colours.

The data, tools/proto/people-dress.json:
  "bodies": {SL object: {"name": ..., "parts": [PART, ...]}}: each PART {"name", "colours": [SL
     palette numbers], and at most one place: "top": N (the top N filled rows of each frame),
     "bottom": N (the bottom N), "crown": true (flood fill from the top two rows), "below": N /
     "above": N (rows from the top / from the bottom, the rest of the figure)}, and "holes": [colours] (those
     colours taken too where they sit inside the part, 3 of 4 neighbours in it, and given the part's
     darkest new shade: SL's black-and-colour checker garments, which speckle once made light).
     The first part that takes a pixel has it.
  "dress": {WR picture: {"body": SL object, "note": ..., PART NAME: RAMP or {"from": "to"}}}: a RAMP
     is a list of SL palette numbers dark to light; the part's colours, sorted by lightness, are
     spread over it by rank (several old shades can share a new one, as the half-elf's do). A dict
     names each colour's new one outright. "skin" may be named as a part like any other.

    people_dress.py inspect SL_OBJECT OUT.png       a body's colours, one panel each (to write parts)
    people_dress.py numbers sl|wr N OUT.png         front, side, combat at 16x, each pixel's number on it
    people_dress.py wr WR_PICTURE OUT.png           a WR figure, its colours and their nearest SL ones
    people_dress.py sheet OUT.png [WR_PICTURE ...]  WR | SL as it is | dressed (front, side, combat)
    people_dress.py build BASE_OBJEX OUT_OBJEX [--every] (--every: the restyled ones dressed too, to compare)     the dressed figures swapped in (sl_figures.swap)
"""
import sys, os, json, struct, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import sl_figures as s
import halfelf_dress

SL_DIR, WR_DIR = '/tmp/playtest/sl_mod', '/tmp/playtest/rav'
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'people-dress.json')
A, B, SLPAL = s.games(SL_DIR, WR_DIR)
TABLE, STEADY = s.colour_table(SLPAL, s.wr_palettes(WR_DIR))
WRPAL = s.vga(s.load(os.path.join(WR_DIR, 'RGN032.GFF'))[1][('PAL ', 50)])
SL_L = [s._lab(c) for c in SLPAL]


def frames_of(C, t, p):
    c = C[(t, p)]
    return [s.decode_any(c, f)[2] for f in range(s.frames(c)[0])]


def clear0(frames):
    """FRAMES with palette 0 clear: some SL combat pictures (bodies 75 and 103) are drawn as whole
    rectangles with 0 as the background, which Ravager would show as a box."""
    return [[[None if q == 0 else q for q in r] for r in f] for f in frames]


def body(sobj):
    """(walking frames, combat frames or None, the walking picture, script) in SL numbers."""
    oj = A[('OJFF', sobj)]
    spic = struct.unpack_from('<H', oj, s.PIC)[0]
    script = A[('SCMD', oj[s.SL_SCRIPT])]
    combat = None
    if any(st[2] & s.COMBAT for st in s.steps(script)) and ('BMP ', spic + 1) in A:
        combat = clear0(frames_of(A, 'BMP ', spic + 1))
    return clear0(frames_of(A, 'BMP ', spic)), combat, spic, script


def sprite_colours():
    """The SL palette numbers its figures use (safe to dress with: they convert well)."""
    used = collections.Counter()
    for (t, i), c in A.items():
        if t == 'BMP ' and 2000 <= i < 2500 and s.kind(c) == 'rle':
            for f in range(s.frames(c)[0]):
                for r in s.decode(c, f)[2]:
                    used.update(q for q in r if q is not None)
    return used


def _fill(rows, seeds, colours):
    h, w = len(rows), len(rows[0]) if rows else 0
    seen, stack = set(), list(seeds)
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h) or rows[y][x] not in colours:
            continue
        seen.add((x, y))
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return seen


def part_map(rows, parts):
    """Rows of part names (None where no part takes the pixel). A part's "holes" (colours, usually
    254, SL's black) are taken too where they sit inside it: at least 3 of their 4 neighbours in
    the part. SL draws many garments as a checker of black and a colour, which turns to speckle
    once the colour is made light."""
    filled = [y for y, r in enumerate(rows) if any(p is not None for p in r)]
    out = [[None] * len(r) for r in rows]
    if not filled:
        return out
    top, bottom = filled[0], filled[-1]
    for part in parts:
        cs = set(part['colours'])
        if part.get('crown'):
            w = len(rows[0])
            where = _fill(rows, [(x, y) for y in range(top, top + 2) for x in range(w) if rows[y][x] in cs], cs)
            ok = lambda x, y: (x, y) in where
        elif 'top' in part:
            ok = lambda x, y, n=part['top']: y < top + n
        elif 'bottom' in part:
            ok = lambda x, y, n=part['bottom']: y > bottom - n
        elif 'below' in part:
            ok = lambda x, y, n=part['below']: y >= top + n
        elif 'above' in part:
            ok = lambda x, y, n=part['above']: y <= bottom - n
        else:
            ok = lambda x, y: True
        for y, r in enumerate(rows):
            for x, q in enumerate(r):
                if q in cs and out[y][x] is None and ok(x, y):
                    out[y][x] = part['name']
        holes = set(part.get('holes', ()))
        if holes:
            name, h, w = part['name'], len(rows), len(rows[0])
            inside = lambda x, y: 0 <= y < h and 0 <= x < w and out[y][x] == name
            add = [(x, y) for y, r in enumerate(rows) for x, q in enumerate(r)
                   if q in holes and out[y][x] is None and ok(x, y)
                   and sum(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) >= 3]
            for x, y in add:
                out[y][x] = name + '#hole'
    return out


def ramp_map(colours, ramp):
    """{colour: new} spreading COLOURS (by lightness) over RAMP (dark to light) by rank."""
    cs = sorted(colours, key=lambda q: SL_L[q][0])
    if len(cs) == 1:
        return {cs[0]: ramp[len(ramp) // 2]}
    return {q: ramp[round(i * (len(ramp) - 1) / (len(cs) - 1))] for i, q in enumerate(cs)}


def dress_frames(frames, parts, dress):
    """FRAMES with each part's colours changed as DRESS says."""
    maps = {}
    for part in parts:
        want = dress.get(part['name'])
        if want is None:
            continue
        if isinstance(want, dict):
            m = {int(k): v for k, v in want.items()}
        else:
            m = ramp_map(part['colours'], want)
        maps.setdefault(part['name'], {}).update(m)
        if part.get('holes'):
            darkest = m[min(m, key=lambda q: SL_L[q][0])]
            maps[part['name'] + '#hole'] = {q: darkest for q in part['holes']}
    out = []
    for f in frames:
        P = part_map(f, parts)
        out.append([[q if p is None or q not in maps.get(p, {}) else maps[p][q] for q, p in zip(r, pr)]
                    for r, pr in zip(f, P)])
    return out


def dressed(wpic, data):
    d = data['dress'][str(wpic)]
    if d['body'] in halfelf_dress.BODIES:  # (the Obsidian Edition's half-elves: halfelf_dress.py)
        dw, dc, walk, combat, script = halfelf_dress.dressed(d, body, SLPAL)
        spic = body(halfelf_dress.BODIES[d['body']])[2]
    else:
        walk, combat, spic, script = body(d['body'])
        parts = data['bodies'][str(d['body'])]['parts']
        dw, dc = dress_frames(walk, parts, d), (dress_frames(combat, parts, d) if combat else None)
    if d.get('tentacles'):  # (a mind flayer's face: flayer.py)
        import flayer
        dw = flayer.tentacles(dw, d['tentacles'])
        dc = flayer.tentacles(dc, d['tentacles']) if dc else None
    if d.get('weapon') == 'pick':  # (a pick in the hands: weapons_draw.py)
        import weapons_draw as wd
        groups = [[wd.armed(r, f, spic, i, False, SLPAL) for i, (r, f) in enumerate(zip(walk, dw))]]
        if dc:
            groups.append([wd.armed(r, f, spic, i, True, SLPAL) for i, (r, f) in enumerate(zip(combat, dc))])
        groups, (dx, dy) = wd.trim(groups)
        dw, dc = groups[0], (groups[1] if dc else None)
        script = wd.shift(script, dx, dy)
    return dw, dc, walk, combat, script


def load_data():
    """people-dress.json: every SL body's parts and every Ravager person's dress."""
    return json.load(open(DATA))


# ---- pictures for the eye ----
def img(f, pal, conv=None):
    from PIL import Image
    o = Image.new('RGBA', (len(f[0]), len(f)), (0, 0, 0, 0))
    for y, r in enumerate(f):
        for x, q in enumerate(r):
            if q is not None:
                o.putpixel((x, y), tuple(pal[conv[q] if conv else q]) + (255,))
    return o


def strip(ims, gap=4):
    from PIL import Image
    W = sum(i.width for i in ims) + gap * len(ims); H = max(i.height for i in ims)
    o = Image.new('RGBA', (W, H), (0, 0, 0, 0)); x = 0
    for i in ims:
        o.paste(i, (x, H - i.height), i); x += i.width + gap
    return o


def pick(w, c):
    return [w[0], w[min(2, len(w) - 1)]] + ([c[min(6, len(c) - 1)]] if c else [])


def inspect(sobj, out):
    """The body's front, side and combat frames, then one panel per colour: where it falls."""
    from PIL import Image, ImageDraw
    walk, combat, spic, _ = body(sobj)
    fs = pick(walk, combat) + walk[3:5]
    n = collections.Counter(q for f in walk + (combat or []) for r in f for q in r if q is not None)
    base = strip([img(f, SLPAL) for f in fs])
    cols = sorted(n, key=lambda q: SL_L[q][0])
    Z = 3; pw, ph = base.width * Z, base.height * Z + 14
    per = 3
    sh = Image.new('RGB', (pw * per + 8, ph * (1 + (len(cols) + per - 1) // per) + 8), (60, 60, 60))
    d = ImageDraw.Draw(sh)
    sh.paste(base.resize((pw, base.height * Z), Image.NEAREST), (4, 18), base.resize((pw, base.height * Z), Image.NEAREST))
    d.text((4, 2), f'SL object {sobj}, picture {spic}: front, side, combat, walking', fill=(255, 255, 0))
    for k, q in enumerate(cols):
        ims = []
        for f in fs:
            o = img(f, SLPAL)
            px = o.load()
            for y, r in enumerate(f):
                for x, p in enumerate(r):
                    if p is not None and p != q:
                        g = int(sum(SLPAL[p]) / 3 * 0.35 + 40)
                        px[x, y] = (g, g, g, 255)
                    elif p == q:
                        px[x, y] = (255, 0, 255, 255) if SL_L[q][0] < 25 else tuple(SLPAL[q]) + (255,)
            ims.append(o)
        im = strip(ims).resize((pw, base.height * Z), Image.NEAREST)
        x, y = 4 + (k % per) * pw, ph * (1 + k // per) + 4
        d.rectangle([x, y + 1, x + 10, y + 11], fill=tuple(SLPAL[q]))
        d.text((x + 14, y), f'{q}  x{n[q]}  L{SL_L[q][0]:.0f}' + ('  (shown magenta)' if SL_L[q][0] < 25 else ''), fill=(255, 255, 255))
        sh.paste(im, (x, y + 14), im)
    sh.save(out); print(out)


def numbers(frames, pal, out, conv=None):
    """FRAMES at 16x with each pixel's palette number written on it (SL numbers for SL frames)."""
    from PIL import Image, ImageDraw
    Z = 16; W = sum(len(f[0]) for f in frames) + 2 * len(frames); H = max(len(f) for f in frames)
    sh = Image.new('RGB', (W * Z, H * Z), (60, 60, 60)); d = ImageDraw.Draw(sh); x0 = 0
    for f in frames:
        for y, r in enumerate(f):
            for x, q in enumerate(r):
                if q is None:
                    continue
                c = tuple(pal[conv[q] if conv else q]); X, Y = (x0 + x) * Z, y * Z
                d.rectangle([X, Y, X + Z - 1, Y + Z - 1], fill=c)
                d.text((X + 1, Y + 3), str(q), fill=(0, 0, 0) if sum(c) > 330 else (255, 255, 255))
        x0 += len(f[0]) + 2
    sh.save(out); print(out)


def wr(wpic, out):
    """A WR figure (front, side, combat) and each of its colours with the nearest sprite colours."""
    from PIL import Image, ImageDraw
    w = frames_of(B, 'BMP ', wpic)
    c = frames_of(B, 'CBMP', wpic) if ('CBMP', wpic) in B else None
    fs = pick(w, c)
    base = strip([img(f, WRPAL) for f in fs])
    n = collections.Counter(q for f in w + (c or []) for r in f for q in r if q is not None)
    safe = [q for q, k in sprite_colours().items() if k > 50]
    near = lambda L: sorted(safe, key=lambda j: sum((a - b) ** 2 for a, b in zip(SL_L[j], L)))[:3]
    Z = 4
    sh = Image.new('RGB', (max(base.width * Z, 380) + 8, base.height * Z + 24 + 14 * len(n)), (60, 60, 60))
    d = ImageDraw.Draw(sh)
    big = base.resize((base.width * Z, base.height * Z), Image.NEAREST); sh.paste(big, (4, 18), big)
    d.text((4, 2), f'WR picture {wpic}', fill=(255, 255, 0))
    y = base.height * Z + 22
    for q, k in sorted(n.items(), key=lambda t: -t[1]):
        L = s._lab(WRPAL[q])
        d.rectangle([4, y + 1, 14, y + 11], fill=tuple(WRPAL[q]))
        x = 20; d.text((x, y), f'{q} x{k} L{L[0]:.0f} ->', fill=(255, 255, 255)); x += 120
        for j in near(L):
            d.rectangle([x, y + 1, x + 10, y + 11], fill=tuple(SLPAL[j])); d.text((x + 13, y), str(j), fill=(255, 255, 255)); x += 44
        y += 14
    sh.save(out); print(out)


def sheet(out, pics, data, Z=3):
    """WR | SL as it is | dressed, each front, side and combat, at Z times, one row a figure."""
    from PIL import Image, ImageDraw
    pics = pics or list(data['dress'])
    rows = []
    for wp in pics:
        dw, dc, w, c, _ = dressed(wp, data)
        wf = frames_of(B, 'BMP ', int(wp))
        wc = frames_of(B, 'CBMP', int(wp)) if ('CBMP', int(wp)) in B else None
        ims = [strip([img(f, WRPAL) for f in pick(wf, wc)]), strip([img(f, WRPAL, TABLE) for f in pick(w, c)]),
               strip([img(f, WRPAL, TABLE) for f in pick(dw, dc)])]
        ims = [i.resize((i.width * Z, i.height * Z), Image.NEAREST) for i in ims]
        dd = data['dress'][str(wp)]
        rows.append((f"WR {wp} <- SL {dd['body']}: {dd.get('note', '')}", ims))
    cw = [max(r[1][k].width for r in rows) + 16 for k in range(3)]
    H = sum(max(i.height for i in r[1]) + 20 for r in rows) + 24
    sh = Image.new('RGB', (sum(cw) + 8, H), (52, 52, 52)); d = ImageDraw.Draw(sh)
    d.text((4, 4), 'Ravager | Shattered Lands as it is | dressed      (front, side, combat)', fill=(255, 255, 255))
    y = 24
    for label, ims in rows:
        d.line([(0, y), (sh.width, y)], fill=(90, 90, 90)); d.text((4, y + 3), label[:120], fill=(255, 255, 0))
        x = 4; h = max(i.height for i in ims)
        for k, im in enumerate(ims):
            sh.paste(im, (x, y + 18 + h - im.height), im); x += cw[k]
        y += h + 20
    sh.save(out); print(out)


def build(base, out, data, every=False):
    """The dressed figures into BASE, as OUT; those in people-restyle.json are left out (restyled)."""
    skip = set() if every else set(json.load(open(os.path.join(os.path.dirname(DATA), 'people-restyle.json')))['restyle'])
    new = {}
    for wp in [w for w in data['dress'] if int(w) not in skip]:
        dw, dc, w, c, script = dressed(wp, data)
        conv = lambda fs: [[[None if q is None else TABLE[q] for q in r] for r in f] for f in fs]
        new[('BMP ', int(wp))] = s.picture(conv(dw))
        if dc:
            new[('CBMP', int(wp))] = s.picture(conv(dc))
        wr_like = B.get(('SCMD', int(wp)), b'')
        new[('SCMD', int(wp))] = s.sl_script_for_wr(script, wr_like or b'\0' * (s.SLOTS * 2))
    s.write_ranged(base, new, out); print(out, sum(k[0] == 'BMP ' for k in new), 'figures dressed')


if __name__ == '__main__':
    cmd = sys.argv[1]
    data = load_data()
    if cmd == 'inspect':
        inspect(int(sys.argv[2]), sys.argv[3])
    elif cmd == 'numbers':  # numbers sl|wr N OUT.png: front and side frames, numbered
        if sys.argv[2] == 'sl':
            w, c, _, _ = body(int(sys.argv[3])); numbers(pick(w, c), SLPAL, sys.argv[4])
        else:
            p = int(sys.argv[3]); w = frames_of(B, 'BMP ', p)
            numbers(pick(w, frames_of(B, 'CBMP', p) if ('CBMP', p) in B else None), WRPAL, sys.argv[4])
    elif cmd == 'wr':
        wr(int(sys.argv[2]), sys.argv[3])
    elif cmd == 'sheet':
        sheet(sys.argv[2], sys.argv[3:], data)
    elif cmd == 'build':
        build(sys.argv[2], sys.argv[3], data, '--every' in sys.argv)
