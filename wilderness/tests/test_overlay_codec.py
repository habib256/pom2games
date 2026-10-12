#!/usr/bin/env python3
"""Backward module streams, real DOS decode and exact projection cache."""
import random
from common import HERE, DISK, L, a2test
from pack_overlay import pack, unpack, safe_in_place, MAGIC, PREFIX
from pack_boot import compress
from dos33 import read_file, file_sectors


def main():
    rng = random.Random(5800)
    fixtures = [bytes([i])*8192 for i in (0,1,255)]
    fixtures += [rng.randbytes(n) for n in (127,128,129,255,256,2048,8192)]
    fixtures += [bytes(range(256))*32, b'ABC'*2700, b'\xA9\x01\x85\x50'*2000]
    for data in fixtures:
        assert unpack(pack(data)) == data
    # A long final run compresses well, but decoding it backward would
    # overwrite the unread random prefix. A shorter stream alone is unsafe.
    unsafe = rng.randbytes(7000) + bytes(1100)
    stream = compress(unsafe[PREFIX:][::-1])
    assert 6 + len(stream) + PREFIX < len(unsafe)
    assert not safe_in_place(stream, len(unsafe))
    assert pack(unsafe) == unsafe
    print('  host streams: raw fallback, overlap, page boundaries and 8 KB windows: OK')
    image = DISK.read_bytes()
    for name, path, sectors in (
            ('WILDSIM', 'wildsim.bin', (32, 22)),
            ('WILDPLN', 'original_graphics/wreck.bin', (8, 6)),
            ('WILDBER', 'original_graphics/bear.bin', (4, 2)),
            ('WILDHUT', 'original_graphics/cabin.bin', (5, 3))):
        original = (HERE / 'build' / path).read_bytes()
        encoded = read_file(image, name)
        assert encoded.startswith(MAGIC), name
        assert unpack(encoded) == original, name
        assert (len(encoded)+259)//256 < (len(original)+259)//256, name
        assert len(file_sectors(image, name)) == (len(original)+259)//256, (name, 'reserved extent')
    assert not read_file(image, 'WILDMED').startswith(MAGIC)
    print('  DOS header limits transfers: packed modules reduce sectors; extents retained: OK')
    modules = {1:'wildvoc.bin',2:'wildscr.bin',3:'wildsim.bin',
               4:'wildwat.bin',5:'original_graphics/wreck.bin',
               6:'original_graphics/bear.bin',7:'original_graphics/cougar.bin',
               8:'original_graphics/rattlesnake.bin',9:'original_graphics/cabin.bin',
               10:'wildsit.bin',11:'wildprj.bin',12:'wildtrv.bin',13:'wildinp.bin',
               14:'wilditm.bin',15:'wildhud.bin',16:'wildsta.bin',17:'wildmed.bin',
               18:'wildmed.bin',19:'wildmvi.bin',20:'wildtre.bin',21:'wildadv.bin',22:'wildout.bin'}
    with a2test.Session(DISK) as s:
        s.step(L.until('idle',20000))
        rows = s.step(L.peek('row_n0',256)).data
        assert rows == bytes(95+(3*q+15)//16 for q in range(256))
        entry=L['idle']
        address=L['overlay_load']
        code=bytes((0xA9,0,0x20,address&255,address>>8,0x4C,entry&255,entry>>8))
        for i,b in enumerate(code):s.step(f'poke:{entry+i:04X}:{b:02X}')
        for module,name in modules.items():
            base=0x2000 if module == 3 else 0x5800
            expected=(HERE/'build'/name).read_bytes()
            s.step(L.poke('overlay_current',0));s.step(L.poke('sim_loaded',0))
            s.step(f'poke:{entry+1:04X}:{module:02X}')
            guard=s.step(f'peek:{base+(8192 if base==0x2000 else 2048):04X}:16').data
            s.step(L.until('overlay_before_dos',20000))
            zp=s.step('peek:0000:256').data
            text=s.step('peek:0400:1024').data
            s.step(L.until('overlay_ready',20000))
            assert s.step(f'peek:{base:04X}:{len(expected)}').data==expected,name
            assert s.step('peek:0000:256').data==zp,(name,'ZP')
            actual=s.step('peek:0400:1024').data
            for row in range(24):
                offset=(row%8)*128+(row//8)*40
                assert actual[offset:offset+40]==text[offset:offset+40],(name,'text')
            assert s.step(f'peek:{base+(8192 if base==0x2000 else 2048):04X}:16').data==guard,(name,'window overrun')
            s.step(L.until('idle',100))
    print('  22 native DOS module loads: exact bytes, all ZP/FAC, text and window guards: OK')
    print('  reconstructed 256-row projection cache is exact: OK')


if __name__=='__main__':main()
