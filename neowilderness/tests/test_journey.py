#!/usr/bin/env python3
"""Port mechanics on artificial maps; these do not certify a native journey."""
import tempfile
from common import HERE,L,a2test,disk_with,fp,text_screen
from test_input import IDLE,command,flat,snapshot


def screen(s):return '\n'.join(text_screen(s.step('peek:0400:1024').data))
def status(s):
    s.step('key:STATUS');s.step('press:\\r');s.step(L.until('status_key',20000))
    result=screen(s)
    s.step('key:\\e');s.step(IDLE)
    return result

def progress():
    m=flat();m[8:10]=bytes((20,40))
    with tempfile.TemporaryDirectory() as tmp,a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        before=snapshot(s)
        assert 'DONE=0%' in status(s)
        assert snapshot(s)==before
        command(s,'WALK 38 MIN')
        assert 'DONE=20%' in status(s)
        assert s.step(L.peek('journey_left',2)).data==bytes((8,0))
        command(s,'LOOK B');command(s,'WALK 57 MIN')
        assert 'DONE=0%' in status(s),'distance away must not become unsigned progress'
    print('  Route starts at 0, advances with distance, clamps detours, and STATUS changes no survival state')

def refill():
    m=flat();m[64+40*112+11]=138
    with tempfile.TemporaryDirectory() as tmp,a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        command(s,'DRINK WATER 16 OZ')
        before_ground=s.step(L.peek('it_gnd_lo',1,22)).data
        time=fp(s.step(L.peek('s_elap',5)).data)
        command(s,'FILL CANTEEN')
        assert s.step(L.peek('it_pack_lo',1,22)).data==b'@'
        assert s.step(L.peek('it_gnd_lo',1,22)).data==before_ground
        assert abs(fp(s.step(L.peek('s_elap',5)).data)-time-1/6)<1e-6
        assert 'CANTEEN FILLED TO 64 OZ' in screen(s)
        assert s.step(L.peek('water_untreated')).data==b'\1'
        assert s.step(L.peek('injury_active',1,11)).data==b'\0'
        s.step(L.poke('water_rng',4))
        rng=s.step(L.peek('fauna_rng')).data
        command(s,'DRINK WATER 4 OZ')
        assert s.step(L.peek('injury_active',1,11)).data==b'\1'
        assert s.step(L.peek('fauna_rng')).data==rng
        assert s.step(L.peek('water_rng')).data==b'\2'
        command(s,'DRINK WATER 4 OZ')
        assert s.step(L.peek('water_rng')).data==b'\1'
        command(s,'DRINK WATER 4 OZ')
        assert s.step(L.peek('water_rng')).data==b'\xB8'
        command(s,'REFILL CANTEEN')
        before=snapshot(s);command(s,'REFILL CANTEEN')
        assert snapshot(s)==before and 'IS FULL' in screen(s)
        command(s,'DRINK WATER 8 OZ')
        # A transaction refused by weight must preserve both stocks and time.
        used=s.step(L.peek('load_used',2)).data
        limits=s.step(L.peek('load_limits',2)).data
        for k,b in enumerate(used):s.step(L.poke('load_limits',b,k))
        before=snapshot(s);command(s,'REFILL CANTEEN')
        assert snapshot(s)==before and 'REFILL REFUSED' in screen(s)
        for k,b in enumerate(limits):s.step(L.poke('load_limits',b,k))
        command(s,'LOOK B');command(s,'WALK 57 MIN')
        before=snapshot(s);command(s,'FILL CANTEEN')
        assert snapshot(s)==before and 'NEARBY BANK' in screen(s)
    with tempfile.TemporaryDirectory() as tmp,a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE);command(s,'DRINK WATER 16 OZ')
        for name,value in (('it_gnd_lo',207),('it_gnd_hi',255),('it_oz_lo',255),('it_oz_hi',255)):
            s.step(L.poke(name,value,22))
        stocks=[s.step(L.peek(name,1,22)).data for name in ('it_pack_lo','it_gnd_lo','it_gnd_hi','it_oz_lo','it_oz_hi')]
        time=s.step(L.peek('s_elap',5)).data
        command(s,'FILL CANTEEN')
        assert stocks==[s.step(L.peek(name,1,22)).data for name in ('it_pack_lo','it_gnd_lo','it_gnd_hi','it_oz_lo','it_oz_hi')]
        assert s.step(L.peek('s_elap',5)).data==time and 'REFILL REFUSED' in screen(s)
    print('  FILL/REFILL: adjacent water, 64 oz capacity, ten minutes, remote piles, full and overweight refusals are atomic')

