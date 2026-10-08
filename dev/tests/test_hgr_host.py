#!/usr/bin/env python3
"""Compile and run host conversion regressions with ASan/UBSan."""
from pathlib import Path
import os
import shlex
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='hgr-host-') as tmp:
    binary=Path(tmp)/'host'
    subprocess.run([*shlex.split(os.environ.get('CC','cc')),'-O1','-g',
                    '-fsanitize=address,undefined','-fno-sanitize-recover=all',
                    '-DHGR_NO_APPLE2','-I',str(ROOT/'dev/lib/hgrc'),
                    str(ROOT/'dev/tests/hgr_host_fixture.c'),
                    str(ROOT/'dev/lib/hgrc/hgr_x2.c'),str(ROOT/'dev/lib/hgrc/hgr_blit_x2.c'),
                    '-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
