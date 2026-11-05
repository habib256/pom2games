#!/usr/bin/env python3
"""Standalone public save-under cursor oracle for strided row movement.

Valid widths 1..80 and heights through 127 exercise all byte/bank phases,
large row gaps, overlap, edge placements and hiding. Every screen store,
its IRQ mask and both complete page banks are checked independently.
"""
import argparse
import random
import tempfile
from pathlib import Path

from test_hgr import DEV, build, compile_source, a2test, run
from test_dhgr_spr import Model, OVBITS, SOURCES, STORE, MARKERS, VIA_IRQ


def cases():
    result = []
    for width in range(1, 81):
        height = 127//width
        result += [(0, 0, width, height),
                   (80-width, 192-height, width, height),
                   ((80-width)//2, (192-height)//2, width, height), (0, 0, 0, 0)]
    rng = random.Random(40177)
    for _ in range(80):
        width = rng.randrange(1, 81)
        height = rng.randrange(1, 127//width+1)
        result += [(rng.randrange(81-width), rng.randrange(193-height), width, height)
                   for _ in range(3)]
        result.append((0, 0, 0, 0))
    assert all(not w or (bx+w <= 80 and y+h <= 192 and w*h <= 127)
               for bx, y, w, h in result)
    return result


def build_fixture(work, source, calls):
    fixture = work/'cursor.c'
    fixture.write_text('''#include "dhgr.h"
void request(void); void begin(void); void end(void); void irq_on(void);
unsigned char page=1,irq_after,guard_ok;
static unsigned char under[256];
static const unsigned char bits[]={'''+','.join(map(str, OVBITS))+'''};
static const unsigned char calls[][4]={'''
        + ','.join('{'+','.join(map(str, call))+'}' for call in calls)+'''};
int main(void) {
    unsigned i;
    if(!dhgr_init()) return 1;
    request();
    dhgr_draw_page(1); dhgr_clear(5);
    dhgr_draw_page(2); dhgr_clear(10);
    dhgr_draw_page(page); dhgr_show_page(3-page);
    under[0]=0xa5; under[255]=0x5a;
    irq_on();
    for(i=0;i<sizeof(calls)/sizeof(calls[0]);++i) {
        if(i&1) { asm("sei"); } else { asm("cli"); }
        begin();
        dhgr_cursor(calls[i][0],calls[i][1],calls[i][2],calls[i][3],bits,under+1);
        asm("php"); asm("pla"); asm("sta _irq_after");
        guard_ok=under[0]==0xa5 && under[255]==0x5a;
        end(); asm("cli");
    }
    for(;;) {} return 0;
}
''')
    # Give the archive the candidate member under its normal stem, so the
    # test can also prove that the original kernel satisfies this oracle.
    member = work/'dhgr_spr_cursor.s'
    member.write_text(source.read_text())
    request = work/'request.s'
    request.write_text('.export _request\n.code\n_request: rts\n')
    for name, text in (('markers', MARKERS), ('via', VIA_IRQ)):
        marker = work/(name+'.s')
        marker.write_text(text)
        compile_source(marker, work/(name+'.o'), ['-t', 'none'])
    extras = [member, request, work/'markers.s']+[DEV/'lib/hgrc'/s for s in SOURCES
                                                 if s != 'dhgr_spr_cursor.s']
    build(work, fixture, extra_sources=extras)
    return fixture


def check(work, calls, machine, page, irq=False):
    binary, labels_path = work/'cursor.bin', work/'cursor.lbl'
    run(['cl65', '-t', 'none', '-C', DEV/'cc65/apple2_hgr_c.cfg',
         '-Ln', labels_path, '-o', binary, work/'crt0_apple2.o', work/'cursor.o',
         work/('via.o' if irq else 'markers.o'), work/'apple2io_asm.o', work/'hgrc.lib'])
    labels = a2test.labels(labels_path)
    disk = a2test.build_disk(work, 'CURSOR', binary)
    base, other = 0x2000*page, 0x2000*(3-page)
    steps = [labels.until('_request'), labels.poke('_page', page)]
    for _ in calls:
        steps += [labels.until('_begin'), 'storewatch:2000:5FFF', labels.until('_end'),
                  'unstorewatch', labels.peek('_irq_after', 2), 'peek:C013:2', 'peek:C018:8',
                  f'peek:{base:04X}:8192', 'poke:C003:0', f'peek:{base:04X}:8192', 'poke:C002:0']
    steps += ['peek:C013:2', f'peek:{other:04X}:8192', 'poke:C003:0', f'peek:{other:04X}:8192', 'poke:C002:0']
    if irq:
        steps += [labels.peek('irq_ticks', 4)]
    result = a2test.Result(run([DEV/'tools/a2shot/a2shot', machine,
                               *(['--mockingboard'] if irq else []), '--disk', disk, *steps]))
    assert len(result.dumps) == len(calls)*5+3+int(irq), len(result.dumps)
    model = Model()
    model.draw = page
    expected = []
    for index, (bx, y, width, height) in enumerate(calls):
        stores = {}
        model.cursor((bx, y, width, height) if width else None, stores)
        # Model.cursor enumerates the row/byte union in screen order.
        for (bank, address), value in stores.items():
            expected.append((bank, address, value, bool(index&1) or bank == 'aux'))
        status, banks, flags, main, aux = result.dumps[index*5:index*5+5]
        assert bool(status[0]&4) == bool(index&1), ('IRQ mask', machine, page, index)
        assert status[1] == 1, ('save-under guard', machine, page, index)
        assert not any(v&128 for v in banks) and not flags[0]&128, ('bank state', index)
        assert bool(flags[4]&128) == (page == 1), ('display page', index)
        assert main == model.pages[page][0] and aux == model.pages[page][1], \
            ('cursor pixels', machine, page, index, calls[index])
    final_banks, other_main, other_aux = result.dumps[len(calls)*5:len(calls)*5+3]
    assert not any(v&128 for v in final_banks), 'final bank state'
    assert other_main == model.pages[3-page][0] and other_aux == model.pages[3-page][1], \
        ('other page changed', machine, page)
    if irq:
        ticks = result.dumps[-1]
        assert int.from_bytes(ticks[:2], 'little') > 20, 'VIA IRQs not serviced'
        assert ticks[2] == 0 and ticks[3] != 0, ('IRQ bank check / negative control', ticks)
    observed, previous = [], None
    for line in result.out.splitlines():
        if line.startswith('until '):
            previous = None
        match = STORE.match(line)
        if not match:
            continue
        signature = match.group(1, 2, 3, 4, 5)
        if irq and signature == previous:
            continue  # one pending store sampled before/after IRQ dispatch
        previous = signature
        assert match[9] == '0' and match[10] == '0', ('ALTZP/RAMRD', line)
        bank = 'aux' if match[11] == '1' else 'main'
        observed.append((bank, int(match[2], 16), int(match[3], 16), bool(int(match[6], 16)&4)))
    assert observed == expected, ('ordered stores / IRQ windows', machine, page,
                                  len(observed), len(expected))
    return len(observed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEV/'lib/hgrc/dhgr_spr_cursor.s',
                        help='optional old or candidate assembly member')
    args = parser.parse_args()
    calls = cases()
    with tempfile.TemporaryDirectory(prefix='dhgr-cursor-rows-') as directory:
        work = Path(directory)
        build_fixture(work, args.source, calls)
        for machine in ('--iie', '--iic'):
            total = sum(check(work, calls, machine, page) for page in (1, 2))
            print(f'Cursor rows {machine[2:]}: {2*len(calls):,} public calls, both pages/banks, '
                  f'all widths/maximal heights, {total:,} exact ordered stores, guards and IRQ masks OK.')
        stores = check(work, calls, '--iie', 1, irq=True)
        print(f'Cursor rows VIA IRQ: {len(calls):,} calls and {stores:,} ordered stores; '
              'periodic interrupts, restored banks and negative control OK.')


if __name__ == '__main__':
    main()
