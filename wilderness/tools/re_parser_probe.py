#!/usr/bin/env python3
"""re_parser_probe.py: run commands in the original, log overlays and messages.

For each command typed at the prompt: the $03DB (load and run) / $03DE
(load) calls as (track, sector, count, page) and the message numbers given
to $4E78. Local analysis aid (needs build/SIERRA.woz and build/JOURNEY.dsk).
Usage: re_parser_probe.py "CMD" ["CMD" ...]
"""
import re, subprocess, sys

A2SHOT = '../dev/tools/a2shot/a2shot'
BOOT = ['wait:5000', 'key:1\\r', 'wait:3000', 'insert:build/JOURNEY.dsk', 'key:\\r', 'wait:3000',
        'key:\\r', 'wait:600', 'key:\\r', 'wait:2400']


def text_rows(blob):
    rows = []
    for r in (20, 21, 22, 23):
        o = 0x400 + (r % 8) * 128 + (r // 8) * 40 - 0x650
        rows.append(bytes(c & 0x7F for c in blob[o:o + 40]).decode('latin1').rstrip())
    return ' | '.join(x for x in rows if x)


def probe(cmd):
    steps = BOOT + ['watch:03DB:BAFD:1', 'watch:03DE:BAFD:1', 'watch:4E78',
                    f'key:{cmd}\\r', 'wait:1500', 'peek:0650:432']
    out = subprocess.run([A2SHOT, '--disk', 'build/SIERRA.woz'] + steps, capture_output=True, text=True).stdout
    log = []
    for pc, a, x, y, mem in re.findall(r'^watch (\w{4}) A=(\w\w) X=(\w\w) Y=(\w\w).*?(?:mem=(\w+))?$', out, re.M):
        if pc == '4E78':
            log.append(f'msg {int(x, 16)}')
        elif mem != '02':
            log.append(f'{"run" if pc == "03DB" else "load"} T{x} S{y} n{int(a, 16)}')
    dump = bytes.fromhex(' '.join(re.findall(r'^0[67][0-9A-F]{2}: ([0-9A-F ]+)$', out, re.M)))
    return log, text_rows(dump) if len(dump) >= 432 else ''


def main():
    for c in sys.argv[1:]:
        log, txt = probe(c)
        print(f'{c:18} {", ".join(log):60} || {txt}')


if __name__ == '__main__':
    main()
