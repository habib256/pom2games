#!/usr/bin/env python3
"""Read actual DHGR glyphs: a stable priority names an accessible action."""
from common import DISK, L, a2test, dhgr_page
from test_guidance import state
from test_save import differing, DERIVED_BYTES
import dhgr_ui


def main():
    for field, value, offset, expected in (
            ('ui_previous', 1, 3, 'BODY: WARM'),
            ('ui_previous', 2, 3, 'BODY: COOL'),
            ('wet_mode', 2, 0, 'BODY: WET'),
            ('thermal_mode', 1, 0, 'GEAR: COOL'),
            ('thermal_mode', 2, 0, 'GEAR: WARM')):
        with a2test.Session(DISK) as s:
            idle = L.until('idle', 60000)
            s.step(idle)
            for name in ('nature_frequency', 'ui_pending', 'thermal_mode',
                         'wet_mode', 'tree_in', 'shelter_inside', 'animal_kind'):
                s.step(L.poke(name, 0))
            for index in (3, 5):
                s.step(L.poke('ui_previous', 0, index))
            s.step(L.poke(field, value, offset))
            s.step(L.poke('ui_dirty', 1))
            before = state(s)
            # Exercise the real HUD renderer without a command recomputing
            # the deliberately selected observed alert into another state.
            address = L['idle']
            original = s.step(f'peek:{address:04X}:6').data
            target = L['summary_prepare']
            code = (0x20, target & 255, target >> 8,
                    0x4C, address & 255, address >> 8)
            for index, octet in enumerate(code):
                s.step(f'poke:{address + index:04X}:{octet:02X}')
            s.step(L.until('summary_prepare', 60000))
            s.step(f'until:{address + 3:04X}:60000')
            for index, octet in enumerate(original):
                s.step(f'poke:{address + index:04X}:{octet:02X}')
            after = state(s)
            # Rendering consumes its display-dirty flag, not simulation.
            assert not differing(before[0], after[0], DERIVED_BYTES | {L['ui_dirty']}), expected
            assert before[1] == after[1], expected
            actual = dhgr_ui.panels(dhgr_page(s.step('peek:2000:8192').data))[1]
            assert actual == expected, (expected, actual)
    print('Actionable HUD: actual warm/cool/wet and gear glyphs fit, with native state/RNG preserved: OK')


if __name__ == '__main__':
    main()
