# Fabrication : les recettes de MAKE (lot 3)

Ce document spécifie l'étape 1 du lot 3 de la fidélité à l'original
(inventaire [`ORIGINAL_GAP.md`](ORIGINAL_GAP.md) § 2.2, fiches A1 à A3, et D4
du § 2.5) : les abris fabriqués (HUT, IGLOO, TRENCH) et la tente, les armes
et outils (CLUB, SPEAR, BOW, AXE), l'attelle (SPLINT), la visière d'écorce et
la boue (SUNGLASSES, SUNSCREEN), la protection de l'abri, puis, pour le
lot 5, les recettes de la fabrication 2 (corde, radeau, gourde, ustensiles,
hameçons, raquettes, piège, pacotilles, vêtements de peau). Il sert de
cahier des charges au module 6502 « CRAFT ».

**État (15 octobre 2026) : lot 3 réalisé** : les recettes d'A1, A2 et D4
(§ 8 : découpage, écarts, tests), puis les sprites des abris fabriqués sur
NeoWildernessXL (§ 8.4), puis le reste de l'étape 1 (§ 8.5 : GET, PACK,
CARRY, DROP du second jeu, la pierre, une case par objet laissé au sol, les
armes contre les animaux, l'igloo des dangers), puis l'étape 2 (§ 8.6 : la
page CRAFT, le second jeu dans la grille et le panneau) ; les recettes
d'A3 sont mesurées (§ 6) et attendent le lot 5.

Chaque règle vient du désassemblage des modules de la face Journey (`da65`
et [`tools/re_surv_fp.py`](../tools/re_surv_fp.py), locaux) et est vérifiée
sur la ROM par [`tools/re_craft_probe.py`](../tools/re_craft_probe.py), sur
le modèle de [`tools/re_forage_probe.py`](../tools/re_forage_probe.py) (son
pilote, ses relais et son décodeur d'état sont réutilisés) :

- **partie 1** : 176 cas, chaque module seul en `$5800` au-dessus d'une copie
  vierge de l'état sauvegardé (`build/game.bin`, remise à neuf avant chaque
  cas), RND (`$0321`) remplacé par une table de tirages imposés qui compte
  les appels, entrées de message, de saisie, du moteur du temps et de
  chaînage remplacées par des relais : T10/S00 (5 secteurs, MAKE des
  familles 1, 5, 7), T10/S05 (7 secteurs, familles 8 et 9) et T11/S00
  (7 secteurs, USE) ;
- **partie 2** : 68 commandes de la vraie partie (`build/SIERRA.woz` +
  `build/JOURNEY.dsk`) avec quelques écritures en RAM : MAKE à l'épave, après
  une marche, en forêt (`$4B56` = 1), USE, ENTER et EXIT d'un abri, MAKE de
  chaque famille de noms ;
- **partie 3** : la transaction T0E/S02 du second jeu dans la vraie partie,
  41 commandes : GET, PACK, CARRY, DROP, REMOVE, WEAR, USE et MAKE de la
  pierre de l'épave, puis d'un arc, d'une lance, d'un gourdin et d'une
  attelle posés sur la case suivante (b1 = 0), une marche, LOOK BACK et le
  retour (§ 4.1).

Aucun octet original n'entre dans le dépôt : les chiffres sont dans
`build/re_craft/results.json` (local, ≈ 10 s, `python3
tools/re_craft_probe.py`). Les textes cités sont les messages originaux
(« msg n », numérotation de [parser.md](logic/parser.md)).

Notations : celles de [FORAGE.md](FORAGE.md) (B1 `$404C`, B2 `$4098`, W5…W11
pour le premier jeu 1–75 ; b1 `$45C0`, b2 `$45DC`, b3 `$45F8`, b4 `$4614`,
w5 `$4630`… pour le second, k = nom − 75 : 12 STICKS, 13 FIRE, 14 BOW,
15 SPEAR, 16 CLUB, 17 ROCK, 18 SPLINT, 19 HIDE, 20 HUT, 21 IGLOO,
22 TRENCH, 23 AIRPLANE, 24 OUTPOST, 25 CITY). « santé » = `$4C34` (7,86661
dans la partie sauvée, √ = 2,80475) ; « lumière » = `$0D5D` (0 ou 1) ;
« hache », « couteau », « nécessaire » = B2[58], B2[59], B2[65] (« en
usage », 0 ou 1). Tous les temps sont entiers par `$E10C` (troncature).

## 1. Ce que le joueur peut faire (original)

| Commande | Module | Effet |
|---|---|---|
| `MAKE HUT`, `IGLOO`, `TRENCH` | T10/S00 `$599C` | L'abri sur la case (b1 = 0), drapeau `$0D89`/`$0D8A`/`$0D8B` ; 127 à 381 minutes au départ (§ 3) |
| `USE HUT`, `IGLOO`, `TRENCH` | T11/S00 `$58BD` | Dedans (`$0D5E` = 1, b2 = 1), pas de santé de 15 min, msg 9 ; aucun temps |
| `ENTER`, `EXIT` d'un abri | T12/S08 | Dedans ou dehors (msg 10), déjà (msg 11), absent (msg 1) |
| `USE TENT` | T11/S00 `$58E4` | 30 minutes, dedans, pas de 20 min, la tente posée sur la case |
| `MAKE CLUB`, `SPEAR`, `BOW`, `AXE` | T10/S00 `$5B33` | L'arme au sol ; 21 à 852 minutes (§ 4) |
| `USE BOW`, `SPEAR`, `CLUB`, `ROCK` | T11/S00 `$5C42` | En usage (b2 = 1), puis CARRY (en main) |
| `MAKE SPLINT` | T10/S00 `$5A65` | L'attelle au sol ; 26 à 106 minutes (§ 5) |
| `MAKE SUNGLASSES`, `SUNSCREEN` | T10/S00 `$5A86` | Visière d'écorce (msg 28) ou boue (msg 205), 30 minutes |
| `MAKE HIDE` | T10/S00 `$5827` | msg 35 sans peau, msg 101 avec |
| `MAKE` d'un vêtement, de la tente, du sac | T10/S00 `$584A` | Taillé dans la peau (A3, § 6.3) |
| `MAKE ROPE`, `RAFT`, `CANTEEN`, `UTENSILS`, `GEAR`, `SNOWSHOES`, `TRAP`, `TRINKETS` | T10/S05 | Fabrication 2 (A3, § 6) |

Aucun MAKE ne tire de nombre aléatoire, sauf TRINKETS (§ 6.2).

## 2. Aiguillage du cœur (T05/S00 `$551E`)

Le verbe 3 (BUILD, MAKE) passe le contrôle de disponibilité (`$5229`) puis :

1. famille 2 : WATER → module de l'eau (lot 2) ; RAIN, SNOW, ICE → « YOUR
   POWERS DON'T EXTEND THAT FAR! » (msg 21) ;
2. famille 17 (172 et plus : TREE, SHADOW, BAIT…) → T11/S00, sélecteur
   `$1E` = 17 (MAKE TREE : « YOU ARE NOT NEAR A TREE. », msg 16 ; MAKE BAIT,
   MAKE SHADOW : msg 10, mesurés) ;
3. **présence** : HIDE (94) passe ; un nom du second jeu (≥ 76) avec b1 ≥ 0
   → « YOU ALREADY HAVE. » (msg 11), sauf SPLINT : « OK, WHAT NEXT? »
   (msg 10) ; un nom du premier jeu avec B1 ≥ 0 → msg 11 ;
