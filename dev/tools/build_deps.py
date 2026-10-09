#!/usr/bin/env python3
"""Retarget a cc65 -S dependency file from generated assembly to its object."""
from pathlib import Path
import sys
path = Path(sys.argv[1])
data = path.read_text()
_, separator, rest = data.partition(':')
if not separator:
    raise SystemExit('missing dependency target: ' + str(path))
path.write_text(sys.argv[2] + ':' + rest)
