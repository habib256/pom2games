# mkdisk.py -- build physics.dsk (DOS 3.3 sector order, 35 x 16 x 256) from
# the assembled boot sector and segments, following the loader's own table.
#
# usage: python3 -I mkdisk.py <build_dir> <out.dsk>
import sys, os

# DOS-order .dsk files store logical sectors; the loader and boot PROM
# work in PHYSICAL sectors.  physical -> logical (DOS 3.3 interleave):
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'dev', 'tools'))
from re6502.disk import PHYS2LOG  # physical -> logical sector

b = sys.argv[1]
boot = open(os.path.join(b, 'boot.bin'), 'rb').read()
assert len(boot) == 1024
disk = bytearray(35 * 16 * 256)

def put(track, psec, data):
    assert len(data) == 256
    off = (track * 16 + PHYS2LOG[psec]) * 256
    assert not any(disk[off:off + 256]), 'sector written twice'
    disk[off:off + 256] = data

# track 0: boot PROM reads phys 0 to $0800, boot0 reads phys 2/4/6 to $0900-$0B00
for i, ps in enumerate((0, 2, 4, 6)):
    put(0, ps, boot[i * 256:(i + 1) * 256])

# memory image of the program, from the linked segments
mem = bytearray(65536)
for name, base in (('seg_0800.bin', 0x0800), ('seg_2000.bin', 0x2000),
                   ('seg_6000.bin', 0x6000), ('seg_9400.bin', 0x9400),
                   ('seg_A000.bin', 0xA000)):
    d = open(os.path.join(b, name), 'rb').read()
    mem[base:base + len(d)] = d

# walk the loader's load_table ($9353 = offset $353 in boot.bin)
loaded = set()
i = 0x353
while boot[i]:
    trk, ntr, page, aux, last = boot[i:i + 5]
    assert aux == 0
    for t in range(ntr):
        for ps in range(last if t == ntr - 1 else 16):
            p = page + 16 * t + ps
            assert p not in loaded
            loaded.add(p)
            put(trk + t, ps, mem[p * 256:(p + 1) * 256])
    i += 5

# every byte of every segment must have gone to the disk
for name, base, size in (('0800', 0x0800, 0x1500), ('2000', 0x2000, 0x2000),
                         ('6000', 0x6000, 0x1E00), ('9400', 0x9400, 0x700),
                         ('A000', 0xA000, 0x1100)):
    for p in range(base >> 8, (base + size) >> 8):
        assert p in loaded, 'page %02X not in load_table' % p

open(sys.argv[2], 'wb').write(disk)
print('%s: %d sectors from the load table + 4 boot sectors' % (sys.argv[2], len(loaded)))
