# Neowilderness — inventaire et plan mémoire 128 Ko

Ce document décrit la version du lot 4, complétée au lot 7 par le tronc
commun, les paquets de région, le menu de démarrage, la faune et les
couleurs par région, les étoiles et le hall of fame (§ 9) : démarrage ProDOS 8 depuis
`dist/NEOWILDERNESS.po`, tous les modules préchargés en RAM auxiliaire (lots
1–2), paysage DHGR sur une seule page (`$2000-$3FFF` principale et
auxiliaire, lot 3), interface DHGR, texte 80 colonnes et TOPO calculée en RAM
(lot 4, § 8 ; les tableaux des §§ 1–2 sont à jour du lot 4, les §§ 4–7
gardent l'historique). Les chiffres viennent de `build/wild.map`, `build/wild.lbl`,
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
| `LOWPAGE` (`wildpg.bin`, lot 4) | `$0200-$03B0` | 433 | C/E | Modes vidéo, texte 80/40 colonnes du jeu (`t_update`, `t_cout`, défilement, effacements, `topo_pad`) |
| page DHGR, moitié principale | `$2000-$3FFF` | 8 192 | vidéo | Vue logique 16–159, bandeau et panneaux 0–15, cache 160–175 (lignes logiques 0–15) ; la feuille TOPO y est dessinée (rangées 0–159) |
| `GCODE`/`GDATA` (`wildgame.bin`) | `$4000-$57C8` | 6 089 | C/E/K | Logique résidente, état de la partie (`px`…`it_*`, horloge, santé, météo, hasard), chargeur de modules ; humeurs DHGR (302 octets de tables), choix d'humeur, altitudes `sun_alt8`…`sky_mood`, demi-pixels du bandeau, modes vidéo |
| `BSS` | `$57C9-$57F2` | 42 | E/T | `video.s` (unité /RAM) et `mli.s` ; palette courante de la trame (`cur_pal`, couleurs des sprites), variables des bandes de 8 lignes ; mis à zéro par le chargeur |
| `REGIONTEXT` (lot 7) | `$5780-$57FF` | 128 | K | Textes de la région choisie, écrits par son paquet : nom 16, phrase de faune 40, quatre noms d'espèces de 12, région, nombre d'espèces, nom de l'introduction 22 (§ 9) |
| fenêtre `$5800` | `$5800-$5FFF` | ≤ 2 048 | C/K/T | Un module à la fois (tableau 2) ; son image est restaurée à chaque chargement |
| `CODE`/`RODATA` (`wild.bin`) | `$6000-$6FDB` | 4 060 | C/K | Démarrage, moteur de vue, passes DHGR (`dspan`, `column_setup`, tables d'entrée des lignes), texte 40 colonnes propre, sprites, saisie, impressions, transitions, `video.s`, `mli.s` |
| `WILDMAP` | `$7000-$94FF` | 9 472 | K | En-tête 64 octets et grille 112 × 84, du paquet de région (lot 7) ; le chargeur y écrit le niveau (+22) et le genre de voyage (+33) |
| `SCRATCH` | `$9500-$95FF` | 256 | T | `overlay_text` (160) : couleurs de colonne des sprites **et** flottants temporaires du ciel ; puis `scene_*`, thermique, saisie |
| `ENVIRON`+`THERMAL` (`wildsim.bin`) | `$9600-$B5FE` | 8 191 | C/K/T | Simulation ; données de l'image rechargées à chaque activation (même sémantique que le BLOAD HGR) |
| `RESCODE` (`wildres.bin`) | `$B600-$B987` | 904 | C/K | Répertoire des modules (161), `mem_fetch`, boucle de pile, `mli_call`, sortie/RESET (`geo_load` retiré au § 9.10) |
| `RESBSS` | `$B988-$B9DA` | 83 | E | Compteurs, vecteur RESET et bitmap ProDOS sauvegardés, chemin de NEOWILD.GEO (gabarit de `NEOWILD.END`/`.HOF`), compteurs de géographie fine (§ 9.10), `journey_kind` (genre du voyage pour `NEOWILD.END`, HOF.md § 10) |
| `IOBUF` | `$BA00-$BDFF` | 1 024 | T | Tampon d'E/S ProDOS (chargeur, `NEOWILD.END`/`.HOF`) |
| `SAVE` | `$BE00-$BEFF` | 256 | E | Page zéro de ProDOS à l'entrée, restaurée à la sortie |
| `SYSSTUB`+`LOADER` (`NEOWILD.SYSTEM`) | `$2000` puis `$9600-$A56D` | 3 912 | C/T | Chargeur transitoire et menu de démarrage (lot 7), exécutés dans la fenêtre SIM avant la première activation ; table d'enregistrements en `$B500` |

Modules de la fenêtre `$5800` (identifiants de `overlay_load`, inchangés) :

| ID | Image | Octets | ID | Image | Octets |
|---:|---|---:|---:|---|---:|
| 0 | TOPOGEN (`wildtpg.bin`, lot 4) → `$9600` | 2 681 | 12 | `wildtrv.bin` | 2 045 |
| 1 | `wildvoc.bin` | 2 047 | 13 | `wildinp.bin` | 1 442 |
| 2 | `wildscr.bin` | 2 040 | 14 | `wilditm.bin` | 1 647 |
| 3 | `wildsim.bin` → `$9600` | 8 191 | 15 | `wildhud.bin` | 1 739 |
| 4 | `wildwat.bin` | 495 | 16 | `wildsta.bin` | 2 048 |
| 5, 9 | épave, cabane (tronc commun) | 1 900, 1 133 | 17/18 | `wildmed.bin` (médical + dangers) | 2 045 |
| 6–8, 23 | animaux 1 à 4 du paquet de région (Sierra : ours, couguar, crotale) | 464 à 1 227 chacun | 24 / 25 | tête du catalogue des étoiles `wildskycat.bin` (le hall of fame est lu sur disque) / module des étoiles `wildsky.bin` (fenêtre SIM) | 462 / 2 367 |
| 10 | `wildsit.bin` | 1 915 | 19 | `wildmvi.bin` | 878 |
| 11 | `wildprj.bin` | 1 134 | 20–22 | `wildtre`, `wildadv`, `wildout` | 916, 1 971, 1 982 |

`wildgeo.bin` n'est pas un module : jusqu'au lot 7, c'était le gabarit des
24 banques de géographie fine (IDs 32–55, 23–46 avant), lues à la demande
dans `NEOWILD.GEO` ; depuis l'intégration de la branche parallèle (§ 9.10),
c'est le code résident de la géographie fine (`src/geoaux.s`, 843 octets),
chargé avec l'atlas en carte langage auxiliaire sur les seules cartes
natives.

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
| SITES | GAME, LOW, MAIN, FOREST, RESIDENT, TOPOGEN (fenêtre SIM) |
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
| `$0200-$03CF` | `LOWPAGE` : modes vidéo et texte (lot 4) | 31 |
| `$03D0-$03FF` | vecteurs ProDOS ; RESET → `reset_exit` pendant le jeu | — |
| `$0400-$07FF` | texte page 1 (intro, menus 40 colonnes ; colonnes impaires du texte 80 colonnes) | — |
| `$0800-$0FFF` | bois, aide forêt, WILDTXT | 68 |
| `$1000-$1FFF` | WILDLO (ruban de boussole compris) + cache de projection | 247 |
| `$2000-$3FFF` | page DHGR, moitié principale | — |
| `$4000-$57FF` | WILDGAME + BSS | 143 |
| `$5800-$5FFF` | fenêtre de modules | 0 à 1 553 selon le module |
| `$6000-$6FFF` | WILDERNESS | 2 |
| `$7000-$94FF` | carte | 0 |
| `$9500-$95FF` | scratch | 0 |
| `$9600-$B5FF` | fenêtre SIM (chargeur au démarrage ; TOPOGEN et ses tables `$9600-$AEBB` pendant TOPO) | 1 |
| `$B600-$B9FF` | RESIDENT | 37 |
| `$BA00-$BDFF` | tampon d'E/S ProDOS | (réservé) |
| `$BE00-$BEFF` | page zéro de ProDOS sauvegardée | — |
| `$BF00-$BFFF` | page globale ProDOS | — |
| carte langage | ProDOS 8 (banque 1, `$E000-$FFFF`, code QUIT `$D100-$D3FF` de la banque 2) ; le jeu lit la ROM (`$C082`). Lot 7 : banque 2 `$D400-$DE17` dans le stock de modules, `$DE18-$DFFE` liste et code de tracé des étoiles (§ 9.7) | 59 + 1 |

Le passage à ProDOS libère `$9600-$BEFF` (10 496 octets) ; la simulation y
quitte `$2000-$3FFF`. Le retrait de DOS (`dos.asm`, `exit.asm`, noms de
fichiers, sauvegarde des lignes de texte, décodeur en place) libère en plus
environ 930 octets dans WILDGAME, 290 dans WILDLO et 170 dans WILDERNESS
(mesurés contre la référence HGR synchronisée).

Bitmap ProDOS pendant le jeu : pages `$02-$03`, `$08-$57`, `$60-$B9` et `$BE` marquées
en plus de celles de ProDOS ; la fenêtre `$58-$5F` et le tampon `$BA-$BD`
restent libres (lectures de `NEOWILD.END` et `NEOWILD.HOF` en fin de
partie ; plus aucune lecture de géographie depuis le § 9.10). Le bitmap d'origine
est rétabli à la sortie.

### RAM auxiliaire

| Zone | Usage | Libre |
|---|---|---:|
| `$0000-$01FF` | page zéro et pile auxiliaires : jamais utilisées | — |
| `$0200-$03FF` | code du pilote /RAM de ProDOS (appelé par FORMAT à la sortie) : intouchable | — |
| `$0400-$07FF` | texte : colonnes paires du texte 80 colonnes (lignes mixtes, rideau, MAP) | — |
| `$0800-$1FFF` | INP, PRJ, cabane, TRE, MVI, couguar | 102 |
| `$2000-$3FFF` | moitié auxiliaire de la page DHGR (`PAGE2` sous `80STORE`) | — |
| `$4000-$BFFF` | SIM vierge, TOPOGEN, STATUS, VOC, TRV, MED, SCR, ADV, OUT, HUD, épave, SIT, ITM | 325 |
| carte langage banque 2, `$D000-$DBFF` | ours, WAT, crotale | 1 311 |
| banque 2 `$DC00-$DE2F`, banque 1 `$D000-$DFFF`, commun `$E000-$FFCF` | instantané de la vue sous TOPO (§ 8) | — |
| banque 2 `$DE30-$DFFF`, commun `$FFD0-$FFF9` | libres, hors placement | 506 |

Placement : premier emplacement libre, du plus grand au plus petit, dans
l'ordre des zones ci-dessus (`tools/build_disk.py`, `REGIONS`). Total stocké
au lot 4 : 40 246 octets (29 374 de modules et sprites, 8 191 de SIM, 2 681
de TOPOGEN ; l'alias 18 ne coûte rien ; l'image TOPO de 8 192 octets a
disparu). Libre dans le stock : 1 738 octets ; 12 800 octets de carte
langage sont réservés à l'instantané de la vue (§ 8). Rien ne s'exécute en
RAM auxiliaire : hors stock de modules, elle sert à la moitié auxiliaire de
la page DHGR, aux colonnes paires du texte 80 colonnes et à l'instantané.

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

## 8. Lot 4 : interface DHGR, texte 80 colonnes, TOPO en RAM

Point de départ : 128 octets libres en RAM principale, 9,7 Ko libres en RAM
auxiliaire, l'image TOPO (8 Ko) dans le stock auxiliaire. Contraintes
gardées : aucune lecture disque pendant la partie, pas de code ni de donnée
dans la page DHGR, état de simulation identique à la référence HGR.

### 8.1 Options pesées

| Option | Coût / gain mesuré | Décision |
|---|---|---|
| Page `$0200-$03CF` (464 octets) : tampon du Moniteur (GETLN) et zone libre, jamais utilisés par le jeu ni par ProDOS pendant la partie (aucun appel MLI hors `geo_load`, qui lit dans `$5800`) | +464 octets résidents, un enregistrement de plus dans `NEOWILD.DAT`, pages marquées dans le bitmap | **Retenu** : `LOWPAGE` (modes vidéo, texte 80/40 colonnes) |
| Code d'interface dans un module de la fenêtre `$5800` | 35 ms par activation ; la fenêtre contient l'asset de la scène : un ruban modulaire coûterait deux copies par rotation | Ruban **résident** ; panneaux dans WILDHUD (dessinés seulement quand `ui_dirty`) |
| Fenêtre SIM pour un écran qui ne tourne jamais avec SIM actif | TOPO : 8 Ko d'exécution, copie de 2 681 octets en 47 ms, SIM rechargée ensuite comme avant | **Retenu** : TOPOGEN (module 0) |
| Réduire les tables | ruban : bande de 140 octets au lieu de 336 + 16 + 12 ; police HGR du résumé remplacée par la police DHGR (413 octets dans le module) | Retenu |
| Libérer le doublage HGR | `dbl_put` + table : 69 octets | Retenu (remplacé par `dhgr_pack`, partagé ruban/panneaux) |
| Stock auxiliaire | image TOPO supprimée (−8 192), TOPOGEN (+2 681) ; reste 1 738 octets + 12 800 réservés | Instantané de la vue (8.4) |
| Instantané compressé (prédicteur « rangée −2 » ou « octet −2 » + suites de zéros) | mesuré sur cinq vues : 2 741 à 7 018 octets (16 Ko de page → 14 080 octets de rangées utiles) ; pire cas inconnu, encodeur ≈ 30 cycles/octet | Écarté : taille variable et repli obligatoire ; la copie brute tient dans la carte langage libérée |
| Profils de colonnes de la vue (option D de `docs/TOPO_DHGR.md`) | 6,6 à 11,4 Ko, repeinture 0,6 à 1 s, sprites et bois à rejouer | Écarté |

### 8.2 Inventaire des ajouts et retraits (octets, `build/wild.lbl`)

| Élément | Zone | Avant | Lot 4 |
|---|---|---:|---:|
| Ruban HGR (`hud_draw`, bande 8 × 40, pointeurs, bordure, index) | LOWCODE/TEXT/GCODE | ≈ 636 | — |
| Ruban DHGR (`hud_draw`, 4 tables de rangées, bande de 140) | LOWCODE | — | 343 |
| `dbl_put` + demi-octets | GCODE | 69 | — |
| `dhgr_pack` (+ 3 tables de 7–8 octets, groupe uni en accès direct) | CODE | — | 204 |
| Texte 40 colonnes, modes vidéo (`t_*`, `show_*`) | CODE/GCODE | ≈ 245 | — |
| Texte 80/40 colonnes, modes, `topo_pad` différentiel | LOWPAGE | — | 433 |
| Curtain, `topo_output` (inline 40 colonnes), `wait_key` | CODE | ≈ 120 | ≈ 140 |
| `load_totals_quiet`, `sim_quiet` (INVENTORY sans redessin) | GCODE/GDATA | — | 25 |
| Panneaux : rendu de champs DHGR + police 7 rangées (WILDHUD) | module `$5800` | 1 739 | 1 939 |
| MAP en 80 colonnes (`topo_put2`) ; TOPO réduit à l'appel de TOPOGEN | module SITES | 1 915 | 1 888 |
| TOPOGEN : feuille, tables, instantané (code 2 681 + tampons 3 516) | fenêtre SIM | — | 6 197 |

### 8.3 Libre après le lot 4

RAM principale résidente : 31 (`$0200-$03CF`), 68 (`$0800-$0FFF`), 247
(`$1000-$1FFF`), 143 (`$4000-$57FF`), 2 (`$6000-$6FFF`), 37 (RESIDENT), soit
**528 octets** (128 au lot 3). Modules : WILDHUD 109, SITES 160, WILDSCR 5.
Fenêtre SIM pendant TOPO : `$AEBC-$B5FF` libres (1 860 octets). RAM
auxiliaire : 1 738 octets dans le stock, 506 hors placement ; 12 800 réservés.
Volume : `NEOWILD.DAT` 53 847 octets (13 enregistrements), 155 blocs
occupés, **125 libres**.

### 8.4 Instantané de la vue sous TOPO

TOPO dessine sa feuille sur les rangées 0–159 des deux banques ; les rangées
160–175 (cache) ne sont pas touchées. `tp_save` (TOPOGEN) copie ces 160
rangées (80 octets chacune, 12 800 octets) dans la carte langage
auxiliaire avant le premier pixel : rangées 0–152 de `$D000` à `$FFCF` avec
la banque 1 sélectionnée (banque 1 puis zone commune), rangées 153–159 dans
`$DC00-$DE2F` de la banque 2. `ALTZP` choisit la carte auxiliaire, et aussi
la page zéro et la pile auxiliaires (jamais utilisées ailleurs) : les
pointeurs sont posés après la bascule, les IRQ sont masquées, la ROM est
rétablie (`$C082`) avant `ALTZP` bas. Au retour, `topo_close` recopie
l'instantané (0,24 s mesurées, au lieu d'un rendu complet de 1,9 à 5,8 s),
puis `show_dhgr` : bandeau, vue et cache identiques octet pour octet, ni
lancer de rayons, ni avance du temps (`test_graphical_topo.py`,
`test_transitions.py`).

**Risque pour le lot 5.** La géographie fine native compressée (≈ 11 Ko
mesurés sur une carte) ne tient plus dans la RAM auxiliaire avec
l'instantané. Options documentées : instantané compressé (2,7 à 7 Ko mesurés,
repli sur le redessin si la vue ne tient pas), ou retour au redessin
(`topo_close` rend C = 1 sans instantané : le chemin de redessin est déjà
câblé dans `module_graphical_topo`).

**Résolu à l'intégration de la branche parallèle (§ 9.10).** L'atlas
résident (`src/geoaux.s`, ≈ 7,2 Ko pour la Sierra) partage cette zone avec
l'instantané selon la carte : carte héritée (les six régions livrées) →
instantané ; carte native (comparaison) → atlas, et TOPO redessine la vue.

**Compressé depuis la direction 3 (§ 12.2)** : flux prédit par la rangée
−2 dans la banque 1 et `$E000-$F0FF`, 2 à 7 Ko mesurés ; la banque 2 et
`$F100-$FFF9` rejoignent le stock.

## 9. Lot 7 : tronc commun, paquets de région, menu, étoiles, hall of fame

Étapes 2 à 6 de [SCENARIOS.md](SCENARIOS.md) : le volume porte un tronc
commun et six paquets de région au même format d'enregistrements ; le
chargeur lit le tronc et le hall of fame, affiche le menu, puis lit **un
seul** paquet. Chiffres du 13 octobre 2026, fin du lot 7 (étapes 4 à 6
intégrées), mesurés sur `build/layout.json` (`make inspect`),
`build/wild.map`, `build/*.bin` et `tools/profile_loading.py --choice N`.

### 9.1 Fichiers et blocs

Paquetage `lz` (défaut depuis l'étape 5, § 9.5) :

| Fichier | Contenu | Brut → stocké | Enreg. | Blocs |
|---|---|---:|---:|---:|
| `NEOWILD.SYSTEM` | chargeur + menu (`src/boot.s`, textes `build/menu.inc`), lecture du hall of fame et écran H (`src/hof_menu.s`) | 4 943 | — | 11 |
| `NEOWILD.DAT` | tronc : WILDERNESS, claim, stock auxiliaire commun (épave, cabane, module des étoiles compris), carte langage principale (§ 9.7), `$0200`, `$0926-$1FFF`, WILDGAME, RESIDENT | 58 312 → 45 559 | 13 | 91 |
| `NEOWILD.R1` British Columbia | sprites 2 838 | 13 385 → 7 464 | 12 | 16 |
| `NEOWILD.R2` Sierra Nevada | sprites 1 805 | 12 352 → 6 919 | 12 | 15 |
| `NEOWILD.R3` Burma | sprites 3 049 | 13 596 → 7 368 | 12 | 16 |
| `NEOWILD.R4` New Guinea | sprites 2 277 | 12 824 → 7 414 | 12 | 16 |
| `NEOWILD.R5` Bolivia | sprites 3 025 | 13 572 → 7 819 | 12 | 17 |
| `NEOWILD.R6` Chile | sprites 1 576 | 12 124 → 6 497 | 12 | 14 |
| `NEOWILD.END` | module de fin de partie `wildhof.bin` (`src/hof.s`), lu à `$9600` | 3 044 | — | 7 |
| `NEOWILD.HOF` | hall of fame (`tools/genhof.py`), réécrit en place | 512 | — | 1 |

Blocs ProDOS, bloc d'index compris. Volume : **246 blocs occupés sur 280,
34 libres**. Historique : 125 libres au lot 4, 37 après les étapes 2-3, 34
après l'étape 4 (paquetage `auto`), 11 avec les étapes 5-6 en `auto`, 34 en
`lz`. Chaque paquet reste sous la cible de 20 blocs (`test_pack_boot.py`).
Conséquence pour le lot 5 : six atlas de géographie fine (≈ 22 blocs chacun,
≈ 132 au total) ne tiennent pas sur la disquette unique ; la géographie
fine devra être calculée en RAM ou réservée à la Sierra (un atlas tient dans
les 34 blocs). Réalisé pour les cartes natives au § 9.10 : l'atlas `coarse`
(6,4 Ko pour la Sierra, 13 blocs de plus dans `NEOWILD.R2`).

### 9.2 Contenu d'un paquet (ordre des enregistrements)

| Enregistrement | Destination | Octets |
|---|---|---:|
| sprites des espèces 1 à 4 (modules 6, 7, 8, 23) | zone de paquet auxiliaire `$B417-$BFFF`, puis restes du tronc | 1 576 à 3 049 |
| taux et filtres des quatre espèces (étape 4) | image auxiliaire de TRAVEL, `fauna_travel` | 52 |
| les mêmes 52 octets | image auxiliaire de SITES, `fauna_table` | 52 |
| seuils de réaction, noms du parseur, drapeaux | image auxiliaire d'OUTDOOR, `fauna_reactions` | 40 |
| largeurs et bases des sprites | image auxiliaire de PROJECT, `proj_sprites` | 12 |
| espèce de l'indice IGNORE/MOVE | image auxiliaire de SUMMARY, `summary_quiet` | 1 |
| masque des bois | `$0800-$0925` | 294 |
| humeurs, ombrages, couleurs des sprites de la région (`build/dhgr/dhgr_tables_rN.bin`) | `dhgr_moods`…`dhgr_tables_end` (WILDGAME) | 314 |
| textes de région | `REGIONTEXT` `$5780-$57FF` | 128 |
| répertoire des modules entier (26 entrées) | `module_dir` (RESIDENT) | 182 |
| carte (en-tête 64 + grille), **en dernier** : les enregistrements auxiliaires LZ se décodent par `$7000` | `$7000-$94FF` (deux enregistrements de 8 Ko au plus) | 9 472 |

Épave et cabane ne sont **pas** dans les paquets : la Journey n'a qu'un
sprite de chacune (la « cabane » est la hutte `HUT.CIM` du DOS), identique
dans les six régions ; les mettre dans chaque paquet coûterait 6 × 3 033
octets bruts (≈ 36 blocs) pour aucun effet. Le poste de rangers n'a pas de
sprite dans le port (`outpost.bin` existe, non affiché) : il n'est pas chargé.
Chile n'a que deux espèces : son entrée 8 pointe un sprite vide d'un octet
(largeur 0, rien n'est dessiné) ; depuis l'étape 4 sa troisième fiche a un
taux nul et n'est jamais acceptée, le sprite vide reste une garde d'un
octet. L'entrée 23 est vide hors Burma et Bolivia. Les cinq correctifs de
modules sont dérivés des fiches `$6000-$607F` par
`build_disk.fauna_patches` ; le paquet Sierra réécrit les octets que le
tronc contient déjà (vérifié à la construction).

### 9.3 RAM auxiliaire par région

Placement (`tools/build_disk.py`) : la zone de paquet a la taille du plus
gros paquet (Burma, 3 049 octets) au sommet de `$4000-$BFFF` ; le tronc
remplit le reste (premier ajustement, du plus grand au plus petit, puis
recherche exhaustive si la place est morcelée) dans l'ordre : auxiliaire
`$4000-$BFFF`, `$0800-$1FFF`, carte langage auxiliaire banque 2
`$D000-$DBFF` et `$DE30-$DFFF`, puis **banque 2 de la carte langage
principale `$D400-$DE17`** (§ 9.7) ; chaque paquet place ses sprites dans
la zone, puis dans les restes.

| Région | Sprites | Libre, ciel peuplé (dont 59 en carte principale) | Plus grand morceau | Fin du lot 7, 79 étoiles (dont 291) | Plus grand morceau | Après l'étape 4 | Étapes 2-3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 British Columbia | 2 838 | 477 | 211 | 1 524 | 464 | 756 | 887 |
| 2 Sierra Nevada | 1 805 | 1 510 | 1 244 | 2 557 | 1 244 | 1 789 | 1 920 |
| 3 Burma (pire cas) | 3 049 | **266** | 135 | 1 313 | 464 | 545 | 676 |
| 4 New Guinea | 2 277 | 1 038 | 772 | 2 085 | 772 | 1 317 | 1 448 |
| 5 Bolivia | 3 025 | 290 | 135 | 1 337 | 464 | 569 | 700 |
| 6 Chile | 1 576 | 1 738 | 1 472 | 2 785 | 1 472 | 2 017 | 2 148 |

L'étape 4 coûte 131 octets dans chaque région (−69 pour les tables de
faune, +200 pour `module_fauna_cause`, § 9.6). Les étapes 5 et 6 en rendent
768 : +2 816 de carte langage principale, −1 984 du module des étoiles,
−64 d'INPUT (`hof_load.inc`). Le module des étoiles (ID 25) est un module
ordinaire du tronc : premier ajustement à `$9A41` en RAM auxiliaire ; ITM et
MVI passent dans la carte principale (`$D400`, `$DA6F`). Libres avec la
Sierra : auxiliaire `$BB24-$BFFF` 1 244, `$B342-$B416` 213, `$1FB8-$1FFF`
72 ; banque 2 auxiliaire `$DAEF-$DBFF` 273, `$DE30-$DFFF` 464 ; carte
principale `$DDDD-$DEFF` 291.

**Ciel peuplé** (§ 9.7, [STARS.md](STARS.md) § 7) : chaque région perd
1 047 octets (catalogue et module : 462 + 2 337 au lieu de 1 984 ; carte
principale : le stock s'arrête à `$DE17`, −232). La tête du catalogue (ID
24, 462 octets) comble le trou de 464 octets de la banque 2 auxiliaire
(`$DE30`), que le plus petit module (495) ne pouvait pas prendre ; le module
`wildsky.bin` est placé à `$6A78`. Libres avec la Sierra : auxiliaire
`$BB24-$BFFF` 1 244, `$B390-$B416` 135, `$1FE1-$1FFF` 31 ; banque 2
auxiliaire `$DBD9-$DBFF` 39, `$DFFE-$DFFF` 2 ; carte principale
`$DDDD-$DE17` 59.

### 9.4 RAM principale

| Zone | Libre, ciel peuplé | Fin du lot 7 | Après l'étape 4 |
|---|---:|---:|---:|
| LOWPAGE `$0200-$03CF` | 23 (`$03B9-$03CF`) | 23 | 23 |
| FORESTCODE `$0926-$09FF` | 4 (`$09FC-$09FF`) | 4 | 4 |
| TEXT `$0A00-$0FFF` | 11 (`$0FF5-$0FFF`) | 11 | 11 |
| WILDLO `$1000-$1FFF` | **135** (`$1F79-$1FFF`) | 40 (`$1FD8-$1FFF`) | 212 |
| WILDGAME `$4000-$577F` | 4 (`$577C-$577F`) | 4 | 3 |
| WILDERNESS `$6000-$6FFF` | 2 (`$6FFE-$6FFF`) | 2 | 2 |
| RESIDENT `$B600-$B9FF` | 2 (`$B9FE-$B9FF`) | 2 | 12 |
| **Total** | **181** | **86** | **267** |

Ajouts du lot 7 : répertoire 23 → 26 entrées (+21, RESIDENT),
`REGIONTEXT` (+128, fin de WILDGAME), `prodos_restore` séparé de
`prodos_exit` (+4), étape 4 (§ 9.6), étoiles (§ 9.7 : liste 110, `stars_stale` 1
et raccords 61 dans WILDLO, source « carte principale » de `mem_fetch` +10
dans RESIDENT). Le ciel peuplé rend 95 octets à WILDLO : la liste (106)
passe dans la carte principale, `stars_view_dark` grandit de 11. Le hall of fame ne prend rien de résident : son code vit
dans le chargeur, dans INPUT et dans `NEOWILD.END` (§ 9.8).

Emplacement des textes de région : `$0300-$03CF`, candidat du plan, n'est
plus libre depuis le lot 4 (LOWPAGE occupe `$0200-$03B8`) ; la fin de
WILDGAME (`$5780-$57FF`) les reçoit. Le pilote /RAM et ProDOS n'y touchent
pas (pages marquées dans le bitmap).

### 9.5 Menu, latences, retour au menu

Séquence : introduction et `LOADING...` pendant le tronc (comme au lot 4),
lecture de `NEOWILD.HOF`, menu 40 colonnes (`menu_key`, `BEST` lus dans le
fichier), niveau, puis l'introduction revient avec « SIERRA NEVADA, LEVEL
4 » et `LOADING...` pendant le paquet, l'initialisation et le premier rendu
(rien ne change à l'écran tant que la vue n'est pas prête :
`test_transitions.py`).

| Mesure (`tools/profile_loading.py`, Sierra / Burma / Chile) | `lz` | `auto` (Sierra) | étapes 2-3 |
|---|---:|---:|---:|
| amorçage ProDOS jusqu'au chargeur | 9,49 | 9,87 | 9,32 |
| tronc (disque 10,33, LZ 2,78, copies 0,70) → menu | 13,81 (menu à 23,30) | 13,21 (23,08) | 12,07 (21,39) |
| lecture du paquet | 2,52 / 2,95 / 2,68 | 3,26 | 3,01 / 3,14 / 3,02 |
| `start` → première vue jouable | 7,15 / 6,44 / 6,39 | 7,15 | 7,13 / 6,42 / 6,37 |
| **choix → première vue** | **9,76 / 9,48 / 9,17** | 10,50 | 10,24 / 9,65 / 9,49 |
| premier écran jouable sans attente au menu | 33,06 / 32,77 / 32,46 | 33,59 | 31,63 |

Le paquetage `auto` ne compressait un enregistrement que si le modèle
200 cycles par octet lu contre 46 par octet décodé le donnait gagnant : avec
le module des étoiles, il laissait trois blocs de 8 Ko de modules en brut
(taux 84 %) et le volume tombait à 11 blocs libres. Mesuré, `lz` partout
coûte 0,21 s de plus avant le menu mais rend 0,74 s entre le choix et la
première vue (paquets plus courts) et **23 blocs** : il devient le défaut
(`BOOT_PACKING ?= lz` ; `auto` reste disponible). 36 appels MLI au total
avant `start` (27 aux étapes 2-3 : `NEOWILD.HOF`, deux enregistrements de
tronc et quatre de paquet de plus), aucun après.

Fin de partie (mort, arrivée, QUIT puis Y) : `quit` charge INPUT et saute à
`module_end` (§ 9.8) : `NEOWILD.END` lu à `$9600`, score, hall of fame, une
touche, puis INPUT de nouveau et `module_restart` : restauration comme
`prodos_exit` (texte, /RAM reformaté, bitmap, vecteur RESET, page zéro),
OPEN/READ/CLOSE de `NEOWILD.SYSTEM` (chemin de `NEOWILD.GEO`, suffixe
remplacé) vers `$2000` et saut au talon : chargeur neuf, compteurs remis à
zéro, tronc et hall of fame relus, menu. Aucun état de partie ne survit.
`Q` au menu et Ctrl-RESET rendent la main à ProDOS.

### 9.6 Étape 4 : faune, couleurs et textes par région

Octets ajoutés (+) ou rendus (−) par module, tailles de `build/*.bin`
mesurées avant et après l'étape :

| Module (fenêtre) | Avant → après | Détail |
|---|---:|---|
| SITES (`wildsit.bin`) | 2 016 → 1 902 (**−114**) | `fauna_records` (128) et les tables Sierra (42) retirés ; `fauna_table` 52 (taux 4 + filtres 4 × 12) et `fauna_offsets` 4 au lieu de 3. Libre : 146 |
| TRAVEL (`wildtrv.bin`) | 2 045 → 2 045 (0) | `resource_animal_rates` déplacé devant `resource_ranges` : bloc contigu `fauna_travel` de 52 octets. Libre : 3 |
| OUTDOOR (`wildout.bin`) | 1 982 → 2 006 (**+24**) | tables 3 → 4 espèces et `out_tree_injury`, `out_kind` (40 octets réécrits), `out_severity` exposant 3, `outdoor_hurt` pacotilles, drapeaux vol/venin/gravité au lieu des comparaisons au crotale, synonyme PUMA générique, `fauna_named` posé, nom de l'espèce `@`+champ au lieu de « ANIMAL » dans neuf messages. Libre : 42 |
| PROJECT (`wildprj.bin`) | 1 134 → 1 354 (**+220**) | `proj_index`, module 23 de l'espèce 4, `proj_sprites` 6 + 6 octets (+20) ; `module_fauna_cause` (+200 : cause nommée de l'arrêt, ci-dessous). Libre : 694 |
| SUMMARY (`wildhud.bin`) | 1 939 → 1 941 (+2) | `summary_quiet`. Libre : 107 |
| SCREENS (`wildscr.bin`) | 2 043 → 2 042 (−1) | aide « IGNORE / SCARE / ATTACK ». Libre : 6 |
| **Total auxiliaire** | **+131** | chaque région perd 131 octets libres |

