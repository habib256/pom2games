# ARKABREAKOUT — Apple II+ / DOS 3.3 build
#
#   make            -> ../dist/ARKABREAKOUT.dsk
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> game checks in a2run, then the paddle campaign (pilot)
#   make clean / distclean
#
# The shared rules and tool variables come from ../dev/cc65/apple2.mk.

DEV ?= ../dev
include $(DEV)/cc65/apple2.mk

MOUSE := $(DEV)/lib/mouse
A2_INCS += -I $(MOUSE)
APPLE2_RUN_FLAGS := --slot 4=mouseaw
PACKS := $(addprefix $(BUILD)/levels,1.bin 2.bin 3.bin 4.bin 5.bin 6.bin)

DISK := $(DIST)/ARKABREAKOUT.dsk

all: $(DISK)

$(BUILD)/game.o: src/game.s src/mechanics.inc src/hud_cache.inc src/interface.inc src/records.inc src/music.inc src/duet.inc src/music_offsets.inc $(MOUSE)/mouse_context.asm src/capsules.inc src/title.inc $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none $(A2_INCS) -l $(BUILD)/game.lst -o $@ $<

$(BUILD)/mouse.o: $(MOUSE)/mouse.s
	@mkdir -p $(BUILD)
	$(CA65) -D MOUSE_Y_LOW=100 -D MOUSE_Y_HIGH=175 -D MOUSE_Y_START=175 -o $@ $<

$(PACKS) &: src/levels.txt tools/pack_levels.py
	$(PYTHON) tools/pack_levels.py $(BUILD)

src/capsules.inc: tools/generate_sprites.py $(DEV)/tools/fonts.py $(FONT)/bbfont_glyphs.inc
	$(PYTHON) tools/generate_sprites.py

$(BUILD)/game.bin: $(BUILD)/game.o $(BUILD)/mouse.o $(A2_HGR_CFG)
	$(LD65) -C $(A2_HGR_CFG) -m $(BUILD)/game.map -Ln $(BUILD)/game.lbl -o $@ $(BUILD)/game.o $(BUILD)/mouse.o

$(BUILD)/music.bin: src/music_player.s src/music.cfg src/duet.inc src/music_aux.inc src/music_fanfare.inc
	@mkdir -p $(BUILD)
	$(CA65) -I src -o $(BUILD)/music.o src/music_player.s
	$(LD65) -C src/music.cfg -o $@ $(BUILD)/music.o

$(BUILD)/records.bin: tools/seed_records.py
	@mkdir -p $(BUILD)
	$(PYTHON) $< $@

$(DISK): $(BUILD)/game.bin $(PACKS) $(BUILD)/records.bin $(BUILD)/music.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin ARKABREAKOUT=$(BUILD)/game.bin@$(LOAD) $(foreach n,1 2 3 4 5 6,--bin LEVELS$(n)=$(BUILD)/levels$(n).bin@0x1800) --bin RECORDS=$(BUILD)/records.bin@0x1B00 --bin MUSIC=$(BUILD)/music.bin@0x1300

assets:
	$(PYTHON) tools/generate_title.py
	$(PYTHON) tools/generate_sprites.py
	$(PYTHON) tools/pack_levels.py $(BUILD)
	$(PYTHON) tools/generate_music.py

$(BUILD)/pilot: tests/pilot.c $(DEV)/tools/a2run/a2run.c $(DEV)/tools/a2run/a2run.h $(DEV)/tools/a2run/cpu6502.c $(DEV)/tools/a2run/cpu6502.h
	@mkdir -p $(BUILD)
	$(CC) -O2 -Wall -Wextra -std=c99 -fno-common -DA2RUN_LIB -I $(DEV)/tools/a2run tests/pilot.c $(DEV)/tools/a2run/a2run.c $(DEV)/tools/a2run/cpu6502.c -lz -o $@

src/title.inc: tools/generate_title.py $(DEV)/tools/fonts.py $(FONT)/bbfont_glyphs.inc
	$(PYTHON) tools/generate_title.py

test-campaign: all $(BUILD)/pilot
	$(PYTHON) tests/test_campaign.py $(BUILD)/pilot --disk $(DISK) --labels $(BUILD)/game.lbl

test: all $(A2RUN)
	$(PYTHON) $(DEV)/tests/test_hgr_xor.py
	$(PYTHON) tests/test_bricks.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_title_menu.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_hud.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_bonus_visuals.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_game.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_records.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(MAKE) test-campaign

.PHONY: assets test test-campaign

# Optional integration with real AppleMouse firmware, still on the NMOS II+.
POM2_SRC ?= ../../pom2
test-mouse: all
	$(PYTHON) tests/test_mouse.py --pom2-src $(POM2_SRC)
.PHONY: test-mouse
