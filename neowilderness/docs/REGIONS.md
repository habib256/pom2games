# Régions originales : en-têtes, sprites et cartes reconstituées (lot 7)

Étape 1 du lot 7 ([SCENARIOS.md](SCENARIOS.md) § 10) : extraction des six
en-têtes de région et des 27 sprites de la face Journey, cartes des cinq
régions sans carte originale. Les règles de rencontre sondées sur l'original
sont dans [logic/animals.md](logic/animals.md#règles-de-rencontre-des-six-régions).
Aucun octet original n'entre dans Git : tout est produit dans `build/`.

```sh
make regions        # build/regions/, build/original_graphics/, build/maps/
make region-probe   # sondes a2shot : build/re_regions/, build/regions/fauna.json
python3 tests/test_regions.py
```

## 1. Extraction des en-têtes (`tools/regions.py`)

`TMAKE0` (ligne 28) écrit la région en `$601F` puis lit le secteur SMALLDOS
piste 0, secteur région + 8 de la face programme dans la page `$60` : ce
secteur est le gabarit de `TOPO $6000-$60FF`. `tools/regions.py` lit les six
secteurs de `build/SIERRA.dsk` (piste physique `$22`), écrit
`build/regions/r1.bin`…`r6.bin` (256 octets chacun) et
`build/regions/regions.json` (champs décodés, carte des octets, comparaison
MS-DOS), puis vérifie les sommes de [regions.sha256](regions.sha256)
(`--update` les réécrit).

| Fichier | SHA-256 |
|---|---|
| `r1.bin` British Columbia (`T00/S9`) | `ba4f61caa20c0f23…` |
| `r2.bin` Sierra Nevada (`T00/SA`) | `efe5c5ef564c3b4f…` |
| `r3.bin` Burma (`T00/SB`) | `24f893d7af1345d0…` |
| `r4.bin` New Guinea (`T00/SC`) | `0d206c0cba63540f…` |
| `r5.bin` Bolivia (`T00/SD`) | `c4f68f536c59d5ad…` |
| `r6.bin` Chile (`T00/SE`) | `8cf7a1d19dae328d…` |

Contrôle : le secteur Sierra est identique au `TOPO` fourni sur tous les
octets « région » ci-dessous ; les octets « carte » sont réécrits par
`TMAKE`, `POSTP.OBJ` et `TMAKE0` pour chaque carte.

### Carte des octets

| Adresses | Nature | Contenu et preuve |
|---|---|---|
| `$6000-$607F` | région | quatre fiches animales de 32 octets (fiche k en 32 × (k − 1)) ; **ce ne sont pas des tables de terrain**. GO1 `$5D5F-$5D97` copie leurs octets 0-11 dans `$48B4` (filtres des types 1-4) ; T0A/S00 lit l'octet 12 (taux) et 29 ; T06/S04 et T0F/S07 lisent 13-28 ([animals.md](logic/animals.md)) |
| `$601F` | région | numéro de région 1-6 (octet 31 de la fiche 1) |
| `$603F`, `$605F` | carte | niveau (TMAKE0 ligne 68), scénario 1 épave / 2 cité perdue |
| `$607F-$60A2` | carte | résidu de texte sur le disque ; poste, épave, azimuts, sites, base dans TOPO |
| `$60A3` | région | sol rocheux à partir de cette altitude /100 ft (120) ; `POSTP $424C` y retranche la base (Sierra 120 − 24 = 96 niveaux) |
| `$60A4`, `$60A5`, `$60A7` | région | 60, 30 (0 en jungle), 45 ; aucune lecture dans le code (balayage statique des deux faces) |
| `$60A6` | région | GRND SCRUB au-dessus de cette altitude /100 ft : 110, ou 50 en Burma, New Guinea, Bolivia ; la carte de port l'utilise comme limite des arbres (+27) |
| `$60A8`, `$60A9` | carte | latitude et déclinaison tirées par TMAKE0 (§ 3) |
| `$60AA` | région | plus haut sommet /100 ft : `POSTP $4221` base = INT(niveau × (`$60AA` − niveau max) / 10) |
| `$60AB` | région | inconnu (15 à 63), non lu par le code |
| `$60AC` | région | nombre de sources de rivières (TMAKE 1000/3100) |
| `$60AD` | région | paramètre de `TMAKE.OBJ` (TMAKE 1200 `POKE ST+28`) |
| `$60AE`, `$60AF` | région | latitudes minimale et maximale, signées (TMAKE0 32-40) |
| `$60B0-$60B5` | région | précipitations min, max et phase en degrés, LE16 (GO2, T0C/S05) |
| `$60B6` | région | déclinaison magnétique à mi-latitude, octet signé (TMAKE0 32-44) ; `$60B7`, `$60B8` nuls |
| `$60B9` | région | vent maximal en mph (T0A/S0C) |
| `$60BA` | région | indice climatique des filtres de faune et de ressources (T09/S0F) |
| `$60BB-$60CF` | carte | but, distance, dénivelé, version ; résidu disque dans le secteur |
| `$60D0-$60FF` | région | quatre noms d'animaux de 12 octets, ASCII haut, complétés par des zéros (`NO ANIMAL` pour une fiche vide) |

### Valeurs décodées

| Région | Latitudes | Indice | Vent | Précip. min/max/phase | Décl. | Sommet | Rivières | SCRUB | Faune (taux) |
|---|---|---:|---:|---|---:|---:|---:|---:|---|
| 1 British Columbia | 49 à 58 | 28 | 30 | 10 / 60 / 60 | 26 | 12 000 ft | 16 | 11 000 | BEAR 80, WOLF 100, MOOSE 75 |
| 2 Sierra Nevada | 35 à 40 | 31 | 30 | 2 / 60 / 47 | 17 | 14 500 ft | 13 | 11 000 | BEAR 80, COUGAR 40, RATTLESNAKE 100 |
| 3 Burma | 12 à 27 | 75 | 20 | 10 / 120 / 270 | −5 | 10 000 ft | 21 | 5 000 | TIGER 70, ELEPHANT 70, COBRA 70, PYTHON 75 |
| 4 New Guinea | −8 à −3 | 130 | 20 | 60 / 150 / 60 | 5 | 12 000 ft | 23 | 5 000 | CANNIBAL 50, ADDER 80, CROCODILE 120 |
| 5 Bolivia | −22 à −10 | 40 | 20 | 10 / 70 / 60 | 0 | 12 500 ft | 12 | 5 000 | PUMA 80, JAGUAR 100, FERDELANCE 80, ANACONDA 50 |
| 6 Chile | −55 à −22 | 11 | 30 | 1 / 6 / 270 | 10 | 21 000 ft | 2 | 11 000 | PUMA 100, CAT 100 |

Les noms et phrases de l'introduction viennent de `GO3` (chargé en `$3000`) :
nom `$3668` + table `$36AA`, phrase de faune `$3832` + table `$390B`
(« GRIZZLY BEAR, TIMBER WOLF, & MOOSE. », … « PUMA, AND AN OCCASIONAL
MOUNTAIN CAT. »), dans `regions.json` (`intro_name`, `fauna_sentence`).

## 2. Comparaison MS-DOS

Les fichiers `BRCOLUM.CIM`… `CHILE.CIM` (812 octets) de l'archive MS-DOS de
`original/extras/` contiennent 384 octets d'étoiles, `$60AA-$60BA`,
`$60A3-$60A7`, puis quatre fiches précédées d'un identifiant d'animal
global (1 grizzly … 18 chat). `tests/test_regions.py` vérifie :

- bloc climat `$60AA-$60BA` et `$60A4-$60A7` identiques dans les six régions ;
- filtres (octets 0-11) identiques ; les fiches entières aussi, **sauf les
  trois taux Sierra**, abaissés par la version DOS (80/40/100 → 70/35/70) ;
  le port garde les valeurs Apple II ;
- `$60A3` diffère (DOS 106, 115, 128, 128, 128, 78 contre 120 partout) ;
- l'identifiant d'animal suit l'ordre des sprites de la Journey, ce qui
  fixe le sprite de chaque fiche (Chile réutilise le puma de Bolivia).

## 3. Formules dérivées des en-têtes

Établies dans le code original et vérifiées sur les six régions par
`tools/re_region_fauna_probe.py` (valeurs relues en RAM après la préparation
du voyage) :

- **Latitude** (TMAKE0 40) : L = tronque(`$60AE` + (`$60AF` − `$60AE`) × USR(1)).
  **Déclinaison** (TMAKE0 42-44) : ⌊`$60B6` + (L − m) × sin m⌋, m = milieu de la plage.
- **Températures moyennes au niveau de la mer** `$4BB0` (janvier) /
  `$4BB1` (juillet), GO2 `$2876-$2912` : L ≥ 19 : 105 − ⌊1,7 L⌋ et
  105 − ⌊0,75 L⌋ ; −20 ≤ L < 19 : 78 − ⌊0,125 L⌋ et 80 + ⌊0,5 L⌋ ;
  L < −20 : 110 + ⌊1,25 L⌋ et 104 + ⌊1,375 L⌋. Sierra 38 → 41 / 77.
- **Limite des neiges** `$4C0A` (centaines de pieds), GO2 `$29C8-$2A5F` :
  x = |L| / 2 (entier), ⌊135 − 3x + (15 + x) sin 2π(f + k)⌋, k = −0,37 au nord,
  0,13 au sud, f = fraction d'année. L'introduction affiche
  ⌊ligne/10 + 0,5⌋ milliers de pieds, ou NO SNOW au-dessus du plus haut
  sommet ; T17/SC en tire le seuil de neige de la vue `$E8` = (ligne − base)/2.
  Sierra, 6 mai : 72, soit le niveau 48 de `map.bin` avec la base 24.
- **Saisons des ressources** (GO1 `$5CF3`) : L ≥ 23 garde les largeurs de
  saison ; −22 ≤ L < 23 (tropiques) leur donne 55 à 65 (toute l'année) pour
  les types 5, 7, 8, 10, 11, 12 ; L < −22 les rend négatives (−13, −30,
  −18 : saison inversée de l'hémisphère sud).
- **Base d'altitude** (POSTP `$4211-$4248`) : régions 3-5 (jungle) :
  − niveau minimal (le point le plus bas au niveau de la mer) ; autres :
  ⌊niveau × max(0, `$60AA` − niveau max) / 10⌋. Sierra niveau 4 → 24.

Sondes avec la latitude médiane de chaque région (Sierra : 38 du TOPO) :

| Région | Latitude | Janv./juil. | Neige (6 mai) | Introduction (mai) |
|---|---:|---|---:|---|
| British Columbia | 53 | 15 / 66 °F | 5 000 ft | MODERATE, AVERAGE RAINFALL, SNOW ABOVE 6000 |
| Sierra Nevada | 38 | 41 / 77 °F | 7 200 ft | MODERATE, AVERAGE, SNOW ABOVE 8000 |
| Burma | 19 | 73 / 91 °F | 10 400 ft | WARM, HEAVY, SNOW ABOVE 11000 |
| New Guinea | −5 | 79 / 77 °F | 13 100 ft | MODERATE, HEAVY, NO SNOW |
| Bolivia | −16 | 80 / 72 °F | 11 400 ft | MODERATE, AVERAGE, NO SNOW |
| Chile | −38 | 62 / 51 °F | 8 300 ft | COLD, LIGHT, SNOW ABOVE 8000 |

## 4. Sprites de la face Journey (`tools/re_graphics.py`)

Les 27 blocs sont contigus sur les pistes Journey `$00-$01`, `$16-$17` et
`$1C-$1F` ; le décodage (format de [ANALYSE.md](ANALYSE.md#graphismes-originaux-récupérés))
réussit pour chacun et la fin des données tombe avant le bloc suivant.
Les noms viennent de la correspondance avec les `.CIM` MS-DOS : même ordre
que l'identifiant d'animal des fiches, même nombre de colonnes à trois près
(premier octet du `.CIM`), puis contrôle visuel de
`build/original_graphics/sheet.html` (planche contact générée). Les huit
sprites déjà extraits gardent leurs fichiers à l'octet près (et leur nombre
historique de secteurs lus, 5 ou 10, plus large que le bloc).

| Nom | Rôle | Position | Secteurs | Octets codés | Pixels HGR | DOS (colonnes) |
|---|---|---|---:|---:|---|---|
| `wreck` | site (épave) | `T00/S0` | 10 | 1900 | 238 × 92 | `AIRPLANE.CIM` 116 |
| `lost_city` | site (cité perdue) | `T00/S8` | 10 | 2428 | 182 × 93 | `LOSTCITY.CIM` 90 |
| `outpost` | site (poste) | `T01/S2` | 9 | 2289 | 150 × 111 | `OUTPOST.CIM` 76 |
| `tent` | abri | `T16/S0` | 4 | 969 | 116 × 55 | `TENT.CIM` 56 |
| `cabin` | site (hutte) | `T16/S4` | 5 | 1133 | 122 × 64 | `HUT.CIM` 61 |
| `igloo` | abri | `T16/S9` | 4 | 859 | 114 × 55 | `IGLOO.CIM` 57 |
| `trench` | abri | `T16/SD` | 2 | 403 | 112 × 17 | `TRENCH.CIM` 57 |
| `log` | abri | `T16/SF` | 5 | 1216 | 176 × 50 | `LOG.CIM` 88 |
| `rock` | abri | `T17/S4` | 5 | 1158 | 118 × 68 | `ROCK.CIM` 59 |
| `grizzly_bc` | animal 1 | `T1C/S0` | 5 | 759 | 102 × 54 | `GRIZZLY.CIM` 50 |
| `wolf_bc` | animal 2 | `T1C/S3` | 5 | 1121 | 104 × 96 | `WOLF.CIM` 52 |
| `moose_bc` | animal 3 | `T1C/S8` | 5 | 958 | 102 × 82 | `MOOSE.CIM` 52 |
| `bear` | animal 4 | `T1C/SC` | 5 | 781 | 78 × 53 | `BLCKBEAR.CIM` 39 |
| `cougar` | animal 5 | `T1D/S0` | 5 | 539 | 104 × 43 | `COUGAR.CIM` 52 |
| `rattlesnake` | animal 6 | `T1D/S3` | 5 | 485 | 66 × 47 | `RATTLER.CIM` 33 |
| `tiger` | animal 7 | `T1D/S5` | 4 | 906 | 100 × 68 | `TIGER.CIM` 50 |
| `elephant` | animal 8 | `T1D/S9` | 4 | 949 | 96 × 73 | `ELEPHANT.CIM` 48 |
| `cobra` | animal 9 | `T1D/SD` | 3 | 730 | 82 × 88 | `COBRA.CIM` 41 |
| `python` | animal 10 | `T1E/S0` | 2 | 464 | 96 × 26 | `PYTHON.CIM` 47 |
| `dani` | animal 11 | `T1E/S2` | 4 | 905 | 90 × 122 | `DANI.CIM` 46 |
| `adder` | animal 12 | `T1E/S6` | 3 | 544 | 74 × 47 | `ADDER.CIM` 38 |
| `crocodile` | animal 13 | `T1E/S9` | 4 | 828 | 144 × 59 | `CROC.CIM` 72 |
| `puma` | animal 14 | `T1E/SD` | 3 | 639 | 60 × 73 | `PUMA.CIM` 29 |
| `jaguar` | animal 15 | `T1F/S0` | 5 | 1227 | 124 × 68 | `JAGUAR.CIM` 63 |
| `ferdelance` | animal 16 | `T1F/S5` | 2 | 491 | 88 × 31 | `FERLANCE.CIM` 45 |
| `anaconda` | animal 17 | `T1F/S7` | 3 | 668 | 90 × 44 | `ANACONDA.CIM` 45 |
| `cat` | animal 18 | `T1F/SA` | 4 | 937 | 106 × 61 | `CAT.CIM` 52 |

Animaux par région (octets codés) : British Columbia 2 838, Sierra 1 805,
Burma 3 049, New Guinea 2 277, Bolivia 3 025, Chile 1 576 ; plus épave
1 900, hutte 1 133 et poste 2 289 communs.

## 5. Cartes reconstituées (`mkmap.py --region N`)

`--region N` garde le générateur et l'ordre des tirages de `mkmap.py`, et
change seulement le nombre de sources de rivières (`$60AC`) et l'en-tête
(`mkmap.region_header`) : latitude tirée comme TMAKE0 avec un USR pris dans
la graine (`Random(graine ^ 0x4C4154)`), déclinaison TMAKE0, températures
GO2, vent, indice climatique, limite des arbres (`$60A6`), base POSTP
(bornée à 0 : l'octet de base du port est non signé), niveau de neige =
ligne du 6 mai − base (126 = aucune neige), longitude choisie par nous
(l'original n'en a pas : −124, −120, 97, 143, −66, −70 ; l'octet signé +25
borne New Guinea à +127 depuis le lot 7) et l'octet région en
**+32** (zéro dans les cartes héritées, lu comme Sierra). Sans `--region`,
`build/map.bin` reste identique à l'octet près ; `--region 2` ne diffère de
lui que par l'octet +32. La Sierra garde donc sa carte de build et ses
valeurs originales (latitude 38, déclinaison 17). Cette carte de build est
elle aussi générée (graine 1985) : le TOPO original, protégé, ne va jamais
sur le disque distribué (`topo2map.py` ne sert qu'aux comparaisons locales).

Graines fixes (`mkmap.REGION_SEEDS`), niveau 4, choisies parmi 1984-1999
pour une surface d'eau de 2 à 6 % et un trajet épave → poste d'au moins
129 unités, avec cinq reliefs distincts :

| Carte | Graine | Lat. | Décl. | Janv./juil. | Base | Neige | Rivières | Eau (cases) | SHA-256 |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| `build/map.bin` (Sierra) | 1985 | 38 | 17 | 41 / 77 | 24 | 48 | 13 | 360 | `ba1306aeef2a15f6…` |
| `build/maps/r1.bin` | 1987 | 51 | 23 | 19 / 67 | 14 | 39 | 16 | 663 | `860b447ec26a1050…` |
| `build/maps/r3.bin` | 1994 | 23 | −4 | 66 / 88 | 0 | 97 | 21 | 571 | `70a5286198c71b0b…` |
| `build/maps/r4.bin` | 1993 | −7 | 5 | 79 / 76 | 0 | 126 | 23 | 695 | `4cefb23ad7fa55ec…` |
| `build/maps/r5.bin` | 1997 | −19 | 0 | 81 / 70 | 0 | 111 | 12 | 708 | `2aedcffbea8b87b1…` |
| `build/maps/r6.bin` | 1984 | −25 | 1 | 78 / 69 | 50 | 53 | 2 | 216 | `dde987b2b7ba2640…` |

Les aperçus `build/maps/rN.png` colorent la neige avec le niveau de la
région. Ces cartes sont « reconstituées » : ni relief, ni rivières, ni
forêts ne viennent de l'original, seulement les paramètres de région.
`tests/test_mapgen.py` fixe les octets 10-32 de chaque en-tête.

## 6. Pour le chargeur de paquets (étape 2)

- Les tables de faune d'une région sont les fiches `$6000-$607F` (octets
  0-30 utiles), les noms `$60D0-$60FF` et l'indice `$60BA` ;
  `build/regions/fauna.json` les donne décodées, avec le sprite de chaque
  fiche et les lignes de ressources `$48B4` relevées.
- Les largeurs de saison des ressources 5, 7, 8, 10, 11, 12 dépendent de la
  **latitude de la carte** (règle GO1 ci-dessus), pas de la région : Burma
  à 23° (carte r3) garde les saisons du nord, alors que la sonde à 19° les
  rend permanentes. Les lignes de `fauna.json` valent pour la latitude
  sondée.
- Les objets de l'épave ne dépendent pas de la région : même réserve et
  même tirage aléatoire (voir [animals.md](logic/animals.md#objets-de-lépave)).
  Le lot de départ actuel du port convient aux six scénarios.
- L'octet +32 est le seul ajout d'en-tête ; `MAP+33` reste libre. Les
  octets +28 à +63 sont déjà utilisés à l'exécution (températures de
  reprise, sites, mode aventure, vêtements).
- Les valeurs DOS ne servent qu'au contrôle ; garder les taux Apple II.

## 7. Branches de région du code original

Balayage des lectures de `$601F` (absolu) sur la face Journey. Sondées :
pièges du cannibale (T06/S04 `$58DA`, [animals.md](logic/animals.md)).
Lues sans sonde : l'eau en radeau empêche la blessure (T06/S04 `$58FC`,
toutes régions) ; mot JUNGLE ou WOODS et messages de terrain pour 3-5
(T0A/S00 `$589E`, T06/SE, T08/SA, T0B/SA, T0D/SD, T0F/S1, T10/S3, T10/S6,
T13/S1, T15/S0, T15/S9) ; correction de précipitations du Chili selon la
latitude (T0C/S05) ; région 4 et premier animal dans T06/S06, T11/S05 et
T13/S00 (échanges avec le cannibale, non établis) ; T10/S07 pour 3 et 4 ;
table indexée par région en T05/S09 ; sauvegarde (T13/SF). Ces branches ne
font pas partie des sondes de rencontre.
