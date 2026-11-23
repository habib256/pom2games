#!/usr/bin/env python3
"""LOGO's shared HGR engine through actual commands, on II+ and 80-column IIe."""
from pathlib import Path
import math
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


def check_setxy_y(disk, labels, iie):
    steps = [labels.until('read_line')]
    for y in (190, 191, 192, 255, 256, 257):
        steps += [f'key:SETXY 42 {y}', 'press:\r', labels.until('repl'),
                  labels.peek('ty_lo'), labels.until('read_line')]
    result = a2test.run(disk, steps, iie=iie)
    assert list(result.data) == [190, 191, 191, 191, 191, 191], ('SETXY Y', iie, result.data)


def check_editor(disk, labels, iie):
    steps = [labels.until('read_line')]
    expected = bytearray()

    def submit(line):
        steps.extend(['key:'+line, 'press:\r', labels.until('repl'), labels.until('read_line')])

    def editor_key(key, destination='@key_loop'):
        steps.extend(['press:'+key, labels.until('wait_key'), labels.until(destination)])

    def replace(text):
        editor_key('E', '@in_loop')
        steps.extend(['key:'+text, 'press:\r', labels.until('@key_loop')])

    def body(content):
        steps.append(labels.peek('proc_table', len(content)+1, labels['BUFED_BODYLEN_OFF']))
        expected.extend(bytes([len(content)]) + content)

    submit('TO Z')
    submit('END')
    steps.extend(['key:EDIT Z', 'press:\r', labels.until('@key_loop')])
    replace('PX\x08U')
    body(b'PU\r')
    editor_key('I')
    body(b'PU\r\r')
    replace('PD')
    editor_key('U')
    replace('HOME')
    body(b'HOME\rPD\r')
    replace('PU')
    body(b'PU\rPD\r')
    editor_key('X')
    editor_key('X')
    editor_key('I')
    body(b'\r')
    for _ in range(20):
        editor_key('I')
    steps.append(labels.peek('ed_cur_line'))
    expected.append(20)
    replace('PD'+' '*57+'X')
    body(b'\r'*20+b'PD'+b' '*57+b'\r')
    steps.extend(['press:Q', labels.until('repl'), labels.peek('scr_mode')])
    expected.append(1)
    actual = a2test.run(disk, steps, iie=iie).data
    assert actual == expected, ('procedure editor', iie, actual, expected)


def check_console(disk, labels, iie):
    steps = [labels.until('read_line')]
    def command(text):
        steps.extend(['key:'+text, 'press:\r', labels.until('repl')])
    def prompt():
        steps.append(labels.until('read_line'))

    command('STOP PD')
    prompt()
    command('PU')
    steps.append(labels.peek('pen'))
    prompt()
    for line in ['TO Z', 'Z', 'END', 'SETXY 270 40', 'SETSHAPE "HAPPY']:
        command(line)
        prompt()
    steps.append(labels.peek('shape_pat_lo', 2))
    command('LIST')
    steps.append(labels.peek('shape_pat_lo', 2))
    prompt()
    command('LIST Z')
    steps.extend(labels.peek(n) for n in ('tx_lo','tx_hi','ty_lo','turtle_visible'))
    prompt()
    for line, entry in [('Z','proc_invoke'), ('WAIT 100','cmd_wait'), ('PAUSE 255','cmd_pause')]:
        command('SS')
        prompt()
        steps.extend(['key:'+line, 'press:\r', labels.until(entry), 'press:\x14', 'wait:5',
                      labels.peek('scr_mode'), 'press:\x07', labels.until('repl', 10),
                      labels.peek('ctrl_sp')])
        prompt()
    for page in (1, 257):
        steps.extend([f'key:HELP {page}', 'press:\r', labels.until('print_str_ax'),
                      'until:FDED:10', labels.peek('mptr_lo', 2), labels.until('repl')])
        prompt()
    state = a2test.run(disk, steps, iie=iie).data
    assert state[0] == 0 and state[1:3] == state[3:5], ('STOP / LIST', iie, state)
    assert state[5:9] == bytes([14,1,40,0]), ('LIST Z turtle', iie, state)
    assert state[9:15] == bytes(6), ('keyboard during execution', iie, state)
    pages = [labels[name].to_bytes(2,'little') for name in ('help_p1','help_toc')]
    assert state[15:] == b''.join(pages), ('HELP topic', iie, state)


