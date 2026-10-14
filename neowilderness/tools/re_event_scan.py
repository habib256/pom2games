#!/usr/bin/env python3
"""re_event_scan.py: who reads or writes a state byte on the Journey side.

  re_event_scan.py ADDR...           absolute accesses (LDA/STA/LDX/STX/...,
                                     indexed included) to each address, on
                                     the Journey side and in build/files/
  re_event_scan.py --table X         calls of the core accessor $4D12 with
                                     LDX #X (condition tables: 2 prevented,
                                     3 treated, 4 active, 7 percentages)

Locations are SMALLDOS track/sector + offset (a module loaded from T/S runs
at $5800 + 256 x (sector - S) + offset). Used for lot 13 (docs/IMPLEMENTATION.md,
"Infection et malaria"): the event consumer T06/S00 and the onsets of T0B/S07.
Local analysis only: nothing original is written to the repository.
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smalldos import Disk  # noqa: E402

OPS = (0x8C, 0x8D, 0x8E, 0x9D, 0x99, 0xAC, 0xAD, 0xAE, 0xBD, 0xB9, 0xEE, 0xCE,
       0x2C, 0xCD, 0xEC, 0xCC, 0xDD, 0xD9)


def where(name, i):
    return f'T{i//4096:02X}/S{(i//256)%16:X}+{i%256:02X}' if name == 'J' else f'{name}+{i:04X}'


def main():
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build')
    journey = Disk(open(os.path.join(here, 'JOURNEY.dsk'), 'rb').read())
    journey.flip = True
    sources = {'J': journey.run(0, 0, 35 * 16)}
    files = os.path.join(here, 'files')
    if os.path.isdir(files):
        for f in sorted(os.listdir(files)):
            sources[f] = open(os.path.join(files, f), 'rb').read()
    args = sys.argv[1:]
    if args[:1] == ['--table']:
        x = int(args[1], 0)
        data = sources['J']
        for m in re.finditer(rb'\x20\x12\x4d', data):
            i = m.start()
            ctx = data[i - 8:i]
            xs = [ctx[k + 1] for k in range(7) if ctx[k] == 0xA2]
            if xs and xs[-1] == x:
                print(where('J', i), data[i - 8:i + 8].hex(' '))
        return
    for addr in (int(a, 16) for a in args):
        for name, data in sources.items():
            for m in re.finditer(re.escape(bytes([addr & 255, addr >> 8])), data):
                i = m.start() - 1
                if i >= 0 and data[i] in OPS:
                    print(f'${addr:04X}', where(name, i), data[max(0, i - 8):i + 3].hex(' '))


if __name__ == '__main__':
    main()
