#!/usr/bin/env python3
"""Build the Neowilderness ProDOS volume (Apple IIe enhanced / IIc, 128 KB).

The volume holds PRODOS, NEOWILD.SYSTEM (src/boot.s) and NEOWILD.DAT: one
sequential file of records read once at boot. Main RAM images go to their
linked addresses; every module (TOPO included: src/topo.s draws it from the
resident map) and the pristine simulation go to auxiliary RAM, where memory.s copies them into their execution
windows. A native map (header byte 37: the Sierra comparison maps, mkmap
--native) carries its 224 x 168 fine geography: it becomes a compressed atlas
(tools/geo_atlas.atlas_bytes) loaded with its decoder (src/geoaux.s) into the
auxiliary language card, bank 1 view $D480-$FFF9 (lot 5). A map whose atlas
exceeds that budget is refused.

NEOWILD.DAT is a 128-byte record table followed by the payloads, back to
back. Record: kind, address, length, stored length; kind 0 end, 1 claim, otherwise
$80 | $40 (LZ, tools/pack_boot.py) | bank (0 main, 1 auxiliary, 2 auxiliary
language card bank 2, 3 bank 1). Stored data never exceeds 8 KB.
"""
import argparse
import hashlib
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
import geo_atlas                                # noqa: E402

VOLUME = 'NEOWILDERNESS'
CHUNK = 0x2000
TABLE_SIZE = 128                 # src/boot.s TABLE_SIZE: 18 records
MAIN, AUX, LC2, LC1 = 0, 1, 2, 3
BANK_NAMES = {AUX: 'aux', LC2: 'lc2', LC1: 'lc1'}
DIR_BANK = {AUX: 0, LC2: 1, LC1: 2}      # memory.s directory bank codes
# Auxiliary regions of the modules, in allocation order. $0000-$07FF holds
# the ProDOS /RAM driver code ($0200-$03FF) and the 80-column text page;
# $2000-$3FFF is the auxiliary half of the DHGR page. The language card
# bank 1 and the common $E000-$FFF9 belong to the fine geography (GEO_*).
REGIONS = [(AUX, 0x4000, 0xC000), (AUX, 0x0800, 0x2000), (LC2, 0xD000, 0xE000)]
GEO_CACHE = 0xD000               # 4 decoded tiles + woodland, not stored
GEO_CODE = 0xD480                # src/geoaux.s (segment GEOAUX), then the atlas
# Directory index -> (image, execution window). 18 is an alias of 17.
MODULES = {0: ('wildtop.bin', 0x5800), 1: ('wildvoc.bin', 0x5800), 2: ('wildscr.bin', 0x5800),
           3: ('wildsim.bin', 0x9600), 4: ('wildwat.bin', 0x5800),
           5: ('original_graphics/wreck.bin', 0x5800), 6: ('original_graphics/bear.bin', 0x5800),
           7: ('original_graphics/cougar.bin', 0x5800),
           8: ('original_graphics/rattlesnake.bin', 0x5800),
           9: ('original_graphics/cabin.bin', 0x5800), 10: ('wildsit.bin', 0x5800),
           11: ('wildprj.bin', 0x5800), 12: ('wildtrv.bin', 0x5800), 13: ('wildinp.bin', 0x5800),
           14: ('wilditm.bin', 0x5800), 15: ('wildhud.bin', 0x5800), 16: ('wildsta.bin', 0x5800),
           17: ('wildmed.bin', 0x5800), 19: ('wildmvi.bin', 0x5800), 20: ('wildtre.bin', 0x5800),
           21: ('wildadv.bin', 0x5800), 22: ('wildout.bin', 0x5800)}
DIR_ENTRIES = 23
# Boot costs measured in POM2 (IIe, Disk II, ProDOS 2.4.3; docs/MEMORY.md):
# guest cycles per stored byte read through MLI READ, per byte LZ-decoded.
DISK_CYCLES = 200
DECODE_CYCLES = 46
WINDOW_LIMIT = {0x5800: 0x0800, 0x9600: 0x2000}


def labels(build):
    return {name: int(addr, 16) for addr, name in
            re.findall(r'^al ([0-9A-Fa-f]+) \.(\w+)$', (build / 'wild.lbl').read_text(), re.M)}


def place(images):
    """First fit, largest first, deterministic: {index: (bank, address)}."""
    free = [list(region) for region in REGIONS]
    placed = {}
    for index in sorted(images, key=lambda i: (-len(images[i]), i)):
        size = len(images[index])
        for region in free:
            if region[2] - region[1] >= size:
                placed[index] = (region[0], region[1])
                region[1] += size
                break
        else:
            raise SystemExit(f'auxiliary memory full: module {index}, {size} bytes')
    return placed, free


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


def records(main, aux, first, packing, cache=None):
    """NEOWILD.DAT: a 128-byte record table, then the payloads back to back.

    The loader reads the table once, then each payload with one READ.
    Measured: block-aligned payloads read slower in POM2's Disk II than this
    contiguous stream through the I/O buffer (docs/MEMORY.md).
    """
    table, payloads = bytearray(), bytearray()
    stats = dict(raw=0, stored=0, records=0)

    def emit(bank, address, data):
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

    for bank, address, data in first:
        emit(bank, address, data)
    table.extend(struct.pack('<BHHH', 1, 0, 0, 0))
    for bank, address, data in aux + main:
        emit(bank, address, data)
    table.extend(struct.pack('<BHHH', 0, 0, 0, 0))
    assert len(table) <= TABLE_SIZE, 'record table too long'
    out = bytes(table + bytes(TABLE_SIZE - len(table)) + payloads)
    stats['file'] = len(out)
    return out, stats


