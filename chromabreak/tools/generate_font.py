#!/usr/bin/env python3
"""Build the shared compact DHGR font tables for relocation to $0800."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
game=root/'chromabreak'
with tempfile.TemporaryDirectory(prefix='chroma-font-') as directory:
    obj=Path(directory)/'font.o'
    subprocess.run(['ca65','-I',str(root/'dev/lib/hgrc'),'-o',str(obj),str(game/'src/small_font.s')],check=True)
    subprocess.run(['ld65','-C',str(game/'src/small_font.cfg'),'-o',str(game/'src/font.bin'),str(obj)],check=True)
