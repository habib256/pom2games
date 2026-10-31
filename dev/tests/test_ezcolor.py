#!/usr/bin/env python3
"""lib/apple2/ezcolor.asm + the dev/lib/tms9918 port on a2run --ezcolor=N
(E-Z Color Graphics Interface, a TMS9918A in a slot): detection in every
slot it may sit in (and none), the boot-slot skip and slot 3, the VRAM
around the probe left as it was; the access helpers, ez_fill / ez_copy /
ez_read and their blanked variants; the frame flag; a Graphics I screen the
TMS_Rogue way (init_vdp_g1, name_at_rc, WRT_DATA_*, a 16x16 sprite) and a
Graphics II one (init_vdp_g2, line_xy, text_blit_glyph) rendered to PNG; the
silicon-strict counter (0 for every library path, > 0 for an unpadded
loop); the NMOS dummy read of an indexed store; the frame IRQ.
Then the same library on POM2's own card (a2shot --ezcolor=N, silicon-strict
access window, ba7f04da): detection in slots 4 and 7 and none, the helpers'
round trip (R1 bit 7 set first: 16 KB addressing), a Graphics I screen whose
VRAM is byte-identical to a2run's, droppedAccesses 0 for every library path
and > 0 for a 4-cycle burst."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402
import tms9918  # noqa: E402

LIB = ROOT / 'dev/lib'
OUT = ROOT / 'build/tests'            # the rendered pictures (ignored)

HEAD = '''
.include "apple2.inc"
.include "zp.inc"
.include "tms9918.inc"
.bss
r_slot:  .res 1
r_p:     .res 1
r_slotx: .res 1
r_buf:   .res 16
r_copy:  .res 300
r_irq:   .res 1
r_boot:  .res 1
.code
'''

PROGRAM_A = HEAD + '''
t_detect:
        JSR     ez_detect
        STA     r_slot
        PHP
        PLA
        STA     r_p
        LDA     ez_slotx
        STA     r_slotx
        RTS

t_mark:                                 ; 11 22 33 44 at $3FFC
        LDA     #$FC
        LDX     #$3F
        JSR     ez_vram_addr_w
        LDA     #$11
        JSR     ez_data_w
        LDA     #$22
        JSR     ez_data_w
        LDA     #$33
        JSR     ez_data_w
        LDA     #$44
        JSR     ez_data_w
        RTS

t_helpers:
        LDA     #$F4
        LDX     #7
        JSR     ez_set_reg
        LDA     #$34                    ; 16 bytes at $1234, read back
        LDX     #$12
        JSR     ez_vram_addr_w
        LDY     #0
:       TYA
        EOR     #$A5
        JSR     ez_data_w
        INY
        CPY     #16
        BNE     :-
        LDA     #$34
        LDX     #$12
        JSR     ez_vram_addr_r
        LDY     #0
:       JSR     ez_data_r
        STA     r_buf,Y
        INY
        CPY     #16
        BNE     :-
        LDA     #<300
        STA     ez_count
        LDA     #>300
        STA     ez_count+1
        LDA     #$00                    ; 300 x $5A at $2000
        LDX     #$20
        JSR     ez_vram_addr_w
        LDA     #$5A
        JSR     ez_fill
        LDA     #$00                    ; 300 bytes of src_tbl at $2200
        LDX     #$22
        JSR     ez_vram_addr_w
        LDA     #<src_tbl
        STA     ez_ptr
        LDA     #>src_tbl
        STA     ez_ptr+1
        JSR     ez_copy
        LDA     #$00                    ; and back into r_copy
        LDX     #$22
        JSR     ez_vram_addr_r
        LDA     #<r_copy
        STA     ez_ptr
        LDA     #>r_copy
        STA     ez_ptr+1
        JSR     ez_read
        LDA     #<513                   ; blanked variants (R1 = 0 after reset)
        STA     ez_count
        LDA     #>513
        STA     ez_count+1
        LDA     #$00
        LDX     #$30
        JSR     ez_vram_addr_w
        LDA     #$77
        JSR     ez_fill_blank
        LDA     #<src_tbl
        STA     ez_ptr
        LDA     #>src_tbl
        STA     ez_ptr+1
        LDA     #<300
        STA     ez_count
        LDA     #>300
        STA     ez_count+1
        LDA     #$00
        LDX     #$34
        JSR     ez_vram_addr_w
        JSR     ez_copy_blank
        RTS

t_vbl:                                  ; three frame flags
        EZ_WAIT_VBLANK_SAFE
        EZ_WAIT_VBLANK
        WAIT_VBLANK
        RTS

t_m1:                                   ; a TMS_Rogue-style Graphics I screen
        JSR     init_vdp_g1
        JSR     clear_name_table
        LDA     #$00                    ; font: chars $20-$7F at $0100
        LDX     #$01
        JSR     ez_vram_addr_w
        LDA     #<tms_bbfont
        STA     ez_ptr
        LDA     #>tms_bbfont
        STA     ez_ptr+1
        LDA     #<768
        STA     ez_count
        LDA     #>768
        STA     ez_count+1
        JSR     ez_copy
        LDA     #$00                    ; colours: white on dark blue
        LDX     #$20
        JSR     ez_vram_addr_w
        LDA     #32
        STA     ez_count
        LDA     #0
        STA     ez_count+1
        LDA     #$F4
        JSR     ez_fill
        LDA     #$00                    ; chars 0-7 (blank): light yellow
        LDX     #$20
        JSR     ez_vram_addr_w
        LDA     #$4B
        JSR     ez_data_w
        LDA     #2
        STA     vdp_row
        LDA     #4
        STA     vdp_col
        JSR     name_at_rc
        JSR     vdp_set_write
        LDY     #0
:       LDA     msg,Y
        BEQ     :+
        WRT_DATA_REG
        INY
        BNE     :-
:       LDA     #10
        STA     vdp_row
        LDA     #8
        STA     vdp_col
        LDA     #'*'
        JSR     print_at_rc
        LDA     #$00                    ; sprite pattern 0 = Quale's sword
        LDX     #$38
        JSR     ez_vram_addr_w
        LDA     #<outfit_sword_pat
        STA     ez_ptr
        LDA     #>outfit_sword_pat
        STA     ez_ptr+1
        LDA     #32
        STA     ez_count
        LDA     #0
        STA     ez_count+1
        JSR     ez_copy
        LDA     #$00                    ; SAT[0]: Y 79, X 120, pattern 0, red
        LDX     #$1B
        JSR     ez_vram_addr_w
        WRT_DATA_VAL 79
        WRT_DATA_VAL 120
        WRT_DATA_VAL 0
        WRT_DATA_VAL 8
        WRT_DATA_VAL $D0
        LDA     #$C3                    ; 16x16 sprites, magnified
        LDX     #1
        JSR     ez_set_reg
        RTS
msg:    .byte   "HELLO E-Z COLOR", 0

t_fast:                                 ; unpadded stores, display on
        LDA     #$C0
        LDX     #1
        JSR     ez_set_reg
        LDA     #$00
        LDX     #$00
        JSR     ez_vram_addr_w
        LDY     #0
:       STA     $C0C0                   ; slot 4, 9 cycles a byte
        INY
        BNE     :-
        RTS

t_r16k:                                 ; R1 = $80: 16 KB, display off
        LDA     #$80
        LDX     #1
        JSR     ez_set_reg
        RTS

t_burst:                                ; stores 4 cycles apart, display on
        LDA     #$C0
        LDX     #1
        JSR     ez_set_reg
        LDA     #$00
        LDX     #$00
        JSR     ez_vram_addr_w
        LDY     #0
:       STA     $C0C0
        STA     $C0C0
        INY
        BNE     :-
        RTS

t_indexed:                              ; STA EZ_DATA,X: dummy read first
        LDA     #$00
        LDX     #$01
        JSR     ez_vram_addr_w
        LDX     ez_slotx
        LDA     #$AB
        STA     EZ_DATA,X
        RTS

t_irq:                                  ; R1 IE: about one IRQ a frame
        LDA     #0
        STA     r_irq
        LDA     #<irq_h
        STA     $03FE
        LDA     #>irq_h
        STA     $03FF
        LDA     #$A0                    ; 16K, display off, IE
        LDX     #1
        JSR     ez_set_reg
        CLI
        JSR     delay5
        SEI
        RTS
t_noirq:
        LDA     #0
        STA     r_irq
        LDA     #<irq_h
        STA     $03FE
        LDA     #>irq_h
        STA     $03FF
        LDA     #$80                    ; IE off
        LDX     #1
        JSR     ez_set_reg
        CLI
        JSR     delay5
        SEI
        RTS
irq_h:  INC     r_irq
        JSR     ez_status               ; drops /INT
        LDA     $45                     ; the Monitor saved A there
        RTI
delay5:                                 ; ~5 frames
        LDX     #66
:       LDY     #0
:       DEY
        BNE     :-
        DEX
        BNE     :--
        RTS

src_tbl:
.repeat 300, I
        .byte   (I * 7 + 3) & $FF
.endrepeat

.include "tms9918m1.asm"
.include "tms9918_pad.asm"
.include "sprites_outfit.asm"
.include "bbfont_tms.inc"
.include "ezcolor.asm"
'''

PROGRAM_B = '''
TMS9918_M2_ZP = 1
''' + HEAD + '''
.zeropage
mptr_lo:   .res 1
mptr_hi:   .res 1
plot_mode: .res 1
.code
t_m2:
        JSR     ez_detect
        JSR     init_vdp_g2
        LDA     #0
        STA     plot_mode
        LDA     #10
        STA     ln_x0
        LDA     #10
        STA     ln_y0
        LDA     #240
        STA     ln_x1
        LDA     #150
        STA     ln_y1
        JSR     line_xy
        LDA     #10
        STA     ln_x0
        LDA     #150
        STA     ln_y0
        LDA     #240
        STA     ln_x1
        LDA     #10
        STA     ln_y1
        JSR     line_xy
        LDA     #9                      ; light red text
        STA     pen_color
        LDX     #0
:       TXA
        ASL
        ASL
        ASL
        CLC
        ADC     #88
        STA     pix_x
        LDA     #168
        STA     pix_y
        LDA     txt,X
        BEQ     :+
        STX     r_buf
        JSR     text_blit_glyph
        LDX     r_buf
        INX
        BNE     :-
:       RTS
txt:    .byte   "MODE 2", 0

.include "text_bitmap.asm"
.include "tms9918m2.asm"
.include "ezcolor.asm"
'''

PROGRAM_D = '''
TMS9918_CONSOLE_ZP = 1
''' + HEAD + '''
t_text:
        JSR     ez_detect
        JSR     init_vdp_text
        JSR     upload_charmap
        JSR     clear_screen_text
        JSR     console_init
        LDA     #<hello
        LDX     #>hello
        JSR     console_print_ax
        LDY     #26                     ; 26 more lines: scrolls 3 times
:       TYA
        PHA
        LDA     #<line
        LDX     #>line
        JSR     console_print_ax
        PLA
        TAY
        DEY
        BNE     :-
        RTS
hello:  .byte   "HELLO FROM THE E-Z COLOR", $0D, "TEXT MODE 40X24", $0D, 0
line:   .byte   "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789", $0D, 0

.include "tms9918_console.asm"
.include "tms9918_text.asm"
.include "ezcolor.asm"
'''

PROGRAM_C = '''
EZ_DETECT_SKIP3 = 0
EZ_DETECT_BOOT_SLOT = r_boot
''' + HEAD + '''
t_detect:
        JSR     ez_detect
        STA     r_slot
        RTS
.include "ezcolor.asm"
'''

checks = 0


def ok(cond, what):
    global checks
    checks += 1
    if not cond:
        raise AssertionError(what)


def build(work, name, src):
    names = sorted(set(re.findall(r'^([tr]_\w+):', src, re.M)))
    src += ''.join(f'.export {n}\n' for n in names)
    (work / f'{name}.s').write_text(src)
    inc = ['-I', str(LIB / 'apple2'), '-I', str(LIB / 'tms9918'), '-I', str(LIB / 'math')]
    r = subprocess.run(['ca65', *inc, '-o', str(work / f'{name}.o'), str(work / f'{name}.s')],
                       capture_output=True, text=True)
    if r.returncode or 'Warning' in r.stderr:
        raise AssertionError(f'{name}: ca65\n{r.stderr}')
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(work / f'{name}.lbl'),
                    '-o', str(work / f'{name}.bin'), str(work / f'{name}.o')], check=True)
    return a2test.labels(work / f'{name}.lbl'), work / f'{name}.bin'


def run(binary, steps, slot):
    return a2test.run(None, [f'load:{binary}@6000'] + steps, ezcolor=slot)


def call(L, name, frames=200):
    return f'call:{L[name]:04X}:{frames}'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ezcolor-') as tmp:
        work = Path(tmp)
        LA, A = build(work, 'a', PROGRAM_A)
        LB, B = build(work, 'b', PROGRAM_B)
        LC, C = build(work, 'c', PROGRAM_C)
        LD, D = build(work, 'd', PROGRAM_D)

        # detection: the card's slot, VRAM around the probe kept
        for slot in (1, 2, 4, 5, 6, 7, None):
            r = run(A, [call(LA, 't_detect'), call(LA, 't_mark'), call(LA, 't_detect'),
                        LA.peek('r_slot', 3)]
                    + (['vpeek:3FFC:4', 'vregs'] if slot else []), slot)
            got, p, sx = r.dumps[0][:3]
            ok(got == (slot or 0), f'slot {slot}: ez_detect returned {got}')
            ok(bool(p & 2) == (slot is None), f'slot {slot}: Z flag {p:02X}')
            ok(sx == (slot or 0) * 16, f'slot {slot}: ez_slotx {sx:02X}')
            if slot:
                ok(r.vmem(0x3FFC, 4) == bytes([0x11, 0x22, 0x33, 0x44]),
                   f'slot {slot}: probe changed VRAM {r.vmem(0x3FFC, 4).hex()}')
                ok(r.vdp_fast == 0, f'slot {slot}: {r.vdp_fast} fast accesses')
        print('ok   ez_detect: slots 1 2 4 5 6 7, none; VRAM kept; fast accesses 0')

        # slot 3: skipped by default, found last with EZ_DETECT_SKIP3 = 0;
        # the boot slot is never probed
        r = run(A, [call(LA, 't_detect'), LA.peek('r_slot')], 3)
        ok(r.dumps[0][0] == 0, 'slot 3 skipped by default')
        r = run(C, [LC.poke('r_boot', 0x60), call(LC, 't_detect'), LC.peek('r_slot')], 3)
        ok(r.dumps[0][0] == 3, 'EZ_DETECT_SKIP3 = 0 finds slot 3')
        for boot, slot, want in ((0x60, 6, 0), (0x50, 6, 6), (0x50, 5, 0), (0x0A, 5, 5)):
            r = run(C, [LC.poke('r_boot', boot), call(LC, 't_detect'), LC.peek('r_slot')], slot)
            ok(r.dumps[0][0] == want, f'boot byte {boot:02X}, card in {slot}: got {r.dumps[0][0]}')
        print('ok   slot 3 (default skip, SKIP3=0), EZ_DETECT_BOOT_SLOT ($B7E9 / DEVNUM forms)')

        # helpers
        r = run(A, [call(LA, 't_detect'), call(LA, 't_helpers', 400), LA.peek('r_buf', 16 + 300), 'vpeek:1234:16', 'vpeek:2000:302', 'vpeek:2200:300',
                    'vpeek:3000:514', 'vpeek:3400:300', 'vregs'], 4)
        pat = bytes(i ^ 0xA5 for i in range(16))
        src = bytes((i * 7 + 3) & 0xFF for i in range(300))
        ok(r.vmem(0x1234, 16) == pat, 'ez_data_w')
        ok(r.mem(LA['r_buf'], 16) == pat, 'ez_data_r')
        ok(r.vmem(0x2000, 302) == b'\x5A' * 300 + b'\0\0', 'ez_fill 300')
        ok(r.vmem(0x2200, 300) == src, 'ez_copy 300')
        ok(r.mem(LA['r_copy'], 300) == src, 'ez_read 300')
        ok(r.vmem(0x3000, 514) == b'\x77' * 513 + b'\0', 'ez_fill_blank 513')
        ok(r.vmem(0x3400, 300) == src, 'ez_copy_blank 300')
        ok(r.vregs[7] == 0xF4, f'ez_set_reg R7 {r.vregs}')
        ok(r.vdp_fast == 0, f'helpers: {r.vdp_fast} fast accesses')
        cyc = [int(x) for x in re.findall(r'elapsed=(\d+)', r.out)]
        print(f'ok   helpers: data w/r, set_reg, fill, copy, read, blank variants '
              f'({cyc[1]} cycles)')

        # frame flag: three waits = between 2 and 3 frames
        r = run(A, [call(LA, 't_detect'), call(LA, 't_vbl', 10)], 4)
        el = int(re.findall(r'elapsed=(\d+)', r.out)[1])
        ok(2 * 17030 <= el <= 3 * 17030 + 200, f'3 VBL waits took {el} cycles')
        print(f'ok   EZ_WAIT_VBLANK(_SAFE) / WAIT_VBLANK: 3 frame flags in {el} cycles')

        # Graphics I, the TMS_Rogue way
        r = run(A, [call(LA, 't_detect'), call(LA, 't_m1', 400)] + a2test.VDP_SHOT_STEPS, 4)
        ok(r.vdp_fast == 0, f'mode 1: {r.vdp_fast} fast accesses')
        ok(r.vregs == [0x00, 0xC3, 0x06, 0x80, 0x00, 0x36, 0x07, 0x01], f'mode 1 regs {r.vregs}')
        msg = b'HELLO E-Z COLOR'
        ok(r.vmem(0x1800 + 2 * 32 + 4, len(msg)) == msg, 'name table text')
        ok(r.vmem(0x1800 + 10 * 32 + 8, 1) == b'*', 'print_at_rc')
        ok(r.vmem(0x1B00, 5) == bytes([79, 120, 0, 8, 0xD0]), 'SAT')
        ok(r.vmem(0x1B05, 3) == b'\xD1\xD1\xD1', 'disable_sprites tail')
        ok(r.vmem(0x0100 + 8 * (ord('H') - 32), 8) == r.vmem(0x0100 + 8 * (ord('H') - 32), 8)
           and any(r.vmem(0x0100 + 8 * (ord('H') - 32), 8)), 'font uploaded')
        rows = a2test.vdp_shot(r, OUT / 'ezcolor_mode1.png')
        ok(rows[0][0] == tms9918.PALETTE[11], f'backdrop chars 0-7 {rows[0][0]}')
        red = sum(px == tms9918.PALETTE[8] for row in rows[80:112] for px in row[120:152])
        ok(red > 40, f'sprite pixels {red}')
        print(f'ok   Graphics I (init_vdp_g1 + font + text + 16x16 sprite): {OUT / "ezcolor_mode1.png"}')

        # Graphics II
        r = run(B, [call(LB, 't_m2', 1500)] + a2test.VDP_SHOT_STEPS, 5)
        ok(r.vdp_fast == 0, f'mode 2: {r.vdp_fast} fast accesses')
        ok(r.vregs == [0x02, 0xC0, 0x0E, 0xFF, 0x03, 0x76, 0x03, 0xF1], f'mode 2 regs {r.vregs}')
        ok(r.vmem(0x3800, 768) == bytes(range(256)) * 3, 'linear name table')
        rows = a2test.vdp_shot(r, OUT / 'ezcolor_mode2.png')
        white = tms9918.PALETTE[15]
        ok(rows[10][10] == white and rows[150][240] == white and rows[10][240] == white,
           'line_xy end points')
        lit = sum(px == tms9918.PALETTE[9] for row in rows[168:176] for px in row[88:136])
        ok(lit > 30, f'text_blit_glyph pixels {lit}')
        print(f'ok   Graphics II (init_vdp_g2 + line_xy + text_blit_glyph): {OUT / "ezcolor_mode2.png"}')

        # Text mode + console (scrolling)
        r = run(D, [call(LD, 't_text', 3000)] + a2test.VDP_SHOT_STEPS, 2)
        ok(r.vdp_fast == 0, f'text: {r.vdp_fast} fast accesses')
        ok(r.vregs[:2] == [0x00, 0xD0], f'text regs {r.vregs}')
        line = b'ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789'
        names = r.vmem(0x0800, 960)
        ok(all(names[40 * k:40 * k + len(line)] == line for k in range(23)), 'scrolled lines')
        ok(names[40 * 23:40 * 24] == b' ' * 40, 'last line blank')
        rows = a2test.vdp_shot(r, OUT / 'ezcolor_text.png')
        ok(rows[0][0] == tms9918.PALETTE[1] and any(px == tms9918.PALETTE[15] for px in rows[1]),
           'text colours')
        print(f'ok   Text mode + console (26 lines, scrolling): {OUT / "ezcolor_text.png"}')

        # the silicon-strict counter sees an unpadded loop
        r = run(A, [call(LA, 't_detect'), call(LA, 't_fast')], 4)
        ok(r.vdp_fast > 100, f'unpadded loop: {r.vdp_fast} fast accesses')
        print(f'ok   unpadded STA loop, display on: vdp_fast_writes={r.vdp_fast}')

        # indexed store: the NMOS dummy read advances the VRAM address first
        r = run(A, [call(LA, 't_detect'), call(LA, 't_indexed'), 'vpeek:0100:2'], 4)
        ok(r.vmem(0x100, 2) == b'\x00\xAB', f'STA EZ_DATA,X landed {r.vmem(0x100, 2).hex()}')
        print('ok   STA EZ_DATA,X: dummy read modelled (byte lands one further)')

        # frame IRQ
        r = run(A, [call(LA, 't_detect'), call(LA, 't_irq', 20), LA.peek('r_irq')], 4)
        n = r.dumps[0][0]
        ok(4 <= n <= 6, f'IRQ count {n}')
        r = run(A, [call(LA, 't_detect'), call(LA, 't_noirq', 20), LA.peek('r_irq')], 4)
        ok(r.dumps[0][0] == 0, 'no IRQ with R1 IE off')
        print(f'ok   frame IRQ: {n} in ~5 frames with R1 IE, 0 without')

        pom2(work, A, LA)

    print(f'test_ezcolor: {checks} checks passed')


def pom2(work, A, LA):
    """The library on POM2's card: a2shot, a DOS disk that BRUNs program A
    (its first routine, t_detect, is harmless), then call: steps."""
    if not a2test.have_a2shot('ezcolor on POM2'):
        return
    disk = a2test.build_disk(work, 'EZA', A)
    boot = ['wait:900']

    def shot(steps, slot):
        return a2test.run(disk, boot + steps, emulator=a2test.A2SHOT, ezcolor=slot)

    for slot in (4, 7, None):
        r = shot([call(LA, 't_detect'), LA.peek('r_slot', 3)] + (['vregs'] if slot else []), slot)
        got, p, sx = r.dumps[0][:3]
        ok(got == (slot or 0) and sx == (slot or 0) * 16 and bool(p & 2) == (slot is None),
           f'POM2, slot {slot}: ez_detect returned {got} P={p:02X} slotx={sx:02X}')
        ok(r.vdp_dropped == (0 if slot else None), f'POM2, slot {slot}: dropped {r.vdp_dropped}')
    print('ok   POM2 card: ez_detect in slots 4 and 7, none; nothing dropped')

    r = shot([call(LA, 't_detect'), call(LA, 't_r16k'), call(LA, 't_helpers', 400),
              LA.peek('r_buf', 16 + 300), 'vpeek:1234:16', 'vpeek:2000:302', 'vpeek:2200:300',
              'vpeek:3000:514', 'vpeek:3400:300', 'vregs'], 4)
    pat = bytes(i ^ 0xA5 for i in range(16))
    src = bytes((i * 7 + 3) & 0xFF for i in range(300))
    ok(r.vmem(0x1234, 16) == pat and r.mem(LA['r_buf'], 16) == pat, 'POM2: ez_data_w / ez_data_r')
    # (POM2's VRAM powers up as an FF/00 pattern, not zeros: only the
    # written bytes are compared)
    ok(r.vmem(0x2000, 300) == b'\x5A' * 300 and r.vmem(0x2200, 300) == src
       and r.mem(LA['r_copy'], 300) == src, 'POM2: ez_fill / ez_copy / ez_read')
    ok(r.vmem(0x3000, 513) == b'\x77' * 513 and r.vmem(0x3400, 300) == src,
       'POM2: ez_fill_blank / ez_copy_blank')
    ok(r.vregs[1] == 0x80 and r.vregs[7] == 0xF4, f'POM2: registers {r.vregs}')
    ok(r.vdp_dropped == 0, f'POM2 helpers: {r.vdp_dropped} dropped')
    print('ok   POM2 card: helpers round trip (16 KB), 0 dropped')

    steps = [call(LA, 't_detect'), call(LA, 't_m1', 400)] + a2test.VDP_SHOT_STEPS
    # two whole frames before the picture: the VDP paints line by line
    r = shot(steps + ['wait:2', f'vshot:{OUT / "ezcolor_mode1_pom2.png"}'], 4)
    m = run(A, steps, 4)
    ok(r.vdp_dropped == 0, f'POM2 mode 1: {r.vdp_dropped} dropped')
    ok(r.vregs == m.vregs and r.vram == m.vram,
       f'POM2 mode 1: VRAM and registers = a2run ({sum(x != y for x, y in zip(r.vram, m.vram))} bytes differ)')
    print(f'ok   POM2 card: Graphics I screen = a2run byte for byte: {OUT / "ezcolor_mode1_pom2.png"}')

    r = shot([call(LA, 't_detect'), call(LA, 't_fast'), 'vregs', 'vdrop:reset', call(LA, 't_burst'), 'vregs'], 4)
    nine = int(re.findall(r'^vregs .* dropped=(\d+)', r.out, re.M)[0])
    ok(r.vdp_dropped > 20, f'POM2: 4-cycle burst dropped {r.vdp_dropped}')
    print(f'ok   POM2 card: 9-cycle STA loop dropped {nine}, 4-cycle burst {r.vdp_dropped} (window counted)')

    # Reported, not checked: POM2 ba7f04da does not send the NMOS dummy read
    # of STA abs,X to the card (the byte lands at $0100; a2run and the 6502
    # put it at $0101). The library never writes indexed.
    r = shot([call(LA, 't_detect'), call(LA, 't_r16k'), call(LA, 't_indexed'), 'vpeek:0100:2'], 4)
    print(f'info POM2 card: STA EZ_DATA,X wrote {r.vmem(0x100, 2).hex()} at $0100 '
          f'({"dummy read seen" if r.vmem(0x100, 2) == bytes([0, 0xAB]) else "no dummy read"})')


if __name__ == '__main__':
    main()
