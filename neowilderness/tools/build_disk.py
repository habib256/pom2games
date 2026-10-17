#!/usr/bin/env python3
"""Build the Neowilderness ProDOS volume (Apple IIe enhanced / IIc, 128 KB).

The volume holds PRODOS, NEOWILD.SYSTEM (src/boot.s), the common trunk
NEOWILD.DAT and one pack per region, NEOWILD.R1..R6 (lot 7). NEOWILD.SYSTEM
reads the trunk at boot, shows the start menu, then reads the pack of the
chosen region only. Both kinds of file have the same format and go through
the same loader loop. Main RAM images go to their linked addresses; every
module, the pristine simulation and the sprites go to auxiliary RAM, where
memory.s copies them into their execution windows. A native map (header byte
37: the Sierra comparison maps, mkmap --native; only through --map, i.e. in
the Sierra Nevada pack) carries its 224 x 168 fine geography: it becomes a
compressed atlas (tools/geo_atlas.atlas_bytes) loaded with its decoder
(src/geoaux.s) by the pack into the auxiliary language card, bank 1 view
$D480-$F0FF, the area of the TOPO snapshot, which native maps do without
(lot 5, ported from commit 9795a58). A map whose atlas exceeds that budget
is refused. NEOWILD.END (the end-of-game module, src/hof.s) and NEOWILD.HOF (the
hall of fame, one block) are plain files read and written at the end of a
journey (lot 7 step 6, docs/HOF.md). NeoWildernessXL adds NEOWILD.BLK
(docs/MEMORY.md 14): four rarely loaded modules read by block number during
the game instead of living in the auxiliary store.

A file is a 256-byte record table followed by the payloads, back to back.
Record: kind, address, length, stored length; kind 0 end, 1 claim, otherwise
$80 | $40 (LZ, tools/pack_boot.py) | bank (0 main, 1 auxiliary, 2 auxiliary
language card bank 2, 3 bank 1). Stored data never exceeds 8 KB.

Trunk: WILDERNESS, the claim, the auxiliary store of every common module
(the wreck sprite included, a single sprite on the Journey side; entry 9,
the hut, waits for MAKE HUT, TODO lot 3: the fixed cabin is drawn as the log
or the rock of NEOWILD.BLK), LOWPAGE, $0926-$1FFF, WILDGAME, RESIDENT and the
menu of the four
80-column rows (src/menu.s: $BA00 resident, and its grid read at $AF00 then
hidden in the HGR rows 176-191; the loader reads with its own I/O buffer).
Pack: the 2-4 animal sprites (modules 6, 7, 8, 23) in the auxiliary space
the trunk leaves free, the region's patches of four module images (rates and
filters of the four animal records into TRAVEL fauna_travel, reaction thresholds into OUTDOOR fauna_reactions, sprite sizes
into PROJECT proj_sprites, the IGNORE/MOVE hint into SUMMARY summary_quiet;
all derived from the 128-byte animal records $6000-$607F of the region
header by fauna_patches), the woodland mask ($0800), the region's DHGR mood
and sprite colour tables (build/dhgr/dhgr_tables_rN.bin, tools/gendhgr.py),
the region texts ($5780), the whole module directory, then the map ($7000;
last, since auxiliary LZ records decode through $7000). The trunk's images
hold the Sierra Nevada: its pack rewrites the same bytes.
"""
import argparse
import hashlib
from fractions import Fraction
import json
import re
import struct
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
DEV = HERE.parent / 'dev'
sys.path.insert(0, str(DEV / 'tools/prodos'))
sys.path.insert(0, str(HERE / 'tools'))
from build_volume import Volume, prodos_date   # noqa: E402
from pack_boot import compress, decompress     # noqa: E402
from re_graphics import decode                  # noqa: E402
import dhgr_palette as P                        # noqa: E402
import geo_atlas                                # noqa: E402

VOLUME = 'NEOWILDERNESS'
CHUNK = 0x2000
TABLE_SIZE = 256                 # src/boot.s TABLE_SIZE: 36 records (direction 3: more pieces)
MAIN, AUX, LC2, LC1 = 0, 1, 2, 3
MLC2 = 0x20 | LC2                # record bank: bank 2 of the MAIN language card (lot 7)
BANK_NAMES = {AUX: 'aux', LC2: 'lc2', LC1: 'lc1', MLC2: 'mlc2'}
DIR_BANK = {AUX: 0, LC2: 1, LC1: 2, MLC2: 3}      # memory.s directory bank codes
# Auxiliary regions, in allocation order. $0000-$07FF holds the ProDOS /RAM
# driver code ($0200-$03FF) and the 80-column text page; $2000-$3FFF is the
# auxiliary half of the DHGR page.
# Lot 4: the language card keeps $DC00-$DE2F of bank 2, bank 1 and the
# common area $E000-$FFCF for the snapshot of the view under TOPO
# (src/topo_dhgr.s, 12,800 bytes). Lot 7 adds the free end of bank 2.
# Lot 7: bank 2 of the MAIN language card, which ProDOS 8 leaves free past its
# QUIT code ($D100-$D3FF; measured: $D400-$DFFF untouched after the boot and
# the loader), joins the store; $DE18-$DFFF holds the star list and drawing
# code (docs/STARS.md: 160 entries of 2 bytes, 36 buckets, the code).
# Direction 3 (docs/MEMORY.md section 12): the snapshot is compressed into
# bank 1 and $E000-$F0FF (src/topo_dhgr.s TP_SNAP_END, the native atlas's
# geo_atlas.ATLAS_END): the whole of bank 2 and $F100-$FFF9 of the common
# area join the store.
SNAP_END = 0xEC00
REGIONS = [(AUX, 0x4000, 0xBF00), (AUX, 0x0800, 0x2000), (LC2, 0xD000, 0xE000),
           (LC2, SNAP_END, 0xFFFA), (MLC2, 0xD400, 0xDE18)]
SKYLC = (MLC2, 0xDE18, 'wildskylc.bin')     # src/stars_draw.s, runs in place
# Direction 3: the unrolled DHGR rows and their entry tables (src/dhgr.s,
# segment DROWS) run in place at the start of the main card's store.
DROWS = (MLC2, 0xD400, 'wilddrows.bin')
# Docs/MEMORY.md 14: the LZ decoder of mem_fetch (src/memory.s, segment LZCODE)
# runs in place in $D001-$D0FF of that bank, unused by ProDOS 8 ($D000 is its
# bank signature, $D100-$D3FF its QUIT code).
LZLC = (MLC2, 0xD001, 'wildlzlc.bin')
# Docs/MEMORY.md 15: ProDOS's QUIT code area $D100-$D3FF of that bank holds
# five routines of the view (src/dhgr.s B2_ENTRY) during the game: the loader
# puts the QUIT code aside in the exit state at the claim, before this
# record, and every exit puts it back.
B2LC = (MLC2, 0xD100, 'wildb2.bin')
SNAPSHOT = [(LC1, 0xD000, 0xE000), (LC2, 0xE000, SNAP_END)]
# Native maps only: the fine geography takes bank 1 and the common area
# instead of the snapshot (src/geoaux.s, src/topo_dhgr.s tp_save).
GEO_CACHE = 0xD000               # 4 decoded tiles + woodland, not stored
GEO_CODE = 0xD480                # src/geoaux.s (segment GEOAUX), then the atlas
G = 'original_graphics/'
# Directory index -> (image, execution window) of the common trunk. 18 is the
# animated campfire (src/fire.s; overlay_load turns 18 into 17 by itself and
# never fetches the entry), read from NEOWILD.BLK on both editions (FIRE_DIR).
# 25 is the hourly star module (docs/STARS.md); 24 (hall of
# fame) is read from the disk at the end of a game (NEOWILD.END), so its
# entry holds the head of the star catalogue (462 bytes: it fills the
# 464-byte hole of the auxiliary card), which the star module copies in
# front of itself: both run in the SIM window (free while the simulation is
# not loaded: show_view_scene, docs/STARS.md). Their windows come from
# build/wild.lbl (st_cat, st_cat2).
MODULES = {0: ('wildtpg.bin', 0x9600), 1: ('wildvoc.bin', 0x5800),
           3: ('wildsim.bin', 0x9600), 4: ('wildcamp.bin', 0x5800),
           5: (G + 'wreck.bin', 0x5800),
           10: ('wildsit.bin', 0x5800),
           11: ('wildprj.bin', 0x5800), 12: ('wildtrv.bin', 0x5800), 13: ('wildinp.bin', 0x5800),
           14: ('wilditm.bin', 0x5800), 15: ('wildhud.bin', 0x5800), 16: ('wildsta.bin', 0x9600),
           17: ('wildmed.bin', 0x5800), 19: ('wildmvi.bin', 0x5800), 20: ('wildtre.bin', 0x5800),
           18: ('wildfire.bin', 0x9600), 21: ('wildadv.bin', 0x5800), 22: ('wildout.bin', 0x5800),
           24: ('wildskycat.bin', 0x9600), 25: ('wildsky.bin', 0x97CE),
           26: ('wildori.bin', 0x5800), 27: ('wildalr.bin', 0x5800),
           9: ('wildcrf.bin', 0x9600),
           28: ('wildtxb.bin', 0x0000), 31: ('wildfrg.bin', 0x9600),
           32: ('wildgrid.bin', 0xA300), 33: ('wildeqp.bin', 0x5800)}
