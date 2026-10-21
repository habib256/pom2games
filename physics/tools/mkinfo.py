# mkinfo.py -- emit a da65 info file for one segment from the same tracer +
# annotations, as an independent cross-check of the generator (gen.py).
# usage: python3 -I mkinfo.py <tools_dir> <image.bin> <start> <end> <out.info>
import sys, os
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'dev', 'tools'))
from re6502.trace import trace
from re6502.da65 import info
import annotations as A
img = open(sys.argv[2], 'rb').read()
lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
code, tg, _ = trace(img, [0x800], [(0x800, 0x1d00), (0x9400, 0x9b00)])
open(sys.argv[5], 'w').write(info(code, lo, hi, A.LABELS_MAIN, A.ZP_MAIN))
