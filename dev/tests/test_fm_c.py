#!/usr/bin/env python3
"""lib/apple2c/apple2fm (C wrappers over lib/apple2/fm.asm) in a2run, on a
real DOS 3.3: a C program (crt0_apple2.s, apple2_hgr_c.cfg) creates a
binary file (A2_FM_CREATED), writes its BLOAD header and 300 bytes, reads
it back after a seek, gets A2_FM_ERR_END past its end, rewrites 2 bytes;
lock (delete and write refused, a2_fm_type shows it), unlock, verify; a
missing file; three files kept open through a2_fm_file, the 4th open
refused (NO BUFFER), the three closed. The arguments of every wrapper are
checked by the data (buffer, length, position, name). The disk saved
after the run is read with dos33.py; the cc65 zero page is compared before
and after: the C stack pointer must not move. Also prints the object's size."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / 'dev'
sys.path.insert(0, str(DEV / 'tools'))
import a2test  # noqa: E402
import dos33  # noqa: E402

N = 300
FIXTURE = r'''
#include <string.h>
#include "apple2fm.h"

unsigned char res[32];
unsigned char data[4 + %(N)d];
unsigned char back[4 + %(N)d + 1];
unsigned char tail;
unsigned handles[4];
unsigned char zp_before[176], zp_after[176];
static const unsigned char patch[2] = {0x11, 0x22};
static const char *const names[4] = {"A", "B", "C", "D"};

void done(void) { for (;;) ; }

int main(void)
{
    unsigned i;
    memset(res, 0xFF, sizeof res);
    for (i = 0; i < %(N)d; ++i) data[4 + i] = (unsigned char)(i ^ 0xC3);
    data[0] = 0x00; data[1] = 0x40; data[2] = %(N)d & 255; data[3] = %(N)d >> 8;
    memset(back, 0xEE, sizeof back);
    memcpy(zp_before, (void *)0x50, 176);

    res[0] = a2_fm_open("SAVE", A2_FM_BINARY);
    res[1] = a2_fm_write(data, 4 + %(N)d);
    res[2] = a2_fm_close();

    res[3] = a2_fm_open("SAVE,D1", A2_FM_TEXT);       /* exists: type kept */
    res[4] = a2_fm_type;
    res[5] = a2_fm_seek(4);
    res[6] = a2_fm_read(back + 4, %(N)d);
    res[7] = a2_fm_seek(0);
    res[8] = a2_fm_read(back, 4);
    res[9] = a2_fm_seek(600);
    res[10] = a2_fm_read(&tail, 1);                    /* END OF DATA */
    res[11] = a2_fm_seek(4 + 10);
    res[12] = a2_fm_write(patch, 2);
    res[13] = a2_fm_close();

    res[14] = a2_fm_lock("SAVE");
    res[15] = a2_fm_delete("SAVE");
    res[16] = a2_fm_open("SAVE", A2_FM_MUST_EXIST);
    res[17] = a2_fm_type;
    res[18] = a2_fm_write(patch, 2);
    res[19] = a2_fm_close();
    res[20] = a2_fm_unlock("SAVE");
    res[21] = a2_fm_verify("SAVE");
    res[22] = a2_fm_open("NONE", A2_FM_MUST_EXIST);

    for (i = 0; i < 4; ++i) {
        res[23 + i] = a2_fm_open(names[i], A2_FM_TEXT);
        handles[i] = a2_fm_file;
    }
    for (i = 0; i < 3; ++i) {
        a2_fm_file = handles[i];
        res[27 + i] = a2_fm_close();
    }
    res[30] = a2_fm_delete("C");
    memcpy(zp_after, (void *)0x50, 176);
    done();
    return 0;
}
''' % {'N': N}


def build(work):
    (work / 'fixture.c').write_text(FIXTURE)
    objects = []
    for source, flags in ((work / 'fixture.c', ['-Oirs', '-I', DEV / 'lib/apple2c']),
                          (DEV / 'cc65/crt0_apple2.s', []),
                          (DEV / 'lib/apple2c/apple2fm.s', ['--asm-include-dir', DEV / 'lib/apple2'])):
        obj = work / (source.stem + '.o')
        if source.suffix == '.c':                       # never a .s beside the source
            subprocess.run(['cl65', '-t', 'none', *flags, '-S', '-o', work / 'fixture.gen.s', source], check=True)
            source = work / 'fixture.gen.s'
        subprocess.run(['cl65', '-t', 'none', *flags, '-c', '-o', obj, source], check=True)
        objects.append(obj)
    binary = work / 'fm.bin'
    subprocess.run(['cl65', '-t', 'none', '-C', DEV / 'cc65/apple2_hgr_c.cfg', '-m', work / 'fm.map',
                    '-Ln', work / 'fm.lbl', '-o', binary, *objects], check=True)
    return a2test.labels(work / 'fm.lbl', any_name=True), binary


def module_size(work):
    """CODE / DATA / BSS bytes of apple2fm.o alone (ld65's module list)."""
    text = (work / 'fm.map').read_text()
    lines = text[text.index('apple2fm.o:'):].splitlines()[1:]
    block = '\n'.join(line for line in lines[:next((i for i, x in enumerate(lines) if not x.startswith(' ')), len(lines))])
    return {seg: int(size, 16) for seg, size in re.findall(r'(CODE|DATA|BSS|RODATA)\s+Offs=\w+\s+Size=(\w+)', block)}


def main():
    with tempfile.TemporaryDirectory(prefix='fm-c-') as tmp:
        work = Path(tmp)
        L, binary = build(work)
        disk = a2test.build_disk(work, 'FMC', binary)
        r = a2test.run(disk, ['wait:200', L.until('_done', 6000), L.peek('_res', 32), L.peek('_back', N + 5),
                              L.peek('_zp_before', 176), L.peek('_zp_after', 176), f'dsk:{work / "after.dsk"}'])
        res = list(r.mem(L['_res'], 32))
        expect = {0: 1, 1: 0, 2: 0, 3: 0, 4: 4, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 5, 11: 0, 12: 0, 13: 0,
                  14: 0, 15: 10, 16: 0, 17: 0x84, 18: 10, 19: 0, 20: 0, 21: 0, 22: 6,
                  23: 1, 24: 1, 25: 1, 26: 12, 27: 0, 28: 0, 29: 0, 30: 0}
        bad = {i: (res[i], a) for i, a in expect.items() if res[i] != a}
        assert not bad, f'step: (got, expected) {bad}'
        payload = bytes((i & 255) ^ 0xC3 for i in range(N))
        back = r.mem(L['_back'], N + 5)
        assert back[:N + 4] == bytes([0, 0x40, N & 255, N >> 8]) + payload, 'read back differs'
        assert back[N + 4] == 0xEE, 'a2_fm_read wrote past its length'
        image = (work / 'after.dsk').read_bytes()
        patched = payload[:10] + b'\x11\x22' + payload[12:]
        assert dos33.read_file(image, 'SAVE') == patched, 'SAVE on the disk differs'
        raw = b''.join(image[s:s + 256] for s in dos33.file_sectors(image, 'SAVE'))
        assert raw[N + 4:] == bytes(len(raw) - N - 4), 'bytes written past the length'
        names = [e[0] for e in dos33.catalog(image)]
        assert {'SAVE', 'A', 'B'} <= set(names) and not {'C', 'D', 'NONE'} & set(names), names
        before, after = r.mem(L['_zp_before'], 176), r.mem(L['_zp_after'], 176)
        # the cc65 runtime's scratch (ptr1-4, tmp1-4...) may differ; its C stack pointer must not
        changed = {0x50 + i for i in range(176) if before[i] != after[i]}
        assert {L['sp'], L['sp'] + 1}.isdisjoint(changed), f'C stack pointer moved: {sorted(changed)}'
        size = module_size(work)
    print(f'fm (C): open/created/type kept, seek + read, END OF DATA, rewrite, lock: delete and write refused, '
          f'unlock, verify, missing, 3 handles + NO BUFFER, disk image exact; apple2fm.o {size}')


if __name__ == '__main__':
    main()
