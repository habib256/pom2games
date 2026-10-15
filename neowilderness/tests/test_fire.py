#!/usr/bin/env python3
"""The animated campfire (src/fire.s, tools/genfire.py; docs/CAMP.md 8).

On both editions (the module is read from NEOWILD.BLK when the fire
appears): after MAKE FIRE, at the prompt, the fire appears over the view
(one read, four blocks, none between frames), each frame equals
tools/genfire.frame_pixels over the bare view (the rest of both DHGR banks
untouched), frames follow one another; every screen (STATUS, TOPO), a turn,
LOOK UP and DOUSE see the bare view, byte for byte; a key arriving during
the read cuts it and the command is read whole; the fire stays on its cell.

Anchored in the world (NeoWildernessXL): the fire keeps the bearing the
player faced when lighting it (fire_bear) and is drawn, like the local art
of src/project.s, at pixel 56 + (fire_bear - heading) (mod 560 into
-280..279), clipped at the view's edges, absent outside -83..83: LOOK R and
LOOK L (45 degrees) put it half out of the view on either side, LOOK BACK
takes it away, an arrow turn (22.5 degrees) moves it by 35 pixels; each
time the frame equals the genfire frame at that place over the bare view.

As in the original it burns until DOUSE (decision of 15 October 2026, no
lifetime): the original's run of tools/re_camp_probe.py (LONG_FIRE, five
WAIT 4, rain poked before the last two) is replayed, the weather held dry
then rainy at every health update; the fire burns after each command as in
build/re_camp/results.json (when present), no message, WALK refused (msg
132), still drawn whole at the same pace; SAVE and RESTORE keep it and its
bearing; DOUSE puts it out.
"""
import json
import re
import sys

from common import HERE, L, DISK, DISK140, a2test, fp, text_screen
sys.path.insert(0, str(HERE / 'tools'))
import genfire as G     # noqa: E402
import dhgr_ref as R    # noqa: E402
from hgr_tables import hgr_offset   # noqa: E402

IDLE = L.until('idle', 20000)
AFTER_TICK = L['fire_idle'] + 3          # fire_idle's JMP idle: a whole turn done
fails = []
EDITION = ''
MHZ = 1.0205e6


def check(name, ok, detail=''):
    name = f'{EDITION}: {name}'
    print(f'  {name}: {"OK" if ok else "FAIL"}' + (f' {detail}' if not ok and detail else ''))
    if not ok:
        fails.append(name)


def say(s, text, answer=' '):
    s.step(f'key:{text}')
    s.step('press:\\r')
    s.step('wait:1')
    for _ in range(8):
        r = s.step(f'until:{L["idle"]:04X},{L["keyboard_wait"]:04X}:40000')
        if int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16) == L['idle']:
            return
        s.step(f'key:{answer}')


def banks(s):
    main = s.step('peek:2000:8192').data
    s.step('poke:C055:00')
    aux = s.step('peek:2000:8192').data
    s.step('poke:C054:00')
    return bytes(main), bytes(aux)


def b(s, name):
    return s.step(L.peek(name)).data[0]


def shown(s, frames=150):
    """Run the idle loop until the fire is on screen and a turn has ended."""
    for _ in range(frames):
        s.step('wait:2')
        if b(s, 'fire_st'):
            s.step(f'until:{AFTER_TICK:04X}:100')
            return True
    return False


def next_frame(s):
    s.step(L.poke('fm_cnt', 1))
    s.step(L.poke('fm_cnt', 1, 1))
    s.step(L.until('fire_tick', 100))
    s.step(f'until:{AFTER_TICK:04X}:200')
    return b(s, 'fm_frame')


def expected(bare, frame, night=False, x0=G.X0):
    """The bare view with the frame at pixel x0 (None: out of view), clipped."""
    page = R.decode(*bare)
    if x0 is None:
        return page
    for y, row in enumerate(G.frame_pixels(frame, night)):
        for x, c in enumerate(row):
            if c is not None and 0 <= x0 + x < 140:
                page[G.TOP + y][x0 + x] = c
    return page


