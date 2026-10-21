# extract.py -- rebuild the program's memory image from the original disk,
# using the loader's own load table (no emulator needed).
#
# usage: python3 -I extract.py <tools_dir> <physics.dsk> <outdir>
#   writes <outdir>/boot0_9000.bin (T0 phys 0,2,4,6 = $9000-$93FF after relocation)
#          <outdir>/image.bin      (64K, every loaded page in place)
#          <outdir>/loadmap.txt
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'dev', 'tools'))
from re6502.disk import PHYS2LOG  # physical -> logical sector
d = open(sys.argv[2], 'rb').read()
assert len(d) == 143360
out = sys.argv[3]
def phys(t, ps):
    o = (t * 16 + PHYS2LOG[ps]) * 256
    return d[o:o + 256]
boot = b''.join(phys(0, ps) for ps in (0, 2, 4, 6))
open(os.path.join(out, 'boot0_9000.bin'), 'wb').write(boot)
img = bytearray(65536)
lines = ['T0 phys 0,2,4,6 -> $0800-$0BFF (boot PROM + boot0), relocated to $9000-$93FF']
i = 0x353
used = {(0, 0), (0, 2), (0, 4), (0, 6)}
while boot[i]:
    trk, ntr, page, aux, last = boot[i:i + 5]
    for t in range(ntr):
        n = last if t == ntr - 1 else 16
        for ps in range(n):
            p = page + 16 * t + ps
            img[p * 256:p * 256 + 256] = phys(trk + t, ps)
            used.add((trk + t, ps))
        lines.append('T%d phys 0-%d -> $%04X-$%04X%s' % (trk + t, n - 1, (page + 16 * t) << 8,
                     ((page + 16 * t + n) << 8) - 1, ' (aux)' if aux else ''))
    i += 5
open(os.path.join(out, 'image.bin'), 'wb').write(img)
# any non-empty sector the loader does not read?
stray = [(t, ps) for t in range(35) for ps in range(16)
         if (t, ps) not in used and any(phys(t, ps))]
lines.append('non-empty sectors not loaded: %s' % (stray or 'none'))
open(os.path.join(out, 'loadmap.txt'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
