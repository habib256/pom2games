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
journey (lot 7 step 6, docs/HOF.md).

A file is a 256-byte record table followed by the payloads, back to back.
Record: kind, address, length, stored length; kind 0 end, 1 claim, otherwise
$80 | $40 (LZ, tools/pack_boot.py) | bank (0 main, 1 auxiliary, 2 auxiliary
language card bank 2, 3 bank 1). Stored data never exceeds 8 KB.

Trunk: WILDERNESS, the claim, the auxiliary store of every common module
(wreck and cabin sprites included: a single sprite each on the Journey
side), LOWPAGE, $0926-$1FFF, WILDGAME, RESIDENT and the menu of the four
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
SNAP_END = 0xED00
REGIONS = [(AUX, 0x4000, 0xC000), (AUX, 0x0800, 0x2000), (LC2, 0xD000, 0xE000),
           (LC2, SNAP_END, 0xFFFA), (MLC2, 0xD400, 0xDE18)]
SKYLC = (MLC2, 0xDE18, 'wildskylc.bin')     # src/stars_draw.s, runs in place
# Direction 3: the unrolled DHGR rows and their entry tables (src/dhgr.s,
# segment DROWS) run in place at the start of the main card's store.
DROWS = (MLC2, 0xD400, 'wilddrows.bin')
SNAPSHOT = [(LC1, 0xD000, 0xE000), (LC2, 0xE000, SNAP_END)]
# Native maps only: the fine geography takes bank 1 and the common area
# instead of the snapshot (src/geoaux.s, src/topo_dhgr.s tp_save).
GEO_CACHE = 0xD000               # 4 decoded tiles + woodland, not stored
GEO_CODE = 0xD480                # src/geoaux.s (segment GEOAUX), then the atlas
G = 'original_graphics/'
# Directory index -> (image, execution window) of the common trunk. 18 is an
# alias of 17. 25 is the hourly star module (docs/STARS.md); 24 (hall of
# fame) is read from the disk at the end of a game (NEOWILD.END), so its
# entry holds the head of the star catalogue (462 bytes: it fills the
# 464-byte hole of the auxiliary card), which the star module copies in
# front of itself: both run in the SIM window (free while the simulation is
# not loaded: show_view_scene, docs/STARS.md). Their windows come from
# build/wild.lbl (st_cat, st_cat2).
MODULES = {0: ('wildtpg.bin', 0x9600), 1: ('wildvoc.bin', 0x5800), 2: ('wildscr.bin', 0x5800),
           3: ('wildsim.bin', 0x9600), 4: ('wildcamp.bin', 0x5800),
           5: (G + 'wreck.bin', 0x5800), 9: (G + 'cabin.bin', 0x5800),
           10: ('wildsit.bin', 0x5800),
           11: ('wildprj.bin', 0x5800), 12: ('wildtrv.bin', 0x5800), 13: ('wildinp.bin', 0x5800),
           14: ('wilditm.bin', 0x5800), 15: ('wildhud.bin', 0x5800), 16: ('wildsta.bin', 0x5800),
           17: ('wildmed.bin', 0x5800), 19: ('wildmvi.bin', 0x5800), 20: ('wildtre.bin', 0x5800),
           21: ('wildadv.bin', 0x5800), 22: ('wildout.bin', 0x5800),
           24: ('wildskycat.bin', 0x9600), 25: ('wildsky.bin', 0x97CE),
           26: ('wildori.bin', 0x5800), 27: ('wildalr.bin', 0x5800)}
DIR_ENTRIES = 28                 # memory.s MOD_COUNT
# Modules stored LZ-packed in the auxiliary store and decoded in their window
# by mem_fetch (src/memory.s lz_unpack; docs/MEMORY.md 13): the rarely loaded
# ones (TOPOGEN, ITEMS, MEDVIEW, TREE, ORIENT, ALERT), whose
# decoding (about 50 cycles per byte instead of 17 for a copy) never runs
# during a view. SCREENS and STATUS fill their window: an in-place copy has
# no room behind them. INPUT (13) must stay raw: it is loaded after the end
# of a journey, once NEOWILD.END's I/O buffer has overwritten the decoder
# (MENUCODE). The packs patch TRAVEL, OUTDOOR, PROJECT and SUMMARY in place.
LZ_MODULES = (0, 5, 9, 14, 19, 20, 26)
LZ_WINDOW_END = {0x5800: 0x6000, 0x9600: 0xA200}     # TOPOGEN: its BSS at $A200
# The animals of the packs too: one sprite at most is loaded per view
# (sprites.s scene_prepare), about 40 cycles more per byte, under 1 % of a
# full view (6.1 million cycles).
LZ_SPRITES = True
BANK_LZ = 0x80                   # memory.s BANK_LZ
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
WINDOW_LIMIT = {0x5800: 0x0800, 0x9600: 0x2000, 0x2000: 0x2000, 0x97CE: 0xB600 - 0x97CE}


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
        if key in seen:
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


