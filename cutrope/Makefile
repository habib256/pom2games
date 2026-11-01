# VERHILLE Arnaud — GPL-3.0. CUTROPE: a "Cut the Rope"-like for the Apple II+
# 48 KB, DOS 3.3, HGR, assembly (dev/lib only).
#
#   make            -> ../dist/CUTROPE.dsk (boots into the game; + dist/woz/)
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> 6502 physics == tools/cutrope.py, then the disk in a2run
#   python3 tools/cutrope.py        the levels' solutions on the model
DEV ?= ../dev
include $(DEV)/cc65/apple2.mk

DISK := $(DIST)/CUTROPE.dsk
SRCS := src/cutrope.s src/phys.inc src/physdefs.inc src/cutconst.inc

all: $(DISK)

src/cutconst.inc: tools/cutrope.py $(wildcard $(DEV)/tools/verlet/*.py) $(DEV)/tools/audio/tune.py \
		$(DEV)/tools/audio/notes.py
	$(PYTHON) tools/cutrope.py $@

$(BUILD)/cutrope.o: $(SRCS) $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none -g $(A2_INCS) -l $(BUILD)/cutrope.lst -o $@ $<

$(BUILD)/cutrope.bin: $(BUILD)/cutrope.o $(A2_HGR_CFG)
	$(LD65) -C $(A2_HGR_CFG) -m $(BUILD)/cutrope.map -Ln $(BUILD)/cutrope.lbl -o $@ $<

$(DISK): $(BUILD)/cutrope.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin CUTROPE=$<@$(LOAD)

test: all $(A2RUN)
	$(PYTHON) tests/test_cutrope.py

test-long:
	@echo "cutrope: no long tests"

.PHONY: test test-long
