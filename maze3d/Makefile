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
include $(DEV)/cc65/fhpack.mk

DISK    := $(DIST)/MAZE3D.dsk
BIN     := $(BUILD)/maze3d.bin
OBJS    := $(BUILD)/maze3d.o

all: $(DISK)

$(BUILD)/title.lz4fh: assets/title.hgr $(FHPACK)
	$(FHPACK) -c -9 -h $< $@
	$(FHPACK) -d $@ $(BUILD)/title.roundtrip.hgr
	cmp $< $(BUILD)/title.roundtrip.hgr
	$(PYTHON) -c 'from pathlib import Path; assert Path("$@").stat().st_size <= 0xE00, "title exceeds the buffer before MAZESCORE"'

$(BUILD)/packed_sprites.inc: tools/pack_sprites.py $(DEV)/tools/assets/pack_hgr_sprites.py src/maze3d.s src/sprites_trollkind.asm src/sprites_characters.asm
	@mkdir -p $(BUILD)
	$(PYTHON) tools/pack_sprites.py

$(BUILD)/narrator_packed.inc: tools/pack_narrator.py src/narrator.asm
	@mkdir -p $(BUILD)
	$(PYTHON) tools/pack_narrator.py

$(BUILD)/maze3d.o: src/maze3d.s src/narrator.asm src/save.inc src/ux.inc $(BUILD)/narrator_packed.inc $(BUILD)/packed_sprites.inc $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -g -t none $(A2_INCS) -I $(BUILD) -l $(BUILD)/maze3d.lst -o $@ $<

$(BUILD)/%.o: src/%.asm
	@mkdir -p $(BUILD)
	$(CA65) -g -t none $(A2_INCS) -o $@ $<

$(BIN): $(OBJS) src/maze3d.cfg
	$(LD65) -C src/maze3d.cfg -m $(BUILD)/maze3d.map -Ln $(BUILD)/maze3d.lbl -o $@ $(OBJS)
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(BUILD)/maze3d_state.bin: $(BIN)
	@test -s $@

$(BUILD)/maze3d_prefs.bin: Makefile
	@mkdir -p $(BUILD)
	@printf 'MZP\001\001\001\012\012' > $@

$(BUILD)/maze3d_save.bin: Makefile
	@mkdir -p $(BUILD)
	$(PYTHON) -c 'from pathlib import Path; Path("$@").write_bytes(bytes(256))'

$(BUILD)/maze3d_text.bin: $(BIN)
	@test -s $@

$(BUILD)/maze3d_score.bin: Makefile
	@mkdir -p $(BUILD)
	@printf 'MZ3\001\000\000\000\245' > $@

$(DISK): $(BIN) $(BUILD)/maze3d_text.bin $(BUILD)/maze3d_score.bin $(BUILD)/maze3d_state.bin $(BUILD)/maze3d_prefs.bin $(BUILD)/maze3d_save.bin $(BUILD)/title.lz4fh $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin MAZE3D=$(BIN)@$(LOAD) \
	    --bin MAZETEXT=$(BUILD)/maze3d_text.bin@0x1100 \
	    --bin MAZESCORE=$(BUILD)/maze3d_score.bin@0x1F00 \
	    --bin MAZETITLE=$(BUILD)/title.lz4fh@0x1100 \
	    --bin MAZESTATE=$(BUILD)/maze3d_state.bin@0x1B93 \
	    --bin MAZEPREFS=$(BUILD)/maze3d_prefs.bin@0x1F10 \
	    --bin MAZESAVE1=$(BUILD)/maze3d_save.bin@0x1000 \
	    --bin MAZESAVE2=$(BUILD)/maze3d_save.bin@0x1000 \
	    --bin MAZESAVE3=$(BUILD)/maze3d_save.bin@0x1000 \
	    --catalog

test: $(DISK)
	$(PYTHON) tests/check_generation.py
	$(PYTHON) tests/check_seed_entry.py
	$(PYTHON) tests/check_rendering.py
	$(PYTHON) tests/check_joystick.py
	$(PYTHON) tests/check_configuration.py
	$(PYTHON) tests/check_profiles.py
	$(PYTHON) tests/check_ergonomics.py
	$(PYTHON) tests/check_playthrough.py

.PHONY: test
