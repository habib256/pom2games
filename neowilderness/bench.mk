# Shared by the standalone benches (dhgr.mk, hof.mk, stars.mk): the
# NEO*.SYSTEM loader and the dev/lib/prodos objects.
# Before the include: BUILD, BOOT and BENCH_ID (DHGR, HOF or STARS).

BENCH_DISK_DEPS := $(DEV)/tools/prodos/PRODOS $(DEV)/tools/prodos/boot.bin $(DEV)/tools/prodos/build_volume.py

$(BOOT): src/bench_boot.s src/bench_boot.cfg
	@mkdir -p $(@D)
	$(CA65) -t none -D BENCH_$(BENCH_ID) -o $(BUILD)/bench_boot.o $<
	$(LD65) -C src/bench_boot.cfg -o $@ $(BUILD)/bench_boot.o

$(BUILD)/prodos_%.o: $(DEV)/lib/prodos/%.s
	@mkdir -p $(@D)
	$(CA65) -t none -o $@ $<
