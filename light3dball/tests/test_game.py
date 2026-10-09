#!/usr/bin/env python3
"""Exercise the real 6502 game: swept collisions, page restore and a full course."""
from pathlib import Path
import sys
import re
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools'))
import a2test

ROOT = Path(__file__).resolve().parents[2]
L = a2test.labels(ROOT / 'light3dball/build/game.lbl', strip=True)
DISK = ROOT / 'dist/LIGHT3DBALL.dsk'
STACK_PEAKS=[]


def checked_run(disk, steps):
    """Observe startup, gameplay, menus and exit against the linker reserve."""
    steps=list(steps)
    exit_key='key:\\e'
    if exit_key in steps:
        # DOS exit restores the BASIC caller's stack outside this reservation.
        steps.insert(steps.index(exit_key),'stack')
    else: steps.append('stack')
    result=a2test.run(disk,[L.until('main'),
        f'stackwatch:{L["sp"]:02X}:{L["__STACKSTART__"]:04X}:{L["__STACKSIZE__"]:04X}',
        *steps])
    peak,reserved,overflow=map(int,re.search(r'stack peak=(\d+) reserved=(\d+) overflow=(\d+)',result.out).groups())
    assert peak<reserved and not overflow,('C stack',peak,reserved,overflow)
    STACK_PEAKS.append(peak)
    result.cycles=result.cycles[1:] # exclude the added main-entry checkpoint
    return result


def setv(name, value, word=False):
    steps = [L.poke(name, value)]
    if word:
        steps.append(L.poke(name, value >> 8, 1))
    return steps


def scenario(values, names):
    steps = ['wait:1100', L.until('physics')]
    for name, value, word in values:
        steps += setv(name, value, word)
    steps += [L.until('frame_mark')]
    for name, word in names:
        steps.append(L.peek(name, 2 if word else 1))
    result = checked_run(DISK, steps)
    return [int.from_bytes(result.mem(L[name], 2 if word else 1), 'little', signed=word)
            for name, word in names]


base = [('launched', 1, False), ('advancing', 0, False),
        ('camera_z', 0, True), ('ball_x', 64 * 16, True),
        ('ball_y', 64 * 16, True), ('vel_x', 0, True), ('vel_y', 0, True)]

# A swept axial step hits a panel, while the opening passes the same ball.
z, vz, hits = scenario(base + [('ball_z', 125, True), ('vel_z', 1, False),
                             ('ball_x', 100 * 16, True), ('wall_hits', 0, False)],
                       [('ball_z', True), ('vel_z', False), ('wall_hits', False)])
assert z < 126 and vz == 255 and hits == 1, ('panel collision', z, vz, hits)
z, vz = scenario(base + [('ball_z', 125, True), ('vel_z', 1, False), ('ball_x', 32*16, True)],
                  [('ball_z', True), ('vel_z', False)])
assert z == 129 and vz == 1, ('opening', z, vz)

# A close ball reflects off a side wall without escaping the world bounds.
x, vx, hits = scenario(base + [('ball_z', 40, True), ('vel_z', 1, False),
                              ('ball_x', 33, True), ('vel_x', -4, True),
                              ('wall_hits', 0, False)],
                        [('ball_x', True), ('vel_x', True), ('wall_hits', False)])
assert 32 <= x <= 2000 and vx == 4 and hits == 1, ('side wall', x, vx, hits)

# Rebound angle follows the impact offset, and a miss consumes exactly one life.
vz, vx, hits, lives = scenario(base + [('ball_z', 5, True), ('vel_z', -1, False),
                                     ('ball_x', 68 * 16, True), ('hits', 0, False)],
                              [('vel_z', False), ('vel_x', True), ('hits', False), ('lives', False)])
assert (vz, vx, hits, lives) == (1, 2, 1, 4), ('paddle rebound', vz, vx, hits, lives)
lives, launched, advance = scenario(base + [('ball_z', 5, True), ('vel_z', -1, False),
                                          ('ball_x', 12 * 16, True), ('advancing', 1, False)],
                                   [('lives', False), ('launched', False), ('advancing', False)])
