# MB TRACKER — a Mockingboard tracker, Apple //e enhanced / //c 128 KB,
# ProDOS 8, 80 columns. Edits and plays AYS v1 songs (the format games
# embed: dev/lib/apple2/AYSONG_FORMAT.md).
#
#   make            -> ../dist/MBTRACKER.po (MBT.SYSTEM, MBT.SYS, DEMO.AYS)
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
OBJS := $(BUILD)/entry.o $(BUILD)/crt0_prodos.o $(BUILD)/main.o $(BUILD)/song.o $(BUILD)/files.o $(BUILD)/mbt_asm.o
LIB_SRCS := $(PRODOS_SRCS) $(PRODOS_FILE_SRCS)
LIB_OBJS := $(addprefix $(BUILD)/,$(notdir $(LIB_SRCS:.s=.o)))
CFLAGS := -t none --cpu 65c02 -Ors --static-locals -I src $(PRODOS_INCS)
vpath %.c src
vpath %.s src $(DEV)/cc65 $(PRODOS)

all: $(DISK)

$(BUILD)/%.o: %.c src/mbt.h $(PRODOS)/prodos.h
	@mkdir -p $(@D)
	$(CL65) $(CFLAGS) -c -o $@ $<
$(BUILD)/mbt_asm.o: src/mbt_asm.s $(APPLE2)/mockingboard.asm $(APPLE2)/mb_irq.asm $(APPLE2)/aysong.asm
	@mkdir -p $(@D)
	$(CA65) -t none -g -I $(APPLE2) -o $@ $<
$(BUILD)/file.o: $(PRODOS_FILE_DEPS)
$(BUILD)/%.o: %.s
	@mkdir -p $(@D)
	$(CA65) -t none -g -I $(PRODOS) -o $@ $<

$(BUILD)/mbt.bin: $(OBJS) $(LIB_OBJS) src/mbt.cfg
	$(CL65) -t none -C src/mbt.cfg -m $(BUILD)/mbt.map -Ln $(BUILD)/mbt.lbl -o $@ $(OBJS) $(LIB_OBJS)

# The demo song of dev/tools/audio/aysong.py, on the disk as DEMO.AYS.
$(BUILD)/DEMO.AYS: $(AUDIO_TOOLS)/aysong.py $(AUDIO_TOOLS)/notes.py
	@mkdir -p $(@D)
	$(PYTHON) $(AUDIO_TOOLS)/aysong.py --demo -o $@

# The help pages, in aux memory from boot (tools/help.py).
$(BUILD)/MBT.HELP: tools/help.py
	@mkdir -p $(@D)
	$(PYTHON) tools/help.py $@

$(DISK): $(BUILD)/mbt.bin $(BUILD)/MBT.SYSTEM $(BUILD)/DEMO.AYS $(BUILD)/MBT.HELP $(PRODOS_VOLUME_DEPS)
	$(call prodos_volume,$@,MBTRACKER,$(BUILD)/MBT.SYSTEM=MBT.SYSTEM#FF2000 \
		$(BUILD)/mbt.bin=MBT.SYS#FF2000 $(BUILD)/DEMO.AYS=DEMO.AYS#060000 \
		$(BUILD)/MBT.HELP=MBT.HELP#040000)

run-iic: all
	$(POM2) --preset iic --slot 4=mockingboard $(DISK)

test: all
	$(PYTHON) tests/test_mbt.py

# Long tier (convention of ../dev/cc65/apple2.mk): nothing slow yet.
test-long:
	@echo "mbtracker: no long tests"

.PHONY: test test-long run-iic
