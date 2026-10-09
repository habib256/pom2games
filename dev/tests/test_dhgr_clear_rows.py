#!/usr/bin/env python3
"""Compare bounded DHGR clears against both full banks/pages including holes."""
from pathlib import Path
import tempfile
from test_hgr import DEV, build, run
from test_dhgr import PATTERNS, offset
import a2test


def main():
    with tempfile.TemporaryDirectory(prefix='dhgr-rows-') as directory:
        work = Path(directory)
        fixture = work / 'rows.c'
        fixture.write_text('''#include "dhgr.h"
#include "apple2io.h"
unsigned char check_irq(void);
int main(void) {
    unsigned char page, color;
    if (!dhgr_init()) return 1;
    for (page=1; page<=2; ++page) for (color=0; color<16; ++color) {
        dhgr_draw_page(1); dhgr_clear(6);
        dhgr_draw_page(2); dhgr_clear(9);
        dhgr_draw_page(page); dhgr_show_page(3-page);
        dhgr_clear_rows(255,255,color); dhgr_clear_rows(0,0,color);
        dhgr_clear_rows(color*11,255,color);
        *(volatile unsigned char *)0x1000=page;
        *(volatile unsigned char *)0x1001=color;
        *(volatile unsigned char *)0x1002=check_irq();
        apple2_getkey();
    }
    return 0;
}
''')
        probe = work / 'row_irq.s'
        probe.write_text('''.export _check_irq, _row_begin, _row_end
.import _dhgr_clear_row_asm
.code
_check_irq:
    php
    cli
_row_begin:
    jsr _dhgr_clear_row_asm
_row_end:
    php
    pla
    and #4
    bne failed
    sei
    jsr _dhgr_clear_row_asm
    php
    pla
    and #4
    beq failed
    lda #1
    bne done
failed: lda #0
done: ldx #0
    plp
    rts
''')
        disk = build(work, fixture, extra_sources=[probe])
        labels = a2test.labels(work / 'test.lbl')
        steps = []
        for _ in range(32):
            steps += [labels.until('_row_begin'), labels.until('_row_end'), 'wait:1',
                      'peek:1000:3', 'peek:C013:2', 'peek:C018:8',
                      'peek:2000:16384', 'poke:C003:0', 'peek:2000:16384',
                      'poke:C002:0', 'key: ']
        result = a2test.run(disk, steps, iie=True)
        durations = [end-start for start,end in zip(result.cycles[::2], result.cycles[1::2])]
        assert all(0 < ticks < 1300 for ticks in durations), durations
        for index in range(32):
            page, color = index // 16, index % 16
            state, banks, flags, main, aux = result.dumps[index*5:index*5+5]
            assert state == bytes((page+1, color, 1)), 'IRQ mask changed'
            assert not any(v & 128 for v in banks) and not flags[0] & 128
            assert bool(flags[4] & 128) == (page == 0), 'display page changed'
            expected = []
            for bank in (0, 1):
                pages = []
                for target, initial in enumerate((6, 9)):
                    p = bytearray(PATTERNS[initial][1-bank::2]) * 4096
                    if target == page:
                        for y in range(color*11, 192):
                            start = offset(y)
                            p[start:start+40] = bytes(PATTERNS[color][1-bank::2]) * 20
                    pages.extend(p)
                expected.append(bytes(pages))
            assert main == expected[0] and aux == expected[1], (page, color)
    periodic_irq_test()
    print('DHGR row clear: colors, both pages/banks, holes/display, IRQ mask; max', max(durations), 'cycles.')