assert (lives, launched, advance) == (3, 0, 0), ('miss', lives, launched, advance)

# Left and right edge aiming must be symmetric, without unsigned wraparound.
left_vx, = scenario(base + [('ball_z', 7, True), ('vel_z', -1, False),
                            ('ball_x', 56*16, True)], [('vel_x', True)])
right_vx, = scenario(base + [('ball_z', 7, True), ('vel_z', -1, False),
                             ('ball_x', 72*16, True)], [('vel_x', True)])
assert (left_vx, right_vx) == (-4, 4), ('asymmetric aiming', left_vx, right_vx)

# A central paddle hit must preserve the incoming lateral component.
vx, vy = scenario(base + [('ball_z', 7, True), ('vel_z', -1, False),
                          ('vel_x', 4, True), ('vel_y', -4, True)],
                  [('vel_x', True), ('vel_y', True)])
assert (vx, vy) == (4, -4), ('central hit destroyed trajectory', vx, vy)

# A grazing return at an edge gets the perspective tolerance. The center
# keeps its old extent, and one Q4 unit outside the new edge still loses a life.
for px, py, dx, dy, expected_hit in [
        (16, 64, 192, 0, True), (112, 64, -192, 0, True),
        (64, 24, 0, 200, True), (64, 104, 0, -200, True),
        (16, 24, 192, 200, True), (112, 104, -192, -200, True),
        (16, 64, 193, 0, False), (112, 64, -193, 0, False),
        (64, 64, 145, 0, False), (64, 64, 0, 161, False)]:
    hits, lives, launched = scenario(base + [('paddle_x', px, False), ('paddle_y', py, False),
                            ('ball_x', px*16+dx, True), ('ball_y', py*16+dy, True),
                            ('ball_z', 7, True), ('vel_z', -1, False), ('hits', 0, False)],
                           [('hits', False), ('lives', False), ('launched', False)])
    assert (hits, lives, launched) == ((1, 4, 1) if expected_hit else (0, 3, 0)), \
        ('edge tolerance or free rebound', px, py, dx, dy, hits, lives, launched)

# The back face reflects an approaching ball, not a ball moving away from it.
z, vz, hits = scenario(base + [('ball_z', 387, True), ('vel_z', -1, False),
                              ('ball_x', 100 * 16, True), ('wall_hits', 0, False)],
                       [('ball_z', True), ('vel_z', False), ('wall_hits', False)])
assert z > 386 and vz == 1 and hits == 1, ('back face', z, vz, hits)
z, vz, hits = scenario(base + [('ball_z', 126, True), ('vel_z', -1, False),
                              ('ball_x', 100 * 16, True), ('wall_hits', 0, False)],
                       [('ball_z', True), ('vel_z', False), ('wall_hits', False)])
assert z == 122 and vz == 255 and hits == 0, ('repeated contact', z, vz, hits)

# The camera cannot push the paddle through a solid barrier.
camera, blocked = scenario(base + [('camera_z', 118, True), ('ball_z', 160, True),
                                  ('vel_z', 1, False), ('advancing', 1, False),
                                  ('paddle_x', 100, False)],
                           [('camera_z', True), ('blocked', False)])
assert camera == 118 and blocked == 1, ('camera barrier', camera, blocked)
camera, blocked = scenario(base + [('camera_z', 118, True), ('ball_z', 160, True),
                                  ('vel_z', 1, False), ('advancing', 1, False),
                                  ('paddle_x', 40, False)],
                           [('camera_z', True), ('blocked', False)])
assert camera == 120 and blocked == 0, ('camera opening', camera, blocked)
camera, blocked = scenario(base + [('camera_z', 246, True), ('ball_z', 300, True),
                                  ('vel_z', 1, False), ('advancing', 1, False),
                                  ('paddle_x', 30, False)],
                           [('camera_z', True), ('blocked', False)])
assert camera == 246 and blocked == 2, ('right alignment hint', camera, blocked)

