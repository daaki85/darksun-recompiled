#!/usr/bin/env python3
"""Shattered Lands' figures in Wake of the Ravager (Phase 8): the checks behind docs/FIGURES.md, and
a copy of the sequel's OBJEX.GFF with the party's figures taken from Shattered Lands.

    sl_figures.py report SL_DIR WR_DIR          the format checks, printed
    sl_figures.py sheet  SL_DIR WR_DIR OUT.png  the 14 party figures: SL's, SL's in WR's colours, WR's
    sl_figures.py build  SL_DIR WR_DIR OUT.GFF  WR's OBJEX.GFF with objects 300-313 drawn as SL's

Nothing of either game is in the repository: everything is read from the owner's two installs.
`sheet` needs Pillow. `build` is untested in the game (docs/FIGURES.md, "What is not known").
"""
import collections
import glob
import os
import struct
import sys

PARTY = range(300, 314)
PIC = 0x0C            # OJFF: the walking picture's number (both games)
SL_SCRIPT = 0x0E      # OJFF: SL's SCMD number (0: none); WR's script is SCMD <picture>
SLOTS = 36            # SCMD: 36 u16 slots (the step each animation starts at), then 8-byte steps
STEP = 8
COMBAT = 0x20         # step flag: a frame of the combat picture (SL: BMP n+1; WR: CBMP n)
WR_PARTY_FLAG = 0x40  # set on every step of WR's figures that have a CBMP (meaning not known)
WR_NONE = 0xFFFF      # WR's empty slot (SL's is 0, which slot 0 also uses for its step 0)


# --- GFF: chunks, and where the index says each one is (both games write the same container) ---

def index(data):
    """{(type, id): (where its u32 offset/length pair is, offset, length)}."""
    toc, = struct.unpack_from('<I', data, 12)
    p = toc + 8
    ntypes, = struct.unpack_from('<H', data, p); p += 2
    places, ranged = {}, []
    for _ in range(ntypes):
        t = data[p:p + 4].decode('latin1'); n, = struct.unpack_from('<I', data, p + 4); p += 8
        if n & 0x80000000:
            _, gi, runs = struct.unpack_from('<III', data, p); p += 12
            ids = []
            for _ in range(runs):
                first, k = struct.unpack_from('<II', data, p); p += 8
                ids += range(first, first + k)
            ranged.append((t, gi, ids))
            continue
        for _ in range(n):
            cid, off, ln = struct.unpack_from('<III', data, p)
            places[(t, cid)] = (p + 4, off, ln); p += 12
    for t, gi, ids in ranged:
        at = places[('GFFI', gi)][1] + 4
        for k, cid in enumerate(ids):
            off, ln = struct.unpack_from('<II', data, at + 8 * k)
            places[(t, cid)] = (at + 8 * k, off, ln)
    return places


def load(path):
    data = open(path, 'rb').read()
    if data[:4] != b'GFFI':
        raise SystemExit(f'{path}: not a GFF file')
    return data, {k: data[o:o + n] for k, (_, o, n) in index(data).items()}


def find(folder, name):
    for e in os.listdir(folder):
        if e.lower() == name.lower():
            return os.path.join(folder, e)
    raise SystemExit(f'no {name} in {folder}')


# --- pictures, palettes, scripts ---

def frames(chunk):
    n, = struct.unpack_from('<H', chunk, 4)
    return n, struct.unpack_from(f'<{n}I', chunk, 6)


def kind(chunk, f=0):
    """'rle' (SL's run-length frames), or WR's 'PLNR'/'PLAN' (packed bits)."""
    o = frames(chunk)[1][f]
    tag = chunk[o + 4:o + 9]
    return tag[1:].decode('latin1') if tag in (b'\xffPLNR', b'\xffPLAN') else 'rle'


def decode(chunk, f):
    """(w, h, rows of palette numbers or None) of an 'rle' frame: u16 w, u16 h, rows until FFh:
    u8 y, spans of u8 x, u8 flags (80h last), u8 pixels, u8 bytes, runs (c even: c/2+1 literal
    bytes; odd: one byte c/2+1 times)."""
    o = frames(chunk)[1][f]
    w, h = struct.unpack_from('<HH', chunk, o)
    rows = [[None] * w for _ in range(h)]
    p = o + 4
    while chunk[p] != 0xFF:
        y = chunk[p]; p += 1
        while True:
            x, fl, _, ln = chunk[p:p + 4]; p += 4
            end, run = p + ln, []
            while p < end:
                c = chunk[p]; n = (c >> 1) + 1
                if c & 1:
                    run += [chunk[p + 1]] * n; p += 2
                else:
                    run += chunk[p + 1:p + 1 + n]; p += 1 + n
            if y < h:
                rows[y][x:x + len(run)] = run[:w - x]
            if fl & 0x80:
                break
    return w, h, rows


