# VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
# Include after the consumer's first target. hgrc.mk must already be included.
CL65 ?= cl65
CA65 ?= ca65
AR65 ?= ar65
PYTHON ?= python3
HGRC_ARCHIVE_SRCS := $(sort $(HGRC_ALL_SRCS) $(HGRC_EXTRA_SRCS))
# ar65 indexes by basename: encode both directory and source extension.
hgrc_object = $(HGRC_BUILD)/$(subst /,__,$(patsubst $(DEV)/lib/%,%,$(1))).o
HGRC_OBJECTS := $(foreach s,$(HGRC_ARCHIVE_SRCS),$(call hgrc_object,$(s)))
ifneq ($(words $(HGRC_OBJECTS)),$(words $(sort $(HGRC_OBJECTS))))
$(error HGRC sources produce duplicate archive member names)
endif
HGRC_CFLAGS ?= -t none -Oirs $(HGRC_INCS) -I $(HGRC)/../apple2c
HGRC_ASMFLAGS ?= -t none $(HGRC_AFLAGS)
HGRC_CONFIG := $(HGRC_BUILD)/config.json
# Quote every configuration value as one shell argument, including apostrophes.
hgrc_quote = '$(subst ','"'"',$(1))'
HGRC_CONFIG_ARGS = $(foreach v,HGRC_CONFIG HGRC_CFLAGS HGRC_ASMFLAGS CL65 CA65 AR65 HGRC_ARCHIVE_SRCS,$(call hgrc_quote,$($(v))))
# GNU make 3.81 compares whole-second timestamps. An explicit change check
# forces rebuilds even when flags change within the same second; --check is
# read-only, including during make -n. The recipe records the new signature.
HGRC_CONFIG_CHANGED := $(shell $(PYTHON) $(HGRC)/../../tools/build_config.py --check -- $(HGRC_CONFIG_ARGS))
HGRC_CONFIG_FORCE := $(if $(HGRC_CONFIG_CHANGED),hgrc-config-force)

.PHONY: hgrc-config-force
$(HGRC_CONFIG): $(HGRC_CONFIG_FORCE) $(HGRC)/../../tools/build_config.py
	@$(PYTHON) $(HGRC)/../../tools/build_config.py -- $(HGRC_CONFIG_ARGS)

define hgrc_compile
$(call hgrc_object,$(1)): $(1) $(HGRC_CONFIG) $(HGRC_CONFIG_FORCE) $(HGRC_HEADERS) $(HGRC_ASM_DEPS) $(wildcard $(HGRC)/../apple2c/*.h) $(HGRC)/hgrc_build.mk
	@mkdir -p $$(@D)
$(if $(filter %.c,$(1)),	$$(CL65) $$(HGRC_CFLAGS) -S -o $$@.s $$<
	$$(CL65) $$(HGRC_CFLAGS) -c -o $$@ $$@.s,	$$(CA65) $$(HGRC_ASMFLAGS) -o $$@ $$<)
endef
$(foreach s,$(HGRC_ARCHIVE_SRCS),$(eval $(call hgrc_compile,$(s))))

$(HGRC_LIB): $(HGRC_OBJECTS) $(HGRC_CONFIG) $(HGRC_CONFIG_FORCE) $(HGRC)/hgrc.mk $(HGRC)/hgrc_build.mk
	rm -f $@
	$(AR65) a $@ $(HGRC_OBJECTS)
