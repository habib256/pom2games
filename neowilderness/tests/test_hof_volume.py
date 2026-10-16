#!/usr/bin/env python3
"""The whole volume after a hall of fame write (docs/HOF.md section 10).

On 13 October 2026 a Sierra Nevada journey played in POM2 left the volume
directory with NEOWILD.DAT's EOF at $003F47 instead of $00BC47 (block 2,
byte $41), and the next boot stopped on "NEOWILD DISK ERROR $4C". That is
exactly what ProDOS 8 writes when it closes NEOWILD.DAT while its file
control block (main language card, bank 1, $D800) says "modified" with a
wrong EOF: a CLOSE rewrites the directory entry of a file opened with the
write right from its FCB. The volume now locks every file but NEOWILD.HOF.

On ../dist/NEOWILDERNESS.po (a2shot --iie, private copy, ejected and read
back):
  1. rights: every file of the volume directory but NEOWILD.HOF is read
     only (access $01); NEOWILD.HOF keeps the write right;
  2. stray FCB: at the loader's CLOSE of NEOWILD.DAT, its FCB is given the
     report's EOF ($3F in the middle byte) and the "modified" flag, as a
     stray write would; the loader still reaches the menu and not one byte
     of the volume changes (before the lock: block 2 byte $41, $BC -> $3F,
     the report's byte);
  3. a real journey: Sierra Nevada level 4, walks (the wild food scan
     rewrites MAP+28..MAP+33), meals, rests, views and a sleep, then QUIT,
     Y, ten hours and more. Since 14 October 2026 LOOK N/E/S/W puts the
     carried compass in use and turns the player (it used to answer "FIRST
     PUT DIRECTION AID IN USE" and leave the heading): the first look is
     LOOK S, as the walks that follow a LOOK N (or E) are blocked at once
     and the journey stops at 9 hours. The end module ranks it in the Sierra Nevada (region_number /
     journey_kind; with MAP+32 / MAP+33 it said "FREE JOURNEY: NOT
     RANKED"), a name is typed and saved, the loader comes back to its
     menu. From QUIT to that menu (NEOWILD.END, NEOWILD.HOF, the restart
     and the second load of NEOWILD.DAT), no code but ProDOS's stores into
     ProDOS's memory (main language card bank 1 and $E000-$FFFF, the global
     page except its bitmap): a2shot storewatch (watching the whole journey
     costs a quarter of an hour). After ejection every block equals the
     original image but NEOWILD.HOF's data block, which holds
     tools/score_ref.py's file; the directory is unchanged.

  test_hof_volume.py [DISK.po [wild.lbl]]
"""
import glob
import os
import re
import secrets
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(ROOT / 'dev/tools/prodos'))
sys.path.insert(0, str(HERE / 'tests'))
import a2test  # noqa: E402
import score as R  # noqa: E402
from read_volume import Image  # noqa: E402
from test_hof_game import screen, show, check  # noqa: E402

DISK = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'dist/NEOWILDERNESSXL.po'
LABELS = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / 'build/wild.lbl'
BLOCK = 512
FCB = 0xD800                    # ProDOS 8 file control blocks, 32 bytes each
FCB_EOF, FCB_DIRTY = 0x15, 0x1C
JOURNEY = ['WEAR PARKA', 'DRINK WATER 10 OZ', 'EAT CHEESE 8 OZ',
           'WALK 1 H', 'WALK 1 H', 'LOOK S', 'WALK 1 H', 'WALK 1 H',
           'EAT CHEESE 6 OZ', 'DRINK WATER 8 OZ', 'WALK 1 H', 'WALK 1 H',
           'REST 2 H', 'REST 2 H', 'REST 2 H', 'LOOK N', 'LOOK E',
           'SLEEP 8 H', 'WALK 1 H', 'LOOK S']


def entries(img):
    return {e[1:1 + (e[0] & 15)].decode(): e for e in img.entries(2)}


def private_image(work, nonce):
    """Identify the private copy even when every volume block is allocated.

    S5's last data block has padding beyond EOF: the nonce changes no file
    content, allocation bit or directory entry. This journey never saves S5.
    """
    img = bytearray(DISK.read_bytes())
    volume = Image(img)
    entry = entries(volume)['NEOWILD.S5']
    assert entry[0] >> 4 == 2, 'S5 must be a sapling file'
    eof = int.from_bytes(entry[0x15:0x18], 'little')
    assert 0 < eof % BLOCK <= BLOCK - len(nonce), 'S5 needs padding for the nonce'
    index = volume.block(int.from_bytes(entry[0x11:0x13], 'little'))
    n = (eof - 1) // BLOCK
    block = index[n] | index[256+n] << 8
    assert block
    at = (block + 1) * BLOCK - len(nonce)
    content = volume.read(entry)
    assert not any(img[at:at+len(nonce)]), 'S5 padding must be unused'
    img[at:at+len(nonce)] = nonce
    assert Image(img).read(entry) == content
    path = work / 'volume.po'
    path.write_bytes(img)
    return path, bytes(img)


