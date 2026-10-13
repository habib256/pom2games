#!/usr/bin/env python3
"""Every screen returns to the same view without disk access or elapsed time.

From a fresh game, one session opens and leaves each screen by the keyboard:
STATUS (Esc), STATUS -> M -> B -> Esc (medical detail and back), INVENTORY
(every page), HELP (every page), MAP (scrolled four ways, then C), TOPO and
QUIT answered N, Return and Esc. After each return:

* no MLI call: the mli_calls/mli_reads counters of memory.s are unchanged and
  an a2shot watch on the ProDOS entry $BF00 never fires;
* the module loads are exactly the expected ones: an a2shot watch on
  mem_fetch records each directory index, xfer_count grows by that many
  (overlay_reads too, but for TOPOGEN, fetched directly), and xfer_bytes by
  the sum of their lengths (build/layout.json);
* the journey is unchanged: clock and simulation block (s_hour..s_t0, with
  s_elap and s_health), position and heading, the five item tables,
  fauna_rng, water_rng, weather_seed, injuries, animal and NATURE frequency;
* the picture is identical: both DHGR banks (rows 0-191, screen holes
  excluded: they hold simulation scratch), the graphics of the rendered
  560 x 384 frame of a2shot (shot:) and the memory/video soft switches; the
  four text lines (page 1 rows 20-23 and their frame rows) hold the prompt
  alone after the first return, which clears the welcome message, and
  stay identical afterwards (rows 0-19 of the text page are hidden under
  the graphics and keep the last screen);
* the stack pointer and the I flag at do_command are the same for every
  command.
"""
import json
import re
import struct
import sys
import tempfile
import time
import zlib
from pathlib import Path

from common import result_rows, HERE, L, DISK, a2test, text_screen

LIMIT = 20000
DISCOVER = '--discover' in sys.argv   # print the loads without checking them
IDLE = L.until('idle', LIMIT)
SCREEN = L.until('keyboard_wait', LIMIT)
COUNTERS = (('mli_calls', 2), ('mli_reads', 2), ('mli_bytes', 3), ('xfer_count', 2),
            ('xfer_bytes', 3), ('overlay_reads', 2), ('geo_queries', 3))
SWITCHES = 'peek:C011:15'   # LCBNK2 LCRAM RAMRD RAMWRT CXROM ALTZP C3ROM 80STORE VBL TEXT MIXED PAGE2 HIRES ALTCHAR 80COL
STATE = (('px', 6), ('s_hour', L['s_t0'] + 5 - L['s_hour']), ('fauna_rng', 1),
         ('water_rng', 1), ('weather_seed', 4), ('injury_active', 15),
         ('animal_kind', 6), ('nature_frequency', 1))
STATE += tuple((name, 76) for name in ('it_place', 'it_pack_lo', 'it_pack_hi',
                                      'it_gnd_lo', 'it_gnd_hi'))
LAYOUT = json.loads((HERE / 'build/layout.json').read_text())['modules']

# (name, keystrokes (each followed by the screen's keyboard loop, the last
# one by the command line), module indexes copied by mem_fetch, in order).
# The sequence is deterministic from a fresh game:
# STATUS shows its module (16), which asks ADV (21) for the route progress
# (DONE=) and is copied again; M adds MEDICAL (17) and its view (19), B
# returns to STATUS. INVENTORY (2) computes its load totals in SIM (3),
# whose activation hides the view: the return redraws it (HUD 15, wreck
# sprite 5). HELP shares module 2; MAP is SITES (10). TOPO copies TOPOGEN
# (0) into the SIM window by a direct mem_fetch (not a module load: no
# overlay_reads) and copies the snapshot of the view back on return
# (docs/MEMORY.md 8.4): no HUD or sprite reload. QUIT asks through INP (13).
SCREENS = (
    ('STATUS', ['STATUS\r', '\\e'], [16, 21, 16]),
    ('STATUS M B', ['STATUS\r', 'M', 'B', '\\e'], [21, 16, 17, 19, 16, 21, 16]),
    ('INVENTORY', ['INVENTORY\r', '2', '3', '4', '5', '1', 'N', 'B', '\\e'], [2, 3, 15, 5]),
    ('HELP', ['HELP\r', '2', '3', 'N', 'B', '\\e'], [2]),
    ('MAP', ['MAP\r', 'D', 'S', 'A', 'W', 'D', 'C', '\\e'], [10]),
    ('TOPO', ['TOPO\r', '\\e'], [0]),
    ('QUIT N', ['QUIT\r', 'N'], [13]),
    ('QUIT RETURN', ['QUIT\r', '\\r'], []),
    ('QUIT ESC', ['QUIT\r', '\\e'], []),
)


def frame(path):
    """The 560 x 384 RGB frame of an a2shot PNG (filter 0 rows)."""
    png = path.read_bytes()
    pos, idat = 8, bytearray()
    while pos < len(png):
        size = struct.unpack_from('>I', png, pos)[0]
        kind, data = png[pos + 4:pos + 8], png[pos + 8:pos + 8 + size]
        if kind == b'IHDR':
            assert struct.unpack_from('>II', data) == (560, 384)
        elif kind == b'IDAT':
            idat += data
        pos += size + 12
    return zlib.decompress(idat)


def visible(page):
    """Rows 0..191 of both DHGR banks of a 16 KB dump (no screen holes)."""
    return b''.join(page[bank + a2test.hgr_offset(y):bank + a2test.hgr_offset(y) + 40]
                    for bank in (0, 8192) for y in range(192))


