#!/usr/bin/env python3
"""An animal present is always seen (user rule of 15 October 2026: "quand un
animal est là, on doit voir son sprite sauf dans nos abris").

PROJECT's module_animal draws the animal of the player's cell after the
whole view (game.s animal_view), facing the player whatever the heading,
centred, over the site of the cell and everything else; each view is
compared pixel for pixel with tools/dhgr_ref.view (tests/scene_ref
animal_geometry, dhgr_palette.Lighting.animal) on NeoWildernessXL:

- a site and the animal on the same cell, both drawn (the original's two
  slots): the wreck of the start cell, the shelter (the log) of the map;
- every direction: LOOK R, L, BACK, N (with the compass), the arrow turns,
  LOOK DOWN (the rattlesnake lies low: allowed), LOOK UP (the one view
  without the animal, as in the original), LOOK AHEAD;
- a campfire on the cell: the animal right of the fire when the fire is left
  of the centre (the fire lit facing the heading included), left of it
  otherwise, never overlapping (the fire then drawn at the prompt touches
  its own columns only); MAKE FIRE itself; a wide sprite (the crocodile of
  New Guinea, 72 columns) clipped at the right edge, or left of the fire;
- without light: the night silhouette (night without a full Moon: "NOT
  ENOUGH LIGHT." still), the silhouette moods (sunset), the dim ones
  (nautical twilight);
- ENTER SHELTER keeps the animal (D4), no view inside; EXIT SHELTER shows
  it again in front of the shelter;
- a generated map: the record goes when the player walks off its cell (the
  next view shows no animal); a native map: walking away is still the
  animal's reaction (no step).
Screenshots: build/animal_site.png, build/animal_look_back.png,
build/animal_fire.png, build/animal_night.png.
"""
import re
import sys
import tempfile

from common import (HERE, L, DISK, a2test, dhgr, dhgr_view, dhgr_page, mood_name, state,
                    view_diff, menu_keys, text_screen, disk_with)
from test_sprites import resident_stars, LIST_BYTES
from test_boot import expected_map
import scene_ref

R = dhgr()
IDLE = L.until('idle', 20000)
MAP = (HERE / 'build/map.bin').read_bytes()
SX, SY = int.from_bytes(MAP[2:4], 'little'), int.from_bytes(MAP[4:6], 'little')
HEAD = int.from_bytes(MAP[6:8], 'little')
fails = []
DEBUG = None                    # a directory: PNGs of the views that differ


def check(name, ok, detail=''):
    print(f'  {name}: {"OK" if ok else "FAIL"}' + (f' {detail}' if not ok and detail != '' else ''))
    if not ok:
        fails.append(name)


def boot(s, keys=None):
    for step in keys or []:
        s.step(step)
    s.step(L.until('game_start', 20000))
    for name in ('forest_enabled', 'sky_enabled', 'ui_enabled'):
        s.step(L.poke(name, 0))
    s.step(IDLE)
    s.step(L.poke('nature_frequency', 0))


def typed(s, text):
    s.step(f'key:{text}')
    s.step('press:\\r')
    s.step('wait:1')
    s.step(IDLE)


def key(s, k):
    s.step(f'key:{k}')
    s.step('wait:1')
    s.step(IDLE)


def b(s, name, offset=0):
    return s.step(L.peek(name, 1, offset)).data[0]


def place(s, x, y, h=None):
    s.step(L.poke('px', x & 255))
    s.step(L.poke('px', x >> 8, 1))
    s.step(L.poke('py', y & 255))
    s.step(L.poke('py', y >> 8, 1))
    if h is not None:
        s.step(L.poke('heading', h & 255))
        s.step(L.poke('heading', h >> 8, 1))


def animal(s, kind, x, y):
    for name, value in (('animal_kind', kind), ('animal_x', x >> 8), ('animal_y', y >> 8),
                        ('animal_age', 0)):
        s.step(L.poke(name, value))


def grab(s):
    page = s.step('peek:2000:8192').data
    mood = mood_name(s.step(L.peek('sky_mood')).data)
    px, py, h = state(s.step(L.peek('px', 6)).data)
    return page, mood, px, py, h


