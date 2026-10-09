#!/usr/bin/env python3
"""Seed five zero scores and sector 1 in the versioned DOS record file."""
from pathlib import Path
import sys
Path(sys.argv[1]).write_bytes(b'ABR\x01\x00'+5*(b'000000AAA'+bytes([1])))
