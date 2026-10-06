#!/usr/bin/env python3
"""Empty, checksummed table: five little-endian score/initials/mode entries.

Format 2: scores count tens of points."""
from pathlib import Path
import sys
data=bytearray(b'CBR1\x02\x00'+b'\x00\x00---\x00'*5)
data+=sum(data).to_bytes(2,'little')
assert len(data)==38
Path(sys.argv[1]).write_bytes(data)
