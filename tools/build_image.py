#!/usr/bin/env python3
"""Build the start-up memory image of a Dark Sun DSUN.EXE with every overlay loaded.

DOS would load the resident image, apply its MZ relocations and leave the
Borland overlay manager (VROOMM) to page the 50-odd overlay modules in and out
of a buffer as their entry stubs are hit. A static recompilation cannot follow
code that moves, so this does once, at build time, what the manager does each
time it loads a module, for all of them at the same time:

  1. copy the module's code to a segment of its own (above the VGA memory,
     where DOS never hands out memory),
  2. apply the module's relocation table: each entry names a word holding a
     byte offset into the segment table, replaced by that record's (already
     relocated) segment,
  3. rewrite each of the module's 5-byte entry stubs from `INT 3Fh <entry>`
     to `JMP FAR <entry>:<module segment>`, and mark the descriptor loaded.

After that the program is an ordinary one: an overlay call is a far call to a
stub that jumps straight into code that never moves, and the overlay manager is
never entered. The formats are the ones OpenDS documents
(docs/overlay-formats.md in github.com/VirInvictus/opends).

Output (in --out):
  image.bin    the guest's first 1 MB + 64 KB, as the runtime starts it
  layout.json  where everything is: segments, entry point, stubs, modules

The game's own files are only read.
"""
import argparse
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helper_symbols  # noqa: E402

MEM_SIZE = 0x110000          # 1 MB + the HMA, as runtime/cpu.h allocates
PSP_SEG = 0x0800             # program segment prefix; the image follows it
ENV_SEG = 0x07E0             # the environment block, just below the PSP
OVL_FIRST_SEG = 0xC000       # overlay modules from here up (no EMS page frame)
TOP_OF_DOS = 0xA000          # end of conventional memory
BIOS_STUBS_SEG = 0xFFE0      # the interrupt vectors' stubs (F000:FE00): the overlays and upper memory end below
UMB_WANT = 0x200             # upper memory DSCLOG2 asks for beside the overlays (its see-through
                             # figures' block is 160h paragraphs)
TSR_PSP_SEG = 0xB000         # a resident helper (the mod's DSCLOG.EXE) lives in B000-BFFF,
                             # which nothing else uses in mode 13h
WOTR_SIZE = 634416           # Wake of the Ravager's DSUN.EXE (GOG 1.1): its mod's patches are the
                             # mod's dsloader/ravager.py's, its helper DSCLOG2.EXE (dsclog2.asm)

# The mod's patches that put data after the INT, which the helper's handler
# steps over: how many bytes, so the decoder does too. VEC_CR_SPELLS sites
# carry a site number; "scroll" replaces the first 3 bytes of a far call and
# the helper returns past the segment that stays.
MOD_SITE_SKIP = {'scroll': 3}
# Wake of the Ravager's helper's SITE (INT F5h): the byte after the INT is the site's number in its
# SITE_TABLE (the mod's ravager._site), stepped over as VEC_CR_SPELLS' is in Shattered Lands.
RAV_VEC_SITE = 0xF5

# The helper's SEG_MOVE: at the game's first file open it points two entries
# of the game's segment table (selector 3B8h, a small stack; 3C0h, the
# monster kinds' table) at a block of its own (seg_space, image offset D680h)
# and copies the 200h bytes there, so the new spells' records can take the
# old place. Under DOS every overlay loaded afterwards is relocated with the
# changed table; here the overlays are relocated now, so those two selectors
# get the helper's segments from the start (the copy still happens at run
# time, as the helper does it).
HELPER_SEG_SPACE = 0xD680
# Routines of the helper called as `call X / db ARG`: they read the byte after
# the call through their return address and return past it (kit_is_b and
# cb_is directly; cr_is through kit_is_b, which knows cr_is's return address).
# Image offset -> bytes after the call; the decoder lengthens such calls.
HELPER_INLINE_ARGS = {0x30FF: 1, 0x30F4: 1, 0x38FE: 1}
# ... except cr_is's own call to kit_is_b, which takes the argument from cr_is's caller
HELPER_INLINE_PLAIN_SITES = {0x30F9}      # image offsets of such calls with no argument after them
HELPER_MOVED = {0x3B8: 0, 0x3C0: 6}       # selector -> paragraphs into seg_space