DIR_ENTRIES = 34                 # memory.s MOD_COUNT
ZP_ENTRY, ZP_AUX = 30, 0xBF00    # ProDOS's zero page during the game (src/boot.s)
# The text bank (src/textbank.s): entry 28, never loaded whole; entry 29 is
# the scratch entry of memory.s text_fetch (its bank and destination here).
TB_DIR, TB_FETCH = 28, 29
# Docs/MEMORY.md 15: entry 2 is the exit state, written by the loader at the
# claim (src/boot.s ld_claim, at the address patched into ld_exit), never by
# a record: ProDOS's bitmap and RESET vector at entry, the /RAM unit and
# ProDOS's QUIT code (memory.s EX_SIZE bytes), which the exit path in INPUT
# copies to EX_BUF (the QUIT code then back to bank 2).
# It sits in auxiliary $4000-$BEFF, just below the packs' sprite area.
EXIT_ENTRY, EXIT_BUF = 2, 0x2000
# Modules stored LZ-packed in the auxiliary store and decoded in their window
# by mem_fetch (src/memory.s lz_unpack; docs/MEMORY.md 13): the rarely loaded
# ones (TOPOGEN, CAMP, the wreck, ITEMS, STATUS with its five
# pages, MEDVIEW, TREE, ORIENT, ADVENTURE: start, end, the day's weather,
# JOURNEY DONE, the clothes of a native map) and ALERT (after a health update: 40 cycles more per byte,
# under 0.5 % of a REST), whose decoding (about 50 cycles per byte instead
# of 17 for a copy) never runs during a view. INPUT (13) and the text bank
# stay raw; the packs patch TRAVEL, OUTDOOR, PROJECT and SUMMARY in place.
LZ_MODULES = (0, 1, 4, 5, 14, 16, 19, 20, 21, 26, 27)
# Docs/MEMORY.md 28: the store of the six packs (XL, the comparison disks)
# packs the grid's module (32) too, for the animal's background (OUTDOOR
# ab_copy): 2,676 -> 2,441 bytes, about 0.1 s more per choice of the grid.
# The 140 KB edition kept it raw until 16 October 2026 (LZ_140).
# CATCH durations (MEMORY.md 35): also pack the hourly star module (25),
# saving 45 bytes. It runs only when the night sky list needs refreshing.
# EQUIPMENT (33) is loaded only when its page opens; packing it makes room
# for care return logic without slowing the simulation's medical updates.
LZ_SIX_PACKS = (25, 32, 33)
# Docs/MEMORY.md 30 (16 October 2026): since the OBJECTS page of transfers
# the 140 KB edition packs the grid's module too (its store is full; its
# NEOWILD.DAT has room again since the saved games take four blocks).
# The taller OBJECTS layout also packs MEDICAL (17) on 140 KB.
LZ_140 = (3, 17, 25, 32)
# The animals of the packs too: one sprite at most is loaded per view
# (sprites.s scene_prepare), about 40 cycles more per byte, under 1 % of a
# full view (6.1 million cycles).
LZ_SPRITES = True
BANK_LZ = 0x80                   # memory.s BANK_LZ; bits 2-6: the margin
# Docs/MEMORY.md 14: modules read from the disk during the game (memory.s
# disk_fetch, MLI READ_BLOCK into their $5800 window), edition by edition
# (EDITIONS disk_modules). NEOWILD.BLK: a header block (BLK_SIGNATURE, then a
# 2-byte id of the file's contents; the loader checks both, src/boot.s
# ld_blk), then each module raw, padded to whole blocks. Its name sorts
# before every other file of the volume: Volume allocates it first, index
# block 7 and data from block 8 (BLK_FIRST, checked on the image), so the
# block numbers are known before NEOWILD.DAT, which holds the directory.
BANK_DISK = 0x40                 # memory.s BANK_DISK: source = first block
BLK_FIRST = 8
# Lot 4 (docs/FORAGE.md 17): FORAGE (31) runs in the SIM window and is read
# from NEOWILD.BLK on every disk (src/forage.s forage_gate frees ProDOS's
# bitmap of $90-$AF around the read); whole blocks must stay below the
# grid of the menu ($B000, src/menu.s MENUSWAP).
FORAGE_DIR = 31
# The animated campfire (docs/CAMP.md 8) too: read into the SIM window when
# the fire appears at the prompt (src/fire.s fire_tick, sim_fetch), on both
# editions and every comparison disk; it takes no byte of the store.
FIRE_DIR = 18
# TOPOGEN (docs/MEMORY.md 18): the TOPO page's sheet, read when the page
# opens (src/sites.s module_graphical_topo, sim_fetch) on both editions:
# its 2.7 KB of store made room for the grid's module (GRID, entry 32).
TOPO_DIR = 0
# Lot 3 (docs/CRAFT.md): the MAKE recipes, CRAFT (9, the hut's old entry),
# read by CAMP into the SIM window at a MAKE or a USE of a shelter or weapon
# (src/camp.s camp_craft), on both editions.
CRAFT_DIR = 9
ALWAYS_DISK = (TOPO_DIR, CRAFT_DIR, FIRE_DIR, FORAGE_DIR)
# Site sprites (lot 6, docs/MEMORY.md 19): the log and the rock of a natural
# shelter found on a native map, the ranger outpost at the goal. Raw, after
# the modules of NEOWILD.BLK on every disk, read into the SIM window when a
# view shows them (src/project.s module_site_load, through the scratch entry
# TB_FETCH); PROJECT's site_blocks/site_heads are written here.
SITE_SPRITES = ('log', 'rock', 'outpost', 'tent', 'cabin', 'igloo', 'trench')
# Lot 3 step 3 (docs/CRAFT.md 8.4): the built shelters, the tent, the hut
# (cabin.bin), the igloo and the trench, are site sprites too, on
# NeoWildernessXL and the comparison disks only: the 140 KB edition has no
# room for their 8 blocks (EDITIONS shelters), PROJECT finds site_blocks 0
# there and draws no built shelter.
SHELTER_SPRITES = SITE_SPRITES[3:]
SITE_WINDOW = 0x9600
SITE_HEAD = 4                    # bytes of each image compared in the window
DISK_END = {0x5800: 0x6000, 0x9600: 0xB000}
# Docs/MEMORY.md 29: STATUS (16) of NeoWildernessXL, read from NEOWILD.BLK with
# its tail (the post-its), runs up to $B5FF, over the grid's image as when
# it was decoded from the store (get_line gathers the grid again).
STATUS_DIR = 16
DISK_LIMIT = {STATUS_DIR: 0xB600}
BLK_SIGNATURE = b'NWBK'
DISK_WINDOW = 0x5800
LZ_MARGIN = 31
# Species slots 1-4 of a region -> module IDs (animal_kind = slot + 5; the
# fourth species takes 23, SCENARIOS.md section 4).
SLOT_MODULES = (6, 7, 8, 23)
# Sprite of each animal record, from the global animal id of the MS-DOS
# .CIM files (regions.SPRITE_ORDER, build/regions/fauna.json). Chile reuses
# Bolivia's puma.
REGION_SPRITES = P.REGION_ANIMALS
PACK_REGIONS = tuple(range(1, 7))
EMPTY_SPRITE = b'\0'             # a sprite of no column (sprites.s: cmp $5800)
TEXT_SIZE = 128                  # memory.s REGIONTEXT
# Boot costs measured in POM2 (IIe, Disk II, ProDOS 2.4.3; docs/MEMORY.md):
# guest cycles per stored byte read through MLI READ, per byte LZ-decoded.
DISK_CYCLES = 200
DECODE_CYCLES = 46
WINDOW_LIMIT = {0x0000: 0x2000, 0x5800: 0x0800, 0x9600: 0x2000, 0x2000: 0x2000, 0x97CE: 0xB600 - 0x97CE,
                0xA300: 0xB000 - 0xA300}


def labels(build):
    return {name: int(addr, 16) for addr, name in
            re.findall(r'^al ([0-9A-Fa-f]+) \.(\w+)$', (build / 'wild.lbl').read_text(), re.M)}


def place(images, free=None):
    """Deterministic placement: {index: (bank, address)}, remaining [bank, start, end].

    First fit, largest first; when that fragments the space, a depth-first
    search over the regions (largest images first) finds a fit if one exists.
    `free` is a list of [bank, start, end]; default REGIONS.
    """
    free = [list(region) for region in (free if free is not None else REGIONS)]
    order = sorted(images, key=lambda i: (-len(images[i]), str(i)))
    room = [region[2] - region[1] for region in free]
    choice = {}

    def first_fit():
        left = list(room)
        for index in order:
            for k, size in enumerate(left):
                if size >= len(images[index]):
                    choice[index] = k
                    left[k] -= len(images[index])
                    break
            else:
                return False
        return True

    def search(n, left, seen):
        if n == len(order):
            return True
        key = (n, tuple(left))
        if key in seen or len(seen) > 200000:      # bounded: a full store fails fast
            return False
        seen.add(key)
        size = len(images[order[n]])
        for k in range(len(left)):
            if left[k] >= size:
                left[k] -= size
                choice[order[n]] = k
                if search(n + 1, left, seen):
                    return True
                left[k] += size
        return False

    if not first_fit() and not search(0, list(room), set()):
        raise SystemExit(f'auxiliary memory full: {sum(map(len, images.values()))} bytes '
                         f'for {sum(room)} free')
    placed = {}
    for index in order:
        region = free[choice[index]]
        placed[index] = (region[0], region[1])
        region[1] += len(images[index])
    return placed, free


def lz_tokens(packed, size):
    """The (match, bytes) tokens of a pack_boot stream of `size` bytes."""
    tokens, pos, out = [], 0, 0
    while out < size:
        flags = packed[pos]
        pos += 1
        for bit in range(8):
            if out >= size:
                break
            if flags >> bit & 1:
                length = (packed[pos + 1] & 15) + 3
                token = packed[pos:pos + 2]
                if length == 18:
                    length += packed[pos + 2]
                    token = packed[pos:pos + 3]
                tokens.append((True, bytes(token), length))
                pos += len(token)
                out += length
            else:
                tokens.append((False, packed[pos:pos + 1], 1))
                pos += 1
                out += 1
    assert pos == len(packed) and out == size
    return tokens


def lz_stream(raw, cache=None):
    """pack_boot tokens of `raw` and an end token (a match of distance 0):
    (stream, tokens)."""
    tokens = lz_tokens(cached_compress(raw, cache), len(raw)) + [(True, b'\0\0', 0)]
    stream = bytearray()
    for k in range(0, len(tokens), 8):
        group = tokens[k:k + 8]
        stream.append(sum(match << bit for bit, (match, _, _) in enumerate(group)))
        for _, token, _ in group:
            stream.extend(token)
    return bytes(stream), tokens