def stars(s):
    s.step('peek:C080')
    lst = s.step(L.peek('st_a', LIST_BYTES)).data
    s.step('peek:C082')
    return resident_stars(lst)


def compare(s, label, m, kind, fire=None, tilt=0, star_list=(), region=2, want_mood=None):
    """The view on screen against dhgr_ref with the animal of kind (None:
    no animal expected) on the player's cell."""
    page, mood, px, py, h = grab(s)
    a = (kind, px, py, 0) if kind else None
    sky = R.Sky(mood_name=mood, stars=star_list, region=region)
    want = R.view(m, px, py, h, sky, a, forest=False, tilt=tilt, fire=fire)
    bad, first = view_diff(dhgr_view(page), want)
    ok = not bad and (want_mood is None or mood == want_mood)
    check(f'{label} ({mood})', ok, (bad, first, mood))
    if bad and DEBUG:
        n = len(fails)
        R.to_png(DEBUG / f'fail{n}_got.png', dhgr_view(page))
        R.to_png(DEBUG / f'fail{n}_want.png', want)
    return page, (px, py, h)


FAST = 0x83                     # scene_drawn: the animal's background kept (OUTDOOR ab_copy)
TURNS = (('\\>', 'arrow right'), ('\\<', 'arrow left'), ('LOOK R', 'LOOK R'),
         ('LOOK L', 'LOOK L'))             # LOOK B and LOOK N redraw, animal or not


def turn(s, k):
    """Type turn k; the first of animal_unpan (the background put back, the
    view scrolls) and show_view (the whole view redrawn) it reaches."""
    if k.startswith('LOOK'):
        s.step(f'key:{k}')
        k = '\\r'
    r = s.step(f'press:{k}')
    r = s.step(f'until:{L["animal_unpan"]:04X},{L["show_view"]:04X}:20000')
    pc = int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16)
    s.step('wait:1')
    s.step(IDLE)
    return 'scroll' if pc == L['animal_unpan'] else 'redraw'


def turns(s, label, m, kind, fire=None, star_list=None, region=2, want='scroll', moves=TURNS):
    """Each turn of moves: the path taken (want: 'scroll' after a view with
    the animal on a legacy map, 'redraw' otherwise) and the pixels of the
    whole redraw (tools/dhgr_ref: the animal centred, or beside the fire)."""
    for k, name in moves:
        armed = b(s, 'scene_drawn')
        path = turn(s, k)
        if m is not None:           # None: a native map (no reference of its view here)
            compare(s, f'{label}, {name}: {path}', m, kind, fire=fire, region=region,
                    star_list=stars(s) if star_list else ())
        check(f'  {label}, {name}: the {want} path', path == want and
              (armed == FAST) == (want == 'scroll'), (path, hex(armed)))


def geometry(kind, px, py, h, fire=None):
    return scene_ref.animal_geometry(px, py, h, (kind, px, py, 0), fire)


