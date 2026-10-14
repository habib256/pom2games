#!/usr/bin/env python3
"""Probe the original's journey preparation (GO1, GO2, GO3) on the Apple II.

Lot 1 of docs/ORIGINAL_GAP.md (P1, P2). MENU option 2 (a new journey on the
supplied Sierra Nevada map) loads TOPO and runs GO1 at $5800. When GO1 is
entered, the probe pokes:
- the difficulty level into the map header ($603F, normally fixed by TMAKE);
- an imposed RND: SMALLDOS's generator at $0321 becomes `LDA #$28 / LDY #$03 /
  JMP MOVFM`, returning the 5-byte float at $0328 at every call (the key wait
  of the date question calls it too).
Then the questions are answered (tools/prepare_ref.py ANSWERS order: plane
crash, date Y/N [month, hour], normal or research [sex, weight, frame,
height, age, pulse], wildlife and storm frequencies), the screen with the
fitness verdict and both introduction pages are read, and the state is
dumped when GO1 hands over to the engine ($5E9D, JMP $03DB): page 3 (GO
variables $0300-$0311) and $4000-$4FFF (item rows, floats $4B00-$4CFF).

Results: build/re_prepare/cases.json (raw bytes and screens per case),
compared by tests/test_prepare.py --original with the port and with
tools/prepare_ref.py.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE.parent / 'dev/tools'), str(HERE / 'tools')]
import a2test  # noqa: E402
import prepare_ref as R  # noqa: E402

OUT = HERE / 'build/re_prepare'
GO1_DONE = 0x5E7F          # GO1: JSR $3003, the introduction (state complete)
RND_STUB = 0x0321          # SMALLDOS RND (FAC = RND)
RND_VALUE = 0x0328


def text_page(mem):
    rows = []
    for r in range(24):
        o = (r % 8) * 0x80 + (r // 8) * 0x28
        rows.append(''.join(chr(b & 0x7F) if (b & 0x7F) >= 0x20 else chr((b & 0x7F) + 0x40)
                            for b in mem[o:o + 40]).rstrip())
    return rows


def steps_for(case):
    """a2shot steps of one case (tools/prepare_ref.CASES entry)."""
    stub = bytes([0xA9, RND_VALUE & 255, 0xA0, RND_VALUE >> 8, 0x4C, 0xF9, 0xEA]) + R.encode(case['rnd'])
    steps = ['wait:5400', 'key:2\r', f'until:5800:3000', f'poke:603F:{case["level"]:02X}']
    steps += [f'poke:{RND_STUB + i:04X}:{b:02X}' for i, b in enumerate(stub)]
    # GO1 $5E7F (JSR $3003) becomes JMP $5E7F: a trap the breakpoint cannot miss.
    steps += [f'poke:{GO1_DONE:04X}:4C', f'poke:{GO1_DONE + 1:04X}:{GO1_DONE & 255:02X}',
              f'poke:{GO1_DONE + 2:04X}:{GO1_DONE >> 8:02X}']
    steps += ['wait:300', f'insert:{HERE / "build/JOURNEY.dsk"}', 'key:\r', 'wait:1500']
    answers = R.original_answers(case)
    research = case.get('research')
    for k, answer in enumerate(answers[:-1]):
        steps += [f'key:{answer}\r', 'wait:150']
        if not research and k == len(answers) - 3:     # after the pulse: the verdict
            steps += ['wait:200', 'peek:0400:1024']
    if research:
        steps += ['peek:0400:1024']
    steps += [f'key:{answers[-1]}\r', 'wait:1', f'until:{GO1_DONE:04X}:20000', 'peek:0300:256',
              'peek:4000:4096', f'poke:{GO1_DONE:04X}:20',
              f'poke:{GO1_DONE + 1:04X}:03', f'poke:{GO1_DONE + 2:04X}:30', 'wait:1400', 'peek:0400:1024', 'key:\r', 'wait:300', 'peek:0400:1024']
    return steps


def run_case(case):
    r = a2test.run(HERE / 'build/SIERRA.woz', steps_for(case), emulator=a2test.A2SHOT, timeout=900)
    d = r.dumps
    assert len(d) == 5, (case['name'], len(d))
    return dict(case, verdict_screen=text_page(d[0]), intro=[text_page(d[3]), text_page(d[4])],
                page3=d[1].hex(), state=d[2].hex())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:]
    results = []
    for case in R.CASES:
        if names and case['name'] not in names:
            continue
        res = run_case(case)
        results.append(res)
        got = R.from_original(bytes.fromhex(res['page3']), bytes.fromhex(res['state']))
        print(f"{case['name']:10} level {case['level']:2} rnd {case['rnd']}: injury {got['injury']}, "
              f"Hmax {got['hmax']:.6f}, rate {got['rate']:.4f}, date {got['date']:.5f}, "
              f"hour {got['hour']:.3f}, front {got['front']:.2f}/{got['duration']}, wind {got['wind']}")
    path = OUT / 'cases.json'
    if names and path.exists():
        old = [c for c in json.loads(path.read_text()) if c['name'] not in names]
        results = old + results
    path.write_text(json.dumps(results, indent=1) + '\n')
    print(f'{path}: {len(results)} cases')


if __name__ == '__main__':
    main()