def fire_x(bear, heading):
    """src/fire.s fm_show (src/project.s project_center): the fire's first
    column, or None out of view."""
    d = (bear - heading) % 560
    ang = d if d < 280 else d - 560
    return G.X0 + ang if -84 < ang < 84 else None


def same_view(a, b):
    """Rows 0..175 of both banks (176..191: the menu's hidden image)."""
    return all(a[k][hgr_offset(y):hgr_offset(y) + 40] == b[k][hgr_offset(y):hgr_offset(y) + 40]
               for k in (0, 1) for y in range(176))


def word(s, name):
    d = s.step(L.peek(name, 2)).data
    return d[0] | d[1] << 8


def hour(s):
    return fp(s.step(L.peek('s_hour', 5)).data)


def cycles(r):
    return r.cycles[-1]


def edition(disk, name):
    global EDITION
    EDITION = name
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        say(s, 'USE MATCHES')
        say(s, 'MAKE FIRE')
        bare = banks(s)
        check('at the prompt after MAKE FIRE: the bare view first (the fire waits)', b(s, 'fire_st') == 0)
        # say() stopped at the prompt's first idle turn: the latency from there.
        t0 = cycles(s.step(L.until('idle', 100)))
        reads = word(s, 'mli_reads')
        t1 = cycles(s.step(L.until('disk_fetch', 200000)))
        t2 = cycles(s.step(f'until:{L["fm_show"]:04X}:5000000'))
        t3 = cycles(s.step(f'until:{AFTER_TICK:04X}:1000000'))
        check('then the fire appears, read from NEOWILD.BLK (four blocks)',
              b(s, 'fire_st') == 1 and word(s, 'mli_reads') - reads == 4, word(s, 'mli_reads') - reads)
        latency = (t1 - t0, t2 - t1, t3 - t2)
        print(f'  {name}: appearance after the prompt: wait {latency[0] / MHZ:.3f} s, '
              f'read {latency[1] / MHZ:.3f} s, first frame {latency[2] / MHZ:.3f} s, '
              f'total {(t3 - t0) / MHZ:.3f} s')
        frames, ok = [], True
        reads = word(s, 'mli_reads')
        for _ in range(6):
            f = b(s, 'fm_frame')
            frames.append(f)
            got = R.decode(*banks(s))
            ok &= got == expected(bare, f, b(s, 'sky_mood') >= G.NIGHT_MOOD)
            next_frame(s)
        check('six frames: each one the art over the bare view, nothing else touched', ok, frames)
        check('the frames follow one another', frames == [(frames[0] + i) % 4 for i in range(6)], frames)
        check('no disk read between frames (the module stays in its window)', word(s, 'mli_reads') == reads)

        s.step('key:\x0b')                       # UP: STATUS
        s.step(L.until('keyboard_wait', 20000))
        check('STATUS: the view under it is bare', same_view(banks(s), bare))
        s.step('key:\x1b')
        s.step(IDLE)
        check('back from STATUS: the bare view, then the fire again',
              same_view(banks(s), bare) and b(s, 'fire_st') == 0 and shown(s))

        say(s, 'TOPO')
        check('back from TOPO: the bare view', same_view(banks(s), bare) and b(s, 'fire_st') == 0)
        shown(s)

        s.step('key:\x15')                       # RIGHT: the view turns
        s.step('wait:1')
        s.step(IDLE)
        turned = banks(s)
        check('after a turn: no fire before the next appearance', b(s, 'fire_st') == 0)
        check('then the fire on the turned view', shown(s))
        if name == 'NeoWildernessXL':
            check('an arrow turn (22.5 degrees right): the fire 35 pixels left',
                  fire_x(word(s, 'fire_bear'), word(s, 'heading')) == G.X0 - 35
                  and placed(s, turned, G.X0 - 35))
        s.step('key:\x08')
        s.step('wait:1')
        s.step(IDLE)
        shown(s)
        check('turned back: the fire over the same view', R.decode(*banks(s)) == expected(bare, b(s, 'fm_frame')))

        if name == 'NeoWildernessXL':
            anchored(s)

        say(s, 'LOOK UP')                         # typed over the animated fire
        check('a command typed over the animated fire is read whole', b(s, 'tilt') == 1)
        check('LOOK UP: no fire (the player\'s feet are out of view)', not shown(s, 20))
        say(s, 'LOOK AHEAD')
        check('LOOK AHEAD: the fire again', shown(s))

        # A key arriving while the module is read: the read stops at the end
        # of the block, the key and the rest of the command are read whole.
        say(s, 'LOOK AHEAD')
        c0 = cycles(s.step(L.until('disk_fetch', 200000)))
        s.step('press:U')
        c1 = cycles(s.step(IDLE))
        cut = s.step(L.peek('df_left')).data[0]
        print(f'  {name}: the key waits {(c1 - c0) / MHZ:.3f} s (the first block)')
        s.step('wait:1')                        # idle takes the U
        s.step('key:SE FIRE')
        s.step('press:\r')
        s.step('wait:1')
        s.step(IDLE)
        check('a key during the read cuts it; the command typed then is read whole',
              cut > 0 and b(s, 'fire_near') == 1, (cut, b(s, 'fire_near')))
        check('then the fire after the next quiet spell', shown(s))

        # The fire belongs to its cell (camp_walk lets the player walk away
        # when an animal shares it): drawn only on that cell.
        say(s, 'LOOK AHEAD')
        x = word(s, 'px') >> 8
        s.step(L.poke('px', x + 1, 1))
        check('the player on another cell: no fire there', not shown(s, 30))
        s.step(L.poke('px', x, 1))
        check('back on its cell: the fire', shown(s))

        say(s, 'DOUSE FIRE')
        check('DOUSE FIRE: the bare view, no fire any more',
              same_view(banks(s), bare) and not shown(s, 20) and same_view(banks(s), bare))
    return t3 - t0