def unpack_stream(stream):
    """The bytes of an lz_stream (the stub of NEOWILD.SYSTEM, src/boot.s)."""
    out, i = bytearray(), 0
    while True:
        flags = stream[i]
        i += 1
        for bit in range(8):
            if not flags >> bit & 1:
                out.append(stream[i])
                i += 1
                continue
            lo, hi = stream[i], stream[i + 1]
            i += 2
            if not lo and not hi:
                return bytes(out)
            distance, length = lo | (hi >> 4) << 8, (hi & 15) + 3
            if length == 18:
                length += stream[i]
                i += 1
            for _ in range(length):
                out.append(out[-distance])


def system_file(build, sym, marks, prepare_length, cache=None, regions=6, blk=bytes(8), exit_at=0,
                name='NEOWILD.SYSTEM'):
    """NEOWILD.SYSTEM: the stub (SYSSTUB), then the loader with its marks
    (ld_marks), the edition's scenario count (ld_regions), NEOWILD.BLK's
    first block and signature (ld_blk, zeros without it) and the address of
    the exit state (ld_exit), LZ-packed; the stub decodes it to
    __LOADER_RUN__."""
    raw = (Path(build) / name).read_bytes()
    at = sym['__LOADER_LOAD__'] - 0x2000
    loader = bytearray(raw[at:])
    assert len(loader) == sym['__LOADER_SIZE__']
    if regions == 1:
        # These menu parts are never used by the 140 KB edition. Keep the
        # linked addresses but compress zeros, preserving its five saves.
        for first, last in (('m_title_xl', 'm_title'), ('m_more', 'm_free_1')):
            a, b = (sym[n] - sym['__LOADER_RUN__'] for n in (first, last))
            loader[a:b] = bytes(b - a)
    mark = sym['ld_marks'] - sym['__LOADER_RUN__']
    assert loader[mark:mark + 23] == bytes(23), 'NEOWILD.SYSTEM ld_marks'
    loader[mark:mark + 23] = b''.join(m.to_bytes(3, 'little') for m in marks) + \
        prepare_length.to_bytes(2, 'little')
    count = sym['ld_regions'] - sym['__LOADER_RUN__']
    assert loader[count] == 0, 'NEOWILD.SYSTEM ld_regions'
    loader[count] = regions
    blk_at = sym['ld_blk'] - sym['__LOADER_RUN__']
    assert loader[blk_at:blk_at + 8] == bytes(8) and len(blk) == 8, 'NEOWILD.SYSTEM ld_blk'
    loader[blk_at:blk_at + 8] = blk
    exit_ptr = sym['ld_exit'] - sym['__LOADER_RUN__']
    assert loader[exit_ptr:exit_ptr + 2] == bytes(2) and 0x4000 <= exit_at < 0xBF00, 'NEOWILD.SYSTEM ld_exit'
    loader[exit_ptr:exit_ptr + 2] = exit_at.to_bytes(2, 'little')
    stream = lz_stream(bytes(loader), cache)[0]
    assert unpack_stream(stream) == loader
    return raw[:at] + stream, bytes(loader)


def lz_store(raw, window, cache=None):
    """An image for the store, decoded in place by lz_unpack: (blob, copy
    address, margin) or None when it would not be shorter. The blob is the
    window address, then the tokens and an end token (a match of distance 0).
    The copy ends `margin` bytes past the image's own end (at most 31), the
    least that keeps every unread token ahead of the output; mem_fetch keeps
    those bytes aside during the copy and the decoding and puts them back
    (src/memory.s lz_guard), so that nothing past the image changes."""
    stream, tokens = lz_stream(raw, cache)
    worst, read, written = -1, 2, 0
    for k in range(0, len(tokens), 8):
        read += 1                           # the flag byte
        for match, token, length in tokens[k:k + 8]:
            read += len(token)
            for _ in range(length):         # each written byte: o - i
                worst = max(worst, written - read)
                written += 1
    assert written == len(raw)
    blob = bytes((window & 255, window >> 8)) + bytes(stream)
    margin = max(0, worst + 1 - len(raw) + len(blob))
    if len(blob) >= len(raw) or margin > LZ_MARGIN:
        return None
    copy = window + len(raw) + margin - len(blob)
    assert lz_unpack(blob, copy) == raw
    return blob, copy, margin


# NeoWildernessXL (decision of 15 October 2026, docs/MENUS.md 9): the
# MouseText pages. The linked images are the 140 KB edition's; the XL edition
# (and the comparison disks of the tests) take copies with a tail appended
# (segments STATX, CRAFTX, MEDVX) and the bytes of the XLPATCH records
# (src/mousetext.inc XL_*: image, address, byte) written: build/*-xl.bin,
# NEOWILD-xl.SYSTEM. Image code -> (file, address of its first byte, tail
# file, label of the tail's first byte).
XL_IMAGES = {16: ('wildsta.bin', 0x9600, 'wildstx.bin', 'stx_base'),
             9: ('wildcrf.bin', 0x9600, 'wildcrx.bin', 'crx_base'),
             19: ('wildmvi.bin', 0x5800, 'wildmvx.bin', 'inventory_keys_x'),
             0x80: ('wildhof.bin', 0x9600, 'wildendx.bin', 'endx_base'),
             0x81: ('NEOWILD.SYSTEM', None, None, None),
             0x82: ('wildmenusw.bin', 0xB000, None, None),
             0x83: ('wild.bin', 0x6000, None, None),
             0x84: ('wildmenu.bin', 0xBA00, None, None),
             0x85: ('wildpg.bin', 0x0200, None, None),
             0x86: ('wildgame.bin', 0x4000, None, None)}
# Resident code of the XL edition, position independent, copied over shared
# code that XL never runs: (image code, file, first label, end label of the
# room). xl_pad (src/mt_pages.s, the grid's boxes) over page_foot: the XL
# pages call page_foot_x instead.
XL_COPIES = [(0x83, 'wildxlr.bin', 'page_foot', 'pg_lines')]


def xl_name(name):
    stem, dot, ext = name.partition('.')
    return f'{stem}-xl.{ext}'


def xl_files(build, sym):
    """Write the XL copies of XL_IMAGES; {file: XL file}."""
    build = Path(build)
    records = (build / 'wildxlp.bin').read_bytes()
    assert len(records) % 4 == 0, 'build/wildxlp.bin: 4-byte records'
    images, shared = {}, {}
    for code, (name, base, tail, label) in XL_IMAGES.items():
        data = bytearray((build / name).read_bytes())
        if code == 0x81:                # the loader, past the stub
            base = sym['__LOADER_RUN__'] - (sym['__LOADER_LOAD__'] - 0x2000)
        shared[code] = len(data)
        if tail:
            start = sym[label] - base
            assert len(data) <= start, (name, 'reaches its XL tail')
            data += bytes(start - len(data)) + (build / tail).read_bytes()
        images[code] = (data, base)
    for code, name, first, end in XL_COPIES:
        data, base = images[code]
        code_bytes = (build / name).read_bytes()
        assert first in sym and sym[first] + len(code_bytes) <= sym[end], ('XL copy', name, first)
        data[sym[first] - base:sym[first] - base + len(code_bytes)] = code_bytes
    zero = (build / 'wildxlz.bin').read_bytes()
    for k in range(0, len(zero), 5):          # XL_ZERO: code XL never runs
        code, first, last = zero[k], zero[k + 1] | zero[k + 2] << 8, zero[k + 3] | zero[k + 4] << 8
        data, base = images[code]
        assert 0 <= first - base < last - base <= shared[code], ('XL_ZERO', code, hex(first), hex(last))
        data[first - base:last - base] = bytes(last - first)
    for k in range(0, len(records), 4):
        code, address, value = records[k], records[k + 1] | records[k + 2] << 8, records[k + 3]
        data, base = images[code]
        offset = address - base
        assert 0 <= offset < len(data), ('XL byte outside the image', code, hex(address))
        data[offset] = value
    out = {}
    for code, (data, _) in images.items():
        name = XL_IMAGES[code][0]
        (build / xl_name(name)).write_bytes(bytes(data))
        out[name] = xl_name(name)
    return out


def module_image(build, module):
    """The raw image of a layout.json module entry, with the bytes this
    disk writes into it (PROJECT: site_project)."""
    raw = bytearray((Path(build) / module['image']).read_bytes())[:module['length']]
    for offset, value in module.get('patches', ()):
        raw[offset] = value
    return bytes(raw)


def stored_bytes(build, module):
    """The bytes a layout.json module entry occupies in the store."""
    raw = module_image(build, module)
    if 'lz' not in module:
        return raw
    return lz_store(raw, module['window'], Path(build) / 'lz-cache')[0]


def lz_unpack(blob, copy, size=None):
    """Python model of memory.s lz_unpack, in place in a 64 KB memory."""
    mem = bytearray(0x10000)
    mem[copy:copy + len(blob)] = blob
    i = copy + 2
    out = start = blob[0] | blob[1] << 8
    while True:
        flags = mem[i]
        i += 1
        for bit in range(8):
            if flags >> bit & 1:
                lo, hi = mem[i], mem[i + 1]
                i += 2
                if not lo and not hi:
                    return bytes(mem[start:out])
                distance, length = lo | (hi >> 4) << 8, (hi & 15) + 3
                if length == 18:
                    length += mem[i]
                    i += 1
                for _ in range(length):
                    assert out < i or out >= copy + len(blob), 'decoder overtakes its input'
                    mem[out] = mem[out - distance]
                    out += 1
            else:
                value = mem[i]
                i += 1
                assert out < i or out >= copy + len(blob), 'decoder overtakes its input'
                mem[out] = value
                out += 1


