# a2shot — scripted headless Apple II+ screenshots on the POM2 core.
#
#   make            -> ./a2shot
#
# Self-contained: sdk/ holds the POM2 core SDK (include/pom2/core.hpp and
# lib/libpom2_core.a — arm64, debug symbols stripped) and roms/ the Apple ][+
# and Disk II ROMs a run boots from, both copied from POM2. Only libslirp
# (brew) and zlib come from the system.

PREFIX ?= sdk
CXX    ?= clang++

LIBS := $(PREFIX)/lib/libpom2_core.a \
        -framework CoreAudio -framework AudioToolbox -framework AudioUnit \
        $(shell pkg-config --libs slirp) -lz

a2shot: a2shot.cpp
	$(CXX) -std=c++17 -O2 -I $(PREFIX)/include $< $(LIBS) -o $@

clean:
	rm -f a2shot

.PHONY: clean
