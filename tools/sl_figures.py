#!/usr/bin/env python3
"""Shattered Lands' figures in Wake of the Ravager (Phase 8): the checks behind docs/FIGURES.md, and
a copy of the sequel's OBJEX.GFF with the party's figures taken from Shattered Lands.

    sl_figures.py report SL_DIR WR_DIR          the format checks, printed
    sl_figures.py sheet  SL_DIR WR_DIR OUT.png  the 14 party figures: SL's, SL's in WR's colours, WR's
    sl_figures.py build  SL_DIR WR_DIR OUT.GFF  WR's OBJEX.GFF with objects 300-313 drawn as SL's
    sl_figures.py build-ui SL_DIR WR_DIR OUT.GFF  WR's RESOURCE.GFF with SL's interface pictures and icons
    sl_figures.py regrade SL_DIR WR_DIR RGNxxx STRENGTH OUT.GFF  a WR region's colours moved toward SL's
    sl_figures.py squash WR_DIR RGNxxx FACTOR OUT_DIR [furniture]  a WR region's objects lowered (furniture: only
                                                    tables, chairs and other map artwork; walls kept)

Nothing of either game is in the repository: everything is read from the owner's two installs.
`sheet` needs Pillow. `build` was seen working in the game (docs/FIGURES.md, "Seen in the game").
"""
import collections
import glob
import math
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
# RESOURCE.GFF's interface pictures (BMP) that are the same drawing in both games, at the same size and
# frame count (checked by eye, 2026-11-20). Left out: 11000 and 20029 (SL's are cut away on one side, the
# screens laid out otherwise), 13005 (WR's has a second frame), 20125 (another picture), 12000 and
# 20000-20013 (other sizes: WR's portrait frame and creation figures are larger), 20126-20134 (others).
UI_PICTURES = (10000, 10001, 10002, 10003, 10004, 13000, 13001, 13002, 13003, 13004, 13007, 13008, 14000,
               15000, 15001, 15002, 17000, 17001, 17002, 20028, 20047, *range(20048, 20059), 20075, 20079,
               20080, 20083, 20084, 20085, 20086, 20087, 20088, 20104, 20105, 20106, 20107)
# An icon is matched by look, not number (WR renumbered part of its spell list): each WR icon takes the
# SL icon of the same size and frame count whose pixels are nearest, if the mean RGB distance (a clear
# pixel against a drawn one counting 200) is at most ICON_NEAR: 36.5 by eye (36.2 the same drawing,
# 36.7 another symbol).
ICON_NEAR = 36.5
# Icons kept as WR's whatever the match: the MORE and scroll buttons (12100-12102) are drawn on WR's own
# talk boxes, whose stone is neutral grey; SL's dimmed frames, from its bluer stone, showed there as a
# lavender ghost of the button (seen in the game, 2026-11-20).
ICON_KEEP = (12100, 12101, 12102)


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


def _codes(data, bits):
    acc = n = 0
    for byte in data:
        acc, n = (acc << 8) | byte, n + 8
        while n >= bits:
            n -= bits
            yield (acc >> n) & ((1 << bits) - 1)


def decode_any(chunk, f):
    """(w, h, rows) of a frame in any of the three formats. WR's: u16 w, h, FFh, 'PLNR' or 'PLAN',
    u8 bits a pixel, a colour map of 2**bits palette numbers, then the pixels as codes of those bits,
    highest first. PLAN: one code a pixel. PLNR: code 0 escapes (0 then 0: a pixel of map entry 0; 0
    then k: the last pixel k + 2 more times). Palette number 0 is clear."""
    k = kind(chunk, f)
    if k == 'rle':
        return decode(chunk, f)
    o = frames(chunk)[1][f]
    w, h = struct.unpack_from('<HH', chunk, o)
    bits = chunk[o + 9]
    cmap = chunk[o + 10:o + 10 + (1 << bits)]
    data = chunk[o + 10 + (1 << bits):]
    px = []
    if bits == 0:
        px = [0] * (w * h)
    elif k == 'PLAN':
        it = _codes(data, bits)
        px = [next(it, 0) for _ in range(w * h)]
    else:
        it, last = _codes(data, bits), 0
        for code in it:
            if len(px) >= w * h:
                break
            if code:
                px.append(code); last = code
                continue
            count = next(it, 0)
            if count:
                px += [last] * (count + 2)
            else:
                px.append(0); last = 0
    px = (px + [0] * (w * h))[:w * h]
    cols = [cmap[p] or None for p in px]
    return w, h, [cols[y * w:(y + 1) * w] for y in range(h)]


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


