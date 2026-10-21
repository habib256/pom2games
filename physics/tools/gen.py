# gen.py -- turn the PHYSICS memory image + annotations into ca65 source.
#
# usage: python3 -I gen.py <tools_dir> <image.bin> <boot_9000.bin> <outdir>
#
# The tracer (dev/tools/re6502) decides code vs data; annotations.py supplies the
# names, comments and data-table layouts.  The output is meant to be read by
# humans; the build then proves it reassembles to the original bytes.
import sys, os
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'dev', 'tools'))
from re6502.trace import trace
from re6502.opcodes import OPS, C02OPS
import annotations as A

img = bytearray(open(sys.argv[2], 'rb').read())
boot = open(sys.argv[3], 'rb').read()
outdir = sys.argv[4]

# The boot image lives at $9000-$93FF, but its first $25 bytes execute at
# $0801-$0824 before the copy.  Build a combined 64K view for tracing/labels.
view = bytearray(img)
view[0x9000:0x9400] = boot
view[0xD000:0xE100] = img[0xA000:0xB100]   # LC data runs at $D000
os.makedirs(os.path.join(outdir, 'data'), exist_ok=True)
open(os.path.join(outdir, 'data', 'background.hgr'), 'wb').write(img[0x2000:0x4000])
bootlo = bytearray(65536)
bootlo[0x0800:0x0845] = boot[:0x45]

MAIN_REGIONS = [(0x800, 0x1d00), (0x9400, 0x9b00)]
code_main, tg_main, pr = trace(view, [0x800], MAIN_REGIONS)
assert not pr, pr
code_b1, tg_b1, pr1 = trace(bootlo, [0x801], [(0x801, 0x845)])
code_b2, tg_b2, pr2 = trace(view, [0x9045], [(0x9045, 0x9230), (0x928E, 0x9351)])
targets = set(tg_main) | set(tg_b2) | set(tg_b1)

def make_labels(base, tg, codes):
    L = dict(base)
    for t in tg:
        if t not in L and any(t in c for c in codes):
            L[t] = 'L%04X' % t
    return L
LABELS_MAIN = make_labels(A.LABELS_MAIN, tg_main, [code_main])
LABELS_BOOT = make_labels(A.LABELS_BOOT, set(tg_b1) | set(tg_b2), [code_b1, code_b2])
LABELS = LABELS_MAIN

# map every SMC operand byte to (instruction address, offset)
SMC_AT = {}
for opaddr, name in A.SMC_DEF.items():
    SMC_AT[opaddr] = name
    SMC_AT.setdefault(opaddr + 1, name + '+1')
for opaddr, name in A.SMC_DEF.items():
    SMC_AT[opaddr] = name

# data tables: (start, end, label) used to symbolise abs,X / abs,Y operands
TABLES_MAIN = sorted([t for t in A.TABLE_SYMS if t[2] != 'load_table'], key=lambda t: t[0])
TABLES_BOOT = [t for t in A.TABLE_SYMS if t[2] == 'load_table']
TABLES = TABLES_MAIN

def sym_abs(v, mode, at):
    """symbolic text for an absolute operand value v"""
    if v in SMC_AT:
        return SMC_AT[v]
    if v in A.HW:
        return A.HW[v]
    if v in LABELS:
        return LABELS[v]
    best = None
    for s, e, name in TABLES:
        if s <= v < e:
            best = (s, name)
    if best:
        s, name = best
        return name if v == s else '%s+$%02X' % (name, v - s)
    if v < 0x100:
        return ('' if mode == 'ind' else 'a:') + sym_zp(v)
    return '$%04X' % v

def sym_zp(v):
    if v in A.ZP:
        return A.ZP[v]
    for k in (1, 2, 3):           # hi / later byte of a multi-byte variable
        if v - k in A.ZP:
            return '%s+%d' % (A.ZP[v - k], k)
    return '$%02X' % v

