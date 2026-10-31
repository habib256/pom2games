# VERHILLE Arnaud — GPL-3.0. HALFPIPE: a Verlet skate / BMX half-pipe, the
# dev/lib/physics segment-ground demo -- Apple II+ 48 KB, DOS 3.3, HGR,
# assembly; the disk stays in build/.
#
#   make            -> build/HALFPIPE.dsk (boots into the game)
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> 6502 physics == tools/halfpipe.py, then the disk in a2run
#   python3 tools/halfpipe.py      the pipe's segments and a pumping ride on the model
DEV ?= ../..
include $(DEV)/cc65/apple2.mk

DISK := $(BUILD)/HALFPIPE.dsk
SRCS := src/halfpipe.s src/phys.inc src/physdefs.inc src/pipeconst.inc

all: $(DISK)

src/pipeconst.inc: tools/halfpipe.py $(wildcard $(DEV)/tools/verlet/*.py)
	$(PYTHON) tools/halfpipe.py $@

$(BUILD)/halfpipe.o: $(SRCS) $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none -g $(A2_INCS) -l $(BUILD)/halfpipe.lst -o $@ $<

$(BUILD)/halfpipe.bin: $(BUILD)/halfpipe.o $(A2_HGR_CFG)
	$(LD65) -C $(A2_HGR_CFG) -m $(BUILD)/halfpipe.map -Ln $(BUILD)/halfpipe.lbl -o $@ $<

$(DISK): $(BUILD)/halfpipe.bin $(DOS33_DEPS)
	$(DOS33) --bin HALFPIPE=$<@$(LOAD)

test: all $(A2RUN)
	$(PYTHON) tests/test_halfpipe.py

test-long:
	@echo "halfpipe: no long tests"

.PHONY: test test-long
