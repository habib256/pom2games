# Orientation (lot 7 de fidélité)

LOOK SUN, LOOK STARS, LOOK avec un objet (MAP, CHART, COMPASS, WATCH,
ALTIMETER), la règle « aide à l'orientation en usage » de LOOK N/E/S/W et
LOOK AZ (boussole, montre et soleil, bâton et ombre), USE MAP, COMPASS,
WATCH, ALTIMETER, CHART et SHADOW. Inventaire de départ :
[ORIGINAL_GAP.md](ORIGINAL_GAP.md) § 2.7 (O1, O2). Code : `src/orient.s`.
Preuves : `tools/re_orientation_probe.py` (ROM, données originales locales)
et `tests/test_orientation.py` (port).

## 1. Sources dans l'original

| Module | Rôle | Adresses |
|---|---|---|
| T$0F/S$0F (1 secteur) | LOOK + objet ou direction | famille 14 → T$10/S$0C ; MAP (52) et CHART (56) → USE (`$1E` = 0) ; COMPASS (53) → msg 256 ; WATCH (54) et ALTIMETER (55) → « SEE STATUS DISPLAY » ; sinon msg 12 |
| T$10/S$0C (4 secteurs) | LOOK + direction | abri `$5800`, SUN `$580D`, STARS `$5835`, aide `$586B`, AZ `$5882`, boussole `$58D7`, montre `$5933`, ombre `$5992`, fin commune `$5AB8` |
| T$11/S$00 (7 secteurs) | USE | famille 6 `$5BF9`, SHADOW `$5DAC` |
| T$0A/S$05 | premier pas de toute action qui dure | `$58C4` efface les drapeaux « en usage » de 38-42, 51, 52, 54-57, 66, 68, 69, 74 et `$4B4A` (pas la boussole, 53) |
| T$0D/S$07 `$5886` | portée de lumière | `$4B96` = INT(V·L/(V+L)), `$E1` = min(128, `$4B96`/2) |
| T$0D/S$0A `$5AB7` | lumière `$0D5D` | 1 en AM/PM, à l'aube et au crépuscule par ciel clair, ou avec MATCHES/FLASHLIGHT en usage |

Drapeaux : B2 (`$4098` + objet) vaut 1 quand l'objet est « en usage »
(COMPASS `$40CD`, WATCH `$40CE`) ; `$4B4A` = 1 quand le bâton est planté.

## 2. Règles portées

