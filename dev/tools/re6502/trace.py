"""Recursive-descent code tracer: which bytes of a memory image are code.

    trace(img, entries, regions, stops=()) -> (code, targets, problems)

From each entry point, follow every path (branches both ways, JSR and JMP
targets) while it stays inside `regions` [(lo, hi), ...]. RTS / RTI / BRK,
JMP and BRA end a path; `stops` are addresses where a path ends too (code
after a call that never returns).
    code      {address: instruction length}
    targets   addresses reached by a branch, JSR or JMP (label candidates)
    problems  ('outside', pc), ('badop', pc, opcode), ('65c02', pc, mnemonic),
              ('extjsr' / 'extjmp', pc, target), ('indjmp', pc, operand)
65C02 opcodes are decoded but reported, so an NMOS program shows none.
"""
from .opcodes import OPS, C02OPS, LEN


def trace(img, entries, regions, stops=()):
    code = {}
    targets = set(entries)
    probs = []
    work = list(entries)

    def inside(a):
        return any(lo <= a < hi for lo, hi in regions)

    while work:
        pc = work.pop()
        while True:
            if pc in code:
                break
            if not inside(pc):
                probs.append(('outside', pc))
                break
            o = img[pc]
            if o in OPS:
                mn, mo = OPS[o]
            elif o in C02OPS:
                mn, mo = C02OPS[o]
                probs.append(('65c02', pc, mn))
            else:
                probs.append(('badop', pc, o))
                break
            length = LEN[mo]
            code[pc] = length
            if mo == 'rel':
                t = pc + 2 + ((img[pc + 1] ^ 0x80) - 0x80)
                targets.add(t)
                work.append(t)
                if mn == 'bra':
                    break
            if mn == 'jsr':
                t = img[pc + 1] | img[pc + 2] << 8
                targets.add(t)
                if inside(t):
                    work.append(t)
                else:
                    probs.append(('extjsr', pc, t))
            if mn == 'jmp':
                t = img[pc + 1] | img[pc + 2] << 8
                if mo == 'abs':
                    targets.add(t)
                    if inside(t):
                        work.append(t)
                    else:
                        probs.append(('extjmp', pc, t))
                else:
                    probs.append(('indjmp', pc, t))
                break
            if mn in ('rts', 'rti', 'brk'):
                break
            pc += length
            if pc in stops:
                break
    return code, targets, probs


def runs(code):
    """Contiguous code ranges [(start, end_exclusive), ...]."""
    out, start, end = [], None, None
    for a in sorted(code):
        if start is None:
            start, end = a, a + code[a]
        elif a == end:
            end = a + code[a]
        else:
            out.append((start, end))
            start, end = a, a + code[a]
    if start is not None:
        out.append((start, end))
    return out
