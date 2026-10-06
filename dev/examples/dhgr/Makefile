# Apple IIe with extended 80-column RAM, or IIc. Not for II/II+.
DEV ?= ../..
DIST ?= ../../../dist
APPLE2_PRESET := iie
include $(DEV)/cc65/apple2.mk
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
DISK := $(DIST)/DHGR.dsk
SRCS := $(HGRC_DHGR_SRCS) $(APPLE2C_SRCS) $(APPLE2C_FRAME_SRCS) $(HGRC_DHGR_COLOR_BACKEND) $(GFX)/gfx_circle.c
OBJS := $(BUILD)/crt0_apple2.o $(BUILD)/dhgr_demo.o $(BUILD)/ball_render.o \
        $(addprefix $(BUILD)/,$(notdir $(SRCS:.c=.o)))
OBJS := $(OBJS:.s=.o)
CFLAGS := -t none -Oirs $(HGRC_INCS) $(APPLE2C_INCS)
vpath %.c src $(HGRC) $(APPLE2C) $(GFX)
vpath %.s src $(DEV)/cc65 $(HGRC) $(APPLE2C)

all: $(DISK)

$(BUILD)/%.o: %.c src/ball.h $(HGRC_HEADERS) $(wildcard $(APPLE2C)/*.h)
	@mkdir -p $(@D)
	$(CL65) $(CFLAGS) -c -o $@ $<

$(BUILD)/%.o: %.s $(APPLE2)/apple2.inc
	@mkdir -p $(@D)
	$(CA65) -t none $(HGRC_AFLAGS) -o $@ $<

$(BUILD)/ball_render.o: src/ball.bin src/digits.inc

$(BUILD)/dhgr.bin: $(OBJS) $(A2_HGR_C_CFG)
	$(CL65) -t none -C $(A2_HGR_C_CFG) -m $(BUILD)/dhgr.map -Ln $(BUILD)/dhgr.lbl -o $@ $(OBJS)

$(DISK): $(BUILD)/dhgr.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin DHGR=$(BUILD)/dhgr.bin@$(LOAD)

test:
	$(PYTHON) $(DEV)/tests/test_dhgr.py
	$(PYTHON) $(DEV)/tests/test_dhgr_example.py
	$(PYTHON) $(DEV)/tests/test_dhgr_starter.py

assets:
	$(PYTHON) $(DEV)/tools/assets/convert.py src/ball_source.png --out src/ball --mode dhgr --kind sprite --name ball

.PHONY: assets test
