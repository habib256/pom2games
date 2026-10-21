"""6502 / 65C02 opcode tables and instruction decoding.

    OPS[opcode]    = (mnemonic, mode) for the documented NMOS 6502 opcodes
    C02OPS[opcode] = (mnemonic, mode) for the opcodes the 65C02 adds
    LEN[mode]      = instruction length
    decode(mem, a) -> (mnemonic, mode, length, operand) or None
    branch_target(mem, a) for a relative branch at a
    operand_text(mem, a), text(mem, a)  plain ca65-style text ($ operands)

Modes: imp acc imm zp zpx zpy izx izy rel abs abx aby ind, and on the 65C02
izp ((zp)) and iax ((abs,x)). From the PHYSICS reconstruction (physics/).
"""

LEN = {'imp':1,'acc':1,'imm':2,'zp':2,'zpx':2,'zpy':2,'izx':2,'izy':2,'rel':2,'abs':3,'abx':3,'aby':3,'ind':3,'izp':2,'iax':3}

_NMOS = """00 brk imp;01 ora izx;05 ora zp;06 asl zp;08 php imp;09 ora imm;0a asl acc;
0d ora abs;0e asl abs;10 bpl rel;11 ora izy;15 ora zpx;16 asl zpx;
18 clc imp;19 ora aby;1d ora abx;1e asl abx;20 jsr abs;21 and izx;24 bit zp;
25 and zp;26 rol zp;28 plp imp;29 and imm;2a rol acc;2c bit abs;2d and abs;
2e rol abs;30 bmi rel;31 and izy;35 and zpx;36 rol zpx;38 sec imp;
39 and aby;3d and abx;3e rol abx;40 rti imp;41 eor izx;45 eor zp;46 lsr zp;
48 pha imp;49 eor imm;4a lsr acc;4c jmp abs;4d eor abs;4e lsr abs;
50 bvc rel;51 eor izy;55 eor zpx;56 lsr zpx;58 cli imp;59 eor aby;
5d eor abx;5e lsr abx;60 rts imp;61 adc izx;65 adc zp;66 ror zp;68 pla imp;
69 adc imm;6a ror acc;6c jmp ind;6d adc abs;6e ror abs;70 bvs rel;
71 adc izy;75 adc zpx;76 ror zpx;78 sei imp;79 adc aby;7d adc abx;
7e ror abx;81 sta izx;84 sty zp;85 sta zp;86 stx zp;88 dey imp;8a txa imp;
8c sty abs;8d sta abs;8e stx abs;90 bcc rel;91 sta izy;94 sty zpx;
95 sta zpx;96 stx zpy;98 tya imp;99 sta aby;9a txs imp;9d sta abx;
a0 ldy imm;a1 lda izx;a2 ldx imm;a4 ldy zp;a5 lda zp;a6 ldx zp;a8 tay imp;
a9 lda imm;aa tax imp;ac ldy abs;ad lda abs;ae ldx abs;b0 bcs rel;
b1 lda izy;b4 ldy zpx;b5 lda zpx;b6 ldx zpy;b8 clv imp;b9 lda aby;
ba tsx imp;bc ldy abx;bd lda abx;be ldx aby;c0 cpy imm;c1 cmp izx;c4 cpy zp;
c5 cmp zp;c6 dec zp;c8 iny imp;c9 cmp imm;ca dex imp;cc cpy abs;cd cmp abs;
ce dec abs;d0 bne rel;d1 cmp izy;d5 cmp zpx;d6 dec zpx;d8 cld imp;
d9 cmp aby;dd cmp abx;de dec abx;e0 cpx imm;e1 sbc izx;e4 cpx zp;e5 sbc zp;
e6 inc zp;e8 inx imp;e9 sbc imm;ea nop imp;ec cpx abs;ed sbc abs;ee inc abs;
f0 beq rel;f1 sbc izy;f5 sbc zpx;f6 inc zpx;f8 sed imp;f9 sbc aby;
fd sbc abx;fe inc abx"""

_C02 = """04 tsb zp;0c tsb abs;12 ora izp;14 trb zp;1a inc acc;1c trb abs;32 and izp;
34 bit zpx;3a dec acc;3c bit abx;52 eor izp;5a phy imp;64 stz zp;72 adc izp;
74 stz zpx;7a ply imp;7c jmp iax;80 bra rel;89 bit imm;92 sta izp;
9c stz abs;9e stz abx;b2 lda izp;d2 cmp izp;da phx imp;f2 sbc izp;
fa plx imp"""


def _table(text):
    table = {}
    for entry in text.replace('\n', '').split(';'):
        code, mnemonic, mode = entry.split()
        table[int(code, 16)] = (mnemonic, mode)
    return table


OPS = _table(_NMOS)
C02OPS = _table(_C02)

_FORMAT = {'imp': '', 'acc': 'a', 'imm': '#${:02X}', 'zp': '${:02X}', 'zpx': '${:02X},x',
           'zpy': '${:02X},y', 'izx': '(${:02X},x)', 'izy': '(${:02X}),y', 'izp': '(${:02X})',
           'abs': '${:04X}', 'abx': '${:04X},x', 'aby': '${:04X},y', 'ind': '(${:04X})',
           'iax': '(${:04X},x)', 'rel': '${:04X}'}


def decode(mem, a, cmos=True):
    """The instruction at a, or None for an undefined opcode."""
    entry = OPS.get(mem[a]) or (C02OPS.get(mem[a]) if cmos else None)
    if entry is None:
        return None
    mnemonic, mode = entry
    length = LEN[mode]
    operand = mem[a + 1] if length == 2 else mem[a + 1] | mem[a + 2] << 8 if length == 3 else None
    return mnemonic, mode, length, operand


def branch_target(mem, a):
    return (a + 2 + ((mem[a + 1] ^ 0x80) - 0x80)) & 0xFFFF


def operand_text(mem, a):
    """The operand as text ('#$12', '$1234,x', 'a', '' ...)."""
    _, mode, _, operand = decode(mem, a)
    if mode == 'rel':
        operand = branch_target(mem, a)
    return _FORMAT[mode].format(operand)


def text(mem, a):
    return (decode(mem, a)[0] + ' ' + operand_text(mem, a)).rstrip()
