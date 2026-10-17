#!/usr/bin/env python3
"""Native USE FIRE priorities and remedies, STATUS preview through joystick."""
import tempfile
from common import disk_with
from test_care_water_preview import fixture
from test_care_presence import fire


def main():
    with tempfile.TemporaryDirectory() as tmp:
        dry = disk_with(tmp, fixture())
        for burning in (0, 1, 2):
            fire(dry, burning)
        for wind in (40, 41, 255):
            for fuel in (False, True):
                fire(dry, 1, wind=wind, fuel=fuel)
        for fuel in (False, True):
            fire(dry, 1, rain=True, wind=41, fuel=fuel)
            fire(dry, 1, immersed=True, rain=True, wind=41, fuel=fuel)
        # The shelter warning bypasses water and storm, but needs a fire.
        fire(dry, 1, inside=True, rain=True, wind=255, immersed=True)
        fire(dry, 0, inside=True, rain=True, wind=255, immersed=True, fuel=True)
        fire(dry, 2, inside=True, rain=True, wind=255, fuel=True)
        # A legacy adjacent bank is a water source, not immersion for FIRE.
        fire(disk_with(tmp, fixture(False, (21, 20, 128))), 1)
        # Exact fine cell, including the other half of a coarse cell.
        fire(disk_with(tmp, fixture(True, (40, 40, 128))), 1, immersed=True, native=True)
        fire(disk_with(tmp, fixture(True, (40, 40, 192))), 1, immersed=True, native=True, fuel=True)
        fire(disk_with(tmp, fixture(True, (41, 40, 128))), 1, native=True)
    print('Care fire context: OK')


if __name__ == '__main__':
    main()
