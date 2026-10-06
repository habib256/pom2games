#!/usr/bin/env python3
"""HGR integration tests: actual cc65 code on portable a2run, both video pages.

The expected RAM is calculated per pixel in Python, including untouched bytes
and screen holes. No golden snapshots or host build of the target algorithm.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / 'dev'
sys.path.insert(0, str(DEV / 'tools'))
import fonts
import a2test
from a2test import hgr_offset as offset


def run(args, **kwargs):
    """Run a host command (cl65, make, an emulator...) and return its stdout."""
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True, **kwargs)
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    return p.stdout


def pixel(page, x, y, value, mode='set', white=False):
    if x >= 280 or y >= 192:
        return
    addr, bit = offset(y) + x // 7, 1 << (x % 7)
    if white:
        page[addr] &= 127
    if mode == 'xor':
        if value: page[addr] ^= bit
    elif value: page[addr] |= bit
    else: page[addr] &= 255 ^ bit


def rect(page, x0, y0, x1, y1, set=True):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    for y in range(y0, min(192, y1 + 1)):
        for x in range(x0, min(280, x1 + 1)):
            pixel(page, x, y, set, white=True)


def sprite(page, x, y, rows, width, mode='set'):
    for dy, bits in enumerate(rows):
        for dx in range(width):
            if bits & (1 << (width - 1 - dx)):
                pixel(page, x + dx, y + dy, 1, mode)


def text(page, font, x, y, s, scale):
    for ch in s:
        if x > (264 if scale == 2 else 273) or y > 192 - 8 * scale: break
        glyph = font[(ord(ch) - 32) * 8:(ord(ch) - 31) * 8]
        for dy, bits in enumerate(glyph):
            for dx in range(8):
                if bits & (1 << dx):
                    for sy in range(scale):
                        for sx in range(scale):
                            pixel(page, x + dx * scale + sx, y + dy * scale + sy, 1)
        x += 18 if scale == 2 else 8


def build(work, fixture=None):
    # A tiny pre-shift bank: 10101 / 01110 / 11011, seven phases, two bytes/row.
    data = []
    for phase in range(7):
        for row in (0b10101, 0b01110, 0b11011):
            bits = sum(((row >> (4 - x)) & 1) << (phase + x) for x in range(5))
            data.extend((bits & 127, bits >> 7))
    (work / 'hgr_test_sprite.inc').write_text(
        'static const unsigned char test_bits[] = {' + ','.join(map(str, data)) + '};\n'
        'static const hgr_sprite_t test_sprite = {test_bits, 2, 3};\n')
    mk = work / 'sources.mk'
    mk.write_text(f'HGRC := {DEV}/lib/hgrc\nGFX := {DEV}/lib/gfx\n'
                  f'include {DEV}/lib/hgrc/hgrc.mk\n'
                  'print:\n\t@echo $(HGRC_ALL_SRCS)\n')
    sources = run(['make', '-s', '-f', mk, 'print']).split()
    objects = []
    for source in sources:
        source = Path(source)
        obj = work / (source.stem + '.o')
        run(['cl65', '-t', 'none', '-Oirs', '-I', DEV / 'lib/hgrc',
             '-I', DEV / 'lib/apple2c', '-I', DEV / 'lib/gfx',
             '--asm-include-dir', DEV / 'lib/apple2',
             '--asm-include-dir', DEV / 'lib/hgrc', '-c', '-o', obj, source])
        objects.append(obj)
    archive = work / 'hgrc.lib'
    run(['ar65', 'a', archive, *objects])
    objects = []
    for source in (DEV / 'cc65/crt0_apple2.s', fixture or DEV / 'tests/hgr_fixture.c',
                   DEV / 'lib/apple2c/apple2io_asm.s'):
        obj = work / (source.stem + '.o')
        run(['cl65', '-t', 'none', '-Oirs', '-I', work, '-I', DEV / 'lib/hgrc',
             '-I', DEV / 'lib/apple2c', '-I', DEV / 'lib/gfx', '-c', '-o', obj, source])
        objects.append(obj)
    binary = work / 'test.bin'
    run(['cl65', '-t', 'none', '-C', DEV / 'cc65/apple2_hgr_c.cfg',
         '-m', work / 'test.map', '-o', binary, *objects, archive])
    return a2test.build_disk(work, 'TEST', binary)


def check_archive(work):
    cases = [
        ('clear', 'hgr_clear(0u);', 'hgr_clear_asm.o',
         ('hgr_text16_asm.o', 'hgr_text8_asm.o', 'hgr_sprite_params.o', 'hgr_pixrect_asm.o')),
        ('text8', 'hgr_puts8(0u, 0u, "A");', 'hgr_text8_asm.o',
         ('hgr_text16_asm.o', 'hgr_carrier_params.o', 'hgr_utoa_asm.o', 'hgr_pixrect_asm.o', 'hgr_sprite_params.o')),
        ('text16', 'hgr_puts(0u, 0u, "A");', 'hgr_text16_asm.o',
         ('hgr_text8_asm.o', 'hgr_utoa_asm.o', 'hgr_pixrect_asm.o', 'hgr_sprite_params.o')),
        ('rectangle', 'gfx_filled_rect(0u, 0u, 279u, 191u);', 'hgr_pixrect_asm.o',
         ('hgr_text_params.o', 'hgr_cell_asm.o', 'hgr_carrier_params.o', 'hgr_sprite_params.o')),
        ('sprite7', 'hgr_blit7(0u, 0u, 1u, 1u, bits, HGR_SET);', 'hgr_blit7_asm.o',
         ('hgr_bitmap_asm.o', 'hgr_preshift_asm.o', 'hgr_text_params.o', 'hgr_pixrect_asm.o')),
        ('decimal', 'char b[7]; gfx_utoa(b,65535u); gfx_itoa(b,-32767-1);', 'gfx_num_dec.o',
         ('hgr_text8_asm.o', 'hgr_text16_asm.o', 'hgr_sprite_params.o')),
        ('celltext', 'gfx_gotoxy(0u,0u); gfx_text("A"); gfx_putu(42u);', 'gfx_text.o',
         ('hgr_text16_asm.o', 'hgr_sprite_params.o', 'hgr_pixrect_asm.o')),
        ('dhgr_mode', 'dhgr_init();', 'dhgr.o',
         ('dhgr_pixel.o', 'dhgr_fill.o', 'dhgr_block.o', 'dhgr_small_asm.o', 'gfx_u16_digits.o',
          'dhgr_clear_asm.o', 'dhgr_span_asm.o', 'dhgr_access_asm.o')),
        ('dhgr_pixel', 'dhgr_plot(1u,1u,1u);', 'dhgr_pixel.o',
         ('dhgr_fill.o', 'dhgr_address.o', 'dhgr_block.o', 'dhgr_small_asm.o', 'dhgr_getpixel.o', 'dhgr_read_asm.o')),
        ('dhgr_read', 'return dhgr_getpixel(1u,1u);', 'dhgr_read_asm.o',
         ('dhgr_pixel.o', 'dhgr_write_asm.o', 'dhgr_fill.o', 'dhgr_block.o')),
        ('dhgr_fill', 'dhgr_fill_rect(1u,1u,2u,2u,9u);', 'dhgr_fill.o',
         ('dhgr_pixel.o', 'dhgr_address.o', 'dhgr_block.o', 'dhgr_small_asm.o',
          'dhgr_clear.o', 'dhgr_clear_asm.o', 'dhgr_fill_bits.o', 'dhgr_plot_color.o', 'dhgr_access_asm.o')),
        ('dhgr_clear', 'dhgr_clear(9u);', 'dhgr_clear_asm.o',
         ('dhgr_pixel.o', 'dhgr_fill.o', 'dhgr_fill_bits.o', 'dhgr_bit_rect.o',
          'dhgr_span_asm.o', 'dhgr_access_asm.o', 'dhgr_small_asm.o')),
        ('dhgr_bits', 'dhgr_fill_bits(1u,1u,2u,2u,1u);', 'dhgr_span_asm.o',
         ('dhgr_pixel.o', 'dhgr_fill.o', 'dhgr_clear.o', 'dhgr_clear_asm.o',
          'dhgr_pattern.o', 'dhgr_plot_color.o', 'dhgr_access_asm.o')),
        ('dhgr_small', 'dhgr_small_x=0; dhgr_small_y=0; dhgr_small_char(65u);', 'dhgr_small_asm.o',
         ('dhgr_small.o', 'dhgr_small_string.o', 'hgr_font.o', 'dhgr_fill.o',
          'dhgr_clear_asm.o', 'dhgr_span_asm.o', 'dhgr_access_asm.o')),
        ('dhgr_block', 'unsigned char b[1]; dhgr_read_block(0u,0u,1u,1u,b,1u);', 'dhgr_address.o',
         ('dhgr_pixel.o', 'dhgr_fill.o', 'dhgr_sprite.o', 'dhgr_small_asm.o')),
    ]
    for name, call, required, excluded in cases:
        source = work / ('link_' + name + '.c')
        source.write_text('#include "hgr.h"\n#include "gfx.h"\n#include "dhgr.h"\n'
                          'static const unsigned char bits[] = {127};\n'
                          'int main(void) {' + call + 'return 0;}\n')
        obj, binary, mapfile = source.with_suffix('.o'), source.with_suffix('.bin'), source.with_suffix('.map')
        run(['cl65', '-t', 'none', '-Oirs', '-I', DEV / 'lib/hgrc',
             '-I', DEV / 'lib/apple2c', '-I', DEV / 'lib/gfx', '-c', '-o', obj, source])
        run(['cl65', '-t', 'none', '-C', DEV / 'cc65/apple2_hgr_c.cfg',
             '-m', mapfile, '-o', binary, work / 'crt0_apple2.o', obj, work / 'hgrc.lib'])
        linked = set(re.findall(r'hgrc\.lib\(([^)]+)\)', mapfile.read_text()))
        if not name.startswith('dhgr_'):
            assert not any(n.startswith('dhgr') for n in linked), (name, 'unexpected DHGR dependency')
        assert required in linked, (name, 'missing kernel', required)
        assert not linked.intersection(excluded), (name, 'unwanted families', linked.intersection(excluded))
    print('HGR/DHGR archive: 15 minimal programs exclude unused code and zero-page families.')


def check_cell_text(work, font):
    disk = build(work, DEV / 'tests/gfx_text_fixture.c')
    steps = ['wait:1100']
    for _ in range(4):
        steps += ['peek:1000:1','peek:2000:16384','key: ','wait:60']
    output = run([DEV / 'tools/a2run/a2run','--disk',disk,*steps])
    blocks = re.split(r'(?m)^1000:',output)[1:]
    assert len(blocks) == 4
    page1, page2 = bytes([42])*8192, bytearray(8192)
    for stage, block in enumerate(blocks):
        assert int(block.splitlines()[0],16) == stage
        if stage == 1:
            for x,y,ch in ((272,0,'A'),(0,8,'B'),(0,16,'C'),(0,16,'D')):
                text(page2,font,x,y,ch,1)
        elif stage == 2:
            for y,value in ((24,'65535'),(32,'-32768'),(40,'ABCD')):
                text(page2,font,16,y,value,1)
        elif stage == 3:
            text(page2,font,272,184,'Z',1)
            text(page2,font,0,184,'Q',1)
        lines = re.findall(r'(?m)^[2345][0-9A-F]{3}: ([0-9A-F ]+)$',block)
        actual = bytes.fromhex(' '.join(lines))
        assert actual == page1 + page2, ('gfx cell text scene',stage)
    print('GFX text: 4 scenes passed; page 2, wrap/newline/carriage return,')
    print('decimal/signed/hex, white cells and edge clamping.')


def main():
    run(['make', '-C', DEV / 'tools/a2run'])
    font = bytes(fonts.glyphs(0x20, 0x7F))
    with tempfile.TemporaryDirectory(prefix='pom2-hgr-') as work:
        work = Path(work)
        disk = build(work)
        check_archive(work)
        steps = ['wait:1100']
        for stage in range(21):
            steps += ['peek:1000:1', 'peek:2000:16384', 'key: ', 'wait:300']
        output = run([DEV / 'tools/a2run/a2run', '--disk', disk, *steps])
        blocks = re.split(r'(?m)^1000:', output)[1:]
        assert len(blocks) == 21, 'missing checkpoints'
        page = bytearray([128]) * 8192
        page2 = bytearray([42]) * 8192
        rows = (0x297, 0x16A, 0x3FC)  # 10 leftmost bits of A5 C0 / 5A 80 / FF 00
        for stage, block in enumerate(blocks):
            assert int(block.splitlines()[0], 16) == stage, (stage, 'guest did not finish')
            if stage == 1: rect(page, 0, 0, 255, 3)
            elif stage == 2: rect(page, 0, 5, 279, 8)
            elif stage == 3: rect(page, 65535, 255, 100, 180)
            elif stage == 5:
                rect(page, 3, 15, 12, 16)
                rect(page, 275, 189, 529, 443)
            elif stage == 6: rect(page, 6, 15, 9, 15, False)
            elif stage == 7:
                for x in range(280): pixel(page, x, x % 192, 1)
                for x in range(0, 280, 3): pixel(page, x, x % 192, 0)
            elif stage == 8:
                page[offset(190) + 39] |= 0x12
                page[offset(191) + 39] |= 0x61
            elif stage == 9:
                for p in range(7): sprite(page, p * 22, 50, rows, 10)
                sprite(page, 276, 191, rows, 10)
            elif stage in (11, 12):
                for p in range(7): sprite(page, p * 22, 80, (21, 14, 27), 5, 'xor')
                sprite(page, 276, 191, (21, 14, 27), 5, 'xor')
                if stage == 12:
                    for dy, bits in enumerate((21, 14, 27)):
                        for dx in range(5):
                            if bits & (1 << (4 - dx)): pixel(page, 200 + dx, 80 + dy, 0)
            elif stage == 13:
                text(page, font, 13, 120, 'Hi!', 1)
                text(page, font, 150, 120, 'AB', 2)
                text(page, font, 273, 184, 'AB', 1)
            elif stage == 14:
                for y in range(100, 104):
                    for col in range(6): page[offset(y) + col] = 128 | (0x2A if col % 2 == 0 else 0x55)
            elif stage == 15:
                for x, y, ch, high in ((6, 136, 'C', 128), (15, 154, 'D', 0)):
                    glyph = bytearray(8192)
                    text(glyph, font, x, y, ch, 2)
                    for yy in range(y, y + 16):
                        for col in range(40):
                            addr = offset(yy) + col
                            if glyph[addr]:
                                carrier = 0x2A if col % 2 == 0 else 0x55
                                page[addr] |= (glyph[addr] & carrier) | high
            elif stage == 16:
                rect(page, 50, 20, 137, 35, False)
                text(page, font, 122, 20, '9', 2)
                text(page, font, 0, 20, '0', 2)
                text(page, font, 150, 20, '-32768', 2)
                text(page, font, 0, 40, 'ABCD', 2)
                text(page, font, 220, 60, '65535', 1)
            elif stage == 17: rect(page, 272, 184, 277, 189)
            elif stage == 18: rect(page, 272, 184, 277, 189, False)
            elif stage == 19: rect(page2, 279, 191, 0, 0)
            lines = re.findall(r'(?m)^[2345][0-9A-F]{3}: ((?:[0-9A-F]{2} ?)+)$', block)
            actual, expected = bytes.fromhex(' '.join(lines)), page + page2
            assert len(actual) == 16384, (stage, len(actual))
            if actual != expected:
                i = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
                raise AssertionError(f'stage {stage}: ${0x2000+i:04X} = {actual[i]:02X}, expected {expected[i]:02X}')
        print('HGR: 21 checkpoints passed (rectangles 256/280, clipping, both pages,')
        print('pixels, sprites SET/CLEAR/XOR and 7 phases, text, numbers, cells, colorization).')
        check_cell_text(work, font)


if __name__ == '__main__':
    main()
