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

APPLE2C_SRCS := $(APPLE2C)/apple2io_str.s $(APPLE2C)/apple2io_asm.s
APPLE2C_INCS := -I $(APPLE2C)

# Opt-in objects (assemble them with $(APPLE2C_AFLAGS)): speaker + joystick,
# and DOS commands (256 + 41 bytes of BSS). Add them to SRCS only if used.
# Independent opt-ins: application-owned IRQ clock, or model-detected VBL/delay.
APPLE2C_CADENCE_SRCS := $(APPLE2C)/apple2cadence.s
APPLE2C_FRAME_SRCS := $(APPLE2C)/apple2frame.s
# ProDOS video clock (//e VBL polling, //c mouse VBL IRQ): with the frame
# and mouse objects; the 50/60 Hz measure is apart.
APPLE2C_VBL_SRCS := $(APPLE2C)/apple2vbl.s
APPLE2C_VBL_PAL_SRCS := $(APPLE2C)/apple2vbl_pal.s
# 128 KB auxiliary memory, whole pages (apple2aux.h, dev/lib/apple2/auxmem.asm):
# aux_store (main -> aux) and aux_fetch_pages (aux -> main, 16 ZP bytes).
# Assemble with $(APPLE2C_AFLAGS) and make the objects depend on
# $(APPLE2C_AUX_DEPS).
APPLE2C_AUX_SRCS := $(APPLE2C)/apple2aux.s
APPLE2C_AUXFETCH_SRCS := $(APPLE2C)/apple2auxfetch.s
APPLE2C_AUX_DEPS := $(APPLE2C)/../apple2/auxmem.asm
APPLE2C_GAME_SRCS := $(APPLE2C)/apple2game_asm.s
APPLE2C_DOS_SRCS  := $(APPLE2C)/apple2dos_asm.s
# More opt-ins (separate objects, nothing for the programs that do not call
# them): a2_rand16 (math/random.asm's LFSR; deps APPLE2C_RAND_DEPS),
# a2_stick_present (with APPLE2C_GAME_SRCS), a2_dos_bload / a2_dos_bsave
# (with APPLE2C_DOS_SRCS).
APPLE2C_RAND_SRCS := $(APPLE2C)/apple2rand.s
APPLE2C_RAND_DEPS := $(APPLE2C)/../math/random.asm
APPLE2C_STICK_SRCS := $(APPLE2C)/apple2stick.s
APPLE2C_DOSBIN_SRCS := $(APPLE2C)/apple2dosbin.s
# Vapor lock (frame sync on the floating bus, II / II+ / //e): see apple2vapor.h.
APPLE2C_VAPOR_SRCS := $(APPLE2C)/apple2vapor_asm.s
APPLE2C_AFLAGS    := -I $(APPLE2C)/../apple2

# Public umbrella headers are transitive dependencies of C consumers.
APPLE2C_HEADERS := $(wildcard $(APPLE2C)/*.h)
