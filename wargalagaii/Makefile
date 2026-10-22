# WARGALAGA II — Apple //e enhanced / //c 128 KB, ProDOS, HGR (en préparation)
#
#   make            -> pour l'instant : rappelle l'état, ne construit rien
#   (prévu) make            -> ../dist/WARGALAGAII.po
#   (prévu) make run        -> POM2, //e enhanced + AppleMouse
#   (prévu) make run-iic    -> POM2, //c et sa souris intégrée
#   (prévu) make test       -> logique 6502 == modèle Python, son avec et
#                              sans Mockingboard, cadence, démarrage
#
# Pas encore dans les listes all / test du Makefile racine (TODO.md, lot 9).
# Modèle complet : ../chromabreak/Makefile (ProDOS, crt0_prodos, archive des
# libs, volume 280 blocs).

DEV ?= ../dev
APPLE2_PRESET := iie
APPLE2_RUN_FLAGS := --slot 4=mouseaw
include $(DEV)/cc65/apple2.mk
# include $(HGRC)/hgrc.mk
# include $(APPLE2C)/apple2c.mk
# PRODOS := $(DEV)/lib/prodos
# MOUSE  := $(DEV)/lib/mouse
# include $(PRODOS)/prodos.mk
# include $(MOUSE)/mouse.mk

DISK := $(DIST)/WARGALAGAII.po

all:
	@echo "WARGALAGA II : pas encore de code (voir TODO.md). Rien a construire."

# --- Prévu (lots 1 à 9) ------------------------------------------------------
# CFLAGS := -t none --cpu 65c02 -Ors -I src $(HGRC_INCS) $(APPLE2C_INCS) \
#           $(PRODOS_INCS) $(MOUSE_INCS)
# LIB_SRCS := $(APPLE2C_SRCS) $(APPLE2C_FRAME_SRCS) $(APPLE2C_CADENCE_SRCS) \
#             $(PRODOS_SRCS) $(MOUSE_SRCS) <noyaux hgrc : mode, hud8, texte>
# Sources asm : .setcpu "65C02", libs dev/lib/apple2 (mockingboard.asm,
# sound.asm) et dev/lib/hgr incluses A LA FIN du source (.ifref).
#
# src/sprites.inc: tools/sprites.py          # 7 prédécalages, fond noir
# src/paths.inc:   tools/paths.py            # trajectoires en tables
# $(BUILD)/WG2.AUX: tools/levels.py          # réserve mémoire aux
# $(BUILD)/game.bin: ... -C $(DEV)/cc65/apple2_dhgr_prodos_c.cfg
#                                            # (pages HGR = $2000-$5FFF main)
# $(BUILD)/WG2.SYS: src/startup.s            # reloge game.bin à $6000
# $(BUILD)/WG2.SYSTEM: src/boot.s src/boot.cfg   # refuse un 6502 NMOS
#
# $(DISK): $(BUILD)/WG2.SYSTEM $(BUILD)/WG2.SYS $(BUILD)/WG2.AUX $(BUILD)/HIGHSCORES
# 	@mkdir -p $(BUILD)/stage $(DIST)
# 	cp $(DEV)/tools/prodos/PRODOS $(BUILD)/stage/PRODOS#FF0000
# 	cp $(BUILD)/WG2.SYSTEM $(BUILD)/stage/WG2.SYSTEM#FF2000
# 	cp $(BUILD)/WG2.SYS $(BUILD)/stage/WG2.SYS#FF2000
# 	...
# 	$(PYTHON) $(DEV)/tools/prodos/build_volume.py $(BUILD)/stage $@ \
# 		--volume WARGALAGAII --boot $(DEV)/tools/prodos/boot.bin --blocks 280
#
# run-iic: all
# 	$(POM2) --preset iic --slot 4=iicmouse $(DISK)
# test: all
# 	$(PYTHON) tests/test_logic.py          # 6502 == tools/model.py
# 	$(PYTHON) tests/test_audio.py          # haut-parleur
# 	$(PYTHON) tests/test_audio.py --mockingboard   # a2shot --iie --mockingboard
# 	$(PYTHON) tests/test_cadence.py        # même vitesse avec et sans carte

.PHONY: all
