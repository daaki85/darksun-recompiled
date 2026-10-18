#!/usr/bin/env python3
"""Find the functions in a built image (build_image.py) and what each contains.

Recursive descent from every entry point that can be proven statically:

  * the program's entry (Borland's C0 start-up),
  * every overlay entry stub (the target it now jumps to),
  * the start-up's _INIT_ / _EXIT_ tables (routines nothing else names),
  * every direct near and far call target met on the way,
  * Borland prologues (`push bp / mov bp, sp`) found anywhere in code,
  * far function pointers stored in data (an MZ relocation whose word is a
    code segment, preceded by an offset that lands on a prologue or a stub),
  * addresses a previous run of the game reported as dispatch misses
    (build/<game>/misses.txt), which is how the work list converges.

A function is everything reachable from its entry by jumps that stay inside
its code segment, stopping at ret/retf/iret and at jumps to other functions.
Jump tables (`jmp cs:[bx+table]`, Borland's switch) are followed.

Output: build/<game>/functions.json
"""
import argparse
import json
import os
import sys

from dsimage import Image, OpType

JCC = {'jo', 'jno', 'jb', 'jae', 'je', 'jne', 'jbe', 'ja', 'js', 'jns', 'jp',
       'jnp', 'jl', 'jge', 'jle', 'jg', 'loop', 'loopz', 'loopnz', 'jcxz'}
STOP = {'ret', 'retf', 'iret', 'hlt'}


# Tables of near function pointers in DGROUP, per game (by EXE size): offset,
# count and the code segment the handlers run in. Nothing in the code names
# these as code (a near pointer has no segment), so they are listed. DS1: the
# GPL script interpreter's opcode handlers (OpenDS, dispatch-table-ds1.md).
NEAR_TABLES = {
    611408: [(0xC0, 0x81, 0x0C4D)],
    634416: [(0x30A, 0x81, 0x0F3C)],     # DS2: DGROUP:30A, handlers in paragraph 72C + load
}


