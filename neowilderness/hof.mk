# Neowilderness lot 7 — score and hall of fame, standalone IIe bench (docs/HOF.md).
#
#   make -f hof.mk          -> ../dist/NEOHOF_TEST.po (ProDOS 2.4.3, Apple IIe/IIc 128 KB)
#   make -f hof.mk run      -> boot it in POM2 (IIe preset): three journeys end (type a
#                              name, RETURN), then the menu's BEST cells and the H
#                              screen; any key goes on
#   make -f hof.mk test     -> tests/test_hof_ref.py (Python) + tests/test_hof.py
#                              (a2shot --iie: entry, sort, write, re-read of the .po,
#                              write-protected WOZ, MLI errors)
#   make -f hof.mk sizes    -> bytes of the module and of the loader fragment
#
# Independent of the main Makefile: every output stays in build/hof/.

DEV ?= ../dev
include $(DEV)/cc65/apple2.mk
BUILD := build/hof
APPLE2_PRESET := iie

DISK  := $(DIST)/NEOHOF_TEST.po
BOOT  := $(BUILD)/NEOHOF.SYSTEM
BENCH_ID := HOF
BIN   := $(BUILD)/hof_test.bin
MODULE := $(BUILD)/NEOWILD.END
CA65FLAGS := -g -t none -I src -I $(APPLE2)
PYDEPS := tools/score_ref.py tools/po2woz.py tests/score.py

all: $(DISK)

include bench.mk

# The module, as the game builds it, with the game labels imported from the
# bench (HOF_BENCH); the bench links it at $9600 into NEOWILD.END.
$(BUILD)/hof.o: src/hof.s src/hof_menu.s hof.mk
	@mkdir -p $(@D)
	$(CA65) $(CA65FLAGS) -D HOF_BENCH -l $(BUILD)/hof.lst -o $@ $<

$(BUILD)/hof_test.o: src/hof_test.s src/hof_menu.s src/hof_load.inc hof.mk
	@mkdir -p $(@D)
	$(CA65) $(CA65FLAGS) -l $(BUILD)/hof_test.lst -o $@ $<

$(BIN) $(MODULE): $(BUILD)/hof_test.o $(BUILD)/hof.o src/hof_test.cfg
	$(LD65) -C src/hof_test.cfg -m $(BUILD)/hof_test.map -Ln $(BUILD)/hof_test.lbl -o $(BIN) $(BUILD)/hof_test.o $(BUILD)/hof.o

$(DISK): $(BIN) $(MODULE) $(BOOT) tests/test_hof.py $(PYDEPS) $(BENCH_DISK_DEPS)
	@mkdir -p $(DIST)
	$(PYTHON) tests/test_hof.py --demo-po $@

sizes: $(BIN) $(MODULE)
	@echo "module NEOWILD.END: $$(wc -c < $(MODULE) | tr -d ' ') bytes (6 data blocks + index while <= 3072)"
	@$(PYTHON) -c "import re; L={n:int(a,16) for a,n in re.findall(r'^al ([0-9A-F]+) \.(\w+)$$', open('$(BUILD)/hof_test.lbl').read(), re.M) if int(a,16) < 0x9600}; \
print('loader fragment (HOF_LOADER, bench copy, own pathname buffer):', L['bench_read'] - L['hm_load'], 'bytes')"

test: all $(A2SHOT)
	$(PYTHON) tests/test_hof_ref.py
	$(PYTHON) tests/test_hof.py

.PHONY: sizes test
