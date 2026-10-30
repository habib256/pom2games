# WARGALAGA II — Apple //e enhanced / //c 128 KB, ProDOS 8, HGR double buffer.
#
#   make            -> ../dist/WARGALAGAII.po
#   make run        -> POM2, //e enhanced (clock: VBL $C019)
#   make run-iic    -> POM2, //c (clock: VBL interrupt of the mouse firmware)
#   make test       -> fast tier: volume, boot, cadence, ship and shots
#   make test-long  -> long tier: autopilot levels 1/25/100, worst levels
#
# Game in 65C02 assembly (src/game.s + src/timing.s), linked behind cc65's
# ProDOS crt0 with the ProDOS (/RAM claim) and mouse (//c clock) libraries.

DEV ?= ../dev
APPLE2_PRESET := iie
APPLE2_RUN_FLAGS :=
include $(DEV)/cc65/apple2.mk
include $(APPLE2C)/apple2c.mk
PRODOS := $(DEV)/lib/prodos
MOUSE  := $(DEV)/lib/mouse
include $(PRODOS)/prodos.mk
include $(MOUSE)/mouse.mk
include $(DEV)/cc65/fhpack.mk

DISK := $(DIST)/WARGALAGAII.po
ASFLAGS := --cpu 65c02 -g -I src -I $(HGR) -I $(APPLE2) -I $(MATH) -I $(FONT) -I $(PRODOS)
OBJS := $(BUILD)/crt0_prodos.o $(BUILD)/game.o $(BUILD)/timing.o $(BUILD)/music.o
PT3 := $(APPLE2)/pt3
LIB_OBJS := $(BUILD)/mli.o $(BUILD)/video.o $(BUILD)/mouse.o $(BUILD)/apple2frame.o $(BUILD)/apple2vbl.o

all: $(DISK)

src/sprites.inc: tools/sprites.py
	$(PYTHON) tools/sprites.py
src/paths.inc: tools/paths.py
	$(PYTHON) tools/paths.py
src/sound.inc: tools/sound.py
	$(PYTHON) tools/sound.py
src/bonus.inc: tools/bonus.py tools/model.py tools/paths.py
	cd tools && $(PYTHON) bonus.py
src/hud.inc: tools/hud.py tools/model.py
	$(PYTHON) tools/hud.py
src/demo.inc: tools/demo.py tools/autopilot.py tools/model.py tools/paths.py
	$(PYTHON) tools/demo.py

# The title picture (LZ4FH) and the new disk's HIGHSCORES, in the overlay.
$(BUILD)/title.lz4: tools/title.py tools/sprites.py $(FHPACK)
	@mkdir -p $(@D)
	$(PYTHON) tools/title.py $(BUILD)/title.hgr
	$(FHPACK) -c -9 -h $(BUILD)/title.hgr $@ > /dev/null
	$(FHPACK) -d $@ $(BUILD)/title.check.hgr > /dev/null
	cmp $(BUILD)/title.hgr $(BUILD)/title.check.hgr
$(BUILD)/HIGHSCORES: tools/records.py
	@mkdir -p $(@D)
	$(PYTHON) tools/records.py $@

$(BUILD)/game.o: src/game.s src/logic.s src/render.s src/sound.s src/shop.s src/memory.s src/storm.s src/front.s src/demo.s $(APPLE2)/duet.asm $(APPLE2)/lz4fh.asm $(PRODOS)/file.asm src/sprites.inc src/paths.inc src/sound.inc src/bonus.inc src/hud.inc src/demo.inc $(BUILD)/title.lz4 $(BUILD)/HIGHSCORES $(A2_ASM_DEPS)
$(BUILD)/%.o: src/%.s
	@mkdir -p $(@D)
	$(CA65) $(ASFLAGS) --bin-include-dir $(BUILD) -o $@ $<
$(BUILD)/crt0_prodos.o: $(DEV)/cc65/crt0_prodos.s
	@mkdir -p $(@D)
	$(CA65) -g -o $@ $<
$(BUILD)/mli.o $(BUILD)/video.o: $(BUILD)/%.o: $(PRODOS)/%.s
	@mkdir -p $(@D)
	$(CA65) -g -o $@ $<
$(BUILD)/mouse.o: $(MOUSE)/mouse.s
	@mkdir -p $(@D)
	$(CA65) -g -o $@ $<
$(BUILD)/apple2frame.o: $(APPLE2C)/apple2frame.s
	@mkdir -p $(@D)
	$(CA65) -g -o $@ $<
# The music interrupt scans the //e clock too: edges read again under SEI.
$(BUILD)/apple2vbl.o: $(APPLE2C)/apple2vbl.s
	@mkdir -p $(@D)
	$(CA65) -g -D A2_VBL_SCAN_SEI=1 -o $@ $<

# The PT3 player (dev/lib/apple2/pt3) and the song, linked for aux $6000.
$(BUILD)/song.pt3: tools/pt3.py tools/sound.py
	@mkdir -p $(@D)
	cd tools && $(PYTHON) pt3.py $(abspath $@)
