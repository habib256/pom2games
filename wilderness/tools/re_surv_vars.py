#!/usr/bin/env python3
"""re_surv_vars.py: print the survival state of RAM dumps (16-bit words,
Applesoft floats and the two 25-float arrays at $4950 / $49CD)."""
import sys
sys.path.insert(0, 'tools')
from re_surv_fp import fp  # noqa: E402
W = {'BD2 food eaten?': 0x4BD2, 'BD4 water drunk?': 0x4BD4, 'BD8 energy left?': 0x4BD8,
     'BDA energy used?': 0x4BDA, 'BDC energy budget?': 0x4BDC, 'BDE goal pen.': 0x4BDE,
     'BE2 ?': 0x4BE2, 'BE6 weight': 0x4BE6, 'BF6 body?': 0x4BF6, 'C08 min ctr': 0x4C08,
     'C14 action min': 0x4C14, 'C16 goal pen.': 0x4C16, 'BC6 step min': 0x4BC6, 'BCC remain': 0x4BCC}
F = {'C20 met rate?': 0x4C20, 'C25': 0x4C25, 'C2F Hmax': 0x4C2F, 'C34 health': 0x4C34,
     'C57 hour': 0x4C57, 'C61 hours': 0x4C61, 'C70 body T': 0x4C70, 'C75': 0x4C75,
     'C7A': 0x4C7A, 'C89 year': 0x4C89}
for f in sys.argv[1:]:
    m = open(f, 'rb').read()
    s16 = lambda a: int.from_bytes(m[a:a + 2], 'little', signed=True)
    print('==', f)
    print('  ' + '  '.join(f'{k}={s16(a)}' for k, a in W.items()))
    print('  ' + '  '.join(f'{k}={fp(m[a:a + 5]):.4g}' for k, a in F.items()))
    for base, name in ((0x4950, 'A1'), (0x49CD, 'A2')):
        print(f'  {name}: ' + ' '.join(f'{i + 1}:{fp(m[base + 5 * i: base + 5 * i + 5]):.3g}' for i in range(25)))
