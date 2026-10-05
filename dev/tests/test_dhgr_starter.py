#!/usr/bin/env python3
"""Compare fast DHGR sprites/HUD with the general library in the IIe core."""
from pathlib import Path
import re
import tempfile
from test_dhgr import DEV, run


def main():
    with tempfile.TemporaryDirectory(prefix='dhgr-starter-render-') as directory:
        work = Path(directory)
        sources = [DEV/'cc65/crt0_apple2.s', DEV/'tests/dhgr_starter_fixture.c',
                   DEV/'examples/dhgr/src/ball_render.s',
                   *[DEV/'lib/hgrc'/name for name in
                     ('dhgr.c', 'dhgr_asm.s', 'dhgr_sprite.c',
                      'dhgr_transfer_params.c', 'dhgr_block_asm.s',
                      'dhgr_text.c', 'dhgr_text_asm.s', 'hgr_font.c')],
                   DEV/'lib/apple2c/apple2io_asm.s']
        objects = []
        for source in sources:
            obj = work/(source.stem+'.o')
            run(['cl65', '-t', 'none', '-Oirs', '-I', DEV/'examples/dhgr/src',
                 '-I', DEV/'lib/hgrc', '-I', DEV/'lib/apple2c',
                 '--asm-include-dir', DEV/'lib/apple2', '-c', '-o', obj, source])
            objects.append(obj)
        binary = work/'test.bin'
        run(['cl65', '-t', 'none', '-C', DEV/'cc65/apple2_hgr_c.cfg',
             '-o', binary, *objects])
        hello = work/'hello.bas'
        hello.write_text('10 PRINT CHR$(4);"BRUN TEST"\n')
        disk = work/'test.dsk'
        run(['python3', DEV/'tools/dos33.py', '--master',
             DEV/'tools/dos33_system.bin', '--out', disk,
             '--bas', f'HELLO={hello}', '--bin', f'TEST={binary}@0x6000'])
        steps = ['wait:1400']
        for stage in range(9):
            steps += ['peek:1000:1', 'peek:C013:2', 'peek:C018:8',
                      'poke:C002:0', 'peek:2000:16384',
                      'poke:C003:0', 'peek:2000:16384', 'poke:C002:0',
                      'key: ', 'wait:300']
        output = run([DEV/'tools/a2shot/a2shot', '--iie', '--disk', disk, *steps])
        blocks = re.split(r'(?m)^1000:', output)[1:]
        assert len(blocks) == 9
        for stage, block in enumerate(blocks):
            assert int(block.splitlines()[0], 16) == stage, 'missing checkpoint'
            flags = bytes.fromhex(re.search(r'(?m)^C013: (.*)$', block)[1])
            assert not any(v & 128 for v in flags), 'RAMRD/RAMWRT not restored'
            flags = bytes.fromhex(re.search(r'(?m)^C018: (.*)$', block)[1])
            assert not flags[0] & 128, '80STORE not restored'
            dumps = re.findall(r'(?m)^[2345][0-9A-F]{3}: ([0-9A-F ]+)$', block)
            data = bytes.fromhex(' '.join(dumps))
            assert len(data) == 32768
            for base in (0, 16384):
                expected, actual = data[base:base+8192], data[base+8192:base+16384]
                assert actual == expected, (stage, 'main' if base == 0 else 'aux',
                    next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b))
    print('DHGR fast renderer: all seven shifts, overlapping sprites, scanlines, '
          'edge positions, decimal carries and background restoration passed.')


if __name__ == '__main__':
    main()
