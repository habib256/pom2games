#!/usr/bin/env python3
"""po2woz.py: a 140 KB ProDOS-order image (.po) as a write-protected WOZ 2
disk, for the hall of fame's write-protected cases (tests/test_hof.py,
tests/test_save.py).

Usage: po2woz.py IN.po OUT.woz [--write-protected]

POM2 (a2shot) honours the INFO write-protect flag of a WOZ image: ProDOS then
returns $2B on a WRITE, as with a covered notch. The encoder is
dev/tools/dsk2woz.py's; this keeps the layout these tests always booted
(volume 254, 40/6/16 self-sync gaps, synchronized flag, creator), so the
images are byte-identical to the former stand-alone encoder's.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools'))
import dsk2woz  # noqa: E402

LAYOUT = dict(gaps=(40, 6, 16), creator=b'neowilderness test_hof', synchronized=True)


def po_to_woz(po, write_protected=True):
    assert len(po) == dsk2woz.IMAGE_SIZE, 'a 280-block volume'
    return dsk2woz.build(po, dsk2woz.PRODOS_ORDER, 254, verify=False,
                         write_protected=write_protected, **LAYOUT)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--write-protected', action='store_true')
    a = ap.parse_args()
    a.out.write_bytes(po_to_woz(a.src.read_bytes(), a.write_protected))


if __name__ == '__main__':
    main()
