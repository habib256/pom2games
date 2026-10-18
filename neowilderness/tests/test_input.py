#!/usr/bin/env python3
"""Real keyboard input, atomic refusal and interruption at completed steps."""
import tempfile
from common import HERE, L, a2test, disk_with, fp, text_screen

IDLE = L.until('idle', 20000)
NUMBER = L.until('input_number_idle', 20000)


def command(s, text):
    s.step(f'key:{text}')
    s.step('press:\\r')
    s.step('wait:1')
    s.step(IDLE)


def snapshot(s):
    fields = [('px',6),('s_hour',5),('s_elap',5),('s_body',5),
              ('health',1),('nature_frequency',1)]
    fields += [(name,76) for name in ('it_place','it_pack_lo','it_pack_hi','it_gnd_lo','it_gnd_hi')]
    return tuple(s.step(L.peek(name,size)).data for name,size in fields)


def screen(s):
    return '\n'.join(text_screen(s.step('peek:0400:1024').data))


def flat():
    m=bytearray((HERE/'build/map.bin').read_bytes())
    m[2:8]=bytes((0,10,0,40,140,0))
    m[8:12]=bytes((100,70,0,90))
    m[13:17]=bytes((90,90,20,0))
    m[23]=100
    m[64:]=bytes([10])*9408
    return m