# Only the target cell wins; merely reaching the back of the corridor does not.
z, vz, victory = scenario(base + [('ball_z', 1533, True), ('camera_z', 1280, True), ('vel_z', 1, False),
                                ('ball_x', 90*16, True)],
                          [('ball_z', True), ('vel_z', False), ('won', False)])
assert z < 1534 and vz == 255 and victory == 0, ('back-wall miss', z, vz, victory)
victory, = scenario(base + [('ball_z', 1533, True), ('camera_z', 1280, True), ('vel_z', 1, False)], [('won', False)])
assert victory == 1, 'target hit did not win'
victory, = scenario(base + [('camera_z', 1502, True), ('ball_z', 1524, True),
                            ('vel_z', 1, False), ('ball_x', 90*16, True),
                            ('advancing', 1, False)], [('won', False)])
assert victory == 0, 'camera reaching the end won without a target hit'
victory, = scenario(base + [('ball_z', 1533, True), ('vel_z', 1, False)], [('won', False)])
assert victory == 0, 'distant target won before reaching final chamber'

# Pause stabilizes BOTH pages (including overlaps), even through many renders.
steps = ['wait:1100', 'key:P', 'wait:60', L.until('frame_mark'),
         'peek:2000:16384', 'wait:100', L.until('frame_mark'), 'peek:2000:16384',
         L.peek('paused'), 'key:P', 'wait:80', L.peek('paused'),
         'key:L', 'wait:20', L.peek('paddle_x'), 'key:I', 'wait:20', L.peek('paddle_y'),
         'key:R', 'wait:20', L.peek('lives')]
r = checked_run(DISK, steps)
assert r.mem(0x2000, 16384, 0) == r.mem(0x2000, 16384, 1), 'pause changed page contents'
assert r.mem(L['paused'], 1, 0) == b'\x01' and r.mem(L['paused'], 1, 1) == b'\0'
assert r.mem(L['paddle_x'], 1)[0] > 64 and r.mem(L['paddle_y'], 1)[0] < 64
assert r.mem(L['lives'], 1) == b'\x04'

# Inject firmware polling results to exercise the mouse contract in the actual
# game binary. This checks the game logic; it is not a mouse-hardware test.
steps = ['wait:1100', L.until('frame_mark'), L.poke('mouse_enabled', 1),
         f'poke:{L["mouse_poll"]:04X}:60', L.poke('mouse_x', 70),
         L.poke('mouse_y', 96), L.poke('mouse_buttons', 0),
         L.until('physics'), L.until('frame_mark')]
for x, y, control in [(110, 60, 'click'), (30, 140, 'return')]:
    steps += ['key:R', L.until('physics'), L.until('frame_mark'),
              L.poke('mouse_buttons', 0), L.until('physics'), L.until('frame_mark'),
              L.poke('mouse_x', x), L.poke('mouse_y', y)]
    if control == 'click':
        steps += [L.poke('mouse_buttons', 128)]
    else:
        steps += ['key:\\r']
    steps += [L.until('physics'), L.until('frame_mark'), L.peek('paddle_x'),
              L.peek('paddle_y'), L.peek('ball_x', 2), L.peek('ball_y', 2), L.peek('launched')]
r = checked_run(DISK, steps)
for index in range(2):
    assert r.mem(L['launched'], 1, index) == b'\x01'
    for ball, paddle in [('ball_x', 'paddle_x'), ('ball_y', 'paddle_y')]:
        position = int.from_bytes(r.mem(L[ball], 2, index), 'little')
        assert position == 16*r.mem(L[paddle], 1, index)[0], 'serve used old paddle position'

steps = ['wait:1100', L.until('frame_mark'), L.poke('mouse_enabled', 1),
         f'poke:{L["mouse_poll"]:04X}:60', L.poke('mouse_x', 70),
         L.poke('mouse_y', 96), L.poke('mouse_buttons', 0),
         L.until('physics'), L.until('frame_mark'),
         L.poke('mouse_buttons', 128), L.until('physics'), L.until('frame_mark'),
         L.peek('launched'), L.peek('camera_z', 2),
         L.poke('mouse_buttons', 0), L.until('physics'), L.until('frame_mark'),
         L.peek('advancing')]
