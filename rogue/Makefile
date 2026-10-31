# ROGUE — Apple II+ 48 KB / DOS 3.3 + E-Z Color card (TMS9918A), any slot
#
#   make            -> ../dist/ROGUE.dsk (+ ../dist/woz/ROGUE.woz)
#   make run        -> boot it in POM2 as an Apple II+ with the card in slot 4
#                      (Display > Card Monitor shows the card's screen)
#   make test       -> boot + detection in several slots, no-card message,
#                      VRAM / registers, 18-cycle VDP rule over a scripted
#                      game, sounds (a2run --ezcolor); the same on POM2's
#                      card (a2shot --ezcolor: pictures, VRAM = a2run's, no
#                      dropped VDP access); ROGUE.DHGR on a2shot //e and //c
#   make clean / distclean
#
# The shared rules and tool variables come from ../dev/cc65/apple2.mk.

DEV ?= ../dev
include $(DEV)/cc65/apple2.mk

DISK := $(DIST)/ROGUE.dsk
CORE := $(wildcard src/core/*.inc src/core/*.asm) src/core/music.inc
GFX  := $(wildcard src/gfx/*)
TMS_SRCS := src/rogue_tms.s src/boot.inc src/ezvdp.inc src/video_tms.asm \
            $(CORE) $(GFX)
APPLE2_RUN_FLAGS ?= --slot 4=ezcolor
TMS_LOAD  := 0x4000
# ROGUE.DHGR: the DHGR builder's src/rogue_dhgr.s when it exists (cfg
# src/rogue_dhgr.cfg, load address DHGR_LOAD), a stand-in until then.
DHGR_LOAD ?= 0x4000
DHGR_MAIN := src/rogue_dhgr.s
DHGR_CFG  := $(if $(wildcard src/rogue_dhgr.cfg),src/rogue_dhgr.cfg,src/launcher.cfg)


all: $(DISK)

src/core/music.inc: tools/music.py $(DEV)/tools/audio/tune.py $(DEV)/tools/audio/notes.py
	$(PYTHON) tools/music.py $@

$(BUILD)/rogue_tms.o: $(TMS_SRCS) $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -g -t none $(A2_INCS) -l $(BUILD)/rogue_tms.lst -o $@ $<

$(BUILD)/rogue_tms.bin: $(BUILD)/rogue_tms.o src/rogue_tms.cfg
	$(LD65) -C src/rogue_tms.cfg -m $(BUILD)/rogue_tms.map -Ln $(BUILD)/rogue_tms.lbl -o $@ $<
	@echo "ROGUE.TMS: $$(wc -c < $@) bytes at $(TMS_LOAD)"

$(BUILD)/launcher.o: src/launcher.s src/ezvdp.inc $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -g -t none $(A2_INCS) -l $(BUILD)/launcher.lst -o $@ $<

$(BUILD)/launcher.bin: $(BUILD)/launcher.o src/launcher.cfg
	$(LD65) -C src/launcher.cfg -m $(BUILD)/launcher.map -Ln $(BUILD)/launcher.lbl -o $@ $<
	@echo "ROGUE (launcher): $$(wc -c < $@) bytes at 0x6000"

$(BUILD)/rogue_dhgr.o: $(DHGR_MAIN) $(wildcard src/video_dhgr.*) $(CORE) $(GFX) $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -g -t none $(A2_INCS) -l $(BUILD)/rogue_dhgr.lst -o $@ $<

# DHGR back-end data: the TMS tiles / font / sprites halved (tools/tiles_dhgr.py;
# `make dhgr-previews` writes its preview PNGs to screenshots/)
src/video_dhgr_data.inc: tools/tiles_dhgr.py $(GFX) $(DEV)/tools/apple2img.py
	$(PYTHON) tools/tiles_dhgr.py $@

$(BUILD)/rogue_dhgr.o: src/video_dhgr_data.inc

dhgr-previews:
	$(PYTHON) tools/tiles_dhgr.py src/video_dhgr_data.inc --png screenshots

$(BUILD)/rogue_dhgr.bin: $(BUILD)/rogue_dhgr.o $(DHGR_CFG)
	$(LD65) -C $(DHGR_CFG) -m $(BUILD)/rogue_dhgr.map -Ln $(BUILD)/rogue_dhgr.lbl -o $@ $<

$(DISK): $(BUILD)/launcher.bin $(BUILD)/rogue_tms.bin $(BUILD)/rogue_dhgr.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin ROGUE=$(BUILD)/launcher.bin@0x6000 \
		--bin ROGUE.TMS=$(BUILD)/rogue_tms.bin@$(TMS_LOAD) \
		--bin ROGUE.DHGR=$(BUILD)/rogue_dhgr.bin@$(if $(wildcard src/rogue_dhgr.s),$(DHGR_LOAD),0x6000) \
		--catalog

test: all $(A2RUN)
	$(PYTHON) tests/test_rogue.py
	$(PYTHON) tests/test_dhgr.py
	$(PYTHON) tests/test_rogue_pom2.py

# Long tier (convention of ../dev/cc65/apple2.mk): nothing slow yet.
test-long:
	@echo "rogue: no long tests"

.PHONY: test test-long dhgr-previews
