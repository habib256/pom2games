#!/usr/bin/env python3
"""Compare every production terrain-bank query with native ROM samples."""
import tempfile
from pathlib import Path
from common import HERE, L, a2test, disk_with
from test_adventure import original_map
import topo


def main():
    start = L['idle']
    # The command loop is retired for this isolated exhaustive lookup probe.
    # Each row runs real cell_native, including DOS bank switches, then pauses.
    code = bytearray((0xA0,0,0xA2,0,0x20,L['cell_native']&255,L['cell_native']>>8,
                      0xAC,(start+1)&255,(start+1)>>8,0x99,0,0x20,
                      0xAD,L['geo_wooded']&255,L['geo_wooded']>>8,0x99,0,0x21,
                      0xAD,L['geo_water_kind']&255,L['geo_water_kind']>>8,0x99,0,0x22,
                      0xEE,(start+1)&255,(start+1)>>8,
                      0xAC,(start+1)&255,(start+1)>>8,0xC0,224))
    code += bytes((0xD0,(2-len(code)-2)&255))
    stop = start+len(code)
    code += bytes((0x4C,start&255,start>>8))
    steps = [L.until('idle',20000)]
    steps += [f'poke:{start+i:04X}:{v:02X}' for i,v in enumerate(code)]
    for y in range(168):
        steps += [f'poke:{start+1:04X}:00',f'poke:{start+3:04X}:{y:02X}',
                  f'until:{stop:04X}:6000','peek:2000:224','peek:2100:224','peek:2200:224',
                  f'until:{start:04X}:1000']
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp,original_map())
        r = a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    heights = (HERE/'build/re_geography/heights.bin').read_bytes()
    types = (HERE/'build/re_geography/types.bin').read_bytes()
    woods = list(topo.woods((HERE/'build/files/TOPO.B').read_bytes()))
    for y in range(168):
        expected = bytes(h | (128 if t in (1,128) else 0)
                         for h,t in zip(heights[y*224:(y+1)*224],types[y*224:(y+1)*224]))
        assert r.mem(0x2000,224,y) == expected, ('height/water',y)
        assert [bool(v) for v in r.mem(0x2100,224,y)] == [
            any(a<=x<=b for a,b in woods[y]) for x in range(224)], ('woodland',y)
        for x, kind in enumerate(types[y*224:(y+1)*224]):
            if kind in (1,128):
                assert r.mem(0x2200,224,y)[x] == (64 if kind == 1 else 0), ('river/lake',x,y)
    print('37632 heights, shores, river/lake types and woodland coordinates match native ROM samples')


if __name__=='__main__': main()