def append_chunks(path, new, out):
    """PATH's GFF with each chunk of NEW ({(type, id): bytes}, all already in the file) appended at
    the end and the index pointed at it; a picture chunk's leading length set to its own."""
    data = bytearray(open(path, 'rb').read())
    places = index(bytes(data))
    for key, chunk in new.items():
        if key[0] in ('BMP ', 'CBMP', 'ICON', 'TILE'):
            chunk = struct.pack('<I', len(chunk)) + chunk[4:]
        struct.pack_into('<II', data, places[key][0], len(data), len(chunk))
        data += chunk
    open(out, 'wb').write(data)
    return len(data) - os.path.getsize(path)


def ui_colour_table(sl_res, wr_dir, wr_res):
    """SL's RESOURCE palette (PAL 1000) -> the nearest of WR's colours that are the same in its
    RESOURCE palette and in every region's (the interface is drawn over the map in the region's)."""
    sp, wp = vga(sl_res[('PAL ', 1000)]), vga(wr_res[('PAL ', 1000)])
    regions = list(wr_palettes(wr_dir).values())
    ok = [j for j in range(16, 256) if not 240 <= j <= 248 and all(d2(p[j], wp[j]) < 16 for p in regions)]
    return [min(ok, key=lambda j: d2(sp[i], wp[j])) for i in range(256)], sp, wp


def icon_pairs(sl_res, wr_res, sp, wp):
    """{WR icon: (SL icon, distance)} for every WR icon with an SL icon within ICON_NEAR (ICON_NEAR)."""
    def pixels(chunk, pal):
        out = []
        for f in range(frames(chunk)[0]):
            w, h, rows = decode_any(chunk, f)
            out.append(((w, h), [pal[p] if p is not None else None for row in rows for p in row]))
        return out
    sl = {i: pixels(c, sp) for (t, i), c in sl_res.items() if t == 'ICON'}
    by_shape = collections.defaultdict(list)
    for i, px in sl.items():
        by_shape[tuple(s for s, _ in px)].append(i)
    pairs = {}
    for (t, i), c in sorted(wr_res.items()):
        if t != 'ICON':
            continue
        wpx = pixels(c, wp)
        best = None
        for j in by_shape.get(tuple(s for s, _ in wpx), ()):
            tot = n = 0
            for (_, a), (_, b) in zip(sl[j], wpx):
                for u, v in zip(a, b):
                    if (u is None) != (v is None):
                        tot += 200; n += 1
                    elif u is not None:
                        tot += d2(u, v) ** .5; n += 1
            dist = tot / max(n, 1)
            if best is None or dist < best[1]:
                best = (j, dist)
        if best and best[1] <= ICON_NEAR and i not in ICON_KEEP:
            pairs[i] = best
    return pairs


# --- a region's colours (phase 2) ---