def recolour(chunk, table):
    """CHUNK with every pixel byte of its 'rle' frames put through TABLE (the layout is unchanged:
    only literal and repeated pixel bytes are rewritten)."""
    out = bytearray(chunk)
    for o in frames(chunk)[1]:
        p = o + 4
        while out[p] != 0xFF:
            p += 1
            while True:
                fl, ln = out[p + 1], out[p + 3]; p += 4
                end = p + ln
                while p < end:
                    c = out[p]; n = (c >> 1) + 1
                    if c & 1:
                        out[p + 1] = table[out[p + 1]]; p += 2
                    else:
                        out[p + 1:p + 1 + n] = bytes(table[b] for b in out[p + 1:p + 1 + n]); p += 1 + n
                if fl & 0x80:
                    break
    return bytes(out)


def vga(chunk):
    s = lambda v: (v & 0x3F) * 255 // 63
    return [(s(chunk[i]), s(chunk[i + 1]), s(chunk[i + 2])) for i in range(0, 768, 3)]


def d2(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def wr_palettes(wr_dir):
    """Every region's map palette (each RGNxxx.GFF holds one PAL)."""
    out = {}
    for f in sorted(glob.glob(os.path.join(wr_dir, 'RGN*.GFF')) + glob.glob(os.path.join(wr_dir, 'rgn*.gff'))):
        for k, v in load(f)[1].items():
            if k[0] == 'PAL ':
                out[os.path.basename(f)] = vga(v)
    return out


def colour_table(sl_pal, wr_pals, spread=40):
    """SL palette number -> WR palette number: the nearest of WR's colours that stay within SPREAD
    of each other in every region (and outside 0-15 and 240-248, the cycled and system colours)."""
    pals = list(wr_pals.values())
    ok = [j for j in range(16, 256) if not 240 <= j <= 248
          and max(d2(p[j], pals[0][j]) for p in pals) <= spread * spread]
    return [min(ok, key=lambda j: d2(sl_pal[i], pals[0][j])) for i in range(256)], ok


def steps(script):
    return [script[SLOTS * 2 + STEP * k:SLOTS * 2 + STEP * (k + 1)] for k in range((len(script) - SLOTS * 2) // STEP)]


def sl_script_for_wr(script, wr_like):
    """SL's SCMD in WR's form: empty slots FFFFh (SL's 0; slot 0's own 0 kept), and WR's flag 40h
    on every step when WR's own script for the figure has it on all of its steps (WR_LIKE)."""
    slots = list(struct.unpack_from(f'<{SLOTS}H', script, 0))
    slots = [s if (k == 0 or s) else WR_NONE for k, s in enumerate(slots)]
    out = bytearray(struct.pack(f'<{SLOTS}H', *slots))
    flag = WR_PARTY_FLAG if all(s[2] & WR_PARTY_FLAG for s in steps(wr_like)) else 0
    for s in steps(script):
        s = bytearray(s); s[2] |= flag; out += s
    return bytes(out)


# --- the three commands ---

def games(sl_dir, wr_dir):
    _, A = load(find(sl_dir, 'SEGOBJEX.GFF'))
    _, B = load(find(wr_dir, 'OBJEX.GFF'))
    sl_pal = vga(load(find(sl_dir, 'GPLDATA.GFF'))[1][('PAL ', 1)])
    return A, B, sl_pal


def report(sl_dir, wr_dir):
    A, B, sl_pal = games(sl_dir, wr_dir)
    for name, C in (('SL SEGOBJEX', A), ('WR OBJEX', B)):
        types = collections.Counter(t for t, _ in C)
        enc = collections.Counter((t, kind(c, f)) for (t, _), c in C.items() if t in ('BMP ', 'CBMP')
                                  for f in range(frames(c)[0]))
        print(f'{name}: chunks {dict(types)}')
        print(f'  frame encodings {dict(enc)}')
    cb = [i for t, i in B if t == 'CBMP']
    print(f'WR: {sum(("BMP ", i) in B for i in cb)}/{len(cb)} CBMP have a BMP of the same number, '
          f'{sum(("SCMD", i) in B for i in cb)}/{len(cb)} an SCMD of it')
    plain = combat = bad = 0
    for i in cb:
        nb, nc = frames(B[('BMP ', i)])[0], frames(B[('CBMP', i)])[0]
        for s in steps(B[('SCMD', i)]):
            if s[2] & COMBAT:
                combat += 1; bad += s[0] >= nc
            else:
                plain += 1; bad += s[0] >= nb
    print(f'WR: steps without flag 20h name a BMP frame ({plain}), with it a CBMP frame ({combat}); out of range {bad}')
    print('party (object: SL walking picture/frames + combat picture/frames, script | WR picture BMP/CBMP frames)')
    for o in PARTY:
        a, b = A[('OJFF', o)], B[('OJFF', o)]
        pa, pb = struct.unpack_from('<H', a, PIC)[0], struct.unpack_from('<H', b, PIC)[0]
        print(f'  {o}: SL {pa}/{frames(A[("BMP ", pa)])[0]} + {pa + 1}/{frames(A[("BMP ", pa + 1)])[0]}, SCMD {a[SL_SCRIPT]}'
              f' | WR {pb}: {frames(B[("BMP ", pb)])[0]} / {frames(B[("CBMP", pb)])[0]}')
    wp = wr_palettes(wr_dir)
    groups = collections.Counter(tuple(map(tuple, p)) for p in wp.values())
    table, ok = colour_table(sl_pal, wp)
    used = collections.Counter()
    for o in PARTY:
        pa = struct.unpack_from('<H', A[('OJFF', o)], PIC)[0]
        for pic in (pa, pa + 1):
            c = A[('BMP ', pic)]
            for f in range(frames(c)[0]):
                used.update(p for row in decode(c, f)[2] for p in row if p is not None)
    pal0 = list(wp.values())[0]
    err = sum(d2(sl_pal[i], pal0[table[i]]) ** .5 * n for i, n in used.items()) / sum(used.values())
    print(f'WR: {len(wp)} region palettes, {len(groups)} different; {len(ok)} colours steady enough to draw with')
    print(f'SL party colours into them: mean RGB distance {err:.1f} (0-441), worst '
          f'{max(d2(sl_pal[i], pal0[table[i]]) ** .5 for i in used):.0f}')


def sheet(sl_dir, wr_dir, out):
    from PIL import Image
    A, B, sl_pal = games(sl_dir, wr_dir)
    wp = wr_palettes(wr_dir)
    table, _ = colour_table(sl_pal, wp)
    pal0 = list(wp.values())[0]
    W = 60
    img = Image.new('RGB', (W * len(PARTY), 3 * 70), (40, 40, 40))
    for k, o in enumerate(PARTY):
        pa = struct.unpack_from('<H', A[('OJFF', o)], PIC)[0]
        pb = struct.unpack_from('<H', B[('OJFF', o)], PIC)[0]
        rows = ((A[('BMP ', pa)], sl_pal, None), (A[('BMP ', pa)], pal0, table), (B[('BMP ', pb)], pal0, None))
        for r, (c, pal, t) in enumerate(rows):
            w, h, px = decode(c, 0)
            for y, row in enumerate(px):
                for x, p in enumerate(row):
                    if p is not None:
                        img.putpixel((k * W + W // 2 - w // 2 + x, r * 70 + 65 - h + y), pal[t[p] if t else p])
    img.resize((img.width * 2, img.height * 2), Image.NEAREST).save(out)
    print(out)


def build(sl_dir, wr_dir, out):
    """WR's OBJEX.GFF with the party's BMP, CBMP and SCMD chunks replaced by SL's (colours
    remapped, script in WR's form), the new chunks appended and the index pointed at them."""
    A, B, sl_pal = games(sl_dir, wr_dir)
    path = find(wr_dir, 'OBJEX.GFF')
    data = bytearray(open(path, 'rb').read())
    places = index(bytes(data))
    table, _ = colour_table(sl_pal, wr_palettes(wr_dir))
    done = set()
    for o in PARTY:
        a = A[('OJFF', o)]
        pa, pb = struct.unpack_from('<H', a, PIC)[0], struct.unpack_from('<H', B[('OJFF', o)], PIC)[0]
        if pb in done:
            continue
        done.add(pb)
        new = {('BMP ', pb): recolour(A[('BMP ', pa)], table),
               ('CBMP', pb): recolour(A[('BMP ', pa + 1)], table),
               ('SCMD', pb): sl_script_for_wr(A[('SCMD', a[SL_SCRIPT])], B[('SCMD', pb)])}
        for key, chunk in new.items():
            if key[0] != 'SCMD':  # a picture chunk starts with its own length
                chunk = struct.pack('<I', len(chunk)) + chunk[4:]
            at = places[key][0]
            struct.pack_into('<II', data, at, len(data), len(chunk))
            data += chunk
    open(out, 'wb').write(data)
    check = load(out)[1]
    for o in PARTY:
        pb = struct.unpack_from('<H', check[('OJFF', o)], PIC)[0]
        assert decode(check[('BMP ', pb)], 0) and decode(check[('CBMP', pb)], 0)
    print(f'{out}: {len(done)} figures replaced, {len(data) - os.path.getsize(path)} bytes appended')


if __name__ == '__main__':
    cmds = {'report': (report, 2), 'sheet': (sheet, 3), 'build': (build, 3)}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds or len(sys.argv) != 2 + cmds[sys.argv[1]][1]:
        raise SystemExit(__doc__)
    cmds[sys.argv[1]][0](*sys.argv[2:])
