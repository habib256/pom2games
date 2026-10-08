#!/usr/bin/env python3
"""Recover only the documented missing assets from the pinned reference disk."""
import argparse
import hashlib
import json
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('disk', type=Path)
args = ap.parse_args()
assets = Path(__file__).resolve().parents[1] / 'assets'
manifest = json.loads((assets / 'origin.json').read_text())
disk = args.disk.read_bytes()
if hashlib.sha256(disk).hexdigest() != manifest['reference_sha256']:
    raise SystemExit('Reference disk SHA-256 does not match assets/origin.json')
for name, spec in manifest['assets'].items():
    data = disk[spec['offset']:spec['offset'] + spec['length']]
    if hashlib.sha256(data).hexdigest() != spec['sha256']:
        raise SystemExit('Asset SHA-256 does not match: ' + name)
    (assets / name).write_bytes(data)
    print(name, len(data))
