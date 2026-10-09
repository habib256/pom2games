#!/usr/bin/env python3
"""Coherent cc65 stack depths must ignore transient split-byte pointer updates."""
from pathlib import Path
import argparse
import tempfile
from test_hgr import build
import a2test


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--iie',action='store_true')
    args=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='cc65-stack-') as directory:
        work=Path(directory)
        source=work/'profile.c'
        source.write_text('void profile(void); int main(void) {profile(); return 0;}')
        probe=work/'probe.s'
        probe.write_text('''.export _profile, profile_begin, profile_one, profile_end
.importzp sp
.code
_profile:
profile_begin:
    lda #$ff
    sta sp
    lda #$95
    sta sp+1
    jsr touch
    lda #0
    sta sp
    lda #$96
    sta sp+1
profile_one:
    lda #$db
    sta sp
    lda #$95
    sta sp+1
    jsr touch
    lda #0
    sta sp
    lda #$96
    sta sp+1
profile_end:
    rts
touch: rts
''')
        disk=build(work,source,extra_sources=[probe]);labels=a2test.labels(work/'test.lbl')
        watch=f'stackwatch:{labels["sp"]:02X}:9600:0800'
        result=a2test.run(disk,[labels.until('profile_begin'),watch,
            labels.until('profile_one'),'stack',watch,labels.until('profile_end'),'stack'],iie=args.iie)
        import re
        peaks=[tuple(map(int,m)) for m in re.findall(r'stack peak=(\d+) reserved=(\d+) overflow=(\d+)',result.out)]
        assert peaks==[(1,2048,0),(37,2048,0)],peaks
    with tempfile.TemporaryDirectory(prefix='hardware-stack-') as directory:
        work=Path(directory);source=work/'hardware.c'
        source.write_text('void hardware(void); int main(void) {hardware(); return 0;}')
        asm=work/'hardware.s'
        asm.write_text(''' .export _hardware, hardware_begin, hardware_end
.code
_hardware:
hardware_begin:
    tsx
    stx $1002
    ldx $1003
    lda #$a5
pushloop:
    pha
    dex
    bne pushloop
hardware_end:
    jmp hardware_end
''')
        disk=build(work,source,extra_sources=[asm]);labels=a2test.labels(work/'test.lbl')
        for count in (37,255):
            result=a2test.run(disk,[labels.until('hardware_begin'),f'poke:1003:{count:02X}',
                'hwstackwatch',labels.until('hardware_end'),'hwstack','peek:1002:1'],iie=args.iie)
            peak,available,overflow=map(int,re.search(r'hwstack peak=(\d+) available=(\d+) overflow=(\d+)',result.out).groups())
            if count==37:
                assert peak==255-result.dumps[0][0]+37 and available==255 and not overflow,(peak,available,overflow)
            else: assert overflow,'hardware stack wrap negative control missed'
    print('C stack profiler: exact 1/37-byte allocations, split-byte restoration and reservation, hardware pushes and wrap detection OK.')


if __name__=='__main__':main()
