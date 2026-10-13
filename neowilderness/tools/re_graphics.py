#!/usr/bin/env python3
"""Extract original sprites from local Journey SMALLDOS data, into ignored build/.

SURV3D $1CBF/$1CDF chooses the sectors; $1D8A-$1E2E decodes each column.
No original bitmap data is embedded in this script or checked into source.
"""
import argparse, hashlib, json, struct, zlib
from pathlib import Path
from smalldos import Disk

HERE=Path(__file__).resolve().parents[1]
# Sierra Nevada animal set, SURV3D $1CF5; wreck selected by $0D84=$87.
SPRITES={'cabin':(0x16,0x04,5), 'wreck':(0x00,0x00,10), 'bear':(0x1C,0x0C,5),
         'cougar':(0x1D,0x00,5), 'rattlesnake':(0x1D,0x03,5),
         'grizzly_bc':(0x1C,0x00,5), 'wolf_bc':(0x1C,0x03,5), 'moose_bc':(0x1C,0x08,5)}
COLOURS=((0,0,0),(208,64,255),(48,192,48),(255,255,255))


def decode(data):
    """Return columns x 192 original colour codes, -1 = transparent.

One column represents two HGR pixels. The first byte is column count,
then count+1 relative LE16 offsets. Each column begins with its bottom-up
Y coordinate; subsequent bytes pack four colour codes, least bits first.
00 followed by 00 skips a pair; 00 followed by a nonzero code paints black.
Other codes paint magenta/green/white. The end pointer is exclusive.
"""
    width=data[0]
    header=1+2*(width+1)
    if not width or header>len(data): raise ValueError('Invalid sprite header')
    offsets=[int.from_bytes(data[1+2*x:3+2*x],'little') for x in range(width+1)]
    if offsets[0]<header or any(not a<b<=len(data) for a,b in zip(offsets,offsets[1:])):
        raise ValueError('Invalid sprite column offsets')
    image=[[-1]*width for _ in range(192)]
    for x,(start,end) in enumerate(zip(offsets,offsets[1:])):
        y=data[start]
        codes=[(b>>shift)&3 for b in data[start+1:end] for shift in (0,2,4,6)]
        k=0
        while k<len(codes):
            colour=codes[k];k+=1
            if colour==0:
                if k==len(codes): break
                escaped=codes[k];k+=1
                if escaped==0: y=(y+1)&255;continue
            if y<192: image[191-y][x]=colour
            y=(y+1)&255
    return image,offsets[-1]


def png(path,width,height,rgba):
    def chunk(kind,payload):
        return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
    rows=b''.join(b'\0'+rgba[y*width*4:(y+1)*width*4] for y in range(height))
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))
                          +chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b''))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disk',type=Path,default=HERE/'build/JOURNEY.dsk')
    parser.add_argument('--out',type=Path,default=HERE/'build/original_graphics')
    args=parser.parse_args()
    raw=args.disk.read_bytes()
    if len(raw)!=35*16*256: raise ValueError('Expected a 35-track DOS-order DSK')
    disk=Disk(raw);disk.flip=True # Journey has raw assets, no catalogue signature
    args.out.mkdir(parents=True,exist_ok=True)
    manifest={'source':str(args.disk),'sha256':hashlib.sha256(raw).hexdigest(),'sprites':{}}
    for name,(track,sector,count) in SPRITES.items():
        data=disk.run(track,sector,count)
        image,end=decode(data)
        (args.out/f'{name}.bin').write_bytes(data[:end])
        active=[y for y,row in enumerate(image) if any(v>=0 for v in row)]
        top,bottom=min(active),max(active)+1
        rgba=bytearray()
        for row in image[top:bottom]:
            for v in row:
                pixel=bytes((*COLOURS[v],255)) if v>=0 else b'\0\0\0\0'
                rgba+=pixel*2
        width=2*len(image[0]);height=bottom-top
        png(args.out/f'{name}.png',width,height,rgba)
        manifest['sprites'][name]={'track':track,'sector':sector,'sectors':count,
            'columns':width//2,'width':width,'height':height,'original_top_row':top,
            'encoded_bytes':end,'sha256':hashlib.sha256(data).hexdigest(),
            'encoded_sha256':hashlib.sha256(data[:end]).hexdigest()}
        print(f'{name}: T{track:02X}/S{sector:X}, {count} sectors, {width}x{height} -> {args.out/name}.png')
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__': main()
