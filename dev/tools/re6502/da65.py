"""da65 info files from a trace: an independent disassembler as a cross-check.

    info(code, lo, hi, labels={}, zp={}, cpu='6502') -> text
One `range` per run of code / data in lo..hi (data as bytetable), a label
per entry of `labels` inside the segment and per zero-page name. Feed it
to `da65 -i`, reassemble with ca65 / ld65 and compare with the bytes.
"""


def info(code, lo, hi, labels=None, zp=None, cpu='6502'):
    out = ['global { startaddr $%04X; cpu "%s"; comments 0; };' % (lo, cpu)]
    a = lo
    while a < hi:
        e = a
        is_code = a in code
        while e < hi and ((e in code) if is_code else (e not in code)):
            e += code[e] if is_code else 1
        out.append('range { start $%04X; end $%04X; type %s; };' % (a, e - 1, 'code' if is_code else 'bytetable'))
        a = e
    for addr, name in sorted((labels or {}).items()):
        if lo <= addr < hi:
            out.append('label { name "%s"; addr $%04X; };' % (name, addr))
    for addr, name in sorted((zp or {}).items()):
        out.append('label { name "%s"; addr $%02X; };' % (name, addr))
    return '\n'.join(out) + '\n'
