# MB TRACKER — a Mockingboard tracker, Apple //e enhanced / //c 128 KB,
# ProDOS 8, 80 columns. Edits and plays AYS v1 songs (the format games
# embed: dev/lib/apple2/AYSONG_FORMAT.md).
#
#   make            -> ../dist/MBTRACKER.po (MBT.SYSTEM, MBT.SYS, MBT.OVL, MBT.HELP,
#                      DEMO.AYS, WG.AYS)
#   make run        -> POM2, //e enhanced with a Mockingboard in slot 4
#   make run-iic    -> POM2, //c with a Mockingboard 4c
#   make test       -> a2shot with a Mockingboard on //e and //c, and without
#
# C (cc65) for the editor; src/mbt_asm.s wraps the asm libraries
# (mockingboard.asm, mb_irq.asm, aysong.asm), the 80-column text and the
# aux memory copies.
DEV ?= ../dev
APPLE2_PRESET := iie
APPLE2_RUN_FLAGS := --slot 4=mockingboard
include $(DEV)/cc65/apple2.mk
include $(APPLE2C)/apple2c.mk
PRODOS := $(DEV)/lib/prodos
include $(PRODOS)/prodos.mk

DISK := $(DIST)/MBTRACKER.po
AUDIO_TOOLS := $(DEV)/tools/audio
MOUSE := $(DEV)/lib/mouse
MOUSE_SRCS := $(MOUSE)/mouse.s              # (not mouse.mk: its run-iic is ours)
MOUSE_INCS := -I $(MOUSE)
OBJS := $(BUILD)/entry.o $(BUILD)/crt0_prodos.o $(BUILD)/main.o $(BUILD)/song.o $(BUILD)/files.o \
        $(BUILD)/insed.o $(BUILD)/fileui.o $(BUILD)/voices.o $(BUILD)/mbt_asm.o
LIB_SRCS := $(PRODOS_SRCS) $(PRODOS_FILE_SRCS) $(MOUSE_SRCS)
LIB_OBJS := $(addprefix $(BUILD)/,$(notdir $(LIB_SRCS:.s=.o)))
CFLAGS := -t none --cpu 65c02 -Ors --static-locals -I src $(PRODOS_INCS) $(MOUSE_INCS)
vpath %.c src
vpath %.s src $(DEV)/cc65 $(PRODOS) $(MOUSE)

all: $(DISK)

$(BUILD)/%.o: %.c src/mbt.h src/ui.h $(PRODOS)/prodos.h $(MOUSE)/mouse.h
	@mkdir -p $(@D)
	$(CL65) $(CFLAGS) -c -o $@ $<
$(BUILD)/mbt_asm.o: src/mbt_asm.s $(APPLE2)/mockingboard.asm $(APPLE2)/mb_irq.asm $(APPLE2)/aysong.asm
	@mkdir -p $(@D)
	$(CA65) -t none -g -I $(APPLE2) -o $@ $<
$(BUILD)/file.o: $(PRODOS_FILE_DEPS)
$(BUILD)/%.o: %.s
	@mkdir -p $(@D)
	$(CA65) -t none -g -I $(PRODOS) -o $@ $<

# (ld65 also writes the overlays OVL1 + OVL2: mbt.bin.ovl, MBT.OVL)
$(BUILD)/mbt.bin: $(OBJS) $(LIB_OBJS) src/mbt.cfg
	$(CL65) -t none -C src/mbt.cfg -m $(BUILD)/mbt.map -Ln $(BUILD)/mbt.lbl -o $@ $(OBJS) $(LIB_OBJS)

# The demo song of dev/tools/audio/aysong.py, on the disk as DEMO.AYS.
$(BUILD)/DEMO.AYS: $(AUDIO_TOOLS)/aysong.py $(AUDIO_TOOLS)/notes.py
	@mkdir -p $(@D)
	$(PYTHON) $(AUDIO_TOOLS)/aysong.py --demo -o $@

# WARGALAGA II's music (the repo's own, GPL-3.0): its PT3 module written by
# ../wargalagaii/tools/pt3.py, imported by dev/tools/audio/pt3import.py
# (25 Hz in the game: retimed for 50 Hz), on the disk as WG.AYS.
WG_TOOLS := ../wargalagaii/tools
$(BUILD)/WG.AYS: $(WG_TOOLS)/pt3.py $(WG_TOOLS)/sound.py $(AUDIO_TOOLS)/pt3import.py $(AUDIO_TOOLS)/pt3play.py $(AUDIO_TOOLS)/aysong.py
	@mkdir -p $(@D)
	cd $(WG_TOOLS) && $(PYTHON) pt3.py $(abspath $(BUILD)/wg.pt3)
	$(PYTHON) $(AUDIO_TOOLS)/pt3import.py $(BUILD)/wg.pt3 -o $@ --rate 25 --to-50hz

# The help pages, in aux memory from boot (tools/help.py).
$(BUILD)/MBT.HELP: tools/help.py
	@mkdir -p $(@D)
	$(PYTHON) tools/help.py $@

$(DISK): $(BUILD)/mbt.bin $(BUILD)/MBT.SYSTEM $(BUILD)/DEMO.AYS $(BUILD)/WG.AYS $(BUILD)/MBT.HELP $(PRODOS_VOLUME_DEPS)
	$(call prodos_volume,$@,MBTRACKER,$(BUILD)/MBT.SYSTEM=MBT.SYSTEM#FF2000 \
		$(BUILD)/mbt.bin=MBT.SYS#FF2000 $(BUILD)/DEMO.AYS=DEMO.AYS#060000 $(BUILD)/WG.AYS=WG.AYS#060000 \
		$(BUILD)/MBT.HELP=MBT.HELP#040000 $(BUILD)/mbt.bin.ovl=MBT.OVL#060000)

run-iic: all
	$(POM2) --preset iic --slot 4=mockingboard $(DISK)
# //e with the card in slot 4 and an AppleMouse in slot 2
run-mouse: all
	$(POM2) --preset iie --slot 4=mockingboard --slot 2=mouse $(DISK)

test: all
	$(PYTHON) tests/test_mbt.py

# Long tier (convention of ../dev/cc65/apple2.mk): nothing slow yet.
test-long:
	@echo "mbtracker: no long tests"

.PHONY: test test-long run-iic run-mouse
