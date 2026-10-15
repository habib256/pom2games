#!/usr/bin/env python3
"""Zero disk access after the preload; RAM transfers counted and exact.

Two independent observations cover every disk path of ordinary play:
the MLI counters of memory.s (every call made through mli_call, including
the loader's) and an a2shot watch on the ProDOS MLI entry $BF00, which also
catches a call that would bypass the counters. DOS 3.3 is absent: no code
of the link refers to its entry points, and RWTS/BLOAD/$03D0 never run.
The script runs on the default (legacy) map, then on a native map whose fine
geography is resident (lot 5): the former on-demand NEOWILD.GEO reads are gone.
Docs/MEMORY.md 14: on NeoWildernessXL, CAMP, MEDVIEW, TREE and ORIENT are read
by block from NEOWILD.BLK when loaded (memory.s disk_fetch); since docs/MEMORY.md
18 TOPOGEN too, on every disk, when the TOPO page opens: the steps of
DISK_LOADS make exactly those READ_BLOCK calls, 512 bytes each, and nothing
else.
"""
import json
import re
import sys
import tempfile
from common import HERE, L, DISK, a2test, disk_with, text_screen
from scenario import SCRIPT, play

COUNTERS = (('mli_calls', 2), ('mli_reads', 2), ('mli_bytes', 3),
            ('xfer_count', 2), ('xfer_bytes', 3), ('overlay_reads', 2),
            ('geo_queries', 3), ('geo_decodes', 2))


def counters(session):
    return {name: int.from_bytes(session.step(L.peek(name, size)).data, 'little')
            for name, size in COUNTERS}


DOS_TARGETS = {0x03D0 + k for k in range(0x20)} | {0xB7B5, 0xA56E}
OPCODES = {0x20, 0x4C, 0x6C, 0xAD, 0x8D, 0x2C}


def static_check():
    """No DOS 3.3 entry, RWTS call or BLOAD command survives in the link.

    Every assembled instruction of build/wild.lst and build/boot.lst is
    decoded from the listing: an absolute JSR/JMP/LDA/STA/BIT operand may
    not reach the DOS vectors $03D0-$03EF, RWTS $B7B5 or BLOAD $A56E.
    """
    for name in ('wild', 'boot'):
        for line in (HERE / f'build/{name}.lst').read_text().splitlines():
            m = re.match(r'^[0-9A-F]{6}r \d+\s+((?:[0-9A-Fr]{2} ){3})', line)
            if not m:
                continue
            fields = m.group(1).split()
            if 'rr' in fields[1:] or not all(re.fullmatch('[0-9A-F]{2}', f) for f in fields):
                continue
            opcode, lo, hi = (int(f, 16) for f in fields)
            assert not (opcode in OPCODES and lo | hi << 8 in DOS_TARGETS), line
    for path in [HERE / 'build/wild.bin', HERE / 'build/NEOWILD.SYSTEM'] + sorted(
            (HERE / 'build').glob('wild*.bin')):
        assert b'BLOAD' not in path.read_bytes(), path
    names = (HERE / 'build/wild.lbl').read_text()
    assert 'dos_cmd' not in names and 'apple2_zp_save' not in names


# Steps of scenario.SCRIPT that load a module of NEOWILD.BLK (XL): MEDVIEW (19)
# shows the body for USE SUNSCREEN and USE FIRSTAID KIT; TOPOGEN (0) the TOPO
# page on every disk (docs/MEMORY.md 18).
DISK_LOADS = {'USE SUNSCREEN': (19,), 'USE FIRSTAID KIT': (19,), 'TOPO': (0,),
              # NeoWildernessXL (docs/MEMORY.md 29): STATUS and its post-its
              # read with the top pages (none on a comparison disk)
              'STATUS': (16,), 'INVENTORY': (16,), 'HELP': (16,)}


def disk_blocks():
    """{module: blocks} of NEOWILD.BLK on the tested disk (build/layout.json)."""
    layout = json.loads((HERE / 'build/layout.json').read_text())
    return {int(m): d['blocks'] for m, d in layout['disk']['modules'].items()}


