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

from dsimage import Image, OpType
from decode16 import Instruction, Operand
import lift16
from lift16 import Lifter

CHUNK = 80

# One program holds both games, so every generated symbol carries the game's
# tag; the runtime picks a game by the size of the DSUN.EXE it is pointed at.
GAMES = {
    611408: ('ds1', 'Dark Sun: Shattered Lands'),
    634416: ('ds2', 'Dark Sun: Wake of the Ravager'),
    70288: ('ct', 'Dark Sun: character transfer'),      # CHARTRAN.EXE unpacked (tools/unlzexe.py)
}
TAG = 'ds1'

# Routines answered by a few lines of C instead of being lifted, by linear
# entry and by the EXE's size (one table per game). Each is
# (C body, why). Far routines end in `cpu->sp += 4`: the caller pushed CS:IP.
NATIVE = {
    611408: {   # Shattered Lands, GOG 1.10
        0x3F35A: ('cpu->ax = 0; cpu->sp += 4;',
                  'VROOMM init (3E63:0D2A, from _INIT_): every module is already '
                  'in place and its stubs patched, so the manager must not install '
                  'INT 3Fh or take over the descriptors'),
        0x3EF1E: ('cpu->ax = 0; cpu->sp += 4;',
                  'VROOMM: cache overlays in expanded/extended memory -- nothing to cache'),
        0x3F0E8: ('cpu->ax = 0; cpu->sp += 4;',
                  'VROOMM: the other memory-cache set-up, same reason'),
    },
    634416: {   # Wake of the Ravager, GOG 1.1: the same three routines, found by their bytes
        0x43C77: ('cpu->ax = 0; cpu->sp += 4;', 'VROOMM init (from _INIT_)'),
        0x4383B: ('cpu->ax = 0; cpu->sp += 4;', 'VROOMM: cache overlays in EMS/XMS'),
        0x43A05: ('cpu->ax = 0; cpu->sp += 4;', 'VROOMM: the other memory-cache set-up'),
    },
}


# Functions that move the stack on purpose, left out of the --spcheck audit.
SP_OK = {
    611408: {
        0x08799,   # Borland's struct-by-value push: makes room below its return address
        0x09E3A, 0x08320,   # the start-up's argv/env builders
    },
    634416: {               # Wake of the Ravager: the same run-time
        0x08799,
        0x0A977, 0x08320,
    },
}


def name_of(lin):
    return f'{TAG}_fn_{lin:05X}'