**LOOK + direction (N, E, S, W, AZ, SUN, STARS).** Dans un abri (`$0D5E`)
: message court « INSIDE SHELTER » (offset `$17` de la table de SURV3D),
pour toutes ces directions, mais pas pour LOOK COMPASS/WATCH/ALTIMETER
(T$0F/S$0F ne teste pas l'abri).

- **LOOK SUN** : msg 41 (« SORRY, THE SUN IS OBSCURED. ») si `$E0` ≠ 0
  (nuit) ou si la portée `$E1` < 44 ; sinon la vue se tourne vers l'azimut
  du soleil (`$B5/$B6`). La portée vient de la visibilité V
  (`weather_visibility`, `$4B91`) et de la lumière L (240 en AM/PM, 192 à
  l'aube et au crépuscule) : soleil visible si INT(V·L/(V+L)) ≥ 88, soit
  **V ≥ 139 de jour, V ≥ 163 à l'aube et au crépuscule** (22 cas ROM).
  L'azimut est celui de `sky_position` (atan2 est/nord de `src/sky.s`,
  calculé même quand le disque est hors du ciel dessiné).
- **LOOK STARS** : msg 52 (« SORRY, THE STARS ARE NOT VISIBLE. ») sauf si
  `$4B49` + `$4B4C` < 0, c'est-à-dire de nuit (−1) par ciel clair (0) ;
  l'aube claire (0 + 0) et la nuit nuageuse (−1 + 1) refusent. Sinon la vue
  se tourne vers le pôle céleste estimé : INT(octet `$BC` du générateur
  SURV3D `$0D2A`/4) − 33 degrés (−33 à +30), +180 si la latitude `$60A8`
  est négative (Bolivia, Chile, New Guinea). Pas de catalogue nommé
  (extension de [STARS.md](STARS.md) § 11, hors de ce lot).
- **LOOK N/E/S/W et LOOK AZ** exigent une aide en usage (B2[53] + B2[54] +
  `$4B4A` ≠ 0), sinon msg 42 (« FIRST PUT DIRECTION AID IN USE. »).
  **Au départ du voyage figé, aucune aide n'est en usage** : LOOK N répond
  msg 42 sur la ROM, même après CARRY COMPASS (porter n'est pas utiliser).
  **Écart du portage (14 octobre 2026)** : la grille de commandes propose
  NORTH..WEST en tout état ; sans aide en usage, une BOUSSOLE à portée est
  mise en usage par le LOOK lui-même (en main, bit 0, comme USE COMPASS),
  puis le cap magnétique suit. Sans boussole, msg 42 comme la ROM.
  LOOK AZ demande l'azimut (msg 43, redemandé avec msg 46 au-delà de 359),
  puis l'aide décide, dans cet ordre :
  - **boussole** : msg 44 (« DIRECTION SHOWN IS MAGNETIC, NOT TRUE. »),
    puis le cap magnétique déjà porté (erreur INT((RND − 0,5)·4)°,
    déclinaison `$60A9`) ;
  - **montre** (soleil visible, sinon msg 41) : msg 189/190 (Y/N). Y : msg
    10, rien d'autre. N : msg 13/14 (« WITH THE HOUR HAND POINTED AT THE
    SUN… ») si sin δ − sin φ < 0, sinon msg 201/202 (« WITH 12 POINTED AT
    SUN… »), puis l'estimation de l'azimut (0-359). Cap = direction
    demandée + azimut du soleil + INT(∓0,262 × 57,296 × h) + 180 si
    INT(57,296 × h) ≥ 344 − estimation, h = heure sur un cadran de 12 h
    (h − 12 l'après-midi), signe − pour msg 13. Aucun temps ;
  - **bâton** (`$4B4A`) : msg 29/30 (E ou W), msg 48, durée d'observation.
    Cap = direction demandée + INT((RND − 0,5) × 481 × (1 + 0,33 |12 − t|)
    / min), t = heure + min/120, + 180 pour W (la bonne réponse est E). Les
    minutes passent ensuite (comme WAIT), ce qui efface le bâton : une
    observation par USE SHADOW.
- **LOOK MAP / LOOK CHART** = USE MAP / USE CHART ; **LOOK COMPASS** : msg
  256, cap − déclinaison en degrés, sans exiger l'usage ; **LOOK WATCH** et
  **LOOK ALTIMETER** : « SEE STATUS DISPLAY. ». Objet absent : refus
  d'objet (msg 1 de l'original, `m_noitem` du port).
- **PAN** + ces noms : « YOU'RE NOT MAKING MUCH SENSE. » (msg 2, T$15/S$0A)
  ; PAN L/R/B/F reste la vue.

**USE.** Famille 6 (52-56) : B2[53] et B2[54] sont effacés d'abord (la
boussole et la montre s'excluent ; USE MAP ou ALTIMETER les retirent
aussi), puis, sauf pour la boussole, il faut de la lumière (`$0D5D`, sinon
msg 53 « SORRY, THERE IS INSUFFICIENT LIGHT. » — l'aide précédente est
déjà perdue). CHART : msg 1 après coup. MAP : en main et l'écran de carte
(T$05/S$08 puis T$01/S$0B, le TOPO de l'original : le port ouvre TOPO, pas
sa carte MAP 80 colonnes qui est une extension). COMPASS, WATCH, ALTIMETER
: en main (CARRY), msg 10, aucun temps. USE SHADOW : seulement en AM/PM par
ciel clair (`$4B49` − `$4B4C` = 1), sinon msg 53 ; efface boussole et
montre, plante le bâton.

