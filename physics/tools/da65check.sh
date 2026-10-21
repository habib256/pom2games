#!/bin/sh
# da65check.sh -- independent cross-check: disassemble each code segment with
# da65 driven by an info file built from the same tracer/annotations, then
# reassemble that output and compare it with the disk bytes.
set -e
T=$(cd "$(dirname "$0")" && pwd)
W=${1:-work}
cd "$W"
for seg in 0800:1D00 9400:9B00; do
  lo=${seg%:*}; hi=${seg#*:}
  python3 -I -B -c "import sys;d=open('image.bin','rb').read();open('img$lo.bin','wb').write(d[0x$lo:0x$hi])"
  python3 -I -B "$T/mkinfo.py" "$T" image.bin $lo $hi da65_$lo.info
  da65 -i da65_$lo.info img$lo.bin -o da65_$lo.s
  ca65 da65_$lo.s -o da65_$lo.o
  ld65 -t none -S 0x$lo -o da65_$lo.bin da65_$lo.o
  cmp da65_$lo.bin img$lo.bin && echo "da65 \$$lo-\$$hi: reassembles identical"
done
