CA65 ?= ca65
LD65 ?= ld65
PYTHON ?= python3
CC ?= cc
DEV ?= ../dev
DIST ?= ../dist
BUILD ?= build
POM2 ?= /Applications/POM2.app/Contents/MacOS/POM2
DISK := $(DIST)/ARKABREAKOUT.dsk

all: $(DISK)

$(BUILD)/game.o: src/game.s src/levels.inc src/capsules.inc src/title.inc $(wildcard $(DEV)/lib/apple2/*) $(wildcard $(DEV)/lib/hgr/*)
	@mkdir -p $(BUILD)
	$(CA65) -t none -I $(DEV)/lib/apple2 -I $(DEV)/lib/hgr -I src -l $(BUILD)/game.lst -o $@ $<

$(BUILD)/game.bin: $(BUILD)/game.o $(DEV)/cc65/apple2_hgr.cfg
	$(LD65) -C $(DEV)/cc65/apple2_hgr.cfg -m $(BUILD)/game.map -Ln $(BUILD)/game.lbl -o $@ $<

$(DISK): $(BUILD)/game.bin src/hello.bas $(DEV)/tools/dos33.py $(DEV)/tools/dos33_system.bin
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(DEV)/tools/dos33_system.bin --out $@ --bas HELLO=src/hello.bas --bin ARKABREAKOUT=$(BUILD)/game.bin@0x6000

assets:
	$(PYTHON) tools/generate_title.py

run: $(DISK)
	$(POM2) --preset ii+ $(DISK)

$(BUILD)/pilot: tests/pilot.c $(DEV)/tools/a2run/a2run.c $(DEV)/tools/a2run/cpu6502.c $(DEV)/tools/a2run/cpu6502.h
	@mkdir -p $(BUILD)
	$(CC) -O2 -Wall -Wextra -std=c99 tests/pilot.c $(DEV)/tools/a2run/cpu6502.c -lz -o $@

src/title.inc: tools/generate_title.py $(DEV)/lib/hgr/bbfont_ascii5f.inc
	$(PYTHON) tools/generate_title.py

test-campaign: all $(BUILD)/pilot
	$(PYTHON) tests/test_campaign.py $(BUILD)/pilot --disk $(DISK) --labels $(BUILD)/game.lbl

test: all
	$(MAKE) -C $(DEV)/tools/a2run
	$(PYTHON) tests/test_game.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(MAKE) test-campaign

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(DISK)

.PHONY: all assets run test test-campaign clean distclean
