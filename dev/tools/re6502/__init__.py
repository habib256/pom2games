"""re6502 -- reverse-engineering helpers for 6502 programs (dev/tools).

    opcodes   OPS / C02OPS / LEN tables, decode(), text()
    trace     recursive code tracer, runs()
    disk      physical sectors of a DOS-order .dsk (PHYS2LOG)
    da65      da65 info files from a trace (cross-check disassembly)
    cli.py    trace / listing / refs from the command line
    flux2dsk.py  WOZ2 / A2R2 flux image -> DOS-order .dsk (script)
    peek2bin.py  a2shot peek dumps -> flat RAM image (script, peek2bin())

From the PHYSICS reconstruction (physics/tools), which uses them.
"""
