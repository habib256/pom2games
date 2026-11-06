#!/usr/bin/env python3

"""Tile restore oracle: exact ordered stores, public pixels, bank and IRQ guards.

Default covers 1,828 repeated calls: every byte page/column/row/width/height,
independent pointer low bytes, count boundaries, clipping, nulls and invalid IDs.
Reloads the original CODE every third call. Guards both entire main HGR pages,
both auxiliary pages, maps, tiles, context, page state and software-stack cleanup.

--irq adds real slot-4 VIA interrupts and alternates the caller's I flag. a2shot
logs a prospective STA before core.step(); a pending IRQ can consume that step
instead, producing a deferred unchanged sample before RTI executes the real STA.
Before EACH call, outside storewatch and before starting the VIA, prefill every
geometrically targeted byte with the complement of its intended source byte.
The IRQ handler deliberately sets carry before RTI to exercise status recovery.
Each legal target occurs exactly once in the tile order, so real STAs must change
memory. Filter only samples whose post-byte differs from A, requiring unchanged
memory and I=0. A real duplicate leaves post=A, remains visible and fails. Guards
and bank/opcode/PC checks apply before filtering; the report counts all filters.

--negative proves this filter rejects a deliberately duplicated executed STA,
with I=1 so IRQ deferral is impossible. --reference REV uses the old kernel from
git. --bench --out FILE records the 19 canonical tile scenes and environment.
"""

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from pathlib import Path
import test_hgr
from test_hgr import ROOT, DEV, build, a2test, offset
from test_dhgr_spr import STORE

def cases():
    out = [(1, 0, 0, 40, 24, 256, 0, 0), (2, 0, 0, 40, 24, 8, 127, 0)]
    for value in range(256):
        for page in (1, 2):
            out.append((page, value * 13 % 40, value * 7 % 24, 1 + (value & 3), 1 + (value >> 2 & 3), 256, value, 0))
    for axis in range(5):
        for value in range(256):
            args = [1, 3, 5, 4, 3]
            args[axis] = value
            out.append((*args, 8, value, 0))
    for count in (0, 1, 2, 3, 8, 127, 128, 255, 256, 257, 511, 512, 65535):
        for flags in (0, 8):
            out.append((2, 38, 22, 255, 255, count, 129, flags))
    for flags in (1, 2, 4):
        out.append((1, 0, 0, 40, 24, 256, 17, flags))
    out += [(1, 1, 2, 1, 1, 8, 19, 0), (3, 0, 0, 2, 2, 256, 32, 0), (2, 37, 21, 3, 3, 256, 255, 0), (1, 0, 0, 2, 2, 8, 4, 8), (1, 0, 0, 1, 1, 8, 65, 0)]
    return out