class ImageError(Exception):
    pass


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def parse_mz(exe):
    if exe[:2] != b'MZ':
        raise ImageError('not an MZ executable')
    lastp, pages, nrel, hdr_paras = struct.unpack_from('<4H', exe, 2)
    ss, sp, _csum, ip, cs, reloff = struct.unpack_from('<6H', exe, 0x0E)
    image_end = pages * 512 - ((512 - lastp) if lastp else 0)
    hdr = hdr_paras * 16
    relocs = [struct.unpack_from('<2H', exe, reloff + 4 * i) for i in range(nrel)]
    return dict(hdr=hdr, image_end=image_end, ss=ss, sp=sp, ip=ip, cs=cs,
                relocs=relocs)


def load_tsr(mem, path):
    """Load a resident helper's EXE at TSR_PSP_SEG the way DOS would (PSP,
    environment, image at PSP+10h), and return where it starts."""
    exe = open(path, 'rb').read()
    mz = parse_mz(exe)
    load = TSR_PSP_SEG + 0x10
    image = exe[mz['hdr']:mz['image_end']]
    base = load * 16
    mem[base:base + len(image)] = image
    for off, seg in mz['relocs']:
        lin = base + seg * 16 + off
        struct.pack_into('<H', mem, lin, (u16(mem, lin) + load) & 0xFFFF)
    # The environment goes right above the helper's install stack (whose top
    # is past the image), and the overlays right above that: the room this
    # leaves below the BIOS area is one of the two upper memory blocks the
    # helper asks for (its ring; its panel gets the HMA).
    ss, sp = (mz['ss'] + load) & 0xFFFF, mz['sp']
    env_seg = (max(base + len(image), ss * 16 + sp) + 15) >> 4
    env = b'COMSPEC=C:\\COMMAND.COM\0\0' + b'\x01\x00' + b'D:\\' + os.path.basename(path).upper().encode('ascii') + b'\0'
    mem[env_seg * 16:env_seg * 16 + len(env)] = env
    p = TSR_PSP_SEG * 16
    mem[p:p + 2] = b'\xCD\x20'
    struct.pack_into('<H', mem, p + 2, env_seg)            # first segment past ours
    struct.pack_into('<H', mem, p + 0x2C, env_seg)
    mem[p + 0x80] = 0
    mem[p + 0x81] = 0x0D
    for k in range(20):
        mem[p + 0x18 + k] = k if k < 5 else 0xFF
    return dict(exe=os.path.basename(path).upper(), psp=TSR_PSP_SEG, load=load, env=env_seg,
                cs=(mz['cs'] + load) & 0xFFFF, code_cs=load, ip=mz['ip'], ss=ss, sp=sp,
                image=[base, base + len(image)], next_seg=env_seg + ((len(env) + 15) >> 4))


