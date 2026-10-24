# The vendored POM2 core SDK, for the programs that link it (a2shot,
# chess/test). Set A2SHOT_DIR to this folder, then include this file; it
# defines
#   POM2_HOST         darwin-arm64 or linux-x86_64 (empty on other hosts)
#   POM2_CORE_LIB     the archive for this host
#   POM2_CORE_CFLAGS  POM2_CORE_LIBS
#
# PROVISIONAL (2026-10-24): darwin-arm64 is pom2_core built from POM2's
# working tree on top of 788b301e, not yet committed ("pom2_core: the bus,
# the display, the RGB card, a Disk II anywhere": setBusWatch, displayState,
# attachRgbCard, attachDiskII slot, setDiskWriteProtected, Machine::AppleIIe
# — LETTRE_POM2_CHROMABREAK.md), debug symbols stripped (strip -S);
# sdk/include/pom2/core.hpp is that tree's header. linux-x86_64 is still the
# 0849ee51 archive: to rebuild both from the POM2 commit once it is pushed.
#   darwin-arm64  built on the author's Mac (cmake --build --target pom2_core,
#                 cmake --install --component pom2_core_sdk)
#   linux-x86_64  built on ubuntu-24.04 (glibc 2.39) by
#                 .github/workflows/pom2-core-linux.yml, run 40105356133
#                 (github.com/habib256/pom2games/actions/runs/40105356133)
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
POM2_CORE_CFLAGS := -std=c++17 -I $(A2SHOT_DIR)/sdk/include

ifeq ($(POM2_HOST),darwin-arm64)
POM2_SYS_LIBS := -framework CoreAudio -framework AudioToolbox -framework AudioUnit
else
POM2_SYS_LIBS := -ldl -lpthread -lm
endif
POM2_CORE_LIBS := $(POM2_CORE_LIB) $(POM2_SYS_LIBS) $(shell pkg-config --libs slirp) -lz
