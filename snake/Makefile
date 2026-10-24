# Snake — Apple II+ / DOS 3.3 build (cc65 C)
#
#   make            -> ../dist/SNAKE.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> fast tier: gameplay, sound, joystick, speeds, record (a2run)
#   make clean      -> remove build/ (the disk stays)
#   make distclean  -> remove build/ and the disk
#
# Needs cc65 (cl65/ca65) and python3 only; the shared rules and tool
# variables come from ../dev/cc65/apple2.mk.

DEV     ?= ../dev
include $(DEV)/cc65/apple2.mk
include $(APPLE2C)/apple2c.mk
include $(HGRC)/hgrc.mk

DISK    := $(DIST)/SNAKE.dsk
BIN     := $(BUILD)/snake.bin

# -g: the C statics reach build/snake.lbl for the tests (same binary).
CFLAGS  := -t none -Oirs -g -I $(HGRC) -I $(APPLE2C) -I $(GFX)
AFLAGS  := -t none -I $(APPLE2) -I $(HGRC)
ifneq ($(FIXED_SEED),)
CFLAGS  += -DSNAKE_FIXED_SEED=$(FIXED_SEED)
endif

# crt0_apple2 FIRST: it provides __STARTUP__ / _exit instead of none.lib's crt0.
# Speaker + joystick (apple2game), DOS commands for the record (apple2dos),
# the vapor lock for the pace (apple2vapor).
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS) $(APPLE2C_GAME_SRCS) $(APPLE2C_DOS_SRCS) $(APPLE2C_VAPOR_SRCS)
OBJS := $(BUILD)/crt0_apple2.o $(BUILD)/snake.o

vpath %.c src $(HGRC) $(GFX) $(APPLE2C)
vpath %.s $(DEV)/cc65 $(HGRC) $(APPLE2C)

all: $(DISK)

$(BUILD)/%.o: %.c $(HGRC_HEADERS) $(APPLE2C)/apple2io.h
	@mkdir -p $(BUILD)
	$(CL65) $(CFLAGS) -c -o $@ $<

$(BUILD)/%.o: %.s $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) $(AFLAGS) -o $@ $<

# The C stack peaks at 37 bytes (a2run stackwatch over a whole game): 256
# are reserved instead of 2 KB, and the program area grows to $94FF.
$(BIN): $(OBJS) $(HGRC_LIB) $(A2_HGR_C_CFG) Makefile
	$(CL65) -t none -g -C $(A2_HGR_C_CFG) -Wl -D,__STACKSIZE__=0x0100 \
	    -m $(BUILD)/snake.map -Ln $(BUILD)/snake.lbl -o $@ $(OBJS) $(HGRC_LIB)
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

# HISCORE: the record, two bytes (0 on a new disk). The game BLOADs it at
# start, and DOS would stop the game if it were missing.
$(BUILD)/hiscore.bin:
	@mkdir -p $(BUILD)
	printf '\000\000' > $@

$(DISK): $(BIN) $(BUILD)/hiscore.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin SNAKE=$(BIN)@$(LOAD) --bin HISCORE=$(BUILD)/hiscore.bin@0x1000 --catalog

# Two tiers (convention of ../dev/cc65/apple2.mk).
test: all $(A2RUN)
	$(PYTHON) tests/test_snake.py --disk $(DISK) --labels $(BUILD)/snake.lbl
test-long:
	@echo "snake: no long tests"
.PHONY: test test-long

# $6000-$8DFF is full: the DOS command buffers go to LOWBSS ($1000-$1FFF).
HGRC_AFLAGS += -D DOS_LOWBSS=1
include $(HGRC)/hgrc_build.mk
