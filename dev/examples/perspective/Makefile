# Optional perspective + PWM integration, II+ 48 KB; disk stays in build/.
DEV ?= ../..
include $(DEV)/cc65/apple2.mk
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
include $(AUDIO)/audio.mk
include $(PERSPECTIVE)/perspective.mk
DISK := $(BUILD)/PERSPECTIVE.dsk
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS) $(PERSPECTIVE_SRCS) $(AUDIO_SRCS)
HGRC_CFLAGS := -t none -Ors $(HGRC_INCS) $(APPLE2C_INCS) $(PERSPECTIVE_INCS) $(AUDIO_INCS)

all: $(DISK)

$(BUILD)/camera.h: $(DEV)/tools/perspective.py Makefile
	@mkdir -p $(@D)
	$(PYTHON) $< --out $@ --name camera --horizon 24 --bottom 159

$(BUILD)/chirp.wav: make_chirp.py
	@mkdir -p $(@D)
	$(PYTHON) $< $@

# The stamp avoids races between the two generated outputs on make 3.81.
$(BUILD)/chirp.stamp: $(BUILD)/chirp.wav $(DEV)/tools/audio/pack_wav.py
	$(PYTHON) $(DEV)/tools/audio/pack_wav.py $< --out $(BUILD)/chirp --name chirp
	@touch $@
$(BUILD)/chirp.s $(BUILD)/chirp.h: $(BUILD)/chirp.stamp
	@test -f $@ || { $(PYTHON) $(DEV)/tools/audio/pack_wav.py $(BUILD)/chirp.wav --out $(BUILD)/chirp --name chirp; }

$(BUILD)/main.o: src/main.c $(BUILD)/camera.h $(BUILD)/chirp.h $(HGRC_HEADERS) $(APPLE2C_HEADERS) $(AUDIO_HEADERS) $(PERSPECTIVE_HEADERS) Makefile
	$(CL65) $(HGRC_CFLAGS) -I $(BUILD) -c -o $@ $<
$(BUILD)/chirp.o: $(BUILD)/chirp.s
	$(CA65) -t none -o $@ $<
$(BUILD)/crt0.o: $(A2_CRT0)
	@mkdir -p $(@D)
	$(CA65) -t none -o $@ $<
$(BUILD)/perspective.bin: $(BUILD)/crt0.o $(BUILD)/main.o $(BUILD)/chirp.o $(HGRC_LIB) $(A2_HGR_C_CFG)
	$(CL65) -t none -C $(A2_HGR_C_CFG) -m $(BUILD)/perspective.map -Ln $(BUILD)/perspective.lbl -o $@ $(BUILD)/crt0.o $(BUILD)/main.o $(BUILD)/chirp.o $(HGRC_LIB)
$(DISK): $(BUILD)/perspective.bin $(DOS33_DEPS)
	$(DOS33) --bin PROJECT=$<@$(LOAD)

include $(HGRC)/hgrc_build.mk

test:
	$(PYTHON) $(DEV)/tests/test_shufflepuck_example.py
.PHONY: test
