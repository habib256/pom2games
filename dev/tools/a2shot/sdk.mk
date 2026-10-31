# The vendored POM2 core SDK, for the programs that link it (a2shot,
# chess/test). Set A2SHOT_DIR to this folder, then include this file; it
# defines
#   POM2_HOST         darwin-arm64 or linux-x86_64 (empty on other hosts)
#   POM2_CORE_LIB     the archive for this host
#   POM2_CORE_CFLAGS  POM2_CORE_LIBS
#
# Both archives are pom2_core built at POM2 commit ba7f04da (github.com/
# habib256/pom2 main, 2026-10-31, "Disk II / Monitor / Applecorn / CP/M-65
# traces; FASTChip //e; E-Z Color in the SDK"), debug symbols stripped
# (strip -S); sdk/include/pom2/core.hpp is that commit's header (it now
# includes <array>). New since 6f7f06a7: the E-Z Color card (TMS9918A) —
# attachEzColor(slot, siliconStrict), ezColorAttached, ezColorState,
# ezColorVram, resetEzColorDropCount, renderEzColorFrame (our letter
# LETTRE_POM2_EZCOLOR.md) — and Machine::AppleIIcPlus; the Disk II boot PROM
# became optional. POM2_SDK_HAS_EZCOLOR=1 (below) tells a2shot.cpp the header
# has the card: drop it if a host's archive ever lags behind the header.
#   darwin-arm64  built on the author's Mac (cmake --build build --target
#                 pom2_core, cmake --install build --component pom2_core_sdk)
#   linux-x86_64  built on ubuntu-24.04 (glibc 2.39) by
#                 .github/workflows/pom2-core-linux.yml, run 41225532582
#                 (github.com/habib256/pom2games/actions/runs/41225532582,
#                 -f pom2_commit=ba7f04da19c3047a83eb33538254c885f3c8cb80;
#                 its header is byte-identical to the vendored one)
# The compiled core is GPL-3.0, like POM2.
#
# The core's own link needs, on macOS, the CoreAudio frameworks (miniaudio);
# on Linux, libdl, pthread and libm (miniaudio loads ALSA/PulseAudio at run
# time, when a device is opened, which a headless run never does). Both need
# libslirp (pkg-config slirp: brew install libslirp / apt install
# libslirp-dev) and zlib.

POM2_HOST := $(subst Darwin-arm64,darwin-arm64,$(subst Linux-x86_64,linux-x86_64,$(shell uname -sm | tr ' ' -)))
POM2_HOST := $(filter darwin-arm64 linux-x86_64,$(POM2_HOST))
POM2_CORE_LIB    := $(A2SHOT_DIR)/sdk/lib/$(POM2_HOST)/libpom2_core.a
POM2_CORE_CFLAGS := -std=c++17 -I $(A2SHOT_DIR)/sdk/include -DPOM2_SDK_HAS_EZCOLOR=1

ifeq ($(POM2_HOST),darwin-arm64)
POM2_SYS_LIBS := -framework CoreAudio -framework AudioToolbox -framework AudioUnit
else
POM2_SYS_LIBS := -ldl -lpthread -lm
endif
POM2_CORE_LIBS := $(POM2_CORE_LIB) $(POM2_SYS_LIBS) $(shell pkg-config --libs slirp) -lz
