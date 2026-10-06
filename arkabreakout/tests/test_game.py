#!/usr/bin/env python3
"""Exercise the actual NMOS 6502 game on a 48K Apple II+, including forced edge cases."""
from pathlib import Path
import argparse
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'arkabreakout'
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test
DISK = ROOT / 'dist/ARKABREAKOUT.dsk'
labels = a2test.Labels()


def poke(name, value, offset=0):
    return labels.poke(name, value, offset)


def peek(name, length=1):
    return labels.peek(name, length)


def run(*steps, menu=False):
    boot = ['wait:1100'] + ([] if menu else ['key: ', 'wait:60'])
    result = a2test.run(DISK, boot + list(steps))
    memory = {}
    for address, values in result.rows:
        for i, value in enumerate(values):
            memory[address + i] = value
    return result.out, memory


def value(memory, name, offset=0):
    return memory[labels[name]+offset]


def fields(*names):
    return [peek(name, 5 if name in ('score','best_score') else 2 if name == 'frames' else 1)
            for name in names]


def setup_ball(x, y, dx=0, dy=1, horizontal=128):
    # Pause first so pokes cannot interleave with a simulation update.
    return ['key:P', 'wait:15', poke('ball_x',x), poke('ball_y',y),
            poke('ball_live',1), poke('ball_dirx',dx), poke('ball_diry',dy),
            poke('ball_speed',horizontal), poke('ball_yspeed',255),
            poke('ball_yfrac',255), poke('ball_frac',255), poke('speed',2), 'press:P']