4. famille 4 (MATCHES, GLASS, FUEL, STICKS, FIRE) → T11/S00 `$1E` = 4
   (lot 2) ; familles 1, 5, 7 → T10/S00 ; famille 9 → T10/S05 `$1E` = 9 ;
   famille 8 : ROPE (60) `$1E` = 8, SNOWSHOES (63) `$1E` = 9, PITONS et
   CRAMPONS msg 21 ; toute autre famille → msg 21.

Mesuré dans la vraie partie (partie 2) : MAKE BEAR, GAME, FRUIT, GUN,
AIRPLANE (hors épave), OUTPOST, CITY, RAIN → msg 21 ; MAKE FOOD, SHELTER,
COLD → « TRY TO BE MORE SPECIFIC. » (msg 17, familles 13 et 16) ; MAKE
NORTH, CUTS, BODY → « YOU'RE NOT MAKING MUCH SENSE. » (msg 2, familles 14,
10, 15) ; MAKE STATUS affiche la page STATUS ; MAKE AXE, SUNGLASSES,
PARKA, CHEESE, ROPE (présents) → msg 11 ; MAKE ROCK → msg 11 (la pierre
est au sol de la case de départ, b1[17] = 0 dans la partie sauvée).

## 3. Abris (A1)

### 3.1 MAKE HUT, IGLOO, TRENCH (`$5812-$5A53`)

Contrôles, dans l'ordre (le cœur a déjà répondu msg 11 si l'abri est sur la
case) :

1. **dans l'eau** (`$5832`) : `$4B56` ≥ 3 et rive `$4B6B` = 0 ou 3 → « YOU'RE
   IN THE WATER ALREADY! » (msg 92) ; sur une rive (`$4B6B` = 1, 2) l'abri se
   construit (mesuré : rivière et lac) ;
2. **épave ou poste** : `$D8` = `$7F` ou `$D9` = `$7F` → « THINK! » (msg 49).
   Sonde 5 d'ORIGINAL_GAP.md : T09/S08 `$5C9C` met `$D8` = `$D9` = `$FF`, puis
   `LSR $D8` quand la case du joueur (`$F5`, `$F7`) est celle d'en-tête TOPO
   `$6081`/`$6080` (le **poste**, but du voyage), `LSR $D9` quand c'est
   `$6084`/`$6083` (l'**épave**, ou la cité perdue d'un autre scénario,
   `$605F`) ; mesuré : `$D9` = `$7F` au départ, `$FF` après une marche ;
3. HUT : forêt (`$4B56` = 1) ou arbre en vue (`$D7` ≠ 0), sinon « SORRY,
   SUFFICIENT RAW MATERIAL IS NOT AVAILABLE. » (msg 76) ; IGLOO : sol
   enneigé (`$4B57` ≠ 0), sinon msg 76 ; TRENCH : partout (rocher compris).

Puis : effort `$4C20` += **0,023** × W(`$4C02`) (213 lb : 6,549) ; temps
**INT(4 000 k / ((lumière + 2)(hache + 2) × santé))**, k = 1 TRENCH, 2 HUT,
3 IGLOO ; b1[k + 19] = 0 ; `$0D88 + (nom − 94)` = 1 ; « IT TOOK A WHILE TO
MAKE YOUR {NOUN}. » (msg 15) ; `$4B73` = 0, `$0D5F` = 1, `JMP $4D00`.

| Cas (mesuré) | TRENCH | HUT | IGLOO |
|---|---:|---:|---:|
| lumière 1, hache 0, santé 7,867 | 84 | 169 | 254 |
| lumière 0 | 127 | 254 | 381 |
| hache en usage | 56 | 112 | 169 |
| santé 2,5 | 266 | 533 | 800 |
| lumière 0, hache, santé 2,5 | 266 | 533 | 800 |

ORIGINAL_GAP.md donnait 127/254/381 « au départ » : c'est la nuit ; de jour
84/169/254. Le « d » de la formule (sonde 4) est bien `$0D5D`, la lumière.

MAKE HIDE (`$5827`) : « FOR MORE HIDE, SKIN A CREATURE AND ADD TO YOUR
SUPPLY. » (msg 101) quand b1[19] ≥ 0, sinon « YOU NEED TO SKIN A CREATURE
FOR ITS HIDE. » (msg 35).

### 3.2 Entrer, sortir, la tente

- USE HUT/IGLOO/TRENCH (`$58BD`, aussi AIRPLANE, OUTPOST, CITY) : b2 = 1,
  `$0D5E` = 1, `$4BCC` (pas de la mise à jour de santé) = 15, « YOU'RE NOW
  SAFELY INSIDE SHELTER. » (msg 9) ; aucun temps, aucun contrôle de plus
  (le cœur exige l'abri sur la case : sinon msg 1). Deux USE HUT de suite :
  msg 9 deux fois.
- ENTER HUT (vraie partie) : dehors → msg 10 et dedans (b2 = 1) ; dedans →
  msg 11. EXIT HUT : dedans → msg 10 et dehors (b2 = 0) ; **dehors → msg 11**.
  EXIT TRENCH sans tranchée → msg 1. EXIT SHELTER dans une hutte → « TRY TO
  BE MORE SPECIFIC. » (msg 17) : l'abri naturel seul répond à SHELTER.
- USE TENT (`$58E4`) : épave ou poste → msg 49 ; B2[9] = 1 ; **30 minutes**
  (W7[9]) à l'effort 0,02 ; `$0D5E` = 1, `$0D88` = 1, `$4BCC` = 20 ; msg 9
  (et la suite) ; tente au sol : `JMP $4D03` (temps seul), tente portée :
  DROP (`$03` = 8, `JMP $4D00`), la tente reste sur la case.
- Marcher depuis l'intérieur est permis : `$0D5E` et `$0D88-$0D8C`
  repassent à 0 (T0C/S0B `$58E0`).

### 3.3 Quitter la case, revenir

T0C/S0B `$596E` : pour k = 12…27 sauf 19, un objet au sol (b1 = 0) passe
à `$FF` et garde ses coordonnées (b3 = `$D0`, b4 = `$D1`), sauf STICKS,
FIRE, CLUB et ROCK (perdus). Mesuré : HUT et TRENCH, SPEAR, SPLINT gardent la
case quittée (b3/b4), CLUB non ; la tente (premier jeu) aussi. Au retour,
la découverte « THERE IS A PREVIOUSLY DROPPED ITEM HERE » rend b1 = 0 et
T0D/S00 `$587E` recopie b1[20..22] + 1 dans `$0D89-$0D8B`. Un seul abri de
chaque sorte existe donc : en refaire un ailleurs efface l'ancien.

La découverte est T0A/S00 `$5BD0` : les objets dont b3/b4 valent la case
d'arrivée (`$4BA5`, `$4BA6`), premier jeu puis k = 22 à 14, entrent dans la
liste `$4B12` et lèvent l'événement `$0D90 + $16` ; mesuré (partie 3) :
l'arc, la lance et l'attelle laissés sur une case y sont retrouvés (b1 = 0,
« THERE IS A PREVIOUSLY DROPPED ITEM HERE. CHECK INVENTORY. »), le gourdin
non (b3 = 0, b4 non écrit).

**La pierre** (ROCK, k = 17) n'est pas fabriquée : T0D/S00 `$585F`, à
l'arrivée sur une case, met b1[17] = 0 quand elle est absente (b1 < 0) et
que la case n'est pas de l'eau (`$4B56` < 3) ; en partant, T0C/S0B la perd
(b1 = `$FF`, sans coordonnées). Il y a donc une pierre au sol sur toute
case de terre tant que le joueur n'en porte pas une (mesuré à la
`storewatch` de `$45D1` : `$5B75` la perd, `$5873` la pose ; la partie
sauvée l'a au sol de l'épave).

