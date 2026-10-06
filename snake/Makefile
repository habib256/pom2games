# Snake — Apple II+ / DOS 3.3 build (cc65 C)
#
#   make            -> ../dist/SNAKE.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple II+
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

CFLAGS  := -t none -Oirs -I $(HGRC) -I $(APPLE2C) -I $(GFX)
AFLAGS  := -t none -I $(APPLE2) -I $(HGRC)
ifneq ($(FIXED_SEED),)
CFLAGS  += -DSNAKE_FIXED_SEED=$(FIXED_SEED)
endif

# crt0_apple2 FIRST: it provides __STARTUP__ / _exit instead of none.lib's crt0.
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS)
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

$(BIN): $(OBJS) $(HGRC_LIB) $(A2_HGR_C_CFG) Makefile
	$(CL65) -t none -C $(A2_HGR_C_CFG) -m $(BUILD)/snake.map -o $@ $(OBJS) $(HGRC_LIB)
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(DISK): $(BIN) $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin SNAKE=$(BIN)@$(LOAD) --catalog

include $(HGRC)/hgrc_build.mk
