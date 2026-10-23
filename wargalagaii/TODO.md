# WARGALAGA II — plan de travail

Cible : Apple //e enhanced et //c, 128 Ko, 65C02, ProDOS, HGR double tampon
partout, 30 i/s NTSC (2 rafraîchissements par image ; 25 en PAL, jeu 17 %
plus lent, accepté), avec ou sans Mockingboard, clavier et manette (pas de
souris), disquette 140 Ko.
Raisons et carte mémoire : [README](README.md). Règles reprises de Warblade :
[docs/warblade-reference.md](docs/warblade-reference.md).

Modèle de projet : [CHROMABREAK](../chromabreak/README.md) pour l'amorce
ProDOS, `/RAM`, la cadence //e et //c, la manette lue dans l'attente ; [DIRTBIKE](../dirtbike/README.md) pour le modèle Python oracle
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

## Lot 1 — V0.1 : démarrage, horloge, vaisseau, tir (fait, 2026-10-23)

Jeu en assembleur 65C02 (`src/game.s`, `src/timing.s`) derrière le crt0
ProDOS de cc65 ; `src/game.cfg` = `apple2_dhgr_prodos_c.cfg` + segment
`SYSBSS` en `$0200-$03CF` (tables `hgr_lo/hi`).

- [x] `src/boot.s` / `boot.cfg` : `WG2.SYSTEM`, refus d'un 6502 NMOS (test
      `INC A`), charge `WG2.SYS` ; `src/startup.s` le reloge à `$6000`.
- [x] Lien `crt0_prodos.s` + `none.lib`, libs `mli.s`, `video.s`, `mouse.s`,
      `apple2frame.s`.
- [x] `/RAM` réclamé (`PD_VIDEO_DISCARD_RAM`) puis reformaté à la sortie ;
      128 Ko vérifiés par MACHID (`$BF98`), sinon message.
- [x] HGR double tampon : `hgr_scanline_ram.asm` (`$0200`), pages par
      opérandes patchés (`hgr_pages.inc/.asm`), bascule `$C054/$C055`.
- [x] Horloge `src/timing.s` (dérivée de `chromabreak/src/timing.s`) : //e =
      fronts de `$C019` comptés par `timing_scan` (appelé entre les phases du
      dessin), //c = interruption VBL du firmware souris (mode 9, ProDOS
      `ALLOC_INTERRUPT`), sinon délais `a2_frame_wait`. Attente bornée, repli.
      Manette (paddle 0) lue dans l'attente, jusqu'à l'échéance.
- [x] Pas fixe : un pas logique par paire de rafraîchissements comptés entre
      deux bascules (`timing_refreshes`), reste reporté, au plus 2 pas par image.
- [x] 24 étoiles sur 3 vitesses, 1 point chacune ; effacées seulement si leur
      octet n'a pas changé, posées seulement sur un octet noir.
- [x] Vaisseau 7 cellules × 10 lignes, 7 prédécalages (`tools/sprites.py`),
      redessiné sur une page seulement s'il a bougé depuis cette page.
- [x] Clavier : ← → / J L (la direction tient tant qu'une touche est
      enfoncée, `$C010` bit 7, donc ESPACE ne l'arrête pas), ESPACE et Pomme
      ouverte / bouton 0 tirent (front). **TAB** bascule clavier / manette en
      attendant le menu du lot 9.
- [x] Tir simple, 5 au plus (jauge B de départ), listes d'effacement par page.
- [x] `tools/model.py` (oracle de la logique, commencé dès ce lot) et
      `tests/test_game.py` (`make test`, ~3 s).
- **Acceptation** (`make test`) : volume ; 1 000 images en 2 000
  rafraîchissements, aucune en retard, NTSC et PAL ; 300 pas identiques au
  modèle ; flèches, ESPACE, Pomme ouverte, manette ; ESC et Ctrl-RESET →
  texte, `/RAM` reconstruit, lanceur ProDOS ; II+ (NMOS) → message. Rendu
  mesuré : ~8 400 cycles avec vaisseau mobile, 5 tirs, 24 étoiles (budget
  28 060).
- [ ] **Reste** : //c non testé (a2shot n'a pas de //c : `make run-iic`
      dans POM2 ou une vraie machine) ; factoriser `src/timing.s` et
      `chromabreak/src/timing.s` en `[lib]` `dev/lib/apple2c/apple2vbl.s`
      (bascule de page en paramètre : DHGR et HGR), CHROMABREAK à garder
      identique.

## Lot 2 — V0.2 : sprites, formation, plongées (fait, 2026-10-23)

Code : `src/logic.s` (logique), `src/render.s` (dessin), `src/game.s`
(boucle, entrées, tables). Tables de lignes alignées en `$1000-$12FF`
(segment `ROWS`) : `hgr_hi+R,X` par ligne R du sprite, et `select_page`
ne réécrit que l'octet fort de chaque opérande (`HI_LDA`) ; `hgr_pages`
de la lib n'est plus utilisé (il réécrit les deux octets et ne gère pas
`+R`).