def placed(s, bare, want):
    """The fire on screen (shown) at pixel want (None: nothing drawn) over
    the bare view, each of the next two frames too."""
    night = b(s, 'sky_mood') >= G.NIGHT_MOOD
    ok = (b(s, 'fm_vis') >= 0x80) == (want is not None)
    for _ in range(2):
        ok &= R.decode(*banks(s)) == expected(bare, b(s, 'fm_frame'), night, want)
        next_frame(s)
    return ok


def look(s, cmd, want, label):
    say(s, cmd)
    bare = banks(s)
    ok = b(s, 'fire_st') == 0 and shown(s)
    x = fire_x(word(s, 'fire_bear'), word(s, 'heading'))
    check(label, ok and x == want and placed(s, bare, want), (x, want))


def anchored(s):
    """The fire keeps its bearing: LOOK R, L, BACK move it or take it away."""
    look(s, 'LOOK R', G.X0 - 70, 'LOOK R (45 degrees): the fire half out of the view on the left')
    look(s, 'LOOK L', G.X0, 'LOOK L back: the fire centred again')
    look(s, 'LOOK L', G.X0 + 70, 'LOOK L (45 degrees): the fire half out of the view on the right')
    look(s, 'LOOK R', G.X0, 'LOOK R back: centred')
    look(s, 'LOOK B', None, 'LOOK BACK: the fire behind, nothing drawn, the view bare')
    reads = word(s, 'mli_reads')
    for _ in range(3):
        next_frame(s)
    check('behind: no frame, no read while the prompt waits', word(s, 'mli_reads') == reads
          and b(s, 'fm_vis') == 0)
    look(s, 'LOOK B', G.X0, 'LOOK BACK again: centred')


