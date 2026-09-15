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