def build_disk(out, map_path=None, build=None, packing='auto', layout=None):
    build = Path(build) if build else HERE / 'build'
    out = Path(out)
    from mkmap import MAP_BYTES, FOREST_BYTES
    mapdata = Path(map_path).read_bytes() if map_path else (build / 'map.bin').read_bytes()
    sym = labels(build)

    images = {}
    for index, (name, window) in MODULES.items():
        data = (build / name).read_bytes()
        assert 0 < len(data) <= WINDOW_LIMIT[window], (name, len(data))
        images[index] = data
    placed, free = place(images)
    directory = bytearray(DIR_ENTRIES * 7)
    for index in range(DIR_ENTRIES):
        source = 17 if index == 18 else index
        bank, address = placed[source]
        window = MODULES[source][1]
        directory[index*7:index*7+7] = struct.pack('<BHHH', DIR_BANK[bank], address,
                                                   len(images[source]), window)
    resident = bytearray((build / 'wildres.bin').read_bytes())
    offset = sym['module_dir'] - 0xB600
    resident[offset:offset + len(directory)] = directory

    # Auxiliary blobs: contiguous placements of one region form one blob.
    blobs = {}
    for index, (bank, address) in sorted(placed.items(), key=lambda kv: (kv[1], kv[0])):
        key = (bank, next(r[1] for r in REGIONS if r[0] == bank and r[1] <= address < r[2]))
        blob = blobs.setdefault(key, [address, bytearray()])
        assert blob[0] + len(blob[1]) == address
        blob[1].extend(images[index])
    aux = [(bank, start, bytes(data)) for (bank, _), (start, data) in sorted(blobs.items())]

    # Fine geography area (language card bank 1 view): free on a legacy map.
    code = (build / 'wildgeo.bin').read_bytes()
    base = sym['geo_atlas']
    assert GEO_CODE + len(code) == base, 'wildgeo.bin must end at geo_atlas'
    geo = dict(loaded=False, cache=GEO_CACHE, code_address=GEO_CODE, code=len(code), base=base,
               budget=geo_atlas.ATLAS_END - base, size=0, free=geo_atlas.ATLAS_END - GEO_CACHE)
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
        aux.append((LC1, GEO_CODE, code + atlas))
    mask = mapdata[MAP_BYTES:MAP_BYTES+FOREST_BYTES] if mapdata[26] else b''
    if len(mask) != FOREST_BYTES:
        mask = bytes(FOREST_BYTES)
    low = bytearray(0x1800)                       # $0800-$1FFF, gaps restored as zero
    for address, data in ((0x0800, mask), (0x0926, (build / 'wildforest.bin').read_bytes()),
                          (0x0A00, (build / 'wildtxt.bin').read_bytes()),
                          (0x1000, (build / 'wildlo.bin').read_bytes())):
        low[address - 0x0800:address - 0x0800 + len(data)] = data
    first = [(MAIN, 0x6000, (build / 'wild.bin').read_bytes())]
    main = [(MAIN, 0x0800, bytes(low)),
            (MAIN, 0x4000, (build / 'wildgame.bin').read_bytes()),
            (MAIN, 0x7000, mapdata[:MAP_BYTES]),
            (MAIN, 0xB600, bytes(resident))]
    data, stats = records(main, aux, first, packing, build / 'lz-cache')

    stage = Path(tempfile.mkdtemp(prefix='neowild-stage-'))
    try:
        (stage / 'PRODOS#FF0000').write_bytes((DEV / 'tools/prodos/PRODOS').read_bytes())
        (stage / 'NEOWILD.SYSTEM#FF2000').write_bytes((build / 'NEOWILD.SYSTEM').read_bytes())
        (stage / 'NEOWILD.DAT#060000').write_bytes(data)
        boot = (DEV / 'tools/prodos/boot.bin').read_bytes()
        boot = (boot + bytes(1024))[:1024]
        volume = Volume(VOLUME, 280, boot, prodos_date('2026-10-13T12:00'))
        volume.build(stage)
    finally:
        for path in stage.iterdir():
            path.unlink()
        stage.rmdir()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(volume.image))
    info = dict(packing=packing, blocks_used=volume.next_free, blocks=280,
                dat=stats, geo=geo,
                modules={str(i): dict(image=MODULES[17 if i == 18 else i][0],
                                      bank=BANK_NAMES[placed[17 if i == 18 else i][0]],
                                      address=placed[17 if i == 18 else i][1],
                                      length=len(images[17 if i == 18 else i]),
                                      window=MODULES[17 if i == 18 else i][1])
                         for i in range(DIR_ENTRIES)},
                aux_free=[dict(bank=BANK_NAMES[b], start=s, end=e, free=e-s) for b, s, e in free])
    if layout:
        Path(layout).write_text(json.dumps(info, indent=1) + '\n')
    return info


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--map')
    parser.add_argument('--build')
    parser.add_argument('--packing', choices=('raw', 'lz', 'auto'), default='auto')
    parser.add_argument('--layout', help='write the placement/record summary as JSON')
    args = parser.parse_args()
    info = build_disk(args.out, args.map, args.build, args.packing, args.layout)
    print(f'{args.out}: NEOWILD.DAT {info["dat"]["raw"]} -> {info["dat"]["stored"]} bytes '
          f'({info["packing"]}, {info["dat"]["records"]} records), '
          f'{info["blocks_used"]}/{info["blocks"]} blocks')
