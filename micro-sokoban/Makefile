# MICRO-SOKOBAN — Apple II+ / DOS 3.3 build
#
#   make            -> ../dist/MICRO-SOKOBAN.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> play the checked solution of every level (all 454,
#                      levels/solutions.txt) in a2run, headless
#   make clean      -> remove build/ (the disk stays)
#   make distclean  -> remove build/ and the disk
#
# Needs cc65 (ca65/ld65) and python3 only; the shared rules and tool
# variables come from ../dev/cc65/apple2.mk.

DEV     ?= ../dev
include $(DEV)/cc65/apple2.mk

INCS    := $(A2_INCS) -I $(BUILD)/lv
CFG     := apple2_micro_sokoban.cfg
DISK    := $(DIST)/MICRO-SOKOBAN.dsk
BIN     := $(BUILD)/micro_sokoban.bin
BOOT    := $(BUILD)/micro_sokoban.lz

# Level collections, PREFIX:HUD:FILE (see tools/micro_sokoban_levels.py).
COLLS   := MB1:I:levels/microban.xsb MB2:II:levels/microban2.xsb \
           MB3:III:levels/microban3.xsb MB4:IV:levels/microban4.xsb
# Levels of the title-screen demo (HUD:original number), from the checked
# solutions of tools/make_solutions.py. Packs are loaded as needed.
# The last three have 4, 3 and 5 boxes, with much
# longer solutions than the four introductory levels.
SOLUTIONS := levels/solutions.txt
DEMO    := I:1,I:3,I:12,I:23,I:60,I:84,I:98
LEVELS  := $(BUILD)/lv/levels.inc

all: $(DISK)

src/bbfont_subset.inc: tools/hud_font.py $(DEV)/tools/fonts.py $(FONT)/bbfont_glyphs.inc
	$(PYTHON) tools/hud_font.py

$(LEVELS): tools/micro_sokoban_levels.py tools/hud_font.py $(wildcard levels/*.xsb) $(SOLUTIONS) Makefile
	$(PYTHON) tools/micro_sokoban_levels.py --out $(BUILD)/lv --solutions $(SOLUTIONS) --demo $(DEMO) $(COLLS)

$(BUILD)/micro_sokoban.o: src/micro_sokoban.s src/bbfont_subset.inc src/score_hof.inc src/profiles.inc src/beginner.inc src/title_music.inc src/resume.inc src/fast_disk.inc src/solution.inc $(LEVELS) $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none -g $(INCS) -l $(BUILD)/micro_sokoban.lst -o $@ $<

$(BIN): $(BUILD)/micro_sokoban.o $(CFG)
	$(LD65) -C $(CFG) -m $(BUILD)/micro_sokoban.map -Ln $(BUILD)/micro_sokoban.lbl -o $@ $<
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(BUILD)/unpack.bin: src/unpack.s
	@mkdir -p $(BUILD)
	$(CA65) -t none -g -o $(BUILD)/unpack.o $<
	$(LD65) -t none --start-addr 0x0800 -Ln $(BUILD)/unpack.lbl -o $@ $(BUILD)/unpack.o

$(BOOT): $(BIN) $(BUILD)/unpack.bin tools/pack_program.py
	$(PYTHON) tools/pack_program.py $(BIN) $@

# The level packs (MB1A, MB1B, ...) and an empty save file go on the disk
# next to the game; runtime I/O uses DOS RWTS and cached sector lists.
$(DISK): $(BOOT) $(LEVELS) src/hello.bas tools/build_disk.py $(DEV)/tools/dos33.py $(SYSTEM)
	$(PYTHON) tools/build_disk.py --build $(BUILD) --master $(SYSTEM) --out $@

test: $(DISK) $(A2RUN)
	$(PYTHON) tools/test_exit.py --a2run $(A2RUN) --disk $(DISK)
	$(PYTHON) tools/test_graphics.py --a2run $(A2RUN) --disk $(DISK)
	$(PYTHON) tools/test_menu_render.py --a2run $(A2RUN) --disk $(DISK)
	$(PYTHON) tools/test_resume.py --a2run $(A2RUN) --disk $(DISK)
	$(PYTHON) tools/test_play.py --a2run $(A2RUN) --disk $(DISK)
	$(PYTHON) tools/test_damage.py --a2run $(A2RUN) --disk $(DISK)
	$(PYTHON) tools/test_tutorial_options.py --a2run $(A2RUN) --disk $(DISK)
	$(PYTHON) tools/test_score.py --a2run $(A2RUN) --disk $(DISK)
	$(PYTHON) tools/test_levels.py --a2run $(A2RUN) --disk $(DISK) --all
	$(PYTHON) tools/test_levels.py --a2run $(A2RUN) --disk $(DISK) --coll 2 --all
	$(PYTHON) tools/test_levels.py --a2run $(A2RUN) --disk $(DISK) --coll 3 --all
	$(PYTHON) tools/test_levels.py --a2run $(A2RUN) --disk $(DISK) --coll 4 --all

.PHONY: test