def command(s, text, sky=None, answer=' '):
    """A command run to the prompt, the weather held (sky) at each health
    update. Returns the result's text."""
    jump = L['health']                       # game.s: the health update
    s.step(f'key:{text}')
    s.step('press:\\r')
    s.step('wait:1')
    for _ in range(400):
        r = s.step(f'until:{L["idle"]:04X},{L["keyboard_wait"]:04X},{jump:04X}:400000')
        pc = int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16)
        if pc == L['idle']:
            break
        if pc == L['keyboard_wait']:
            s.step(f'key:{answer}')
            continue
        if sky is not None:
            s.step(L.poke('weather_sky', sky))
        s.step(L.until('injury_health', 2000))
    return ' '.join(' '.join(l[:39].split()) for l in text_screen(s.step('peek:0400:1024').data)[20:24])


# tools/re_camp_probe.py LONG_FIRE: (command, sky held during it)
LONG_FIRE = (('USE MATCHES', 0), ('MAKE FIRE', 0), ('WAIT 4', 0), ('WAIT 4', 0), ('WAIT 4', 0),
             ('WAIT 4', 2), ('WAIT 4', 2), ('DOUSE FIRE', 2))


def original_long_fire():
    """The original's fire after each LONG_FIRE command (True: burning), or
    None without build/re_camp/results.json (make test-original)."""
    path = HERE / 'build/re_camp/results.json'
    if not path.exists():
        return None
    rows = [r for r in json.loads(path.read_text())['game'] if r.get('long_fire')][1:]
    return [r['state']['fire'][0] == 0 for r in rows] or None


def burns(disk):
    """The fire burns until DOUSE, hours on, dry or in rain."""
    global EDITION
    EDITION = 'until DOUSE'
    orig = original_long_fire()
    want = orig or [False, True, True, True, True, True, True, False]
    if orig is None:
        print('  (build/re_camp/results.json missing: the original\'s answers assumed)')
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        got, texts, h0 = [], [], None
        for text, sky in LONG_FIRE[:-1]:
            texts.append(command(s, text, sky))
            got.append(b(s, 'fire_on') == 1)
            if text == 'MAKE FIRE':
                h0 = hour(s)
        hours = (hour(s) - h0) % 24
        check('MAKE FIRE then five WAIT 4, rain held for the last two: burning after each command, as the original',
              got == want[:-1] and hours >= 12, (got, want, hours))
        check('no message about the fire going out', not any('FIRE' in t and 'OUT' in t for t in texts), texts)
        check('WALK refused while it burns (msg 132)', 'SMOKEY' in command(s, 'WALK', 2))
        say(s, 'LOOK AHEAD')
        night = b(s, 'sky_mood') >= G.NIGHT_MOOD
        bare = banks(s)
        ok = shown(s) and word(s, 'fm_cnt') >> 8 == 14
        frames = []
        for _ in range(4):
            frames.append(b(s, 'fm_frame'))
            ok &= R.decode(*banks(s)) == expected(bare, frames[-1], night)
            next_frame(s)
        check('hours later: the same fire drawn, whole, at the same pace', ok, frames)
        say(s, 'LOOK R')
        bear = word(s, 'fire_bear')
        say(s, 'SAVE 1', 'Y')
        s.step(L.poke('fire_on', 0))
        s.step(L.poke('fire_bear', 0))
        s.step(L.poke('fire_bear', 0, 1))
        say(s, 'RESTORE 1', 'Y')
        check('SAVE then RESTORE: the fire burns again at its bearing',
              (b(s, 'fire_on'), word(s, 'fire_bear')) == (1, bear), (b(s, 'fire_on'), bear))
        say(s, 'LOOK L')
        view = banks(s)
        command(s, LONG_FIRE[-1][0])
        check('DOUSE FIRE: out, as the original', (b(s, 'fire_on') == 1) == want[-1]
              and b(s, 'fire_on') == 0 and not shown(s, 20) and same_view(banks(s), view))


def main():
    edition(DISK, 'NeoWildernessXL')
    edition(DISK140, 'Neowilderness 140 KB')
    burns(DISK)
    print('Animated campfire: ' + ('OK' if not fails else 'FAILED: ' + ', '.join(fails)))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
