# Apple IIe with extended 80-column RAM, or IIc. Not for II/II+.
CL65 ?= cl65
CA65 ?= ca65
PYTHON ?= python3
DEV ?= ../..
DIST ?= ../../../dist
BUILD ?= build
POM2 ?= /Applications/POM2.app/Contents/MacOS/POM2
HGRC := $(DEV)/lib/hgrc
APPLE2C := $(DEV)/lib/apple2c
GFX := $(DEV)/lib/gfx
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
SRCS := $(HGRC_DHGR_SRCS) $(APPLE2C_SRCS) $(APPLE2C_FRAME_SRCS) $(HGRC_DHGR_COLOR_BACKEND) $(GFX)/gfx_circle.c
OBJS := $(BUILD)/crt0_apple2.o $(BUILD)/dhgr_demo.o \
        $(addprefix $(BUILD)/,$(notdir $(SRCS:.c=.o)))
OBJS := $(OBJS:.s=.o)
CFLAGS := -t none -Oirs $(HGRC_INCS) $(APPLE2C_INCS)
vpath %.c src $(HGRC) $(APPLE2C) $(GFX)
vpath %.s $(DEV)/cc65 $(HGRC) $(APPLE2C)

all: $(DIST)/DHGR.dsk

$(BUILD)/%.o: %.c src/ball.h $(HGRC_HEADERS) $(wildcard $(APPLE2C)/*.h)
	@mkdir -p $(@D)
	$(CL65) $(CFLAGS) -c -o $@ $<

$(BUILD)/%.o: %.s $(DEV)/lib/apple2/apple2.inc
	@mkdir -p $(@D)
	$(CA65) -t none $(HGRC_AFLAGS) -o $@ $<

$(BUILD)/dhgr.bin: $(OBJS) $(DEV)/cc65/apple2_hgr_c.cfg
	$(CL65) -t none -C $(DEV)/cc65/apple2_hgr_c.cfg -m $(BUILD)/dhgr.map -o $@ $(OBJS)

$(DIST)/DHGR.dsk: $(BUILD)/dhgr.bin src/hello.bas $(DEV)/tools/dos33.py $(DEV)/tools/dos33_system.bin
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(DEV)/tools/dos33_system.bin \
	    --out $@ --bas HELLO=src/hello.bas --bin DHGR=$(BUILD)/dhgr.bin@0x6000

run: all
	$(POM2) --preset iie $(DIST)/DHGR.dsk

test:
	$(PYTHON) $(DEV)/tests/test_dhgr.py

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(DIST)/DHGR.dsk

.PHONY: all run test clean distclean

assets:
	$(PYTHON) $(DEV)/tools/assets/convert.py src/ball_source.png --out src/ball --mode dhgr --kind sprite --name ball

.PHONY: assets
