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
| `RESBSS` | `$B988-$B9DA` | 83 | E | Compteurs, vecteur RESET et bitmap ProDOS sauvegardés, chemin de NEOWILD.GEO (gabarit de `NEOWILD.END`/`.HOF`), compteurs de géographie fine (§ 9.10) |
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
