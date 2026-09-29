# pom2games — build every disk
#
#   make            -> */dist/*.dsk
#   make clean
#
# Each folder builds on its own too: make -C chess [run]

DIRS := sokoban chess maze3d snake logo demos dev/examples/hello

all:
	@for d in $(DIRS); do $(MAKE) -C $$d || exit 1; done

clean:
	@for d in $(DIRS); do $(MAKE) -C $$d clean; done

.PHONY: all clean
