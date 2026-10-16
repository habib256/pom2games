#!/usr/bin/env python3
"""The load of the original (lot 14, the OBJECTS page's gauge), on the ROM.

Part 1 runs the preparation of a walk or a swim alone (T08/S07 $5B51, the
module of build/re_env/ch over the saved first-journey state build/game.bin,
as tests/test_swim_cadence.py does): the factor $4C84 = ($4C02 + $4BBE) /
$4BF6 for every carried weight from 0 to 1 200 oz ($4C02 = body +
INT(ounces / 16), the core's $50A1). The duration of a step is this factor
times the terrain, weather and health terms (T09/S00): the load slows the
walk in proportion from the first pound, with no threshold.

Part 2 plays the real game (build/SIERRA.woz + build/JOURNEY.dsk): the
weight left at the start ($4BF8), the maximum ($4BFA), the body ($4BF6) and
the total pounds ($4C02); GET ROCK at the start; then GET ROCK with exactly
the rock's 100 oz left (accepted) and with 99 (refused, msg 7): the
transaction T0E/S02 refuses a transfer when $4BF8 - W5 < 0, its only rule
of weight.

No original byte enters the repository: disks stay in build/, results go to
build/re_load/results.json (numbers quoted in docs/MENUS.md and TODO.md).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE / 'tests'))
import a2test                       # noqa: E402
from re_surv_fp import fp           # noqa: E402

OUT = HERE / 'build/re_load'
LOADS = list(range(0, 1201, 16)) + [15, 772, 815, 816]


def writes(addr, data):
    return [f'poke:{addr + i:04X}:{v:02X}' for i, v in enumerate(data)]


def word(m, a):
    return int.from_bytes(m[a:a + 2], 'little')


def isolated(body=165):
    """$4C84 for each load (ounces), the walk preparation of T08/S07."""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'state.bin').write_bytes((HERE / 'build/game.bin').read_bytes()[0x4000:0x5000])
    hello = OUT / 'hello.bas'
    hello.write_text('10 PRINT CHR$(4);"BLOAD STATE"\n'
                     '20 PRINT CHR$(4);"BLOAD MODULE"\n'
                     '30 PRINT CHR$(4);"BRUN DRIVER"\n')
    data = bytearray((HERE / 'build/re_env/ch/t08s07.bin').read_bytes())
    data[0x5B96 - 0x5800] = 0x60            # $4C84 stored: back to the driver
    (OUT / 'module.bin').write_bytes(data)
    (OUT / 'driver.bin').write_bytes(bytes((0x20, 0x51, 0x5B, 0x4C, 0, 8)))
    disk = OUT / 'probe.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'),
                    '--out', str(disk), '--bas', f'HELLO={hello}',
                    '--bin', f'STATE={OUT / "state.bin"}@0x4000',
                    '--bin', f'MODULE={OUT / "module.bin"}@0x5800',
                    '--bin', f'DRIVER={OUT / "driver.bin"}@0x0800'],
                   check=True, capture_output=True)
    steps = ['until:0800:20000']
    for oz in LOADS:
        steps += writes(0x4BF6, body.to_bytes(2, 'little'))
        steps += writes(0x4C02, (body + oz // 16).to_bytes(2, 'little'))
        steps += writes(0x4BBE, (2).to_bytes(2, 'little'))
        steps += ['until:0803:1000', 'peek:4C84:5', 'until:0800:1000']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=1800)
    rows = []
    for k, oz in enumerate(LOADS):
        factor = fp(r.mem(0x4C84, 5, k))
        rows.append(dict(ounces=oz, pounds=oz // 16, factor=round(factor, 6),
                         slower_pct=round(100 * (factor / ((body + 2) / body) - 1), 4)))
    return rows


def game():
    import re_camp_probe

    class Original(re_camp_probe.Original):
        def __exit__(self, *a):
            (OUT / 'game.log').write_text(self.s.out)
            self.s.__exit__(*a)

    def snap(m):
        return dict(left=word(m, 0x4BF8), max=word(m, 0x4BFA), body=word(m, 0x4BF6),
                    pounds=word(m, 0x4C02), wear=word(m, 0x4BEE), pack=word(m, 0x4BF0),
                    hand=word(m, 0x4BF2), rock=m[0x45C0 + 17])

    rows = []
    with Original() as o:
        rows.append(dict(command='START', state=snap(o.mem())))
        for left, cmd in ((None, 'GET ROCK'), (100, 'GET ROCK'), (None, 'DROP ROCK'), (99, 'GET ROCK')):
            if left is not None:
                o.poke(0x4BF8, list(left.to_bytes(2, 'little')))
            text = o.cmd(cmd)
            rows.append(dict(command=cmd, left_before=left, text=text, state=snap(o.mem())))
    return rows


def main():
    walk = isolated()
    for row in walk:
        print(row)
    rows = game() if '--no-game' not in sys.argv else []
    for row in rows:
        print(row)
    (OUT / 'results.json').write_text(json.dumps(dict(walk=walk, game=rows), indent=1) + '\n')


if __name__ == '__main__':
    main()