def sierra():
    with a2test.Session(DISK) as s:
        boot(s)
        print(' Site and animal on the same cell:')
        animal(s, 6, SX, SY)
        typed(s, 'V')
        compare(s, 'the wreck of the start cell and the bear in front', MAP, 6)
        typed(s, 'LOOK B')
        compare(s, 'LOOK BACK: the wreck behind, the bear still centred', MAP, 6)
        turns(s, 'the wreck and the bear', MAP, 6)
        cx, cy, bh = MAP[17] << 8, MAP[18] << 8, int.from_bytes(MAP[19:21], 'little')
        place(s, cx, cy, bh)
        animal(s, 8, cx, cy)
        typed(s, 'V')
        name = ('log', 'rock')[MAP[16] - 1]
        compare(s, f'the shelter ({name}) and the rattlesnake', MAP, 8)

        print(' Every direction (the bear, a plain cell):')
        x, y = SX + 512, SY
        place(s, x, y, 10)
        animal(s, 6, x, y)
        typed(s, 'V')
        compare(s, 'VIEW', MAP, 6)
        for cmd in ('LOOK R', 'LOOK L', 'LOOK L', 'LOOK R', 'LOOK B'):
            typed(s, cmd)
            compare(s, cmd, MAP, 6)
        for k, label in (('\x15', 'arrow right'), ('\x08', 'arrow left'), ('\x08', 'arrow left')):
            key(s, k)
            compare(s, label, MAP, 6)
        turns(s, 'the bear', MAP, 6)
        s.step('key:TOPO')
        s.step('press:\\r')
        s.step(L.until('graphical_topo_key', 20000))
        s.step('press:\\e')
        s.step(IDLE)
        check('TOPO takes the background (its snapshot zone): scene_drawn 3',
              b(s, 'scene_drawn') == 3)
        turns(s, 'after TOPO', MAP, 6, want='redraw', moves=TURNS[:1])
        turns(s, '  then', MAP, 6, moves=TURNS[1:2])
        typed(s, 'USE COMPASS')
        typed(s, 'LOOK N')
        compare(s, 'LOOK N (compass in use)', MAP, 6)
        typed(s, 'LOOK DOWN')
        check('LOOK DOWN refused while the bear stands (message 64)', b(s, 'tilt') == 0)
        animal(s, 8, x, y)
        typed(s, 'LOOK DOWN')
        compare(s, 'LOOK DOWN: the rattlesnake lies low, drawn at its rows', MAP, 8, tilt=-1)
        typed(s, 'LOOK UP')
        compare(s, 'LOOK UP: no sprite (the original\'s rule)', MAP, None, tilt=1)
        typed(s, 'LOOK AHEAD')
        compare(s, 'LOOK AHEAD: the rattlesnake again', MAP, 8)

        print(' A campfire on the cell:')
        animal(s, 6, x, y)
        h = 10
        for d, where in ((0, 'lit facing the heading: the bear right of it'),
                         (-40, 'left of the view: no overlap, the bear centred'),
                         (20, 'right of the centre: the bear left of it'),
                         (-20, 'a little left: the bear right of it')):
            place(s, x, y, h)
            s.step(L.poke('fire_on', 1))
            for i, v in enumerate((x & 255, x >> 8, y & 255, y >> 8, (h + d) % 560 & 255, (h + d) % 560 >> 8)):
                s.step(L.poke('fire_pos', v, i))
            typed(s, 'V')
            fire = (x >> 8, y >> 8, (h + d) % 560)
            bare, _ = compare(s, f'fire at {d:+}: {where}', MAP, 6, fire=fire)
            if d in (-20, 20):
                turns(s, f'  fire at {d:+}', MAP, 6, fire=fire, moves=TURNS[:3])
                place(s, x, y, h)
                typed(s, 'V')
            g = geometry(6, x, y, h, fire)
            fl = 56 + ((h + d) - h + 280) % 560 - 280
            apart = set(range(g['left'], g['left'] + g['width'])).isdisjoint(range(fl, fl + 28))
            check(f'  fire at {d:+}: animal columns {g["left"]}..{g["left"] + g["width"] - 1}, '
                  f'fire {fl}..{fl + 27}: apart', apart)
            if d in (0, 20):
                ok = shown(s)
                after = dhgr_view(s.step('peek:2000:8192').data)
                before = dhgr_view(bare)
                touched = {c for r in range(160) for c in range(140) if after[r][c] != before[r][c]}
                check(f'  fire at {d:+}: drawn at the prompt, its own columns only',
                      ok and touched and touched <= set(range(fl, fl + 28)), sorted(touched)[:4])
        s.step(L.poke('fire_on', 0))
        place(s, SX, SY, HEAD)
        animal(s, 6, SX, SY)
        typed(s, 'V')
        typed(s, 'USE MATCHES')
        typed(s, 'MAKE FIRE')
        check('MAKE FIRE at the wreck: the fire burns', b(s, 'fire_on') == 1)
        fire = (SX >> 8, SY >> 8, int.from_bytes(s.step(L.peek('fire_pos', 2, 4)).data, 'little'))
        compare(s, 'after MAKE FIRE: the view redrawn, the bear right of the fire', MAP, 6, fire=fire)
        typed(s, 'DOUSE FIRE')
        # DOUSE spends no time and redraws nothing: the fire's columns come
        # back bare, the bear keeps its place until the next view.
        compare(s, 'after DOUSE FIRE: the fire gone, the bear where it was', MAP, 6, fire=fire)
        turns(s, '  then turned: the bear centred', MAP, 6, moves=TURNS[:2])
        typed(s, 'V')
        compare(s, 'the next view: the bear centred again', MAP, 6)

        print(' Without light:')
        place(s, x, y, 10)
        animal(s, 7, x, y)
        s.step(L.poke('night', 1))
        s.step(L.poke('view_dark', 1))
        s.step('key:V')
        s.step('press:\\r')
        s.step('wait:1')
        s.step(IDLE)
        page, mood, *_ = grab(s)
        screen = '\n'.join(text_screen(s.step('peek:0400:1024').data))
        compare(s, 'night without a full Moon: the cougar as a night silhouette', MAP, 7,
                star_list=stars(s), want_mood='night dark')
        check('  and still NOT ENOUGH LIGHT.', 'NOT ENOUGH LIGHT' in screen, screen[-400:])
        key(s, '\x15')
        compare(s, '  a turn in the dark: the silhouette centred', MAP, 7, star_list=stars(s))
        turns(s, '  in the dark', MAP, 7, star_list=True, moves=TURNS[1:3])
        s.step(L.poke('night', 0))
        s.step(L.poke('view_dark', 0))
        for sun8, want in ((0, 'sunset'), (-10, 'civil'), (-20, 'nautical')):
            s.step(L.poke('sun_alt8', sun8 & 255))
            typed(s, 'V')
            compare(s, f'{want}: the silhouette, readable', MAP, 7, star_list=stars(s), want_mood=want)
            if want == 'sunset':
                turns(s, '  at sunset', MAP, 7, star_list=True, moves=TURNS[:1])
        s.step(L.poke('sun_alt8', 60))

        print(' Shelters:')
        place(s, cx, cy, bh)
        animal(s, 7, cx, cy)
        typed(s, 'V')
        typed(s, 'ENTER SHELTER')
        check('ENTER SHELTER: inside, the cougar stays (D4)',
              b(s, 'shelter_inside') == 1 and b(s, 'animal_kind') == 7)
        inside = dhgr_view(s.step('peek:2000:8192').data)
        check('  no view inside: no sprite', all(c == 0 for r in inside[16:160] for c in r))
        typed(s, 'EXIT SHELTER')
        check('EXIT SHELTER: out, the cougar still there',
              b(s, 'shelter_inside') == 0 and b(s, 'animal_kind') == 7)
        compare(s, '  the shelter and the cougar in front', MAP, 7)

        print(' Walking away (generated map):')
        x = SX + 512 + 128                # the centre: the first half-step leaves the cell
        place(s, x, y, 140)
        animal(s, 6, x, y)
        typed(s, 'V')
        s.step('key:WALK')
        s.step('press:\\r')
        s.step('wait:1')
        s.step(L.until('wait_key', 6000))
        s.step('key:1')
        s.step('press:\\r')
        s.step('wait:1')
        s.step(IDLE)
        px, py, _ = state(s.step(L.peek('px', 6)).data)
        kind, ax, ay, age = s.step(L.peek('animal_kind', 4)).data
        # A new encounter may stop the walk: then a new animal, on the new cell.
        check('WALK: the player leaves the cell, the bear stays behind, no record off the cell',
              (px >> 8) != (x >> 8) and (kind == 0 or (ax, ay) == (px >> 8, py >> 8)),
              (hex(px), kind, ax, ay, age))
        typed(s, 'V')
        compare(s, '  the next view: no bear (a new animal of this cell only)', MAP, kind or None)


