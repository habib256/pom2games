#!/usr/bin/env python3
"""Keyboard decisions, independent combat rolls, theft accounting and cover."""
import tempfile
from common import L, a2test, disk_with, fp
from test_input import IDLE, command, flat, snapshot, screen
from test_forest import map_fixture


def rng(seed):
    for _ in range(7): seed=(seed>>1) ^ (0xB8 if seed&1 else 0)
    return seed


def seed_for(*bounds):
    for seed in range(1,256):
        value=seed
        for lower,upper in bounds:
            value=rng(value)
            if not lower<=value<upper: break
        else: return seed
    raise AssertionError(bounds)


def prepare(s,kind,seed):
    for axis in ('x','y'):
        s.step(L.poke('animal_'+axis,s.step(L.peek('p'+axis,1,1)).data[0]))
    for name,value in [('animal_kind',kind),('animal_age',0),('fauna_rng',seed),('fauna_alert',0),('tree_in',0),('shelter_inside',0)]:
        s.step(L.poke(name,value))
    for condition in (0,1,2,3,7):
        s.step(L.poke('injury_active',0,condition))
        s.step(L.poke('injury_prevented',0,condition))


def injury(s,kind):
    return s.step(L.peek('injury_active',1,7)).data[0] if kind==8 else any(s.step(L.peek('injury_active',4)).data)


def decisions():
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,flat())) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        for kind,noun in ((6,'BEAR'),(7,'COUGAR'),(8,'RATTLER')):
            prepare(s,kind,seed_for((0,129),(0,154)) if kind==8 else seed_for((0,129)))
            time=fp(s.step(L.peek('s_elap',5)).data)
            command(s,'SCARE '+noun)
            assert abs(fp(s.step(L.peek('s_elap',5)).data)-time-5/60)<1e-7
            if kind==8:
                assert s.step(L.peek('animal_kind')).data==b'\10' and injury(s,kind),(screen(s),s.step(L.peek('fauna_rng')).data,s.step(L.peek('outdoor_result')).data,s.step(L.peek('animal_kind')).data,injury(s,kind))
            else:
                assert s.step(L.peek('animal_kind')).data==b'\0' and not injury(s,kind)
        # Noise failure with/without injury. Knife/axe do not make SCARE certain.
        for seed,hurt in ((seed_for((129,256),(0,52)),1), (seed_for((129,256),(52,256)),0)):
            prepare(s,6,seed);command(s,'SCARE BEAR')
            assert s.step(L.peek('animal_kind')).data==b'\6' and injury(s,6)==hurt
            assert ('INJURES YOU' if hurt else 'NOISE FAILS') in screen(s)
        # Native independent rolls: a successful defence may also leave a wound.
        for seed,hurt,leaves in ((seed_for((180,256),(0,4)),0,1),
                                 (seed_for((0,180),(0,4)),1,1),
                                 (seed_for((180,256),(4,256)),0,0),
                                 (seed_for((0,180),(4,256)),1,0)):
            prepare(s,6,seed);command(s,'ATTACK BEAR')
            assert injury(s,6)==hurt
            assert s.step(L.peek('animal_kind')).data==bytes((0 if leaves else 6,))
            assert ('INJURED' if hurt and leaves else ('INJURES' if hurt else ('DEFEND' if leaves else 'ATTACK FAILS'))) in screen(s)
        # Native axe/knife share a method; species thresholds differ.
        s.step(L.poke('it_place',255,58))
        for kind,noun,threshold,success in ((6,'BEAR',180,4),(7,'COUGAR',129,13),(8,'RATTLER',103,39)):
            prepare(s,kind,seed_for((threshold,256),(0,success)))
            command(s,'ATTACK '+noun)
            assert not injury(s,kind) and s.step(L.peek('animal_kind')).data==b'\0'
        s.step(L.poke('it_place',5,59))
        prepare(s,6,4);before=snapshot(s);command(s,'ATTACK BEAR')
        assert snapshot(s)==before and 'AXE OR KNIFE' in screen(s)
        prepare(s,7,4);before=snapshot(s);command(s,'SCARE BEAR')
        assert snapshot(s)==before and 'NO MATCHING ANIMAL' in screen(s)
        prepare(s,6,seed_for((11,256),(13,256),(128,256)))
        command(s,'IGNORE BEAR')
        assert s.step(L.peek('animal_kind')).data==b'\6' and 'STILL WATCHING' in screen(s)
        prepare(s,8,seed_for((16,256),(0,192)))
        command(s,'IGNORE RATTLER')
        assert s.step(L.peek('animal_kind')).data==b'\0' and not injury(s,8)
        prepare(s,7,seed_for((0,11)))
        command(s,'IGNORE COUGAR')
        assert injury(s,7) and 'INJURES YOU' in screen(s)
        prepare(s,6,4);s.step(L.poke('tree_in',1));before=snapshot(s)
        command(s,'ATTACK BEAR')
        assert snapshot(s)==before and not injury(s,6) and 'LEAVE COVER' in screen(s)
        # D4 (lot 3, docs/CRAFT.md 3.4): a shelter is no cover; inside, the
        # injury risk is x .1 (T06/S04 $5866: bear 180 -> 18 of 256).
        s.step(L.poke('it_place',2,59))
        for seed,hurt in ((seed_for((18,180),(4,256)),0),(seed_for((0,18),(4,256)),1)):
            prepare(s,6,seed);s.step(L.poke('shelter_inside',1))
            command(s,'ATTACK BEAR')
            assert injury(s,6)==hurt and 'LEAVE COVER' not in screen(s),(hurt,screen(s))
        print('  Species noise, both independent combat rolls, knife/axe access, failed decisions, tree cover, shelter x .1: OK',flush=True)


