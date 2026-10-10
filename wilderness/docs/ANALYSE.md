# Wilderness : analyse de l'original

*Wilderness: A Survival Adventure*, Electric Transit, 1985 (© 1984), par
Wesley Huntress, Charles Kohlhase et Peter Farson. Simulation de survie :
seul survivant d'un crash d'avion, le joueur doit rejoindre à pied le poste de
rangers indiqué sur sa carte topographique en gérant faim, soif, énergie,
température, blessures et maladies. Le terrain est rendu en 3D (HGR) à partir
d'un modèle d'altitude, les ordres sont tapés au clavier (parseur verbe + nom).

Ce document décrit ce qu'on a pu établir sur les disques originaux, pour servir
de référence à une réimplémentation (pas un portage du binaire).

## Sources

| Fichier (dans `original/`, hors git) | Origine | Contenu |
|---|---|---|
| `WILDERNESS.woz` | archive.org, woz-a-day (« 00playable ») | Disque 1 face B « Sierra Nevadas » : **face programme**, amorçable |
| `extras/Wilderness - Journey.a2r` | idem, extras | Face A « Journey » : **face données**, flux brut |
| `extras/Wilderness - Sierra Nevadas.a2r` | idem, extras | Même face que le .woz (décodage identique octet pour octet) |
| `extras/*.png` | idem, extras | Écran titre, menu, partie |
| `WILDERNESS_DEMO.dsk` | archive.org, disque de démonstration | Diaporama publicitaire en Applesoft + SMALLDOS |

`make originals` télécharge le tout, `make extract` le décode dans `build/`.

## Disques

### Format physique

Pistes standard 16 secteurs, prologues `D5 AA 96` / `D5 AA AD`, codage 6&2 :
`tools/flux2dsk.py` décode les 560 secteurs des deux faces (WOZ comme A2R).
La face programme a des marques supplémentaires (`D5 EE ED` piste 1,
`D5 BA FF` piste 17) : protection anti-copie. Un `.dsk` reconstruit ne démarre
pas (le jeu tombe dans le moniteur), le `.woz` démarre dans POM2.

### SMALLDOS

DOS maison (la RAM du jeu contient l'en-tête « SMALLDOS IMAGE » et une table
de commandes DOS 3.3 reprise telle quelle). Lu par `tools/smalldos.py`.

- **Ordre des secteurs** : le secteur SMALLDOS *s* est le secteur logique
  DOS 3.3 *15 − s* de la même piste.