### 3.4 L'abri dans la simulation

- Température (T0B/S02, [state.md](logic/state.md)) : dedans, **35 °F** si
  b2[21] (USE IGLOO) ≠ 0, sinon l'air + 15 °F ; près d'un feu + 25 °F.
- Faune (D4, T06/S04 `$5866-$5888`) : dedans, le risque de blessure est
  multiplié par **0,1** ; ATTACK et SCARE restent possibles. Décision du
  15 octobre 2026 : le port fait **comme l'original** dans tout abri, l'abri
  naturel trouvé compris (§ 8.2). Depuis le même jour, ENTER de l'abri
  naturel **garde** l'animal (il l'effaçait encore) : la règle D4 vaut
  donc aussi là ([LOOK_UPDOWN.md](LOOK_UPDOWN.md) § 4).

## 4. Armes et outils (A2, `$5B33-$5C51`)

1. Famille 7 : AXE (58), BOW (89), SPEAR (90), CLUB (91) ; GUN, KNIFE,
   ROCK → msg 21.
2. Forêt (`$4B56` = 1) ou arbre en vue (`$D7`), sinon msg 76 (aussi dans
   l'eau ; épave et poste ne comptent pas).
3. **CLUB** (`$5B54`) : effort 0,01 (3,78) ; **INT(60 / √santé)** (21 ; 37 à
   santé 2,5) ; b1[16] = 0 ; msg 15 ; `JMP $4D03`.
4. **SPEAR, BOW, AXE** : hors régions 3, 4, 5 (`$601F`), ROPE (B1[60] ≥ 0)
   ou FISHNG GEAR (B1[67] ≥ 0), sinon « YOU NEED STRONG ROPE. » (msg 4) ;
   effort 0,02 (5,91) ; **t = INT(600 / (√santé × (3 couteau + 1)))** ;
   AXE : B1[58] = 0, B3[58] = 0 ; SPEAR : b1[15] = 0 ; BOW : b1[14] = 0,
   puis **INT(4 t / (lumière + 1))** ; msg 15 ; `JMP $4D03`.

| Cas (mesuré, minutes) | SPEAR, AXE | BOW |
|---|---:|---:|
| lumière 1, couteau 0 | 213 | 426 |
| couteau en usage | 53 | 106 |
| santé 2,5 | 379 | 758 |
| lumière 0 | 213 | 852 |
| lumière 0, couteau | 53 | 212 |

USE BOW/SPEAR/CLUB/ROCK (T11/S00 `$5C42`) : b2 = 1, puis CARRY (`$03` = 7,
`JMP $4D00`) : l'arme passe en main si la charge le permet (vraie partie :
USE CLUB → « EXCEEDS WEIGHT OR VOLUME LIMIT… » puis msg 10, l'arme reste au
sol). À KILL GAME/FISH (T0F/S07, [FORAGE.md](FORAGE.md) § 3.2) le premier
moyen en usage est pris et effacé : fusil 21, arc 20, lance 19, hache ou
couteau 18, gourdin ou pierre 17 ; p = 0,1 × (moyen − 18) de jour. Le temps
efface b2[14..17] (lot 2, CAMP.md § 2.1).

### 4.1 Prendre, ranger, poser (T0E/S02, mesuré)

La transaction du second jeu, partie 3 de la sonde (charge maintenue sous
les limites : la tente et la corde posées d'abord, un seul objet lourd en
main) :