- [x] `tools/sprites.py` : dessins par cellules de 2 points, `X` = point de
      la teinte (violet, vert, bleu, orange), 7 prédécalages, entrée
      `2*décalage+image`. **6 petits aliens en 7×8 cellules** (8 lignes et
      non 10 : 20 % de moins par alien), 2 gros en 10×16, 2 images chacun ;
      `--png F` donne la planche de tous les dessins et teintes. Écrit à
      part de `dev/tools/assets/pack_hgr_sprites.py` (cellules et teintes
      propres au jeu) ; à rapprocher si un second jeu en a besoin.
      **Boss pas encore dessiné** (lot 6). Le jeu ne lie qu'un dessin et
      une teinte (`GAME_SMALL`) : la réserve en mémoire aux est au lot 6.
- [x] Dessin (`src/render.s`) : routines déroulées par macro
      (`SPRITE_ROWS`). Mesures (`make test`) : alien posé **STA 470**
      cycles, **EOR 593**, effacement **322** (objectifs 650 / 400 tenus).
      Changement de méthode en cours de lot : effacer en zéros ce qui vole
      abîmait la formation (redessin sur les deux pages : 47 000 cycles par
      image) ; **ce qui vole (plongeurs, aliens en entrée, tirs) est tracé
      et effacé en EOR**, dans l'ordre exactement inverse du tracé, ce qui
      rend l'écran tel quel sans rien redessiner. Formation posée en STA,
      vaisseau en STA. Tirs : un octet, motif identique sur 6 lignes.
- [x] Formation 5 × 8, respiration d'une cellule ; **une rangée tous les
      2 pas** (une par pas = 16 aliens redessinés par image, chaque
      changement étant tracé sur les deux pages). Une rangée inchangée
      depuis le dernier tracé de la page est sautée en quelques tests.
- [x] `tools/paths.py` : tortue (cap, vitesse, virage) échantillonnée à
      chaque pas, quantifiée en octets Δx (cellules) / Δy (lignes) signés
      4 bits, `$80` = fin ; 1 entrée (boucle) en miroir à droite, 4 plongées
      (demi-tour puis : dérive, zigzag, diagonale, boucle), en miroir sur la
      moitié droite de la formation.
- [x] Vagues : 5 vagues de 4 paires (une rangée chacune, du centre vers
      les bords), puis retour à la place ; plongée toutes les 20 pas si
      moins de 6 aliens volent ; sortie par le bas → retour par le haut.
      Hasard : `dev/lib/math/random.asm`.
- [x] `tools/model.py` : oracle au bit près ; `tests/test_game.py`
      compare **2 000 pas** à chaque pas (état complet + hasard).
- **Acceptation** (`make test`, ~8 s) : banc formation + plongeurs +
  **10 tirs** tirés sans arrêt : **0 image en retard sur 300** ; formation
  posée : 0 retard sur 1 000 images NTSC et PAL ; oracle vert. Profil
  (`tools/profile.py`) : rendu moyen 17 300 / pire 23 200 cycles sans tirs,
  22 000 / 28 000 avec 10 tirs ; logique ~3 000-3 600.
- **Reste / à surveiller** :
  - Phase d'entrée : jusqu'à ~16 aliens volent ; en NTSC 3 images en
    retard (sur ~1 600) quand une vague arrive pendant que la précédente
    se pose, la vitesse du jeu restant exacte (prévu par le README). PAL :
    aucune.
  - Le pire cas avec 10 tirs (28 000 + logique 3 400) dépasse les 28 060
    qui gardent 6 000 cycles pour la musique sous IRQ (lot 4). Pistes :
    sauter les colonnes d'octets vides selon le décalage, étoiles moins
    chères (~2 300 cycles, ~1 500 prévus), données d'alien à adresse fixe
    (copie du paquet en `$1000`, lot 6) pour un `LDA abs,X`.
  - Promouvoir les routines en `[lib]` `dev/lib/hgr/` une fois stables.

## Lot 3 — collisions, tirs ennemis, vies, score, HUD

