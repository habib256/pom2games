#!/usr/bin/env python3
"""Exact HGR sprite rasters, saved backgrounds and transition checkpoints."""
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test
PARITY = [0,0,1,1,0,0,1,1,0,1,0,1,0,1,0,0]
PALETTE = [0]*4+[128]*6+[0]*6
SHAPES = {'HAPPY':('happy_pat',16), 'BIRD1':('bird1_pat',16),
          'BIRD2':('bird2_pat',16), 'HEART':('heart_pat',8)}


def raster(bg, pattern, dim, x, y, color=0, pen=15):
    page=bytearray(bg)
    if not 9 <= y <= 182:
        return page
    x0=x-dim+(PARITY[pen] if color else 0)
    y0=y-dim-2
    for row in range(dim):
        for col in range(dim):
            index=row+(16 if col>=8 else 0)
            if pattern[index] & (128 >> (col%8)):
                for dy in (0,1):
                    for dx in ((0,) if color else (0,1)):
                        px,py=x0+col*2+dx,y0+row*2+dy
                        if 0 <= px < 280 and 0 <= py < 192:
                            a=a2test.hgr_offset(py)+px//7
                            page[a] |= 1 << (px%7)
                            if color: page[a]=(page[a]&127)|PALETTE[pen]
    return page


def command(steps,L,text):
    steps += ['key:'+text,'press:\r',L.until('repl')]


