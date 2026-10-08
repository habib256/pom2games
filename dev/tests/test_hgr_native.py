#!/usr/bin/env python3
"""Test standalone shared ASM modules with their default scratch allocations."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(ROOT / 'dev/tools/assets'))
import a2test
from pack_hgr_sprites import packed


def put(**values):
    return '\n'.join(f'        LDA #{v}\n        STA {k}' for k, v in values.items()) + '\n'


def reference_line(ends):
    x0, y0, x1, y1 = ends
    if x1 < x0:
        x0, y0, x1, y1 = x1, y1, x0, y0
    dx, dy = x1 - x0, abs(y1 - y0)
    sy = 1 if y1 >= y0 else -1
    major, minor = max(dx, dy), min(dx, dy)
    error = major // 2
    pixels = []
    for n in range(major + 1):
        pixels.append((x0, y0))
        if n == major:
            break
        if dx >= dy:
            x0 += 1
        else:
            y0 += sy
        error -= minor
        if error < 0:
            error += major
            if dx >= dy:
                y0 += sy
            else:
                x0 += 1
    return pixels


def check(work, page, compressor):
    # Deliberately cover X=255, opposite directions, steep and flat lines.
    lines = [(0,0,255,191), (255,0,0,191), (3,180,8,1),
             (20,191,20,0), (255,191,255,191), (0,100,255,100)]
    body = put(hgr_front_page=0) + f'        LDA #{page}\n        JSR hgr_set_draw_page\n        JSR fill_zero\n'
    for x0,y0,x1,y1 in lines:
        body += put(hl_ln_x0=x0, hl_ln_y0=y0, hl_ln_x1=x1, hl_ln_y1=y1)
        body += '        JSR hgr_line8\n'
    body += put(hs_end_col=39, hs_left_mask=0x78, hs_right_mask=0x07)
    body += '        LDA hgr_lo+190\n        STA hs_ptr\n        LDA hgr_hi+190\n        STA hs_ptr+1\n        LDY #36\n        JSR hgr_hspan\n'
    body += put(hs_left_mask=0x40)
    body += '        LDY #39\n        LDX #0\n        LDA #192\n        JSR hgr_vspan\n'
    body += '''lines_done:
        JSR fill_ff
        JSR hgr_clear_viewport160
clear_done:
        JSR fill_zero
'''
    # Both engines share the colour module; repeat includes exercise guards.
    pat = [0xA5 if y % 2 else 0xFF for y in range(32)]
    data = packed(pat, 4)
    body += put(sp_ptr='<sprite_data', **{'sp_ptr+1': '>sprite_data'}, hsp_col=3,
                sp_yy=20, sp_wout=10, packed_rows=16, packed_repeat=4, packed_tail=1)
    body += '        LDA #HSPR_ORANGE\n        JSR hgr_spr16_color_a\n        JSR hgr_sprite_packed\nsprite_done:\n'
    raw = bytes(((i * 37) ^ (i >> 3)) & 255 for i in range(8192))
    (work/'raw.hgr').write_bytes(raw)
    subprocess.run([str(compressor), '-c', '-9', '-h', str(work/'raw.hgr'), str(work/'raw.lz4')],
                   check=True, stdout=subprocess.DEVNULL)
    body += put(lz4fh_src='<compressed_data', **{'lz4fh_src+1': '>compressed_data'},
                lz4fh_dst=0, **{'lz4fh_dst+1': 0x40 if page else 0x20})
    body += '        JSR lz4fh_unpack\ndecode_done:\n        JMP decode_done\n'
    source = '.include "apple2.inc"\n.globalzp fill_ptr, fill_value, lz4fh_src, lz4fh_dst, sp_ptr, sp_yy, sp_wout\n.globalzp hl_ln_x0, hl_ln_y0, hl_ln_x1, hl_ln_y1, hs_ptr, hs_left_mask, hs_right_mask, hs_end_col\n.code\nentry:\n'+body+'''
fill_ff:
        LDA #255
        BNE fill_memory
fill_zero:
        LDA #0
fill_memory:
        STA fill_value
        LDA #0
        STA fill_ptr
        LDA #$20
        STA fill_ptr+1
        LDY #0
@loop:  LDA fill_value
        STA (fill_ptr),Y
        INY
        BNE @loop
        INC fill_ptr+1
        LDA fill_ptr+1
        CMP #$60
        BNE @loop
        RTS
.zeropage
fill_ptr: .res 2
fill_value: .res 1
.code
.include "hgr_scanline.inc"
.include "hgr_flip.asm"
.include "hgr_line.asm"
.include "hgr_span.asm"
.include "hgr_clear_rows.asm"
.include "hgr_sprite_packed.asm"
.include "hgr_sprite_color.inc"
.include "lz4fh.asm"
sprite_data:
'''+ '\n'.join('        .byte '+','.join(str(v) for v in data[i:i+16]) for i in range(0,len(data),16))+f'\ncompressed_data: .incbin "{work / "raw.lz4"}"\n'
    src=work/'native.s'; src.write_text(source)
    config=work/'native.cfg'; config.write_text('''MEMORY {
 ZP: start=$50, size=$B0, type=rw;
 MAIN: start=$6000, size=$3600, type=rw, file=%O;
}
SEGMENTS {
 ZEROPAGE: load=ZP, type=zp;
 CODE: load=MAIN, type=ro;
 BSS: load=MAIN, type=bss;
}
''')
    obj=work/'native.o'; binary=work/'native.bin'; lbl=work/'native.lbl'
    subprocess.run(['ca65','-g','-I',str(ROOT/'dev/lib/apple2'),'-I',str(ROOT/'dev/lib/hgr'),
                    '-o',str(obj),str(src)],check=True)
    subprocess.run(['ld65','-C',str(config),'-Ln',str(lbl),'-o',str(binary),str(obj)],check=True)
    disk=a2test.build_disk(work,'NATIVE',binary)
    labels=a2test.labels(lbl)
    steps=[]
    for name in ('lines_done','clear_done','sprite_done','decode_done'):
        steps += [labels.until(name), 'peek:2000:16384']
    result=a2test.run(disk,steps,emulator=a2test.A2SHOT)
    base=8192 if page else 0
    expected=bytearray(16384)
    for line in lines:
        for x,y in reference_line(line):
            expected[base+a2test.hgr_offset(y)+x//7] |= 1 << (x%7)
    for col, mask in ((36,0x78),(37,0x7F),(38,0x7F),(39,0x07)):
        expected[base+a2test.hgr_offset(190)+col] |= mask
    for y in range(192):
        expected[base+a2test.hgr_offset(y)+39] |= 0x40
    assert result.dumps[0] == expected, 'standalone native line raster/page mismatch'
    expected=bytearray([255]*16384)
    for y in range(160):
        offset=base+a2test.hgr_offset(y)
        expected[offset:offset+40]=bytes(40)
    assert result.dumps[1] == expected, 'clear changed HUD, padding or other page'
    expected=bytearray(16384)
    for y in range(64):
        for col in range(10):
            byte=data[y//4*10+col]
            byte &= 0x2A if (3+col)%2 == 0 else 0x55
            expected[base+a2test.hgr_offset(20+y)+3+col]=byte|0x80
    assert result.dumps[2] == expected, 'packed sprite colour/repetition/page mismatch'
    expected[base:base+8192]=raw
    assert result.dumps[3] == expected, 'LZ4FH roundtrip changed output or other page'
    print(f'native libraries page {1 if not page else 2}: default scratch, raster, clear, sprite, LZ4FH OK')


def main():
    with tempfile.TemporaryDirectory(prefix='hgr-native-') as tmp:
        work=Path(tmp)
        compressor=work/'fhpack'
        subprocess.run(['c++','-O2','-o',str(compressor),
                        str(ROOT/'dev/tests/techniques/upstream/fhpack/fhpack.cpp')],check=True)
        for page in (0,0x60):
            check(work,page,compressor)


if __name__ == '__main__':
    main()
