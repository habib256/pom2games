# VERHILLE Arnaud — GPL-3.0. CUTROPE: a "Cut the Rope"-like for the Apple II+
# 48 KB, DOS 3.3, HGR, assembly (dev/lib only).
#
#   make            -> ../dist/CUTROPE.dsk (boots into the game; + dist/woz/)
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> 6502 physics == tools/cutrope.py, then the disk in a2run
#   python3 tools/cutrope.py        the levels' solutions on the model
DEV ?= ../dev
include $(DEV)/cc65/apple2.mk
MOUSE := $(DEV)/lib/mouse
APPLE2_RUN_FLAGS := --slot 4=mouseaw

DISK := $(DIST)/CUTROPE.dsk
SRCS := src/cutrope.s src/phys.inc src/physdefs.inc src/cutconst.inc src/disk.inc src/menu.inc
TOOLS := tools/cutrope.py tools/levels.py $(wildcard $(DEV)/tools/verlet/*.py)

all: $(DISK)

src/cutconst.inc: $(TOOLS) $(DEV)/tools/audio/tune.py $(DEV)/tools/audio/notes.py
	$(PYTHON) tools/cutrope.py $@

$(BUILD)/levels.bin: $(TOOLS)
	@mkdir -p $(BUILD)
	$(PYTHON) tools/cutrope.py --levels $@

$(BUILD)/save.bin: $(TOOLS)
	@mkdir -p $(BUILD)
	$(PYTHON) tools/cutrope.py --save $@

$(BUILD)/cutrope.o: $(SRCS) $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none -g $(A2_INCS) -l $(BUILD)/cutrope.lst -o $@ $<

# the AppleMouse: the cursor's box (x 0..252: the game keeps x >= 3)
$(BUILD)/mouse.o: $(MOUSE)/mouse.s
	@mkdir -p $(BUILD)
	$(CA65) -D MOUSE_X_HIGH=252 -D MOUSE_X_START=128 -D MOUSE_Y_LOW=19 -D MOUSE_Y_HIGH=187 \
		-D MOUSE_Y_START=100 -o $@ $<

$(BUILD)/cutrope.bin: $(BUILD)/cutrope.o $(BUILD)/mouse.o $(A2_HGR_CFG)
	$(LD65) -C $(A2_HGR_CFG) -m $(BUILD)/cutrope.map -Ln $(BUILD)/cutrope.lbl -o $@ $(BUILD)/cutrope.o \
		$(BUILD)/mouse.o

# LEVELS (a level a sector) and CUTSAVE (the stars won): read and written
# through RWTS, where they lie patched into CUTROPE (disk.inc)
$(DISK): $(BUILD)/cutrope.bin $(BUILD)/levels.bin $(BUILD)/save.bin $(DOS33_DEPS) $(DOS33PATCH_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin CUTROPE=$<@$(LOAD) --bin LEVELS=$(BUILD)/levels.bin@0x0900 \
		--bin CUTSAVE=$(BUILD)/save.bin@0x0A00
	$(DOS33PATCH) $@ CUTROPE $(BUILD)/cutrope.lbl --sectors lvl_t lvl_s LEVELS --sectors sav_t sav_s CUTSAVE

test: all $(A2RUN)
	$(PYTHON) tests/test_cutrope.py
	$(PYTHON) tests/test_cutrope_mouse.py

# every level's solution on the disk: the cycles and the cadence
test-long: all $(A2RUN)
	$(PYTHON) tests/test_cutrope_disk.py --all

.PHONY: test test-long
