# The vendored POM2 core SDK, for the programs that link it (a2shot,
# chess/test). Set A2SHOT_DIR to this folder, then include this file; it
# defines
#   POM2_HOST         darwin-arm64 or linux-x86_64 (empty on other hosts)
#   POM2_CORE_LIB     the archive for this host
#   POM2_CORE_CFLAGS  POM2_CORE_LIBS
#
# sdk/include/pom2/core.hpp and both archives are pom2_core at POM2 commit
# 0d1d388e98b2268629cc65269c1aba161720585a (github.com/habib256/pom2 main,
# 2026-11-04, "The SDK mounts hard disks and answers a test harness"). They
# include E-Z Color (TMS9918A), hard disks and the harness API (physical RAM,
# keyboard state and SDK provenance). POM2_SDK_HAS_EZCOLOR=1 and
# POM2_SDK_HAS_HARNESS=1 enable these APIs on both supported hosts.
#   darwin-arm64  packaged on the author's Mac with tools/package_core_sdk.sh
#   linux-x86_64  built on ubuntu-24.04 (glibc 2.39) by
#                 .github/workflows/pom2-core-linux.yml, run 41894229835
#                 (github.com/habib256/pom2games/actions/runs/41894229835),
#                 with the same commit; its header is byte-identical.
# Debug symbols stripped (strip -S) on both hosts. The compiled core is
# GPL-3.0, like POM2.
#
# The core's own link needs, on macOS, the CoreAudio frameworks (miniaudio);
# on Linux, libdl, pthread and libm (miniaudio loads ALSA/PulseAudio at run
# time, when a device is opened, which a headless run never does). Both need
# libslirp (pkg-config slirp: brew install libslirp / apt install
# libslirp-dev) and zlib.

POM2_HOST := $(subst Darwin-arm64,darwin-arm64,$(subst Linux-x86_64,linux-x86_64,$(shell uname -sm | tr ' ' -)))
POM2_HOST := $(filter darwin-arm64 linux-x86_64,$(POM2_HOST))
POM2_CORE_LIB    := $(A2SHOT_DIR)/sdk/lib/$(POM2_HOST)/libpom2_core.a
POM2_CORE_CFLAGS := -std=c++17 -I $(A2SHOT_DIR)/sdk/include -DPOM2_SDK_HAS_EZCOLOR=1 -DPOM2_SDK_HAS_HARNESS=1

ifeq ($(POM2_HOST),darwin-arm64)
POM2_SYS_LIBS := -framework CoreAudio -framework AudioToolbox -framework AudioUnit
else
POM2_SYS_LIBS := -ldl -lpthread -lm
endif
POM2_CORE_LIBS := $(POM2_CORE_LIB) $(POM2_SYS_LIBS) $(shell pkg-config --libs slirp) -lz
