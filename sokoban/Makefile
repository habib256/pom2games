# Sokoban — Apple II+ / DOS 3.3 build
#
#   make            -> dist/SOKOBAN.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple II+
#   make clean
#
# Needs cc65 (ca65/ld65) and python3 only: the disk tool and the DOS 3.3
# system tracks come from the shared ../dev tree. `make run` uses the
# installed POM2 app.

CA65    ?= ca65
LD65    ?= ld65
PYTHON  ?= python3
DEV     ?= ../dev
POM2    ?= /Applications/POM2.app/Contents/MacOS/POM2
SYSTEM  ?= $(DEV)/tools/dos33_system.bin

BUILD   := build
INCS    := -I src -I $(DEV)/lib/apple2 -I $(BUILD)/lv
CFG     := $(DEV)/cc65/apple2_hgr.cfg
DIST    := dist
DISK    := $(DIST)/SOKOBAN.dsk
BIN     := $(BUILD)/sokoban.bin
LOAD    := 0x6000

# Level collections, PREFIX:HUD:FILE (see tools/sokoban_levels.py). Microban
# II joins as the second collection as soon as levels/microban2.xsb exists.
COLLS   := MB1:I:levels/microban.xsb
ifneq ($(wildcard levels/microban2.xsb),)
COLLS   += MB2:II:levels/microban2.xsb
endif
LEVELS  := $(BUILD)/lv/levels.inc

all: $(DISK)

$(LEVELS): tools/sokoban_levels.py $(wildcard levels/*.xsb) Makefile
	$(PYTHON) tools/sokoban_levels.py --out $(BUILD)/lv $(COLLS)

$(BUILD)/sokoban.o: src/sokoban.s src/bbfont_subset.inc $(LEVELS) $(wildcard $(DEV)/lib/apple2/*)
	@mkdir -p $(BUILD)
	$(CA65) -t none $(INCS) -l $(BUILD)/sokoban.lst -o $@ $<

$(BIN): $(BUILD)/sokoban.o $(CFG)
	$(LD65) -C $(CFG) -m $(BUILD)/sokoban.map -o $@ $<
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

# The level packs (MB1A, MB1B, ...) and an empty save file go on the disk
# next to the game: it BLOADs / BSAVEs them while it runs.
$(DISK): $(BIN) $(LEVELS) src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ \
	    --bas HELLO=src/hello.bas \
	    --bin SOKOBAN=$(BIN)@$(LOAD) \
	    $$(cat $(BUILD)/lv/packs.args) \
	    --bin SOKOSAVE=$(BUILD)/lv/sokosave.bin@0x0000 \
	    --catalog

run: $(DISK)
	$(POM2) --preset ii+ $(DISK)

clean:
	rm -rf $(BUILD) $(DIST)

.PHONY: all run clean
