# WARGALAGA II — plan de travail

Cible : Apple //e enhanced et //c, 128 Ko, 65C02, ProDOS, HGR double tampon,
30 i/s NTSC (2 rafraîchissements par image), avec ou sans Mockingboard.
Raisons et carte mémoire : [README](README.md). Règles reprises de Warblade :
[docs/warblade-reference.md](docs/warblade-reference.md).

Modèle de projet : [CHROMABREAK](../chromabreak/README.md) pour l'amorce
ProDOS, `/RAM`, la cadence //e et //c, la souris et la manette lues dans
l'attente ; [DIRTBIKE](../dirtbike/README.md) pour le modèle Python oracle
au bit près, le rendu « ne réécrire que ce qui change » et les lots.
Seuil de performance : un gain mesuré de 5 % mérite d'être fait.

Légende : `[lib]` = à ajouter ou modifier dans `dev/lib` (partagé, avec son
test dans `dev/tests` et sa ligne dans le README de la lib) ; `[jeu]` =
propre au jeu, dans `wargalagaii/src` ou `tools`.

## Lot 0 — préparation (fait, 2026-10-22)

- [x] Dossier, README (machine, mémoire, cadence, son, commandes), TODO.
- [x] Référence Warblade vérifiée, avec sources (`docs/warblade-reference.md`).
- [x] Recherche d'un « WarGalaga » existant : aucun ; POM1 a un TMS Galaga
      (TMS9918, sprites matériels), utile seulement pour les plongées.
- [x] `Makefile` squelette (inclut `apple2.mk`, ne construit rien).

## Lot 1 — V0.1 : démarrage, horloge, vaisseau, tir

- [ ] `[jeu]` `src/boot.s` + `src/boot.cfg` : `WG2.SYSTEM`, refus d'un
      processeur NMOS avec message (copie de `chromabreak/src/boot.s`, test
      `INC A`), chargement et relogement de `WG2.SYS` à `$6000`
      (`chromabreak/src/startup.s`).
- [ ] Lien : `dev/cc65/crt0_prodos.s` + `dev/cc65/apple2_dhgr_prodos_c.cfg`
      (les pages principales `$2000-$5FFF` sont les deux pages HGR), libs
      `$(PRODOS)/mli.s`, `$(PRODOS)/video.s`. `--cpu 65c02`, `.setcpu "65C02"`.
- [ ] `/RAM` : `prodos_video_claim(PD_VIDEO_DISCARD_RAM)` avant toute
      écriture en aux, libération à la sortie ; `game_shutdown()` remet le
      texte, coupe la souris et la Mockingboard (`mb_stop`).
- [ ] HGR : `hgr_init` / `hgr_init_clear` (`hgrc`, `hgr_mode_asm.s`,
      `hgr_mode_clear_asm.s`), tables de lignes en RAM
      (`dev/lib/hgr/hgr_scanline_ram.asm` en `$0200`), page de dessin par
      opérandes patchés (`dev/lib/hgr/hgr_pages.inc` / `hgr_pages.asm`,
      `HGR_HI_SITE`), bascule `$C054/$C055` après le VBL.