def mod_sites(mod_dir, exe, hdr, base, modules):
    """The mod's INT sites in the patched EXE as linear addresses, with the
    bytes after each INT its handler steps over, and the vectors it uses."""
    sys.path.insert(0, mod_dir)
    from dsloader import gamepatch                      # noqa: E402
    ravager = len(exe) == WOTR_SIZE
    if ravager:
        from dsloader import ravager as rav             # noqa: E402
    area = min(m['file'] for m in modules if m['size']) if modules else len(exe)

    def linear(off):
        if off < area:
            return base + off - hdr
        for m in modules:
            if m['seg'] is not None and m['file'] <= off < m['file'] + m['size']:
                return m['seg'] * 16 + off - m['file']
        return None

    sites, vectors, applied, originals = {}, set(), 0, {}
    for pt in (rav.PATCHES if ravager else gamepatch.PATCHES):
        here = exe[pt.offset:pt.offset + len(pt.original)]
        if here == pt.replacement and pt.replacement != pt.original:
            applied += 1
        if pt.replacement[:1] != b'\xCD' or here != pt.replacement:
            continue
        vectors.add(pt.replacement[1])
        # a VEC_CR_SPELLS site carries a site number only when the byte after the INT is not a NOP
        # (the handler steps over that byte either way: a NOP needs no help)
        site_vec = RAV_VEC_SITE if ravager else gamepatch.VEC_CR_SPELLS
        skip = MOD_SITE_SKIP.get(pt.name, 1 if pt.replacement[1] == site_vec
                                 and len(pt.replacement) > 2 and (ravager or pt.replacement[2] != 0x90) else 0)
        if ravager and skip == 1 and pt.replacement[1] == site_vec:
            skip = cut_skip(pt, exe, skip)
        lin = linear(pt.offset)
        if lin is None:
            raise ImageError(f'patch {pt.name} at {pt.offset:X} is outside the loaded code')
        if skip:
            sites[f'{lin:05X}'] = dict(skip=skip, vector=pt.replacement[1], name=pt.name)
        originals[f'{lin:05X}'] = pt.original.hex()     # (the finder reads a `mov cx, N` an INT replaced: a switch's size)
    if not applied:
        raise ImageError(f'{mod_dir}: none of the mod\'s patches is in this EXE (give DSUNLOG.EXE, or DSUNLOG2.EXE for Wake of the Ravager)')
    return sites, sorted(vectors), applied, originals


def cut_skip(pt, exe, skip):
    """A SITE that cuts an instruction of the game's in two (DSCLOG2's FIG_KEEP, PACE_PASS and PACE_DRAW
    put INT F5h + the site's number over the first 3 bytes of a 5-byte "call far", read the segment
    left there and come back past it): the way back is past the whole instruction, the skip counted
    from after the INT. Any other SITE steps over its number alone."""
    from dsimage import Decoder
    code = pt.original + exe[pt.offset + len(pt.original):pt.offset + len(pt.original) + 16]
    d, end = Decoder(code), 0
    while end < 3:                                  # (the INT and its number: the instruction they end in)
        end += d.decode_one().length
    # Cut only when that instruction runs past the patch's bytes: a patch whose bytes cover it, NOPs
    # after the number, comes back to the NOPs (DSCLOG2's AMMO_OKAY: INT, number, two NOPs over a
    # 5-byte compare, and its patch goes on to change the jump after it, so its bytes run past the
    # compare: counted as a cut there, the game came back mid-instruction and the first fight stalled)
    return end - 2 if end > len(pt.replacement) else skip


