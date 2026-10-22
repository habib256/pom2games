# tools/re6502 — reverse engineering of 6502 programs

*[← dev](../../README.md)*

The generic tools that came out of the reconstruction of the PHYSICS demo
([`physics/`](../../../physics/README.md)), which still uses them to
regenerate its sources and cross-check them against da65.

| Module | Role |
|---|---|
| `opcodes.py` | `OPS` (documented NMOS 6502), `C02OPS` (65C02 additions), `LEN`; `decode()`, `branch_target()`, `operand_text()`, `text()` |
| `trace.py` | `trace(img, entries, regions, stops)`: recursive walk (branches, JSR, JMP) → code bytes, targets, problems (unknown opcode, 65C02, indirect jump or jump outside the image); `runs()` |
| `da65.py` | `info(code, lo, hi, labels, zp)`: da65 info file derived from the trace, for an independent disassembly |
| `disk.py` | `PHYS2LOG`, `phys_sector()`: physical sectors of a .dsk image in DOS order (custom loaders) |
| `cli.py` | `trace`, `listing`, `refs abs|zp` on a 64 KB memory image |

```
python3 dev/tools/re6502/cli.py trace physics/work/image.bin --region 800-1D00 --region 9400-9B00
python3 dev/tools/re6502/cli.py listing physics/work/image.bin 0800 0900 --region 800-1D00
python3 dev/tools/re6502/cli.py refs physics/work/image.bin zp --region 800-1D00
```

In a script, import the package from `dev/tools`:
`sys.path.insert(0, '<root>/dev/tools')` then `from re6502.trace import trace`.
The scripts in `physics/tools` find it through a path relative to their own
location, and stay compatible with `python3 -I`.

Checked during the extraction: regenerated sources, extracted image and da65
info files byte-identical to those of the old scripts; the rebuilt disk is
still identical to the original and `make da65check` passes.

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).
