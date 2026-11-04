#!/usr/bin/env python3
"""Real ProDOS hard-disk writes and side-effect-free physical RAM inspection."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT/'dev'
sys.path.insert(0, str(DEV/'tools'))
sys.path.insert(0, str(DEV/'tools/prodos'))
import a2test
from read_volume import Image

ASM='''
.setcpu "65C02"
.code
start:
        cld
; Release pages $3000-$33FF in ProDOS's system bitmap for our I/O buffer.
        lda $BF5E
        and #$0F
        sta $BF5E
        lda #<name
        sta pf_name
        lda #>name
        sta pf_name+1
        lda #0
        sta pf_iobuf
        lda #$30
        sta pf_iobuf+1
        lda #<payload
        sta pf_buf
        lda #>payload
        sta pf_buf+1
        lda #0
        sta pf_len
        lda #4
        sta pf_len+1
        jsr prodos_save
        sta errors
        bcs failed
        lda #0
        sta pf_buf
        lda #$40
        sta pf_buf+1
        jsr prodos_load_free
        sta errors+1
        bcs failed
done:   lda $C000
        bpl done
        bit $C010
        inc keys
        bra done
keys:   .byte 0
failed: jmp failed
errors: .byte $FF,$FF
name:   .byte 15,"/HARNESS/RESULT"
payload:
.repeat 1024,I
        .byte (I*73+19)&255
.endrepeat
.include "file.asm"
'''


PAYLOAD = bytes((i*73+19) & 255 for i in range(1024))
VOLUME_BYTES = 2048*512
PREFIX_BYTES = 128
TRAILER = b'POM2 HDD harness: preserve the 2IMG comment.\n'


def run(command):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout+result.stderr
    return result.stdout


def wrapped(raw):
    header = bytearray(PREFIX_BYTES)
    header[:8] = b'2IMGPYTH'
    header[8:10] = (64).to_bytes(2, 'little')
    header[10:12] = (1).to_bytes(2, 'little')
    for offset, value in ((12, 1), (20, 2048), (24, PREFIX_BYTES),
                          (28, len(raw)), (32, PREFIX_BYTES+len(raw)), (36, len(TRAILER))):
        header[offset:offset+4] = value.to_bytes(4, 'little')
    header[64:] = bytes([0xA5])*64
    return bytes(header)+raw+TRAILER


def check(work, emulator, labels, original, machine, container, expected_commit):
    tag = machine+('-2mg' if container else '-raw')
    source = work/(tag+('.2mg' if container else '.po'))
    source.write_bytes(wrapped(original) if container else original)
    before = source.read_bytes()
    saved = work/(tag+'-saved'+source.suffix)
    done = labels['done']
    pause = f'until:{done:04X}:1'
    # Stop at the same PC around physical auxiliary RAM access, with an
    # unread key pending and RAMRD toggled, without advancing the machine.
    steps = [f'until:{done:04X},{labels["failed"]:04X}:2000',
             labels.peek('errors', 2), 'peek:4000:1024', 'hddinfo',
             'press:A', 'keyinfo', pause,
             'ramset:aux:4000:11223344', 'ram:aux:4000:4',
             'peek:4000:4', 'ramhash:aux:4000:4', 'peek:C013:2', 'poke:C003:0',
             'ram:aux:4000:4', 'peek:C013:2', 'poke:C002:0', 'keyinfo', pause,
             'keywait:120', 'keyinfo', 'rawkey:1B', 'keywait:120', 'keyinfo',
             f'ram:main:{labels["keys"]:04X}:1', f'hddsave:{saved}', 'hddinfo', 'provenance']
    output = run([emulator, '--'+machine, '--roms', DEV/'tools/a2shot/roms',
                  '--disk', source, *a2test.escape(steps)])
    result = a2test.Result(output)
    assert result.mem(labels['errors'], 2) == bytes(2), output
    assert result.mem(0x4000, 1024) == PAYLOAD
    assert result.mem(0x4000, 4, 1) == bytes.fromhex('11223344')
    assert result.mem(0x4000, 4, 2) == PAYLOAD[:4], 'auxiliary write changed main RAM'
    assert result.mem(0x4000, 4, 3) == bytes.fromhex('11223344')
    assert result.mem(labels['keys'], 1) == b'\x02', output[-2500:]
    cycles = re.findall(r'until .* cycles=(\d+) PC=([0-9A-F]+)', output)
    assert len(cycles) == 3 and len(set(cycles)) == 1 and int(cycles[0][1], 16) == done, cycles
    keyboard = re.findall(r'keyboard key=([0-9A-F]+) strobe=(\d+) queued=(\d+)', output)
    assert len(keyboard) == 4 and keyboard[0] == keyboard[1], keyboard
    assert int(keyboard[0][1]) or int(keyboard[0][2]), keyboard
    assert all(strobe == queued == '0' for _, strobe, queued in keyboard[2:]), keyboard
    before_flags = result.mem(0xC013, 2)
    after_flags = result.mem(0xC013, 2, 1)
    assert not any(value & 128 for value in before_flags)
    assert bytes(a ^ b for a, b in zip(before_flags, after_flags)) == b'\x80\0'
    assert 'ramhash aux 4000 4 '+hashlib.sha256(bytes.fromhex('11223344')).hexdigest() in output
    slot = 7 if machine == 'iie' else 5
    states = re.findall(r'hdd slot=(\d+) blocks=(\d+) wp=(\d+) unsaved=(\d+)', output)
    assert len(states) == 2 and all(s[:3] == (str(slot), '2048', '0') for s in states), states
    assert int(states[0][3]) > 0 and states[1][3] == '0', states
    assert source.read_bytes() == before, 'a2shot changed the source image'
    exported = saved.read_bytes()
    if container:
        assert len(exported) == len(before)
        assert exported[:PREFIX_BYTES] == before[:PREFIX_BYTES]
        assert exported[PREFIX_BYTES+VOLUME_BYTES:] == TRAILER
        exported = exported[PREFIX_BYTES:PREFIX_BYTES+VOLUME_BYTES]
    assert len(exported) == VOLUME_BYTES and exported != original
    image = Image(exported)
    entry = next(e for e in image.entries(2) if e[1:1+(e[0] & 15)] == b'RESULT')
    assert image.read(entry) == PAYLOAD
    assert int.from_bytes(entry[0x11:0x13], 'little') >= 1600, 'write did not reach beyond 800 KiB'
    assert 'hddsave ok' in output
    if expected_commit:
        assert 'commit='+expected_commit in output
    for capability in ('harddisk', 'ram.banks', 'keyboard.state', 'provenance'):
        assert capability in output
    print(f'{tag}: ProDOS boot/write/read above 800 KiB, private hddsave, RAM/keyboard/cycles OK', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--a2shot', type=Path)
    parser.add_argument('--expected-commit')
    args = parser.parse_args()
    if args.a2shot is None:
        if not args.expected_commit and not a2test.have_a2shot('hard-disk harness'):
            return
        args.a2shot = a2test.A2SHOT
    with tempfile.TemporaryDirectory(prefix='a2shot-hdd-') as temporary:
        work = Path(temporary)
        source = work/'fixture.s'
        source.write_text(ASM)
        run(['ca65', '-g', '-I', DEV/'lib/prodos', '-I', DEV/'lib/apple2',
             '-o', work/'fixture.o', source])
        run(['ld65', '-C', DEV/'cc65/prodos_sys.cfg', '-Ln', work/'fixture.lbl',
             '-o', work/'fixture.bin', work/'fixture.o'])
        labels = a2test.labels(work/'fixture.lbl')
        # Force ProDOS to allocate RESULT beyond the 800 KiB floppy limit.
        disk = a2test.prodos_volume(work/'original.po', {
            'PRODOS#FF0000': (DEV/'tools/prodos/PRODOS').read_bytes(),
            'HARNESS.SYSTEM#FF2000': (work/'fixture.bin').read_bytes(),
            'FILLER#060000': bytes([0xD7])*(900*1024)}, 'HARNESS', blocks=2048)
        original = disk.read_bytes()
        for machine in ('iie', 'iic'):
            for container in (False, True):
                check(work, args.a2shot.resolve(), labels, original, machine,
                      container, args.expected_commit)


if __name__ == '__main__':
    main()
