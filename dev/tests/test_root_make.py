#!/usr/bin/env python3
"""Root builds and test tiers must not race on shared game artifacts."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RootMakeTests(unittest.TestCase):
    def test_parallel_invocation_orders_build_and_test_tiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            game = work / 'game'
            game.mkdir()
            # A test requires the completed build, and both tiers use one
            # artifact directory. mkdir fails if their lifetimes overlap.
            (game / 'Makefile').write_text(
                'all:\n\t@sleep 0.2; touch built\n'
                'test test-long:\n\t@test -f built\n'
                '\t@mkdir active\n\t@sleep 0.2\n'
                '\t@echo $@ >> ran\n\t@rmdir active\n'
                '.PHONY: all test test-long\n')
            result = subprocess.run(
                ['make', '-j4', '-f', str(ROOT / 'Makefile'), 'test-all',
                 'DIRS=game', 'TESTED=game', 'DEV_CHECKS='],
                cwd=work, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((game / 'ran').read_text().splitlines(),
                             ['test', 'test-long'])


if __name__ == '__main__':
    unittest.main()