- **Ordre des pistes** : sur les disques du jeu, la piste SMALLDOS *t* est la
  piste physique *34 − t* (le disque de démo garde l'ordre normal). Les pistes
  du tableau ci-dessous sont des pistes SMALLDOS.
- **Catalogue** : piste SMALLDOS 0 (physique $22 sur la face programme),
  secteurs SMALLDOS 0 à 3. Le secteur 0 commence par `06 00 00 00` puis une carte
  d'occupation (`FF` = libre). Chaque secteur porte 5 entrées de 32 octets à
  partir de `+$60` : type (`$C1` « A », `$C2` « B »), nombre de secteurs,
  piste, secteur, `00`, nom sur 27 caractères ASCII bit 7.
- **Fichiers contigus** : *n* secteurs à partir de (piste, secteur).
- Type « A » : Applesoft tokenisé chargé en $0801, sans en-tête de longueur
  (`tools/applesoft.py` liste MENU, TMAKE0, TMAKE, TSAVE, DEMO1, DEMOS).
- Lecture brute depuis le BASIC : `POKE 47869,page` (`PG`), `POKE 73,n`,
  `POKE 74,piste`, `POKE 75,secteur`, `CALL 972`. Commandes `& LOAD "X"` et
  `& RUN "X"`.

### Face programme « Sierra Nevadas »

| Fichier | Type | Sect. | Piste/Sect. | Rôle (déduit) |
|---|---|---:|---|---|
| `USRRND` | B | 1 | $00/$F | Routine USR (aléa / attente clavier du menu) |
| `TOPO` | B | 80 | $01/$0 | Carte topographique fournie, image mémoire $6000-$AFFF |
| `ORAPIC` | B | 32 | $06/$0 | Images HGR (avion, objets) |
| `SURV3D.CODE` | B | 24 | $08/$0 | Moteur de la vue 3D, chargé en $0800-$1FFF |
| `GO1` | B | 8 | $09/$8 | Lancement d'une partie (chargé en $5800, `& RUN`) |
| `TMAKE.OBJ` | B | 18 | $0A/$0 | Générateur de cartes (code), chargé en $4E00 |
| `TMAKE0` | A | 5 | $0B/$2 | Générateur de cartes (menu) |
| `TMAKE` | A | 18 | $0B/$8 | Générateur de cartes (BASIC) |
| `TSAVE` | A | 11 | $0C/$A | Sauvegarde des cartes |
| `MENU` | A | 13 | $0D/$5 | Menu principal (listé : `build/MENU.bas`) |
| `TDRAW.OBJ` | B | 10 | $0E/$2 | Tracé des cartes topo, chargé en $4000 (entrée $4298) |
| `POSTP.OBJ` | B | 4 | $0E/$C | ? |
| `GO2` | B | 16 | $0F/$0 | Moteur de jeu, 2ᵉ partie |
| `GO3` | B | 15 | $10/$0 | Moteur de jeu, 3ᵉ partie |
| `GETPIC` | B | 1 | $11/$1 | Chargeur d'images |
| `DEMOS` | A | 1 | $11/$2 | Lanceur « Preview global explorations » |
| `INPUT` | B | 1 | $11/$3 | Saisie de ligne |
| `SVGO2` | B | 2 | $11/$4 | Reprise de partie (chargé en $5800, `CALL 22528`) |
| `PAG3` | B | 1 | $11/$E | ? |
| `DEMO1` | A | 12 | $12/$F | Démo des six régions |

Piste 17 secteur 15 : identifiant du disque, lu par le menu (`X = PEEK(I)` :
17 = disque programme, 2 = disque de cartes, 3 = disque de sauvegardes ;
`I+13` = région, `I+14` = version, qui doit valoir 1).

### Face données « Journey »

Pas de catalogue : le moteur la lit par piste/secteur. La piste $22 commence
par une table d'index de mots 16 bits suivie de données graphiques. Contenu
probable : textes longs, images, scénario. Format restant à établir.

## Déroulement

Menu principal (`MENU`), région courante lue sur le disque (`C$(1..6)` :
British Columbia, Sierra Nevada, Burma, New Guinea, Bolivia, Chile) :

1. Premier voyage sur la carte fournie (niveau « respectable », 7 h, 6 mai)
2. Nouveau voyage sur la carte fournie (`TOPO` → page 96, puis `GO1`)
3. Nouveau voyage sur une de vos cartes (disque de cartes, 5 cartes max)
4. Reprendre une partie sauvegardée (disque de sauvegardes, 5 parties max ;
   chaque entrée : nom 32 car., région, niveau, n° de scénario, drapeau « R »)
5. Créer une nouvelle carte topo (`TMAKE0`)
6. Aperçu des explorations (`DEMOS` / `DEMO1`)
7. Fin

Une partie demande ensuite le disque Journey, affiche l'introduction (lieu,
heure, météo, faune dangereuse), l'objectif (rejoindre le poste de rangers),
l'altitude maximale de la carte et le niveau de difficulté, puis le paysage.

Le disque de démo annonce aussi : dix niveaux de difficulté, saisons et cycle
jour/nuit, pluie et neige, une seconde aventure (archéologue cherchant une
cité d'or perdue, avec indices du type « la cité est près d'une rivière »).

## Écrans

- **Vue** : HGR plein écran, ciel magenta, soleil, relief vert en 3D avec
  neige au-dessus d'une altitude, objets dessinés (épave de l'avion) ; deux
  lignes de texte en bas (`>` invite, « PLEASE WAIT » pendant le calcul).
- **STATUS** (texte) :
  - environnement : DATE, TIME, TEMP, SKY, WIND, TREND, ALT, GRND, SLOPE ;
  - joueur : état global (OKAY, POOR…), GOAL=%, HEALTH=%, signes
    (SHIVERING…), ENRG, HNGR, THRST, TEMP (98.6F), FOOD (oz), WATER (oz),
    INJ (blessures), ILL (maladies).
- **INVENTORY** : chaque objet est PACK, WEAR, CARRY ou GND (au sol),
  consommables en oz ou en USES ; totaux WEIGHT, WEAR VOL, PACK VOL,
  CARRY VOL (in³). Défilement par [ESPACE].