- [ ] Horloge (`[jeu]` d'abord, `[lib]` ensuite) : //e = front VBL de
      `$C019` (`dev/lib/apple2c/apple2frame.s`, `a2_frame_init/wait`) ;
      //c = mode 9 de la souris + gestionnaire ProDOS `ALLOC_INTERRUPT`
      (`dev/lib/mouse/mouse.s` : `_mouse_timing_mode`, `_mouse_serve_irq`),
      compteur `a2_cadence_tick` (`dev/lib/apple2c/apple2cadence.s`, période 2).
      Repli borné si le VBL disparaît. **Factoriser** `chromabreak/src/timing.s`
      en `[lib]` `dev/lib/apple2c/apple2vbl.s` (VBL //e + //c + manette lue
      dans l'attente) : deux clients, la règle du dépôt est remplie.
- [ ] Pas de jeu fixe : la logique avance d'un pas par paire de
      rafraîchissements comptés par l'horloge, pas par image dessinée ; une
      image en retard rattrape au plus un pas. (Écueil ARKABREAKOUT : une
      attente fixe `WAIT` ajoutée au rendu fait changer la vitesse du jeu à
      chaque optimisation.)
- [ ] Champ d'étoiles : ~24 étoiles sur 3 vitesses, 1 octet chacune,
      effacée puis reposée par page (historique par page).
- [ ] Vaisseau 14×10 prédécalé (7 phases, pas de 2 points), gauche/droite
      au clavier : `$C000` + `BIT $C010` pour acquitter, et `$C010` bit 7
      (touche tenue) pour continuer à bouger ; Pomme ouverte / fermée
      `$C061/$C062` lues en continu.
- [ ] Tir simple, 5 tirs à l'écran au plus (jauge B de départ).
- **Accepté si** : démarre sur //e enhanced et //c dans POM2, refuse une
  //e NMOS ; 30 i/s tenus (aucune échéance VBL manquée sur 1 000 images,
  NTSC et PAL) ; ESC → ProDOS `QUIT` propre, `/RAM` reformaté ; Ctrl-RESET
  suit la même sortie.

## Lot 2 — V0.2 : sprites, formation, plongées

- [ ] `[jeu]` `tools/sprites.py` : dessins en ASCII → 7 prédécalages HGR
      (groupe de 14 points, bit de palette par octet, parité de colonne),
      largeur 2 → 3 octets, avec ou sans masque. Base :
      `dev/tools/assets/pack_hgr_sprites.py` (l'étendre plutôt que copier :
      `[lib]`).
- [ ] `[jeu]` `src/sprites.s` : dessin `ORA` sur fond noir, effacement par
      `STZ`/`STA #0` du rectangle de l'image d'avant, boucles déroulées par
      hauteur, liste d'effacement **par page**. Pas de `hgr_sprengine`
      (`dev/lib/hgrc`) : 8 emplacements au plus et sauvegarde du fond
      inutile ici ; son bench « quatre sprites 21×16 tous mobiles » fait
      39 217 cycles. Pas de `hgr_tile_restore` dans l'aire de jeu (fond
      noir) : il ne sert que si le HUD a un décor.
      Promouvoir en `[lib]` `dev/lib/hgr/hgr_sprite_black.asm` une fois
      stable (voisin de `hgr_xor.asm`, qui ne fait que 2 octets × 8 lignes).
- [ ] Mesurer un alien 14×10 : objectif ≤ 650 cycles dessin, ≤ 400
      effacement, toutes phases. Si plus : sprites compilés (comparaison
      déjà faite dans `make test-techniques`).
- [ ] Formation de 10 puis 40 aliens (5 rangées × 8) ; « respiration » par
      pas de 2 points, une rangée par image.
- [ ] `[jeu]` `tools/paths.py` : trajectoires d'entrée et de plongée en
      tables (Δx, Δy signés par pas, ou positions 8.8 virgule fixe), tirées
      de courbes (sinus, boucles, spirales) calculées en Python ; aucune
      trigonométrie à l'exécution. Symétrie gauche/droite par signe de Δx
      (boucle des 100 niveaux en miroir). Plongées du TMS Galaga de POM1
      (droite, zigzag, diagonale, boucle) comme premier jeu de tables.
- [ ] Hasard : `dev/lib/math/random.asm` ; multiplications éventuelles :
      `dev/lib/math/mul.asm` (`MUL_TABLES` alignée sur une page).
- [ ] `[jeu]` `tools/model.py` : modèle Python de la logique (formation,
      plongées, tirs, collisions, hasard), **oracle au bit près** comme
      `dirtbike/tools/physics.py` ; `tests/test_logic.py` rejoue un script
      d'entrées de 2 000 pas et compare l'état 6502 (`a2test` :
      `Labels.peek`) à chaque pas témoin.
- **Accepté si** : 40 aliens en formation + 6 plongeurs + 10 tirs à 30 i/s
  sur la pire phase ; test oracle vert.

## Lot 3 — collisions, tirs ennemis, vies, score, HUD

