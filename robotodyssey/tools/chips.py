#!/usr/bin/env python3
"""chips.py: decode Robot Odyssey (Apple II) chips into a readable netlist.

    chips.py library [IMAGE.po]     the Chip Library (side B, default
                                    build/B_LABS.po): catalog, headers,
                                    documentation and netlists
    chips.py code FILE [PINS]       one compiled chip (e.g. a segment such as
                                    build/files/B_LABS/06D_D800_cd_chip2.bin); PINS =
                                    8 direction bytes in hex (optional)
    chips.py sim K CYCLES [P=V ...] run library chip K for CYCLES cycles with
                                    input pins P held at V; prints the pins

Storage (see docs/logic/chips.md):
  block 8           catalog: 26 names of 18 bytes, 13 per 256-byte half
  block 9+3k, 10+3k chip k's compiled code (1 KB, loaded at $D000+$400*slot,
                    language card bank 1)
  block 11+3k       chip k's header: 8 pin directions, code length (LE16),
                    documentation (title 19 bytes + 8 lines of 35 bytes)

Compiled code (offsets are big-endian, relative to the chip base):
  +0..+7   pin values (index 0-3 = pins 1-4, index 4-7 = pins 8,7,6,5)
  01 a b OUT.. FF              AND      02 .. OR      03 .. XOR
  04 a OUT.. FF                NOT
  05 s r q /q OUTq.. FF OUT/q.. FF   flipflop (s sets q, r resets it)
  06 <nested chip: 8 pins, gates, 07 section>   nested chip, inline
  07 {SRC DST.. FF}.. FF       end: copy SRC to each DST
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN_OF_INDEX = (1, 2, 3, 4, 8, 7, 6, 5)
DIRS = {0: '-', 1: 'in', 2: 'out'}
OPS = {1: 'AND', 2: 'OR', 3: 'XOR', 4: 'NOT', 5: 'FF', 6: 'CHIP', 7: 'END'}


def hi_ascii(b):
    return ''.join(chr(x & 0x7F) if 0x20 <= (x & 0x7F) < 0x7F else '.' for x in b)


class Chip:
    """Parse one compiled chip (and its nested chips) into records."""

    def __init__(self, code):
        self.code = code
        self.records = []   # (depth, base, pos, op, fields, outlists)
        self.labels = {}    # absolute position -> label
        self.counter = {}
        self.end = self.parse(0, 0)

    def name(self, op):
        n = self.counter.get(op, 0) + 1
        self.counter[op] = n
        return '%s%d' % (OPS[op], n)

    def outs(self, pos, base):
        out = []
        while self.code[pos] != 0xFF:
            out.append(base + (self.code[pos] << 8 | self.code[pos + 1]))
            pos += 2
        return out, pos + 1

    def parse(self, base, depth):
        c = self.code
        chipname = 'C%d' % depth if depth else ''
        for i in range(8):
            self.labels[base + i] = '%sP%d' % (chipname + '.' if chipname else '', PIN_OF_INDEX[i])
        pos = base + 8
        while pos < len(c):
            op = c[pos]
            if op in (1, 2, 3):
                g = self.name(op)
                self.labels[pos + 1], self.labels[pos + 2] = g + '.a', g + '.b'
                o, nxt = self.outs(pos + 3, base)
                self.records.append((depth, base, pos, g, [pos + 1, pos + 2], [o]))
                pos = nxt
            elif op == 4:
                g = self.name(op)
                self.labels[pos + 1] = g + '.in'
                o, nxt = self.outs(pos + 2, base)
                self.records.append((depth, base, pos, g, [pos + 1], [o]))
                pos = nxt
            elif op == 5:
                g = self.name(op)
                for k, f in enumerate(('s', 'r', 'q', '/q')):
                    self.labels[pos + 1 + k] = g + '.' + f
                o1, nxt = self.outs(pos + 5, base)
                o2, nxt = self.outs(nxt, base)
                self.records.append((depth, base, pos, g, [pos + 1, pos + 2, pos + 3, pos + 4], [o1, o2]))
                pos = nxt
            elif op == 6:
                self.counter['nest'] = self.counter.get('nest', 0) + 1
                self.records.append((depth, base, pos, 'CHIP', [pos + 1], []))
                pos = self.parse(pos + 1, depth + 1)
            elif op == 7:
                groups = []
                pos += 1
                while c[pos] != 0xFF:
                    src = base + (c[pos] << 8 | c[pos + 1])
                    dst, pos = self.outs(pos + 2, base)
                    groups.append((src, dst))
                pos += 1
                self.records.append((depth, base, pos, 'END', [], groups))
                return pos
            else:
                self.records.append((depth, base, pos, '?%02X' % op, [], []))
                pos += 1
        return pos

    def label(self, a):
        return self.labels.get(a, '+%03X' % a)

    def dump(self, out=sys.stdout):
        for depth, base, pos, g, fields, lists in self.records:
            ind = '  ' * depth
            if g == 'CHIP':
                out.write('%s+%03X CHIP (imbriquée, base +%03X)\n' % (ind, pos, pos + 1))
            elif g == 'END':
                out.write('%s     END\n' % ind)
                for src, dst in lists:
                    out.write('%s       %s -> %s\n' % (ind, self.label(src),
                                                       ', '.join(self.label(d) for d in dst)))
            elif g.startswith('?'):
                out.write('%s+%03X octet %s ignoré\n' % (ind, pos, g[1:]))
            else:
                vals = ''.join(str(self.code[f]) for f in fields)
                outs = ' | '.join(', '.join(self.label(d) for d in lst) or '(rien)' for lst in lists)
                out.write('%s+%03X %-6s [%s] -> %s\n' % (ind, pos, g, vals, outs))
        tail = self.code[self.end:]
        if tail:
            out.write('     après END : %s\n' % tail.hex(' '))


class Machine:
    """Cycle-exact model of the chip interpreter ($1BAF lab, $F208 game).

    Writes to a slot at or after the current record are deferred to the end
    of the chip (or to the next nested chip), the others are immediate; the
    comparison is done byte by byte like the 6502 ($1C8F-$1CA3). Deferred
    writes are applied last pushed first. Opcode 7 copies are immediate.
    """

    def __init__(self, code, base=0xD000):
        self.mem = bytearray(code)
        self.base = base

    def run(self):
        self.deferred = []
        self.chip(0)

    def write(self, rec, off, val):
        t = self.base + off
        cur = self.base + rec
        if (t >> 8) < (cur >> 8) or (t & 0xFF) < (cur & 0xFF):
            self.mem[off] = val
        else:
            self.deferred.append((off, val))

    def flush(self):
        while self.deferred:
            off, val = self.deferred.pop()
            self.mem[off] = val

    def outs(self, rec, cbase, pos, val):
        m = self.mem
        while m[pos] != 0xFF:
            self.write(rec, cbase + (m[pos] << 8 | m[pos + 1]), val)
            pos += 2
        return pos + 1

    def chip(self, cbase):
        m = self.mem
        pos = cbase + 8
        while True:
            op = m[pos]
            if op in (1, 2, 3):
                a, b = m[pos + 1], m[pos + 2]
                v = a & b if op == 1 else a | b if op == 2 else a ^ b
                pos = self.outs(pos, cbase, pos + 3, v)
            elif op == 4:
                pos = self.outs(pos, cbase, pos + 2, (m[pos + 1] ^ 1) & 1)
            elif op == 5:
                in1, in2 = m[pos + 1], m[pos + 2]
                m[pos + 1] = m[pos + 2] = 0
                a = ((in2 << 1) | (in1 & 1)) & 0xFF
                x = a & 3
                if x not in (0, 3) and (a & 1) != m[pos + 3] and (x & 2) != m[pos + 4]:
                    m[pos + 3] ^= 1
                    m[pos + 4] ^= 1
                q, qb = m[pos + 3], m[pos + 4]
                rec = pos
                pos = self.outs(rec, cbase, pos + 5, q)
                pos = self.outs(rec, cbase, pos, qb)
            elif op == 6:
                self.flush()
                pos = self.chip(pos + 1)
            elif op == 7:
                pos += 1
                while m[pos] != 0xFF:
                    src = m[cbase + (m[pos] << 8 | m[pos + 1])]
                    pos += 2
                    while m[pos] != 0xFF:
                        m[cbase + (m[pos] << 8 | m[pos + 1])] = src
                        pos += 2
                    pos += 1
                self.flush()
                return pos + 1
            else:
                pos += 1


def simulate(code, pins, cycles, inputs):
    """Run a chip: inputs = {pin: value}; print the pin values per cycle."""
    mach = Machine(code)
    idx = {p: i for i, p in enumerate(PIN_OF_INDEX)}
    print('cycle  ' + ' '.join('%d' % p for p in range(1, 9)))
    for c in range(cycles):
        for p, v in inputs.items():
            mach.mem[idx[p]] = v
        mach.run()
        print('%5d  %s' % (c, ' '.join(
            str(mach.mem[idx[p]]) if pins[idx[p]] else '.' for p in range(1, 9))))


def pins_text(pins):
    return ' '.join('%d:%s' % (PIN_OF_INDEX[i], DIRS.get(p, '?%02X' % p)) for i, p in sorted(
        enumerate(pins), key=lambda t: PIN_OF_INDEX[t[0]]))


def library(path):
    d = open(path, 'rb').read()

    def blk(b):
        return d[b * 512:(b + 1) * 512]

    cat = blk(8)
    for k in range(26):
        off = (k // 13) * 256 + (k % 13) * 18
        name = hi_ascii(cat[off:off + 18]).rstrip()
        if not name:
            continue
        head = blk(11 + 3 * k)
        code = blk(9 + 3 * k) + blk(10 + 3 * k)
        length = head[8] | head[9] << 8
        print('=' * 70)
        print('Puce %d (%s) : blocs $%03X-$%03X code, $%03X en-tête' % (
            k, name, 9 + 3 * k, 10 + 3 * k, 11 + 3 * k))
        print('broches  %s' % pins_text(head[:8]))
        print('longueur $%03X octets' % length)
        rec = head[10:10 + 0x12B]
        print('titre    "%s"' % hi_ascii(rec[:18]).strip())
        for i in range(8):
            print('   | %s' % hi_ascii(rec[19 + 35 * i:19 + 35 * i + 34]))
        chip = Chip(code[:length])
        counts = {}
        for r in chip.records:
            counts[r[3].rstrip('0123456789')] = counts.get(r[3].rstrip('0123456789'), 0) + 1
        print('contenu  %s' % ', '.join('%d %s' % (n, g) for g, n in sorted(counts.items())))
        chip.dump()


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('library', 'code', 'sim'):
        print(__doc__)
        return 1
    if sys.argv[1] == 'sim':
        d = open(os.path.join(ROOT, 'build', 'B_LABS.po'), 'rb').read()
        k = int(sys.argv[2])
        head = d[(11 + 3 * k) * 512:(12 + 3 * k) * 512]
        code = d[(9 + 3 * k) * 512:(11 + 3 * k) * 512][:head[8] | head[9] << 8]
        inputs = {int(a.split('=')[0]): int(a.split('=')[1]) for a in sys.argv[4:]}
        simulate(code, head[:8], int(sys.argv[3]), inputs)
        return 0
    if sys.argv[1] == 'library':
        library(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'build', 'B_LABS.po'))
    else:
        code = open(sys.argv[2], 'rb').read()
        if len(sys.argv) > 3:
            print('broches  %s' % pins_text(bytes.fromhex(sys.argv[3])))
        Chip(code).dump()
    return 0


if __name__ == '__main__':
    sys.exit(main())
