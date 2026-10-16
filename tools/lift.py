#!/usr/bin/env python3
"""Translate every function in functions.json to C, with pcrecomp's lift16.

Each function is decoded against its code segment's base, so its
instructions' addresses are IPs and the lifter's func_start is the segment's
linear base. Functions are named by linear entry address (fn_C30F0 lives at
C30F:0000 + ...). Far calls to an overlay entry stub go straight to the code
the stub jumps to, since every module stays where build_image.py put it.

Output: build/<game>/gen/recomp_NNN.c, recomp_all.h, recomp_dispatch.c
"""
import argparse
import json
import os

from dsimage import Image
import lift16
from lift16 import Lifter

CHUNK = 80

# Routines replaced by C in runtime/native.c rather than lifted (by linear
# entry, per game). Each says why.
NATIVE = {}


def name_of(lin):
    return f'fn_{lin:05X}'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('build', nargs='?', default='build/ds1')
    a = ap.parse_args(argv)
    img = Image(a.build)
    funcs = {int(k, 16): v for k, v in
             json.load(open(os.path.join(a.build, 'functions.json'))).items()}

    known = {lin: name_of(lin) for lin in funcs}
    for stub, target in img.stub_target.items():
        if target in known:
            known[stub] = known[target]

    out = os.path.join(a.build, 'gen')
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.startswith('recomp_') and f.endswith('.c'):
            os.remove(os.path.join(out, f))

    lift16.DIV0_FN = 'recomp_div0'
    bodies, calls, segs, failed, unhandled = [], set(), set(), 0, 0
    for lin in sorted(funcs):
        f = funcs[lin]
        cs = f['cs']
        segs.add(cs)
        name = name_of(lin)
        if lin in NATIVE:
            continue
        insns = []
        for ip in f['ips']:
            ins = img.decode_at(cs, ip)
            ins.address = ip
            ins.offset = cs * 16 + ip
            insns.append(ins)
        lf = Lifter(known_funcs=known)
        lf.dispatch = True
        lf.far_base = 0
        lf.iret_frame = True
        lf.unwind_sp = True
        lift16._CODE_SEG = f'{cs:04X}'
        lf.jump_tables = {int(ip): [cs * 16 + arm for arm in arms]
                          for ip, arms in f['tables'].items()}
        entry_ip = lin - cs * 16
        try:
            body = lf.lift_function(name, insns, cs * 16, is_far=True,
                                    entry_addr=entry_ip if insns[0].address != entry_ip else None)
        except Exception as e:                      # keep going; report it
            failed += 1
            body = (f'/* {name}: lift failed: {e!r} */\n'
                    f'void {name}(CPU *cpu) {{ recomp_unlifted(cpu, 0x{lin:05X}); }}')
        unhandled += body.count('UNHANDLED') + body.count('/* FPU:')
        body = body.replace('(CPU *cpu)\n{', f'(CPU *cpu)\n{{\n    cpu->cs = 0x{cs:04X};', 1)
        bodies.append(body)
        calls |= lf.func_calls

    names = sorted(set(known.values()))
    stubs = sorted(c for c in calls if c not in names)

    for i in range(0, len(bodies), CHUNK):
        with open(os.path.join(out, f'recomp_{i // CHUNK:03d}.c'), 'w') as fh:
            fh.write('#include "recomp_all.h"\n\n' + '\n\n'.join(bodies[i:i + CHUNK]) + '\n')

    with open(os.path.join(out, 'recomp_all.h'), 'w') as fh:
        fh.write('#ifndef RECOMP_ALL_H\n#define RECOMP_ALL_H\n#include "runtime.h"\n\n')
        for s in sorted(segs):
            fh.write(f'#define SEG_{s:04X} 0x{s:04X}\n')
        for n in names + stubs:
            fh.write(f'void {n}(CPU *cpu);\n')
        fh.write('#endif\n')

    lay = img.layout
    with open(os.path.join(out, 'layout.h'), 'w') as fh:
        fh.write('/* written by tools/lift.py from layout.json */\n')
        fh.write(f'#define GAME_EXE "{lay["exe"]}"\n')
        fh.write(f'#define GAME_PSP 0x{lay["psp_seg"]:04X}\n')
        fh.write(f'#define GAME_ENTRY_CS 0x{lay["entry"]["cs"]:04X}\n')
        fh.write(f'#define GAME_ENTRY_IP 0x{lay["entry"]["ip"]:04X}\n')
        fh.write(f'#define GAME_SS 0x{lay["stack"]["ss"]:04X}\n')
        fh.write(f'#define GAME_SP 0x{lay["stack"]["sp"]:04X}\n')

    with open(os.path.join(out, 'recomp_dispatch.c'), 'w') as fh:
        fh.write('#include "recomp_all.h"\n\n')
        entries = sorted(known.items())
        fh.write(f'const DispEntry g_dispatch[{len(entries)}] = {{\n')
        for lin, n in entries:
            fh.write(f'  {{0x{lin:05X}, {n}}},\n')
        fh.write('};\n')
        fh.write(f'const int g_dispatch_n = {len(entries)};\n\n')
        for s in stubs:
            # A call to something no function covers: say so at run time,
            # and keep the stack balanced the way the call site expects.
            pop = 4 if s.startswith('far_') else 2
            fh.write(f'void {s}(CPU *cpu) {{ recomp_missing(cpu, "{s}"); cpu->sp += {pop}; }}\n')

    print(f'lifted {len(bodies)} functions into {(len(bodies) + CHUNK - 1) // CHUNK} files; '
          f'{failed} failed, {unhandled} unhandled instructions, '
          f'{len(stubs)} unresolved call targets, {len(segs)} code segments')


if __name__ == '__main__':
    main()
