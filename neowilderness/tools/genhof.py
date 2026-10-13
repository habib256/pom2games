#!/usr/bin/env python3
"""genhof.py: the empty hall of fame NEOWILD.HOF (lot 7, step 6).

Usage: genhof.py OUT.HOF

One 512-byte block (a ProDOS seedling file: no index block): 'H', version 1,
zero journey counters and reserved bytes, then 6 scenarios x 5 empty entries
of 16 bytes (outcome 0). Layout: tools/score_ref.py and docs/HOF.md.
tools/build_disk.py places it on the volume; the game never creates it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_ref  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    Path(sys.argv[1]).write_bytes(score_ref.empty_file())


if __name__ == '__main__':
    main()
