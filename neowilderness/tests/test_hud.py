#!/usr/bin/env python3
"""Compass ribbon: independent pixels, magnetic alignment and UI lifecycle.

Lot 4: the native DHGR ribbon, bytes 14..25 of both banks (colour pixels
49..90), rows 0..15, against tools/dhgr_ref.hud_banks (strip of
tools/genhud.py, 4 azimuth units per pixel, fixed yellow pointer).
"""
import tempfile
from common import HERE, L, DISK, a2test, disk_with, state, text_screen, DHGR_BANKS, dhgr, banks


def header(main, aux=None):
    """(main, aux) bytes 14..25 of rows 0..15, other bytes zero (a 16 KB page
    dump, or its two banks)."""
    if aux is None:
        main, aux = banks(main)
    def rows(page):
        return b''.join(bytes(14) + page[a2test.hgr_offset(y)+14:a2test.hgr_offset(y)+26] + bytes(14)
                        for y in range(16))
    return rows(main), rows(aux)


def expected(heading, offset):
    return dhgr().hud_banks(heading, offset)


def all_headings():
    steps = [L.until('idle', 20000), L.peek('hud_offset',2)]
    # Redirect VIEW to the real HUD routine in this private emulator session.
    # This covers every azimuth without recomputing 560 terrain frames.
    code = bytes([0x4C, L['hud_draw'] & 255, L['hud_draw'] >> 8])
    for i, b in enumerate(code):
        steps += [L.poke('show_view_scene', b, i)]
    for heading in range(560):
        steps += [L.poke('heading', heading), L.poke('heading', heading>>8,1),
                  'key:V\\r', 'wait:1', L.until('idle',20000), *DHGR_BANKS]
    result = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    offset = int.from_bytes(result.dumps[0],'little')
    for heading in range(560):
        main, aux = result.dumps[1+2*heading:3+2*heading]
        assert header(main, aux) == expected(heading,offset), f'azimuth {heading}: ribbon differs'
    assert len(result.dumps) == 1121
    print('  560 azimuths: exact labels/ticks, fixed pointer, clipping, and full-circle seam OK')


def lifecycle():
    probe = [L.peek('px',6), *DHGR_BANKS]
    steps = [L.until('idle',20000), L.peek('px',6), L.peek('hud_offset',2), *DHGR_BANKS]
    turns = [('\\>',35), ('\\<',-35), ('LOOK R\\r',70), ('LOOK L\\r',-70), ('LOOK B\\r',280),
             ('USE COMPASS\\r',0),   # lot 7: LOOK N/E/S/W need the compass in use
             ('LOOK N\\r',None), ('LOOK E\\r',None), ('LOOK S\\r',None), ('LOOK W\\r',None)]
    for key,_ in turns:
        steps += [f'key:{key}', 'wait:1', L.until('idle',20000), *probe]
    steps += ['key:STATUS\\r','wait:1',L.until('wait_key',20000),'key: ','wait:1',L.until('idle',20000),
              *DHGR_BANKS,L.poke('night',1),L.poke('view_dark',1),'key:V\\r','wait:1',L.until('idle',20000),*DHGR_BANKS,
              'key:USE COMPASS\\r','wait:1',L.until('idle',20000),'peek:0400:1024']
    result = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    d = result.dumps
    _,_,heading = state(d[0]); offset=int.from_bytes(d[1],'little')
    assert header(d[2], d[3]) == expected(heading,offset)
    for i, (key,delta) in enumerate(turns):
        _,_,actual = state(d[4+3*i])
        if delta is not None:
            heading=(heading+delta)%560
            assert actual==heading
        else:
            heading=actual
            cardinal='NESW'.index(key[5])
            error=(heading-cardinal*140-offset)%560   # the compass error: +-2 degrees
            assert min(error,560-error) <= 4, (key,heading)
        assert header(d[5+3*i], d[6+3*i]) == expected(heading,offset),key
    assert header(d[-5], d[-4]) == expected(heading,offset), 'STATUS return lost compass'
    assert header(d[-3], d[-2]) == expected(heading,offset), 'night lost compass'
    assert 'OK, WHAT NEXT?' in '\n'.join(text_screen(d[-1]))
    print('  active on boot, arrows/LOOK, magnetic cardinals, STATUS, night and USE COMPASS OK')


def magnetic_seams():
    original=(HERE/'build/map.bin').read_bytes()
    for declination in (-90, -17, 0, 17, 90):
        m=bytearray(original);m[24]=declination&255
        with tempfile.TemporaryDirectory() as tmp:
            disk=disk_with(tmp,m)
            steps=[L.until('idle',20000),'key:USE COMPASS\\r','wait:1',L.until('idle',20000),
                   'key:LOOK N\\r','wait:1',L.until('idle',20000),
                   L.peek('heading',2), L.peek('hud_offset',2),*DHGR_BANKS]
            result=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        heading,offset=(int.from_bytes(b,'little') for b in result.dumps[:2])
        assert min((heading-offset)%560,(offset-heading)%560) <= 4   # compass error +-2 degrees
        assert header(*result.dumps[2:4])==expected(heading,offset)
    print('  signed regional declinations: magnetic north stays beneath pointer OK')


if __name__=='__main__':
    all_headings()
    lifecycle()
    magnetic_seams()
