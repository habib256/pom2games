# CHROMABREAK — Apple //e enhanced 128 KB / ProDOS build (DHGR, AppleMouse).
# Tool variables, run / clean / distclean come from ../dev/cc65/apple2.mk.
DEV ?= ../dev
APPLE2_PRESET := iie
APPLE2_RUN_FLAGS := --slot 4=mouseaw
include $(DEV)/cc65/apple2.mk
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
PRODOS := $(DEV)/lib/prodos
MOUSE := $(DEV)/lib/mouse
include $(PRODOS)/prodos.mk
include $(MOUSE)/mouse.mk
DISK := $(DIST)/CHROMABREAK.po
SRCS := src/game.c src/records.c src/spare.s src/render.s src/physics.s src/collision.s src/number.s src/sound.s src/timing.s src/finetext.s src/enemies.s src/tables.s src/finale_music.s
LIB_SRCS := $(HGRC_65C02_NUM_SRCS) $(sort $(HGRC_DHGR_SRCS) $(HGRC_DHGR_SMALL_TEXT_SRCS)) $(APPLE2C_SRCS) $(APPLE2C_FRAME_SRCS) $(PRODOS_SRCS) $(MOUSE_SRCS)
OBJS := $(BUILD)/crt0_prodos.o $(addprefix $(BUILD)/,$(notdir $(SRCS:.c=.o)))
OBJS := $(OBJS:.s=.o)
LIB_OBJS := $(addprefix $(BUILD)/,$(notdir $(LIB_SRCS:.c=.o)))
LIB_OBJS := $(LIB_OBJS:.s=.o)
GAME_LIB := $(BUILD)/platform.lib
CFLAGS := -t none --cpu 65c02 -Ors -I src $(HGRC_INCS) $(APPLE2C_INCS) \
          $(PRODOS_INCS) $(MOUSE_INCS)
