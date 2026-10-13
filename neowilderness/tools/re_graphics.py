#!/usr/bin/env python3
"""Extract original sprites from local Journey SMALLDOS data, into ignored build/.

SURV3D $1CBF/$1CDF chooses the sectors; $1D8A-$1E2E decodes each column.
No original bitmap data is embedded in this script or checked into source.
"""
import argparse, hashlib, json, struct, sys, zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from smalldos import Disk  # noqa: E402

HERE=Path(__file__).resolve().parents[1]
# Sierra Nevada animal set, SURV3D $1CF5; wreck selected by $0D84=$87.
# The first eight entries keep their historical sector counts (the manifest
# hashes the whole run). The other nineteen use the exact run up to the next
# block: the 27 blocks are contiguous on Journey tracks $00-$01, $16-$17 and
# $1C-$1F. Names follow the MS-DOS .CIM files: same order as the global
# animal id of the region records, same column count within three columns.
SPRITES={'cabin':(0x16,0x04,5), 'wreck':(0x00,0x00,10), 'bear':(0x1C,0x0C,5),
         'cougar':(0x1D,0x00,5), 'rattlesnake':(0x1D,0x03,5),
         'grizzly_bc':(0x1C,0x00,5), 'wolf_bc':(0x1C,0x03,5), 'moose_bc':(0x1C,0x08,5),
         'tiger':(0x1D,0x05,4), 'elephant':(0x1D,0x09,4), 'cobra':(0x1D,0x0D,3),
         'python':(0x1E,0x00,2), 'dani':(0x1E,0x02,4), 'adder':(0x1E,0x06,3),
         'crocodile':(0x1E,0x09,4), 'puma':(0x1E,0x0D,3), 'jaguar':(0x1F,0x00,5),
         'ferdelance':(0x1F,0x05,2), 'anaconda':(0x1F,0x07,3), 'cat':(0x1F,0x0A,4),
         'tent':(0x16,0x00,4), 'igloo':(0x16,0x09,4), 'trench':(0x16,0x0D,2),
         'log':(0x16,0x0F,5), 'rock':(0x17,0x04,5), 'lost_city':(0x00,0x08,10),
         'outpost':(0x01,0x02,9)}
# Matching MS-DOS file (cross-check of the column count only).
DOS_NAMES={'cabin':'HUT', 'wreck':'AIRPLANE', 'bear':'BLCKBEAR', 'cougar':'COUGAR',
           'rattlesnake':'RATTLER', 'grizzly_bc':'GRIZZLY', 'wolf_bc':'WOLF',
           'moose_bc':'MOOSE', 'tiger':'TIGER', 'elephant':'ELEPHANT', 'cobra':'COBRA',
           'python':'PYTHON', 'dani':'DANI', 'adder':'ADDER', 'crocodile':'CROC',
           'puma':'PUMA', 'jaguar':'JAGUAR', 'ferdelance':'FERLANCE',
           'anaconda':'ANACONDA', 'cat':'CAT', 'tent':'TENT', 'igloo':'IGLOO',
           'trench':'TRENCH', 'log':'LOG', 'rock':'ROCK', 'lost_city':'LOSTCITY',
           'outpost':'OUTPOST'}
KIND={'cabin':'site', 'wreck':'site', 'outpost':'site', 'lost_city':'site',
      'tent':'shelter', 'igloo':'shelter', 'trench':'shelter', 'log':'shelter',
      'rock':'shelter'}
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
        if end>len(data): raise ValueError(f'{name}: {end} bytes exceed {count} sectors')
        print(f'{name}: T{track:02X}/S{sector:X}, {count} sectors, {width}x{height} -> {args.out/name}.png')
    dos=dos_columns()
    if dos:
        for name,entry in manifest['sprites'].items():
            entry['dos_columns']=dos[DOS_NAMES[name]]
            if abs(entry['columns']-entry['dos_columns'])>3:
                raise ValueError(f"{name}: {entry['columns']} columns, DOS {DOS_NAMES[name]} has {entry['dos_columns']}")
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (args.out/'sheet.html').write_text(sheet(manifest))


def dos_columns():
    """Column count (first byte) of each MS-DOS .CIM, if the zip is present."""
    import zipfile
    found=sorted((HERE/'original/extras').glob('*MS-DOS*.zip'))
    if not found: return None
    with zipfile.ZipFile(found[0]) as z:
        return {name:z.read(f'WILD/{name}.CIM')[0] for name in DOS_NAMES.values()}


def sheet(manifest):
    """Contact sheet of the decoded PNGs, for a visual check (build/ only)."""
    cards=[]
    for name,e in manifest['sprites'].items():
        dos=f" &middot; DOS {DOS_NAMES[name]}.CIM {e['dos_columns']} col." if 'dos_columns' in e else ''
        cards.append(f'<figure><div class="img"><img src="{name}.png" width="{2*e["width"]}" '
                     f'height="{2*e["height"]}" alt="{name}"></div><figcaption><b>{name}</b> '
                     f'<span>{KIND.get(name,"animal")}</span><br>T{e["track"]:02X}/S{e["sector"]:X}'
                     f' &middot; {e["sectors"]} sect. &middot; {e["encoded_bytes"]} octets<br>'
                     f'{e["width"]}&times;{e["height"]} px ({e["columns"]} col.){dos}</figcaption></figure>')
    return ('<!doctype html><html lang="fr"><meta charset="utf-8"><title>Sprites Journey</title>'
            '<style>body{background:#202428;color:#ddd;font:14px system-ui;margin:16px}'
            'main{display:flex;flex-wrap:wrap;gap:12px}figure{margin:0;background:#2c3238;padding:8px;'
            'border-radius:6px}div.img{background:#6a7a8a;display:flex;align-items:end;justify-content:center;'
            'min-height:120px}img{image-rendering:pixelated}span{color:#9ab}</style>'
            f'<h1>Sprites originaux de la face Journey ({len(cards)})</h1>'
            '<p>Paires de pixels HGR mises à l\'échelle 2, fond gris = transparence.</p>'
            '<main>'+''.join(cards)+'</main></html>\n')


if __name__=='__main__': main()