def fmt_ins(mem, a, L):
    o = mem[a]
    mn, mo = OPS.get(o) or C02OPS[o]
    if L == 1:
        return mn + (' a' if mo == 'acc' else '')
    v = mem[a + 1] if L == 2 else mem[a + 1] | mem[a + 2] << 8
    if a in A.OPOV:
        return mn.ljust(5) + A.OPOV[a]
    if mo == 'imm':
        return '%-5s#$%02X' % (mn, v)
    if mo == 'rel':
        t = a + 2 + ((v ^ 0x80) - 0x80)
        return '%-5s%s' % (mn, LABELS.get(t, '$%04X' % t))
    if mo in ('zp', 'zpx', 'zpy', 'izx', 'izy'):
        s = sym_zp(v)
        return mn.ljust(5) + {'zp': '%s', 'zpx': '%s,x', 'zpy': '%s,y',
                              'izx': '(%s,x)', 'izy': '(%s),y'}[mo] % s
    s = sym_abs(v, mo, a)
    if mn in ('jsr', 'jmp') and mo == 'abs':
        s = LABELS.get(v, A.HW.get(v, '$%04X' % v))
    return mn.ljust(5) + {'abs': '%s', 'abx': '%s,x', 'aby': '%s,y',
                          'ind': '(%s)'}[mo] % s

def header(a, out):
    if a in A.HDR:
        out.append('')
        out.append(';' + '-' * 75)
        for line in A.HDR[a].strip('\n').split('\n'):
            out.append(('; ' + line).rstrip())
        out.append(';' + '-' * 75)

def emit_data(mem, a, e, out, per=8):
    first = a
    while a < e:
        if a != first and a in LABELS:
            out.append('%s:' % LABELS[a])
        n = min(per, e - a)
        # break the line at labels
        for k in range(1, n):
            if a + k in LABELS or a + k in A.HDR:
                n = k
                break
        out.append('        .byte   ' + ','.join('$%02X' % mem[a + i] for i in range(n)))
        a += n

def emit_range(mem, code, lo, hi, out):
    """emit lo..hi of mem; code dict says where instructions start"""
    data_specs = {s: (s, e, kind, arg) for (s, e, kind, arg) in A.DATA if lo <= s < hi}
    a = lo
    while a < hi:
        header(a, out)
        if a in A.PRE:
            out.extend(A.PRE[a].strip('\n').split('\n'))
        if a in LABELS and not (a in data_specs and data_specs[a][2] == 'gen'
                                and LABELS[a] + ':' in data_specs[a][3]):
            out.append('%s:' % LABELS[a])
        if a in data_specs:
            s, e, kind, arg = data_specs[a]
            if kind == 'bytes':
                emit_data(mem, s, e, out, arg or 8)
            elif kind == 'text':      # high-bit ASCII via ca65 charmap trick
                out.extend(arg)
            elif kind == 'gen':
                out.extend(arg.strip('\n').split('\n'))
            elif kind == 'incbin':
                out.append('        .incbin "%s"' % arg)
            elif kind == 'ptrs':          # lo table then hi table
                n, lab, labaddr = arg
                ptrs = [mem[s + i] | mem[s + n + i] << 8 for i in range(n)]
                assert e == s + 2 * n
                for half, op in (('lo', '<'), ('hi', '>')):
                    if half == 'hi':
                        out.append('%s:' % LABELS[s + n])
                    for i in range(0, n, 4):
                        out.append('        .byte   ' + ', '.join(
                            '%s(%s+$%03X)' % (op, lab, p - labaddr) for p in ptrs[i:i + 4]))
            elif kind == 'res0':
                assert not any(mem[s:e]), hex(s)
                out.append('        .res    $%X, $00' % (e - s))
            a = e
            continue
        if a in code:
            L = code[a]
            # SMC operand labels live inside this instruction
            pre = []
            for k in range(1, L):
                if a + k in A.SMC_DEF:
                    pre.append('%s := * + %d' % (A.SMC_DEF[a + k], k))
            out.extend(pre)
            text = '        ' + fmt_ins(mem, a, L)
            c = A.CMT.get(a)
            if c:
                text = text.ljust(40) + '; ' + c
            out.append(text)
            a += L
        else:
            # stray data byte(s) not covered by a DATA spec
            e = a + 1
            while e < hi and e not in code and e not in LABELS and e not in data_specs:
                e += 1
            emit_data(mem, a, e, out)
            a = e

