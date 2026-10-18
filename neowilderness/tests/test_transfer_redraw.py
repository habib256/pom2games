#!/usr/bin/env python3
"""Measure inventory repaint savings against the same build with forced redraw.

Reference patches only the tent exception operand while stopped at the helper:
all native command logic, rendering and simulation remain identical.
"""
from common import DISK, L, a2test, text_screen
from test_screen_returns import visible
from test_guidance import state
from test_save import differing

LIMIT = 30000
IDLE = L.until('idle', LIMIT)
COMMANDS = ('CARRY AXE', 'PACK AXE', 'DROP AXE', 'CARRY TENT', 'DROP TENT')


def run(force):
    records = []
    with a2test.Session(DISK, timeout=900) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        for command in COMMANDS:
            s.step('key:' + command)
            s.step('press:\\r')
            beginning = s.step(L.until('do_command', LIMIT)).cycles[-1]
            s.step(L.until('item_load_totals', LIMIT))
            if force:
                noun = s.step(L.peek('noun')).data[0]
                # CPX #N_TENT -> CPX #this_noun: use the original full repaint.
                s.step(f'poke:{L["item_load_totals"] + 1:04X}:{noun:02X}')
            out = s.step(f'until:{L["show_view_scene"]:04X},{L["idle"]:04X}:{LIMIT}')
            redraw = f'PC={L["show_view_scene"]:04X}' in out.out
            if redraw:
                out = s.step(IDLE)
            records.append(dict(command=command, cycles=out.cycles[-1] - beginning,
                                redraw=redraw, state=state(s),
                                pixels=visible(s.step('peek:2000:8192').data),
                                text=text_screen(s.step('peek:0400:1024').data)[20:]))
    return records


def main():
    optimized, forced = run(False), run(True)
    for current, reference in zip(optimized, forced):
        command = current['command']
        # Cache validity is display bookkeeping, rebuilt by the reference
        # repaint; the optimized path intentionally leaves it invalid.
        assert not differing(current['state'][0], reference['state'][0],
                             {L['scene_cache_valid']}), command
        assert current['state'][1] == reference['state'][1], command
        for field in ('pixels', 'text'):
            assert current[field] == reference[field], (command, field)
        assert reference['redraw'], command
        if 'TENT' in command:
            assert current['redraw'], 'Tent must refresh its site sprite'
        else:
            assert not current['redraw'], command
            assert current['cycles'] < reference['cycles'], command
        print(f"{command}: {reference['cycles']} -> {current['cycles']} cycles; "
              f"pixels, messages and simulation identical; redraw={current['redraw']}")


if __name__ == '__main__':
    main()