def severities():
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,flat())) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        for kind,noun,risk,success,bounds in (
                (6,'BEAR',180,4,(0,52,103,154,256)),
                (7,'COUGAR',129,13,(0,115,162,199,256))):
            for condition,(low,high) in enumerate(zip(bounds,bounds[1:])):
                seed=seed_for((0,risk),(success,256),(low,high))
                prepare(s,kind,seed)
                for index in range(30): s.step(L.poke('medical_actions',0,index))
                # A healed previous injury must not confer treatment on a new one.
                s.step(L.poke('injury_treated',1,condition))
                time=s.step(L.peek('s_elap',5)).data
                command(s,'ATTACK '+noun)
                expected=bytes(int(index==condition) for index in range(4))
                assert s.step(L.peek('injury_active',4)).data==expected,(kind,condition)
                assert s.step(L.peek('injury_treated',1,condition)).data==b'\0'
                assert s.step(L.peek('injury_since',5,condition*5)).data==time
                assert s.step(L.peek('animal_kind')).data==bytes((kind,))
                assert s.step(L.peek('injury_percent',1,condition)).data[0]<100
                # Compression is a real keyboard care action for animal cuts.
                if condition==0:
                    command(s,'STOP BLEEDING')
                    assert s.step(L.peek('injury_treated',1,0)).data==b'\1'
                    s.step(L.poke('fauna_rng',seed))
                    command(s,'ATTACK '+noun)
                    assert s.step(L.peek('injury_treated',1,0)).data==b'\1'
                    assert s.step(L.peek('injury_since',5)).data==time
        print('  Bear/cougar cuts, broken arm, broken leg and shock affect health; onset, fresh care and compression: OK',flush=True)


def provisions():
    # Split food, local and remote ground piles, hung food; amounts >255 oz.
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,flat())) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        for item,pack,ground,place,remote in ((23,300,20,4,0),(24,10,40,4,1),(25,20,30,5,0),(26,0,60,0,1)):
            for name,value in [('it_pack',pack),('it_gnd',ground),('it_oz',pack+ground)]:
                s.step(L.poke(name+'_lo',value,item));s.step(L.poke(name+'_hi',value>>8,item))
            s.step(L.poke('it_place',place,item));s.step(L.poke('it_x',11 if remote else 10,item));s.step(L.poke('it_y',40,item))
        water=tuple(s.step(L.peek(n,1,22)).data for n in ('it_oz_lo','it_pack_lo','it_gnd_lo','it_place'))
        gear=s.step(L.peek('it_place',22)).data
        prepare(s,6,seed_for((11,256),(0,13)));command(s,'IGNORE BEAR')
        assert 'FOOD STOLEN' in screen(s) and s.step(L.peek('animal_kind')).data==b'\0'
        for item,pack,ground,total,place in ((23,0,0,0,255),(24,0,40,40,0),(25,20,0,20,5),(26,0,60,60,0)):
            for name,value in [('it_pack',pack),('it_gnd',ground),('it_oz',total)]:
                actual=int.from_bytes(s.step(L.peek(name+'_lo',1,item)).data+s.step(L.peek(name+'_hi',1,item)).data,'little')
                assert actual==value,(item,name,actual,value)
            assert s.step(L.peek('it_place',1,item)).data==bytes((place,))
        assert gear==s.step(L.peek('it_place',22)).data
        assert water==tuple(s.step(L.peek(n,1,22)).data for n in ('it_oz_lo','it_pack_lo','it_gnd_lo','it_place'))
        # Tree theft still follows a separate injury roll. In the cabin the
        # injury risk is x .1 (D4: 11 -> 1 of 256), then theft and departure.
        prepare(s,6,seed_for((11,256),(0,26)));s.step(L.poke('tree_in',1))
        command(s,'IGNORE BEAR');assert not injury(s,6)
        prepare(s,6,seed_for((1,11),(13,256),(0,128)));s.step(L.poke('shelter_inside',1));before=snapshot(s)
        command(s,'IGNORE BEAR');assert not injury(s,6) and s.step(L.peek('animal_kind')).data==b'\0'
        assert before[6:]==snapshot(s)[6:]
        print('  Theft preserves water, gear, hung and remote stocks; exact 16-bit food totals and cover: OK',flush=True)