class Finder:
    def __init__(self, img):
        self.img = img
        self.entries = {}          # linear entry -> cs
        self.code_segs = {s['seg']: s['size'] for s in img.segs}
        self.funcs = {}
        self.why = {}

    # -- seeds ---------------------------------------------------------------
    def seed(self, lin, cs=None, why=''):
        lin = self.img.stub_target.get(lin, lin)      # a stub is its target
        if cs is None or lin in self.img.stub_target.values():
            cs = self.img.seg_of(lin)
        if cs is None or lin < cs * 16 or lin - cs * 16 > 0xFFFF:
            return False
        if lin not in self.entries:
            self.entries[lin] = cs
            self.why[lin] = why
            return True
        return False

    def far_lin(self, seg, off):
        return (seg * 16 + off) & 0xFFFFF if seg < 0xF000 else seg * 16 + off

    def is_prologue(self, lin):
        m = self.img.mem
        k = lin
        for _ in range(3):                           # push si/di before bp
            if m[k] in (0x56, 0x57, 0x1E):
                k += 1
        return m[k] == 0x55 and m[k + 1] == 0x8B and m[k + 2] == 0xEC

    def seed_static(self):
        lay = self.img.layout
        e = lay['entry']
        self.seed(e['cs'] * 16 + e['ip'], e['cs'], 'entry')
        if lay.get('tsr'):
            t = lay['tsr']
            self.seed(t['cs'] * 16 + t['ip'], t['cs'], 'tsr-entry')
        for m in lay['modules']:
            for s in m['stubs']:
                self.seed(s['target'], m['seg'], 'stub')
        n = 0
        for s in self.img.segs:
            b = s['seg'] * 16
            blob = self.img.mem[b:b + s['size']]
            k = blob.find(b'\x55\x8B\xEC')
            while k >= 0:
                n += self.seed(b + k, s['seg'], 'prologue')
                k = blob.find(b'\x55\x8B\xEC', k + 1)
        self.seed_init_tables()
        self.seed_data_pointers()
        self.seed_stack_checks()
        dg = lay['dgroup'] * 16
        for off, count, cs in NEAR_TABLES.get(lay['exe_size'], []):
            for i in range(count):
                self.seed(cs * 16 + self.img.u16(dg + off + 2 * i), cs, 'near-table')
        return n

    def seed_stack_checks(self):
        """Borland's other prologue: a function with no locals opens with
        `[push reg...] cmp word [stack_base], sp / ja ok / call far overflow`.
        The entry is before the pushes, so both the pushes' start and the
        compare are seeded (the bodies overlap harmlessly)."""
        m = self.img.mem
        for s in self.img.segs:
            b = s['seg'] * 16
            blob = m[b:b + s['size']]
            k = blob.find(b'\x39\x26')
            while k >= 0:
                if k + 6 < len(blob) and blob[k + 4] == 0x77 and blob[k + 6] == 0x9A:
                    self.seed(b + k, s['seg'], 'stack-check')
                    j = k
                    for _ in range(4):
                        if j > 0 and (0x50 <= blob[j - 1] <= 0x57 or blob[j - 1] in (0x1E, 0x06)):
                            j -= 1
                    if j != k:
                        self.seed(b + j, s['seg'], 'stack-check')
                k = blob.find(b'\x39\x26', k + 1)

    def seed_init_tables(self):
        """Borland's start-up walks {type, priority, far ptr} records between
        two DGROUP offsets it loads into SI and DI."""
        lay = self.img.layout
        cs, ip = lay['entry']['cs'], lay['entry']['ip']
        dg = lay['dgroup'] * 16
        si = None
        pairs = []
        d = self.img.decoder(cs)
        d.pos = ip
        for _ in range(400):
            ins = d.decode_one()
            if ins is None:
                break
            o1, o2 = ins.op1, ins.op2
            if (ins.mnemonic == 'mov' and o1 and o1.type == OpType.REG16 and o2
                    and o2.type == OpType.IMM16):
                if repr(o1) == 'si':
                    si = o2.disp
                elif repr(o1) == 'di' and si is not None:
                    pairs.append((si, o2.disp))
                    si = None
        for a, b in pairs:
            if not (0 < b - a < 0x400 and (b - a) % 6 == 0):
                continue
            for r in range(dg + a, dg + b, 6):
                ctype = self.img.mem[r]
                if ctype == 0xFF:
                    continue
                off, seg = self.img.u16(r + 2), self.img.u16(r + 4)
                self.seed(self.far_lin(seg, off), None, 'init-table')

    def seed_data_pointers(self):
        code = {s['seg'] for s in self.img.segs}
        size = {s['seg']: s['size'] for s in self.img.segs}
        for r in self.img.layout['relocs']:
            if self.img.seg_of(r) is not None and self.img.seg_of(r - 2) is not None:
                # a relocation inside code is an immediate; handled by descent
                if self.in_code_bytes(r):
                    continue
            seg = self.img.u16(r)
            if seg not in code:
                continue
            off = self.img.u16(r - 2)
            lin = seg * 16 + off
            if off < size[seg] and (lin in self.img.stub_target or self.is_prologue(lin)):
                self.seed(lin, seg, 'data-pointer')

    def in_code_bytes(self, lin):
        return False

    # -- descent ---------------------------------------------------------------
    def jump_table(self, cs, insns_before, ins):
        """Arms of `jmp word cs:[bx+table]`, bounded by the `cmp` before it."""
        o = ins.op1
        if not (o and o.type == OpType.MEM and o.seg == 'cs' and o.base == 'bx'
                and not o.index):
            return None
        bound = bx_imm = cx_imm = None
        add_bx_cx = False
        for j in insns_before[-12:]:
            if j.mnemonic == 'add' and repr(j.op1) == 'bx' and j.op2 and repr(j.op2) == 'cx':
                add_bx_cx = True
            if not (j.op1 and j.op1.type == OpType.REG16 and j.op2
                    and j.op2.type in (OpType.IMM8, OpType.IMM16)):
                continue
            reg = repr(j.op1)
            if j.mnemonic == 'cmp' and reg == 'bx':
                bound = (j.op2.disp & 0xFFFF) + 1
            elif j.mnemonic == 'mov' and reg == 'bx':
                bx_imm = j.op2.disp & 0xFFFF
            elif j.mnemonic == 'mov' and reg == 'cx':
                cx_imm = j.op2.disp & 0xFFFF
        # Borland's sparse switch: bx walks a list of N case values, cx counts
        # down, and the arm offsets follow the list. Word values: the hit
        # jumps through cs:[bx + 2N], so the arms start at list + 2N. Dword
        # values (4 bytes each): `add cx,cx / add bx,cx / jmp cs:[bx+2N]`, so
        # for a hit at index i (bx = list + 4i, cx = N - i) the arm is at
        # list + 2N + 2N + 2i: the arms start at list + 4N.
        if bx_imm is not None and cx_imm and (o.disp & 0xFFFF) == cx_imm * 2:
            start, bound = bx_imm + cx_imm * (4 if add_bx_cx else 2), cx_imm
        else:
            start = o.disp & 0xFFFF
            if bound is None:
                return None
        base = cs * 16
        arms = []
        for k in range(bound):
            a = base + ((start + 2 * k) & 0xFFFF)
            arms.append(self.img.u16(a))
        return arms

    def body(self, lin, cs):
        ip0 = lin - cs * 16
        seen = {}
        tables = {}
        order = []
        work = [ip0]
        calls = set()
        while work:
            ip = work.pop()
            while ip not in seen:
                # Falling into another function's entry is not the end of this
                # one: the CPU runs on, so the code is decoded again here.
                ins = self.img.decode_at(cs, ip)
                if ins is None or ins.mnemonic == 'db':
                    break
                seen[ip] = ins
                order.append(ip)
                m, o = ins.mnemonic, ins.op1
                nxt = (ip + ins.length) & 0xFFFF
                if m in STOP:
                    break
                if m in JCC and o and o.type in (OpType.REL8, OpType.REL16):
                    t = o.disp & 0xFFFF
                    if cs * 16 + t in self.entries and t != ip0:
                        pass                                # conditional tail jump
                    else:
                        work.append(t)
                    ip = nxt
                    continue
                if m == 'jmp':
                    if o and o.type in (OpType.REL8, OpType.REL16):
                        t = o.disp & 0xFFFF
                        if cs * 16 + t in self.entries and t != ip0:
                            break
                        ip = t
                        continue
                    if o and o.type == OpType.FAR:
                        calls.add(self.far_lin(o.far_seg, o.disp))
                        break
                    prev = [seen[a] for a in sorted(seen) if a < ip][-10:]
                    arms = self.jump_table(cs, prev, ins)
                    if arms:
                        tables[ip] = arms
                        work.extend(arms)
                    break
                if m == 'jmp far' or (m == 'call far' and o and o.type == OpType.MEM):
                    # `jmp far cs:[bx+table]`: a table of far pointers in the
                    # code segment (the sprite blitters pick a routine that
                    # way). Entries are read while they point into code.
                    if o and o.type == OpType.MEM and o.seg == 'cs' and o.base == 'bx' and not o.index:
                        a = cs * 16 + (o.disp & 0xFFFF)
                        for k in range(256):
                            off, sg = self.img.u16(a + 4 * k), self.img.u16(a + 4 * k + 2)
                            if sg not in self.code_segs or off >= self.code_segs[sg]:
                                break
                            calls.add(sg * 16 + off)
                    if m == 'jmp far':
                        break
                if m == 'call' and o and o.type == OpType.REL16:
                    calls.add(cs * 16 + (o.disp & 0xFFFF))
                elif m == 'call' and o and o.type == OpType.FAR:
                    calls.add(self.far_lin(o.far_seg, o.disp))
                ip = nxt
        # `mov dx, imm16 ... mov ah, 25h / int 21h`: an interrupt handler being
        # installed (the sound drivers hook their IRQ that way). Every
        # `mov dx, imm` in a function that calls DOS is seeded if it decodes.
        if any(i.mnemonic == 'int' and i.op1 and i.op1.disp == 0x21 for i in seen.values()):
            for i in seen.values():
                if (i.mnemonic == 'mov' and i.op1 and repr(i.op1) == 'dx' and i.op2
                        and i.op2.type == OpType.IMM16):
                    t = i.op2.disp & 0xFFFF
                    ins = self.img.decode_at(cs, t)
                    # (`00 00`, add [bx+si],al, is how zeroed data decodes; a
                    # real add is code: the mod's helper opens a handler with one)
                    if ins and ins.mnemonic != 'db' and not (ins.mnemonic == 'add' and ins.raw[:1] == b'\x00') and t < 0xFFF0:
                        calls.add(cs * 16 + t)
        # `mov reg, imm16 ... call reg` / `jmp reg`: the immediate is a routine
        # in this segment (Borland's run-time picks helpers that way). Only
        # immediates that decode as code, and only when the function calls or
        # jumps through a register at all.
        if any(i.mnemonic in ('call', 'jmp') and i.op1 and i.op1.type == OpType.REG16
               for i in seen.values()):
            for i in seen.values():
                if (i.mnemonic == 'mov' and i.op1 and i.op1.type == OpType.REG16 and i.op2
                        and i.op2.type == OpType.IMM16 and repr(i.op1) in ('bx', 'ax', 'si', 'di', 'dx', 'cx')):
                    t = i.op2.disp & 0xFFFF
                    ins = self.img.decode_at(cs, t)
                    # (`00 00`, add [bx+si],al, is how zeroed data decodes; a
                    # real add is code: the mod's helper opens a handler with one)
                    if ins and ins.mnemonic != 'db' and not (ins.mnemonic == 'add' and ins.raw[:1] == b'\x00') and t < 0xFFF0:
                        calls.add(cs * 16 + t)
        return dict(cs=cs, ips=sorted(seen), tables=tables), calls

    def run(self, misses=()):
        self.seed_static()
        for a in misses:
            self.seed(a, None, 'miss')
        # Entries keep appearing (calls found inside bodies), and a new entry
        # can cut an earlier body short, so iterate until nothing changes.
        while True:
            before = len(self.entries)
            self.funcs = {}
            for lin in sorted(self.entries):
                cs = self.entries[lin]
                f, calls = self.body(lin, cs)
                self.funcs[lin] = f
                for c in calls:
                    self.seed(c, None, 'call')
            if len(self.entries) == before:
                return self.funcs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('build', nargs='?', default='build/ds1')
    a = ap.parse_args(argv)
    img = Image(a.build)
    misses = []
    mp = os.path.join(a.build, 'misses.txt')
    if os.path.exists(mp):
        misses = [int(x, 16) for x in open(mp).read().split() if x.strip()]
    f = Finder(img)
    funcs = f.run(misses)
    out = {f'{k:05X}': dict(v, tables={str(i): t for i, t in v['tables'].items()},
                            why=f.why.get(k, '')) for k, v in sorted(funcs.items())}
    json.dump(out, open(os.path.join(a.build, 'functions.json'), 'w'))
    from collections import Counter
    why = Counter(f.why[k] for k in funcs)
    n_ins = sum(len(v['ips']) for v in funcs.values())
    print(f'{len(funcs)} functions, {n_ins} instructions, '
          f'{sum(len(v["tables"]) for v in funcs.values())} jump tables')
    print('  entries by source:', dict(why))


if __name__ == '__main__':
    main()