def play_counted(disk, title, blocks=None):
    """The ordinary-play script on `disk`, every MLI call counted and watched;
    `blocks`: its NEOWILD.BLK modules (none: no disk access at all)."""
    with a2test.Session(disk, timeout=900) as s:
        s.step(L.until('idle', 40000))
        if blocks == 'directory':           # its NEOWILD.BLK modules (bank $40)
            blocks = {m: -(-int.from_bytes(s.step(L.peek('module_dir', 2, m * 7 + 3)).data, 'little') // 512)
                      for m in (0, 4, 19) if s.step(L.peek('module_dir', 1, m * 7)).data[0] == 0x40}
        blocks = blocks or {}
        boot = counters(s)
        assert boot['xfer_count'] >= 1
        # Watch the ProDOS entry for the rest of the run.
        s.step(f'watch:BF00')
        rows = []
        state = dict(before=counters(s))

        def each(step):
            after = counters(s)
            before = state['before']
            rows.append((step[0], {k: after[k] - before[k] for k in after}))
            state['before'] = after

        out_before = len(s.out)
        play(s, L, SCRIPT, each)
        watched = s.out[out_before:].count('watch BF00')
        final = counters(s)
    print(f'  {title} boot: {boot["mli_calls"]} MLI calls, {boot["mli_reads"]} reads, '
          f'{boot["mli_bytes"]} bytes read; {boot["xfer_count"]} RAM transfers')
    failures = 0
    expected_total = 0
    for keys, delta in rows:
        label = keys.replace('\r', '').replace('\\', '')
        reads = sum(blocks.get(m, 0) for m in DISK_LOADS.get(label, ()))
        expected_total += reads
        ok = delta['mli_calls'] == reads and delta['mli_reads'] == reads and \
            delta['mli_bytes'] == 512 * reads
        failures += not ok
        geo = (f', geography {delta["geo_queries"]:3} queries {delta["geo_decodes"]} decodes'
               if delta['geo_queries'] else '')
        print(f'  {label:18} disk calls {delta["mli_calls"]}, module loads '
              f'{delta["overlay_reads"]:2}, RAM transfers {delta["xfer_count"]:2} '
              f'({delta["xfer_bytes"]:6} bytes){geo}: {"OK" if ok else "FAIL"}')
    assert final['xfer_count'] - boot['xfer_count'] == sum(d['xfer_count'] for _, d in rows)
    print(f'  ProDOS MLI entry $BF00 reached {watched} times after the preload '
          f'({expected_total} READ_BLOCK of NEOWILD.BLK expected)')
    return bool(failures or watched != expected_total
                or final['mli_calls'] - boot['mli_calls'] != expected_total), final, boot


# Lot 9 (docs/SAVE.md): SAVE and RESTORE are the only commands that may call
# the MLI: NEOWILD.SAV (OPEN, READ, CLOSE), then SAVE: OPEN, READ of the
# header, SET_MARK, WRITE, CLOSE; RESTORE: OPEN, READ, CLOSE.
DISK_COMMANDS = (('WALK 1 H', 0), ('SAVE 1', 8), ('EAT CHEESE 4 OZ', 0), ('RESTORE 1', 6),
                 ('REST 2 H', 0))


def save_restore_counted():
    with a2test.Session(DISK, timeout=900) as s:
        s.step(L.until('idle', 40000))
        s.step('watch:BF00')
        for line, allowed in DISK_COMMANDS:
            before, out_before = counters(s), len(s.out)
            play(s, L, [(line + '\r', 'idle', None)])
            delta = counters(s)['mli_calls'] - before['mli_calls']
            watched = s.out[out_before:].count('watch BF00')
            assert delta == watched == allowed, (line, delta, watched, allowed)
            print(f'  {line:18} disk calls {delta} (ProDOS entry reached {watched} times): OK')


def main():
    static_check()
    print('  no DOS 3.3 entry, RWTS, BLOAD or command buffer left in the link: OK')
    failed, final, boot = play_counted(DISK, 'default map', disk_blocks())
    assert final['geo_queries'] == 0, 'a legacy map queried the fine geography'
    # A native map (fine geography resident in the auxiliary language card,
    # lot 5): the same script, with fine queries and tile decodes.
    from test_geo_resident import generated_native
    with tempfile.TemporaryDirectory() as tmp:
        native = generated_native()[0]
        # Lot 4 (docs/MEMORY.md 16): a native comparison disk whose atlas
        # leaves too little store reads MEDVIEW (and CAMP) from NEOWILD.BLK
        # (tools/build_disk.py), as XL does: the directory says which.
        failed_native, final, boot = play_counted(disk_with(tmp, native), 'native map', 'directory')
    print(f'  native map: {final["geo_queries"] - boot["geo_queries"]} fine queries, '
          f'{final["geo_decodes"] - boot["geo_decodes"]} tiles decoded after the preload')
    if failed or failed_native:
        print('FAIL: disk access during ordinary play')
        sys.exit(1)
    save_restore_counted()
    print('Zero disk reads after the preload: OK')


if __name__ == '__main__':
    main()