def _lab(c):
    def lin(u):
        u /= 255
        return ((u + 0.055) / 1.055) ** 2.4 if u > 0.04045 else u / 12.92
    r, g, b = (lin(x) for x in c)
    X = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    Z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda u: u ** (1 / 3) if u > 0.008856 else 7.787 * u + 16 / 116
    fx, fy, fz = f(X), f(Y), f(Z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _rgb(lab):
    l, a, b = lab
    fy = (l + 16) / 116; fx = fy + a / 500; fz = fy - b / 200
    inv = lambda u: u ** 3 if u ** 3 > 0.008856 else (u - 16 / 116) / 7.787
    X, Y, Z = inv(fx) * 0.95047, inv(fy), inv(fz) * 1.08883
    lin = (3.2406 * X - 1.5372 * Y - 0.4986 * Z, -0.9689 * X + 1.8758 * Y + 0.0415 * Z,
           0.0557 * X - 0.2040 * Y + 1.0570 * Z)
    g = lambda u: 255 * (1.055 * max(u, 0) ** (1 / 2.4) - 0.055 if u > 0.0031308 else 12.92 * u)
    return tuple(max(0, min(255, round(g(u)))) for u in lin)


def _spread(weights):
    """Lab mean and deviation of {RGB: weight}."""
    n = sum(weights.values())
    labs = [(_lab(c), k) for c, k in weights.items()]
    mu = [sum(l[j] * k for l, k in labs) / n for j in range(3)]
    sd = [(sum((l[j] - mu[j]) ** 2 * k for l, k in labs) / n) ** .5 for j in range(3)]
    return mu, sd


def _ground(chunks, pal, weights):
    """Add a region's ground pixels to WEIGHTS ({RGB: count}), each tile counted as often as the
    region's map (SL's RMAP, WR's MAP) uses it."""
    m = next(v for k, v in chunks.items() if k[0] in ('MAP ', 'RMAP'))
    used = collections.Counter(m)
    for (t, i), c in chunks.items():
        if t == 'TILE' and used.get(i):
            for row in decode_any(c, 0)[2]:
                for p in row:
                    if p is not None:
                        weights[pal[p]] += used[i]


def sl_ground(sl_dir):
    """Shattered Lands' ground colours over all its regions: region N is drawn in GPLDATA's PAL N
    (the slave pens, RGN29, in PAL 41: checked against a screenshot of the game)."""
    _, gpl = load(find(sl_dir, 'GPLDATA.GFF'))
    weights = collections.Counter()
    for f in sorted(glob.glob(os.path.join(sl_dir, 'RGN*.GFF')) + glob.glob(os.path.join(sl_dir, 'rgn*.gff'))):
        n = int(os.path.basename(f)[3:5], 16)
        if ('PAL ', n) in gpl:
            _ground(load(f)[1], vga(gpl[('PAL ', n)]), weights)
    return _spread(weights)


def region_objects_colours(chunks, objex):
    """The palette numbers 16-95 (the region's own) that the region's objects (its ETAB: 8 bytes an
    entity, x, y, height, flags, the object negated) are drawn with."""
    etab = next(v for k, v in chunks.items() if k[0] == 'ETAB')
    used = set()
    for k in range(len(etab) // 8):
        ob = abs(struct.unpack_from('<h', etab, 8 * k + 6)[0])
        oj = objex.get(('OJFF', ob))
        if not oj:
            continue
        pic = struct.unpack_from('<H', oj, PIC)[0]
        for t in ('BMP ', 'CBMP'):
            c = objex.get((t, pic))
            for f in range(frames(c)[0] if c else 0):
                for row in decode_any(c, f)[2]:
                    used.update(p for p in row if p is not None and 16 <= p <= 95)
    return used


def regrade(sl_dir, wr_dir, region, strength, out, cap=1.6):
    """WR's region file with its colours moved toward SL's ground colours (lightness by a power
    curve from WR's mean to SL's, a and b by the mean and spread, the spread's scale at most CAP; all
    at STRENGTH 0-1): its palette's own entries 16-95
    (the ground and the region's objects together) graded; ground pixels in any other colour (the
    shared ones 96-255, which the interface and figures use too, so not changed) graded and
    clustered into the 16-95 entries that neither the tiles nor the region's objects use."""
    strength = float(strength)
    path = find(wr_dir, region if region.upper().endswith('.GFF') else region + '.GFF')
    _, chunks = load(path)
    _, objex = load(find(wr_dir, 'OBJEX.GFF'))
    pk = next(k for k in chunks if k[0] == 'PAL ')
    pal = vga(chunks[pk])
    mine = collections.Counter()
    _ground(chunks, pal, mine)
    (ms, ss), (mw, sw) = sl_ground(sl_dir), _spread(mine)
    # lightness by a power curve that takes WR's mean to SL's and keeps white white (a straight shift
    # blew Tyr's light sandstone out to white, seen in the game 2026-11-20); the colour axes a and b
    # by the mean and spread
    gamma = math.log(max(ms[0], 1) / 100) / math.log(max(mw[0], 1) / 100)
    def graded(c):
        l = _lab(c)
        t = [100 * (max(l[0], 0) / 100) ** gamma] + [
            ms[j] + (l[j] - mw[j]) * min(cap, ss[j] / max(sw[j], 1e-6)) for j in (1, 2)]
        return [l[j] + strength * (t[j] - l[j]) for j in range(3)]
    new = list(pal)
    for i in range(16, 96):
        new[i] = _rgb(graded(pal[i]))
    tiles = {k: c for k, c in chunks.items() if k[0] == 'TILE'}
    tile_used = set()
    weight = collections.Counter()
    m = next(v for k, v in chunks.items() if k[0] in ('MAP ', 'RMAP'))
    on_map = collections.Counter(m)
    for (t, i), c in tiles.items():
        for row in decode_any(c, 0)[2]:
            for p in row:
                if p is not None:
                    tile_used.add(p)
                    if not 16 <= p <= 95:
                        weight[p] += on_map.get(i, 0) + 1
    # 16-31 left out: the game cycles 16-23 at run time (torches, fire), overwriting what the file
    # holds there (seen in the game, 2026-11-20: the ground put in 21 and 23 showed in yellow and
    # orange), and the rest of that band is kept clear of the same risk
    free = [i for i in range(32, 96) if i not in tile_used and i not in region_objects_colours(chunks, objex)]
    if not free and weight:
        raise SystemExit('no free palette entries in 16-95 for the shared colours')
    pts = {p: graded(pal[p]) for p in weight}
    near = lambda l, cs: min(range(len(cs)), key=lambda j: sum((a - b) ** 2 for a, b in zip(l, cs[j])))
    centres = [pts[p] for p in sorted(pts, key=lambda p: -weight[p])[:len(free)]]
    for _ in range(30):  # k-means, weighted by how much of the map each colour covers
        groups = collections.defaultdict(list)
        for p, l in pts.items():
            groups[near(l, centres)].append(p)
        for j, g in groups.items():
            tot = sum(weight[p] for p in g)
            centres[j] = [sum(pts[p][d] * weight[p] for p in g) / tot for d in range(3)]
    table = list(range(256))
    for p, l in pts.items():
        table[p] = free[near(l, centres)]
    for j, l in enumerate(centres):
        new[free[j]] = _rgb(l)
    pal_chunk = bytearray(chunks[pk])
    for i in range(256):
        pal_chunk[3 * i:3 * i + 3] = bytes(v * 63 // 255 for v in new[i])
    changed = {pk: bytes(pal_chunk)}
    for k, c in tiles.items():
        changed[k] = recolour(c, table)
    grown = append_chunks(path, changed, out)
    print(f'{out}: {region} at {strength}: palette 16-95 graded, {len(pts)} shared colours of the ground in '
          f'{len(centres)} free entries {free}, {len(tiles)} tiles; {grown} bytes appended')


# --- a region seen from SL's angle (phase 4) ---

def encode(rows):
    """One frame in SL's run-length format from rows of palette numbers (None clear)."""
    h, w = len(rows), len(rows[0])
    out = bytearray(struct.pack('<HH', w, h))
    for y, row in enumerate(rows):
        spans, x = [], 0
        while x < w:
            if row[x] is None:
                x += 1
                continue
            x0 = x
            while x < w and row[x] is not None and x - x0 < 120:
                x += 1
            spans.append((x0, row[x0:x]))
        if not spans:
            continue
        out.append(y)
        for k, (x0, px) in enumerate(spans):
            data, i = bytearray(), 0
            while i < len(px):
                n = 1
                while i + n < len(px) and px[i + n] == px[i] and n < 128:
                    n += 1
                if n >= 3:
                    data += bytes((((n - 1) << 1) | 1, px[i]))
                    i += n
                    continue
                j, lit = i, []
                while j < len(px) and len(lit) < 128:
                    m = 1
                    while j + m < len(px) and px[j + m] == px[j] and m < 3:
                        m += 1
                    if m >= 3:
                        break
                    lit.append(px[j])
                    j += 1
                data += bytes(((len(lit) - 1) << 1,)) + bytes(lit)
                i = j
            out += bytes((x0, 0x80 if k == len(spans) - 1 else 0, len(px), len(data))) + data
    out.append(0xFF)
    return bytes(out)


def picture(frames_rows):
    """A picture chunk from a list of frames' rows."""
    frs = [encode(r) for r in frames_rows]
    at, offs = 6 + 4 * len(frs), []
    for f in frs:
        offs.append(at)
        at += len(f)
    return struct.pack('<IH', at, len(frs)) + b''.join(struct.pack('<I', o) for o in offs) + b''.join(frs)


# Rugs and mats lying on Tyr's floor (by eye): flat, so not lowered
FLAT = {534, 535, 536, 537, 2385, 2386, 2896}
FACE = 48  # WR's upright wall face, in rows


def squash(wr_dir, region, factor, out_dir, what='all'):
    """A WR region's structures and furniture as seen from SL's steeper angle (about 65 degrees
    above the horizontal against WR's 50: upright faces shrink by cos 65 / cos 50, about 0.66).
    For every picture the region's entities place (not the animated ones: people, doors, curtains;
    not FLAT): a structure (24 wide or less, or 56 tall or more) has its top brought down by DROP
    (FACE x (1 - FACTOR): 16 at 0.66) and as much cut off its bottom, so walls running away from
    the camera stay joined; furniture is squashed toward its base. A picture only ever placed on top
    of something (an entity height of 30 or more: a wall's upper part) keeps its picture and comes
    down by DROP through its height. Every picture keeps its size, so its anchor (OJFF +2, +4: the
    bottom centre) still holds. Tried on Tyr in the game, 2026-11-20 (docs/FIGURES.md). WHAT
    'furniture' leaves the structures and what stands on them alone (the owner's choice after the
    second comparison: walls at WR's height, tables and other map artwork squashed)."""
    furniture_only = what == 'furniture'
    factor = float(factor)
    drop = FACE - int(FACE * factor + 0.5)
    rpath = find(wr_dir, region if region.upper().endswith('.GFF') else region + '.GFF')
    opath = find(wr_dir, 'OBJEX.GFF')
    _, chunks = load(rpath)
    _, objex = load(opath)
    ek = next(k for k in chunks if k[0] == 'ETAB')
    etab = bytearray(chunks[ek])
    by_pic = collections.defaultdict(list)
    for k in range(len(etab) // 8):
        ob = abs(struct.unpack_from('<h', etab, 8 * k + 6)[0])
        by_pic[struct.unpack_from('<H', objex[('OJFF', ob)], PIC)[0]].append(k)
    new = {}
    for pic, ents in by_pic.items():
        if ('SCMD', pic) in objex or pic in FLAT or ('BMP ', pic) not in objex:
            continue
        if all(etab[8 * k + 4] >= 30 for k in ents):
            if furniture_only:
                continue
            for k in ents:
                etab[8 * k + 4] = max(0, etab[8 * k + 4] - drop)
            continue
        c = objex[('BMP ', pic)]
        out_frames = []
        for f in range(frames(c)[0]):
            w, h, px = decode_any(c, f)
            out = [[None] * w for _ in range(h)]
            if w <= 24 or h >= 56:
                if furniture_only:
                    out_frames = None
                    break
                for y in range(drop, h):
                    out[y] = list(px[y - drop])
            else:
                for y in range(h):
                    src = h - 1 - int((h - 1 - y) / factor + 0.5)
                    if src >= 0:
                        out[y] = list(px[src])
            out_frames.append(out)
        if out_frames is None:
            continue
        new[('BMP ', pic)] = picture(out_frames)
        for k in ents:
            if 0 < etab[8 * k + 4] < 30:
                etab[8 * k + 4] = int(etab[8 * k + 4] * factor + 0.5)
    os.makedirs(out_dir, exist_ok=True)
    append_chunks(opath, new, os.path.join(out_dir, os.path.basename(opath)))
    append_chunks(rpath, {ek: bytes(etab)}, os.path.join(out_dir, os.path.basename(rpath)))
    print(f'{out_dir}: {len(new)} pictures lowered, the drop {drop} rows')


# --- the commands ---

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


def build_ui(sl_dir, wr_dir, out):
    """WR's RESOURCE.GFF with UI_PICTURES and the icons icon_pairs finds taken from SL's RESOURCE.GFF,
    recoloured (ui_colour_table), appended, the index pointed at them."""
    _, S = load(find(sl_dir, 'RESOURCE.GFF'))
    path = find(wr_dir, 'RESOURCE.GFF')
    _, W = load(path)
    table, sp, wp = ui_colour_table(S, wr_dir, W)
    new = {('BMP ', i): recolour(S[('BMP ', i)], table) for i in UI_PICTURES}
    pairs = icon_pairs(S, W, sp, wp)
    for i, (j, _) in pairs.items():
        new[('ICON', i)] = recolour(S[('ICON', j)], table)
    grown = append_chunks(path, new, out)
    check = load(out)[1]
    for key in new:
        for f in range(frames(check[key])[0]):
            decode(check[key], f)
    moved = sum(i != j for i, (j, _) in pairs.items())
    print(f'{out}: {len(UI_PICTURES)} pictures and {len(pairs)} icons ({moved} from another number) '
          f'replaced, {grown} bytes appended')


if __name__ == '__main__':
    cmds = {'report': (report, 2), 'sheet': (sheet, 3), 'build': (build, 3), 'build-ui': (build_ui, 3),
            'regrade': (regrade, 5), 'squash': (squash, 4)}
    if len(sys.argv) == 7 and sys.argv[1] == 'squash':
        cmds['squash'] = (squash, 5)
    if len(sys.argv) < 2 or sys.argv[1] not in cmds or len(sys.argv) != 2 + cmds[sys.argv[1]][1]:
        raise SystemExit(__doc__)
    cmds[sys.argv[1]][0](*sys.argv[2:])