**Temps.** Toute action qui fait passer le temps efface la montre et le
bâton (T$0A/S$05 au premier pas) ; la boussole reste en usage, même rangée
dans le sac (PACK COMPASS la garde, vérifié sur la ROM).

**STATUS sans altimètre.** Déjà porté : LOW < 30 ≤ MEDIUM < 101 ≤ HIGH
(niveau `$D4` + `$60A1`). Vérifié sur la ROM : l'altitude chiffrée reste
affichée tant que B1[55] < `$80`, altimètre au sol compris ; MEDIUM dès
B1[55] = `$FF`.

## 3. Sondes (`tools/re_orientation_probe.py`)

Trois sortes d'exécutions sur la ROM, données locales ignorées par Git :

1. **Portée** : T$0D/S$07 `$5886` seul, 22 couples (phase 0/1 ; V = 24,
   60, 100, 138, 139, 140, 162, 163, 164, 200, 240) : formule exacte,
   soleil caché pour V ≤ 138 de jour et V ≤ 162 à l'aube.
2. **Module T$10/S$0C seul**, RND (`$0321`) forcé, sortie de vue et
   d'horloge rendues au pilote : 14 cas exacts. Montre : 7 h E est. 30
   (Sierra, msg 13) → 219° ; 13 h W 200 → 270° ; 15,5 h ; 18,25 h ; 6 h et
   12 h (bord 344) ; deux cas msg 201 (sin φ < 0). Bâton : 2 h, 0 h (→ 10
   min), 1.5 h (90 min), 12 h, .25 h (15 min), 24 h ; RND 0,1 à 0,999 ; E et
   W.
3. **Parties tapées** (SIERRA.woz + JOURNEY.dsk, 3 sessions) : msg 42 au
   départ et après CARRY COMPASS ; USE WATCH sans temps ; LOOK SUN à 7 h =
   85° (`$B5`) ; montre à 7 h → 219°, à 13 h (soleil 216°) → 270° ; REST
   efface la montre ; exclusion COMPASS/WATCH/ALTIMETER ; PACK COMPASS
   garde l'usage ; LOOK COMPASS « 253 DEGREES MAGNETIC » (270 − 17) ; bâton
   E 2 h → 2,000 h écoulées, cap dans la borne ; W 0 h → 10 min + 180 ;
   USE SHADOW nuageux, USE WATCH/MAP sans lumière : msg 53 ; USE COMPASS
   sans lumière : accepté ; LOOK SUN `$E1` 43/44 et `$E0` ; LOOK STARS de
   jour, nuit nuageuse, aube claire : msg 52 ; nuit claire : 332° (Sierra,
   état `$12345678`), 156° et 210° (latitude −17) ; INSIDE SHELTER pour N
   et STARS, pas pour COMPASS ; PAN N, PAN SUN, PAN E : msg 2.

`make test-original` lance la sonde (≈ 25 s).

## 4. Le port

> **Intégration (docs/MEMORY.md § 13).** Depuis l'intégration des lots 2, 7,
> 9, 13 et LOOK, les textes de ce document sont dans la banque de textes
> (`src/textbank.txt`, lus à l'impression), la logique LOOK, l'azimut du
> Soleil et l'erreur du bâton dans le module ORIENT (26, compressé LZ dans
> le stock), USE MAP…CHART/SHADOW et LOOK MAP/CHART dans TREE ; restent
> résidents les portes `orient_look`/`orient_use` (WILDLO) et `orient_ask`
> (TEXT). Les tableaux ci-dessous décrivent la version livrée par le lot.


