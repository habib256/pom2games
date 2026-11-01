#!/usr/bin/env python3
"""Two-voice tunes for the one-bit speaker player (src/duet.inc): the tunes
and the encoder are shared with CHROMABREAK in dev/tools/audio/breakout_tunes.py;
this writes src/music_aux.inc, music_offsets.inc and music_fanfare.inc."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools/audio'))
import breakout_tunes  # noqa: E402

breakout_tunes.write(Path(__file__).resolve().parents[1] / 'src')