vpath %.c src $(HGRC) $(APPLE2C) $(DEV)/lib/prodos
vpath %.s src $(GFX) $(DEV)/cc65 $(HGRC) $(APPLE2C) $(DEV)/lib/prodos $(DEV)/lib/mouse
all: $(DISK)
$(BUILD)/%.o: %.c src/collision_tables.h src/layout.h $(HGRC_HEADERS) $(wildcard $(DEV)/lib/prodos/*.h $(DEV)/lib/mouse/*.h)
	@mkdir -p $(@D)
	$(CL65) $(CFLAGS) -c -o $@ $<
$(BUILD)/%.o: %.s $(DEV)/lib/apple2/apple2.inc
	@mkdir -p $(@D)
	$(CA65) -t none --bin-include-dir src -I src -I $(HGRC) -I $(DEV)/lib/apple2 -o $@ $<
$(BUILD)/render.o: src/layout.inc src/sprite_tables.inc src/levels.inc $(HGRC_ASM_DEPS)
src/sprite_tables.inc src/bg_tiles.inc: tools/generate_sprite_tables.py
	$(PYTHON) tools/generate_sprite_tables.py
$(BUILD)/physics.o $(BUILD)/collision.o $(BUILD)/enemies.o: src/layout.inc
$(BUILD)/finetext.o: src/fine_font.inc src/tables.inc src/levels.inc
$(BUILD)/tables.o: src/tables.inc
src/fine_font.inc: tools/generate_fine_font.py $(DEV)/tools/fonts.py $(DEV)/lib/font/bbfont_glyphs.inc
	$(PYTHON) tools/generate_fine_font.py
$(BUILD)/dhgr_small_asm.o: $(HGRC_ASM_DEPS)
$(BUILD)/levels.bin src/levels.inc: src/levels.txt tools/pack_levels.py
	$(PYTHON) tools/pack_levels.py $(BUILD)/levels.bin
src/layout.inc src/collision_tables.h: src/layout.h tools/generate_layout.py
	$(PYTHON) tools/generate_layout.py
$(BUILD)/game.o $(BUILD)/records.o: src/records.h src/sound.h
$(BUILD)/sound.o: src/music_offsets.inc src/levels.inc src/fine_font.inc src/duet.inc
$(BUILD)/finale_music.o: src/music_fanfare.inc
src/music_aux.inc src/music_offsets.inc src/music_fanfare.inc: tools/generate_music.py
	$(PYTHON) tools/generate_music.py
$(BUILD)/tables.bin: src/payload.s src/payload.cfg src/tables.inc src/fine_font.inc src/bg_tiles.inc $(HGRC)/dhgr_layout.inc
	@mkdir -p $(@D)
	$(CA65) -I $(HGRC) -I src -o $(BUILD)/payload.o src/payload.s
	$(LD65) -C src/payload.cfg -o $@ $(BUILD)/payload.o
$(BUILD)/dhgr_small_asm.o: $(HGRC)/dhgr_small_asm.s
	@mkdir -p $(@D)
	$(CA65) -D DHGR_SMALL_FONT_EXTERNAL=1 -I $(HGRC) -o $@ $(HGRC)/dhgr_small_asm.s
# The mouse height is the paddle's: its travel (layout.h), starting on the floor.
PAD_MIN := $(shell awk '$$2=="CB_PAD_MIN"{print $$3}' src/layout.h)
PAD_Y := $(shell awk '$$2=="CB_PAD_Y"{print $$3}' src/layout.h)
$(BUILD)/mouse.o: $(MOUSE)/mouse.s src/layout.h
	@mkdir -p $(@D)
	$(CA65) -D MOUSE_Y_LOW=$(PAD_MIN) -D MOUSE_Y_HIGH=$(PAD_Y) -D MOUSE_Y_START=$(PAD_Y) -o $@ $<
$(BUILD)/dhgr_small_string.o: $(HGRC)/dhgr_small_string.s $(HGRC_ASM_DEPS)
	@mkdir -p $(@D)
	$(CA65) -D DHGR_SMALL_USE_PROGRESS=1 -I $(HGRC) -o $@ $<
$(GAME_LIB): $(LIB_OBJS) Makefile $(HGRC)/hgrc.mk
	$(PYTHON) -c 'from pathlib import Path; Path("$@").unlink(missing_ok=True)'
	$(AR65) a $@ $(LIB_OBJS)
$(BUILD)/game.bin: $(OBJS) $(GAME_LIB) Makefile $(DEV)/cc65/apple2_dhgr_prodos_c.cfg
	$(CL65) -t none -C $(DEV)/cc65/apple2_dhgr_prodos_c.cfg -m $(BUILD)/game.map -Ln $(BUILD)/game.lbl -o $@ $(OBJS) $(GAME_LIB)
$(BUILD)/CHROMA.SYS: $(BUILD)/game.bin $(BUILD)/tables.bin $(BUILD)/levels.bin src/levels.inc src/fine_font.inc src/music_aux.inc src/music_offsets.inc src/duet.inc src/startup.s src/startup.cfg
	$(CA65) --bin-include-dir $(BUILD) --bin-include-dir src -I src -o $(BUILD)/startup.o src/startup.s
	$(LD65) -C src/startup.cfg -o $@ $(BUILD)/startup.o
$(BUILD)/CHROMA.SYSTEM: src/boot.s src/boot.cfg
	@mkdir -p $(@D)
	$(CA65) -o $(BUILD)/boot.o src/boot.s
	$(LD65) -C src/boot.cfg -o $@ $(BUILD)/boot.o
$(BUILD)/HIGHSCORES: tools/seed_records.py
	@mkdir -p $(@D)
	$(PYTHON) $< $@
$(DISK): $(BUILD)/CHROMA.SYS $(BUILD)/CHROMA.SYSTEM $(BUILD)/HIGHSCORES $(DEV)/tools/prodos/PRODOS $(DEV)/tools/prodos/boot.bin $(DEV)/tools/prodos/build_volume.py
	@mkdir -p $(BUILD)/stage $(DIST)
	cp $(DEV)/tools/prodos/PRODOS $(BUILD)/stage/PRODOS#FF0000
	$(PYTHON) -c 'from pathlib import Path; p=Path("$(BUILD)/stage/STARTUP.SYSTEM#FF2000"); p.unlink(missing_ok=True); p=Path("$(BUILD)/STARTUP.SYSTEM"); p.unlink(missing_ok=True)'
	cp $(BUILD)/CHROMA.SYSTEM $(BUILD)/stage/CHROMA.SYSTEM#FF2000
	cp $(BUILD)/CHROMA.SYS $(BUILD)/stage/CHROMA.SYS#FF2000
	cp $(BUILD)/HIGHSCORES $(BUILD)/stage/HIGHSCORES#060000
	cp $(BUILD)/game.bin.ovl $(BUILD)/stage/ENDING#064000
	$(PYTHON) $(DEV)/tools/prodos/build_volume.py $(BUILD)/stage $@ --volume CHROMABREAK --boot $(DEV)/tools/prodos/boot.bin --blocks 280
run-iic: all
	$(POM2) --preset iic --slot 4=iicmouse $(DISK)
test: all
	$(PYTHON) tests/test_game.py --disk $(DISK) --labels $(BUILD)/game.lbl
.PHONY: run-iic test

# Optional real-firmware integration. Normal build/test has no sibling dependency.
POM2_SRC ?= ../../pom2
test-mouse: all
	$(PYTHON) tests/test_mouse.py --pom2-src $(POM2_SRC) --disk $(DISK) --labels $(BUILD)/game.lbl --build $(BUILD)
test-records: all
	$(PYTHON) tests/test_mouse.py --pom2-src $(POM2_SRC) --disk $(DISK) --labels $(BUILD)/game.lbl --build $(BUILD) --records-only
.PHONY: test-mouse test-records
