"""Translate only the Merlin directives used by the pinned test sources.

Instructions and algorithms are preserved. ORG is replaced by linker placement;
fdraw's private scratch bytes are allocated outside cc65's scratch locations.
This is deliberately not a general Merlin assembler.
"""
import re
from pathlib import Path


def translate(path, fast=1, allocate_zp=False):
    constants = {'USE_FAST': fast, 'NOISE_ON': 0, 'overrun_check': 0}
    aliases = {}
    output = ['.segment "CODE"']
    conditions = []
    macro = False
    scope = 'root'

    def expression(s):
        s = re.sub(r'\$([0-9a-fA-F]+)', r'0x\1', s)
        for key, value in constants.items():
            s = re.sub(r'\b' + re.escape(key) + r'\b', str(value), s)
        if not re.fullmatch(r'[0-9xXa-fA-F+*() /-]+', s):
            raise ValueError('unsupported conditional: ' + s)
        try:
            return int(eval(s, {'__builtins__': {}}, {}))
        except (SyntaxError, TypeError) as exc:
            raise ValueError('unsupported expression: ' + s) from exc

    def visit(file):
        nonlocal macro, scope
        lines = Path(file).read_text().splitlines()
        cursor = 0
        while cursor < len(lines):
            raw = lines[cursor]
            cursor += 1
            if not raw.strip() or raw.startswith('*'):
                continue
            line = raw.split(';', 1)[0].rstrip()
            if not line.strip():
                continue
            if line[0].isspace():
                label = ''
                fields = line.split(None, 1)
            else:
                parts = line.split(None, 2)
                label = parts[0]
                fields = parts[1:]
            op = fields[0].lower() if fields else ''
            arg = fields[1].strip() if len(fields) > 1 else ''
            if op == 'mac':
                macro = True
                continue
            if macro:
                if op == '<<<':
                    macro = False
                continue
            if op == 'do':
                conditions.append(bool(expression(arg)) if all(conditions) else False)
                continue
            if op == 'else':
                conditions[-1] = not conditions[-1]
                continue
            if op == 'fin':
                conditions.pop()
                continue
            if not all(conditions):
                continue
            if op in ('lst', 'org', 'sav'):
                continue
            if op == 'put':
                visit(Path(file).with_name(arg + '.S'))
                continue
            if op in ('click', 'beep', 'break'):
                continue  # NOISE_ON=0
            if op in ('equ', '='):
                if label in constants:
                    arg = str(constants[label])
                if label.startswith(']'):
                    for key, value in sorted(aliases.items(), key=lambda kv: -len(kv[0])):
                        arg = arg.replace(key, value)
                    try:
                        arg = str(expression(arg))
                    except ValueError:
                        pass
                    aliases[label] = arg
                    continue
                try:
                    constants[label] = expression(arg)
                except ValueError:
                    pass
                if allocate_zp and (label == 'zptr0' or re.fullmatch(r'zloc\d+', label)):
                    output.extend(['.segment "ZEROPAGE"', label + ': .res ' + ('2' if label == 'zptr0' else '1'), '.segment "CODE"'])
                else:
                    output.append(label + ' = ' + arg)
                continue
            # Merlin local labels belong to the previous global code label.
            if label and not label.startswith((':', ']')):
                scope = label
            for key, value in sorted(aliases.items(), key=lambda kv: -len(kv[0])):
                arg = arg.replace(key, value)
            arg = re.sub(r'[:\]]([\w]+)', lambda m: scope + '__' + m[1], arg)
            if label.startswith((':', ']')):
                label = scope + '__' + label[1:]
            prefix = label + ': ' if label else ''
            if op == 'pg_align' or (op == 'ds' and arg == '\\'):
                output.append(prefix + '.align 256')
            elif op == 'ds':
                output.append(prefix + '.res ' + arg + ', 0')
            elif op == 'hex':
                output.append(prefix + '.byte ' + ','.join('$' + arg[i:i+2] for i in range(0, len(arg), 2)))
            elif op in ('dfb', 'da'):
                output.append(prefix + ('.byte ' if op == 'dfb' else '.addr ') + arg)
            elif op == 'asc':
                # The sole string in FDRAW.S ends with three hex bytes.
                match = re.fullmatch(r'("[^"]*")(.*)', arg)
                output.append(prefix + '.byte ' + match[1] + ''.join(',$' + v for v in match[2].lstrip(',').split(',') if v))
            elif op == 'lup':
                end = cursor
                while end < len(lines) and lines[end].strip() != '--^':
                    end += 1
                if end == len(lines):
                    raise ValueError('unterminated LUP')
                body = lines[cursor:end]
                lines[cursor:end+1] = body * expression(arg)
            elif op == '--^':
                raise ValueError('unexpected loop end')
            else:
                output.append(prefix + {'blt': 'bcc', 'bge': 'bcs'}.get(op, op) + (' ' + arg if arg else ''))
    visit(path)
    return '\n'.join(output) + '\n'
