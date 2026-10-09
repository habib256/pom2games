DEV ?= ../dev
include $(DEV)/cc65/apple2.mk
include $(APPLE2C)/apple2c.mk
include $(HGRC)/hgrc.mk

DISK := $(DIST)/MCS.dsk
BIN := $(BUILD)/mcs.bin
CFLAGS := -t none -Oirs -I $(HGRC) -I $(APPLE2C) -I src
AFLAGS := -t none -I $(APPLE2)
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS) $(APPLE2C_DOS_SRCS)
OBJS := $(BUILD)/crt0_apple2.o $(BUILD)/mcs.o $(BUILD)/audio.o
vpath %.c src
vpath %.s src $(DEV)/cc65

all: $(DISK)

$(BUILD)/%.o: %.c src/song.h $(BUILD)/pitches.h $(HGRC_HEADERS)
	@mkdir -p $(BUILD)
	$(CL65) $(CFLAGS) -I $(BUILD) -c -o $@ $<

$(BUILD)/%.o: %.s $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) $(AFLAGS) -o $@ $<

$(BUILD)/pitches.h $(BUILD)/song.bin: tools/assets.py
	@mkdir -p $(BUILD)
	$(PYTHON) tools/assets.py $(BUILD)

$(BUILD)/mcs.cfg: $(A2_HGR_C_CFG) tools/link_config.py
	@mkdir -p $(BUILD)
	$(PYTHON) tools/link_config.py $< $@

$(BIN): $(OBJS) $(HGRC_LIB) $(BUILD)/mcs.cfg Makefile
	$(CL65) -t none -C $(BUILD)/mcs.cfg -m $(BUILD)/mcs.map -Ln $(BUILD)/mcs.lbl -o $@ $(OBJS) $(HGRC_LIB)

$(DISK): $(BIN) $(BUILD)/song.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin MCS=$(BIN)@$(LOAD) --bin SONG=$(BUILD)/song.bin@0x1000 --catalog

test: all $(A2RUN)
	$(PYTHON) tests/test_mcs.py

include $(HGRC)/hgrc_build.mk
.PHONY: test