| Commande | Effet sur b1 | Réponses mesurées |
|---|---|---|
| GET, CARRY (verbes 1, 7) | 3, en main, du sol ou du sac | déjà en main : msg 11 ; absent (ou au sol d'une autre case) : msg 1 |
| PACK (6) | 2, dans le sac, du sol ou de la main | déjà dans le sac : msg 11 |
| DROP, REMOVE (8) | 0, au sol de la case, b2 inchangé (l'arc lâché reste « en usage » jusqu'à ce que le temps passe) | déjà au sol : msg 11 |
| WEAR (5) | l'attelle seule : 1, b2[18] = 1 et sélecteur de soins 3 levé, comme USE SPLINT ; REMOVE, DROP, PACK, GET d'une attelle portée effacent b2 et le sélecteur (T0E/S0A `$5AC4`) | une arme, la pierre : « TRY ANOTHER VERB. » |
| USE BOW, SPEAR, CLUB, ROCK | 3 et b2 = 1, du sol ou du sac | — |
| MAKE ROCK | — | présente (au sol ou portée) : msg 11 ; absente : msg 21 |

Chaque succès répond « OK, WHAT NEXT? » (msg 10). Poids (W5, W6 du second
jeu) : arc et lance 50 oz, 90 in³ ; gourdin 100 oz, 200 in³ ; pierre
100 oz, 100 in³ ; attelle 50 oz, 120 in³. Au départ, GET ROCK dépasse la
limite (« EXCEEDS WEIGHT OR VOLUME LIMIT… »), comme USE CLUB.

## 5. Soins et protections (`$5A54-$5B32`)

**SPLINT** (`$5A65`) : un **raccourci** mène droit au temps quand une lance
est là (b1[15] ≥ 0), à l'épave (b1[23] = 0), au poste (b1[24] = 0) ou avec
la hache (B1[58] ≥ 0, présente au départ : le cas ordinaire). Sinon :
`$4B56` ≥ 2 → msg 76 ; effort 0,01 ; forêt ou arbre, sinon msg 76 ; ROPE ou
GEAR dans **toutes** les régions, sinon msg 4. Temps **INT(300 / (√santé ×
(lumière + 1)(couteau + 1)))** : 53 ; 106 de nuit ; 26 avec le couteau ;
94 à santé 2,5. b1[18] = 0, msg 15, `JMP $4D03`, sans effort par le
raccourci. Une attelle déjà là : msg 10 (cœur).

**SUNGLASSES** (43) et **SUNSCREEN** (44) (`$5A86`, `$5B0A`) : `$4B56` ≥ 2
(rocher, eau) → msg 76 ; effort 0,01 ; B1 = 0, B3 = 0 ; « GOOD! YOU MADE EYE
SHADES FROM SLITTED BARK. » (msg 28) ou « SMEARING MUD ON YOUR SKIN TO BLOCK
THE SUN'S RAYS. » (msg 205), puis msg 15 ; **30 minutes**, `JMP $4D03`. Les
usages de la crème (W8[44]) ne sont pas réécrits.

## 6. Fabrication 2 (A3, lot 5 : mesurée, non portée)

### 6.1 Corde (T10/S05 `$5809`, `$1E` = 8)

Effort 0,02 ; temps de base **T = INT(240 / ((lumière + 1)(couteau + 1)))**
(120 de jour) ; `$4B53` = 1 (corde forte) ; « FROM ARTIFICIAL [A] OR
NATURAL [N] MATERIALS? » (msg 24) :

- **A** : « ENTER ITEM NUMBER: [1]SLEEPING BAG, [2]PARKA, [3]WOOL PANTS,
  [4]TENT, [5]GNDCOVER, [6]JEANS, [7]RAFT, [0]NO ACTION. » (msg 107-108) ;
  0 → msg 10 ; un objet absent → bip et nouvelle saisie. Table réelle
  `$58E4` : 1, 2, 4, 9, 11, **19, 2** — le choix 6 détruit le chapeau
  (HAT), pas le jean, et le choix 7 la parka, pas le radeau (bizarrerie
  mesurée). Objet au sol : B1 = `$FF` ; porté : `$4B4B` = 1 et DROP (la
  transaction le détruit). Corde W5 = 32, W6 = 330, au sol ; « IT TOOK A
  WHILE TO MAKE YOUR ITEM. » (msg 191) ; T minutes.
- **N** : peau ≥ 36 oz → −36 (du sol, sinon du sac par DROP), corde, msg 191,
  T ; sinon « TOO LITTLE HIDE. LET'S SEARCH FOR PLANT FIBERS. » (msg 51),
  forêt (msg 76), régions 3-5 : bambou, msg 191, T ; ailleurs « ENTER ROPE
  DIAMETER IN QUARTER-INCH UNITS. » (msg 45), d < 38 (sinon msg 2) : W5 =
  **2 d²** oz, `$4B53` = 0 si d < 4, **INT(T d² / 5)** minutes (96, 384,
  1 536 pour d = 2, 4, 8), msg 15, `JMP $4D03`.
- La plage `$58EB-$58FF` désassemble mal (ORIGINAL_GAP.md : « endommagée ») ;
  les résultats ci-dessus sont ceux des octets livrés, exécutés.

### 6.2 Famille 9 et raquettes (T10/S05 `$5A5E`, `$1E` = 9)

- TRINKETS (74) : **un tirage**, RND < 0,2 → W8[74] = 2, 30 minutes, msg 15 ;
  sinon « SORRY, BETTER LUCK NEXT TIME. » (msg 67), 15 minutes.
- FLASHLIGHT, BINOCULARS, THERMOMETER (66, 68, 69), GOLD (75) → msg 21 ;
  STOVE (71) → msg 2 avec un feu, sinon « YOU NEED A FIRE TO BOIL OR COOK
  THINGS » (msg 65).
- Drapeaux : matériau `$5E81` (un des 1, 2, 4, 14, 15, 60 ou la peau, ou
  terrain dégagé en régions 3-4), sol `$5E80` (`$4B56` < 2), aiguille
  `$5E82` (SEWING KIT ou FISHNG GEAR). Effort 0,02 ; temps de base **T =
  INT(180 / ((lumière + 1)(couteau + hache + 1)))** (90 ; 30 avec hache et
  couteau).
- RAFT (70) : forêt, arbre ou rive (`$4B6B` = 1, 2), matériau, sinon msg 76 ;
  W5 = **21 × poids du corps** (`$4BF6` : 3 465), W6 = 36 × poids ;
  **4 T** minutes (360 ; 120), msg 15.
- UTENSILS (73) : sol `$5E80`, sinon msg 76 ; « WILDERNESS-MADE EARTHENWARE,
  EH! » (msg 206) ; matériau ou aiguille ; T ; msg 15.
- GEAR (67), SNOWSHOES (63), TRAP (72) : matériau ou aiguille (msg 76) ;
  GEAR avec l'aiguille : « SEWING KIT NEEDLES CAN BE BENT INTO FISH HOOKS. »
  (msg 207) ; T ; msg 15.
- SEWING KIT (65) : FISHNG GEAR → msg 112, gibier ou poisson → msg 113,
  sinon msg 76.
- CANTEEN (64) : msg 24 ; **A** : « [1]SLEEPING BAG, [2]PARKA, [3]TENT,
  [4]GND COVER, [5]RAINCOAT, [6]RAFT » (msg 114-115, table 1, 2, 9, 11, 12,
  70 conforme) : l'objet perd 16 oz (W5, W6), gourde de 16 oz, capacités
  `$4BF0`/`$4BF4`/`$4BF8`/`$4BFC` corrigées, T ; **N** : peau (« DO YOU
  WANT TO USE YOUR ANIMAL HIDE [Y/N]? », msg 26, 24 oz) en T, sinon poterie
  (sol `$5E80`) en **2 T** (180) ; gourde de 24 oz ; msg 191.

### 6.3 Vêtements, tente et sac de peau (T10/S00 `$584A-$599B`)

Noms 1-21 absents : b2[19] (peau en usage, USE HIDE) sinon « USE THE
APPROPRIATE ITEM FIRST. » (msg 25) ; peau ≥ **12 × W8[nom]** oz (PARKA 36,
TENT 216, BACKPACK 36) sinon msg 76 ; prise du sol, sinon du sac (DROP) ;
l'objet au sol, W10 = 60, W11 = 80 (pertes thermiques) ; effort 0,015 ;
**INT(350 √W8 / ((lumière + 1)(couteau + 1)(nécessaire + 1)))** minutes
(PARKA 303, TENT 742 ; 75 avec couteau et nécessaire) ; le sac remet
`$4BAF`, `$4BFC`, `$4BF4` ; msg 15, `JMP $4D00`.

## 7. Correspondance avec le port

| Original | Port |
|---|---|
| `$0D5D` lumière, `$4C34` santé | `light`, `s_health` |
| `$4B56` classe, `$D7` arbre, `$4B57` neige | `camp_class` (forêt = classe 1 ; les arbres du port poussent en forêt), `level_here` ≥ `M_SNOW` ; calculés par CAMP avant le module (`cr_class`, `cr_snow`) |
| `$D9`, `$D8` = `$7F` | case de l'épave (`MAP+3`, `MAP+5`), case du but (`MAP+8`, `MAP+9`) |
| B2[58], B2[59] hache, couteau en usage | `care_tools` sur `care_tool_x/y` (lot 13) |
| b1[14..18] BOW, SPEAR, CLUB, ROCK, SPLINT | `cr_b1` (`$FF`, 0 au sol, 1 portée, 2 sac, 3 main ; `splint_place` = `cr_b1` + 4) |
| b3/b4[14, 15, 18] | `cr_cx`, `cr_cy` (WILDERNESS) : la case de l'arc, de la lance, de l'attelle au sol |
| départ de la case (T0C/S0B), pierre de l'arrivée (T0D/S00) | `cr_still` = 0 par `forage_here`, réglé par `cr_here` (CRAFT) ou `inventory_settle` (STATUS) |
| b2[14..17] en usage | bits 2-4 de `fg_use` (FT_BOW, FT_SPEAR, FT_CLUB : gourdin ou pierre) |
| b1/b3/b4[20..22] HUT, IGLOO, TRENCH | `cr_sx`, `cr_sy` (case de chaque abri, `$FF` aucun) |
| `$0D5E`, b2[21] (igloo en usage) | `shelter_inside` 1, 2 (igloo : 35 °F) |
| `$4BCC` pas de santé | `health_period` |
| B1, B3/B4 de AXE, SUNGLASSES, SUNSCREEN, TENT | `it_place`, `it_x`, `it_y` |
| effort 0,01 / 0,02 / 0,023 | `cr_eff` 1 / 2 / 3, `camp_effort` |

## 8. Réalisation (15 octobre 2026)

### 8.1 Découpage

| Partie | Où | Rôle |
|---|---|---|
| `src/craft.s`, module CRAFT (entrée 9, l'ancienne place de la hutte, 1 639 octets) | NEOWILD.BLK sur les deux éditions, lu dans la fenêtre SIM (`$9600`, 4 blocs) | MAKE de T05/S00 `$551E` et de T10/S00 (A1, A2), USE HUT/IGLOO/TRENCH, TENT, BOW, SPEAR, CLUB ; ses textes originaux |
| `camp_craft` (CAMP) | module CAMP déjà chargé par MAKE et USE | calcule `cr_class`, `cr_snow` (SIM), lit CRAFT (`sim_fetch`), puis l'effort (`cr_eff`) et le temps (`camp_done`) ; USE d'un abri : `show_view` |
| `craft_state` (12 octets) | LOWPAGE `$03C3-$03CE` | `cr_b1` (+ `splint_place`), `cr_still`, `cr_sx/sy` ; sauvé (`sv_ranges`) |
| `craft_cells` (6 octets) | WILDERNESS (segment DATA) | `cr_cx`, `cr_cy` ; sauvé (§ 8.5) |
| GET, PACK, CARRY, DROP, WEAR de 89 à 93 | ITEMS (`item_noun`) → CRAFT (`cr_items`) | § 8.5 |
| ENTER, EXIT des abris fabriqués | SITES (`module_site`) | messages 10, 11, 1 mesurés |
| KILL GAME/FISH à l'arc, à la lance, au gourdin | FORAGE (`fr_hunt`, `fr_means`) | moyens 20, 19, 17 |
| BOW, SPEAR, CLUB plus en usage quand le temps passe | SIM (`module_survival_clock`) | |
| igloo à 35 °F | SIM (`thermal`) ; MEDICAL (`hz_air`, § 8.5) | |
| D4 : risque × 0,1 dans un abri, ATTACK et SCARE permis | OUTDOOR (`outdoor_hurt`) | |
| ATTACK selon le moyen en usage (17 à 21) | OUTDOOR (`outdoor_weapon`, `out_means_*`) | § 8.5 |
| INVENTORY : BOW, SPEAR, CLUB, ROCK, SPLINT, HUT, IGLOO, TRENCH | STATUS | |
| USE SPLINT d'une attelle au sol d'une autre case : msg 1 | MEDVIEW (`care_splint`) | |

Mesures de place : [MEMORY.md](MEMORY.md) § 20.

### 8.2 Écarts à l'original

- **Arbre en vue** (`$D7`) hors forêt : le port n'en a pas (ses arbres
  poussent en forêt, `tree_ok`) ; HUT, armes et attelle exigent la forêt.
- **Objets laissés au sol** : l'arc, la lance et l'attelle gardent leur
  case et sont retrouvés au retour, le gourdin est perdu, la pierre revient
  sur toute case de terre (§ 3.3, § 8.5) ; au retour, ni le message
  « THERE IS A PREVIOUSLY DROPPED ITEM HERE » ni le message 157 des abris.
- **Poids** (16 octobre 2026) : le second jeu pèse ses W5 et W6 (arc et
  lance 50 oz, 90 in³ ; gourdin 100 oz, 200 in³ ; pierre 100 oz,
  100 in³ ; attelle 50 oz, 120 in³) portés, rangés ou en main
  (`module_load_totals`, `lt_crw`/`lt_crv`) : ils comptent dans la charge,
  la marche et l'effort comme le premier jeu. Pris au sol (GET, PACK,
  CARRY, WEAR, USE), il est refusé quand le poids ou le volume de sa
  place dépasserait la limite (`cr_load`, la règle de T0E/S02 : le poids
  restant `$4BF8` doit rester ≥ 0 ; mesuré par `tools/re_load_probe.py` :
  GET ROCK avec 100 oz restants accepté, 99 refusé) ; GET ROCK au départ
  est donc refusé, comme dans l'original. Réponse du port « TOO MUCH
  WEIGHT OR VOLUME. DROP SOME GEAR. » au lieu du msg 7 ; USE garde l'arme
  « en usage » au sol, comme l'original (§ 4). Un objet déjà porté qui
  change de place n'est pas contrôlé (son poids ne change pas ; son
  volume passe d'une place à l'autre). Reste du lot 14 : les formules des
  conteneurs.
