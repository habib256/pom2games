# Chess — Apple II+ / DOS 3.3 build
#
#   make            -> ../dist/CHESS.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> castling, promotion and draw rules played in a2run
#   make clean      -> remove build/ (the disk stays)
#   make distclean  -> remove build/ and the disk
#
# Needs cc65 (ca65/ld65) and python3 only; the shared rules and tool
# variables come from ../dev/cc65/apple2.mk.

DEV     ?= ../dev
include $(DEV)/cc65/apple2.mk

DEFS    := -D CHESS_SMART_EVAL
DISK    := $(DIST)/CHESS.dsk
BIN     := $(BUILD)/chess.bin
OBJS    := $(BUILD)/chess.o $(BUILD)/chess_engine.o

all: $(DISK)

$(BUILD)/chess.o: src/chess.s src/chess_common.inc $(HGR)/sprites/chess_cc65_pieces.asm $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none -g $(A2_INCS) $(DEFS) -l $(BUILD)/chess.lst -o $@ $<

$(BUILD)/chess_engine.o: src/chess_engine.asm src/chess_common.inc src/chess_tables.inc
	@mkdir -p $(BUILD)
	$(CA65) -t none -g $(A2_INCS) $(DEFS) -l $(BUILD)/chess_engine.lst -o $@ $<

$(BIN): $(OBJS) src/chess.cfg
	$(LD65) -C src/chess.cfg -m $(BUILD)/chess.map -Ln $(BUILD)/chess.lbl -o $@ $(OBJS)
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(DISK): $(BIN) $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin CHESS=$(BIN)@$(LOAD) --catalog

test: $(DISK) $(A2RUN)
	$(PYTHON) tests/test_game.py --a2run $(A2RUN) --disk $(DISK) --labels $(BUILD)/chess.lbl

.PHONY: test
