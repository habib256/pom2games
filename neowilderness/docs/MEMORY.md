# Neowilderness — inventaire et plan mémoire 128 Ko

Ce document décrit la version du lot 3, le bandeau et les panneaux couleur
(§7) et le TOPO DHGR (§8) du lot 4, la géographie fine résidente du
lot 5 (§9), puis les garde-fous vérifiés (§10) et le relevé final du
lot 6 (§11) : démarrage ProDOS 8 depuis `dist/NEOWILDERNESS.po`, tous les
modules préchargés en RAM auxiliaire (lots 1–2), paysage DHGR sur une seule
page (`$2000-$3FFF` principale et auxiliaire), TOPO dessiné en DHGR depuis
la carte résidente (§8) et, sur les cartes natives, atlas de la géographie
fine en carte langage auxiliaire (§9). Les chiffres viennent de `build/wild.map`, `build/wild.lbl`,
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
| `TEXT` (`wildtxt.bin`) | `$0A00-$0FB3` | 1 460 | K/E | Messages, constantes, tables de rotation, quelques états textuels |
| `LOWDATA`/`LOWCODE`/`LOWTEXT` (`wildlo.bin`) | `$1000-$1EA6` | 3 751 | C/K/E | Projection, **lignes DHGR déroulées** (`drows`, 1 601), effacement des deux banques, ruban de boussole et `hud_col` (488), LOOK, raccourcis, noms d'objets, compteurs de charge |
| `LOWCACHE` | `$1EA7-$1FA6` | 256 | T | `row_n0`, recalculé par `project_init` |
| page DHGR, moitié principale | `$2000-$3FFF` | 8 192 | vidéo | Vue logique 16–159, bandeau et panneaux 0–15, cache 160–175 (lignes logiques 0–15) ; TOPO y est dessiné en DHGR (lignes 0–159, module 0) |
| `GCODE`/`GDATA` (`wildgame.bin`) | `$4000-$5748` | 5 961 | C/E/K | Logique résidente, état de la partie (`px`…`it_*`, horloge, santé, météo, hasard), chargeur de modules ; humeurs DHGR (290 octets de tables), choix d'humeur, altitudes `sun_alt8`…`sky_mood`, `hgr_row`/`hgr_row2` (TOPO), modes vidéo |
| `BSS` | `$5749-$5770` | 40 | E/T | `video.s` (unité /RAM) et `mli.s` ; palette courante de la trame (`cur_pal`, couleurs des sprites), variables des bandes de 8 lignes ; mis à zéro par le chargeur |
| fenêtre `$5800` | `$5800-$5FFF` | ≤ 2 048 | C/K/T | Un module à la fois (tableau 2) ; son image est restaurée à chaque chargement |
| `CODE`/`RODATA` (`wild.bin`) | `$6000-$6FDB` | 4 060 | C/K | Démarrage, moteur de vue, passes DHGR (`dspan`, `column_setup`, tables d'entrée des lignes), texte 40 colonnes propre, sprites, saisie, impressions, transitions, `video.s`, `mli.s` |
| `WILDMAP` | `$7000-$94FF` | 9 472 | K | En-tête 64 octets et grille 112 × 84 |
| `SCRATCH` | `$9500-$95FF` | 256 | T | `overlay_text` (160) : couleurs de colonne des sprites **et** flottants temporaires du ciel ; puis `scene_*`, thermique, saisie |
| `ENVIRON`+`THERMAL` (`wildsim.bin`) | `$9600-$B5E7` | 8 168 | C/K/T | Simulation ; données de l'image rechargées à chaque activation (même sémantique que le BLOAD HGR) |
| `RESCODE` (`wildres.bin`) | `$B600-$B8E5` | 742 | C/K | Répertoire des modules (161), `mem_fetch`, boucle de pile, `mli_call`, sortie/RESET |
| `RESBSS` | `$B8E6-$B915` | 48 | E | Compteurs (dont `geo_queries`, `geo_decodes`), vecteur RESET et bitmap ProDOS sauvegardés |
| `IOBUF` | `$BA00-$BDFF` | 1 024 | T | Tampon d'E/S ProDOS (chargeur) |
| `GEOAUX` (`wildgeo.bin`) | `$D480-$D7CA` auxiliaire | 843 | C/K | Requête et décodeur de la géographie fine (`src/geoaux.s`), carte langage auxiliaire vue banque 1 ; chargé avec l'atlas sur les cartes natives seulement (§9) |
| `SAVE` | `$BE00-$BEFF` | 256 | E | Page zéro de ProDOS à l'entrée, restaurée à la sortie |
| `SYSSTUB`+`LOADER` (`NEOWILD.SYSTEM`) | `$2000` puis `$9600-$9EC7` | 2 216 | C/T | Chargeur transitoire, exécuté dans la fenêtre SIM avant la première activation |

Modules de la fenêtre `$5800` (identifiants de `overlay_load`, inchangés) :

| ID | Image | Octets | ID | Image | Octets |
|---:|---|---:|---:|---|---:|
| 0 | `wildtop.bin` (TOPO DHGR, lot 4) | 1 531 | 12 | `wildtrv.bin` | 2 045 |
| 1 | `wildvoc.bin` | 2 047 | 13 | `wildinp.bin` | 1 442 |
| 2 | `wildscr.bin` | 2 040 | 14 | `wilditm.bin` | 1 647 |
| 3 | `wildsim.bin` → `$9600` | 8 191 | 15 | `wildhud.bin` | 1 628 |
| 4 | `wildwat.bin` | 495 | 16 | `wildsta.bin` | 2 048 |
| 5–9 | épave, ours, couguar, crotale, cabane | 1 900, 781, 539, 485, 1 133 | 17/18 | `wildmed.bin` (médical + dangers) | 2 045 |
| 10 | `wildsit.bin` | 1 758 | 19 | `wildmvi.bin` | 878 |
| 11 | `wildprj.bin` | 1 134 | 20–22 | `wildtre`, `wildadv`, `wildout` | 916, 1 971, 1 982 |

Les IDs 23–46 (24 banques de géographie fine lues dans `NEOWILD.GEO` sur
les disques de comparaison) n'existent plus depuis le lot 5 : `wildgeo.bin`
est désormais l'image du décodeur résident (§9).

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
| SITES | GAME, LOW, MAIN, FOREST |
| TOPO | GAME, MAIN (tables de phase et `dc_pat` de `dhgr.s`, texte 40 colonnes) |
| autres modules | GAME, LOW, MAIN |

Règle conservée : un module n'en charge pas un autre dans sa propre fenêtre
sans repasser par du code résident. Les appels de modules vers SIM supposent
que la fenêtre SIM contient du code valide : dans la version HGR, HGR page 1
pouvait contenir l'image à ce moment (voir §6).

### Adresses absolues

- Carte `MAP = $7000` (`M_*`), fenêtre `$5800` (`cmp $5800` des
  sprites, `unpack` supprimé), géographie fine `$D000-$FFF9` en carte langage
  auxiliaire, vue banque 1 (`GEO_CELLS`, `GEO_WOODS`, `geo_atlas`), lignes DHGR `$2000` déroulées dans `drows`
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
| `$0200-$03CF` | inutilisé (ProDOS/Moniteur) ; `$0300-$037F` : table niveau → couleur de TOPO (lot 4), le temps de son dessin | — |
| `$03D0-$03FF` | vecteurs ProDOS ; RESET → `reset_exit` pendant le jeu | — |
| `$0400-$07FF` | texte page 1 (intro, menus, 4 lignes mixtes, colonnes impaires en DHGR) | — |
| `$0800-$0FFF` | bois, aide forêt, WILDTXT | 76 |
| `$1000-$1FFF` | WILDLO + cache de projection | 89 |
| `$2000-$3FFF` | page DHGR, moitié principale | — |
| `$4000-$57FF` | WILDGAME + BSS | 143 |
| `$5800-$5FFF` | fenêtre de modules | 0 à 1 553 selon le module |
| `$6000-$6FFF` | WILDERNESS | 36 |
| `$7000-$94FF` | carte | 0 |
| `$9500-$95FF` | scratch | 0 |
| `$9600-$B5FF` | fenêtre SIM (chargeur au démarrage) | 24 |
| `$B600-$B9FF` | RESIDENT | 234 |
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
restent non marqués comme avant le lot 5, bien que plus rien n'y lise le
disque. Le bitmap d'origine est rétabli à la sortie. Jusqu'au lot 6, la
table `game_pages` de `src/boot.s` (une macro `.define` à paramètre) était
assemblée en 24 octets nuls par ca65 2.18 : aucune page n'était marquée.
Sans conséquence en jeu (aucun appel MLI après le préchargement), mais le
garde-fou n'existait pas ; la table est désormais écrite octet par octet et
`test_prodos.py` vérifie le bitmap exact pendant la partie.

### RAM auxiliaire

| Zone | Usage | Libre |
|---|---|---:|
| `$0000-$01FF` | page zéro et pile auxiliaires : seulement pendant une requête de géographie fine (`ALTZP`, interruptions masquées : registres du décodeur `$10-$F0`, adresses de retour) | — |
| `$0200-$03FF` | code du pilote /RAM de ProDOS (appelé par FORMAT à la sortie) : intouchable | — |
| `$0400-$07FF` | texte : colonnes paires des 4 lignes mixtes (espaces, écrits par `show_dhgr`) | — |
| `$0800-$1FFF` | PRJ, cabane, TRE, MVI, ours, couguar, crotale | 278 |
| `$2000-$3FFF` | moitié auxiliaire de la page DHGR (`PAGE2` sous `80STORE`) | — |
| `$4000-$BFFF` | SIM vierge, STATUS, VOC, TRV, MED, SCR, ADV, OUT, épave, SIT, ITM, HUD, TOPO, INP, WAT | 10 |
| carte langage banque 2 (`$D000-$DFFF`) | libre (modules seulement) | 4 096 |
| carte langage banque 1 (`$D000-$DFFF`) et `$E000-$FFF9` | géographie fine (§9) : cache de 4 tuiles (1 152), requête et décodeur (843), atlas (≤ 10 287) ; vide sur une carte héritée | 12 282 (héritée), 3 908 (Sierra) |

Placement des modules : premier emplacement libre, du plus grand au plus
petit, dans l'ordre des zones ci-dessus, la carte langage limitée à la
banque 2 `$D000-$DFFF` (`tools/build_disk.py`) ; la banque 1 et
`$E000-$FFF9` appartiennent à la géographie fine (§9). Total stocké :
38 624 octets (30 456 de modules et sprites, TOPO compris, et 8 168 de SIM ;
l'alias 18 ne coûte rien), plus 843 + atlas sur une carte native. Libre :
288 octets en RAM auxiliaire principale, 4 096 en banque 2, 12 282 dans la
zone de géographie d'une carte héritée (3 908 avec l'atlas Sierra),
`$FFFA-$FFFF` exclus (lot 3 : 45 561 stockés, 373 et 9 356 libres, avec la
feuille TOPO HGR de 8 192 octets). Seul le code de la géographie fine
s'exécute en RAM auxiliaire (§9) : hors stock de modules, elle sert à la
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
  `overlay_load` au lot 3 ; 18,1 au lot 4, le plus petit module (WAT,
  495 octets) étant passé de la carte langage à la RAM auxiliaire principale,
  où la boucle est d'abord recopiée dans la pile, soit environ 35 ms pour 2 Ko et 140 ms pour SIM.

La simulation conserve sa sémantique de rechargement : chaque activation
recopie l'image vierge (8 191 octets), comme le BLOAD vers `$2000`. Le
drapeau `sim_loaded`, `ui_dirty` et le passage en texte pendant le calcul
sont conservés pour garder l'affichage identique ; le redessin qui suit reste
nécessaire puisque le temps a pu avancer.

## 5. Démarrage et fichiers

Volume `NEOWILDERNESS`, 280 blocs (5,25 pouces) : `PRODOS` (17 128 octets),
`NEOWILD.SYSTEM` (2 216 ; 2 267 au lot 4, avant le retrait du chemin de `NEOWILD.GEO`) et
`NEOWILD.DAT` (50 602 au lot 5 ; 50 787 au lot 4 ; 53 031 au lot 3 ; 50 620
aux lots 1–2). 148 blocs occupés, **132 libres** (lot 4 : 149 et 131).
Relevé du lot 6 (§11) : `NEOWILD.SYSTEM` 2 212 octets, `NEOWILD.DAT`
50 470 octets en 11 enregistrements, démarrage en 16 appels MLI dont
13 lectures, 50 982 octets lus (le relevé précédent indiquait 12
enregistrements, 17 appels, 14 lectures et 51 114 octets). Une carte native ajoute un enregistrement
(décodeur + atlas) : Sierra 56 919 octets, 161 blocs ; carte générée native
162 blocs, 18 appels MLI dont 15 lectures, 58 074 octets lus, premier écran
jouable 30,41 s contre 28,75 s (§9). Les mesures de
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
auxiliaire garde 16,5 Ko libres depuis le TOPO DHGR (9,7 Ko au lot 3, §6).

## 6. Comptage honnête et risques

- Budget initial du TODO : 78 839 octets. Réel : RAM principale résidente
  hors vidéo et carte 15 319 octets d'images (dont 904 RESIDENT) et 294 de masque des bois, fenêtres
  d'exécution 2 048 + 8 192, RAM auxiliaire 38 746 octets stockés (lot 4).
  Les temporaires partagés ne sont comptés qu'une fois : `overlay_text`
  (sprites/ciel), `$50-$A3` (rendu/ROM), fenêtre SIM (chargeur/SIM),
  `$2000` (vue/TOPO DHGR/tampon du chargeur), `$7000` (carte/décodage du
  chargeur).
- Les copies vierges en RAM auxiliaire doublent les fenêtres : SIM coûte
  16 Ko au total (exécution + image), chaque module 2 Ko + sa taille.
- Appels de modules vers SIM : la référence HGR (tête de `../wilderness`)
  charge SIM avant les sondes de rive de SWIM ; avant cette correction,
  SWIM juste après un rendu exécutait l'image de la vue et s'arrêtait dans
  le Moniteur. La fenêtre SIM n'étant plus jamais écrasée par la vue, ce type
  d'oubli ne plante plus en 128 Ko, mais reste un écart de comportement
  à éviter : tout appel vers SIM doit passer par `overlay_load` 3.
- Géographie fine (lot 5, §9) : seul code exécuté en RAM auxiliaire, avec
  `ALTZP` actif, donc page zéro, pile et carte langage auxiliaires ; toute
  interruption y serait détournée par les vecteurs auxiliaires : `cell_native`
  masque les interruptions jusqu'à 47 ms (pire décodage) et suppose `RAMRD`
  et `RAMWRT` inactifs (toujours vrai hors transferts). Les modules n'ont
  plus que 4 Ko de carte langage (banque 2). Le format natif limite l'eau au
  niveau 63 (bit 6 = lac) ; `build_disk.py` refuse un atlas de plus de
  10 287 octets.
- DHGR (lot 3) : le code DHGR ne peut pas s'exécuter en RAM auxiliaire ;
  il a pris la place du code HGR retiré (§7). Après le lot 3 il ne restait
  que 128 octets libres en RAM principale résidente. Le bandeau couleur du
  lot 4 (§7) rend 274 octets, le TOPO DHGR (§8) 16 (`show_hgr` retiré ;
  `hgr_row`/`hgr_row2`, 56 octets, restent pour TOPO) et le lot 5 (§9)
  220 : **578 octets libres** mesurés après fusion, en cinq zones. Toute
  fonction d'interface supplémentaire doit encore vivre dans un module de
  la fenêtre `$5800` ou libérer de la place.

## 7. Lot 3 : page DHGR et inventaire

Page unique `$2000-$3FFF`, principale et auxiliaire. `80STORE` et `HIRES`
restent actifs pendant toute la partie ; `PAGE2` (`$C055`/`$C054`) choisit la
banque vue par le CPU, sans changer la page affichée. Le code, la pile et les
tables restent en RAM principale ; chaque passe auxiliaire s'exécute
interruptions masquées (`render`, `scroll`, `clear_rows`, `hud_col`), et
toutes les routines rendent la main banque principale sélectionnée.

| Rangées physiques | Contenu (deux banques) |
|---|---|
| 0–15 | bandeau : boussole (octets 16–23, colonnes couleur 56–83), panneaux de survie (octets 0–15 et 24–39), en pixels couleur (lot 4) |
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
libres (`NEOWILD.DAT` 53 031 octets, +2 411). Le lot 4 (§8) porte ces
chiffres à 144 octets principaux, 16,5 Ko auxiliaires et 131 blocs.

**Lot 4 : bandeau et panneaux en couleur** ([DHGR.md](DHGR.md) §11). Le
ruban et les panneaux dessinent des pixels couleur avec la petite police
DHGR ; plus aucun octet HGR doublé.

| Élément | Zone | Octets |
|---|---|---:|
| retiré : `hud_draw` HGR (263), bandes HGR 2–9 (280) | WILDLO | −543 |
| retiré : bande HGR 1 (40), `hud_border_byte` (25) | WILDTXT | −65 |
| retiré : `dbl_put` + demi-octets (69), `hgr_row`/`hgr_row2` (56), `hud_strip_lo/hi` (16), `hud_ptr` (12) | GCODE | −153 |
| retiré : `dbl_lo`, `dbl_x` | BSS | −2 |
| ajouté : `hud_draw` couleur (225), `hud_strip` (80) et masques de l'index (5) | WILDLO | +310 |
| ajouté : `hud_col` (137), `hud_row` (19), `hud_pen` (8), `hud_next` (14), partagés avec les panneaux | WILDLO | +178 |
| WILDHUD : police 4 × 5 en colonnes (236 au lieu de 413), styles par champ | module 15 | 1 727 → 1 628 |

Libre après le lot 4, RAM principale : 72 octets (`$0800-$0FFF`), 89
(`$1000-$1FFF`), 168 (`$4000-$57FF`), 36 (`$6000-$6FFF`), 37 (RESIDENT),
soit **402 octets** (+274), mesurés seuls ; 578 après fusion avec le TOPO
DHGR et le lot 5 (§6, `hgr_row` conservé). La fenêtre de modules garde 420 octets libres
avec WILDHUD. RAM auxiliaire : 9 828 octets libres (+99). La page zéro ne
change pas : `hud_col` emprunte le scratch de passe (`dm`…`dp`) et les
octets `be`/`row0` de l'ancien ruban.

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

## 8. Lot 4 : TOPO DHGR généré en RAM

La feuille TOPO HGR de 8 192 octets (générée au build par
`tools/graphical_topo.py`, copiée de la RAM auxiliaire vers `$2000` et
affichée en HGR simple) est remplacée par le module 0 `wildtop.bin`
(`src/topo.s`, fenêtre `$5800`), qui dessine TOPO en DHGR couleur à
l'ouverture depuis la carte résidente (`$7000`) et le masque des bois
(`$0800`). `tools/topo_ref.py` en est le modèle exact ;
`tests/test_graphical_topo.py` compare les deux banques des lignes 0–159
(carte par défaut, carte de remplacement, après WALK). Rendu décrit dans
`docs/DHGR.md` §12.

| Élément | Avant (lot 3) | Lot 4 |
|---|---:|---:|
| module 0 stocké en RAM auxiliaire | 8 192 (`topo`, fenêtre `$2000`) | 1 531 (`wildtop.bin`, fenêtre `$5800`) |
| tampons du module (`TOPOBSS`, non stockés, après l'image dans la fenêtre) | — | 488 |
| table niveau → couleur (`$0300-$037F` principal, temporaire) | — | 128 |
| `wildsit.bin` (`module_graphical_topo` retiré) | 1 912 | 1 758 |
| GCODE (`show_hgr` retiré) | 4 482 | 4 466 |
| RAM principale résidente libre | 128 | 144 |
| RAM auxiliaire libre (principale + cartes langage) | 373 + 9 356 | 651 + 15 893 |
| `NEOWILD.DAT` / blocs libres | 53 031 / 127 | 50 787 / 131 |
| octets copiés pour ouvrir TOPO (`xfer_bytes`) | 8 192 + 1 912 (SITES si absent) | 1 531 |
| ouverture de TOPO (`profile_actions.py TOPO`) | 172 031 cycles (0,169 s) | 1 023 974 cycles (1,004 s) |

`scr_topo` (résident) entre dans `overlay_load` après son test de cache
(`overlay_fetch`) : le module 0 est toujours recopié, compté dans
`overlay_reads`, et `overlay_current` vaut 0 (« rien de chargé ») ensuite,
comme avant. Le module garde le reste du protocole (`sim_loaded`,
`scene_drawn`, `shown` à 0, `ui_dirty` à 1) et le retour par `view_hide`,
`t_home`, `show_view_hidden`.

Coût de l'ouverture, cycles POM2 mesurés par compteur de PC
(`pcprof`) de `do_command` à `graphical_topo_key` : classement des 9 408
cellules 430 000 (≈ 46 cycles par cellule : niveau, deux comparaisons de
courbe, couleur), empaquetage de 84 lignes de carte et des lignes de
légende qui changent 210 000 (tables de 160 octets, une par fragment de
pixel), écriture des 160 lignes dans les deux banques 162 000 (la partie
carte est écrite dans les deux lignes d'une cellule en une passe), bois
41 000, repères 50 000 (lecture-modification-écriture pixel par pixel,
`div7` compris), le reste (légende, tables, adresses de ligne, copie du
module, rideau, texte) ≈ 133 000. L'objectif de la
préparation (0,7 M cycles) n'est pas atteint (mesure de la première
version ; la légende adaptée, l'encre des bois et le fond de P ne changent
le total que de −0,2 %) ; le classement est proche du
minimum dans cette forme, et le dessin se fait derrière le rideau texte.

## 9. Lot 5 : géographie fine résidente

Détail et mesures dans [GEOGRAPHY.md](GEOGRAPHY.md) § 9. Sur une carte
native (octet 37 de l'en-tête), `build_disk.py` ajoute un enregistrement
banque 1 de la carte langage auxiliaire à `$D480` : `wildgeo.bin` (843
octets : étiquettes, requête, décodeur) suivi de l'atlas (`$D7CB`,
≤ 10 287 octets, refusé au-delà). Le cache de 4 tuiles décodées
(`$D000-$D47F`) n'est pas stocké.

| Élément | Lot 4 | Lot 5 |
|---|---:|---:|
| géographie fine en jeu | `NEOWILD.GEO`, 24 banques de 2 Ko lues dans la fenêtre `$5800` | atlas résident (Sierra 6 379 octets) |
| lectures disque par pas (carte native) | ≥ 1 (2 Ko) | 0 |
| RESIDENT + RESBSS | 904 + 83 | 742 + 48 |
| RAM principale résidente libre | 144 | 364 |
| SIM (`wildsim.bin`) | 8 191 | 8 168 (pont de rechargement retiré) |
| carte langage auxiliaire, modules | `$D000-$FFF9` + banque 1 | banque 2 `$D000-$DFFF` |
| zone géographie (banque 1 + `$E000-$FFF9`) | — | 12 282, dont 1 152 de cache et 843 de code |
| `NEOWILD.DAT` par défaut / blocs libres | 50 787 / 131 | 50 602 / 132 |
| disque Sierra de comparaison | `NEOWILD.DAT` + `NEOWILD.GEO` (96 blocs) | 161 blocs en tout |

Invariants vérifiés par `tests/test_geo_resident.py` après des décodages :
commutateurs (`LCBNK2`, `LCRAM`, `RAMRD`, `RAMWRT`, `ALTZP`, `80STORE`,
`PAGE2`) inchangés, page zéro principale intacte, `$0200-$03FF` auxiliaire
(pilote /RAM) intact ; aucun appel MLI (compteurs et `watch` sur `$BF00`).

## 10. Garde-fous vérifiés

Relevé du lot 6 : ce que les tests de `make test` vérifient réellement, au
clavier dans a2shot (IIe enhanced).

- **Aucun accès disque après le préchargement** : compteurs `mli_calls`,
  `mli_reads`, `mli_bytes` inchangés et `watch` a2shot sur l'entrée MLI
  `$BF00` jamais atteinte : `test_resident.py` (scénario ordinaire, carte
  héritée et carte native), `test_journey_resident.py` (trajet crash →
  rangers, deux cartes), `test_screen_returns.py` (neuf retours d'écran),
  `test_geo_resident.py` (requêtes et partie native), `test_walk.py`,
  `test_sleep.py`. Aucune entrée DOS 3.3, RWTS ni BLOAD dans le code lié
  (analyse des listings, `test_resident.py`).
- **Chargements de modules = transferts RAM** : `overlay_reads` et
  `xfer_count` avancent ensemble (`test_journey_resident.py`, `test_walk.py`,
  `test_screen_returns.py`) ; modules attendus copiés par écran (`watch` sur
  `mem_fetch`) et octets copiés égaux à leurs longueurs
  (`test_screen_returns.py`) ; image exacte, aucun débordement de fenêtre
  (`test_transfers.py`).
- **Page zéro** : inchangée par chaque transfert (`test_transfers.py`) et
  par les requêtes de géographie fine (`test_geo_resident.py`) ; rendue à
  ProDOS identique à celle de l'entrée de `NEOWILD.SYSTEM`, à l'appel MLI
  QUIT, après QUIT Y et après Ctrl-RESET (`test_prodos.py`). Fin du
  scratch du rendu sous `$A4` : assertion d'édition de liens.
- **Pile** : pointeur identique (`S=$FD`) à chaque `do_command`, donc
  équilibré à travers commandes, écrans, transferts et décodages
  (`test_screen_returns.py`, `test_journey_resident.py`) ; sur tout le
  trajet crash → rangers, pile la plus profonde à `S=$DD` (34 octets), sans
  retour par `$00`, bien au-dessus de la boucle de copie `$0120-$015B`
  (`hwstack` a2shot, `test_journey_resident.py`).
- **Interruptions** : drapeau I identique à chaque `do_command` (masqué
  pendant la partie, `test_screen_returns.py`, `test_journey_resident.py`) ;
  `mem_fetch` et `cell_native` les masquent par `PHP/SEI … PLP` (code ; le
  bit I n'est pas relevé à l'intérieur de ces routines).
- **Commutateurs** : `LCBNK2`, `LCRAM`, `RAMRD`, `RAMWRT`, `CXROM`, `ALTZP`,
  `C3ROM`, `80STORE` inchangés par chaque transfert (`test_transfers.py`)
  et chaque requête fine, `PAGE2` compris (`test_geo_resident.py`) ; les
  quinze commutateurs mémoire et vidéo (hors VBL) identiques après chaque
  écran (`test_screen_returns.py`) ; commutateurs mémoire identiques en fin
  de trajet (`test_journey_resident.py`) ; modes vidéo et lignes texte
  (`test_dhgr_video.py`).
- **RAM auxiliaire réservée** : `$0200-$03FF` auxiliaire (pilote /RAM)
  intact après des décodages (`test_geo_resident.py`) et après tout le
  trajet (`test_journey_resident.py`) ; zones auxiliaires réservées et
  enregistrements de `NEOWILD.DAT` vérifiés sur le volume
  (`test_pack_boot.py`) ; atlas refusé au-delà du budget
  (`test_geo_resident.py`).
- **Vidéo** : effacements des deux banques sans toucher bandeau, trous ni
  colonnes conservées (`test_render_memory.py`) ; image complète (deux
  banques, trame rendue) et état identiques au retour de STATUS, M/B,
  INVENTORY, HELP, MAP, TOPO et des refus de QUIT (`test_screen_returns.py`).
- **Retour au système** : QUIT et Ctrl-RESET rétablissent texte 40
  colonnes, banques principales, ROM, vecteur RESET, bitmap et page zéro,
  reconstruisent /RAM vide et rendent la main au lanceur ; relance possible ;
  /RAM occupé effacé seulement après Y ; ][+ refusé ; bitmap marquant
  exactement `$08-$57`, `$60-$B9` et `$BE` pendant la partie
  (`test_prodos.py`).

Restent hors tests : le IIc (a2shot n'émule que le //e) et une machine
réelle ; le bit I n'est pas observé à l'intérieur des sections masquées.

## 11. Relevé final (lot 6)

Mesuré sur `build/wild.map`, `build/layout.json`, `make inspect` et
`tools/profile_loading.py --packings auto` (carte par défaut, `auto`).

RAM principale résidente libre, par zone :

| Zone | Fin occupée | Libre |
|---|---|---:|
| `$0800-$0FFF` (WILDTXT) | `$0FB3` | 76 (+ 4 en fin de `FORESTCODE`, `$09FC-$09FF`) |
| `$1000-$1FFF` (WILDLO + cache) | `$1FA6` | 89 |
| `$4000-$57FF` (WILDGAME + BSS) | `$5770` | 143 |
| `$6000-$6FFF` (WILDERNESS) | `$6FDB` | 36 |
| `$B600-$B9FF` (RESIDENT) | `$B915` | 234 |
| **Total** | | **578** (+ 4) |

Fenêtres d'exécution : `$5800-$5FFF` pleine avec WILDSTA (2 048 octets),
29 octets libres avec TOPO (1 531 + 488 de tampons) ; fenêtre SIM
`$9600-$B5FF` : 24 octets libres (8 168 octets de SIM).

RAM auxiliaire : 38 627 octets stockés (22 images distinctes, l'alias 18
ne coûte rien : 30 459 de modules et sprites, TOPO compris, et 8 168 de
SIM) ; libres 285 octets en RAM auxiliaire principale (`$1EEA-$1FFF` 278,
`$BFF9-$BFFF` 7), 4 096 en carte langage banque 2, 12 282 dans la zone de
géographie fine d'une carte héritée (carte native générée
`mkmap.py --native` : atlas 6 113 octets, 4 174 libres sur le budget de
10 287).

| Module | Octets | Module | Octets |
|---|---:|---|---:|
| 0 WILDTOP | 1 531 | 12 WILDTRV | 2 045 |
| 1 WILDVOC | 2 047 | 13 WILDINP | 1 442 |
| 2 WILDSCR | 2 043 | 14 WILDITM | 1 647 |
| 3 WILDSIM | 8 168 | 15 WILDHUD | 1 628 |
| 4 WILDWAT | 495 | 16 WILDSTA | 2 048 |
| 5 épave | 1 900 | 17/18 WILDMED | 2 045 |
| 6 ours | 781 | 19 WILDMVI | 878 |
| 7 couguar | 539 | 20 WILDTRE | 916 |
| 8 crotale | 485 | 21 WILDADV | 1 982 |
| 9 cabane | 1 133 | 22 WILDOUT | 1 982 |
| 10 WILDSIT | 1 758 | `wildgeo.bin` (cartes natives) | 843 |
| 11 WILDPRJ | 1 134 | | |

Images principales résidentes : WILDFOREST 214, WILDTXT 1 460, WILDLO 3 751,
WILDGAME 5 961, WILDERNESS 4 060, RESIDENT 742 (16 188 octets), plus le
masque des bois (294) et la carte (9 472).

Volume `NEOWILDERNESS` (280 blocs) : `PRODOS` 17 128 octets,
`NEOWILD.SYSTEM` 2 212, `NEOWILD.DAT` 50 470 (11 enregistrements,
65 006 octets bruts → 50 342 stockés) ; 148 blocs occupés, **132 libres**.
Carte native générée : 12 enregistrements, 162 blocs.

Démarrage (POM2, IIe enhanced, Disk II) : 16 appels MLI, dont 13 lectures,
50 982 octets lus ; ProDOS 8,70 s, préchargement 12,56 s (disque 9,82 s,
décodage LZ 2,10 s, copies 0,64 s), initialisation et premier rendu 7,00 s :
**premier écran jouable 28,26 s** (référence HGR/DOS 3.3 : 45,11 s, mesure
des lots 1–2). Ensuite, plus aucun appel MLI jusqu'à QUIT.