def build(exe_path, out_dir, game_args='', tsr_path=None, mod_dir=None, original=None):
    exe = open(exe_path, 'rb').read()
    mz = parse_mz(exe)
    hdr, image_end = mz['hdr'], mz['image_end']
    # A plain program (CHARTRAN.EXE, once unpacked) has no overlays: no
    # segment table either, so its code segments are read from its
    # relocations below.
    has_ovl = exe[image_end:image_end + 4] == b'FBOV'
    if has_ovl:
        ovrsize, exeinfo, segnum = struct.unpack_from('<3I', exe, image_end + 4)
        area = ((image_end + 15) & ~15) + 16      # overlay area base (file offset)
    else:
        exeinfo = segnum = area = 0

    mem = bytearray(MEM_SIZE)
    load = PSP_SEG + 0x10
    res = exe[hdr:image_end]
    base = load * 16
    mem[base:base + len(res)] = res
    for off, seg in mz['relocs']:
        a = base + seg * 16 + off
        struct.pack_into('<H', mem, a, (u16(mem, a) + load) & 0xFFFF)
    res_end = base + len(res)

    # The segment table: 8-byte records {para, size, class, x} at exeinfo
    # (a file offset; the table is part of the resident image).
    segtab_lin = base + (exeinfo - hdr) if has_ovl else 0
    records = []
    for i in range(segnum):
        para, size, cls, x = struct.unpack_from('<4H', exe, exeinfo + 8 * i)
        records.append(dict(index=i, para=para, seg=(para + load) & 0xFFFF,
                            size=size, cls=cls, x=x))

    # Class-3 records are the overlay stub blocks; each begins with its
    # module's 32-byte descriptor, then 5-byte stubs. They pair 1:1, in order,
    # with the modules.
    seg_override = {}
    # Where the helper keeps the routines below: from its source and nasm
    # (tools/helper_symbols.py) when they are there, so a new helper moves
    # nothing out from under us; else the table above (helper 2.5.0's).
    # Wake of the Ravager's helper (DSCLOG2.EXE, from dsclog2.asm) has no cb_is and no SEG_MOVE, and
    # no table to fall back on: without its symbols the build stops.
    inline_args, plain_sites, seg_space = dict(HELPER_INLINE_ARGS), set(HELPER_INLINE_PLAIN_SITES), HELPER_SEG_SPACE
    asm = None
    if tsr_path and mod_dir:
        sequel = len(exe) == WOTR_SIZE
        asm = os.path.join(os.path.dirname(os.path.abspath(tsr_path)), 'dsclog2.asm' if sequel else 'dsclog.asm')
        need = helper_symbols.NEEDED_RAVAGER if sequel else helper_symbols.NEEDED
        syms = helper_symbols.symbols(asm, tsr_path, need) if os.path.exists(asm) else None
        if syms:
            inline_args = {syms[k]: 1 for k in ('kit_is_b', 'cr_is', 'cb_is') if k in syms}
            plain_sites = {syms['cr_is_back'] - 3}          # cr_is's `call kit_is_b`, right before cr_is_back
            seg_space = syms.get('seg_space')
        elif sequel:
            raise ImageError(f'the helper\'s symbols were not read from {asm} (nasm, and the source that '
                             f'assembles to {os.path.basename(tsr_path)}, are needed)')
        else:
            print(f'  (helper symbols not read from {asm}: using the built-in table)')
        if seg_space is not None:
            for sel, paras in HELPER_MOVED.items():
                seg_override[sel] = TSR_PSP_SEG + 0x10 + seg_space // 16 + paras
    moved = 0
    modules = []
    tsr = load_tsr(mem, tsr_path) if tsr_path else None
    seg_next = tsr['next_seg'] if tsr else OVL_FIRST_SEG
    # Wake of the Ravager's 49 modules (3F29h paragraphs) and DSCLOG2 (1253h) don't fit together
    # between B000h and the BIOS's stubs (the helper lives in upper memory there, the overlays in
    # a buffer of conventional memory under DOS): a few modules go below the video memory instead,
    # at the top of conventional memory, which the game's then ends below (its PSP's "first
    # segment past ours", which runtime/dos.c's memory chain follows). The game took at most
    # 8240h paragraphs from 0800h in play, under 8A40h: the low area is far above that.
    low = set()
    top_of_dos = TOP_OF_DOS
    if tsr:
        sizes = []
        for r in (r for r in records if r['cls'] == 3):
            d = base + r['para'] * 16
            sizes.append((u16(mem, d + 8) + 15) >> 4)
        # (Shattered Lands' DSCLOG takes what is left, 91h paragraphs for its ring: nothing moves)
        short = seg_next + sum(sizes) + (UMB_WANT if len(exe) == WOTR_SIZE else 0) - BIOS_STUBS_SEG
        if short > 0:
            fits = sorted((n, i) for i, n in enumerate(sizes) if n >= short)
            if fits:
                low = {fits[0][1]}
            else:                                         # (the biggest, until they are enough)
                for n, i in sorted(((n, i) for i, n in enumerate(sizes)), reverse=True):
                    low.add(i)
                    if sum(sizes[j] for j in low) >= short:
                        break
            top_of_dos = TOP_OF_DOS - sum(sizes[j] for j in low)
    low_next = top_of_dos
    for r in (r for r in records if r['cls'] == 3):
        d = base + r['para'] * 16
        if bytes(mem[d:d + 4]) != b'\xCD\x3F\x00\x00':
            raise ImageError(f'segment table record {r["index"]}: no descriptor at {d:X}')
        payload = u32(mem, d + 4)
        size = u16(mem, d + 8)
        nreloc_bytes = u16(mem, d + 0x0A)
        nstubs = u32(mem, d + 0x0C)
        m = dict(index=len(modules), record=r['index'], stub_seg=r['seg'],
                 size=size, nstubs=nstubs, file=area + payload, seg=None,
                 stubs=[])
        modules.append(m)
        if size == 0:
            continue                                  # an empty slot
        seg = low_next if m['index'] in low else seg_next
        if seg > 0xFFFF or seg * 16 + size > MEM_SIZE or (tsr and seg_next >= BIOS_STUBS_SEG):
            raise ImageError('the overlay modules do not fit above the video memory')
        m['seg'] = seg
        code = exe[m['file']:m['file'] + size]
        lin = seg * 16
        mem[lin:lin + size] = code
        rel = exe[m['file'] + size:m['file'] + size + nreloc_bytes]
        for k in range(0, nreloc_bytes, 2):
            e = u16(rel, k)
            v = u16(mem, lin + e)
            if v & 1:
                raise ImageError(f'module {m["index"]}: marker-form relocation at +{e:X}')
            if (v & ~7) in seg_override:
                struct.pack_into('<H', mem, lin + e, seg_override[v & ~7])
                moved += 1
            else:
                struct.pack_into('<H', mem, lin + e, u16(mem, segtab_lin + (v & ~7)))
        for j in range(nstubs):
            s = d + 0x20 + 5 * j
            if mem[s:s + 2] != b'\xCD\x3F':
                raise ImageError(f'module {m["index"]} stub {j}: not an INT 3Fh stub')
            entry = u16(mem, s + 2)
            mem[s] = 0xEA                             # jmp far entry:seg
            struct.pack_into('<HH', mem, s + 1, entry, seg)
            m['stubs'].append(dict(stub=s, stub_off=s - r['seg'] * 16,
                                   entry=entry, target=lin + entry))
        struct.pack_into('<H', mem, d + 0x10, seg)    # descriptor: loaded here
        mem[d + 0x1A] |= 0x04                         # in use
        mem[d + 0x1B] = 1                             # locked
        if m['index'] in low:
            m['low'] = True
            low_next = seg + ((size + 15) >> 4)
        else:
            seg_next = seg + ((size + 15) >> 4)

    # The environment and the program segment prefix, as DOS leaves them.
    exe_name = os.path.basename(original or exe_path).upper().encode('ascii')
    env = b'COMSPEC=C:\\COMMAND.COM\0PATH=C:\\\0\0' + b'\x01\x00' + b'C:\\' + exe_name + b'\0'
    mem[ENV_SEG * 16:ENV_SEG * 16 + len(env)] = env
    p = PSP_SEG * 16
    mem[p:p + 2] = b'\xCD\x20'
    struct.pack_into('<H', mem, p + 2, top_of_dos)    # first segment past ours
    struct.pack_into('<H', mem, p + 0x2C, ENV_SEG)
    tail = (' ' + game_args if game_args else '').encode('ascii')
    mem[p + 0x80] = len(tail)
    mem[p + 0x81:p + 0x81 + len(tail)] = tail
    mem[p + 0x81 + len(tail)] = 0x0D
    for k in range(20):                               # job file table
        mem[p + 0x18 + k] = k if k < 5 else 0xFF

    dgroup = (u16(exe, hdr + 1) + load) & 0xFFFF      # `mov dx, DGROUP` first
    code_segs = [dict(seg=r['seg'], size=r['size'], record=r['index'])
                 for r in records if r['cls'] == 1 and r['size']]
    if not has_ovl:
        # Borland links the code segments first, DGROUP after them: every
        # segment a relocation names below DGROUP is code, up to the next.
        named = sorted({(u16(mem, a) + 0) & 0xFFFF for a in
                        (base + seg * 16 + off for off, seg in mz['relocs'])} | {(mz['cs'] + load) & 0xFFFF})
        named = [v for v in named if load <= v < dgroup] + [dgroup]
        code_segs = [dict(seg=v, size=(named[i + 1] - v) * 16, plain=True)
                     for i, v in enumerate(named[:-1])]
    code_segs += [dict(seg=m['seg'], size=m['size'], module=m['index'])
                  for m in modules if m['seg'] is not None]

    # Upper memory blocks for the helper (segment, paragraphs): what is left
    # below the BIOS area (the interrupt vectors' stubs start at F000:FE00),
    # and the HMA. Its ring takes the first (best fit), its panel the HMA.
    # Call sites whose return address the helper reads off the stack (its
    # SPREAD_GATHER knows a fight's end by the gather routine's caller): the
    # lifter pushes the real address there instead of its stand-in.
    real_returns = []
    if asm:
        if os.path.exists(asm):
            src = open(asm, encoding='latin-1').read()
            para = re.search(r'SPREAD_FROM_DS\s+equ\s+0x4356\s*-\s*0x([0-9A-Fa-f]+)', src)
            offs = re.findall(r'GATHER_FROM_FIGHT2?\s+equ\s+0x([0-9A-Fa-f]+)', src)
            if para and offs:
                cs = load + int(para.group(1), 16)
                real_returns = [f'{cs * 16 + int(o, 16):05X}' for o in offs]
            # ... and the calls DONE on the creation screen makes to the grant routines
            # (PSI_FROM_DONE, CR_FROM_DONE: the INT's way back, less the routine's into DONE): the
            # helper tells DONE's call from START GAME's by the return address under the INT's
            # frame, and with the stand-in there every new character got the game's powers and
            # spells, never its picks (2026-11-16). The second number is the return address, a
            # file offset in the creation overlay.
            for m_ in re.finditer(r'\w+_FROM_DONE\s+equ\s+0x([0-9A-Fa-f]+)\s*-\s*0x([0-9A-Fa-f]+)', src):
                file_off = int(m_.group(2), 16)
                for mod in modules:
                    if mod.get('seg') is not None and mod['file'] <= file_off < mod['file'] + mod['size']:
                        real_returns.append(f'{mod["seg"] * 16 + file_off - mod["file"]:05X}')
    # Where the helper jumps into the middle of a game routine: RS_TAIL, the die routine's
    # tail (a file offset in the creation overlay), reached by a far jump after a recall. The
    # lifter gives that address an entry of its own (tools/lift.py, recomp_enter_ip).
    interior_entries = []
    if asm and os.path.exists(asm):
        for m_ in re.finditer(r'RS_TAIL\s+equ\s+0x([0-9A-Fa-f]+)\s*-\s*0x([0-9A-Fa-f]+)', src):
            file_off = int(m_.group(1), 16)
            for mod in modules:
                if mod.get('seg') is not None and mod['file'] <= file_off < mod['file'] + mod['size']:
                    interior_entries.append(f'{mod["seg"] * 16 + file_off - mod["file"]:05X}')
    umb = [[seg_next, BIOS_STUBS_SEG - seg_next], [0xFFFF, 0x0FFF]] if tsr else []
    if tsr:
        tsr['moved_relocs'] = moved
        tsr['inline_args'] = {f'{tsr["load"] * 16 + off:05X}': n for off, n in inline_args.items()}
        tsr['inline_plain_sites'] = [f'{tsr["load"] * 16 + off:05X}' for off in sorted(plain_sites)]
        tsr['seg_space'] = seg_space
    if tsr:
        # The helper's code: its segment, its tail (code run with CS the tail's segment, through
        # TAIL_CALL and PL_CALL, after the tables) and, for DSCLOG2, its install, which runs from a
        # segment of its own past the rest (the MZ header's CS). From its sections (nasm's map);
        # without them, one segment as before.
        secs = helper_symbols.sections(asm, tsr_path) if asm and os.path.exists(asm) else None
        tsr['end'] = tsr['image'][1]
        if secs and 'image' in secs:
            code_segs.append(dict(seg=tsr['load'], size=secs['image'][1], tsr=True))
            if 'tail' in secs:
                t_off = secs['tail'][0]
                t_len = sum(secs[k][1] for k in ('tail', 'tailz') if k in secs)
                code_segs.append(dict(seg=tsr['load'] + t_off // 16, size=t_len, tsr=True, tail=True))
                tsr['end'] = tsr['load'] * 16 + t_off + t_len
            if tsr['cs'] != tsr['load']:
                code_segs.append(dict(seg=tsr['cs'], size=tsr['image'][1] - tsr['cs'] * 16, tsr=True, install=True))
        elif tsr['cs'] != tsr['load']:
            raise ImageError(f'{tsr["exe"]}: its sections were not read (nasm and its source are needed)')
        else:
            code_segs.append(dict(seg=tsr['cs'], size=tsr['image'][1] - tsr['image'][0], tsr=True))
        tsr['segs'] = [s['seg'] for s in code_segs if s.get('tsr')]
    sites, vectors, applied, originals = mod_sites(mod_dir, exe, hdr, base, modules) if mod_dir else ({}, [], 0, {})

    layout = dict(
        exe=os.path.basename(original or exe_path), exe_size=len(exe),
        disk_size=os.path.getsize(original) if original else len(exe),
        tsr=tsr, mod=dict(dir=os.path.abspath(mod_dir), patches=applied, vectors=vectors) if mod_dir else None,
        int_sites=sites, int_originals=originals, real_returns=real_returns, interior_entries=interior_entries,
        psp_seg=PSP_SEG, load_seg=load, env_seg=ENV_SEG, top_of_dos=top_of_dos,
        resident=[base, res_end],
        entry=dict(cs=(mz['cs'] + load) & 0xFFFF, ip=mz['ip']),
        stack=dict(ss=(mz['ss'] + load) & 0xFFFF, sp=mz['sp']),
        dgroup=dgroup,
        segtab=segtab_lin, records=records, code_segments=code_segs,
        relocs=sorted(base + seg * 16 + off for off, seg in mz['relocs']),
        modules=modules,
        overlay_top=seg_next * 16, umb=umb,
    )
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'image.bin'), 'wb') as f:
        f.write(mem)
    with open(os.path.join(out_dir, 'layout.json'), 'w') as f:
        json.dump(layout, f, indent=1)
    return layout


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('exe', help="the game's DSUN.EXE (read only)")
    ap.add_argument('--out', default='build/ds1', help='output folder')
    ap.add_argument('--args', default='', help='command tail for the PSP')
    ap.add_argument('--tsr', help='a resident helper to load first (the mod\'s DSCLOG.EXE)')
    ap.add_argument('--mod', help="the mod's obsidian-edition folder (its dsloader/gamepatch.py names the INT sites)")
    ap.add_argument('--original', help='the file as the game folder has it, when exe is an unpacked copy (tools/unlzexe.py)')
    a = ap.parse_args(argv)
    try:
        lay = build(a.exe, a.out, a.args, a.tsr, a.mod, a.original)
    except ImageError as e:
        sys.exit(f'build_image: {e}')
    live = [m for m in lay['modules'] if m['seg'] is not None]
    print(f"{lay['exe']}: resident {lay['resident'][0]:05X}-{lay['resident'][1]:05X}, "
          f"entry {lay['entry']['cs']:04X}:{lay['entry']['ip']:04X}, "
          f"DGROUP {lay['dgroup']:04X}")
    print(f"  {len(live)} overlay modules at {OVL_FIRST_SEG:04X}0-{lay['overlay_top']:05X}, "
          f"{sum(m['nstubs'] for m in live)} stubs patched")
    lows = [m for m in live if m.get('low')]
    if lows:
        print(f"  {len(lows)} of them below the video memory, from {lay['top_of_dos']:04X}0 (modules "
              f"{', '.join(str(m['index']) for m in lows)}): the game's memory ends there")
    print(f"  {len(lay['code_segments'])} code segments")
    if lay['tsr']:
        t = lay['tsr']
        print(f"  helper {t['exe']} at {t['psp']:04X}, entry {t['cs']:04X}:{t['ip']:04X}; "
              f"{t['moved_relocs']} overlay references moved to its seg_space; "
              f"inline-argument routines at {', '.join(sorted(t['inline_args']))}")
    if lay['mod']:
        print(f"  mod: {lay['mod']['patches']} patches in the EXE, {len(lay['int_sites'])} INT sites with data after them, "
              f"{len(lay['mod']['vectors'])} vectors")


if __name__ == '__main__':
    main()
