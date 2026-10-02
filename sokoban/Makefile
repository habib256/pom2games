# Sokoban — Apple II+ / DOS 3.3 build
#
#   make            -> ../dist/SOKOBAN.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> play the checked solution of every level (all 454,
#                      levels/solutions.txt) in a2run, headless
#   make clean      -> remove build/ (the disk stays)
#   make distclean  -> remove build/ and the disk
#
# Needs cc65 (ca65/ld65) and python3 only: the disk tool and the DOS 3.3
# system tracks come from the shared ../dev tree. `make run` uses the
# installed POM2 app.

CA65    ?= ca65
LD65    ?= ld65
PYTHON  ?= python3
DEV     ?= ../dev
A2RUN   ?= $(DEV)/tools/a2run/a2run
POM2    ?= /Applications/POM2.app/Contents/MacOS/POM2
SYSTEM  ?= $(DEV)/tools/dos33_system.bin

BUILD   := build
INCS    := -I src -I $(DEV)/lib/apple2 -I $(BUILD)/lv
CFG     := $(DEV)/cc65/apple2_hgr.cfg
DIST    ?= ../dist
DISK    := $(DIST)/SOKOBAN.dsk
BIN     := $(BUILD)/sokoban.bin
LOAD    := 0x6000

# Level collections, PREFIX:HUD:FILE (see tools/sokoban_levels.py).
COLLS   := MB1:I:levels/microban.xsb MB2:II:levels/microban2.xsb \
           MB3:III:levels/microban3.xsb MB4:IV:levels/microban4.xsb
# Levels of the title-screen demo (HUD:original number), from the checked
# solutions of tools/make_solutions.py. All in the first pack of Microban,
# which is loaded under the title: no disk access during the demo.
SOLUTIONS := levels/solutions.txt
DEMO    := I:1,I:3,I:12,I:23
LEVELS  := $(BUILD)/lv/levels.inc

all: $(DISK)

$(LEVELS): tools/sokoban_levels.py $(wildcard levels/*.xsb) $(SOLUTIONS) Makefile
	$(PYTHON) tools/sokoban_levels.py --out $(BUILD)/lv --solutions $(SOLUTIONS) --demo $(DEMO) $(COLLS)

$(BUILD)/sokoban.o: src/sokoban.s src/bbfont_subset.inc $(LEVELS) $(wildcard $(DEV)/lib/apple2/*)
	@mkdir -p $(BUILD)
	$(CA65) -t none -g $(INCS) -l $(BUILD)/sokoban.lst -o $@ $<

$(BIN): $(BUILD)/sokoban.o $(CFG)
	$(LD65) -C $(CFG) -m $(BUILD)/sokoban.map -Ln $(BUILD)/sokoban.lbl -o $@ $<
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

$(A2RUN): $(wildcard $(DEV)/tools/a2run/*.[ch])
	$(MAKE) -C $(DEV)/tools/a2run

test: $(DISK) $(A2RUN)
	$(PYTHON) tools/test_levels.py --a2run $(A2RUN) --disk $(DISK) --all
	$(PYTHON) tools/test_levels.py --a2run $(A2RUN) --disk $(DISK) --coll 2 --all
	$(PYTHON) tools/test_levels.py --a2run $(A2RUN) --disk $(DISK) --coll 3 --all
	$(PYTHON) tools/test_levels.py --a2run $(A2RUN) --disk $(DISK) --coll 4 --all

run: $(DISK)
	$(POM2) --preset ii+ $(DISK)

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(DISK)

.PHONY: all run test clean distclean
