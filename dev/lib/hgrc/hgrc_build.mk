# VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
# Include after the consumer's first target (normally all).
# hgrc.mk must already be included. HGRC_EXTRA_SRCS adds optional platform code.
CL65 ?= cl65
CA65 ?= ca65
AR65 ?= ar65
HGRC_ARCHIVE_SRCS := $(sort $(HGRC_ALL_SRCS) $(HGRC_EXTRA_SRCS))
HGRC_OBJECTS := $(addprefix $(HGRC_BUILD)/,$(notdir $(HGRC_ARCHIVE_SRCS:.c=.o)))
HGRC_OBJECTS := $(HGRC_OBJECTS:.s=.o)
HGRC_CFLAGS ?= -t none -Oirs $(HGRC_INCS) -I $(HGRC)/../apple2c
HGRC_ASMFLAGS ?= -t none $(HGRC_AFLAGS)

vpath %.c $(HGRC) $(GFX) $(HGRC)/../apple2c
vpath %.s $(HGRC) $(HGRC)/../apple2c

$(HGRC_BUILD)/%.o: %.c $(HGRC_HEADERS) $(wildcard $(HGRC)/../apple2c/*.h) $(HGRC)/hgrc_build.mk
	@mkdir -p $(@D)
	$(CL65) $(HGRC_CFLAGS) -c -o $@ $<

$(HGRC_BUILD)/%.o: %.s $(HGRC_ASM_DEPS) $(HGRC)/hgrc_build.mk
	@mkdir -p $(@D)
	$(CA65) $(HGRC_ASMFLAGS) -o $@ $<

$(HGRC_LIB): $(HGRC_OBJECTS) $(HGRC)/hgrc.mk $(HGRC)/hgrc_build.mk
	rm -f $@
	$(AR65) a $@ $(HGRC_OBJECTS)