- **Réponses de la transaction** : un succès affiche le texte du port
  (« HAND: BOW », « PACK: », « GROUND: », « WEARING: », comme le premier
  jeu) au lieu de « OK, WHAT NEXT? » ; WEAR d'une arme ou de la pierre
  répond « YOU CAN'T WEAR THAT. » au lieu de « TRY ANOTHER VERB. » ; PACK
  sans sac porté refuse comme pour le premier jeu ; WEAR SPLINT porte
  l'attelle et lève le sélecteur 3 comme l'original, mais le port n'a pas
  de b2[18].
- **EXIT SHELTER** sort de tout abri, fabriqué ou naturel : **écart voulu,
  décision du 15 octobre 2026** (l'original répond msg 17 dans un abri
  fabriqué : seul l'abri naturel répond à SHELTER) ; marcher depuis un abri
  reste refusé (« EXIT SHELTER BEFORE TRAVELLING. »).
- **Faune dans un abri** : D4 change OUTDOOR (blessure × 0,1, ATTACK/SCARE
  permis, plus de départ automatique), dans tout abri, l'abri naturel
  trouvé compris : règle de l'original confirmée par l'utilisateur le
  15 octobre 2026 (avant le lot 3, la cabane protégeait absolument) ; la
  vue de l'intérieur ne fait toujours pas arriver d'animal
  (`module_shelter_view`) et n'en montre aucun (pas de vue dans un abri).
  ENTER SHELTER (l'abri naturel) n'efface plus l'animal présent (même
  jour, `src/sites.s`) : dedans, il est toujours là (risque × 0,1) ; EXIT
  le montre devant l'abri.
- **ATTACK sans moyen en usage** : le port garde sa règle d'avant le lot 3,
  la hache ou le couteau accessibles (moyen 18) sans USE, là où l'original
  répond « USE THE APPROPRIATE ITEM FIRST. » (msg 25) : **écart voulu,
  décision du 15 octobre 2026**. Les seuils sont ceux de nuit (`$19` = 2 −
  lumière : lot 11).
- **Grille et panneau** (§ 8.6) : GET de la grille tape `GET x` pour le
  second jeu (en main, comme l'original) alors qu'il range le premier jeu
  au sac (`PACK x`) ; l'indice « ITEMS » du panneau compte l'arc, la lance,
  l'attelle et le gourdin au sol ici, pas la pierre (présente sur toute
  case de terre, elle l'allumerait partout).
- **Familles 17 et mots 101-109** (MAKE TREE, BAIT, SHADOW, STATUS) : « NOT IN
  THIS VERSION YET. » ; les animaux de la région : msg 21 (sans le msg 11
  d'une carcasse).
- **A3** (vêtements de peau, T10/S05) : « NOT IN THIS VERSION YET. »
  (lot 5).
- **Moyen 17** : p = −0,1 de jour est remplacé par 0 (`DIV10` de la ROM
  perd le signe) : même résultat, RND ≥ 0.

### 8.3 Tests

`tests/test_craft.py` : partie 1, les 109 cas de T10/S00 et T11/S00 de
`results.json` traduits dans l'état du port (le contexte de `camp_craft`
imposé à la lecture du module), messages, minutes, effort, objets, abris,
drapeaux comparés ; 67 cas écartés avec leur raison (A3 : lot 5 ; arbre
hors forêt ; USE SPLINT : `test_care.py`) ; partie 2, les messages de
34 commandes de la vraie partie (MAKE ROCK compris) ; partie 3, la
transaction du second jeu (§ 4.1) rejouée commande par commande, b1, b2 et
refus comparés ; partie 4, l'inventaire, KILL GAME à l'arc, le temps qui
efface l'usage, USE HUT ailleurs, une vraie marche (gourdin perdu, pierre
de la case suivante), SAVE/RESTORE des objets sur leurs cases, ATTACK BEAR
avec chaque moyen en usage, et MAKE TRENCH et GET ROCK sur l'édition de
140 Ko (lecture de CRAFT sur NEOWILD.BLK). `--original` : les parties 1 à 3,
dans `make test-original` après `tools/re_craft_probe.py`.
`tests/test_forage.py` joue les cinq cas des moyens 20, 19, 17, et ses cas
de carcasse au fusil prennent désormais le moyen 21 d'OUTDOOR.
`tests/test_exposure.py` (`shelters`) : l'igloo à −20 °F donne le compteur
de gelure de 35 °F.

### 8.4 Étape 3 : les sprites des abris (15 octobre 2026)

Sur NeoWildernessXL (décision du 15 octobre 2026), la tente, la hutte
(`cabin.bin`), l'igloo et la tranchée sont des **sprites de site** comme le
rondin, le rocher et le poste du lot 6 ([IMPLEMENTATION.md](IMPLEMENTATION.md)
« Sprites de site ») : vue locale sur leur case, panneau jusqu'à 8 cases
ailleurs. Mémoire : [MEMORY.md](MEMORY.md) § 21.

- **Règle de l'original** (SURV3D, code de site `$0D84`, table `$1D0D`) :
  1 tente `T16/S0`, 2 hutte `T16/S4`, 3 igloo `T16/S9`, 4 tranchée
  `T16/SD`, 5 abri naturel. À l'arrivée sur une case, T0D/SE `$5F13-$5F64`
  prend d'abord le poste ou l'épave (`$D8`, `$D9`, codes `$86`, `$87`, bit 7),
  puis le premier drapeau levé de `$0D8A` igloo, `$0D89` hutte, `$0D88`
  tente, `$0D8C` abri naturel, `$0D8B` tranchée. Le port garde cet ordre pour
  la vue locale (`local_order` de PROJECT) : épave, poste, igloo, hutte,
  tente, rondin ou rocher, tranchée, puis l'animal. Sans bit 7, ces sprites
  sont relevés de 10 lignes comme le rondin et le rocher.
- **Où.** La hutte, l'igloo et la tranchée sur leur case (`cr_sx`,
  `cr_sy`) ; la tente là où elle est posée au sol (`it_place` 0, `it_x`,
  `it_y` de l'objet 9 : USE TENT la pose), jamais sur la case de l'épave
  (l'original y refuse USE TENT, msg 49 : la tente de l'épave n'est pas
  montée). Vue locale centrée sur le cap du joueur, comme le poste.
- **Panneaux.** Sept candidats au lieu de trois (épave, abri naturel, poste,
  tente, hutte, igloo, tranchée ; à égalité, le premier) ; un abri plus loin
  d'une case entière que le meilleur panneau déjà trouvé est écarté sans
  calcul flottant (borne entière de `project_shelter`).
- **Couleurs** fixes (`tools/dhgr_palette.py` SPRITES) : tente orange au
  sol vert, hutte brune au chaume vert (celles de l'ancienne cabane), igloo
  blanc aux joints bleu clair, tranchée verte (branches) et brune.
- **Vue rafraîchie.** MAKE HUT, IGLOO, TRENCH, USE TENT (CRAFT), DROP et GET
  (ITEMS) oublient le cache de `scene_prepare` : la vue suivante, celle
  qui suit le temps de la fabrication comprise, montre l'abri.
- **Édition de 140 Ko** : inchangée. Elle n'a pas la place des 8 blocs ;
  ses abris fabriqués n'ont pas de sprite et la vue ne les montre pas
  (paysage seul, comme avant l'étape 3) ; ils existent pour MAKE, USE,
  ENTER, EXIT, INVENTORY, la température et la faune. `build_disk` y met
  `site_blocks` à 0 et coupe PROJECT à `project_tail` : volume, stock et
  code de vue identiques.
- **Écarts.** L'original ne dessine un abri que sur sa case, et la tente
  seulement après USE TENT jusqu'au départ du joueur (`$0D88`, que le retour
  ne relève pas) ; le port montre aussi les panneaux (comme pour les autres
  sites) et toute tente au sol hors de l'épave, montée ou seulement posée
  (DROP TENT). À l'arrivée sur un site sans bit 7, l'original règle
  `$E7` = −1 (vue vers le bas, T0D/SE `$5F6F`) : le port garde la vue à
  niveau, comme pour le rondin et le rocher (LOOK_UPDOWN.md § 1.2). Un seul
  site par vue (lot 6).
- **Tests.** `tests/test_sites.py` `built_shelter_sprites` : sur un disque
  de comparaison (XL), chaque abri vu sur sa case et en panneau, exact au
  pixel contre `tools/dhgr_ref.py` (`scene_ref.built_shelters`, `select`
  étendu), l'ordre local (igloo, hutte, tente, rondin, tranchée), la tente
  de l'épave absente, une lecture de NEOWILD.BLK par sprite (2, 3, 2,
  1 blocs) ; MAKE TRENCH, DROP TENT, GET TENT redessinent la vue ; sur
  l'édition de 140 Ko, une hutte sur la case ne dessine et ne lit rien,
  la même hutte sur NeoWildernessXL lit ses 3 blocs.

### 8.5 Suite de l'étape 1 : second jeu, pierre, armes, igloo (15 octobre 2026)

Les quatre restes de l'étape 1 (TODO.md), fidèles à la ROM (§ 3.3, § 4.1,
partie 3 de la sonde ; seuils d'ATTACK de `build/regions/fauna.json`, mesurés
par `tools/re_region_fauna_probe.py`). Mémoire : [MEMORY.md](MEMORY.md) § 22.

