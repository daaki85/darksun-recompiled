"""The figure catalogue: every Wake of the Ravager figure the port changes, as Ravager ships it, the
Shattered Lands figure it is matched with (where there is one) and ours, each from every side: the
standing frame and the whole walk toward the viewer, from the side and away, and the side attack, as the
figures' scripts play them. All in Ravager's colours (Tyr's palette), twice the game's size.

figure_catalogue.py OURS_OBJEX PARTY_OBJEX OUT_DIR
    OURS_OBJEX: the built OBJEX (people_dress.build, then restyle.py over it); PARTY_OBJEX: the sequel's
    OBJEX with the mod's party figures (sl_figures.py build, from the modded Shattered Lands). Writes
    OUT_DIR/img/*.png (the frames side by side), OUT_DIR/img/*.gif (the same, playing) and
    OUT_DIR/README.md. The pictures are made from the games' art: OUT_DIR belongs in the owner's private
    installation files, never in this repository."""
import json, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..')]
import sl_figures as s, people_dress as pd
from PIL import Image, ImageDraw

# side by side, each a run of the script from its slot: (title, slot)
VIEWS = (('toward', 16), ('toward walk', 17), ('side', 8), ('side walk', 9), ('away', 0), ('away walk', 1),
         ('side attack', 12))
# Shattered Lands' nearest creature for the restyled ones (as the comparison sheets)
ANALOG = {693: 158, 2394: 35, 2539: 35, 2556: 269, 2555: 278, 1753: 39, 1754: 39, 2884: 78, 2885: 78, 2887: 78,
          2888: 78, 2889: 78, 2890: 78, 2891: 78, 2554: 163, 2537: 166, 2526: 305, 3866: 305,
          **{p: 70 for p in (2850, 2852, 2853, 2854, 2855, 2858, 2859, 2860, 2861, 2863)}}
Z = 2

def runs(script, sl=False):
    """{title: [(frame, combat, ax, ay)]} for VIEWS."""
    st = s.steps(script); slots = struct.unpack_from('<36H', script, 0); out = {}
    for title, slot in VIEWS:
        v = slots[slot]
        if v == 0xFFFF or (sl and slot and not v) or v >= len(st):
            continue
        seq = []
        while v < len(st):
            x = st[v]; seq.append((x[0], bool(x[2] & 0x20), x[5], x[6])); v += 1
            if x[2] & 2 or len(seq) > 12:
                break
        out[title] = seq
    return out

