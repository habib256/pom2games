#!/usr/bin/env python3
"""Check converter layouts independently, PNG filters and transparent masks."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import zlib
import random
import subprocess
spec=importlib.util.spec_from_file_location('assets',Path(__file__).resolve().parents[1]/'tools/assets/convert.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
img=a._img   # dev/tools/apple2img.py, loaded by convert.py


def image_helpers(work):
    """apple2img: PNG round trips, HGR/DHGR known bytes, preshift7 by hand."""
    rgba=[[(x*40,y*60,x^y,255-x) for x in range(5)] for y in range(3)]
    for mode,rows in (('rgba',rgba),('rgb',rgba),('gray',[[x*50 for x in range(5)]]*3),
                      ('pal',[[x%3 for x in range(5)]]*3)):
        pal=[(1,2,3),(200,100,0),(9,9,250)]
        img.png_write(work/'rt.png',rows,mode=mode,palette=pal)
        w,h,back=img.png_read(work/'rt.png')
        want={'rgba':lambda p:p,'rgb':lambda p:p[:3]+(255,),'gray':lambda v:(v,v,v,255),
              'pal':lambda i:pal[i]+(255,)}[mode]
        assert (w,h)==(5,3) and back==[[want(p) for p in r] for r in rows],mode
    img.png_write(work/'big.png',[b'\x01\x02\x03\x04\x05\x06'],scale=(2,3))
    assert img.png_read(work/'big.png')==(4,3,[[(1,2,3,255)]*2+[(4,5,6,255)]*2]*3)
    flat=[p for r in rgba for p in r]
    a.png_write(work/'legacy.png',5,3,flat)
    img.png_write(work/'new.png',rgba,mode='rgba',level=-1)
    assert (work/'legacy.png').read_bytes()==(work/'new.png').read_bytes()
    # HGR: one byte at column 0 of line 0 -> its 7 dots.
    V,G,B,O,W,K=(255,68,253),(20,245,60),(20,207,253),(255,106,60),(255,255,255),(0,0,0)
    for byte,dots in ((0x01,[V,K]),(0x81,[B,K]),(0x02,[K,G]),(0x82,[K,O]),(0x03,[W,W,K]),
                      (0x05,[V,V,V,K]),(0x85,[B,B,B,K]),(0x0A,[K,G,G,G,K])):
        page=bytearray(8192);page[0]=byte
        line=img.hgr_to_rgb(page)[0]
        assert line[:len(dots)]==dots and line[len(dots):]==[K]*(280-len(dots)),hex(byte)
    page=bytearray(8192);page[img.hgr_offset(77)+3]=0x85
    assert img.hgr_to_rgb(page,mono=True)[77][21:28]==[W,K,W,K,K,K,K]
    mono=[[(x*y+x)%3==0 for x in range(280)] for y in range(192)]
    page=img.hgr_from_mono(mono)
    assert [[p==W for p in r] for r in img.hgr_to_rgb(page,mono=True)]==mono
    assert all(page[img.hgr_offset(y)+c]<0x80 for y in range(192) for c in range(40))
    assert img.hgr_from_mono([[1]],hibits=1)[0:41]==bytes([0x81])+bytes([0x80]*39)+bytes(1)
    hib=[[c%2 for c in range(40)]]
    assert img.hgr_from_mono([[0]*280],hibits=hib)[0:4]==bytes([0,0x80,0,0x80])
    # DHGR: LORES colour 1 (magenta) = dots 0001 rotated -> aux bit 3; 15 -> 4 dots.
    main,aux=img.dhgr_from_colors([[1,15]])
    assert aux[0]==0x08|0x70 and main[0]==0x01 and not any(aux[1:]) and not any(main[1:])
    colours=[[(x+y)%16 for x in range(140)] for y in range(192)]
    main,aux=img.dhgr_from_colors(colours)
    assert img.dhgr_to_rgb(main,aux)==[[img.PALETTE[c] for c in r] for r in colours]
    assert a.framebuffer(140,1,colours[0],'dhgr')==b''.join(img.dhgr_from_colors(colours[:1]))
    # preshift7: dots 0 and 2 (0b101), 3 wide. Phase 6 -> dots 6, 8: $40, $02.
    ph=img.preshift7([0b101],3)
    assert len(ph)==7 and ph[0]==[[0x05,0x00]] and ph[1]==[[0x0A,0x00]] and ph[6]==[[0x40,0x02]]
    assert img.preshift7([[1,0,1]],3)==ph
    ph,mk=img.preshift7([0b101],3,palette=1,mask=True)
    assert ph[6]==[[0xC0,0x82]] and mk[6]==[[0xBF,0xFD]] and mk[0]==[[0xFA,0xFF]]
    # step=2 (2-dot cells): phases shift 0,2,4,6,1,3,5; fit keeps one byte uncut.
    ph=img.preshift7([0b11],2,step=2)
    assert [p[0] for p in ph]==[[3,0],[12,0],[48,0],[64,1],[6,0],[24,0],[96,0]]
    assert [p[0][0] for p in img.preshift7([0b101],3,nbytes=1,fit=True)]==[5,10,20,40,80,80,80]
    assert img.preshift7([0xFF],7,nbytes=2)[1]==[[0x7E,0x01]]   # width masks the row
    assert img.asm_bytes([1,255],per_line=8)=='        .byte $01,$FF\n'




def main():
    with tempfile.TemporaryDirectory(prefix='apple2-assets-') as d:
        work=Path(d);image_helpers(work);pixels=[a.PALETTE[c]+(255,) for c in range(16)]
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
        compressor=work/'fhpack'
        source=Path(__file__).resolve().parent/'techniques/upstream/fhpack/fhpack.cpp'
        subprocess.run(['c++','-O2','-o',str(compressor),str(source)],check=True)
        blank=bytes(8192)
        packed,encoding=a.compress_frame(blank,compressor)
        assert encoding=='lz4fh' and len(packed)<len(blank)
        noise=random.Random(6502).randbytes(8192)
        packed,encoding=a.compress_frame(noise,compressor)
        assert encoding=='raw' and packed==noise, 'compression growth must select raw'
        stats=a.convert(work/'input.png',work/'compressed','hgr','frame','screen',compressor)
        assert stats['load_encoding']=='lz4fh' and stats['load_bytes']<8192
        assert (work/stats['load_file']).stat().st_size==stats['load_bytes']
        assert (work/'compressed.bin').stat().st_size==8192
        try: a.convert(work/'input.png',work/'invalid','dhgr','frame','screen',compressor)
        except ValueError: pass
        else: raise AssertionError('DHGR compression accepted by 8-KB-only decoder')
    print('Assets: apple2img helpers, PNG/PPM, 5 PNG filters, HGR/DHGR frames, 7 phases and transparent masks passed.')

if __name__=='__main__':main()
