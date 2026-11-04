#!/usr/bin/env python3
"""Every doubled-text clipping count through the actual cc65 fastcall ABI."""
import argparse
from pathlib import Path
import tempfile
from test_hgr import build, a2test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-text-cells-') as directory:
        work = Path(directory)
        source = work/'cells.c'
        source.write_text('''#include "hgr_internal.h"
void done(void);
unsigned char counts[265];
int main(void) {
    unsigned room;
    for(room=0;room<=264;++room)counts[room]=hgr_text16_cells(room);
    done();
    for(;;){}
    return 0;
}
''')
        marker = work/'marker.s'
        marker.write_text('.export _done\n.code\n_done: rts\n')
        disk = build(work, source, extra_sources=(marker,))
        labels = a2test.labels(work/'test.lbl')
        result = a2test.run(disk, [labels.until('_done'), labels.peek('_counts', 265)],
                            iie=args.iie)
        assert result.dumps[0] == bytes(room//18+1 for room in range(265))
    print('HGR doubled-text count: all 265 rooms, including 18-pixel and 256-byte boundaries OK.')


if __name__ == '__main__':
    main()
