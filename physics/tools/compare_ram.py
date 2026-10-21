# compare_ram.py -- prove the load map: compare every page the loader fills
# (image.bin, rebuilt from the disk) with a RAM dump of a running machine.
# usage: python3 -I compare_ram.py <image.bin> <ram.bin (main 64K first)>
import sys
img = open(sys.argv[1], 'rb').read()
ram = open(sys.argv[2], 'rb').read()[:65536]
for lo, hi, what in ((0x0800, 0x1D00, 'main program'), (0x2000, 0x4000, 'HGR page 1 (background, then drawn on)'),
                     (0x6000, 0x7E00, 'tables'), (0x9400, 0x9B00, 'box module'),
                     (0xA000, 0xB100, 'sprite data (copied to LC; $A000 then reused)')):
    diff = [a for a in range(lo, hi) if img[a] != ram[a]]
    print('$%04X-$%04X %-46s %5d bytes differ%s' % (lo, hi - 1, what, len(diff),
          (' e.g. ' + ' '.join('$%04X' % a for a in diff[:6])) if diff else ''))
