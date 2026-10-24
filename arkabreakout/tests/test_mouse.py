#!/usr/bin/env python3
"""Real AppleMouse firmware on the II+ (both card models) and the native //c
mouse (16 and 32 KB ROMs), by tests/mouse_probe.cpp on the POM2 core facade
(build/mouse_probe); each variant leaves once by Q and once by RESET."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--probe', type=Path, required=True)
    ap.add_argument('--roms', type=Path, required=True)
    ap.add_argument('--disk', type=Path, required=True)
    ap.add_argument('--labels', type=Path, required=True)
    a = ap.parse_args()
    failed = []
    with tempfile.TemporaryDirectory(prefix='arka-mouse-') as tmp:
        disk = Path(tmp) / 'GAME.dsk'
        for variant in ('applewin', 'mame', 'iic16', 'iic32'):
            for action in ([], ['reset']):
                shutil.copyfile(a.disk, disk)
                result = subprocess.run([str(a.probe.resolve()), str(a.roms.resolve()), str(disk),
                                         str(a.labels.resolve()), variant, *action],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                print(*[l for l in result.stdout.splitlines() if l.startswith(('PASS', 'FAIL'))], sep='\n')
                if result.returncode:
                    failed.append('/'.join([variant, *action]))
    if failed:
        raise SystemExit('FAIL ' + ', '.join(failed))


if __name__ == '__main__':
    main()
