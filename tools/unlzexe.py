#!/usr/bin/env python3
"""Unpack an LZEXE 0.91 compressed DOS program (CHARTRAN.EXE is one).

    python3 tools/unlzexe.py game/ds2/CHARTRAN.EXE build/chartran/CHARTRAN.EXE

The packed program's code segment holds a small decompressor whose first
sixteen bytes say where the real program starts (ip, cs, sp, ss), how large
the compressed data is and how much the program grows; the relocation table
follows the decompressor (at CS:0158) as spans between fix-ups. The data is
a bit-coded LZ stream read from the paragraph before the decompressor's
segment backwards in the usual unlzexe fashion: a 1 bit copies a byte, 00
copies 2 to 5 bytes from a distance of up to 256, 01 a longer run from up
to 8 KB back.
"""
import struct, sys


class Bits:
    def __init__(self, data, pos):
        self.data, self.pos = data, pos
        self.buf = struct.unpack_from('<H', data, pos)[0]; self.pos += 2; self.n = 16

    def bit(self):
        b = self.buf & 1
        self.buf >>= 1
        self.n -= 1
        if self.n == 0:
            self.buf = struct.unpack_from('<H', self.data, self.pos)[0]; self.pos += 2; self.n = 16
        return b

    def byte(self):
        b = self.data[self.pos]; self.pos += 1
        return b


def unpack(d):
    h = list(struct.unpack_from('<14H', d, 0))
    if d[0x1C:0x20] != b'LZ91':
        raise SystemExit('not an LZEXE 0.91 file')
    cs0 = (h[11] + h[4]) << 4
    inf = struct.unpack_from('<8H', d, cs0)
    ip, cs, sp, ss, csize, grow, dsize = inf[:7]
    # relocation table
    relocs = []
    p = cs0 + 0x158
    seg = 0; off = 0
    while True:
        span = d[p]; p += 1
        if span == 0:
            span = struct.unpack_from('<H', d, p)[0]; p += 2
            if span == 0:
                seg += 0x0FFF; continue
            if span == 1:
                break
        off += span
        seg += (off & ~0xF) >> 4
        off &= 0xF
        relocs.append((off, seg))
    # the data
    bits = Bits(d, (h[11] - csize + h[4]) << 4)
    out = bytearray()
    while True:
        if bits.bit():
            out.append(bits.byte()); continue
        if not bits.bit():
            length = bits.bit() << 1
            length |= bits.bit()
            length += 2
            span = bits.byte() | 0xFF00
        else:
            span = bits.byte()
            length = bits.byte()
            span |= ((length & ~7) << 5) | 0xE000
            length = (length & 7) + 2
            if length == 2:
                length = bits.byte()
                if length == 0:
                    break
                if length == 1:
                    continue
                length += 1
        span -= 0x10000
        for _ in range(length):
            out.append(out[span])
    # header
    nrel = len(relocs)
    hdr = 0x1C + nrel * 4
    hdrparas = (hdr + 15) >> 4
    total = hdrparas * 16 + len(out)
    nh = h[:]
    nh[1] = total & 0x1FF; nh[2] = (total + 511) >> 9
    nh[3] = nrel; nh[4] = hdrparas
    nh[5] = max(0, h[5] - (grow + ((dsize + 15) >> 4) + 9)); nh[6] = h[6]
    nh[7] = ss; nh[8] = sp; nh[9] = 0; nh[10] = ip; nh[11] = cs; nh[12] = 0x1C; nh[13] = 0
    o = bytearray(struct.pack('<14H', *nh))
    for off, seg in relocs:
        o += struct.pack('<HH', off, seg)
    o += bytes(hdrparas * 16 - len(o))
    o += out
    return bytes(o), (ip, cs, sp, ss, nrel, len(out))


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    o, info = unpack(d)
    open(sys.argv[2], 'wb').write(o)
    print('ip=%04X cs=%04X sp=%04X ss=%04X relocs=%d image=%d bytes' % info)
