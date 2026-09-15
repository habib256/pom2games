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
DIST    := dist
DISK    := $(DIST)/SOKOBAN.dsk
BIN     := $(BUILD)/sokoban.bin
LOAD    := 0x4000

all: $(DISK)

$(BUILD)/sokoban.o: src/sokoban.s src/sokoban_levels.inc src/sokoban_levels_ext.inc src/bbfont_subset.inc
	@mkdir -p $(BUILD)
	$(CA65) -t none -I src -l $(BUILD)/sokoban.lst -o $@ $<

$(BIN): $(BUILD)/sokoban.o src/apple2_dos33.cfg
	$(LD65) -C src/apple2_dos33.cfg -m $(BUILD)/sokoban.map -o $@ $<
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(DISK): $(BIN) src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ \
	    --bas HELLO=src/hello.bas \
	    --bin SOKOBAN=$(BIN)@$(LOAD) \
	    --catalog

run: $(DISK)
	$(POM2) --preset ii+ $(DISK)

clean:
	rm -rf $(BUILD) $(DIST)

.PHONY: all run clean