def cancellations(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        before=snapshot(s)
        for text in ('','WALK','DRINK WATER'):
            if text:
                s.step(f'key:{text}')
            s.step('press:\\e')
            s.step('wait:1')
            s.step(IDLE)
            assert s.step(L.peek('linelen')).data == b'\0'
            assert snapshot(s)==before
        for text,answer in [('WALK','\\e'),('REST','\\e'),('DRINK WATER','0\\r'),
                            ('EAT CHEESE','12\\e'),('NATURE','\\e')]:
            s.step(f'key:{text}')
            s.step('press:\\r')
            s.step(L.until('keyboard_wait', 20000) if text in ('WALK', 'REST') else NUMBER)
            s.step(f'key:{answer}')
            s.step(IDLE)
            assert snapshot(s)==before,(text,answer)
            assert 'ACTION CANCELLED.' in screen(s)
        for text in ('WALK 0 MIN','REST 0 H','DRINK WATER 0 OZ',
                     'WALK 256 H','WALK 15301 MIN','REST 65536 MIN',
                     'WALK -1 MIN','WALK 1.5 H','WALK 1 OZ',
                     'REST 1 SEC','DRINK WATER 256 OZ','DRINK WATER 4 H',
                     'STATUS 1','WALK 999999999999999999999 MIN',
                     '  SLEEP 0 MIN','  REST 1 OZ'):
            command(s,text)
            assert snapshot(s)==before,text
            assert ('CANCELLED' in screen(s) or 'INVALID' in screen(s)),text
        for typed,response in zip(('QUIT',' QUIT ','  QUIT'),('N','\\r','\\e')):
            s.step(f'key:{typed}')
            s.step('press:\\r')
            s.step(L.until('wait_key',20000))
            assert 'UNSAVED PROGRESS WILL BE LOST' in screen(s)
            s.step(f'key:{response}')
            s.step(IDLE)
            assert snapshot(s)==before,response
        for text in ('STATUS','INVENTORY','TOPO','MAP','HELP'):
            s.step(f'key:{text}')
            s.step('press:\\r')
            s.step(L.until('wait_key',20000))
            s.step('key:\\e')
            s.step(IDLE)
            assert snapshot(s)==before,(text,'ESC')
        s.step('key:\\e')
        s.step(IDLE)
        assert snapshot(s)==before
        s.step('key:QUIT')
        s.step('press:\\r')
        s.step(L.until('wait_key',20000))
        s.step('press:Y')
        s.step(L.until('quit',6000))
    print('  ESC, empty/zero input, invalid units/ranges and QUIT confirmation: no unintended state changes OK')


def durations(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        # Native flat-ground pace is nine minutes per half-cell. An entire
        # step must fit the requested duration, including its final minute.
        command(s,'WALK 3 MIN')
        assert s.step(L.peek('px',2)).data == bytes((0,10))
        assert fp(s.step(L.peek('s_elap',5)).data)==0
        command(s,'WALK 4 MIN')
        assert s.step(L.peek('px',2)).data == bytes((0,10))
        assert fp(s.step(L.peek('s_elap',5)).data)==0
        assert 'NEXT STEP 9 MIN.' in screen(s)
        command(s,'WALK 9 MIN')
        assert s.step(L.peek('px',2)).data == bytes((128,10))
        assert abs(fp(s.step(L.peek('s_elap',5)).data)*60-9)<1e-6
        command(s,'WALK 19 MIN')
        assert s.step(L.peek('px',2)).data == bytes((128,11))
        assert abs(fp(s.step(L.peek('s_elap',5)).data)*60-27)<1e-6
        assert 'TRAVEL: 18 MINUTES.' in screen(s)
        command(s,'REST 10 MIN')
        assert 'YOU RESTED 10 MINUTES.' in screen(s)
        assert abs(fp(s.step(L.peek('s_elap',5)).data)*60-37)<1e-6
        command(s,'REST 1 H')
        assert 'YOU RESTED 1 HOUR.' in screen(s)
        assert abs(fp(s.step(L.peek('s_elap',5)).data)*60-97)<1e-6
        water=s.step(L.peek('it_pack_lo',1,22)).data[0]
        command(s,'DRINK WATER 4 OZ')
        assert s.step(L.peek('it_pack_lo',1,22)).data[0]==water-4
        assert 'YOU DRANK 4 OUNCES.' in screen(s)
        for text in ('  SLEEP 1 MIN', ' REST 1 MIN   '):
            command(s,text)
            assert 'YOU RESTED 1 MINUTE.' in screen(s),text
        assert abs(fp(s.step(L.peek('s_elap',5)).data)*60-99)<1e-6
        for text in ('CAMP 1 MIN', 'WAIT 1 MIN', 'PAUSE 1 MIN', 'EXERCISE 1 MIN'):
            elapsed = fp(s.step(L.peek('s_elap',5)).data)
            command(s, text)
            assert abs((fp(s.step(L.peek('s_elap',5)).data)-elapsed)*60-1)<1e-6, text
        before=snapshot(s)
        command(s,'  WALK 1 MIN')
        assert snapshot(s)==before, 'leading spaces bypassed short-step refusal'
        command(s,'  DRINK WATER 1 OZ   ')
        assert s.step(L.peek('it_pack_lo',1,22)).data[0]==water-5
        assert 'YOU DRANK 1 OUNCE.' in screen(s)
    print('  Inline H/MIN/OZ, refused short step, complete native steps, exact budgets and minute rest: OK')
    print('  Leading/trailing spaces: sleep, rest, qualified drinking and atomic short-step refusal OK')


def nature_inline(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        before=snapshot(s)
        view=s.step('peek:2000:8192').data
        rng=s.step(L.peek('fauna_rng')).data
        for text,value in (('NATURE 0',0),('NATURE 1',1),('NATURE 100',100),
                           ('  NATURE 5   ',5)):
            command(s,text)
            assert s.step(L.peek('nature_frequency')).data==bytes((value,)),text
            assert 'OK, WHAT NEXT?' in screen(s),text
            after=snapshot(s)
            assert after[:5]==before[:5] and after[6:]==before[6:],text
            assert s.step('peek:2000:8192').data==view,text
            assert s.step(L.peek('fauna_rng')).data==rng,text
        before=snapshot(s)
        for text in ('NATURE 101','NATURE 255','NATURE 256','NATURE -1',
                     'NATURE 1.5','NATURE 0 H','NATURE 1 MIN','NATURE 5 OZ'):
            command(s,text)
            assert snapshot(s)==before,text
            assert 'FREQUENCY MUST' in screen(s) or 'INVALID' in screen(s),text
            assert s.step('peek:2000:8192').data==view,text
            assert s.step(L.peek('fauna_rng')).data==rng,text
        # The original prompted command must still accept zero after refusals.
        s.step('key:NATURE')
        s.step('press:\\r')
        s.step(NUMBER)
        s.step('key:0\\r')
        s.step(IDLE)
        assert s.step(L.peek('nature_frequency')).data==b'\0'
    print('  Inline NATURE 0..100 and spaces; invalid values/units refused atomically; prompted zero preserved OK')


def editing(disk):
    for typed,expected in [('1\\<9',9),('12\\<\\<9',9),('123\\<\\<\\<9',9),('65536\\<',6553)]:
        with a2test.Session(disk) as s:
            s.step(IDLE)
            s.step('key:REST')
            s.step('press:\\r')
            s.step(L.until('keyboard_wait', 20000))
            s.step(f'key:{typed}')
            assert s.step(L.peek('linelen')).data[0]==len(str(expected))
            assert f'> {expected}' in screen(s)
            s.step('key: MIN')
            if expected > 100:
                s.step('key:\\e')
            else:
                s.step('press:\\r')
            s.step(IDLE)
            elapsed=fp(s.step(L.peek('s_elap',5)).data)*60
            assert abs(elapsed-(expected if expected<100 else 0))<1e-6
    print('  One, two and three backspaces remove only the last digit; unit entry and ESC remain usable OK')


def interrupted(m, swimming=False, button=False):
    if swimming:
        m=bytearray(m)
        for x in range(10,30):
            m[64+40*112+x] |= 128
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,m)
        with a2test.Session(disk) as s:
            s.step(IDLE)
            s.step('key:SWIM' if swimming else 'key:WALK')
            s.step('press:\\r')
            s.step(L.until('keyboard_wait', 20000))
            s.step('key:4')
            s.step('press:\\r')
            s.step(L.until('walk_progress',20000))
            completed=snapshot(s)
            used=int.from_bytes(s.step(L.peek('used',2)).data,'little')
            s.step('btn:1,1' if button else 'press:\\e')
            s.step(IDLE)
            assert snapshot(s)==completed,('swim' if swimming else 'walk')
            assert f'TRAVEL: {used} MINUTES.' in screen(s) and 'STOPPED BY ESC.' in screen(s)
            assert abs(fp(s.step(L.peek('s_elap',5)).data)*60-used)<1e-5
    print(f'  {"SWIM" if swimming else "WALK"}: {"button 1" if button else "ESC"} after first completed step preserves position, health, supplies and actual time OK')


def main():
    m=flat()
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,m)
        cancellations(disk)
        durations(disk)
        nature_inline(disk)
        editing(disk)
    interrupted(m)
    interrupted(m,True)
    print('Neowilderness input lot 1: OK')


if __name__=='__main__':
    main()
