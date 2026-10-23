#!/usr/bin/env python3
"""Optional: WARGALAGA II's clock on POM2's //c (ROM 16 KB and 32 KB, NTSC
and PAL) and //e, built against a POM2 source tree (a2shot has no //c).

    make test-iic [POM2_SRC=../../pom2]
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pom2-src', type=Path, required=True)
    ap.add_argument('--disk', type=Path, required=True)
    ap.add_argument('--labels', type=Path, required=True)
    ap.add_argument('--build', type=Path, required=True)
    a = ap.parse_args()
    src = a.pom2_src.resolve()
    library = src / 'build/libpom2_core_test.a'
    if not library.exists():
        raise SystemExit(f'Build the POM2 core test library first: {library}')
    libs = ['-framework', 'CoreAudio', '-framework', 'AudioToolbox', '-framework', 'AudioUnit'] \
        if sys.platform == 'darwin' else ['-pthread']
    libs += subprocess.check_output(['pkg-config', '--libs', 'slirp'], text=True).split() + ['-lz']
    a.build.mkdir(parents=True, exist_ok=True)
    exe = (a.build / 'iic_probe').resolve()
    subprocess.run(['c++', '-std=c++17', '-O2', '-I', str(src / 'src'), '-I', str(src / 'include'),
                    '-I', str(src / 'build/generated'), str(Path(__file__).with_name('iic_probe.cpp')),
                    str(library), *libs, '-o', str(exe)], check=True)
    failed = 0
    for variant in ('iic16', 'iic32', 'iic32-pal', 'iic32-joy', 'iic16-joy', 'iic32-reset', 'iic32-irqstop', 'iic16-irqstop', 'iic32-joy-irqstop', 'iie', 'iie-pal',
                    'iie-joy', 'iie-reset'):
        with tempfile.TemporaryDirectory(prefix='wargalagaii-iic-') as tmp:
            disk = Path(tmp) / 'GAME.po'
            shutil.copyfile(a.disk, disk)       # the probe may write to it
            failed += subprocess.run([str(exe), str(src / 'roms'), str(disk),
                                      str(a.labels.resolve()), variant]).returncode != 0
    if failed:
        raise SystemExit(f'{failed} variant(s) failed')


if __name__ == '__main__':
    main()
