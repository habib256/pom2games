#!/usr/bin/env python3
"""Compatibility entry: ChromaBreak uses the shared library font builder."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[2]
subprocess.run(['python3',str(root/'dev/tools/build_dhgr_font.py'),'--out',str(root/'chromabreak/src/font.bin')],check=True)