def check(disk,L,iie):
    steps=[L.until('read_line')]
    for name,dim in SHAPES.values(): steps += [L.peek(name,32 if dim==16 else 8)]
    cases=[]
    # All seven bit alignments, the 255/256 seam, clipping on every side,
    # both TMS sizes, and all sixteen colour/parity settings.
    for shape in SHAPES:
        for x,y in [(98+n,96) for n in range(7)]+[(0,9),(1,182),(255,96),(256,96),(279,182),(140,8),(140,183)]:
            cases.append((shape,x,y,0,15))
    cases += [('HAPPY',139+pen%2,96,1,pen) for pen in range(16)]
    command(steps,L,'PU CS SETSHAPE "HAPPY')
    steps += [L.until('read_line')]
    for shape,x,y,color,pen in cases:
        steps += [L.poke('em_color',color)]
        command(steps,L,f'SETPC {pen} SETXY {x} {y} SETSHAPE "{shape}')
        steps += ['peek:2000:8192',L.until('read_line')]
    result=a2test.run(disk,steps,iie=iie)
    patterns={}; offset=0
    for shape,(name,dim) in SHAPES.items():
        n=32 if dim==16 else 8
        patterns[shape]=result.data[offset:offset+n]; offset+=n
    for shape,x,y,color,pen in cases:
        actual=result.data[offset:offset+8192]; offset+=8192
        expected=raster(bytes(8192),patterns[shape],SHAPES[shape][1],x,y,color,pen)
        assert actual==expected, ('sprite raster',iie,shape,x,y,color,pen,
                                  next((i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b))
    assert offset==len(result.data)
    # Re-emitting the same frame should bypass conversion and all HGR writes.
    steps=[L.until('read_line')]
    command(steps,L,'PU CS SETSHAPE "BIRD1')
    steps += ['peek:2000:8192',L.until('read_line'),'key:SETSHAPE "BIRD1',
              'press:\r',L.until('cmd_setshape'),L.until('hgr_draw_emote'),
              L.until('emote_unchanged'),L.until('repl'),'peek:2000:8192']
    repeated=a2test.run(disk,steps,iie=iie)
    assert repeated.data[:8192]==repeated.data[8192:]
    assert repeated.cycles[-2]-repeated.cycles[-3]<200, ('identical frame was regenerated',iie)
    # SETPC alone must refresh a visible coloured emote (no move/shape change).
    steps=[L.until('read_line')]
    command(steps,L,'PU CS SETXY 140 96 SETSHAPE "HAPPY')
    steps += [L.until('read_line'),L.poke('em_color',1)]
    for pen in (4,3):
        command(steps,L,f'SETPC {pen}')
        steps += ['peek:2000:8192',L.until('read_line')]
    tinted=a2test.run(disk,steps,iie=iie).data
    for index,pen in enumerate((4,3)):
        assert tinted[index*8192:(index+1)*8192]==raster(bytes(8192),patterns['HAPPY'],16,140,96,1,pen), ('SETPC did not refresh emote',iie,pen)
    # CS must discard the old saved background before redrawing at HOME.
    steps=[L.until('read_line')]
    command(steps,L,'PU CS SETXY 140 96 SETSHAPE "HAPPY')
    steps += [L.until('read_line')]
    command(steps,L,'CS')
    steps += ['peek:2000:8192']
    cleared=a2test.run(disk,steps,iie=iie).data
    assert cleared==raster(bytes(8192),patterns['HAPPY'],16,128,96), ('CS restored obsolete background',iie)
    # Move off the old rectangle: old image survives preparation, new image
    # is present before restoring old-exclusive bytes (also on the II+).
    steps=[L.until('read_line')]
    command(steps,L,'PU CS SETXY 80 80 SETSHAPE "BIRD1')
    steps += ['peek:2000:8192',L.until('read_line'),'key:SETXY 180 120','press:\r',
              L.until('hgr_draw_emote'),'peek:2000:8192',L.until('ds_restore_old'),
              'peek:2000:8192',L.until('repl'),'peek:2000:8192']
    data=a2test.run(disk,steps,iie=iie).data
    old,pre,transition,final=[data[n:n+8192] for n in range(0,len(data),8192)]
    assert old==pre, ('sprite erased during preparation',iie)
    new=raster(bytes(8192),patterns['BIRD1'],16,180,120)
    assert final==new, ('movement left residue',iie)
    assert transition==bytes(a|b for a,b in zip(old,new)), ('new image not visible before old restoration',iie)
    # Draw through the current sprite, then move it away. The trail must
    # survive, including the palette bit; use a reference straight HGR line.
    steps=[L.until('read_line')]
    command(steps,L,'PU CS SETXY 120 96 SETSHAPE "HAPPY')
    steps += [L.until('read_line')]
    command(steps,L,'SETPC 4 PD SETH 90 FD 40')
    steps += [L.until('read_line')]
    command(steps,L,'PU SETXY 240 140')
    steps += ['peek:2000:8192',L.until('read_line')]
    command(steps,L,'SETXY 240 191') # hide via the turtle Y window
    steps += ['peek:2000:8192']
    data=a2test.run(disk,steps,iie=iie).data
    bg=bytearray(8192)
    for x in range(120,161):
        a=a2test.hgr_offset(96)+x//7
        bg[a]=(bg[a]|(1<<(x%7)))|128
    assert data[:8192]==raster(bg,patterns['HAPPY'],16,240,140), ('trail under moving sprite',iie)
    assert data[8192:]==bg, ('hide did not restore trail/palette',iie)
    # Bitmap text drawn over the sprite must update its saved background.
    steps=[L.until('read_line'),L.peek('bbfont',8,65*8)]
    command(steps,L,'PU CS SETXY 128 96 SETSHAPE "HAPPY')
    steps += [L.until('read_line')]
    command(steps,L,'LABEL "A')
    steps += [L.until('read_line')]
    command(steps,L,'SETXY 240 140')
    steps += ['peek:2000:8192']
    labeled=a2test.run(disk,steps,iie=iie).data
    bg=bytearray(8192)
    for row,bits in enumerate(labeled[:8]):
        for bit in range(8):
            if bits&(1<<bit):
                px=128+bit
                bg[a2test.hgr_offset(96+row)+px//7] |= 1<<(px%7)
    assert labeled[8:]==raster(bg,patterns['HAPPY'],16,240,140), ('glyph under sprite lost',iie)
    print(f'LOGO {"IIe" if iie else "II+"}: {len(cases)} exact sprite rasters, transition without blanking, trail and palette restoration OK.')


if __name__=='__main__':
    subprocess.run(['make','-C',str(ROOT/'logo')],check=True,stdout=subprocess.DEVNULL)
    L=a2test.labels(ROOT/'logo/build/logo.lbl')
    for iie in (False,True): check(ROOT/'dist/LOGO.dsk',L,iie)
