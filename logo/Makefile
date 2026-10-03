# LOGO — Apple II / DOS 3.3 build (APPLE-1 LOGO V2.6, GEN2 HGR edition)
#
#   make            -> ../dist/LOGO.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple //e (80 columns)
#   make clean      -> remove build/ (the disk stays)
#   make distclean  -> remove build/ and the disk
#
# Needs cc65 (ca65/ld65) and python3 only: the shared ../dev tree has the rest,
# DOS 3.3 system tracks included. `make run` uses the installed POM2 app.

CA65    ?= ca65
LD65    ?= ld65
PYTHON  ?= python3
DEV     ?= ../dev
POM2    ?= /Applications/POM2.app/Contents/MacOS/POM2
SYSTEM  ?= $(DEV)/tools/dos33_system.bin

# CODETANK_BUILD = the full feature set (LABEL, SAY, LIST, EDIT, DEMO2);
# LOGO_HGR = the HGR code paths of the shared interpreter.
DEFS    := -D CODETANK_BUILD -D LOGO_HGR
INCS    := -I src -I $(DEV)/lib/apple2 -I $(DEV)/lib/hgr
BUILD   := build
DIST    ?= ../dist
DISK    := $(DIST)/LOGO.dsk
BIN     := $(BUILD)/logo.bin
LOAD    := 0x4000

# logo.o FIRST: its CODE segment starts with `jmp main`.
MODS    := logo hgr_logom2 text_bitmap math sprite_helpers sprites_emotes bubble buffer_editor
OBJS    := $(MODS:%=$(BUILD)/%.o)
LIBDEPS := $(wildcard src/*.inc $(DEV)/lib/apple2/*.inc $(DEV)/lib/apple2/*.asm $(DEV)/lib/hgr/*.inc)

all: $(DISK)

$(BUILD)/logo.o: src/logo.s src/screen.asm $(LIBDEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none $(INCS) $(DEFS) -l $(BUILD)/logo.lst -o $@ $<

$(BUILD)/%.o: src/%.asm $(LIBDEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none $(INCS) $(DEFS) -o $@ $<

$(BIN): $(OBJS) src/logo.cfg
	$(LD65) -C src/logo.cfg -m $(BUILD)/logo.map -o $@ $(OBJS)
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(DISK): $(BIN) src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ \
	    --bas HELLO=src/hello.bas \
	    --bin LOGO=$(BIN)@$(LOAD) \
	    --catalog

run: $(DISK)
	$(POM2) --preset iie $(DISK)

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(DISK)

.PHONY: all run clean distclean
