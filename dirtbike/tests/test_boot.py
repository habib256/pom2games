"""A failed boot read can be retried, restoring the entire patched DOS binary."""
from pathlib import Path
import sys

GAME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GAME.parent / 'dev/tools'))
import a2test
import dos33


def main():
    disk = GAME.parent / 'dist/DIRTBIKE.dsk'
    image = disk.read_bytes()
    binary = dos33.read_file(image, 'DIRTBIKE')
    loader = dos33.read_file(image, 'BOOT')
    labels = a2test.labels(GAME / 'build/boot.lbl')
    offset = labels['rwts_sectors'] - labels['boot']
    # Return an I/O error on the first read, then restore RWTS before retrying.
    result = a2test.run(disk, [labels.until('boot'), labels.poke('rwts_sectors', 0x38),
                               labels.poke('rwts_sectors', 0x60, 1), labels.until('wait'),
                               'peek:0400:1024', labels.poke('rwts_sectors', loader[offset]),
                               labels.poke('rwts_sectors', loader[offset + 1], 1), 'press: ',
                               'until:6000:3000', f'peek:6000:{len(binary)}'])
    assert any(b'PRESS A KEY TO RETRY' in bytes(c & 127 for c in row)
               for row in a2test.text_rows(result))
    assert result.mem(0x6000, len(binary)) == binary
    print(f'RWTS boot: retry prompt and all {len(binary)} program bytes verified')


if __name__ == '__main__':
    main()
