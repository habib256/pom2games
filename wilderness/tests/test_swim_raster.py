#!/usr/bin/env python3
"""Original integer swimming paths: headings, sector boundaries and overlay state."""
import argparse, subprocess, sys
from common import HERE,L,DISK,a2test,fp
from gendata import fp as encode
from test_thermal import call

HEADS = list(range(360))
COUNT = 8


def writes(addr,data):
    return [f'poke:{addr+i:04X}:{b:02X}' for i,b in enumerate(data)]


def native():
    out=HERE/'build/re_swim_raster';out.mkdir(exist_ok=True)
    (out/'state.bin').write_bytes((HERE/'build/game.bin').read_bytes()[0x4000:0x5000])
    (out/'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n20 PRINT CHR$(4);"BLOAD MODULE"\n30 PRINT CHR$(4);"BRUN DRIVER"\n')
    def disk(name,path,entry,stop=None,save=False):
        module=bytearray((HERE/path).read_bytes())
        if stop: module[stop-0x5800]=0x60
        (out/f'{name}.bin').write_bytes(module)
        driver=bytes((0x20,entry&255,entry>>8))+(bytes.fromhex('8E 00 02 8C 01 02') if save else b'')
        end=0x800+len(driver);driver+=bytes.fromhex('4C 00 08')
        (out/f'{name}-driver.bin').write_bytes(driver)
        d=out/f'{name}.dsk'
        subprocess.run([sys.executable,str(HERE.parent/'dev/tools/dos33.py'),'--out',str(d),
            '--bas',f'HELLO={out/"hello.bas"}','--bin',f'STATE={out/"state.bin"}@0x4000',
            '--bin',f'MODULE={out/(name+".bin")}@0x5800',
            '--bin',f'DRIVER={out/(name+"-driver.bin")}@0x0800'],check=True,capture_output=True)
        return d,f'until:{end:04X}:1000'
    d,end=disk('prepare','build/re_env/ch/t08s07.bin',0x5BFB,0x5C97)
    steps=['until:0800:20000']
    for h in HEADS:
        steps+=writes(0xD0,bytes((100,80,h&255,h>>8)))
        steps += [end,'peek:4B78:2','peek:4BA2:1','peek:4C8E:10','until:0800:1000']
    r=a2test.run(d,steps,emulator=a2test.A2SHOT,timeout=1800)
    starts=[(r.mem(0x4B78,2,k),r.mem(0x4BA2,1,k),r.mem(0x4C8E,10,k)) for k in range(len(HEADS))]
    d,end=disk('steps','build/re_env/ch/t09s00.bin',0x5B35,save=True)
    steps=['until:0800:20000']
    for flags,major,floats in starts:
        steps+=writes(0x4B78,flags)+writes(0x4BA2,major)+writes(0x4C8E,floats)
        for _ in range(COUNT): steps += [end,'peek:0200:2','until:0800:1000']
    r=a2test.run(d,steps,emulator=a2test.A2SHOT,timeout=1800)
    poses=[tuple(r.mem(0x200,2,k)) for k in range(len(HEADS)*COUNT)]
    (out/'paths.txt').write_text('\n'.join(f'{h}: {poses[k*COUNT:(k+1)*COUNT]}' for k,h in enumerate(HEADS))+'\n')
    return poses


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--original',action='store_true');args=ap.parse_args()
    idle=L.until('idle',20000);steps=[idle]
    prep_end=f'until:{L["idle"]+3:04X}:6000'
    # The next-step driver commits its result just as do_walk does.
    next_code=bytearray((0x20,L['swim_next']&255,L['swim_next']>>8))
    for i in range(4):
        src=L['nx']+i;dest=L['px']+i
        next_code+=bytes((0xAD,src&255,src>>8,0x8D,dest&255,dest>>8))
    next_end=f'until:{L["idle"]+len(next_code):04X}:6000'
    next_code+=bytes((0x4C,L['idle']&255,L['idle']>>8))
    for h in HEADS:
        head=round(h*560/360)%560
        for name,value in (('px',100*128),('py',80*128),('heading',head)):
            steps += [L.poke(name,value),L.poke(name,value>>8,1)]
        steps+=call(['swim_prepare'])+[prep_end,idle]
        steps+=writes(L['idle'],next_code)
        for _ in range(COUNT): steps += [next_end,L.peek('px',4),idle]
    r=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    poses=[]
    for k in range(len(HEADS)*COUNT):
        b=r.mem(L['px'],4,k)
        coords=tuple(int.from_bytes(b[i:i+2],'little') for i in (0,2))
        assert all(c%128==0 for c in coords),(k,coords)
        poses.append(tuple(c//128 for c in coords))
    if args.original:
        oracle=native()
        assert poses==oracle,[(HEADS[k//COUNT],k%COUNT,a,b) for k,(a,b) in enumerate(zip(poses,oracle)) if a!=b][:20]
    else:
        for k,h in enumerate(HEADS):
            path=poses[k*COUNT:(k+1)*COUNT];previous=(100,80)
            angle=(90-h)%360
            axis=1 if 46<=angle<135 or 226<=angle<315 else 0
            sign=-1 if 135<=angle<315 else 1
            for p in path:
                assert p[axis]-previous[axis]==sign,(h,previous,p)
                assert abs(p[1-axis]-previous[1-axis])<=1,(h,previous,p)
                previous=p
    print(f'{len(poses)} integer swimming positions / 360 headings'+(' match original ROM' if args.original else '')+': OK')


if __name__=='__main__':main()
