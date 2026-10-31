# VERHILLE Arnaud — GPL-3.0. LANDER: a Verlet lunar lander, the dev/lib/physics
# demo -- Apple II+ 48 KB, DOS 3.3, HGR, assembly; the disk stays in build/.
#
#   make            -> build/LANDER.dsk (boots into the game)
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> 6502 physics == tools/lander.py, then the disk in a2run
#   python3 tools/lander.py        try the autopilot on the model
DEV ?= ../..
include $(DEV)/cc65/apple2.mk

DISK := $(BUILD)/LANDER.dsk
SRCS := src/lander.s src/phys.inc src/physdefs.inc src/landconst.inc

all: $(DISK)

src/landconst.inc: tools/lander.py $(wildcard $(DEV)/tools/verlet/*.py)
	$(PYTHON) tools/lander.py $@

$(BUILD)/lander.o: $(SRCS) $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none -g $(A2_INCS) -l $(BUILD)/lander.lst -o $@ $<

$(BUILD)/lander.bin: $(BUILD)/lander.o $(A2_HGR_CFG)
	$(LD65) -C $(A2_HGR_CFG) -m $(BUILD)/lander.map -Ln $(BUILD)/lander.lbl -o $@ $<

$(DISK): $(BUILD)/lander.bin $(DOS33_DEPS)
	$(DOS33) --bin LANDER=$<@$(LOAD)

test: all $(A2RUN)
	$(PYTHON) tests/test_lander.py

test-long:
	@echo "lander: no long tests"

.PHONY: test test-long