def check_procedure_frames(disk, labels, iie):
    steps = [labels.until('read_line')]
    def submit(line):
        steps.extend(['key:'+line, 'press:\r', labels.until('repl'), labels.until('read_line')])

    for line in ('TO LEAF :A :B', 'SETXY :A :B', 'END',
                 'TO TOP', 'SETXY 10 20', 'LEAF RANDOM 10 42', 'END', 'TOP'):
        submit(line)
    steps.extend(labels.peek(name) for name in ('tx_lo','ty_lo','lfsr_lo','lfsr_hi'))
    for line in ('MAKE "X 71', 'TO ZERO', 'SETXY :X 43', 'END',
                 'TO PASS :X', 'SETXY 11 22', 'ZERO', 'END', 'PASS 19'):
        submit(line)
    steps.extend(labels.peek(name) for name in ('tx_lo','ty_lo'))
    for line in ('TO DEEP :N', 'IF :N = 1 [STOP]', 'REPEAT 1 [IF 1 = 1 [DEEP :N - 1]]',
                 'SETXY :N 44', 'RT 1', 'END', 'DEEP 16'):
        submit(line)
    steps.extend(labels.peek(name) for name in ('tx_lo','th_lo','ctrl_sp','n_params_active','cmd_status'))
    submit('DEEP 17')
    steps.extend(labels.peek(name) for name in ('ctrl_sp','cmd_status'))
    for line in ('TO EVEN :N', 'IF :N = 0 [SETXY 80 45 STOP]', 'ODD :N - 1', 'END',
                 'TO ODD :N', 'IF :N = 0 [SETXY 81 45 STOP]', 'EVEN :N - 1', 'END',
                 'EVEN 33'):
        submit(line)
    steps.extend(labels.peek(name) for name in ('tx_lo','ty_lo','ctrl_sp','cmd_status'))
    state = a2test.run(disk, steps, iie=iie).data
    assert state == bytes([6,42,0xD6,0x70,71,43,16,15,0,0,1,0,2,81,45,0,1]), ('procedure frames', iie, state)


