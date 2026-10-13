# Ciel nocturne : étoiles (lot 7, étape 5 ; ciel peuplé)

Étape 5 du lot 7 ([TODO.md](../TODO.md), boîtes « Dessiner les étoiles la
nuit », « Ciel plus peuplé » et « LOOK STARS » ; [SCENARIOS.md](SCENARIOS.md)
§ 6). Tout ce qui est décrit ici existe et est testé hors du jeu (catalogue,
référence Python bit à bit, module 6502 horaire, routine de tracé, banc IIe
autonome) **et dans le jeu** (section 10, `tests/test_stars_game.py`).
Le 13 octobre 2026, le ciel est passé de **79 étoiles** (V ≤ 2,31, liste de
32) à **282 étoiles** (V ≤ 3,50, liste de 160) : section 13.

| Élément | Fichier | Taille |
|---|---|---:|
| Catalogue (282 étoiles, sources citées) | `tools/stars_catalog.py` | 846 octets assemblés (3 par étoile) |
| Référence entière (spécification du 6502) | `tools/stars_ref.py` | — |
| Tables assemblées | `tools/genstars.py` → `build/stars_tables.inc` | 195 octets + catalogue |
| Tête du catalogue `wildskycat.bin` (ID 24, `$9600`) | segment `SKYCAT` | 462 octets (154 étoiles) |
| Module horaire `wildsky.bin` (ID 25, `$97CE`) | `src/stars.s` | 2 337 octets (reste du catalogue 384, code 1 758, tables 195) + 3 346 de BSS |
| Liste visible et tracé par colonne | `src/stars_draw.s` | 487 octets en carte langage principale (`$DE18-$DFFE` : liste 356, code 131) + 4 de variables (WILDLO) |
| Banc IIe | `src/stars_test.s`, `src/stars_test.cfg`, `src/stars_boot.s`, `stars.mk` | `../dist/NEOSTARS_TEST.po` |
| Tests | `tests/test_stars_ref.py` (Python pur), `tests/test_stars.py` (a2shot `--iie`), `tests/test_stars_game.py` (jeu) | `make -f stars.mk test`, `make test` |

## 1. Décisions en bref

- **Calcul horaire dans un module, liste résidente** : le catalogue et le
  code du calcul vivent dans le stock de modules (RAM auxiliaire) et sont
  copiés dans la **fenêtre SIM** (`$9600`) le temps du calcul, libre hors
  simulation ; seule la liste visible (160 × 2 octets + 36 octets de seaux)
  est résidente, dans la banque 2 de la carte langage principale, à côté du
  code de tracé.
