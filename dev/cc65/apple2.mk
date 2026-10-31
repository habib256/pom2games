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
#     test: all $(A2RUN)         # fast tier: a minute or two, after each change
#     	$(PYTHON) tests/test_game.py
#     test-long: all $(A2RUN)    # long tier: full campaigns, every level...
#     	$(PYTHON) tests/test_campaign.py       # (may be empty: `test-long:`)
#
# Tests come in two tiers in every program: `make test` is the dev-loop
# reflex (make -C <game> test) and the root `make test` / `make test-changed`
# run it; `make test-long` holds what is too slow for that (root `make
# test-long`, `make test-all` = both). Keep `test` short: move a script to
# `test-long` rather than letting the fast tier grow past a couple of minutes.
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
# a2shot links a vendored POM2 core built for macOS arm64 and Linux x86_64:
# on other hosts the tests that need it are skipped. `make A2SHOT_HOST=`
# simulates that.
ifeq ($(origin A2SHOT_HOST),undefined)
A2SHOT_HOST := $(if $(filter Darwin-arm64 Linux-x86_64,$(shell uname -sm | tr ' ' -)),yes)
endif
LOAD    ?= 0x6000
APPLE2_PRESET ?= ii+
APPLE2_RUN_FLAGS ?=

APPLE2  := $(DEV)/lib/apple2
HGR     := $(DEV)/lib/hgr
FONT    := $(DEV)/lib/font
HGRC    := $(DEV)/lib/hgrc
GFX     := $(DEV)/lib/gfx
APPLE2C := $(DEV)/lib/apple2c
AUDIO   := $(DEV)/lib/audio
PERSPECTIVE := $(DEV)/lib/perspective
MATH    := $(DEV)/lib/math
PHYSICS := $(DEV)/lib/physics

# Assembly programs: include path and the library files a rebuild depends on.
A2_INCS     := -I src -I $(APPLE2) -I $(HGR) -I $(FONT) -I $(MATH) -I $(PHYSICS)
A2_ASM_DEPS := $(wildcard $(APPLE2)/*.inc $(APPLE2)/*.asm $(HGR)/*.inc $(HGR)/*.asm $(FONT)/*.inc \
               $(MATH)/*.inc $(MATH)/*.asm $(PHYSICS)/*.inc $(PHYSICS)/*.asm)
A2_HGR_CFG   := $(DEV)/cc65/apple2_hgr.cfg
A2_HGR_C_CFG := $(DEV)/cc65/apple2_hgr_c.cfg
A2_CRT0      := $(DEV)/cc65/crt0_apple2.s

# Bootable DOS 3.3 disk: $(DOS33) --bin NAME=file@addr ... [--catalog]
DOS33      = $(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ --bas HELLO=src/hello.bas
DOS33_DEPS := src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)
# where files lie on the disk, patched into a program that reads them through
# RWTS once DOS is gone (dev/tools/dos33patch.py)
DOS33PATCH = $(PYTHON) $(DEV)/tools/dos33patch.py
DOS33PATCH_DEPS := $(DEV)/tools/dos33patch.py $(DEV)/tools/dos33.py

# WOZ twin of a 140K disk in dist/, in dist/woz/ (dev/tools/dsk2woz.py): the MiSTer
# Apple-II core's own .dsk/.po conversion has no sync bytes, and RWTS reads
# made by the program fail there; it also writes saves back to a WOZ only.
# `all` builds it; a program clears WOZ after the include to go without (an
# 800K disk, a disk outside dist/).
WOZ ?= $(if $(filter $(DIST)/%.dsk $(DIST)/%.po,$(DISK)),$(DIST)/woz/$(notdir $(basename $(DISK))).woz)
DSK2WOZ_DEPS := $(DEV)/tools/dsk2woz.py
$(DIST)/woz/%.woz: $(DIST)/%.dsk $(DSK2WOZ_DEPS)
	@mkdir -p $(DIST)/woz
	$(PYTHON) $(DEV)/tools/dsk2woz.py $< $@
$(DIST)/woz/%.woz: $(DIST)/%.po $(DSK2WOZ_DEPS)
	@mkdir -p $(DIST)/woz
	$(PYTHON) $(DEV)/tools/dsk2woz.py $< $@
.SECONDEXPANSION:
all: $$(WOZ)

.DEFAULT_GOAL := all

run: all
	$(POM2) --preset $(APPLE2_PRESET) $(APPLE2_RUN_FLAGS) $(DISK)

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(DISK) $(WOZ)

$(A2RUN): $(wildcard $(DEV)/tools/a2run/*.[ch] $(DEV)/tools/a2run/Makefile)
	$(MAKE) -C $(DEV)/tools/a2run

$(A2SHOT): $(DEV)/tools/a2shot/a2shot.cpp $(DEV)/tools/a2shot/Makefile $(DEV)/tools/a2shot/sdk.mk
	$(MAKE) -C $(DEV)/tools/a2shot

# C++ test probes on the POM2 core facade (tests/NAME_probe.cpp, with
# dev/tools/a2shot/probe.hpp), linked by a2shot's Makefile against its SDK.
$(BUILD)/%_probe: tests/%_probe.cpp $(DEV)/tools/a2shot/probe.hpp $(DEV)/tools/a2shot/sdk.mk
	@mkdir -p $(BUILD)
	$(MAKE) -C $(DEV)/tools/a2shot probe SRC=$(abspath $<) OUT=$(abspath $@)

.PHONY: all run clean distclean
