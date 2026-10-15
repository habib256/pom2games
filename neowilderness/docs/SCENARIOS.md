# Scénarios, menu de démarrage, score et hall of fame (lot 7)

Plan détaillé du lot 7 de [TODO.md](../TODO.md). Il s'appuie sur l'état du
lot 3 ([MEMORY.md](MEMORY.md)) et sur les relevés du 13 octobre 2026 : les six
régions originales sont entièrement présentes sur les disques Apple II.
Rien n'est à récupérer de la version MS-DOS, qui n'a servi qu'à la
vérification croisée (ses fichiers région sont identiques octet pour octet
sur le bloc climat et les tables de terrain).

## 1. Ce que contiennent déjà les originaux

| Donnée | Emplacement | Taille | Vérifié |
|---|---|---:|---|
| En-tête de région (quatre fiches animales `$6000-$607F`, climat `$60A3-$60BA`, noms des quatre animaux `$60D0-$60FF`) | face Sierra Nevadas, piste SMALLDOS 0, secteur région + 8 (1 British Columbia, 2 Sierra Nevada, 3 Burma, 4 New Guinea, 5 Bolivia, 6 Chile) | 256 par région | extraits et décodés ([REGIONS.md](REGIONS.md)) ; bloc climat et filtres identiques au `.CIM` DOS, taux Sierra abaissés en DOS |
| Sprites d'animaux : tigre, éléphant, cobra, python, Dani, vipère, crocodile, puma, jaguar, fer-de-lance, anaconda, chat | face Journey, `T1D/S5`, `T1D/S9`, `T1D/SD`, `T1E/S0`, `T1E/S2`, `T1E/S6`, `T1E/S9`, `T1E/SD`, `T1F/S0`, `T1F/S5`, `T1F/S7`, `T1F/SA` | 464 à 1 227 | décodés et vus, tailles dans [REGIONS.md](REGIONS.md#4-sprites-de-la-face-journey-toolsre_graphicspy) |
| Sprites de sites : tente, igloo, tranchée, bille, rocher, cité perdue, poste de rangers | Journey `T16/S0`, `T16/S9`, `T16/SD`, `T16/SF`, `T17/S4`, `T00/S8`, `T01/S2` | 403 à 2 428 | décodés et vus |
| Gabarit d'introduction et six phrases de faune | `GO3.B` (face Sierra) | — | lu |
| Vocabulaire des animaux de toutes les régions | parseur (`$B201-$B9F6`) | — | documenté |

Le verrou de l'original est purement logiciel : `TMAKE0` lit la région en
`PEEK(950)` et `MENU` refuse toute carte ou sauvegarde d'une autre région.
Les « Country Disks » et le pack « Global Explorer » n'étaient donc qu'un
code région et une carte fournie. Nous ne possédons que la carte fournie de
la Sierra Nevada : les cinq autres scénarios utiliseront des cartes générées
par `tools/mkmap.py` avec les paramètres de région originaux, et seront
annoncés comme « reconstitués ».