- **TOPO** : courbes de niveau HGR (vert), rivières et lacs (magenta),
  position, échelle verticale 0-40, légende « SIERRAS USA LAT+38 MAGD+17 »
  (déclinaison magnétique) ; touches V vue, S échelle, J/K/I/M défilement.

## Parseur

280 mots, table triée par longueur (de 1 à 12 lettres, chaque groupe terminé
par `$FF`) ; chaque mot est suivi d'une classe et d'un identifiant, les
synonymes partagent l'identifiant. En RAM vers `$B201-$B9F6` pendant une
partie.

**Verbes (classe 0)** : CATCH/FIND/GET 1, USE 2, BUILD/MAKE 3, SKIN 4,
WEAR 5, PACK/STORE 6, CARRY/TAKE 7, DROP/REMOVE 8, BOIL 9, DRINK 10,
COOK/FRY 11, EAT 12, DRY/WARM 13, COOL 14, CURE/HEAL/TREAT 15, LOOK 16,
ATTACK/KILL 17, SCARE 18, PAUSE/WAIT 19, REST/SLEEP 20, CAMP 21, GO/WALK 22,
RUN 23, SWIM 24, CLIMB 25, DOUSE/STOP 26, MOVE 27, PADDLE/ROW 28, LOWER 29,
SHIELD 30, CUT 31, SUCK 32, WET 33, HANG 34, SAMPLE/TASTE 35, PAN/SCAN 36,
IGNORE/SKIP 37, FLAG 38, EXIT/LEAVE 39, ENTER 40, SAVE 41, RESTORE 42,
CRAWL 43, EXERCISE 44.

**Qualificatifs (classe 1)** : WOOL 1, COTTN/COTTON 2, FIRSTAID/FRSTAID 3,
SNAKEBITE/SNAKEBT 4, SEWING 5, IODIN/IODINE 6, SALT 7, H/HALF 10.

**Noms (classe 2)**, par familles :

- vêtements et couchage 1-21 : BAG, PARKA, BALACLAVA, PANTS, BOOTS, SOCKS,
  MITTENS, SWEATER, TENT, PAD, COVER, RAINCOAT, GAITERS, JERSEY, JEANS,
  SHORTS, SHOES, HAT 19, GLOVES, BACKPACK ;
- nourriture et eau 22-37 : WATER, NUTS, EGGS, BARS/CANDYBARS, BACON, RICE,
  CHEESE, CARROTS, POTATOES, PEAS, RAISINS, BOLOGNA, BREAD, TUNA, BEANS,
  APPLES ;
- matériel 38-75 : MATCHES, GLASS, FUEL, KIT, SUNGLASSES 43, SUNSCREEN,
  REPELLENT, TAB/TABLETS, FLAGYL, OXYGEN 49, QUININE, SOAP, MAP, COMPASS,
  WATCH, ALTIMETER, CHART, GUN, AXE, KNIFE, ROPE, PITONS, CRAMPONS,
  SNOWSHOES, CANTEEN, FLASHLIGHT 66, GEAR, BINOCULARS, THERMOMETER,
  BOAT/RAFT, STOVE, TRAP, UTENSILS, TRINKETS, GOLD/STATUE ;
- nature et ressources 76-92 : BEAR, WOLF, MOOSE, GAME 80, FISH, INSECTS,
  FRUIT, CACTI, MUSHROOMS, PLANTS, STICKS, FIRE, BOW, SPEAR, CLUB, ROCK ;
- fabrications et lieux 93-100 : SPLINT, HIDE, HUT, IGLOO, TRENCH,
  AIRPLANE, OUTPOST, CITY ;
- commandes d'écran 103-108 : T/TOPO, V/VIEW, STAT/STATUS, INV/INVENTORY,
  HELP, CLUE ;
- blessures et maladies 110-128 : CUTS, ARM, LEG, SHOCK, SUNBURN, BLINDNESS,
  FROSTBITE, BITE, INFECTION, DEFICIENCY, POISONING, GIARDIA, MALARIA,
  DEHYDRATION, STARVATION, EXHAUSTION, SICKNESS, HYPOTHERMIA, HYPERTHERMIA ;
- thèmes d'aide 129-143 : THREAT, HAZARD, DANGER, FOOD 135, CLOTHES,
  SHELTER, INJURY, ILLNESS, DIRECTION, PROTECTION, RESCUE, WEATHER ;