| Élément | Où | Rôle |
|---|---|---|
| `orient_aid` (1 octet) | GDATA | bit 0 boussole, bit 1 montre, bit 2 bâton (B2[53], B2[54], `$4B4A`) |
| `orient_lcg` (4 octets) | GDATA | copie du générateur SURV3D `$0D2A`, état `$BC-$BF` de la première vue (`F5 CA 66 1D`) : LOOK STARS ne consomme pas le RND de la météo |
| `orient_look`, `orient_use` | WILDLO (résident) | appelés en tête de `module_tree_look` et de `do_medical` (une ligne chacun) : les noms concernés chargent le module TREE, les autres reviennent ; PAN + ces noms : msg 2 |
| `orient_ask` | WILDLO | dialogues : message, puis deux touches (Échap annule) ou un nombre lu par `module_number` (INPUT chargé, puis TREE rechargé) |
| `orient_sun_core`, `orient_shadow_error` | WILDLO | azimut du soleil après `sky_position` (SIM chargée) ; erreur du bâton avec `weather_random` (le RND `$0321`) |
| textes (≈ 1 Ko) | LOWTEXT | messages de l'original, mis en lignes de 40 colonnes |
| `module_orient_look`, `module_orient_use` | TREE | la logique de T$0F/S$0F, T$10/S$0C et T$11/S$00 |
| effacement | SIM (`module_survival_clock`) | à chaque pas de temps : montre et bâton |

Placement : TREE (1 132 octets libres) ne suffisait pas ; INPUT et SIM
auraient tenu le reste, mais le stock auxiliaire ne l'aurait pas permis
pour une carte native de niveau 10 (`tests/test_geo_resident.py`, 92
octets de trop) : dialogues, textes et calculs du soleil et du bâton sont
résidents en WILDLO.

Autres retouches : `module_magnetic_heading` (TRAVEL) prend l'erreur de la
boussole quand elle est **en usage** (et non plus « en main ») ;
`input_validate` accepte 0 comme azimut (nord) au lieu d'annuler ; LOOK AZ
passe par le module TREE (le `module_look_az` d'INPUT n'est plus appelé) ;
le menu propose LOOK SUN et LOOK STARS, et USE liste MAP…CHART (filtre
41-56).

### Écarts conservés (choisis)

- **Hauteur de la vue** : LOOK SUN lève la vue si le soleil est à 40° ou
  plus, LOOK STARS la lève toujours (`$E7` = 1) ; non porté ici (lot LOOK
  UP/DOWN).
- **Cap posé sans vue** : avant un refus (msg 41 de la montre) ou la
  réponse Y, l'original écrit déjà la direction demandée dans `$D2/$D3`
  sans redessiner ; le port garde le cap affiché.
- **Saisie** : l'original lit trois chiffres (vide = 0) et des heures
  décimales (« 1.5 », « .25 », moins de 25 h, 0 → 10 min, « TOO LONG! »
  sinon). Le port garde sa saisie : entier, unités H ou MIN (« 90 MIN »),
  Échap ou vide annule, 0 h annule le bâton, 1 500 minutes et plus →
  « TOO LONG! » ; 0 est accepté comme azimut.
- **Temps du bâton** : passé comme WAIT, avec « YOU WAITED # MINUTES. » au
  lieu de « OK, WHAT NEXT? ».
- **LOOK STARS** : la suite exacte du générateur n'est pas reproduite (dans
  l'original, le dessin l'avance aussi) ; seule la formule l'est.
- **Lumière** : lampes (MATCHES, FLASHLIGHT en usage) absentes du port
  (lot 2, F2).
- **STATUS** : un altimètre laissé au sol sur une autre case compte encore
  dans l'original (B1 < `$80`), pas dans le port (`have`) ; STATUS est
  plein (2 048 octets), écart laissé.
