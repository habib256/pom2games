# VERHILLE Arnaud — GPL-3.0. ROPE: a pinned Verlet rope toy, the dev/lib/physics
# demo -- Apple II+ 48 KB, DOS 3.3, HGR, assembly; the disk stays in build/.
#
#   make            -> build/ROPE.dsk (boots into the game)
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> 6502 physics == tools/rope.py, then the disk in a2run
#   python3 tools/rope.py        the model, in a few lines of text
DEV ?= ../..
include $(DEV)/cc65/apple2.mk

DISK := $(BUILD)/ROPE.dsk
SRCS := src/rope.s src/phys.inc src/physdefs.inc src/plot.inc src/ropeconst.inc

all: $(DISK)

src/ropeconst.inc: tools/rope.py $(wildcard $(DEV)/tools/verlet/*.py)
	$(PYTHON) tools/rope.py $@

$(BUILD)/rope.o: $(SRCS) $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none -g $(A2_INCS) -l $(BUILD)/rope.lst -o $@ $<

$(BUILD)/rope.bin: $(BUILD)/rope.o $(A2_HGR_CFG)
	$(LD65) -C $(A2_HGR_CFG) -m $(BUILD)/rope.map -Ln $(BUILD)/rope.lbl -o $@ $<

$(DISK): $(BUILD)/rope.bin $(DOS33_DEPS)
	$(DOS33) --bin ROPE=$<@$(LOAD)

test: all $(A2RUN)
	$(PYTHON) tests/test_rope.py

test-long:
	@echo "rope: no long tests"

.PHONY: test test-long
