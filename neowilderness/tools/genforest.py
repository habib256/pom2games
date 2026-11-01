# Shared with Wilderness: the one copy is ../../wilderness/<this folder>/<this
# name>. It runs here, in this module, so __file__ (HERE, common, gendata...)
# stays this game's.
from pathlib import Path as _Path
_SHARED = _Path(__file__).resolve().parents[2] / 'wilderness' / _Path(__file__).parent.name / _Path(__file__).name
exec(compile(_SHARED.read_text(), str(_SHARED), 'exec'))
