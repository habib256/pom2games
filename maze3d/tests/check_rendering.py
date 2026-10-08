#!/usr/bin/env python3
"""Exercise the game's actual 6502 drawing routines on both HGR pages.

Fixtures branch out after normal game initialization, avoiding a second
implementation of the renderer. Check visible bytes, holes, HUD and hidden
page, native line coverage, packed sprite pixels and distant wall occlusion.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / "maze3d"
sys.path.insert(0, str(ROOT / "dev/tools"))
sys.path.insert(0, str(GAME / "tools"))
import a2test
from pack_sprites import pattern, SOURCES


def fixture(work, name, body, page=0, background=0):
    source = (GAME / "src/maze3d.s").read_text().replace(
        "main_loop:\n", "        JMP test_entry\nmain_loop:\n", 1)
    source += f'''
.segment "CODE"
test_entry:
        LDA #$20
        STA pix_addr_hi
        LDA #0
        STA pix_addr_lo
        TAY
        LDA #{background}
@fill:  STA (pix_addr_lo),Y
        INY
        BNE @fill
        INC pix_addr_hi
        LDX pix_addr_hi
        CPX #$60
        BNE @fill
        LDA #{page}
        JSR set_draw_page
test_begin:
{body}
test_end:
        JMP test_end
'''
    src = work / (name + ".s")
    src.write_text(source)
    obj, binary, labels = src.with_suffix('.o'), src.with_suffix('.bin'), src.with_suffix('.lbl')
    config = work / 'fixture.cfg'
    config.write_text((GAME / 'src/maze3d.cfg').read_text().replace(
        '"build/maze3d_text.bin"', '"' + str(work / 'text.bin') + '"').replace(
        '"build/maze3d_state.bin"', '"' + str(work / 'state.bin') + '"'))
    subprocess.run(['ca65', '-g', '-t', 'none', '-I', str(GAME / 'src'),
                    '-I', str(GAME / 'build'), '-I', str(ROOT / 'dev/lib/apple2'),
                    '-I', str(ROOT / 'dev/lib/hgr'), '-I', str(ROOT / 'dev/lib/font'),
                    '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(config), '-Ln', str(labels), '-o', str(binary), str(obj)], check=True)
    disk = a2test.build_disk(work, 'FIXTURE', binary)
    l = a2test.labels(labels)
    r = a2test.run(disk, [l.until('test_begin'), l.until('test_end'), 'peek:2000:16384'],
                   emulator=a2test.A2SHOT)
    return r.mem(0x2000, 16384), r.cycles[1] - r.cycles[0]


def assign(**values):
    return '\n'.join(f'        LDA #{value}\n        STA {name}' for name, value in values.items()) + '\n'


def native(x):
    return 28 + x // 8 * 7 + min(x % 8, 6)


def pixel(memory, x, y, page=0):
    return bool(memory[page * 8192 + a2test.hgr_offset(y) + x // 7] & 1 << (x % 7))


def primitives(work):
    for page in (0, 0x60):
        index = int(page != 0)
        memory, cycles = fixture(work, 'clear' + str(index), '        JSR clear_viewport', page, 255)
        expected = bytearray([255] * 16384)
        for y in range(160):
            offset = index * 8192 + a2test.hgr_offset(y)
            expected[offset:offset + 40] = bytes(40)
        assert memory == expected, 'clear changed HUD, holes or hidden page'
        print(f'viewport page {index + 1}: {cycles} cycles')
        body = ''
        lines = [(0, 0, 255, 159), (220, 140, 35, 20), (40, 0, 50, 159),
                 (7, 12, 6, 150), (0, 191, 255, 191), (100, 90, 100, 90)]
        # Each line gets its own fixture so intersection pixels do not mask gaps.
        for n, ends in enumerate(lines):
            x0, y0, x1, y1 = ends
            body = assign(ln_x0=x0, ln_y0=y0, ln_x1=x1, ln_y1=y1) + '        JSR line_xy'
            memory, cycles = fixture(work, f'line{index}_{n}', body, page)
            actual = {(x, y) for y in range(192) for x in range(280) if pixel(memory, x, y, index)}
            x0, x1 = native(x0), native(x1)
            dx, dy = x1 - x0, y1 - y0
            major = max(abs(dx), abs(dy))
            assert len(actual) == major + 1
            assert (x0, y0) in actual and (x1, y1) in actual
            assert all(min(x0, x1) <= x <= max(x0, x1) and min(y0, y1) <= y <= max(y0, y1)
                       and abs(dy * (x - x0) - dx * (y - y0)) <= major / 2 for x, y in actual)
            ordered = sorted(actual, key=lambda p: p[0] if abs(dx) >= abs(dy) else p[1])
            assert all(max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1 for a, b in zip(ordered, ordered[1:]))
            expected = bytearray(16384)
            for x, y in actual:
                expected[index * 8192 + a2test.hgr_offset(y) + x // 7] |= 1 << (x % 7)
            assert memory == expected, 'line touched holes or hidden page'
            if n == 0:
                print(f'long diagonal page {index + 1}: {cycles} cycles')
        body = ''
        expected = bytearray(16384)
        for y, (x0, x1) in enumerate(((0, 255), (7, 7), (2, 10), (250, 255), (13, 42))):
            body += assign(fl_x0=x0, fl_x1=x1, fl_y0=y) + '        JSR hline\n'
            for x in range(native(x0), native(x1) + 1):
                expected[index * 8192 + a2test.hgr_offset(y) + x // 7] |= 1 << (x % 7)
        # Keep injected code within the game's DOS memory ceiling. These
        # disjoint horizontal/vertical scenes need not share one fixture.
        memory, _ = fixture(work, 'hspans' + str(index), body, page)
        assert memory == expected, 'horizontal span mismatch'
        body = ''
        expected = bytearray(16384)
        for x in (0, 7, 100, 255):
            body += assign(fl_x0=x, fl_y0=10, fl_y1=191) + '        JSR vline\n'
            for y in range(10, 192):
                xx = native(x)
                expected[index * 8192 + a2test.hgr_offset(y) + xx // 7] |= 1 << (xx % 7)
        memory, _ = fixture(work, 'vspans' + str(index), body, page)
        assert memory == expected, 'vertical span mismatch'


def sprites(work):
    # Independently interpret the original TMS art, including real colour parity,
    # downsampling, magnification and preserved trailing background pixels.
    for page in (0, 0x60):
        index = int(page != 0)
        for size, scale in enumerate((0, 1, 2, 4, -1, -2, -3)):
            expected = bytearray([0x7F] * 16384)
            body = ''
            for kind, (file, label) in enumerate(SOURCES):
                col, top = kind * 10, (0, 16, 40, 88, 156, 164, 168)[size]
                body += assign(mob_sz=size, mob_curx=col, mob_spy=top)
                body += f'        LDA #{kind}\n        STA mob_type\n        LDX #0\n        JSR draw_packed_mob\n'
                pat = pattern(GAME / 'src' / file, label)
                source = [[(pat[y + x // 8 * 16] >> (7 - x % 8)) & 1 for x in range(16)] for y in range(16)]
                factor = 2 if scale == 0 else 2 ** (1 - scale) if scale < 0 else 1
                width = 16 // factor if scale <= 0 else 16 * scale
                height = width
                for y in range(height):
                    for x in range(width):
                        if scale <= 0:
                            bit = any(source[y * factor + yy][x * factor + xx]
                                      for yy in range(factor) for xx in range(factor))
                        else:
                            bit = source[y // scale][x // scale]
                        physical = col * 7 + x
                        if size in (1, 2, 3):
                            bit = bit and physical % 2 == (0 if kind == 2 else 1)
                        offset = index * 8192 + a2test.hgr_offset(top + y) + physical // 7
                        mask = 1 << (physical % 7)
                        expected[offset] = (expected[offset] & ~mask) | (mask if bit else 0)
                    for byte in range((width + 6) // 7):
                        offset = index * 8192 + a2test.hgr_offset(top + y) + col + byte
                        if size in (1, 2, 3) and kind in (1, 3):
                            expected[offset] |= 128
            memory, cycles = fixture(work, f'sprites{index}_{size}', body, page, 0x7F)
            assert memory == expected, 'packed sprites differ from original art or overwrite padding'
            if size == 3:
                print(f'four 64px packed sprites page {index + 1}: {cycles} cycles')


def visibility():
    l = a2test.labels(GAME / 'build/maze3d.lbl')
    prefix = ['wait:2200', 'key:X', 'wait:130', 'press:L', l.until('render_3d')]
    prefix += [f'poke:{0x1000+i:04x}:{2 if i % 11 < 10 else 0:02x}' for i in range(77)]
    prefix += [l.poke('p_col', 0), l.poke('p_row', 3), l.poke('p_face', 1)]
    prefix += [f'poke:{0x10b0+i:04x}:ff' for i in range(8)]
    for i, col in enumerate((1, 5, 9, 10)):
        prefix += [f'poke:{0x10a0+i:04x}:{col:02x}', f'poke:{0x10a8+i:04x}:03',
                   f'poke:{0x10b0+i:04x}:00']
    for blocked, expected in ((False, bytes((1, 5, 9, 10, 0, 0, 0, 0))),
                              (True, bytes((1, 0, 0, 0, 0, 0, 0, 0)))):
        steps = prefix + (['poke:1023:00'] if blocked else [])
        steps += [l.until('play_input'), l.peek('visible_depth', 8)]
        r = a2test.run(ROOT / 'dist/MAZE3D.dsk', steps, emulator=a2test.A2SHOT)
        assert r.mem(l['visible_depth'], 8) == expected, 'monster visible through wall or missing at distance'
    print('visibility: monsters at depths 1, 5, 9 and 10; walls stop the scan')


def main():
    with tempfile.TemporaryDirectory(prefix='maze3d-render-') as tmp:
        work = Path(tmp)
        primitives(work)
        sprites(work)
    visibility()
    print('rendering: both HGR pages, lines, viewport, packed sprites and occlusion verified')


if __name__ == '__main__':
    main()
