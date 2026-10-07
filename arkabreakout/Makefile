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

DISK := $(DIST)/ARKABREAKOUT.dsk

all: $(DISK)

$(BUILD)/game.o: src/game.s src/levels.inc src/capsules.inc src/title.inc $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none $(A2_INCS) -l $(BUILD)/game.lst -o $@ $<

$(BUILD)/game.bin: $(BUILD)/game.o $(A2_HGR_CFG)
	$(LD65) -C $(A2_HGR_CFG) -m $(BUILD)/game.map -Ln $(BUILD)/game.lbl -o $@ $<

$(DISK): $(BUILD)/game.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin ARKABREAKOUT=$(BUILD)/game.bin@$(LOAD)

assets:
	$(PYTHON) tools/generate_title.py

$(BUILD)/pilot: tests/pilot.c $(DEV)/tools/a2run/a2run.c $(DEV)/tools/a2run/a2run.h $(DEV)/tools/a2run/cpu6502.c $(DEV)/tools/a2run/cpu6502.h
	@mkdir -p $(BUILD)
	$(CC) -O2 -Wall -Wextra -std=c99 -fno-common -DA2RUN_LIB -I $(DEV)/tools/a2run tests/pilot.c $(DEV)/tools/a2run/a2run.c $(DEV)/tools/a2run/cpu6502.c -lz -o $@

src/title.inc: tools/generate_title.py $(DEV)/tools/fonts.py $(FONT)/bbfont_glyphs.inc
	$(PYTHON) tools/generate_title.py

test-campaign: all $(BUILD)/pilot
	$(PYTHON) tests/test_campaign.py $(BUILD)/pilot --disk $(DISK) --labels $(BUILD)/game.lbl

test: all $(A2RUN)
	$(PYTHON) tests/test_game.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(MAKE) test-campaign

.PHONY: assets test test-campaign
