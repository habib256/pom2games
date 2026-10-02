# Maze 3D — Apple II+ / DOS 3.3 build
#
#   make            -> ../dist/MAZE3D.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple II+
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

INCS    := -I src -I $(DEV)/lib/apple2 -I $(DEV)/lib/hgr
BUILD   := build
DIST    ?= ../dist
DISK    := $(DIST)/MAZE3D.dsk
BIN     := $(BUILD)/maze3d.bin
LOAD    := 0x6000
OBJS    := $(BUILD)/maze3d.o $(BUILD)/sprites_trollkind.o $(BUILD)/sprites_characters.o

all: $(DISK)

$(BUILD)/maze3d.o: src/maze3d.s $(wildcard $(DEV)/lib/apple2/*) $(wildcard $(DEV)/lib/hgr/*)
	@mkdir -p $(BUILD)
	$(CA65) -t none $(INCS) -l $(BUILD)/maze3d.lst -o $@ $<

$(BUILD)/%.o: src/%.asm
	@mkdir -p $(BUILD)
	$(CA65) -t none $(INCS) -o $@ $<

$(BIN): $(OBJS) src/maze3d.cfg
	$(LD65) -C src/maze3d.cfg -m $(BUILD)/maze3d.map -o $@ $(OBJS)
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(DISK): $(BIN) src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ \
	    --bas HELLO=src/hello.bas \
	    --bin MAZE3D=$(BIN)@$(LOAD) \
	    --catalog

run: $(DISK)
	$(POM2) --preset ii+ $(DISK)

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(DISK)

.PHONY: all run clean distclean
