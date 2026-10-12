#!/usr/bin/env python3
"""Refusal matrix, real stock/capacity numbers, persistence and bounded text."""
import tempfile
from common import L, a2test, disk_with, fp, text_screen
from test_input import flat, command, IDLE, NUMBER, snapshot
from test_thermal import call


def rows(s):
    return text_screen(s.step('peek:0400:1024').data)


def refuse(s, text, expected):
    before=snapshot(s)
    command(s,text)
    actual='\n'.join(rows(s)[21:])
    assert all(part in actual for part in expected),(text,actual,expected)
    assert snapshot(s)==before,(text,'refusal changed state')
    return actual


def set16(s,name,value,offset=0):
    s.step(L.poke(name,value,offset))
    s.step(L.poke(name,value>>8,offset+1))


def exact_travel_end():
    for obstacle, start, next_cell in (('water', 10, 138),
                                        ('cliff', 10, 60),
                                        ('map edge', 108, 10)):
        m = flat()
        m[3] = start
        m[64+40*112+start+2] = next_cell
        with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,m)) as s:
            s.step(IDLE)
            s.step(L.poke('nature_frequency',0))
            command(s,'WALK 18 MIN')
            assert s.step(L.peek('px',2)).data == bytes((0,start+1)), obstacle
            assert abs(fp(s.step(L.peek('s_elap',5)).data)*60-18)<1e-5
            assert s.step(L.peek('travel_reason')).data == b'\0', obstacle
            actual='\n'.join(rows(s)[21:])
            assert 'TRAVEL: 18 MINUTES.' in actual, (obstacle,actual)
            assert 'REQUESTED TRAVEL TIME ENDED.' in actual, (obstacle,actual)
    m = flat()
    m[3] = 109
    m[21] = 11
    m[64:] = bytes([138])*9408
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency',0))
        command(s,'SWIM 28 MIN')
        assert s.step(L.peek('px',2)).data == bytes((128,109))
        assert abs(fp(s.step(L.peek('s_elap',5)).data)*60-28)<1e-5
        assert s.step(L.peek('travel_reason')).data == b'\0'
        assert 'REQUESTED TRAVEL TIME ENDED.' in '\n'.join(rows(s)[21:])
    for flag,reason,expected in (('fauna_alert',5,'A DISCOVERY INTERRUPTS'),
                                ('night',3,'TOO DARK TO TRAVEL')):
        with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,flat())) as s:
            s.step(IDLE)
            s.step(L.poke('nature_frequency',0))
            s.step('key:WALK 19 MIN')
            s.step('press:\\r')
            s.step(L.until('walk_progress',20000))
            s.step(L.until('at_goal',6000))
            s.step(L.poke(flag,1))
            s.step(IDLE)
            assert s.step(L.peek('travel_reason')).data == bytes([reason]), flag
            assert expected in '\n'.join(rows(s)[21:]), flag
    # If time is still available, a real obstruction must keep its own cause.
    m = flat()
    m[64+40*112+12] = 138
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,m)) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency',0))
        command(s,'WALK 36 MIN')
        assert s.step(L.peek('travel_reason')).data == b'\1'
        assert 'WATER AHEAD.' in '\n'.join(rows(s)[21:])
    print('  Exact WALK/SWIM duration: no extra obstacle probe; animal/night priority and remaining-time obstacles retained')


