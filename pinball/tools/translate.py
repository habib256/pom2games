#!/usr/bin/env python3
"""Convert the original PCS assembler syntax to ca65 without editing upstream."""
import argparse
from pathlib import Path
import re


def translate(source):
    lines = source.read_text().splitlines()
    names = {line.split()[0] for line in lines if line and not line[0].isspace() and not line.startswith('*')}
    def expr(s):
        return re.sub(r'(?<![$\w])[A-Za-z_][A-Za-z_0-9]*\b', lambda m: 'pcs_' + m[0] if m[0] in names else m[0], s)
    out = ['; Generated from ' + str(source), '.setcpu "6502"', '.segment "CODE"']
    origin = None
    constants = {}
    def value(s):
        s = re.sub(r"\$([0-9A-Fa-f]+)", r"0x\1", s)
        return eval(s, {"__builtins__": {}}, constants)
    for line in lines:
        if not line.strip() or line.startswith('*'):
            out.append('; ' + line.lstrip('*'))
            continue
        code, _, comment = line.partition(';')
        parts = code.split()
        if not parts:
            continue
        label = None
        if not line[0].isspace():
            label = parts.pop(0)
        op = parts.pop(0)
        arg = ' '.join(parts)
        if op in ('LST', 'OBJ'):
            continue
        if op == 'ORG':
            origin = value(arg)
            out.append('.org $%04X' % origin)
            continue
        prefix = 'pcs_' + label if label else ''
        if op == 'EQU':
            if label == 'PBDX':
                arg = '$6240'  # reserve $6300-$6FFF for mouse, runtime tables and graphics buffer
            if source.stem in ('RUN', 'RUN2'):
                relocated = {'PBTBLO': '$6800', 'PBTBHI': '$68C0',
                             'VLO': '$6980', 'VHI': '$6A00', 'RCN': '$6A80', 'TIME': '$6B00'}
                if label in relocated:
                    arg = relocated[label]
            out.append(prefix + ' = ' + expr(arg))
            try:
                constants[label] = value(arg)
            except (NameError, SyntaxError):
                pass
        else:
            if label:
                out.append(prefix + ':')
            if op == 'HEX':
                data = bytes.fromhex(arg.replace(',', ''))
                out.append('.byte ' + ','.join('$%02X' % b for b in data))
            elif op == 'DA':
                if source.stem == 'EDIT' and label == 'LOGO':
                    arg = '$6B80'  # $380..$7FF overlaps native mouse IRQ mailboxes
                out.append(('.byte ' + arg[0] + '(' + expr(arg[1:]) + ')' if arg.startswith(('<', '>')) else '.word ' + expr(arg)))
            elif op == 'DS':
                out.append('.res ' + expr(arg) + ', 0')
            else:
                operand = expr(arg)
                if arg.startswith(('#<', '#>')):
                    operand = arg[:2] + '(' + expr(arg[2:]) + ')'
                out.append(op.lower() + (' ' + operand if arg else ''))
        if comment:
            out[-1] += ' ;' + comment
    text = '\n'.join(out) + '\n'
    if source.stem == 'CDRAW':
        text = text.replace('pcs_GETBUTNS:\nlda $C061\nora $C062\nrts',
                            'pcs_GETBUTNS:\njmp $6303\nnop\nnop\nnop\nrts')
        for name, entry in [('DOCRSRX', '$6306'), ('DOCRSRY', '$6309')]:
            text = text.replace('pcs_' + name + ':\nlda #50\njsr $FCA8',
                                'pcs_' + name + ':\njmp ' + entry + '\nnop\nnop')
    elif source.stem == 'EDIT':
        text = text.replace('ldx pcs_PARAM+3\nlda pcs_D7,X\nsta pcs_CXD7\n'
                            'lda pcs_M7,X\nsta pcs_CXM7',
                            'jsr $6315\n.res 9, $EA')
        # Preserve all fixed entry addresses. The paddle-era delta guard
        # rejects normal absolute mouse drags across the palette boundary.
        text = text.replace('cmp #$10\nbcc *+6\ncmp #$F0\nbcc pcs_DRAGO8',
                            'jsr $6312\nbcc pcs_DRAGO8\n.res 3, $EA')
    elif source.stem == 'DISK':
        # The loader records the real controller slot as $n0. Match the
        # overlay loader instead of always using slot 6 for SAVE/LOAD.
        text = text.replace('lda #6\nsta pcs_SLOT',
                            'lda $B7C3\nlsr\nlsr\nlsr\nlsr\nsta pcs_SLOT')
        text = text.replace('pcs_MAIN:\njsr pcs_JSCTRL\njsr pcs_UPDATECRSR\nlda $C061',
                            'pcs_MAIN:\njsr pcs_JSCTRL\njsr pcs_UPDATECRSR\njsr $6303')
        text = text.replace('jsr pcs_FMGR', 'jsr $630F')
        text = text.replace('jsr pcs_DOFCMD\n; \njsr pcs_CLOSE\n; \njsr pcs_INIT',
                            'jsr pcs_READ_TABLE\n; \njsr pcs_CLOSE\n; \njsr pcs_INIT')
        # LOAD's header is read separately at $3FFC. Validate the body
        # before DOS reads any table bytes into the reduced workspace.
        text += ('\npcs_READ_TABLE:\nlda pcs_FMPL+7\ncmp #$23\nbcc pcs_TABLE_FITS\n'
                 'bne pcs_TABLE_TOO_LARGE\nlda pcs_FMPL+6\nbeq pcs_TABLE_FITS\n'
                 'pcs_TABLE_TOO_LARGE:\nlda #14\nsta pcs_FMPL+10\njmp pcs_ERROR\n'
                 'pcs_TABLE_FITS:\njmp pcs_DOFCMD\n')
        # Check every compressed byte, including indexed stores spanning a
        # page. Geometry stays below MIDBTM; scan tables can be rebuilt on
        # failure, but the resident adapter at $6300 must remain untouched.
        start = text.index('pcs_COMPRESS:')
        end = text.index('pcs_DECOMPRESS:', start)
        compression = text[start:end].replace('sta (pcs_MIDBTM),Y', 'jsr pcs_COMPRESS_PUT')
        text = text[:start] + compression + text[end:]
        text += ('\npcs_COMPRESS_PUT:\nphp\npha\ntya\nclc\nadc pcs_MIDBTM\n'
                 'lda pcs_MIDBTM+1\nadc #0\ncmp #$63\nbcs pcs_COMPRESS_FULL\n'
                 'pla\nplp\nsta (pcs_MIDBTM),Y\nrts\n'
                 'pcs_COMPRESS_FULL:\npla\nplp\npla\npla\npla\nsta pcs_HTOP\n'
                 'lda #14\nsta pcs_FMPL+10\njmp pcs_ERROR\n')
        # SAVE, LOAD and ERROR jump out of DOMENU and abandon its return
        # address. Restore the module's entry stack on every menu restart.
        text = text.replace('pcs_START:\nldy #0',
                            'pcs_START:\nldx pcs_STACKTEMP\ntxs\nldy #0')
        start = text.index('ldy #0\ntya\npcs_UNDODLG2:')
        end = text.index('bne pcs_UNDODLG2', start) + len('bne pcs_UNDODLG2')
        text = text[:start] + 'pcs_UNDODLG2:\njsr $630C\n.res 12, $EA' + text[end:]
    elif source.stem == 'BOOT2':
        start = text.index('pcs_TIME:')
        end = text.index('pcs_TIM3 =')
        text = text[:start] + ('pcs_TIME:\nlda #13\nsta pcs_SECTORCOUNT\nlda #15\nldx #12\nldy #$6F\n'
                'jsr pcs_READSECTORS\njsr $6300\npcs_TIM2 = pcs_TIME\n.res 24-(*-pcs_TIME), $EA\n') + text[end:]
    out = [text.rstrip()]
    out.extend('.export ' + 'pcs_' + name for name in sorted(names))
    return '\n'.join(out) + '\n', origin


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    text, origin = translate(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    args.output.with_suffix('.cfg').write_text('MEMORY { RAM: start = $%04X, size = $%04X, file = %%O; }\nSEGMENTS { CODE: load = RAM, type = ro; }\n' % (origin, 0x10000-origin))

if __name__ == '__main__':
    main()
