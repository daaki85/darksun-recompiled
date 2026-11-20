"""The before-and-after table of Wake of the Ravager's figures (docs/RAVAGER-FIGURES.md): for each WR
figure picture, its front, side and combat frames as shipped beside the same frames after the change
(Shattered Lands' party or creature swapped in, recoloured, or WR's own art restyled), one small PNG a
figure in docs/img/ravager-figures/. Reads the owner's installs and the built OBJEX files; writes only
pictures and the page.

figure_table.py WR_OBJEX PARTY_SWAP_OBJEX RECOLOUR_OBJEX RESTYLE_OBJEX PROPOSALS.json BATCH1.json OUT_DIR PAGE.md
                [SQUASH_OBJEX SQUASH_RGN]   (also the map artwork the squash lowered: tables, chairs, beds...)"""
import sys, os, json, struct
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import sl_figures as s
from PIL import Image, ImageDraw

wr_path, party_path, recol_path, rest_path, props_path, batch_path, out_dir, page = sys.argv[1:9]
squash_path, squash_rgn = (sys.argv[9], sys.argv[10]) if len(sys.argv) > 10 else ('-', None)
os.makedirs(out_dir, exist_ok=True)
_, W = s.load(wr_path)
srcs = {k: (s.load(p)[1] if p != '-' and os.path.exists(p) else None)
        for k, p in (('party', party_path), ('recolour', recol_path), ('restyle', rest_path), ('squash', squash_path))}
pal = s.vga(s.load('/tmp/playtest/rav/RGN032.GFF')[1][('PAL ', 50)])
props = json.load(open(props_path)); batch = json.load(open(batch_path))

def frames_of(C, pic):
    """front, side and a combat frame: walking frames 0 and 2 (SL's and WR's front and side
    standing frames), and the combat picture's first frame when there is one."""
    out = []
    c = C.get(('BMP ', pic))
    if c:
        n = s.frames(c)[0]
        for f in ((0, 2) if n > 2 else range(n)):
            out.append(s.decode_any(c, f))
    cb = C.get(('CBMP', pic))
    if cb:
        out.append(s.decode_any(cb, 0))
    return out

def strip(fr, height):
    ims = []
    for w, h, px in fr:
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        for y, row in enumerate(px):
            for x, q in enumerate(row):
                if q is not None:
                    im.putpixel((x, y), pal[q] + (255,))
        ims.append(im)
    W_ = sum(i.width for i in ims) + 4 * max(len(ims) - 1, 0)
    o = Image.new('RGBA', (max(W_, 1), height), (0, 0, 0, 0)); x = 0
    for i in ims:
        o.paste(i, (x, height - i.height), i); x += i.width + 4
    return o

def picture(before, after, path):
    h = max([f[1] for f in before + after] + [1])
    a, b = strip(before, h), strip(after, h)
    o = Image.new('RGB', (a.width + b.width + 30, h + 8), (36, 36, 40))
    o.paste(a, (4, 4), a); d = ImageDraw.Draw(o)
    d.polygon([(a.width + 9, h // 2 - 4), (a.width + 17, h // 2 + 4 - 4), (a.width + 9, h // 2 + 4)], fill=(230, 200, 60))
    o.paste(b, (a.width + 24, 4), b)
    o = o.resize((o.width * 2, o.height * 2), Image.NEAREST); o.save(path)

rows = []
def add(kind, pic, src_key, what, users, status, via):
    C = srcs[src_key]
    if C is None or ('BMP ', pic) not in C:
        return
    name = f'{pic}.png'
    picture(frames_of(W, pic), frames_of(C, pic), os.path.join(out_dir, name))
    rows.append((kind, pic, what, users, via, status, name))

party_names = {300: 'human man', 301: 'human woman', 302: 'dwarf man', 303: 'dwarf woman', 304: 'elf man',
               305: 'elf woman', 306: 'half-elf man', 307: 'half-elf woman', 308: 'half-giant man',
               309: 'half-giant woman', 310: 'halfling man', 311: 'halfling woman', 312: 'mul', 313: 'thri-kreen'}
for o, n in party_names.items():
    pic = struct.unpack_from('<H', W[('OJFF', o)], 12)[0]
    add('Party', pic, 'party', n, 'the party', 'done, seen in the game', "the Obsidian Edition's figure")
batch_names = {'915': 'water elemental', '2538': 'air elemental', '2540': 'fire elemental', '1881': 'earth elemental',
               '2425': 'defiler', '3893': 'shadow', '2409': 'notaku', '2420': 'templar (purple robe)'}
for p in batch:
    add('Creature', int(p), 'party', batch_names.get(p, ''), batch_names.get(p, ''), 'done', 'SL figure swapped in')
RESTYLED = set(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'people-restyle.json')))['restyle'])
for p, v in sorted(props.items(), key=lambda kv: int(kv[0])):
    users = ', '.join(sorted(set(v.get('users', []))))[:80]
    if v.get('confidence') in ('good', 'fair') and int(p) in RESTYLED:
        add('Person', int(p), 'recolour', v.get('wr_what', ''), users, 'restyled, not yet seen in the game',
            "WR's own art restyled (SL's nearest figure had the wrong shape)")
    elif v.get('confidence') in ('good', 'fair'):
        add('Person', int(p), 'recolour', v.get('wr_what', ''), users, "dressed, not yet seen in the game",
            f"SL {v.get('sl_picture')} dressed in WR's colours")
    elif v.get('confidence') == 'none':
        add('No SL equivalent', int(p), 'restyle', v.get('wr_what', ''), users, 'restyled', "WR's own art restyled")

