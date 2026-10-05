#!/usr/bin/env python3
"""Boot the DHGR introduction and exercise animation in both video banks."""
from pathlib import Path
import re
import tempfile
from test_dhgr import DEV, offset, run


def snapshot_steps():
    return ['peek:C018:8', 'poke:C002:0', 'peek:2000:16384',
            'poke:C003:0', 'peek:2000:16384', 'poke:C002:0']


def playfield(banks):
    return bytes(bank[page + offset(y) + col]
                 for bank in banks for page in (0, 8192)
                 for y in range(60, 169) for col in range(40))


def main():
    with tempfile.TemporaryDirectory(prefix='pom2-dhgr-example-') as temp:
        work = Path(temp)
        run(['make', '-s', '-C', DEV/'examples/dhgr',
             f'BUILD={work}/build', f'DIST={work}'])
        labels = (work/'build/dhgr.lbl').read_text()
        counter = int(re.search(r'al ([0-9A-Fa-f]+) \._frame_text$',
                                labels, re.M)[1], 16)
        counter_peek = f'peek:{counter:04X}:5'
        steps = ['wait:2600', *snapshot_steps(), 'key: ', 'wait:1800',
                 *snapshot_steps(), counter_peek, 'wait:120', *snapshot_steps(),
                 counter_peek,
                 'key: ', 'wait:200', *snapshot_steps(),
                 'wait:200', *snapshot_steps(),
                 'key: ', 'key:\\<', 'wait:120', 'key:\\>', 'wait:120',
                 'key:\\^', 'wait:120', 'key:\\v', 'wait:120', *snapshot_steps(),
                 'key:\\e', 'wait:120', 'peek:C018:8', 'peek:03F2:3']
        output = run([DEV/'tools/a2shot/a2shot', '--iie', '--disk',
                      work/'DHGR.dsk', *steps])
        blocks = re.split(r'(?m)^C018:', output)[1:]
        assert len(blocks) == 7, 'missing checkpoints'
        snapshots = []
        for block in blocks[:-1]:
            flags = bytes.fromhex(block.splitlines()[0])
            assert not flags[0] & 128, '80STORE must remain off'
            assert not flags[2] & 128, 'animation left graphics mode'
            assert flags[5] & 128 and flags[7] & 128, 'HIRES/80COL missing'
            dumps = re.findall(r'(?m)^[2345][0-9A-F]{3}: ([0-9A-F ]+)$', block)
            data = bytes.fromhex(' '.join(dumps))
            assert len(data) == 32768, 'missing main/aux video RAM'
            snapshots.append((data[:16384], data[16384:]))
        assert snapshots[0] != snapshots[1], 'introduction did not advance'
        counters = [int(bytes.fromhex(v).decode('ascii')) for v in
                    re.findall(rf'(?m)^{counter:04X}: ([0-9A-F ]+)$', output)]
        assert len(counters) == 2
        assert (counters[1]-counters[0]) % 100000 >= 40, \
               ('animation below 20 fps on a 1 MHz IIe', counters)
        for bank in range(2):
            assert playfield((snapshots[1][bank],)) != \
                   playfield((snapshots[2][bank],)), \
                   'animation must move in main and auxiliary RAM'
        assert playfield(snapshots[3]) == playfield(snapshots[4]), 'pause unstable'
        assert playfield(snapshots[4]) != playfield(snapshots[5]), 'resume failed'
        flags = bytes.fromhex(blocks[-1].splitlines()[0])
        assert flags[2] & 128 and not flags[7] & 128, 'text display not restored'
        vector = bytes.fromhex(re.search(r'(?m)^03F2: ([0-9A-F ]+)$', output)[1])
        assert vector[:2] == bytes((0xBF, 0x9D)), 'DOS reset vector not restored'
    print('DHGR starter: introduction, animation in both banks, pause/resume, '
          'arrows and DOS restoration passed (IIe).')


if __name__ == '__main__':
    main()
