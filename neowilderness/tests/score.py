"""tests/score.py: the score and hall of fame reference, for the tests.

docs/SCENARIOS.md names the reference tests/score.py; the single source is
tools/score_ref.py (also used by tools/genhof.py). This module re-exports it
so tests import `score` without duplicating a formula.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from score_ref import *  # noqa: E402,F401,F403
from score_ref import score, Hof, end_screen, hall_screen, menu_best_cells  # noqa: E402,F401
