"""Write a ca65 include of constants and tables from a Python model.

    emit_inc(path, consts, tables, header=[...])

consts: (name, value) -> `NAME = $XXXX` (name padded to 18), or
        (name, value, 'dec') -> `NAME = value`.
tables: a line of text (a comment, a directive) as it is, or
        (label, values) -> `label:  .byte v, v, ...` (label + ':' padded to 8),
        (label, values, '.word') for words.
        A value is written as given when it is a string ('<9216', '>9216',
        '<-62': see lo(), hi(), sb()), with str() otherwise.
The file is written only when its text changed (make does not rebuild what
depends on it for nothing). -> True if it was written.
"""
from pathlib import Path


def lo(values):
    return [f'<{v}' for v in values]


def hi(values):
    return [f'>{v}' for v in values]


def sb(values):
    """Signed bytes: '<v' (ca65 takes the low byte of a negative value)."""
    return [f'<{v}' for v in values]


def const_line(name, value, fmt='hex', width=18):
    if fmt == 'dec':
        return f'{name:{width}} = {value}'
    return f'{name:{width}} = ${value:04X}'


def table_line(label, values, directive='.byte'):
    return f'{label + ":":<8} {directive} ' + ', '.join(v if isinstance(v, str) else str(v) for v in values)


def inc_text(consts, tables, header=(), segment='RODATA', end_segment='CODE'):
    out = list(header)
    for c in consts:
        out.append(const_line(*c))
    if tables:
        out.append('')
        if segment:
            out.append(f'.segment "{segment}"')
        for t in tables:
            out.append(t if isinstance(t, str) else table_line(*t))
        if end_segment:
            out.append(f'.segment "{end_segment}"')
    return '\n'.join(out) + '\n'


def write_if_changed(path, text):
    path = Path(path)
    if path.exists() and path.read_text() == text:
        return False
    path.write_text(text)
    return True


def emit_inc(path, consts, tables, header=(), segment='RODATA', end_segment='CODE'):
    return write_if_changed(path, inc_text(consts, tables, header, segment, end_segment))
