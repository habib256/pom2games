#!/usr/bin/env python3
"""Build the optional C game object and exercise its actual cc65 calling ABI."""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / 'dev'
sys.path.insert(0,str(DEV/'tools'))
import a2test


def check(work):
    source = work / 'game_api.c'
    source.write_text('''#include "apple2game.h"
#include "apple2io.h"
#define BYTE(a) (*(volatile unsigned char *)(a))
static const unsigned char flips[] = {3u,7u,2u,0u};
static const unsigned char periods[] = {2u,40u,0u,1u};
int main(void) {
    unsigned char scene;
    BYTE(0x1000)=0u;
    for (scene=0; scene<7u; ++scene) {
        apple2_getkey();
        BYTE(0x1001)=a2_read_stick();
        BYTE(0x1002)=a2_joy_x; BYTE(0x1003)=a2_joy_y;
        BYTE(0x1004)=a2_button(0u); BYTE(0x1005)=a2_button(1u);
        *(volatile unsigned *)0x1006=a2_button(2u);
        BYTE(0x1000)=scene+1u;
    }
    for (scene=0; scene<4u; ++scene) {
        apple2_getkey();
        a2_tone(flips[scene],periods[scene]);
        BYTE(0x1000)=8u+scene;
    }
    for (;;) {}
    return 0;
}
''')
    objects = []
    for src in (DEV/'cc65/crt0_apple2.s', source, DEV/'lib/apple2c/apple2io_asm.s',
                DEV/'lib/apple2c/apple2game_asm.s'):
        obj = work/(src.stem+'.o')
        subprocess.run(['cl65','-t','none','-Oirs','-I',str(DEV/'lib/apple2c'),
                        '--asm-include-dir',str(DEV/'lib/apple2'),'-c','-o',str(obj),str(src)],check=True)
        objects.append(obj)
    binary = work/'game.bin'
    subprocess.run(['cl65','-t','none','-C',str(DEV/'cc65/apple2_hgr_c.cfg'),
                    '-o',str(binary),*map(str,objects)],check=True)
    disk = a2test.build_disk(work,'GAMEAPI',binary)
    cases = [(0,0,0),(-1,0,3),(1,0,4),(0,-1,1),(0,1,2),(-1,-1,1),(1,1,2)]
    tones = [(3,2),(7,40),(2,0),(256,1)]
    steps = ['wait:1100','peek:1000:1']
    for index,(x,y,direction) in enumerate(cases):
        steps += [f'joy:{x},{y}', *[f'btn:{b},{int(index%3==b)}' for b in range(3)],
                  'key: ','wait:2','peek:1000:8']
    for index,_ in enumerate(tones):
        steps += [f'spklog:{work / (str(index)+".spk")}', 'key: ','wait:5','peek:1000:1']
    result = a2test.run(disk,steps)
    assert result.dumps[0] == b'\0'
    for index,(x,y,direction) in enumerate(cases):
        values = result.dumps[index+1]
        assert values[0:2] == bytes([index+1,direction]), ('direction',x,y,values)
        for position,count in zip((x,y),values[2:4]):
            assert count < 30 if position<0 else count>90 if position>0 else 30<=count<=90, ('axis',position,count)
        assert values[4:8] == bytes([128 if index%3==b else 0 for b in range(3)]+[0]), ('buttons/return promotion',values)
    for index,(flips,period) in enumerate(tones):
        assert result.dumps[8+index] == bytes([8+index]), 'tone did not finish'
        cycles = [int(line) for line in (work/(str(index)+'.spk')).read_text().splitlines()]
        assert len(cycles) == flips, ('tone flip count',index,len(cycles))
        intervals = [b-a for a,b in zip(cycles,cycles[1:])]
        # LDA speaker / LDX absolute period / DEX-BNE / DEY-BNE.
        # Taken branches may each cross a page (one extra cycle).
        count = period or 256
        expected = 12+5*count
        assert len(set(intervals)) == 1 and intervals[0] in {expected,expected+1,expected+count-1,expected+count}, ('tone half-period',index,intervals)
    print('C game API: builds, seven joystick positions, three buttons, diagonal priority and speaker ABI/zero counts OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='apple2game-') as tmp:
        check(Path(tmp))
