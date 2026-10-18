#!/usr/bin/env python3
"""Compare guide cancellation with the same code forced through full rendering.

Patch only the return JMP operand while stopped at guidance_leave. Visible
pixels exclude HGR screen holes, which are native simulation scratch.
"""
from common import DISK, L, a2test, text_screen
from test_guidance import start, open_guide, state
from test_joystick_journey import event, IDLE
from test_save import differing
from test_screen_returns import visible

LIMIT = 60000


def command(s, text):
    s.step('key:' + text)
    s.step('press:\\r')
    s.step(L.until('do_command', LIMIT))
    s.step(IDLE)


def pixels(s):
    raw = s.step('peek:2000:8192').data
    assert len(raw) == 16384, 'Both visible DHGR banks are required'
    return visible(raw)


def run(force, dark):
    with a2test.Session(DISK, timeout=900) as s:
        start(s)
        if dark:
            # Set a deterministic test hour, then let native WAIT update sky,
            # weather, thermal state and night gating before the measurement.
            for offset, value in enumerate((133, 48, 0, 0, 0)):  # 22:00
                s.step(L.poke('s_hour', value, offset))
            command(s, 'WAIT 1 MIN')
            assert s.step(L.peek('night')).data[0], 'Native night setup failed'
        else:
            assert not s.step(L.peek('night')).data[0]
        # Clear the welcome/result once and settle the shared text prompt.
        event(s, 'up')
        event(s, 'cancel', IDLE)
        picture_before = pixels(s)
        open_guide(s)
        before = state(s)
        # Stop before cancellation clears UI scratch; only baseline's JMP
        # destination differs. Exclude identical input polling from timing.
        s.step('btn:1,1')
        beginning = s.step(L.until('guidance_leave', LIMIT)).cycles[-1]
        jump = L['guidance_leave'] + 5  # LDA #0 / STA dep_mask
        assert s.step(f'peek:{jump:04X}:3').data == bytes((
            0x4C, L['back_to_view_now'] & 255, L['back_to_view_now'] >> 8))
        if force:
            s.step(f'poke:{jump + 1:04X}:{L["show_view"] & 255:02X}')
            s.step(f'poke:{jump + 2:04X}:{L["show_view"] >> 8:02X}')
        out = s.step(IDLE)
        after = state(s)
        assert not differing(before[0], after[0], {L['scene_cache_valid']}), ('simulation', dark, force)
        assert before[1] == after[1], ('RNG', dark, force)
        picture_after = pixels(s)
        assert picture_after == picture_before, ('visible banks changed', dark, force)
        return dict(cycles=out.cycles[-1] - beginning, state=after,
                    pixels=picture_after,
                    text=text_screen(s.step('peek:0400:1024').data)[20:])


def main():
    for dark in (False, True):
        current, reference = run(False, dark), run(True, dark)
        assert not differing(current['state'][0], reference['state'][0], {L['scene_cache_valid']})
        assert current['state'][1] == reference['state'][1]
        assert current['pixels'] == reference['pixels']
        # Full rendering can leave the guide footer (day) or print
        # NOT ENOUGH LIGHT (night) in the message half. Compare the native
        # action grid and prompt; cancellation must clear its guide hint.
        assert [line[40:] for line in current['text']] == [line[40:] for line in reference['text']]
        assert current['text'][3] == reference['text'][3]
        assert 'UP/DOWN NEED' not in current['text'][2], current['text']
        assert current['cycles'] < reference['cycles']
        print(f"GUIDANCE cancel {'night' if dark else 'day'}: "
              f"{reference['cycles']} -> {current['cycles']} cycles; "
              'both DHGR banks, action grid, prompt, native state and RNG identical; guide footer cleared')


if __name__ == '__main__':
    main()