class SiteLifter(Lifter):
    """The mod's INT sites: the helper's handler may step over data after the
    INT, or send the game on elsewhere by changing the return address in the
    interrupt frame. The lifted iret records where it returned to (cpu->cs:ip);
    after the INT the code compares that with the address it expects and, when
    they differ, jumps there through a switch over the function's labels (or
    dispatches, for an address outside the function)."""

    def __init__(self, known_funcs, sites, seg, real_returns=False):
        super().__init__(known_funcs=known_funcs)
        self.sites = sites          # function-relative IPs of the INT sites
        self.seg = seg
        self.used = False
        # The helper's near calls push their real return address: some of its
        # routines read an argument byte after the call through it (and one
        # recognises its caller by it) before returning past it.
        self.real_returns = real_returns

    def lift_instruction(self, inst, func_start):
        if (self.real_returns and inst.mnemonic == 'call' and inst.op1 and inst.op1.type == OpType.REL16
                and (func_start + (inst.op1.disp & 0xFFFF)) in self.known_funcs):
            target = self.known_funcs[func_start + (inst.op1.disp & 0xFFFF)]
            ret = (inst.address + 3) & 0xFFFF           # the byte after the call itself
            back = (inst.address + inst.length) & 0xFFFF  # where the callee comes back to: past any argument byte
            self._emit_label(inst.address)
            # The callee says where it came back to (its lifted ret pops the
            # address into cpu->ip): a routine that pops the return address and
            # jumps through it later (TEXT_ENTER) has run the rest of this
            # function already, and the iret at the end of that left the game's
            # address there; carrying on here would run it a second time.
            self._emit(f'cpu->cs = SEG_{self.seg:04X}; cpu->ip = 0x{back:04X};', 'where a ret comes back to')
            self._emit(f'push16(cpu, 0x{ret:04X});', 'near call: the real return address')
            self._emit(f'{target}(cpu);', f'call {inst.op1!r}')
            self.func_calls.add(target)
            if getattr(self, 'unwind_sp', False):
                self._emit('if (cpu->ss == _ss0 && (int16_t)(cpu->sp - _sp0) > 0) return;', 'a callee unwound past this frame')
            # (IP alone: a far call the callee made into the game leaves cpu->cs
            # the game's, and a near ret cannot change the segment)
            self._emit(f'if (cpu->ip != 0x{back:04X}) goto resume_{self.func_name}; cpu->cs = SEG_{self.seg:04X};',
                       'the callee went on elsewhere')
            self.used = True
            return
        if self.real_returns and inst.mnemonic == 'ret':
            # the real return address popped: the caller checks it
            self._emit_label(inst.address)
            extra = f' cpu->sp += 0x{inst.op1.disp:X};' if inst.op1 else ''
            self._emit(f'cpu->ip = pop16(cpu);{extra} return;', 'ret' + (f' 0x{inst.op1.disp:X}' if inst.op1 else ''))
            return
        if inst.mnemonic == 'int' and inst.op1 and inst.op1.disp != 0x3F:
            # Every INT's frame carries the real return address: a handler
            # that returns with `retf 2` instead of iret (the mod's pointer
            # probe does) dispatches to it, and a stale IP there is a jump
            # into whatever happens to be at that address.
            nxt = (inst.address + inst.length) & 0xFFFF     # after the INT and any data the handler steps over
            frame_ip = (inst.address + 2) & 0xFFFF           # what the CPU would push: right after the INT itself
            self._emit_label(inst.address)              # (before the assignment: a jump here must set them too)
            self._emit(f'cpu->cs = SEG_{self.seg:04X}; cpu->ip = 0x{frame_ip:04X};', 'the return address the frame carries')
            super().lift_instruction(inst, func_start)
            if inst.address in self.sites:
                self._emit(f'if (cpu->ip != 0x{nxt:04X} || cpu->cs != SEG_{self.seg:04X}) goto resume_{self.func_name};',
                           'the handler moved the return address')
                self.used = True
        else:
            super().lift_instruction(inst, func_start)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('build', nargs='?', default='build/ds1')
    ap.add_argument('--spcheck', action='store_true',
                    help='wrap every function to report the ones that leave the guest stack unbalanced')
    a = ap.parse_args(argv)
    img = Image(a.build)
    funcs = {int(k, 16): v for k, v in
             json.load(open(os.path.join(a.build, 'functions.json'))).items()}

    global TAG
    exe_size = img.layout['exe_size']
    TAG, title = GAMES.get(exe_size, (f'x{exe_size}', os.path.basename(img.layout['exe'])))
    if img.layout.get('mod'):
        TAG += 'o'                    # the mod's build of the game: its own entry beside the plain one
    native = NATIVE.get(exe_size, {})
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
    bodies, calls, segs, failed, unhandled, overlaps = [], set(), set(), 0, 0, 0
    ranges = []                                 # [start, end) of each function's code
    for lin in sorted(funcs):
        f = funcs[lin]
        cs = f['cs']
        segs.add(cs)
        name = name_of(lin)
        if lin in native:
            code, why = native[lin]
            bodies.append(f'/* {why} */\nvoid {name}(CPU *cpu)\n{{\n    RECOMP_ENTER("{name}");\n    {code}\n}}')
            continue
        insns = []
        for ip in f['ips']:
            ins = img.decode_at(cs, ip)
            ins.address = ip
            ins.offset = cs * 16 + ip
            insns.append(ins)
        ranges.append((lin, cs * 16 + max(i.address + i.length for i in insns)))
        # Every instruction that can fall through must be followed by the one
        # it falls into: the lifter emits them in order and C falls through.
        # Where it does not (code that jumps into the middle of an instruction,
        # so two decodings overlap), make the fall-through an explicit jump.
        ends = {'ret', 'retf', 'iret', 'hlt', 'jmp', 'jmp far'}
        fixed = []
        for i, ins in enumerate(insns):
            fixed.append(ins)
            nxt = (ins.address + ins.length) & 0xFFFF
            if ins.mnemonic in ends or (i + 1 < len(insns) and insns[i + 1].address == nxt):
                continue
            j = Instruction()
            j.mnemonic, j.address, j.offset, j.length, j.raw = 'jmp', -1, -1, 0, b''
            j.op1 = Operand(type=OpType.REL16, disp=nxt, size=2)
            fixed.append(j)
            overlaps += 1
        insns = fixed
        # every INT of the mod's gets the resume check: any handler may move the return address
        sites_here = {i.address for i in insns if i.mnemonic == 'int' and i.op1 and i.op1.disp in img.mod_vectors}
        lf = SiteLifter(known, sites_here, cs, real_returns=(cs == img.tsr_cs))
        lf.dispatch = True
        lf.far_base = 0
        lf.iret_frame = True
        # The "callee unwound past this frame" check after calls is for the
        # game's code; the helper's handlers pop their interrupt frame before
        # calling anything, which puts SP above their entry value and made
        # the check return from them early.
        lf.unwind_sp = cs != img.tsr_cs
        lift16._CODE_SEG = f'{cs:04X}'
        lf.jump_tables = {int(ip): [cs * 16 + arm for arm in arms]
                          for ip, arms in f['tables'].items()}
        resumes = bool(sites_here) or cs == img.tsr_cs      # (the helper's near calls check their return too)
        if resumes:                 # every instruction gets a label: the resume switch needs them
            lf.jump_tables[-1] = [cs * 16 + ip for ip in f['ips']]
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
        # a far return to a real address goes through recomp_return (a tail
        # call, or the mod's helper sending the game on)
        body = body.replace('recomp_dispatch(cpu,_cs,_ip); return; } /* retf', 'recomp_return(cpu,_cs,_ip); return; } /* retf')
        if cs == img.tsr_cs:
            # The helper's retf popping the lifter's sentinel: the routine it stands in for
            # (rand, patched to start with an INT) has returned to its C caller; the game
            # function the INT is in must return too (recomp_return knows the sentinel).
            body = body.replace('if (_ip != 0xFFFF && _ip != 0) recomp_return(cpu,_cs,_ip); return; } /* retf',
                                'if (_ip == 0xFFFF) { cpu->cs = _cs; cpu->ip = 0xFFFF; } else if (_ip != 0) recomp_return(cpu,_cs,_ip); return; } /* retf')
        # an indirect far jump is the same thing (the helper jumps back into the game that way)
        body = '\n'.join(l.replace('recomp_dispatch(cpu, ', 'recomp_return(cpu, ', 1) if '/* jmp far' in l else l
                         for l in body.split('\n'))
        # an iret says where it went back to (the mod's handlers move it)
        body = body.replace('cpu->sp += 4; cpu->flags = pop16(cpu); return; /* iret */',
                            'cpu->ip = pop16(cpu); cpu->cs = pop16(cpu); cpu->flags = pop16(cpu); return; /* iret */')
        if resumes and getattr(lf, 'used', False):
            cases = ''.join(f'        case 0x{ip:04X}: goto L_{name}_{ip:06X};\n' for ip in f['ips'])
            # Sent outside this function (into the helper, usually): run that code; when it
            # comes back having moved CS:IP into this function, carry on there. An address
            # in the middle of the game's code (an iret's, run on the helper's behalf) is
            # left for the caller (recomp_return).
            block = (f'resume_{name}:\n'
                     f'    if (cpu->ip != 0xFFFF) trace("[resume] {name} -> %04X:%04X (ss:sp %04X:%04X)\\n", cpu->cs, cpu->ip, cpu->ss, cpu->sp);\n'
                     f'    if (cpu->cs == SEG_{cs:04X}) switch (cpu->ip) {{\n{cases}        default: break;\n    }}\n'
                     f'    {{ uint16_t _c = cpu->cs, _i = cpu->ip; recomp_return(cpu, _c, _i);\n'
                     f'      if ((cpu->cs != _c || cpu->ip != _i) && cpu->cs == SEG_{cs:04X}) goto resume_{name}; }}\n'
                     f'    return;\n')
            k = body.rfind('\n}')
            body = body[:k + 1] + block + body[k + 1:]
        if a.spcheck and lin not in SP_OK.get(img.layout['exe_size'], ()):
            body = body.replace(f'void {name}(CPU *cpu)', f'static void {name}__body(CPU *cpu)', 1)
            body += (f'\nvoid {name}(CPU *cpu) {{ uint16_t _s = cpu->sp, _ss = cpu->ss, _bp = cpu->bp; '
                     f'{name}__body(cpu); recomp_sp_check(0x{lin:05X}, _s, _ss, _bp, cpu); }}')
        bodies.append(body)
        calls |= lf.func_calls

    names = sorted(set(known.values()))
    stubs = sorted(c for c in calls if c not in names)

    for i in range(0, len(bodies), CHUNK):
        with open(os.path.join(out, f'recomp_{i // CHUNK:03d}.c'), 'w') as fh:
            fh.write('#include "recomp_all.h"\n\n' + '\n\n'.join(bodies[i:i + CHUNK]) + '\n')

    with open(os.path.join(out, 'recomp_all.h'), 'w') as fh:
        fh.write('#ifndef RECOMP_ALL_H\n#define RECOMP_ALL_H\n#include "runtime.h"\n\n')
        fh.write('void recomp_sp_check(unsigned fn, uint16_t sp0, uint16_t ss0, uint16_t bp0, CPU *cpu);\n')
        for s in sorted(segs):
            fh.write(f'#define SEG_{s:04X} 0x{s:04X}\n')
        for n in names + stubs:
            fh.write(f'void {n}(CPU *cpu);\n')
        fh.write(f'extern const DrvImage {TAG}_drivers[];\nextern const int {TAG}_ndrivers;\n')
        fh.write('#endif\n')
    with open(os.path.join(out, 'tag.txt'), 'w') as fh:     # read by CMakeLists.txt
        fh.write(TAG + '\n')

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
        fh.write(f'static const DispEntry dispatch[{len(entries)}] = {{\n')
        for lin, n in entries:
            fh.write(f'  {{0x{lin:05X}, {n}}},\n')
        fh.write('};\n\n')
        # merged into non-overlapping stretches (functions nest and overlap),
        # so the runtime's binary search over them is sound
        merged = []
        for start, end in sorted(ranges):
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        ranges = merged
        fh.write(f'static const unsigned ranges[{len(ranges)}][2] = {{\n')
        for start, end in ranges:
            fh.write(f'  {{0x{start:05X}, 0x{end:05X}}},\n')
        fh.write('};\n\n')
        umb = lay.get('umb') or []
        fh.write('static const uint16_t umb[][2] = {\n' + ''.join(f'  {{0x{s:04X}, 0x{n:04X}}},\n' for s, n in umb)
                 + ('  {0, 0},\n' if not umb else '') + '};\n\n')
        cd = 'cd' if TAG == 'ds2' else ''
        mod = lay.get('mod')
        tsr = lay.get('tsr') or dict(psp=0, cs=0, ip=0, ss=0, sp=0)
        if mod:
            title += ' (Obsidian Edition)'
        fh.write(f'const GameDesc {TAG}_game = {{\n'
                 f'    "{TAG}", "{title}", "{lay["exe"]}", {lay.get("disk_size", exe_size)},\n'
                 f'    0x{lay["psp_seg"]:04X}, 0x{lay["entry"]["cs"]:04X}, 0x{lay["entry"]["ip"]:04X}, '
                 f'0x{lay["stack"]["ss"]:04X}, 0x{lay["stack"]["sp"]:04X},\n'
                 f'    dispatch, {len(entries)}, {TAG}_drivers, &{TAG}_ndrivers, "{cd}",\n'
                 f'    "{os.path.basename(os.path.abspath(a.build))}", "{"obsidian" if mod else ""}",\n'
                 f'    0x{tsr["psp"]:04X}, 0x{tsr["cs"]:04X}, 0x{tsr["ip"]:04X}, 0x{tsr["ss"]:04X}, 0x{tsr["sp"]:04X},\n'
                 f'    ranges, {len(ranges)},\n'
                 f'    umb, {len(umb)},\n'
                 f'}};\n\n')
        for s in stubs:
            # A call to something no function covers: say so at run time,
            # and keep the stack balanced the way the call site expects.
            pop = 4 if s.startswith('far_') else 2
            fh.write(f'void {s}(CPU *cpu) {{ recomp_missing(cpu, "{s}"); cpu->sp += {pop}; }}\n')

    print(f'lifted {len(bodies)} functions into {(len(bodies) + CHUNK - 1) // CHUNK} files; '
          f'{failed} failed, {unhandled} unhandled instructions, '
          f'{len(stubs)} unresolved call targets, {len(segs)} code segments, '
          f'{overlaps} overlapping fall-throughs made explicit')


if __name__ == '__main__':
    main()
