# VERHILLE Arnaud — GPL-3.0. Standalone HGR starter, II+ / IIe / IIc.
CL65 ?= cl65
CA65 ?= ca65
PYTHON ?= python3
DEV ?= ../..
DIST ?= ../../../dist
BUILD ?= build
POM2 ?= /Applications/POM2.app/Contents/MacOS/POM2
HGRC := $(DEV)/lib/hgrc
GFX := $(DEV)/lib/gfx
APPLE2C := $(DEV)/lib/apple2c
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS) $(APPLE2C_FRAME_SRCS)
# Keep the three-ball demo inside the 48 KB layout by avoiding inlined
# runtime helpers in both the demo and its private library archive.
HGRC_CFLAGS := -t none -Ors $(HGRC_INCS) $(APPLE2C_INCS)

all: $(DIST)/HGR.dsk

$(BUILD)/crt0_apple2.o: $(DEV)/cc65/crt0_apple2.s
	@mkdir -p $(@D)
	$(CA65) -t none -o $@ $<

$(BUILD)/hgr_demo.o: src/hgr_demo.c src/ball.h $(HGRC_HEADERS) $(wildcard $(APPLE2C)/*.h)
	@mkdir -p $(@D)
	$(CL65) -t none -Ors $(HGRC_INCS) $(APPLE2C_INCS) -c -o $@ $<

$(BUILD)/hgr.bin: $(BUILD)/crt0_apple2.o $(BUILD)/hgr_demo.o $(HGRC_LIB) $(DEV)/cc65/apple2_hgr_c.cfg
	$(CL65) -t none -C $(DEV)/cc65/apple2_hgr_c.cfg -m $(BUILD)/hgr.map -Ln $(BUILD)/hgr.lbl -o $@ $(BUILD)/crt0_apple2.o $(BUILD)/hgr_demo.o $(HGRC_LIB)

$(DIST)/HGR.dsk: $(BUILD)/hgr.bin src/hello.bas $(DEV)/tools/dos33.py $(DEV)/tools/dos33_system.bin
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(DEV)/tools/dos33_system.bin --out $@ --bas HELLO=src/hello.bas --bin HGR=$(BUILD)/hgr.bin@0x6000

include $(HGRC)/hgrc_build.mk

assets:
	$(PYTHON) $(DEV)/tools/assets/convert.py src/ball_source.png --out src/ball --mode hgr --kind sprite --name ball

run: all
	$(POM2) --preset ii+ $(DIST)/HGR.dsk

test:
	$(PYTHON) $(DEV)/tests/test_hgr_example.py

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(DIST)/HGR.dsk

.PHONY: all assets run test clean distclean
