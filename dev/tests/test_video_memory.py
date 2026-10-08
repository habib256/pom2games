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


def bitmap(work):
    cfg = work / 'bus.cfg'
    cfg.write_text('''MEMORY { ZP: start=$50,size=$B0,type=rw;
 RAM: start=$6000,size=$2000,type=rw,file=%O; }
SEGMENTS { ZEROPAGE: load=ZP,type=zp; CODE: load=RAM,type=ro; }
''')
    objects = []
    for source in (DEV / 'tests/hgr_bitmap_bus.s', DEV / 'lib/hgrc/hgr_bitmap_asm.s'):
        obj = work / (source.stem + '.o')
        subprocess.run(['ca65', '-I', str(DEV / 'lib/hgrc'), '-o', str(obj), str(source)], check=True)
        objects.append(obj)
    binary = work / 'bus.bin'
    subprocess.run(['ld65', '-C', str(cfg), '-o', str(binary), *map(str, objects)], check=True)
    probe = work / 'probe'
    subprocess.run([*shlex.split(os.environ.get('CC', 'cc')), '-O1', '-g',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-I', str(DEV / 'tools/a2run'), str(DEV / 'tests/hgr_bitmap_bus.c'),
                    str(DEV / 'tools/a2run/cpu6502.c'), '-o', str(probe)], check=True)
    subprocess.run([str(probe), str(binary)], check=True)


def lores(work):
    source = work / 'lores.c'
    source.write_text('''#include "hgr.h"
int main(void) {
    unsigned i;
    for (i=0x0400u; i<0x0C00u; ++i) *(unsigned char *)i=0xA5u;
    hgr_lores_clear(3u);
    hgr_set_draw_page(2u); hgr_lores_clear(0x1Au);
    *(volatile unsigned char *)0x1000=1u;
    for (;;) {}
    return 0;
}
''')
    disk = test_hgr.build(work, source)
    result = test_hgr.a2test.run(disk, ['wait:1100', 'peek:1000:1', 'peek:0400:2048'])
    assert result.dumps[0] == b'\x01', 'fixture did not finish'
    expected = bytearray([0xA5]*2048)
    for page, color in ((0,0x33),(1024,0xAA)):
        for y in range(24):
            offset = (y%8)*128 + (y//8)*40
            expected[page+offset:page+offset+40] = bytes([color])*40
    assert result.dumps[1] == expected, 'LORES clear overwrote firmware screen holes or missed visible cells'
    print('LORES clear: both pages filled, 64 firmware bytes per page preserved.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='video-memory-') as tmp:
        work = Path(tmp)
        bitmap(work)
        lores(work)