def check_labels_and_timing(disk, labels, iie):
    steps = [labels.until('read_line'), labels.peek('bbfont', 8, 65 * 8)]
    cases = [(128, 96), (252, 150), (278, 190)]
    for x, y in cases:
        for command in (f'PU CS SETXY {x} {y}', 'LABEL "AA', 'SETXY 1 191'):
            steps += ['key:' + command, 'press:\r', labels.until('repl'), labels.until('read_line')]
            if command.startswith('LABEL'):
                steps += [labels.peek('tx_lo'), labels.peek('tx_hi')]
        steps += ['peek:2000:8192']
    result = a2test.run(disk, steps, iie=iie)
    font = result.data[:8]
    pos = 8
    for x, y in cases:
        assert int.from_bytes(result.data[pos:pos+2], 'little') == min(x+16, 279)
        pos += 2
        expected = bytearray(8192)
        for left in (x, x+8):
            for row, bits in enumerate(font):
                for bit in range(8):
                    px = left + bit
                    if px < 280 and y+row < 192 and bits & (1 << bit):
                        expected[a2test.hgr_offset(y+row)+px//7] |= 1 << (px%7)
        assert result.data[pos:pos+8192] == expected, ('LABEL raster', iie, x, y)
        pos += 8192

    for command, minimum, maximum in [('WAIT', 575000, 625000), ('PAUSE', 95000, 105000)]:
        steps = [labels.until('read_line')]
        for units in (0, 1):
            steps += [f'key:{command} {units}', 'press:\r', labels.until('cmd_'+command.lower()),
                      labels.until('repl'), labels.until('read_line')]
        cycles = a2test.run(disk, steps, iie=iie).cycles
        duration = (cycles[-2]-cycles[-3]) - (cycles[-5]-cycles[-6])
        assert minimum <= duration <= maximum, (command, iie, duration)


def reset(disk, labels, iie):
    result = a2test.run(disk,[labels.until('read_line'),'key:SETXY 279 191\r',
                             'wait:30','reset','wait:120','peek:0400:1024'],iie=iie)
    assert b']' in bytes(c & 127 for c in result.data), ('RESET did not return to DOS',iie)
    print(f'LOGO {"IIe" if iie else "II+"}: Ctrl-RESET returns to DOS.')


def check_numeric_rules(disk, labels, iie):
    steps = [labels.until('read_line'), labels.peek('sin_q', 91)]
    cases = [
        ('PU SETXY 0 120 SETH 14 FD 64', 'tx_lo', 15),
        ('PD IF 32767 > 0 - 1 [PU]', 'pen', 0),
        ('PD IFELSE 0 - 32768 < 1 [PU] [PD]', 'pen', 0),
        ('PD IF 0 = 0 - 32768 [PU]', 'pen', 1),
        ('SETXY 42 RANDOM 1 + 20', 'ty_lo', 20),
        ('SETXY 42 RANDOM 254', 'ty_lo', 180),
        ('SETXY 42 RANDOM 256', 'ty_lo', 1),
        ('PU REPEAT 65535 [] PD', 'pen', 1),
        ('PD REPEAT FOREVER - 65535 [PU]', 'pen', 1),
    ]
    for command, state, _ in cases:
        if 'RANDOM' in command:
            # The next two mixed bytes are 1 and 180. With N=254 the
            # incomplete bucket discards 1, while with N=255 it accepts 1.
            steps += [labels.poke('lfsr_lo', 2), labels.poke('lfsr_hi', 0)]
        steps += ['key:' + command, 'press:\r', labels.until('repl'),
                  labels.peek(state), labels.until('read_line')]
    # Allow more time than 65535 empty iterations, then interrupt the loop.
    steps += ['key:PU REPEAT FOREVER [] PD', 'press:\r', 'wait:3000',
              labels.peek('pen'), 'press:\x1b', labels.until('repl'),
              labels.peek('pen'), labels.until('read_line')]
    result = a2test.run(disk, steps, iie=iie)
    expected = [want for _, _, want in cases] + [0, 0]
    assert list(result.data[:91]) == [round(64 * math.sin(math.radians(n))) for n in range(91)]
    assert list(result.data[91:]) == expected, ('numeric rules', iie, result.data[91:], expected)


if __name__ == '__main__':
    subprocess.run(['make','-C',str(ROOT/'logo')],check=True,stdout=subprocess.DEVNULL)
    labels = a2test.labels(ROOT/'logo/build/logo.lbl', any_name=True)
    for iie in (False,True):
        if iie and not a2test.have_a2shot('LOGO on the IIe'):
            continue
        check(ROOT/'dist/LOGO.dsk',labels,iie)
        check_labels_and_timing(ROOT/'dist/LOGO.dsk',labels,iie)
        check_setxy_y(ROOT/'dist/LOGO.dsk',labels,iie)
        check_numeric_rules(ROOT/'dist/LOGO.dsk', labels, iie)
        check_editor(ROOT/'dist/LOGO.dsk',labels,iie)
        check_console(ROOT/'dist/LOGO.dsk',labels,iie)
        check_procedure_frames(ROOT/'dist/LOGO.dsk',labels,iie)
        reset(ROOT/'dist/LOGO.dsk',labels,iie)