def main():
    global labels, DISK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disk',type=Path,default=DISK)
    parser.add_argument('--labels',type=Path,default=GAME/'build/game.lbl')
    args = parser.parse_args()
    DISK = args.disk.resolve()
    labels = a2test.labels(args.labels)
    _, m = run(*fields('state','level','lives','remaining','ball_live','score'))
    assert [value(m,n) for n in ('state','level','lives','remaining','ball_live')] == [1,0,3,48,0]
    assert bytes(m[labels['score']+i] for i in range(5)) == b'00000'

    # Keyboard steering continues without repeats; S stops it, launch advances.
    _, m = run('key:A','wait:15','key:S','wait:15',*fields('pad_x','movement'))
    assert value(m,'pad_x') < 112 and value(m,'movement') == 0
    _, m = run('key: ','wait:12',*fields('ball_live','ball_y'))
    assert value(m,'ball_live') == 1 and value(m,'ball_y') < 170

    # Paused pages converge and then stay byte-for-byte identical, including HUD.
    out, m = run('key: ','wait:10','key:P','wait:15','peek:2000:16384',
                 'wait:45','peek:2000:16384',*fields('paused'))
    chunks = re.split(r'(?m)^2000:', out)[1:]
    def page_bytes(chunk):
        return a2test.page_dump('2000:' + chunk)
    assert len(chunks) == 2 and page_bytes(chunks[0]) == page_bytes(chunks[1])
    frozen = page_bytes(chunks[0])
    visible = [a2test.hgr_offset(y) + x for y in range(192) for x in range(40)]
    assert all(frozen[i] == frozen[i+8192] for i in visible), "paused pages disagree"
    assert value(m,'paused') == 1

    # XOR capsule glyphs must restore coloured bricks at every pixel alignment.
    _, baseline_memory = run('key:P','wait:15','peek:2000:16384')
    for kind in (1,2,3):
        for alignment in range(7):
            _, restored = run('key:P','wait:15',poke('capsule',kind),
                              poke('cap_x',98+alignment),poke('cap_y',48),
                              'key:P','wait:3','key:P','wait:15',
                              poke('capsule',0),'key:P','wait:3','key:P','wait:15',
                              'peek:2000:16384')
            assert all(restored[0x2000+i] == baseline_memory[0x2000+i]
                       for i in visible), (kind,alignment,'capsule damaged background')

    # Axis and corner cases, no tunnelling at the maximum supported speed.
    _, m = run(*setup_ball(2,145,1,1,240),'wait:4',*fields('ball_dirx','ball_x'))
    assert value(m,'ball_dirx') == 0 and value(m,'ball_x') >= 2
    _, m = run(*setup_ball(100,18,0,1,64),'wait:4',*fields('ball_diry'))
    assert value(m,'ball_diry') == 0
    _, m = run(*setup_ball(10,68,0,1,64),poke('speed',5),'wait:4',
               peek('bricks',96),*fields('score','remaining'))
    assert value(m,'bricks',36) == 0 and value(m,'remaining') == 47
    assert bytes(m[labels['score']+i] for i in range(5)) == b'00010'

    # Diagonal corner contacts, including simultaneous ceiling/side-wall impact.
    _, m = run(*setup_ball(2,18,1,1,255),'wait:4',
               *fields('ball_dirx','ball_diry','ball_x','ball_y'))
    assert value(m,'ball_dirx') == value(m,'ball_diry') == 0
    assert value(m,'ball_x') >= 2 and value(m,'ball_y') >= 18
    for dx, index in ((1,36),(0,37)):
        _, m = run(*setup_ball(19,68,dx,1,255),'wait:4',
                   peek('bricks',96),*fields('score','remaining'))
        assert value(m,'bricks',index) == 0 and value(m,'remaining') == 47
        assert bytes(m[labels['score']+i] for i in range(5)) == b'00010'

    # Resistant and steel bricks: one impact removes one HP, steel stays intact.
    for hp in (3,255):
        _, m = run(*setup_ball(10,68,0,1,64),poke('bricks',hp,36),
                   'wait:4',peek('bricks',96),*fields('remaining','score'))
        assert value(m,'bricks',36) == (2 if hp == 3 else 255)
        assert value(m,'remaining') == 48
        if hp == 255:
            assert bytes(m[labels['score']+i] for i in range(5)) == b'00000'

    # Raquette: directed angle, catch mode, and a miss costs exactly one life.
    _, m = run(*setup_ball(113,171,0,0,64),'wait:4',*fields('ball_diry','ball_dirx','ball_speed'))
    assert value(m,'ball_diry') == 1 and value(m,'ball_dirx') == 1
    assert value(m,'ball_speed') == 240
    _, m = run(*setup_ball(125,171,0,0,64),poke('effect',3),'wait:4',
               *fields('ball_live','lives'))
    assert value(m,'ball_live') == 0 and value(m,'lives') == 3
    _, m = run(*setup_ball(20,179,0,0,64),'wait:5',*fields('ball_live','lives','state'))
    assert value(m,'lives') == 2 and value(m,'ball_live') == 0 and value(m,'state') == 1
    _, m = run(*setup_ball(20,179,0,0,64),poke('lives',1),'wait:15',*fields('state'),
               'key: ','wait:30',*fields('lives'))
    assert value(m,'state') == 2 and value(m,'lives') == 3

    # Every impact zone has the same intended direction on normal and wide paddles.
    # Edge shots must be flatter, without increasing the velocity magnitude.
    for width, hits in ((28,(1,5,9,12,15,19,23,26)),
                        (42,(2,7,13,18,23,28,34,39))):
        vectors = []
        for zone, hit in enumerate(hits):
            _, m = run(*setup_ball(112+hit-1,171,0,0,0),poke('pad_width',width),
                       'wait:4',*fields('ball_dirx','ball_diry','ball_speed','ball_yspeed'))
            assert value(m,'ball_diry') == 1
            assert value(m,'ball_dirx') == (1 if zone < 4 else 0)
            vx, vy = value(m,'ball_speed'), value(m,'ball_yspeed')
            assert 240**2 <= vx*vx + vy*vy <= 264**2, (zone,vx,vy)
            vectors.append((vx,vy))
        assert vectors == vectors[::-1], 'rebounds are not symmetric'
        assert vectors[0][0] > vectors[0][1] and vectors[3][0] < vectors[3][1]

    # The ramp no longer accelerates the ball at each capsule (5 broken bricks).
    for previous, target_speed, target_hits in ((4,2,5),(10,2,11),(11,3,0)):
        _, m = run(*setup_ball(10,68,0,1,0),poke('ramp_hits',previous),
                   'wait:4',*fields('speed','ramp_hits'))
        assert value(m,'speed') == target_speed and value(m,'ramp_hits') == target_hits
    _, m = run(*setup_ball(10,68,0,1,0),poke('hit_count',4),'wait:4',
               *fields('capsule','speed'))
    assert value(m,'capsule') == 1 and value(m,'speed') == 2

    # Award one life at 1000 points, respect the five-life cap, reset the counter.
    for starting_lives, expected in ((3,4),(5,5)):
        _, m = run(*setup_ball(10,68,0,1,0),poke('reward_hits',99),
                   poke('lives',starting_lives),poke('score',ord('9'),2),
                   poke('score',ord('9'),3),'wait:4',
                   *fields('score','lives','reward_hits'))
        assert bytes(m[labels['score']+i] for i in range(5)) == b'01000'
        assert value(m,'lives') == expected and value(m,'reward_hits') == 0

    # The session record survives replay, and a smaller score cannot overwrite it.
    record_steps = setup_ball(20,179,0,0,0) + [poke('lives',1)]
    record_steps += [poke('score',ord(c),i) for i,c in enumerate('01230')]
    record_steps += ['wait:15','key: ','wait:30']
    record_steps += setup_ball(20,179,0,0,0) + [poke('lives',1),'wait:15']
    _, m = run(*record_steps,*fields('best_score'))
    assert bytes(m[labels['best_score']+i] for i in range(5)) == b'01230'

    # Collect each capsule at the paddle; effects replace one another.
    for kind in (1,2,3):
        _, m = run('key:P','wait:15',poke('capsule',kind),poke('cap_x',120),
                   poke('cap_y',169),poke('speed',5),'key:P','wait:5',
                   *fields('effect','capsule','pad_width','speed'))
        assert value(m,'effect') == kind and value(m,'capsule') == 0
        assert value(m,'pad_width') == (42 if kind == 1 else 28)
        if kind == 2:
            assert value(m,'speed') == 2

    # Width changes retain the paddle centre and do not displace an attached ball.
    for original, kind, target_width, target_x, target_ball in (
            (28,1,42,105,125),(42,2,28,119,132),(42,3,28,119,132)):
        _, m = run('key:P','wait:15',poke('pad_width',original),poke('capsule',kind),
                   poke('cap_x',120),poke('cap_y',169),'key:P','wait:8',
                   *fields('pad_x','pad_width','ball_x'))
        assert value(m,'pad_width') == target_width and value(m,'pad_x') == target_x
        assert value(m,'ball_x') == target_ball

    # All twelve boards load with nonzero targets and use only legal cell types.
    for number in range(1,12):
        _, m = run(*setup_ball(100,140),poke('level',number-1),poke('remaining',0),
                   'wait:25',peek('bricks',96),*fields('level','remaining','ball_live'))
        assert value(m,'level') == number and value(m,'remaining') > 0
        assert value(m,'ball_live') == 0
        cells = [value(m,'bricks',i) for i in range(96)]
        assert set(cells) <= {0,1,2,3,255}
        assert sum(0 < c < 255 for c in cells) == value(m,'remaining')
    _, m = run(*setup_ball(100,140),poke('level',11),poke('remaining',0),
               'wait:25',*fields('state'))
    assert value(m,'state') == 3

    # Real paddle timer input, launch button and optional endpoint calibration.
    _, m = run('key:J','wait:25','joy:-1,0','wait:20',*fields('pad_x','mode'),menu=True)
    assert value(m,'mode') == 1 and value(m,'pad_x') == 2
    _, m = run('key:J','wait:25','joy:1,0','wait:20',
               'btn:0,1','wait:5',*fields('pad_x','ball_live'),menu=True)
    assert value(m,'pad_x') == 223 and value(m,'ball_live') == 1
    _, m = run('key:C','wait:20','joy:-0.7,0','key: ','wait:20',
               'joy:0.7,0','key: ','wait:20','key:J','wait:30',
               'joy:-0.7,0','wait:20',*fields('pad_x'),menu=True)
    assert value(m,'pad_x') == 2

    # Estimate normal cadence from the simulated frame counter, ~1MHz CPU.
    _, start = run(*fields('frames'))
    _, end = run('wait:120',*fields('frames'))
    count = lambda m: value(m,'frames') + 256*value(m,'frames',1)
    hz = (count(end)-count(start))/2
    assert 20 <= hz <= 65, f'unexpected idle cadence: {hz} Hz'
    rates = {}
    for control in ('keyboard','paddle'):
        begin = ['key: ' if control == 'keyboard' else 'key:J','wait:60']
        launch = 'key: ' if control == 'keyboard' else 'btn:0,1'
        _, start_m = run(*begin,launch,'wait:10',*fields('frames'),menu=True)
        _, end_m = run(*begin,launch,'wait:10','wait:120',*fields('frames'),menu=True)
        rates[control] = (count(end_m)-count(start_m))/2
        assert 26 <= rates[control] <= 36, rates
    assert abs(rates['keyboard']-rates['paddle']) <= 2, rates
    print(f'Active cadence: keyboard {rates["keyboard"]:g} Hz, paddle {rates["paddle"]:g} Hz.')
    out, _ = run('key:\\e','wait:20','peek:03F2:3','text')
    assert '03F2: BF 9D' in out and re.search(r'\|.*\].*\|',out)
    out, _ = run('reset','wait:20','peek:03F2:3','text')
    assert '03F2: BF 9D' in out and re.search(r'\|.*\].*\|',out)
    print(f'ARKABREAKOUT: boot, controls, pause, collisions, bonuses, 12 boards, '
          f'victory/defeat, paddle calibration, ESC/RESET passed. Idle cadence: {hz:g} Hz.')

if __name__ == '__main__':
    main()
