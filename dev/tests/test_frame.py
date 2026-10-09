#!/usr/bin/env python3
"""Measure real cadence calls: II+ delay, ROM-ID fallback, IIe VBL and timeout.

Portable cases run in a2run. --iie adds the SDK-backed POM2 IIe test.
IIc/IIgs ID cases simulate detection only, not full IIc/IIgs hardware.
"""
import argparse
from pathlib import Path
import re
import shutil
import tempfile
from test_hgr import DEV, run, a2test


def build(work):
    objects = []
    for source in (DEV/'cc65/crt0_apple2.s', DEV/'tests/frame_fixture.s',
                   DEV/'lib/apple2c/apple2frame.s'):
        obj = work/(source.stem+'.o')
        run(['ca65','-t','none','-o',obj,source])
        objects.append(obj)
    labels, binary = work/'frame.lbl', work/'frame.bin'
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
         '-Ln',labels,'-o',binary,*objects])
    points = a2test.labels(labels, prefix='_frame_')
    return a2test.build_disk(work, 'FRAME', binary), points


def check(emulator, disk, points, options, mode, timeout=False):
    steps = []
    for _ in range(4):
        steps += [f'until:{points["_frame_begin"]:04X}:1500',
                  f'until:{points["_frame_end"]:04X}:100', 'peek:1000:3']
    output = run([emulator,*options,'--disk',disk,*steps])
    ticks = [int(n) for n in re.findall(r'cycles=(\d+)',output)]
    results = [bytes.fromhex(s) for s in re.findall(r'(?m)^1000: ([0-9A-F ]+)$',output)]
    assert len(ticks) == 8 and len(results) == 4, output
    waits = [ticks[i+1]-ticks[i] for i in (0,2,4,6)]
    actual_mode = 0 if timeout else mode
    assert results == [bytes((mode,actual_mode,4))]*3 + [bytes((mode,actual_mode,0))], (results, 'mode or IRQ mask')
    if actual_mode == 0:
        if timeout: assert 60000 < waits[0] < 100000, waits
        else: assert 17000 < waits[0] < 17400, waits
        assert 390 < waits[1] < 700, waits
        assert all(30 < n < 250 for n in waits[2:]), waits
    else:
        assert all(0 < n < 2*17030 for n in waits), waits
        # End of each call must land at the fresh blanking edge, not merely
        # somewhere within an old interval. Consecutive calls span one frame.
        assert all(abs((ticks[i]-ticks[i-2])-17030) < 100 for i in (3,5,7)), ticks
    return waits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args = parser.parse_args()
    run(['make','-s','-C',DEV/'tools/a2run'])
    with tempfile.TemporaryDirectory(prefix='pom2-frame-') as temp:
        work = Path(temp); disk, points = build(work)
        emulator = DEV/'tools/a2run/a2run'
        print('II+ delay cycles:',check(emulator,disk,points,[],0))
        for name, id_byte, gs, mode in (('IIc-ID',0,False,0), ('IIgs-ID',0xE0,True,0),
                                        ('IIe-stalled-VBL',0xE0,False,1)):
            roms = work/name; roms.mkdir()
            for source in (DEV/'tools/a2shot/roms').glob('*.rom'):
                shutil.copyfile(source,roms/source.name)
            rom = bytearray((roms/'apple2p.rom').read_bytes())
            base = 65536 - len(rom)
            rom[0xFBB3-base] = 6; rom[0xFBC0-base] = id_byte
            if gs: rom[0xFE1F-base:0xFE21-base] = bytes((0x18,0x60)) # CLC; RTS
            (roms/'apple2p.rom').write_bytes(rom)
            print(name,'cycles:',check(emulator,disk,points,['--roms',roms],mode,mode==1))
        if args.iie:
            print('IIe VBL cycles:',check(DEV/'tools/a2shot/a2shot',disk,points,['--iie'],1))
    print('Cadence: mode, delay adjustment, zero normalization, IRQ mask and bounded fallback passed.')


if __name__ == '__main__':
    main()