def ejected(s, work, nonce, since):
    """Eject (POM2 writes the private copy back) and return its bytes."""
    other = work / 'other.po'
    other.write_bytes(bytes(143360))
    s.step('insert:' + str(other))
    for path in glob.glob('/tmp/a2shot-*.po'):
        try:
            if os.path.getmtime(path) >= since - 2 and nonce in Path(path).read_bytes():
                return Path(path).read_bytes()
        except OSError:
            continue
    raise AssertionError('private copy of the volume not found')


def changed_blocks(a, b):
    return sorted({i // BLOCK for i in range(len(a)) if a[i] != b[i]})


def rights():
    img = Image(DISK.read_bytes())
    files = entries(img)
    assert 'NEOWILD.HOF' in files and 'NEOWILD.DAT' in files
    for name, e in files.items():
        if name == 'NEOWILD.HOF' or (name.startswith('NEOWILD.S') and name[9:].isdigit()):
            assert e[0x1E] & 0x02, f'{name} must stay writable'   # hall of fame, saved games (lot 9)
        else:
            assert e[0x1E] == 0x01, f'{name}: access ${e[0x1E]:02X}, read only ($01) expected'
    print(f'  rights: files read only but NEOWILD.HOF and the saved games: OK')


def stray_fcb(L):
    """A stray write into NEOWILD.DAT's FCB before the loader's CLOSE."""
    with tempfile.TemporaryDirectory(prefix='hofvol-') as work:
        work = Path(work)
        nonce = secrets.token_bytes(16)
        disk, before = private_image(work, nonce)
        dat_key = entries(Image(before))['NEOWILD.DAT'][0x11:0x13]
        t0 = time.time()
        with a2test.Session(disk, iie=True, timeout=600) as s:
            s.step(L.until('ld_close', 30000))           # the trunk: NEOWILD.DAT
            s.step('peek:C08B:1')
            s.step('peek:C08B:1')                        # read RAM bank 1 (ProDOS)
            fcbs = s.step(f'peek:{FCB:04X}:256').dumps[0]
            slot = next(k for k in range(8) if fcbs[32 * k] and fcbs[32 * k + 0x0C:32 * k + 0x0E] == dat_key)
            fcb = FCB + 32 * slot
            eof = fcbs[32 * slot + FCB_EOF:32 * slot + FCB_EOF + 3]
            assert eof == entries(Image(before))['NEOWILD.DAT'][0x15:0x18], 'FCB EOF = directory EOF'
            s.step(f'poke:{fcb + FCB_EOF + 1:04X}:3F')       # the report's EOF, $003F47
            s.step(f'poke:{fcb + FCB_DIRTY:04X}:80')         # "modified"
            s.step('peek:C082:1')                        # the loader's ROM again
            r = s.step(f"until:{L['menu_key']:04X},{L['ld_error']:04X}:40000")
            assert f"PC={L['menu_key']:04X}" in r.out, 'the loader must reach its menu'
            after = ejected(s, work, nonce, t0)
    diff = [(hex(i), before[i], after[i]) for i in range(len(before)) if before[i] != after[i]]
    assert not diff, f'a stray FCB reached the disk: {diff[:8]}'
    print('  stray FCB (EOF $3F47, modified) at the CLOSE of NEOWILD.DAT: volume unchanged: OK')


def prodos_guard(out, L):
    """Stores of the game (not ProDOS) into ProDOS's memory, from the
    storewatch lines: main language card outside bank 2 $D001-$D0FF (the LZ
    decoder, docs/MEMORY.md 14), $D100-$D3FF (the bank 2 code of the view and
    ProDOS's QUIT code put back at exit, docs/MEMORY.md 15) and $D400-$DFFF,
    and the global page but its bitmap."""
    bad = []
    for line in out.splitlines():
        if not line.startswith('store '):
            continue
        f = line.split()
        pc, ea = int(f[1], 16), int(f[2], 16)
        lc = re.search(r'LC=(\d)(\d)(\d)(\d)(\d)', line).groups()
        bank2, altzp, ramwrt = lc[0] == '1', lc[2] == '1', lc[4] == '1'
        if pc >= 0xD000 or 0xBF00 <= pc < 0xC000:   # ProDOS (kernel, drivers, global page)
            continue
        if 0x0200 <= pc < 0x0400 and lc[3] == '1':  # the /RAM driver, run in auxiliary RAM
            continue
        if 0xC000 <= ea < 0xD000:                   # soft switches
            continue
        if ea < 0xC000:
            if ramwrt or 0xBF58 <= ea < 0xBF70:     # auxiliary RAM, or the bitmap
                continue
            bad.append(line)
        elif not altzp and not (bank2 and 0xD001 <= ea < 0xE000):
            bad.append(line)
    assert not bad, 'stores into ProDOS memory:\n' + '\n'.join(bad[:12])


def journey(L):
    with tempfile.TemporaryDirectory(prefix='hofvol-') as work:
        work = Path(work)
        nonce = secrets.token_bytes(16)
        disk, before = private_image(work, nonce)
        t0 = time.time()
        with a2test.Session(disk, iie=True, timeout=1800) as s:
            text = lambda: screen(s.step('peek:0400:1024').dumps[0])  # noqa: E731
            s.step(L.until('menu_key', 40000))
            s.step('key:1\r')                    # menu key 1: the Sierra Nevada
            s.step(L.until('idle', 40000))
            waits = ','.join(f'{L[n]:04X}' for n in ('idle', 'quit', 'keyboard_wait', 'wait_key'))
            for c in JOURNEY:
                s.step('key:' + c + '\r')
                s.step('wait:3')
                for _ in range(4):
                    r = s.step(f'until:{waits}:60000')
                    if f"PC={L['idle']:04X}" in r.out or f"PC={L['quit']:04X}" in r.out:
                        break
                    s.step('key: ')              # a message that waits for a key
                    s.step('wait:3')
                assert f"PC={L['idle']:04X}" in r.out, f'the journey ended during {c}'
            food = s.step('peek:7020:2').dumps[0]
            s.step('storewatch:BF00:FFFF')       # the end: NEOWILD.END, .HOF, restart
            s.step('key:QUIT\r')
            s.step('wait:30')
            s.step('key:Y')
            s.step(L.until('hof_key_wait', 30000))
            v = s.step(L.peek('hof_outcome', 8)).dumps[0]
            outcome, level, region, kind, progress, health = v[:6]
            hours = v[6] | v[7] << 8
            assert (outcome, level, region, kind) == (R.ABANDONED, 4, 2, 0), (v.hex(), food.hex())
            assert hours >= 10, hours
            c = R.score(progress, health, hours, outcome, level)
            want, _ = R.end_screen(c, 2, 'SIERRA NEVADA', False, R.empty_file(), '', phase='entry')
            check('name entry after a real journey', text(), want.bytes())
            for k in 'WALKER\r':
                s.step('key:' + k)
                s.step(L.until('hof_key_wait', 4000))
            want, new = R.end_screen(c, 2, 'SIERRA NEVADA', False, R.empty_file(), 'WALKER')
            check('saved', text(), want.bytes())
            s.step('key: ')
            s.step(L.until('menu_key', 40000))
            s.step('unstorewatch')
            prodos_guard(s.out, L)
            after = ejected(s, work, nonce, t0)
    files = entries(Image(before))
    hof_block = int.from_bytes(files['NEOWILD.HOF'][0x11:0x13], 'little')
    blocks = changed_blocks(before, after)
    assert blocks == [hof_block], f'blocks changed: {blocks} (only NEOWILD.HOF\'s {hof_block} may)'
    assert after[hof_block * BLOCK:(hof_block + 1) * BLOCK] == new, 'NEOWILD.HOF = tools/score_ref.py'
    assert entries(Image(after)) == files, 'directory entries unchanged'
    print(f"  Sierra journey of {hours} h with walks, QUIT: region 2, scenario, "
          f"score {c['score']}, saved; MAP+32/33 = {food.hex()} (food scan); "
          f"no store into ProDOS memory; only block {hof_block} changed: OK")


def main():
    if sys.platform != 'darwin' or not a2test.A2SHOT.exists():
        print('SKIP: a2shot (IIe POM2 core) is required')
        return
    L = a2test.labels(LABELS)
    rights()
    stray_fcb(L)
    journey(L)
    print('Volume after the hall of fame: OK')


if __name__ == '__main__':
    main()