1. **GET, PACK, CARRY, DROP, REMOVE, WEAR** de 89 à 93 (BOW, SPEAR, CLUB,
   ROCK, SPLINT) : `item_noun` (ITEMS) lit CRAFT dans la fenêtre SIM et
   saute à `cr_items` (le module garde une seule entrée : verbe 3 MAKE,
   2 USE, sinon la transaction). GET et CARRY en main, PACK dans le sac
   (sac porté exigé), DROP et REMOVE au sol de la case, WEAR l'attelle
   (sélecteur de soins 3 de USE SPLINT, effacé quand elle quitte le corps) ;
   msg 11 (déjà), msg 1 (absent). **ROCK** : une pierre au sol de l'épave au
   départ, puis sur toute case de terre quand le joueur n'en porte pas ;
   MAKE ROCK → msg 11 ou msg 21 ; USE ROCK la prend en main « en usage »
   (bit du gourdin, moyen 17 de KILL et d'ATTACK). L'USE de 92 passe par
   CAMP comme 89 à 91.
2. **Une case par objet** : `cr_cx/cr_cy` (arc, lance, attelle) ; `cr_where`
   rend `$FF` pour un objet au sol d'une autre case (le b1 de l'original une
   fois la case quittée), MAKE en refait alors un sur la case ; `cr_still`,
   mis à 0 par `forage_here` à chaque pas qui change de case, fait perdre le
   gourdin et poser la pierre (`cr_here`, `inventory_settle`) ; l'ancienne
   case commune `cr_gx/cr_gy` disparaît. SAVE garde le tout (`craft_state`,
   `craft_cells` dans `sv_ranges`) ; USE SPLINT (MEDVIEW) lit la case de
   l'attelle.
