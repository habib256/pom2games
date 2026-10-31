# ROBOT SPACE STATION — Apple //e enhanced / //c 128 KB, ProDOS 8, DHGR, mouse.
#
#   make            -> ../dist/ROBOTSTATION.po
#   make run        -> POM2, //e enhanced with an AppleMouse in slot 4
#   make run-iic    -> POM2, //c (built-in mouse)
#   make test       -> reference model, then the lab and the missions on //e and //c (a2shot)
#   make test-long  -> the whole campaign, each mission's solution in C == the model, and random
#                      boards' turns == the model's Sim, random drones in the rooms ==
#                      its Zone (//e, //c)
#
# C (cc65) on the shared DHGR, gfx, ProDOS and mouse libraries; the logic
# simulation follows tools/model.py bit for bit (docs/SPEC.md).
DEV ?= ../dev
APPLE2_PRESET := iie
APPLE2_RUN_FLAGS := --slot 4=mouse
include $(DEV)/cc65/apple2.mk
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
PRODOS := $(DEV)/lib/prodos
MOUSE := $(DEV)/lib/mouse
include $(PRODOS)/prodos.mk
include $(MOUSE)/mouse.mk

DISK := $(DIST)/ROBOTSTATION.po
SRCS := src/main.c src/ui.c src/board_ui.c src/zone.c src/sim.c src/title.c src/help.c src/hover.c src/sprites.c src/symbol.s \
        src/pointer.s src/swap.s src/text.s src/overlay.s
LIB_SRCS := $(sort $(HGRC_DHGR_SRCS) $(HGRC_DHGR_SMALL_TEXT_SRCS)) $(HGRC_DHGR_COLOR_BACKEND) \
            $(GFX)/gfx_line.c $(APPLE2C_SRCS) $(APPLE2C_FRAME_SRCS) \
            $(PRODOS_SRCS) $(PRODOS_FILE_SRCS) $(MOUSE_SRCS)
# (the speaker's tone right after crt0: its timed loops must not cross a
# page, wherever the game's code grows; dev/lib/apple2/sound.asm asserts it)
OBJS := $(BUILD)/crt0_prodos.o $(BUILD)/apple2game_asm.o $(addprefix $(BUILD)/,$(notdir $(SRCS:.c=.o)))
OBJS := $(OBJS:.s=.o)
LIB_OBJS := $(addprefix $(BUILD)/,$(notdir $(LIB_SRCS:.c=.o)))
LIB_OBJS := $(LIB_OBJS:.s=.o)
GAME_LIB := $(BUILD)/platform.lib
CFLAGS := -t none --cpu 65c02 -Ors -I src $(HGRC_INCS) $(APPLE2C_INCS) $(PRODOS_INCS) $(MOUSE_INCS)
vpath %.c src $(HGRC) $(APPLE2C) $(GFX)
vpath %.s src $(GFX) $(DEV)/cc65 $(HGRC) $(APPLE2C) $(PRODOS) $(MOUSE)

all: $(DISK)

# The missions: count and goals in src/room.h, the rooms in RSS.ROOMS.
src/room.h $(BUILD)/RSS.ROOMS: tools/gen_room.py tools/model.py
	@mkdir -p $(BUILD)
	$(PYTHON) tools/gen_room.py $(BUILD)/RSS.ROOMS
$(BUILD)/zone.o: src/room.h
# Every text (tools/gen_text.py): ids in src/text.h, the bank in RSS.TEXT1/2.
src/text.h $(BUILD)/RSS.TEXT1 $(BUILD)/RSS.TEXT2: tools/gen_text.py tools/model.py
	@mkdir -p $(BUILD)
	$(PYTHON) tools/gen_text.py $(BUILD)

