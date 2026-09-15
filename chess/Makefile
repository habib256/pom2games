# Chess — Apple II+ / DOS 3.3 build
#
#   make            -> dist/CHESS.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple II+
#   make clean
#
# Needs cc65 (ca65/ld65) and python3 only: the shared ../dev tree has the rest,
# DOS 3.3 system tracks included. `make run` uses the installed POM2 app.

CA65    ?= ca65
LD65    ?= ld65
PYTHON  ?= python3
DEV     ?= ../dev
POM2    ?= /Applications/POM2.app/Contents/MacOS/POM2
SYSTEM  ?= $(DEV)/tools/dos33_system.bin

INCS    := -I src -I $(DEV)/lib/apple2 -I $(DEV)/lib/hgr
DEFS    := -D CHESS_SMART_EVAL
BUILD   := build
DIST    := dist
DISK    := $(DIST)/CHESS.dsk
BIN     := $(BUILD)/chess.bin
LOAD    := 0x6000
OBJS    := $(BUILD)/chess.o $(BUILD)/chess_engine.o

all: $(DISK)

$(BUILD)/chess.o: src/chess.s src/chess_common.inc $(wildcard $(DEV)/lib/apple2/*) $(wildcard $(DEV)/lib/hgr/*)
	@mkdir -p $(BUILD)
	$(CA65) -t none $(INCS) $(DEFS) -l $(BUILD)/chess.lst -o $@ $<

$(BUILD)/chess_engine.o: src/chess_engine.asm src/chess_common.inc src/chess_tables.inc
	@mkdir -p $(BUILD)
	$(CA65) -t none $(INCS) $(DEFS) -l $(BUILD)/chess_engine.lst -o $@ $<

$(BIN): $(OBJS) src/chess.cfg
	$(LD65) -C src/chess.cfg -m $(BUILD)/chess.map -o $@ $(OBJS)
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(DISK): $(BIN) src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ \
	    --bas HELLO=src/hello.bas \
	    --bin CHESS=$(BIN)@$(LOAD) \
	    --catalog

run: $(DISK)
	$(POM2) --preset ii+ $(DISK)

clean:
	rm -rf $(BUILD) $(DIST)

.PHONY: all run clean