def write(name, lines):
    with open(os.path.join(outdir, name), 'w') as f:
        f.write('\n'.join(lines) + '\n')

for fname, spec in A.FILES.items():
    A.ZP = spec['zp']
    for k in ('HDR', 'CMT', 'PRE', 'OPOV', 'DATA'):
        setattr(A, k, getattr(A, k + ('_BOOT' if spec.get('boot') else '_MAIN')))
    LABELS = LABELS_BOOT if spec.get('boot') else LABELS_MAIN
    TABLES = TABLES_BOOT if spec.get('boot') else TABLES_MAIN
    codes = [code_b1, code_b2] if spec.get('boot') else [code_main]
    for k in A.OPOV:
        assert any(k in c for c in codes), 'OPOV not at an instruction: %04X' % k
    out = list(spec['head'].strip('\n').split('\n'))
    for item in spec['parts']:
        if isinstance(item, str):
            out.extend(item.strip('\n').split('\n'))
            continue
        which, lo, hi = item
        mem = {'main': view, 'boot1': bootlo, 'boot2': view}[which]
        code = {'main': code_main, 'boot1': code_b1, 'boot2': code_b2}[which]
        emit_range(mem, code, lo, hi, out)
    write(fname, out)

# list of named-but-unused labels / unnamed targets, for the curator
unnamed = sorted(a for a, n in LABELS_MAIN.items() if n.startswith('L') and n[1:].isalnum() and len(n) == 5)
with open(os.path.join(outdir, '..', 'work', 'unnamed_targets.txt'), 'w') as f:
    f.write('\n'.join('%04X' % a for a in unnamed))

# ---------------------------------------------------------------- includes
def equ_file(name, title, items):
    lines = ['; %s -- %s' % (name, title), '; Generated by tools/gen.py.', '']
    for addr, sym, doc in items:
        lines.append(('%-14s = $%02X' % (sym, addr) if addr < 0x100 else
                      '%-14s = $%04X' % (sym, addr)).ljust(32) + ('; ' + doc if doc else ''))
    write(name, lines)

equ_file('zp_boot.inc', 'zero page used by the boot loader',
         [(a, n, A.ZPDOC_BOOT.get(a, '')) for a, n in sorted(A.ZP_BOOT.items())])
equ_file('zp_main.inc', 'zero page used by the main program',
         [(a, n, A.ZPDOC_MAIN.get(a, '')) for a, n in sorted(A.ZP_MAIN.items())] +
         [(s, n, '%d entries' % (e - s)) for s, e, n in TABLES_MAIN if s < 0x400])
HWDOC = {
    'KBD': 'keyboard data, bit 7 = key waiting', 'KBDSTRB': 'clear keyboard strobe',
    'RDVBLBAR': '//e: bit 7 = 0 during vertical blank (//c: VBL interrupt flag!)',
    'TXTCLR': 'graphics', 'MIXCLR': 'full screen', 'LOWSCR': 'display page 1',
    'HISCR': 'display page 2', 'HIRES': 'hi-res', 'LCRAM1RW': 'LC bank 1, read RAM / write RAM (access twice)',
    'RAMWRTOFF': 'write main 48K', 'RAMWRTON': 'write aux 48K', 'WAIT': 'monitor delay routine',
    'PHASE0OFF': '+slot*16+phase*2', 'PHASE0ON': '+slot*16+phase*2', 'MOTOROFF': '+slot*16',
    'Q6L': '+slot*16: read data latch',
}
write('hw.inc', ['; hw.inc -- Apple II soft switches and ROM entry points', '; Generated by tools/gen.py.', ''] +
      [('%-10s = $%04X' % (n, a)).ljust(24) + '; ' + HWDOC[n] for a, n in sorted(A.HW.items())])
