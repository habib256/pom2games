# a2run -- portable headless Apple II+ runs (see a2run.c).
#
#   make            -> ./a2run
#
# Plain C99 + zlib: builds on Linux and macOS alike. The ROMs are shared with
# ../a2shot/roms.

CC     ?= cc
CFLAGS ?= -O2 -Wall -Wextra -std=c99

a2run: a2run.c cpu6502.c cpu6502.h
	$(CC) $(CFLAGS) a2run.c cpu6502.c -lz -o $@

clean:
	rm -f a2run

.PHONY: clean
