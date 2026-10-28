#!/usr/bin/env python3
"""memimg.py OUT SIDE SEG... : build a 64 KB memory image from extracted segments.

Starts from build/l4000_64k.bin (resident module), then lays each segment
build/files/SIDE/SEG.bin (e.g. 05B_9500) at its load address, in order,
like the loader calls do. Language-card segments go to $D000-$FFFF as is
(bank 2 for $D000-$DFFF, as the game uses it).
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(side, segs, base=None):
    if base is None:
        base = os.path.join(ROOT, 'build', 'l4000_64k.bin')
    mem = bytearray(open(base, 'rb').read())
    for s in segs:
        # extract.py appends the segment's role: BBB_AAAA_role.bin
        path, = glob.glob(os.path.join(ROOT, 'build', 'files', side, s + '*.bin'))
        data = open(path, 'rb').read()
        addr = int(s.split('_')[1], 16)
        mem[addr:addr + len(data)] = data
    return mem


# loads per menu entry: the $4590 lesson base, then the lesson's own call
LESSON_BASE = ['05B_9500', '008_14C0', '00E_B900', '011_D000', '019_F000']
LESSONS = {
    'anatomy': ('C_TUTORIAL', LESSON_BASE + ['020_0803', '027_14C0', '06D_6000']),
    'wiring': ('C_TUTORIAL', LESSON_BASE + ['020_0803', '02B_14C0', '087_6000']),
    'sensors': ('C_TUTORIAL', LESSON_BASE + ['020_0803', '09F_6000']),
    'toolkit': ('C_TUTORIAL', LESSON_BASE + ['0B9_0803', '0BE_14C0', '0C2_6000']),
    'circuits': ('C_TUTORIAL', LESSON_BASE + ['0DB_0803', '0E1_14C0', '0E5_6000']),
    'teamwork': ('C_TUTORIAL', LESSON_BASE + ['0DB_0803', '0FE_6000']),
    'preview': ('B_LABS', ['05B_9500', '071_0803', '077_14C0', '07D_6000', '08D_7F80',
                           '092_8880', '095_9000', '097_D000', '09F_E000', '0A0_E470']),
    'innovation': ('B_LABS', ['05B_9500', '0C6_6000', '0E1_0803', '0A7_0B00', '0B2_B8E0',
                              '0B6_D000', '0BE_F000']),
    'chipdesign': ('B_LABS', ['05B_9500', '0E3_6000', '0FE_0803', '0A7_0B00', '100_0B00',
                              '0B2_B8E0', '0B6_D000', '0BE_F000', '06D_D800', '0A6_D000']),
}


def main():
    out, name = sys.argv[1], sys.argv[2]
    if name in LESSONS:
        side, segs = LESSONS[name]
    else:
        side, segs = name, sys.argv[3:]
    open(out, 'wb').write(build(side, segs))


if __name__ == '__main__':
    main()
