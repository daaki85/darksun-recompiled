#!/usr/bin/env python3
"""Translate the game's Miles AIL 2 drivers (.ADV, in RESOURCE.GFF) to C.

The sound library loads a driver into heap memory and far-calls its functions,
so the driver is code like the game's, only loaded where the build cannot know.
Each driver is lifted against a code segment that is a variable (SEG_DRVnn, set
by the runtime to the segment the game loaded it at), from the entries in its
own function table, by the same recursive descent as the game's functions.

At run time (runtime/aildrv.c) a far call into heap memory that holds one of
these images, byte for byte, runs the lifted function at that offset.

Output: build/<game>/gen/drv_NN.c and drivers.h
"""
import argparse
import os
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsimage import Decoder, OpType        # noqa: E402  (sets up pcrecomp's paths)
import gff                                 # noqa: E402
import lift16                              # noqa: E402
from lift16 import Lifter                  # noqa: E402
from find_funcs import Finder              # noqa: E402

SIG_LEN = 256          # bytes compared to recognise a loaded driver


class DriverImage:
    """Just enough of dsimage.Image for find_funcs.Finder.body()."""

    def __init__(self, blob):
        self.mem = blob + bytes(0x10000 - len(blob))
        self.segs = []                  # no far-pointer tables inside a driver
        self.stub_target = {}
        self.layout = {}
        self._dec = Decoder(self.mem, base_offset=0)

    def seg_of(self, lin):
        return 0 if lin < 0x10000 else None

    def decoder(self, cs):
        return self._dec

    def decode_at(self, cs, ip):
        self._dec.pos = ip
        try:
            return self._dec.decode_one()
        except (IndexError, KeyError):
            return None

    def u16(self, lin):
        return self.mem[lin] | (self.mem[lin + 1] << 8)


def lift_driver(cid, blob, out):
    img = DriverImage(blob)
    table = img.u16(0)
    entries = {}
    for i in range(64):
        fn, off = img.u16(table + 4 * i), img.u16(table + 4 * i + 2)
        if fn == 0xFFFF:
            break
        entries[off] = fn
    f = Finder(img)
    for off in entries:
        f.seed(off, 0, 'table')
    while True:                                   # bodies add near-call targets
        before = len(f.entries)
        funcs = {}
        for lin in sorted(f.entries):
            body, calls = f.body(lin, 0)
            funcs[lin] = body
            for c in calls:
                if c < len(blob):
                    f.seed(c, 0, 'call')
        if len(f.entries) == before:
            break
    # The lifter names the code segment SEG_<hex> and does arithmetic on the
    # hex, so the driver gets a pretend segment no game segment can be (the
    # overlays end below FE00), and the macro is pointed at the real one.
    pseg = 0xFF00 + cid
    seg = f'{pseg:04X}'
    base = pseg * 16
    lift16._CODE_SEG = seg
    known = {base + lin: f'drv{cid:02d}_{lin:04X}' for lin in funcs}
    bodies = []
    for lin in sorted(funcs):
        insns = []
        for ip in funcs[lin]['ips']:
            ins = img.decode_at(0, ip)
            ins.address, ins.offset = ip, ip
            insns.append(ins)
        lf = Lifter(known_funcs=known)
        lf.dispatch, lf.far_base, lf.iret_frame = True, 0, True
        lf.jump_tables = {int(ip): [base + a for a in arms] for ip, arms in funcs[lin]['tables'].items()}
        name = known[base + lin]
        body = lf.lift_function(name, insns, base, is_far=True,
                                entry_addr=lin if insns[0].address != lin else None)
        body = body.replace('(CPU *cpu)\n{', f'(CPU *cpu)\n{{\n    cpu->cs = SEG_{seg};', 1)
        bodies.append(body)
    with open(os.path.join(out, f'drv_{cid:02d}.c'), 'w') as fh:
        fh.write('#include "recomp_all.h"\n#include "drivers.h"\n\n')
        fh.write(f'#undef SEG_{seg}\n#define SEG_{seg} (g_drv_seg[{cid}])\n\n')
        for n in known.values():
            fh.write(f'void {n}(CPU *cpu);\n')
        fh.write('\n' + '\n\n'.join(bodies) + '\n\n')
        fh.write(f'const DrvEntry g_drv{cid:02d}_fns[] = {{\n')
        for lin in sorted(known):
            fh.write(f'  {{0x{lin - base:04X}, {known[lin]}}},\n')
        fh.write('  {0xFFFF, 0}\n};\n')
    return len(funcs), zlib.crc32(blob[:SIG_LEN]), len(blob)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('resource', help="the game's RESOURCE.GFF (read only)")
    ap.add_argument('build', nargs='?', default='build/ds1')
    a = ap.parse_args(argv)
    out = os.path.join(a.build, 'gen')
    os.makedirs(out, exist_ok=True)
    for name in os.listdir(out):
        if name.startswith('drv_') and name.endswith('.c'):
            os.remove(os.path.join(out, name))
    chunks = gff.chunks(a.resource)
    data = open(a.resource, 'rb').read()
    done = []
    for (fourcc, cid), (off, ln) in sorted(chunks.items()):
        if fourcc != 'ADV ':
            continue
        blob = data[off:off + ln]
        if b'Miles Design' not in blob[:64] or len(blob) > 0xFFF0:
            continue                       # not an AIL driver we can lift as one
        n, crc, size = lift_driver(cid, blob, out)
        done.append((cid, crc, size, n))
    with open(os.path.join(out, 'drivers.h'), 'w') as fh:
        fh.write('/* written by tools/lift_drivers.py */\n#ifndef DRIVERS_H\n#define DRIVERS_H\n')
        fh.write('#include "runtime.h"\n')
        fh.write('typedef struct { unsigned off; recomp_fn fn; } DrvEntry;\n')
        fh.write('extern uint16_t g_drv_seg[64];\n')
        for cid, _, _, _ in done:
            fh.write(f'extern const DrvEntry g_drv{cid:02d}_fns[];\n')
        fh.write('typedef struct { int id; uint32_t crc; unsigned size; const DrvEntry *fns; } DrvImage;\n')
        fh.write(f'#define SIG_LEN {SIG_LEN}\n')
        fh.write('static const DrvImage g_drivers[] = {\n')
        for cid, crc, size, _ in done:
            fh.write(f'  {{{cid}, 0x{crc:08X}u, {size}, g_drv{cid:02d}_fns}},\n')
        fh.write('};\n#endif\n')
    print(f'{len(done)} drivers lifted: ' + ', '.join(f'ADV {c} ({n} functions)' for c, _, _, n in done))


if __name__ == '__main__':
    main()