- [ ] Collisions par boîtes en coordonnées logiques (pas de lecture de
      l'écran) : tir/alien, tir ennemi/vaisseau, alien/vaisseau ; grille
      grossière par colonne pour ne tester que les aliens proches.
- [ ] Vies (3, max 4), réapparition, invulnérabilité courte.
- [ ] Armure (max 2) : absorbe un tir ennemi puis bouclier quelques
      secondes. Contre une collision : à décider (voir questions).
- [ ] Score BCD (mode décimal du 65C02, comme CHROMABREAK) ; crédits.
- [ ] HUD : `hgr_hud8` (`dev/lib/hgrc` : `hgr_hud8_asm.s`, `hgr_hud8_putu.s`,
      historique par page, 7 850 cycles pour 5 chiffres) **un chiffre au plus
      par image** ; jauges S/B/T en barres d'octets. Texte : `hgr_text8`
      (`dev/lib/hgr/hgr_text8.asm`, `HGR_TEXT8_HGR_ORDER=1`) et
      `dev/lib/font/bbfont.inc` ; texte ×1 blanc seulement (règle de `lib/hgr`).
- [ ] Conversion décimale hors BCD (boutique, records) : `gfx_u16_digits`
      (`dev/lib/gfx`, 65C02) ou le noyau décimal unique du lot 3 des libs
      **s'il est fusionné** (en attente).
- **Accepté si** : `test_logic.py` couvre les collisions ; une partie
  jouée par script perd ses 3 vies au bon pas.

## Lot 4 — son : Mockingboard ou haut-parleur

- [ ] Détection au démarrage, **avant la souris** : `mb_detect`
      (`dev/lib/apple2/mockingboard.asm`) ; //e : slots 7..1 sauf 3 ;
      //c : réveil de la Mockingboard 4c à `$C403`. Résultat dans une
      variable `audio_backend` (0 = haut-parleur, n = slot).
- [ ] Vérifier sur //c avec Mockingboard 4c que la souris (et donc le VBL du
      mode 9) reste utilisable ; sinon horloge par le timer T1 de la VIA
      (régulière mais pas calée sur le VBL : déchirure possible à la bascule).
- [ ] `[lib]` `mockingboard.asm` : `mb_write` en `STA $Cn00/$Cn01` absolus
      patchés par `mb_init` (−35 % estimé par l'audit, **non fait**).
- [ ] `[lib]` `dev/lib/apple2/pt3.asm` : lecteur PT3 (aucun dans `dev/lib`).
      Base : `pt3_lib` de Vince Weaver (0BSD) ou le port GROUiK d'A2FileCmd
      (voir `dev/lib/apple2/README.md`, « Extension PT3 ») ; ZP allouée par
      ld65, morceau aligné sur 256 octets, table de fréquences AY convertie
      pour 1,023 MHz ; ne pas réécrire R13 quand le décodeur rend `$FF`.
- [ ] Back-end AY : un gestionnaire ProDOS unique sert le T1 de la VIA à
      50 Hz (recharge ~20 454 cycles) → tick PT3 + bruitages AY (une voix
      réservée aux bruitages). Pas de ZP cc65 ni de pile C dans
      l'interruption. Mesurer le pire tick (10-15 % du CPU annoncé en amont,
      soit ~3 000-4 300 cycles par image de jeu) : il doit tenir dans les
      6 000 réservés.
- [ ] Back-end haut-parleur : bruitages non bloquants joués **dans
      l'attente du VBL** (boucle comptée qui bascule `$C030` tant que
      l'échéance n'est pas atteinte ; sans temps libre, l'effet est sauté,
      jamais l'image retardée). `[lib]` candidat :
      `dev/lib/apple2/sfx_wait.asm`. `tone` (`dev/lib/apple2/sound.asm`) reste
      pour les écrans fixes seulement (il bloque).
- [ ] Musique haut-parleur hors jeu : `dev/lib/apple2/duet.asm` **si
      disponible** (lot 3 des libs ; sinon `chromabreak/src/duet.inc`), boucle
      en page 3 sans franchir de page, IRQ masquées pendant une note.