C='''#include "hgr.h"
#include <string.h>
extern unsigned char hgr_base,hgr_draw_page2;
void ready(void);void started(void);void finished(void);void resume(void);
void clock_start(void);void clock_stop(void);void tint_aux(void);
#pragma bss-name(push,"LOWBSS")
unsigned char maps[1216],tiles[2304];
#pragma bss-name(pop)
struct {unsigned char before;hgr_tilemap_t ctx;unsigned char after;} box,copy;
unsigned char inputs[10],result[4],*map,*tile;unsigned i;unsigned count,at,bx,by,bp,bw,bh,yy,address;
int main(void){
 hgr_init();tint_aux();for(i=0;i<2304;++i)tiles[i]=(unsigned char)((i/8u)*61u+(i&7u)*23u+7u);
 for(;;){ready();
  for(i=0;i<1216;++i)maps[i]=(unsigned char)(i*37u+13u);
  map=maps+(((unsigned)inputs[7]*73u-(unsigned)maps)&255u);
  tile=tiles+(((unsigned)inputs[7]-(unsigned)tiles)&255u);
  count=inputs[5]+((unsigned)inputs[6]<<8);
  if(count>0&&count<256)for(i=0;i<960;++i)map[i]=(unsigned char)(i%count);
  if((inputs[8]&8)&&inputs[1]<40&&inputs[2]<24&&inputs[3]&&inputs[4]){
   at=(unsigned)(inputs[2]+(inputs[4]<24-inputs[2]?inputs[4]:24-inputs[2])-1u)*40u+
      inputs[1]+(inputs[3]<40-inputs[1]?inputs[3]:40-inputs[1])-1u;
   map[at]=(unsigned char)count;
  }
  box.before=0xa5;box.after=0x5a;box.ctx.map=inputs[8]&2?0:map;box.ctx.tiles=inputs[8]&4?0:tile;box.ctx.count=count;copy=box;
  hgr_set_draw_page(1);hgr_clear(0xaa);hgr_set_draw_page(2);hgr_clear(0x55);hgr_show_page();
#ifdef TILE_IRQ
  /* Every expected store changes its byte. This distinguishes a real STA
   * from a2shot's prospective record when core.step services an IRQ first. */
  if((inputs[0]==1||inputs[0]==2)&&inputs[1]<40&&inputs[2]<24&&inputs[3]&&inputs[4]){
   bw=inputs[3]<40-inputs[1]?inputs[3]:40-inputs[1];bh=inputs[4]<24-inputs[2]?inputs[4]:24-inputs[2];
   for(by=inputs[2];by<inputs[2]+bh;++by)for(bx=inputs[1];bx<inputs[1]+bw;++bx)for(bp=0;bp<8;++bp){
    yy=by*8u+bp;address=(inputs[0]==1?0x2000u:0x4000u)+((yy&7u)<<10)+(((yy>>3)&7u)<<7)+(yy>>6)*40u+bx;
    *(unsigned char*)address=(unsigned char)~tile[(unsigned)map[by*40u+bx]*8u+bp];
   }
  }
#endif
#ifdef TILE_IRQ
  clock_start();
#endif
  if(inputs[9]){asm("sei");}else{asm("cli");}
  started();result[0]=hgr_tile_restore(inputs[8]&1?0:&box.ctx,inputs[0],inputs[1],inputs[2],inputs[3],inputs[4]);
  asm("stx _result+1");asm("php");asm("pla");asm("sta _result+2");
  result[3]=memcmp(&box,&copy,sizeof(box))==0&&hgr_get_draw_page()==2&&hgr_base==0x40&&hgr_draw_page2==1&&(*(volatile unsigned char*)0xc01c&128);
  finished();
#ifdef TILE_IRQ
  clock_stop();
#endif
  asm("cli");resume();
 }
 return 0;
}'''

ASM='''.export _ready,_started,_finished,_resume,_clock_start,_clock_stop,_irq_ticks,_tint_aux
.importzp sp,ptr1
.bss
saved:.res 2
old_vector:.res 2
old_status:.res 1
_irq_ticks:.res 2
.code
_tint_aux:
 php
 sei
 lda #0
 sta ptr1
 lda #$20
 sta ptr1+1
 sta $c005
 ldy #0
@fill:
 lda #$69
 sta (ptr1),y
 iny
 bne @fill
 inc ptr1+1
 lda ptr1+1
 cmp #$60
 bne @fill
 sta $c004
 plp
 rts
_ready:rts
_resume:rts
_started:lda sp
 sta saved
 lda sp+1
 sta saved+1
 rts
_finished:lda sp
 cmp saved
 bne bad
 lda sp+1
 cmp saved+1
 bne bad
 rts
bad:jmp bad
_clock_start:
 php
 pla
 sta old_status
 sei
 lda $03fe
 sta old_vector
 lda $03ff
 sta old_vector+1
 lda #<handler
 sta $03fe
 lda #>handler
 sta $03ff
 lda #0
 sta _irq_ticks
 sta _irq_ticks+1
 lda #$7f
 sta $c40e
 lda #$40
 sta $c40b
 lda #$fe
 sta $c404
 lda #1
 sta $c405
 lda #$c0
 sta $c40e
 cli
 rts
_clock_stop:
 sei
 lda #$7f
 sta $c40e
 lda $c404
 lda old_vector
 sta $03fe
 lda old_vector+1
 sta $03ff
 lda old_status
 pha
 plp
 rts
handler:
 pha
 txa
 pha
 tya
 pha
 lda $c404
 inc _irq_ticks
 bne :+
 inc _irq_ticks+1
:pla
 tay
 pla
 tax
 pla
 sec                         ; RTI must recover the interrupted carry
 rti
'''

