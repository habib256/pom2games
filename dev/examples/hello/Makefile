# hello — the two starter programs for dev/lib (asm + C) on one DOS 3.3 disk
#
#   make            -> ../../../dist/HELLO.dsk   (boots into HELLOASM; then BRUN HELLOC)
#   make run        -> boot it in POM2 as an Apple II+
#
# Copy this folder to start a new Apple II program. Copied next to micro-sokoban/,
# set DEV ?= ../dev and DIST ?= ../dist so the disk joins the others.

CA65    ?= ca65
CL65    ?= cl65
LD65    ?= ld65
PYTHON  ?= python3
DEV     ?= ../..
POM2    ?= /Applications/POM2.app/Contents/MacOS/POM2
SYSTEM  ?= $(DEV)/tools/dos33_system.bin

APPLE2  := $(DEV)/lib/apple2
APPLE2C := $(DEV)/lib/apple2c
include $(APPLE2C)/apple2c.mk

BUILD   := build
DIST    ?= ../../../dist
DISK    := $(DIST)/HELLO.dsk
LOAD    := 0x6000

all: $(DISK)

# --- asm track ---------------------------------------------------------------
$(BUILD)/hello_asm.o: src/hello_asm.s $(wildcard $(APPLE2)/*)
	@mkdir -p $(BUILD)
	$(CA65) -t none -I $(APPLE2) -o $@ $<

$(BUILD)/hello_asm.bin: $(BUILD)/hello_asm.o $(DEV)/cc65/apple2_hgr.cfg
	$(LD65) -C $(DEV)/cc65/apple2_hgr.cfg -o $@ $<

# --- C track (crt0_apple2 first) ---------------------------------------------
C_OBJS := $(BUILD)/crt0_apple2.o $(BUILD)/hello_c.o $(BUILD)/apple2io.o $(BUILD)/apple2io_asm.o

$(BUILD)/crt0_apple2.o: $(DEV)/cc65/crt0_apple2.s
	@mkdir -p $(BUILD)
	$(CA65) -t none -o $@ $<
$(BUILD)/apple2io_asm.o: $(APPLE2C)/apple2io_asm.s
	@mkdir -p $(BUILD)
	$(CA65) -t none -o $@ $<
$(BUILD)/apple2io.o: $(APPLE2C)/apple2io.c $(APPLE2C)/apple2io.h
	@mkdir -p $(BUILD)
	$(CL65) -t none -Oirs $(APPLE2C_INCS) -c -o $@ $<
$(BUILD)/hello_c.o: src/hello_c.c $(APPLE2C)/apple2io.h
	@mkdir -p $(BUILD)
	$(CL65) -t none -Oirs $(APPLE2C_INCS) -c -o $@ $<

$(BUILD)/hello_c.bin: $(C_OBJS) $(DEV)/cc65/apple2_hgr_c.cfg
	$(CL65) -t none -C $(DEV)/cc65/apple2_hgr_c.cfg -o $@ $(C_OBJS)

# --- disk --------------------------------------------------------------------
$(DISK): $(BUILD)/hello_asm.bin $(BUILD)/hello_c.bin src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ \
	    --bas HELLO=src/hello.bas \
	    --bin HELLOASM=$(BUILD)/hello_asm.bin@$(LOAD) \
	    --bin HELLOC=$(BUILD)/hello_c.bin@$(LOAD) \
	    --catalog

run: $(DISK)
	$(POM2) --preset ii+ $(DISK)

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(DISK)

.PHONY: all run clean distclean