steps += setv('ball_z', 60, True) + setv('vel_z', -1)
steps += [L.poke('mouse_buttons', 128), L.until('physics'), L.until('frame_mark'),
          L.peek('launched'), L.peek('vel_z'), L.peek('ball_z', 2),
          L.peek('camera_z', 2), L.peek('lives')]
r = checked_run(DISK, steps)
assert r.mem(L['launched'], 1, 0) == b'\x01'
assert r.mem(L['advancing'], 1) == b'\0', 'button release did not stop advance'
assert r.mem(L['launched'], 1, 1) == b'\x01' and r.mem(L['vel_z'], 1) == b'\xff'
assert int.from_bytes(r.mem(L['ball_z'], 2), 'little') == 56, 'click caught/relaunched an incoming ball'
cam0 = int.from_bytes(r.mem(L['camera_z'], 2, 0), 'little')
cam1 = int.from_bytes(r.mem(L['camera_z'], 2, 1), 'little')
assert cam1-cam0 == 2, ('mouse advance speed', cam0, cam1)
assert r.mem(L['lives'], 1) == b'\x04'

# Repeated paddle contacts keep the ball free, including fresh clicks. Moving
# the mouse and pressing Return after a contact must not move/re-serve it.
steps = ['wait:1100', L.until('frame_mark'), L.poke('mouse_enabled', 1),
         f'poke:{L["mouse_poll"]:04X}:60', L.poke('mouse_x', 70),
         L.poke('mouse_y', 96), L.poke('launched', 1), L.poke('hits', 0), 'spk']
for button in (0, 128, 0, 128):
    steps += [L.poke('mouse_buttons', button), L.until('physics')]
    for name, value, word in [('ball_z', 7, True), ('ball_x', 1024, True),
                              ('ball_y', 1024, True), ('vel_x', 0, True),
                              ('vel_y', 0, True), ('vel_z', -1, False)]:
        steps += setv(name, value, word)
    steps += [L.until('frame_mark'), L.peek('launched'), L.peek('hits'),
              L.peek('vel_z'), L.peek('ball_z', 2), L.peek('lives'), 'spk']
steps += [L.poke('mouse_x', 110), L.poke('mouse_y', 60),
          L.poke('mouse_buttons', 0), 'key:\\r', L.until('physics'),
          L.until('frame_mark'), L.peek('ball_x', 2), L.peek('ball_y', 2),
          L.peek('paddle_x'), L.peek('paddle_y'), L.peek('launched')]
r = checked_run(DISK, steps)
for index in range(4):
    assert r.mem(L['launched'], 1, index) == b'\x01', 'paddle contact caught ball'
    assert r.mem(L['hits'], 1, index) == bytes([index+1]), 'missing/duplicate rebound'
    assert r.mem(L['vel_z'], 1, index) == b'\x01'
    assert int.from_bytes(r.mem(L['ball_z'], 2, index), 'little') > 7
    assert r.mem(L['lives'], 1, index) == b'\x04'
    assert r.spk[index+1] == 12, 'paddle cue missing or repeated'
assert r.mem(L['ball_x'], 2) == r.mem(L['ball_y'], 2) == b'\0\x04'
assert r.mem(L['paddle_x'], 1)[0] != 64 and r.mem(L['paddle_y'], 1)[0] != 64
assert r.mem(L['launched'], 1, 4) == b'\x01', 'Return recaptured ball'

# A held mouse button cannot automatically relaunch after losing a life.
steps = ['wait:1100', L.until('frame_mark'), L.poke('mouse_enabled', 1),
         f'poke:{L["mouse_poll"]:04X}:60', L.poke('mouse_x', 70),
         L.poke('mouse_y', 96), L.poke('mouse_buttons', 128), L.until('physics')]
for name, value, word in [('ball_z', 7, True), ('ball_x', 192, True),
                          ('vel_x', 0, True), ('vel_y', 0, True), ('vel_z', -1, False)]:
    steps += setv(name, value, word)
