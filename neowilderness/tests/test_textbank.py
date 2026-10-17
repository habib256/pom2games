#!/usr/bin/env python3
"""Native decoder checks every source byte, including bank/dictionary boundaries."""
import subprocess
import sys
import tempfile
from pathlib import Path
from common import HERE, L, DISK, a2test
from gentextbank import items


def source_texts():
    for line in (HERE/'src/textbank.txt').read_text().splitlines():
        if not line.strip() or line.lstrip().startswith(';') or ':' not in line:
            continue
        label, data = line.split(':', 1)
        expected = []
        for value in items(data):
            if isinstance(value, str):
                assert value.startswith('<'), value
                value = L[value[1:]] & 255
            expected.append(value)
        yield label, bytes(expected)


def compiler_boundaries():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source, output = root/'texts.txt', root/'texts.inc'
        for count, text in ((1, 'Q'), (255, 'REPEATED WORDS FOR DICTIONARY')):
            source.write_text(''.join(f'text_{i}: "{text}",0\n' for i in range(count)))
            subprocess.run([sys.executable, str(HERE/'tools/gentextbank.py'), str(source), str(output)], check=True)
            generated = output.read_text()
            assert f'TB_TEXTS = {count}' in generated
            if count == 1:
                assert 'TB_WORDS = 0' in generated
            else:
                assert 'text_254 = 255' in generated
            subprocess.run(['ca65', '-t', 'none', '-o', str(root/'texts.o'), str(output)], check=True)
        source.write_text(source.read_text() + 'too_many: "EXTRA",0\n')
        rejected = subprocess.run([sys.executable, str(HERE/'tools/gentextbank.py'), str(source), str(output)], capture_output=True, text=True)
        assert rejected.returncode and 'public text IDs exhausted' in rejected.stderr
    print('  Compiler: empty dictionary, all 255 public IDs with compression, explicit rejection at 256: OK')


def main():
    compiler_boundaries()
    texts = list(source_texts())
    assert L['TB_TEXTS'] == len(texts) and L['TB_DICT'] == 256
    assert L['TB_WORDS'] == 32  # dictionary no longer shrinks with text count
    stub = L['idle']
    done = f'until:{stub+5:04X}:60000'
    with a2test.Session(DISK) as s:
        s.step(L.until('idle', 60000))
        for ident, (name, expected) in enumerate(texts, 1):
            code = bytes((0xA9, ident, 0x20, L['text_fetch'] & 255,
                          L['text_fetch'] >> 8, 0x4C, stub & 255, stub >> 8))
            for i, value in enumerate(code):
                s.step(f'poke:{stub+i:04X}:{value:02X}')
            s.step(done)
            actual = s.step(L.peek('tb_buf', len(expected))).data
            assert actual == expected, (ident, name, actual, expected)
            s.step(L.until('idle', 60000))
    print(f'  {len(texts)} native decodes = source bytes, text IDs across 128, dictionary indices >=256, embedded NUL/CR and literals: OK')


if __name__ == '__main__':
    main()
