#!/usr/bin/env python3
"""dev/tools/a2test.py's pure-Python helpers: keys, type_line and Checker
(no emulator needed)."""
import contextlib
import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import a2test  # noqa: E402


def captured(fn):
    out = io.StringIO()
    code = None
    with contextlib.redirect_stdout(out):
        try:
            fn()
        except SystemExit as e:
            code = e.code
    return out.getvalue(), code


def main():
    assert a2test.keys('AB') == ['key:A', 'wait:3', 'key:B', 'wait:3']
    assert a2test.keys(['\\r', '\x1b'], 30) == ['key:\\r', 'wait:30', 'key:\x1b', 'wait:30']
    assert a2test.keys('') == []
    assert a2test.type_line('LOOK R') == ['key:LOOK R', 'press:\\r', 'wait:1']
    assert a2test.type_line('V', ret=False, wait=0) == ['key:V']

    c = a2test.Checker('T')
    out, code = captured(lambda: (c.check('a', True, 'hidden'), c.check('b', 1 == 2, [1, 2]),
                                  c.check('z', False, 0), c.fail('c'), c.done()))
    assert out == '  a: OK\n  b: FAIL [1, 2]\n  z: FAIL 0\n  c: FAIL\nT: FAIL 3/4: b; z; c\n', out
    assert code == 1 and c.fails == ['b', 'z', 'c']

    c = a2test.Checker(style='column', width=6, prefix='XL ')
    out, code = captured(lambda: (c.check('x', True), c.done()))
    assert out == '  XL x   ok\nOK\n' and code is None, (out, code)

    c = a2test.Checker(limit=3)
    out, _ = captured(lambda: c.check('long', False, 'abcdef'))
    assert out == '  long: FAIL abc\n', out

    c = a2test.Checker(strict=True)
    try:
        captured(lambda: c.check('s', False, 'why'))
    except AssertionError as e:
        assert str(e) == 's why', e
    else:
        raise AssertionError('strict did not raise')
    print('a2test keys, type_line, Checker: OK')


if __name__ == '__main__':
    main()
