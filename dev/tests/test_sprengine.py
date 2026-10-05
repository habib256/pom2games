#!/usr/bin/env python3
"""Compare complete HGR scenes with an independent pixel composition model."""
from pathlib import Path
import re
import tempfile
from test_hgr import DEV, build, offset, run

SHAPES = (("10101", "0.1.0", "11011"), ("01110", "1.0.1", "10101"))


def banks(rows):
    data, masks = [], []
    for phase in range(7):
        for row in rows:
            bits, cover = 0, 0
            for x, ch in enumerate(row):
                if ch != '.': cover |= 1 << (phase + x)
                if ch == '1': bits |= 1 << (phase + x)
            data.extend((bits & 127, (bits >> 7) & 127))
            masks.extend((255 ^ (cover & 127), 255 ^ ((cover >> 7) & 127)))
    return data, masks


def scene(background, sprites):
    result = bytearray(background)
    for shape, x, y in sprites:
        for dy, row in enumerate(SHAPES[shape]):
            for dx, ch in enumerate(row):
                xx, yy = x + dx, y + dy
                if ch == '.' or xx >= 280 or yy >= 192: continue
                addr, bit = offset(yy) + xx // 7, 1 << (xx % 7)
                result[addr] = (result[addr] & (255 ^ bit)) | (bit if ch == '1' else 0)
    return result


def main():
    run(['make', '-C', DEV / 'tools/a2run'])
    with tempfile.TemporaryDirectory(prefix='pom2-sprengine-') as temp:
        work = Path(temp)
        header = ''
        for n, rows in enumerate(SHAPES):
            data, masks = banks(rows)
            for name, values in (('data', data), ('mask', masks)):
                header += f'static const unsigned char {name}{n}[] = {{' + ','.join(map(str, values)) + '};\n'
            header += f'static const hgr_mspr_t shape{n} = {{data{n},mask{n},2,3}};\n'
        (work / 'masked_test_sprite.inc').write_text(header)
        disk = build(work, DEV / 'tests/sprengine_fixture.c')
        steps = ['wait:1100']
        for _ in range(24):
            steps += ['peek:1000:2', 'peek:2000:16384', 'key: ', 'wait:60']
        output = run([DEV / 'tools/a2run/a2run', '--disk', disk, *steps])
        blocks = re.split(r'(?m)^1000:', output)[1:]
        assert len(blocks) == 24
        backgrounds = [bytes((i * 13 + seed) & 255 for i in range(8192)) for seed in (128, 42)]
        pages = [bytearray(b) for b in backgrounds]
        for stage, block in enumerate(blocks):
            assert bytes.fromhex(block.splitlines()[0]) == bytes((stage, 0)), (stage, 'guest contract check failed')
            if 1 <= stage <= 7:
                phase = stage - 1
                pages[0] = scene(backgrounds[0], [(0,14+phase,40),(1,16+phase,41)])
            elif stage == 8: pages[0] = scene(backgrounds[0], [(0,279,191)])
            elif stage == 9: pages[0] = bytearray(backgrounds[0])
            elif 10 <= stage <= 16:
                phase = stage - 10
                pg = 0 if phase & 1 else 1
                pages[pg] = scene(backgrounds[pg], [(0,255+phase,187),(1,257+phase,188)])
            elif stage in (17,18):
                pg = stage - 17
                pages[pg] = scene(backgrounds[pg], [(1,263,188)])
            elif stage in (19,20): pages[stage-19] = bytearray(backgrounds[stage-19])
            elif stage == 22: pages[0] = scene(backgrounds[0], [(0,48,60)])
            elif stage == 23: pages[0] = bytearray(backgrounds[0])
            lines = re.findall(r'(?m)^[2345][0-9A-F]{3}: ((?:[0-9A-F]{2} ?)+)$', block)
            actual, expected = bytes.fromhex(' '.join(lines)), pages[0] + pages[1]
            assert len(actual) == len(expected)
            if actual != expected:
                i = next(i for i,(a,b) in enumerate(zip(actual,expected)) if a != b)
                raise AssertionError(f'stage {stage}: ${8192+i:04X}={actual[i]:02X}, expected {expected[i]:02X}')
    print('Sprite engine: 24 scenes passed; overlaps, both pages, seven phases,')
    print('clipping, hiding, redefinition, invalid geometry, palette bits and screen holes.')


if __name__ == '__main__':
    main()
