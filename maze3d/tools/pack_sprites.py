#!/usr/bin/env python3
"""Maze3D asset manifest; packing is shared in dev/tools/assets."""
import sys
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GAME.parent / "dev/tools/assets"))
from pack_hgr_sprites import pattern, packed, emit

SOURCES = (("sprites_trollkind.asm", "troll_goblin_pat"),
           ("sprites_trollkind.asm", "troll_orc_pat"),
           ("sprites_characters.asm", "char_necromancer_m_pat"),
           ("maze3d.s", "dragon_pat"))


def main():
    sources = [(GAME / "src" / file, label) for file, label in SOURCES]
    (GAME / "build/packed_sprites.inc").write_text(emit(sources, "packed_mob"))


if __name__ == "__main__":
    main()