3. **Armes contre les animaux** : `outdoor_weapon` prend le premier moyen en
   usage comme T0F/S07 `$590F` (fusil 21, arc 20, lance 19, hache ou couteau
   en usage sur la case 18, gourdin ou pierre 17), efface son drapeau, et
   lit les seuils `out_means_injury` (0,02 × fiche[moyen]) et
   `out_means_success` (0,005 × fiche[moyen + 6]) ; sans moyen en usage, la
   hache ou le couteau accessibles (§ 8.2). Les paquets de région écrivent
   les cinq moyens (`fauna_reactions` : 44 → 76 octets). Sierra, ours :
   blessure 70 %, 70 %, 50 %, 30 %, 10 % et réussite 0,5 %, 1,5 %, 3,5 %,
   10 %, 17,5 % pour les moyens 17 à 21 (seuils de nuit).
4. **Igloo des dangers** : `hz_air` (HAZARDS) prend 35 °F dans l'igloo
   (`shelter_inside` 2), comme `thermal` ; la place vient de la table
   `hz_since_lo/hi`, doublon de `injury_since_lo/hi` du même module MEDICAL
   (30 octets rendus, 6 pris).

### 8.6 Étape 2 : la page CRAFT, la grille, le panneau (15 octobre 2026)

Le « livre de recettes » de TODO.md, sans grille 3 × 3 ni recette
inventée : les MAKE de l'original que CRAFT exécute, rien d'autre.
Mémoire : [MEMORY.md](MEMORY.md) § 23 et § 25 ; navigation : [MENUS.md](MENUS.md)
§ 5.

