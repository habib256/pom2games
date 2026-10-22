# Neowilderness lot 3 — DHGR column primitives, standalone IIe bench.
#
#   make -f dhgr.mk          -> ../dist/NEODHGR_TEST.po (ProDOS 2.4.3, Apple IIe/IIc 128 KB)
#   make -f dhgr.mk run      -> boot it in POM2 (IIe preset): golden hour, then every
#                               mood on a key press (name on the 80-column lines), ESC quits
#   make -f dhgr.mk test     -> tests/test_dhgr_ref.py + tests/test_dhgr_cols.py
#   make -f dhgr.mk refs     -> reference PNG captures in build/dhgr/
#
# Independent of the main Makefile: every output stays in build/dhgr/.
# The reference map is regenerated here (same seed/level as the game).

DEV ?= ../dev
include $(DEV)/cc65/apple2.mk
BUILD := build/dhgr
APPLE2_PRESET := iie

DISK  := $(DIST)/NEODHGR_TEST.po
BOOT  := $(BUILD)/NEODHGR.SYSTEM
BENCH_ID := DHGR
BIN   := $(BUILD)/dhgr_test.bin
BIN4  := $(BUILD)/dhgr_test4.bin
MAPBIN := $(BUILD)/map.bin
SPRITES := $(BUILD)/sprites/manifest.json
CA65FLAGS := -t none -I src -I $(APPLE2) -I $(HGRC)
PYDEPS := tools/dhgr_ref.py tools/dhgr_palette.py tools/dhgr_sprites.py tools/view_ref.py \
          tests/scene_ref.py tests/test_forest.py

all: $(DISK) $(BIN4) $(BOOT)

include bench.mk

$(MAPBIN): tools/mkmap.py tools/topo.py
	@mkdir -p $(@D)
	$(PYTHON) -I $< --seed 1985 --level 4 $@ $(BUILD)/map.png

$(SPRITES): tools/dhgr_sprites.py tools/dhgr_palette.py tools/re_graphics.py
	$(PYTHON) tools/dhgr_sprites.py --out $(@D)

$(BUILD)/dhgr_cols.o: src/dhgr_cols.s dhgr.mk
	@mkdir -p $(@D)
	$(CA65) $(CA65FLAGS) -l $(BUILD)/dhgr_cols.lst -o $@ $<

$(BUILD)/dhgr_test.o: src/dhgr_test.s dhgr.mk
	@mkdir -p $(@D)
	$(CA65) $(CA65FLAGS) -o $@ $<

$(BUILD)/dhgr_clear_asm.o: $(HGRC)/dhgr_clear_asm.s
	@mkdir -p $(@D)
	$(CA65) $(CA65FLAGS) -o $@ $<

LIBOBJS := $(BUILD)/dhgr_clear_asm.o $(BUILD)/prodos_video.o $(BUILD)/prodos_mli.o

$(BIN): $(BUILD)/dhgr_test.o $(BUILD)/dhgr_cols.o $(LIBOBJS) src/dhgr_test.cfg
	$(LD65) -C src/dhgr_test.cfg -m $(BUILD)/dhgr_test.map -Ln $(BUILD)/dhgr_test.lbl -o $@ $(filter %.o,$^)

# Page 2 variant: RAMRD/RAMWRT banking, DCROWS mirrored in aux, script at $2000.
$(BUILD)/dhgr_cols4.o: src/dhgr_cols.s dhgr.mk
	@mkdir -p $(@D)
	$(CA65) $(CA65FLAGS) -D DHGR_BASE=0x4000 -o $@ $<

$(BUILD)/dhgr_test4.o: src/dhgr_test.s dhgr.mk
	@mkdir -p $(@D)
	$(CA65) $(CA65FLAGS) -D DHGR_BASE=0x4000 -D SCRIPT=0x2000 -o $@ $<

$(BIN4): $(BUILD)/dhgr_test4.o $(BUILD)/dhgr_cols4.o $(LIBOBJS) src/dhgr_test.cfg
	$(LD65) -C src/dhgr_test.cfg -m $(BUILD)/dhgr_test4.map -Ln $(BUILD)/dhgr_test4.lbl -o $@ $(filter %.o,$^)

# Demo: SCENE starts at the golden hour, MOOD0..9 cycle on a key press.
$(DISK): $(BIN) $(BOOT) tests/test_dhgr_cols.py $(PYDEPS) $(MAPBIN) $(SPRITES) $(BENCH_DISK_DEPS)
	@mkdir -p $(DIST)
	$(PYTHON) tests/test_dhgr_cols.py --demo-po $@ --map $(MAPBIN)
	rm -f $(DIST)/NEODHGR_TEST.dsk

refs: $(MAPBIN) $(SPRITES)
	$(PYTHON) tests/test_dhgr_ref.py --refs --map $(MAPBIN)

test: all $(A2SHOT)
	$(PYTHON) tests/test_dhgr_ref.py --map $(MAPBIN)
	$(PYTHON) tests/test_dhgr_cols.py --map $(MAPBIN)

.PHONY: refs test
