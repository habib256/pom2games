# VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
# apple2.mk — what every program Makefile in pom2games shares.
#
#     DEV ?= ../dev              # ../.. from dev/examples
#     include $(DEV)/cc65/apple2.mk
#     DISK := $(DIST)/NAME.dsk
#     all: $(DISK)
#     ...
#     $(DISK): $(BIN) $(DOS33_DEPS)
#     	@mkdir -p $(DIST)
#     	$(DOS33) --bin NAME=$(BIN)@$(LOAD) --catalog
#
# Provides the tool variables (all overridable: make CA65=... DIST=...), the
# library paths, the asm include path and dependency list, the DOS 3.3 disk
# command and the run / clean / distclean targets. `all` stays the default
# goal even though this file is included first.

CA65    ?= ca65
LD65    ?= ld65
CL65    ?= cl65
AR65    ?= ar65
CC      ?= cc
PYTHON  ?= python3
BUILD   ?= build
DIST    ?= ../dist
POM2    ?= /Applications/POM2.app/Contents/MacOS/POM2
SYSTEM  ?= $(DEV)/tools/dos33_system.bin
A2RUN   ?= $(DEV)/tools/a2run/a2run
A2SHOT  ?= $(DEV)/tools/a2shot/a2shot
LOAD    ?= 0x6000
APPLE2_PRESET ?= ii+
APPLE2_RUN_FLAGS ?=

APPLE2  := $(DEV)/lib/apple2
HGR     := $(DEV)/lib/hgr
FONT    := $(DEV)/lib/font
HGRC    := $(DEV)/lib/hgrc
GFX     := $(DEV)/lib/gfx
APPLE2C := $(DEV)/lib/apple2c

# Assembly programs: include path and the library files a rebuild depends on.
A2_INCS     := -I src -I $(APPLE2) -I $(HGR) -I $(FONT)
A2_ASM_DEPS := $(wildcard $(APPLE2)/*.inc $(APPLE2)/*.asm $(HGR)/*.inc $(HGR)/*.asm $(FONT)/*.inc)
A2_HGR_CFG   := $(DEV)/cc65/apple2_hgr.cfg
A2_HGR_C_CFG := $(DEV)/cc65/apple2_hgr_c.cfg
A2_CRT0      := $(DEV)/cc65/crt0_apple2.s

# Bootable DOS 3.3 disk: $(DOS33) --bin NAME=file@addr ... [--catalog]
DOS33      = $(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ --bas HELLO=src/hello.bas
DOS33_DEPS := src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)

.DEFAULT_GOAL := all

run: all
	$(POM2) --preset $(APPLE2_PRESET) $(APPLE2_RUN_FLAGS) $(DISK)

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(DISK)

$(A2RUN): $(wildcard $(DEV)/tools/a2run/*.[ch] $(DEV)/tools/a2run/Makefile)
	$(MAKE) -C $(DEV)/tools/a2run

.PHONY: all run clean distclean
