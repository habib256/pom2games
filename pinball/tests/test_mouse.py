#!/usr/bin/env python3
"""Real AppleMouse firmware on the Apple II+ (both card models) and the
native //c mouse (16 and 32 KB ROMs), by tests/mouse_probe.cpp on the POM2
core facade (build/mouse_probe)."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

GAME = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--probe', type=Path, required=True)
ap.add_argument('--roms', type=Path, required=True)
args = ap.parse_args()
failed = []
with tempfile.TemporaryDirectory(prefix='pinball-mouse-') as tmp:
    for variant in ('applewin', 'mame', 'iic16', 'iic32'):
        disk = Path(tmp) / 'PINBALL.dsk'
        shutil.copyfile(GAME.parent / 'dist/PINBALL.dsk', disk)
        result = subprocess.run([str(args.probe.resolve()), str(args.roms.resolve()), str(disk),
                                 str(GAME / 'build'), variant],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(*[l for l in result.stdout.splitlines() if not l.startswith('[INFO]')], sep='\n')
        if result.returncode:
            failed.append(variant)
if failed:
    raise SystemExit('FAIL ' + ', '.join(failed))