def cached_compress(chunk, cache):
    """compress() is an optimal parse, slow in Python: keep results by content.

    Alternate-map test disks share every image but the map.
    """
    if cache is None:
        return compress(chunk)
    path = cache / (hashlib.sha256(chunk).hexdigest() + '.lz')
    if path.exists():
        packed = path.read_bytes()
        if decompress(packed, len(chunk)) == chunk:
            return packed
    packed = compress(chunk)
    cache.mkdir(parents=True, exist_ok=True)
    path.write_bytes(packed)
    return packed


def records(sections, packing, cache=None):
    """A record file: the 256-byte record table, then the payloads back to back.

    `sections` lists (bank, address, data), or None for the claim record.
    The loader reads the table once, then each payload with one READ.
    Measured: block-aligned payloads read slower in POM2's Disk II than this
    contiguous stream through the I/O buffer (docs/MEMORY.md).
    """
    table, payloads = bytearray(), bytearray()
    stats = dict(raw=0, stored=0, records=0)
    for section in sections:
        if section is None:
            table.extend(struct.pack('<BHHH', 1, 0, 0, 0))
            continue
        bank, address, data = section
        for offset in range(0, len(data), CHUNK):
            chunk = data[offset:offset + CHUNK]
            packed = cached_compress(chunk, cache) if packing in ('lz', 'auto') else None
            if packed is not None and len(packed) < len(chunk) and (
                    packing == 'lz' or
                    DISK_CYCLES * len(packed) + DECODE_CYCLES * len(chunk)
                    < DISK_CYCLES * len(chunk)):
                assert decompress(packed, len(chunk)) == chunk
                kind, payload = 0xC0 | bank, packed
            else:
                kind, payload = 0x80 | bank, chunk
            table.extend(struct.pack('<BHHH', kind, address + offset, len(chunk), len(payload)))
            payloads.extend(payload)
            stats['raw'] += len(chunk)
            stats['stored'] += len(payload)
            stats['records'] += 1
    table.extend(struct.pack('<BHHH', 0, 0, 0, 0))
    assert len(table) <= TABLE_SIZE, 'record table too long'
    out = bytes(table + bytes(TABLE_SIZE - len(table)) + payloads)
    stats['file'] = len(out)
    data_blocks = -(-len(out) // 512)
    stats['blocks'] = data_blocks + (data_blocks > 1)    # ProDOS: + the index block
    return out, stats


def blobs(placed, images):
    """Auxiliary records: contiguous placements of one region form one blob."""
    out = {}
    for index, (bank, address) in sorted(placed.items(), key=lambda kv: (kv[1], str(kv[0]))):
        key = (bank, next(r[1] for r in REGIONS if r[0] == bank and r[1] <= address < r[2]))
        blob = out.setdefault(key, [address, bytearray()])
        if blob[0] + len(blob[1]) != address:      # a gap: start another blob
            key = (bank, address)
            blob = out.setdefault(key, [address, bytearray()])
        blob[1].extend(images[index])
    return [(bank, start, bytes(data)) for (bank, _), (start, data) in sorted(out.items())]


# ---------------------------------------------------------------------------
# Region fauna (lot 7 step 4, docs/logic/animals.md): the bytes the engine
# reads, derived from the four 32-byte animal records of the region header.
TERRAINS = (0, 10, 20, 30, 40)       # fauna_environment: rock, clear, woods, (high woods), water
# Port withdrawal after IGNORE (not an original rate): cats 25 %, snakes
# (venomous, severity exponent >= 4) 75 %, the others 50 %.
CATS = {'COUGAR', 'PUMA', 'JAGUAR', 'TIGER', 'CAT'}


def accepted(centre, width, e):
    """fauna_eligible on one dimension: d = |e - c|, signed width w."""
    d = abs(e - centre)
    if width >= 128:
        return d > 256 - width
    return d <= width if width else d > 0


def fold_water(centre, width):
    """Header byte 29 (never in water): the port's water cell is terrain 40
    on every region map (no native river code), so the gate removes 40 from
    the terrain filter. Returns the closest pair accepting the same terrains
    but water."""
    want = [e for e in TERRAINS if accepted(centre, width, e) and e != 40]
    best = None
    for c in range(256):
        for w in range(1, 128):
            if [e for e in TERRAINS if accepted(c, w, e)] == want:
                cost = abs(c - centre) + abs(w - width)
                if best is None or cost < best[0]:
                    best = (cost, c, w)
    return best[1], best[2]


def threshold(p):
    """Quantized probability of outdoor_roll: floor(256 p) + 1, 0 never, 255 at most."""
    return 0 if p <= 0 else min(255, int(p * 256) + 1)


SEVERITY = (Fraction(2, 10), Fraction(4, 10), Fraction(6, 10))


def nouns():
    sys.path.insert(0, str(HERE / 'tools'))
    from gendata import VOCAB
    return {word: number for word, kind, number in VOCAB if kind == 2}


def species_name(header, k):
    return bytes(b & 0x7F for b in header[0xD0 + 12*k:0xDC + 12*k]).split(b'\0')[0].decode('ascii')


def fauna_patches(header, region, build):
    """{symbol: bytes} of the module images for a region (see the docstring)."""
    from re_graphics import decode
    vocab = nouns()
    travel = bytearray(52)
    reactions = [bytearray(4) for _ in range(19)]
    quiet = 0
    for k in range(4):
        rec = header[32*k:32*k + 32]
        if not rec[12]:
            continue                            # no animal: rate 0, null filters
        name = species_name(header, k)
        rows = bytearray(rec[0:12])
        if rec[29]:
            rows[4], rows[5] = fold_water(rows[4], rows[5])
        travel[k] = rec[12]
        travel[4 + 12*k:16 + 12*k] = rows
        noise = threshold(Fraction(8, 10) - Fraction(3, 100) * rec[14])
        venom = rec[22] >= 4
        kind = (0x80 if rec[28] else 0) | (0x40 if venom else 3 * (rec[22] - 1)) | (
            0x20 if region == 4 and k == 0 else 0)
        values = (noise, threshold(Fraction(2, 100) * rec[14]),
                  *(threshold(Fraction(2, 100) * rec[m]) for m in range(17, 22)),       # ATTACK by means
                  *(threshold(Fraction(5, 1000) * rec[m + 6]) for m in range(17, 22)),  # (lot 3)
                  threshold(Fraction(2, 100) * rec[15]),
                  threshold(Fraction(2, 100) * rec[16]), threshold(Fraction(2, 100) * rec[13]),
                  64 if name in CATS else 192 if venom else 128, vocab[name], kind,
                  rec[30])                              # lot 4: V (src/forage.s forage_kill)
        for table, value in zip(reactions, values):
            table[k] = value
        if not noise and not quiet:
            quiet = 6 + k
    sizes = bytearray(12)
    for slot, name in enumerate(P.region_assets(region)):
        if name:
            image, _ = decode((build / G / f'{name}.bin').read_bytes())
            sizes[slot] = len(image[0])
            sizes[6 + slot] = max(y for y, row in enumerate(image) if any(c >= 0 for c in row))
    return {'fauna_travel': bytes(travel),
            'fauna_reactions': b''.join(reactions), 'proj_sprites': bytes(sizes),
            'summary_quiet': bytes((quiet,))}


# Module image of each patched symbol (directory index).
PATCH_MODULES = {'fauna_travel': 12, 'fauna_reactions': 22,
                 'proj_sprites': 11, 'summary_quiet': 15}


def region_texts(entry, header):
    """REGIONTEXT (memory.s): name 16, fauna sentence 40, four species names
    of 12, region, species count, introduction name 22; ASCII, zero padded."""
    def field(text, size):
        data = text.encode('ascii')[:size]
        return data + bytes(size - len(data))
    names = b''.join(field(bytes(b & 0x7F for b in header[0xD0 + 12*k:0xDC + 12*k])
                           .split(b'\0')[0].decode('ascii') if header[32*k + 12] else '', 12)
                     for k in range(4))
    count = sum(1 for k in range(4) if header[32*k + 12])
    out = (field(entry['name'], 16) + field(entry['fauna_sentence'], 40) + names
           + bytes((entry['region'], count)) + field(entry.get('intro_name', entry['name']), 22))
    assert len(out) == TEXT_SIZE
    return out


def region_data(build, region, map_override=None):
    """Map (with its region byte), woodland mask, header and texts of a region."""
    from mkmap import MAP_BYTES, FOREST_BYTES
    doc = json.loads((build / 'regions/regions.json').read_text())
    entry = next(e for e in doc['regions'] if e['region'] == region)
    header = (build / f'regions/r{region}.bin').read_bytes()
    if map_override is not None:
        mapdata = Path(map_override).read_bytes()
    else:
        mapdata = (build / ('map.bin' if region == 2 else f'maps/r{region}.bin')).read_bytes()
    mapdata = bytearray(mapdata)
    if mapdata[32] == 0:            # legacy Sierra map: the region byte (lot 7)
        mapdata[32] = region
    mask = bytes(mapdata[MAP_BYTES:MAP_BYTES + FOREST_BYTES]) if mapdata[26] else b''
    if len(mask) != FOREST_BYTES:
        mask = bytes(FOREST_BYTES)
    sprites = REGION_SPRITES[region]
    assert sum(1 for k in range(4) if header[32*k + 12]) == len(sprites), region
    return dict(entry=entry, header=header, map=bytes(mapdata), mask=mask, sprites=sprites)


# Every file the game only reads is locked (access $01, read only): ProDOS 8
# then never rewrites its directory entry, whatever happens to its file
# control block in memory. A CLOSE (or a flush) rewrites the entry of a file
# opened with the write right as soon as that FCB is marked modified, from the
# FCB's EOF, key block and block count; on the 13 October 2026 POM2 report,
# NEOWILD.DAT came back with EOF $003F47 instead of $00BC47 and the next boot
# stopped on "NEOWILD DISK ERROR $4C" (docs/HOF.md section 10). Only
# NEOWILD.HOF is written (hall of fame, in place).
ACCESS_READ_ONLY = 0x01
WRITE_RIGHT = 0x02


def lock_files(volume, keep):
    """Clear the write, rename and destroy rights of every file of the volume
    directory except the names in `keep`."""
    from build_volume import DIR_START, DIR_BLOCKS, ENTRY_LEN, ENTRIES_PER_BLOCK
    for n in range(DIR_START, DIR_START + DIR_BLOCKS):
        block = volume.block(n)
        for k in range(ENTRIES_PER_BLOCK):
            e = 4 + k * ENTRY_LEN
            storage, length = block[e] >> 4, block[e] & 15
            if storage not in (1, 2, 3):        # seedling, sapling, tree
                continue
            if bytes(block[e + 1:e + 1 + length]).decode('ascii') not in keep:
                block[e + 0x1E] = ACCESS_READ_ONLY


SAVE_GAMES = 5


def file_blocks(size):
    """ProDOS blocks of a file: data blocks, + the index block of a sapling."""
    data = max(1, -(-size // 512))
    return data + (data > 1)


def save_files(build, sym, trunk, packs):
    """NEOWILD.SAV (build/wildsav.bin) with its build id, and the length of
    a NEOWILD.Sn file (src/save.s sv_size). The id is two bytes of the
    SHA-256 of the trunk and region packs, never 0."""
    module = bytearray((build / 'wildsav.bin').read_bytes())
    base = 0x9600
    assert 0 < len(module) <= 0x9C00 - base, 'NEOWILD.SAV overlaps its slot image'
    digest = hashlib.sha256(trunk + b''.join(packs[r] for r in sorted(packs))).digest()
    build_id = int.from_bytes(digest[:2], 'little') or 1
    at = sym['sv_build'] - base
    module[at:at + 2] = build_id.to_bytes(2, 'little')
    at = sym['sv_size'] - base
    slot_size = int.from_bytes(module[at:at + 2], 'little')
    return bytes(module), slot_size


# The two editions (14 October 2026): Neowilderness, a 140 KB 5.25" disk
# with the Sierra Nevada alone (and the journey preparation, the saved
# games); NeoWildernessXL, an 800 KB 3.5" disk with the six scenarios.
# Docs/MEMORY.md 14: XL reads CAMP, MEDVIEW, TREE and ORIENT from NEOWILD.BLK;
# the 140 KB edition reads MEDVIEW, TREE and ORIENT there (lot 4, MEMORY.md
# 16, 18: its store had no room left for them).
EDITIONS = {'neowilderness': dict(regions=(2,), blocks=280, volume='NEOWILDERNESS',
                                  disk_modules=(19, 20), shelters=False, mousetext=False,
                                  lz_modules=LZ_MODULES + LZ_140),
            'xl': dict(regions=PACK_REGIONS, blocks=1600, volume='NEOWILDERNESSXL',
                       disk_modules=(4, 16, 19, 20, 26), shelters=True, mousetext=True)}


def blk_file(build, modules, disk_modules, shelters=True):
    """NEOWILD.BLK: (file bytes, {index: (first block, blocks)}, the 8 bytes
    of ld_blk). Empty bytes when no module is on the disk."""
    if not disk_modules:
        return b'', {}, bytes(8)
    body, where, block = bytearray(), {}, BLK_FIRST + 1
    for index in sorted(disk_modules):
        name, window = modules[index]
        raw = (Path(build) / name).read_bytes()
        blocks = -(-len(raw) // 512)
        assert window in DISK_END and 0 < len(raw) and \
            window + 512 * blocks <= DISK_LIMIT.get(index, DISK_END[window]), \
            (index, name, len(raw))
        where[index] = (block, blocks)
        body += raw + bytes(blocks * 512 - len(raw))
        block += blocks
    for name in SITE_SPRITES:
        if name in SHELTER_SPRITES and not shelters:
            continue
        raw = (Path(build) / G / f'{name}.bin').read_bytes()
        blocks = -(-len(raw) // 512)
        assert 0 < len(raw) and SITE_WINDOW + 512 * blocks <= 0xA000, (name, len(raw))
        where[name] = (block, blocks)
        body += raw + bytes(blocks * 512 - len(raw))
        block += blocks
    ident = hashlib.sha256(bytes(body)).digest()[:2]
    head = BLK_SIGNATURE + ident
    data = head + bytes(512 - len(head)) + bytes(body)
    return data, where, BLK_FIRST.to_bytes(2, 'little') + head


def site_project(build, sym, images, raw_images, where, shelters=True):
    """PROJECT (module 11, raw: the packs patch it) learns where the site
    sprites are on NEOWILD.BLK (block 0: not on this disk, the built shelters
    on the 140 KB edition) and how each image begins. No other image of the
    SIM window may begin like one of them: module_site_load would take it
    for the sprite (src/project.s). Without the built shelters (the 140 KB
    edition) PROJECT ends at project_tail: its tail serves them alone."""
    project = bytearray(images[11])
    def at(label):
        return sym[label] - 0x5800
    count = len(SITE_SPRITES)
    heads = []
    for k, name in enumerate(SITE_SPRITES):
        raw = (Path(build) / G / f'{name}.bin').read_bytes()
        index = 17 + k if k < 6 else 29            # src/project.s proj_index
        width, base = at('proj_sprites') + index - 5, at('proj_sprites') + index + 1
        assert project[at('site_len_lo') + k] | project[at('site_len_lo') + count + k] << 8 == len(raw), name
        assert project[width] == raw[0], (name, 'width')
        image = decode(raw)[0]
        assert project[base] == max(y for y, row in enumerate(image) if any(c >= 0 for c in row)), \
            (name, 'bottom row')
        assert bytes(project[at('site_colours') + 4 * k:at('site_colours') + 4 * k + 4]) == \
            bytes(P.SPRITES[name]), (name, 'colours: tools/dhgr_palette.py SPRITES')
        if name not in where:
            assert name in SHELTER_SPRITES, name
            continue
        block = where[name][0]
        assert 0 < block < 256, (name, block)      # module_site_load: one byte
        project[at('site_blocks') + k] = block
        head = raw[:SITE_HEAD]
        project[at('site_heads') + SITE_HEAD * k:at('site_heads') + SITE_HEAD * (k + 1)] = head
        heads.append(head)
    assert len(set(heads)) == len(heads)
    others = [(build / name).read_bytes() for name, window in MODULES.values() if window == SITE_WINDOW]
    others += [(build / name).read_bytes() for name in ('wildsav.bin', 'wildhof.bin', 'NEOWILD.SYSTEM')]
    assert not any(o[:SITE_HEAD] in heads for o in others), 'a SIM window image begins like a site sprite'
    assert len(project) == at('project_end'), 'PROJECT must end with its tail (src/project.s)'
    if not shelters:
        assert not any(name in where for name in SHELTER_SPRITES)
        del project[at('project_tail'):]
    original = images[11]
    images[11] = raw_images[11] = bytes(project)
    return [[k, b] for k, (a, b) in enumerate(zip(original, project)) if a != b]


def check_blk(image, data, where):
    """NEOWILD.BLK on the built image: a sapling whose data blocks are
    BLK_FIRST.. in order, holding `data` (the directory's block numbers)."""
    from read_volume import Image
    volume = Image(bytes(image))
    entry = next(e for e in volume.entries(2) if e[1:1 + (e[0] & 15)] == b'NEOWILD.BLK')
    assert entry[0] >> 4 == 2, 'NEOWILD.BLK: a sapling expected'
    key = int.from_bytes(entry[0x11:0x13], 'little')
    index = volume.block(key)
    count = len(data) // 512
    assert [index[n] | index[256 + n] << 8 for n in range(count)] == \
        list(range(BLK_FIRST, BLK_FIRST + count)), 'NEOWILD.BLK moved: its blocks are not BLK_FIRST..'
    assert volume.read(entry) == data
    for index_, (block, blocks) in where.items():
        assert BLK_FIRST < block and block + blocks <= BLK_FIRST + count, index_


def build_disk(out, map_path=None, build=None, packing='lz', layout=None, blocks=280, omit=(),
               regions=PACK_REGIONS, volume_name=VOLUME, disk_modules=(), shelters=True, mousetext=False,
               lz_modules=LZ_MODULES + LZ_SIX_PACKS):
    """map_path replaces the map of the Sierra Nevada pack (tests). regions:
    the packs on the volume (the others stay out of NEOWILD.DAT; the loader's
    menu follows, src/boot.s ld_regions): all six, or the Sierra Nevada.
    disk_modules: read from NEOWILD.BLK during the game (docs/MEMORY.md 14).
    shelters: the built shelters' site sprites on NEOWILD.BLK (lot 3).
    mousetext: the MouseText pages of NeoWildernessXL (XL_IMAGES)."""
    build = Path(build) if build else HERE / 'build'
    out = Path(out)
    from mkmap import MAP_BYTES, FOREST_BYTES
    sym = labels(build)
    cache = build / 'lz-cache'
    assert (sym['st_cat'], sym['st_cat2']) == (MODULES[24][1], MODULES[25][1]), \
        'src/wild.cfg SKYCAT/SKYSTARS and MODULES[24]/[25]'

    # Native-map stress fixtures also need the compressed SIM image.
    # Its four mutable preparation constants now live in resident RAM.
    if map_path:
        lz_modules = tuple(sorted(set(lz_modules) | {3}))
    # ---- common trunk: every module but the animals.
    images, raw_images, lz = {}, {}, {}
    xl = xl_files(build, sym) if mousetext else {}
    modules = {i: (xl.get(name, name), window) for i, (name, window) in MODULES.items()}
    assert 13 not in lz_modules and TB_DIR not in lz_modules, 'INPUT and the text bank stay raw'
    bank = (build / MODULES[TB_DIR][0]).read_bytes()
    first = struct.unpack_from('<H', bank, 2)[0]     # the index ends where text 1 starts
    offsets = struct.unpack_from(f'<{first // 2}H', bank)
    if 'TB_TEXTS' in sym:
        count, base = sym['TB_TEXTS'], sym['TB_DICT']
        pairs = list(zip(offsets[1:count+1], offsets[2:count+2]))
        pairs += list(zip(offsets[base:-1], offsets[base+1:]))
        assert len(offsets) == base + sym['TB_WORDS'] + 1, 'bank directory size'
        assert all(a == offsets[base] for a in offsets[count+1:base]), 'bank index padding'
    else:
        pairs = list(zip(offsets[1:], offsets[2:]))  # frozen reference format
    assert all(0 < b - a <= sym['tb_end'] for a, b in pairs), 'bank index'
    assert not set(PATCH_MODULES.values()) & set(lz_modules), 'the packs patch these images'
    assert not set(PATCH_MODULES.values()) & set(disk_modules), 'the packs patch these images'
    # Docs/MEMORY.md 15: a native-map comparison disk (tests) loses 1.2 KB of
    # store to its atlas; TREE (20) and ORIENT (26) are read from NEOWILD.BLK
    # there, as on NeoWildernessXL. Since lot 4 (docs/MEMORY.md 16) every
    # comparison disk does so, as the 140 KB edition: the store of six packs
    # with the lot's growth no longer holds them.
    if map_path and not disk_modules:
        disk_modules = (20, 26)
    assert mousetext or STATUS_DIR not in disk_modules, \
        'STATUS on NEOWILD.BLK needs the XL status_fetch (sim_fetch, src/game.s)'
    disk_modules = tuple(sorted(set(disk_modules) | set(ALWAYS_DISK)))
    blk, blk_where, blk_head = blk_file(build, modules, disk_modules, shelters)
    for index, (name, window) in modules.items():
        data = (build / name).read_bytes()
        assert 0 < len(data) <= WINDOW_LIMIT[window], (name, len(data))
        images[index] = raw_images[index] = data
        if index in blk_where:
            continue                    # NEOWILD.BLK: neither stored nor packed
        packed = lz_store(data, window, cache) if index in lz_modules else None
        if packed:
            images[index] = packed[0]
            lz[index] = dict(stored=len(packed[0]), copy=packed[1], margin=packed[2])
    project_patches = site_project(build, sym, images, raw_images, blk_where, shelters)
    regions_data = {r: region_data(build, r, map_path if r == 2 else None) for r in PACK_REGIONS}
    def sprite_image(name):
        """(stored bytes, LZ entry or None) of an animal sprite."""
        raw = (build / G / f'{name}.bin').read_bytes()
        packed = lz_store(raw, 0x5800, cache) if LZ_SPRITES else None
        if not packed:
            return raw, None
        return packed[0], dict(stored=len(packed[0]), copy=packed[1], margin=packed[2])
    sprite_sizes = {r: sum(len(sprite_image(n)[0]) for n in d['sprites'])
                    for r, d in regions_data.items()}
    mapdata = regions_data[2]['map']
    resident = bytearray((build / 'wildres.bin').read_bytes())
    # Fine geography area (language card bank 1 view): the TOPO snapshot's
    # on a legacy map. A native map's atlas goes to the Sierra Nevada pack.
    code = (build / 'wildgeo.bin').read_bytes()
    base = sym['geo_atlas']
    assert GEO_CODE + len(code) == base, 'wildgeo.bin must end at geo_atlas'
    geo = dict(loaded=False, cache=GEO_CACHE, code_address=GEO_CODE, code=len(code), base=base,
               budget=geo_atlas.ATLAS_END - base, size=0, free=geo_atlas.ATLAS_END - GEO_CACHE)
    geo_record = None
    if mapdata[37]:
        fine = mapdata[MAP_BYTES+FOREST_BYTES:]
        assert len(fine) == 224*168 + 28*168, 'incomplete native geography'
        geo['loaded'] = True
        atlas = geo_atlas.atlas_bytes(fine[:224*168], fine[224*168:],
                                      mapdata[64:MAP_BYTES], base, geo)
        if len(atlas) > geo['budget']:
            raise SystemExit(f'fine geography atlas too large: {len(atlas)} bytes, '
                             f'budget {geo["budget"]} (${base:04X}-${geo_atlas.ATLAS_END-1:04X})')
        geo['free'] = geo['budget'] - len(atlas)
        geo_record = (LC1, GEO_CODE, code + atlas)
        geo['size'] = len(atlas)
    # The store starts past the snapshot area, or past a larger native atlas
    # (comparison disks only: the trunk is placed for this disk).
    store_start = max(SNAP_END, base + geo['size'])
    geo['store_start'] = store_start

    # The packs' sprites get one contiguous area at the top of $4000-$BFFF,
    # as large as the largest pack of the edition (Bolivia on XL; the Sierra
    # alone on the 140 KB edition: 1,334 bytes more of store); the trunk
    # fills the rest. Each pack places its sprites there first, then in the
    # trunk's leftovers.
    area = max(sprite_sizes[r] for r in regions)
    # A comparison disk (tests, --map: the Sierra Nevada with another map)
    # plays the Sierra Nevada only: the sprite area is sized for that pack,
    # and another pack whose animals no longer fit keeps its map and loses
    # its animals (docs/MEMORY.md 13). A native map's atlas takes 1.2 KB of
    # the store; since docs/MEMORY.md 15 a legacy map's comparison disk, which
    # keeps every module in the store (no NEOWILD.BLK), needs it too.
    sierra_only = bool(map_path)
    if sierra_only:
        area = sprite_sizes[2]
    trunk_regions = [list(r) for r in REGIONS]
    exit_size = sym['EX_SIZE']
    exit_at = REGIONS[0][2] - area - exit_size
    trunk_regions[0][2] -= area + exit_size
    drows = (build / DROWS[2]).read_bytes()
    for r in trunk_regions:
        if r[:2] == [LC2, SNAP_END]:
            r[1] = store_start
        if r[:2] == [DROWS[0], DROWS[1]]:
            r[1] += len(drows)
    placed, free = place({i: d for i, d in images.items() if i not in blk_where}, trunk_regions)
    pack_area = (AUX, REGIONS[0][2] - area, REGIONS[0][2])
    free = [list(pack_area)] + free

    def directory(placed_all, images_all, lz_all):
        table = bytearray(DIR_ENTRIES * 7)
        for index in range(DIR_ENTRIES):
            source = index
            if source in blk_where:                 # first block, raw length
                length = len(raw_images[source])
                if source == CRAFT_DIR:             # MAKE reads the recipes' blocks only;
                    length = sym['craft_page'] - MODULES[source][1]   # pg_craft: all
                    end = sym['crx_end' if mousetext else 'craft_end']      # (XL: its tail)
                    assert end - MODULES[source][1] == len(raw_images[source])
                table[index*7:index*7+7] = struct.pack('<BHHH', BANK_DISK, blk_where[source][0],
                                                       length, MODULES[source][1])
                continue
            if source not in placed_all:
                continue                            # a missing 23: empty
            bank, address = placed_all[source]
            window = MODULES[source][1] if source in MODULES else 0x5800
            kind = DIR_BANK[bank]
            if source in lz_all:
                kind |= BANK_LZ | lz_all[source]['margin'] << 2
                window = lz_all[source]['copy']
            table[index*7:index*7+7] = struct.pack('<BHHH', kind, address,
                                                   len(images_all[source]), window)
        bank = placed_all[TB_DIR][0]
        table[TB_FETCH*7:TB_FETCH*7+7] = struct.pack('<BHHH', DIR_BANK[bank], 0, 0, sym['tb_buf'])
        table[ZP_ENTRY*7:ZP_ENTRY*7+7] = struct.pack('<BHHH', DIR_BANK[AUX], ZP_AUX, 256, sym['saved_zp'])
        assert EXIT_ENTRY not in placed_all and EXIT_ENTRY not in MODULES
        table[EXIT_ENTRY*7:EXIT_ENTRY*7+7] = struct.pack('<BHHH', DIR_BANK[AUX], exit_at, exit_size, EXIT_BUF)
        return bytes(table)

    dir_offset = sym['module_dir'] - 0xB600
    resident[dir_offset:dir_offset + DIR_ENTRIES*7] = directory(placed, images, lz)
    low = bytearray(0x1800)                       # $0800-$1FFF, gaps restored as zero
    for address, data in ((0x0926, (build / 'wildforest.bin').read_bytes()),
                          (0x0A00, (build / 'wildtxt.bin').read_bytes()),
                          (0x1000, (build / 'wildlo.bin').read_bytes())):
        low[address - 0x0800:address - 0x0800 + len(data)] = data
    skylc = (build / SKYLC[2]).read_bytes()
    assert len(skylc) <= 0x200
    trunk_sections = [(MAIN, 0x6000, (build / xl.get('wild.bin', 'wild.bin')).read_bytes()), None]
    trunk_sections += blobs(placed, images)
    lzlc = (build / LZLC[2]).read_bytes()
    assert 0 < len(lzlc) <= 0xFF and sym['lzc_entry'] == LZLC[1], 'the decoder fills $D001-$D0FF at most'
    b2lc = (build / B2LC[2]).read_bytes()
    assert 0 < len(b2lc) <= 0x300 and sym['b2_column_setup'] >= B2LC[1], 'bank 2 code: $D100-$D3FF'
    assert sym['EX_SIZE'] == sym['EX_STATE'] + 0x300, 'the exit state holds the QUIT code'
    trunk_sections += [(SKYLC[0], SKYLC[1], skylc), (DROWS[0], DROWS[1], drows),
                       (LZLC[0], LZLC[1], lzlc), (B2LC[0], B2LC[1], b2lc)]
    trunk_sections += [(MAIN, 0x0200, (build / xl.get('wildpg.bin', 'wildpg.bin')).read_bytes()),
                       (MAIN, 0x0926, bytes(low[0x0126:])),
                       (MAIN, 0x4000, (build / xl.get('wildgame.bin', 'wildgame.bin')).read_bytes()),
                       (MAIN, 0xB600, bytes(resident)),
                       (MAIN, 0xBA00, (build / xl.get('wildmenu.bin', 'wildmenu.bin')).read_bytes()),
                       # HICODE: moved to $BE00 by the loader once ProDOS's
                       # zero page is in auxiliary $BF00 (src/boot.s).
                       (MAIN, sym['HI_LOAD'] if 'HI_LOAD' in sym else 0xA900,
                        (build / 'wildhi.bin').read_bytes()),
                       # The grid of the menu: read here (free during the load),
                       # hidden in the HGR rows 176-191 by the loader (ld_scatter).
                       (MAIN, sym['SWAP_LOAD'], (build / xl.get('wildmenusw.bin', 'wildmenusw.bin')).read_bytes())]
    trunk, trunk_stats = records(trunk_sections, packing, cache)

    # ---- one pack per region.
    tables_start, tables_end = sym['dhgr_moods'], sym['dhgr_tables_end']
    sierra_tables = (build / 'wildgame.bin').read_bytes()[tables_start - 0x4000:tables_end - 0x4000]
    assert (build / 'dhgr/dhgr_tables_r2.bin').read_bytes() == sierra_tables, \
        'build/dhgr/dhgr_tables_r2.bin must equal the linked Sierra tables'
    packs, pack_info = {}, {}
    replaced = []
    for region, data in regions_data.items():
        if region not in regions:       # not on this edition: no pack, no sprite area
            pack_info[str(region)] = dict(name=data['entry']['name'], filename='NEOWILD.DAT',
                                          omitted=True, stored=0, file=0, modules={})
            continue
        raw_sprites = {SLOT_MODULES[k]: (build / G / f'{name}.bin').read_bytes()
                       for k, name in enumerate(data['sprites'])}
        stored_sprites = {SLOT_MODULES[k]: sprite_image(name) for k, name in enumerate(data['sprites'])}
        sprites = {i: image for i, (image, _) in stored_sprites.items()}
        sprite_lz = {i: entry for i, (_, entry) in stored_sprites.items() if entry}
        # Until the four-species port (step 4), fauna.s may still draw the
        # Sierra's third species: a region with two species points module 8
        # at a one-byte empty sprite (width 0: nothing drawn), never at
        # whatever the window held before.
        empties = [m for m in SLOT_MODULES[:3] if m not in sprites]
        pack_images = dict(sprites, **({'empty': EMPTY_SPRITE} if empties else {}))
        try:
            pack_placed, pack_free = place(pack_images, free)
        except SystemExit:
            if not sierra_only or region == 2:
                raise
            print(f'{out}: comparison disk: pack {region} without its animals',
                  file=sys.stderr)
            replaced.append(region)
            sprites, sprite_lz, raw_sprites = {}, {}, {}
            empties = list(SLOT_MODULES[:3])
            pack_images = {'empty': EMPTY_SPRITE}
            pack_placed, pack_free = place(pack_images, free)
        all_placed = {**placed, **pack_placed}
        all_images = {**images, **sprites}
        for m in empties:
            all_placed[m], all_images[m] = pack_placed['empty'], EMPTY_SPRITE
        sections = blobs(pack_placed, pack_images)
        patches = {}
        for symbol, patch in fauna_patches(data['header'], region, build).items():
            index = PATCH_MODULES[symbol]
            offset = sym[symbol] - 0x5800
            trunk_bytes = images[index][offset:offset + len(patch)]
            bank, address = placed[index]
            if region == 2:     # the trunk's images hold the Sierra Nevada:
                assert trunk_bytes == patch, (symbol, trunk_bytes.hex(), patch.hex())
            if region != 2:
                sections.append((bank, address + offset, patch))
            patches[symbol] = dict(module=index, bank=BANK_NAMES[bank], address=address + offset,
                                   data=patch.hex())
        dhgr_tables = (build / f'dhgr/dhgr_tables_r{region}.bin').read_bytes()
        assert len(dhgr_tables) == tables_end - tables_start, region
        if region == 2 and geo_record:
            sections.append(geo_record)         # before the map: LZ decodes through $7000
        # The Sierra Nevada's colours are the trunk's (GAME, asserted above):
        # its pack leaves them (15 October 2026, docs/MEMORY.md 27), as its
        # fauna patches; the loader always reads the trunk first.
        sections += [(MAIN, 0x0800, data['mask'])]
        if region != 2:
            sections.append((MAIN, tables_start, dhgr_tables))
        sections += [(MAIN, sym['__REGIONTEXT_RUN__'], region_texts(data['entry'], data['header'])),
                     (MAIN, sym['module_dir'], directory(all_placed, all_images, {**lz, **sprite_lz})),
                     (MAIN, 0x7000, data['map'][:MAP_BYTES])]
        packs[region], stats = records(sections, packing, cache)
        pack_info[str(region)] = dict(
            name=data['entry']['name'], filename='NEOWILD.DAT', **stats,
            sprites=list(data['sprites']), sprite_bytes=sum(map(len, raw_sprites.values())),
            sprite_stored=sum(map(len, sprites.values())),
            aux_free=sum(e - s for _, s, e in pack_free),
            aux_free_largest=max(e - s for _, s, e in pack_free),
            modules={str(i): dict(image=G + data['sprites'][SLOT_MODULES.index(i)] + '.bin',
                                  bank=BANK_NAMES[b], address=a, length=len(raw_sprites[i]),
                                  stored=len(sprites[i]), window=0x5800,
                                  **({'lz': sprite_lz[i]} if i in sprite_lz else {}))
                     for i, (b, a) in pack_placed.items() if i != 'empty'},
            empty_slots={str(m): dict(bank=BANK_NAMES[pack_placed['empty'][0]],
                                      address=pack_placed['empty'][1], length=1)
                         for m in empties},
            patches=patches,
            map_region=data['map'][32])

    for region in replaced:
        pack_info[str(region)]['animals_dropped'] = True
    # One file (docs/MEMORY.md 13): the trunk, the six packs, the preparation
    # (LZ-packed, src/boot.s reads it at PRE_PACK $3000, at most 4 KB, and
    # decodes it behind itself to $2000). The loader opens NEOWILD.DAT for
    # each part and moves to the mark that ld_marks gives (src/boot.s
    # ld_open): six pack files cost six index blocks and six partial ones.
    prepare_module = compress((build / 'wildpre.bin').read_bytes())
    assert 0 < len(prepare_module) <= 0x1000 and (build / 'wildpre.bin').stat().st_size <= 0x1F00
    dat, marks = bytearray(trunk), []
    assert tuple(regions) in ((2,), PACK_REGIONS), 'the Sierra Nevada alone, or the six'
    for region in PACK_REGIONS:
        marks.append(len(dat))
        pack_info[str(region)]['mark'] = len(dat)
        if region in regions:
            dat += packs[region]
    marks.append(len(dat))
    dat += prepare_module
    system_name = xl.get('NEOWILD.SYSTEM', 'NEOWILD.SYSTEM')
    system = system_file(build, sym, marks, len(prepare_module), cache, len(regions), blk_head, exit_at,
                         system_name)[0]
    stage = Path(tempfile.mkdtemp(prefix='neowild-stage-'))
    try:
        (stage / 'PRODOS#FF0000').write_bytes((DEV / 'tools/prodos/PRODOS').read_bytes())
        (stage / 'NEOWILD.SYSTEM#FF2000').write_bytes(bytes(system))
        (stage / 'NEOWILD.DAT#060000').write_bytes(bytes(dat))
        if blk:
            (stage / 'NEOWILD.BLK#060000').write_bytes(blk)
        # Lot 7 step 6 (docs/HOF.md): the end-of-game module, read from the
        # disk by module_end at $9600 (directory entry 24: the star catalogue), and
        # the empty hall of fame (tools/genhof.py), rewritten in place.
        end_module = bytearray((build / xl.get('wildhof.bin', 'wildhof.bin')).read_bytes())
        at = sym['hm_regions'] - 0x9600     # the hall of fame's scenarios
        assert end_module[at] == 6
        end_module[at] = len(regions)
        end_module = bytes(end_module)
        hof_file = (build / 'NEOWILD.HOF').read_bytes()
        assert 0 < len(end_module) <= 0x2000 and len(hof_file) == 512
        if 'NEOWILD.END' not in omit:       # tests/test_save.py: room for 3 games
            (stage / 'NEOWILD.END#069600').write_bytes(end_module)
        (stage / 'NEOWILD.HOF#060000').write_bytes(hof_file)
        # Lot 9 (docs/SAVE.md): the SAVE/RESTORE module, read at $9600 by
        # do_save, with the build id of this volume (a game saved by another
        # build is refused), and the five games, fixed-length files written
        # in place (no CREATE, no block allocated), empty (zeros) here.
        save_module, slot_size = save_files(build, sym, trunk, packs)
        (stage / 'NEOWILD.SAV#069600').write_bytes(save_module)
        for game in range(1, SAVE_GAMES + 1):
            (stage / f'NEOWILD.S{game}#060000').write_bytes(bytes(slot_size))
        boot = (DEV / 'tools/prodos/boot.bin').read_bytes()
        boot = (boot + bytes(1024))[:1024]
        # A volume too small for the five games (a native map's atlas in a
        # 280-block comparison disk) keeps as many as fit; the game answers
        # "NEOWILD.Sn IS MISSING." for the others.
        # A comparison disk with a native map (its atlas takes 13 more blocks)
        # may still overflow with no game at all: it then also drops the
        # SAVE/RESTORE module, which its tests do not use (the shipped image
        # keeps it: it is checked by tests/test_pack_boot.py). The journey
        # preparation is part of NEOWILD.DAT (docs/MEMORY.md 13).
        dropped = []
        if 'preparation' in omit:           # tests/test_save.py: room for 3 games
            (stage / 'NEOWILD.DAT#060000').write_bytes(bytes(dat[:marks[-1]]))
            (stage / 'NEOWILD.SYSTEM#FF2000').write_bytes(
                system_file(build, sym, marks, 0, cache, len(regions), blk_head, exit_at, system_name)[0])
            dropped.append('preparation')
        optional = ['NEOWILD.SAV#069600'] + ([] if 'preparation' in omit else ['preparation'])
        while True:
            built = False
            for games in range(SAVE_GAMES, -1, -1):
                try:
                    volume = Volume(volume_name, blocks, boot, prodos_date('2026-10-13T12:00'))
                    volume.build(stage)
                    built = True
                    break
                except SystemExit:
                    if games:
                        (stage / f'NEOWILD.S{games}#060000').unlink(missing_ok=True)
            if built:
                break
            if not optional or not map_path:
                raise SystemExit('le contenu deborde le volume de %d blocs' % blocks)
            name = optional.pop(0)
            if name == 'preparation':       # NEOWILD.DAT without it (0 bytes)
                (stage / 'NEOWILD.DAT#060000').write_bytes(bytes(dat[:marks[-1]]))
                (stage / 'NEOWILD.SYSTEM#FF2000').write_bytes(
                    system_file(build, sym, marks, 0, cache, len(regions), blk_head, exit_at, system_name)[0])
            else:
                (stage / name).unlink()
            dropped.append(name.split('#')[0])
        if games < SAVE_GAMES:
            print(f'{out}: room for {games} saved games of {SAVE_GAMES} only', file=sys.stderr)
        if dropped:
            print(f'{out}: native-map comparison disk without {", ".join(dropped)}', file=sys.stderr)
        # The hall of fame and the saved games are the only files written in place.
        lock_files(volume, keep={'NEOWILD.HOF'} | {f'NEOWILD.S{g}' for g in range(1, games + 1)})
    finally:
        for path in stage.iterdir():
            path.unlink()
        stage.rmdir()
    if blk:
        check_blk(volume.image, blk, blk_where)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(volume.image))

    # Layout: the trunk plus the Sierra Nevada pack, as after the default
    # menu choice "2, RETURN" (what the tests load), and every pack.
    sierra = pack_info['2']['modules']
    trunk_modules = {str(i): dict(image=modules[i][0], bank=BANK_NAMES[placed[i][0]],
                                  address=placed[i][1], length=len(raw_images[i]),
                                  stored=len(images[i]), window=modules[i][1],
                                  **({'lz': lz[i]} if i in lz else {}))
                     for i in range(DIR_ENTRIES) if i in placed}
    trunk_modules['11']['patches'] = project_patches   # module_image: NEOWILD.BLK's site sprites
    for i, (block, count) in blk_where.items():
        if i in SITE_SPRITES:
            continue
        trunk_modules[str(i)] = dict(image=modules[i][0], bank='disk', block=block, blocks=count,
                                     length=len(raw_images[i]), stored=count * 512,
                                     window=modules[i][1])
        if i == CRAFT_DIR:              # the directory's length: the recipes (MAKE)
            trunk_modules[str(i)]['fetch'] = sym['craft_page'] - modules[i][1]
    trunk_modules = dict(sorted(trunk_modules.items(), key=lambda kv: int(kv[0])))
    info = dict(packing=packing, blocks_used=volume.next_free, blocks=blocks,
                blocks_free=blocks - volume.next_free,
                dat=trunk_stats, geo=geo,
                modules=dict(sorted({**trunk_modules, **sierra}.items(), key=lambda kv: int(kv[0]))),
                trunk_modules=trunk_modules,
                aux_free=[dict(bank=BANK_NAMES[b], start=s, end=e, free=e-s)
                          for b, s, e in place(dict(enumerate(
                              sprite_image(n)[0]
                              for n in regions_data[2]['sprites'])), free)[1]],
                aux_trunk_free=sum(e - s for _, s, e in free),
                pack_area=dict(bank='aux', start=pack_area[1], end=pack_area[2]),
                exit_state=dict(bank='aux', address=exit_at, length=exit_size, buffer=EXIT_BUF),
                star_code=dict(bank=BANK_NAMES[SKYLC[0]], address=SKYLC[1], length=len(skylc)),
                dhgr_rows=dict(bank=BANK_NAMES[DROWS[0]], address=DROWS[1], length=len(drows)),
                disk=dict(file='NEOWILD.BLK', bytes=len(blk), first_block=BLK_FIRST if blk else 0,
                          signature=blk_head[2:].hex(),
                          modules={str(i): dict(block=b, blocks=n) for i, (b, n) in blk_where.items()
                                   if i not in SITE_SPRITES},
                          sites={i: dict(block=b, blocks=n) for i, (b, n) in blk_where.items()
                                 if i in SITE_SPRITES}),
                lz_decoder=dict(bank=BANK_NAMES[LZLC[0]], address=LZLC[1], length=len(lzlc)),
                bank2_code=dict(bank=BANK_NAMES[B2LC[0]], address=B2LC[1], length=len(b2lc)),
                packs=pack_info,
                region_text=sym['__REGIONTEXT_RUN__'], dhgr_tables=[tables_start, tables_end],
                end_module=dict(file='NEOWILD.END', bytes=len(end_module),
                                blocks=-(-len(end_module) // 512) + (len(end_module) > 512)),
                hof_file=dict(file='NEOWILD.HOF', bytes=len(hof_file), blocks=1),
                prepare_module=dict(file='NEOWILD.DAT', mark=marks[-1], bytes=len(prepare_module)),
                dat_file=dict(bytes=len(dat), blocks=-(-len(dat) // 512) + (len(dat) > 512),
                              marks=marks),
                save_module=dict(file='NEOWILD.SAV', bytes=len(save_module),
                                 blocks=file_blocks(len(save_module)),
                                 on_volume='NEOWILD.SAV' not in dropped),
                save_games=dict(files=[f'NEOWILD.S{g}' for g in range(1, games + 1)],
                                bytes=slot_size, blocks=file_blocks(slot_size)))
    if layout:
        Path(layout).write_text(json.dumps(info, indent=1) + '\n')
    return info


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--map')
    parser.add_argument('--build')
    # Default lz, as the Makefile (BOOT_PACKING): disks built by the tests
    # (tests/common.disk_with) match the shipped volume; with auto a native
    # map (atlas in the Sierra pack) would not fit the 280 blocks.
    parser.add_argument('--packing', choices=('raw', 'lz', 'auto'), default='lz')
    parser.add_argument('--layout', help='write the placement/record summary as JSON')
    # Lot 9: 280 blocks (5.25-inch, the shipped image) or 1600 (3.5-inch 800 KB).
    parser.add_argument('--blocks', type=int, default=280)
    parser.add_argument('--omit', action='append', default=[], help='leave a file out (NEOWILD.END)')
    parser.add_argument('--mousetext', action='store_true',
                        help='a comparison disk with the MouseText pages of XL (docs/MENUS.md 9)')
    parser.add_argument('--edition', choices=sorted(EDITIONS),
                        help='neowilderness: 140 KB, the Sierra Nevada alone; xl: 800 KB, the six scenarios')
    args = parser.parse_args()
    # The comparison disks of the tests (--map, no edition) keep the plain
    # pages, as the 140 KB edition whose store they share the pressure of
    # (docs/MENUS.md 9); --mousetext gives them XL's.
    edition = EDITIONS[args.edition] if args.edition else dict(regions=PACK_REGIONS, volume=VOLUME,
                                                               disk_modules=(), mousetext=args.mousetext)
    blocks = edition.get('blocks', args.blocks) if args.edition else args.blocks
    try:
        info = build_disk(args.out, args.map, args.build, args.packing, args.layout, blocks, args.omit,
                          edition['regions'], edition['volume'], edition['disk_modules'],
                          edition.get('shelters', True), edition.get('mousetext', False),
                          edition.get('lz_modules', LZ_MODULES + LZ_SIX_PACKS))
    except SystemExit as e:
        # Lot 4 (docs/MEMORY.md 16): a comparison disk whose native atlas no
        # longer leaves room on 280 blocks keeps the Sierra Nevada pack alone
        # (its tests play the Sierra Nevada; the menu then offers it alone);
        # one whose atlas leaves the store too small (the noise-tile stress
        # maps of tests/test_geo_resident.py, which play no command) reads
        # XL's four modules from NEOWILD.BLK.
        if not (args.map and not args.edition and ('deborde' in str(e) or 'auxiliary' in str(e))):
            raise
        # The fewest modules on the disk first: MEDVIEW, then XL's four
        # (tests/test_resident.py and test_geo_resident.py read the
        # directory to expect their reads).
        regions, disk_modules = PACK_REGIONS, (20, 26)
        # (STATUS stays in the store: only XL's status_fetch reads it from
        # the disk, docs/MEMORY.md 29.)
        steps = [(19, 20, 26), tuple(m for m in EDITIONS['xl']['disk_modules'] if m != STATUS_DIR)] \
            if 'auxiliary' in str(e) else []
        info = None
        while info is None:
            if 'auxiliary' in str(e):
                if not steps:
                    raise e
                disk_modules = steps.pop(0)
                print(f'{args.out}: comparison disk: modules {disk_modules} on NEOWILD.BLK',
                      file=sys.stderr)
            elif regions != (2,):
                regions = (2,)
                print(f'{args.out}: comparison disk: the Sierra Nevada pack alone', file=sys.stderr)
            else:
                raise e
            try:
                info = build_disk(args.out, args.map, args.build, args.packing, args.layout, blocks,
                                  args.omit, regions, edition['volume'], disk_modules,
                                  mousetext=edition.get('mousetext', False))
            except SystemExit as e2:
                if 'deborde' not in str(e2) and 'auxiliary' not in str(e2):
                    raise
                e = e2
    if args.edition and not args.omit:
        assert len(info['save_games']['files']) == SAVE_GAMES, 'shipping editions must keep all five saves'
    packs = ', '.join(f'R{r} {p["stored"]}' for r, p in info['packs'].items())
    print(f'{args.out}: NEOWILD.DAT {info["dat"]["raw"]} -> {info["dat"]["stored"]} bytes '
          f'({info["packing"]}, {info["dat"]["records"]} records); packs (bytes) {packs}; '
          f'{info["blocks_used"]}/{info["blocks"]} blocks')
