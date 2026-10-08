#!/usr/bin/env python3
"""PNG/PPM -> native Apple II framebuffers and seven-phase masked sprites.

Only Python's standard library. PNG: non-interlaced, 8-bit gray/RGB/index/RGBA.
HGR output is monochrome (bit 7 clear); DHGR uses the 16 LORES color IDs.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import zlib
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hgr_tables import hgr_offset

PALETTE = [(0,0,0),(157,9,102),(42,42,165),(199,52,255),
           (0,118,44),(128,128,128),(0,157,255),(170,170,255),
           (128,80,0),(255,106,0),(128,128,128),(255,137,229),
           (0,208,55),(255,244,0),(77,255,191),(255,255,255)]


def png_write(path, w, h, pixels):
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind+body))
    raw = b''.join(b'\0'+bytes(v for px in pixels[y*w:(y+1)*w] for v in px) for y in range(h))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB',w,h,8,6,0,0,0)) +
                     chunk(b'IDAT',zlib.compress(raw)) + chunk(b'IEND',b''))


def load(path):
    data = path.read_bytes()
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        # P3/P6 with comments, maximum sample value 255.
        tokens = list(re.finditer(rb'#[^\n]*|\S+', data))
        tokens = [t for t in tokens if not t[0].startswith(b'#')]
        if len(tokens) < 4 or tokens[0][0] not in (b'P3',b'P6'):
            raise ValueError('expected PNG or PPM (P3/P6)')
        w,h,maxval = (int(t[0]) for t in tokens[1:4])
        if maxval != 255: raise ValueError('PPM max value must be 255')
        if tokens[0][0] == b'P3': raw = bytes(int(t[0]) for t in tokens[4:])
        else:
            start = tokens[3].end()
            if data[start:start+2] == b'\r\n': start += 2
            else: start += 1
            raw = data[start:]
        if len(raw) != w*h*3: raise ValueError('invalid PPM sample count')
        return w,h,[tuple(raw[i:i+3])+(255,) for i in range(0,len(raw),3)]
    pos=8; compressed=bytearray(); palette=[]; alpha=b''
    while pos < len(data):
        size, = struct.unpack_from('>I',data,pos); kind=data[pos+4:pos+8]; body=data[pos+8:pos+8+size]
        crc, = struct.unpack_from('>I',data,pos+8+size)
        if zlib.crc32(kind+body) != crc: raise ValueError('PNG CRC mismatch')
        pos += 12+size
        if kind==b'IHDR': w,h,depth,typ,comp,filt,inter=struct.unpack('>IIBBBBB',body)
        elif kind==b'PLTE': palette=[tuple(body[i:i+3]) for i in range(0,len(body),3)]
        elif kind==b'tRNS': alpha=body
        elif kind==b'IDAT': compressed.extend(body)
        elif kind==b'IEND': break
    if depth!=8 or inter or comp or filt or typ not in (0,2,3,4,6):
        raise ValueError('PNG must be non-interlaced with 8-bit gray/RGB/index/RGBA samples')
    bpp={0:1,2:3,3:1,4:2,6:4}[typ]; stride=w*bpp
    raw=zlib.decompress(compressed)
    if len(raw)!=h*(stride+1): raise ValueError('invalid PNG sample count')
    rows=[]; previous=bytearray(stride)
    for y in range(h):
        f=raw[y*(stride+1)]; row=bytearray(raw[y*(stride+1)+1:(y+1)*(stride+1)])
        if f>4: raise ValueError('invalid PNG filter')
        for i in range(stride):
            a=row[i-bpp] if i>=bpp else 0; b=previous[i]; c=previous[i-bpp] if i>=bpp else 0
            estimate=a+b-c
            pa,pb,pc=abs(estimate-a),abs(estimate-b),abs(estimate-c)
            predictor=(0,a,b,(a+b)//2,a if pa<=pb and pa<=pc else b if pb<=pc else c)[f]
            row[i]=(row[i]+predictor)&255
        rows.extend(row); previous=row
    pixels=[]
    for i in range(0,len(rows),bpp):
        px=rows[i:i+bpp]
        if typ==6: rgba=tuple(px)
        elif typ==2:
            transparent = len(alpha)==6 and tuple(px)==struct.unpack('>HHH',alpha)
            rgba=tuple(px)+(0 if transparent else 255,)
        elif typ==3: rgba=palette[px[0]]+(alpha[px[0]] if px[0]<len(alpha) else 255,)
        else:
            transparent=typ==0 and len(alpha)==2 and px[0]==struct.unpack('>H',alpha)[0]
            rgba=(px[0],)*3+(px[1] if typ==4 else 0 if transparent else 255,)
        pixels.append(rgba)
    return w,h,pixels


def quantize(pixels, mode):
    if mode=='hgr': return [int(sum(px[:3])>=384) for px in pixels]
    return [min(range(16),key=lambda c:sum((a-b)**2 for a,b in zip(px,PALETTE[c]))) for px in pixels]


def banks(w,h,colors,pixels,mode):
    scale=1 if mode=='hgr' else 4
    stride=(w*scale+12)//7
    bits=bytearray(7*stride*h); masks=bytearray([255])*len(bits)
    for phase in range(7):
        for y in range(h):
            for x in range(w):
                if pixels[y*w+x][3]<128: continue
                color=colors[y*w+x]
                nibble=((color>>1)|(color<<3))&15 if scale==4 else color
                for k in range(scale):
                    pos=phase+x*scale+k; byte,shift=divmod(pos,7)
                    idx=phase*stride*h+y*stride+byte
                    masks[idx]&=~(1<<shift)
                    bits[idx]|=((nibble>>k)&1)<<shift
    return stride,bits,masks


def framebuffer(w,h,colors,mode):
    scale=1 if mode=='hgr' else 4
    result=bytearray(8192*(1 if mode=='hgr' else 2))
    for y in range(h):
        row=hgr_offset(y)
        for x in range(w):
            c=colors[y*w+x]; value=((c>>1)|(c<<3))&15 if scale==4 else c
            for k in range(scale):
                byte,bit=divmod(x*scale+k,7)
                # DHGR file = main 8K then auxiliary 8K, both page-relative.
                addr=row+byte if scale==1 else (1-byte%2)*8192+row+byte//2
                result[addr]|=((value>>k)&1)<<bit
    return result


def c_array(name,data):
    rows=['    '+','.join('0x%02X'%v for v in data[i:i+16])+',' for i in range(0,len(data),16)]
    return 'static const unsigned char '+name+'['+str(len(data))+'] = {\n'+'\n'.join(rows)+'\n};\n'


def convert(source,out,mode,kind,name):
    w,h,pixels=load(source)
    limit=280 if mode=='hgr' else 140
    if not (0<w<=limit and 0<h<=192): raise ValueError(f'{mode} input must fit {limit}x192')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name): raise ValueError('invalid C symbol')
    colors=quantize(pixels,mode)
    if kind=='frame': colors=[c if px[3]>=128 else 0 for c,px in zip(colors,pixels)]
    if kind=='sprite' and 7*((w*(1 if mode=='hgr' else 4)+12)//7)*h>65535:
        raise ValueError('sprite phase bank exceeds 16-bit address space; split the image')
    out.parent.mkdir(parents=True,exist_ok=True)
    preview=[((255,255,255) if c else (0,0,0))+(px[3],) if mode=='hgr' else PALETTE[c]+(px[3],) for c,px in zip(colors,pixels)]
    png_write(out.with_suffix('.png'),w,h,preview)
    stats=dict(mode=mode,kind=kind,width=w,height=h)
    if kind=='sprite':
        stride,data,mask=banks(w,h,colors,pixels,mode)
        out.with_suffix('.h').write_text('/* Generated by dev/tools/assets/convert.py */\n'+
            f'#define {name.upper()}_WIDTH {w}u\n#define {name.upper()}_HEIGHT {h}u\n#define {name.upper()}_STRIDE {stride}u\n'+
            c_array(name+'_data',data)+c_array(name+'_mask',mask))
        out.with_suffix('.bin').write_bytes(data+mask)
        stats.update(stride=stride,phases=7,data_bytes=len(data),mask_bytes=len(mask),save_under_bytes=stride*h)
    else:
        data=framebuffer(w,h,colors,mode)
        out.with_suffix('.bin').write_bytes(data)
        stats.update(data_bytes=len(data),mask_bytes=0)
    stats['rom_bytes']=stats['data_bytes']+stats['mask_bytes']
    out.with_suffix('.json').write_text(json.dumps(stats,indent=2)+'\n')
    return stats


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input',type=Path); ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--mode',choices=['hgr','dhgr'],required=True)
    ap.add_argument('--kind',choices=['frame','sprite'],default='sprite')
    ap.add_argument('--name',default='sprite')
    args=ap.parse_args()
    try: stats=convert(args.input,args.out,args.mode,args.kind,args.name)
    except (ValueError,IndexError,struct.error,zlib.error) as exc: ap.error(str(exc))
    print(json.dumps(stats,indent=2))

if __name__=='__main__': main()
