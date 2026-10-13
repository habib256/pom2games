# Neowilderness lot 7 — night-sky stars, standalone IIe bench (docs/STARS.md).
#
#   make -f stars.mk          -> ../dist/NEOSTARS_TEST.po (ProDOS 2.4.3, Apple IIe/IIc 128 KB)
#   make -f stars.mk run      -> boot it in POM2 (IIe preset): one night view per region,
#                                any key for the next one
#   make -f stars.mk test     -> tests/test_stars_ref.py (Python) + tests/test_stars.py
#                                (a2shot --iie: list and both banks against tools/stars_ref.py)
#   make -f stars.mk previews -> PNG previews in build/stars/ (tools/stars_ref.py)
#
# Independent of the main Makefile: every output stays in build/stars/.

DEV ?= ../dev
include $(DEV)/cc65/apple2.mk
BUILD := build/stars
APPLE2_PRESET := iie

DISK  := $(DIST)/NEOSTARS_TEST.po
BOOT  := $(BUILD)/NEOSTARS.SYSTEM
BIN   := $(BUILD)/stars_test.bin
CA65FLAGS := -g -t none -I src -I $(APPLE2) -I $(BUILD)
PYDEPS := tools/stars_ref.py tools/stars_catalog.py tools/sky_ephemeris.py tools/dhgr_palette.py

all: $(DISK)

$(BUILD)/tables.inc $(BUILD)/rowtab.inc: tools/gentables.py
	@mkdir -p $(@D)
	$(PYTHON) -I $< $(BUILD)/tables.inc $(BUILD)/rowtab.inc

$(BUILD)/dhgr_tables.inc: tools/gendhgr.py tools/dhgr_palette.py
	@mkdir -p $(@D)
	$(PYTHON) -I $< $@

$(BUILD)/stars_tables.inc: tools/genstars.py $(PYDEPS)
	@mkdir -p $(@D)
	$(PYTHON) -I $< $@ --names $(BUILD)/stars_names.inc

$(BUILD)/stars_test.o: src/stars_test.s src/stars.s src/stars_draw.s src/dhgr.s stars.mk \
                       $(BUILD)/tables.inc $(BUILD)/dhgr_tables.inc $(BUILD)/stars_tables.inc
	$(CA65) $(CA65FLAGS) -l $(BUILD)/stars_test.lst -o $@ $<

$(BUILD)/prodos_video.o: $(DEV)/lib/prodos/video.s
	@mkdir -p $(@D)
	$(CA65) -t none -o $@ $<

$(BUILD)/prodos_mli.o: $(DEV)/lib/prodos/mli.s
	@mkdir -p $(@D)
	$(CA65) -t none -o $@ $<

$(BIN): $(BUILD)/stars_test.o $(BUILD)/prodos_video.o $(BUILD)/prodos_mli.o src/stars_test.cfg
	$(LD65) -C src/stars_test.cfg -m $(BUILD)/stars_test.map -Ln $(BUILD)/stars_test.lbl -o $@ $(filter %.o,$^)

# Same loader as the DHGR bench (src/dhgr_boot.cfg layout).
$(BOOT): src/stars_boot.s src/dhgr_boot.cfg
	@mkdir -p $(@D)
	$(CA65) -t none -o $(BUILD)/stars_boot.o $<
	$(LD65) -C src/dhgr_boot.cfg -o $@ $(BUILD)/stars_boot.o

# Demo: one night view per region (any key: the next one).
$(DISK): $(BIN) $(BOOT) tests/test_stars.py $(PYDEPS) \
         $(DEV)/tools/prodos/PRODOS $(DEV)/tools/prodos/boot.bin $(DEV)/tools/prodos/build_volume.py
	@mkdir -p $(DIST)
	$(PYTHON) tests/test_stars.py --demo-po $@

previews: $(PYDEPS)
	$(PYTHON) tools/stars_ref.py --out $(BUILD)

test: all $(A2SHOT)
	$(PYTHON) tests/test_stars_ref.py
	$(PYTHON) tests/test_stars.py

.PHONY: previews test
