#!/usr/bin/env python3
"""re_state_items.py: dump the original's item property tables from a RAM image.

Items (ids 1..75 = parser nouns): byte arrays B0..B4 at $4000 $404C $4098 $40E4
$4130 and word arrays W5..W11 at $417C $4214 $42AC $4344 $43DC $4474 $450C
(76 entries each, index = noun id; core $4D0C). Second set (28 entries, $4D0F):
B0..B4 at $45A4 $45C0 $45DC $45F8 $4614, W5..W11 at $4630 .. $4780.
Usage: re_state_items.py RAM.bin
"""
import sys

m = open(sys.argv[1], 'rb').read()
names = {}
i, L = 0xB201, 1
while L <= 12:
    while m[i] != 0xFF:
        w = bytes(c & 0x7F for c in m[i:i + L]).decode()
        if m[i + L] == 2:
            names.setdefault(m[i + L + 1], w)
        i += L + 2
    i += 1
    L += 1
B = (0x4000, 0x404C, 0x4098, 0x40E4, 0x4130)
W = (0x417C, 0x4214, 0x42AC, 0x4344, 0x43DC, 0x4474, 0x450C)
B2 = (0x45A4, 0x45C0, 0x45DC, 0x45F8, 0x4614)
W2 = (0x4630, 0x4668, 0x46A0, 0x46D8, 0x4710, 0x4748, 0x4780)
w = lambda a, k: int.from_bytes(m[a + 2 * k:a + 2 * k + 2], 'little', signed=True)
print('id  name         ' + ' '.join(f'B{k}' .rjust(4) for k in range(5)) + ' ' + ' '.join(f'W{k}'.rjust(6) for k in range(5, 12)))
for k in range(76):
    print(f'{k:3d} {names.get(k, "?"):12} ' + ' '.join(f'{m[a + k]:4d}' for a in B) + ' ' + ' '.join(f'{w(a, k):6d}' for a in W))
print('--- second set (index -> noun id 75+k ?)')
for k in range(28):
    print(f'{k:3d} {names.get(75 + k, "?"):12} ' + ' '.join(f'{m[a + k]:4d}' for a in B2) + ' ' + ' '.join(f'{w(a, k):6d}' for a in W2))
