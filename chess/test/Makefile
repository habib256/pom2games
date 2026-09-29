# Engine bench: the chess engine alone on the POM2 core, with cycle counts.
#
#   make            -> build/bench (host tool) + build/engine.bin (engine + bench.s)
#   make perft | best | undo | play | prof | exact
#
# Compare two engine versions by diffing the text output (cycle counts aside).
# Host side reuses ../../dev/tools/a2shot (POM2 core SDK + II+ ROM).

CA65    ?= ca65
LD65    ?= ld65
CXX     ?= clang++
A2SHOT  ?= ../../dev/tools/a2shot
SRC     ?= ../src
DEFS    := -D CHESS_SMART_EVAL
BUILD   := build

LIBS := $(A2SHOT)/sdk/lib/libpom2_core.a \
        -framework CoreAudio -framework AudioToolbox -framework AudioUnit \
        $(shell pkg-config --libs slirp) -lz

BENCH   := $(BUILD)/bench --roms $(A2SHOT)/roms --bin $(BUILD)/engine.bin --lbl $(BUILD)/engine.lbl
FEN     ?= rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1
PLIES   ?= 40
LEVELS  ?= 2
STRAT   ?= 1

all: $(BUILD)/bench $(BUILD)/engine.bin

$(BUILD)/bench: bench.cpp
	@mkdir -p $(BUILD)
	$(CXX) -std=c++17 -O2 -I $(A2SHOT)/sdk/include $< $(LIBS) -o $@

$(BUILD)/bench.o: bench.s
	@mkdir -p $(BUILD)
	$(CA65) -t none -g -o $@ $<

$(BUILD)/chess_engine.o: $(SRC)/chess_engine.asm $(SRC)/chess_common.inc $(SRC)/chess_tables.inc
	@mkdir -p $(BUILD)
	$(CA65) -t none -g -I $(SRC) $(DEFS) -o $@ $<

$(BUILD)/engine.bin: $(BUILD)/bench.o $(BUILD)/chess_engine.o bench.cfg
	$(LD65) -C bench.cfg -Ln $(BUILD)/engine.lbl -o $@ $(BUILD)/bench.o $(BUILD)/chess_engine.o

perft undo: all
	$(BENCH) $@

best: all
	$(BENCH) best $(LEVELS)

play: all
	$(BENCH) play $(PLIES) $(LEVELS)

# The search with every cutoff disabled: `make exact` checks that the cutoffs
# change no move (best moves and games, all levels).
$(BUILD)/nocut.o: $(SRC)/chess_engine.asm $(SRC)/chess_common.inc $(SRC)/chess_tables.inc
	@mkdir -p $(BUILD)
	$(CA65) -t none -g -I $(SRC) $(DEFS) -D CHESS_NO_CUTOFF -o $@ $<

$(BUILD)/nocut.bin: $(BUILD)/bench.o $(BUILD)/nocut.o bench.cfg
	$(LD65) -C bench.cfg -Ln $(BUILD)/nocut.lbl -o $@ $(BUILD)/bench.o $(BUILD)/nocut.o

NOCUT   := $(BUILD)/bench --roms $(A2SHOT)/roms --bin $(BUILD)/nocut.bin --lbl $(BUILD)/nocut.lbl

exact: all $(BUILD)/nocut.bin
	$(BENCH) best 3 | sed 's/ *[0-9]* cy.*//' > $(BUILD)/cut.txt
	$(BENCH) play $(PLIES) 3 | grep -v total >> $(BUILD)/cut.txt
	$(NOCUT) best 3 | sed 's/ *[0-9]* cy.*//' > $(BUILD)/nocut.txt
	$(NOCUT) play $(PLIES) 3 | grep -v total >> $(BUILD)/nocut.txt
	diff $(BUILD)/cut.txt $(BUILD)/nocut.txt && echo "exact: same moves with and without cutoffs"

prof: all
	$(BENCH) prof "$(FEN)" $(STRAT)

clean:
	rm -rf $(BUILD)

.PHONY: all perft best undo play prof exact clean
