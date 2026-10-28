#!/usr/bin/env python3
"""extract.py: decode the three Robot Odyssey sides and cut out every loader segment.

original/{A_ROBOTROPOLIS,B_LABS,C_TUTORIAL}.woz -> build/X.dsk (DOS order),
build/X.po (ProDOS block order: block b = track b/8, what the custom RWTS reads)
and build/files/X/BBB_AAAA_role.bin: each segment is cut only from the side(s)
the resident loader really reads it from (block numbers overlap between
sides). SEGMENTS is checked against the 6-byte descriptors (block, address,
length) of the loader table $4FE5-$51AF of the $4000 module (blocks $030-$038);
the two entries marked * use a descriptor the module patches before loading.
Side B also gets its chip library (block 8 directory, 3 blocks per chip).
See docs/logic/loader.md.

Usage: extract.py [ORIGINAL_DIR [BUILD_DIR]]
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SIDES = {'A': 'A_ROBOTROPOLIS', 'B': 'B_LABS', 'C': 'C_TUTORIAL'}
DOS2PO = [0, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 15]
TABLE = range(0x4FE5, 0x51B0, 6)

# sides, block, address, length, role (rt = Robotropolis, l1-l5 = levels,
# pv = Preview, cd = Chip Design, tut = the six tutorials, lc = language card)
SEGMENTS = [
    ('ABC', 0x030, 0x4000, 0x1200, 'module'),
    ('ABC', 0x039, 0x0803, 0x05D3, 'scenes'),
    ('ABC', 0x03C, 0x6000, 0x02A6, 'menu'),
    ('ABC', 0x03E, 0x6300, 0x38CB, 'menu_data'),
    ('ABC', 0x05B, 0x9500, 0x23D7, 'engine'),
    ('AB', 0x06E, 0x5A00, 0x0600, 'format'),
    ('A', 0x06D, 0xD400, 0x0183, 'chip_preset'),
    ('A', 0x008, 0x6000, 0x019A, 'intro'),
    ('A', 0x009, 0x6300, 0x49BB, 'story_data'),
    ('A', 0x02E, 0x6000, 0x01AD, 'ending'),
    ('A', 0x03E, 0x6200, 0x01CB, 'ending_6200*'),
    ('A', 0x072, 0x1AB0, 0x054C, 'rt_1ab0'),
    ('A', 0x075, 0x8200, 0x0CD5, 'rt_8200'),
    ('A', 0x07C, 0xB8E0, 0x06B9, 'rt_b8e0'),
    ('A', 0x080, 0xD000, 0x0FFE, 'rt_lc_d000'),
    ('A', 0x088, 0xF000, 0x0FF4, 'rt_lc_f000'),
    ('A', 0x071, 0xD000, 0x01AA, 'l1_chip0'),
    ('A', 0x090, 0x6000, 0x2200, 'l1_world'),
    ('A', 0x0A1, 0x0803, 0x1105, 'l1_code'),
    ('A', 0x0AA, 0x8EF0, 0x0505, 'l1_data'),
    ('A', 0x0AD, 0x6E40, 0x13C0, 'l2_world'),
    ('A', 0x0B7, 0x0803, 0x1092, 'l2_code'),
    ('A', 0x0C0, 0x8EF0, 0x0142, 'l2_data'),
    ('A', 0x0C1, 0x6E40, 0x13C0, 'l3_world'),
    ('A', 0x0CB, 0x0803, 0x1270, 'l3_code'),
    ('A', 0x0D5, 0x8EF0, 0x05FB, 'l3_data'),
    ('A', 0x0D8, 0x6E40, 0x13C0, 'l4_world'),
    ('A', 0x0E2, 0x0803, 0x108B, 'l4_code'),
    ('A', 0x0EB, 0x8EF0, 0x0561, 'l4_data'),
    ('A', 0x0EE, 0x6E40, 0x13C0, 'l5_world'),
    ('A', 0x0F8, 0x0803, 0x1253, 'l5_code'),
    ('A', 0x102, 0x8EF0, 0x05DE, 'l5_data'),
    ('B', 0x071, 0x0803, 0x0BAE, 'pv_code'),
    ('B', 0x077, 0x14C0, 0x0AF6, 'pv_14c0'),
    ('B', 0x07D, 0x6000, 0x1FF8, 'pv_6000'),
    ('B', 0x08D, 0x7F80, 0x0818, 'pv_7f80'),
    ('B', 0x092, 0x8880, 0x0440, 'pv_8880'),
    ('B', 0x095, 0x9000, 0x0395, 'pv_9000'),
    ('B', 0x097, 0xD000, 0x0F65, 'pv_lc_d000'),
    ('B', 0x09F, 0xE000, 0x00CE, 'pv_lc_e000'),
    ('B', 0x0A0, 0xE470, 0x0BD0, 'pv_lc_e470'),
    ('B', 0x0A7, 0x0B00, 0x149B, 'lab_0b00'),
    ('B', 0x0B2, 0xB8E0, 0x06A1, 'lab_b8e0'),
    ('B', 0x0B6, 0xD000, 0x0FFA, 'lab_lc_d000'),
    ('B', 0x0BE, 0xF000, 0x0FF8, 'lab_lc_f000'),
    ('B', 0x0C6, 0x6000, 0x3500, 'lab_6000'),
    ('B', 0x0E1, 0x0803, 0x02FB, 'lab_code'),
    ('B', 0x0E3, 0x6000, 0x3500, 'cd_6000'),
    ('B', 0x0FE, 0x0803, 0x02F3, 'cd_code'),
    ('B', 0x100, 0x0B00, 0x0800, 'cd_0b00'),
    ('B', 0x0A6, 0xD000, 0x0013, 'cd_chip0'),
    ('B', 0x06D, 0xD800, 0x0183, 'cd_chip2*'),
    ('C', 0x008, 0x14C0, 0x0B1C, 'tut_14c0'),
    ('C', 0x00E, 0xB900, 0x0572, 'tut_b900'),
    ('C', 0x011, 0xD000, 0x0FF2, 'tut_lc_d000'),
    ('C', 0x019, 0xF000, 0x0C76, 'tut_lc_f000'),
    ('C', 0x020, 0x0803, 0x0C9E, 'tut_code1'),
    ('C', 0x027, 0x14C0, 0x0679, 'anatomy_14c0'),
    ('C', 0x06D, 0x6000, 0x3350, 'anatomy_6000'),
    ('C', 0x02B, 0x14C0, 0x0679, 'wiring_14c0'),
    ('C', 0x087, 0x6000, 0x2EF9, 'wiring_6000'),
    ('C', 0x09F, 0x6000, 0x33D8, 'sensors_6000'),
    ('C', 0x0B9, 0x0803, 0x0982, 'toolkit_code'),
    ('C', 0x0BE, 0x14C0, 0x0679, 'toolkit_14c0'),
    ('C', 0x0C2, 0x6000, 0x3165, 'toolkit_6000'),
    ('C', 0x0DB, 0x0803, 0x0A46, 'tut_code2'),
    ('C', 0x0E1, 0x14C0, 0x0679, 'circuits_14c0'),
    ('C', 0x0E5, 0x6000, 0x30E0, 'circuits_6000'),
    ('C', 0x0FE, 0x6000, 0x30E2, 'teamwork_6000'),
]
NAME_AT = [0x12 * k for k in range(13)]  # directory entries: 15 chars, 2 pages of 13


def prodos_order(dsk):
    return b''.join(dsk[(t * 16 + DOS2PO[s]) * 256:(t * 16 + DOS2PO[s] + 1) * 256]
                    for t in range(35) for s in range(16))


def descriptors(po):
    mod = po[0x30 * 512:0x39 * 512]  # resident module at $4000
    return {tuple(int.from_bytes(mod[a - 0x4000 + k:a - 0x3FFE + k], 'little') for k in (0, 2, 4))
            for a in TABLE}


def library(po):
    """Side B chip library: (letter, name, 3 blocks = 1 KB chip + header) per used entry."""
    d = po[8 * 512:9 * 512]
    for n in range(26):
        o = (n // 13) * 256 + NAME_AT[n % 13]
        name = ''.join(chr(c & 0x7F) for c in d[o:o + 15]).strip()
        b = 9 + 3 * n
        if name and b + 3 <= 0x30:
            yield chr(65 + n), name, b, po[b * 512:(b + 3) * 512]


def main():
    orig = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else HERE.parent / 'original')
    build = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else HERE.parent / 'build')
    build.mkdir(parents=True, exist_ok=True)
    for key, side in SIDES.items():
        dsk = build / f'{side}.dsk'
        subprocess.run([sys.executable, '-I', str(HERE / 'flux2dsk.py'), str(orig / f'{side}.woz'), str(dsk)],
                       check=True)
        po = prodos_order(dsk.read_bytes())
        (build / f'{side}.po').write_bytes(po)
        table = descriptors(po)
        out = build / 'files' / side
        out.mkdir(parents=True, exist_ok=True)
        for old in out.glob('*.bin'):
            old.unlink()
        count = 0
        for sides, blk, addr, n, role in SEGMENTS:
            if key not in sides:
                continue
            if not role.endswith('*') and role != 'module' and (blk, addr, n) not in table:
                sys.exit(f'{side}: ${blk:03X} ${addr:04X}+${n:04X} is not in the loader table')
            (out / f'{blk:03X}_{addr:04X}_{role.rstrip("*")}.bin').write_bytes(po[blk * 512:blk * 512 + n])
            count += 1
        if key == 'B':
            for letter, name, b, data in library(po):
                slug = ''.join(c if c.isalnum() else '_' for c in name.lower())
                (out / f'{b:03X}_D000_lib{letter}_{slug}.bin').write_bytes(data)
                count += 1
            (out / '008_5A00_lib_directory.bin').write_bytes(po[8 * 512:9 * 512])
            count += 1
        print(f'{side}: {count} segments -> {out}')


if __name__ == '__main__':
    main()