if srcs['squash'] is not None and squash_rgn:
    S = srcs['squash']
    _, R = s.load(squash_rgn); e = R[next(k for k in R if k[0] == 'ETAB')]
    placed = {}
    for k in range(len(e) // 8):
        ob = abs(struct.unpack_from('<h', e, 8 * k + 6)[0])
        oj = W.get(('OJFF', ob))
        if oj:
            q = struct.unpack_from('<H', oj, 12)[0]; placed[q] = placed.get(q, 0) + 1
    party_pics = {r[1] for r in rows}
    for (t_, pic), c in sorted(S.items()):
        if t_ == 'BMP ' and pic in placed and pic not in party_pics and W.get(('BMP ', pic)) != c and ('SCMD', pic) not in W:
            add('Map artwork (squashed)', pic, 'squash', 'map object', f'placed {placed[pic]} times in Tyr', 'done, seen in the game',
                'lowered to two-thirds toward its base')

with open(page, 'w') as f:
    f.write('''# Wake of the Ravager's figures, before and after

Each picture shows a Wake of the Ravager figure as shipped (front, side and combat frames, left of the
arrow) and the same frames after the change (right). Everything is drawn in Ravager's own colours
(Tyr's palette), at twice the game's size. How each change is made: [FIGURES.md](FIGURES.md).

- **Party:** the Obsidian Edition's figures (Shattered Lands' party with the mod's elves and half-elves).
- **Creature:** a Shattered Lands figure of the same kind swapped in.
- **Person:** a Shattered Lands figure matched by look, dressed in Ravager's colours part by part, as the Obsidian Edition makes its half-elves (`tools/proto/people_dress.py`); where Shattered Lands' nearest figure had the wrong shape (no legs, a loincloth for a robe, the wrong size), Ravager's own art restyled instead (`tools/proto/people-restyle.json`).
- **No SL equivalent:** Ravager's own figure restyled to sit with Shattered Lands' figures.
- **Map artwork (squashed):** tables, chairs, beds and other objects on the map, lowered to two-thirds of
  their height toward their base, as Shattered Lands' steeper view shows them (walls keep their height).

The pictures are made from the owner's own copies of the games by `tools/proto/figure_table.py`.

''')
    for kind in ('Party', 'Creature', 'Person', 'No SL equivalent', 'Map artwork (squashed)'):
        rs = [r for r in rows if r[0] == kind]
        if not rs:
            continue
        f.write(f'## {kind} ({len(rs)})\n\n| WR picture | What it is | Used for | Change | Status | Before → after |\n|---|---|---|---|---|---|\n')
        for _, pic, what, users, via, status, name in rs:
            f.write(f'| {pic} | {what} | {users} | {via} | {status} | ![{pic}](img/ravager-figures/{name}) |\n')
        f.write('\n')
print(len(rows), 'rows:', {k: sum(r[0] == k for r in rows) for k in ('Party', 'Creature', 'Person', 'No SL equivalent', 'Map artwork (squashed)')})
