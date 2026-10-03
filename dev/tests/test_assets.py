#!/usr/bin/env python3
"""Check converter layouts independently, PNG filters and transparent masks."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import zlib
spec=importlib.util.spec_from_file_location('assets',Path(__file__).resolve().parents[1]/'tools/assets/convert.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


def main():
    with tempfile.TemporaryDirectory(prefix='apple2-assets-') as d:
        work=Path(d);pixels=[a.PALETTE[c]+(255,) for c in range(16)]
        pixels[-1]=pixels[-1][:3]+(0,)
        a.png_write(work/'input.png',8,2,pixels)
        assert a.load(work/'input.png')==(8,2,pixels)
        for mode in ('hgr','dhgr'):
            stats=a.convert(work/'input.png',work/mode,mode,'sprite','sample')
            data=(work/mode).with_suffix('.bin').read_bytes();size=stats['data_bytes'];bits,mask=data[:size],data[size:]
            colors=a.quantize(pixels,mode);scale=1 if mode=='hgr' else 4
            stride=stats['stride']
            for phase in range(7):
                for y in range(2):
                    for bit in range(stride*7):
                        index=phase*stride*2+y*stride+bit//7
                        logical=bit-phase
                        inside=0<=logical<8*scale
                        px=y*8+logical//scale if inside else 0
                        opaque=inside and pixels[px][3]>=128
                        assert bool(mask[index]&(1<<(bit%7)))==(not opaque)
                        c=colors[px];value=((c>>1)|(c<<3))&15 if scale==4 else c
                        expected=opaque and bool(value&(1<<(logical%scale)))
                        assert bool(bits[index]&(1<<(bit%7)))==expected
            frame=a.framebuffer(8,2,colors,mode)
            assert len(frame)==8192*(1 if mode=='hgr' else 2)
            for y in range(2):
                row=(y%8)*1024
                for x in range(8):
                    c=colors[y*8+x];value=((c>>1)|(c<<3))&15 if scale==4 else c
                    for k in range(scale):
                        byte,bit=divmod(x*scale+k,7)
                        addr=row+byte if scale==1 else (1-byte%2)*8192+row+byte//2
                        assert ((frame[addr]>>bit)&1)==((value>>k)&1)
        # P6: first sample is whitespace; binary parser must retain it.
        ppm=work/'input.ppm';ppm.write_bytes(b'P6\n# example\n1 1\n255\n'+bytes([10,32,255]))
        assert a.load(ppm)[2]==[(10,32,255,255)]
        # Exercise all five PNG filters, including Paeth, with known samples.
        rgba=[(x*17,y*35,(x+y)*13,255) for y in range(5) for x in range(4)]
        rows=[];previous=bytes(16)
        for y in range(5):
            raw=bytes(v for px in rgba[y*4:y*4+4] for v in px);filtered=[]
            for i,v in enumerate(raw):
                left=raw[i-4] if i>=4 else 0; up=previous[i];corner=previous[i-4] if i>=4 else 0
                candidates=[left,up,corner];estimate=left+up-corner
                paeth=min(enumerate(candidates),key=lambda pair:(abs(estimate-pair[1]),pair[0]))[1]
                predictor=[0,left,up,(left+up)//2,paeth][y]
                filtered.append((v-predictor)&255)
            rows.append(bytes([y])+bytes(filtered));previous=raw
        def chunk(kind,body):return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body))
        filtered=work/'filtered.png'
        filtered.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',4,5,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b''))
        assert a.load(filtered)==(4,5,rgba)
    print('Assets: PNG/PPM, 5 PNG filters, HGR/DHGR frames, 7 phases and transparent masks passed.')

if __name__=='__main__':main()
