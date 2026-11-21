#!/usr/bin/env python3
"""Names for the lifted functions, from OpenDS's symbol catalogue (ovr-map/syms/<game>.toml).

    python3 tools/syms.py build/ds1 game/ds1/DSUN.EXE path/to/opends/tools/ovr-map/syms/ds1.toml

writes build/ds1/symbols.json ({"2CBA4": {"name", "confidence"}}, keyed by the linear address
the lifter names functions by) and checks every row against the image. tools/lift.py reads that file
when it is there and puts each name in a comment above its function's C; the function names
themselves (ds1_fn_2CBA4) do not change, so nothing that refers to them does.

OpenDS addresses a function two ways (the catalogue's header explains): a resident one by file
offset, an overlay one by (segment index, offset within that segment). The segment index is the
overlay module's index in layout.json (OpenDS's ovr-map numbers the same 52 modules). In the image:

    resident   linear = load_seg*16 + file offset - the EXE's header size
    overlay    linear = the module's load segment*16 + offset

A row that points outside its segment, or a function that does not start where a function starts
(a Borland `push bp / mov bp, sp`, or the thunk shapes OpenDS names), is reported, not written
silently: the catalogue is hand-curated and these are the places it and the image disagree.
"""
import json
import os
import struct
import sys

try:
    import tomllib
except ImportError:  # Python before 3.11
    tomllib = None


def load_rows(path):
    if tomllib is None:
        raise SystemExit('tools/syms.py needs Python 3.11+ (tomllib)')
    with open(path, 'rb') as fh:
        return tomllib.load(fh).get('function', [])


def mz_header_size(exe):
    return struct.unpack_from('<H', exe, 8)[0] * 16


def linear_of(row, layout, hdr):
    """(linear address, None) for a catalogue row, or (None, why)."""
    seg, off = row['segment'], row['offset']
    if seg == 'resident':
        lin = layout['load_seg'] * 16 + off - hdr
        lo, hi = layout['resident']
        return (lin, None) if lo <= lin < hi else (None, f'file offset {off:X} is outside the resident image')
    mods = layout['modules']
    if not isinstance(seg, int) or not 0 <= seg < len(mods):
        return None, f'no overlay module {seg}'
    m = mods[seg]
    if m['seg'] is None or not 0 <= off < m['size']:
        return None, f'offset {off:X} is outside module {seg} ({m["size"]:X} bytes)'
    return m['seg'] * 16 + off, None


def frame_kind(mem, lin, starts=()):
    """(kind, start): 'at' when a Borland frame starts at LIN (push bp / mov bp, sp; a far function
    has an inc bp before it), 'after' when LIN is just past one (OpenDS names some functions at the
    stack check after the frame), else ('interior', LIN)."""
    if lin in starts:  # tools/find_funcs.py found a function here: the finder's word beats a byte pattern
        return 'at', lin
    if mem[lin:lin + 3] == b'\x55\x8b\xec' or mem[lin:lin + 4] == b'\x45\x55\x8b\xec':
        return 'at', lin
    if mem[lin - 3:lin] == b'\x55\x8b\xec':
        return 'after', lin - 4 if mem[lin - 4] == 0x45 else lin - 3
    if mem[lin - 1] in (0xC3, 0xCB) and (mem[lin:lin + 2] in (b'\x39\x26', b'\x56\x39', b'\x57\x39')
                                         or (mem[lin] == 0x6A and mem[lin + 2] == 0xE8)):
        # no frame: starts with the stack check (cmp [9Ch], sp in DS1; push n / call in DS2) right after
        # the last function's return
        return 'at', lin
    return 'interior', lin


def build(build_dir, exe_path, toml_path, quiet=False):
    layout = json.load(open(os.path.join(build_dir, 'layout.json')))
    mem = open(os.path.join(build_dir, 'image.bin'), 'rb').read()
    hdr = mz_header_size(open(exe_path, 'rb').read(64))
    out, problems, interior, adjusted = {}, [], 0, 0
    fpath = os.path.join(build_dir, 'functions.json')   # (find_funcs.py's, when it has run)
    starts = {int(k, 16) for k in json.load(open(fpath))} if os.path.exists(fpath) else set()
    for row in load_rows(toml_path):
        lin, why = linear_of(row, layout, hdr)
        label = f'{row["name"]} ({row["segment"]}:{row["offset"]:X})'
        if lin is None:
            problems.append(f'{label}: {why}')
            continue
        kind, lin = frame_kind(mem, lin, starts)
        if kind == 'interior':
            interior += 1
            if not quiet:
                print(f'  note: {label} at {lin:05X} is not at a frame: {mem[lin - 3:lin + 4].hex()} (interior or data; written, but no function starts here' + ('' if starts else ' - or find_funcs.py has not run, so only byte patterns were checked') + ')')
        if f'{lin:05X}' in out:
            problems.append(f'{label}: {out[f"{lin:05X}"]["name"]} is already at {lin:05X}')
            continue
        if kind == 'after':
            adjusted += 1
        out[f'{lin:05X}'] = {'name': row['name'], 'confidence': row.get('confidence', ''),
                             'at': kind}
    path = os.path.join(build_dir, 'symbols.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(f'{path}: {len(out)} names ({adjusted} moved back to their frame, {interior} at no frame, {len(problems)} rows refused)')
    for p in problems:
        print('  refused:', p)
    return out, problems


def load(build_dir):
    """{linear: {name, confidence}} from BUILD_DIR/symbols.json, or {} when it is not there."""
    path = os.path.join(build_dir, 'symbols.json')
    if not os.path.exists(path):
        return {}
    return {int(k, 16): v for k, v in json.load(open(path)).items()}


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    _, problems = build(*sys.argv[1:4])
    sys.exit(1 if problems else 0)