def run_oracle(source, irq=False, limit=None, masked=False):
    args = SimpleNamespace(source=source, irq=irq, limit=limit)
    with tempfile.TemporaryDirectory(prefix='hgr-tile-rows-') as directory:
        w = Path(directory)
        src = w / 'fixture.c'
        src.write_text(C)
        probe = w / 'probe.s'
        probe.write_text(ASM)
        original = test_hgr.compile_source

        def compile(member, obj, flags):
            return original(args.source if Path(member).name == 'hgr_tile_restore.s' else member, obj, flags)
        test_hgr.compile_source = compile
        try:
            disk = build(w, src, extra_sources=[probe], cflags=['-DTILE_IRQ=1'] if args.irq else ())
        finally:
            test_hgr.compile_source = original
        labels = a2test.labels(w / 'test.lbl')
        text = (w / 'test.map').read_text()
        section = text.split('hgr_tile_restore.o):')[1].split('.o):')[0]
        base = int(re.search('(?m)^CODE\\s+([0-9A-F]+)', text.split('Segment list:')[1])[1], 16)
        off, size = [int(v, 16) for v in re.search('CODE\\s+Offs=([0-9A-F]+)\\s+Size=([0-9A-F]+)', section).groups()]
        address = base + off
        window = w / 'window.bin'
        window.write_bytes((w / 'test.bin').read_bytes()[address - 24576:address - 24576 + size])
        assert address == labels['_hgr_tile_restore']
        ops = cases()
        ops = ops[:args.limit] if args.limit else ops
        total = 0
        irqtotal = 0
        deferred = 0
        for first in range(0, len(ops), 32):
            chunk = ops[first:first + 32]
            steps = []
            for j, op in enumerate(chunk):
                page, col, row, width, height, count, align, flags = op
                serial = first + j
                irq_state = 1 if masked else serial & 1
                values = bytes((page, col, row, width, height, count & 255, count >> 8, align, flags, irq_state))
                path = w / f'input{j}.bin'
                path.write_bytes(values)
                steps += [labels.until('_ready'), f"load:{path}@{labels['_inputs']:04X}", labels.until('_started')]
                if serial % 3 == 0:
                    steps.append(f'load:{window}@{address:04X}')
                steps += ['storewatch:2000:5FFF', labels.until('_finished'), 'unstorewatch', labels.peek('_result', 4), labels.peek('_maps', 1216), 'peek:2000:16384', 'peek:C013:2', labels.peek('_irq_ticks', 2), 'poke:C003:0', 'peek:2000:16384', 'poke:C002:0', labels.until('_resume')]
            steps += [labels.peek('_tiles', 2304)]
            result = a2test.run(disk, steps, iie=True, mockingboard=args.irq, timeout=300)
            expected = []
            assert len(result.dumps) == len(chunk) * 6 + 1, (len(result.dumps), len(chunk))
            for j, (page, col, row, width, height, count, align, flags) in enumerate(chunk):
                serial = first + j
                irq_state = 1 if masked else serial & 1
                mapoff = align * 73 - labels['_maps'] & 255
                tileoff = align - labels['_tiles'] & 255
                maps = bytearray((i * 37 + 13 & 255 for i in range(1216)))
                if 0 < count < 256:
                    maps[mapoff:mapoff + 960] = bytes((i % count for i in range(960)))
                wclip = min(width, 40 - col)
                hclip = min(height, 24 - row)
                if flags & 8 and col < 40 and (row < 24) and width and height:
                    maps[mapoff + (row + hclip - 1) * 40 + col + wclip - 1] = count & 255
                valid = page in (1, 2) and col < 40 and (row < 24) and width and height and (1 <= count <= 256) and (not flags & 7)
                if valid:
                    valid = all((maps[mapoff + y * 40 + x] < count for y in range(row, row + hclip) for x in range(col, col + wclip)))
                screen = bytearray(bytes([170]) * 8192 + bytes([85]) * 8192)
                if args.irq and page in (1, 2) and (col < 40) and (row < 24) and width and height:
                    for y in range(row, row + hclip):
                        for x in range(col, col + wclip):
                            tileid = maps[mapoff + y * 40 + x]
                            for dy in range(8):
                                source = tileoff + tileid * 8 + dy
                                value = source // 8 * 61 + (source & 7) * 23 + 7 & 255
                                at = (page - 1) * 8192 + offset(y * 8 + dy) + x
                                screen[at] = value ^ 255
                if valid:
                    for y in range(row, row + hclip):
                        for x in range(col, col + wclip):
                            tileid = maps[mapoff + y * 40 + x]
                            for dy in range(8):
                                source = tileoff + tileid * 8 + dy
                                value = source // 8 * 61 + (source & 7) * 23 + 7 & 255
                                at = (page - 1) * 8192 + offset(y * 8 + dy) + x
                                screen[at] = value
                                expected.append((8192 + at, value, irq_state))
                state, actualmap, actual, banks, ticks, aux = result.dumps[j * 6:j * 6 + 6]
                assert state[0] == bool(valid) and state[1] == 0 and (state[2] & 4 == 4 * irq_state) and (state[3] == 1), (serial, op, 'state', state.hex())
                assert actualmap == maps, (serial, 'map changed')
                assert actual == screen, (serial, 'screen')
                assert not any((b & 128 for b in banks)), (serial, 'banks')
                assert aux == bytes([105]) * 16384, (serial, 'aux changed')
                irqtotal += int.from_bytes(ticks, 'little')
            assert result.dumps[-1] == bytes((i // 8 * 61 + (i & 7) * 23 + 7 & 255 for i in range(2304))), 'tiles changed'
            stores = []
            for line in result.out.splitlines():
                m = STORE.match(line)
                if m:
                    assert tuple((m[i] for i in (9, 10, 11))) == ('0', '0', '0'), line
                    assert address <= int(m[1], 16) < address + size, line
                    assert m[12] in ('91', '9D'), line
                    old, post = (int(v, 16) for v in line.split()[3].split('>'))
                    if args.irq and post != int(m[3], 16):
                        assert old == post and (not int(m[6], 16) & 4), line
                        deferred += 1
                        continue
                    if args.irq:
                        assert old != post, ('idempotent/duplicate store', line)
                    stores.append((int(m[2], 16), int(m[3], 16), 1 if int(m[6], 16) & 4 else 0))
            if stores != expected:
                i = next((i for i, (a, b) in enumerate(zip(stores, expected)) if a != b), min(len(stores), len(expected)))
                print('STORE DIFF', i, stores[max(0, i - 3):i + 10], expected[max(0, i - 3):i + 10], flush=True)
                (w / 'failed-trace.txt').write_text(result.out)
                raise AssertionError(('ordered stores', len(stores), len(expected), i))
            total += len(stores)
        if args.irq and (not masked):
            assert irqtotal > 0, 'no hardware IRQ ran'
        print('Tile row oracle', len(ops), 'calls', total, 'exact ordered writes; IRQs', irqtotal, 'deferred pre-store IRQ samples', deferred, '; reloads/changing pointers/pages/regions, atomic rejections, sources/context/stack/banks/PASS')
        return dict(calls=len(ops), ordered_stores=total, hardware_irqs=irqtotal, deferred_pre_store_samples=deferred, code_reloads=sum((i % 3 == 0 for i in range(len(ops)))))

KERNEL = DEV / 'lib/hgrc/hgr_tile_restore.s'

def negative_control(work):
    source = KERNEL.read_text()
    changes = [('.endrepeat\n lda hgr_fixed_rowhi,x', '.endrepeat\n sta duplicate_store+1\n lda hgr_fixed_rowhi,x'), ('.endrepeat\n lda width\n sta left\n ldx #0', '.endrepeat\n sta duplicate_store+2\n lda width\n sta left\n ldx #0'), ('.endrepeat\n inc ptr1\n bne map_advanced', '.endrepeat\nduplicate_store:\n sta $FFFF,x\n inc ptr1\n bne map_advanced')]
    for before, after in changes:
        assert source.count(before) == 1, 'negative-control template changed'
        source = source.replace(before, after)
    path = work / 'duplicate.s'
    path.write_text(source)
    try:
        run_oracle(path, irq=True, limit=2, masked=True)
    except AssertionError as error:
        assert error.args[0][0] == 'idempotent/duplicate store', error
        event = error.args[0][1]
        match = STORE.match(event)
        assert int(match[6], 16) & 4, 'negative duplicate must execute with I=1'
        print('Deliberate executed duplicate rejected after filtering:', event)
        return dict(rejected=True, event=event, irq_masked=True)
    raise AssertionError('duplicate store incorrectly accepted')

def bench(source, out):
    spec = importlib.util.spec_from_file_location('tile_bench', DEV / 'bench/run.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CASES = {}
    module.SCENES = {name: value for name, value in module.SCENES.items() if name.startswith('hgr_tile_')}
    original = test_hgr.compile_source

    def compile(member, obj, flags):
        return original(source if Path(member).name == 'hgr_tile_restore.s' else member, obj, flags)
    test_hgr.compile_source = compile
    previous = sys.argv
    try:
        sys.argv = ['run.py', '--dhgr', '--out', str(out)]
        module.main()
    finally:
        sys.argv = previous
        test_hgr.compile_source = original
    report = json.loads(out.read_text())
    report['focused_sources'] = {str(KERNEL.relative_to(ROOT)): hashlib.sha256(source.read_bytes()).hexdigest(), str(Path(__file__).resolve().relative_to(ROOT)): hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out.write_text(json.dumps(report, indent=2) + '\n')

def compiler_version():
    result = subprocess.run(['cl65', '--version'], capture_output=True, text=True, check=True)
    return (result.stdout + result.stderr).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--source', type=Path, help='substitute this kernel without modifying production')
    group.add_argument('--reference', help='read the kernel from this git revision')
    parser.add_argument('--irq', action='store_true', help='real VIA IRQs; alternate initial I flag')
    parser.add_argument('--negative', action='store_true', help='prove a real duplicated STA fails filtering')
    parser.add_argument('--limit', type=int, help='smoke-test only this many calls')
    parser.add_argument('--bench', action='store_true', help='19 canonical archive-linked tile cases')
    parser.add_argument('--out', type=Path, help='write reproducible JSON report')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-tile-reference-') as directory:
        work = Path(directory)
        source = args.source or KERNEL
        if args.reference:
            source = work / 'hgr_tile_restore.s'
            source.write_bytes(subprocess.check_output(['git', 'show', args.reference + ':dev/lib/hgrc/hgr_tile_restore.s'], cwd=ROOT))
        if args.bench:
            assert args.out, '--bench requires --out'
            bench(source, args.out)
            return
        result = run_oracle(source, args.irq, args.limit)
        if args.negative:
            result['duplicate_negative'] = negative_control(work)
        if args.out:
            spec = importlib.util.spec_from_file_location('tile_bench', DEV / 'bench/run.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            report = dict(schema=2, compiler=compiler_version(), flags='-Oirs' + (' -DTILE_IRQ=1' if args.irq else ''), results={'hgr_tile_ordered': result}, case_environments={'hgr_tile_ordered': 'iie'}, environments={'iie': module.environment(True)}, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), reference=args.reference)
            args.out.write_text(json.dumps(report, indent=2) + '\n')

if __name__ == '__main__':
    main()