steps += [L.until('frame_mark'), L.peek('lives'), L.peek('launched'),
          L.until('physics'), L.until('frame_mark'), L.peek('launched'),
          L.poke('mouse_buttons', 0), L.until('physics'), L.until('frame_mark'),
          L.poke('mouse_buttons', 128), L.until('physics'), L.until('frame_mark'),
          L.peek('launched'), L.peek('lives')]
r = checked_run(DISK, steps)
assert r.mem(L['lives'], 1, 0) == r.mem(L['lives'], 1, 1) == b'\x03'
assert r.mem(L['launched'], 1, 0) == r.mem(L['launched'], 1, 1) == b'\0'
assert r.mem(L['launched'], 1, 2) == b'\x01'

# Mouse presses consumed during pause do not become serves upon resuming.
steps = ['wait:1100', L.until('frame_mark'), L.poke('mouse_enabled', 1),
         f'poke:{L["mouse_poll"]:04X}:60', L.poke('mouse_buttons', 0),
         'key:P', L.until('physics'), L.until('frame_mark'),
         L.poke('mouse_buttons', 128), L.until('physics'), L.until('frame_mark'),
         'key:P', L.until('physics'), L.until('frame_mark'), L.peek('paused'), L.peek('launched')]
r = checked_run(DISK, steps)
assert r.mem(L['paused'], 1) == r.mem(L['launched'], 1) == b'\0'

# Sound can be muted; restarting preserves that preference. A serve is one
# short cue, with no repeated sound on the next display page.
steps = ['wait:1100', L.until('frame_mark')]
for _ in range(2):
    steps += ['key:M', L.until('physics'), L.until('frame_mark'),
              'key:R', L.until('physics'), L.until('frame_mark'), 'spk',
              'key:\\r', L.until('physics'), L.until('frame_mark'), 'spk',
              L.until('physics'), L.until('frame_mark'), 'spk']
r = checked_run(DISK, steps)
assert r.spk[1:3] == [0, 0] and r.spk[4:6] == [12, 0], ('mute/serve cues', r.spk)

# A centered shot must NOT complete the course. The first broad wall stops
# both the ball and the advancing player until the paddle moves left.
r = checked_run(DISK, ['wait:1100', 'key:\\r', 'wait:8', 'key: ', 'wait:3000',
                     L.until('frame_mark'), L.peek('won'), L.peek('lives'), L.peek('camera_z', 2),
                     'key:R', 'wait:20', L.peek('won'), L.peek('camera_z', 2),
                     'key:\\e', 'wait:30', 'peek:03F2:3', 'text'])
assert r.mem(L['won'], 1, 0) == b'\0', 'centered shot bypassed the chicanes'
assert r.mem(L['lives'], 1) == b'\x04', 'centered course lost lives'
assert 0 < int.from_bytes(r.mem(L['camera_z'], 2, 0), 'little') <= 118
assert r.mem(L['won'], 1, 1) == b'\0' and r.mem(L['camera_z'], 2, 1) == b'\0\0'
assert r.mem(0x03F2, 3)[:2] == b'\xbf\x9d', 'DOS reset vector not restored'
assert any(']' in screen for screen in r.text_screens()), 'DOS prompt missing'

# Report completed image costs, distinguishing cached frames from redraws.
steps = ['wait:1100', L.until('frame_mark')]
for _ in range(16):
    steps += [L.until('physics'), L.until('frame_mark')]
r = checked_run(DISK, steps)
cycles = r.cycles[::2]
costs = [b-a for a, b in zip(cycles, cycles[1:])]
assert min(costs) < 60000 and max(costs) < 250000, ('frame budget', costs)
print('LIGHT3DBALL: collisions, aiming, barriers, double-page pause, controls, straight-shot blocking and DOS exit passed.')
print(f'Frame costs including delay: {min(costs):,}–{max(costs):,} cycles at 1.02 MHz.')

print(f'Observed C stack peak: {max(STACK_PEAKS)} / {L["__STACKSIZE__"]} bytes.')
