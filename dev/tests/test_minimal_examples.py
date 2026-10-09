#!/usr/bin/env python3
"""Boot, page presentation, visible strip and clean exit of standalone examples."""
import argparse
import json
from test_hgr import DEV, run, offset
import a2test

EXAMPLE = DEV/'examples/minimal'
BUILD = EXAMPLE/'build'


def hgr(name,double,iie=False):
    labels = a2test.labels(BUILD/(name+'.lbl'))
    steps = []
    for _ in range(3):
        steps += [labels.until('_minimal_present'), labels.peek('_frame',2),
                  labels.peek('_draw_page'), 'peek:C018:8', 'peek:2000:16384', 'wait:1']
    steps += ['press:\\e', 'wait:60', 'peek:C018:8' if iie else 'text']
    result = a2test.run(BUILD/(name+'.dsk'),steps,iie=iie)
    previous = -1
    for stage in range(3):
        value = result.mem(labels['_frame'],2,stage)
        page = result.mem(labels['_draw_page'],1,stage)
        flags = result.mem(0xc018,8,stage)
        video = result.mem(0x2000,16384,stage)
        frame = int.from_bytes(value,'little')
        assert frame > previous
        draw = page[0]
        assert draw == (2 if double and frame%2==0 else 1)
        if iie:
            assert bool(flags[4]&128) == (double and frame%2==1), 'display changed before present'
        image = video[(draw-1)*8192:draw*8192]
        expected = bytearray(8192)
        for y in range(80,87):
            for x in range(frame%273,frame%273+7):
                expected[offset(y)+x//7] |= 1 << (x%7)
        for y in range(80,88):
            start=offset(y)
            assert image[start:start+40] == expected[start:start+40],(name,frame,y)
        previous=frame
    if iie: assert result.mem(0xc018,8,3)[2]&128, 'text mode not restored'
    else: assert any(']' in screen for screen in result.text_screens()), 'DOS prompt not restored'


def prodos():
    labels=a2test.labels(BUILD/'dhgr-prodos.lbl')
    disk=BUILD/'dhgr-prodos.po'
    # Standard ProDOS boot has /RAM installed: safe policy must refuse it.
    result=a2test.run(disk,[labels.until('_apple2_getkey'),labels.peek('_claimed'),
        labels.peek('_frame',2),'peek:C018:8','press:\\e',labels.until('_prodos_quit')],iie=True)
    assert result.mem(labels['_claimed'],1)==b'\x00' and result.mem(labels['_frame'],2)==b'\x00\x00'
    assert result.mem(0xc018,8)[2]&128, 'refusal should remain in text mode'
    # Simulate a machine with no installed /RAM by removing only its DEVLST
    # entry. Disk units remain available. Guest sources still use PRESERVE.
    probe=a2test.run(disk,[labels.until('_main'),'peek:BF31:15'],iie=True)
    devices=probe.dumps[0]
    assert devices[:4]==bytes((2,0xe0,0x60,0xbf)), 'unexpected fixture ProDOS device list'
    steps=[labels.until('_main'),'poke:BF31:01']
    for _ in range(2):
        steps += [labels.until('_minimal_present'),labels.peek('_frame',2),
                  labels.peek('_claimed'),'peek:C013:2','peek:C018:8',
                  'peek:2000:16384','poke:C003:0','peek:2000:16384','poke:C002:0','wait:1']
    steps += ['press:\\e',labels.until('_prodos_quit'),labels.peek('_claimed'),'peek:C018:8']
    result=a2test.run(disk,steps,iie=True)
    from test_dhgr import color_pixel
    previous=-1
    for stage in range(2):
        value=result.mem(labels['_frame'],2,stage)
        claimed=result.mem(labels['_claimed'],1,stage)
        banks=result.mem(0xc013,2,stage)
        flags=result.mem(0xc018,8,stage)
        main=result.mem(0x2000,16384,stage*2)
        aux=result.mem(0x2000,16384,stage*2+1)
        frame=int.from_bytes(value,'little')
        assert frame>previous and claimed==b'\x01'
        assert not any(v&128 for v in banks) and not flags[0]&128
        draw=2 if frame%2==0 else 1
        assert bool(flags[4]&128)==(frame%2==1)
        expected=[bytearray(8192),bytearray(8192)]
        for y in range(80,87):
            for x in range(frame%133,frame%133+7): color_pixel(expected,x,y,9)
        for bank,video in enumerate((main,aux)):
            image=video[(draw-1)*8192:draw*8192]
            for y in range(80,88):
                start=offset(y)
                assert image[start:start+40]==expected[bank][start:start+40],(frame,bank,y)
        previous=frame
    assert result.mem(labels['_claimed'],1,2)==b'\x00' and result.mem(0xc018,8,2)[2]&128, 'shutdown did not restore text/release'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dhgr',action='store_true')
    args=ap.parse_args()
    run(['make','-s','-C',EXAMPLE])
    metrics=json.loads((BUILD/'memory.json').read_text())
    assert set(metrics)=={'hgr-single','hgr-double','dhgr-prodos'}
    if args.dhgr:
        hgr('hgr-single',False,iie=True)
        hgr('hgr-double',True,iie=True)
        prodos()
    else:
        hgr('hgr-single',False)
        hgr('hgr-double',True)
    print('Minimal examples: memory report, boot, frame pixels/pages and exit OK'+(' (ProDOS, /RAM refusal and no-/RAM path).' if args.dhgr else ' (HGR single/double).'))


if __name__=='__main__':
    main()
