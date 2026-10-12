#!/usr/bin/env python3
"""Compass ribbon: independent pixels, magnetic alignment and UI lifecycle."""
import tempfile
from common import HERE, L, DISK, a2test, disk_with, state, text_screen
from fonts import glyph


def header(page):
    return b''.join(bytes(13) + page[a2test.hgr_offset(y)+13:a2test.hgr_offset(y)+27] + bytes(13) for y in range(16))


def expected(heading, offset):
    out = bytearray(16*40)
    left = ((heading-offset-98) % 560)//2
    def pixel(x, y):
        out[y*40+x//7] |= 1 << (x%7)
    for bearing, label in zip(range(0, 280, 35), ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')):
        for i, letter in enumerate(label):
            for y, bits in enumerate(glyph(letter)[:7]):
                for b in range(7):
                    if bits & (1<<b):
                        x = 91+(bearing-len(label)*7//2+i*7+b-left) % 280
                        if x < 189:
                            pixel(x, y+2)
    for tick in range(16):
        x = 91+(tick*35//2-left) % 280
        if x < 189:
            pixel(x, 9)
    for x, y in ((139,12), (140,12), (141,12), (140,13)):
        pixel(x,y)
    for x in range(91,189):
        pixel(x,0); pixel(x,15)
    for y in range(16):
        pixel(91,y); pixel(188,y)
    return bytes(out)


def all_headings():
    steps = [L.until('idle', 20000), L.peek('hud_offset',2)]
    # Redirect VIEW to the real HUD routine in this private emulator session.
    # This covers every azimuth without recomputing 560 terrain frames.
    code = bytes([0x4C, L['hud_draw'] & 255, L['hud_draw'] >> 8])
    for i, b in enumerate(code):
        steps += [L.poke('show_view_scene', b, i)]
    for heading in range(560):
        steps += [L.poke('heading', heading), L.poke('heading', heading>>8,1),
                  'key:V\\r', 'wait:1', L.until('idle',20000), 'peek:2000:8192']
    result = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    offset = int.from_bytes(result.dumps[0],'little')
    for heading,page in enumerate(result.dumps[1:]):
        assert header(page) == expected(heading,offset), f'azimuth {heading}: ribbon differs'
    assert len(result.dumps) == 561
    print('  560 azimuths: exact labels/ticks, fixed pointer, clipping, and full-circle seam OK')


def lifecycle():
    steps = [L.until('idle',20000), L.peek('px',6), L.peek('hud_offset',2), 'peek:2000:8192']
    turns = [('\\>',35), ('\\<',-35), ('LOOK R\\r',70), ('LOOK L\\r',-70), ('LOOK B\\r',280),
             ('LOOK N\\r',None), ('LOOK E\\r',None), ('LOOK S\\r',None), ('LOOK W\\r',None)]
    for key,_ in turns:
        steps += [f'key:{key}', 'wait:1', L.until('idle',20000),L.peek('px',6),'peek:2000:8192']
    steps += ['key:STATUS\\r','wait:1',L.until('wait_key',20000),'key: ','wait:1',L.until('idle',20000),
              'peek:2000:8192',L.poke('night',1),L.poke('view_dark',1),'key:V\\r','wait:1',L.until('idle',20000),'peek:2000:8192',
              'key:USE COMPASS\\r','wait:1',L.until('idle',20000),'peek:0400:1024']
    result = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    _,_,heading = state(result.dumps[0]); offset=int.from_bytes(result.dumps[1],'little')
    assert header(result.dumps[2]) == expected(heading,offset)
    for i, (key,delta) in enumerate(turns):
        _,_,actual = state(result.dumps[3+2*i])
        if delta is not None:
            heading=(heading+delta)%560
            assert actual==heading
        else:
            heading=actual
            cardinal='NESW'.index(key[5])
            assert heading == (cardinal*140+offset)%560
        assert header(result.dumps[4+2*i]) == expected(heading,offset),key
    assert header(result.dumps[-3]) == expected(heading,offset), 'STATUS return lost compass'
    assert header(result.dumps[-2]) == expected(heading,offset), 'night lost compass'
    assert 'OK, WHAT NEXT?' in '\n'.join(text_screen(result.dumps[-1]))
    print('  active on boot, arrows/LOOK, magnetic cardinals, STATUS, night and USE COMPASS OK')


def magnetic_seams():
    original=(HERE/'build/map.bin').read_bytes()
    for declination in (-90, -17, 0, 17, 90):
        m=bytearray(original);m[24]=declination&255
        with tempfile.TemporaryDirectory() as tmp:
            disk=disk_with(tmp,m)
            steps=[L.until('idle',20000),'key:LOOK N\\r','wait:1',L.until('idle',20000),
                   L.peek('heading',2), L.peek('hud_offset',2),'peek:2000:8192']
            result=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        heading,offset=(int.from_bytes(b,'little') for b in result.dumps[:2])
        assert heading==offset
        assert header(result.dumps[2])==expected(heading,offset)
    print('  signed regional declinations: magnetic north stays beneath pointer OK')


if __name__=='__main__':
    all_headings()
    lifecycle()
    magnetic_seams()