def periodic_irq_test():
    """Real VIA T1 IRQs during full visible-row clears, through the IIe ROM."""
    with tempfile.TemporaryDirectory(prefix='dhgr-irq-') as directory:
        work = Path(directory)
        fixture = work / 'irq.c'
        fixture.write_text('''#include "dhgr.h"
#include "apple2io.h"
void irq_start(void); void irq_stop(void); void irq_checkpoint(void);
unsigned char irq_fault_probe(void);
int main(void) {
    unsigned char page;
    if (!dhgr_init()) return 1;
    dhgr_draw_page(1); dhgr_clear(6);
    dhgr_draw_page(2); dhgr_clear(9);
    irq_start();
    if (!irq_fault_probe()) return 2;
    for (page=1; page<=2; ++page) {
        dhgr_draw_page(page); dhgr_show_page(3-page);
        dhgr_clear_rows(8,180,15);
        irq_checkpoint();
    }
    irq_stop();
    apple2_getkey();
    return 0;
}
''')
        probe = work / 'timer.s'
        probe.write_text('''.export _irq_start, _irq_stop, _irq_checkpoint, _irq_fault_probe
.export irq_ticks, irq_errors, irq_fault_pass
.bss
old_vector: .res 2
old_status: .res 1
irq_ticks: .res 2
irq_errors: .res 1
irq_fault_pass: .res 1
previous_tick: .res 1
.code
_irq_start:
    php
    pla
    sta old_status
    sei
    lda $03fe
    sta old_vector
    lda $03ff
    sta old_vector+1
    lda #<handler
    sta $03fe
    lda #>handler
    sta $03ff
    lda #$a5
    sta $1100
    lda #$5a
    sta $c005
    sta $1100
    sta $c004
    lda #$7f
    sta $c40e
    lda #$40
    sta $c40b
    lda #$fe
    sta $c404
    lda #$07
    sta $c405
    lda #$c0
    sta $c40e
    cli
    rts
_irq_checkpoint: rts
_irq_fault_probe:
    ; Negative control: force one IRQ while RAMWRT is auxiliary. The ROM
    ; dispatch normalizes banks, but our saved-frame check must detect it.
    php
    sei
    lda irq_ticks
    sta previous_tick
    sta $c005
    cli
fault_wait:
    lda irq_ticks
    cmp previous_tick
    beq fault_wait
    sta $c004
    sei
    lda irq_errors
    beq fault_failed
    lda #1
fault_failed:
    sta irq_fault_pass
    ldx #0
    stx irq_errors
    plp
    rts
_irq_stop:
    sei
    lda #$7f
    sta $c40e
    lda $c404
    lda old_vector
    sta $03fe
    lda old_vector+1
    sta $03ff
    lda old_status
    pha
    plp
    rts
handler:
    ; Enhanced IIe ROM saves registers/banks before dispatch to $03FE.
    ; The ROM frame holds RAMRD ($20) / RAMWRT ($10) at SP+5.
    pha
    txa
    pha
    tya
    pha
    tsx
    lda $0108,x
    and #$30
    beq banks_ok
    inc irq_errors
banks_ok:
    lda $c404
    lda $1100
    cmp #$a5
    beq guard_ok
    inc irq_errors
guard_ok:
    inc irq_ticks
    bne done
    inc irq_ticks+1
done:
    pla
    tay
    pla
    tax
    pla
    rti
''')
        disk = build(work, fixture, extra_sources=[probe])
        labels = a2test.labels(work / 'test.lbl')
        steps = []
        for _ in range(2):
            steps += [labels.until('_irq_checkpoint'), labels.peek('irq_ticks', 4),
                      'peek:1100:1', 'peek:C013:2', 'peek:C018:8',
                      'peek:2000:16384', 'poke:C003:0', 'peek:1100:1',
                      'peek:2000:16384', 'poke:C002:0', 'wait:1']
        result = a2test.Result(run([DEV/'tools/a2shot/a2shot', '--iie',
                                   '--mockingboard', '--disk', disk, *steps]))
        previous = 0
        for page in range(2):
            ticks, guard, banks, flags, main, aux_guard, aux = result.dumps[page*7:page*7+7]
            count = int.from_bytes(ticks[:2], 'little')
            assert count > previous + 10, ('IRQ not periodically serviced', count, previous)
            assert ticks[2] == 0, 'IRQ arrived with auxiliary read/write enabled'
            assert ticks[3] == 1, 'negative control did not detect auxiliary IRQ entry'
            assert guard == b'\xa5' and aux_guard == b'\x5a', 'main/aux guard damaged'
            assert not any(v & 128 for v in banks) and not flags[0] & 128
            assert bool(flags[4] & 128) == (page == 0), 'display page changed'
            for bank, actual in enumerate((main, aux)):
                expected = bytearray()
                for target, color in enumerate((6,9)):
                    image = bytearray(PATTERNS[color][1-bank::2]) * 4096
                    if target <= page:
                        for y in range(8,188):
                            start = offset(y)
                            image[start:start+40] = bytes(PATTERNS[15][1-bank::2]) * 20
                    expected.extend(image)
                assert actual == expected, ('IRQ corrupted framebuffer',page,bank)
            previous = count
    print('DHGR VIA IRQ: periodic interrupts serviced during both-page clears; banks, guards and pixels OK.')


if __name__ == '__main__':
    main()