def shown(s, frames=150):
    after_tick = L['fire_idle'] + 3
    for _ in range(frames):
        s.step('wait:2')
        if b(s, 'fire_st'):
            s.step(f'until:{after_tick:04X}:100')
            return True
    return False


def new_guinea():
    """The crocodile (72 columns): clipped at the right edge of the view
    right of a fire lit facing the heading, left of a fire right of the
    centre."""
    region = 4
    m = expected_map((HERE / 'build/maps/r4.bin').read_bytes(), 4, region)
    scene_ref.use_region(region)
    with a2test.Session(DISK, menu=False) as s:
        boot(s, menu_keys('4'))
        px, py, h = state(s.step(L.peek('px', 6)).data)
        x, y = px + 512, py
        place(s, x, y, h)
        animal(s, 8, x, y)
        typed(s, 'V')
        compare(s, 'New Guinea, the crocodile centred', m, 8, region=region)
        turns(s, '  the crocodile', m, 8, region=region, moves=TURNS[:2])
        for d in (0, 20, 10):
            s.step(L.poke('fire_on', 1))
            for i, v in enumerate((x & 255, x >> 8, y & 255, y >> 8, (h + d) % 560 & 255, (h + d) % 560 >> 8)):
                s.step(L.poke('fire_pos', v, i))
            typed(s, 'V')
            fire = (x >> 8, y >> 8, (h + d) % 560)
            g = geometry(8, x, y, h, fire)
            compare(s, f'  fire at {d:+}: the crocodile at {g["left"]} ({g["width"]} columns)', m, 8,
                    fire=fire, region=region)
            turns(s, f'  fire at {d:+}, the crocodile', m, 8, fire=fire, region=region)
            place(s, x, y, h)
        s.step(L.poke('fire_on', 0))
    scene_ref.use_region(2)


