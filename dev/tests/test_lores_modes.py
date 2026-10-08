#!/usr/bin/env python3
"""Native LORES after DHGR/80STORE on IIe, and safe initialization on II+."""
from pathlib import Path
import tempfile
import test_hgr


def check(work):
    source = work / 'lores_modes.c'
    source.write_text('''#include "hgr.h"
#include "dhgr.h"
#define BYTE(a) (*(volatile unsigned char *)(a))
int main(void) {
    unsigned char scene;
    for (scene=0; scene<2u; ++scene) {
        BYTE(0x1001)=dhgr_init();
        dhgr_show_page(2u);
        if (scene) BYTE(0xC001)=0u;
        hgr_lores_init();
        hgr_lores_clear(5u);
        BYTE(0x1000)=scene;
        apple2_getkey();
    }
    for (;;) {}
    return 0;
}
''')
    disk = test_hgr.build(work, source)
    for iie in (True,False):
        steps = ['wait:1100']
        for _ in range(2):
            steps += ['peek:1000:2', 'peek:C013:2', 'peek:C018:8',
                      'peek:0400:1024', 'key: ', 'wait:60']
        result = test_hgr.a2test.run(disk, steps, iie=iie)
        for scene in range(2):
            stage, banks, flags, screen = result.dumps[scene*4:scene*4+4]
            assert stage == bytes([scene, int(iie)]), ('DHGR capability/scene',iie,stage)
            if iie:
                assert not any(v&128 for v in banks), 'RAMRD/RAMWRT must be main'
                assert not any(flags[i]&128 for i in (0,2,3,4,5,7)), ('LORES video switches',scene,flags.hex())
            for row in range(24):
                offset = (row%8)*128+(row//8)*40
                assert screen[offset:offset+40] == bytes([0x55])*40, ('LORES visible row',iie,scene,row)
    print('LORES modes: native 40 columns after DHGR/80STORE, main RAM, full screen/page 1, II+ safe.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='lores-modes-') as tmp:
        check(Path(tmp))
