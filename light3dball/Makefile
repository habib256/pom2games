DEV ?= ../dev
include $(DEV)/cc65/apple2.mk
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
DISK := $(DIST)/LIGHT3DBALL.dsk
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS) $(APPLE2C_FRAME_SRCS)
HGRC_CFLAGS := -t none -Ors $(HGRC_INCS) $(APPLE2C_INCS)

all: $(DISK)

$(BUILD)/assets.h: tools/assets.py levels.json
	@mkdir -p $(@D)
	$(PYTHON) $< $@

$(BUILD)/background.h $(BUILD)/mousemap.h $(BUILD)/levels.h: $(BUILD)/assets.h
	@test -s $@ || $(PYTHON) tools/assets.py $(BUILD)/assets.h

$(BUILD)/game.cfg: src/game.cfg Makefile
	@mkdir -p $(@D)
	$(PYTHON) -c 'from pathlib import Path; import sys; Path(sys.argv[2]).write_text(Path(sys.argv[1]).read_text().replace("build/assets.bin", sys.argv[3]))' "$<" "$@" "$(BUILD)/assets.bin"

$(BUILD)/crt0.o: $(A2_CRT0)
	@mkdir -p $(@D)
	$(CA65) -t none -o $@ $<

$(BUILD)/game.o: src/game.c $(BUILD)/assets.h $(BUILD)/background.h $(BUILD)/mousemap.h $(BUILD)/levels.h $(HGRC_HEADERS) $(DEV)/lib/mouse/mouse.h
	$(CL65) -t none -Ors $(HGRC_INCS) $(APPLE2C_INCS) -I $(DEV)/lib/mouse -I $(BUILD) -c -o $@ $<

$(BUILD)/render.o: src/render.s $(A2_ASM_DEPS)
	@mkdir -p $(@D)
	$(CA65) -t none $(A2_INCS) -o $@ $<

$(BUILD)/mouse.o: $(DEV)/lib/mouse/mouse.s
	@mkdir -p $(@D)
	$(CA65) -t none -I $(APPLE2) -o $@ $<

$(BUILD)/physics.o: src/physics.s
	@mkdir -p $(@D)
	$(CA65) -t none -o $@ $<

$(BUILD)/levels.o: src/levels.s
	@mkdir -p $(@D)
	$(CA65) -t none -o $@ $<

$(BUILD)/game.bin: $(BUILD)/crt0.o $(BUILD)/game.o $(BUILD)/render.o $(BUILD)/physics.o $(BUILD)/levels.o $(BUILD)/mouse.o $(HGRC_LIB) $(BUILD)/game.cfg
	$(CL65) -t none -C $(BUILD)/game.cfg -m $(BUILD)/game.map -Ln $(BUILD)/game.lbl -o $@ $(BUILD)/crt0.o $(BUILD)/game.o $(BUILD)/render.o $(BUILD)/physics.o $(BUILD)/levels.o $(BUILD)/mouse.o $(HGRC_LIB)

$(BUILD)/assets.bin: $(BUILD)/game.bin
	@test -s $@ || $(MAKE) -B $(BUILD)/game.bin

$(DISK): $(BUILD)/game.bin $(BUILD)/assets.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin LIGHT3DBALL=$(BUILD)/game.bin@$(LOAD) --bin LCBALL=$(BUILD)/assets.bin@0x11E0

test: all $(A2RUN)
	$(PYTHON) tests/test_game.py
	$(PYTHON) tests/test_physics.py
	$(PYTHON) tests/test_render.py
	$(PYTHON) tests/test_levels.py

include $(HGRC)/hgrc_build.mk
.PHONY: test