- déplacement et orientation 144-157 : LAKE/RIVER, N, E, S, W, U, D
  (et NORTH…DOWN), R/RIGHT, L/LEFT, SUN, STARS, AZ/AZIMUTH,
  F/AHEAD/FORWARD, B/BACK/BACKWARD ;
- corps et soins 158-163 : BODY, BLEEDING, EYES, VENOM, PRESSURE, HEAD ;
- météo et environnement 166-177 : COLD, HEAT, WIND, RAIN, SNOW, ICE, TREE
  173, SHADOW, BAIT, SCRUB, NATURE ;
- animaux 181-197 : COUGAR, RATTLER/RATTLESNAKE, TIGER 184, ELEPHANT, COBRA,
  PYTHON, CANNIBAL/DANI, ADDER, CROC/CROCODILE, PUMA 192, JAGUAR,
  FER/FERDELANCE, ANACONDA, CAT 197.

Les animaux et maladies couvrent les six régions (cobra et tigre en Birmanie,
fer-de-lance et anaconda en Bolivie, Dani en Nouvelle-Guinée, etc.) : le
moteur est commun, la région change la faune, le climat et la carte.

## Mémoire pendant une partie

- `$0800-$5FFF` : moteur et tampons (textes d'introduction vers `$59B5`,
  messages courts vers `$0EDE` : NOT ENOUGH LIGHT, INSIDE SHELTER, NOT
  AVAILABLE, PLEASE WAIT, NOT NOW!).
- `$6000-$95FF` : données de terrain (tables de profils pour la vue 3D).
- `$9600-$BFFF` : SMALLDOS et parseur (vocabulaire `$B201-$B9F6`).
- Pointeurs Applesoft écrasés : le jeu proprement dit est en langage machine.

## Méthode

Le jeu tourne dans `a2shot` (cœur POM2) depuis le `.woz`, avec une étape
`insert:` pour changer de disque :

```sh
../dev/tools/a2shot/a2shot --disk build/SIERRA.woz wait:5400 key:"1\r" \
  wait:3000 insert:build/JOURNEY.dsk key:"\r" wait:3000 key:"\r" wait:600 \
  key:"\r" wait:1800 shot:vue.png peek:0000:0xC000 | python3 -I tools/peek2bin.py > ram.bin
```

`tools/applesoft.py` liste un programme Applesoft tiré d'un dump.

## Carte topographique (TOPO)

Établi à partir de `TMAKE` (BASIC), `TDRAW.OBJ` et `SURV3D.CODE`
(désassemblés avec `da65`) ; `tools/topo.py` décode une carte et en fait une
image qui se superpose à l'écran TOPO du jeu.

### Monde