RAM principale (segments de `build/wild.map`) :

| Segment | Après l'étape 4 | Détail |
|---|---:|---|
| LOWPAGE `$0200-$03CF` | fin `$03B8` (+8) | `fauna_cause` : talon qui charge PROJECT (module 11) et saute à `module_fauna_cause`. Libre : 23 |
| TEXT `$0A00-$0FFF` | 1 525 octets | `m_crash` avec région et faune, `message_region`, `fauna_named`, `wait_any` venu de GCODE ; `m_fauna_stop` (27 octets réservés, réécrits par PROJECT) remplace « A DISCOVERY INTERRUPTS YOUR ACTION. ». Libre : 11 |
| WILDGAME `$4000-$577F` | 5 966 octets + BSS | `dhgr_frame` : module 23 → entrée 5 ; `dhgr_assets` 5 → 6 entrées ; marqueur `@` dans `message`. Libre : 3 |

Cause nommée d'un arrêt (WALK, SWIM, REST, WAIT) : quand `fauna_alert`
interrompt l'action, `fauna_cause` (LOWPAGE) charge PROJECT et
`module_fauna_cause` écrit dans `m_fauna_stop` : l'espèce de la région si
un animal vient d'être accepté sur la case du joueur (`animal_age` 0, nom
de `region_species`, « BEAR IN YOUR AREA! »), sinon la première ressource
de ce balayage (`MAP+36` bits 0-7 : GAME, FISH, INSECTS, FRUIT, CACTI,
MUSHROOMS, PLANTS, NUTS), sinon l'abri naturel (`SHELTER`) : « YOU FIND
FISH. ». Aucun tirage, aucun état de jeu écrit ; l'appelant recharge ce
dont son compte rendu a besoin.

Paquets : quatre enregistrements de plus (TRAVEL, OUTDOOR, PROJECT,
SUMMARY ; SITES remplace les fiches), soit 12 par paquet sur 17 possibles ;
+33 octets bruts par paquet (correctifs 157 au lieu de 128, couleurs 314 au
lieu de 310).

Piste non retenue pour la RAM auxiliaire : `fauna_eligible`,
`fauna_probability`, `fauna_table`, `fauna_offsets`, `fauna_k`,
`fauna_threshold` (232 octets) et `fauna_random` (16, sans appelant) ne
servent qu'aux tests de `test_fauna.py` ; le balayage de production est
celui de TRAVEL. Les retirer rendrait 248 octets dans chaque région ;
inutile depuis la carte langage principale (§ 9.7).

### 9.7 Étape 5 : étoiles et carte langage principale

Le module horaire des étoiles (`wildsky.bin`, 1 984 octets, ID 25) ne
tenait dans la RAM auxiliaire d'aucune région (545 octets libres avec Burma
après l'étape 4, 481 après l'INPUT du hall of fame). Options pesées, dans
l'ordre :

1. **Banque 2 de la carte langage principale** — retenu. ProDOS 8 occupe la
   banque 1 `$D000-$DFFF` et la zone commune `$E000-$FFFF` (MLI, pilotes,
   vecteurs) ; dans la banque 2, il ne garde que son code QUIT
   (`$D100-$D3FF`, Bitsy Bye 2.4.3, recopié en `$1000` à l'appel de QUIT).
   Mesuré dans POM2 (vidage des deux banques par `$C08B`/`$C083` pendant la
   partie) : banque 1 pleine de code, banque 2 `$D100-$D3FF` occupée,
   `$D400-$DFFF` intacte (motif de mise sous tension `$00/$FF`), `$D000`
   seul modifié (`$EE`). `video.s` et le chargeur n'y touchaient pas ;
   `mli.s` n'utilise que la banque 1 (pilote /RAM en `$FF00`). Le jeu ne
   fait aucun appel MLI pendant la partie, et les interruptions sont
   masquées pendant chaque copie et chaque rendu.
2. Instantané TOPO sans le bandeau (+1 280 octets) et ≈ 700 octets à
   trouver ailleurs : non nécessaire.
3. Abandon de l'instantané TOPO pour certaines régions : non nécessaire.

Disposition de la banque 2 principale : `$D400-$DEFF` (2 816 octets)
rejoint le stock de modules (ITM `$D400`, MVI `$DA6F`, 291 libres à
`$DDDD`), `$DF00-$DF78` reçoit le code de tracé des étoiles (121 octets,
segment `SKYRES`, fichier `build/wildskylc.bin`), qui s'y **exécute** :
`$DF79-$DFFF` restent libres (135). Le chargeur écrit ces enregistrements
avec le bit 5 du type (`$A2`/`$E2`) : même boucle que la carte auxiliaire,
`ALTZP` reste éteint. `mem_fetch` reçoit la source 3 (`BANK_MLC2`) :
lecture de la banque 2 (`$C080`), pas d'`ALTZP` ; +10 octets dans
RESIDENT.

| Élément | Où | Octets |
|---|---|---:|
| Module `wildsky.bin` (calcul horaire) | stock auxiliaire `$9A41` → fenêtre `$5800` | 1 984 |
| `stars_frame`, `stars_column` | carte principale banque 2 `$DF00` | 121 |
| Liste visible, seaux, variables de balayage, seuil | WILDLO (`st_az` `$1E62`) | 110 |
| `stars_stale` | WILDLO | 1 |
| Raccords `stars_dhgr_frame`, `stars_sky_column`, `stars_view_dark`, `stars_mark` | WILDLO (LOWCODE `$17D2-$180E`) | 61 |
| Appels dans CODE/GCODE | `render_frame`, `render_sky`, `show_view_scene`, fin de `sky_position` | 0 (−1) : chaque raccord remplace une instruction de même taille |

Les deux raccords de rendu sélectionnent la banque 2 en lecture seule
(`BIT $C080`), appellent le code en `$DF00`, puis rendent la ROM
(`BIT $C082`) ; la liste, écrite par le module dans la fenêtre `$5800`,
reste en RAM principale. Coûts mesurés en jeu (Sierra, vue complète,
`pcprof`) : nuit noire 47 553 à 54 290 cycles par vue (1,6 à 1,9 % d'une
vue de 2,93 M cycles ; 7 et 13 étoiles dessinées) ; de jour, 3 277 cycles
(raccords et sortie immédiate, 0,1 %) ; calcul horaire : module 170 000 à
175 000 cycles plus la copie RAM de 1 984 octets, 0,17 à 0,21 s par heure
de jeu, la nuit seulement ([BASELINE_DHGR.json](BASELINE_DHGR.json), clé
`lot7_stars`).

**Ciel peuplé (13 octobre 2026, [STARS.md](STARS.md) § 7 et § 13).** 282
étoiles (V ≤ 3,50) au lieu de 79, liste de 160 au lieu de 32 :

| Élément | Où | Octets |
|---|---|---:|
| Tête du catalogue `wildskycat.bin` (154 étoiles), entrée 24 | stock, banque 2 auxiliaire `$DE30` → `$9600` | 462 |
| Module `wildsky.bin` (reste du catalogue 384, code 1 788, tables 195 ; constellations entières, STARS.md § 14), entrée 25 | stock auxiliaire → `$994E` (tête et reste du catalogue devant) | 2 367 |
| BSS du module (quarts de carrés, produits de l'heure, lignes, S, AT, passe 1) | `$A200-$AF11`, fenêtre SIM | 3 346 |
| Liste (`st_a`, `st_row` : 160 + 160) et seaux (36) | carte principale banque 2 `$DE18-$DF7B` | 356 |
| `stars_frame`, `stars_column` (seuils, entrées unies et longueurs en WILDLO) | carte principale banque 2 `$DF7C-$DFF9` | 126 |
| `star_thr` et variables de balayage | WILDLO | 4 |
| `stars_stale` et raccords (dont la sauvegarde d'`overlay_current`) | WILDLO | 73 |

Le calcul horaire tourne dans la **fenêtre SIM** : `show_view_scene` n'est
appelé qu'après `sim_loaded` = 0 (`show_view_hidden`, `finish_simulation`),
et `stars_view_dark` remet `sim_loaded` à 0 et restaure `overlay_current`
(la fenêtre `$5800` ne change plus). Le module copie lui-même la tête du
catalogue (`mem_fetch` 24) devant son image ; il écrit la liste en ouvrant
la banque 2 principale en écriture (`$C083` deux fois, interruptions
masquées), puis rend la ROM. La banque 2 principale : stock
`$D400-$DE17` (ITM, MVI, 59 libres), étoiles `$DE18-$DFFE`, 1 octet libre.

Coûts mesurés en jeu (même méthode que ci-dessus, `BASELINE_DHGR.json`,
`lot7_stars`) : nuit noire, tracé 34 366 à 35 191 cycles par vue
(1,4 à 1,5 % d'une vue de 2,43 M cycles, mesure sans l'appel de
`stars_column` ; 33 et 31 étoiles dessinées) ; de jour 2 100 cycles
(0,1 %) ; calcul horaire 338 627 à 347 494 cycles (module 292 644 à
300 364, plus les copies de 2 799 octets), **0,33 à 0,34 s** par heure de
jeu la nuit ; pire cas du banc (Bolivia) 342 594 + ≈ 48 000 de copie,
0,38 s. Captures `game_stars_*` : Sierra nord 2 → 10 étoiles dessinées,
Sierra sud 7 → 31, pleine Lune 2 → 2 (Antares, Spica), Bolivia (Croix du
Sud) 10 → 37.

### 9.8 Étape 6 : score et hall of fame

Rien de résident : `NEOWILD.SYSTEM` grandit de 3 911 à 4 943 octets
(lecture de `NEOWILD.HOF` après le tronc, `BEST`, écran H : `src/hof_menu.s`),
LOADER `$9600-$A92C` et LOADBSS jusqu'à `$A974` sous `TABLE` (`$B500`) ;
INPUT passe de 1 602 à 1 666 octets (`src/hof_load.inc` : `module_end`,
`module_restart` et leur lecture commune ; 382 libres) ; le module de fin
`wildhof.bin` (3 044 octets) est lu depuis le disque (`NEOWILD.END`) à
`$9600`, fenêtre SIM libre une fois le voyage fini : l'entrée 24 du
répertoire reste vide (depuis le ciel peuplé, elle porte la tête du
catalogue des étoiles, § 9.7). Le fichier `NEOWILD.HOF` est lu dans `$5800-$59FF`
(fenêtre de modules) et réécrit en place (OPEN, WRITE 512, CLOSE) : aucun
bloc n'est alloué. Les pages `$96-$B5` du bitmap ProDOS sont libérées avant
le READ du module (le jeu les protège ; READ y refuserait le tampon,
erreur `$56`). Appels MLI après `start` : aucun pendant la partie ; en fin
de voyage 3 (`NEOWILD.END`) + 3 (lecture) + 3 (écriture), 3 seulement en
voyage libre, puis la relance (§ 9.5). Détail : [HOF.md](HOF.md).

### 9.9 Inventaire final du lot 7

| Ressource | Libre |
|---|---|
| RAM principale résidente | **361 octets** après l'intégration (§ 9.10) ; 181 à la fin du lot 7 (§ 9.4 ; 86 avant le ciel peuplé) |
| RAM auxiliaire + carte principale, par région | British Columbia 489, Sierra 1 522, **Burma 278** (plus grand morceau 147), New Guinea 1 050, Bolivia 302, Chile 1 750 après l'intégration (§ 9.10) ; fin du lot 7 : 477, 1 510, 266 (135), 1 038, 290, 1 738 (§ 9.3 ; avant le ciel peuplé : 1 524, 2 557, 1 313, 2 085, 1 337, 2 785) |
| Carte principale banque 2 | 59 (stock, `$DDDD-$DE17`) + 1 (`$DFFF`) ; avant : 291 + 135 |
| Fenêtre `$5800` | SITES 146, PROJECT 694, SUMMARY 107, INPUT 382 (le module des étoiles est passé dans la fenêtre SIM) |
| Fenêtre SIM au calcul des étoiles | `$AF12-$B5FF` 1 774 au-dessus du BSS du module |
| Volume | 247 / 280 blocs, **33 libres** (paquetage `lz`) ; disque de comparaison à carte native : 260 / 280 (§ 9.10) |

### 9.10 Intégration de la branche parallèle : géographie fine résidente

Portage du lot 5 de la branche `worktree-neowilderness-lot4` (commit
`9795a58`) ; verdict et mesures dans [GEOGRAPHY.md](GEOGRAPHY.md) § 9.
Chiffres de `build/wild.map` et `make inspect` après l'intégration.

| Changement | Effet |
|---|---|
| `geo_load`, son chemin MLI et ses paramètres retirés de RESIDENT ; `geo_decodes` (2) et `geo_queries` (3) ajoutés en RESBSS | RESIDENT `$B961-$B9FF` : **159 libres** (2 avant) |
| `native_here_travel`, `native_next_travel`, `native_restore_travel` (TEXT, GCODE) ; chemin `GEO_FIRST` d'`overlay_fetch` ; tronçon `cell_native` de 24 octets | WILDGAME `$576D-$577F` : 19 libres (4) ; TEXT `$0FED-$0FFF` : 19 (11) |
| Module `wildgeo.bin` de la fenêtre `$5800` (IDs 32–55 lus dans `NEOWILD.GEO`) remplacé par le segment `GEOAUX` (`$D480-$D7CA`, 843 octets, chargé seulement avec une carte native) | — |
| `water_native_here` retiré d'ENVIRON (SIM) ; `tp_save` saute l'instantané sur carte native (+11 octets de TOPOGEN) | stock auxiliaire : **+12 octets par région** |

| Zone | Libre |
|---|---:|
| LOWPAGE `$03B9-$03CF` | 23 |
| FORESTCODE `$09FC-$09FF` | 4 |
| TEXT `$0FED-$0FFF` | 19 |
| WILDLO `$1F79-$1FFF` | 135 |
| WILDGAME `$576D-$577F` | 19 |
| WILDERNESS `$6FFE-$6FFF` | 2 |
| RESIDENT `$B961-$B9FF` | 159 |
| **Total RAM principale résidente** | **361** (181 avant) |

Carte langage auxiliaire, vue banque 1 (`$D000-$DFFF`) et zone commune
(`$E000-$FFF9`) : sur une carte héritée, instantané de la vue sous TOPO
(§ 8.4, inchangé) ; sur une carte native, cache de 4 tuiles (`$D000-$D47F`),
code (`$D480-$D7CA`) et atlas (`$D7CB-$FFF9`, budget 10 287 octets ; Sierra
6 379, carte générée 6 113). L'enregistrement code + atlas est dans le
paquet `NEOWILD.R2` (avant la carte, décodée en dernier), seul paquet qui
reçoit la carte de `--map` : disque natif 260/280 blocs, paquet Sierra 15 →
28 blocs. Le disque livré est inchangé : `NEOWILD.DAT` 46 063 octets
stockés (14 enregistrements), 247/280 blocs. Garde-fous vérifiés
(`test_prodos.py`, `test_screen_returns.py`, `test_journey_resident.py`,
`test_geo_resident.py`) : bitmap ProDOS, page zéro et vecteur RESET rendus
à l'identique au QUIT final, pages du jeu marquées pendant la partie ;
`$0200-$03FF` auxiliaire, page zéro principale et commutateurs inchangés
par les requêtes et les écrans ; pile au plus profond à `S=$DD`.

## 11. Lot 8, étape 2 : les quatre lignes du bas (`src/menu.s`)

La surface de commande des rangées 20 à 23 ([MENUS.md](MENUS.md) § 4)
représente 2,2 Ko de code et de tables, que ni la RAM principale résidente
(361 octets libres) ni le stock auxiliaire (278 en Burma) ne pouvaient
loger. Deux emplacements sans coût pour le reste du jeu :

| Partie | Où | Octets | Libre |
|---|---|---:|---:|
| `MENUCODE` : `get_line`, boucle `idle`, ligne tapée, `prompt`, dernière rangée de droite, `cell_put`, recopie de la grille, état | `$BA00-$BDFF` (`wildmenu.bin`) : l'ancien tampon E/S ProDOS, que seuls le chargeur (désormais `LD_IOBUF = $AB00`) et la fin de partie utilisent | 842 | 182 |
| `MENUSWAP` : grille, listes, filtres d'objets, ligne de stock, tables | image dans les lignes HGR 176 à 191 des deux banques (32 morceaux de 48 octets, trous compris : rangée 176 + 8g en `$2350 + $400 g`, 184 + 8g `$80` plus loin), jamais affichées en mode mixte ni dessinées (sprites bornés à 159, `clear_rows` 16-175, instantané 0-159) ; recopiée en `$B000-$B5FF` à chaque invite (`menu_gather`, 1 536 octets, PAGE2 sous 80STORE) | 1 474 | 62 |
| `msg_begin`, `msg_char`, `msg_flush`, `msg_newline` (colonne de résultat, appelés par `message` pendant les commandes) | GCODE (`get_line` et `prompt` partis) | 161 | WILDGAME 6 |
| Temporaires de dessin et pointeurs de recopie | page zéro `$F0-$FC` (`MZP`, hors scratch du rendu et hors zone flottante Applesoft) | 13 | — |

RESIDENT garde ses 159 octets libres.

Le chargeur lit l'image de la grille en `$AF00` (libre entre son tampon
et `TABLE`) et la disperse dans les lignes cachées à la fin du chargement
(`ld_scatter`, avant la page zéro du jeu : ses pointeurs `source`/`dest`
sont en `$A2-$A5`, zone flottante). `SKYTMP` s'arrête à `$AFFF` : le module
des étoiles, qui tourne dans la fenêtre SIM depuis la vue, ne peut plus
atteindre la grille. Tronc : 16 enregistrements, 48 092 octets stockés ;
volume 250/280 blocs (30 libres, 33 avant). TEXT gagne 54 octets libres
(message de départ raccourci). Aucun octet auxiliaire, aucune lecture
disque, aucun transfert de module en plus : `test_overlays.py` et
`test_resident.py` sont inchangés.

## 12. Direction 3 : réserves conquises (14 octobre 2026)

Point de départ : tête `b941346` (lot 8, étape 2), mesurée par `make
inspect` et `build/wild.map`. Quatre gains, un commit chacun, suite
`make test` relancée en entier après chacun (73 étapes ; seule
`tests/test_sim.py`, « Night view: black terrain », échoue, et elle échouait
déjà à `b941346` : défaut antérieur, non traité ici).

### 12.1 Bilan

RAM principale résidente (`build/wild.map`) :

| Zone | Avant | Après | Changement |
|---|---:|---:|---|
| LOWPAGE `$0200-$03CF` | 23 | 23 | — |
| FORESTCODE `$0926-$09FF` | 4 | 4 | — |
| TEXT `$0A00-$0FFF` | 54 | 54 | — |
| WILDLO `$1000-$1FFF` | 124 (`$1F84`) | **1 718** (`$194A-$1FFF`) | `drows` en carte principale (12.3) |
| WILDGAME `$4000-$577F` | 6 | 6 | — |
| WILDERNESS `$6000-$6FFF` | 5 | **318** (`$6EC2-$6FFF`) | `drow_lo`/`drow_hi` en carte principale |
| RESIDENT `$B600-$B9FF` | 159 | 159 | — |
| **Total résident** | **375** | **2 282** | ×6 |
| MENUCODE `$BA00-$BDFF` / MENUSWAP | 182 / 62 | 182 / 62 | — |

Stock auxiliaire (+ carte principale), par région, libre total (plus grand
morceau) :

| Région | Avant | Après | Gain |
|---|---:|---:|---:|
| 1 British Columbia | 382 (211) | 2 860 (2 239) | +2 478 |
| 2 Sierra Nevada | 1 415 (1 244) | 3 893 (2 239) | +2 478 |
| 3 **Burma** (pire cas) | **171 (77)** | **2 649 (2 239)** | +2 478 |
| 4 New Guinea | 943 (772) | 3 421 (2 239) | +2 478 |
| 5 Bolivia | 195 (77) | 2 673 (2 239) | +2 478 |
| 6 Chile | 1 643 (1 472) | 4 121 (2 239) | +2 478 |

Morceaux libres avec la Sierra : auxiliaire `$BB24-$BFFF` 1 244,
`$B3CC-$B416` 75, `$1FF7-$1FFF` 9 ; carte auxiliaire banque 2 `$DF24-$DFFF`
220, zone commune `$F73B-$FFF9` **2 239** ; carte principale `$DDAE-$DE17`
106.

Fenêtres d'exécution :

| Fenêtre | Avant | Après |
|---|---:|---:|
| SIM `$9600-$B5FF` (`wildsim.bin`) | 8 168 (24 libres) | 7 619 (**573** libres) |
| SITES (`wildsit.bin`) | 1 902 (146) | 1 653 (**395**) |
| TOPOGEN | 2 692 | 2 928 (codeur et décodeur de l'instantané) |
| VOCAB, TRAVEL, STATUS, SCREENS | pleines (1 à 6 libres) | inchangées |

Volume : 30 → 27 blocs libres (tables d'enregistrements de 256 octets,
paquets plus morcelés). Le disque n'est plus une ressource rare (une image
800 Ko est permise), il n'a pas été optimisé.

### 12.2 Instantané TOPO compressé (commit `68543db`)

L'instantané brut (§ 8.4, 12 800 octets : banque 1, zone commune
`$E000-$FFCF`, banque 2 `$DC00-$DE2F`) devient un flux codé ligne par ligne
(`src/topo_dhgr.s`, `tp_save`/`topo_close`) : chaque ligne de 40 octets
(rangée y, banque principale puis auxiliaire) est prédite par la ligne de
la même banque deux rangées plus haut (rangées 0 et 1 : cache 160 et 161,
que TOPO ne touche pas), déjà restituée quand on la décode. Jetons, jamais à
cheval sur deux lignes : `c < $80` recopie `c + 1` octets du prédicteur,
`c ≥ $80` est suivi de `(c & $7F) + 1` littéraux ; une ligne se parcourt de
l'octet 39 à l'octet 0 (`dey`/`bmi`). Une ligne coûte au plus 60 octets.

| Mesure | Valeur |
|---|---|
| Zone | banque 1 `$D000-$DFFF` + commun `$E000-$F0FF` (8 448 octets ; `TP_SNAP_END`, `build_disk.SNAP_END`) |
| Taille mesurée, 49 vues réelles des six cartes (a2shot, positions et caps tirés) | 2 128 à 6 962 octets, moyenne 4 183 |
| Vue de départ Sierra (épave) | 6 920 octets |
| Débordement | le flux s'arrête, `tp_valid` = 0, le retour redessine la vue comme sur une carte native (`test_graphical_topo.py`, vue bruitée) |
| Ouverture de TOPO | 2,96-3,02 s → 3,12-3,18 s (+0,15 s, codeur) |
| Retour de TOPO | 0,36 s → 0,48 s (décodeur) |

Libéré : toute la banque 2 auxiliaire (`$DC00-$DE2F` rejoint le stock) et
`$F100-$FFF9` de la zone commune, soit 4 394 octets de stock. Une carte
native partage la même zone avec l'atlas (`geo_atlas.ATLAS_END` reste
`$FFFA`) : si l'atlas dépasse `$F0FF`, `build_disk` repousse le début du
stock commun pour ce seul disque (`geo['store_start']`) ; l'atlas de test
« s1985-L10 + 6 tuiles de bruit » (8 108 octets) le pousse à `$F777`.

Options écartées : compresser plus fort (prédicteur « rangée −1 » et
répétition à −2 octets : −25 % de flux en moyenne, mais décodeur plus lent
et zone déjà dictée par l'atlas Sierra natif, 6 379 octets jusqu'à
`$F0B6`) ; supprimer l'instantané (redessin de 1,9 à 6,2 s à chaque retour).

### 12.3 Lignes DHGR déroulées en carte langage principale (commit `8acedbf`)

`drows` (1 601 octets) et ses tables d'entrée `drow_lo`/`drow_hi` (322)
quittent WILDLO et WILDERNESS pour la banque 2 de la carte principale, en
`$D400` (segment `DROWS`, `build/wilddrows.bin`, enregistrement `$A2` du
tronc comme le code des étoiles). `dspan` lit `$C083` deux fois (RAM banque 2,
lecture et écriture : il plante un RTS dans les lignes), lit les tables,
passe, rétablit `LDA abs,Y`, puis rend la ROM (`$C082`). `stars_column`, qui
s'exécute lui-même dans cette banque, appelle `stars_span` (WILDLO) : un
`jsr scene_span` suivi de `bit $C080`. Les bancs (`stars_test.s`) gardent les
lignes en RAM principale (pas de `DROWS_LC`). Coût : 12 cycles par span,
+0,5 à 1,1 % de cycles par vue complète (`test_scene_render.py`). Les
tables d'enregistrements passent de 128 à 256 octets (36 entrées ;
`src/boot.s`, `build_disk.TABLE_SIZE`) : le paquet Sierra d'un disque natif
morcelé dépassait 17 enregistrements.

### 12.4 Faune : copies de référence retirées (commit `ec9ea61`)

