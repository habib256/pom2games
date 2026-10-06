#!/usr/bin/env python3
"""ProDOS image round trip; optional IIe execution with the bundled a2shot SDK."""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
TILE_TOP=int(re.search(r'^#define CB_TILE_TOP (\d+)$',(ROOT/'chromabreak/src/layout.h').read_text(),re.M)[1])

def run(args):
    args=[str(a) for a in args]
    args=[step for a in args for step in (["wait:1",a] if a.startswith("until:") else [a])]
    result=subprocess.run(args,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    return result.stdout

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--disk',type=Path,default=ROOT/'dist/CHROMABREAK.po')
    ap.add_argument('--labels',type=Path,default=ROOT/'chromabreak/build/game.lbl')
    ap.add_argument('--image-only',action='store_true')
    a=ap.parse_args()
    source=(ROOT/'chromabreak/src/levels.h').read_text()
    rows=re.findall(r'\{([0-9,]+)\}',source)
    boards=[tuple(map(int,row.split(','))) for row in rows]
    assert len(boards)==12 and len(set(boards))==12
    for board in boards:
        assert len(board)==96 and set(board)<=set((0,1,2,3,255))
        assert any(0<hp<255 for hp in board) and 0 in board
        # Every destructible tile has a route from below once preceding
        # bricks are removed; steel must never enclose a required tile.
        seen=set(i for i in range(84,96) if board[i]!=255);pending=list(seen)
        while pending:
            i=pending.pop();x,y=i%12,i//12
            for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=nx<12 and 0<=ny<8:
                    n=ny*12+nx
                    if n not in seen and board[n]!=255:seen.add(n);pending.append(n)
        assert all(i in seen for i,hp in enumerate(board) if 0<hp<255),'steel seals a required brick'
    print('PASS twelve distinct boards, resistance values and routes around steel')
    spec=importlib.util.spec_from_file_location('prodos_read',ROOT/'dev/tools/prodos/read_volume.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    image=module.Image(a.disk.read_bytes())
    assert image.header()['name']=='CHROMABREAK'
    assert image.header()['blocks']==280 and len(image.d)==143360
    entries={e[1:1+(e[0]&15)].decode():e for e in image.entries(2)}
    assert set(entries)=={'PRODOS','CHROMA.SYSTEM','CHROMA.SYS','HIGHSCORES'}
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
    labels={n:int(v,16) for v,n in re.findall(r'al ([0-9a-fA-F]+) \.(_\w+)',a.labels.read_text())}
    def peek(name,length=1): return f'peek:{labels["_"+name]:04X}:{length}'
    def poke(name,value): return f'poke:{labels["_"+name]:04X}:{value:02X}'
    def values(out,name):
        return [bytes.fromhex(s) for s in re.findall(rf'(?m)^{labels["_"+name]:04X}: ([0-9A-F ]+)$',out)]
    tick=f'until:{labels["_game_tick"]:04X}:3000'
    with tempfile.TemporaryDirectory(prefix='chromabreak-') as folder:
        steps=[tick,'peek:C018:8',peek('mouse_slot'),'key: ',tick,tick,peek('state'),peek('remaining'),
               peek('ball_live'),peek('frames',2),'wait:120',peek('frames',2),
               'key: ',tick,tick,peek('ball_live'),peek('ball_y'),'wait:120',peek('ball_y'),
               'key:P',tick,tick,peek('paused'),peek('ball_x'),peek('ball_y'),
               'wait:120',peek('ball_x'),peek('ball_y'),'key:P',tick,tick,peek('paused'),
               'key:A',tick,tick,'wait:20','key:S',tick,tick,peek('pad_x'),
               'key:\\e','wait:600','peek:C018:8']
        out=run([emulator,'--iie','--disk',a.disk,*steps])
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
            launch=run([emulator,'--iie','--disk',a.disk,tick,'key:'+key,tick,tick,
                        peek('state'),peek('ball_live'),peek('mode')])
            assert values(launch,'state')==[b'\1'] and values(launch,'ball_live')==[b'\1']
            assert values(launch,'mode')==[b'\0'],'quick keyboard launch'
        for choice, expected in enumerate(((5,26,2,4,10,4),(3,22,3,6,8,5),(2,18,4,7,6,6)),1):
            fields=('lives','pad_width','speed','speed_limit','ramp_period','reward_period')
            selected=run([emulator,'--iie','--disk',a.disk,tick,'key:'+str(choice),tick,
                          'key: ',tick,tick,*[peek(field) for field in fields]])
            assert tuple(values(selected,field)[0][0] for field in fields)==expected,'difficulty configuration'
        # Last brick transitions through all 12 boards, using actual collision
        # and level-loader code; scenario injection is limited to test setup.
        steps=[tick,'key: ',tick,tick]
        for level in range(12):
            steps += [poke('level',level),poke('remaining',1)]
            for i in range(96): steps.append(f'poke:{labels["_bricks"]+i:04X}:{1 if i==0 else 0:02X}')
            steps += [poke('ball_x',8),poke('ball_y',TILE_TOP+8),poke('ball_live',1),poke('round_live',1),poke('dx',1),
                      poke('dy',255),poke('vx',0),poke('vy',255),poke('fraction_y',255),
                      tick,peek('level'),peek('state'),peek('ball_live')]
        steps += ['key:\\e',tick,'key: ',tick,tick,peek('level'),peek('state'),'reset','wait:600','peek:C018:8']
        out=run([emulator,'--iie','--disk',a.disk,*steps])
        assert [s[0] for s in values(out,'level')]==list(range(1,13))+[0]
        assert [s[0] for s in values(out,'state')]==[1]*11+[4,1]
        final=bytes.fromhex(re.findall(r'(?m)^C018: ([0-9A-F ]+)$',out)[-1])
        assert final[2]&128 and not final[7]&128,'RESET must return to ProDOS'
    print('PASS IIe DHGR boot, >=25fps, keyboard, pause, 12 sector transitions, victory/replay, ESC/RESET')
if __name__=='__main__': main()
