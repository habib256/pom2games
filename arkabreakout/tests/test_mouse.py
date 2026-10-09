#!/usr/bin/env python3
"""Optional Apple II+ / AppleMouse II integration against the POM2 core."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pom2-src',type=Path,default=ROOT.parent/'pom2')
    a=ap.parse_args();src=a.pom2_src.resolve()
    library=src/'build/libpom2_core_test.a'
    if not library.exists():raise SystemExit(f'Build POM2 core test library first: {library}')
    libs=['-framework','CoreAudio','-framework','AudioToolbox','-framework','AudioUnit'] if sys.platform=='darwin' else ['-pthread']
    libs+=subprocess.check_output(['pkg-config','--libs','slirp'],text=True).split()+['-lz']
    exe=ROOT/'arkabreakout/build/mouse-test'
    subprocess.run(['c++','-std=c++17','-O2','-I',str(src/'src'),'-I',str(src/'include'),'-I',str(src/'build/generated'),str(Path(__file__).with_name('mouse.cpp')),str(library),*libs,'-o',str(exe)],check=True)
    with tempfile.TemporaryDirectory(prefix='arka-mouse-') as tmp:
        disk=Path(tmp)/'GAME.dsk'
        for variant in ('applewin','mame'):
            for action in ([],['reset']):
                shutil.copyfile(ROOT/'dist/ARKABREAKOUT.dsk',disk)
                subprocess.run([str(exe),str(src/'roms'),str(disk),str(ROOT/'arkabreakout/build/game.lbl'),variant,*action],check=True)
if __name__=='__main__':main()
