# a2shot — scripted headless Apple II+ / IIe runs on the POM2 core.
#
#   make            -> ./a2shot
#
# Self-contained: sdk/ holds the POM2 core SDK (include/pom2/core.hpp and
# lib/<host>/libpom2_core.a for darwin-arm64 and linux-x86_64, debug symbols
# stripped; provenance in sdk.mk) and roms/ the Apple ][+, //e and Disk II
# ROMs a run boots from, both copied from POM2. Only libslirp (brew install
# libslirp / apt install libslirp-dev) and zlib come from the system.

A2SHOT_DIR := .
include sdk.mk

ifeq ($(POM2_HOST),)
$(error a2shot: no POM2 core archive for $(shell uname -sm); sdk/lib/ has darwin-arm64 and linux-x86_64)
endif

a2shot: a2shot.cpp
	$(CXX) $(POM2_CORE_CFLAGS) -O2 $< $(POM2_CORE_LIBS) -o $@

clean:
	rm -f a2shot

.PHONY: clean