- Grille de 224 × 168 cellules ; x croît vers l'est, la ligne y = 0 est le
  bord sud. L'échelle de l'écran TOPO (0-40 sur la hauteur) donne environ
  0,24 mile par cellule (carte d'environ 53 × 40 miles).
- **Altitude en pieds = 2400 + 100 × niveau** ; 2400 vient de l'octet $60A0
  (24). Vérifié : crash niveau 36 → 6000 ft (écran STATUS), sommet niveau 84
  → 10800 ft (texte d'introduction).
- Limite de neige : niveau/2 ≥ 24 (`$E8`), soit 7200 ft (« snow above 7000
  feet »).

### Génération (TMAKE)

Altitude = somme de montagnes gaussiennes séparables, en quatre échelles :
table exp(−x²) échantillonnée sur ±3·2^k (k = 0..3, k = 0 relevée de 0,2 pour
le fond), chaque montagne stockée comme deux pointeurs dans la table (x, y) et
une amplitude 16 bits (facteurs 0,25 / 0,4 / 0,7 / 0,3 selon l'échelle) ;
montagnes de bordure, de coin, puis 224 × 168 × 2,1e-4 × √niveau montagnes
centrales. Forêts : contours polaires r(θ) = r0 + Σ aₖ sin(kθ + φₖ),
excentrés, 1,5 × niveau formes. Rivières : départs aléatoires
(`$60AC` sources). Le code machine (`CALL 21856`) calcule ensuite la base de
données de contours qu'on retrouve dans TOPO, `POSTP.OBJ` place les points
spéciaux. Une carte niveau 10 prend plus de trois heures sur la machine.

### Format (image mémoire chargée en $6000)

| Adresse | Contenu |
|---|---|
| `$6000-$605F` | Paramètres de région (copiés depuis la piste 0, secteur région+8) |
| `$601F` | Région (1-6), `$603F` niveau de difficulté |
| `$6080-$6082` | Poste de rangers : y, x, niveau du sol |
| `$6083-$6085` | Crash (départ) : y, x, niveau du sol |
| `$6087-$608A` | Azimuts en degrés (16 bits) du départ puis du but vers le centre de la carte |
| `$608B…` | Objets et sites spéciaux (paires y, x) |
| `$60A0` | Altitude de base / 100 |
| `$60A8-$60B6` | Climat (température, pluie, vent… signés) |
| `$60BD` | Distance départ → but (cellules) ; `$60BF` version (1) |
| `$60C0-$60FF` | Textes : « BEAR », « COUGAR », « RATTLESNAKE », « NO ANIMAL »… |
| `$6100-$61A7` | Octet haut du pointeur de chaque ligne y (168) |
| `$61A8-$624F` | Octet bas du pointeur de chaque ligne y |
| `$6250…` | Forêts : par ligne, paires (x0, x1) terminées par `$FF` |
| `$63E4-$A121` | Enregistrements des lignes (ci-dessous) |

Chaque ligne y est une suite d'enregistrements terminée par `$FF` :

| Octets | Sens |
|---|---|
| `x, n` (n < $80) | Le sol vaut n en x (croisement d'une courbe, équidistance 4, ou extremum) |
| `x, $80+n, $80` | Point de rivière en x, au niveau n |
| `x, $80+n, $01, x1` | Lac de x à x1, au niveau n |

L'altitude en (x, y) s'obtient en interpolant linéairement le niveau entre les
deux enregistrements de la ligne y qui encadrent x (`SURV3D` `$15A8`, qui
renvoie aussi le type de terrain en `$C0` : 1 lac, `$80` rivière).

## Vue 3D (SURV3D.CODE)

Lancer de rayons sur la carte d'altitude, une colonne à la fois
(`tools/view3d.py` en est un prototype ; à 128° depuis le crash il reproduit
la première vue du jeu) :

- **Champ** : 140 colonnes de 2 pixels (280 px), une unité d'azimut par
  colonne ; 139 unités = 90°, donc 90° de champ. Le cap est en `$E5`
  (quadrant) et `$E4` (0-139). `PAN` fait défiler la moitié de l'écran
  (20 octets) et ne recalcule que 70 colonnes.
- **Rayon** : part de la position (`$D0` x, `$D1` y), avance de 2 cellules
  par pas (vecteurs sin/cos 8.8 à 512 = 2,0 en `$0A98/$0B24`), au plus `$E1`
  pas (128 par temps clair : toute la carte).
- **Projection** : à chaque pas n, h = altitude/2, dz = h − œil (`$D5` =
  niveau du sol/2 + 1), q = clamp(dz·256/n, ±127) ; ligne écran =
  95 − q·96/256 (horizon ligne 95, ±48 lignes). Multiplication et division
  8 bits signées maison (`$0C80`, `$0CC0`).
- **Occlusion** : un échantillon n'est tracé que si q dépasse le plus grand q
  déjà vu dans la colonne ; chaque nouveau sommet est un point EOR, puis la
  colonne est remplie jusqu'au précédent. D'où les bandes horizontales
  caractéristiques du rendu.
- **Couleurs** : ciel magenta, sol vert, neige blanche au-dessus du niveau 48,
  points de rivière et lacs en magenta ; arbres (`$6250`), soleil et images
  (`ORAPIC` : épave, objets) dessinés par-dessus.
- Tables de lignes HGR en tête du fichier (`$0800` octets hauts, `$08C0`
  octets bas, index i = ligne 191 − i).

## Reste à établir

- Couleurs exactes (motifs HGR par colonne `$C4`/`$C5`), forêts dans la vue,
  soleil selon l'heure, visibilité (`$E1`) selon la météo.
- Modèle de survie : évolution par heure de faim, soif, énergie, température
  corporelle selon météo, vêtements, pente, altitude ; seuils des maladies.
- Contenu et format de la face Journey (textes, images, aides `HELP`/`CLUE`).
- Effets de chaque verbe et règles de fabrication (SPLINT, HUT, IGLOO,
  TRENCH, BOW, SPEAR…).
- Niveaux de difficulté (dix), météo et saisons, `TMAKE` (génération de
  cartes).
