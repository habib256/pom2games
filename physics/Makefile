# PHYSICS -- rebuild the disk from source and check it against the original.
#   make            assemble, link, build build/physics.dsk, compare
#   make regen      regenerate src/*.s from the original disk (needs ORIG)
#   make da65check  da65 + info-file disassembly of the code, reassembled, compared
#   make ramcheck RAM=ram.bin   compare loaded pages with a RAM dump
#   make clean
CA65 ?= ca65
LD65 ?= ld65
PY   ?= python3 -I -B
ORIG ?= orig/physics.dsk

SRC  := src
B    := $(SRC)/build
PHYS_SRCS := $(SRC)/physics.s $(SRC)/main.s $(SRC)/boxes.s $(SRC)/tables.s \
             $(SRC)/lcdata.s $(SRC)/hw.inc $(SRC)/zp_main.inc $(SRC)/data/background.hgr

all: check

$(B)/boot.o: $(SRC)/boot.s $(SRC)/hw.inc $(SRC)/zp_boot.inc
	mkdir -p $(B)
	cd $(SRC) && $(CA65) -o build/boot.o boot.s

$(B)/physics.o: $(PHYS_SRCS)
	mkdir -p $(B)
	cd $(SRC) && $(CA65) -o build/physics.o physics.s

$(B)/boot.bin: $(B)/boot.o $(SRC)/boot.cfg
	cd $(SRC) && $(LD65) -C boot.cfg -o /dev/null build/boot.o

$(B)/seg_0800.bin: $(B)/physics.o $(SRC)/physics.cfg
	cd $(SRC) && $(LD65) -C physics.cfg -m build/physics.map -o /dev/null build/physics.o

build/physics.dsk: $(B)/boot.bin $(B)/seg_0800.bin tools/mkdisk.py
	mkdir -p build
	$(PY) tools/mkdisk.py $(B) $@

check: build/physics.dsk
	cmp build/physics.dsk $(ORIG) && echo "IDENTICAL: build/physics.dsk == $(ORIG)"

# independent cross-check with da65 (needs `make regen` first)
da65check:
	tools/da65check.sh work

# prove the load map against a RAM dump of the running program
ramcheck:
	$(PY) tools/compare_ram.py work/image.bin $(RAM)

regen:
	mkdir -p work
	$(PY) tools/extract.py tools $(ORIG) work
	$(PY) tools/gen.py tools work/image.bin work/boot0_9000.bin $(SRC)

clean:
	rm -rf $(B) build

.PHONY: all check regen clean da65check ramcheck