def water_quality():
    m=flat();m[64+40*112+11]=138
    with tempfile.TemporaryDirectory() as tmp,a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        command(s,'DRINK WATER 16 OZ');command(s,'FILL CANTEEN')
        command(s,'DROP WATER')
        assert s.step(L.peek('water_untreated')).data==b'\0'
        assert s.step(L.peek('water_ground_untreated')).data==b'\1'
        command(s,'DRINK WATER 64 OZ')
        command(s,'GET WATER')
        assert s.step(L.peek('water_untreated')).data==b'\1'
        assert s.step(L.peek('water_ground_untreated')).data==b'\0'
        assert s.step(L.peek('it_pack_lo',1,22)).data==b'@'
        command(s,'DRINK WATER 64 OZ')
        assert s.step(L.peek('water_untreated')).data==b'\0'
        assert s.step(L.peek('water_ground_untreated')).data==b'\0'
    with tempfile.TemporaryDirectory() as tmp,a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE)
        s.step(L.poke('water_ground_untreated',1))
        s.step(L.poke('water_rng',4))
        command(s,'DRINK WATER 4 OZ')
        assert s.step(L.peek('injury_active',1,11)).data==b'\0'
        assert s.step(L.peek('water_rng')).data==b'\4','clean carried water must not draw contamination from an untouched ground pile'
        command(s,'DRINK WATER 64 OZ')
        assert s.step(L.peek('injury_active',1,11)).data==b'\1'
    print('  Collected water keeps its quality through drop, ground drinking, recovery and depletion')


def animal(s,kind):
    for axis in ('x','y'):
        s.step(L.poke('animal_'+axis,s.step(L.peek('p'+axis,1,1)).data[0]))
    s.step(L.poke('animal_kind',kind));s.step(L.poke('animal_age',0))

def wildlife():
    # The former guaranteed-reaction fixtures are superseded by the dedicated
    # native-inspired decision suite (including adverse and mixed outcomes).
    from test_animal_reactions import decisions, severities, provisions, hanging, postures, unattended
    decisions();severities();provisions();hanging();postures();unattended()


def victory():
    m=flat();m[8:10]=bytes((14,40))
    with tempfile.TemporaryDirectory() as tmp,a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        command(s,'DRINK WATER 4 OZ');command(s,'EAT CHEESE 4 OZ');command(s,'REST 1 H')
        s.step('key:WALK 4 H');s.step('press:\\r');s.step(L.until('the_end',20000));s.step(L.until('ending_key',20000))
        actual=screen(s)
        assert s.step(L.peek('won')).data==b'\1'
        assert s.step(L.peek('dead')).data==b'\0'
        assert s.step(L.peek('journey_steps',2)).data==bytes((6,0))
        assert 68 < fp(s.step(L.peek('s_elap',5)).data)*60 <= 308
        for text in ('RANGER OUTPOST REACHED','YOU SURVIVED WILDERNESS','JOURNEY TIME:','TRAVEL STEPS: 6','TRAVEL DISTANCE: 3 CELLS','FINAL HEALTH:','WATER LEFT: 60 OZ','FOOD LEFT:','NATIVE JOURNEY SCORE:'):
            assert text in actual,(text,actual)
        s.step('wait:120');assert screen(s)==actual
    print('  Artificial-map arrival: ending mechanism only, no native adventure parity claim')


def fractional_journey():
    m=flat();m[2]=128;m[8:10]=bytes((20,40))
    with tempfile.TemporaryDirectory() as tmp,a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        assert abs(fp(s.step(L.peek('s_d0',5)).data)-19)<1e-6
        command(s,'WALK 19 MIN')
        assert 'DONE=10%' in status(s)
        assert s.step(L.peek('journey_left',2)).data==bytes((9,0))
    m[8:10]=bytes((12,40));m[64:]=bytes([138])*9408
    with tempfile.TemporaryDirectory() as tmp,a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        s.step('key:SWIM 28 MIN');s.step('press:\\r')
        s.step(L.until('the_end',20000));s.step(L.until('ending_key',20000))
        assert s.step(L.peek('journey_steps',2)).data==bytes((1,0))
        assert s.step(L.peek('journey_halfcells',2)).data==bytes((1,0))
        assert 'TRAVEL DISTANCE: 0.5 CELLS' in screen(s)
    print('  Fractional crash distance and route arithmetic; swim ending reports half a cell without truncation')

if __name__=='__main__':
    progress();refill();water_quality();wildlife();victory();fractional_journey();print('Journey improvements: OK')
