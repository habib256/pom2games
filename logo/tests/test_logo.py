#!/usr/bin/env python3
"""LOGO's shared HGR engine through actual commands, on II+ and 80-column IIe."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test

COMMANDS = [
    'PU CS SETXY 0 80 SETH 90 PD FD 279',
    'PU CS SETPC 4 SETXY 255 100 SETH 90 PD FD 24',
    'CS SETPC 15 SETXY 40 100 SETH 0 PD REPEAT 4 [FD 40 RT 90]',
    'PU CS SETXY 268 80 SETSHAPE "HAPPY',
    'RT 90',
    'SAY "HELLO',
    'SETSHAPE "ARROW',
    'FS', 'SS', 'TS COLUMNS 40',
]


def pixel(page,x,y):
    return page[a2test.hgr_offset(y)+x//7] & (1 << (x%7))


def check(disk, labels, iie):
    names = ['cmd_status','tx_lo','tx_hi','ty_lo','sprite_mode','scr_mode','scr_iie','col80_ok']
    state_size = len(names) + int(iie)
    def snapshot():
        return [labels.peek(name) for name in names] + (['peek:C01F:1'] if iie else []) + ['peek:2000:8192']
    commands = COMMANDS + (['COLUMNS 80','COLUMNS 40'] if iie else [])
    steps = [labels.until('read_line'),*snapshot()]
    for command in commands:
        # a2shot's queueKey holds one key: type the line with pacing, then
        # queue only RETURN so the instruction checkpoint remains exact.
        steps += ['key:'+command,'press:\r',labels.until('repl'),*snapshot(),labels.until('read_line')]
    steps += ['key:BYE\r','wait:90','peek:0400:1024']
    result = a2test.run(disk,steps,iie=iie)
    records, pos = [], 0
    for _ in range(len(commands)+1):
        state = result.data[pos:pos+state_size]
        pos += state_size
        page = result.data[pos:pos+8192]
        pos += 8192
        records.append((state,page))
    boot = records[0][0]
    assert boot[1:4] == bytes((128,0,96)), ('boot turtle',iie,boot)
    assert boot[5:8] == bytes((1,int(iie),int(iie))), ('console/model',iie,boot)
    if iie:
        assert boot[8] & 128, '80-column console did not start'
    for index,(state,page) in enumerate(records[1:]):
        assert state[0] != 2, ('LOGO command error',iie,commands[index],state)
    state,page = records[1]
    assert state[1:4] == bytes((23,1,80)), ('full-width move',iie,state)
    assert all(pixel(page,x,80) for x in range(270)), ('full-width trail',iie)
    state,page = records[2]
    assert state[1:4] == bytes((23,1,100)), ('high-X move',iie,state)
    assert all(pixel(page,x,100) for x in range(255,270)), ('right-edge trail',iie)
    assert page[a2test.hgr_offset(100)+36] & 128, ('pen palette',iie)
    state,page = records[3]
    assert state[1:4] == bytes((40,0,100)), ('REPEAT square',iie,state)
    assert all(pixel(page,x,y) for x,y in ((40,60),(80,60),(80,100))), ('square',iie)
    assert records[4][0][4] == 1, ('dynamic turtle',iie)
    assert any(pixel(records[4][1],x,y) for y in range(60,100) for x in range(256,280)), ('emote beyond 255',iie)
    assert records[4][1] == records[5][1], ('turning emote changes pixels',iie)
    assert records[6][1] != records[5][1], ('SAY did not draw',iie)
    assert records[7][0][4] == 0, ('ARROW adapter',iie)
    assert [records[n][0][5] for n in (8,9,10)] == [2,1,0], ('FS/SS/TS',iie)
    if iie:
        assert [records[n][0][8] & 128 for n in (10,11,12)] == [0,128,0], 'COLUMNS 40/80 switches'
    text = bytes(c & 127 for c in result.data[pos:])
    assert b']' in text, ('BYE did not return to DOS',iie)
    assert len(result.data) == pos+1024
    print(f'LOGO {"IIe 80 columns" if iie else "II+ 40 columns"}: full-width trails, colour, REPEAT, sprites, SAY, screen modes, columns and BYE OK.')
    return records


def reset(disk, labels, iie):
    result = a2test.run(disk,[labels.until('read_line'),'key:SETXY 279 191\r',
                             'wait:30','reset','wait:120','peek:0400:1024'],iie=iie)
    assert b']' in bytes(c & 127 for c in result.data), ('RESET did not return to DOS',iie)
    print(f'LOGO {"IIe" if iie else "II+"}: Ctrl-RESET returns to DOS.')


if __name__ == '__main__':
    subprocess.run(['make','-C',str(ROOT/'logo')],check=True,stdout=subprocess.DEVNULL)
    labels = a2test.labels(ROOT/'logo/build/logo.lbl')
    for iie in (False,True):
        check(ROOT/'dist/LOGO.dsk',labels,iie)
        reset(ROOT/'dist/LOGO.dsk',labels,iie)