Les règles de rencontre des régions 1 et 3 à 6 ne sont pas dans `fauna.s`
(filtres Sierra seulement) : elles sont dans les fiches animales de chaque
en-tête et ont été sondées sur l'original en patchant les octets de région
de TOPO (fiches, `$601F`, `$60A4-$60BA`, noms) avant GO1
([animals.md](logic/animals.md#règles-de-rencontre-des-six-régions)) : mêmes
formules qu'en Sierra, plus la règle des pacotilles de New Guinea.

## 2. Définition d'un scénario

Un scénario est un ensemble fixe et reproductible, condition d'un classement
honnête :

- une région (1 à 6) : climat, latitude, déclinaison, longitude, limite des
  arbres, indice climatique, faune (jusqu'à quatre espèces) ;
- une carte : la carte originale pour la Sierra Nevada, une carte générée à
  graine fixe pour les cinq autres ;
- des conditions de départ : 7 h, 6 mai, niveau « respectable » (4) par
  défaut, blessures initiales selon le niveau, comme l'original ;
- une humeur de palette propre à la région (§ 5).

Le niveau de difficulté (1 à 10) reste au choix du joueur et entre dans le
score. Le hasard (LFSR indépendant de la météo) varie d'une partie à l'autre :
deux parties du même scénario ne sont pas identiques, elles sont comparables.

**Voyage libre** (hors scénarios originaux) : même menu, choix d'une région
et d'un niveau, graine aléatoire pour les rencontres et la météo, score affiché
mais non classé. La génération de cartes en jeu (`TMAKE` prenait plus de trois
heures sur Apple II) est hors périmètre sur une disquette de 140 Ko ; une banque
de cartes supplémentaires n'y tient pas non plus (§ 4).

## 3. Menu de démarrage

Réalisé (étape 3) dans le chargeur `NEOWILD.SYSTEM` (fenêtre SIM, `$9600`),
toujours résident jusqu'au premier `overlay_load 3` :

1. Page de chargement (titre inverse NEOWILDERNESS, machine, auteurs de
   l'original et du portage, le but en deux lignes, « TYPE A COMMAND, THEN
   PRESS RETURN. HELP LISTS THE COMMANDS. ») et `LOADING...` pendant le
   tronc commun `NEOWILD.DAT` (12,1 s), **sans** carte, bois, sprites
   d'animaux, textes ni fiches de faune. La liste des commandes a quitté
   cette page : HELP la donne en jeu.
2. Menu texte 40 colonnes (Moniteur, page 1), une ligne par scénario
   `[1]`–`[6]` dans l'ordre de `tools/genmenu.py` `MENU_ORDER` (Sierra
   Nevada en tête, puis British Columbia, Burma, New Guinea, Bolivia,
   Chile ; `menu_regions` traduit la touche en région, `menu_rows` donne
   la ligne d'une région) : touche, nom (colonne 2), terrain et température
   (colonne 20 : « FOREST, MILD »), meilleur score à droite (colonne 35,
   en-tête `BEST` sur la ligne 1 ; `-` sans entrée dans `NEOWILD.HOF`) ;
   RETURN seul choisit la première ligne (`CHOICE (RETURN = 1, 1-7, H,
   Q)?`) ; puis
   `7 FREE JOURNEY    ANY REGION, NOT RANKED` et `H HALL OF FAME    Q QUIT
   TO PRODOS`. Les mots sont dérivés par `tools/genmenu.py` des en-têtes de
   région (`regions.json` : jungle, précipitations) et des en-têtes de carte
   (températures) ; la phrase de faune de l'original apparaît au crash
   (« WILDLIFE: … »), la limite des neiges dans STATUS.
3. Niveau sur la ligne 12 (`MENU_ROW`) : `LEVEL 1-10 (RETURN = 4, ESC)?`, un ou deux
   chiffres puis RETURN ; hors plage : bip et nouvelle saisie ; ESC revient
   au choix. `[7]` demande d'abord la région (`1`–`6`, mêmes touches que le
   menu, ESC). `[H]` affiche le hall of fame dans l'ordre du menu (six
   tables lues avant le menu, aucun accès disque) ; `[Q]`
   rend la main à ProDOS.
4. L'introduction revient, avec « SIERRA NEVADA, LEVEL 4 » (« (FREE) » pour
   un voyage libre) au-dessus de `LOADING...`, et reste affichée pendant la
   lecture du paquet `NEOWILD.R1`…`R6` (même format, même boucle, un OPEN de
   plus), l'initialisation et le premier rendu ; puis `start`.

