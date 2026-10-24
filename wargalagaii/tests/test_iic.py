#!/usr/bin/env python3
"""WARGALAGA II's clock on the //c (ROM 16 KB and 32 KB, NTSC and PAL) and
the //e, by tests/iic_probe.cpp on the POM2 core facade (build/iic_probe).

    make test
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

VARIANTS = ('iic16', 'iic32', 'iic32-pal', 'iic32-joy', 'iic16-joy', 'iic32-reset', 'iic32-irqstop',
            'iic16-irqstop', 'iic32-joy-irqstop', 'iie', 'iie-pal', 'iie-joy', 'iie-reset')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', type=Path, required=True)
    ap.add_argument('--roms', type=Path, required=True)
    ap.add_argument('--disk', type=Path, required=True)
    ap.add_argument('--labels', type=Path, required=True)
    a = ap.parse_args()
    failed = []
    for variant in VARIANTS:
        with tempfile.TemporaryDirectory(prefix='wargalagaii-iic-') as tmp:
            disk = Path(tmp) / 'GAME.po'
            shutil.copyfile(a.disk, disk)       # the probe may write to it
            result = subprocess.run([str(a.probe.resolve()), str(a.roms.resolve()), str(disk),
                                     str(a.labels.resolve()), variant],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            print(*[l for l in result.stdout.splitlines() if not l.startswith('[INFO]')], sep='\n')
            if result.returncode:
                failed.append(variant)
    if failed:
        raise SystemExit('FAIL ' + ', '.join(failed))


if __name__ == '__main__':
    main()
