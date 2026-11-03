#!/usr/bin/env python3
"""Conservative selection when disk comparisons cannot establish equality."""
import sys
import subprocess
import tempfile
from unittest.mock import patch
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import test_changed
from test_changed import binary_changes


class BinarySelectionTests(unittest.TestCase):
    def test_failed_reference_tests_every_program(self):
        self.assertEqual(set(binary_changes(['snake', 'chess'], None,
                                             {'snake': 'hash'})),
                         {'snake', 'chess'})

    def test_missing_images_are_not_equal(self):
        for base, work in [({}, {}), ({'snake': None}, {'snake': None}),
                           ({'snake': 'hash'}, {}), ({}, {'snake': 'hash'})]:
            with self.subTest(base=base, work=work):
                self.assertIn('snake', binary_changes(['snake'], base, work))

    def test_only_proven_equal_images_are_skipped(self):
        self.assertEqual(set(binary_changes(
            ['snake', 'chess'], {'snake': 'a', 'chess': 'b'},
            {'snake': 'a', 'chess': 'c'})), {'chess'})


class ChangedPathTests(unittest.TestCase):
    def test_git_paths_keep_unicode_tabs_and_newlines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True)
            git('init', '-q')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                'commit', '--allow-empty', '-qm', 'initial')
            names = ['snake/café.c', 'snake/tab\tfile.c', 'snake/line\nfile.c']
            (root / 'snake').mkdir()
            for name in names:
                (root / name).write_text('test')
            # Cover both the tracked diff and the untracked listing.
            git('add', '--', names[0], names[1])
            with patch.object(test_changed, 'git', side_effect=git):
                self.assertEqual(test_changed.changed_files('HEAD'), sorted(names))


if __name__ == '__main__':
    unittest.main()
