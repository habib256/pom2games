# The vendored POM2 core SDK, for the programs that link it (a2shot,
# chess/test). Set A2SHOT_DIR to this folder, then include this file; it
# defines
#   POM2_HOST         darwin-arm64 or linux-x86_64 (empty on other hosts)
#   POM2_CORE_LIB     the archive for this host
#   POM2_CORE_CFLAGS  POM2_CORE_LIBS
#
# Both archives are pom2_core built at POM2 commit 28700c39 (github.com/
# habib256/pom2, "Display paints the RAM the beam fetched: the video write
# log"), debug symbols stripped (strip -S). sdk/include/pom2/core.hpp is that
# commit's header (identical from 6f8f436 to POM2 main of 2026-10-22).
#   darwin-arm64  built on the author's Mac (cmake --build --target pom2_core,
#                 cmake --install --component pom2_core_sdk)
#   linux-x86_64  built on ubuntu-24.04 (glibc 2.39) by
#                 .github/workflows/pom2-core-linux.yml, run 39837617633
#                 (github.com/habib256/pom2games/actions/runs/39837617633)
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