def switches(raw):
    """Bit 7 of each soft-switch status (the low bits float), VBL excluded."""
    return tuple(b >> 7 for i, b in enumerate(raw) if i != 8)


def main():
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(DISK, timeout=600) as s:
        shot = Path(tmp) / 'frame.png'

        def counters():
            return {n: int.from_bytes(s.step(L.peek(n, k)).data, 'little') for n, k in COUNTERS}

        def snapshot():
            s.step('wait:2')        # let the video beam show the settled page
            s.step(f'shot:{shot}')
            page = s.step('peek:2000:8192').data
            assert len(page) == 16384, 'both DHGR banks expected'
            return dict(state=[s.step(L.peek(n, k)).data for n, k in STATE],
                        page=visible(page), text=text_screen(s.step('peek:0400:1024').data)[20:],
                        switches=switches(s.step(SWITCHES).data), frame=frame(shot))

        s.step(IDLE)
        before = snapshot()
        assert before['switches'][7] and before['switches'][11], '80STORE/HIRES expected'
        assert len(set(before['frame'][:320 * (560 * 3 + 1)])) > 4, 'the landscape must be on screen'
        fetch = L['mem_fetch']
        s.step('watch:BF00')
        s.step(f'watch:{fetch:04X}')
        s.step(f'watch:{L["do_command"]:04X}')
        stacks = []
        prompt = None
        for name, keys, modules in SCREENS:
            start = counters()
            mark = len(s.out)
            for k, key in enumerate(keys):
                text = key[:-1] if key.endswith('\r') else key
                s.step(f'key:{text}')
                if key.endswith('\r'):
                    s.step('press:\\r')
                    s.step(L.until('do_command', LIMIT))
                s.step(IDLE if k == len(keys) - 1 else SCREEN)
                if k < len(keys) - 1:
                    screen = '\n'.join(text_screen(s.step('peek:0400:1024').data))
                    if name.startswith('QUIT'):
                        assert 'UNSAVED PROGRESS WILL BE LOST' in screen, screen
                    if key == 'M':
                        assert 'MEDICAL STATUS' in screen, screen
            out = s.out[mark:]
            fetched = [int(x, 16) for x in re.findall(rf'^watch {fetch:04X} .* X=([0-9A-F]{{2}})', out, re.M)]
            mli = out.count('watch BF00')
            stacks += re.findall(rf'^watch {L["do_command"]:04X} .* S=([0-9A-F]{{2}}) P=([0-9A-F]{{2}})', out, re.M)
            end = counters()
            delta = {k: end[k] - start[k] for k in end}
            after = snapshot()
            size = sum(LAYOUT[str(m)]['length'] for m in fetched)
            print(f'  {name:12} MLI {delta["mli_calls"]} (watch {mli}), module loads '
                  f'{delta["overlay_reads"]} {fetched}, RAM transfers {delta["xfer_count"]} '
                  f'({delta["xfer_bytes"]} bytes)', flush=True)
            assert mli == 0 and delta['mli_calls'] == delta['mli_reads'] == delta['mli_bytes'] == 0, name
            assert fetched == modules or DISCOVER, (name, fetched, modules)
            direct = fetched.count(0)       # TOPOGEN: mem_fetch without overlay_load
            assert delta['xfer_count'] == len(fetched), (name, delta)
            assert delta['overlay_reads'] == len(fetched) - direct, (name, delta)
            assert delta['xfer_bytes'] == size, (name, delta, size)
            assert delta['geo_queries'] == 0, name
            for (field, _), old, new in zip(STATE, before['state'], after['state']):
                assert old == new, (name, field, old.hex(), new.hex())
            assert after['switches'] == before['switches'], (name, before['switches'], after['switches'])
            assert after['page'] == before['page'], (name, 'DHGR page (both banks) changed')
            rows = 320 * (560 * 3 + 1)      # graphics rows of the frame, above the text lines
            assert after['frame'][:rows] == before['frame'][:rows], (name, 'displayed graphics changed')
            lines = after['text']
            if name.startswith('QUIT'):
                # Declining QUIT reports the cancellation, like any refusal.
                res = result_rows(lines)
                assert res[0].rstrip() == 'ACTION CANCELLED.' and not res[1].strip(), (name, lines)
            else:
                if prompt is None:
                    # The first return clears the welcome message: the command
                    # line is left with its prompt alone, then stays so.
                    assert not any(r.strip() for r in result_rows(lines)[:3]) and result_rows(lines)[3].startswith('FOOD'), lines
                    prompt = dict(text=lines, frame=after['frame'][rows:])
                assert lines == prompt['text'], (name, lines)
                assert after['frame'][rows:] == prompt['frame'], (name, 'displayed text lines changed')
        assert len({sp for sp, _ in stacks}) == 1, ('stack pointer at do_command varies', stacks)
        assert len({int(p, 16) & 4 for _, p in stacks}) == 1, ('I flag at do_command varies', stacks)
        s.step('unwatch')
    print(f'  {len(SCREENS)} screens: zero MLI, exact module loads, journey, both DHGR banks, text, '
          f'frame and soft switches unchanged; S=${stacks[0][0]}, I={int(stacks[0][1], 16) >> 2 & 1} at every command '
          f'({time.monotonic() - started:.0f} s)')
    print('Screen returns: OK')


if __name__ == '__main__':
    main()