- **HELP** : SCREENS est plein ; pas de ligne d'aide.
- **Boussole et HUD** : `hud_init` calcule le décalage du ruban par
  `magnetic_heading` ; il ne doit pas être appelé avec la boussole en
  usage (au démarrage elle ne l'est jamais ; à surveiller pour SAVE/RESTORE).

## 5. Mémoire (`build/wild.map`, avant → après)

| Segment | Avant | Après | Écart |
|---|---:|---:|---:|
| LOWCODE | 752 | 1 217 | +465 |
| LOWTEXT | 1 114 | 2 091 | +977 |
| **WILDLO libre** (`$1000-$1FFF`) | 1 718 | **276** | −1 442 |
| GCODE | 4 342 | 4 345 | +3 |
| GDATA | 1 609 | 1 614 | +5 |
| WILDGAME libre (`$4000-$577F`) | 18 | 10 | −8 |
| TREE (fenêtre `$5800`) | 916 | 1 926 | +1 010 (122 libres) |
| INPUT | 1 666 | 1 672 | +6 (376 libres) |
| TRAVEL | 2 045 | 2 044 | −1 |
| SIM (ENVIRON + THERMAL) | 7 619 | 7 627 | +8 (565 libres) |
| MENUSWAP | 1 474 | 1 484 | +10 (52 libres) |

Stock auxiliaire (`build_disk.py --layout`) : −1 023 octets par région
(TREE, INPUT, SIM) ; Burma 2 938 → 1 915 libres, plus grand morceau
2 494 → 1 347 (zone commune de la carte langage). Disque : 261 → 265
blocs sur 280 (NEOWILD.DAT 48 128 → 50 108 octets compressés, surtout
WILDLO, enregistré en entier).

**Volume de 140 Ko plein pour les cartes natives.** Le disque de test
de `tests/test_geo_resident.py` (carte générée de niveau 10, atlas dans le
paquet Sierra, plus six tuiles de bruit stockées brutes) tenait en 279
blocs ; il en demande 283 avec ce lot. La carte de niveau 10 seule tient
en 280, avec deux tuiles brutes (la première et une de la dernière rangée
de 8 lignes) aussi : la sonde garde ces deux-là. Les lots suivants
n'auront plus de place pour une carte native de niveau 10 : le passage à
l'image 800 Ko (permise, [ORIGINAL_GAP.md](ORIGINAL_GAP.md) § 1.3) est le
prochain pas pour ces cartes.

## 6. Tests

- `tests/test_orientation.py` (dans `make test`, ≈ 6 s) : deux parties.
  Jour : msg 42, exclusion des aides sans temps, LOOK AZ refusé, LOOK SUN =
  `sky_bearing`, LOOK STARS de jour, montre à 7 h (E, 30 → 341 unités,
  219° comme la ROM) et à 13,5 h (W, 200), Y, LOOK COMPASS, LOOK WATCH, deux
  bâtons (E 2 h, W 30 MIN) recalculés depuis `weather_seed`, REST qui
  efface la montre. Nuit : msg 41, pôle Sierra et latitude −17 recalculés
  depuis `orient_lcg`, msg 52 sous les nuages, msg 53 (bâton, montre),
  boussole sans lumière, seuil de visibilité 138/139, INSIDE SHELTER,
  PAN N et PAN SUN → msg 2, USE MAP → TOPO.
- Scripts existants rendus honnêtes (USE COMPASS ajouté, pas de règle
  affaiblie) : `test_compass.py` (et tolérance de l'erreur ±2° de la
  boussole originale), `test_hud.py` (cycle de vie et déclinaisons),
  `test_pan.py`, `test_sites.py` (marches cardinales), `test_play.py`
  (USE COMPASS au départ, cap du jeu accepté à ±2°). `test_hof_volume.py`
  est inchangé : ses LOOK N/E/S, sans aide, répondent msg 42 et le voyage
  garde plus de dix heures (avec USE COMPASS, l'erreur tirée de la boussole
  décale le RND et un repos interrompu le ramène à 9 h). `test_tree.py` : la boussole pend dans le sac à cet instant,
  LOOK W devient LOOK B (demi-tour). `test_menu_bar.py` : USE disparaît
  quand ni remède ni instrument n'est accessible (41-56).
- `tests/test_geo_resident.py` : la carte de contrôle « patchy » garde le
  niveau 10 et deux tuiles brutes au lieu de six (§ 5).
- `tests/test_adventure.py --scenario travel/discovery` (LOOK E, LOOK AZ
  après USE COMPASS) : 0 différence avec l'original, comme avant.
- `make test` : tout vert sauf l'échec connu et antérieur de
  `tests/test_sim.py` (« Night view: black terrain ») ; les scripts qui le
  suivent, lancés un par un, sont verts.
- `tests/test_reference_state.py` reste vert : le script de référence ne
  fait que LOOK R.
