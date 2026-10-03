# DEMO — five Apple II demos on one DOS 3.3 disk, with a menu
#
#   make            -> ../dist/DEMO.dsk
#   make run        -> boot it in POM2 as an Apple II+
#   make clean      -> remove build/ (the disk stays)
#   make distclean  -> remove build/ and the disk
#
# Needs cc65 and python3. All C demos share one archive; ld65 pulls only
# the called routine families and their zero-page state.

CL65    ?= cl65
CA65    ?= ca65
LD65    ?= ld65
AR65    ?= ar65
PYTHON  ?= python3
DEV     ?= ../dev
POM2    ?= /Applications/POM2.app/Contents/MacOS/POM2
SYSTEM  ?= $(DEV)/tools/dos33_system.bin

HGRC    := $(DEV)/lib/hgrc
GFX     := $(DEV)/lib/gfx
APPLE2C := $(DEV)/lib/apple2c
APPLE2  := $(DEV)/lib/apple2
HGR     := $(DEV)/lib/hgr
include $(APPLE2C)/apple2c.mk
include $(HGRC)/hgrc.mk
BUILD   := build
DIST    ?= ../dist
DISK    := $(DIST)/DEMO.dsk
LOAD    := 0x6000

CFLAGS  := -t none -Oirs -I src -I $(HGRC) -I $(APPLE2C) -I $(GFX)
AFLAGS  := -t none -I $(APPLE2) -I $(HGRC)

HGRC_EXTRA_SRCS := $(APPLE2C_SRCS)
HDRS := $(HGRC_HEADERS) $(wildcard $(APPLE2C)/*.h src/*.h)
vpath %.c src $(HGRC) $(GFX) $(APPLE2C)
vpath %.s src $(HGRC) $(APPLE2C) $(DEV)/cc65

C_DEMOS   := bounces animals preshift
ASM_DEMOS := life font

all: $(DISK)

# --- C demos -----------------------------------------------------------------
$(BUILD)/crt0_apple2.o: crt0_apple2.s
	@mkdir -p $(BUILD)
	$(CA65) -t none -o $@ $<

define c_demo
$(BUILD)/$(1)/$(1).o: src/$(1).c $(HDRS) Makefile
	@mkdir -p $$(@D)
	$(CL65) $(CFLAGS) -c -o $$@ $$<

$(BUILD)/$(1).bin: $(BUILD)/crt0_apple2.o $(BUILD)/$(1)/$(1).o $(HGRC_LIB) src/demo_c.cfg Makefile
	$(CL65) -t none -C src/demo_c.cfg -m $(BUILD)/$(1).map -o $$@ \
	    $(BUILD)/crt0_apple2.o $(BUILD)/$(1)/$(1).o $(HGRC_LIB)
	@echo "$(1): $$$$(wc -c < $$@) bytes at $(LOAD)"
endef
$(foreach d,$(C_DEMOS),$(eval $(call c_demo,$(d))))

# --- assembly demos ----------------------------------------------------------
$(BUILD)/%.o: src/%.s $(wildcard $(APPLE2)/*.inc $(APPLE2)/*.asm $(HGR)/*.inc $(HGR)/*.asm)
	@mkdir -p $(BUILD)
	$(CA65) -t none -I $(APPLE2) -I $(HGR) -l $(BUILD)/$*.lst -o $@ $<

$(addprefix $(BUILD)/,$(ASM_DEMOS:=.bin)): $(BUILD)/%.bin: $(BUILD)/%.o $(DEV)/cc65/apple2_hgr.cfg
	$(LD65) -C $(DEV)/cc65/apple2_hgr.cfg -m $(BUILD)/$*.map -o $@ $<
	@echo "$*: $$(wc -c < $@) bytes at $(LOAD)"

# --- disk --------------------------------------------------------------------
BINS := $(addprefix $(BUILD)/,$(C_DEMOS:=.bin) $(ASM_DEMOS:=.bin))

$(DISK): $(BINS) src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ \
	    --bas HELLO=src/hello.bas \
	    --bin BOUNCES=$(BUILD)/bounces.bin@$(LOAD) \
	    --bin ANIMALS=$(BUILD)/animals.bin@$(LOAD) \
	    --bin LIFE=$(BUILD)/life.bin@$(LOAD) \
	    --bin PRESHIFT=$(BUILD)/preshift.bin@$(LOAD) \
	    --bin FONT=$(BUILD)/font.bin@$(LOAD) \
	    --catalog

run: $(DISK)
	$(POM2) --preset ii+ $(DISK)

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(DISK)

.PHONY: all run clean distclean

include $(HGRC)/hgrc_build.mk
