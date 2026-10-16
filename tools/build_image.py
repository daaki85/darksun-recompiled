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
import struct
import sys

MEM_SIZE = 0x110000          # 1 MB + the HMA, as runtime/cpu.h allocates
PSP_SEG = 0x0800             # program segment prefix; the image follows it
ENV_SEG = 0x07E0             # the environment block, just below the PSP
OVL_FIRST_SEG = 0xC000       # overlay modules from here up (no EMS page frame)
TOP_OF_DOS = 0xA000          # end of conventional memory


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


def build(exe_path, out_dir, game_args=''):
    exe = open(exe_path, 'rb').read()
    mz = parse_mz(exe)
    hdr, image_end = mz['hdr'], mz['image_end']
    if exe[image_end:image_end + 4] != b'FBOV':
        raise ImageError('no Borland overlay (FBOV) header after the image')
    ovrsize, exeinfo, segnum = struct.unpack_from('<3I', exe, image_end + 4)
    area = ((image_end + 15) & ~15) + 16          # overlay area base (file offset)

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
    segtab_lin = base + (exeinfo - hdr)
    records = []
    for i in range(segnum):
        para, size, cls, x = struct.unpack_from('<4H', exe, exeinfo + 8 * i)
        records.append(dict(index=i, para=para, seg=(para + load) & 0xFFFF,
                            size=size, cls=cls, x=x))

    # Class-3 records are the overlay stub blocks; each begins with its
    # module's 32-byte descriptor, then 5-byte stubs. They pair 1:1, in order,
    # with the modules.
    modules = []
    seg_next = OVL_FIRST_SEG
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
        seg = seg_next
        if seg > 0xFFFF or seg * 16 + size > MEM_SIZE:
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
        seg_next = seg + ((size + 15) >> 4)

    # The environment and the program segment prefix, as DOS leaves them.
    env = b'COMSPEC=C:\\COMMAND.COM\0PATH=C:\\\0\0' + b'\x01\x00' + b'C:\\DSUN.EXE\0'
    mem[ENV_SEG * 16:ENV_SEG * 16 + len(env)] = env
    p = PSP_SEG * 16
    mem[p:p + 2] = b'\xCD\x20'
    struct.pack_into('<H', mem, p + 2, TOP_OF_DOS)    # first segment past ours
    struct.pack_into('<H', mem, p + 0x2C, ENV_SEG)
    tail = (' ' + game_args if game_args else '').encode('ascii')
    mem[p + 0x80] = len(tail)
    mem[p + 0x81:p + 0x81 + len(tail)] = tail
    mem[p + 0x81 + len(tail)] = 0x0D
    for k in range(20):                               # job file table
        mem[p + 0x18 + k] = k if k < 5 else 0xFF

    code_segs = [dict(seg=r['seg'], size=r['size'], record=r['index'])
                 for r in records if r['cls'] == 1 and r['size']]
    code_segs += [dict(seg=m['seg'], size=m['size'], module=m['index'])
                  for m in modules if m['seg'] is not None]

    layout = dict(
        exe=os.path.basename(exe_path), exe_size=len(exe),
        psp_seg=PSP_SEG, load_seg=load, env_seg=ENV_SEG, top_of_dos=TOP_OF_DOS,
        resident=[base, res_end],
        entry=dict(cs=(mz['cs'] + load) & 0xFFFF, ip=mz['ip']),
        stack=dict(ss=(mz['ss'] + load) & 0xFFFF, sp=mz['sp']),
        dgroup=(u16(exe, hdr + 1) + load) & 0xFFFF,   # `mov dx, DGROUP` first
        segtab=segtab_lin, records=records, code_segments=code_segs,
        relocs=sorted(base + seg * 16 + off for off, seg in mz['relocs']),
        modules=modules,
        overlay_top=seg_next * 16,
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
    a = ap.parse_args(argv)
    try:
        lay = build(a.exe, a.out, a.args)
    except ImageError as e:
        sys.exit(f'build_image: {e}')
    live = [m for m in lay['modules'] if m['seg'] is not None]
    print(f"{lay['exe']}: resident {lay['resident'][0]:05X}-{lay['resident'][1]:05X}, "
          f"entry {lay['entry']['cs']:04X}:{lay['entry']['ip']:04X}, "
          f"DGROUP {lay['dgroup']:04X}")
    print(f"  {len(live)} overlay modules at {OVL_FIRST_SEG:04X}0-{lay['overlay_top']:05X}, "
          f"{sum(m['nstubs'] for m in live)} stubs patched")
    print(f"  {len(lay['code_segments'])} code segments")


if __name__ == '__main__':
    main()
