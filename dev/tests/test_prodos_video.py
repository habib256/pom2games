#!/usr/bin/env python3
"""Real cc65 /RAM discovery must stay inside ProDOS's 14-entry DEVLST."""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
DEV=ROOT/'dev'
sys.path.insert(0,str(DEV/'tools'))
import a2test

CASES = [(0,0),(13,13),(13,0),(0,13),(0,255),(255,255),
         (14,255),(14,0),(15,255),(16,255)]


def check(work):
    source=work/'prodos_video.c'
    source.write_text('''#include "prodos.h"
#include "apple2io.h"
#define BYTE(a) (*(volatile unsigned char *)(a))
static unsigned char calls, last_unit;
static const struct {unsigned char count, ram_index;} cases[]={''' + ','.join('{%du,%du}'%c for c in CASES) + '''};
unsigned char __fastcall__ prodos_format_ram(unsigned char unit) {
    ++calls; last_unit=unit; return 1u;
}
int main(void) {
    unsigned i;
    unsigned char scene, status;
    for (scene=0; scene<sizeof(cases)/sizeof(cases[0]); ++scene) {
        for (i=0xBF10u; i<0xBF50u; ++i) BYTE(i)=0x55u;
        for (i=0; i<14u; ++i) BYTE(0xBF32u+i)=0x60u;
        BYTE(0xBF31)=cases[scene].count;
        /* First bytes after DEVLST resemble a unit with a /RAM vector.
         * They must never be consulted as device-list entries. */
        BYTE(0xBF40)=0x4Fu; BYTE(0xBF41)=0x4Fu;
        BYTE(0xBF18)=0u; BYTE(0xBF19)=0xFFu;
        if (cases[scene].ram_index<14u) {
            BYTE(0xBF32u+cases[scene].ram_index)=0xBFu;
            BYTE(0xBF26)=0u; BYTE(0xBF27)=0xFFu;
        }
        calls=0u; last_unit=0u;
        status=prodos_video_claim(PD_VIDEO_PRESERVE_RAM);
        BYTE(0x1005)=status;
        /* Failed/invalid policy must neither format nor erase a claim. */
        BYTE(0x1006)=prodos_video_claim(255u);
        BYTE(0x1007)=prodos_video_claim(PD_VIDEO_DISCARD_RAM);
        BYTE(0x1008)=prodos_video_claim(PD_VIDEO_PRESERVE_RAM);
        BYTE(0x1009)=prodos_video_claim(PD_VIDEO_DISCARD_RAM);
        BYTE(0x1001)=prodos_video_release();
        BYTE(0x1002)=prodos_video_release();
        BYTE(0x1003)=calls; BYTE(0x1004)=last_unit;
        BYTE(0x1000)=scene;
        apple2_getkey();
    }
    for (;;) {}
    return 0;
}
''')
    objects=[]
    for index,src in enumerate((DEV/'cc65/crt0_apple2.s',source,DEV/'lib/prodos/video.s',DEV/'lib/apple2c/apple2io_asm.s')):
        obj=work/(str(index)+'.o')
        subprocess.run(['cl65','-t','none','-Oirs','-I',str(DEV/'lib/prodos'),'-I',str(DEV/'lib/apple2c'),
                        '-c','-o',str(obj),str(src)],check=True)
        objects.append(obj)
    binary=work/'video.bin'
    subprocess.run(['cl65','-t','none','-C',str(DEV/'cc65/apple2_hgr_c.cfg'),'-o',str(binary),*map(str,objects)],check=True)
    disk=a2test.build_disk(work,'PDVIDEO',binary)
    steps=['wait:1100']
    for _ in CASES:
        steps+=['peek:1000:10','key: ','wait:2']
    result=a2test.run(disk,steps)
    for scene,(count,index) in enumerate(CASES):
        found = index<=count and count<14
        invalid = count != 255 and count >= 14
        preserve = 3 if invalid else 1 if found else 0
        discard = 3 if invalid else 0
        expected=bytes([scene,1,1,int(found),0xB0 if found else 0,
                        preserve,2,discard,preserve,discard])
        assert result.dumps[scene]==expected, ('DEVCNT /RAM discovery',count,index,result.dumps[scene])
    print('ProDOS video: 14-entry device-list bounds, first/last /RAM, no /RAM, empty/invalid lists, preserve/discard policies, idempotent claim and one release only OK.')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='prodos-video-') as tmp:
        check(Path(tmp))