`fauna_eligible`, `fauna_probability`, `fauna_table`, `fauna_offsets`,
`fauna_k`, `fauna_threshold` et `fauna_random` (SITES, 249 octets) ne
servaient qu'aux tests. `tests/test_fauna.py` teste désormais le balayage de
production : la boucle `idle` porte une sonde (`LDA #12`, `JSR
overlay_load`, `LDA #phase`, `STA resource_phase`, `JMP
resource_scan_species`) ; `fauna_env` est posé, l'émulateur s'arrête à
`resource_eligible`, `resource_next` ou `resource_rolled` (exportés de
`src/travel.s`, dont les étiquettes locales `@x` sont devenues `rs_x`, même
code), puis ces adresses reçoivent `JMP idle`. Les 162 fixtures Sierra, les
fixtures des cinq autres régions et les seuils (`sqrt(niveau) × minutes ×
1e-5 × taux`) sont vérifiés sur le code qui joue. Le paquet n'écrit plus que
`fauna_travel` (TRAVEL).

### 12.5 Éphéméride lunaire en carte principale (commit `b96dbe5`)

La table `sky_ephemeris` (549 octets immuables) quitte THERMAL (SIM) pour
le segment `LCDATA`, à la suite des lignes DHGR (`$DB83`) ; ses deux lectures
(`lda (gp1),y`) sont encadrées par `bit $C080` / `bit $C082` (les appels
flottants qui suivent ont besoin de la ROM). SIM : 24 → 573 octets libres
dans sa fenêtre ; le stock perd 6 octets net (−555 en carte principale, −549
d'image SIM). `test_sky`, `test_moonlight` et `test_reference_state`
inchangés.

### 12.6 Pistes mesurées et non retenues

| Piste | Mesure | Décision |
|---|---|---|
| Ne plus recopier SIM à chaque activation | après WALK, EAT, REST, WAIT, l'image diffère de la vierge en 35 octets sous `$B000` (`$AA32-$AA54`, état de SIM) et dans `$B000-$B5FF`, que la grille du menu écrase à chaque invite | Écartée : il faudrait recopier au moins `$AA00-$B5FF` et prouver sur tous les chemins qu'aucun autre octet ne change ; gain ≈ 0,45 s par WALK 1 H (≈ 5 %), au seuil |
| Images LZ dans le stock, décodées au chargement | gain 20 à 25 % sur le code des modules (7,5 Ko au total dont 2,7 Ko pour SIM) ; décodage 46 cycles/octet contre 17 en copie | Écartée pour SIM et les modules chargés à chaque commande ; possible pour TOPOGEN, STATUS, SCREENS, MVI (≈ 1,5 Ko) avec un décodeur résident en place |
| Vocabulaire en 5 bits par lettre (VOCAB) | ≈ 1 500 octets de mots → −400 octets environ | Non fait : réécriture de `lookup` et du parseur ; à faire quand VOCAB doit grandir |
| Page `SAVE` (`$BE00`, page zéro de ProDOS) en RAM auxiliaire | +256 octets contigus | Non fait : la restauration au QUIT/RESET devrait lire la RAM auxiliaire depuis la pile ; risque sur `test_prodos.py` pour 256 octets |
| Trous d'écran des rangées 0-175 | 512 octets par banque en morceaux de 8 | Déjà utilisés par des temporaires de la simulation (`hgr_rows` des tests les ignore) |
| Chargeur `NEOWILD.SYSTEM` | rien de résident après `start` (fenêtre SIM, `$A2-$AF` de page zéro) | Rien à gagner |
| Disquette 800 Ko | permettrait des enregistrements bruts (lecture plus rapide), six atlas de géographie fine | Non engagée : aucun gain de RAM |

### 12.7 Contraintes à respecter

- La carte principale banque 2 `$D400-$DE17` contient du **code exécuté**
  (`drows`) et une table lue par SIM : tout appelant qui y laisse la RAM
  sélectionnée doit savoir que `dspan` rend la ROM (passer par un relais
  comme `stars_span`) ; personne n'appelle la ROM pendant que `$C080`/`$C083`
  est actif ; ProDOS 8 2.4.3 ne touche pas cette zone (§ 9.7), à vérifier
  sur d'autres versions.
- La zone `$D000-$F0FF` de la carte auxiliaire est réservée à l'instantané
  (carte héritée) ou à l'atlas (carte native) ; le stock commence à
  `$F100` (ou après l'atlas). `$FFFA-$FFFF` reste intouché.
- `tp_save`/`topo_close` utilisent la page zéro auxiliaire (`dx`, `dy`,
  `hp`) sous `ALTZP` ; le flux peut manquer de place : le chemin de redessin
  doit rester valide.
- Une table d'enregistrements fait 256 octets ; le chargeur la lit en
  `$B500-$B5FF`.

### 12.8 Ce qui reste possible

- Carte principale banque 2 : 106 octets ; WILDLO 1 718 et WILDERNESS 318
  octets résidents libres, pour du code ou pour décharger une fenêtre pleine
  (VOCAB, TRAVEL, STATUS, SCREENS à 0-6 octets) en y déplaçant une table.
- D'autres feuilles exécutables en carte principale (comme `drows`) si la
  RAM principale manque de nouveau : `clear_rows`, `scroll`, `dhgr_pack`,
  `hud_draw` (≈ 0,8 Ko), avec le même protocole de banque.
- Modules rarement chargés compressés dans le stock (≈ 1,5 Ko), vocabulaire
  compacté (≈ 0,4 Ko de VOCAB), page `SAVE` en auxiliaire (256 octets).

## 13. Intégration des lots 2, 7, 9, 13 et LOOK : deuxième récupération (14 octobre 2026)

Point de départ : `main` à `f0d4a33` (§ 12), puis les branches du lot 7
(orientation), du lot 13 (soins, alertes, maladies) et du lot 2 (feu,
lumière, eau), enfin `main` avec le lot 9 (SAVE/RESTORE), LOOK UP/DOWN et la
MAP différentielle. Les trois lots de fidélité avaient chacun rendu
résidents environ 1 Ko de textes originaux pour la même raison (le stock
auxiliaire débordait sur le disque de stress « atlas natif bruité » de
`test_geo_resident.py`) ; ensemble, ils dépassaient WILDLO de 1 301 octets
(lots 7 + 13) puis de près de 3 Ko avec le lot 2. Les mesures viennent de
`build/wild.map` (script de zones), `make inspect` et
`tools/profile_actions.py` sur l'émulateur.

### 13.1 Bilan par zone

RAM principale résidente, octets libres :

| Zone | `f0d4a33` (§ 12) | `main` 41d5dce (lots 9 + LOOK) | lots 7 + 13 bruts | après (tout intégré) |
|---|---:|---:|---:|---:|
| TEXT `$0A00-$0FFF` | 54 | 61 | 73 | **11** (décodeur LZ, `orient_ask`, crochets SIM du lot 13) |
| WILDLO `$1000-$1FFF` | 1 718 | 1 110 | **−1 301** | **274** |
| WILDGAME `$4000-$577F` | 6 | 1 | 15 | **128** |
| WILDERNESS `$6000-$6FFF` | 318 | 305 | 94 | **40** (piles d'eau du lot 2) |
| RESIDENT `$B600-$B9FF` | 159 | 158 | 158 | **81** (3 entrées de répertoire, variables de bande de la MAP, `xfer_texts`) |
| MENUCODE `$BA00-$BDFF` | 182 | 182 | 182 | **36** (lot 2, filtres d'objets) |
| HICODE `$BE00-$BEFF` (nouveau) | — | — | — | **34** (`text_fetch`) |
| MENUSWAP (grille) | 62 | 54 | 52 | **20** |
| SIM sous `$B500` | 266 | 266 | 266 | **177** (fin `$B44F`) |

Stock auxiliaire, libre total (plus grand morceau du placement retenu) :

| Région | `f0d4a33` | lots 7 + 13 bruts | après |
|---|---:|---:|---:|
| 1 British Columbia | 3 070 (2 494) | 882 (255) | 1 656 (709) |
| 2 Sierra Nevada | 4 103 (2 494) | 1 915 (1 244) | 2 281 (1 334) |
| 3 **Burma** | 2 938 (2 494) | 671 (255) | **1 349 (429)** |
| 4 New Guinea | 3 631 (2 494) | 1 443 (772) | 1 875 (928) |
| 5 **Bolivia** (pire cas) | 2 883 (2 494) | 695 (255) | **947 (429)** |
| 6 Chile | 4 331 (2 494) | 2 143 (1 472) | 2 414 (1 467) |

« Plus grand morceau » est celui du placement glouton : un nouveau module
du tronc est replacé par la recherche en profondeur de `place()`, qui
regroupe les trous ; la vraie limite est le total du tronc. Mesuré
(`build_disk` avec un module factice incompressible) : 700 octets entrent,
900 non. La zone des sprites est dimensionnée par Bolivia (2 847 octets
compressés, le jaguar ne se compresse pas) : c'est Bolivia, pas Burma, qui
borne le stock.

Disque (140 Ko, 280 blocs) :

| Fichier | `main` 41d5dce | après |
|---|---:|---:|
| PRODOS | 35 | 35 |
| NEOWILD.SYSTEM | 10 | 9 (chargeur LZ) |
| NEOWILD.DAT (tronc) | 107 | 210 (tronc + six paquets + préparation) |
| NEOWILD.R1-R6 | 96 | — |
| NEOWILD.PRE | 8 | — |
| NEOWILD.END / .HOF | 7 / 1 | 7 / 1 |
| NEOWILD.SAV | 4 | 4 |
| parties sauvegardées | 3 × 4 | **1 × 4** |
| volume | 278/280 | 277/280 |

Sans partie sauvegardée, le volume passe de 266 (`main`) à 273 blocs : les
trois lots ajoutent environ 22 blocs, les gains de rangement (fichier
unique, chargeur compressé) en reprennent 15. Selon la règle convenue, les
parties sauvegardées sont sacrifiées les premières : il en reste une sur
l'image de 140 Ko ; `make disk800` (1 600 blocs) les garde toutes les cinq.

### 13.2 Ce qui a été fait (un commit par piste)

1. **Code mort du lot 7** (`9699b76`) : `@card`/`@az` de
   `module_tree_look`, `do_look_az` (WILDGAME 9), `module_look_az` et son
   invite (INPUT 123), le bloc USE COMPASS de `care.s` (WILDMVI 27) :
   `orient_look`/`orient_use` les prennent avant.
2. **Modules ORIENT (26) et ALERT (27)** (`a9a88f1`) : la logique de LOOK
   d'orientation, ses dialogues, l'azimut du Soleil et l'erreur du bâton
   (avec SIM chargé) quittent WILDLO pour ORIENT ; USE MAP…CHART/SHADOW,
   LOOK MAP/CHART restent dans TREE. Les règles d'alerte du lot 13 et leurs
   pourcentages tournent dans ALERT, chargé après la mise à jour de santé
   (qui vient de mettre MED dans la fenêtre : le prochain MED est un
   rechargement, 35 000 cycles) et après une commande qui a mis une alerte
   en file. Résident : l'état (`care_state`), le sommeil forcé, les ponts
   de soins.
3. **Images LZ dans le stock** (`a9a88f1`, `29306ce`, `555941a`) :
   `mem_fetch` décode en place les entrées dont l'octet de banque a le
   bit 7 (`lz_unpack`, page zéro `$50-$55` empruntée et rendue, 56 cycles
   par octet au pire contre 17 pour une copie). La copie se termine au plus
   31 octets après l'image (la marge, bits 2-6) ; `lz_guard` met ces octets
   de côté avant la copie et `lz_back` les rend : rien ne change hors de
   l'image, une fenêtre pleine (SCREENS, STATUS) aussi. Compressés :
   TOPOGEN, SCREENS, CAMP, épave, cabane, ITEMS, STATUS, MEDVIEW, TREE,
   ORIENT, ALERT et les animaux des paquets (un sprite au plus est décodé
   par vue). Écartés : MED (rechargé à chaque mise à jour de santé) et
   ADVENTURE (appelé par `mul60`, les pas thermiques, la météo) : +4 à
   +7 % sur REST et SLEEP mesurés ; SIM, VOCAB, TRAVEL, SITES, PROJECT,
   SUMMARY (à chaque commande ou à chaque vue).
4. **Instantané TOPO** : zone `$D000-$EBFF` (`TP_SNAP_END = $EC00`, était
   `$F100`) : 7 108 octets de flux au plus, contre 6 962 mesurés au pire
   sur 49 vues ; au-delà, le retour redessine la vue (comme une carte
   native). +1 280 octets de stock.
5. **Un seul fichier de données et un chargeur compressé** (`29306ce`) :
   les six paquets et la préparation suivent le tronc dans `NEOWILD.DAT` ;
   le chargeur ouvre le fichier et se place à la marque de la partie
   (`ld_open`, `ld_marks` écrites par `build_disk.py` dans
   NEOWILD.SYSTEM). Le chargeur est compressé LZ ; le talon le décode dans
   la fenêtre SIM puis remet sa page zéro dans l'état de ProDOS.
   −8 blocs pour les paquets, −2 pour NEOWILD.SYSTEM.
6. **Banque de textes** (`555941a`, `5b0b344`) : `src/textbank.txt`,
   compilé par `tools/gentextbank.py` en `build/textbank.inc` (entrée 28 du
   répertoire, segments TBINDEX/TEXTBANK à `$0000`). 150 textes imprimés
   par `message` (5 836 octets) : `messages.inc`, lot 2 (camp, eau), lot 13
   (soins, alertes), lot 7 (LOOK, dialogues), TREE, SITES, INPUT, ITEMS,
   MEDVIEW, OUTDOOR. Le « pointeur » d'un texte de la banque est son numéro
   (octet fort 0) : `lda #<m_ok / ldx #>m_ok / jsr message` ne change pas ;
   `message` voit X = 0 et appelle `text_fetch`, qui copie le texte dans
   `tb_buf` par deux `mem_fetch` (entrée de travail 29 : la paire d'index,
   puis les octets, alignés en fin de tampon) et le développe : un octet
   `$80 + k` (sauf `$A1`, littéral des textes originaux) est le mot k d'un
   dictionnaire de 105 mots choisis glouton­nement (3 372 + 286 octets au
   lieu de 5 836) ; « @ » et son opérande restent littéraux ; la sortie ne
   rattrape jamais l'entrée (un mot est plus long que son jeton). Textes
   identiques une seule fois (messages 1, 2, 11, 53 de l'original partagés
   par les lots 2, 7, 13). Coût : environ 3 000 cycles par message.
7. **SIM sous `$B500`** : les crochets SIM du lot 13 (`alert_drink`,
   `alert_rest`, `hz_diseases`, constantes) passent dans TEXT, les piles
   d'eau du lot 2 dans CODE : SIM finit à `$B44F`.
8. **Page `$BE00`** (`5b0b344`) : la page zéro de ProDOS est copiée par le
   chargeur, en fin de chargement, en auxiliaire `$BF00-$BFFF` (hors du
   stock : `REGIONS` s'arrête à `$BF00`) ; `$BE00` reçoit HICODE
   (`text_fetch`, lu avec le tronc en `$A900`). `prodos_restore` commence
   par rapatrier la page (entrée 30 du répertoire) avant de reconstruire
   /RAM, puis la restaure comme avant ; `test_prodos.py` vérifie les 256
   octets. +256 octets résidents, −256 de stock.
9. **SAVE/RESTORE** : la partie disque de `do_save` (bitmap, chemin,
   lecture de NEOWILD.SAV) passe dans INPUT (`module_save_load`, comme
   `module_end`) ; `camp_state` et `care_state` rejoignent `sv_ranges` et
   `SV_STATE` (1 487 octets par partie, toujours 4 blocs).
10. **Répartition** : `orient_ask` en TEXT, `al_sleep` en GCODE, les
    filtres d'objets du menu en MENUCODE, pour que WILDLO garde de la marge.
11. **Compteurs et tests** : les copies de `text_fetch` sont des transferts
    (`xfer_count`), comptés à part dans `xfer_texts` ; `test_walk`,
    `test_journey_resident`, `test_screen_returns` comparent les chargements
    de modules aux transferts hors textes ; `test_sleep`/`test_walk`/
    `test_overlays` comptent ALERT après chaque mise à jour de santé ;
    `tests/common.text_id` donne le numéro d'un texte de la banque. Une
    alerte n'est plus affichée sous le message de mort ou d'arrivée
    (`alerts_after` : la fin de partie parle seule ; `test_sim`).
    `src/stars_test.cfg` reçoit RESBSS (variables de bande de la MAP).

### 13.3 Coût résident par lot (avant / après la banque de textes)

| Lot | Livré (résident) | Après | Où sont passés les octets |
|---|---|---|---|
| 7 (orientation) | WILDLO +1 442 | ≈ 200 (portes `orient_look/take/use` en WILDLO, `orient_ask` en TEXT, 5 en GDATA) | ORIENT (26, LZ), TREE, banque |
| 13 (soins) | WILDLO +1 577, WILDERNESS +224, SIM +308 | ≈ 450 en WILDLO/GCODE (état 57, sommeil forcé, ponts, `alerts_after`), ≈ 300 en TEXT (crochets SIM), SIM 0 | ALERT (27, LZ), banque, OUTDOOR (`alerts_day`) |
| 2 (feu, lumière, eau) | WILDLO +1 648, WILDERNESS +206, SIM +255 | ≈ 600 en WILDLO (état, `camp_say/done/walk/verb`, `water_here`), ≈ 170 en CODE (piles d'eau) | banque (28 textes, 1 047 octets), CAMP (4, LZ) |
| 9 (SAVE) | WILDLO +237 | ≈ 80 | INPUT (`module_save_load`), banque |

### 13.4 Temps (cycles émulés, Sierra au départ)

| Action | `main` 41d5dce | après | Écart |
|---|---:|---:|---:|
| VIEW (vue complète) | 6,013 s | 6,024 s | +0,2 % |
| LOOK R (épave en vue) | 2,082 s | 2,167 s | +4,1 % (sprite de l'épave décodé : +74 000 cycles, 1,2 % d'une vue complète) |
| STATUS | 0,241 s | 0,392 s | +0,15 s (STATUS décodé deux fois : `goal_pct` charge ADVENTURE puis STATUS) |
| REST 1 H | 8,256 s | 8,409 s | +1,9 % (ALERT et le rechargement de MED) |
| SLEEP 8 H | 9,401 s | 9,618 s | +2,3 % |
| TOPO | 3,142 s | 3,253 s | +3,5 % (TOPOGEN décodé) |

WALK 1 H n'est pas comparable (la MAP différentielle est arrivée entre les
deux mesures : 10,65 → 9,27 s).

### 13.5 Contraintes nouvelles

- Un module du stock peut être LZ : tout ce qui le remplit doit passer par
  `mem_fetch`. INPUT reste brut, les modules corrigés par les paquets
  (TRAVEL, OUTDOOR, PROJECT, SUMMARY) aussi (`build_disk.py` l'affirme).
  De même pour l'image corrigée par la préparation (`pr_patch_sim`) : SIM,
  brut, porte `th_surface`, `th_a`, `th_native_composition` et `wf_storm`
  (ce dernier sorti d'ADVENTURE quand ADVENTURE est devenu LZ).
- Un texte de la banque n'a pas d'adresse : seul `message` (X = 0) ou
  `text_fetch` le lit ; un texte écrit par le jeu (`m_fauna_stop`) ou lu
  par une autre routine (`puts`, `hm_print`, `message_string` des raisons
  de voyage, imbriquée dans un message) reste résident. `tb_buf` ne sert
  qu'au texte en cours d'impression.
- `$BE00-$BEFF` n'est HICODE qu'entre la fin du chargement et
  `prodos_restore` ; l'auxiliaire `$BF00-$BFFF` est réservé.
- SIM doit finir sous `$B500` (table d'enregistrements du chargeur).
- Les disques de comparaison à carte native (tests) : leur atlas occupe le
  début du stock commun (1,2 Ko de moins) ; la zone des sprites y est
  dimensionnée pour la Sierra, un paquet dont les animaux n'entrent plus
  les perd, puis NEOWILD.SAV et la préparation sont retirés si le volume
  déborde encore. La carte de stress de niveau 10 et la vraie carte native
  de la Sierra se construisent ainsi ; l'image livrée (cartes héritées)
  n'est pas concernée.
- `test_save.py` tourne sur une copie de 140 Ko sans NEOWILD.END quand
  l'image livrée a moins de trois parties (elle en a une).

### 13.6 Pistes mesurées et écartées

| Piste | Mesure | Décision |
|---|---|---|
| Lignes DHGR et autres feuilles en carte principale (`clear_rows`, `scroll`, `dhgr_pack`, `hud_draw`) | 106 octets libres en banque 2 | Écartée : pas de place |
| Vocabulaire 5 bits | ≈ 0,4 Ko de VOCAB, réécriture de `lookup` | Non faite : VOCAB n'est pas le facteur limitant |
| LZ de SIM | −2 870 octets de stock, +0,3 s à chaque activation (3 à 4 par WALK 1 H) | Écartée |
| LZ de MED et d'ADVENTURE | +1 025 octets de stock ; REST +4 à 6 %, STATUS ×2 | Écartée |
| Zone d'instantané à `$EB00` | +256 octets, mais la vue de départ Sierra (6 920 octets) déborderait | Écartée |
| NEOWILD.END dans NEOWILD.DAT (LZ) | −2 blocs ; demande un décodeur hors MENUCODE à la fin de partie et la reprise du banc HOF | Non faite : une partie sauvegardée de plus seulement |
| Fichiers de partie plus petits | 1 487 octets : 3 blocs + index | Impossible sans réduire l'état |

### 13.7 Marge restante

WILDLO 274, WILDGAME 128, TEXT 11, WILDERNESS 40, RESIDENT 81, MENUCODE 36,
HICODE 34, MENUSWAP 20, SIM 177 sous `$B500` ; stock : Burma 1 349, Bolivia
947 octets libres (un nouveau module du tronc : 700 octets entrent, 900 non) ;
disque : 3 blocs libres avec une partie sauvegardée. Les
objectifs « WILDLO ≥ 900 avant lot 9 + LOOK » (équivalent : 292 octets
après eux) et « SIM ≥ 150 » sont tenus, à 18 octets près pour le premier ; le
« plus grand morceau ≥ 1,5 Ko » du stock de Burma et « disque ≤ 262 blocs »
ne le sont pas (1 349 octets libres en tout ; 273 blocs sans partie). Leviers
encore ouverts : LZ de MED/ADVENTURE (+1 Ko de stock, au prix de REST),
compression de VOCAB, NEOWILD.END dans le fichier unique (2 blocs).

## 14. Troisième récupération (14 octobre 2026)

Deux pistes de l'étude de conception, mesurées sur `build/wild.map`, les
`layout*.json` et a2shot (IIe, ProDOS 2.4.3, SmartPort du slot 5 pour
l'édition XL).

### 14.1 Le décodeur LZ en banque 2 de la carte principale (`$D001-$D0FF`)

ProDOS 8 2.4.3 garde `$D100-$D3FF` de la banque 2 pour son code QUIT (Bitsy
Bye) et ne lit `$D000` que pour reconnaître la banque à l'appel du MLI
(`$EE` en banque 2, `$D8` en banque 1 : cet octet ne doit jamais changer).
`$D001-$D0FF` garde le motif de mise sous tension, identique après le
démarrage et une partie, sur les deux éditions. Le décodeur de `mem_fetch`
(`lz_unpack`, `lz_guard`, `lz_back` : 251 octets de code) y tourne
désormais en place (segment `LZCODE`, enregistrement MLC2 du tronc,
`build_disk.py` `LZLC`, 253 octets avec l'aiguillage d'entrée) ; ses
variables (36 octets) restent en TEXT.

- Appel : un relais de 16 octets à deux entrées en TEXT (`lz_guard` :
  `CLC`, `lz_unpack` : `SEC`, puis `BIT $C083` deux fois, `JSR lzc_entry`,
  `BIT $C082`, `RTS` ; `lzc_entry` aiguille sur C).
  La banque 2 est lue **et** écrite : `lz_guard` réécrit ses propres
  opérandes et ceux de `lz_back`. Rien d'autre n'est écrit dans la carte : la
  sortie va dans la fenêtre (`$5800` ou `$9600`), sous `$C000`.
- Le décodeur ne touche que la RAM principale sous `$C000` (fenêtre, `mf_*`,
  `lz_*`, `$50-$55`, pile) : ni ROM, ni MLI, ni banque 1. `mem_fetch`
  masque les interruptions ; `mf_done` remet ensuite l'état de carte de
  l'appelant, comme avant.
- Les tests : `test_boot` lit `$D000` (`$EE`) et l'image du décodeur ;
  `test_pack_boot` admet un enregistrement en `$D001-$D0FF` et interdit
  toujours `$D000` et `$D100-$D3FF` ; `test_hof_volume` admet les écritures
  en `$D001-$D0FF` (le chargeur).
- TEXT : 11 → 246 octets libres (+235 : 251 de code moins le relais). Coût
  en temps négligeable (quatre `BIT` et un `JSR` de plus par image décodée).

### 14.2 Levier A, palier 1 : quatre modules lus par bloc (XL seulement)

CAMP (4), MEDVIEW (19), TREE (20) et ORIENT (26), rarement chargés, ne
sont plus dans le stock auxiliaire de NeoWildernessXL : `mem_fetch` les lit
sur le disque, bloc par bloc, directement dans leur fenêtre `$5800`.

- **NEOWILD.BLK** (`build_disk.py` `blk_file`) : un bloc d'en-tête
  (`"NWBK"` et 2 octets d'identité, SHA-256 du contenu), puis chaque module
  brut (pas LZ : plus rapide, et une lecture n'écrit jamais sous `$5800`),
  complété de zéros jusqu'au bloc. Son nom précède tous les autres : le
  constructeur de volume l'alloue le premier, bloc d'index 7, données à
  partir du bloc 8 (`BLK_FIRST`), sur les deux tailles de volume ; les
  numéros de bloc sont donc connus avant NEOWILD.DAT, qui contient le
  répertoire (pas de circularité). `build_disk` relit l'image construite et
  vérifie l'index et le contenu (`check_blk`). CAMP blocs 9-12, MEDVIEW
  13-15, TREE 16-17, ORIENT 18-20 ; 13 blocs + l'index.
- **Répertoire** : nouveau code de banque `BANK_DISK = $40` ; source = le
  premier bloc absolu, longueur = la longueur brute, fenêtre `$5800`. Une
  image ≤ `$800` (affirmé) : la lecture du dernier bloc écrit au plus 511
  octets de bourrage après le module, toujours dans la fenêtre de 2 Ko.
- **Lecteur résident** : dans `mem_fetch`, après le chargement du code de
  banque, `CMP #BANK_DISK / BNE / JMP disk_fetch` (7 octets) ; `mf_dst`,
  `mf_src`, `mf_rest`, `mf_pages` passent en RESBSS derrière deux octets
  `rb_parms` (3) et `rb_unit` : ensemble, une liste de paramètres
  READ_BLOCK `[3, unité, tampon, bloc]` (+2 octets). `disk_fetch` (TEXT) : blocs = ⌈longueur / 512⌉, boucle READ_BLOCK par `mli_call`
  (compté dans `mli_reads`/`mli_bytes`) en avançant tampon et bloc, puis
  `mf_done` (97 octets avec son compteur). Sur erreur (disque retiré) : un bip, une touche, nouvel essai.
  ProDOS laisse modifiée la commande de son pilote de blocs (`$42-$47`) et
  d'autres octets de `$3A-$4F` (mesuré : `$40`, `$41`, `$45`, `$46`, `$4F`) :
  `disk_fetch` garde `$3A-$4F` sur la pile, `mem_fetch` préserve toujours
  toute la page zéro. Aucune préparation de plus : `mem_fetch` masque déjà
  les interruptions, coupe 80STORE, RAMRD et RAMWRT, la page zéro et la
  pile sont les principales ; les pages `$58-$5F` sont libres dans le bitmap
  de ProDOS (`boot.s` `game_pages`), sans quoi READ_BLOCK refuserait le
  tampon (erreur `$56`, mesurée vers `$9800`).
- **Chargeur** : `rb_unit` = DEVNUM au démarrage (l'unité d'amorçage). Si
  `ld_blk` (écrit par `build_disk`, 0 sur 140 Ko) est non nul, il lit le
  bloc d'en-tête et compare ses 6 premiers octets : une copie fichier par
  fichier qui aurait déplacé les blocs reçoit « NEOWILD.BLK HAS MOVED: COPY
  THE WHOLE DISK BLOCK BY BLOCK, NOT FILE BY FILE. » puis revient à ProDOS
  (`test_editions.moved_blk`). Le chargeur a grandi de 157 octets : HICODE
  est lu en `$AA00` au lieu de `$A900` (`HI_LOAD`, exporté pour
  `build_disk`), 119 octets restent sous lui.
- **Quand ils se chargent** : CAMP aux commandes de feu et d'eau (GET
  WATER, FILL…) et au retour d'un appel imbriqué ; MEDVIEW aux soins (USE
  SUNSCREEN, USE FIRSTAID KIT…) ; ORIENT à LOOK N/E/S/O/STARS et après les
  saisies de ses dialogues ; TREE à USE COMPASS et aux commandes d'arbre.
  Jamais pendant le rendu d'une vue, un demi-pas de marche ou le retour
  d'un écran : `test_screen_returns` garde zéro appel MLI.
- **Politique** : XL = palier 1 sur disque ; l'édition 140 Ko (Disk II,
  lent, et dont le stock a la place : sa zone de sprites est celle de la
  Sierra seule) garde tout dans le stock (`EDITIONS` `disk_modules`). Le
  lecteur résident existe dans les deux ; les répertoires diffèrent.
  Les disques de comparaison des tests (`common.disk_with`, 280 blocs, six
  paquets) gardent aussi tout dans le stock.

Latence (a2shot, `test_transfers`, `overlay_load` compris) :

| Module | octets | blocs | avant (LZ du stock) | après (disque, XL) |
|---|---:|---:|---:|---:|
| CAMP (4) | 1 617 | 4 | 91 364 cycles | **34 843** (8 710 par bloc) |
| MEDVIEW (19) | 1 058 | 3 | 58 621 | **26 343** |
| TREE (20) | 710 | 2 | 36 877 | **17 848** |
| ORIENT (26) | 1 149 | 3 | 64 766 | **26 343** |

Sur le vrai matériel : un lecteur 3,5" arrêté met environ 0,5 à 1 s à
reprendre sa vitesse ; le premier chargement d'un de ces modules après un
temps sans accès disque peut donc durer une seconde (l'émulateur ne le
modélise pas). Les tests qui comptent les appels MLI d'une partie
(`test_resident` : USE SUNSCREEN et USE FIRSTAID KIT lisent MEDVIEW,
3 READ_BLOCK chacun) attendent exactement ces lectures sur XL.

### 14.3 Bilan

RAM principale résidente, octets libres (`build/wild.map`) :

| Zone | avant (§ 13, état du 14/10) | après |
|---|---:|---:|
| TEXT `$0A00-$0FFF` | 11 | **149** (+235 net du décodeur, −97 de `disk_fetch`) |
| WILDLO `$1000-$1FFF` | 7 | 7 |
| WILDGAME `$4000-$577F` | 14 | 14 |
| WILDERNESS `$6000-$6FFF` | 4 | 4 |
| RESIDENT `$B600-$B9FF` | 12 | **3** (aiguillage `BANK_DISK` 7, `rb_parms`/`rb_unit` 2) |
| MENUCODE `$BA00-$BDFF` | 12 | 12 |
| HICODE `$BE00-$BEFF` | 3 | 3 |
| banque 2 principale `$D001-$D0FF` | 255 (inutilisé) | 2 |
| chargeur (sous HICODE) | 20 | 119 (HICODE lu en `$AA00`) |

Stock auxiliaire (`layout.json`, `layout-140.json`) ; « place du tronc » =
`aux_trunk_free` moins la zone des sprites de l'édition :

| Édition | `aux_trunk_free` avant → après | zone des sprites | place du tronc avant → après |
|---|---:|---:|---:|
| XL (800 Ko) | 3 343 → **7 209** | 2 847 (Bolivia) | 496 → **4 362** |
| Neowilderness (140 Ko) | 3 343 → 3 343 | 1 513 (Sierra) | 1 830 → 1 830 |

Après le paquet le plus lourd de XL (Bolivia), 4 362 octets restent libres
(Sierra 5 696). Disque XL : 298 → 305 blocs sur 1 600 (NEOWILD.BLK 14
blocs, NEOWILD.DAT 7 de moins) ; 140 Ko : 222 → 223 blocs sur 280 (le
chargeur, NEOWILD.SYSTEM, prend un bloc de plus).

## 15. Quatrième récupération : lot de relocalisation (14 octobre 2026)

But : au moins 1,5 Ko de RAM principale résidente pour les travaux à venir
(FORAGE : chasse, pêche, cueillette ; générateur de terrain). Deux études
mesurées : la couverture de douze parties (chaque instruction exécutée
comptée : le code résident est chaud à 87 %, ce qui reste froid est surtout
le démarrage et la sortie) et la banque 2 de la carte langage principale
(`$D100-$D3FF`, le code QUIT de ProDOS 8). Comptes : `build/wild.map`
(zones de `src/wild.cfg`), `build/layout.json` et `layout-140.json`.

### 15.1 Les pas

| Pas | Ce qui bouge | Zones |
|---|---|---|
| T1 | `start`, les commutateurs de `native_video` et la prise de /RAM (`_prodos_video_claim`) passent dans le chargeur (`boot.s` `start`, `ld_claim`, et un FORMAT de /RAM dans `ld_quit`) ; `dev/lib/prodos` n'est plus lié au jeu (`video.o`, `mli.o` : 4 octets de BSS en moins) | WILDERNESS +187 (dont 41 rendus par T2), WILDGAME +4 ; chargeur +74 |
| T2 | La sortie dans INPUT : `prodos_restore` (texte, FORMAT de /RAM, bitmap, vecteur RESET, page zéro), `prodos_quit`, `module_reset_exit`. RESET : relais résident `reset_exit` (12 octets : `CLD`, pile `$FF`, `mem_fetch` direct d'INPUT, brut, puis `module_reset_exit` ; un RESET remet la //e en RAM principale, ALTZP coupé, ROM, interruptions masquées ; `overlay_current` peut mentir, d'où la copie directe). L'état de départ (bitmap 24, vecteur 3, unité /RAM 1) quitte RESBSS : le chargeur l'écrit à la prise dans l'entrée 2 du répertoire (`EX_ENTRY`, stock auxiliaire juste sous la zone des sprites, adresse écrite par `build_disk` dans `ld_exit`), la sortie le recopie en `EX_BUF` = `$2000`. Le FORMAT de /RAM prend `$2000` pour tampon : bitmap et vecteur sont relus avant lui | RESIDENT +127, WILDERNESS +41, INPUT −145, stock −177 |
| T3 | `st_inputs` et `st_tugap` rentrent dans le module des étoiles (25) | WILDLO +85, WILDGAME +72, SKYSTARS 186 → 32 libres, stock −159/−163 |
| T4 | La boîte à deux touches d'`orient_ask` passe dans ORIENT ; `orient_number` (le nombre par INPUT, puis ORIENT de nouveau) reste en TEXT | TEXT +67 ; stock 140 Ko −67 (XL : ORIENT est sur le disque) |
| T5 | `select` (RETURN dans la grille) dans INPUT : relais de 8 octets (`overlay_load` 13, `module_select`). Il n'appelle que du résident et MENUSWAP et finit dans `idle` ou `done_menu` | MENUCODE +157, INPUT −165, stock −165 |
| T7 | `do_save` : relais (INPUT, `module_save` : lecture, exécution, bitmap) ; `do_save_view` (la vue et « GAME n RESTORED. ») reste résident, `show_view` ne pouvant tourner depuis `$5800` | WILDLO +51 (`sl_bitmap` dans INPUT), INPUT −57 |
| Banque 2 (B2) | Le chargeur met le code QUIT (`$D100-$D3FF`) dans l'état de sortie, à la prise, avant tout enregistrement qui le remplace (`ldc_put` par `ld_place`) ; `EX_SIZE` = 28 + 768. La sortie d'INPUT le remet (avant le FORMAT de /RAM) ; `ld_quit` aussi (Q au menu, erreur), par une boucle de 15 octets copiée en `$0100` (RAMRD déplace aussi le programme : `ld_unquit`). `column_setup`, `scroll`, `clear_rows`, `dhgr_pack`, `hud_draw` (746 octets, segment `B2CODE`, enregistrement MLC2 du tronc après la prise) y tournent derrière un relais de 10 octets (`B2_ENTRY` : `BIT $C080`, `JSR b2_…`, `BIT $C082`, `RTS`) ; `hud_draw` appelle `b2_dhgr_pack` sans relais | WILDLO +269, WILDERNESS +427, banque 2 libre 770 → 24, stock −768 |
| Navigation | Correction du même jour (bas ouvre la grille, bas sous sa dernière rangée ouvre TOPO : `grid_bottom`) | MENUCODE −60 |

`dc_pat` (64 octets, ne doit pas franchir une page) passe devant les tables
de phase dans CODE. Le chargeur lit HICODE en `$5800` (`HI_LOAD`, la fenêtre des modules,
qu'aucun enregistrement ni la préparation ne touche et que le jeu remplit
avant de la lire ; pas `$9500` : des variables de SCRATCH y sont lues au
départ, `test_reference_state` l'a montré) au lieu de `$AA00` : il gagne une
page ; il garde 105 octets libres sous son
tampon d'E/S (`$AB00`).

### 15.2 Bilan

RAM principale résidente, octets libres :

| Zone | avant (§ 14) | après |
|---|---:|---:|
| TEXT `$0A00-$0FFF` | 149 | **216** |
| WILDLO `$1000-$1FFF` | 7 | **412** |
| WILDGAME `$4000-$577F` | 14 | **90** |
| WILDERNESS `$6000-$6FFF` | 4 | **659** |
| RESIDENT `$B600-$B9FF` | 3 | **129** |
| MENUCODE `$BA00-$BDFF` | 9 | **106** (166 avant la navigation) |
| HICODE `$BE00-$BEFF` | 3 | 3 |
| MENUSWAP `$B000-$B5FF` | 47 | 47 |
| banque 2 principale `$D001-$D3FF` | 770 (`$D100-$D3FF` : code QUIT) | 24 |
| INPUT (fenêtre `$5800`) | 663 | 264 |

Total : **1 486 octets** résidents de plus (1 546 avant la correction de la
navigation).

Stock auxiliaire ; place du tronc = `aux_trunk_free` moins la zone des
sprites de l'édition :

| Édition | `aux_trunk_free` | zone des sprites | place du tronc avant → après |
|---|---:|---:|---:|
| XL (800 Ko) | 7 140 → 5 796 | 2 847 | 4 293 → **2 949** |
| Neowilderness (140 Ko) | 3 274 → 1 858 | 1 513 | 1 761 → **345** |

Disque : XL 305 → 304 blocs, 140 Ko 223 → 224 blocs.

Temps (cycles émulés, XL, Sierra, de `do_command` à `idle`) : vue complète
(V) 6 342 285 → 6 325 006 ; LOOK L 1 848 836 → 1 844 305 (les relais de
banque 2 coûtent environ 20 cycles par appel, 140 colonnes par vue : moins
que ce que la vue a gagné ailleurs). Un RETURN dans la grille copie INPUT
(1 784 octets bruts, ≈ 24 000 cycles) ; SAVE/RESTORE et QUIT chargeaient
déjà INPUT.

### 15.3 Contraintes nouvelles

- Entrée 2 du répertoire : l'état de sortie, écrit par le chargeur, jamais
  par un enregistrement (`test_pack_boot`). `$D100-$D3FF` de la banque 2 :
  le code de la vue pendant la partie ; toute sortie remet le code QUIT
  (`test_prodos` compare `$D000` et `$D100-$D3FF` à l'entrée du chargeur, à
  QUIT puis Q et à RESET). Un enregistrement qui écrit `$D100-$D3FF` doit
  suivre la prise (`test_pack_boot` `replay`).
- Le code de banque 2 ne doit appeler ni ROM, ni MLI, ni `mem_fetch`, ni
  `dspan`, ni aucune routine qui rend la ROM ; entre elles, les routines de
  la banque s'appellent par leur nom `b2_`. Leurs appelants tournent avec la
  ROM.
- INPUT porte désormais la sortie : il reste brut dans le stock (le relais
  RESET le copie directement).
- Le FORMAT de /RAM écrit `$2000` : tout ce que la sortie lit dans `EX_BUF`
  doit l'être avant lui.
- Disques de comparaison des tests (`--map`) : zone de sprites de la Sierra
  seule (les autres paquets perdent leurs animaux s'ils n'entrent plus,
  comme à carte native) ; à carte native, TREE et ORIENT sont lus sur
  NEOWILD.BLK (aucun test ne les joue sur ces cartes).

### 15.4 Pistes écartées

| Piste | Mesure | Décision |
|---|---|---|
| T6 : noms d'objets (`it_n*`, `it_name_lo/hi`, 761 octets de WILDLO) et textes d'arrêt de voyage (116 de TEXT) dans le stock | stock +650 à 800 octets ; il en reste 345 sur 140 Ko | Non faite : il faudrait garder au moins 300 octets sur 140 Ko |
| B1 : relire les deux blocs de PRODOS au lieu de garder le code QUIT dans le stock | rendrait 768 octets de stock (et permettrait T6) | Non faite : dépend du PRODOS du disque de démarrage (une copie de Bitsy Bye modifiée en mémoire ou un autre ProDOS la casserait) ; B2 est sûr sur les deux éditions |
| `select` dans TREE ou ITEMS | TREE est lu sur le disque (XL), ITEMS est LZ (≈ 50 cycles par octet) | INPUT, brut, est le plus rapide |
| `grid_bottom` dans INPUT | MENUCODE +47, mais stock 140 Ko 345 → 293 | Gardé en MENUCODE |

## 16. Lot 4 : chasse, pêche, cueillette, repas (14 octobre 2026)

Le lot ([FORAGE.md](FORAGE.md) § 17) ajoute environ 7,8 Ko de code et de
textes. Les règles retenues : les commandes sont **un module disque** sur
les deux éditions (le stock de l'édition de 140 Ko n'avait que 345 octets
de place, les fenêtres `$5800` sont pleines ou presque), ce qui ne sert
qu'à un moment précis va dans le module déjà chargé à ce moment, le reste
(état, porte, filtre) est résident. Mesures : `build/wild.map`,
`build/layout.json`, `build/layout-140.json`, `tests/test_transfers.py`,
`tests/test_editions.py`.

### 16.1 Où est le lot

| Partie | Zone | Octets |
|---|---|---:|
| Module FORAGE (entrée 31 du répertoire, `src/frg.s`) | NEOWILD.BLK, lu en `$9600` (12 blocs, 834 octets libres sous `$B000`) | 5 822 |
| État `forage_state` (sauvé), `fg_hm`, `fg_after`, `fg_eff`, `fg_t`, `fg_q`, `fg_bm`, `fg_fidelity` | WILDLO (LOWTEXT) | 221 + 12 |
| `forage_here`, `fg_place`, `forage_hours`, `fg_count` | WILDLO (LOWCODE) | 169 |
| `forage_gate` (porte, bitmap, effort, `camp_done`) | TEXT | 118 |
| `forage_wants`, `forage_cond`, `forage_menu`, masques | WILDERNESS (CODE) | 313 |
| `forage_after` (gibier, poisson partis), `forage_day`, entrée 31 du répertoire, test `X_FORAGE` de `verb_extra` | RESIDENT | 72 |
| `forage_skip`, crochets de `spend`, `do_walk`, `resolve_menu` | WILDGAME | 41 |
| CATCH, KILL, SKIN, COOK, TASTE de la grille | MENUSWAP | 37 |
| `module_resource_results` (venu d'ADVENTURE) + `forage_found` | ITEMS | +686 |
| `forage_kill`, `out_value` (V, rempli par les paquets) | OUTDOOR | +129 |
| `forage_clock`, `forage_news`, `module_forage_day`, `fg_seg` | ALERT | +830 |
| INVENTORY (piles, `SPOIL`), deux lignes de HELP | STATUS | +306 |
| `forage_skip` à la place de deux tests de verbe | TRAVEL | −8 |
| `module_resource_results` parti | ADVENTURE | −256 |
| `sv_ranges` + `forage_state` | SAVEMOD | +4 |
| SIM | — | 0 (`$B453`, 172 octets sous `$B500`) |

### 16.2 RAM principale résidente, octets libres

| Zone | avant (§ 15.2) | après |
|---|---:|---:|
| TEXT `$0A00-$0FFF` | 216 | **98** |
| WILDLO `$1000-$1FFF` | 412 | **4** |
| WILDGAME `$4000-$577F` | 90 | **49** |
| WILDERNESS `$6000-$6FFF` | 477 | **164** |
| RESIDENT `$B600-$B9FF` | 129 | **57** |
| MENUCODE `$BA00-$BDFF` | 106 | 106 |
| HICODE `$BE00-$BEFF` | 3 | 3 |
| MENUSWAP `$B000-$B5FF` | 47 | **10** |
| SIM sous `$B500` | 172 | 172 |

Total : 989 octets résidents pris (WILDLO est plein : l'état seul en prend
221). Fenêtres `$5800` (libre sur 2 048) : ITEMS 396, OUTDOOR 637, ALERT
346, ADVENTURE 308, TRAVEL 9.

### 16.3 Stock auxiliaire et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc (`aux_trunk_free` − zone des sprites) avant | 2 949 | 345 |
| après | **1 372** | **392** |
| Modules lus sur NEOWILD.BLK | CAMP, MEDVIEW, TREE, ORIENT, FORAGE | TREE, ORIENT, FORAGE |
| NEOWILD.BLK | 25 blocs + index (12 800 octets) | 18 blocs + index (9 216 octets) |
| Volume | 305 → **327** blocs sur 1 600 | 224 → **249** blocs sur 280 (31 libres) |
| Partie sauvegardée (NEOWILD.Sn) | 1 709 octets, 5 blocs (était 4) | idem, cinq parties |

Le lot fait grandir le stock d'environ 1 440 octets stockés (ITEMS +620,
ALERT +639, STATUS +256, OUTDOOR +129, ADVENTURE −201, TRAVEL −8) sur les
deux éditions ; sur 140 Ko, TREE (561 octets LZ) et ORIENT (1 065) passent
sur NEOWILD.BLK pour les y loger. Les disques de comparaison des tests
(`--map`) : TREE et ORIENT sur NEOWILD.BLK ; si l'atlas d'une carte native
laisse trop peu de stock, MEDVIEW aussi, puis les quatre modules de XL
(carte native de la Sierra, cartes de stress) ; si le volume de 280 blocs
déborde, le seul paquet de la Sierra (`tools/build_disk.py`, au moins de
modules possible). `test_resident.py` et `test_geo_resident.py` lisent le
répertoire du disque pour attendre les lectures de MEDVIEW et de CAMP.

### 16.4 Temps

| Mesure | XL | 140 Ko |
|---|---:|---:|
| Lecture de FORAGE (12 blocs, de `forage_gate` à `$9600`) | 103 480 cycles (0,10 s) | **1 328 070 cycles (1,30 s)** |
| par bloc (`test_transfers.py`, XL) | 8 568 | — |

Une commande du lot coûte donc 0,1 s sur XL et 1,3 s sur le Disk II émulé
(plus la remise en vitesse d'un lecteur arrêté sur le vrai matériel) ; une
commande refusée aussi (le filtre résident ne prend que les couples
verbe-nom du lot). Les découvertes pendant la marche chargent ITEMS (LZ,
déjà le cas d'ADVENTURE avant), une fois par découverte ; le facteur du
jour charge ALERT à minuit (une fois par jour) ; l'horloge tourne dans
ALERT déjà chargé après chaque mise à jour de santé. Aucune lecture disque
pendant une vue, un demi-pas de marche ou un écran (`test_resident.py`,
`test_screen_returns.py`).

### 16.5 Contraintes nouvelles

- WILDLO n'a plus que 4 octets : l'état d'un lot futur ira en WILDGAME,
  TEXT ou WILDERNESS.
- Un module disque de la fenêtre SIM : son lecteur (la porte) libère les
  pages `$90-$AF` du bitmap de ProDOS autour de `mem_fetch` ; ses blocs
  entiers restent sous `$B000` (`build_disk.DISK_END`, affirmé).
- FORAGE ne peut appeler ni SIM, ni `load_totals`, ni `take_oz` : il a son
  propre générateur (`fr_rnd`, même graine que `weather_random`) et fait la
  transaction des onces lui-même ; la porte recharge SIM pour le temps.
- Les textes du module sont imprimés par `message` avec leur adresse ; un
  « ! » littéral s'écrit `$A1` (le « ! » est la raison de voyage).

## 17. Messages collés, triangle des arbres, feu animé (14-15 octobre 2026)

Trois correctifs après le lot 4. Mesures : `build/wild.map`,
`build/layout.json`, `build/layout-140.json`, `tests/test_fire.py`.

| Changement | Zones |
|---|---|
| « ! » littéral en `'!'\|$80` (`cause_area`, `m_fauna_stop`, `ol_long_msg`) | 0 |
| Une couronne, une case (`forest_candidate`, `forest_crown`, `forest_square` en WILDERNESS ; `forest_centre` en TEXT ; `forest_dist` en FORESTCODE) | TEXT +88, WILDERNESS +135, FORESTCODE +1, WILDGAME −40 |
| Feu : `fire_tick`, `fire_hide`, état, crochets de `menu.s` | MENUCODE +94 |
| Feu : `fire_fetch` ; `sim_fetch` (lecture SIM commune à FORAGE et au feu) | WILDGAME +55 |
| `df_kbd` (une touche coupe la lecture entre deux blocs) ; `forage_gate` appelle `sim_fetch` | TEXT +11 −27 |
| Case du feu `fire_cx`, `fire_cy` dans `camp_state` (sauvée) | WILDLO +2, CAMP +12 |
| Module FIRE (entrée 18, l'ancien alias de 17) sur NEOWILD.BLK, les deux éditions | stock 0, 3 blocs |

### 17.1 RAM principale résidente, octets libres

| Zone | avant (§ 16.2) | après |
|---|---:|---:|
| TEXT `$0A00-$0FFF` | 98 | **26** |
| WILDLO `$1000-$1FFF` | 4 | **2** |
| WILDGAME `$4000-$577F` | 49 | **34** |
| WILDERNESS `$6000-$6FFF` | 164 | **29** |
| RESIDENT `$B600-$B9FF` | 57 | 57 |
| MENUCODE `$BA00-$BDFF` | 106 | **12** |
| HICODE / MENUSWAP | 3 / 10 | 3 / 10 |
| SIM sous `$B500` | 172 | 172 |

### 17.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc avant → après | 1 372 → **1 373** | 392 → **387** |
| NEOWILD.BLK | + FIRE (3 blocs) | + FIRE (3 blocs) |
| Volume | 327 → **331** blocs sur 1 600 | 249 → **253** blocs sur 280 (27 libres) |

### 17.3 Temps

| Mesure | XL | 140 Ko |
|---|---:|---:|
| Apparition du feu après l'invite : attente, lecture, première image | 1,04 + 0,03 + 0,13 = **1,19 s** | 1,04 + 0,84 + 0,13 = **2,0 s** |
| Premier bloc d'une lecture coupée par une touche | 0,01 s | 0,96 s |
| Vue V / LOOK L (cinq scènes de forêt, `landfix/fx/cycles.py`) | +0,3 à +2,0 % / +0,8 à +1,6 % | idem |

Le feu n'est lu qu'à son apparition, pas entre deux images (rien d'autre
ne tourne dans `idle`) ; chaque invite qui le montre le relit (la commande
précédente a pu reprendre `$9600`). Contrainte nouvelle : MENUCODE n'a
plus que 12 octets.

### 17.4 Feu ancré dans le monde et qui se consume (15 octobre 2026)

Le feu se dessine à la colonne de son relèvement (le cap à l'allumage) et
brûle 180 minutes ([CAMP.md](CAMP.md) § 8). Mesures sur l'arbre intégré :

| Changement | Zones |
|---|---|
| `fire_light` (copie `px`, `py`, `heading` ; durée neuve), appelé par MAKE FIRE | WILDGAME +17, CAMP −9 |
| `fire_pos` (6), `fire_life` (1) en GDATA, plage sauvée de l'horloge ; `fire_cx`, `fire_cy` quittent `camp_state` | WILDGAME +7, WILDLO −2 |
| `fire_clock` (en tête de `module_health`) ; quatrième nouvelle de `forage_news` (« YOUR FIRE HAS BURNED OUT. ») | SIM +70 (172 → 102 sous `$B500`) ; ALERT +28 |
| Module FIRE : place, découpe, stades (petites flammes, braises) ; 1 453 → 1 993 octets | NEOWILD.BLK 3 → 4 blocs |
| Tampons : fond rangée × 20, variables, rangée composée de 20 octets | `$A000-$A2BB` (sous GRID, `$A300`) |

Après : TEXT 26, WILDLO 4, WILDGAME 10, WILDERNESS 18, RESIDENT 5,
MENUSWAP 9, MENUCODE 15, HICODE 3 octets libres, SIM 102 sous `$B500` ;
tronc XL 1 562 → 1 463, 140 Ko 1 475 → 1 382 ; volume XL 337 → 338 blocs,
140 Ko 260 → 261 sur 280.
Apparition sur 140 Ko : lecture 0,84 → 1,22 s (un bloc de plus). Image :
61 000 à 75 000 cycles (flammes pleines), 27 000 à 30 000 (petites
flammes), ≈ 9 500 (braises) ; `fire_hide` 29 800.

## 18. Grille rationalisée : module GRID, TOPOGEN et MEDVIEW sur disque (15 octobre 2026)

La grille d'actions rationalisée ([MENUS.md](MENUS.md) § 4 : onze verbes
fixes grisés, verbes contextuels par urgence, listes, file des
prérequis, soins de la page MEDICAL, ligne F d'OPTIONS) ne tenait ni dans
MENUSWAP (10 octets libres) ni dans MENUCODE (12). Ce que fait RETURN
devient un module du stock, et deux modules rarement chargés quittent le
stock pour NEOWILD.BLK. Mesures : `build/wild.map`, `build/layout.json`,
`build/layout-140.json` ; avant = l'arbre du § 17 reconstruit à part.

| Changement | Zones |
|---|---|
| Module GRID (`src/grid.s`, entrée 32, `MOD_COUNT` 33) : `module_select` (venu d'INPUT), listes, composition, file `module_queue` ; exécuté en `$A300-$AC97`, au-dessus des tampons du feu (`$A000-$A2BB`), sous MENUSWAP (`$B000`) | stock +2 456 ; INPUT −139 |
| `grid_fetch` (recopie de GRID à chaque RETURN de la grille et à chaque étape de la file), `grid_water` | RESIDENT +52 |
| `mk_stock`, `mk_water` (MAKE grisé ou non), état de la file `mq_*`, crochets de `get_line` | MENUCODE −3 (net, après déplacements) |
| `verb_table` réordonnée (`K_BASE`, cellule WALK/SWIM) ; TAKE, ATTACK, TASTE, STICKS hors grille | MENUSWAP +1 |
| Gestes de soin de la page MEDICAL (`med_foot`, rangée 23, CARE) | MEDVIEW +546 (1 058 → 1 604) |
| Focus sur les affections, `pg_open`, ligne F d'OPTIONS | STATUS +259 (5 869 → 6 128) |
| `BOIL WATER n OZ` en ligne (analyseur) | INPUT (inclus ci-dessus) |
| `forage_menu` : le KILL du lot 4 seulement sans animal sur la case ; TASTE hors grille | WILDERNESS +11 |
| TOPOGEN (entrée 0, 2 987 octets) lu sur NEOWILD.BLK par `sim_fetch` à l'ouverture de TOPO, **les deux éditions** | stock −2 987, disque +6 blocs |
| MEDVIEW (entrée 19) sur NEOWILD.BLK aussi sur l'édition 140 Ko (XL l'y lisait déjà) | stock 140 Ko −1 604, disque +4 blocs |

### 18.1 RAM principale résidente, octets libres

| Zone | avant (§ 17.1) | après |
|---|---:|---:|
| TEXT `$0A00-$0FFF` | 26 | 26 |
| WILDLO `$1000-$1FFF` | 2 | 2 |
| WILDGAME `$4000-$577F` | 34 | 34 |
| WILDERNESS `$6000-$6FFF` | 29 | **18** |
| RESIDENT `$B600-$B9FF` | 57 | **5** |
| MENUCODE `$BA00-$BDFF` | 12 | **15** |
| HICODE / MENUSWAP | 3 / 10 | 3 / **9** |
| SIM sous `$B500` | 172 | 172 |

### 18.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc avant → après | 1 373 → **1 562** | 387 → **1 475** |
| NEOWILD.BLK avant | CAMP, FIRE, MEDVIEW, TREE, ORIENT, FORAGE | FIRE, TREE, ORIENT, FORAGE |
| NEOWILD.BLK après | + TOPOGEN (6 blocs) | + TOPOGEN (6 blocs), + MEDVIEW (4 blocs) |
| Volume | 331 → **337** blocs sur 1 600 | 253 → **260** blocs sur 280 (20 libres) |

GRID reste dans le stock : il est recopié à chaque RETURN de la grille,
trop souvent pour le disque. La marge du stock regagnée (≈ 1,1 Ko sur
140 Ko) est la réserve du prochain lot.

### 18.3 Temps

| Mesure | XL | 140 Ko (Disk II émulé) |
|---|---:|---:|
| Ouverture de TOPO (lecture de TOPOGEN) | négligeable (non mesuré) | **+0,66 s** |
| Première page de soins (lecture de MEDVIEW) | inchangé (déjà sur disque) | **+0,44 s** |
| RETURN dans la grille (recopie de GRID, 2 456 octets, RAM auxiliaire) | à mesurer | idem |

`tests/test_grid_play.py` publie, par action jouée au joystick, les
commandes tapées, les lectures de blocs et le temps émulé.

### 18.4 Contraintes nouvelles

- RESIDENT n'a plus que 5 octets, MENUCODE 15, WILDERNESS 18 : l'état d'un
  lot futur ira en WILDGAME, TEXT ou dans un module.
- GRID, le feu animé (`$9600-$9DC8`, tampons `$A000-$A2BB`), STATUS
  (`$9600-$ADEF`) et TOPOGEN partagent la fenêtre SIM : GRID est recopié à
  chaque RETURN et à chaque étape de la file, jamais supposé présent. Une
  adresse de STATUS (`page_top`, `$A8A6`) tombe dans GRID : un test qui
  attend une page s'arrête sur une entrée résidente (`scr_status`), pas
  sur une adresse de la fenêtre.
- Le trajet crash → rangers de `test_journey_resident.py` lit MEDVIEW
  (4 blocs) au SUCK VENOM quand le disque l'a sur NEOWILD.BLK, comme
  l'édition 140 Ko : le test l'attend exactement, pour cette commande seule.
  De même `test_graphical_topo.py` attend, à chaque ouverture de TOPO, les
  seuls blocs de TOPOGEN (6), lus du répertoire des modules ; MAP ↔ TOPO
  ne relit rien.

## 19. Sprites de site : rondin, rocher, poste des rangers (15 octobre 2026)

Lot 6 ([IMPLEMENTATION.md](IMPLEMENTATION.md), « Sprites de site ») :
trois sprites de l'original de plus (rondin 1 216 octets, rocher 1 158,
poste 2 289), bruts sur NEOWILD.BLK, lus dans la fenêtre SIM. Mesures :
`build/wild.map`, `build/layout.json`, `build/layout-140.json`.

| Changement | Zones |
|---|---|
| Socle : `scene_asset` 33-35, détournés par `overlay_load` (`cmp`/`bcs`, 4 octets) vers `site_load` (10 octets : PROJECT, puis `module_site_load`) | WILDGAME +14 |
| Couleurs : `dhgr_frame` donne l'emplacement 6 aux sites (+6), `dhgr_site` (4 octets, après les six emplacements de `dhgr_assets`, hors des tables réécrites par les paquets) | WILDGAME +10 |
| `summary_refresh` ne recharge pas un sprite de site (il n'est pas en `$5800`) | WILDGAME +4 |
| `env_day`, `env_hour`, `thermal` (relais de la simulation) passent de WILDGAME en TEXT pour faire la place | WILDGAME −24, TEXT +24 |
| Page du sprite : les quatre octets `$58` de `sprite_column` (`sprite_page0..3`) sont réécrits par `project_commit` (`$58` ou `$96`) | 0 |
| Entrée de répertoire du sprite : l'entrée de travail TB_FETCH (29) de `text_fetch`, remplie puis remise par PROJECT (banque, pages) ; `MOD_COUNT` reste 33 | RESIDENT 0 |
| PROJECT : poste (local et panneau), trois candidats, `cabin_asset`, `module_site_load`, tables (largeurs, bases, blocs, têtes de 8 octets, couleurs) | PROJECT 1 373 → 1 662 octets (386 libres dans sa fenêtre) |
| Cabane fixe des cartes générées en rondin ou rocher : `tools/mkmap.py` écrit `MAP+16` = 1 ou 2 (niveau de sa case ≥ 96), `cabin_asset` ne teste plus `MAP+37` (−8 octets) ; la hutte (`cabin.bin`, entrée 9) quitte le stock jusqu'à MAKE HUT (TODO lot 3) | stock −704 octets (LZ), les deux éditions ; résident 0 |
| TRAVEL : rondin ou rocher à la découverte (`level_here`, seuil 96) | TRAVEL 2 039 → 2 046 (2 libres) |

Chaque octet résident ajouté (28) vient des 24 octets de relais déplacés
en TEXT et de 4 des 10 octets libres de WILDGAME.

### 19.1 RAM principale résidente, octets libres

| Zone | avant (§ 18.1, puis feu § 17.4) | après |
|---|---:|---:|
| TEXT `$0A00-$0FFF` | 26 | **2** |
| WILDLO `$1000-$1FFF` | 4 | 4 |
| WILDGAME `$4000-$577F` | 10 | **6** |
| WILDERNESS `$6000-$6FFF` | 18 | 18 |
| RESIDENT `$B600-$B9FF` | 5 | 5 |
| MENUSWAP / MENUCODE / HICODE | 9 / 15 / 3 | 9 / 15 / 3 |
| SIM sous `$B500` | 102 | 102 |

### 19.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc avant → avec les sites | 1 463 → 1 155 (PROJECT, brut : +297) | 1 382 → 1 074 |
| … puis sans la hutte (entrée 9, 704 octets LZ ; PROJECT −8) | **1 859** | **1 778** |
| NEOWILD.BLK | + rondin 3, rocher 3, poste 5 blocs | idem |
| Volume | 338 → 349 → **347** blocs sur 1 600 | 261 → 273 → **272** blocs sur 280 (8 libres) |

### 19.3 Temps

Lecture du sprite à sa première vue (cycles émulés, de `do_command` à
`idle`, même vue avec et sans lecture, disque de test de la Sierra) :

| Sprite | XL (SmartPort) | 140 Ko (Disk II émulé) |
|---|---:|---:|
| Poste (5 blocs) | 43 400 cycles (**0,04 s**) | 1 246 000 cycles (**1,25 s**) |
| Rondin, rocher (3 blocs) | ≈ 0,03 s | ≈ 0,75 s (estimé au prorata) |

Une vue complète coûte ≈ 5 millions de cycles. La lecture n'a lieu qu'à la
première vue qui montre le site, puis après une commande qui a repris la
fenêtre SIM (simulation, STATUS, TOPO, feu, sauvegarde) ; jamais au
retour d'un écran (`test_screen_returns`), ni d'une vue à l'autre tant que
le sprite est dans la fenêtre (`test_projection` `outpost`,
`test_sites` `native_shelter` comptent les READ_BLOCK). Le trajet crash →
rangers en lit le poste près du but : `test_journey_resident` et
`test_geo_resident` admettent, par commande, zéro lecture ou exactement les
blocs du sprite de site que montre la vue (15 sur le trajet de
`test_journey_resident` : chaque WALK près du but recharge la simulation).
`layout.json` donne les octets que le disque écrit dans PROJECT
(`patches`, `build_disk.module_image`), et `disk.sites` les blocs.

### 19.4 Contraintes nouvelles

- La fenêtre SIM sert aussi aux sprites de site pendant la préparation
  d'une vue : aucun code de la simulation ne doit être sur la pile quand
  une vue, un tour ou `summary_refresh` se prépare (déjà vrai pour les
  étoiles). Les blocs entiers du poste vont jusqu'à `$9FFF` : les tampons
  du feu (`$A000`) et GRID (`$A300`) restent intacts.
- Toute image placée en `$9600` commence en `$9600` et ne doit pas
  commencer comme un sprite de site (`build_disk.site_project` le vérifie
  pour les modules de la fenêtre, NEOWILD.SAV, NEOWILD.END) : c'est ce qui
  dit à `module_site_load` que le sprite est encore là.
- L'entrée 29 du répertoire (TB_FETCH) sert à deux : `text_fetch` ne réécrit
  que ses octets 1-3 et 5-6 ; PROJECT remet l'octet de banque (celui de
  l'entrée 28) et le nombre de pages (0) après sa lecture.
- TEXT n'a plus que 2 octets, WILDGAME 6 : le prochain lot doit libérer de la
  place ou vivre dans un module.

## 20. Lot 3, étape 1 : recettes de MAKE (15 octobre 2026)

Le lot ([CRAFT.md](CRAFT.md) § 8) porte MAKE et USE des abris, de la tente,
des armes, de l'attelle, de la visière et de la boue (A1, A2), et la
protection d'abri × 0,1 (D4). Aucune récupération : le code est un module
de NEOWILD.BLK sur l'entrée de répertoire libre depuis le départ de la
hutte (9), la porte vit dans CAMP (déjà chargé par MAKE et USE), l'état
dans les 13 octets restants de LOWPAGE. Mesures : `build/wild.map`,
`build/layout.json`, `build/layout-140.json` ; avant = § 19 (puis la mesure
des modules de l'arbre avant leurs changements).

| Changement | Zones |
|---|---|
| Module CRAFT (`src/craft.s`, entrée 9 : `MOD_COUNT` inchangé) : aiguillage de T05/S00 `$551E`, T10/S00 (abris, armes, attelle, visière, boue, HIDE), USE des abris, de la tente, des armes ; textes originaux | NEOWILD.BLK, 1 645 octets, 4 blocs, lu en `$9600` ; stock 0 |
| `camp_craft` : contexte (`camp_class`, ligne de neige), `sim_fetch`, effort (`cr_eff`, 0,023 à `$5C5C`), `camp_done`, `show_view` après USE d'un abri ; renvois de `camp_make` et de l'USE de 9, 89-91, 95-97 | CAMP 1 620 → 1 757 (+137) |
| `craft_state` : `cr_b1` (3), `cr_gx/cr_gy` (2), `cr_sx/cr_sy` (6) | LOWPAGE `$03C3-$03CD` : 13 → **2** libres |
| `sv_ranges` + `craft_state` | SAVEMOD (disque) ; NEOWILD.Sn 1 716 → 1 727 octets, 5 blocs |
| ENTER, EXIT des abris fabriqués et de la tente ; `site_specific` réécrit | SITES 1 679 → 1 802 (+123) ; banque de textes : texte plus court |
| INVENTORY : BOW, SPEAR, CLUB, SPLINT, HUT, IGLOO, TRENCH | STATUS 6 128 → 6 273 (+145) |
| `fr_means` (arc 20, lance 19, gourdin 17) ; p = 0 pour le gourdin (`DIV10` perd le signe) | FORAGE 5 822 → 5 867 (+45) |
| BOW, SPEAR, CLUB plus en usage quand le temps passe ; igloo à 35 °F | SIM 7 834 → 7 862 (+28) : 102 → **74** sous `$B500` |
| D4 : risque × 0,1 dans un abri, plus de couverture ni de départ automatique | OUTDOOR 1 411 → 1 417 (+6) |
| `care_splint` : l'attelle au sol d'une autre case n'est pas là | MEDVIEW 1 604 → 1 624 (+20) |

### 20.1 RAM principale résidente, octets libres

Inchangée hors LOWPAGE : TEXT 2, WILDLO 4, WILDGAME 6, WILDERNESS 18,
RESIDENT 5, MENUSWAP 9, MENUCODE 15, HICODE 3 ; LOWPAGE 13 → **2** ; SIM 74
sous `$B500`.

### 20.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc (§ 19.2) → après | 1 859 → **1 599** | 1 778 → **1 389** |
| NEOWILD.BLK | + CRAFT (4 blocs) | + CRAFT (4 blocs) |
| Volume | 347 → **352** blocs sur 1 600 | 272 → **276** blocs sur 280 (4 libres) |

Le stock perd surtout STATUS et SITES (CAMP est sur NEOWILD.BLK sur XL,
LZ dans le stock sur 140 Ko).

### 20.3 Temps

Une commande MAKE ou USE d'abri, de tente ou d'arme lit CRAFT (4 blocs) :
≈ 0,03 s sur XL (8 568 cycles par bloc, § 16.4), ≈ 0,3 s sur le Disk II
émulé (au prorata des 12 blocs de FORAGE : 0,89 s dans `test_editions.py`). MAKE FIRE, STICKS,
WATER, MATCHES, GLASS, FUEL et les USE du lot 2 n'y touchent pas.

### 20.4 Contraintes nouvelles

- L'entrée 9 n'est plus libre : la hutte de MAKE HUT reviendra en sprite de
  site (`build_disk.SITE_SPRITES`), pas en module de répertoire.
- LOWPAGE n'a plus que 2 octets ; l'édition de 140 Ko 4 blocs : les sprites
  des abris (étape 3, ≈ 8 blocs) n'y tiennent pas sans place reprise.
- CRAFT tourne dans la fenêtre SIM pendant que CAMP reste en `$5800` : il
  appelle CAMP (`cr_class`, `cr_snow`, `cr_eff`, `cr_msg`, `cr_view` y
  vivent) et le résident, jamais SIM ni `load_totals` (comme FORAGE).

## 21. Lot 3, étape 3 : sprites des abris fabriqués (15 octobre 2026)

Les quatre abris de MAKE et USE TENT (tente 969 octets, hutte `cabin.bin`
1 133, igloo 859, tranchée 403) deviennent des sprites de site du § 19 sur
NeoWildernessXL seul ([CRAFT.md](CRAFT.md) § 8.4). Aucune récupération :
rien de résident, les octets de plus vont dans une **queue de PROJECT**
que `build_disk` coupe sur l'édition de 140 Ko. Mesures : `build/wild.map`,
`build/layout.json`, `build/layout-140.json` ; avant = § 20.

| Changement | Zones |
|---|---|
| Sprites de site 36-39 (`SITE_SPRITES` + `SHELTER_SPRITES`), bruts sur NEOWILD.BLK après le poste | XL : + 2 + 3 + 2 + 1 = 8 blocs ; 140 Ko : 0 (`EDITIONS` `shelters`) |
| PROJECT, partie commune : sept candidats (`SITE_COUNT`), ordre local de l'original (`local_order`, boucle), `project_ahead`, `site_blocks` sur un octet (0 : sprite absent du disque), tables à sept entrées (largeur et base de la tranchée de part et d'autre de `proj_1_256`, `proj_index` 29), `site_heads` sur 4 octets | 1 667 → 1 667 octets (code resserré) |
| PROJECT, queue (`project_tail` … `project_end`) : têtes des quatre abris, `project_shelter` (case, tente au sol hors de l'épave, borne entière avant le calcul flottant) | XL : + 120 octets (1 787, 261 libres dans la fenêtre) ; 140 Ko : coupée |
| Cache de `scene_prepare` oublié par MAKE d'un abri et `cr_ground_item` (CRAFT), DROP et GET (ITEMS) | CRAFT 1 645 → 1 653 (NEOWILD.BLK, 4 blocs) ; ITEMS 1 652 → 1 660 (stock LZ) |
| `tools/dhgr_palette.py` SPRITES : `tent`, `igloo`, `trench` (`cabin` déjà là) | 0 |

`site_project` vérifie pour chaque site la largeur, la ligne de base et les
couleurs écrites dans PROJECT, met le numéro de bloc (< 256) ou 0, et coupe
l'image à `project_tail` sans abris ; `module_image` lit `length` (l'image
coupée). Une seule table (`site_heads`) chevauche la coupure : les têtes
des trois sites restent avant `project_tail`, celles des abris viennent
après ; `project_site` teste `site_blocks` avant de sauter dans la queue.

### 21.1 RAM principale résidente, octets libres

Inchangée : TEXT 2, WILDLO 4, WILDGAME 6, WILDERNESS 18, RESIDENT 5,
MENUSWAP 9, MENUCODE 15, HICODE 3, LOWPAGE 2, banque 2 principale 24 ; SIM
74 sous `$B500`.

### 21.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc (§ 20.2) → après | 1 599 → **1 469** (PROJECT + 120, ITEMS + 8) | 1 389 → **1 379** (ITEMS + 8) |
| NEOWILD.BLK | + tente 2, hutte 3, igloo 2, tranchée 1 blocs | inchangé |
| Volume | 352 → **360** blocs sur 1 600 | **276** blocs sur 280 (4 libres) |
| NEOWILD.DAT | 107 297 octets | 70 646 octets : **10 octets** avant un 140e bloc |

Les disques de comparaison des tests (`build_disk --map`) portent les
abris comme XL (278 blocs avec la carte native de `test_sites.py`).

### 21.3 Temps

Lecture d'un abri à sa première vue : 1 à 3 blocs, ≈ 0,01 à 0,03 s sur XL
(8 568 cycles par bloc, § 16.4) ; aucune sur l'édition de 140 Ko. Coût de
VIEW (cycles émulés, disque de comparaison, `module_project` compris) :

| Cas | VIEW | dont `module_project` |
|---|---:|---:|
| Aucun site à moins de 8 cases | 3 541 384 | 2 489 |
| Quatre abris à plus de 8 cases | 3 541 935 (+ 0,02 %) | 2 990 |
| Rondin en panneau, sans abri | 2 677 855 | 182 897 |
| Même vue, une hutte plus loin que le rondin | 2 678 085 (+ 0,01 %) | 183 127 |
| Même vue, quatre abris proches (la tranchée à moins d'une case du rondin) | 2 732 153 (+ 2,0 %) | 237 145 |
| Même vue, la hutte plus proche que le rondin (choisie) | 2 671 102 | 278 101 |

Un abri plus loin d'une case que le meilleur panneau ne coûte que sa borne
entière ; un abri à moins d'une case de lui, ou choisi, coûte la projection
flottante d'un site (≈ 54 000 cycles), comme l'épave, le rondin ou le poste.

### 21.4 Contraintes nouvelles

- PROJECT finit par sa queue : tout ce qui sert à l'édition de 140 Ko doit
  rester avant `project_tail` (`site_project` vérifie que l'image finit à
  `project_end`) ; la queue n'est atteinte que si `site_blocks` ≠ 0.
- NEOWILD.DAT de l'édition de 140 Ko est à 10 octets d'un bloc de plus :
  la prochaine croissance du stock de cette édition prend un des 4 blocs
  libres.

## 22. Lot 3, reste de l'étape 1 : second jeu, pierre, armes, igloo (15 octobre 2026)

Le reste de l'étape 1 ([CRAFT.md](CRAFT.md) § 8.5) : GET, PACK, CARRY,
DROP, REMOVE et WEAR de l'arc, de la lance, du gourdin, de la pierre et de
l'attelle ; la pierre de toute case de terre ; une case par objet laissé au
sol ; les armes contre les animaux ; l'igloo des dangers. Une récupération
dans le module MEDICAL, une prise dans WILDERNESS, documentées ci-dessous ;
le reste vit dans des modules. Mesures : `build/wild.map`,
`build/layout.json`, `build/layout-140.json` ; avant = § 21.

| Changement | Zones |
|---|---|
| `craft_state` : `cr_b1` + la pierre (4), `splint_place` (venue de `care_state`, contiguë : `cr_b1` + 4), `cr_still` (1) remplace `cr_gx/cr_gy` (2), `cr_sx/cr_sy` (6) | LOWPAGE `$03C3-$03CE` : 11 → 12 octets, 2 → **1** libre ; `care_state` (WILDLO) − 1 |
| `craft_cells` : `cr_cx/cr_cy`, la case de l'arc, de la lance, de l'attelle (segment DATA) | **WILDERNESS 18 → 12** (prise documentée : LOWPAGE est plein) |
| `forage_here` : `sta cr_still` quand le joueur change de case | WILDLO + 3 (− 1 de `care_state`) : 4 → **2** |
| `sv_ranges` + `craft_cells` | SAVEMOD 1 242 → 1 246 ; NEOWILD.Sn 1 727 → 1 733 octets (5 blocs) |
| CRAFT : `cr_items` (la transaction), `cr_where`, `cr_put`, `cr_here` (gourdin perdu, pierre posée par `cell_native`), MAKE ROCK, USE ROCK, sélecteur 3 de l'attelle | NEOWILD.BLK : 1 653 → 1 855 octets, **4 blocs** (fenêtre `$9600-$9FFF` : 705 libres) |
| `item_noun` (ITEMS) : 89 à 93 → `sim_fetch` de CRAFT, `CRAFT_RUN` | ITEMS 1 660 → 1 683 (stock LZ) |
| `inventory_settle`, `inventory_craft` (cases propres, ROCK), nom ROCK | STATUS 6 273 → 6 344 (stock LZ) |
| `outdoor_weapon` (premier moyen en usage, drapeau effacé), `out_means_injury/success` (5 moyens × 4 espèces) | OUTDOOR 1 417 → 1 541 (stock LZ) ; paquets de région : `fauna_reactions` 44 → 76 octets |
| `hz_air` : 35 °F dans l'igloo (+ 6) ; `hz_since_lo/hi` supprimées, `module_hazards` lit `injury_since_lo/hi` du même module (− 30) | fenêtre MEDICAL (MEDICAL + HAZARDS) : 1 → **25** libres |
| USE de 92 par CAMP (`cpx #93`), USE SPLINT lit `cr_cx/cr_cy` + 2 (MEDVIEW), texte `out_weapon` raccourci | 0 |

**Récupération** : la table `hz_since_lo/hi` (30 octets) de HAZARDS
doublait `injury_since_lo/hi` de MEDICAL, liés dans la même image
(`wildmed.bin`) et toujours chargés ensemble ; HAZARDS lit désormais
celle de MEDICAL. **Prise** : 6 octets d'état résident dans WILDERNESS
(`craft_cells`, segment DATA lié après RODATA), sauvés par une entrée de
plus de `sv_ranges`.

### 22.1 RAM principale résidente, octets libres

| Zone | avant (§ 21.1) | après |
|---|---:|---:|
| TEXT `$0A00-$0FFF` | 2 | 2 |
| WILDLO `$1000-$1FFF` | 4 | **2** |
| WILDGAME `$4000-$577F` | 6 | 6 |
| WILDERNESS `$6000-$6FFF` | 18 | **12** |
| RESIDENT `$B600-$B9FF` | 5 | 5 |
| LOWPAGE `$0200-$03CF` | 2 | **1** |
| MENUSWAP / MENUCODE / HICODE | 9 / 15 / 3 | 9 / 15 / 3 |
| banque 2 principale | 24 | 24 |
| SIM sous `$B500` | 74 | 74 |

### 22.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc (`aux_trunk_free` − zone des sprites) | 1 469 → **1 277** | 1 379 → **1 187** |
| NEOWILD.DAT | 107 297 → 107 652 octets | 70 646 → 70 916 octets, 139 → **140** blocs : 252 octets avant un 141e |
| NEOWILD.BLK | CRAFT toujours 4 blocs | idem |
| Volume | 360 → **361** blocs sur 1 600 | 276 → **277** blocs sur 280 (**3** libres) |

Le stock grandit d'ITEMS, STATUS et OUTDOOR (+ 218 octets bruts, − 24
dans MEDICAL) ; le bloc annoncé au § 21.4 pour NEOWILD.DAT de 140 Ko est
pris.

### 22.3 Temps

GET, PACK, CARRY, DROP, REMOVE et WEAR d'un objet 89 à 93 lisent CRAFT
(4 blocs) comme MAKE : ≈ 0,03 s sur XL, ≈ 0,3 s sur le Disk II émulé
(§ 20.3) ; les autres objets n'y touchent pas. `cr_here` et
`inventory_settle` ne font qu'une requête de case (`cell_native`) après un
changement de case. ATTACK : le choix du moyen ajoute moins de 100 cycles.

### 22.4 Contraintes nouvelles

- `splint_place` est `cr_b1` + 4 : `cr_where`, `cr_put` et
  `inventory_craft` indexent les cinq objets 89 à 93 d'un seul tableau ;
  ne pas les séparer.
- `cr_still` n'est remis à 0 que par `forage_here`, appelé à chaque pas
  de la marche et de la nage : tout autre moyen de changer `px/py` (tests,
  futur radeau du lot 5) doit appeler `forage_here` pour que le gourdin se
  perde et que la pierre change de case.
- CRAFT tourne aussi depuis ITEMS (`cr_items`) : ce chemin n'appelle ni
  CAMP (`camp_said`, `cr_say`, `cr_class` y vivent) ni `load_totals` ; il
  écrit ses messages par `message`.
- `fauna_reactions` (OUTDOOR) a maintenant 76 octets ; `tools/build_disk.py`
  `fauna_patches` et l'ordre des tables doivent rester accordés
  (`out_means_injury` puis `out_means_success`, moyens 17 à 21).
- LOWPAGE n'a plus qu'un octet, WILDLO 2 ; l'édition de 140 Ko 3 blocs.

## 23. Lot 3, étape 2 : page CRAFT, second jeu dans la grille (15 octobre 2026)

La page CRAFT, « livre de recettes » des MAKE de l'original, et l'arc, la
lance, le gourdin, la pierre et l'attelle dans les listes GET, DROP, USE
et la file de KILL de la grille, dans l'indice ITEMS du panneau
([CRAFT.md](CRAFT.md) § 8.6). Aucun octet résident pour la page : son code
et ses recettes sont la queue du module CRAFT (NEOWILD.BLK) ; une
récupération dans MENUSWAP et MENUCODE pour la grille, une dans SUMMARY
pour le panneau. Mesures : `build/wild.map`, `build/layout.json`,
`build/layout-140.json` ; avant = § 22.

| Changement | Zones |
|---|---|
| Page CRAFT (`craft_page` … `craft_end`) : contexte, recettes, ingrédients, focus, touches, `MAKE x` tapé ; `cr_water` partagé avec `cr_here` | CRAFT 1 855 → 2 815 octets (recettes 1 858, page 957) ; NEOWILD.BLK 4 → **6 blocs**, fenêtre `$9600-$A1FF` (CRAFTM `$0C00`) |
| Longueur de l'entrée 9 : `build_disk` y écrit celle des recettes seules (`craft_page` − `$9600`) : MAKE, USE et la transaction lisent toujours 4 blocs ; `pg_craft` y écrit le module entier avant `sim_fetch`, `craft_page` la remet | RESIDENT 0 |
| `pg_craft` (onglets, longueur, adresse de retour empilée, `sim_fetch`) ; septième onglet, tables, lettre R ; un espace de moins entre les onglets | STATUS 6 344 → 6 380 (stock LZ) |
| `member` : 89 à 93 (sur-ensemble des listes : place de `cr_b1`, pierre absente sur terre) | MENUSWAP + 23 ; `append_space` (− 14) passe dans GRID, son seul appelant : **9 → 0** libres |
| `cr_rock_land` (+ 14), `use_items` + 2 octets (USE de 89 à 93), `filt_hi` de USE 74 → 94 ; `mn_idx` 32 → 27 octets (une case au plus par entrée de `verb_table`, 27) | MENUCODE **15 → 4** |
| GRID : `gr_where` (place exacte), `gr_ok` pour 89 à 93, noms du second jeu, `GET x`, `gr_r_use`, KILL : `USE BOW`, `USE SPEAR` (étapes S_BOW, S_SPEAR, contrôle 15), rien quand une arme est en usage ; `append_space` | GRID 2 456 → 2 676 (stock brut, fenêtre `$A300-$AFFF` : 652 libres) |
| SUMMARY : indice ITEMS de l'arc, la lance, l'attelle, le gourdin (+ 40) ; table des alertes en décalages d'un octet (− 10), deux `lda #0` et un `jmp` en moins (− 6) | fenêtre `$5800` : **25 → 1** libre (stock brut) |

**Récupérations** : dans MENUSWAP, `append_space` (14 octets) n'était
appelé que par GRID ; dans MENUCODE, `mn_idx` réservait 32 cases pour 27
entrées de `verb_table` au plus (5) ; dans SUMMARY, la table des poids forts
des alertes (14 octets) devient un décalage depuis `ui_hunger_worse`
(chaînes de moins de 256 octets), plus deux chargements et un saut
redondants.

### 23.1 RAM principale résidente, octets libres

| Zone | avant (§ 22.1) | après |
|---|---:|---:|
| TEXT `$0A00-$0FFF` | 2 | 2 |
| WILDLO `$1000-$1FFF` | 2 | 2 |
| WILDGAME `$4000-$577F` | 6 | 6 |
| WILDERNESS `$6000-$6FFF` | 12 | 12 |
| RESIDENT `$B600-$B9FF` | 5 | 5 |
| LOWPAGE `$0200-$03CF` | 1 | 1 |
| MENUSWAP / MENUCODE / HICODE | 9 / 15 / 3 | **0 / 4** / 3 |
| banque 2 principale | 24 | 24 |
| SIM sous `$B500` | 74 | 74 |

### 23.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc (`aux_trunk_free` − zone des sprites) | 1 277 → **990** | 1 187 → **900** |
| NEOWILD.BLK | CRAFT 4 → 6 blocs | idem |
| Volume | 361 → **363** blocs sur 1 600 | 277 → **279** blocs sur 280 (**1** libre) |
| NEOWILD.DAT | 107 652 → 107 888 octets | 70 916 → 70 704 octets, 140 blocs : 464 octets avant un 141e |

Le stock grandit de GRID (+ 220), SUMMARY (+ 24) et STATUS (LZ) : 287
octets sur les deux éditions.

### 23.3 Temps

MAKE, USE et la transaction du second jeu lisent les 4 blocs des recettes,
comme avant (≈ 0,03 s sur XL, ≈ 0,3 s sur le Disk II émulé). L'ouverture de
la page lit les 6 blocs : ≈ 0,05 s sur XL (8 568 cycles par bloc, § 16.4),
≈ 0,45 s sur le Disk II émulé (au prorata des 12 blocs de FORAGE). Les
déplacements du focus ne lisent rien (dessin différentiel, une écriture par
cellule changée). `test_screen_returns` compte la lecture : CRAFT (9) entre
INVENTORY et HELP dans le cycle, 6 READ_BLOCK.

### 23.4 Contraintes nouvelles

- L'entrée 9 du répertoire n'a pas la longueur de l'image : `build_disk`
  y met `craft_page` − `$9600` et vérifie `craft_end` (`layout.json` :
  `fetch` de l'entrée 9, que lisent `test_boot`, `test_pack_boot`,
  `test_transfers`) ; tout code que MAKE appelle doit rester avant
  `craft_page`, et la page après.
- La page lit CRAFT jusqu'à `$A1FF`, sur les tampons du feu animé
  (`$A000-$A2BB`) : le feu est caché à chaque page (`fire_hide` avant la
  fin de `get_line`) et relu à l'invite suivante ; GRID (`$A300`) reste
  intact.
- MENUSWAP est plein et MENUCODE n'a plus que 4 octets ; SUMMARY 1 dans sa
  fenêtre ; l'édition de 140 Ko n'a plus qu'un bloc libre (les cinq
  parties sauvées sont déjà allouées).
- `member` répond pour 89 à 93 un sur-ensemble : seules les listes de GRID
  (`gr_where`) sont exactes ; un code qui doit savoir si un objet du second
  jeu est là appelle `cr_where` (CRAFT) ou `gr_where` (GRID).

## 24. Le feu brûle jusqu'à DOUSE (15 octobre 2026)

Décision du 15 octobre 2026 : la gestion du feu suit l'original, qui le
laisse brûler jusqu'à DOUSE ([CAMP.md](CAMP.md) § 2.1 et § 8 ; sonde
`LONG_FIRE` de `re_camp_probe.py`). La durée de vie du § 17.4 est retirée :
`FIRE_LIFE`, `fire_life`, `fire_clock`, le message « YOUR FIRE HAS BURNED
OUT. » et les deux stades de fin (petites flammes, braises). Le reste du
feu animé (images, place, case, cadence) est inchangé. Mesures :
`build/wild.map`, `build/layout.json`, `build/layout-140.json` ; avant =
§ 23.

| Retrait | Zones |
|---|---|
| `fire_life` (GDATA, plage sauvée) | WILDGAME −1 ; état sauvé 1 701 → 1 700 octets (`NEOWILD.Sn` 1 733 → 1 732, toujours un bloc) |
| `lda #FIRE_LIFE` / `sta fire_life` de `fire_light` | WILDGAME −5 |
| `fire_clock` (67) et son `JSR` en tête de `module_health` | SIM −70 (ENVIRON) |
| quatrième nouvelle de `forage_news` (chaîne 26, deux pointeurs) | ALERT −28 |
| module FIRE : couche des petites flammes (192), masques des stades 1 et 2 (32), choix du stade, couches 3 et 4 (le lit lu comme une seule couche de flammes avec le reste) | FIRE 1 993 → **1 683** octets (−310), toujours 4 blocs de NEOWILD.BLK |

### 24.1 RAM principale résidente, octets libres

| Zone | avant (§ 23.1) | après |
|---|---:|---:|
| TEXT, WILDLO, WILDERNESS, RESIDENT, LOWPAGE | 2, 2, 12, 5, 1 | inchangés |
| WILDGAME `$4000-$577F` | 6 | **12** |
| MENUSWAP / MENUCODE / HICODE | 0 / 4 / 3 | inchangés (`fire_tick`, `fire_hide` intacts) |
| banque 2 principale | 24 | 24 |
| SIM sous `$B500` | 74 | **144** |

Fenêtres à la demande : ALERT 1 730 → 1 702 octets (`$5800`), FIRE
`$9600-$9C92` (fond et variables inchangés en `$A000-$A2BB`).

### 24.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc (`aux_trunk_free` − zone des sprites) | 990 → **1 091** | 900 → **1 002** |
| NEOWILD.DAT | 107 888 → 107 852 octets | 70 704 → 70 605 octets, 140 → **139 blocs** : 51 octets avant un 140e |
| Volume | 363 blocs sur 1 600 | 279 → **278** blocs sur 280 (**2** libres) |

Le stock gagne SIM (−70, brut) et ALERT (LZ, −29) sur les deux éditions.
NEOWILD.BLK garde sa taille : FIRE reste au-dessus de 1 536 octets (trois
blocs), il lui faudrait encore 147 octets de moins (pistes : CAMP.md § 8) ;
165 depuis le feu remonté de trois rangées (1 701 octets, `fm_setrow`
général, CAMP.md § 8 **Hauteur**).

### 24.3 Temps

Chaque mise à jour de santé économise `fire_clock` (quelques dizaines de
cycles). L'apparition du feu lit toujours quatre blocs ; une image coûte
comme avant les flammes pleines (61 000 à 75 000 cycles).

### 24.4 Contraintes nouvelles

- Aucune : `fire_on` seul dit si le feu brûle (comme B1[FIRE] de
  l'original) ; les tests qui le posent n'ont plus de cas « sans horloge ».
- Une partie sauvée avant ce changement est refusée comme toute partie
  d'une autre construction (`GAME n WAS SAVED BY ANOTHER VERSION.`,
  [SAVE.md](SAVE.md)).

## 25. Lot 3, étape 2 : la page CRAFT lisible (15 octobre 2026)

Deuxième version de la page CRAFT, maquette approuvée par l'utilisateur
([CRAFT.md](CRAFT.md) § 8.6) : trois groupes, état en MouseText, temps de
chaque recette, panneau de la recette choisie (contrôles, effet, temps,
ce qui ralentit), rangée 23 qui dit ce que tape RETURN. Aucun octet
résident : tout est dans le module CRAFT de NEOWILD.BLK. Mesures :
`build/wild.map`, `build/layout.json`, `build/layout-140.json` ; avant =
§ 24.

| Changement | Zones |
|---|---|
| `cr_minutes` : le temps de MAKE (formules de la ROM, ordre des opérations inchangé) devient une routine, appelée par MAKE une fois ses contrôles passés et par la page pour chaque recette | recettes 1 858 → **1 878** octets : MAKE, USE et la transaction lisent toujours **4 blocs** (170 octets libres avant un cinquième) |
| Page : contexte, états et temps calculés une fois à l'arrivée, moitié gauche (groupes, `>`, état, temps), trait, panneau, légende, rangée 23, touches ; `ALTCHARSET` levé à l'arrivée, baissé à chaque sortie | page 957 → **2 209** octets ; CRAFT 2 815 → **4 087** octets, NEOWILD.BLK 6 → **8 blocs** (9 octets libres dans le huitième) ; fenêtre CRAFTM `$9600-$A5FF` (`$1000`) |
| Octets de travail de la page (12 variables, états, minutes : 42 octets) | après `craft_end`, hors image (`$A5F7-$A620`, fenêtre de GRID) |
| `pg_craft` (STATUS) : deux constantes (longueur du module) | stock LZ de STATUS : +5 octets (140 Ko), +6 (XL) |

### 25.1 RAM principale résidente, octets libres

Inchangée (§ 24.1) : TEXT 2, WILDLO 2, WILDGAME 12, WILDERNESS 12,
RESIDENT 5, LOWPAGE 1, MENUSWAP / MENUCODE / HICODE 0 / 4 / 3, banque 2
principale 24, SIM sous `$B500` 144.

### 25.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc (`aux_trunk_free` − zone des sprites) | 1 091 → **1 087** | 1 002 → **998** |
| NEOWILD.BLK | CRAFT 6 → 8 blocs | idem |
| Volume | 363 → **365** blocs sur 1 600 | 278 → **280** blocs sur 280 (**0** libre) |
| NEOWILD.DAT | 107 852 → 107 858 octets | 70 605 → 70 610 octets, 139 blocs : 46 octets avant un 140e |

L'édition de 140 Ko est pleine : un bloc de plus pour CRAFT, ou un octet
qui fait passer NEOWILD.DAT à 140 blocs, ne tient plus sans place rendue
ailleurs. La page ne pouvait pas tenir dans 7 blocs avec les lignes
d'effet (2 209 octets de page pour 1 706 disponibles).

### 25.3 Temps

L'ouverture de la page lit 8 blocs au lieu de 6 : ≈ 0,07 s sur XL
(8 568 cycles par bloc, § 16.4), ≈ 0,6 s sur le Disk II émulé (au prorata
des 12 blocs de FORAGE), puis dix `cr_minutes` (cinq racines carrées
Applesoft) avant le premier dessin. Un déplacement du curseur ne recalcule
rien : il redessine les deux moitiés en différentiel, seules les cellules
qui changent sont écrites (13 de la rangée d'onglets à HUT, mesuré par
`storewatch` dans `test_craft_page.py`). MAKE lit toujours 4 blocs.

### 25.4 Contraintes nouvelles

- La page lit CRAFT jusqu'à `$A5FF` et écrit ses octets de travail
  jusqu'à `$A620` : par-dessus les tampons du feu (caché à chaque page,
  § 23.4) et le début de GRID (`$A300`). GRID est recopié du stock à
  chaque usage (`grid_fetch` : RETURN dans la grille, chaque pas de sa
  file) et aucune liste n'est ouverte quand une page s'ouvre (`level1` à
  l'invite) : rien n'y lit entre-temps. Un code qui supposerait GRID
  présent entre deux commandes devra le recopier.
- `ALTCHARSET` n'est levé que sur la page CRAFT (140 Ko ; sur XL, pour
  toute la partie depuis le § 26) : toute nouvelle sortie de
  la page doit passer par `cp_view` ou la table `cp_go_lo/hi` (qui le
  baissent). Ailleurs, les codes `$40-$5F` restent des majuscules
  clignotantes (jamais écrites par le jeu).
- Tout ce que MAKE appelle reste avant `craft_page` (§ 23.4) :
  `cr_minutes` y est, la page l'appelle ; 170 octets libres dans les
  4 blocs de MAKE, 9 dans les 8 blocs du module.
- 140 Ko : **0 bloc libre** sur le volume.

## 26. Pages en MouseText, sur NeoWildernessXL seul (15 octobre 2026)

Plan de l'utilisateur ([MENUS.md](MENUS.md) § 9) : onglets, boîtes,
jauges, pied de page, grille, rideau et écran du score en MouseText ;
décision du même jour : **l'édition de 140 Ko n'en a pas besoin** et ne
doit pas grandir. Tout est donc sur XL, par des queues d'images et des
octets propres à XL (§ 9.1 de MENUS.md) ; les images liées restent celles
de 140 Ko, et la table de symboles est la même pour les deux disques.
Mesures : `build/wild.map`, `build/layout.json`, `build/layout-140.json` ;
avant = § 25.

| Changement | Zones |
|---|---|
| Queue de STATUS (`STATX`, `src/mt_pages.s`) : onglets, pied de page, boîtes, jauges, page STATUS, MEDICAL, INVENTORY, OPTIONS, MENU | 1 457 octets en `$AF00-$B4B0` ; l'image XL de STATUS (6 380 → 7 857 octets, `$9600-$B4B0`) passe de 5 119 à 5 872 octets dans le stock (LZ), après `XL_ZERO` du code partagé que XL n'exécute plus (`page_top`, `st_at`, `st_heading`, `bar`, `hours_gauge`, les morceaux de `module_status` entre ceux qu'il réutilise) |
| Queue de CRAFT (`CRAFTX`, `$A640`) : le pied de page | 67 octets ; CRAFT XL 4 227 octets, NEOWILD.BLK **8 → 9 blocs** (MAKE en lit toujours 4) |
| Queue de MEDVIEW (`MEDVX`, `$5E80`) : le pied de page des gestes | 26 octets, toujours 4 blocs |
| Queue de NEOWILD.END (`ENDX`, `$A200`) : bande de titre, trait du total, boîte du tableau | 122 octets ; NEOWILD.END XL 3 045 → 3 194 octets, 7 → **8 blocs** |
| Résident XL : `xl_pad` (barres de la grille) et `xl_curtain` (sablier du rideau) copiés sur `page_foot` (`XL_COPIES`) | 38 octets sur les 54 de `page_foot`, que XL n'appelle plus : **0 octet résident de plus** |
| Octets changés (`XLPATCH`, 200 enregistrements) : chargeur, CRAFT, STATUS, MEDVIEW, END, `wildmenusw.bin` (séparateur, flèches), `wildmenu.bin` (`cell_put`), `wild.bin` (`view_hide`) | 0 |
| Les deux éditions : **bas** sur TOPO ou MAP ouvre les pages du haut (`topo_pages`, demande du 15 octobre 2026) | SITES 1 802 → 1 821 octets (stock, brut) |
| Les deux éditions : TOPO centrée (marges de 14 pixels, `TP_SX`) ; **haut** sur la rangée d'onglets ouvre TOPO (`page_keys`, `cp_key`) | TOPOGEN 2 987 → 2 997 (six blocs, 75 octets avant `TOPOBSS` à `$A200`), STATUS 6 380 → 6 384 (LZ 5 119 → 5 122 ; 16 octets sous STATX), CRAFT 4 087 → 4 089 (7 libres dans `$9600-$A5FF`) ; XL : images à longueur fixe, stock inchangé |

### 26.1 RAM principale résidente, octets libres

Inchangée sur les deux éditions (§ 25.1) : TEXT 2, WILDLO 2, WILDGAME 12,
WILDERNESS 12, RESIDENT 5, LOWPAGE 1, MENUSWAP / MENUCODE / HICODE
0 / 4 / 3, banque 2 principale 24, SIM sous `$B500` 144. Sur XL, 16 des
54 octets de `page_foot` restent libres (code mort de XL, § 26.4).

### 26.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc (`aux_trunk_free` − zone des sprites) | 1 087 → **315** (STATUS + 753, SITES + 19) | 998 → **979** (SITES + 19) |
| NEOWILD.DAT | 107 858 → 108 615 octets, 212 → 214 blocs | 70 610 → **70 630** octets, 139 blocs : 26 octets avant un 140e |
| NEOWILD.BLK | CRAFT 8 → 9 blocs | inchangé |
| NEOWILD.END | 7 → 8 blocs | inchangé |
| Volume | 365 → **369** blocs sur 1 600 | **280** blocs sur 280, cinq parties sauvées |

Après la TOPO centrée et haut → TOPO (dernière ligne du tableau du § 26) :
140 Ko, NEOWILD.DAT 70 632 octets (24 avant un 140e bloc), place du tronc
976, toujours 280 blocs ; XL inchangé (108 615 octets, 369 blocs, 315).

L'image de 140 Ko est identique octet pour octet à celle d'avant ces
travaux, hormis les 19 octets de SITES (vérifié par `cmp` sur le disque de
référence gardé pendant les travaux).

### 26.3 Temps

Une page du haut de XL décode 753 octets LZ de plus en ouvrant STATUS
(≈ 0,04 s à 50 cycles par octet) ; les déplacements du focus restent
différentiels (une écriture par cellule changée, `test_focus.py`,
`test_transitions.py`). La page CRAFT de XL lit 9 blocs au lieu de 8
(≈ 0,01 s de plus). La grille ajoute moins de 30 cycles par case.

### 26.4 Contraintes nouvelles

- Le stock de XL n'a plus que **315 octets** de place de tronc : la
  prochaine croissance de XL doit lire depuis NEOWILD.BLK ou rendre de la
  place (les pistes du § 22 valent pour XL aussi).
- La queue de STATUS court sur `$B000-$B5FF` (l'image de la grille) : le
  code des pages de XL ne doit appeler aucune routine de `MENUSWAP` ; une
  commande tapée par une page passe par `do_command`, dont aucun chemin
  n'y touche avant le `get_line` suivant (`forage_wants` n'appelle
  `ctx_ok` que pour un KILL tapé).
- Les morceaux de `module_status` (`XL_ENTRY` … `XL_JMP`) et les octets
  mis à zéro sur XL (`XL_ZERO`) suivent le code de la page de 140 Ko : un
  changement de cette page doit garder ses bornes (`@c_*`, `@y*`), sinon
  XL saute au mauvais endroit. `test_reference_state.py` vérifie que
  STATUS laisse `g0` et `g1` comme la page de 140 Ko.
- `page_foot` n'est plus du code sur XL : un futur appel de XL doit viser
  `page_foot_x`.
- Les disques de comparaison (`--map`) gardent les pages sans cadre :
  avec celles de XL, le stock d'un disque de 280 blocs déborde et CAMP
  passe sur NEOWILD.BLK (`--mousetext` pour les essayer).

## 27. L'animal présent toujours visible (15 octobre 2026)

Règle de l'utilisateur : « quand un animal est là, on doit voir son sprite
sauf dans nos abris » ([LOOK_UPDOWN.md](LOOK_UPDOWN.md) § 4, décisions 1 à
7). Les deux éditions. Mesures : `build/wild.map`, `build/layout.json`,
`build/layout-140.json` ; avant = § 26.

| Changement | Zones |
|---|---|
| PROJECT : `module_animal` (case, inclinaison, géométrie face au joueur, couleurs, silhouette de nuit), `animal_fire` (à côté du feu), la boucle de colonnes copiée en `$A000` (26 octets) ; `project_offset` (entrée de `project_center`) ; l'animal retiré des candidats de `module_project` (−31) | 1 787 → 1 967 octets (XL), 1 667 → 1 847 (140 Ko, coupé à `project_tail`) : **+180**, brut dans le stock |
| Résident : `animal_view` (14 octets) et deux appels dans `show_view_scene` (+6) ; `dhgr_sprite_map` (entrée de `dhgr_frame`, 0 octet) ; la clef du cache de scène sans l'animal (`scene_prepare` −21) ; `animal_bearing` (−2) et `scene_cache_animal` (−5) supprimés de GDATA | WILDGAME 12 → **23** libres ; état sauvé 1 732 → 1 725 octets (`NEOWILD.Sn`, toujours 5 blocs) |
| SIM (ENVIRON) : `fauna_accept` ne note plus de relèvement | −12 : 144 → **156** octets sous `$B500` |
| SITES : ENTER de l'abri naturel garde l'animal | −5 (1 821 → 1 816) |
| Paquet de la Sierra Nevada : ses couleurs DHGR (314 octets) et ses quatre correctifs de modules (141 octets) ne sont plus écrits, identiques à ceux du tronc que le chargeur lit toujours d'abord (`tools/build_disk.py`, déjà vérifiés par assertion) | paquet R2 7 059 → **6 668** octets stockés, les deux éditions |

`NEOWILD.DAT` de 140 Ko : 70 632 → **70 365** octets, toujours 139 blocs,
**291 octets** avant un 140e (étaient 24) ; volume 280 / 280 blocs, cinq
parties sauvées. Sans l'allègement du paquet de la Sierra, l'animal seul
débordait d'un bloc (70 756 octets : `build_disk` ne gardait que quatre
parties) ; le module du feu dans `animal_fire` coûte à lui seul 55 octets
stockés. XL : 108 615 → 108 764 octets, 369 blocs sur 1 600.

### 27.1 RAM principale résidente, octets libres

TEXT 2, WILDLO 2, **WILDGAME 23** (12), WILDERNESS 12, RESIDENT 5,
MENUCODE 4, LOWPAGE 1, HICODE 3, banque 2 principale 24, SIM sous `$B500`
**156** (144). Aucune croissance résidente.

### 27.2 Stock et fenêtres

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc (`aux_trunk_free` − zone des sprites) | 315 → **150** | 976 → **811** |
| PROJECT (fenêtre `$5800`, 2 048) | 261 → **81** | 381 → **201** |
| NEOWILD.DAT | 108 764 octets, 369 blocs | 70 365 octets (291 avant un bloc de plus), 280 / 280 blocs |

La boucle de l'animal tourne en `$A000-$A019` (fenêtre SIM) : libre
pendant une vue (le sprite d'un site s'arrête à `$9FFF`, les tampons du feu
ne servent qu'à l'invite, GRID commence en `$A300`).

### 27.3 Temps

Sans animal : `lda animal_kind / beq` (7 cycles) après chaque vue, PROJECT
copié avec 180 octets de plus quand la scène est recalculée (≈ 3 000
cycles) : moins de 0,1 % d'une vue (6,5 millions de cycles à la case de
départ). Avec un animal (l'ours à la case de départ) : VIEW 6,51 → 7,30
millions (+12 %) : PROJECT 30 000, le sprite LZ 42 000, la boucle 740 000
(39 colonnes de sprite, ≈ 19 000 chacune, et 101 colonnes vides) ; une
rotation redessinait toute la vue (≈ 6,8 millions au lieu de 1,2 à 1,5 par
défilement), pour garder l'animal centré : elle défile depuis le § 28.

### 27.4 Contraintes nouvelles

- `scene_drawn` = 3 après une vue avec un animal (`$83` depuis le § 28,
  carte héritée) : `turn_view` redessine (défile) ;
  `sprite_*` et `scene_asset` décrivent alors l'animal, le cache de scène
  est invalidé. `scene_cache_asset` reste l'emplacement principal (le site
  ou le panneau) : `test_journey_resident.py` le lit.
- La boucle copiée en `$A000` suppose la fenêtre SIM libre pendant une
  vue (comme `module_site_load`) ; un module de la fenêtre SIM ne doit
  jamais appeler `show_view` en restant sur la pile.
- `animal_fire` suppose une largeur d'animal d'au plus 80 colonnes (gauche
  ≥ 30 ; la plus large, le crocodile, en a 72 : `scene_ref.animal_geometry`
  le vérifie) ; le fond gardé, au plus 72 (§ 28).
- La silhouette de nuit dépend des indices des nuances (2 silhouette, 3
  faible, `$FF` aucune) de `dhgr_palette.mood_table` : `test_dhgr_ref.py`
  les vérifie.
- `test_reference_state.py` est rebasé : avec un animal sur la case, la
  comptabilité de la scène (`scene_drawn`, `scene_cache_*`) et les flottants
  `t1`…`t5` de sa projection diffèrent de la référence HGR par
  construction ; ils restent comparés sans animal.

## 28. Rotation avec un animal : le fond gardé, la vue défile (15 octobre 2026)

Décision de l'utilisateur : optimiser la rotation (§ 27.3 : avec un animal,
une flèche redessinait toute la vue). Mesures : `build/wild.map`,
`build/layout.json`, `build/layout-140.json`, catalogue ProDOS des
`dist/*.po` ; avant = § 27.

**Mécanique.** Avant de dessiner l'animal, `ANIMAL_RUN` charge OUTDOOR et
appelle `module_animal_bg` : sur une carte héritée, `ab_copy` copie les
octets de ses colonnes (`AB_J0` = l'octet de sa première colonne, `AB_N` + 1
octets, calculés par PROJECT : colonne 7g + k → octet 2g, + 1 si k ≥ 4 ;
dernier bit 4c + 3 → 2g, + 1 si k ≥ 3), rangées 16 à 175, banque
auxiliaire puis principale, vers la carte langage auxiliaire, banque 1
(`AB_BUF` = `$D000`, au plus 160 × 2 × 22 = 7 040 octets, sous
`TP_SNAP_END` = `$EC00`) ; `scene_drawn` = `$83`. La copie tourne avec
ALTZP levé (page zéro, pile et carte auxiliaires, interruptions masquées,
comme `tp_save`) : pointeurs en `$F0-$F3` auxiliaires, `hgr_row` y écrit
`hp`. Une rotation (`turn_view`, bit 7 de `scene_drawn`) appelle
`animal_unpan` : OUTDOOR remet le fond (`module_animal_unbg`), PROJECT
refait la scène du site (`module_project` : `sprite_*`, `scene_asset`,
`scene_drawn` 0 à 3), puis le défilement habituel (`scroll`, colonnes
neuves) et `animal_view` (le fond de la nouvelle vue gardé, l'animal
dessiné). La boucle de l'animal ne parcourt plus que ses colonnes (`an_last`,
`an_first`, opérandes de la copie en `$A000`). Pixels identiques au
redessin complet : le fond remis est exactement l'écran sans animal ;
le feu de l'invite est caché avant (`fire_hide`) et ne touche jamais les
colonnes de l'animal.

**Invalidation.** Toute vue complète remet `scene_drawn` (`scene_prepare`,
nuit noire, abri) ; `tp_save` (TOPO, MAP) prend la zone : `asl` / `lsr`
de `scene_drawn` (`$83` → 3, la rotation suivante redessine, TOPOGEN
+6 octets) ; une carte native (`MAP+37`, l'atlas occupe la zone) ne garde
rien (`scene_drawn` = 3 : redessin, comme avant). LOOK B et LOOK N
redessinent, animal ou non.

| Changement | Zones |
|---|---|
| PROJECT : colonnes de l'animal (`AB_J0`, `AB_N`, bornes de la boucle), OUTDOOR appelé par `ANIMAL_RUN` (+8, copiés en `$A000-$A021`) ; `animal_fire` rend `proj_width` (il le laissait à 28 : la largeur du feu) ; `project_offset` et le relèvement de `project_candidate` passent par `wrap_ang` (−34) | XL 1 967 → **2 002** (46 libres dans la fenêtre), 140 Ko 1 847 → 1 882 (166) |
| OUTDOOR : `module_animal_bg`, `module_animal_unbg`, `ab_copy`, `ab_bank` | 1 541 → **1 648** octets (+107 ; 400 libres) |
| Résident : `animal_unpan` (GCODE, 19), `turn_view` (+10 : `bpl`, `jsr`, `lda`, `jmp animal_view`), `AB_J0` / `AB_N` (LOWTEXT, 2) | WILDGAME 23 → **2**, WILDERNESS 12 → **2**, WILDLO 2 → **0** |
| Stock des six paquets (XL, disques de comparaison) : le module de la grille (32) compressé LZ (`build_disk.LZ_SIX_PACKS`) | 2 676 → 2 441 octets stockés ; ≈ 33 cycles de plus par octet, ≈ 88 000 par chargement (0,09 s par choix ou pas de la file de la grille) |

Sans la grille compressée, XL ne plaçait plus ses modules : 44 309 octets
pour 44 329 libres, mais en morceaux (28 869, 6 144, 4 096, 5 114 et un de
106 octets, trop petit pour un module) : il fallait 86 octets de plus. La
140 Ko garde la grille brute : son NEOWILD.DAT, compressé en entier,
grandissait d'un bloc avec un module déjà compressé (quatre parties au lieu
de cinq).

### 28.1 RAM principale résidente, octets libres

TEXT 2, WILDLO **0** (2), WILDGAME **2** (23), WILDERNESS **2** (12),
RESIDENT 5, MENUCODE 4, LOWPAGE 1, HICODE 3, banque 2 principale 24, SIM
sous `$B500` 156.

### 28.2 Stock, disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc (`aux_trunk_free` − zone des sprites) | 150 → **241** | 811 → **666** |
| PROJECT (fenêtre `$5800`, 2 048) | 81 → **46** | 201 → **166** |
| NEOWILD.DAT | 109 249 octets, 215 blocs | 70 365 → **70 587** octets, 139 blocs (**69** avant un bloc de plus) |
| Volume | 370 / 1 600 blocs | 280 / 280 blocs, cinq parties |

La carte langage auxiliaire, banque 1 et `$E000-$EBFF`, sert d'instantané
à TOPO (cartes héritées) ou d'atlas (cartes natives) ; le fond de l'animal
la partage avec l'instantané, jamais avec l'atlas.

### 28.3 Temps (cycles, XL, l'ours à deux cases à l'est du départ, cap 10)

| Rotation | Sans animal | Avec, avant | Avec, après |
|---|---:|---:|---:|
| flèche droite | 1 251 507 | 4 553 305 | **2 382 700** |
| flèche gauche | 853 340 | 4 160 830 | **1 985 111** |
| LOOK R | 2 326 650 | 4 946 454 | **3 352 629** |
| LOOK L | 1 567 960 | 4 195 211 | **2 594 893** |
| flèche droite, feu allumé face au cap | — | 4 559 236 | **2 388 330** |

`test_pan.py`, 52 rotations (17 + 17 flèches, 9 + 9 LOOK) : redessin forcé
4,17 millions par rotation, défilement 2,37 millions (−43 %), sans animal
1,27 million (+86 %). Une vue complète avec un animal coûte en plus la
copie du fond (≈ 60 000 cycles pour l'ours, 12 octets × 2 × 160 ; 22 au
pire) et le chargement d'OUTDOOR (≈ 28 000) : ≈ +1 %.

### 28.4 Le reste du surcoût, et pourquoi la cible de +10 % n'est pas atteinte

Par rotation (≈ 1,1 million) : décoder et peindre le sprite (≈ 600 000 :
`sprite_code`, `spc_clear` et `scene_emit` balaient 160 rangées par colonne
de sprite, `dspan`), copier OUTDOOR deux fois et PROJECT (≈ 85 000), le
sprite LZ (42 000), les deux copies du fond (≈ 85 000), `module_project` et
`module_animal`. Ne plus redessiner l'animal demanderait son image et son
masque (bit à bit : une couleur de l'animal peut égaler celle du fond),
deux rectangles de plus que le fond : 3 × 7 040 octets au pire, quand la
zone libre en a 7 168. Les couleurs des sprites sont pleines (`spr_map`,
octet `$nn`) et l'animal reste aux mêmes colonnes sans feu : l'image
gardée resterait juste. Pistes, toutes hors de la place actuelle :
réserver 14 Ko pour image et masque (lignes du haut de l'animal seulement :
2 à 3,4 Ko par rectangle selon l'animal, au prix d'un calcul de ses
rangées) ; ou réduire le balayage de `sprite_column` / `scene_emit` aux
rangées du sprite (code résident, plein).

## 29. Post-its et pages restructurées (15 octobre 2026)

Deux demandes de l'utilisateur du même jour : généraliser en « post-it »
la présentation du panneau STATUS de XL ([MENUS.md](MENUS.md) § 9.3), puis
restructurer les pages du haut **sur les deux éditions** (§ 5 : MEDICAL
fusionnée dans STATUS, INVENTORY renommée OBJECTS avec CARRYING, RANGERS
dans MENU, HERE et la ligne d'état devenues LOCAL ; onglets STATUS |
OBJECTS | CRAFT | HELP | OPTIONS | MENU). Le style MouseText reste propre
à XL. Mesures : `build/wild.map`, `build/layout.json`,
`build/layout-140.json`, catalogue ProDOS des `dist/*.po` ; avant = § 28.

**Mécanisme.** Le code partagé dispose les pages pour les deux éditions
(un titre en inverse par bloc, les rangées depuis la colonne 0 ou 41) ;
XL encadre chaque bloc par la sortie elle-même : `mt_cout` (le COUT des
pages) et `mt_pad` (tous les remplissages, par `xl_padhook`, résident)
lisent la table de post-its de la page (six octets par post-it,
`pf_pages`, `pf_craft` dans la queue de CRAFT) et un tampon de cadre de 80
octets (le corps de `page_top`, mort sur XL : `XL_ZERO`, au-dessus des
neuf blocs de CRAFT ; assertions dans `src/mt_pages.s`). La page STATUS de
XL n'a plus de code propre (la queue faisait 1 457 octets).

| Changement | Zones |
|---|---|
| STATUS partagé : MEDICAL fusionnée (`module_status` porte le focus des soins, `med_cell` en trois colonnes, la liste CONDITIONS sans les blessures), OBJECTS (titre du groupe, `PAGE n/m` sur la rangée 15, CARRYING, 33 objets par page), MENU (RANGERS : `st_rangers`, `st_cells`), HELP (texte d'OBJECTS) ; `goal_pct` à l'arrivée sur STATUS (l'état reste celui de la référence, `test_reference_state.py`) | 6 384 → **6 306** octets (`$9600-$AEA1` : **94** libres sous `$AF00`, étaient 16) ; LZ 5 124 → 5 110 |
| CRAFT partagé : `cp_medical` supprimé, lettres `SMIHTO` | 4 089 → 4 083 (13 libres dans `$9600-$A5FF`) |
| WILDGAME : `scr_medical` supprimé (inutilisé) | 5 979 → 5 970 octets (**11** libres) |
| Queue STATX (XL) : onglets, pied, moteur des cadres, tables | 1 457 → **1 096** octets (`$AF00-$B347`) |
| Queue CRAFTX (XL) : rangées des post-its, titre de la recette, tracé par `mt_cout` après une touche (`cp_redraw_x`) | 67 → 148 octets ; CRAFT XL 4 308 octets, toujours 9 blocs |
| Queue ENDX (XL) : le détail du score en post-it | 122 → 192 octets |
| Queue MEDVX (XL) | 26 → 23 octets |
| Résident XL (`XL_COPIES`) : `xl_padhook` (15 octets) avec `xl_pad` et `xl_curtain` sur `page_foot` | 38 → **53** octets sur 54 : **0 octet résident de plus** |
| XL : STATUS lu de NEOWILD.BLK (`status_fetch` → `sim_fetch` par `XL_ABS`, image `XI_GAME` ; pages `$B0-$B5` libres dans la table de ProDOS, `game_pages` par `XL_BYTE` du chargeur ; `DISK_LIMIT` de `build_disk.py`) | STATUS XL 7 496 octets, **15 blocs** (`$9600-$B5FF`) ; quitte le stock LZ |

### 29.1 RAM principale résidente, octets libres

TEXT 2, WILDLO 0, **WILDGAME 11** (2), WILDERNESS 2, RESIDENT 5,
MENUCODE 4, LOWPAGE 1, HICODE 3, banque 2 principale 24, SIM sous `$B500`
156. Sur XL, 1 des 54 octets de `page_foot` reste libre.

### 29.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| Place du tronc (`aux_trunk_free` − zone des sprites) | 241 → **6 114** | 666 → **679** |
| NEOWILD.DAT | 109 249 → **102 561** octets, 215 → 202 blocs | 70 587 → **70 561** octets, 139 blocs (**95** avant un bloc de plus ; étaient 69) |
| NEOWILD.BLK | 65 → **80** blocs (+ STATUS) | inchangé (52) |
| Volume | 370 → **372** blocs sur 1 600 | **280 / 280** blocs, cinq parties sauvées |

### 29.3 Temps (cycles, émulés)

| | XL | 140 Ko |
|---|---:|---:|
| STATUS chargé (`status_fetch`) | **128 555** (15 blocs ; ≈ 395 000 en LZ avant, estimé à 67 cycles par octet stocké) | 345 641 (LZ) |
| Ouvrir STATUS (de `module_status` à l'invite des touches, avec ADV et MEDICAL) | 531 062 | 351 381 |
| Tracé des pages (de `page_top` à l'invite) : MENU, OPTIONS, focus d'OPTIONS, HELP, OBJECTS, STATUS | 340 607, 184 228, 183 129, 275 146, 262 104, 323 038 | 224 986, 69 283, 68 539, 137 683, 151 011, 162 470 |

Les cadres coûtent environ 115 000 cycles par tracé de page (≈ 0,11 s) :
`pf_sync` (construction du cadre d'une rangée, sautée quand la signature
de la rangée est celle du tampon), `mt_cout` et `mt_pad` (une comparaison
par cellule). Chaque cellule reste écrite une fois : les déplacements du
focus ne stockent que les cellules qui changent. L'ouverture d'une page du
haut sur XL reste plus rapide qu'avant (≈ −0,27 s de chargement contre
+0,11 s de cadres). Piste pour réduire le surcoût : coder dans le tampon
la longueur de la plage vide suivante (les cellules vides ont le bit 7),
pour que `mt_pad` saute les plages sans les parcourir.

### 29.4 Contraintes nouvelles

- `PG_*` renumérotés (0 STATUS, 1 OBJECTS, 2 CRAFT, 3 HELP, 4 OPTIONS,
  5 MENU) ; `pg_letter` / `pg_letpg` (S, I, R, H, O, M).
- Le corps de `page_top` doit rester d'au moins 83 octets (le tampon des
  cadres de XL) et au-dessus des blocs de CRAFT : assertions.
- XL : une page du haut ne doit écrire qu'à travers COUT, `tab`, `vtab`,
  CR et `topo_pad` (pas de `STA` direct dans la page texte) pour que ses
  cadres restent justes ; un bloc nouveau demande une entrée dans sa table.
- XL : STATUS est lu de NEOWILD.BLK jusqu'à `$B5FF` (sa taille au plus
  8 192 octets, `DISK_LIMIT`) ; les disques de comparaison le gardent dans
  le stock (`build_disk.py` le refuse sur NEOWILD.BLK sans `mousetext`).
- 140 Ko : les pages changent (nouvelle disposition) ; l'image n'est plus
  celle d'avant ces travaux (décision de l'utilisateur : la
  restructuration vaut pour les deux éditions).

## 30. OBJECTS de transfert, charge du second jeu, GET sans question (16 octobre 2026)

Demandes de l'utilisateur du 15 octobre 2026 : la page OBJECTS refaite
pour transférer vite ([MENUS.md](MENUS.md) § 5.1), la jauge de la charge
aux seuils de l'original (mesurés : `tools/re_load_probe.py`), le poids du
second jeu ([CRAFT.md](CRAFT.md) § 8.2), GET des quantités sans question
([FORAGE.md](FORAGE.md) § 17.3, [CAMP.md](CAMP.md) § 3). Les deux éditions.
Mesures : `build/wild.map`, `build/layout.json`, `build/layout-140.json` ;
avant = § 29 et l'état du 15 octobre au soir (NEOWILD.DAT de 70 628
octets, volume plein).

| Changement | Zones |
|---|---|
| OBJECTS refaite (`src/inventory.s`) : deux listes, curseur, transfert tapé, LOAD ; les groupes, pages et touches 1-5, N, B retirés ; les abris hors des objets | STATUS 6 396 → **6 830** octets (`$9600-$B0AD`), LZ 5 175 → 5 641 ; il passe au-dessus de `$B000` (l'image de la grille, comme SIM : `get_line` la reprend) |
| La queue STATX de XL déplacée (`$AF00` → **`$B100-$B5BF`**, `src/wild.cfg`) : post-its d'OBJECTS, `page_foot23_x` | STATUS XL 7 596 → 8 128 octets, NEOWILD.BLK **15 → 16 blocs** (`DISK_LIMIT` `$B600` : 64 libres) |
| Résident : `obj_keep`, `obj_side`, `obj_cur`, `obj_type` à la place de `pg_lines` (10 octets, mort) ; la chaîne des touches d'OBJECTS raccourcie | WILDERNESS 2 → **22** libres ; WILDGAME 11 → **6** (`summary_refresh` attend la sortie de la page : 5 octets) |
| GRID : l'étape `S_OBJECTS` (`INVENTORY`), le nom tapé sans mot à chiffre (`2QT CANTEEN`) | 2 676 → 2 728 octets ; **LZ sur 140 Ko aussi** (`LZ_140`, `build_disk.py` : 2 486 stockés) |
| SIM : le poids et le volume du second jeu dans `module_load_totals` | 7 780 → 7 829 octets |
| CRAFT : `cr_load` (refus au sol au-delà des limites) | 4 083 → 4 185 octets, NEOWILD.BLK **8 → 9 blocs** sur 140 Ko (recettes 1 980 : toujours 4 blocs pour MAKE) ; fenêtre `CRAFTM` `$1000` → `$1100`, queue CRAFTX de XL `$A640` → `$A700` |
| ITEMS, CAMP : la charge avant et après CRAFT, l'eau sans question | ITEMS LZ 1 485 → 1 495 ; CAMP 1 757 → 1 849 (LZ 1 544 → 1 621) |
| FORAGE : PACK sans question, fiches copiées sur une pile vide | 5 867 → 5 979 octets, toujours 12 blocs |
| Banque de textes : « YOU TOOK # OUNCES. » | + 1 texte |
| Parties sauvées : les W5/W6 constants hors de `sv_ranges` (SAVE.md § 5) | 1 725 → **1 509** octets, 5 → **4 blocs** chacune |

### 30.1 RAM principale résidente, octets libres

TEXT 2, WILDLO 0, **WILDGAME 6** (11), **WILDERNESS 22** (2), RESIDENT 5,
MENUCODE 4, LOWPAGE 1, HICODE 3 ; `LOWTEXT` plein (la table des messages
de CAMP y est : un texte de plus passe par `camp_say_tb`).

### 30.2 Stock et disque

| | XL (800 Ko) | Neowilderness (140 Ko) |
|---|---:|---:|
| NEOWILD.DAT | 102 562 → 102 497 octets, 202 blocs | 70 628 → **71 915** octets, 139 → **142 blocs** (277 octets avant un 143e) |
| Stock auxiliaire (`aux_trunk_free`) | 8 847 | 2 127 → 1 705 ; place des sprites de la Sierra 192 octets |
| NEOWILD.BLK | 80 → 81 blocs (+ STATUS) | 52 → 53 (+ CRAFT) |
| Parties | 5 × 4 blocs | 5 × 4 blocs (25 → 20) |
| Volume | 372 → **368** blocs sur 1 600 | **280 → 279** blocs sur 280, cinq parties sauvées |

Le stock de 140 Ko était le premier plafond : 39 octets de trop avant de
déplacer le contrôle de la charge dans CRAFT (disque) et de compresser GRID
(`LZ_140`) ; le module des étoiles (25) ne gagnait que 45 octets en LZ.

### 30.3 Temps (cycles, émulés ; DROP DOWN PARKA depuis la page)

| | XL | 140 Ko |
|---|---:|---:|
| `obj_type` : SIM en silence | 120 131 | 120 131 |
| la commande (ITEMS, `load_totals`) | 245 431 | 245 378 |
| `alerts_after` → `get_line` (le bandeau attend : 0 au lieu de ≈ 347 000) | ≈ 0 | ≈ 0 |
| `get_line` → `module_queue` (la grille, GRID LZ) | 179 339 | 179 209 |
| `scr_inventory` : SIM en silence | 119 985 | 119 985 |
| STATUS chargé | 137 058 (16 blocs) | 376 108 (LZ) |
| tracé de la page (différentiel) | 301 680 | 182 928 |
| **de RETURN à la page revenue** | **≈ 1 112 000 (1,09 s)** | **≈ 1 234 000 (1,21 s)** |

Le bandeau (`summary_refresh`, ≈ 347 000 cycles) ne se redessine plus
pendant un transfert, invisible sous la page : `obj_keep` le retient
jusqu'à la sortie de la page (−24 %). GRID en LZ coûte ≈ 85 000 cycles de
plus par choix de la grille sur 140 Ko (comme XL depuis le § 28).

### 30.4 Contraintes nouvelles

- STATUS dépasse `$B000` sur les deux éditions : comme XL, le code des
  pages ne doit appeler aucune routine de MENUSWAP ; `ob_line` est
  `tb_buf` (la page n'imprime aucun texte de la banque).
- Un transfert de la page ne doit pas faire passer le temps : la file
  (`S_CARRY`, `S_OBJECTS`) ne s'arrête qu'à une rencontre, et SIM est lue
  en silence (pas de vue refaite) ; le sac pendu ne se transfère pas.
- `pg_lines` n'est plus du code (l'état d'OBJECTS) ; `XL_COPIES` s'arrête
  toujours avant lui.
- 140 Ko : un 143e bloc de NEOWILD.DAT est encore libre (279/280) ;
  WILDGAME n'a plus que 6 octets.


## 31. SIM conserve la vue pendant ses calculs (16 octobre 2026)

`overlay_load` ne masque plus la vue en chargeant SIM. Il garde `ui_dirty`
pour reconstruire le résumé après le calcul. `show_view` masque déjà son
redessin ; `finish_simulation` appelle désormais aussi `view_hide` avant
le sien. Le chemin `sim_quiet` reste sans redessin. Aucune donnée ni copie
supplémentaire : le JSR de trois octets passe de GCODE à CODE.
`test_transitions.py` contrôle les pixels, les deux banques DHGR, le texte
et le curseur pendant le chargement, puis le rideau au redessin de REST
après STATUS, sur les deux éditions. Les volumes restent à 279/280 et
368/1600 blocs.


## 32. Accords des messages et objet manquant (16 octobre 2026)

Le marqueur `%` de `message_text` écrit S sauf si `msgnum` vaut exactement
1 (test sur les deux octets). Le branchement ajoute 7 octets à GCODE et
la routine 16 à CODE ; aucun état persistant ajouté. CAMP refuse le nom
absent avant `camp_begin` (+11 octets, image 1 849 → 1 860 ; LZ de 140 Ko
1 621 → 1 630). Le texte commun `m_object` ajoute MAKE FIRE à ses exemples ;
`m_unknown` garde seulement le mot fautif et TYPE HELP. La banque de textes
passe de 4 150 à 4 154 octets, sans nouvel identifiant.

Marges mesurées après construction : WILDGAME **2** octets, WILDERNESS **3** ;
stock auxiliaire de tronc XL **8 842**, 140 Ko **1 686** (incluant les espaces
réservés au paquet). NEOWILD.DAT : 61 147 octets sur 140 Ko, 53 350 sur XL ;
volumes inchangés, **279/280** et **368/1600** blocs. Le placement complet des
images tient toujours dans les deux éditions.

`test_feedback.py` vérifie 0, 1, 2, 255, 256, 257 et 65535 pour les heures,
minutes et onces sur les deux éditions, sans modification de la simulation
ni des banques DHGR. Le même test exerce les six verbes sans objet. Les
commandes réelles de repas, boisson et repos sont couvertes par les tests
de saisie et de sommeil.


## 33. Retrait thermique au rangement d'un vêtement (16 octobre 2026)

`module_do_get` appelle `native_clothes_changed` lorsque `saved_item` indique
un objet auparavant porté, après `accept_load` réussi. Il reprend `noun` dans
X après la mise à jour thermique et la remise en place du module ITEMS.
PACK/GET et TAKE/CARRY suivent ainsi le même historique des pertes arrondies
que DROP ; un transfert refusé ne modifie pas cet historique. Le chemin de
carte héritée reste celui de `native_clothes_changed` (retour immédiat).

ITEMS : 1 692 → **1 704** octets (+12), LZ 1 495 → **1 502** (+7).
Aucun octet résident ajouté : WILDGAME **2**, WILDERNESS **3** libres.
Stock auxiliaire de tronc : XL **8 835**, 140 Ko **1 679**. NEOWILD.DAT :
**61 415** octets sur 140 Ko (25 octets avant un bloc de plus), **53 357**
sur XL. Volumes : **279/280**, **368/1600** blocs.

`test_items.py` initialise le seul en-tête thermique natif de la Sierra
(douze pertes et les bits WORN initiaux d'ADVENTURE), sans déplacement ni
atlas, sur les deux disquettes distribuées. Il compare les cinq verbes,
les valeurs exactes avant et après retrait, l'état sur refus de volume,
le temps, les appels MLI et les deux banques DHGR.


## 34. Portion d'une once dans la grille (16 octobre 2026)

`gr_size` et `list_qty` commencent par 1 et `1 OZ`. La boucle `gr_sizes`
utilise désormais la longueur de `gr_size`, au lieu de la constante 8.
Le même index de portion sert à EAT, DRINK et à la file BOIL : ses prérequis
restent inchangés. Aucun octet résident ajouté.

GRID : 2 728 → **2 734** octets (+6), LZ 2 486 → **2 488** (+2).
Stock auxiliaire de tronc : XL **8 833**, 140 Ko **1 677**. NEOWILD.DAT :
**61 421** octets sur 140 Ko (19 avant un bloc de plus), **53 363** sur XL.
Les volumes restent à **279/280** et **368/1600** blocs.

`test_grid_play.py` vérifie, sur chaque édition, une dernière once d'œufs,
d'eau bue et d'eau bouillie, avec les flèches et RETURN seuls : commande
composée, stocks épuisés, fin de la file et état de simulation identique à
la saisie du même texte. Il contrôle aussi l'annulation de la portion.
`test_menu_bar.py` garde les portions jusqu'à 48 oz et les plafonds.


## 35. CATCH avec durée dans la grille (16 octobre 2026)

Le choix de CATCH ouvre `list_dur` après la cible ; RETURN range l'index
choisi dans `mq_list+4` (`MQ_CATCH_DUR`). Ces cinq octets étaient déjà
réservés : CATCH n'occupe que trois étapes au plus, donc la cinquième
peut garder cet index entre les chargements de GRID. `Q_SIZE` ajoute la
durée de `list_dur` pour S_CATCH, la portion de `list_qty` pour BOIL.
Aucun octet résident ajouté. Les textes du second jeu sont alignés dans
une même page pour garder leurs pointeurs courts (`GRID`, alignement $100).

INPUT : 1 645 → **1 651** octets (CATCH dans les verbes numériques).
FORAGE : 5 979 → **6 029**, toujours **12 blocs** ; `fr_hours` reçoit la
durée validée et refuse 1 500 minutes et plus, ou garde son lecteur décimal
quand la commande n'a pas de suffixe. GRID : 2 734 → **2 863** octets,
LZ 2 488 → **2 529**. Pour garder le stock, le module horaire des étoiles
(25) passe aussi en LZ sur les deux éditions : 2 578 → **2 533** octets,
marge de décodage 5. Décodage supplémentaire estimé à ≈ 0,08 s à 1 MHz
lors du recalcul de la liste d'étoiles, sans lecture disque.

Stock auxiliaire de tronc : 140 Ko **1 675**, XL **8 831**.
NEOWILD.DAT : **61 592** octets sur 140 Ko (122 blocs, 360 octets avant le
bloc suivant), **53 783** sur XL (107 blocs). Volumes : **280/280** et
**369/1600** blocs. Les cinq sauvegardes et le hall of fame sont toujours
préalloués et réécrits en place.

Validation : `test_grid_catch.py`, `test_grid_play.py`, `test_menu_bar.py`,
`test_forage.py` (130 cas, quatre écarts connus écartés, plus le parcours
original), `test_reference_state.py`, `test_editions.py`, `test_pack_boot.py`
et `test_stars_game.py` (sur les deux éditions).


## 36. Dernière page et disposition des listes (16 octobre 2026)

`pg_cur` occupe le dernier octet libre de LOWPAGE et survit aux chargements
SIM/STATUS ; `pg_open = $FF` demande sa réouverture depuis la vue.
La commande STATUS garde son ouverture explicite. OBJECTS distingue le focus
sur l'onglet (bas : vue, Entrée : listes) du focus sur les objets.

HANDS et PACK ont des post-it séparés sur XL, dont la séparation suit le
curseur ; douze entrées visibles, CARRYING/LOAD aux rangées 16–20, aides
à droite aux rangées 21–22. Le titre PACK n'est écrit qu'une fois lorsque
son en-tête atteint le haut du défilement. Le tampon de cadre reste constitué
des 80 octets du corps inutilisé de `page_top` sur XL : le retrait de
S/O/R/H conserve explicitement cette réserve.

MAIN et LOWPAGE sont pleins ; STATUS utilise 6 912 octets (`$9600–$B0FF`),
STATX 1 280 (`$B100–$B5FF`). Les huit octets du programme des groupes
d'OBJETS sont résidents dans CODE. Pour tenir dans le stock 140 Ko,
MEDICAL (17) est aussi compressé ; INPUT reste brut.

Stock auxiliaire libre : 2 186 octets sur 140 Ko, 8 833 sur XL.
NEOWILD.DAT : 61 921 octets (122 blocs) et 53 806 octets (107 blocs),
respectivement. Volumes reconstruits : 280/280 et 369/1600 blocs.
L'échelle de distance de TOPO est aux lignes 149–157, en bas à gauche ;
la dernière cellule DRINK conserve son espacement sans barre à droite.

Validation : `test_objects.py` (dont 22 positions de défilement des cadres),
`test_focus.py` (six pages mémorisées sur les deux éditions), les parcours
OBJECTS de `test_interface.py`, le tracé différentiel de
`test_transitions.py`, `test_craft_page.py`, `test_grid_play.py`,
`test_topo_dhgr.py`, `test_graphical_topo.py` et `test_care.py`.
Les gestes MEDICAL de l'édition 140 Ko sont aussi comparés aux commandes
tapées. `test_reference_state.py` : 163 variables, 1 324 octets, 24 étapes,
état identique à la référence.


## 37. Sélection stable et jauges PACK/HANDS (16 octobre 2026)

`obj_selected` utilise les deux derniers octets BSS libres de WILDGAME,
avec un identifiant par côté. L'ouverture reconstruit les listes puis
retrouve les identifiants ; un objet disparu utilise le repli existant
sur l'indice du curseur, borné à un objet valide. Les mouvements mettent
l'identifiant à jour avant de redessiner. Le défilement reste dérivé du
curseur ; le focus d'arrivée reste sur les onglets. L'état est résident
pendant la partie, hors des plages de sauvegarde : format et taille des
parties inchangés (`test_save.py`).

LOAD garde le poids sur dix cellules et ajoute PACK/HANDS sur six cellules
à la rangée 19 : volume occupé, puis IN3 libres exacts. Le volume libre des
vêtements suit le ralentissement à la rangée 18. La multiplication utilise
six fois un volume légal (6000 IN3 au plus) ; une surcharge est traitée
avant multiplication et le libre est borné à zéro. La capacité nulle
n'appelle pas la division et affiche une jauge vide.

Les calculs `ob_mul`/`ob_div`, la recherche des sélections et les jauges
partagent maintenant MEDVIEW (19), chargé après la préparation d'OBJECTS.
Cette lecture de quatre blocs à l'ouverture permet de conserver les cadres
et informations existants dans la fenêtre STATUS pleine. Aucun chargement
n'est ajouté aux mouvements dans une liste. Le pied de page XL MEDVX passe
de $5E80 à $5FC0 ; MEDVIEW 1624 → 1860 octets ($5800–$5F43), toujours
quatre blocs sur chaque édition, y compris sa queue XL.
STATUS 6912 → 6864 octets ($9600–$B0CF), 48 libres. WILDGAME et MAIN
sont pleins. Le stock de tronc 140 Ko passe de 2186 à 2239 octets libres ;
XL conserve 8833. NEOWILD.DAT : 61859 octets sur 140 Ko, 53805 sur XL.
Volumes inchangés : 280/280 et 369/1600 blocs.

Validation : `test_objects.py` vérifie les deux sélections, le côté, le
retour après SIM/HELP, les changements d'indices et l'objet disparu ; les
jauges vides, à moitié, pleines, surchargées, de capacité nulle et aux
sixièmes sur les deux éditions, avec les codes bruts et les IN3 exacts.
Les transferts restent identiques aux commandes tapées. `test_focus.py`,
`test_load.py`, les parcours OBJECTS de `test_interface.py`, le tracé
différentiel de `test_transitions.py`, `test_save.py` et les gestes de soin
sur les deux éditions passent également.
`test_reference_state.py` confirme les 163 variables (1324 octets) après
chacune des 24 étapes : simulation identique à la référence.


## 38. Entrées communes : place et chargeur (16 octobre 2026)

Le pilote et les dialogues de l'audit approuvé remplacent les entrées
clavier seules (`ui_event.s`, `ui_choice.inc`). Pour obtenir leurs octets
résidents sans réduire la carte, les sprites ni les sauvegardes :

- `grid_row` calcule `GRID + 112 * X` par `128X - 16X`, en coût fixe,
  à la place des deux tables de 84 octets. Il retourne A/Y et conserve X ;
  `cell_at` garde séparément son Y d'entrée, et le décodeur de géographie
  garde son index de sortie. Le rendu et la géographie sont testés.
- `module_take_oz` vit dans ITEMS, appelé par le relais résident `take_oz`,
  qui rétablit le module du demandeur après consommation. Les points
  d'entrée des nombres vivent dans GCODE ; les trois octets du pilote
  sont dans RESBSS, hors du format des parties.
- Sur 140 Ko SIM est LZ (7 809 → 5 005 octets en stock) et ORIENT est en
  RAM (1 356 → 1 168). Les quatre constantes variables de préparation
  `th_surface`, `th_a`, `th_native_composition`, `wf_storm` sont en GDATA :
  PRE écrit directement ces valeurs, sans modifier un flux compressé.
  Les deux premières ont leurs plages SAVE explicites ; les autres sont
  dans la plage résidente déjà sauvée. Une partie occupe 1 529 octets,
  toujours trois blocs de données et un index, cinq parties par volume.
  Les cartes de stress des tests compressent SIM également.
- Le chargeur utilise `$B000-$B3FF` comme tampon ProDOS. La grille attend
  en `$5800-$5DFF`, HICODE en `$5E00-$5EFF`, puis est dispersée dans les
  rangées graphiques cachées comme auparavant. TABLE reste en `$B500`.
  Le chargeur et son BSS finissent en `$ABAA`, donc restent sous le tampon.
- Le code de fin de voyage atteint `$A25F` ; sa queue XL commence en
  `$A400`, avant les autres zones libres de SIM.

Marges de la construction : MAIN plein, BSS termine en `$576D` (18 octets
avant REGIONTEXT), RESBSS en `$B9FD` (2 libres). INPUT 1 875 octets (173
libres), ITEMS 1 846 (202 libres), SITES 1 977 (71 libres). Stock de tronc
libre : 3 309 sur 140 Ko, 8 325 sur XL ; après les sprites Sierra : 1 796
et 6 812. Volumes : 280/280 et 370/1600 blocs, cinq sauvegardes chacun.
Une construction d'édition livrée refuse désormais une réduction de ce
nombre. La taille de NEOWILD.DAT est 73 696 et 103 345 octets.

Mesures `profile_actions.py`, Sierra niveau 4, fréquence animale nulle,
chaque commande depuis un nouveau démarrage, secondes invitées à 1 MHz :

| Commande | 140 Ko | XL |
|---|---:|---:|
| LOOK R | 2,269 | 2,268 |
| STATUS | 0,782 | 0,634 |
| Retour de STATUS | 0,091 | 0,092 |
| REST 1 H | 9,114 | 8,699 |
| WALK 1 H | 10,001 | 9,585 |

SIM en LZ évite les suppressions de sauvegardes mais ajoute du décodage
sur 140 Ko. Les mesures ci-dessus fixent cette contrepartie ; aucun appel
au pilote d'axes n'est ajouté pendant la simulation ou le rendu. Le bouton
retour seul est testé à la frontière des pas WALK/SWIM.


## 39. Retrait du générateur de terrain (16 octobre 2026)

À la demande de l’utilisateur, le générateur et le scénario archipel sont
supprimés : programme, manifeste, chargeur des fichiers supplémentaires,
contrôle d’identité des terrains générés et fond marin spécifique. Les six
régions, la préparation et les cinq emplacements de sauvegarde restent actifs.
Les sections de mémoire ci-dessous précèdent ce retrait ; nouvelles mesures
à la fin du document.

### Suite OBJECTS, XL seule (16 octobre 2026)

L’édition 140 Ko n’est plus une contrainte de livraison. Le nouveau menu
OBJECTS partage la fenêtre TREE (`object_menu.s`) sans nouvelle entrée du
répertoire résident. Les commandes d’orientation USE ont rejoint ORIENT ;
son chargement est adapté. La sauvegarde temporaire des places pour LOWER
utilise `tb_buf`, sans lecture de texte avant restauration. Le calcul de
l’aperçu travaille dans les données du module, sans modifier `load_used`.
Les aides de sortie se placent dans STATUS. Le format SAVE est inchangé et
les cinq fichiers de partie sont conservés sur XL. Les expériences de
compression disque faites pour 140 Ko ont été retirées.

### EQUIPMENT et marges XL (16 octobre 2026)

Le répertoire passe à 34 entrées. Le module 33 EQUIPMENT est chargé par
`mem_fetch` directement à $5800 ; `overlay_load(33)` garde sa signification
historique d’asset de site. Le trampoline de retour vers TREE réside dans
STATUS, hors de la fenêtre remplacée. `overlay_current` est invalidé.
Trois drapeaux temporaires du copieur deviennent des opérandes immédiats
modifiables ; les commutateurs et le registre d’état sont préservés.

Les commandes TREE rejoignent ORIENT (module 26), TAKE OZ rejoint OUTDOOR
(module 22). La légende OBJECTS rejoint la queue MEDVX déjà chargée. Le
calcul des prévisualisations et le rapport des refus utilisent des données
locales aux modules, sans ajout au format SAVE.

Construction XL : 393/1600 blocs occupés, NEOWILD.DAT 65 156 octets bruts,
56 093 stockés, 19 enregistrements, cinq parties conservées. Marges des
fenêtres : EQUIPMENT 334 octets ; TREE 19 ; CRAFT avant $A700 43 (dont 13
réservés au travail de page) ; STATUS 36 ; STATX 28 ; MEDVX 11. Les anciens
tableaux à deux éditions ci-dessus sont historiques ; XL seule est construite.

### Mesures après retrait de TMAP (16 octobre 2026)

XL occupe 379/1600 blocs (14 récupérés). NEOWILD.DAT : 65 137 octets
bruts, 56 056 stockés, 19 enregistrements. NEOWILD.TMP et NEOWILD.SCN
ne sont plus produits ; cinq emplacements de sauvegarde sont conservés.

### Soins et récupération depuis OBJECTS (16 octobre 2026)

`ob_cmd` rejoint MEDVIEW, déjà chargé par OBJECTS ; `object_commit` rejoint
STATUS afin que le remplacement ultérieur des modules ne reprenne pas dans
un code écrasé. `ob_mul` occupe les 28 derniers octets de STATX. La légende
OBJECTS reste dans MEDVX, déplacé de $5FC0 à $5FE0 ; le début du pied médical
est résident, réparti entre GCODE et TEXT. La table `care_use_minutes` est
résidente en LOWCODE et partagée avec l’aperçu : aucune durée dupliquée.

Les sélections réutilisent la position existante avant la recherche par nom,
ce qui permet de traverser les occurrences LOCAL et LOCAL HUNG. Aucun nouvel
état de partie ni changement du format SAVE. Les cartes de test courantes
sont construites explicitement en XL ; la version 140 Ko reste historique.

Marges : TREE 1 octet, MEDVIEW 1 avant sa queue, MEDVX 2, STATUS 1, STATX 0,
TEXT 7, BSS 3 et fin de LOW 2. XL : 379/1600 blocs, cinq parties ; DAT
65 153 octets bruts, 56 094 stockés, 19 enregistrements.

### TASTE et textes de dialogue (16 octobre 2026)

La commande d’ouverture de l’éditeur est copiée dans les 37 premiers octets
`overlay_text` ($9500) pendant le dialogue ; les listes sont reconstruites à
la fermeture. Ainsi les aides peuvent passer par `text_fetch` sans écraser
le nom sélectionné dans `tb_buf`. Aucun nouvel octet résident ni format de
sauvegarde. Les décisions d’édition et d’émission de quantité partagent une
routine : TASTE confirme directement, DRINK WATER reste quantifié.

TREE : $5800–$5FB1, 78 octets libres. XL reste à 379/1600 blocs ; DAT
65 293 octets bruts, 56 093 stockés et 19 enregistrements. Les autres
fenêtres et leurs marges ne changent pas.

### Projection de LOWER FOOD (16 octobre 2026)

L’éditeur parcourt les places 5 du premier ensemble et réutilise son calcul
unitaire : poids, volume et onces réellement suspendues. L’eau est déjà
incluse dans la gourde, le volume propre du sac est exclu. `om_total` reçoit
les capacités projetées et `om_v` le volume PACK supplémentaire ; aucune
place, quantité réelle ou valeur de `load_used` n’est modifiée. Les retenues
16 bits gardent l’alerte de dépassement arithmétique jusqu’à la fin du calcul.

TREE : $5800–$5FEB, 20 octets libres. Les textes de LOWER sont dans la
banque ; les autres fenêtres restent inchangées. XL : 378/1600 blocs,
65 318 octets DAT bruts, 56 001 stockés, 19 enregistrements, cinq parties.

### Durée de cuisson au joystick (17 octobre 2026)

Le lecteur décimal de FORAGE conserve ses heures et accepte haut/bas pour
régler les minutes exactes, bornées à 0–1499. Le mot scratch `fr_min`
porte le réglage, `fr_t = $FF` distingue les minutes du tampon décimal.
Les indications d’unité restent dans FORAGE ; aucun état résident ou
sauvegardé n’est ajouté, INPUT et le moteur de cuisson restent inchangés.

FORAGE : 6 148 → 6 390 octets, `$9600–$AEF5`, 266 octets libres sous
`$B000`, toujours 13 blocs. DAT et occupation XL restent à 65 318 bruts /
56 001 stockés et 378/1600 blocs ; les marges des autres fenêtres sont
inchangées.

### Quantités rapides des transferts (17 octobre 2026)

Le doublement de `om_qty` utilise les deux octets existants et leur retenue ;
les valeurs atteignant ou dépassant `om_max` reprennent le stock source exact.
Les textes FREE AFTER / FREE NOW passent dans la banque pour récupérer
la place du raccourci. Aucun état résident ou sauvegardé n’est ajouté.

TREE : `$5800–$5FF7`, 8 octets libres. DAT : 65 354 bruts / 56 018 stockés,
19 enregistrements ; XL reste à 378/1600 blocs avec cinq parties.

### Filtre de position d’OBJECTS/EQUIPMENT (17 octobre 2026)

Le dialogue lit la position de l’équipement (`it_place`) ou de l’objet
fabriqué (`cr_b1`), puis enlève le bit de l’action redondante. Les piles
quantifiées et le cas LOWER sont exclus de ce filtre. Les textes NEED,
CAN FREE et les fragments de capacités PACK/HANDS passent dans la banque
pour loger le calcul sans état résident ou sauvegardé supplémentaire.

TREE : `$5800–$5FFB`, 4 octets libres. DAT : 65 416 bruts / 56 052 stockés,
19 enregistrements ; XL : 379/1600 blocs, toujours cinq parties. Les autres
marges de code restent inchangées.

### Indications préalables de USE (17 octobre 2026)

Le dialogue lit `fg_bait` pour le piège et le matériel de pêche, `light`
pour la trousse de premiers soins, uniquement sur USE. Il affiche un texte
de la banque à la place de FREE NOW ; aucun appel de préparation ou de
simulation n’a lieu pendant le dessin. Les libellés ACTION, FROM, LOCAL,
CARRIED, TO, QTY, doses, objet indivisible et IN3 rejoignent la banque ;
le nom de commande reste protégé dans le scratch modal existant.

TREE : `$5800–$5FFC`, 3 octets libres. DAT : 65 679 bruts / 56 174 stockés,
19 enregistrements ; XL reste à 379/1600 blocs avec cinq parties. Aucun
octet résident, nouvel état de partie ou changement de SAVE.

### Réchaud et météo des allumettes (17 octobre 2026)

Les verbes et destinations du dialogue deviennent des identifiants de
banque ; `object_commit` récupère le verbe avant de composer sa commande
depuis la copie de nom protégée dans `overlay_text`. Les quantités utilisent
la table `pow10` résidente avec un indice décroissant ; aucune nouvelle
table numérique ni aucun nouvel état n’est ajouté. Le garde de la file
emploie l’entrée de page sans drapeaux, comme le faisait l’ancienne entrée
CARRY, puis retourne à la page sélectionnée.

`inventory_here` partage la requête native de case entre le règlement de
l’inventaire et l’aperçu météo ; l’aperçu préserve `geo_wooded` et
`geo_water_kind`. Les conditions relisent `camp_use`, `fire_near`, la
météo, la position et les stocks, sans charger SIM ni préparer du matériel.

TREE : `$5800–$5FDF`, 32 octets libres. STATUS : `$9600–$B0FF`, zéro octet
avant STATX ; les autres marges restent inchangées. DAT : 66 367 bruts /
56 318 stockés, 19 enregistrements ; XL : 379/1600 blocs, cinq parties.


### Prévisualisation de la lampe et de la loupe (17 octobre 2026)

Les derniers fragments d’unités et de jauges du dialogue rejoignent la
banque pour financer les contrôles. FLASHLIGHT partage le contrôle de
stock signé de FUEL/MATCHES. MAGNF GLASS lit l’abri, la nuit et le ciel,
puis rappelle le seuil solaire exact sans calculer une position ni utiliser
le cache arrondi. Le retour du contrôle restaure les indicateurs Z/N depuis
l’identifiant de texte, indépendamment des comparaisons d’objet.

TREE : `$5800–$5FFF`, zéro octet libre. STATUS reste `$9600–$B0FF`, plein
avant STATX. DAT : 66 813 bruts / 56 407 stockés, 19 enregistrements ;
XL : 379/1600 blocs, cinq parties. Aucun nouvel état résident ou sauvegardé.


### Instruments dans le dialogue partagé (17 octobre 2026)

Les 28 octets d’état temporaire du dialogue rejoignent `overlay_text+37`
à `+64`, après la commande protégée de 37 octets. Les listes OBJECTS et
EQUIPMENT sont fermées durant cet usage et reconstruites au retour ;
l’état modal est initialisé avant lecture et libéré avant la simulation.
Les alias restent exportés pour les contrôles d’émulation. La table des
quatre destinations devient octet et l’initialisation redondante de la
quantité maximale est retirée. Aucun état persistant ni SAVE ne change.

Le contrôle des instruments reproduit `ou_light` en lecture seule depuis
`period` et `weather_sky`, avec exception COMPASS ; il ne charge pas ORIENT.
Cinq textes distincts indiquent l’effet natif et un texte commun explique
le refus sombre et la perte d’aide boussole/montre après confirmation.

TREE : `$5800–$5FFC`, trois octets libres ; STATUS et STATX restent pleins.
DAT : 67 196 bruts / 56 591 stockés, 19 enregistrements ; XL : 380/1600
blocs, cinq parties. Aucune règle d’orientation ou simulation modifiée.


### Variation de poids des transferts (17 octobre 2026)

Le dialogue soustrait les poids `om_total` et `load_used` sur 16 bits,
avec le signe issu de l’emprunt, puis affiche la magnitude. Ce calcul lit
uniquement la projection existante, y compris l’agrégat de LOWER. Il est
omis si `om_bad` signale un débordement. Aucun nouvel état de partie.

Dix libellés de situation/charge rejoignent la banque. `om_bank_puts`
rejoint STATUS, partagé par ces pages et le dialogue TREE ; STATUS reste
chargé pendant l’édition. Le calcul de poids est également dans STATUS.
TREE : `$5800–$5FF9`, six octets libres. STATUS : `$9600–$B0DE`, 33 octets
avant STATX ; STATX reste plein. DAT : 67 778 bruts / 57 021 stockés,
19 enregistrements ; XL : 380/1600 blocs, cinq parties. SAVE inchangé.


### Sources et prérequis de gourde (17 octobre 2026)

`om_source_id` lit le côté sélectionné, la commande LOWER et les positions
natives/craft, en distinguant provisions, eau et piles sauvages/HIDE.
Il ne dépend pas de `om_from`, temporaire de projection qui n’est pas
calculé pour USE. La table de sources est dans TREE, le contrôle dans STATUS.
GET affiche le conseil de gourde existant si sa position est 0, 5 ou $FF.
Aucune nouvelle variable de partie, aucune modification de SAVE.

La conversion de magnitude 16 bits est partagée par WT et OVER dans
`om_neg_num`. Quatre libellés de jauge STATUS rejoignent la banque, sans
modifier leur texte ; le conseil de gourde réutilise `out_no_canteen`.
Le détail LOWER est raccourci d’une espace pour garder la ligne complète
sous 80 colonnes, même avec des chiffres sur cinq positions.

TREE : `$5800–$5FFF` ; STATUS : `$9600–$B0FF`, tous deux pleins avant STATX.
DAT : 68 154 bruts / 56 440 stockés, 19 enregistrements ; XL : 379/1600
blocs, cinq parties. Banque : 247 textes et huit mots de dictionnaire.


### Contenants et dictionnaire indépendant (17 octobre 2026)

Les ID publics de textes restent sur un octet (1–255). Le dictionnaire
commence désormais à l’index 256 et conserve jusqu’à 32 mots, indépendamment
du nombre de textes. `tf_get` sélectionne la page d’index publique, `tf_word`
la page du dictionnaire ; le calcul d’offset inclut cette page. Les entrées
publiques inutilisées pointent vers la fin des textes. Le constructeur
vérifie séparément textes, remplissage et dictionnaire, en conservant le
contrôle du format des données de référence figées.

`tf_idx` (quatre octets de scratch, initialisés avant lecture) rejoint TEXT.
Les cinq libellés de jauge partagent une entrée bankée avec NUL internes et
retours chariot explicites ; `st_gauge_text` sélectionne un suffixe. Les
messages bankés ordinaires du dialogue remplacent les `|` par des espaces
uniquement dans `tb_buf`. Le moteur reprend ses messages multi-lignes à
la prochaine lecture. Aucun nouvel état de partie ni changement de SAVE.

Les intervalles USE remplacent la liste de 30 ID par dix bornes ; la table
de bits est celle de la forêt résidente. Les destinations de transfert sont
calculées par `(action XOR 2) * 2`. Les conversions négatives résident dans
STATUS et le calcul WT dans TREE. Les anciens libellés de touches de
l’édition texte retirée sont remplacés par les courts libellés XL.

TREE : `$5800–$5FFE` ; STATUS : `$9600–$B0FE` ; HICODE : `$BE00–$BEFE`,
un octet libre chacun. TEXT : `$0A00–$0FFC`, trois octets libres.
DAT : 67 245 bruts / 56 801 stockés, 19 enregistrements ; XL : 380/1600
blocs, cinq parties. Banque : 254 textes, 32 mots ; 254 décodages natifs
comparés à leurs octets sources, dont NUL internes et références de région.

### Quantité FIT et regroupement des textes de page (17 octobre 2026)

FIT réutilise la projection de charge en recherche binaire, seize essais au
plus pour un stock 16 bits. Préparation et sélection rapide résident dans
STATUS ; recherche dans STATX, après les routines existantes afin de garder
`stx_base` à `$B100`. Les cinq octets `overlay_text+65..69` contiennent
validité, borne basse et borne haute ; aucun état sauvegardé supplémentaire.
La quantité initiale est restaurée au stock exact après la recherche.

Les petits libellés STATUS rejoignent le bloc des jauges. Les lignes
OPTIONS/MENU et les titres inverses partagent chacun une entrée bankée à
NUL internes ; les descriptions OPTIONS rejoignent aussi la banque. Le
lecteur de suffixe gère la retenue d’adresse, y compris à travers une page.
Les titres ne lisent plus des chaînes derrière l’adresse de retour en pile.
Le texte et la disposition des pages restent identiques.

La projection d’eau vérifie la position transportée de la gourde avant de
calculer son indice de charge : les positions sol, suspendue et absente ne
peuvent plus déborder du scratch vers le code STATUS. Les tests comparent
les 256 premiers octets de ce code pendant ces dialogues.

TREE : `$5800–$5FFE`, un octet libre ; STATUS : `$9600–$B0C4`, 59 libres ;
STATX : `$B100–$B5FD`, deux libres. HICODE : `$BE00–$BEFE`, un libre ;
TEXT : `$0A00–$0FFC`, trois libres. DAT : 67 548 bruts / 57 009 stockés,
19 enregistrements ; XL : 380/1600 blocs, cinq parties. Banque : 254 textes,
32 mots ; les décodages natifs sont comparés aux octets sources.

### Détail NEED/FREE/MISSING des capacités (17 octobre 2026)

Le détail utilise les totaux projetés et les limites natives déjà préparés.
Pour chaque dimension : NEED = max(0, projeté − actuel), FREE = max(0,
limite − actuel), MISSING = max(0, projeté − limite). Les soustractions
non signées conservent les valeurs de 0 à 65 535 ; la retenue borne les
résultats négatifs à zéro. Aucun calcul ne modifie les stocks ou les limites.
Les deux octets `overlay_text+70..71` mémorisent la vue et l’indice de charge.
Ils ne font pas partie de SAVE ; retour de confirmation et nouvelle ouverture
réinitialisent le détail.

Les quatorze noms médicaux sont répartis sur deux entrées bankées à NUL
internes ; trois descriptions OPTIONS partagent une entrée et des offsets.
Leurs textes exacts sont vérifiés à l’écran. `pg_desc_x` rejoint STATUS pour
faire place au petit formateur numérique dans STATX, ajouté après les routines
existantes. `om_free` rejoint également STATUS ; les tables de détail restent
dans TREE, chargé pendant le dialogue. `stx_base` reste à `$B100`.

La banque atteint ses 255 ID publics et 32 mots de dictionnaire : un nouveau
texte public demande désormais de regrouper ou retirer une entrée existante.

TREE : `$5800–$5FFE`, un octet libre ; STATUS : `$9600–$B0F6`, neuf libres ;
STATX : `$B100–$B5FB`, quatre libres. TEXT : `$0A00–$0FFC`, trois libres ;
HICODE : `$BE00–$BEFE`, un libre. DAT : 67 745 bruts / 57 550 stockés,
19 enregistrements ; XL : 381/1600 blocs, cinq parties.

### Aperçu des soins STATUS (17 octobre 2026)

Les dix-neuf commandes médicales passent de chaînes locales MEDVIEW à des
suffixes bankés. Le lecteur retourne le pointeur A/Y dans `tb_buf` avant que
le geste soit imprimé ou copié dans `inbuf`. Les nouveaux conseils et la
légende partagent également des entrées à NUL internes déjà existantes ;
leur premier texte reste identique pour les anciens appelants. La banque
reste à 255 ID publics et 32 mots, avec des enregistrements de 118 octets
au plus. Les conseils répétés sont partagés pour limiter le stock auxiliaire.

Le lecteur des conseils et les seize durées résident dans STATUS ; le
formateur de rangée 22 reste dans MEDVIEW. `overlay_text+72..73` sert
uniquement au geste et à l’objet en cours de consultation. La lecture des
stocks, positions et lumière n’applique aucun soin. Les commandes natives
et leurs durées ne sont pas modifiées. Le pied de page XL n’utilise plus
son détour historique de l’édition texte retirée.

MEDVIEW : `$5800–$5FD8`, sept octets avant la queue MEDVX de `$5FE0` ;
STATUS : `$9600–$B0FF`, plein ; STATX : `$B100–$B5FB`, quatre libres.
TREE : `$5800–$5FFE`, un libre ; TEXT : `$0A00–$0FFC`, trois libres ;
HICODE : `$BE00–$BEFE`, un libre. GCODE finit à `$51AA`, GDATA à `$5753`.
DAT : 68 132 bruts / 57 458 stockés, 19 enregistrements ; XL : 381/1600
blocs, cinq parties. Les marges des régions auxiliaires restent vérifiées
par la construction des six paquets et leurs tests de chargement.

### Retour aux soins et frontières du lecteur de textes (17 octobre 2026)

Les trois octets `sr_condition`, `sr_focus`, `sr_gesture` résident en BSS,
hors état SAVE, et sont tous écrits avant emploi. STATUS prépare une file
dont la dernière étape `S_CARE_RETURN` porte un garde sans condition ; les
préparations existantes gardent leurs contrôles natifs. GRID laisse le résultat
lisible, puis reconstruit le rang depuis `injury_active` avant de composer
STATUS. `pg_open` porte le bit 6 et le rang pour cette seule réouverture ;
`sr_open` le consomme et restaure le geste. Une rencontre termine toujours
la file ; un prérequis refusé saute le soin et propose la lecture du refus.

Le corps historique de `page_top` devient explicitement le tampon PF_BUF
de 80 octets ; il ne doit jamais être réutilisé pour du code. Les sept noms
d’onglets et les libellés de stock/conditions rejoignent des suffixes bankés,
ce qui libère STATUS pour les routines de préparation et de réouverture.
Le module EQUIPMENT (33), chargé à l’ouverture de sa page, rejoint les
modules compressés de XL. Les mises à jour médicales restent dans leur
format précédent ; la décompression est contrôlée par les tests de transfert.

`tf_get` rétablit explicitement la retenue avant de calculer l’alignement
du texte dans `tb_buf`. La soustraction des offsets bas peut l’effacer
lorsqu’un enregistrement traverse 256 octets ; elle ne doit pas influencer
l’adresse de destination. Les 255 décodages sont comparés aux sources,
dont 26 traversées de page ; cet octet occupe la dernière place de HICODE.

STATUS : `$9600–$B0D6`, 41 octets libres ; STATX : `$B100–$B5F8`, sept libres.
MEDVIEW : `$5800–$5FDF`, plein avant MEDVX ; GRID : `$A300–$AEA6`, 345 libres.
HICODE : `$BE00–$BEFF`, plein ; TREE : `$5800–$5FFE`, un libre ; TEXT :
`$0A00–$0FFC`, trois libres. GDATA finit à `$5753`, BSS à `$577B`, quatre
octets avant REGIONTEXT. EQUIPMENT : 1 714 bruts / 1 458 stockés, soit
256 octets auxiliaires récupérés. DAT : 68 088 bruts / 57 862 stockés,
19 enregistrements ; XL : 382/1600 blocs, cinq parties.

### Présence de l’attelle et du feu dans STATUS (17 octobre 2026)

`med_splint_here` extrait le contrôle natif de USE SPLINT en un prédicat
sans écriture : place absente, sol avec les deux coordonnées, autres positions
natives. La commande et l’aperçu le partagent. `med_have`, dans STATUS,
emploie ce prédicat pour l’attelle, `fire_on` pour le feu et le test `have`
existant pour les lunettes/médicaments. Aucun appel SIM n’est nécessaire
pendant la consultation. Les objets de soin hors premier jeu ne lisent
pas les tableaux de doses du premier jeu.

La table de seize objets de soin rejoint STATUS ; le code MEDVIEW ajoute
le filtre des doses. Aucun état sauvegardé, scratch ou ID de texte ajouté.
STATUS : `$9600–$B0FA`, cinq octets libres ; MEDVIEW : `$5800–$5FDC`, trois
octets avant MEDVX ; STATX : `$B100–$B5F8`, sept libres. HICODE reste plein
à `$BEFF`. DAT : 68 088 bruts / 57 864 stockés, 19 enregistrements ; XL :
382/1600 blocs, cinq parties.

### Prérequis de lame en lecture seule (17 octobre 2026)

`med_tool_check` partage le contrôle natif d’outil en usage : coordonnées
entières d’activation, bits de `care_tools`, accès par `have`. Y=0 interroge
sans écriture ; `care_tool_in_use` entre avec Y=1 pour conserver le nettoyage
natif des indicateurs d’une autre case. L’aperçu et la préparation de CUT BODY
emploient le mode sans écriture. Les tables de conseils rejoignent STATUS,
qui héberge aussi le choix des trois messages et leurs suffixes bankés.
Aucun état SAVE ni scratch supplémentaire n’est ajouté.

Les trois messages partagent `om_object_label`, aux offsets 11, 24 et 61.
Les mots qualitatifs de température, altitude et terrain partagent
`om_in3_label`, aux offsets 5/12/19/26/33, 40/47/54 et 61/67/73/79.
Les préfixes historiques, espaces de largeur fixe et le scratch `g2` restent
identiques ; les trois ID identiques de `st_care_ids` deviennent une constante.
La banque conserve 255 ID publics, 32 mots et 118 octets maximum par texte ;
les 255 décodages sont vérifiés, dont 27 traversées de page.

STATUS : `$9600–$B0FF`, plein ; MEDVIEW : `$5800–$5FDA`, cinq octets avant
MEDVX ; STATX : `$B100–$B5F8`, sept libres. HICODE reste plein à `$BEFF` ;
GDATA et BSS ne bougent pas. DAT : 68 220 bruts / 57 671 stockés,
19 enregistrements ; XL : 382/1600 blocs, cinq parties. Les six paquets
restent dans leurs limites. La comparaison native porte sur 163 variables,
1 324 octets, après 24 étapes et conserve notamment le scratch d’affichage.

`care_hypothermia` ne doit pas appeler `al_percent` dans ALERTS : cette
fenêtre contient alors MEDVIEW. Le déplacement du code faisait coïncider
l’adresse cible avec le saut lui-même et bouclait sur WARM d’un corps froid.
`care_percent` conserve localement les 25 octets de conversion native
(clamp, deux multiplications par dix, entier, borne 100), vérifiés par
`test_care.py`. Cette copie occupe une partie de la marge MEDVIEW récupérée.

### Aperçu des sources d’eau médicales (17 octobre 2026)

`med_water_word` reste dans STATUS : WET BODY vérifie front/immersion puis
source naturelle avant `have`, DRINK vérifie `have` avant la source naturelle.
`med_water_near` ne charge pas SIM : sur carte fine, `inventory_here` interroge
l’atlas et restaure `geo_wooded`/`geo_water_kind` ; sur carte historique,
`med_water_legacy` parcourt les neuf cases en bornant lignes et colonnes.
Ni `water_here` ni `care_water_near` ne sont appelés par la page. Aucun
`camp_untreated`, stock, soin ou RNG n’est modifié par cet aperçu.
Les quatre octets `overlay_text+74..77` portent seulement les coordonnées et
compteurs du parcours historique, hors SAVE. Le cache d’atlas peut évoluer.

Les messages partagent `om_to_use` aux offsets 4/30/56/72. Les treize noms
du second jeu partagent `om_to_sense` à partir de 7 ; `inventory_name` retourne
leur pointeur dans `tb_buf`. `ob_cmd` doit donc lire le nom avant de construire
son texte dans ce même tampon : le préfixe SENSES et son NUL protègent le
nom contre les six octets maximum du verbe. Les quatre directions et leurs
espaces de largeur fixe rejoignent `om_in3_label` aux offsets 85/91/97/103 ;
le scratch natif `g2=5` est conservé. Toujours 255 ID et 32 mots de dictionnaire.

La zone `page_foot` réserve explicitement les 53 octets copiés de XLRES
(pad, rideau, crochet du cadre). Elle reste active et ne peut pas servir à
l’aperçu. Les anciens libellés de touches résidents deviennent des alias
vers les libellés XL, libérant le code du parcours des berges. L’édition
140 Ko historique n’est pas reconstruite.

MEDICAL (17) est maintenant compressé dans le stock auxiliaire de XL,
comme il l’était sur l’édition historique : 2 023 bruts / 1 472 stockés,
551 octets récupérés. `mem_fetch` le décompresse avec le chemin existant ;
les tests de transfert comparent tous les octets, les gardes et les banques.
La comparaison native contrôle l’état après 24 étapes de simulation.

MAIN finit à `$6FFC`, trois octets libres ; STATUS à `$B0FC`, trois libres ;
MEDVIEW à `$5FDA`, cinq avant MEDVX ; STATX à `$B5F8`, sept libres.
GDATA, BSS et SAVE ne bougent pas. DAT : 67 829 bruts / 57 605 stockés,
19 enregistrements ; XL : 382/1600 blocs, cinq parties.

`DRINK_FIDELITY` reste à zéro : la consommation d’eau garde les calculs
d’hydratation du scénario de référence et n’appelle pas `drink_care`.
Le test d’onces vérifie cette limite existante, consignée dans le TODO ;
il n’active pas silencieusement le sélecteur 6. WET BODY conserve le 9.

### Conditions de USE FIRE dans STATUS (17 octobre 2026)

`med_fire_word` suit `use_fire`/`use_checks` sans charger CAMP ni SIM :
feu non nul, abri, eau sur la cellule, combustible actif, pluie, vent >=41.
`med_water_native` fournit le contrôle de cellule pour les deux formats de
carte et restaure les deux indicateurs géographiques. Les conditions d’eau
et de météo réutilisent les textes des allumettes, identiques pour ce refus.
Les nouveaux textes partagent `om_to_worn` aux offsets 5/31/56. Le feu sort
de `med_items` et du prédicat de présence `med_have` : aucun suffixe HERE
ni compteur de doses ne complète désormais son conseil contextualisé.

Les six commandes MENU/OPTIONS partagent `om_to_can`, offsets 8/13/28/21/
33/45 (SAVE/RESTORE/QUIT/NATURE/IGNORE FOOD/GET FOOD). `pg_run` conserve le
pointeur dans `gp2` avec report de retenue et copie dans `inbuf` avant de
quitter la page. Le titre QUIT du cadre garde sa chaîne locale, car la
composition différée du cadre exige un pointeur stable.

Les quatre titres de groupes OBJECTS partagent `om_to_body`, offsets
5/10/16/21 (WORN/HANDS/PACK/LOCAL HUNG). Ils sont imprimés par le lecteur
de suffixes déjà utilisé par les autres titres ; les listes, leur défilement
et les commandes gardent leurs règles. Aucun état SAVE ni scratch ajouté.
Toujours 255 ID publics et 32 mots de dictionnaire ; les 255 décodages
passent, dont 28 traversées de page.

STATUS finit à `$B0FB`, quatre octets libres ; MEDVIEW à `$5FDA`, cinq avant
MEDVX ; STATX à `$B5F8`, sept libres ; MAIN à `$6FFC`, trois libres.
GDATA et BSS ne bougent pas. DAT : 67 952 bruts / 58 042 stockés,
19 enregistrements ; XL : 382/1600 blocs, cinq parties.