def main():
    exact_travel_end()
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,flat())) as s:
        s.step(IDLE)
        for text,expected in (
            ('FROBNICATE AXE',('UNKNOWN VERB: FROBNICATE','TYPE HELP')),
            ('GET',('NAME AN ITEM','GET HAT')),
            ('WEAR',('NAME AN ITEM','WEAR PARKA')),
            ('DROP',('NAME AN ITEM','DROP AXE')),
            ('EAT',('NAME A FOOD','EAT CHEESE')),
            ('DRINK',('TRY DRINK WATER',)),
            ('GET SHOES',('SHOES','NOT ACCESSIBLE HERE','CHECK INVENTORY')),
            ('USE AXE',('NOT IN THIS VERSION',)),
            ('WEAR AXE',("YOU CAN'T WEAR THAT",)),
            ('EAT AXE',("YOU CAN'T EAT THAT",)),
            ('DROP BACKPACK',('EMPTY THE BACKPACK','DROP ITS CONTENTS')),
            ('DROP CANTEEN',('EMPTY THE CANTEEN','DRINK WATER OR DROP WATER')),
            ('PACK BACKPACK',('CANNOT HOLD ITSELF','CARRY BACKPACK')),
        ):
            refuse(s,text,expected)
        for item,text,expected in ((21,'GET SUNSCREEN',('BACKPACK NEEDED','CARRY BACKPACK')),
                                   (64,'GET WATER',('CANTEEN NEEDED','GET CANTEEN'))):
            original=s.step(L.peek('it_place',1,item)).data[0]
            s.step(L.poke('it_place',255,item))
            refuse(s,text,expected)
            s.step(L.poke('it_place',original,item))
        usage=s.step(L.peek('load_used',8)).data
        usage=[int.from_bytes(usage[k:k+2],'little') for k in range(0,8,2)]
        limits=s.step(L.peek('load_limits',8)).data
        def restore_limits():
            for k,b in enumerate(limits): s.step(L.poke('load_limits',b,k))
        set16(s,'load_limits',usage[0]+47)
        refuse(s,'GET APPLES',('TRANSFER REFUSED: WEIGHT.','WEIGHT: +1 OZ; FREE 47 OZ'))
        set16(s,'load_limits',usage[2]+95,4)
        refuse(s,'GET APPLES',('WEIGHT + VOLUME','WEIGHT: +1 OZ; FREE 47 OZ','PACK: +1 IN3; FREE 95 IN3'))
        restore_limits()
        for index,text,gain,place in ((1,'WEAR PARKA',180,'WEAR'),(2,'PACK HAT',35,'PACK'),(3,'CARRY HAT',35,'HAND')):
            set16(s,'load_limits',usage[index]+gain-1,2*index)
            refuse(s,text,('TRANSFER REFUSED: VOLUME.',f'{place}: +1 IN3; FREE {gain-1} IN3'))
            restore_limits()
        old=s.step(L.peek('it_gnd_lo',1,37)).data[0]
        s.step(L.poke('it_gnd_lo',255,37));s.step(L.poke('it_gnd_hi',255,37))
        refuse(s,'GET APPLES',('VALUE TOO LARGE','REDUCE THE AMOUNT'))
        s.step(L.poke('it_gnd_lo',old,37));s.step(L.poke('it_gnd_hi',0,37))
        result=refuse(s,'DROP',('NAME AN ITEM',))
        s.step('wait:600')
        assert '\n'.join(rows(s)[21:])==result
        command(s,'')
        assert '\n'.join(rows(s)[21:])==result
        s.step('key:REST');s.step('key:\\e');s.step(IDLE)
        assert '\n'.join(rows(s)[21:])==result
        print('  Refusal matrix: causes, correction commands, exact excess/free capacity, atomic state and persistence OK')
        before=snapshot(s)
        s.step('key:EAT CHEESE');s.step('press:\\r');s.step(NUMBER)
        available=int.from_bytes(s.step(L.peek('stock_available',2)).data,'little')
        assert f'ACCESSIBLE: {available} OZ.' in '\n'.join(rows(s))
        assert snapshot(s)==before
        s.step('key:255\\r');s.step(IDLE)
        assert f'YOU ATE {available} OUNCES.' in '\n'.join(rows(s))
        assert f'ACCESSIBLE BEFORE: {available} OZ.' in '\n'.join(rows(s))
        assert s.step(L.peek('it_pack_lo',1,28)).data==b'\0'
        assert s.step(L.peek('it_gnd_lo',1,28)).data==b'\0'
        command(s,'DRINK WATER 255 OZ')
        available=int.from_bytes(s.step(L.peek('stock_available',2)).data,'little')
        assert f'YOU DRANK {available} OUNCES.' in '\n'.join(rows(s))
        command(s,'GET SNAKEBITE KIT')
        assert 'PACK: SNAKEBT KIT' in '\n'.join(rows(s)),rows(s)[21:]
        print('  Consumption: stock before answer, actual exhausted amount, and qualified inventory names OK')
        # Display all maximum values while preserving the map/text above row 20.
        for name in ('load_excess','load_free'):
            set16(s,name,65535,0);set16(s,name,65535,4)
        s.step(L.poke('load_reason_weight',1));s.step(L.poke('load_reason_volume',4))
        s.step(L.poke('load_reason_overflow',0))
        above=rows(s)[:20]
        # The summary now replaces the item overlay after each transfer.
        # Load the real report module explicitly before this isolated probe.
        addr=L['idle']; load=L['overlay_load']; report=L['load_report']
        code=bytes((0xA9,14,0x20,load&255,load>>8,
                    0x20,report&255,report>>8,0x4C,addr&255,addr>>8))
        for k,b in enumerate(code): s.step(f'poke:{addr+k:04X}:{b:02X}')
        s.step(f'until:{L["idle"]+8:04X}:6000')
        actual=rows(s)
        assert above==actual[:20],'message scrolled the screen'
        assert 'WEIGHT: +65535 OZ; FREE 65535 OZ' in actual[22]
        assert 'PACK: +65535 IN3; FREE 65535 IN3' in actual[23]
        print('  Maximum 16-bit values fit all three rows without scrolling OK')
        # A future longer item label must remain on its row and never scroll.
        for k,b in enumerate(b'A'*60+b'\0'):
            s.step(f'poke:{0x300+k:04X}:{b:02X}')
        s.step(L.poke('noun',19))
        s.step(L.poke('it_name_lo',0,19));s.step(L.poke('it_name_hi',3,19))
        code=bytes((0xA9,L['m_taken']&255,0xA2,L['m_taken']>>8,
                    0x20,L['message']&255,L['message']>>8))
        code+=bytes((0x4C,(L['idle']+7)&255,(L['idle']+7)>>8))
        # The prior driver is stopped at idle+8, so complete its JMP first.
        s.step(IDLE)
        for k,b in enumerate(code): s.step(L.poke('idle',b,k))
        s.step(f'until:{L["idle"]+7:04X}:6000')
        actual=rows(s)
        assert above==actual[:20]
        assert actual[21].startswith('> PACK: '+31*'A') and actual[21][39]==' ',actual[21:]
        assert not actual[22].strip() and not actual[23].strip()
        print('  Expanded item names are clipped without wrapping or scrolling OK')
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,flat())) as s:
        s.step(IDLE)
        s.step('key:WALK 4 H');s.step('press:\\r');s.step(L.until('walk_progress',20000))
        s.step(L.until('at_goal',6000));s.step(L.poke('fauna_alert',1))
        s.step(IDLE)
        actual='\n'.join(rows(s))
        assert 'TRAVEL: 9 MINUTES.' in actual and 'A DISCOVERY INTERRUPTS' in actual
        assert abs(fp(s.step(L.peek('s_elap',5)).data)*60-9)<1e-5
        print('  Animal interruption retains the completed duration and cause together OK')
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,flat())) as s:
        s.step(IDLE)
        s.step('key:WALK 4 H');s.step('press:\\r');s.step(L.until('walk_progress',20000))
        s.step(L.until('at_goal',6000));s.step(L.poke('night',1))
        s.step(IDLE)
        actual='\n'.join(rows(s))
        assert 'TRAVEL: 9 MINUTES.' in actual and 'TOO DARK TO TRAVEL' in actual
        assert 'NOT ENOUGH LIGHT' not in actual
        print('  Night stop survives view restoration with duration and cause together OK')
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp,flat())) as s:
        s.step(IDLE)
        before=rows(s)[:20]
        s.step(L.poke('won',1))
        s.step(L.poke('travel_action',0))
        for step in call(['report']): s.step(step)
        s.step(f'until:{L["idle"]+3:04X}:6000')
        actual=rows(s)
        assert actual[:20]==before,'victory message scrolled the screen'
        assert 'RANGER OUTPOST.' in actual[21] and 'YOU SURVIVED. PRESS A KEY.' in actual[22]
        assert not actual[23].strip(),'victory message expanded a travel placeholder'
        print('  Non-travel victory report: complete literal text, no stop-reason substitution OK')
    print('Neowilderness feedback lot 2: OK')


if __name__=='__main__': main()
