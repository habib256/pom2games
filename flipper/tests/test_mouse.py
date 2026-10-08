#!/usr/bin/env python3
"""Optional POM2 integration with real AppleMouse firmware on Apple II+ and native //c ROMs."""
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
                '-I', str(src / 'build/generated'), str(GAME / 'tests/mouse_probe.cpp'), str(lib), *libs, '-o', str(exe)], check=True)
with tempfile.TemporaryDirectory(prefix='flipper-mouse-') as tmp:
    for variant in ('applewin', 'mame', 'iic16', 'iic32'):
        disk = Path(tmp) / 'FLIPPER.dsk'
        shutil.copyfile(GAME.parent / 'dist/FLIPPER.dsk', disk)
        subprocess.run([str(exe), str(src / 'roms'), str(disk), str(GAME / 'build'), variant], check=True)
