# Optional lossless HGR compressor; include after apple2.mk.
# FHPACK points to the shared build rule; source revision/licence are pinned
# in dev/tests/techniques/upstream/fhpack. No downloads at build time.
# Use -c -9 -h for full 8192-byte HGR pages, and verify with -d + cmp.
FHPACK ?= $(BUILD)/fhpack
FHPACK_SOURCE ?= $(DEV)/tests/techniques/upstream/fhpack/fhpack.cpp

$(FHPACK): $(FHPACK_SOURCE)
	@mkdir -p $(dir $@)
	$(CXX) -O2 -o $@ $<