def native():
    """Walking away from an animal on a native map is still its reaction."""
    from test_journey_resident import native as native_map
    m = native_map()
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp, m)) as s:
        boot(s)
        px, py, h = state(s.step(L.peek('px', 6)).data)
        animal(s, 6, px, py)
        typed(s, 'V')
        turns(s, 'native map (the atlas fills the area)', None, 6, want='redraw', moves=TURNS[:2])
        s.step('key:WALK')
        s.step('press:\\r')
        s.step('wait:1')
        s.step(L.until('wait_key', 6000))
        s.step('key:1')
        s.step('press:\\r')
        s.step('wait:1')
        reaction = L['module_native_walk_reaction']
        r = s.step(f'until:{reaction:04X},{L["idle"]:04X}:200000')
        pc = int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16)
        for _ in range(4):
            r = s.step(f'until:{L["idle"]:04X},{L["keyboard_wait"]:04X}:40000')
            if int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16) == L['idle']:
                break
            s.step('key: ')
        check('native map: walking away is the bear\'s reaction (T08/S07), then the record goes',
              pc == reaction and b(s, 'animal_kind') == 0, (hex(pc), b(s, 'animal_kind')))


def screenshots():
    """build/animal_*.png: the game as played (woods, sky, HUD on)."""
    def shot(s, name):
        R.to_png(HERE / 'build' / f'animal_{name}.png', dhgr_page(s.step('peek:2000:8192').data), range(160))
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        animal(s, 6, SX, SY)
        typed(s, 'V')
        shot(s, 'site')                                 # the wreck and the bear
        typed(s, 'LOOK B')
        shot(s, 'look_back')
        typed(s, 'LOOK B')
        typed(s, 'USE MATCHES')
        typed(s, 'MAKE FIRE')
        shown(s)
        shot(s, 'fire')
        typed(s, 'DOUSE FIRE')
        s.step(L.poke('night', 1))
        s.step(L.poke('view_dark', 1))
        typed(s, 'V')
        shot(s, 'night')


def widths():
    """Every animal of the six packs fits the background kept under it
    (OUTDOOR ab_copy, AB_MAXN = 21: 22 bytes per bank and row, 72 columns)."""
    import dhgr_palette as P
    worst = 0
    for region in range(1, 7):
        scene_ref.use_region(region)
        for asset in (6, 7, 8, 23):
            if asset in scene_ref.IMAGES:
                worst = max(worst, len(scene_ref.IMAGES[asset][0]))
    scene_ref.use_region(2)
    check(f'the widest animal of the six packs: {worst} columns (at most 72)', worst <= 72)


def main():
    widths()
    screenshots()
    sierra()
    new_guinea()
    native()
    print('Animal always in view: ' + ('OK' if not fails else 'FAILED: ' + '; '.join(fails)))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
