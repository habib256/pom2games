#!/usr/bin/env python3
"""ProDOS image round trip; optional IIe execution with the bundled a2shot SDK."""
import argparse
import importlib.util
from pathlib import Path
import re
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test
TILE_TOP=int(re.search(r'^#define CB_TILE_TOP (\d+)$',(ROOT/'chromabreak/src/layout.h').read_text(),re.M)[1])

def run(disk,steps):
    # a2shot wants a frame between a key and the next until: breakpoint.
    return a2test.run(disk,steps,iie=True,pad_until=True).out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--disk',type=Path,default=ROOT/'dist/CHROMABREAK.po')
    ap.add_argument('--labels',type=Path,default=ROOT/'chromabreak/build/game.lbl')
    ap.add_argument('--image-only',action='store_true')
    a=ap.parse_args()
    linkmap=a.labels.with_suffix('.map').read_text()
    linked=set(re.findall(r'platform\.lib\(([^)]+)\):',linkmap))
    assert {'dhgr_clear_asm.o','gfx_u16_digits.o'}<=linked, 'missing library modules'
    unused={'dhgr_pixel.o','dhgr_getpixel.o','dhgr_pixel_address.o',
            'dhgr_access_asm.o','dhgr_write_asm.o','dhgr_read_asm.o','dhgr_fill.o','dhgr_fill_bits.o',
            'dhgr_bit_rect.o','dhgr_span_asm.o','dhgr_plot_color.o','dhgr_span.o',
            'dhgr_block.o','dhgr_block_asm.o','dhgr_sprite.o','dhgr_address.o',
            'dhgr_text.o','dhgr_text_asm.o','hgr_font.o','dhgr_small.o',
            # Text is Beautiful Boot (finetext.s); only the $0800 tables remain.
            'dhgr_small_asm.o','dhgr_small_string.o','dhgr_small_params.o',
            # The game clears to $80 (bit 7: Chat Mauve colour) itself.
            'dhgr_clear.o'}
    assert not linked&unused, ('unused library modules in game',sorted(linked&unused))
    print('PASS link map: unused drawing, transfers and text wrappers excluded')
    spec=importlib.util.spec_from_file_location('pack_levels',ROOT/'chromabreak/tools/pack_levels.py')
    packer=importlib.util.module_from_spec(spec);spec.loader.exec_module(packer)
    levels=packer.load();packer.check(levels)
    for name,board in levels:
        assert set(board)<=set((0,1,2,3,255)) and 0 in board, name
    print(f'PASS {len(levels)} distinct boards, names, resistance values and routes around steel')
    spec=importlib.util.spec_from_file_location('prodos_read',ROOT/'dev/tools/prodos/read_volume.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    image=module.Image(a.disk.read_bytes())
    assert image.header()['name']=='CHROMABREAK'
    assert image.header()['blocks']==280 and len(image.d)==143360
    entries={e[1:1+(e[0]&15)].decode():e for e in image.entries(2)}
    assert set(entries)=={'PRODOS','CHROMA.SYSTEM','CHROMA.SYS','HIGHSCORES','ENDING'}
    assert all(entries[name][0x10]==0xFF for name in ('PRODOS','CHROMA.SYSTEM','CHROMA.SYS'))
    assert entries['HIGHSCORES'][0x10]==6
    assert image.read(entries['HIGHSCORES'])==(a.labels.parent/'HIGHSCORES').read_bytes()
    assert image.read(entries['PRODOS'])==(ROOT/'dev/tools/prodos/PRODOS').read_bytes()
    for name in ('CHROMA.SYSTEM', 'CHROMA.SYS'):
        assert image.read(entries[name])==(a.labels.parent/name).read_bytes()
    assert image.d[:1024]==(ROOT/'dev/tools/prodos/boot.bin').read_bytes()
    assert image.free_blocks()>150
    print('PASS bootable ProDOS 2.4.3 volume, SYS loader and payload round trip')
    emulator=ROOT/'dev/tools/a2shot/a2shot'
    if a.image_only: return
    if sys.platform!='darwin' or not emulator.exists():
        print('SKIP IIe execution: requires macOS arm64 a2shot (make -C dev/tools/a2shot)')
        return
    labels=a2test.labels(a.labels,strip=True)
    peek,poke=labels.peek,labels.poke
    def values(out,name):
        return [bytes.fromhex(s) for s in re.findall(rf'(?m)^{labels[name]:04X}: ([0-9A-F ]+)$',out)]
    tick=labels.until('game_tick',3000)
    with tempfile.TemporaryDirectory(prefix='chromabreak-') as folder:
        steps=[tick,'peek:C018:8',peek('mouse_slot'),'key: ',tick,tick,peek('state'),peek('remaining'),
               peek('ball_live'),peek('frames',2),'wait:120',peek('frames',2),
               'key: ',tick,tick,peek('ball_live'),peek('ball_y'),'wait:120',peek('ball_y'),
               'key:P',tick,tick,peek('paused'),peek('ball_x'),peek('ball_y'),
               'wait:120',peek('ball_x'),peek('ball_y'),'key:P',tick,tick,peek('paused'),
               'key:A',tick,tick,'wait:20','key:S',tick,tick,peek('pad_x'),
               'key:\\e',tick,'key:Q','wait:600','peek:C018:8']
        out=run(a.disk,steps)
        flags=[bytes.fromhex(s) for s in re.findall(r'(?m)^C018: ([0-9A-F ]+)$',out)]
        assert not flags[0][2]&128 and flags[0][7]&128,'DHGR title'
        assert flags[-1][2]&128 and not flags[-1][7]&128,'ProDOS text exit'
        assert values(out,'mouse_slot')==[b'\0'],'keyboard fallback when no card'
        assert values(out,'state')==[b'\1'] and values(out,'remaining')==[bytes([52])]
        assert values(out,'ball_live')==[b'\1',b'\1']
        count=[int.from_bytes(s,'little') for s in values(out,'frames')]
        assert (count[1]-count[0])%65536>=50,('below 25fps',count)
        assert values(out,'paused')==[b'\1',b'\0']
        ys=values(out,'ball_y'); xs=values(out,'ball_x')
        assert ys[0]!=ys[1] and ys[-2]==ys[-1] and xs[0]==xs[1],'motion/pause'
        assert values(out,'pad_x')[0][0]<60,'keyboard controls'
        for key in ('\\r','K'):
            launch=run(a.disk,[tick,'key:'+key,tick,tick,peek('state'),peek('ball_live'),peek('mode')])
            assert values(launch,'state')==[b'\1'] and values(launch,'ball_live')==[b'\1']
            assert values(launch,'mode')==[b'\0'],'quick keyboard launch'
        for choice, expected in enumerate(((5,26,2,4,10,4),(3,22,3,6,8,5),(2,18,4,7,6,6)),1):
            fields=('lives','pad_width','speed','speed_limit','ramp_period','reward_period')
            selected=run(a.disk,[tick,'key:'+str(choice),tick,'key: ',tick,tick,*[peek(field) for field in fields]])
            assert tuple(values(selected,field)[0][0] for field in fields)==expected,'difficulty configuration'
        # Last brick transitions through all 12 boards, using actual collision
        # and level-loader code; scenario injection is limited to test setup.
        steps=[tick,'key: ',tick,tick]
        for level in range(len(levels)):
            steps += [poke('level',level),poke('remaining',1)]
            for i in range(96): steps.append(f'poke:{labels["_bricks"]+i:04X}:{1 if i==0 else 0:02X}')
            steps += [poke('ball_x',8),poke('ball_y',TILE_TOP+8),poke('ball_live',1),poke('round_live',1),poke('dx',1),
                      poke('dy',255),poke('vx',0),poke('vy',255),poke('fraction_y',255),
                      tick,peek('level'),peek('state'),peek('ball_live')]
        steps += ['key:\\e',tick,'key: ',tick,tick,peek('level'),peek('state'),'reset','wait:600','peek:C018:8']
        out=run(a.disk,steps)
        assert [s[0] for s in values(out,'level')]==list(range(1,len(levels)+1))+[0]
        assert [s[0] for s in values(out,'state')]==[1]*(len(levels)-1)+[4,1]
        final=bytes.fromhex(re.findall(r'(?m)^C018: ([0-9A-F ]+)$',out)[-1])
        assert final[2]&128 and not final[7]&128,'RESET must return to ProDOS'
    print('PASS IIe DHGR boot, >=25fps, keyboard, pause, every sector transition, victory/replay, ESC/RESET')
if __name__=='__main__': main()