def system_file(build, sym, marks, prepare_length, cache=None):
    """NEOWILD.SYSTEM: the stub (SYSSTUB), then the loader with its marks
    (ld_marks), LZ-packed; the stub decodes it to __LOADER_RUN__."""
    raw = (Path(build) / 'NEOWILD.SYSTEM').read_bytes()
    at = sym['__LOADER_LOAD__'] - 0x2000
    loader = bytearray(raw[at:])
    assert len(loader) == sym['__LOADER_SIZE__']
    mark = sym['ld_marks'] - sym['__LOADER_RUN__']
    assert loader[mark:mark + 23] == bytes(23), 'NEOWILD.SYSTEM ld_marks'
    loader[mark:mark + 23] = b''.join(m.to_bytes(3, 'little') for m in marks) + \
        prepare_length.to_bytes(2, 'little')
    stream = lz_stream(bytes(loader), cache)[0]
    assert unpack_stream(stream) == loader
    return raw[:at] + stream, bytes(loader)


def lz_store(raw, window, cache=None):
    """An image for the store, decoded in place by lz_unpack: (blob, copy
    address, margin) or None when it would not be shorter. The blob is the
    window address, then the tokens and an end token (a match of distance 0).
    The copy ends `margin` bytes past the image's own end, the least that
    keeps every unread token ahead of the output."""
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
    copy = window + len(raw) + margin - len(blob)
    if len(blob) >= len(raw) or window + len(raw) + margin > LZ_WINDOW_END[window]:
        return None
    assert lz_unpack(blob, copy) == raw
    return blob, copy, margin


def stored_bytes(build, module):
    """The bytes a layout.json module entry occupies in the store."""
    raw = (Path(build) / module['image']).read_bytes()
    if 'lz' not in module:
        return raw
    return lz_store(raw, module['window'], Path(build) / 'lz-cache')[0]


def lz_unpack(blob, copy):
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
    reactions = [bytearray(4) for _ in range(10)]
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
        values = (noise, threshold(Fraction(2, 100) * rec[14]), threshold(Fraction(2, 100) * rec[18]),
                  threshold(Fraction(5, 1000) * rec[24]), threshold(Fraction(2, 100) * rec[15]),
                  threshold(Fraction(2, 100) * rec[16]), threshold(Fraction(2, 100) * rec[13]),
                  64 if name in CATS else 192 if venom else 128, vocab[name], kind)
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


