# VERHILLE Arnaud — GPL-3.0. CATAPULT: circles on boxes, the dev/lib/physics contacts
# demo -- Apple II+ 48 KB, DOS 3.3, HGR, assembly; the disk stays in build/.
#
#   make            -> build/CATAPULT.dsk (boots into the game)
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> 6502 physics == tools/catapult.py, then the disk in a2run
#   python3 tools/catapult.py        a sweep of shots on the model
DEV ?= ../..
include $(DEV)/cc65/apple2.mk

DISK := $(BUILD)/CATAPULT.dsk
SRCS := src/catapult.s src/phys.inc src/physdefs.inc src/plot.inc src/catconst.inc

all: $(DISK)

src/catconst.inc: tools/catapult.py $(wildcard $(DEV)/tools/verlet/*.py)
	$(PYTHON) tools/catapult.py $@

$(BUILD)/catapult.o: $(SRCS) $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none -g $(A2_INCS) -l $(BUILD)/catapult.lst -o $@ $<

$(BUILD)/catapult.bin: $(BUILD)/catapult.o $(A2_HGR_CFG)
	$(LD65) -C $(A2_HGR_CFG) -m $(BUILD)/catapult.map -Ln $(BUILD)/catapult.lbl -o $@ $<

$(DISK): $(BUILD)/catapult.bin $(DOS33_DEPS)
	$(DOS33) --bin CATAPULT=$<@$(LOAD)

test: all $(A2RUN)
	$(PYTHON) tests/test_catapult.py

test-long:
	@echo "catapult: no long tests"

.PHONY: test test-long