Le chargeur écrit le niveau en `MAP+22` et le genre de voyage en `MAP+33`
(0 scénario, 1 voyage libre, octet libre de l'en-tête). Le relief et la base
d'altitude des cartes restent ceux de leur génération au niveau 4 : le
niveau choisi règle ce que le jeu lit dans `+22` (probabilité de rencontre,
et plus tard le score). Voyage libre : même carte que le scénario de la
région, mais générateurs météo (`weather_seed`), faune (`fauna_rng`) et eau
(`water_rng`) réensemencés par le nombre de tours d'attente au menu ;
classement exclu (étape 6 : le module lit `journey_kind`, copie résidente
de `MAP+33` ; `MAP+33` sert aussi aux quantités d'aliments, HOF.md § 10).

Latence mesurée après RETURN (`tools/profile_loading.py`) : 0,09 s de
réaffichage, 3,0 à 3,1 s de paquet, 6,4 à 7,1 s d'initialisation et de
premier rendu, soit **9,5 à 10,2 s** jusqu'à la première vue (Sierra 10,24 s,
Burma 9,65 s, Chile 9,49 s) ; le menu apparaît 21,4 s après la mise sous
tension. Le menu après le tronc commun est gardé : il raccourcit l'attente
entre le choix et la première vue, et le hall of fame s'affichera avec les
routines texte déjà résidentes.

Retour au menu après une partie (mort, arrivée, QUIT) : `quit` charge INPUT
et saute à `module_end`, qui lit et exécute `NEOWILD.END` (score et hall of
fame, § 7–8) ; après « PRESS A KEY FOR THE MENU. », `module_restart`
restaure le système comme `prodos_exit` (`prodos_restore`), relit
`NEOWILD.SYSTEM` à `$2000` et y saute : chargeur neuf, tronc et hall of fame
relus, aucun état de partie conservé. Ctrl-RESET pendant la partie et `Q` au
menu reviennent à ProDOS.

Tests et outils : le volume s'arrête au menu ; `tests/common.py` y répond
« 2, RETURN » (Sierra Nevada, niveau 4 : `MENU_SKIP`) avant le premier pas
de chaque script, sauf si le script s'arrête dans le chargeur avant le menu
(`LOADER_PHASE`) ou passe `menu=False` ; `menu_keys(choix, niveau)` sert aux
autres choix. `tools/profile_actions.py`, `tools/profile.py` et
`tools/profile_loading.py` répondent au menu de la même façon.

Mémoire : le menu vit dans le chargeur (fenêtre SIM, 4 943 octets avec la
lecture du hall of fame, table d'enregistrements en `$B500`) ; aucune place
résidente n'est consommée pendant la partie, sauf `module_end` et
`module_restart` dans le module INPUT.

## 4. Paquets de région et chargement sélectif

Réalisé (étape 2). Le tronc commun garde le moteur, les modules de
commandes, la simulation et les sprites communs (épave, cabane). Un paquet
charge, aux adresses prévues par ses enregistrements :

| Contenu | Destination | Octets bruts | Remarques |
|---|---|---:|---|
| Sprites des 2 à 4 espèces | RAM auxiliaire, modules 6, 7, 8 et 23 (quatrième espèce) | 1 576 à 3 049 | zone de paquet `$B417-$BFFF` (taille de Burma) puis restes du tronc ; Chile reprend le puma de Bolivia |
| Correctifs dérivés des fiches animales `$6000-$607F` de l'en-tête (taux et filtres, seuils de réaction, noms, tailles de sprites, indice IGNORE) | images auxiliaires de TRAVEL, SITES, OUTDOOR, PROJECT, SUMMARY | 157 | étape 4 (`build_disk.fauna_patches`) |
| Bois | `$0800` (`WOODS`) | 294 | |
| Humeurs DHGR et couleurs des sprites (`dhgr_moods`…`dhgr_tables_end`) | `GCODE` `$4000` | 314 | tables de la région (étape 4, `dhgr_tables_rN.bin`) |
| Textes de région : nom 16, phrase de faune 40, noms des espèces 4 × 12, région, nombre d'espèces, nom d'introduction 22 | `REGIONTEXT` `$5780-$57FF` (fin de WILDGAME) | 128 | `$0300-$03CF` n'est plus libre depuis le lot 4 (LOWPAGE) |
| Répertoire des modules entier (26 entrées : 0–22, 23 quatrième espèce, 24 hall of fame, 25 étoiles) | `module_dir` (RESIDENT) | 182 | entrées vides : longueur 0 ; les banques de géographie fine passent aux IDs 32–55 |
| Carte : en-tête 64 octets (région en +32) et grille | `$7000` (`WILDMAP`), en dernier | 9 472 | la carte Sierra de build reçoit l'octet région 2 |

Épave, cabane et poste : un seul sprite de chacun sur la Journey, identique
dans les six régions ; épave et cabane restent dans le tronc (les copier
dans chaque paquet coûterait ≈ 36 blocs), le poste n'est pas dessiné par le
port et n'est pas chargé.

Mesures de fin de lot (`docs/MEMORY.md` § 9, paquetage `lz`) : paquets de
14 à 17 blocs (Sierra 15, Bolivia 17), tronc 91 blocs, volume 246 blocs,
**34 libres** ; RAM auxiliaire (carte langage principale comprise) libre
1 313 octets avec Burma (pire cas), 2 557 avec la Sierra ; RAM principale
86 octets libres. Aucun appel MLI après `start` (`test_resident.py`,
`test_menu.py` pour les six régions), état Sierra identique
(`test_reference_state.py`).

Budget RAM et étoiles : le module `wildsky.bin` (1 984 octets) ne tenait
dans la RAM auxiliaire d'aucune région ; la banque 2 de la carte langage
principale, que ProDOS 8 laisse libre après son code QUIT (`$D400-$DFFF`),
a rejoint le stock de modules et reçoit le code de tracé (MEMORY.md § 9.7).

Budget disque : la géographie fine du lot 5 ne tient pas en six atlas
(≈ 132 blocs pour 34 libres) : elle devra être calculée en RAM
(`GEOGRAPHY.md`, codec `coarse`) ou réservée à la Sierra (un atlas).

## 5. Couleurs par région

Réalisé (étape 4, [DHGR.md](DHGR.md) § 12). `tools/dhgr_palette.REGIONS`
ajuste, pour chaque humeur de jour, le sol, la neige, l'eau et les
couronnes des arbres : forêt boréale et neige basse (British Columbia),
conifères de la Sierra (référence inchangée), jungle de mousson et rivières
boueuses (Burma), forêt pluviale (New Guinea), altiplano ocre (Bolivia),
désert et éboulis (Chile). Les cinq zones de ciel, la crête et les règles de
nuit restent celles du lot 3. `tools/gendhgr.py --regions` écrit
`build/dhgr/dhgr_tables_rN.bin` (314 octets, couleurs des sprites de la
région comprises), chargé par le paquet. `test_dhgr_mood.py` vérifie chaque
table contre `tools/dhgr_ref.py` comme pour la Sierra.

## 6. Ciel nocturne : étoiles

**Réalisé (étape 5)** : la spécification de ce plan a été précisée et
mesurée dans [STARS.md](STARS.md) (79 étoiles, tables entières du moteur,
tracé par colonne), puis intégrée au jeu : module horaire `wildsky.bin`
(ID 25) dans le stock de modules, liste de 32 étoiles en WILDLO, code de
tracé exécuté dans la banque 2 de la carte langage principale (`$DF00`) ;
`tests/test_stars_game.py`. `LOOK STARS` reste optionnel (STARS.md § 11).
Le plan d'origine suit.

Au lot 3, le ciel de nuit reste noir : seuls la Lune et son éclairage sont
dessinés (`sky_position`, `sky.s`, éphémérides 1985). Le lot 7 dessine les
étoiles, qui dépendent du scénario par la latitude, la longitude et
l'hémisphère : Polaris à la hauteur de la latitude en British Columbia et
en Sierra, Croix du Sud en Bolivie, au Chili et en Nouvelle-Guinée.

- **Catalogue** : étoiles brillantes jusqu'à la magnitude 2,5 environ (60 à
  80 entrées, 4 octets chacune : ascension droite 16 bits, déclinaison S8,
  classe de magnitude et teinte), commun à toutes les régions, dans le
  tronc commun. Les 384 premiers octets des fichiers région DOS (51 couples
  x 16 bits, y S8, puis des tracés de constellations séparés par `$FFA6`)
  servent de référence pour la sélection des étoiles et des constellations
  de `LOOK STARS`, une fois leur repère décodé ; ils ne sont pas copiés.
- **Position** : temps sidéral local depuis la date et l'heure solaire du
  jeu et la longitude de l'en-tête de carte (+25), angle horaire, puis
  hauteur et azimut avec les tables entières de `sky_position` et la
  latitude (+12). Calcul **une fois par heure**, avec la Lune, dans un module
  `wildsky.bin` (ID 25) de la fenêtre `$5800` chargé par `overlay_load`
  (transfert RAM, aucune lecture disque) ; résultat : liste résidente de
  32 étoiles visibles au plus (azimut, hauteur, classe : 96 octets en BSS).
- **Tracé** : après le remplissage du ciel et avant le relief et les
  sprites, un pixel DHGR par étoile dans la zone de ciel, colonne déduite de
  azimut − cap par les constantes de projection, ligne déduite de la
  hauteur ; masqué par la crête (`sky_zone_end`) et par le disque lunaire ;
  blanc, jaune pâle ou bleu pâle selon la classe. Les rotations partielles
  retracent seulement les colonnes révélées.
- **Visibilité** : humeurs de nuit seulement ; aucune étoile sous ciel
  couvert ni en crépuscule civil ; sous la pleine Lune, seules les étoiles
  de première grandeur ; toutes en nuit noire. Le paysage reste invisible
  sans Lune, comme dans la règle HGR conservée : les étoiles ne l'éclairent
  pas.
- **`LOOK STARS`** (commande de la version DOS, optionnelle) : nom, azimut
  et hauteur de deux ou trois repères (Polaris ou Croix du Sud, l'étoile la
  plus brillante visible) sur la ligne de message, pour s'orienter la nuit
  sans boussole.
- **Coût** : catalogue ≈ 320 octets et liste 96 octets résidents, module de
  calcul ≈ 1 Ko en RAM auxiliaire, tracé ≈ 150 octets dans le moteur de vue.
  Les 128 octets libres de la RAM principale ne suffisent pas : ce point
  dépend du retrait de TOPO de la RAM auxiliaire et de la réorganisation
  du lot 4, ou d'un déplacement de tables vers la fenêtre de module.
- **Validation** : `tools/sky_ephemeris.py` étendu au temps sidéral et aux
  étoiles (référence : almanach 1985, Polaris à la latitude, lever de Sirius
  à la bonne heure) ; `test_stars.py` compare les pixels attendus aux deux
  banques pour une date, une heure, un cap et une région donnés, vérifie
  l'absence d'étoiles de jour, sous les nuages, au crépuscule et sous la
  crête, et l'hémisphère sud pour Bolivia, Chile et New Guinea.

## 7. Score par scénario

**Réalisé (étape 6)** ; spécification complète et exemples :
[HOF.md](HOF.md) § 2. Calculé à la fin du voyage (arrivée, mort, ou abandon
par `QUIT` puis `Y`) à partir de l'état résident, en entiers 16 bits :

| Composante | Formule | Plage |
|---|---|---:|
| Progression | `DONE=` de STATUS (`goal_pct`, 0–99, 100 seulement à l'arrivée) × 10 | 0–1 000 |
| Arrivée | +1 000 si `won` | 0 / 1 000 |
| Santé finale | arrivée : santé % × 5 ; sinon ⌊santé % × 5 × progression / 100⌋ | 0–500 |
| Rapidité (si `won`) | max(0, 720 − heures écoulées) | 0–720 |
| Niveau | ⌊total × (10 + niveau) / 14⌋ | ×0,79 à ×1,43 |

Décisions prises à la réalisation (HOF.md § 1) :

- **Progression = `DONE=` de STATUS**, et non `module_goal_pct` que nommait
  ce plan : celle-ci est l'efficacité native de l'original, qui vaut 100 %
  quand aucune heure n'est écoulée ; un QUIT immédiat aurait marqué 1 000
  points.
- **Santé pondérée par la progression hors arrivée** : sans cela, QUIT à la
  première invite valait 500 points au niveau 4, plus que la plupart des
  morts après un vrai trajet.
- **Un score nul n'est jamais classé**, même si la table a des places vides.
- **Ordre des opérations** : composantes entières, total, `× (10 + niveau)`,
  puis `/ 14` ; chaque division arrondit vers le bas ; tout tient sur 16 bits
  (maximum 4 600).

Les heures écoulées viennent de `s_elap` (`AYINT`). La référence Python est
`tools/score_ref.py` (réexportée par `tests/score.py`) ; le module 6502 est
vérifié contre elle par `tests/test_hof.py` (banc) et `tests/test_hof_game.py`
(jeu). Le bilan (composantes, total, niveau, score en inverse) est affiché
par le module de fin, pas par `module_ending` : l'écran de fin de l'original
reste inchangé et le module passe après lui.

## 8. Hall of fame

Fichier `NEOWILD.HOF`, un bloc de 512 octets créé par `build_disk.py` (pas
de CREATE à l'exécution) :

| Offset | Contenu |
|---:|---|
| 0–31 | `'H'`, version 1, compteur de parties, réservé |
| 32–511 | 6 scénarios × 5 entrées × 16 octets : nom 8 (ASCII haut, espaces), score u16, heures u16, niveau u8, issue u8 (1 arrivée, 2 mort, 3 abandon), 2 réservés |

Tri par score décroissant, puis heures croissantes ; à égalité complète, le
nouveau résultat passe après l'ancien. Le voyage libre n'entre jamais dans
la table et n'accède jamais au fichier. Les lectures et écritures passent
par `mli_call` avec le tampon `IOBUF` (`$BA00`) : une lecture au démarrage
du chargeur (avant le menu), une lecture et une écriture en fin de voyage.
**Chaque voyage de scénario écrit le fichier** (compteurs de parties), même
hors du top 5 ou après ESC. Une disquette protégée en écriture ou une erreur
MLI affiche un message et poursuit ; le score reste affiché ; un fichier
illisible ou inconnu n'est jamais réécrit.

**Réalisé (étape 6)**, avec ces écarts au plan (HOF.md § 1) :

- **Module à `$9600`, lu depuis `NEOWILD.END`** : `wildhof.bin` (3 044
  octets, 7 blocs) s'exécute dans la fenêtre SIM, libre une fois le voyage
  fini, et non à `$5800` (INPUT, qui le charge, y tourne ; `goal_pct` y
  recharge ADVENTURE puis STATUS). Il est lu depuis le disque : la RAM
  auxiliaire n'avait pas la place. L'entrée 24 du répertoire reste vide.
- **Toutes les fins passent par le module** : mort, arrivée après l'écran de
  fin, QUIT puis Y (`quit` → `module_end` dans INPUT).
- **Ordre** : `module_end` libère les pages `$96-$B5` du bitmap ProDOS
  (protégées pendant le jeu ; READ y refuserait le tampon), lit le module ;
  le module rassemble l'état, calcule le score, affiche le bilan, lit le
  fichier, compte le voyage, cherche le rang, fait saisir le nom sur la
  ligne du classement (A–Z, 0–9, espace, `.`, `-`), écrit, attend une
  touche, puis recharge INPUT et appelle `module_restart`.
- Le menu affiche `BEST` et l'écran `H` avec le code du chargeur
  (`src/hof_menu.s`, partagé avec le module).

## 9. Outils et fichiers

- `tools/regions.py` : extrait les six en-têtes de `build/SIERRA.dsk`
  (piste 0, secteurs 9–14) en `build/regions/rN.bin` et `regions.json`
  (climat, latitude par défaut, noms d'espèces) ; vérifie les sommes contre
  `docs/regions.sha256`.
- `tools/re_graphics.py` : `SPRITES` étendu aux 27 positions (noms établis
  par correspondance de largeur avec les `.CIM` DOS et contrôle visuel).
- `tools/mkmap.py --region N --seed S` : paramètres de région dans l'en-tête
  (latitude, températures, vent, indice, déclinaison, longitude, limite des
  arbres), cartes `build/maps/rN.bin`.
- `tools/dhgr_palette.py` / `gendhgr.py` : `REGIONS`, tables par région.
- `tools/build_disk.py` : tronc commun `NEOWILD.DAT` et `NEOWILD.R1`…`R6`
  (étape 2, toujours produits), `layout.json` par paquet ; `NEOWILD.HOF` à
  l'étape 6. `tools/genmenu.py` : textes du menu.
- `tools/stars_catalog.py`, `tools/stars_ref.py` (référence entière),
  `tools/genstars.py` (tables assemblées) ; `src/stars.s` : module horaire
  `wildsky.bin` (ID 25) ; `src/stars_draw.s` : liste et tracé par colonne
  (carte langage principale) ; raccords dans `src/game.s`.
- `src/boot.s` : menu, lecture du paquet, lecture du hall of fame ;
  `src/hof.s`, `src/hof_menu.s`, `src/hof_load.inc` : module de fin de
  partie, table et chargement ; `tools/score_ref.py`, `tools/genhof.py`.
  Faune à quatre espèces : tables de TRAVEL, OUTDOOR, PROJECT, SUMMARY
  (correctifs du paquet), `src/fauna.s` pour les références de test.
- Tests : `test_menu.py` (chaque scénario choisi au clavier, sprites et
  humeurs présents en RAM, zéro appel MLI après `start`, hall of fame vide),
  `test_regions.py`, `test_hof_ref.py`, `test_hof.py` (banc : écriture,
  relecture depuis le `.po`, tri, disque protégé), `test_hof_game.py`,
  `test_stars_ref.py`, `test_stars.py` (banc), `test_stars_game.py`,
  `test_fauna.py` étendu aux rencontres sondées des autres régions,
  `test_boot.py` et `test_prodos.py` adaptés au retour au menu.

## 10. Ordre de réalisation

1. Extraction et vérification des six régions et des 27 sprites (outils,
   tests, sommes de contrôle) ; sondes des règles de rencontre par région.
2. Paquets de région et chargement sélectif, Sierra d'abord (résultat
   identique au lot 3 : `test_reference_state.py` et `test_resident.py`
   verts), puis les cinq autres ; mesure des blocs par paquet. **Fait.**
3. Menu de démarrage, voyage libre, retour au menu. **Fait** (§ 3, § 4).
4. Faune à quatre espèces, palettes par région, textes de région ; cause
   d'arrêt nommée. **Fait.**
5. Étoiles de nuit (catalogue, module horaire, tracé). **Fait** ;
   `LOOK STARS` reste optionnel.
6. Score, module de fin, hall of fame, tests. **Fait.**

Les étapes 1 et 2 ne dépendaient pas du lot 4 ; l'étape 5 a pris la banque 2
de la carte langage principale (MEMORY.md § 9.7). Reste la validation
finale du lot 6 (IIc, couleurs sur machine réelle).

## 11. Préparation du voyage et niveaux (lot 1 de fidélité)

Éléments P1 et P2 de l'inventaire des manques (`ORIGINAL_GAP.md` § 2.9).
Code : `src/prepare.s` (fichier `NEOWILD.PRE`, 5 005 octets, 3 702
compressés, 9 blocs),
référence Python `tools/prepare_ref.py`, sonde `tools/re_prepare_probe.py`
(`make prepare-probe`), test `tests/test_prepare.py` (`--original`).

### 11.1 Ce que voit le joueur

- Menu : une ligne de plus, `P PREPARATION     QUESTIONS, NOT RANKED`,
  invite `CHOICE (RETURN = 1, 1-7, P, H, Q)?`. `P` demande la région
  (`FREE JOURNEY: REGION (1-6, ESC)?`, l'invite de `7`) puis le niveau : un
  voyage préparé est un voyage libre, jamais classé, hasard renouvelé.
- Après la lecture du paquet, l'écran `JOURNEY PREPARATION` de l'original
  pose les questions (textes de GO3, renumérotées : la cité perdue n'existe
  pas encore, la question « P/L » est sautée) :
  1. date et heure choisies (`Y` : mois 1–12, heure 0–24) ou tirées (`N`) ;
  2. jeu normal (`P`) ou mode recherche (`R`) ;
  3. à 8. (jeu normal) : sexe `M`/`F`, poids 50–350 lb, carrure `S`/`M`/`L`,
     taille 50–85 pouces, âge 8–100 ans, pouls au repos 35–180, puis le
     verdict de GO2 (« YOU SHOULD SEE A DOCTOR IMMEDIATELY! » … « YOU ARE
     OLYMPIC ATHLETE MATERIAL! ») ;
  9. et 10. fréquences de la faune et des orages (nombre > 0, décimales
     admises, quatre chiffres au plus, 100 au plus ; 1.0 = normal).

  Saisie : chiffres, point, flèche gauche pour effacer, RETURN ; hors
  plage : bip et nouvelle saisie.
- Puis un résumé : région et niveau, « THE TERRAIN IS VARIED. », « LEVEL
  OF DIFFICULTY: RESPECTABLE. », « THE TIME IS 7:00AM ON MAY 16. », « YOU
  HAVE NOT BEEN INJURED / IN THE CRASH. » (ou « RESEARCH MODE: INSTRUMENTS
  AT HAND. »), `PRESS RETURN TO BEGIN.`
- Tout voyage autre qu'un scénario au niveau 4 (scénario à un autre
  niveau, voyage libre) passe aussi par `NEOWILD.PRE`, sans questions : les
  mêmes tirages que l'original avec le corps du premier voyage, et le
  résumé sous `LOADING...`, sans attente.
- **Chemin par défaut inchangé** : RETURN, RETURN (et tout scénario au
  niveau 4) garde l'état figé du premier voyage de l'original ; le
  chargeur ne lit pas `NEOWILD.PRE` (`test_reference_state.py`,
  `test_journey_resident.py`, `test_prepare.py`).

### 11.2 Formules (GO1, GO2), vérifiées sur l'original

La sonde lance l'option 2 du menu original, impose au point d'entrée de
GO1 le niveau (`$603F`) et un RND constant (le RND de SMALLDOS en `$0321`
renvoie un flottant fixe), répond aux questions et relève l'état quand GO1
appelle l'introduction (`$5E7F`, transformé en boucle : `until` ne voit le
PC qu'entre les pas de script, et `key:` laisse courir trois trames). Onze
cas : 250 lb ; femme de 120 lb, petite carrure, 62 pouces, 45 ans, pouls
80, fréquences 0,5 et 2,5 ; 330 lb, 85 pouces, 8 ans, pouls 35, niveau 6 ;
mode recherche ; niveaux 1, 4, 7 et 10 avec RND 0,3 et 0,9. Le port refait
les mêmes opérations de la ROM dans le même ordre avec les octets des
constantes de GO1 et GO2 : **dates, heures, phase, métabolisme, Hmax,
santé, précipitations et premier front sont égaux octet pour octet** à
ceux de l'original ; blessure (condition à 90 %), lot de l'épave, usages,
durée du front, vent, poids et Q égaux.

| Grandeur | Formule | Original |
|---|---|---|
| Poids idéal | W0 = (223 + h (0,073 h − 5,98) − 10 [femme]) (1 + 0,065 c), c = −1, 0, 1 | GO2 `$2119` |
| Surpoids `$4BBE` | ⌊w − W0⌋ | idem |
| Métabolisme `$4C20` = `$4C25` | w / 100 (1,65 à 165 lb) ; repas `$4C25` + 0,004 w (2,31) | idem ; T12 `$5E33` |
| Hmax `$4C2F`, santé `$4C34` | 10 / (0,022 p r^1,5) × √(0,033 a) si a < 31, ÷ (0,033 a) sinon ; r = w/W0 si surpoids > 0, W0/w sinon ; jeu normal : Hmax borné à [1,1 ; 10], santé non bornée | GO2 `$2119`, `$2337` |
| Verdict | < 1,7 ; < 3,5 ; puis ⌊H + 0,5⌋ < 6, < 8, sinon | GO2 `$2370` |
| Surface Q `$4C1A` | 2 ⌊1335 S⌋ + ⌊800 S⌋ + 2630, S = 0,00919928 √(h w) | GO2 `$2273` (6058 à 165 lb, 70 pouces) |
| Mode recherche | 175 lb, 73 pouces, 25 ans, pouls 42, moyen, homme ; ni borne ni verdict ; COMPASS, WATCH, ALTIMETER, FLASHLGHT, THERMOMETER à l'épave ; aucune blessure | GO1 `$5B01`, GO2 `$2692` |
| Date tirée `$4C89` | d = 0,05 + 0,05 L r ; nord : 0,5 + d si r > 0,5, sinon 0,5 + d − 0,05 L ; sud : d + 0,025 L si r ≤ 0,5, sinon 1 + d − 0,075 L ; puis min(·, 0,997) | GO1 `$5A38`, GO2 `$285D` |
| Date choisie | (mois − 1) 0,085 + 0,065 r ; heure telle quelle | GO1 `$59D7` |
| Heure tirée `$4C57` | 12 + 1,2 L r si r > 0,5, sinon 12 + 1,2 L r − 1,2 L | GO1 `$5AA6` |
| Onde de température `$4CCF` | 2π r | GO2 `$298F` |
| Blessure du crash | n = ⌊0,45 r L − 0,3⌋ borné à 0–3 (rien, coupures, bras, jambe), condition n − 1 à 90 % ; jamais aux niveaux 1–2, jambe à partir de 8 ; jeu normal | GO2 `$2024` |
| Lot de l'épave | neuf groupes des 75 objets (21, 1, 15, 3, 11, 5, 3, 3, 13) : départ a = ⌊r (s − 1) + 0,5⌋ + 1, pas b = ⌊r (s − 2) + 0,5⌋ + 1 (groupes 1 et 3 : multiple de 3 → −1, puis 5, 7, 10, 14 → 4), k = ⌊(11 − L) s / 10 + 0,5⌋ tirages (doublons possibles) ; toujours DOWN PARKA, BACKPACK, WATER, MATCHES, TOPO MAP, KNIFE, 2QT CANTEEN, CANDYBARS ; BOOTS, JERSEY, JEANS, COTTN SOCKS portés ; STAR CHART, BINOCULARS, GOLD absents ; tout au sol, nourriture comprise (gabarit Journey T$21 : W7 = W5, W8 = 0) | GO2 `$2565` |
| Usages | W8 des objets 38–66, W5 et W6 de FUEL × 1/√L, tronqués ; confirmé : le premier voyage figé (niveau 4) a la moitié des valeurs du gabarit | GO2 `$26C2` |
| Précipitations `$4C43` | max(0,1 ; 0,1 × orages × (2 + 29 (1 + sin((360 date + 47)°)))) (en-tête Sierra) | GO2 `$2A74` |
| Premier front `$4C9D` | 3000 / (L `$4C43`) + 20 (unités de 4 min) ; durée `$4BFE` = ⌊min(540 ; 20 + 10 L `$4C43` r)⌋ | GO1 `$5E0A` |
| Vent `$4B9F` | ⌊16 r⌋ + 2 mph | GO1 `$5E67` |
| Mots | terrain MODERATE (L < 4), VARIED (< 8), PUNISHING ; difficulté LOW (1), LENIENT (2–3), RESPECTABLE (4–5), CHALLENGING (6–7), BACK-BREAKING (8–10) | GO2 `$2B3E`, `$2BAA` |
| Fréquences | faune `$4C4D` et orages `$4C52` : > 0, au plus 100 | GO1 `$5DA3`, `$5DDA` |

Le premier voyage figé correspond aux réponses homme, 165 lb, carrure
moyenne, 70 pouces, 31 ans, pouls 55 (Hmax 7,8666, Q 6058, surpoids 2 :
les constantes `f_hmax`, `th_surface` et `1 − 2/165` du port).

### 11.3 Où le port écrit

Tout est écrit par `NEOWILD.PRE` avant `start`, **sans octet résident en
RAM principale** : le module tourne à `$2000` (tampon de lecture du
chargeur, libre une fois le paquet lu, avant que la grille du menu ne
prenne les rangées HGR 176–191) et disparaît ensuite.

- RAM principale du jeu : `s_date`, `s_hour`, `s_temp_phase`,
  `body_weight`, `f_rest_rate`, `f_eat_rate`, `f_hmax`, `s_health`,
  `it_place`, `it_gnd`, `it_pack`, `it_oz`/`it_vol` de FUEL et de GOLD
  (2 w + 40 oz, w/2 in³, pour le scénario 2), `injury_active` et
  `injury_percent`, `weather_start`, `weather_duration`,
  `weather_frequency`, `wind`, `nature_frequency`.
- Images des modules en RAM auxiliaire (par `ld_place` du chargeur,
  adresse lue dans `module_dir`) : `th_surface`, `th_a` (Q × 10⁻⁷) et
  `th_native_composition` (1 − surpoids/poids) et `wf_storm` de SIM,
  nouveau multiplicateur des précipitations quotidiennes (1,0 : même
  opération que l'ancien `f_one`, résultat identique). `wf_storm` était
  dans l'image ADVENTURE ; depuis qu'ADVENTURE est compressé (LZ), il est
  passé dans le segment THERMAL de SIM, image brute (+5 octets de SIM ; la
  routine `module_weather_daily` reste dans ADVENTURE et ne tourne que
  depuis `env_day`, quand SIM est chargé).
- `NEOWILD.PRE` est compressé (LZ de `tools/pack_boot.py`, 5 005 → 3 702
  octets, 9 blocs) : le chargeur le lit en `$3000` et le décode vers `$2000`
  par `ld_decode_at` (la sortie reste derrière les données compressées).
  Chargeur `NEOWILD.SYSTEM` : 4 413 → 4 585 octets, toujours 9 blocs de
  données (menu `P`, lecture et décodage de `NEOWILD.PRE`, suffixes de
  noms de fichiers mis en commun) ; fin du chargeur et de son BSS sous
  `LD_IOBUF` (`$AB00`). Volume : 251 → 260 blocs, **20 libres** ; la carte
  native la plus grande de `test_geo_resident.py` tient encore (279 blocs).
- Piège trouvé : la page zéro du chargeur (`source`, `dest`) est en
  `$A2-$A5`, sur le signe du FAC, `SHIFT.SIGN.EXT` (`$A4`) et ARG ; après
  chaque `ld_place`, `prepare.s` remet `$A4` à zéro (la ROM le décale dans
  les produits et les sommes). `LINPRT` de l'Applesoft n'imprime rien sans
  la page zéro du BASIC : `prepare.s` a son propre `pr_dec`.

### 11.4 Ce qui reste (et pourquoi)

- **Effets en jeu du mode recherche** (pas de risques de déplacement, pas
  d'attaques, pas de chaîne thermique et de santé, pas de score, STATUS
  « RESEARCH MODE ») : ≈ 60 octets de drapeaux dans SIM (11 octets libres)
  et WILDOUT. Seule la partie chargeur est faite (corps, instruments,
  aucune blessure, voyage non classé). À faire après le lot 0.
- **Facteur de niveau du verdict de STATUS** (×0,85 dès le niveau 3, ×0,7
  dès 8, T$06/S$0C `$5A45`) : le module STATUS est plein (2 048 octets), et
  le niveau 4 lui-même changerait le chemin de référence.
- **Score de l'original** (`$4B99` = ⌊2,5 (L + 10) / Hmax + 0,5⌋, +L
  points) : le port a son propre score, déjà pondéré par le niveau
  ([HOF.md](HOF.md)) ; le score original relève de E2 (lot 8). `src/hof.s`
  n'est pas touché.
- **Phase lunaire 60 − 18 L** (`$4BC0`, lue par T$0D/S$07 pour la clarté
  nocturne) : la Lune du port suit les éphémérides 1985 de la date ; une
  date tirée déplace déjà la Lune.
- **Relief par niveau** (TMAKE : forêts max(5 ; 1,5 L), sommets ∝ √L,
  épave → poste ≥ 76 + 10 L, marge 28 − L) : `tools/mkmap.py --level`
  applique déjà ces paramètres ; il manque une carte par (région, niveau)
  sur un volume de 800 Ko et le choix de la carte par le chargeur.
- **Capacités des conteneurs** selon le poids (`$4BF8`, `$4BEE`, `$4BF2`,
  GO2 `$24D6`) : P3, lot 14 (le port garde son modèle calibré).
- Fréquence de la faune : le port n'a qu'un multiplicateur entier
  (`NATURE`), ⌊f + 0,5⌋ (0,2 donne 0). Précipitations et premier front des
  cinq autres régions : constantes de l'en-tête Sierra, comme
  `module_weather_daily`. Le reste de l'état d'un « nouveau voyage » de
  l'original (gabarit T$21 : compteurs de repas, d'eau, frissons initiaux)
  reste celui du premier voyage.
