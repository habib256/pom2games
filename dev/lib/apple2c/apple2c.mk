# VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
# apple2c.mk — Makefile fragment for the Apple II C base.
#
# Set APPLE2C to the path of dev/lib/apple2c BEFORE including this file:
#
#     APPLE2C := ../dev/lib/apple2c
#     include $(APPLE2C)/apple2c.mk
#
#     SRCS := main.c $(APPLE2C_SRCS)
#     INCS := $(APPLE2C_INCS)
#
# Link with dev/cc65/apple2_hgr_c.cfg and put dev/cc65/crt0_apple2.s FIRST on
# the link line (a2_dos() and returning from main() rely on its _exit).

APPLE2C_SRCS := $(APPLE2C)/apple2io.c $(APPLE2C)/apple2io_asm.s
APPLE2C_INCS := -I $(APPLE2C)

# Opt-in objects (assemble them with $(APPLE2C_AFLAGS)): speaker + joystick,
# and DOS commands (256 + 41 bytes of BSS). Add them to SRCS only if used.
# Optional cadence service: model detection, IIe VBL, bounded delay fallback.
APPLE2C_FRAME_SRCS := $(APPLE2C)/apple2frame.s
APPLE2C_GAME_SRCS := $(APPLE2C)/apple2game_asm.s
APPLE2C_DOS_SRCS  := $(APPLE2C)/apple2dos_asm.s
APPLE2C_AFLAGS    := -I $(APPLE2C)/../apple2
