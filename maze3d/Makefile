# Maze 3D — Apple II+ / DOS 3.3 build
#
#   make            -> ../dist/MAZE3D.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> maze generation across seeds, in a2shot
#   make clean      -> remove build/ (the disk stays)
#   make distclean  -> remove build/ and the disk
#
# Needs cc65 (ca65/ld65) and python3 only; the shared rules and tool
# variables come from ../dev/cc65/apple2.mk.

DEV     ?= ../dev
include $(DEV)/cc65/apple2.mk

DISK    := $(DIST)/MAZE3D.dsk
BIN     := $(BUILD)/maze3d.bin
OBJS    := $(BUILD)/maze3d.o $(BUILD)/sprites_trollkind.o $(BUILD)/sprites_characters.o

all: $(DISK)

$(BUILD)/maze3d.o: src/maze3d.s src/narrator.asm $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none $(A2_INCS) -l $(BUILD)/maze3d.lst -o $@ $<

$(BUILD)/%.o: src/%.asm
	@mkdir -p $(BUILD)
	$(CA65) -t none $(A2_INCS) -o $@ $<

$(BIN): $(OBJS) src/maze3d.cfg
	$(LD65) -C src/maze3d.cfg -m $(BUILD)/maze3d.map -o $@ $(OBJS)
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(BUILD)/maze3d_text.bin: $(BIN)
	@test -s $@

$(BUILD)/maze3d_score.bin: Makefile
	@mkdir -p $(BUILD)
	@printf 'MZ3\001\000\000\000\245' > $@

$(DISK): $(BIN) $(BUILD)/maze3d_text.bin $(BUILD)/maze3d_score.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin MAZE3D=$(BIN)@$(LOAD) \
	    --bin MAZETEXT=$(BUILD)/maze3d_text.bin@0x1100 \
	    --bin MAZESCORE=$(BUILD)/maze3d_score.bin@0x1F00 \
	    --catalog

test: $(DISK)
	$(PYTHON) tests/check_generation.py

.PHONY: test
