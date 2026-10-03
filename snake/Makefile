# Snake — Apple II+ / DOS 3.3 build (cc65 C)
#
#   make            -> ../dist/SNAKE.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple II+
#   make clean      -> remove build/ (the disk stays)
#   make distclean  -> remove build/ and the disk
#
# Needs cc65 (cl65/ca65) and python3 only: the shared ../dev tree has the rest,
# DOS 3.3 system tracks included. `make run` uses the installed POM2 app.

CL65    ?= cl65
CA65    ?= ca65
PYTHON  ?= python3
DEV     ?= ../dev
POM2    ?= /Applications/POM2.app/Contents/MacOS/POM2
SYSTEM  ?= $(DEV)/tools/dos33_system.bin

APPLE2C := $(DEV)/lib/apple2c
HGRC   := $(DEV)/lib/hgrc
GFX     := $(DEV)/lib/gfx
include $(APPLE2C)/apple2c.mk
include $(HGRC)/hgrc.mk
CFG     := $(DEV)/cc65/apple2_hgr_c.cfg
BUILD   := build
DIST    ?= ../dist
DISK    := $(DIST)/SNAKE.dsk
BIN     := $(BUILD)/snake.bin
LOAD    := 0x6000

CFLAGS  := -t none -Oirs -I $(HGRC) -I $(APPLE2C) -I $(GFX)
AFLAGS  := -t none -I $(DEV)/lib/apple2 -I $(HGRC)
ifneq ($(FIXED_SEED),)
CFLAGS  += -DSNAKE_FIXED_SEED=$(FIXED_SEED)
endif

# crt0_apple2 FIRST: it provides __STARTUP__ / _exit instead of none.lib's crt0.
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS)
OBJS := $(BUILD)/crt0_apple2.o $(BUILD)/snake.o

vpath %.c src $(HGRC) $(GFX) $(APPLE2C)
vpath %.s $(DEV)/cc65 $(HGRC) $(APPLE2C)

all: $(DISK)

$(BUILD)/%.o: %.c $(HGRC_HEADERS) $(APPLE2C)/apple2io.h
	@mkdir -p $(BUILD)
	$(CL65) $(CFLAGS) -c -o $@ $<

$(BUILD)/%.o: %.s $(wildcard $(DEV)/lib/apple2/*.inc $(DEV)/lib/apple2/*.asm)
	@mkdir -p $(BUILD)
	$(CA65) $(AFLAGS) -o $@ $<

$(BIN): $(OBJS) $(HGRC_LIB) $(CFG) Makefile
	$(CL65) -t none -C $(CFG) -m $(BUILD)/snake.map -o $@ $(OBJS) $(HGRC_LIB)
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(DISK): $(BIN) src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ \
	    --bas HELLO=src/hello.bas \
	    --bin SNAKE=$(BIN)@$(LOAD) \
	    --catalog

run: $(DISK)
	$(POM2) --preset ii+ $(DISK)

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(DISK)

.PHONY: all run clean distclean

include $(HGRC)/hgrc_build.mk