def hanging():
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,map_fixture())) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        command(s,'GET CHEESE')
        command(s,'HANG FOOD')
        assert s.step(L.peek('it_place',1,21)).data==b'\5'
        carried=tuple(s.step(L.peek(n,15,23)).data for n in ('it_pack_lo','it_pack_hi'))
        assert any(carried[0]) or any(carried[1])
        prepare(s,6,seed_for((11,256),(0,26)))
        command(s,'CLIMB TREE');assert s.step(L.peek('tree_in')).data==b'\1'
        assert 'ANIMALS CAN STILL REACH YOU' in screen(s)
        command(s,'IGNORE BEAR')
        assert not injury(s,6)
        assert carried==tuple(s.step(L.peek(n,15,23)).data for n in ('it_pack_lo','it_pack_hi'))
        command(s,'CLIMB DOWN');command(s,'LOWER FOOD')
        assert s.step(L.peek('it_place',1,21)).data!=b'\5'
        assert carried==tuple(s.step(L.peek(n,15,23)).data for n in ('it_pack_lo','it_pack_hi'))
        print('  Actual HANG FOOD, CLIMB TREE, encounter, descent and recovery preserve provisions: OK',flush=True)


def postures():
    for kind,noun,risk in ((6,'BEAR',11),(7,'COUGAR',11),(8,'RATTLER',16)):
        with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,map_fixture())) as s:
            s.step(IDLE);s.step(L.poke('nature_frequency',0))
            command(s,'HANG FOOD')
            provisions=tuple(s.step(L.peek(name,15,23)).data for name in ('it_pack_lo','it_pack_hi'))
            seed=seed_for((0,risk))
            prepare(s,kind,seed)
            command(s,'CLIMB TREE')
            assert s.step(L.peek('tree_in')).data==b'\1'
            assert 'ANIMALS CAN STILL REACH YOU' in screen(s)
            # Fighting is refused, but waiting in the tree is still dangerous.
            before=snapshot(s);command(s,'SCARE '+noun)
            assert snapshot(s)==before and 'LEAVE COVER' in screen(s)
            command(s,'WAIT 120 MIN')
            assert injury(s,kind) and 'INJURES YOU' in screen(s)
            assert s.step(L.peek('tree_in')).data==b'\1'
            assert s.step(L.peek('animal_kind')).data==bytes((kind,))
            assert abs(fp(s.step(L.peek('s_elap',5)).data)-1.5)<1e-7
            assert provisions==tuple(s.step(L.peek(name,15,23)).data for name in ('it_pack_lo','it_pack_hi'))
            if kind==8:
                command(s,'SUCK VENOM')
                assert s.step(L.peek('injury_treated',1,7)).data==b'\1'
            command(s,'CLIMB DOWN')
            assert s.step(L.peek('tree_in')).data==b'\0'
    # With the same first roll, an outside stationary posture avoids the
    # injury that IGNORE causes; tree/IGNORE use native rows 16/15 instead.
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,flat())) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        seed=seed_for((6,11),(26,256))
        prepare(s,6,seed);command(s,'WAIT 60 MIN')
        assert not injury(s,6) and 'INJURES YOU' not in screen(s)
        prepare(s,6,seed);command(s,'IGNORE BEAR')
        assert injury(s,6) and 'INJURES YOU' in screen(s)
    print('  Native stationary/tree posture risks; all three animals reach trees, hung provisions survive, venom care and descent work: OK',flush=True)


def unattended():
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,flat())) as s:
        s.step(IDLE);s.step(L.poke('nature_frequency',0))
        prepare(s,8,seed_for((0,11)))
        command(s,'WAIT 120 MIN')
        assert injury(s,8) and 'INJURES YOU' in screen(s)
        assert abs(fp(s.step(L.peek('s_elap',5)).data)-1)<1e-7,fp(s.step(L.peek('s_elap',5)).data)
        assert s.step(L.peek('animal_kind')).data==b'\10'
        assert s.step(L.peek('fauna_alert')).data==b'\0'
        command(s,'SUCK VENOM')
        assert s.step(L.peek('medical_actions',1,22)).data==b'\1'
        print('  Waiting stops on a reaction, reports the bite, preserves the animal and consumes the report: OK',flush=True)

if __name__=='__main__':
    decisions();severities();provisions();hanging();postures();unattended();print('Animal reactions: OK')
