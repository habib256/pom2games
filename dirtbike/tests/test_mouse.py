#!/usr/bin/env python3
"""Optional: DIRTBIKE with real AppleMouse firmware (POM2 core), //e cards
(AppleWin and MCU ROMs, slot 4) and the //c's built-in mouse (16 / 32 KB).

    python3 tests/test_mouse.py --pom2-src ../../pom2      (make test-mouse)
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

GAME = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--pom2-src', type=Path, required=True)
args = ap.parse_args()
src = args.pom2_src.resolve()
lib = src / 'build/libpom2_core_test.a'
if not lib.exists():
    raise SystemExit(f'Build the POM2 core test library first: {lib}')
libs = ['-framework', 'CoreAudio', '-framework', 'AudioToolbox', '-framework', 'AudioUnit'] if sys.platform == 'darwin' else ['-pthread']
libs += subprocess.check_output(['pkg-config', '--libs', 'slirp'], text=True).split() + ['-lz']
exe = GAME / 'build/mouse_probe'
subprocess.run(['c++', '-std=c++17', '-O2', '-I', str(src / 'src'), '-I', str(src / 'include'),
                '-I', str(src / 'build/generated'), str(GAME / 'tests/mouse_probe.cpp'), str(lib), *libs, '-o', str(exe)],
               check=True)
bad = 0
with tempfile.TemporaryDirectory(prefix='dirtbike-mouse-') as tmp:
    for variant in ('applewin', 'mame', 'iic16', 'iic32'):
        disk = Path(tmp) / 'DIRTBIKE.dsk'
        shutil.copyfile(GAME.parent / 'dist/DIRTBIKE.dsk', disk)
        bad += subprocess.run([str(exe), str(src / 'roms'), str(disk), str(GAME / 'build/dirtbike.lbl'), variant]).returncode != 0
if bad:
    sys.exit('mouse: failures')
