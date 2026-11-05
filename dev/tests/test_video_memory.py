#!/usr/bin/env python3
"""Observe bitmap bus accesses and verify LORES preserves firmware mailboxes."""
from pathlib import Path
import os
import shlex
import subprocess
import tempfile
import test_hgr

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / 'dev'


def bitmap(work, aligned=False):
    cfg = work / 'bus.cfg'
    cfg.write_text('''MEMORY { ZP: start=$50,size=$B0,type=rw;
 RAM: start=$6000,size=$2000,type=rw,file=%O; }
SEGMENTS { ZEROPAGE: load=ZP,type=zp; CODE: load=RAM,type=ro; }
''')
    objects = []
    defines = ['-D', 'HGRC_BLIT7_BUS=1'] if aligned else []
    kernel = 'hgr_blit7_asm.s' if aligned else 'hgr_bitmap_asm.s'
    for source in (DEV / 'tests/hgr_bitmap_bus.s', DEV / 'lib/hgrc'/kernel):
        obj = work / (source.stem + '.o')
        subprocess.run(['ca65', *defines, '-I', str(DEV / 'lib/hgrc'), '-o', str(obj), str(source)], check=True)
        objects.append(obj)
    binary = work / 'bus.bin'
    subprocess.run(['ld65', '-C', str(cfg), '-o', str(binary), *map(str, objects)], check=True)
    probe = work / 'probe'
    subprocess.run([*shlex.split(os.environ.get('CC', 'cc')), *defines, '-O1', '-g',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-I', str(DEV / 'tools/a2run'), str(DEV / 'tests/hgr_bitmap_bus.c'),
                    str(DEV / 'tools/a2run/cpu6502.c'), '-o', str(probe)], check=True)
    subprocess.run([str(probe), str(binary)], check=True)


def lores(work):
    source = work / 'lores.c'
    source.write_text('''#include "hgr.h"
void checkpoint(void);
int main(void) {
    unsigned i, color;
    unsigned char page;
    for (i=0x0400u; i<0x0C00u; ++i)
        *(unsigned char *)i=(unsigned char)(i*13u+(i>>8));
    hgr_lores_clear(0x1Au); /* uninitialized BSS defaults to page 1 */
    checkpoint();
    for (page=1; page<=2; ++page) {
        hgr_set_draw_page(page);
        for (color=0; color<256; ++color) {
            hgr_lores_clear((unsigned char)color);
            checkpoint();
        }
    }
    for (;;) {}
    return 0;
}
''')
    marker = work / 'marker.s'
    marker.write_text('.export _checkpoint, resume\n.code\n_checkpoint: nop\nresume: rts\n')
    disk = test_hgr.build(work, source, extra_sources=(marker,))
    labels = test_hgr.a2test.labels(work / 'test.lbl')
    cases = [(0, 0x1A)] + [(page*1024, color) for page in range(2) for color in range(256)]
    steps = []
    for _ in cases:
        steps += [labels.until('_checkpoint'), 'peek:0400:2048', labels.until('resume')]
    tested = []
    for iie in (False, True):
        if iie and not test_hgr.a2test.have_a2shot('LORES clear on the IIe'):
            continue
        result = test_hgr.a2test.run(disk, steps, iie=iie)
        expected = bytearray((i*13+(i>>8)) & 255 for i in range(0x400, 0xC00))
        for (page, color), actual in zip(cases, result.dumps):
            for y in range(24):
                offset = page + test_hgr.a2test.text_offset(y)
                expected[offset:offset+40] = bytes([(color & 15)*17])*40
            assert actual == expected, ('LORES cells, firmware holes or other page', iie, page, color)
        assert len(result.dumps) == len(cases)
        tested.append('IIe' if iie else 'II+')
    print('LORES clear: all 256 color bytes on both pages, cold default, '
          f'64 firmware bytes per page and other page preserved ({"/".join(tested)}).')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='video-memory-') as tmp:
        work = Path(tmp)
        bitmap(work)
        bitmap(work, aligned=True)
        lores(work)
