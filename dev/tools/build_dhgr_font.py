#!/usr/bin/env python3
"""Build relocated DHGR compact-font data from the library's checked schema."""
import argparse
from pathlib import Path
import subprocess
import tempfile

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--base',type=lambda v:int(v,0),default=0x0800)
    parser.add_argument('--capacity',type=lambda v:int(v,0),default=2048)
    parser.add_argument('--ca65',default='ca65')
    parser.add_argument('--ld65',default='ld65')
    args=parser.parse_args()
    if args.base<0 or args.capacity<=0 or args.base+args.capacity>65536:parser.error('font image must fit in 16-bit memory')
    lib=Path(__file__).resolve().parents[1]/'lib/hgrc'
    with tempfile.TemporaryDirectory(prefix='dhgr-font-') as directory:
        root=Path(directory);obj=root/'font.o';cfg=root/'font.cfg';binary=root/'font.bin'
        cfg.write_text(f'MEMORY {{ FONT: start=${args.base:04X}, size=${args.capacity:04X}, type=ro, file=%O, fill=yes; }}\nSEGMENTS {{ RODATA: load=FONT, type=ro; }}\n')
        subprocess.run([args.ca65,'-I',str(lib),'-o',str(obj),str(lib/'dhgr_small_payload.s')],check=True)
        subprocess.run([args.ld65,'-C',str(cfg),'-o',str(binary),str(obj)],check=True)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes(binary.read_bytes())
if __name__=='__main__':main()