- [ ] Silence AY avant chaque accès disque (le pilote Disk II de ProDOS
      masque les IRQ : la musique s'arrête pendant un chargement).
- [ ] Tests : `tests/test_audio.py --mockingboard` (a2shot `--iie
      --mockingboard`, carte en slot 4 avec IRQ VIA) : détection, registres
      AY écrits, ticks à 50 Hz ; `tests/test_audio.py` sans carte : bascules
      du haut-parleur (`Result.spk`) ; **test de cadence** : 1 000 images avec
      et sans carte, même nombre de pas logiques et même état final (le son
      ne change pas la vitesse) ; `dev/tests/test_rgb_mockingboard.py` reste
      vert après la modification de `mb_write`.

## Lot 5 — bonus et jauges

- [ ] Objets qui tombent (≤ 6 à la fois) : pièces 10/50/100/200, S, B, T,
      armes (simple, double, triple), tir automatique, armure, vie, crâne,
      lettres E-X-T-R-A, ×2/×5, bouclier, gel, icônes des sous-jeux,
      marques de rang.
- [ ] Jauges S (vitesse du vaisseau), B (tirs à l'écran), T (durée des
      bonus temporaires) avec leur maximum ; au maximum, l'icône donne des
      points.
- **Accepté si** : `test_logic.py` couvre chaque effet.

## Lot 6 — 100 niveaux, paquets, boss

- [ ] `[jeu]` `tools/levels.py` → 25 paquets de 4 niveaux (vagues,
      trajectoires, cadence de tir, dessin d'alien du paquet), 4e niveau
      bonus / kamikaze en alternance, boss aux niveaux 25/50/75/100, boucle
      en miroir et plus rapide après le 100.
- [ ] Réserve en mémoire aux : `WG2.AUX` chargé une fois au démarrage
      (dessins des 25 paquets, trajectoires, musiques) ; copie du paquet
      courant en `$1000-$1FFF` par `AUXMOVE` (`$C311`) pendant la
      « téléportation ». Compression LZ4FH si besoin
      (`dev/lib/apple2/lz4fh.asm`, outil `$(FHPACK)` de `dev/cc65/fhpack.mk`).
- [ ] Boss : sprite composé (32×24 ou plus), points faibles, tirs en
      rosace (table d'angles, comme le super boss du TMS Galaga).
- [ ] Hurry-up : vaisseau qui passe si le niveau traîne.
- **Accepté si** : un pilote automatique (`tools/autopilot.py`, modèle)
  finit les niveaux 1, 25 et 100 ; bench du pire niveau dans le budget.

## Lot 7 — boutique et rangs

- [ ] Boutique après chaque paquet si ≥ 50 crédits : ~12 objets
      (vitesse, tir supplémentaire, double/triple, tir automatique, armure,
      vie, temps, marque de rang, 2-3 armes), prix d'après la référence ;
      écran fixe, routines lentes permises (texte, chiffres, cadres).
      Overlay chargé à `$4000` comme le `ENDING` de CHROMABREAK (hors jeu).
- [ ] Rangs : 6 marques de couleur ; les 6 réunies → rang supérieur à la
      sortie de la boutique ; marque sombre : rang inférieur.

## Lot 8 — sous-jeux

- [ ] Meteor Storm : astéroïdes qui descendent, tir = accélérer (on
      ralentit plus vite qu'on accélère), jauge de vitesse et de distance,
      choc = retour au jeu sans perte de vie, prime selon la vitesse.
      Mêmes sprites et même cadence que le jeu.
- [ ] Memory Station : grille de paires, temps = jauge T, grille plus grande
      à chaque réussite (+25 000), pavillon pirate = fin. Écran fixe,
      souris possible (`dev/lib/mouse`).

## Lot 9 — titre, démo, records, intégration

- [ ] Titre (image LZ4FH), démo en attract mode rejouant un script
      d'entrées (comme DIRTBIKE), aide.
- [ ] `HIGHSCORES` ProDOS (`records.c` de CHROMABREAK comme modèle : MLI
      `OPEN/READ/WRITE`, disquette protégée signalée), initiales.
- [ ] Choix du périphérique : clavier, manette (port //e, DB-9 //c), souris
      (AppleMouse II //e, intégrée //c), retenu dans `HIGHSCORES`.
- [ ] Construction : `dist/WARGALAGAII.po` (`dev/tools/prodos/build_volume.py
      --volume WARGALAGAII --blocks 280`), `make run` (`APPLE2_PRESET := iie`,
      `--slot 4=mouseaw`), `make run-iic`.
- [ ] Racine : ajouter `wargalagaii` à `IIE_PRODOS_GAMES` (donc `all`,
      `profile-iie-prodos`), une cible `test-wargalagaii` dans `test`, la
      ligne du tableau du README racine ; `make check` (disque identique
      après reconstruction) puis `dist/` commité.
- [ ] Bench : scènes « formation pleine + 6 plongeurs + 10 tirs », « boss »,
      « Meteor Storm » mesurées dans le jeu (profil `dev/tools/a2profile.py`)
      et comparées à 28 060 / 34 560 cycles (NTSC / PAL, réserve de 6 000
      comprise, `dev/bench/budgets.json`) ; entrée `bench-check` si une
      partie passe en lib.
- [ ] Validation sur vraies machines (//e enhanced + Mockingboard, //c,
      //c + Mockingboard 4c), selon `dev/lib/HARDWARE.md`.

## Écueils connus du dépôt

- Clavier : lire `$C000` puis acquitter par `BIT $C010` ; sur //e la lecture
  de `$C010` rend aussi « touche tenue » en bit 7.
- `ldx #191 … dex / bpl` ne boucle jamais (191 > 127) : `cpx #$FF / bne`.
- Options des libs testées **par valeur** (`RWTS_SEI`, `DOS_SEI`,
  `MUL_INIT_BOOT`…) : `=0` équivaut à absent, mettre `=1` pour activer ;
  quelques-unes restent en `.ifdef` (lire l'en-tête du module).
- Libs assembleur gardées par `.ifref` : les inclure **à la fin** du source,
  après leurs appelants.
- Boucles à cycles comptés (haut-parleur, attente) : `.assert` qu'elles ne
  franchissent pas de page (DIRTBIKE : `tone` à cheval sur une page = notes
  20 % trop longues). Adresses figées des modules rapides (CHROMABREAK :
  `spare.s`) : quelques octets de décalage ont déjà coûté une image.
- Valeurs de départ : le CRT met la BSS à zéro, **pas `LOWBSS`**, que
  l'application initialise elle-même (`dev/lib/ABI.md`) ; une variable qui
  doit partir d'une valeur va en `DATA` (DIRTBIKE).
- Mémoire aux : avec `RAMRD` en aux, le code lui-même est lu en aux ; une
  boucle qui lit des données aux doit exister aux deux adresses
  (CHROMABREAK copie sa boucle de sprite dans les deux banques). Préférer
  `AUXMOVE` entre deux niveaux.
- IRQ : le gestionnaire ne touche ni la ZP cc65 ni sa pile, ni les
  commutateurs graphiques ; la souris du //c envoie 60 IRQ/s ; la
  Mockingboard 4c se détecte avant la souris.
- `$C05E/$C05F` règlent la souris sur //c si IOUDIS n'est pas mis
  (CHROMABREAK) : ne pas toucher AN3 en HGR.
- POM2 relit la mémoire en fin d'image (« beam racing ») : une bascule de
  page trop rapprochée montre une page en cours de dessin
  (`dev/tools/a2shot/LETTRE_POM2_AFFICHAGE_MANETTE.md`).

## Questions ouvertes

1. Écrans fixes (titre, boutique, Memory Station) en DHGR 16 couleurs ?
   Plus beau, mais la DHGR occupe aux `$2000-$5FFF` (à exclure de la
   réserve) et ajoute les libs DHGR. Proposition : HGR partout d'abord.
2. PAL : jeu 17 % plus lent (comme CHROMABREAK) ou vitesses par seconde ?
3. Collision alien/vaisseau : mort directe, ou l'armure protège aussi ?
4. Volume 140 Ko suffit-il (estimation : ~24 Ko de code, ~40 Ko de
   paquets, musiques), ou 800 Ko comme NeoWildernessXL ?
5. Musique en jeu sans Mockingboard : aucune (bruitages seuls) — d'accord ?
6. Combien de dessins d'aliens : 25 (un par paquet, comme Warblade) ou moins
   avec des palettes ?