$(BUILD)/%.o: %.c $(wildcard src/*.h) $(HGRC_HEADERS) $(wildcard $(PRODOS)/*.h $(MOUSE)/*.h)
	@mkdir -p $(@D)
	$(CL65) $(CFLAGS) -c -o $@ $<
$(BUILD)/%.o: %.s $(HGRC_ASM_DEPS)
	@mkdir -p $(@D)
	$(CA65) -t none -I $(HGRC) -I $(APPLE2) -I $(PRODOS) -o $@ $<
$(BUILD)/file.o: $(PRODOS_FILE_DEPS)
$(GAME_LIB): $(LIB_OBJS) Makefile
	$(PYTHON) -c 'from pathlib import Path; Path("$@").unlink(missing_ok=True)'
	$(AR65) a $@ $(LIB_OBJS)
# The overlays in $4000-$5FFF (src/game.cfg, src/overlay.s): PLAY and
# FRONT; hover.c resident in L8 at $0C40.
$(BUILD)/zone.o $(BUILD)/sprites.o: CFLAGS += --code-name PLAYCODE --rodata-name PLAYDATA
$(BUILD)/title.o $(BUILD)/help.o: CFLAGS += --code-name FRONTCODE --rodata-name FRONTDATA
$(BUILD)/hover.o: CFLAGS += --code-name L8CODE --rodata-name L8DATA
$(BUILD)/game.bin.ovl: $(BUILD)/game.bin
$(BUILD)/game.bin: $(OBJS) $(GAME_LIB) src/game.cfg
	$(CL65) -t none -C src/game.cfg -m $(BUILD)/game.map -Ln $(BUILD)/game.lbl -o $@ $(OBJS) $(GAME_LIB)
$(BUILD)/RSS.SYS: $(BUILD)/game.bin src/startup.s $(PRODOS_SYS_CFG)
	$(CA65) --bin-include-dir $(BUILD) -o $(BUILD)/startup.o src/startup.s
	$(LD65) -C $(PRODOS_SYS_CFG) -o $@ $(BUILD)/startup.o
$(BUILD)/RSS.SYSTEM: src/boot.s $(PRODOS_SYSBOOT_DEPS)
	@mkdir -p $(@D)
	$(CA65) -I $(PRODOS) -o $(BUILD)/boot.o src/boot.s
	$(LD65) -C $(PRODOS_SYSBOOT_CFG) -o $@ $(BUILD)/boot.o
$(DISK): $(BUILD)/RSS.SYS $(BUILD)/game.bin.ovl $(BUILD)/RSS.SYSTEM $(BUILD)/RSS.ROOMS $(BUILD)/RSS.TEXT1 $(BUILD)/RSS.TEXT2 $(DEV)/tools/prodos/PRODOS $(DEV)/tools/prodos/boot.bin $(DEV)/tools/prodos/build_volume.py
	@rm -rf $(BUILD)/stage
	@mkdir -p $(BUILD)/stage $(DIST)
	cp $(DEV)/tools/prodos/PRODOS $(BUILD)/stage/PRODOS#FF0000
	cp $(BUILD)/RSS.SYSTEM $(BUILD)/stage/RSS.SYSTEM#FF2000
	cp $(BUILD)/RSS.SYS $(BUILD)/stage/RSS.SYS#FF2000
	cp $(BUILD)/RSS.ROOMS $(BUILD)/stage/RSS.ROOMS#060000
	cp $(BUILD)/RSS.TEXT1 $(BUILD)/stage/RSS.TEXT1#060000
	cp $(BUILD)/RSS.TEXT2 $(BUILD)/stage/RSS.TEXT2#060000
	cp $(BUILD)/game.bin.ovl $(BUILD)/stage/RSS.OVL#060000
	$(PYTHON) $(DEV)/tools/prodos/build_volume.py $(BUILD)/stage $@ \
		--volume ROBOT.STATION --boot $(DEV)/tools/prodos/boot.bin --blocks 280

run-iic: all
	$(POM2) --preset iic --slot 4=iicmouse $(DISK)

test: all
	$(PYTHON) tests/test_model.py
	$(PYTHON) tests/test_lab.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_zone.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_lab.py --disk $(DISK) --labels $(BUILD)/game.lbl --iic
	$(PYTHON) tests/test_zone.py --disk $(DISK) --labels $(BUILD)/game.lbl --iic

test-long: all
	$(PYTHON) tests/test_campaign.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_campaign.py --iic --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_fuzz.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_fuzz.py --iic --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_zone_fuzz.py --disk $(DISK) --labels $(BUILD)/game.lbl
	$(PYTHON) tests/test_zone_fuzz.py --iic --disk $(DISK) --labels $(BUILD)/game.lbl

.PHONY: run-iic test test-long
