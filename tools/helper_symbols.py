#!/usr/bin/env python3
"""Where the mod's helper (DSCLOG.EXE) keeps the routines the image builder
has to know about, found by assembling its source with nasm and reading the
listing, so a new version of the helper moves nothing out from under us.

    python3 tools/helper_symbols.py <mod>/obsidian-edition/dos/dsclog.asm

The symbols: kit_is_b, cr_is and cb_is (called as `call X / db ARG`; cr_is's
own call to kit_is_b, the one before cr_is_back, has no argument), seg_space (where SEG_MOVE's copies of
two of the game's segments go), and the entry. Offsets are into the helper's
image (its load segment's offset 0). Without nasm, or with a listing that
does not match the EXE, the caller falls back to its built-in table.
"""
import os
import re
import subprocess
import sys
import tempfile

NEEDED = ('kit_is_b', 'cr_is', 'cr_is_back', 'cb_is', 'seg_space')


def listing(asm_path):
    """nasm's listing of the source, or None (no nasm, or it fails)."""
    with tempfile.TemporaryDirectory() as d:
        lst, out = os.path.join(d, 'a.lst'), os.path.join(d, 'a.bin')
        try:
            r = subprocess.run(['nasm', '-f', 'bin', '-l', lst, '-o', out, os.path.basename(asm_path)],
                               cwd=os.path.dirname(os.path.abspath(asm_path)), capture_output=True, text=True)
        except FileNotFoundError:
            return None, None
        if r.returncode != 0:
            return None, None
        return open(lst, encoding='latin-1').read().split('\n'), open(out, 'rb').read()


def symbols(asm_path, exe_path=None):
    """{symbol: image offset} for NEEDED, or None. With exe_path, the assembled
    bytes must equal the EXE's image (the source and the EXE belong together)."""
    lines, image = listing(asm_path)
    if lines is None:
        return None
    if exe_path:
        exe = open(exe_path, 'rb').read()
        if image != exe:
            return None
    line_re = re.compile(r'^\s*\d+\s+(?:([0-9A-F]{8})\s+\S+(?: [0-9A-Fa-f]+h>)?\s+)?(.*)$')   # (bytes may be `00<rep 200h>`)
    found = {}
    pending = None
    for line in lines:
        m = line_re.match(line)
        if not m:
            continue
        addr, text = m.group(1), m.group(2).strip()
        name = text.split()[0] if text else ''
        if pending and addr:
            found.setdefault(pending, int(addr, 16))
            pending = None
        if name.endswith(':') and name[:-1] in NEEDED:
            if addr:
                found.setdefault(name[:-1], int(addr, 16))
            else:
                pending = name[:-1]
        elif name in NEEDED and addr:                   # `seg_space times N db 0`
            found.setdefault(name, int(addr, 16))
    return found if all(s in found for s in NEEDED) else None


if __name__ == '__main__':
    syms = symbols(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    if not syms:
        sys.exit('no symbols (nasm missing, or the listing does not match)')
    for k, v in syms.items():
        print(f'{k:12} {v:04X}')