**La page.** Une page du haut entre OBJECTS (l'ancienne INVENTORY, depuis
le 15 octobre 2026) et HELP (onglet `CRAFT`, lettre R), même système de
focus que les pages à curseur. Sur NeoWildernessXL, chaque groupe et la
recette choisie sont des post-its ([MENUS.md](MENUS.md) § 9.3 : à gauche
colonnes 0-28, à droite 30-79 ; le texte aux mêmes colonnes que sur
140 Ko). Depuis le
15 octobre 2026 (deuxième version, maquette approuvée par l'utilisateur),
deux moitiés séparées par un trait MouseText (colonne 30) :

```
 STATUS  OBJECTS  CRAFT  HELP  OPTIONS  MENU             S/O/R/H, LEFT/RIGHT
 SHELTERS                     | > HUT                                   POSSIBLE
 > HUT         ✓  2 H 49      |   SHELTER: AIR +15 F, ANIMALS 10X SAFER
   IGLOO       ☒  4 H 14      |   NEEDS:
   TRENCH      ✓  1 H 24      |    ✓ DRY LAND
 WEAPONS AND TOOLS            |    ✓ NOT AT THE WRECK OR THE POST
   CLUB        ✓      21 MIN  |    ✓ WOODS
   SPEAR       ☒  3 H 33      |   TIME: 2 H 49 (DAY, NO AXE, HEALTH 100%)
   BOW         ☒  7 H 06      |   SLOWER: NIGHT, AXE NOT IN USE, LOW HEALTH
   AXE         ◆              |
   SPLINT      ✓      53 MIN  |
 PROTECTION                   |
   SUNGLASSES  ◆              |
   SUNSCREEN   ✓      30 MIN  |
 …
 ✓ POSSIBLE   ☒ MISSING   ◆ DONE
↑↓ CHOOSE   RETURN: MAKE HUT                                          ESC: VIEW
```

(en forêt, sans corde ni nécessaire de pêche, loin de l'épave, de jour, à
la santé de la partie sauvée : `tests/test_craft_page.py`,
`build/craft_page_v2.png` ; une recette manquante choisie :
`build/craft_page_v2_missing.png`.)

- **Groupes** : SHELTERS (HUT, IGLOO, TRENCH), WEAPONS AND TOOLS (CLUB,
  SPEAR, BOW, AXE, SPLINT), PROTECTION (SUNGLASSES, SUNSCREEN), dans
  l'ordre des familles de T10/S00 ; les en-têtes ne se choisissent pas.
- **État** (colonne 15), en MouseText du IIe enhanced et du IIc :
  `ALTCHARSET` (`$C00F`) est levé à l'arrivée sur la page et baissé
  (`$C00E`) à chaque sortie (vue, autre page, `MAKE x`) ; le reste du jeu
  garde le jeu de caractères standard (`ALTCHAROFF` du démarrage, aucun
  texte clignotant ailleurs). Coche `$44` : possible ici ; **X inverse**
  `$18` : il manque quelque chose (MouseText n'a pas de croix ; le X
  inverse du jeu standard s'affiche pareil avec ou sans `ALTCHARSET`) ;
  losange `$5B` : déjà fait, un ici ou emporté (msg 11, msg 10 de
  l'attelle). Trait vertical `$5A`, flèches `$4B`/`$4A` de la rangée 23.
  a2shot (`apple2e_char.rom`, 342-0265-A) les dessine. **Sur
  NeoWildernessXL** (15 octobre 2026, [MENUS.md](MENUS.md) § 9),
  `ALTCHARSET` reste levé pour toute la partie (les deux `sta $C00E`
  deviennent `$C00F`), la page est une rangée plus bas (rangées 2 à 20,
  sous la ligne des onglets ; la légende en rangée 21) et son pied de page
  est celui des pages (`←→ PAGE  ↑↓ CHOOSE  ↵ …`, `ESC VIEW` en
  colonne 70) ; l'édition de 140 Ko garde la page décrite ici.
- **Temps** (colonnes 17 à 27) : les minutes que MAKE passerait ici,
  calculées par la routine même de MAKE (`cr_minutes`, avant `craft_page`,
  formules de la ROM du § 3.1, § 4, § 5 dans l'ordre de leurs opérations)
  avec la lumière, la hache ou le couteau en usage sur la case et la santé
  du moment ; « 1 H 24 », « 21 MIN », les minutes en colonne. Rien pour
  une recette déjà faite (MAKE ne passe pas de temps).
- **Panneau de droite** : la recette choisie (HUT sur la rangée
  d'onglets), son verdict (POSSIBLE, MISSING, DONE), son effet (abri : air
  + 15 °F ou 35 °F dans l'igloo, blessure des bêtes × 0,1 ; armes : KILL
  GAME, FISH, ATTACK ; hache : abris plus rapides en usage, attelle,
  ATTACK ; attelle : bras ou jambe cassés ; visière : ophtalmie des
  neiges ; boue : coup de soleil), puis `NEEDS:` et chaque contrôle de
  `src/craft.s`, dans son ordre, coche ou X inverse : pas dans l'eau
  (msg 92), ni à l'épave ni au poste (msg 49), la forêt, la neige, la
  corde ou le nécessaire de pêche (msg 4 ; ni l'un ni l'autre en Birmanie,
  Nouvelle-Guinée, Bolivie pour les armes), sol dégagé ou forêt (msg 76) ;
  l'attelle montre d'abord son raccourci (`AXE, SPEAR, WRECK OR POST;
  OR:`), puis la forêt et la corde ; `YOU HAVE ONE ALREADY` (losange) en
  tête pour une recette faite. Enfin `TIME:` avec ce dont il dépend
  maintenant (`DAY`/`NIGHT`, `AXE`/`NO AXE`, `KNIFE`/`NO KNIFE`, `HEALTH
  n%`, arrondi de STATUS ; `ALWAYS` pour les 30 minutes de la visière et
  de la boue) et `SLOWER:` ce qui l'allonge (`NIGHT`, `AXE NOT IN USE`,
  `KNIFE NOT IN USE`, `LOW HEALTH`). Pas de `TIME` pour une recette faite.
- **Rangée 23** : ce que tape RETURN : `RETURN: MAKE HUT` sur une recette
  possible, `RETURN: NOTHING (MISSING)` ou `(DONE)` sinon, `RETURN: VIEW`
  sur les onglets.
- **Touches** : à l'arrivée le focus est sur les onglets (gauche
  INVENTORY, droite HELP) ; bas et haut vont de recette en recette (`>` en
  colonne 1 et dans le panneau), haut sur la première rend le focus aux
  onglets, bas sous la dernière revient à la vue ; S, M, I, H, T comme
  partout, Échap la vue. **RETURN** (ou espace) sur une recette possible
  tape `MAKE x` dans `inbuf` et lance `do_command` : le chemin du clavier,
  ses temps, ses efforts, ses messages (la page ne pose aucun prérequis :
  la hache ou le couteau en usage raccourcissent le temps, au joueur de
  les mettre, comme au clavier). Sur une recette manquante ou faite RETURN
  bipe et ne fait rien.
- **Temps affiché = temps passé** : l'horloge avance exactement du temps
  affiché (`camp_done`), sauf si un animal arrive pendant la fabrication
  (balayage immobile de T0A/S05, hors de l'épave, quelle que soit la
  fréquence NATURE) : le temps s'arrête alors, comme au clavier.
- **Dessin** : différentiel (`t_update`), la moitié gauche puis la droite,
  chaque cellule écrite une fois ; les états et les temps sont calculés
  une fois à l'arrivée (dix `cr_minutes`, cinq racines carrées), un
  déplacement du curseur ne recalcule rien et ne stocke que les cellules
  qui changent (13 de la rangée d'onglets à HUT, mesuré par `storewatch`).
- **Hors de la page** : MAKE FIRE, WATER (lot 2) restent dans la liste
  MAKE de la grille, avec leur file de prérequis ; MAKE STICKS et HIDE
  n'ont rien à fabriquer ; les recettes d'A3 (§ 6) répondent encore « NOT
  IN THIS VERSION YET. » et n'y sont pas (lot 5). **Alimenter le feu**
  n'est pas une commande de l'original : son feu brûle jusqu'à DOUSE, et
  celui du port aussi depuis le 15 octobre 2026 (durée de vie retirée,
  CAMP.md § 8) ; MAKE FIRE sur un feu répond msg 11 et USE STICKS ne fait
  que prendre les branches en main. Décidé le 15 octobre 2026 : aucune
  commande pour entretenir le feu, il n'y a rien à entretenir.
- **Code** : la page est la queue du module CRAFT (`craft_page` …
  `craft_end`, 2 209 octets) ; `pg_craft` (STATUS) dessine la rangée
  d'onglets, écrit dans l'entrée 9 du répertoire la longueur du module
  entier, empile l'adresse de la page et lit CRAFT par `sim_fetch` : son
  RTS entre dans la page, qui remet la longueur des recettes seules (MAKE,
  USE et la transaction ne lisent que leurs 4 blocs : 1 878 octets) et
  repart vers les autres pages par leurs entrées résidentes (`scr_status`,
  `scr_inventory`, `scr_help`, `scr_topo` ; MEDICAL en empilant
  `page_medical` avant `status_fetch`). Aucun octet résident. Le contexte
  (classe du sol, neige) est recalculé par la page (`cr_water`,
  `woods_here`, `level_here`), comme `camp_class` (CAMP n'est pas chargé).
  Le module entier fait 4 087 octets, **8 blocs** de NEOWILD.BLK (6
  avant), lus dans `$9600-$A5FF` : par-dessus les tampons du feu et le
  début de GRID (`$A300`), recopié de toute façon à chaque usage
  (`grid_fetch`) ; les octets de travail de la page suivent `craft_end`
  (42 octets, hors image). MEMORY.md § 25.

**La grille** (MENUS.md § 4.2, § 4.3) : GET, DROP et USE proposent l'arc, la
lance, le gourdin, la pierre et l'attelle (`gr_where`, GRID : la place
exacte, comme `cr_where` après `cr_here`) ; GET compose `GET x` (en main),
DROP `DROP x` pour ce qui est porté, au sac ou en main, USE `USE x` pour ce
qui est ici ou emporté. La file de KILL prend `USE BOW` puis `USE SPEAR`
avant la hache et le couteau (ordre de T0F/S07), et rien quand l'arc, la
lance, le gourdin ou la pierre est déjà en usage (étape S_BOW, S_SPEAR,
contrôle 15). Les verbes grisés : `member` (MENUSWAP) donne pour 89 à 93
un sur-ensemble (leur place, le sol de n'importe quelle case ; la pierre
absente, sur la case de terre atteinte depuis : `cr_rock_land`).

**Le panneau** : l'indice `ITEMS: INV` s'allume aussi pour l'arc, la lance,
l'attelle au sol de la case et le gourdin tant que le joueur ne l'a pas
quittée (SUMMARY) ; pas pour la pierre.

**Tests** : `tests/test_craft_page.py` (les deux éditions) : la page à
l'écran (texte et codes bruts : groupes, coche, X inverse, losange, trait,
flèches, légende), `ALTCHARSET` levé sur la page et baissé en la quittant
(vue, INVENTORY, HELP, Échap, bas sous la dernière recette), une écriture
par cellule changée quand le curseur bouge (`storewatch`), le panneau de
HUT, IGLOO, AXE, SPLINT, SUNSCREEN, l'état de chaque recette contre le
MAKE tapé en trois lieux (forêt sans corde, forêt, épave), le temps
affiché (liste et panneau) = la formule de la ROM = l'avance de l'horloge
après RETURN dans cinq conditions (jour ; nuit ; hache en usage ; couteau
en usage la nuit ; santé 2,5 avec hache et couteau : 17 fabrications, un
tirage rejoué depuis un autre état de `weather_seed` quand un animal
arrête le temps), RETURN sur HUT, CLUB, SPLINT = les mêmes commandes
tapées (état comparé comme `test_menu_bar.py`), RETURN sur une recette
manquante (IGLOO) ou faite (AXE), les touches du cycle ; la grille (GET
BOW, listes USE et DROP, KILL avec `USE BOW`, KILL seul avec la lance en
usage, DROP BOW) = les commandes tapées ; l'indice ITEMS.
`test_focus.py`, `test_interface.py`, `test_screen_returns.py` suivent la
rangée d'onglets et la lecture de CRAFT (8 blocs) à l'ouverture de la
page ; `test_menu_bar.py` ôte la pierre pour griser USE ; `test_craft.py`
vérifie MAKE après le passage à `cr_minutes` (109 cas de la ROM).

## 9. Incertitudes

- ENTER TENT n'a pas été joué ; le port le traite comme ENTER HUT.
- La table du menu de la corde (§ 6.1) contredit son texte ; la plage
  `$58EB-$58FF` reste à relire avant le lot 5.
- Le relais de `$4D39` répond la même touche à chaque question : le « N » de
  la question 26 (peau pour la gourde) n'a pas été mesuré.
- B2[9] de la tente n'est remis à zéro que par la marche ; l'effet d'une
  tente « en usage » hors de l'abri n'est pas lu.

### Refus de charge (16 octobre 2026, XL)

Les objets fabriqués affichent TRANSFER REFUSED puis chaque limite dépassée :
WEIGHT en OZ et WEAR/PACK/HANDS en IN3, avec NEED et FREE exacts. Le calcul
ne change ni les stocks ni les règles natives : notamment USE peut conserver
son drapeau natif même si la prise en main échoue. EQUIPMENT expose cet état
réel indépendamment de la position physique de l’objet.
