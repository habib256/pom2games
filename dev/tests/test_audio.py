#!/usr/bin/env python3
"""Actual 6502/65C02 PWM bus timing, all levels, page crossings and IRQ mask."""
import argparse
import importlib.util
from pathlib import Path
import re
import tempfile
import wave
from test_hgr import DEV, run, compile_source, a2test


def load_tool(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_tools(work):
    pack = load_tool('pack_wav', DEV/'tools/audio/pack_wav.py')
    gen = load_tool('generate_player', DEV/'tools/audio/generate_player.py')
    assert gen.generate() == (DEV/'lib/audio/sample_player.s').read_text()
    assert pack.encode([-1, 0, 1], fade_ms=0) == bytes((0x32, 0x62, 0x90, 0x92))
    assert pack.encode([], fade_ms=0) == b'\x92'
    for width in (1, 2, 3, 4):
        wav = work/f'pcm{width}.wav'
        with wave.open(str(wav), 'wb') as stream:
            stream.setparams((2, width, 16000, 0, 'NONE', 'not compressed'))
            # Anti-phase stereo must downmix to zero at every bit depth.
            amplitude = 1 << (8*width-2)
            raw = bytearray()
            for _ in range(320):
                for value in (-amplitude, amplitude):
                    raw += ((value + 128).to_bytes(1, 'little') if width==1
                            else value.to_bytes(width, 'little', signed=True))
            stream.writeframes(raw)
        values, rate = pack.read_pcm(wav)
        data = pack.encode(pack.resample(values, rate))
        assert data == bytes([0x62]*160 + [0x92]), (width, data)
    assert len(pack.resample([0.5]*80, 4000)) == 160
    for args in (([0]*65535, 0), ([0], -1)):
        try:
            pack.encode(*args)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid clip accepted')


def build(work):
    # Reverse order after the first sweep catches decreasing as well as
    # increasing duty transitions. Start at $xxFA and cross multiple pages.
    levels = list(range(48)) + list(reversed(range(48)))
    data = bytes(0x32 + 2*level for level in levels for _ in range(5)) + b'\x92'
    fixture = work/'fixture.s'
    fixture.write_text('''.export _main, _clip, _empty, _audio_before, _audio_after
.export _audio_done, _status, _null_before, _null_after
.import _call_audio, _a2_sample_play
.bss
_status: .res 3
.code
_main:
    cli
_audio_before:
    jsr _call_audio
_audio_after:
    php
    pla
    and #4
    sta _status
    sei
    jsr _call_audio
    php
    pla
    and #4
    sta _status+1
_null_before:
    lda #0
    tax
    jsr _a2_sample_play
_null_after:
    php
    pla
    and #4
    sta _status+2
_audio_done: jmp _audio_done
.segment "RODATA"
_empty: .byte $92
.segment "AUDIOCODE"
.align $100
.res 250, $a5
_clip:
''' + '    .byte ' + ','.join(str(b) for b in data) + '\n')
    caller = work/'caller.c'
    caller.write_text('''#include "audio.h"
extern const unsigned char clip[];
extern const unsigned char empty[];
void call_audio(void) {
    a2_sample_play(empty);
    a2_sample_play(0);
    a2_sample_play(clip);
}
''')
    player = work/'player.s'
    player.write_text((DEV/'lib/audio/sample_player.s').read_text() + '\n' +
                      '\n'.join(f'.export sound_level_{i}_0' for i in range(48)))
    objects = []
    for source in (DEV/'cc65/crt0_apple2.s', fixture, caller,
                   player):
        obj = work/(source.stem+'.o')
        compile_source(source, obj, ['-t','none','-Oirs','-I',DEV/'lib/audio'])
        objects.append(obj)
    labels, binary = work/'audio.lbl', work/'audio.bin'
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
         '-Ln',labels,'-o',binary,*objects])
    return a2test.build_disk(work,'AUDIO',binary), a2test.labels(labels), data, levels


def check(work, disk, labels, data, levels, iie):
    log = work/'speaker.txt'
    emulator = a2test.A2SHOT if iie else a2test.A2RUN
    steps = [labels.until('_audio_before')]
    if iie:
        steps += [f'tracepc:{labels[f"sound_level_{i}_0"]:04X}:5:100' for i in range(48)]
    else:
        steps += [f'spklog:{log}']
    steps += [labels.until('_audio_after', 100), labels.peek('_clip',len(data)),
             labels.until('_audio_done',100), labels.peek('_status',3)]
    result = a2test.run(disk, steps, emulator=emulator, iie=iie)
    assert result.mem(labels['_status'],3) == bytes((0,4,4)), result.out
    assert result.mem(labels['_clip'],len(data)) == data, 'clip mutated'
    if iie:
        visits = [int(c) for c in re.findall(r'tracepc [0-9A-F]+ cycles=(\d+)',result.out)]
        assert len(visits)==240, result.out
        assert all(visits[i+1]-visits[i]==126 for i in range(239)), visits
        print('65C02: all 48 levels at exact 126-cycle sample intervals; '
              'crossings, source and IRQ mask OK')
        return
    edges = [int(line) for line in log.read_text().splitlines()]
    # Two playback calls, four edges per sample (two carrier periods).
    size = len(data)-1
    assert len(edges)==size*8, (len(edges),size*8)
    for start in (0, size*4):
        for sample in range(size):
            pos = start+sample*4
            level = levels[sample//5]
            # a2run logs instruction-start timestamps. The second STA is
            # abs,X at level 1 (one cycle longer), so its bus edge occurs
            # one cycle after the timestamp; other levels use matching STA.
            width = level + 4 if level != 1 else 4
            assert edges[pos+1]-edges[pos] == width, (sample, edges[pos:pos+4])
            assert edges[pos+3]-edges[pos+2] == width, (sample, edges[pos:pos+4])
            assert edges[pos+2]-edges[pos] == 63, (sample, edges[pos:pos+4])
            if sample < size-1:
                assert edges[pos+4]-edges[pos] == 126, (sample,edges[pos:pos+5])
    print(f'{"65C02" if iie else "6502"}: 48 PWM levels, {size} samples twice, '
          'exact 63-cycle carrier/126-cycle samples, crossings, source and IRQ mask OK')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    run(['make','-s','-C',DEV/'tools'/('a2shot' if args.iie else 'a2run')])
    with tempfile.TemporaryDirectory(prefix='pom2-audio-') as temp:
        work = Path(temp)
        check_tools(work)
        check(work,*build(work),args.iie)


if __name__ == '__main__':
    main()