- **Tables entières du moteur** : `sky_position` travaille en flottants ROM ;
  la seule table trigonométrique entière du moteur est `sin_lo`
  (`tools/gentables.py`, quart d'onde, 560 unités par tour). Le module
  l'utilise telle quelle (valeur 256 ramenée à 255, produits 8 × 8 bits) :
  les étoiles partagent l'unité d'angle de la vue (1/560 tour = 0,643°).
- **Même perspective que la Lune** : ligne = 95 − INT(48 tan h), comme
  `sky_y` ; rangées 16 à 95 seulement (au-delà de 59° de hauteur l'étoile
  serait dans les rangées cachées 0–15, comme la Lune).
- **Tracé par colonne**, dans `render_sky`, après les zones de ciel et avant
  la Lune : le masque de crête (`top`) n'existe que pendant le rendu de la
  colonne ; mémoriser 140 sommets coûterait plus que la liste. Une rotation
  ne retrace que les colonnes révélées : une étoile ne dépend que de
  l'azimut de sa colonne.
- **Visibilité par humeur** : humeurs de nuit seulement, jamais sous les
  nuages ; pleine Lune (*night bright*) : les plus brillantes (classes 0–1,
  V < 2,5, 90 étoiles) ; *night dim* et nuit noire : toutes (§ 14).
- **Priorité de sélection** : Polaris et les quatre étoiles de la Croix du
  Sud passent avant l'ordre des magnitudes ; quand plus de 160 étoiles sont
  levées (tropiques), les plus faibles tombent, jamais Polaris ni la Croix.

## 2. Catalogue

`tools/stars_catalog.py` embarque deux tables (nom, désignation, α et δ
J2000, V, B−V) :

- `STARS`, **les 79 plus brillantes** (inchangées) : les 78 étoiles de
  V ≤ 2,31 (jusqu'à η Centauri), plus **δ Crucis** (2,79) pour que la Croix
  ait ses quatre branches. Positions Hipparcos (ESA SP-1200, 1997) telles
  que données par SIMBAD (CDS) ; magnitudes V et indices B−V du *Bright Star
  Catalogue*, 5ᵉ édition révisée (Hoffleit & Warren, Yale, 1991), lumière
  combinée pour les couples serrés (Acrux, α Centauri, Castor).
- `EXTRA`, **203 étoiles de V ≤ 3,50** : toutes les entrées du *Bright Star
  Catalogue* (5ᵉ édition, catalogue CDS V/50 : positions J2000 FK5, V, B−V)
  de V ≤ 3,50 à plus de 0,3° des 79 premières (les composantes déjà
  comptées en lumière combinée sont écartées), sauf **T CrB** (HR 5958 : son
  V = 2,0 est l'éruption de 1946) et **Mira** (HR 681 : V de 2 à 10). Le
  numéro HR est conservé dans la table (`source`).

**282 entrées, 846 octets**, commun à toutes les régions. Les positions du
BSC5 et d'Hipparcos diffèrent de moins d'une seconde d'arc à l'échelle du
jeu (1 colonne = 0,64°).

**Époque.** Les tables sont J2000.0 ; `stars()` les précesse vers 1985.0
(angles IAU 1976, Meeus, *Astronomical Algorithms*, éq. 21.2–21.4),
l'équinoxe des éphémérides du jeu (`tools/sky_ephemeris.py`, Schlyter,
équinoxe de la date). Le décalage est d'au plus 15 ans × 50,3″/an = 12,6′
(0,21°, mesuré : 0,210°) ; les mouvements propres sur 15 ans (Arcturus :
34″) sont ignorés.

**Format (3 octets, lus par un pointeur : plus de 256 enregistrements).**

| Octet | Contenu |
|---|---|
| +0 | ascension droite en **quarts d'unité de vue** (2 240 = 24 h, 0,16°), bits 7–0 |
| +1 | bit 7 sud ; bit 6 nul ; bits 5–4 teinte (0 blanc ; 1 jaune pâle, B−V ≥ 0,70 ; 2 bleu pâle, B−V ≤ −0,10) ; bits 3–0 ascension droite, bits 11–8 (0..8) |
| +2 | \|δ\| en unités de vue (1/560 tour), 0..140 |

La **classe de magnitude** (0 : V < 1,5, première grandeur, 21 étoiles ;
1 : V < 2,5, 69 étoiles ; 2 : au-delà, 192) n'est plus stockée : elle
découle de l'indice, le catalogue étant trié (`class_layout` : classes 0,
0, 1, 1, 2 des cinq étoiles prioritaires, puis classe 1 à partir de
l'indice 24 et classe 2 à partir de 91). L'ascension droite en quarts d'unité de vue fait de l'angle
horaire une soustraction (§ 3). La déclinaison reste une grandeur en unités
de vue avec son signe à part (Polaris : 139 unités, hors d'un S8).

Le repère de `LOOK STARS` (Polaris, Croix du Sud = Acrux) reste un champ
Python (`landmark`) : la commande n'existe pas en 6502 (§ 11).

**Ordre** : Acrux, Mimosa, Gacrux, Polaris, δ Crucis d'abord (par magnitude
entre elles), puis toutes les autres par magnitude.

## 3. Algorithme entier (bit à bit avec `tools/stars_ref.py`)

La docstring de `tools/stars_ref.py` est la spécification ; résumé :

**Entrées.** `day` = INT(`s_date` × 365) (0 = 1ᵉʳ janvier, comme
`sky_lunar`), `minute` = INT(`s_hour` × 60) mod 1440 (heure solaire vraie du
jeu : midi = passage du Soleil au méridien), latitude `MAP+12` (S8 degrés),
longitude `MAP+25` (S8 degrés est ; **142° E ne tient pas dans l'octet** :
la Nouvelle-Guinée est bornée à +127, effet nul sur les étoiles, § 4).

**Temps sidéral local** (angle binaire 16 bits). L'horloge du jeu étant
l'heure solaire vraie, TSL = α☉ vraie + angle horaire du Soleil :

    LST16 = C(day) + minute × 45 + (minute × 163 >> 8) − (lon >> 1)
    LSTq  = ((LST16 × 35 + 512) >> 10) mod 2240     (quarts d'unité de vue)

- `C` : α☉(jour 8i, 0 h TU) − 32 768, Soleil de `sky_ephemeris.orbit`
  (1985, équinoxe de la date) ; **47 mots** (un tous les 8 jours),
  interpolation linéaire sur `day & 7` (écarts 1 306..1 616 < 4 096) ;
- 45 + 163/256 = 45,637 unités par minute (taux sidéral, 65 536 × 1,00274 /
  1 440) ;
- `lon >> 1` : le mouvement du Soleil entre heure locale et TU, 0,498 unité
  par degré (décalage arithmétique de l'octet signé).

**Position d'une étoile.**

    H   = (((LSTq − RAq) mod 2240) + 2) >> 2   mod 560   (unités de vue)
    S(i) = min(sin_lo[i], 255)                               (i = 0..140)
    lat_u = (|lat| × 199 + 66) >> 7  (= arrondi de |lat| × 14/9, 0..90)
    sφ, cφ = ±S(lat_u), S(140 − lat_u) ;  sδ, cδ = ±S(dec_u), S(140 − dec_u)
    sin H, cos H par quadrant (S(i), S(140 − i)) ;
    cδcH = signe(cos H) × ((cδ × |cos H| + 128) >> 8)
    up = sφ sδ + cφ cδcH      (sin h, 1,0 = 65 536 ; 24 bits signés)
    N  = cφ sδ − sφ cδcH      E = −sin H × cδ

- `up ≤ 0` : sous l'horizon ; `up ≥ 65 536` : hors de la vue. Une étoile
  dont la déclinaison est de l'autre côté de l'équateur que la latitude,
  avec dec_u + lat_u > 140, ne se lève jamais : le module la saute avant H
  (`up ≤ 0` à tout angle horaire, S étant monotone et cδcH ≤ cδ ; le test
  le vérifie), ce qui ne change aucun résultat.
- **Ligne** : h = nombre de T[k] ≤ `up >> 7`, T[k] = ⌈512 k / √(k² + 48²)⌉,
  k = 1..80 (table de 80 octets : T[k] & 255, bit 8 implicite à partir de
  l'indice 27) ; le module en tire à chaque calcul une table directe de 512
  octets (h pour chaque `up >> 7`) ; h = 80 : au-dessus de la vue ;
  ligne = 95 − h.
- **Azimut** : |E|, |N| divisés par 2 si l'un atteint 65 536 ; q = ⌊petit ×
  256 / grand⌋ (division restaurante 8 bits), r = (q + 1) >> 1 (128 si
  égaux), a = AT[r] = arrondi(atan(r/128) × 560/2π) (129 valeurs, stockées
  comme 128 pas de 0 ou 1 : 16 octets) ; a′ = a si |E| ≤ |N|, sinon
  140 − AT[r(N/E)] ; az = a′ (NE), 280 − a′ (SE), 280 + a′ (SO),
  (560 − a′) mod 560 (NO).
- **Lune** : masquée si `sky_y` ≤ 95, d = (az − `sky_bearing` + 5) mod 560
  < 11 et |ligne − `sky_y`| ≤ `sky_outer[d]` : le disque extérieur entier de
  `sky_column`, partie sombre comprise.
- **Produits** : 8 × 8 bits par quarts de carrés, f(a + b) − f(|a − b|),
  f(x) = INT(x²/4) pour x = 0..511 (table de 1 Ko construite à chaque calcul
  dans le BSS du module) ; sφ × x et cφ × x (x = 0..255) sont aussi tabulés
  pour l'heure (1 Ko) : 4 des 6 produits par étoile levée deviennent des
  lectures.

**Liste visible.** Les 160 premières étoiles du catalogue (ordre de
sélection, § 2) qui passent, **groupées par seau d'azimut** b = az >> 4
(16 unités, 35 seaux) par un tri par dénombrement stable (ordre du
catalogue dans un seau), dans deux tableaux de 160 octets : `st_a` =
classe << 6 | teinte << 4 | (az & 15), `st_row` ; puis `st_bucket[b]` =
premier indice du seau b, b = 0..35 (`st_bucket[35]` = nombre). Entrées
inutilisées à zéro.

## 4. Précision (contre un almanach indépendant)

`tests/test_stars_ref.py` compare la référence entière à un almanach en
flottants indépendant de `sky_ephemeris` : TSMG de Meeus (éq. 12.4), Soleil
de faible précision (ch. 25), équation du temps (éq. 28.3).

| Grandeur | Résultat (6 régions, toute l'année, 24 h, 282 étoiles) |
|---|---|
| Temps sidéral local | écart max 0,164° |
| Hauteur (1° à 59°), 315 103 positions | moyenne −0,014°, écart type 0,247°, max 1,02° |
| Azimut × cos h | écart type 0,42 unité (0,27°), max 1,75 unité (1,57 avec RA sur 16 bits) |
| Ligne (INT : +0,5 en moyenne) | −0,9..+1,7 sous 30° ; −2,1..+3,9 de 30° à 59° (tan h comprime le haut) |
| Polaris (BC, Sierra) | hauteur = latitude ± 1,5°, relèvement nord ± 2 unités, à toute heure |
| Sirius, Sierra, 1ᵉʳ janvier 1985 | lever 18 h 48, culmination 23 h 53 (heure solaire vraie) ; lever entier à ≤ 5 min de l'almanach sur 4 dates |
| Croix du Sud | plein sud depuis la Bolivie le 6 mai à 21 h (quatre étoiles, hauteur 41–48°) ; levée en Nouvelle-Guinée et au Chili ; jamais au-dessus de la Sierra |

La longitude n'entre que par `lon >> 1` : borner la Nouvelle-Guinée à +127
déplace les étoiles de 7/65 536 tour (rien) et la Lune de son mouvement en
une heure (≈ 0,5°).

## 5. Visibilité

`stars_frame` (une fois par trame, après `dhgr_frame`) fixe `star_thr` :

| Humeur (`sky_mood`) | Seuil | Étoiles |
|---|---|---|
| jour, couvert, doré, coucher, crépuscule couvert, civil, nautique | 0 | aucune |
| *night bright* (pleine Lune haute ou basse) | `$80` | les plus brillantes : classes 0–1, V < 2,5 (90 étoiles, dont Polaris et la Croix) |
| *night dim* | `$C0` | toutes (282) |
| *night dark* (Lune couchée ou non pleine) | `$C0` | toutes (282) |
| toute humeur avec `weather_sky` ≠ 0 | 0 | aucune |

Le crépuscule nautique n'est pas une humeur de nuit : pas d'étoiles avant
`night` (`select_mood` n'entre dans les humeurs de nuit qu'avec `night`).
Avec la règle `view_dark` du lot 3, *night dim* n'apparaît en jeu que sous
les nuages (donc sans étoiles) ; le banc la force pour tester le seuil. Le
paysage reste noir sans Lune : en nuit noire les étoiles s'arrêtent sur une
crête invisible, elles ne l'éclairent pas.

**La nuit, avec ou sans Lune, on voit toujours des étoiles** (§ 14). Une
Lune non pleine laisse `view_dark` à 1 (règle HGR : seul le disque plein
éclaire le paysage) : l'humeur est *night dark* et toutes les étoiles sont
tracées, la Lune dessinée par-dessus. Sous la pleine Lune (*night bright*),
le seuil `$80` garde les 90 étoiles de V < 2,5 : au sud de la Sierra le
3 mai à 23 h, Antares, Spica, Menkent, η Cen, α Lup, Dschubba et Muhlifain ;
avant le § 14 (seuil `$40`, première grandeur) il ne restait qu'Antares et
Spica, et une vue sur trois sous la pleine Lune n'avait aucune étoile.

## 6. Tracé : par colonne, et pourquoi

`stars_column` (appelé par `render_sky` pour chaque colonne de ciel) :
seau = `ang >> 4`, parcours des entrées du seau **de la dernière à la
première** (la plus brillante d'un pixel partagé est peinte en dernier) ;
pour une entrée de classe admise, de même azimut (`st_a & 15` = `ang & 15`)
et de ligne < `top` : un pixel par `scene_span` (entrée unie `c << 4 | c`
de la teinte, rangées ligne..ligne+1), ce qui préserve les rangées opaques
d'un sprite. La Lune (`sky_column`) et les arbres (`forest_paint`) passent
après.

Par étoile, il faudrait connaître la crête de chaque colonne après coup
(140 octets de plus que la liste) ou relire l'écran (impossible : ciel et
crête sont noirs la nuit). Par colonne, le coût mesuré reste faible :

| Mesure (banc, cycles) | 79 étoiles, liste 32 | 282 étoiles, liste 160 |
|---|---:|---:|
| `stars_draw.s` sur une vue complète, Sierra nuit noire, nord | 16 728 (27 en liste, 7 pixels) | 22 965 (117 en liste, 25 pixels) |
| même vue, surcoût total avec les spans | +18 789 | **+28 662** |
| Bolivia, sud (Croix du Sud) | 22 963 (12 pixels) | 35 272 (153 en liste, 49 pixels) |
| humeur sans étoiles (jour, crépuscule, nuages) | 1 979–1 991 | 1 979–1 991 |

Une vue complète du moteur coûte 1,9 à 5,8 s : le surcoût du banc est de
0,5 à 1,2 % ; en jeu 1,4 à 1,5 % (MEMORY.md § 9.7).

**Rotations.** `render_frame` efface puis retrace les colonnes révélées ;
les colonnes défilées gardent leurs étoiles, qui ne dépendent que de
l'azimut. Le banc le vérifie octet pour octet : vue à cap − 35, défilement
de 10 octets (copie de `scroll`), colonnes 105..139 = vue complète au cap ;
et rotation à gauche (colonnes 34..0 en ordre décroissant, comme
`render_prev`), y compris à travers le nord (azimut 559 → 0).

## 7. Mémoire

| Quoi | Où | Octets |
|---|---|---:|
| Tête du catalogue `wildskycat.bin` (154 étoiles) | stock (entrée 24 du répertoire, libre depuis que le module de fin est lu sur disque) ; elle remplit le trou de 464 octets de la carte auxiliaire `$DE30-$DFFF` → `$9600` | 462 |
| Module `wildsky.bin` : reste du catalogue 384, code 1 758 (dont 85 de passerelle flottante), tables 195 (`C` 94, T 80, pas de AT 16, classes prioritaires 5) | stock → `$97CE` (fenêtre SIM) | 2 337 |
| BSS du module : quarts de carrés 1 024, produits de l'heure 1 024, lignes 512, S 141, AT 129, passe 1 (3 × 160), comptes 36 | `$A200-$AF11` (fenêtre SIM, hors image) | 3 346 |
| Temporaires du module | page zéro `STARS_ZP` = `$5E`..`$A1` (zone des flottants ROM, libre entre deux vues ; le module ne rappelle plus la ROM après sa passerelle) | 68 |
| Liste visible (`st_a`, `st_row` 160 + 160) et seaux (36) | carte langage principale, banque 2, `$DE18-$DF7B` (segment `SKYRES`, initialisé à zéro : liste vide avant le premier calcul) | 356 |
| `stars_frame` + `stars_column` (avec seuils et entrées unies) | même segment, `$DF7C-$DFFE`, exécutés en place | 131 |
| `star_thr` + 3 variables de balayage (écrites pendant le rendu, banque en lecture seule) | WILDLO (LOWTEXT) | 4 |
| `stars_stale` + raccords `stars_dhgr_frame`, `stars_sky_column`, `stars_view_dark`, `stars_mark` | WILDLO | 73 |

**Choix mesurés** (13 octobre 2026, Burma comme pire cas du stock) :

1. *Catalogue de 3 octets* : retenu (846 au lieu de 1 128 octets à 4
   octets). La classe découle de l'indice ; l'ascension droite en quarts
   d'unité de vue rend l'angle horaire plus rapide qu'avec 16 bits.
2. *Catalogue hors de la fenêtre de 2 Ko* : retenu. Le module et le
   catalogue (2 799 octets) tournent dans la fenêtre SIM, libre au seul
   point d'appel (`show_view_scene`, dont les deux appelants viennent de
   poser `sim_loaded` = 0) ; le BSS de 3 346 octets n'occupe pas de stock.
   La lecture en place depuis la carte principale aurait pris 846 octets
   de plus à la carte (ITM ou MVI repoussés en RAM auxiliaire) pour le même
   bilan, sans gain de temps.
3. *Un seul enregistrement de 2 799 octets* : **ne tenait pas** (« auxiliary
   memory full : 41 793 octets pour 41 959 libres ») : le trou de 464 octets
   de la carte auxiliaire ne reçoit aucun module (le plus petit fait 495
   octets). Coupé en 462 octets (entrée 24) + 2 337 (entrée 25), le
   placement réussit.
4. *Liste de 160 entrées de 2 octets en carte langage* : retenu. La liste
   doit survivre à la simulation (pas de fenêtre SIM) ; en carte, les
   raccords la rendent déjà lisible au tracé, et le module ouvre la banque
   en écriture (`$C083` deux fois, interruptions masquées) le temps de la
   recopier. Seaux de 16 unités : 4,6 entrées par seau pour 160, contre
   17,8 avec les seaux de 64 unités d'avant. 160 couvre la Sierra en tout
   temps (127 au plus) ; sous les tropiques, jusqu'à 161 étoiles sont levées
   (Bolivia, 26 février 0 h 30) : la plus faible tombe.

Bilan par rapport à la version de 79 étoiles : stock de modules **−1 047
octets dans chaque région** (catalogue et module +815, carte principale
−232 : `SKYLC` passe de 121 à 487 octets, le stock de la carte de
`$D400-$DEFF` à `$D400-$DE17`) ; RAM principale **+95 octets** (la liste
quitte WILDLO, le raccord grandit de 11). Libre après le changement :
MEMORY.md § 9.9.

**Coûts du calcul horaire** (banc, 20 cas) : module **279 288 à 342 594
cycles** (avant : 147 232 à 180 424 pour 79 étoiles), plus la copie RAM de
2 799 octets (≈ 48 000 cycles), soit 0,32 à 0,38 s par heure de jeu, la
nuit seulement. En jeu : § 10 et `BASELINE_DHGR.json` (`lot7_stars`).
Optimisations mesurées sur le cas le plus lent (Bolivia, 473 → 343 k
cycles) : arbre de quadrants au lieu de soustractions (−25 k), table directe
des lignes au lieu d'une dichotomie (−36 k), table S au lieu d'appels (−20
k), produits de l'heure (−40 k), division sur registres (−10 k).

## 8. Banc et tests

`make -f stars.mk` construit `../dist/NEOSTARS_TEST.po` (ProDOS 2.4.3) :
`NEOSTARS.SYSTEM` (`src/stars_boot.s`, copie du chargeur de
`dhgr_boot.s`, même `dhgr_boot.cfg`) charge `STARTEST` à `$4000`
(`src/stars_test.s` : banc, `dhgr.s` complet, `stars_draw.s`, puis la tête
du catalogue à `$8000` et le module juste après, comme dans la fenêtre SIM ;
BSS à `$8C00`) puis `SCENE` à `$A000` (enregistrements de 160 octets :
date, heure, latitude, longitude, Lune, humeurs, cap, mode, profil de crête
de 140 colonnes). Le banc lie les vraies routines du moteur (`dhgr_frame`,
`select_mood`, `column_setup`, `dspan`, `clear_rows`) ; la boucle des zones
de `render_sky` et `scroll` sont copiées de `wild.s` ; il n'y a pas de
relief, seulement un profil de crête ; la liste y reste en RAM principale.

- `make -f stars.mk test` : `tests/test_stars_ref.py` (Python pur :
  catalogue épinglé et ses sources, tables, almanach, Polaris, Sirius, Croix
  du Sud, liste, saut des étoiles qui ne se lèvent jamais, Lune, humeurs,
  LOOK STARS, aperçus PNG) puis `tests/test_stars.py` (a2shot `--iie`, 20
  cas : liste résidente et **les deux banques** comparées octet pour octet à
  `stars_ref`, cycles par `pcprof`).
- Cas « aucune étoile » : jour, crépuscule civil, crépuscule nautique, nuit
  couverte, étoile sous le disque de la Lune (Spica, Lune posée sur elle).
- `make -f stars.mk run` : une vue de nuit par région dans POM2 (une touche
  pour la suivante ; crête en bleu tramé dans cette démonstration seulement).
- `make -f stars.mk previews` : `build/stars/panorama_rN.png` (horizon
  complet, 560 colonnes) et `view_*.png` ; les captures a2shot du test sont
  `build/stars/pom2_shot_*.png`.

## 9. Fichiers et symboles

- `src/stars.s` : `module_sky_stars` (entrée du jeu : copie de l'entrée 24,
  `day`, `minute` par la ROM, puis le calcul ; non assemblée si
  `STARS_BENCH`), `stars_compute` (entrée entière : `st_day`, `st_min` en
  page zéro). Lit `M_LAT`, `MAP+25`, `sky_bearing`, `sky_y`, `sin_lo`,
  `SIN_UNIT_START`, `sky_outer`. Segments `STARS_MODULE` (`SKYSTARS`),
  `STARS_CATALOGUE` / `STARS_CATALOGUE2` (`SKYCAT`, `SKYCAT2`) et
  `STARS_BSS` (`SKYSTBSS`, aligné sur une page) ; `STARS_LIST_LC` (jeu) :
  écriture de la liste en carte langage.
- `src/stars_draw.s` : `stars_frame`, `stars_column`, `st_a`, `st_row`,
  `st_bucket`, `star_thr`, `STAR_LIST_MAX`, `STAR_BUCKETS` (vérifiés contre
  `tools/stars_ref.py` par `.assert`). Lit `ang`, `top`, `sp_end`,
  `scene_span`, `sky_mood`, `weather_sky`, `MOOD_NIGHT_BRIGHT`.

## 10. Intégration

**Faite le 13 octobre 2026**, peuplée le même jour :

- `src/wild.cfg` : `SKYCAT` (`$9600`, 462 octets, `build/wildskycat.bin`),
  `SKYSTARS` (`$97CE`, `build/wildsky.bin`, segments `SKYCAT2` puis
  `SKYSTARS`), `SKYTMP` (`$A200`, BSS) et `SKYLC` (`$DE18`, 488 octets,
  `build/wildskylc.bin`, segment `SKYRES`) ; `wild.s` définit
  `STARS_CODE_LC` et `STARS_LIST_LC` (ca65 ne sait pas tester un
  `.define`).
- Les appels ne grossissent ni CODE ni GCODE : `render_frame` appelle
  `stars_dhgr_frame` au lieu de `dhgr_frame`, `render_sky` appelle
  `stars_sky_column` au lieu de `sky_column`, `show_view_scene` appelle
  `stars_view_dark` au lieu de `lda view_dark`, et `sky_position` finit par
  `jmp stars_mark` (`sta moon_phase`, `stars_stale` = 1) sous
  `.ifdef STARS_HOOK`. Les raccords de rendu sélectionnent la banque 2 en
  lecture (`BIT $C080`) et rendent la ROM (`BIT $C082`).
- `stars_view_dark` : si `stars_stale` et `night`, `overlay_load 25` (copie
  du module), `module_sky_stars` (copie de l'entrée 24 par `mem_fetch`,
  puis le calcul), puis remet `overlay_current` (la fenêtre `$5800` n'a pas
  changé) et `sim_loaded` = 0 (la prochaine simulation recopie son image).
- `build_disk.py` traite `wildsky.bin` (ID 25) et `wildskycat.bin` (ID 24)
  comme des modules ordinaires du tronc (fenêtres lues dans `wild.lbl` :
  `st_cat2`, `st_cat`) et écrit `wildskylc.bin` en `$DE18` de la carte
  principale (enregistrement de type `$A2`/`$E2`).
- Test en jeu : `tests/test_stars_game.py` (Sierra, nord et sud, nuages,
  midi, 1ᵉʳ janvier minuit, pleine Lune, rotations en nuit noire et sous la
  pleine Lune ; la liste est lue en carte par `$C080`). `make test` lance
  aussi `test_stars_ref.py` et `make -f stars.mk test`.
  `tools/game_shots.py --stars` : captures `build/dhgr/game_stars_*.png`,
  avec le nombre d'étoiles dessinées.

Coûts mesurés en jeu : MEMORY.md § 9.7 et `BASELINE_DHGR.json`
(`lot7_stars`).

## 11. `LOOK STARS` (optionnel) : spécification

- **Mots** : verbe `LOOK` (`V_LOOK` = 16) + nom `STARS` (154), mot du
  vocabulaire original déjà présent dans `build/gamedata.inc`. Aucune
  minute de jeu ne passe.
- **Refus** : humeur autre que de nuit → `IT IS NOT DARK ENOUGH TO SEE THE
  STARS.` ; `weather_sky` ≠ 0 → `CLOUDS HIDE THE STARS.` ; dans un abri →
  `YOU CANNOT SEE THE SKY FROM HERE.`
- **Lignes** (≤ 40 colonnes, `stars_ref.look_stars`) : Polaris si levée,
  la Croix du Sud (Acrux) si levée, puis l'étoile levée la plus brillante
  parmi les classes admises par l'humeur, si elle n'est pas déjà citée :
  `POLARIS: BEARING 0, HEIGHT 37.`, `SOUTHERN CROSS: BEARING 175, HEIGHT 42.`,
  `ARCTURUS: BEARING 167, HEIGHT 71.` ; aucune → `NO BRIGHT STAR IS ABOVE
  THE HORIZON.`
- **Unités** : relèvement **vrai** = (az × 9 + 7) // 14 ; hauteur =
  (u × 9 + 7) // 14, u = nombre de S(i) << 8 ≤ up (i = 1..140) — calculé à
  la minute courante, pas depuis la liste.
- **Place** : les noms font ≈ 190 octets (`genstars.py --names`). Mettre la
  commande dans un module qui a de la place, ou dans un module dédié de la
  fenêtre SIM réutilisant `stars_compute` (entrée `st_position` à exposer).

## 12. Limites connues

- La sélection garde 160 étoiles ; sous les tropiques jusqu'à 161 étoiles
  du catalogue sont levées : la plus faible de la classe 2 disparaît
  (jamais Polaris ni la Croix).
- Au-delà de 59° de hauteur l'étoile tomberait dans les rangées cachées :
  elle est omise (la Lune y est dessinée dans le cache, invisible).
- Une étoile du disque lunaire est retirée pour l'heure entière ; la liste
  n'est recalculée qu'à la vue suivante après un changement d'heure.
- Les longitudes au-delà de ±127° sont bornées (§ 4).
- Le stock de modules n'a plus que 266 octets libres avec Burma (plus grand
  morceau 135) : un module de plus demandera de la place ailleurs.

## 13. Ciel plus peuplé (13 octobre 2026)

| | Avant | Après |
|---|---:|---:|
| Catalogue | 79 étoiles, V ≤ 2,31 (+ δ Crucis), 4 octets | **282 étoiles, V ≤ 3,50**, 3 octets |
| Liste visible | 32 entrées de 3 octets, 10 seaux | **160 entrées de 2 octets, 36 seaux** |
| Liste, Sierra 6 mai 23 h | 27 | 117 |
| Liste, Bolivia 6 mai 21 h | 32 (pleine) | 153 |
| Captures `game_stars_*` : Sierra nord / sud / pleine Lune / Bolivia (étoiles dessinées) | 2 / 7 / 2 / 10 | **10 / 31 / 2 / 37** |
| En jeu, Sierra : `test_stars_game` nord / sud / 1ᵉʳ janvier 0 h | 2 / 7 / 13 | 10 / 31 / 33 |
| Calcul horaire en jeu (copies comprises) | 174–208 k cycles, 0,17–0,21 s | 339–347 k cycles, 0,33–0,34 s (pire cas du banc 0,38 s) |
| Tracé en jeu, nuit noire | 1,6–1,9 % d'une vue | 1,4–1,5 % (mesure sans l'appel, `BASELINE_DHGR.json`) |
| Module horaire (banc) | 147–180 k cycles + copie 1 984 octets | 279–343 k cycles + copie 2 799 octets |
| Vue de nuit noire, tracé (banc, Sierra nord) | +18 789 cycles | +28 662 cycles |

Les étoiles brillantes gardent leur rendu : mêmes 79 positions sources,
même ordre de sélection (Polaris et la Croix d'abord), mêmes teintes, même
règle de la Lune (première grandeur seulement, 21 étoiles ; élargie au § 14). L'ascension
droite passant de 16 bits à 2 240 quarts d'unité, une étoile peut se
déplacer d'une colonne à certaines heures (écart type de l'azimut inchangé,
0,42 unité).

## 14. Étoiles sous la Lune (13 octobre 2026)

Demande : « même quand la Lune est là, on doit voir les étoiles les plus
lumineuses ». Mesure avant correction : sous une Lune non pleine
(`view_dark` = 1, humeur *night dark*), toutes les étoiles étaient déjà
tracées ; une vue vide y est une crête haute (la Sierra vers l'ouest, noire
la nuit) qui cache aussi la Lune. Le défaut était la **pleine Lune** : seuil
`$40`, 21 étoiles de première grandeur, 1 ou 2 étoiles par vue et **aucune
dans 30 à 34 % des vues** en Colombie-Britannique, en Sierra et en
Birmanie (12 à 18 % en Nouvelle-Guinée, en Bolivie et au Chili).

Correction, sans octet de plus : la limite de la classe 1 passe de V < 2,0
à **V < 2,5** (`magnitude_class`, d'où `STAR_K2` = 91 au lieu de 49 : une
constante du module) et les seuils deviennent `$80`, `$C0`, `$C0`
(`st_thresholds`, mêmes 3 octets) ; la nuit noire garde `$C0`, le jour, le
crépuscule et les nuages gardent 0. *Night dim* (lumière lunaire 6–8, qui
n'apparaît en jeu que sous les nuages) prend `$C0` : moins de Lune, au
moins autant d'étoiles que sous la pleine Lune.

| Pleine Lune, modèle Python (6 régions, pleines Lunes de l'année, 21 h–3 h, 16 caps, crête à la ligne 80) | V < 1,5 (avant) | V < 2,0 | **V < 2,5 (retenu)** |
|---|---:|---:|---:|
| Étoiles par vue, moyenne (Sierra / Bolivia) | 1,2 / 1,7 | 2,7 / 3,8 | **5,4 / 6,6** |
| Vues sans étoile (Sierra / Bolivia) | 34 % / 13 % | 12 % / 8 % | **0 % / 0 %** |

| Captures `game_stars_*` (étoiles dessinées) | Avant | Après |
|---|---:|---:|
| `sierra_full_moon` (3 mai 23 h, sud, pleine Lune) | 2 | **7** |
| `sierra_full_moon_disc` (2 juin 23 h, face à la pleine Lune) | 1 | **9** |
| `sierra_gibbous_moon` (31 mai 23 h, face à la Lune gibbeuse, phase 10, *night dark*) | 35 | 35 |
| `sierra_polaris` / `sierra_south` / `bolivia_cross` (nuit noire) | 10 / 31 / 37 | 10 / 31 / 37 |
| `test_stars_game`, pleine Lune, caps 280 / 315 / 350 / 245 | 2 / 1 / 1 / 2 | 7 / 6 / 3 / 7 |

Mémoire : 0 octet (deux valeurs de `st_thresholds` et une constante
immédiate du module changent ; `wildsky.bin` reste à 2 337 octets). Tracé
sous la pleine Lune au banc : 23 996 cycles (6 pixels, Spica sous le
disque), dans l'enveloppe de la nuit noire.
