#!/usr/bin/env python3
"""Boot the combined perspective/audio example, preserve graphics, exit DOS."""
import argparse
from pathlib import Path
import tempfile
from test_hgr import DEV, run, a2test


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    run(['make','-s','-C',DEV/'tools'/('a2shot' if args.iie else 'a2run')])
    with tempfile.TemporaryDirectory(prefix='pom2-perspective-example-') as temp:
        work=Path(temp)
        run(['make','-s','-j2','-C',DEV/'examples/perspective',f'BUILD={work}'])
        labels=a2test.labels(work/'perspective.lbl')
        steps=[labels.until('_ready'), 'peek:2000:8192', 'peek:03F2:3']
        if not args.iie: steps+=['spk']
        steps+=['press: ', labels.until('_sound_done',100), 'peek:2000:8192']
        if not args.iie: steps+=['spk']
        steps+=['key:\\e','wait:30','peek:03F2:3']
        if not args.iie: steps+=['text']
        result=a2test.run(work/'PERSPECTIVE.dsk',steps,iie=args.iie)
        page=result.mem(0x2000,8192)
        assert any(page), 'grid absent'
        assert result.mem(0x2000,8192,1)==page, 'audio altered HGR'
        assert result.mem(0x03f2,3,1)[:2]==bytes((0xbf,0x9d)), 'DOS RESET vector not restored'
        if not args.iie:
            assert result.spk[1]==320*4, result.spk
            assert any(']' in screen for screen in result.text_screens()), 'DOS prompt absent'
    print('Perspective/audio example: boot, grid, space playback, preserved HGR, '
          f'ESC and DOS restoration OK ({"IIe" if args.iie else "II+"})')


if __name__=='__main__':
    main()