def build_disk(out, map_path=None, build=None, packing='lz', layout=None):
    """map_path replaces the map of the Sierra Nevada pack (tests)."""
    build = Path(build) if build else HERE / 'build'
    out = Path(out)
    from mkmap import MAP_BYTES, FOREST_BYTES
    sym = labels(build)
    cache = build / 'lz-cache'
    assert (sym['st_cat'], sym['st_cat2']) == (MODULES[24][1], MODULES[25][1]), \
        'src/wild.cfg SKYCAT/SKYSTARS and MODULES[24]/[25]'

    # ---- common trunk: every module but the animals.
    images, raw_images, lz = {}, {}, {}
    modules = dict(MODULES)
    assert 13 not in LZ_MODULES, 'INPUT is loaded after the end of a journey: raw'
    assert not set(PATCH_MODULES.values()) & set(LZ_MODULES), 'the packs patch these images'
    for index, (name, window) in modules.items():
        data = (build / name).read_bytes()
        assert 0 < len(data) <= WINDOW_LIMIT[window], (name, len(data))
        images[index] = raw_images[index] = data
        packed = lz_store(data, window, cache) if index in LZ_MODULES else None
        if packed:
            images[index] = packed[0]
            lz[index] = dict(stored=len(packed[0]), copy=packed[1], margin=packed[2])
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
    # as large as the largest pack (Burma); the trunk fills the rest. Each
    # pack places its sprites there first, then in the trunk's leftovers.
    area = max(sprite_sizes.values())
    trunk_regions = [list(r) for r in REGIONS]
    trunk_regions[0][2] -= area
    drows = (build / DROWS[2]).read_bytes()
    for r in trunk_regions:
        if r[:2] == [LC2, SNAP_END]:
            r[1] = store_start
        if r[:2] == [DROWS[0], DROWS[1]]:
            r[1] += len(drows)
    placed, free = place(images, trunk_regions)
    pack_area = (AUX, REGIONS[0][2] - area, REGIONS[0][2])
    free = [list(pack_area)] + free

    def directory(placed_all, images_all, lz_all):
        table = bytearray(DIR_ENTRIES * 7)
        for index in range(DIR_ENTRIES):
            source = 17 if index == 18 else index
            if source not in placed_all:
                continue                            # a missing 23: empty
            bank, address = placed_all[source]
            window = MODULES[source][1] if source in MODULES else 0x5800
            kind = DIR_BANK[bank]
            if source in lz_all:
                kind, window = kind | BANK_LZ, lz_all[source]['copy']
            table[index*7:index*7+7] = struct.pack('<BHHH', kind, address,
                                                   len(images_all[source]), window)
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
    trunk_sections = [(MAIN, 0x6000, (build / 'wild.bin').read_bytes()), None]
    trunk_sections += blobs(placed, images)
    trunk_sections += [(SKYLC[0], SKYLC[1], skylc), (DROWS[0], DROWS[1], drows)]
    trunk_sections += [(MAIN, 0x0200, (build / 'wildpg.bin').read_bytes()),
                       (MAIN, 0x0926, bytes(low[0x0126:])),
                       (MAIN, 0x4000, (build / 'wildgame.bin').read_bytes()),
                       (MAIN, 0xB600, bytes(resident)),
                       (MAIN, 0xBA00, (build / 'wildmenu.bin').read_bytes()),
                       # The grid of the menu: read here (free during the load),
                       # hidden in the HGR rows 176-191 by the loader (ld_scatter).
                       (MAIN, 0xAF00, (build / 'wildmenusw.bin').read_bytes())]
    trunk, trunk_stats = records(trunk_sections, packing, cache)

    # ---- one pack per region.
    tables_start, tables_end = sym['dhgr_moods'], sym['dhgr_tables_end']
    sierra_tables = (build / 'wildgame.bin').read_bytes()[tables_start - 0x4000:tables_end - 0x4000]
    assert (build / 'dhgr/dhgr_tables_r2.bin').read_bytes() == sierra_tables, \
        'build/dhgr/dhgr_tables_r2.bin must equal the linked Sierra tables'
    packs, pack_info = {}, {}
    for region, data in regions_data.items():
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
            if region == 2:     # the trunk's images hold the Sierra Nevada
                assert trunk_bytes == patch, (symbol, trunk_bytes.hex(), patch.hex())
            bank, address = placed[index]
            sections.append((bank, address + offset, patch))
            patches[symbol] = dict(module=index, bank=BANK_NAMES[bank], address=address + offset,
                                   data=patch.hex())
        dhgr_tables = (build / f'dhgr/dhgr_tables_r{region}.bin').read_bytes()
        assert len(dhgr_tables) == tables_end - tables_start, region
        if region == 2 and geo_record:
            sections.append(geo_record)         # before the map: LZ decodes through $7000
        sections += [(MAIN, 0x0800, data['mask']),
                     (MAIN, tables_start, dhgr_tables),
                     (MAIN, sym['__REGIONTEXT_RUN__'], region_texts(data['entry'], data['header'])),
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

    # One file (docs/MEMORY.md 13): the trunk, the six packs, the preparation
    # (LZ-packed, src/boot.s reads it at PRE_PACK $3000, at most 4 KB, and
    # decodes it behind itself to $2000). The loader opens NEOWILD.DAT for
    # each part and moves to the mark that ld_marks gives (src/boot.s
    # ld_open): six pack files cost six index blocks and six partial ones.
    prepare_module = compress((build / 'wildpre.bin').read_bytes())
    assert 0 < len(prepare_module) <= 0x1000 and (build / 'wildpre.bin').stat().st_size <= 0x1F00
    dat, marks = bytearray(trunk), []
    for region in PACK_REGIONS:
        marks.append(len(dat))
        pack_info[str(region)]['mark'] = len(dat)
        dat += packs[region]
    marks.append(len(dat))
    dat += prepare_module
    system = system_file(build, sym, marks, len(prepare_module), cache)[0]
    stage = Path(tempfile.mkdtemp(prefix='neowild-stage-'))
    try:
        (stage / 'PRODOS#FF0000').write_bytes((DEV / 'tools/prodos/PRODOS').read_bytes())
        (stage / 'NEOWILD.SYSTEM#FF2000').write_bytes(bytes(system))
        (stage / 'NEOWILD.DAT#060000').write_bytes(bytes(dat))
        # Lot 7 step 6 (docs/HOF.md): the end-of-game module, read from the
        # disk by module_end at $9600 (directory entry 24: the star catalogue), and
        # the empty hall of fame (tools/genhof.py), rewritten in place.
        end_module = (build / 'wildhof.bin').read_bytes()
        hof_file = (build / 'NEOWILD.HOF').read_bytes()
        assert 0 < len(end_module) <= 0x2000 and len(hof_file) == 512
        (stage / 'NEOWILD.END#069600').write_bytes(end_module)
        (stage / 'NEOWILD.HOF#060000').write_bytes(hof_file)
        boot = (DEV / 'tools/prodos/boot.bin').read_bytes()
        boot = (boot + bytes(1024))[:1024]
        volume = Volume(VOLUME, 280, boot, prodos_date('2026-10-13T12:00'))
        volume.build(stage)
        lock_files(volume, keep={'NEOWILD.HOF'})
    finally:
        for path in stage.iterdir():
            path.unlink()
        stage.rmdir()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(volume.image))

    # Layout: the trunk plus the Sierra Nevada pack, as after the default
    # menu choice "2, RETURN" (what the tests load), and every pack.
    sierra = pack_info['2']['modules']
    trunk_modules = {str(i): dict(image=modules[17 if i == 18 else i][0],
                                  bank=BANK_NAMES[placed[17 if i == 18 else i][0]],
                                  address=placed[17 if i == 18 else i][1],
                                  length=len(raw_images[17 if i == 18 else i]),
                                  stored=len(images[17 if i == 18 else i]),
                                  window=modules[17 if i == 18 else i][1],
                                  **({'lz': lz[17 if i == 18 else i]}
                                     if (17 if i == 18 else i) in lz else {}))
                     for i in range(DIR_ENTRIES) if (17 if i == 18 else i) in placed}
    info = dict(packing=packing, blocks_used=volume.next_free, blocks=280,
                blocks_free=280 - volume.next_free,
                dat=trunk_stats, geo=geo,
                modules=dict(sorted({**trunk_modules, **sierra}.items(), key=lambda kv: int(kv[0]))),
                trunk_modules=trunk_modules,
                aux_free=[dict(bank=BANK_NAMES[b], start=s, end=e, free=e-s)
                          for b, s, e in place(dict(enumerate(
                              sprite_image(n)[0]
                              for n in regions_data[2]['sprites'])), free)[1]],
                aux_trunk_free=sum(e - s for _, s, e in free),
                pack_area=dict(bank='aux', start=pack_area[1], end=pack_area[2]),
                star_code=dict(bank=BANK_NAMES[SKYLC[0]], address=SKYLC[1], length=len(skylc)),
                dhgr_rows=dict(bank=BANK_NAMES[DROWS[0]], address=DROWS[1], length=len(drows)),
                packs=pack_info,
                region_text=sym['__REGIONTEXT_RUN__'], dhgr_tables=[tables_start, tables_end],
                end_module=dict(file='NEOWILD.END', bytes=len(end_module),
                                blocks=-(-len(end_module) // 512) + (len(end_module) > 512)),
                hof_file=dict(file='NEOWILD.HOF', bytes=len(hof_file), blocks=1),
                prepare_module=dict(file='NEOWILD.DAT', mark=marks[-1], bytes=len(prepare_module)),
                dat_file=dict(bytes=len(dat), blocks=-(-len(dat) // 512) + (len(dat) > 512),
                              marks=marks))
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
    args = parser.parse_args()
    info = build_disk(args.out, args.map, args.build, args.packing, args.layout)
    packs = ', '.join(f'R{r} {p["stored"]}' for r, p in info['packs'].items())
    print(f'{args.out}: NEOWILD.DAT {info["dat"]["raw"]} -> {info["dat"]["stored"]} bytes '
          f'({info["packing"]}, {info["dat"]["records"]} records); packs (bytes) {packs}; '
          f'{info["blocks_used"]}/{info["blocks"]} blocks')
