# Neowilderness — inventaire et plan mémoire 128 Ko

Ce document décrit la version du lot 3 : démarrage ProDOS 8 depuis
`dist/NEOWILDERNESS.po`, tous les modules préchargés en RAM auxiliaire (lots
1–2) et paysage DHGR sur une seule page (`$2000-$3FFF` principale et
auxiliaire). Les chiffres viennent de `build/wild.map`, `build/wild.lbl`,
`build/layout.json` (`make inspect`) et `docs/BASELINE_DHGR.json` ; ils
doivent être remesurés après chaque changement de segment. La référence HGR
figée (DOS 3.3, II+) est `build/reference-hgr/` (disque, `wild.lbl`,
`wild.map`), hors Git ; `docs/BASELINE_128K.json` garde les mesures HGR 128 Ko
des lots 1–2.

## 1. Inventaire des segments

Octets = taille liée par ld65 (`build/wild.map`). Nature : C code,
K constantes, E état persistant, T temporaires.

| Segment (fichier) | Adresses | Octets | Nature | Contenu et contraintes |
|---|---|---:|---|---|
| `ZEROPAGE` | `$50-$A3` | 84 | T | Scratch du rendu (`ang`…`num`, passes DHGR `dm`…`dzone`) ; partagé avec la ROM flottante (`$5E-$AC`) : ne survit à aucune commande. Une assertion d'édition de liens garde la fin sous `$A4` (octet d'arrondi d'Applesoft) |
| `ZEROPAGE` (loader) | `$A4-$AF` | 12 | T | Pointeurs de NEOWILD.SYSTEM, morts au lancement du jeu (la ROM y écrit ensuite) |
| `GZP` | `$D0-$ED` | 30 | E/T | Pointeurs `gp1/gp2`, `g0-g2`, analyse de commande, marche (`minutes`, `wdx`…) ; `g0` et `tmp2` servent aussi de `tmp1/tmp2` à `video.s`, seulement au démarrage et à la sortie |
| `WOODS` | `$0800-$0925` | 294 | K | Masque des bois de la carte (non lié, écrit par le chargeur) |
| `FORESTCODE` (`wildforest.bin`) | `$0926-$09FB` | 214 | C | Sonde et peinture des bois |
| `TEXT` (`wildtxt.bin`) | `$0A00-$0FFC` | 1 533 | K/E | Messages, constantes, tables de rotation, quelques états textuels |
| `LOWDATA`/`LOWCODE`/`LOWTEXT` (`wildlo.bin`) | `$1000-$1EDC` | 3 805 | C/K/E | Projection, **lignes DHGR déroulées** (`drows`, 1 601), effacement des deux banques, LOOK, raccourcis, noms d'objets, compteurs de charge |
| `LOWCACHE` | `$1EDD-$1FDC` | 256 | T | `row_n0`, recalculé par `project_init` |
| page DHGR, moitié principale | `$2000-$3FFF` | 8 192 | vidéo | Vue logique 16–159, bandeau et panneaux 0–15, cache 160–175 (lignes logiques 0–15) ; TOPO y est copié (affiché en HGR simple) |
| `GCODE`/`GDATA` (`wildgame.bin`) | `$4000-$57C8` | 6 089 | C/E/K | Logique résidente, état de la partie (`px`…`it_*`, horloge, santé, météo, hasard), chargeur de modules ; humeurs DHGR (302 octets de tables), choix d'humeur, altitudes `sun_alt8`…`sky_mood`, demi-pixels du bandeau, modes vidéo |
| `BSS` | `$57C9-$57F2` | 42 | E/T | `video.s` (unité /RAM) et `mli.s` ; palette courante de la trame (`cur_pal`, couleurs des sprites), variables des bandes de 8 lignes ; mis à zéro par le chargeur |
| fenêtre `$5800` | `$5800-$5FFF` | ≤ 2 048 | C/K/T | Un module à la fois (tableau 2) ; son image est restaurée à chaque chargement |
| `CODE`/`RODATA` (`wild.bin`) | `$6000-$6FDB` | 4 060 | C/K | Démarrage, moteur de vue, passes DHGR (`dspan`, `column_setup`, tables d'entrée des lignes), texte 40 colonnes propre, sprites, saisie, impressions, transitions, `video.s`, `mli.s` |
| `WILDMAP` | `$7000-$94FF` | 9 472 | K | En-tête 64 octets et grille 112 × 84 |
| `SCRATCH` | `$9500-$95FF` | 256 | T | `overlay_text` (160) : couleurs de colonne des sprites **et** flottants temporaires du ciel ; puis `scene_*`, thermique, saisie |
| `ENVIRON`+`THERMAL` (`wildsim.bin`) | `$9600-$B5FE` | 8 191 | C/K/T | Simulation ; données de l'image rechargées à chaque activation (même sémantique que le BLOAD HGR) |
| `RESCODE` (`wildres.bin`) | `$B600-$B987` | 904 | C/K | Répertoire des modules (161), `mem_fetch`, boucle de pile, `mli_call`, `geo_load`, sortie/RESET |
| `RESBSS` | `$B988-$B9DA` | 83 | E | Compteurs, vecteur RESET et bitmap ProDOS sauvegardés, chemin de NEOWILD.GEO |
| `IOBUF` | `$BA00-$BDFF` | 1 024 | T | Tampon d'E/S ProDOS (chargeur, géographie native) |
| `SAVE` | `$BE00-$BEFF` | 256 | E | Page zéro de ProDOS à l'entrée, restaurée à la sortie |
| `SYSSTUB`+`LOADER` (`NEOWILD.SYSTEM`) | `$2000` puis `$9600-$9EFA` | 2 267 | C/T | Chargeur transitoire, exécuté dans la fenêtre SIM avant la première activation |

Modules de la fenêtre `$5800` (identifiants de `overlay_load`, inchangés) :

| ID | Image | Octets | ID | Image | Octets |
|---:|---|---:|---:|---|---:|
| 0 | TOPO (`graphical_topo.py`) → `$2000` | 8 192 | 12 | `wildtrv.bin` | 2 045 |
| 1 | `wildvoc.bin` | 2 047 | 13 | `wildinp.bin` | 1 442 |
| 2 | `wildscr.bin` | 2 040 | 14 | `wilditm.bin` | 1 647 |
| 3 | `wildsim.bin` → `$9600` | 8 191 | 15 | `wildhud.bin` | 1 739 |
| 4 | `wildwat.bin` | 495 | 16 | `wildsta.bin` | 2 048 |
| 5–9 | épave, ours, couguar, crotale, cabane | 1 900, 781, 539, 485, 1 133 | 17/18 | `wildmed.bin` (médical + dangers) | 2 045 |
| 10 | `wildsit.bin` | 1 915 | 19 | `wildmvi.bin` | 878 |
| 11 | `wildprj.bin` | 1 134 | 20–22 | `wildtre`, `wildadv`, `wildout` | 916, 1 971, 1 982 |

`wildgeo.bin` (1 861) n'est pas un module : c'est le gabarit des 24 banques
de géographie fine (IDs 23–46), présentes seulement sur les disques de
comparaison et lues à la demande (lot 5).

### Appels entre segments

Extraits des `jsr`/`jmp` des sources (`.segment` courant → segment de la
cible) :

| Appelant | Cibles hors de son segment |
|---|---|
| GAME | tous les modules, FOREST, LOW, MAIN, TEXT, SIM, RESIDENT |
| MAIN | GAME, LOW, TEXT, INPUT, VOCAB, RESIDENT |
| LOW | GAME, MAIN, TEXT, TRAVEL |
| SIM | GAME, LOW, MAIN, ADVENTURE, MEDICAL, OUTDOOR, TRAVEL |
| TRAVEL, ITEMS, MEDICAL, OUTDOOR, WATER, ADVENTURE | GAME, LOW, MAIN et **SIM** |
| SITES | GAME, LOW, MAIN, FOREST, RESIDENT (TOPO) |
| autres modules | GAME, LOW, MAIN |

Règle conservée : un module n'en charge pas un autre dans sa propre fenêtre
sans repasser par du code résident. Les appels de modules vers SIM supposent
que la fenêtre SIM contient du code valide : dans la version HGR, HGR page 1
pouvait contenir l'image à ce moment (voir §6).

### Adresses absolues

- Carte `MAP = $7000` (`M_*`), fenêtre `$5800` (`geo_rows`, `cmp $5800` des
  sprites, `unpack` supprimé), lignes DHGR `$2000` déroulées dans `drows`
  (une copie sert aux deux banques, choisies par `PAGE2` sous `80STORE`).
- ROM : Applesoft (`MOVFM $EAF9`… `FEXP $EF09`), Moniteur (`COUT`
  seulement par `CSW`, identifiants `$FBB3`/`$FBC0`). Le jeu n'appelle plus
  `HOME`, `VTAB`, `CLREOL`, `CLREOP` ni la sortie `COUT1` du Moniteur :
  sur IIe enhanced, `COUT1` teste `RD80VID` (`$FC46 BIT $C01F`) et passe en
  mise en page 80 colonnes dès que la DHGR est affichée ; `src/dhgr.s` fournit
  des équivalents 40 colonnes (`t_cout`, `t_vtab`, `t_home`, `t_clreol`,
  `t_clreop`, défilement de fenêtre), installés dans `CSW` au démarrage.
- ProDOS : MLI `$BF00`, `DEVNUM $BF30`, `DEVCNT/DEVLST $BF31-$BF3F`,
  `DEVADR $BF10`, bitmap `$BF58-$BF6F`, `MACHID $BF98` ; FORMAT de /RAM à
  `$FF00` (banque 1 de la carte langage principale, via `video.s`).
- Vecteur RESET `$03F2-$03F4` ; boucle de copie `XFER_RUN = $0120`.
- Chargeur : tampon `STAGE = $2000`, décodage auxiliaire `TEMP = $7000`,
  table `$A000`, tampon d'E/S `$BA00`.

## 2. Plan principal / auxiliaire

### RAM principale

| Zone | Usage | Libre |
|---|---|---:|
| `$0000-$00FF` | page zéro (§3) | — |
| `$0100-$01FF` | pile ; FOUT écrit `$0100-$0110` ; boucle de copie `$0120-$015B` pendant un transfert | — |
| `$0200-$03CF` | inutilisé (ProDOS/Moniteur) | — |
| `$03D0-$03FF` | vecteurs ProDOS ; RESET → `reset_exit` pendant le jeu | — |
| `$0400-$07FF` | texte page 1 (intro, menus, 4 lignes mixtes, colonnes impaires en DHGR) | — |
| `$0800-$0FFF` | bois, aide forêt, WILDTXT | 7 |
| `$1000-$1FFF` | WILDLO + cache de projection | 35 |
| `$2000-$3FFF` | page DHGR, moitié principale | — |
| `$4000-$57FF` | WILDGAME + BSS | 13 |
| `$5800-$5FFF` | fenêtre de modules | 0 à 1 553 selon le module |
| `$6000-$6FFF` | WILDERNESS | 36 |
| `$7000-$94FF` | carte | 0 |
| `$9500-$95FF` | scratch | 0 |
| `$9600-$B5FF` | fenêtre SIM (chargeur au démarrage) | 1 |
| `$B600-$B9FF` | RESIDENT | 37 |
| `$BA00-$BDFF` | tampon d'E/S ProDOS | (réservé) |
| `$BE00-$BEFF` | page zéro de ProDOS sauvegardée | — |
| `$BF00-$BFFF` | page globale ProDOS | — |
| carte langage | ProDOS 8 ; le jeu lit la ROM (`$C082`) | — |

Le passage à ProDOS libère `$9600-$BEFF` (10 496 octets) ; la simulation y
quitte `$2000-$3FFF`. Le retrait de DOS (`dos.asm`, `exit.asm`, noms de
fichiers, sauvegarde des lignes de texte, décodeur en place) libère en plus
environ 930 octets dans WILDGAME, 290 dans WILDLO et 170 dans WILDERNESS
(mesurés contre la référence HGR synchronisée).

Bitmap ProDOS pendant le jeu : pages `$08-$57`, `$60-$B9` et `$BE` marquées
en plus de celles de ProDOS ; la fenêtre `$58-$5F` et le tampon `$BA-$BD`
restent libres pour les lectures de géographie native. Le bitmap d'origine
est rétabli à la sortie.

### RAM auxiliaire

| Zone | Usage | Libre |
|---|---|---:|
| `$0000-$01FF` | page zéro et pile auxiliaires : jamais utilisées | — |
| `$0200-$03FF` | code du pilote /RAM de ProDOS (appelé par FORMAT à la sortie) : intouchable | — |
| `$0400-$07FF` | texte : colonnes paires des 4 lignes mixtes (espaces, écrits par `show_dhgr`) | — |
| `$0800-$1FFF` | WILDADV, WILDHUD, WILDITM, ours | 89 |
| `$2000-$3FFF` | moitié auxiliaire de la page DHGR (`PAGE2` sous `80STORE`) | — |
| `$4000-$BFFF` | TOPO, SIM vierge, STATUS, VOC, TRV, MED, SCR, SIT, OUT, épave | 284 |
| carte langage banque 2 (`$D000-$FFF9`) | INP, PRJ, cabane, TRE, MVI, couguar, WAT, crotale | 5 260 |
| carte langage banque 1 (`$D000-$DFFF`) | libre | 4 096 |

Placement : premier emplacement libre, du plus grand au plus petit, dans
l'ordre des zones ci-dessus (`tools/build_disk.py`). Total stocké :
45 561 octets (29 178 de modules et sprites, 8 191 de SIM, 8 192 de TOPO ;
l'alias 18 ne coûte rien). Libre : 373 octets en RAM auxiliaire principale,
9 356 dans la carte langage auxiliaire, `$FFFA-$FFFF` exclus. Rien ne
s'exécute en RAM auxiliaire : hors stock de modules, elle ne sert qu'à la
moitié auxiliaire de la page DHGR et aux colonnes paires du texte mixte.

Politique /RAM : ProDOS installe toujours /RAM sur un IIe 128 Ko ;
`PD_VIDEO_PRESERVE_RAM` refuserait donc toujours. Le chargeur lit le bloc 2
de /RAM : vide, il le prend avec `PD_VIDEO_DISCARD_RAM` ; s'il contient des
fichiers, il demande « ERASE /RAM (Y/N)? » ; N rend la main à ProDOS sans
rien modifier. À QUIT et RESET, `_prodos_video_release` reformate /RAM vide.

## 3. Page zéro, pile, ROM flottante

- `$00-$1F` et `$50-$FF` sont initialisés par le chargeur avec les valeurs
  qu'Applesoft, DOS 3.3 et HELLO laissaient à la version HGR au lancement
  (CHRGET en `$B1`, pointeurs, `SHIFT.SIGN.EXT` en `$A4`…). Sans BASIC,
  le démarrage à froid d'Applesoft n'a pas lieu ; or `FMULT` lit `$A4` avant
  de l'écrire : sans cette initialisation, le premier calcul de distance
  divergeait (erreur OVERFLOW). `$20-$4F` (Moniteur, ProDOS) restent ceux de
  ProDOS.
- La ROM flottante utilise `$5E-$AC` entre deux vues, comme avant.
- `mem_fetch` n'utilise aucun octet de page zéro ; `mli_call` non plus.
- Pile : profondeur inchangée ; la boucle de copie occupe `$0120-$015B`,
  recopiée avant chaque transfert, sous la zone atteinte par la pile.

## 4. Transferts RAM

`overlay_load` garde son cache (`overlay_current`, `sim_loaded`) et ses
compteurs, puis appelle `mem_fetch` (RESIDENT) au lieu de DOS :

- source en RAM auxiliaire principale : `RAMRD` doit être actif, ce qui
  détournerait aussi la lecture du code ; la boucle est donc recopiée dans la
  pile principale (`$0120`, non commutée par `RAMRD`) et s'y modifie ;
- source en carte langage auxiliaire : `ALTZP` sélectionne aussi la pile et
  la page zéro auxiliaires ; la boucle n'utilise ni l'une ni l'autre et
  s'exécute en RAM principale ;
- longueur exacte de l'image : les octets au-delà gardent leur contenu,
  comme après un BLOAD ;
- `PHP/SEI … PLP`, `80STORE` et `RAMWRT` sauvegardés puis rétablis, `RAMRD`
  et `ALTZP` remis à zéro, ROM réactivée dans la carte langage (un appelant
  en RAM de carte langage retrouve sa banque, en lecture seule) ;
- coût mesuré (`test_transfers.py`) : au plus 17,2 cycles par octet avec
  `overlay_load`, soit environ 35 ms pour 2 Ko et 140 ms pour SIM.

La simulation conserve sa sémantique de rechargement : chaque activation
recopie l'image vierge (8 191 octets), comme le BLOAD vers `$2000`. Le
drapeau `sim_loaded`, `ui_dirty` et le passage en texte pendant le calcul
sont conservés pour garder l'affichage identique ; le redessin qui suit reste
nécessaire puisque le temps a pu avancer.

## 5. Démarrage et fichiers

Volume `NEOWILDERNESS`, 280 blocs (5,25 pouces) : `PRODOS` (17 128 octets),
`NEOWILD.SYSTEM` (2 267) et `NEOWILD.DAT` (53 031 au lot 3 ; 50 620 aux
lots 1–2). 153 blocs occupés, **127 libres** (63,5 Ko). Les mesures de
chargement ci-dessous sont celles des lots 1–2. Le nom `NEOWILDERNESS.SYSTEM` dépasse les 15
caractères de ProDOS : le chargeur s'appelle `NEOWILD.SYSTEM`.

`NEOWILD.DAT` : une table de 128 octets (12 enregistrements de 7 octets),
lue en un seul READ, puis les charges utiles bout à bout, un READ chacune.
Ordre : WILDERNESS (qui contient `video.s`), prise de la mémoire auxiliaire,
blocs auxiliaires (décodés via `$7000`), puis `$0800-$1FFF`, WILDGAME, carte
et RESIDENT (avec son répertoire). Au total 17 appels MLI, dont 14 lectures
(13 du fichier et le bloc 2 de /RAM), 51 132 octets lus.

Mesures POM2 (IIe enhanced, Disk II, ProDOS 2.4.3), `tools/profile_loading.py` :

| Paquetage | Lu | ProDOS | Disque | Décodage | Copies | Préchargement | Premier écran jouable |
|---|---:|---:|---:|---:|---:|---:|---:|
| brut | 71 850 | 8,96 s | 13,32 s | 0 | 0,74 s | 14,06 s | 29,83 s |
| LZ partout | 49 038 | 8,72 s | 9,94 s | 3,22 s | 0,74 s | 13,90 s | 29,42 s |
| **auto** (retenu) | 51 132 | 8,70 s | 10,04 s | 2,64 s | 0,74 s | 13,42 s | **28,93 s** |

La référence HGR atteint l'invite après 45,11 s. « auto » compresse un bloc
seulement si 200 cycles par octet lu (débit mesuré) dépassent le coût du
décodage (46 cycles par octet produit). Des charges utiles alignées sur les
blocs, avec table séparée, ont été mesurées plus lentes (+1,2 à 2,4 s) :
POM2 lit mieux le flux contigu par le tampon d'E/S. La fin du démarrage
(6,80 s entre `start` et l'invite) est le calcul d'initialisation et le
premier rendu.

Budget du volume : les 132 blocs libres couvrent les ~12 Ko de sprites DHGR
prévus (24 blocs bruts) et une marge pour palette et données DHGR. La RAM
auxiliaire, elle, ne garde que 9,7 Ko libres (§6).

## 6. Comptage honnête et risques

- Budget initial du TODO : 78 839 octets. Réel : RAM principale résidente
  hors vidéo et carte 15 319 octets d'images (dont 904 RESIDENT) et 294 de masque des bois, fenêtres
  d'exécution 2 048 + 8 192, RAM auxiliaire 45 565 octets stockés.
  Les temporaires partagés ne sont comptés qu'une fois : `overlay_text`
  (sprites/ciel), `$50-$A3` (rendu/ROM), fenêtre SIM (chargeur/SIM),
  `$2000` (vue/TOPO/tampon du chargeur), `$7000` (carte/décodage du
  chargeur).
- Les copies vierges en RAM auxiliaire doublent les fenêtres : SIM coûte
  16 Ko au total (exécution + image), chaque module 2 Ko + sa taille.
- Appels de modules vers SIM : la référence HGR (tête de `../wilderness`)
  charge SIM avant les sondes de rive de SWIM ; avant cette correction,
  SWIM juste après un rendu exécutait l'image de la vue et s'arrêtait dans
  le Moniteur. La fenêtre SIM n'étant plus jamais écrasée par la vue, ce type
  d'oubli ne plante plus en 128 Ko, mais reste un écart de comportement
  à éviter : tout appel vers SIM doit passer par `overlay_load` 3.
- DHGR (lot 3) : le code DHGR ne peut pas s'exécuter en RAM auxiliaire ;
  il a pris la place du code HGR retiré (§7). Il ne reste que 128 octets
  libres en RAM principale résidente : toute fonction d'interface
  du lot 4 devra vivre dans un module de la fenêtre `$5800` ou libérer de la
  place (TOPO généré en RAM : 8 Ko auxiliaires).

## 7. Lot 3 : page DHGR et inventaire

Page unique `$2000-$3FFF`, principale et auxiliaire. `80STORE` et `HIRES`
restent actifs pendant toute la partie ; `PAGE2` (`$C055`/`$C054`) choisit la
banque vue par le CPU, sans changer la page affichée. Le code, la pile et les
tables restent en RAM principale ; chaque passe auxiliaire s'exécute
interruptions masquées (`render`, `scroll`, `clear_rows`, `dbl_put`), et
toutes les routines rendent la main banque principale sélectionnée.

| Rangées physiques | Contenu (deux banques) |
|---|---|
| 0–15 | bandeau : boussole (octets HGR 13–26), panneaux de survie (0–12, 27–39), en pixels HGR doublés |
| 16–159 | vue, lignes logiques 16–159 |
| 160–175 | cache des lignes logiques 0–15 (invisible en mode mixte), défilé avec la vue |
| 176–191 | inutilisées, sous les 4 lignes de texte |

Retiré (HGR seul) : `span_rows` (1 153), `span_lo/hi` (290), `clear_rows`
HGR (26), `column_masks`, `span`, `fill` (223), `col_be`/`col_me` (280),
`hgr_lo`/`hgr_hi` (384, remplacés par le calcul `hgr_row`, 44 octets), les
écritures de pointeur HGR du bandeau. Environ 2 360 octets.

Ajouté (`src/dhgr.s` et adaptations), octets mesurés dans `build/wild.lbl` :

| Élément | Zone | Octets |
|---|---|---:|
| `drows` : 160 lignes logiques déroulées `LDA/AND dm/ORA dv0|dv1/STA` + 1 | WILDLO | 1 601 |
| `clear_rows` (deux banques, bandes de 8 lignes, `STA abs,X` modifiés) | WILDLO | 90 |
| `drow_lo`/`drow_hi` (entrées des lignes) | CODE | 322 |
| `dspan` (1 ou 2 passes, trame par deux registres OR) | CODE | 119 |
| `column_setup`, `div7`, tables de phase (56), `dc_pat` (64), `sky_zone_end` | CODE | 238 |
| `scroll` + `band_copy` (deux banques, bandes de 8 lignes) | CODE | 206 |
| texte 40 colonnes (`t_cout`, `t_vtab`, défilement, `t_home`, `t_clreop`, `t_clreol`) | CODE | 175 |
| humeurs (10 × 21 = 210 : cinq zones de ciel + 16 entrées), ombrages (80), couleurs des sprites (20), index jaune (12) | GCODE | 322 |
| `dhgr_frame`, `select_mood` (seuils en table) | GCODE | 233 |
| `sky_position` (altitudes S8, entiers seulement) | GCODE | 87 |
| `hgr_row`/`hgr_row2`, `band_base` | GCODE | 93 |
| `dbl_put` + table de demi-octets, modes vidéo `show_dhgr`/`show_text`/`show_hgr` | GCODE | 139 |
| `forest_paint` réécrit en trois bandes | GCODE | 121 |
| palette courante, variables de bandes | BSS | 38 |
| scratch de passe (`dm`…`dzone`, `forest_masked`, `forest_pair`) | ZEROPAGE | 18 (21 libérés) |

Les primitives du banc (`src/dhgr_cols.s`, tampons de colonnes et
`dc_flush`) ne sont pas liées au jeu : elles demandaient 2,2 Ko de code et de
tables, 3,6 Ko de lignes déroulées et 1,3 Ko de tampons, soit 7,1 Ko, alors que
le code HGR retiré n'en libère que 2,4 Ko. La passe en lecture-modification-
écriture avec deux registres OR (lignes paires/impaires) absorbe la trame
sans coût et ne demande aucun tampon ; `docs/DHGR.md` §10 en donne les
mesures.

Libre après le lot 3, RAM principale : 7 octets (`$0800-$0FFF`), 35
(`$1000-$1FFF`), 13 (`$4000-$57FF`), 36 (`$6000-$6FFF`), 37 (RESIDENT), soit
128 octets ; RAM auxiliaire inchangée (9,7 Ko). Le volume garde 127 blocs
libres (`NEOWILD.DAT` 53 031 octets, +2 411).

**Double tampon (mesure, pas d'implémentation).** Une seconde page DHGR
demande 16 Ko : 8 Ko principaux à `$4000-$5FFF` (occupés par WILDGAME et la
fenêtre de modules, 14 Ko de code résident à déplacer) et 8 Ko auxiliaires
(9,7 Ko libres, mais fragmentés entre `$0800`, `$BEE4` et les cartes langage,
alors qu'une page doit être à `$4000-$5FFF`). Avec 128 octets libres en RAM
principale, le double tampon est impossible sans retirer TOPO de la RAM
auxiliaire (lot 4) et réécrire la carte mémoire. Côté présentation, il
n'apporterait rien de mesurable : les vues complètes sont déjà préparées
derrière le rideau texte (aucune trame partielle n'est visible), et les
rotations révèlent leurs colonnes progressivement depuis la vue conservée,
ce qui est voulu (`test_view.py`, `test_pan.py`).
