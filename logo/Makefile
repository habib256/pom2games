# LOGO — Apple II / DOS 3.3 build (APPLE-1 LOGO V2.6, GEN2 HGR edition)
#
#   make            -> ../dist/LOGO.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple //e (80 columns)
#   make clean      -> remove build/ (the disk stays)
#   make distclean  -> remove build/ and the disk
#
# Needs cc65 (ca65/ld65) and python3 only; the shared rules and tool
# variables come from ../dev/cc65/apple2.mk.

DEV     ?= ../dev
LOAD    := 0x4000
APPLE2_PRESET := iie
include $(DEV)/cc65/apple2.mk

# CODETANK_BUILD = the full feature set (LABEL, SAY, LIST, EDIT, DEMO2);
# LOGO_HGR = the HGR code paths of the shared interpreter.
DEFS    := -D CODETANK_BUILD -D LOGO_HGR
DISK    := $(DIST)/LOGO.dsk
BIN     := $(BUILD)/logo.bin

# logo.o FIRST: its CODE segment starts with `jmp main`.
MODS    := logo hgr_logom2 text_bitmap math sprite_helpers sprites_emotes bubble buffer_editor
OBJS    := $(MODS:%=$(BUILD)/%.o)
LIBDEPS := $(wildcard src/*.inc) $(A2_ASM_DEPS)

all: $(DISK)

$(BUILD)/logo.o: src/logo.s src/screen.asm $(LIBDEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none $(A2_INCS) $(DEFS) -l $(BUILD)/logo.lst -o $@ $<

$(BUILD)/%.o: src/%.asm $(LIBDEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none $(A2_INCS) $(DEFS) -o $@ $<

$(BIN): $(OBJS) src/logo.cfg
	$(LD65) -C src/logo.cfg -m $(BUILD)/logo.map -o $@ $(OBJS)
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(DISK): $(BIN) $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin LOGO=$(BIN)@$(LOAD) --catalog
