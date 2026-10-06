#!/usr/bin/env python3
"""Compile with cc65 and check real 65C02 execution in POM2's IIe core.

Requires the local a2shot tool (make -C dev/tools/a2shot). Outputs stay in /tmp.
The expected color bytes come from Apple IIe Technical Note #3, table 2.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "dev"
# aux even, main even, aux odd, main odd, in LORES color-number order.
PATTERNS = [
    (0x00, 0x00, 0x00, 0x00), (0x08, 0x11, 0x22, 0x44),
    (0x11, 0x22, 0x44, 0x08), (0x19, 0x33, 0x66, 0x4C),
    (0x22, 0x44, 0x08, 0x11), (0x2A, 0x55, 0x2A, 0x55),
    (0x33, 0x66, 0x4C, 0x19), (0x3B, 0x77, 0x6E, 0x5D),
    (0x44, 0x08, 0x11, 0x22), (0x4C, 0x19, 0x33, 0x66),
    (0x55, 0x2A, 0x55, 0x2A), (0x5D, 0x3B, 0x77, 0x6E),
    (0x66, 0x4C, 0x19, 0x33), (0x6E, 0x5D, 0x3B, 0x77),
    (0x77, 0x6E, 0x5D, 0x3B), (0x7F, 0x7F, 0x7F, 0x7F),
]


def run(args, **kwargs):
    result = subprocess.run([str(a) for a in args], text=True,
                            capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def offset(y):
    return (y % 8) * 1024 + ((y // 8) % 8) * 128 + (y // 64) * 40


def pixel(banks, x, y, value):
    byte, bit = divmod(x, 7)
    bank = 1 - byte % 2  # 0 main, 1 aux
    addr = offset(y) + byte // 2
    banks[bank][addr] = (banks[bank][addr] & ~(1 << bit)) | (value << bit)


def color_pixel(banks, x, y, color):
    # Select the bits at this position from the reference uniform-color bytes.
    for bit in range(x * 4, x * 4 + 4):
        byte, shift = divmod(bit, 7)
        pixel(banks, bit, y, (PATTERNS[color][byte % 4] >> shift) & 1)


def main():
    emulator = DEV / "tools/a2shot/a2shot"
    if not emulator.exists():
        raise SystemExit("Build a2shot first: make -C dev/tools/a2shot")
    with tempfile.TemporaryDirectory(prefix="pom2-dhgr-") as work:
        work = Path(work)
        sources = [DEV / "cc65/crt0_apple2.s", DEV / "tests/dhgr_fixture.c",
                   DEV / "lib/hgrc/dhgr.c", *[DEV / "lib/hgrc" / name for name in ("dhgr_pixel.c", "dhgr_getpixel.c", "dhgr_pixel_address.c", "dhgr_write_asm.s", "dhgr_read_asm.s")],
                   *[DEV / "lib/hgrc" / name for name in ("dhgr_fill.c", "dhgr_clear.c", "dhgr_pattern.c", "dhgr_plot_color.c", "dhgr_fill_bits.c", "dhgr_bit_rect.c", "dhgr_clear_asm.s", "dhgr_span_asm.s", "dhgr_access_asm.s")], DEV / "lib/hgrc/dhgr_asm.s",
                   DEV / "lib/apple2c/apple2io_asm.s"]
        objects = []
        for source in sources:
            obj = work / (source.stem + ".o")
            run(["cl65", "-t", "none", "-Oirs", "-I", DEV / "lib/hgrc",
                 "-I", DEV / "lib/apple2c", "--asm-include-dir", DEV / "lib/apple2",
                 "-c", "-o", obj, source])
            objects.append(obj)
        binary = work / "test.bin"
        run(["cl65", "-t", "none", "-C", DEV / "cc65/apple2_hgr_c.cfg",
             "-o", binary, *objects])
        hello = work / "hello.bas"
        hello.write_text('10 PRINT CHR$(4);"BRUN TEST"\n')
        disk = work / "test.dsk"
        run(["python3", DEV / "tools/dos33.py", "--master",
             DEV / "tools/dos33_system.bin", "--out", disk,
             "--bas", f"HELLO={hello}", "--bin", f"TEST={binary}@0x6000"])
        steps = ["wait:1100"]
        for stage in range(21):
            steps += ["peek:1000:2", "peek:C018:8"]
            # RAMRD changes bus reads only; never resume CPU with aux mapped.
            steps += ["poke:C002:0", "peek:2000:8192",
                      "poke:C003:0", "peek:2000:8192", "poke:C002:0"]
            steps += ["key: ", "wait:600"]
        output = run([emulator, "--iie", "--disk", disk, *steps])
        blocks = re.split(r"(?m)^1000:", output)[1:]
        assert len(blocks) == 21, "missing checkpoints"
        banks = [bytearray(8192), bytearray(8192)]
        for stage, block in enumerate(blocks):
            state = bytes.fromhex(block.splitlines()[0])
            assert state == bytes([stage, 0]), (stage, "guest checkpoint/readback", state)
            status = re.search(r"(?m)^C018: (.*)$", block)
            flags = bytes.fromhex(status[1])
            assert not flags[0] & 128, (stage, "80STORE")
            assert bool(flags[2] & 128) == (stage == 19), (stage, "TEXT")
            assert not flags[3] & 128, (stage, "MIXED")
            assert not flags[4] & 128, (stage, "PAGE2 not restored")
            assert bool(flags[5] & 128) == (stage != 19), (stage, "HIRES")
            assert bool(flags[7] & 128) == (stage != 19), (stage, "80COL")
            if stage < 16 or stage == 20:
                pattern = PATTERNS[stage if stage < 16 else 15]
                banks = [bytearray([pattern[1], pattern[3]]) * 4096,
                         bytearray([pattern[0], pattern[2]]) * 4096]
            elif stage == 16:
                banks = [bytearray(8192), bytearray(8192)]
                for x in range(560):
                    pixel(banks, x, x % 192, int(x % 3 != 0))
            elif stage == 17:
                for x in range(140):
                    color_pixel(banks, x, 0, x % 16)
                    color_pixel(banks, x, 191, 15 - x % 16)
            elif stage == 18:
                for y in (190, 191):
                    for x in (138, 139):
                        color_pixel(banks, x, y, 9)
            dumps = re.findall(r"(?m)^[23][0-9A-F]{3}: ((?:[0-9A-F]{2} ?)+)$", block)
            actual = bytes.fromhex(" ".join(dumps))
            expected = banks[0] + banks[1]
            assert actual == expected, (stage, "video RAM mismatch",
                next((i for i, (a, b) in enumerate(zip(actual, expected)) if a != b), None))
        print("DHGR: 21 checkpoints passed (16 colors, both banks, 560 columns, 192 rows,")
        print("color boundaries, clipping, readback, text exit and reinitialization).")


if __name__ == "__main__":
    main()
