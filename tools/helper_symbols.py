#!/usr/bin/env python3
"""Where the mod's helper (DSCLOG.EXE, or Wake of the Ravager's DSCLOG2.EXE) keeps the routines
the image builder has to know about, found by assembling its source with nasm and reading nasm's
map file, so a new version of the helper moves nothing out from under us.

    python3 tools/helper_symbols.py <mod>/obsidian-edition/dos/dsclog.asm [DSCLOG.EXE]

The symbols: kit_is_b, cr_is and cb_is (called as `call X / db ARG`; cr_is's own call to
kit_is_b, the one before cr_is_back, has no argument), seg_space (where SEG_MOVE's copies of two
of the game's segments go). DSCLOG2 has no cb_is and no SEG_MOVE: what a helper lacks is left
out, and the caller asks only for what that helper must have (`needed`).

Offsets are into the helper's image (the EXE less its MZ header: what DOS loads at the load
segment's offset 0). The map gives each label's place in the file ("Real"), right whatever
section the label is in: the helpers are built of sections that each start their labels at 0
(DSCLOG's image and tail; DSCLOG2's image, tail and install), and their routines shared since
the mod's code audit come from macros in shared_routines.inc, which a listing shows under
`<1>` marks (the listing this read before, 2026-11-28, found none of them and the image builder
fell back to helper 2.5.0's table without a word). Without nasm, or with an assembly that does
not match the EXE, the result is None and the caller falls back to its built-in table.
"""
import os
import re
import struct
import subprocess
import sys
import tempfile

NEEDED = ('kit_is_b', 'cr_is', 'cr_is_back', 'cb_is', 'seg_space')   # (DSCLOG's)
NEEDED_RAVAGER = ('kit_is_b', 'cr_is', 'cr_is_back')                  # (DSCLOG2's)
OPTIONAL = ('cb_is', 'seg_space')


def assemble(asm_path):
    """(nasm's map file, the assembled bytes), or (None, None): no nasm, or it fails."""
    with tempfile.TemporaryDirectory() as d:
        mp, out = os.path.join(d, 'a.map'), os.path.join(d, 'a.bin')
        try:
            r = subprocess.run(['nasm', '--before', f'[map all {mp}]', '-f', 'bin', '-o', out,
                                os.path.basename(asm_path)],
                               cwd=os.path.dirname(os.path.abspath(asm_path)), capture_output=True, text=True)
        except FileNotFoundError:
            return None, None
        if r.returncode != 0 or not os.path.exists(mp):
            return None, None
        return open(mp, encoding='latin-1').read(), open(out, 'rb').read()


def symbols(asm_path, exe_path=None, needed=NEEDED):
    """{symbol: image offset} for the symbols of NEEDED and OPTIONAL the helper has, or None
    when one of NEEDED is missing. With exe_path, the assembled bytes must equal the EXE (the
    source and the EXE belong together)."""
    text, image = assemble(asm_path)
    if text is None:
        return None
    if exe_path and image != open(exe_path, 'rb').read():
        return None
    if image[:2] != b'MZ':
        return None
    hdr = struct.unpack_from('<H', image, 8)[0] * 16
    want = set(needed) | set(OPTIONAL)
    found = {}
    # "-- Symbols --" lines: `Real  Virtual  Name` (hex, the file's place first)
    for m in re.finditer(r'^\s*([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+(\w+)\s*$', text, re.M):
        name = m.group(3)
        if name in want and name not in found:
            found[name] = int(m.group(1), 16) - hdr
    return found if all(s in found for s in needed) else None


def sections(asm_path, exe_path=None):
    """{section name: (image offset, length)} of the helper's sections from nasm's map (its MZ header
    left out): DSCLOG's image and tail, DSCLOG2's image, tail, tailz (the tail's buffers, in the
    tail's segment) and install. The tail holds code too (TAIL_CALL's, PL_CALL's routines, run with
    CS the tail's segment). None without nasm or with an EXE that does not match."""
    text, image = assemble(asm_path)
    if text is None or (exe_path and image != open(exe_path, 'rb').read()):
        return None
    hdr = struct.unpack_from('<H', image, 8)[0] * 16
    out = {}
    for m in re.finditer(r'^\s*[0-9A-Fa-f]+\s+([0-9A-Fa-f]+)\s+[0-9A-Fa-f]+\s+([0-9A-Fa-f]+)\s+progbits\s+(\S+)\s*$', text, re.M):
        start, length, name = int(m.group(1), 16), int(m.group(2), 16), m.group(3)
        if name not in ('.text', 'mz') and length:
            out[name] = (start - hdr, length)
    return out


CODE_RE = re.compile(r'^([A-Za-z_][\w]*):\s*(?:;.*)?$')
DATA_WORDS = ('db', 'dw', 'dd', 'dq', 'times', 'resb', 'resw', 'resd', 'equ', 'incbin', 'align', '%')


def code_labels(asm_path, exe_path=None):
    """The image offsets of the helper's routines in the code that stays (its segment and its tail):
    every label of its own line, outside a macro's definition, whose next line is an instruction
    (not data), in the source and the files it includes. For a helper whose install calls its
    routines through a segment worked out at run time (DSCLOG2), and whose handlers the install
    puts in the vectors, where the finder cannot follow: the image builder's seeds, so a first
    build need not find each one by a run. None without nasm or with an EXE that does not match."""
    text, image = assemble(asm_path)
    if text is None or (exe_path and image != open(exe_path, 'rb').read()):
        return None
    hdr = struct.unpack_from('<H', image, 8)[0] * 16
    places = {}
    for m in re.finditer(r'^\s*([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+(\w+)\s*$', text, re.M):
        places.setdefault(m.group(3), int(m.group(1), 16) - hdr)
    secs = sections(asm_path)
    if not secs or 'image' not in secs:
        return None
    kept = [secs[k] for k in ('image', 'tail') if k in secs]       # (the code that stays: the segment and the tail's)
    names = []
    folder = os.path.dirname(os.path.abspath(asm_path))
    files = [os.path.basename(asm_path)]
    for f in files:
        lines = open(os.path.join(folder, f), encoding='latin-1').read().split('\n')
        for inc in re.findall(r'^\s*%include\s+"([^"]+)"', '\n'.join(lines), re.M):
            if inc not in files:
                files.append(inc)
        pending = None
        for line in lines:
            body = line.split(';', 1)[0].strip()
            if not body:
                continue
            m = CODE_RE.match(line.strip())
            if m:
                pending = m.group(1)
                continue
            if pending:
                word = body.split()[0].lower()
                if not word.startswith(DATA_WORDS) and not word.endswith(':') and not word.startswith('.'):
                    names.append(pending)
                pending = None
    out = sorted({places[n] for n in names if n in places and any(a <= places[n] < a + l for a, l in kept)})
    return out


if __name__ == '__main__':
    asm = sys.argv[1]
    need = NEEDED_RAVAGER if os.path.basename(asm).lower() == 'dsclog2.asm' else NEEDED
    syms = symbols(asm, sys.argv[2] if len(sys.argv) > 2 else None, need)
    if not syms:
        sys.exit('no symbols (nasm missing, or the assembly does not match the EXE)')
    for k, v in syms.items():
        print(f'{k:12} {v:04X}')