- [ ] Collisions par boîtes en coordonnées logiques (pas de lecture de
      l'écran) : tir/alien, tir ennemi/vaisseau, alien/vaisseau ; grille
      grossière par colonne pour ne tester que les aliens proches.
- [ ] Vies (3, max 4), réapparition, invulnérabilité courte.
- [ ] Armure (max 2) : absorbe un tir ennemi puis bouclier quelques
      secondes. **Une collision avec un alien tue directement**, armure ou
      pas (décision du 2026-10-22).
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

- [ ] Détection au démarrage, **avant d'installer l'horloge VBL du //c**
      (firmware souris) : `mb_detect`
      (`dev/lib/apple2/mockingboard.asm`) ; //e : slots 7..1 sauf 3 ;
      //c : réveil de la Mockingboard 4c à `$C403`. Résultat dans une
      variable `audio_backend` (0 = haut-parleur, n = slot).
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
- [ ] Back-end haut-parleur (décision du 2026-10-22 : en jeu, bruitages
      seulement ; musique seulement hors jeu) : bruitages non bloquants joués **dans
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
      (dessins × teintes, trajectoires, musiques) ; copie du paquet
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
      écran fixe **HGR**, routines lentes permises (texte, chiffres, cadres) ;
      flèches + RETURN, ou manette haut/bas + bouton 0.
      Overlay chargé à `$4000` comme le `ENDING` de CHROMABREAK (hors jeu).
- [ ] Rangs : 6 marques de couleur ; les 6 réunies → rang supérieur à la
      sortie de la boutique ; marque sombre : rang inférieur.

## Lot 8 — sous-jeux

- [ ] Meteor Storm : astéroïdes qui descendent, tir = accélérer (on
      ralentit plus vite qu'on accélère), jauge de vitesse et de distance,
      choc = retour au jeu sans perte de vie, prime selon la vitesse.
      Mêmes sprites et même cadence que le jeu.
- [ ] Memory Station : grille de paires, temps = jauge T, grille plus grande
      à chaque réussite (+25 000), pavillon pirate = fin. Écran fixe HGR,
      curseur au clavier ou à la manette.

## Lot 9 — titre, démo, records, intégration

- [ ] Titre HGR (image LZ4FH), démo en attract mode rejouant un script
      d'entrées (comme DIRTBIKE), aide.
- [ ] `HIGHSCORES` ProDOS (`records.c` de CHROMABREAK comme modèle : MLI
      `OPEN/READ/WRITE`, disquette protégée signalée), initiales.
- [ ] Choix du périphérique : clavier ou manette (port //e, DB-9 //c),
      retenu dans `HIGHSCORES`. Pas de souris.
- [ ] Construction : `dist/WARGALAGAII.po` (`dev/tools/prodos/build_volume.py
      --volume WARGALAGAII --blocks 280`, 140 Ko suffisent), `make run`
      (`APPLE2_PRESET := iie`, sans carte souris), `make run-iic`
      (`--preset iic --slot 4=iicmouse` : le firmware souris intégré donne
      l'horloge VBL).
- [ ] Racine : ajouter `wargalagaii` à `IIE_PRODOS_GAMES` (donc `all`,
      `profile-iie-prodos`), une cible `test-wargalagaii` dans `test`, la
      ligne du tableau du README racine ; `make check` (disque identique
      après reconstruction) puis `dist/` commité.
- [ ] Bench : scènes « formation pleine + 6 plongeurs + 10 tirs », « boss »,
      « Meteor Storm » mesurées dans le jeu (profil `dev/tools/a2profile.py`)
      et comparées à 28 060 / 34 560 cycles (NTSC / PAL, réserve de 6 000
      comprise, `dev/bench/budgets.json`) ; entrée `bench-check` si une
      partie passe en lib.
- [ ] Validation sur vraies machines (//e enhanced + Mockingboard, //c),
      selon `dev/lib/HARDWARE.md`.

## À vérifier sur machine

- [ ] //c + Mockingboard 4c : la détection réveille la carte à `$C403` et
      peut masquer la ROM souris du slot 4. L'interruption VBL du firmware
      souris (notre horloge //c) reste-t-elle utilisable ? Sinon : horloge par
      le timer T1 de la VIA (régulière, pas calée sur le VBL : déchirure
      possible à la bascule de page).

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
  commutateurs graphiques ; le firmware souris du //c envoie 60 IRQ/s
  (horloge VBL) ; la Mockingboard 4c se détecte avant de l'installer.
- `$C05E/$C05F` règlent la souris sur //c si IOUDIS n'est pas mis
  (CHROMABREAK) : ne pas toucher AN3 en HGR.
- POM2 relit la mémoire en fin d'image (« beam racing ») : une bascule de
  page trop rapprochée montre une page en cours de dessin
  (`dev/tools/a2shot/LETTRE_POM2_AFFICHAGE_MANETTE.md`).

## Décisions (questions closes le 2026-10-22)

1. HGR partout, écrans fixes compris ; DHGR plus tard.
2. PAL : le jeu va 17 % moins vite, comme CHROMABREAK ; pas de vitesses par
   seconde.
3. L'armure protège des tirs ennemis seulement ; une collision tue.
4. Disquette 140 Ko.
5. Sans Mockingboard : bruitages en jeu, musique hors jeu seulement.
6. Peu de dessins (6 petits, 2 gros, 1 boss) × 4 teintes HGR précalculées ;
   d'autres dessins plus tard.
7. Pas de souris comme entrée ; sur //c, son firmware sert seulement
   d'horloge VBL.
