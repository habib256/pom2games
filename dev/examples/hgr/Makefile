# VERHILLE Arnaud — GPL-3.0. Standalone HGR starter, II+ / IIe / IIc.
DEV ?= ../..
DIST ?= ../../../dist
include $(DEV)/cc65/apple2.mk
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
DISK := $(DIST)/HGR.dsk
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS) $(APPLE2C_FRAME_SRCS)
# Keep the three-ball demo inside the 48 KB layout by avoiding inlined
# runtime helpers in both the demo and its private library archive.
HGR_SLOT_FLAGS := -D HGR_SPR_MAX=3
HGRC_CFLAGS := -t none -Ors $(HGR_SLOT_FLAGS) $(HGRC_INCS) $(APPLE2C_INCS)

all: $(DISK)

$(BUILD)/crt0_apple2.o: $(A2_CRT0)
	@mkdir -p $(@D)
	$(CA65) -t none -o $@ $<

$(BUILD)/hgr_demo.o: src/hgr_demo.c src/ball.h Makefile $(HGRC_HEADERS) $(wildcard $(APPLE2C)/*.h)
	@mkdir -p $(@D)
	$(CL65) -t none -Ors $(HGR_SLOT_FLAGS) $(HGRC_INCS) $(APPLE2C_INCS) -c -o $@ $<

$(BUILD)/hgr.bin: $(BUILD)/crt0_apple2.o $(BUILD)/hgr_demo.o $(HGRC_LIB) $(A2_HGR_C_CFG)
	$(CL65) -t none -C $(A2_HGR_C_CFG) -m $(BUILD)/hgr.map -Ln $(BUILD)/hgr.lbl -o $@ $(BUILD)/crt0_apple2.o $(BUILD)/hgr_demo.o $(HGRC_LIB)

$(DISK): $(BUILD)/hgr.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin HGR=$(BUILD)/hgr.bin@$(LOAD)

include $(HGRC)/hgrc_build.mk

assets:
	$(PYTHON) $(DEV)/tools/assets/convert.py src/ball_source.png --out src/ball --mode hgr --kind sprite --name ball

test:
	$(PYTHON) $(DEV)/tests/test_hgr_example.py

.PHONY: assets test
