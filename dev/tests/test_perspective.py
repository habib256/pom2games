#!/usr/bin/env python3
"""Fixed-camera projection: full host grid and real cc65/6502 boundary cases."""
import argparse
import ctypes
from fractions import Fraction
from pathlib import Path
import tempfile
from test_hgr import DEV, run, compile_source, a2test
from test_audio import load_tool


class Camera(ctypes.Structure):
    _fields_ = [('scale',ctypes.POINTER(ctypes.c_ubyte)),
                ('shift',ctypes.POINTER(ctypes.c_uint)),
                ('screen_y',ctypes.POINTER(ctypes.c_ubyte)),
                ('rows',ctypes.c_ubyte)]


class Point(ctypes.Structure):
    _fields_ = [('x',ctypes.c_uint),('y',ctypes.c_ubyte)]


def expected(x, y, rows=192, focal=78, center=140, horizon=31, bottom=191):
    # Independent rational camera model and documented Q8 quantization.
    ratio = Fraction(focal) / (Fraction(focal) + rows-1-y)
    quantized = max(1, int(256 * ratio))
    return (x * quantized // 256 + center * (256-quantized) // 256,
            horizon + int((bottom-horizon)*ratio))


def host_check(work, tool):
    library = work/'perspective.so'
    run(['cc','-std=c99','-Wall','-Wextra','-Werror','-shared','-fPIC',
         '-D__fastcall__=','-o',library,DEV/'lib/perspective/perspective.c'])
    project = ctypes.CDLL(str(library)).a2_perspective_project
    project.argtypes = [ctypes.POINTER(Camera),ctypes.c_uint,ctypes.c_ubyte,
                       ctypes.POINTER(Point)]
    project.restype = ctypes.c_ubyte
    point = Point()
    for config in ({},dict(rows=17,focal=24,center=0,horizon=8,bottom=160),
                   dict(rows=192,focal=Fraction('0.25'),center=279,horizon=0,bottom=191)):
        scale, shift, screen_y = tool.tables(**config)
        a=(ctypes.c_ubyte*len(scale))(*scale)
        b=(ctypes.c_uint*len(shift))(*shift)
        c=(ctypes.c_ubyte*len(screen_y))(*screen_y)
        camera=Camera(a,b,c,len(scale))
        for y in range(len(scale)):
            for x in range(280):
                assert project(ctypes.byref(camera),x,y,ctypes.byref(point))==1
                assert (point.x,point.y)==expected(x,y,**config), (x,y,config,point.x,point.y)
        for x,y in ((280,0),(65535,0),(0,len(scale)),(0,255)):
            point.x,point.y=0x1234,0x56
            assert not project(ctypes.byref(camera),x,y,ctypes.byref(point))
            assert (point.x,point.y)==(0x1234,0x56)
        assert not project(None,0,0,ctypes.byref(point))
        assert not project(ctypes.byref(camera),0,0,None)
        b[0]=65535
        assert not project(ctypes.byref(camera),0,0,ctypes.byref(point))
        b[0]=0;c[0]=192
        assert not project(ctypes.byref(camera),0,0,ctypes.byref(point))
        camera.scale=None
        assert not project(ctypes.byref(camera),0,0,ctypes.byref(point))
    for config in (dict(rows=0),dict(rows=193),dict(focal=0),dict(focal=-1),
                   dict(center=280),dict(horizon=191),dict(bottom=192)):
        try: tool.tables(**config)
        except ValueError: pass
        else: raise AssertionError(config)
    print('Host: 112280 projections, varied cameras, invalid inputs and unchanged outputs OK')


def target_check(work, tool, iie):
    (work/'camera.h').write_text(tool.generate())
    fixture=work/'fixture.c'
    fixture.write_text('''#include "perspective.h"
#include "camera.h"
void done(void);
static const unsigned xs[]={0,1,140,254,255,256,257,279};
a2_projected_t points[192*8];
unsigned char checks[12];
int main(void) {
    unsigned i=0; unsigned char x,y;
    a2_projected_t guard;
    a2_perspective_t invalid;
    for(y=0;y<192;++y) for(x=0;x<8;++x) {
        if(!a2_perspective_project(&camera,xs[x],y,&points[i++])) done();
    }
    guard.x=0x1234;guard.y=0x56;
    checks[0]=!a2_perspective_project(&camera,280,0,&guard);
    checks[1]=!a2_perspective_project(&camera,65535,0,&guard);
    checks[2]=!a2_perspective_project(&camera,0,192,&guard);
    checks[3]=!a2_perspective_project(0,0,0,&guard);
    checks[4]=!a2_perspective_project(&camera,0,0,0);
    invalid=camera;invalid.scale=0;
    checks[5]=!a2_perspective_project(&invalid,0,0,&guard);
    invalid=camera;invalid.rows=193;
    checks[6]=!a2_perspective_project(&invalid,0,0,&guard);
    invalid.rows=0;
    checks[7]=!a2_perspective_project(&invalid,0,0,&guard);
    invalid=camera;invalid.shift=0;
    checks[8]=!a2_perspective_project(&invalid,0,0,&guard);
    invalid=camera;invalid.screen_y=0;
    checks[9]=!a2_perspective_project(&invalid,0,0,&guard);
    checks[10]=guard.x==0x1234 && guard.y==0x56;
    checks[11]=sizeof(a2_projected_t)==3;
    done();return 0;
}
''')
    marker=work/'marker.s'
    marker.write_text('.export _done\n.code\n_done: rts\n')
    objects=[]
    for source in (DEV/'cc65/crt0_apple2.s',fixture,marker,
                   DEV/'lib/perspective/perspective.c'):
        obj=work/(source.stem+'.o')
        compile_source(source,obj,['-t','none','-Oirs','-I',work,'-I',DEV/'lib/perspective'])
        objects.append(obj)
    binary,labels=work/'perspective.bin',work/'perspective.lbl'
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',labels,'-o',binary,*objects])
    disk=a2test.build_disk(work,'PROJECT',binary); labels=a2test.labels(labels)
    result=a2test.run(disk,[labels.until('_done',3000),labels.peek('_checks',12),
                            labels.peek('_points',192*8*3)],iie=iie)
    assert result.mem(labels['_checks'],12)==bytes([1]*12), result.out
    data=result.mem(labels['_points'],192*8*3)
    wanted=bytearray()
    for y in range(192):
        for x in (0,1,140,254,255,256,257,279):
            px,py=expected(x,y);wanted+=bytes((px&255,px>>8,py))
    assert data==wanted, 'target projection differs from rational camera model'
    print(f'{"65C02" if iie else "6502"}: 1536 projections across all depths, '
          'X=255/256/279, identity row and 12 refusal/ABI checks OK')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    tool=load_tool('perspective_tables',DEV/'tools/perspective.py')
    run(['make','-s','-C',DEV/'tools'/('a2shot' if args.iie else 'a2run')])
    with tempfile.TemporaryDirectory(prefix='pom2-perspective-') as temp:
        work=Path(temp)
        host_check(work,tool)
        target_check(work,tool,args.iie)


if __name__=='__main__':
    main()
