#!/usr/bin/env python3
"""Exercise incremental archive builds with colliding C/ASM basenames."""
import json
from pathlib import Path
import tempfile
from test_hgr import DEV, run


def main():
    with tempfile.TemporaryDirectory(prefix='hgr-build-') as directory:
        work = Path(directory)
        for name in ('first', 'second', 'third'):
            (work / name).mkdir()
        (work / 'first/same.c').write_text(
            '#ifndef OPTION\n#define OPTION 1\n#endif\nint first(void) {return OPTION;}\n')
        (work / 'second/same.c').write_text('int second(void) {return 7;}\n')
        (work / 'first/same.s').write_text(
            '.ifndef ASM_OPTION\nASM_OPTION=3\n.endif\n.export _third\n.code\n'
            '_third: lda #ASM_OPTION\nldx #0\nrts\n')
        (work / 'main.c').write_text(
            'int first(void); int second(void); int third(void);\n'
            'int main(void) {return first()+second()+third();}\n')
        sources = ' '.join(str(work / name) for name in
                           ('first/same.c', 'second/same.c', 'first/same.s'))
        mk = work / 'Makefile'
        mk.write_text(f'DEV := {DEV}\nHGRC := {DEV}/lib/hgrc\n'
                      f'HGRC_ALL_SRCS := {sources}\nHGRC_BUILD := {work}/build\n'
                      f'HGRC_LIB := {work}/build/lib.lib\n'
                      'all: $(HGRC_LIB)\n'
                      f'include {DEV}/lib/hgrc/hgrc_build.mk\n')
        command = ['make', '-s', '-f', mk]
        original_asm = (work / 'first/same.s').read_bytes()
        run(command)
        assert (work / 'first/same.s').read_bytes() == original_asm, 'C compilation overwrote ASM source'
        archive = work / 'build/lib.lib'
        config = work / 'build/config.json'
        objects = list((work / 'build').glob('*.o'))
        assert len(objects) == 3 and len({p.name for p in objects}) == 3
        stamps = {p: p.stat().st_mtime_ns for p in (*objects, archive, config)}
        run(command)
        assert stamps == {p: p.stat().st_mtime_ns for p in stamps}, 'no-op rebuilt archive'
        cobj = next(p for p in objects if 'first__same.c' in p.name)
        aobj = next(p for p in objects if 'same.s' in p.name)
        old_c, old_a = cobj.read_bytes(), aobj.read_bytes()
        binary = work / 'fixture.bin'
        link = ['cl65', '-t', 'none', '-o', binary, work / 'main.c', archive]
        run(link)
        original_binary = binary.read_bytes()
        run([*command, 'HGRC_CFLAGS=-t none -Oirs -D OPTION=2',
             'HGRC_ASMFLAGS=-t none -D ASM_OPTION=4'])
        assert cobj.read_bytes() != old_c and aobj.read_bytes() != old_a, (cobj.read_bytes()!=old_c, aobj.read_bytes()!=old_a, config.read_text())
        assert json.loads(config.read_text())['HGRC_CFLAGS'].endswith('OPTION=2')
        # Link all three members: ar65 must not replace equal source basenames.
        run(link)
        assert binary.read_bytes() != original_binary
        # Returning to defaults must invalidate objects as well.
        run(command)
        run(link)
        assert binary.read_bytes() == original_binary
    print('Archive build: distinct C/ASM members, no-op, flags and configuration rollback OK.')


if __name__ == '__main__':
    main()
