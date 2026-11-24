"""Put the approved Ravager figure redraws into a copy of the game's files, and check them.

    import_catalogue.py CATALOGUE BASE_DIR OUT_DIR [STOCK_DIR]

CATALOGUE is the figure catalogue in the private darksun-installation-files repository
(ravager-figure-redraws/catalogue); its approved.json lists the approved packages in the order
they apply, the objects that move to a new figure number (the greater elementals) and the region
chunks that change with a scene (the Mines3 dining room). BASE_DIR holds the OBJEX.GFF (and the
region files) to build on, usually the mod's restyled build; OUT_DIR gets OBJEX.GFF and each changed
region file. A package made for a stationary figure may hold only its pictures: it was drawn for
the shipped script, so the script (and any combat pictures) it lacks are taken from the shipped
game in STOCK_DIR (default BASE_DIR), since the mod's build may have given that picture another
(the dressed people walk). Nothing in this repository holds the artwork: it stays in the private catalogue.

Every picture written is decoded frame by frame, and every step of every script is checked against
the frames of the picture it runs on (base frames for walking steps, combat frames for steps flagged
0x20), so a package that would show a missing frame fails here rather than in the game."""
import json, os, struct, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..')]
import sl_figures as s

BANKS = {'base': 'BMP ', 'combat': 'CBMP', 'script': 'SCMD'}
# the first stationary packages name the chunk after the picture instead (714.bmp-chunk)
FLAT = {'base': 'bmp', 'combat': 'cbmp', 'script': 'scmd'}
COMBAT = 0x20


def changes(catalogue, objex, stock):
    man = json.load(open(os.path.join(catalogue, 'approved.json')))
    new, source = {}, {}
    for p in man['packages']:
        with zipfile.ZipFile(os.path.join(catalogue, p['zip'])) as z:
            names = set(z.namelist())
            for pic in p['pictures']:
                got = {b: m for b in BANKS for m in (f'{pic}/{b}.chunk', f'{pic}.{FLAT[b]}-chunk') if m in names}
                if 'base' not in got:
                    raise SystemExit(f"{p['zip']}: no base picture for {pic}")
                for b, m in got.items():
                    new[BANKS[b], pic] = z.read(m)
                for b in BANKS:
                    if b not in got:
                        key = BANKS[b], pic
                        if key in stock:
                            new[key] = stock[key]
                        elif key in new:
                            del new[key]
                source[pic] = p['zip']
    for obj, (old, pic) in man.get('objects', {}).items():
        rec = bytearray(objex['OJFF', int(obj)])
        cur, = struct.unpack_from('<H', rec, 12)
        if cur not in (old, pic):
            raise SystemExit(f'object {obj} uses figure {cur}, expected {old}')
        struct.pack_into('<H', rec, 12, pic)
        new['OJFF', int(obj)] = bytes(rec)
    regions = {}
    for r in man.get('regions', []):
        with zipfile.ZipFile(os.path.join(catalogue, r['zip'])) as z:
            for key, member in r['chunks'].items():
                t, i = key.rsplit(' ', 1)
                regions.setdefault(r['file'], {})[t.ljust(4), int(i)] = z.read(member)
    return new, regions, source


def check(objex, pics):
    """Problems with PICS in the loaded OBJEX: undecodable frames, script steps past the frames."""
    bad = []
    for pic in pics:
        n = {}
        for t in ('BMP ', 'CBMP'):
            if (t, pic) in objex:
                c = objex[t, pic]
                n[t] = s.frames(c)[0]
                for f in range(n[t]):
                    try:
                        s.decode_any(c, f)
                    except Exception as e:
                        bad.append(f'{pic} {t.strip()} frame {f}: {e}')
        if ('SCMD', pic) in objex:
            for k, st in enumerate(s.steps(objex['SCMD', pic])):
                t = 'CBMP' if st[2] & COMBAT else 'BMP '
                if st[0] >= n.get(t, 0):
                    bad.append(f'{pic} script step {k}: frame {st[0]} of {n.get(t, 0)} {t.strip()} frames')
    return bad


def main():
    if len(sys.argv) not in (4, 5):
        raise SystemExit(__doc__)
    catalogue, base, out = sys.argv[1:4]
    stock_dir = sys.argv[4] if len(sys.argv) == 5 else base
    os.makedirs(out, exist_ok=True)
    src = s.find(base, 'OBJEX.GFF')
    _, objex = s.load(src)
    _, stock = s.load(s.find(stock_dir, 'OBJEX.GFF'))
    new, regions, source = changes(catalogue, objex, stock)
    s.write_ranged(src, new, os.path.join(out, 'OBJEX.GFF'))
    for name, ch in regions.items():
        rsrc = s.find(base, name)
        _, have = s.load(rsrc)
        for key in ch:
            if key not in have:
                raise SystemExit(f'{name} has no {key}')
        s.append_chunks(rsrc, ch, os.path.join(out, name))   # region files keep their index layout
    _, built = s.load(os.path.join(out, 'OBJEX.GFF'))
    pics = sorted(source)
    for key, c in new.items():
        if built[key] != c and key[0] not in ('BMP ', 'CBMP'):
            raise SystemExit(f'{key} did not round-trip')
    bad = check(built, pics)
    for b in bad:
        print('BAD', b)
    print(f'{len(pics)} pictures from {len(set(source.values()))} packages, '
          f'{sum(1 for k in new if k[0] == "OJFF")} objects moved, {len(regions)} region file(s); '
          f'{len(bad)} problems')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
