#!/usr/bin/env python3
"""DOS records: actual writes, sorted entries, initials, reload and protection."""
from pathlib import Path
import argparse
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test
import dos33

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--disk',type=Path,default=ROOT/'dist/ARKABREAKOUT.dsk')
    ap.add_argument('--labels',type=Path,default=ROOT/'arkabreakout/build/game.lbl')
    args=ap.parse_args()
    L=a2test.labels(args.labels)
    original=args.disk
    before=original.read_bytes()
    with tempfile.TemporaryDirectory(prefix='arka-records-') as tmp:
        disk=Path(tmp)/'game.dsk';disk.write_bytes(before)
        def submit(points,name,wp=False):
            steps=[L.until('menu_loop'),'key: ',L.until('loop'),'key:P','wait:15',L.until('loop')]
            fixture={'ball_x':20,'ball_y':179,'ball_live':1,'ball_diry':0,'ball_speed':0,'ball_yspeed':255,'ball_yfrac':255,'ball_frac':255,'speed':1,'lives':1,'remaining':1,'furthest':20}
            steps += [L.poke(n,v) for n,v in fixture.items()]
            steps += [L.poke('score',ord(c),i) for i,c in enumerate(f'{points:06}')]
            steps += ['press:P','wait:90',f'key:{name}',L.until('menu_loop'),L.peek('record_data',55),L.peek('save_status'),f'dsk:{disk}']
            return a2test.run(disk,steps,wp=wp)
        for score,name in [(3200,'ABC'),(1800,'DEF'),(1500,'GHI'),(1240,'JKL'),(900,'MNO'),(2500,'PQR')]:
            r=submit(score,name);assert r.mem(L['save_status'],1)==b'\1'
        data=dos33.read_file(disk.read_bytes(),'RECORDS')
        assert data[:5]==b'ABR\1\x14' and len(data)==55,data
        assert [data[5+i*10:11+i*10] for i in range(5)]==[b'003200',b'002500',b'001800',b'001500',b'001240'],data
        assert [data[11+i*10:14+i*10] for i in range(5)]==[b'ABC',b'PQR',b'DEF',b'GHI',b'JKL'],data
        r=a2test.run(disk,[L.until('menu_loop'),L.peek('furthest'),L.peek('best_score',6),'key:H','wait:15','key: ',L.until('menu_loop')])
        assert r.mem(L['furthest'],1)==b'\x14' and r.mem(L['best_score'],6)==b'003200'
        saved=disk.read_bytes();r=submit(5000,'XYZ',wp=True)
        assert r.mem(L['save_status'],1)==b'\2' and disk.read_bytes()==saved,'protected disk changed'
    assert original.read_bytes()==before,'test modified release disk'
    print('DOS records: six submissions, sort/initials, reload/progression, high-score screen and write protection passed.')
if __name__=='__main__': main()
