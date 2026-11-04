#!/usr/bin/env python3
"""Lazy HGR x/7 tables at every byte alignment, including independent families."""
from pathlib import Path
import subprocess
import tempfile
from test_hgr import DEV, a2test


def main():
    with tempfile.TemporaryDirectory(prefix='hgr-x7-') as directory:
        work=Path(directory)
        cfg=work/'table.cfg'
        cfg.write_text('''MEMORY {
 ZP: start=$50, size=$B0, type=rw;
 MAIN: start=$6000, size=$3000, type=rw, file=%O;
 TABLE: start=TABLE_START, size=$1000, type=rw;
}
SEGMENTS {
 ZEROPAGE: load=ZP, type=zp;
 CODE: load=MAIN, type=ro, define=yes;
 BSS: load=TABLE, type=bss, define=yes;
}
''')
        can_iie=a2test.have_a2shot('HGR x/7 tables on IIe')
        for family in ('columns','masks','phases','folded'):
            folded=family=='folded'
            entry='columns' if folded else family
            tables={'_hgr_col7':bytes(x//7 for x in range(280)),
                    '_hgr_mask7':bytes(1<<(x%7) for x in range(280)),
                    '_hgr_phase7':bytes(x%7 for x in range(280))}
            if not folded:
                symbol={'columns':'_hgr_col7','masks':'_hgr_mask7','phases':'_hgr_phase7'}[family]
                tables={symbol:tables[symbol]}
            src=work/'fixture.s'
            src.write_text(f'''.exportzp ptr1, tmp1, tmp2, tmp3
.import __BSS_RUN__, __BSS_SIZE__
.import _hgr_build_{entry}
.zeropage
ptr1: .res 2
tmp1: .res 1
tmp2: .res 1
tmp3: .res 1
remaining: .res 2
.code
start: sei
 cld
 lda #$A5
 ldx #0
fill:
 .repeat 17, page
 sta $3F00+page*256,x
 .endrepeat
 inx
 bne fill
 lda #<__BSS_RUN__
 sta ptr1
 lda #>__BSS_RUN__
 sta ptr1+1
 lda #<__BSS_SIZE__
 sta remaining
 lda #>__BSS_SIZE__
 sta remaining+1
 ldy #0
zero:
 lda #0
 sta (ptr1),y
 iny
 bne next
 inc ptr1+1
next:
 lda remaining
 bne low
 dec remaining+1
low:
 dec remaining
 lda remaining
 ora remaining+1
 bne zero
cold_start:
 jsr _hgr_build_{entry}
cold_done:
 nop
 jsr _hgr_build_{entry}
warm_done:
 jmp warm_done
fixture_end:
.export start, cold_start, cold_done, warm_done, fixture_end
''')
            wrapper=work/'fixture.o'; kernel=work/'kernel.o'
            subprocess.run(['ca65','-o',str(wrapper),str(src)],check=True)
            subprocess.run(['ca65','-D',f'HGRC_X7_FOLDED={int(folded)}','-o',str(kernel),
                            str(DEV/'lib/hgrc'/f'hgr_{entry}.s')],check=True)
            costs=[]
            for alignment in range(256):
                binary, labels=work/'table.bin',work/'table.lbl'
                subprocess.run(['ld65','-C',str(cfg),'-D',f'TABLE_START={0x4000+alignment}',
                                '-Ln',str(labels),'-o',str(binary),str(wrapper),str(kernel)],check=True)
                L=a2test.labels(labels)
                begin=L['__BSS_RUN__']; end=begin+L['__BSS_SIZE__']
                probe=L[next(iter(tables))]+127
                steps=a2test.bin_steps(binary)+[L.until('cold_start'),L.until('cold_done')]
                steps += [L.peek(name,280) for name in tables]
                steps += [f'peek:{begin-1:04X}:1',f'peek:{end:04X}:1',f'poke:{probe:04X}:E7',
                          L.until('warm_done'),f'peek:{probe:04X}:1']
                for iie in (False,True) if can_iie and alignment in (0,1,127,128,231,232,255) else (False,):
                    disk=a2test.build_disk(work,'TEST',binary) if iie else None
                    result=a2test.run(disk,steps,iie=iie)
                    for name,expected in tables.items():
                        assert result.mem(L[name],280)==expected, (family,alignment,iie,name)
                    assert result.mem(begin-1,1)==b'\xA5' and result.mem(end,1)==b'\xA5', (family,alignment,'guards')
                    assert result.mem(probe,1)==b'\xE7', (family,alignment,'warm guard')
                    if not iie:
                        costs.append(result.cycles[1]-result.cycles[0])
                        assert result.cycles[2]-result.cycles[1]-2 <= 20, (family,'warm work')
                if folded:
                    assert L['_hgr_build_columns']==L['_hgr_build_masks']==L['_hgr_build_phases']
            size=L['__CODE_SIZE__']-(L['fixture_end']-L['start'])
            print(f'HGR {family}: all 280 values at 256 alignments, guards and warm no-rebuild; '
                  f'{size} code bytes, {min(costs)}..{max(costs)} cold cycles; IIe boundary alignments checked when available.')


if __name__=='__main__':
    main()
