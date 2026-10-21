"""Shared helpers: the memory image, its code segments, and pcrecomp's decoder."""
import bisect
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCRECOMP = os.environ.get('PCRECOMP_HOME', os.path.join(ROOT, 'third_party', 'pcrecomp'))
sys.path.insert(0, os.path.join(PCRECOMP, 'tools', 'disasm'))
sys.path.insert(0, os.path.join(PCRECOMP, 'tools', 'lift'))

import decode16                          # noqa: E402
from decode16 import Decoder, OpType     # noqa: E402

# Every function is decoded against a buffer that starts at its code segment's
# base, so an instruction's address IS its IP and a near branch wraps at 64 KB
# exactly as the CPU does.
decode16.WRAP_NEAR_TARGETS = True


class Image:
    def __init__(self, build_dir):
        self.dir = build_dir
        self.mem = open(os.path.join(build_dir, 'image.bin'), 'rb').read()
        self.layout = json.load(open(os.path.join(build_dir, 'layout.json')))
        segs = sorted(self.layout['code_segments'], key=lambda s: s['seg'])
        self.segs = segs
        self.int_sites = {int(k, 16): v['skip'] for k, v in (self.layout.get('int_sites') or {}).items()}
        # the bytes the mod's INTs replaced (the finder sizes a switch by a `mov cx, N` among them)
        self.int_originals = {int(k, 16): bytes.fromhex(v) for k, v in (self.layout.get('int_originals') or {}).items()}
        tsr = self.layout.get('tsr') or {}
        self.mod_vectors = set((self.layout.get('mod') or {}).get('vectors') or [])
        self.inline_args = {int(k, 16): v for k, v in (tsr.get('inline_args') or {}).items()}
        self.inline_plain_sites = {int(k, 16) for k in (tsr.get('inline_plain_sites') or [])}
        self.tsr_cs = tsr.get('cs')
        self._starts = [s['seg'] * 16 for s in segs]
        self._dec = {}
        # stub linear address -> the entry it jumps to (linear)
        self.stub_target = {}
        for m in self.layout['modules']:
            for s in m['stubs']:
                self.stub_target[s['stub']] = s['target']

    def seg_of(self, lin):
        """The code segment (CS value) whose record covers a linear address."""
        i = bisect.bisect_right(self._starts, lin) - 1
        while i >= 0:
            s = self.segs[i]
            if lin < s['seg'] * 16 + max(s['size'], 1):
                return s['seg']
            if lin - s['seg'] * 16 >= 0x10000:
                break
            i -= 1
        return None

    def decoder(self, cs):
        d = self._dec.get(cs)
        if d is None:
            b = cs * 16
            d = self._dec[cs] = Decoder(self.mem[b:b + 0x10000], base_offset=b)
        return d

    def decode_at(self, cs, ip):
        d = self.decoder(cs)
        d.pos = ip
        try:
            ins = d.decode_one()
        except (IndexError, KeyError):
            return None
        # The mod's INT sites carry data after the INT that the handler steps
        # over: the instruction is that much longer.
        skip = self.int_sites.get(cs * 16 + ip)
        if skip and ins is not None and ins.mnemonic == 'int':
            ins.length += skip
        # `call X / db ARG` in the helper: the argument is data, not code
        if (self.inline_args and ins is not None and ins.mnemonic == 'call' and ins.op1
                and ins.op1.type == OpType.REL16):
            n = self.inline_args.get(cs * 16 + (ins.op1.disp & 0xFFFF))
            if n and cs * 16 + ip not in self.inline_plain_sites:
                ins.length += n
        return ins

    def u16(self, lin):
        return self.mem[lin] | (self.mem[lin + 1] << 8)