$(BUILD)/music.o: src/music.s $(BUILD)/song.pt3 $(wildcard $(PT3)/*.s $(PT3)/*.inc)
	$(CA65) -g -I $(APPLE2) --bin-include-dir $(BUILD) -o $@ $<

$(BUILD)/game.bin: $(OBJS) $(LIB_OBJS) src/game.cfg
	$(LD65) -C src/game.cfg -m $(BUILD)/game.map -Ln $(BUILD)/game.lbl -o $@ \
		$(OBJS) $(LIB_OBJS) none.lib
$(BUILD)/WG2.SYS: $(BUILD)/game.bin src/startup.s $(PRODOS_SYS_CFG)
	$(CA65) --bin-include-dir $(BUILD) -o $(BUILD)/startup.o src/startup.s
	$(LD65) -C $(PRODOS_SYS_CFG) -o $@ $(BUILD)/startup.o
$(BUILD)/WG2.SYSTEM: src/boot.s $(PRODOS_SYSBOOT_DEPS)
	@mkdir -p $(@D)
	$(CA65) -I $(PRODOS) -o $(BUILD)/boot.o src/boot.s
	$(LD65) -C $(PRODOS_SYSBOOT_CFG) -o $@ $(BUILD)/boot.o

# WG2.AUX: the packs at aux $2000, the PT3 player and song at $6000, the
# overlay (shop, Memory Station, title) at $7000, Meteor Storm's code and
# the demo's player (for $0800) at $9000, the resident data for $1C40 at
# $9800, the level records at $9C00, the walls' textures at $A000 (each
# padded to the next).
$(BUILD)/WG2.AUX: tools/sprites.py tools/walls.py $(BUILD)/game.bin
	@mkdir -p $(@D)
	$(PYTHON) tools/sprites.py --aux $@.packs
	$(PYTHON) tools/walls.py --aux $@.walls
	$(PYTHON) -c "import sys; r = lambda f: open(f, 'rb').read(); p, m, s = map(r, sys.argv[1:4]); \
		l, h, v, w = map(r, sys.argv[4:8]); open(sys.argv[8], 'wb').write(p.ljust(0x4000, b'\0') \
		+ m.ljust(0x1000, b'\0') + s.ljust(0x2000, b'\0') + l.ljust(0x800, b'\0') + h.ljust(0x400, b'\0') \
		+ v.ljust(0x400, b'\0') + w)" $@.packs $(BUILD)/game.bin.mus $(BUILD)/game.bin.shop $(BUILD)/game.bin.low \
		$(BUILD)/game.bin.hi $(BUILD)/game.bin.lv $@.walls $@
$(DISK): $(BUILD)/WG2.SYSTEM $(BUILD)/WG2.SYS $(BUILD)/WG2.AUX $(BUILD)/HIGHSCORES $(DEV)/tools/prodos/PRODOS $(DEV)/tools/prodos/boot.bin $(DEV)/tools/prodos/build_volume.py
	@rm -rf $(BUILD)/stage
	@mkdir -p $(BUILD)/stage $(DIST)
	cp $(DEV)/tools/prodos/PRODOS $(BUILD)/stage/PRODOS#FF0000
	cp $(BUILD)/WG2.SYSTEM $(BUILD)/stage/WG2.SYSTEM#FF2000
	cp $(BUILD)/WG2.SYS $(BUILD)/stage/WG2.SYS#FF2000
	cp $(BUILD)/WG2.AUX $(BUILD)/stage/WG2.AUX#060000
	cp $(BUILD)/HIGHSCORES $(BUILD)/stage/HIGHSCORES#060000
	$(PYTHON) $(DEV)/tools/prodos/build_volume.py $(BUILD)/stage $@ \
		--volume WARGALAGAII --boot $(DEV)/tools/prodos/boot.bin --blocks 280

run-iic: all
	$(POM2) --preset iic --slot 4=iicmouse $(DISK)

# Two tiers (convention of ../dev/cc65/apple2.mk): `test` stays fast.
test: all $(if $(A2SHOT_HOST),$(BUILD)/iic_probe)
	$(PYTHON) tests/test_difficulty.py
	$(PYTHON) tools/sprites.py --check
	$(PYTHON) tools/hud.py --check
	$(PYTHON) tools/paths.py --check
	$(PYTHON) tools/sound.py --check
	cd tools && $(PYTHON) bonus.py --check
	$(PYTHON) tools/demo.py --check
	$(PYTHON) tests/test_game.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_screen.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_audio.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_shop.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_subgames.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_front.py --disk $(DISK) --labels $(BUILD)/game.lbl
ifneq ($(A2SHOT_HOST),)
	$(PYTHON) tests/test_iic.py --probe $(BUILD)/iic_probe --roms $(DEV)/tools/a2shot/roms --disk $(DISK) --labels $(BUILD)/game.lbl
endif
test-long: test
	$(PYTHON) tests/test_long.py --disk $(DISK) --labels $(BUILD)/game.lbl


.PHONY: run-iic test test-long