def img(rows, pal):
    o = Image.new('RGBA', (len(rows[0]) if rows else 1, len(rows) or 1), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, q in enumerate(r):
            if q is not None:
                o.putpixel((x, y), pal[q] + (255,))
    return o

def strip(walk, combat, script, conv=None, sl=False):
    """[(title, [images])], each image foot-aligned by its anchor."""
    out = []
    for title, seq in runs(script, sl).items():
        ims = []
        for f, cb, ax, ay in seq:
            fr = combat if cb else walk
            if fr is None or f >= len(fr):
                continue
            rows = fr[f]
            if conv:
                rows = [[None if q is None else conv[q] for q in r] for r in rows]
            ims.append((img(rows, pd.WRPAL), ax, ay))
        if ims:
            out.append((title, ims))
    return out

def frames_rows(C, t, pic):
    c = C.get((t, pic))
    if not c:
        return None
    return [s.decode_any(c, i)[2] for i in range(s.frames(c)[0])]

def figure(pic, rows_in, path):
    """ROWS_IN [(label, [(title, [(image, ax, ay)])])] drawn as labelled rows, groups titled."""
    lab = 92; gap = 3; ggap = 12; top = 12
    lines = []
    for label, groups in rows_in:
        up = max([ay for _, ims in groups for _, ax, ay in ims] + [1]) + 2
        down = max([im.height - ay for _, ims in groups for im, ax, ay in ims] + [1]) + 2
        widths = [sum(max(im.width, 6) + gap for im, _, _ in ims) for _, ims in groups]
        lines.append((label, groups, up, down, widths))
    W = lab + max(sum(w + ggap for w in L[4]) for L in lines)
    H = sum(L[2] + L[3] + top for L in lines)
    o = Image.new('RGB', (W * Z, H * Z), (58, 58, 62)); d = ImageDraw.Draw(o); y = 0
    for label, groups, up, down, widths in lines:
        d.text((4, (y + top + up // 2) * Z), label, fill=(240, 230, 160))
        x = lab
        for (title, ims), w in zip(groups, widths):
            d.text((x * Z, y * Z + 2), title, fill=(170, 170, 170))
            cx = x
            for im, ax, ay in ims:
                big = im.resize((im.width * Z, im.height * Z), Image.NEAREST)
                o.paste(big, (cx * Z, (y + top + up - ay) * Z), big); cx += max(im.width, 6) + gap
            x += w + ggap
        y += top + up + down
        d.line([(0, y * Z - 1), (W * Z, y * Z - 1)], fill=(90, 90, 96))
    o.save(path)

def animation(rows_in, path):
    """ROWS_IN as figure(), each group playing its run in place, at 3x."""
    Z3 = 3; lab = 92; top = 12; ggap = 14
    lines = []
    for label, groups in rows_in:
        up = max([ay for _, ims in groups for _, ax, ay in ims] + [1]) + 2
        down = max([im.height - ay for _, ims in groups for im, ax, ay in ims] + [1]) + 2
        left = [max([ax for _, ax, _ in ims] + [1]) + 2 for _, ims in groups]
        right = [max([im.width - ax for im, ax, _ in ims] + [1]) + 2 for _, ims in groups]
        widths = [max(l + r, 40) for l, r in zip(left, right)]
        lines.append((label, groups, up, down, left, widths))
    W = lab + max(sum(w + ggap for w in L[5]) for L in lines); H = sum(L[2] + L[3] + top for L in lines)
    n = max(len(ims) for _, groups, *_ in lines for _, ims in groups)
    n = max(n * 2, 8)
    pics = []
    for k in range(n):
        o = Image.new('RGB', (W * Z3, H * Z3), (58, 58, 62)); d = ImageDraw.Draw(o); y = 0
        for label, groups, up, down, left, widths in lines:
            d.text((4, (y + top + up // 2) * Z3), label, fill=(240, 230, 160)); x = lab
            for (title, ims), l, w in zip(groups, left, widths):
                d.text((x * Z3, y * Z3 + 2), title, fill=(170, 170, 170))
                im, ax, ay = ims[k % len(ims)]
                big = im.resize((im.width * Z3, im.height * Z3), Image.NEAREST)
                o.paste(big, ((x + l - ax) * Z3, (y + top + up - ay) * Z3), big); x += w + ggap
            y += top + up + down
            d.line([(0, y * Z3 - 1), (W * Z3, y * Z3 - 1)], fill=(90, 90, 96))
        pics.append(o.convert('P', palette=Image.ADAPTIVE, colors=255))
    pics[0].save(path, save_all=True, append_images=pics[1:], duration=180, loop=0, optimize=True)

def main(ours_path, party_path, out):
    os.makedirs(os.path.join(out, 'img'), exist_ok=True)
    W = pd.B; _, O = s.load(ours_path); _, P = s.load(party_path)
    props = json.load(open(os.path.join(HERE, 'people-proposals.json')))
    dress = json.load(open(os.path.join(HERE, 'people-dress.json')))['dress']
    batch = json.load(open(os.path.join(HERE, 'creatures-batch1.json')))
    restyled = set(json.load(open(os.path.join(HERE, 'people-restyle.json')))['restyle'])
    from restyle import figure_walks, knight_melee
    redrawn = set(figure_walks.PICTURES) | set(knight_melee.PICTURES)
    party = {}
    for o in s.PARTY:
        party.setdefault(struct.unpack_from('<H', W[('OJFF', o)], s.PIC)[0], o)
    entries = [(int(p), v.get('wr_what', ''), v.get('confidence')) for p, v in props.items() if int(p) not in party]
    entries += [(pic, (props.get(str(pic), {}).get('wr_what') or 'party figure'), 'party') for pic in party]
    entries += [(int(p), 'creature: Shattered Lands figure swapped in', 'batch') for p in batch]
    table = []
    for pic, what, conf in sorted(entries):
        if ('SCMD', pic) not in W:
            continue
        rows = [('Ravager', strip(frames_rows(W, 'BMP ', pic), frames_rows(W, 'CBMP', pic), W[('SCMD', pic)]))]
        sl, how = None, ''
        if conf == 'batch':
            sl = batch[str(pic)]; how = 'the Shattered Lands figure swapped in'
        elif conf == 'party':
            sl = party[pic]; how = "the Shattered Lands party figure (the mod's)"
        elif str(pic) in dress and pic not in restyled and isinstance(dress[str(pic)].get('body'), int):
            sl = dress[str(pic)]['body']; how = 'dressed on this Shattered Lands body'
        elif pic in ANALOG:
            sl = ANALOG[pic]; how = 'nearest Shattered Lands creature, for comparison'
        if sl is not None and ('OJFF', sl) in pd.A:
            w, c, spic, script = pd.body(sl)
            rows.append(('Shattered Lands' + (' (ours: swapped in)' if conf == 'batch' else ''), strip(w, c, script, pd.TABLE, sl=True)))
        if pic in redrawn:
            kind = "redrawn (Codex)"
        elif str(pic) in dress and pic not in restyled:
            kind = 'dressed'
        elif conf == 'batch':
            kind = 'swapped'
        else:
            kind = 'restyled'
        if conf not in ('batch', 'party') and ('SCMD', pic) in O and O.get(('BMP ', pic)) != W.get(('BMP ', pic)):
            ours = strip(frames_rows(O, 'BMP ', pic), frames_rows(O, 'CBMP', pic), O[('SCMD', pic)])
            rows.append((f'Ours: {kind}', ours))
        elif conf == 'party':
            kind = "the Obsidian Edition's party figure"
            ours = strip(frames_rows(P, 'BMP ', pic), frames_rows(P, 'CBMP', pic), P[('SCMD', pic)])
            rows.append((f'Ours: party figure', ours))
        elif conf != 'batch':
            kind = 'not changed yet'
        name = f'{pic}.png'
        figure(pic, rows, os.path.join(out, 'img', name))
        animation(rows, os.path.join(out, 'img', f'{pic}.gif'))
        table.append((pic, what, kind, f'{how} (SL {sl})' if sl is not None else '', name))
        print(pic, kind, flush=True)
    with open(os.path.join(out, 'README.md'), 'w') as f:
        f.write('# Ravager figure catalogue\n\nEvery Wake of the Ravager figure the port changes. Each figure has an animation (every view playing, three times the game\'s size) and the same frames laid out side by side. Each has up to '
                'three rows: Ravager as shipped, the Shattered Lands figure it is matched with (where there is one), '
                'and ours (redrawn by Codex, dressed on a Shattered Lands body, restyled from Ravager\'s art, or the '
                'Shattered Lands figure swapped in). Each row shows the standing frame and the whole walk toward you, '
                'from the side and away, and the side attack, as the scripts play them, in Ravager\'s colours at '
                'twice the game\'s size. Made by `tools/proto/figure_catalogue.py` (darksun-recompiled).\n\n')
        for pic, what, kind, how, name in table:
            f.write(f'## {pic}: {what}\n\nOurs: {kind}' + (f'. Shattered Lands row: {how}' if how else '') +
                    f'.\n\n![{pic} playing](img/{pic}.gif)\n\n![{pic}](img/{name})\n\n')

if __name__ == '__main__':
    main(*sys.argv[1:4])
