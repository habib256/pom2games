#!/usr/bin/env python3
"""re_surv_fp.py: annotate a module that computes with Applesoft ROM floats.

Reads MODULE.bin (loaded at $5800 unless --org) and the game RAM dump
(build/game.bin) for state values; prints a pseudo-code listing where
'lda #lo / ldy #hi / jsr ROUTINE' become 'FAC = [addr]' etc., with the value
of constant floats (5-byte Applesoft format) and of state floats at the
first view. Usage: re_surv_fp.py MODULE.bin [--org 0x5800] [--from A --to B]
"""
import argparse, re, subprocess, sys

ROM = {
    0xE7A0: 'FAC += 0.5', 0xE7A7: 'FAC = {m} - FAC', 0xE7AA: 'FAC = ARG - FAC',
    0xE7BE: 'FAC = {m} + FAC', 0xE7C1: 'FAC = ARG + FAC', 0xE97F: 'FAC = {m} * FAC',
    0xE982: 'FAC = ARG * FAC', 0xEA66: 'FAC = {m} / FAC', 0xEA69: 'FAC = ARG / FAC',
    0xEA39: 'FAC *= 10', 0xEA55: 'FAC /= 10', 0xEAF9: 'FAC = {m}', 0xEAF9 + 0: 'FAC = {m}',
    0xE9E3: 'ARG = {m}', 0xEB1E: '[$98] = FAC', 0xEB21: '[$93] = FAC',
    0xEB27: '[(X,Y)] = FAC', 0xEB2B: '[(X,Y)] = FAC', 0xEB53: 'FAC = ARG', 0xEB63: 'ARG = FAC (rounded)',
    0xEB66: 'ARG = FAC', 0xEB82: 'A = SIGN(FAC)', 0xEB90: 'FAC = SGN(FAC)', 0xEB93: 'FAC = A (signed)',
    0xEBAF: 'FAC = ABS(FAC)', 0xEBB2: 'A = CMP(FAC, {m})  ; 0 =, 1 >, FF <', 0xEBF2: 'QINT(FAC)',
    0xEC23: 'FAC = INT(FAC)', 0xE10C: '$A0:$A1 = INT16(FAC)', 0xE2F2: 'FAC = A:Y (signed 16)',
    0xE301: 'FAC = Y (unsigned)', 0xEE8D: 'FAC = SQR(FAC)', 0xEE97: 'FAC = ARG ^ FAC',
    0xEED0: 'FAC = -FAC', 0xEF09: 'FAC = EXP(FAC)', 0xE941: 'FAC = LOG(FAC)',
    0xEFEA: 'FAC = COS(FAC)', 0xEFF1: 'FAC = SIN(FAC)', 0xF03A: 'FAC = TAN(FAC)',
    0xF09E: 'FAC = ATN(FAC)', 0xEFAE: 'FAC = RND', 0x0321: 'FAC = RND (SMALLDOS)',
}


def fp(b):
    """Applesoft 5-byte float."""
    if len(b) < 5 or b[0] == 0:
        return 0.0
    mant = ((b[1] | 0x80) << 24) | (b[2] << 16) | (b[3] << 8) | b[4]
    v = mant / 2 ** 32 * 2 ** (b[0] - 128)
    return -v if b[1] & 0x80 else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('module')
    ap.add_argument('--org', type=lambda v: int(v, 0), default=0x5800)
    ap.add_argument('--ram', default='build/game.bin')
    a = ap.parse_args()
    code = open(a.module, 'rb').read()
    ram = bytearray(open(a.ram, 'rb').read()).ljust(0x10000, b'\0')
    rom = open('../dev/tools/a2shot/roms/apple2p.rom', 'rb').read()
    ram[0x10000 - len(rom):] = rom
    ram[a.org:a.org + len(code)] = code
    s = a.module[:-4] + '.s'
    lines = open(s).read().splitlines()
    out, regs = [], {}
    for line in lines:
        m = re.match(r'^(\S*:)?\s+(\w+)\s+(.*?)\s+; ([0-9A-F]{4})', line)
        if not m:
            if line.startswith('L') or line.startswith('; ---'):
                out.append(line.split(';')[0].rstrip())
            continue
        label, op, arg, addr = m.groups()
        lab = (label or '').ljust(8)
        if op in ('lda', 'ldy', 'ldx') and arg.startswith('#$'):
            regs[op[2]] = int(arg[2:], 16)
        elif op in ('lda', 'ldy', 'ldx'):
            regs.pop(op[2], None)
        jm = re.match(r'L([0-9A-F]{4})$', arg)
        if op in ('jsr', 'jmp') and jm and int(jm.group(1), 16) in ROM:
            r = int(jm.group(1), 16)
            ma = (regs.get('y', 0) << 8) | regs.get('a', 0) if 'a' in regs and 'y' in regs else None
            if ma is not None:
                val = fp(ram[ma:ma + 5])
                mtxt = f'[${ma:04X}]({val:.6g})'
            else:
                mtxt = '[A,Y]'
            txt = ROM[r].format(m=mtxt)
            if r in (0xEB27, 0xEB2B) and 'x' in regs and 'y' in regs:
                txt = f'[${(regs["y"] << 8) | regs["x"]:04X}] = FAC'
            out.append(f'{addr} {lab}    {txt}')
            regs.clear()
            continue
        out.append(f'{addr} {lab}{op} {arg}')
        if op in ('jsr', 'jmp', 'rts') or label:
            regs.clear()
    print('\n'.join(out))


if __name__ == '__main__':
    main()
