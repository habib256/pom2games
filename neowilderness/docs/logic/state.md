# État du jeu et inventaire (original)

Rétro-ingénierie de l'état de *Wilderness* (Electric Transit, 1985) à partir
des écrans STATUS et INVENTORY. Sources : `build/re/ov5.s` (STATUS, partie 1),
blocs chaînés extraits dans `build/re_state/` (`ov5b`, `ov5c`), `build/re/ov6.s`
(INVENTORY), aides du cœur `$4D00` (`build/re/core4d.s`), et vidages RAM
avant/après REST, EAT, DRINK dans a2shot. Outils : `tools/re_state_dis.py`
(listing compact), `tools/re_state_fp.py` (flottants Applesoft),
`tools/re_state_items.py` (tables d'objets).

Notations : `W(a)` = mot signé 16 bits petit-boutiste en `a` ; `F(a)` =
flottant Applesoft 5 octets en `a` (le moteur calcule avec les routines de
la ROM : `$EAF9` MOVFM, `$EB2B`/`$EB1E`/`$EB21` MOVMF, `$E97F` FMULT,
`$EA66` FDIV mem/FAC, `$E7BE` FADD, `$E7A7` FSUB mem−FAC, `$EBB2` FCOMP,
`$E10C` → entier, `$EA39`/`$EA55` ×10/÷10, `$EE8D` SQR, `$F09E` ATN,
`$EF09` EXP). « Incertain » marque ce qui n'est pas vérifié.

## Le bloc d'état `$4000-$4CFF`

Tout l'état d'une partie tient dans `$4000-$4CFF` (13 secteurs). La
« première partie » du menu est une partie sauvegardée : ce bloc est lu tel
quel depuis la face programme (piste SMALLDOS `$12`, 13 secteurs ; identique
octet pour octet à la RAM à la première vue). C'est aussi ce que SAVE/RESTORE
écrivent (`SVGO2`). L'initialisation d'une *nouvelle* partie (niveau de
difficulté, autre région) est faite ailleurs (GO1/TMAKE) : non couverte ici.

| Zone | Contenu |
|---|---|
| `$4000-$417B` | 5 tableaux d'octets par objet, 76 entrées (B0..B4) |
| `$417C-$45A3` | 7 tableaux de mots par objet, 76 entrées (W5..W11) |
| `$45A4-$462F` | 5 tableaux d'octets, 28 entrées (ressources naturelles, constructions) |
| `$4630-$47B7` | 7 tableaux de mots, 28 entrées |
| `$47B8-$486B` | Enregistrements de 15 octets (conditions : blessures/maladies) |
| `$486C-$48B3` | Enregistrements de 12 octets (dont l'état physiologique `$48A8`) |
| `$48B4…` | Copie des paramètres climatiques de région (même format que TOPO `$6000`) |
| `$4950` | Tableau de flottants F1[1..25] (`$4950 + 5·(i−1)`) |
| `$49CD` | Tableau de flottants F2[1..26] (`$49CD + 5·(i−1)`) |
| `$4AFF-$4B0C` | Indices de mots calculés pour STATUS (voir plus bas) |
| `$4B40-$4BC8` | Drapeaux et petits compteurs (terrain, météo, état) |
| `$4BD2-$4C03` | Compteurs 16 bits (nutrition, capacités) |
| `$4C16-$4C8D` | Flottants scalaires (temps, santé, température…) |

Accès (cœur, table de sauts `$4D00`) :

| Entrée | Rôle |
|---|---|
| `$4D0C` X, Y | `$CE` ← tableau d'objet X (`$4000,$404C,$4098,$40E4,$4130` pour X=0..4 ; `$417C,$4214,$42AC,$4344,$43DC,$4474,$450C` pour X=5..11, Y doublé) |
| `$4D0F` X, Y | idem pour les 28 entrées (`$45A4…$4614`, `$4630…$4780`) |
| `$4D12` X, Y | `$CE` ← `$47B8 + 15·X` (Y−1) |
| `$4D15` X, Y | `$CE` ← `$486C + 12·X` (Y−1) |
| `$4D1B` X, Y | X/Y ← adresse de F1[X] (Y=1) ou F2[X] (Y=2) |
| `$4D18` X, Y | lit `$48B4 + 12·(X−1) + (Y−1)` (paramètre de région) |
| `$4D1E` A | `$CE` ← `$6000 + 32·(A−1)` (en-tête TOPO) |
| `$4D21` / `$4D24-$4D2A` | Affiche le message n (puis retour à la boucle `$B000`) |

## Objets (inventaire)

Index = identifiant du nom dans le parseur (1..75, voir `docs/ANALYSE.md`).
Les objets sans nom propre dans le vocabulaire : 18 COTTN SOCKS, 41 FRSTAID
KIT, 42 SNAKEBT KIT, 48 SALT TAB, 65 SEWING KIT (un adjectif les distingue).
Second jeu (28 entrées, `$4D0F`) : index k ↔ nom 75+k (1 BEAR … 11 PLANTS,
12 STICKS … 22 TRENCH, 23 AIRPLANE, 24 OUTPOST, 25 CITY).

| Tableau | Sens |
|---|---|
| B0 `$4000` | Ordre/clé d'affichage (incertain) |
| B1 `$404C` | **Emplacement** : `$FF` absent, 0 GND (au sol), 1 WEAR, 2 PACK, 3 CARRY, 4 nourriture/eau répartie au sol et dans le sac |
| B2..B4 | Peu utilisés ici ; second jeu : B2 = stock de la ressource (insectes 6, fruits 72, cactus 96, champignons 48, plantes 120 — incertain), AIRPLANE B3/B4 = (200, 134) (incertain) |
| W5 `$417C` | Poids total en oz (équipement), quantité totale en oz (nourriture, eau) |
| W6 `$4214` | Volume en in³ (équipement), in³ par oz (nourriture) |
| W7 `$42AC` | Nourriture/eau : oz **au sol** ; équipement : durée d'usage en minutes (TENT, ROPE, KIT… 30 ; incertain) |
| W8 `$4344` | Nourriture/eau : oz **dans le sac** (eau : dans la gourde) ; consommables : nombre d'utilisations restantes (MATCHES 24, SUNSCREEN 7…) ; vêtements : petite valeur (temps pour s'habiller ? incertain) |
| W9 `$43DC` | Nourriture : **kcal par oz** (NUTS 160 … APPLES 13) ; vêtements : partie du corps (1 tout, 2 torse, 3 tête, 4 jambes, 5 pieds, 6 mains) |
| W10 `$4474` | Nourriture : **% d'eau** (APPLES 90, NUTS 5) ; vêtements : perte thermique à sec (plus petit = plus chaud) |
| W11 `$450C` | Nourriture : **heures avant pourriture** (≤ 0 affiche SPOIL ; 2426 = non périssable) ; vêtements : perte thermique **mouillé** (coton 1500-2000) |

Second jeu : W5/W6 2000/10000 pour les constructions (intransportables) ;
gibier, poisson, insectes, fruits, cactus, champignons, plantes ont W9 kcal/oz,
W10 % d'eau, W11 heures avant pourriture (ex. FISH 40/75/6, PLANTS 10/90/120).

Vérifié en jeu : EAT CHEESE 8 oz depuis le sac fait passer W8 de 32 à 24, W5
de 48 à 40, les kcal mangés `W($4BDC)` de +880 (= 8 × 110), le poids restant
`W($4BF8)` de +8 et le volume de sac restant `W($4BF0)` de +16 (2 in³/oz).

### Écran INVENTORY (overlay 6)

Ordre d'affichage : objets 1-21 (couchage, vêtements, sac), 52-56, 60-65,
67-73, nourriture 23-37 puis ressources naturelles du second jeu (gibier…
plantes), eau (22), 38-51, 57-59, 66, 74-75, puis second jeu 12-22 (STICKS…
TRENCH). Les noms affichés viennent d'une liste dans l'overlay (SLPNG BAG,
DOWN PARKA, … ; voir l'annexe).

- Équipement : nom + mot d'emplacement (GND/WEAR/PACK/CARRY) si B1 ≠ `$FF`.
- Nourriture : « -G n OZ » (W7) et/ou « -P n OZ » (W8) selon B1 (0, 2 ou 4) ;
  « SPOIL » si W11 ≤ 0.
- Eau : « -G n OZ » (W7) et « -CAN n OZ » (W8, gourde).
- Consommables 38-51 etc. : suffixe -G/-W/-P/-C + W8 + « OZ » (FUEL) ou
  « USES » (MATCHES, IODIN TAB, SALT TAB : nombre seul).
- Bas d'écran « REMAINING AVAILABLE QUANTITIES » : WEIGHT `W($4BF8)` oz,
  WEAR VOL `W($4BEE)`, PACK VOL `W($4BF0)`, CARRY VOL `W($4BF2)` in³ ;
  ce sont des **capacités restantes**, calculées hors de l'overlay.
  Autres valeurs liées : `W($4BFA)` = 815, `W($4BF4)` = 1926 (volume de sac
  utilisé ? −16 après avoir mangé), `W($4BFC)` = 534, `W($4BF6)` = 165
  (**poids du corps en livres**), `W($4C02)` = poids total en lb
  (= 165 + ENT((`W($4BFA)` − `W($4BF8)`)/16), calculé par quatre
  décalages en `$50A1`). Formules
  exactes des limites : incertaines.

## Variables de l'écran STATUS

STATUS est une chaîne de trois blocs chargés en `$5800` : overlay 5 (piste 6
secteur `$0A`, 7 secteurs) calcule date, heure, santé, état général, but,
altitude, terrain, eau, nourriture, pente ; il charge par `$03DB` (lire et
exécuter) la piste 7 secteur 1 (5 secteurs : faim, soif, énergie,
températures), qui charge la piste `$14` secteur 8 (8 secteurs : affichage et
libellés, les mots sont en `$5C52-$5F00`).

### Environnement

| Champ | Source | Calcul / mots |
|---|---|---|
| DATE | `F($4C89)` fraction d'année | jour = ⌊F·365 + 1⌋ ; mois `$4AFF` (1-12, JAN…DEC) par seuils 31/59/90/120/151/181/212/243/273/304/334 ; quantième `$4BB9`. Recalculé si `$4B6F` ≠ 0. Début : 0,34442 → 6 mai |
| TIME | `F($4C57)` heures depuis minuit (7,0 au départ) | heure `$19` = ⌊F⌋ en 12 h, minutes `$1A` = (F − ⌊F⌋)·60, A/P `$4B00` (1/2). **Sans montre** (WATCH, B1 ≥ `$80`) : mot `$4B01` = DAWN/AM/PM/DUSK/NIGHT (calculé ailleurs) |
| TEMP | air en °F, `$17` | `$17` = `$4B9B` avec THERMOMETER (B1[69] < `$80`), `$4B9D` sans. Puis (si `$4B70` ≠ 2) : à l'intérieur d'un abri (`$0D5E` ≠ 0) 35, ou `$4B9B` + 15 si B2 de l'igloo (second jeu, index 21, `$45F1`) est nul ; près d'un feu (B2 index 13 ≠ 0) +25, 127 si ≥ 103. Si `$4B70` = 2 : 70 − 0,3·(alt/100), au moins 33, −20 sans thermomètre (immersion, `$4B70` = 2 pendant SWIM). Mot `$4B05` : FREEZE < 32 ≤ COLD < 60 ≤ NICE < 80 ≤ WARM < 95 ≤ HOT ; avec thermomètre on affiche `$17` + « DEG » |
| SKY | `$4B07` | CLEAR, CLOUDY, RAIN, SNOW (calculé ailleurs) |
| WIND | `$4B9F` | mph |
| TREND | `$4B06` | BETTER, NO CHG, WORSE (calculé ailleurs) |
| ALT | niveau `$D4` + base `$60A1` | avec ALTIMETER (B1[55] < `$80`) : (`$D4` + `$60A1`)·100 ft (`$1B/$1C`) ; sinon LOW < 30 ≤ MEDIUM < 101 ≤ HIGH (`$4B02`) |
| GRND | `$4B56` terrain, `$4B6B` rive, `$4B5B` gel | 0 → CLEAR ; 1 (forêt) → SCRUB si alt ≥ `$60A6`, JUNGLE en régions 3-5, sinon WOODS ; 2 → ROCKY ; 3 → RIVER si `$4B6B` = 3, sinon RIVSHOR ; 4 → LAKESHR si `$4B6B` ≠ 0, FRZLAKE si `$4B5B` ≠ 0, sinon LAKE. Mots LIGHT/AVERAGE/HEAVY présents mais non utilisés ici |
| SLOPE | `$DB` / `$DA` | `$DB` = ⌊4·deg(atan(Δ/24)) + 0,5⌋ où Δ = niveau de la case devant (cap `$D2/$D3` en degrés, 8 directions) − `$D4` ; `$DA` calculé ailleurs (incertain) |

Position et vue (rappel) : `$D0` x, `$D1` y (cellules TOPO), `$D2/$D3` cap en
degrés (128 au départ), `$D4` niveau du sol, `$D5` œil.

### Joueur

| Champ | Source | Calcul / mots |
|---|---|---|
| HEALTH= | `F($4C34)` santé, `F($4C2F)` santé maximale | `$18` = ⌊100·F($4C34)/F($4C2F) + 0,5⌋ (7,8666/7,8666 au départ ; 7,7101 après 3 h de repos dans le froid) |
| PLAYER STATUS | `$4B0C` | s = F($4C34)/F($4C2F), puis ×0,85 ou ×0,7 pour : (1) eau disponible (W5[22] + 8·aléa) < 64 / < 16 ; (2) \|F($4C75)\| > 0,3 et `$4B9D` < 40 / < 20 ; (3) difficulté `$603F` ≥ 3 / ≥ 8 ; (4) distance² au but ≥ 1400 / ≥ 15600 ; (5) produit des 5 pourcentages `$48A8[6..10]`/100 ≤ 0,5 / ≤ 0,1. MISERABLE < 0,2 ≤ POOR < 0,4 ≤ OKAY < 0,6 ≤ GOOD < 0,8 ≤ FANTASTIC. Si `$4B59` ≠ 0 : « RESEARCH MODE » à la place |
| Signes | `$4B7B`, `$4B87` | SWEATING si `$4B7B` ≠ 0, SHIVERING si `$4B87` ≠ 0 |
| GOAL= | `$15` | d = √((`$60BB`−`$D1`)² + (`$60BC`−`$D0`)²), D0 = `$60BD` (distance initiale), u = `F($4C61)` − F1[15] ; si u = 0 : G = 1, sinon G = 0,6·(D0−d)/u combiné à e^(−2,5·u/(D0 ou 2·D0)) (×2 si `$605F` ≠ 1) puis ×(1 − W(`$4C16`)/100 − 0,02·W(`$4BDE`)) ; `$15` = ⌊100·G⌋ borné 0..100 (formule exacte à revérifier) |
| ENRG | e = F2[18] heures depuis le repos | e < 1 → e := 0,5 ; e > 16 → BEAT. Sinon q = W(`$4BE2`)/e ; si épuisement actif (`$48A8[2]` < 95) : BEAT si q < 0,25, sinon TIRED ; sinon TIRED si F1[24] > 12, OKAY si F1[24] ≥ 7, sinon OKAY si santé < 2, GREAT sinon (`$4B0A` : BEAT, TIRED, OKAY, GREAT) |
| HNGR | h = F2[17] heures depuis le repas | h < 1 → h := 0,5. Si h < 2 et `W($4BD2)` > 5·`W($4BF6)` : FILLED. h > 12 : VERY. Sinon r = `W($4BDC)`/(heure+1) ; si bilan `W($4BD8)` < −650 : VERY si 0,33·`W($4BF6)` > r, sinon SO-SO ; sinon OKAY si `W($4BF6)` < r, OKAY si h < 6, SO-SO sinon (`$4B08` : VERY, SO-SO, OKAY, FILLED) |
| THRST | t = F2[16] heures depuis la boisson | t < 1 → t := 0,5. Si t < 2 et `W($4BD4)` > 0,15·`W($4BF6)` : FILLED. t·F($4C7A) > 6 : VERY. Sinon besoin B = `W($4BF6)`·`W($4BDA)`·(1 + 5·F($4C7A)²) / (max(2, 60·heure·F($4C25))·360) ; si `W($4BD4)`/t < B : VERY si t ≥ 1, SO-SO sinon ; sinon SO-SO si 0,5·`W($4BD4)`/t ≤ B ou t ≥ 6, OKAY si déshydratation `$48A8[0]` ≥ 91, sinon SO-SO (`$4B09`) |
| TEMP | `F($4C70)` °F corps (98,6) | avec thermomètre : `$1E`.`$1D` F ; sans : mot `$4B0B` : x = 48,3 − 0,5·F($4C70) ; FREEZE si x > F($4C75), sinon min(5, ⌊(F($4C75) − x)·1,5⌋ + 2) (FREEZE…HOT) |
| FOOD | `W($4BE6)` | Σ W5 des aliments 23-37 présents (B1 ≠ `$FF`, sol compris) + Σ W5 des ressources 1-11 du second jeu présentes (440 au départ) |
| WATER | `W($4BEA)` | W5[22] (128) ; si < 32 et (terrain ≥ 3, ou `$4B4C` ≥ 2 pluie ?, ou `$4B57` = 1) : affiche 150 |
| INJ | `$4821[0..7]` | Actif si < 95 (`$5F`) ; 100 = aucun. SEVERE CUTS, BROKEN ARM, BROKEN LEG, SHOCK, SUNBURN, SNOWBLIND, FROSTBITE, POISON BITE |
| ILL | `$4821[8..14]`, `$48A8[0..5]` | INFECTION, SALT DEFICIENCY, FOOD POISONING, GIARDIA, MALARIA (8-12) ; DEHYDRATION, STARVATION, EXHAUSTION, ALTITUDE SICK, HYPOTHERMIA, HYPERTHERMIA (`$48A8[0..5]`). « NONE » si rien d'actif. Après 3 h de repos : déshydratation et inanition passent de 100 à 99 |

### Flottants et compteurs connus

| Adresse | Valeur au départ | Sens |
|---|---|---|
| `F($4C57)` | 7 | Heure du jour (h, 0-24) |
| `F($4C61)` | 0 | Heures écoulées depuis le début (3 après REST 3 ; +0,267 pour manger) |
| `F($4C89)` | 0,34442 | Date (fraction d'année ; +3/(24·365) après 3 h) |
| `F($4C70)` | 98,6 | Température du corps (°F) |
| `F($4C34)` / `F($4C2F)` | 7,8666 / 7,8666 | Santé / santé maximale |
| `F($4C20)`, `F($4C25)` | 1,65 | Taux métabolique ? (`$4C20` monte en mangeant : 1,65 → 2,31 → 3,77 ; incertain) |
| `F($4C75)` | −0,333 | Bilan thermique ? (0 après repos ; incertain) |
| `F($4C7A)` | 0,5833 | Facteur d'effort/transpiration ? (incertain) |
| F2[16], F2[17], F2[18] | 2, 2, 2 | Heures depuis boire, manger, se reposer (REST remet F2[18] à 0,5 ; manger remet F2[17] à 0) |
| F2[22], F2[23], F2[24] | 190,5 ; 480 ; 68 | Inconnus |
| F1[16..19] | −2, −2, −2, −100 | Inconnus (F1[17] → 3,27 après avoir mangé, F1[18] → 3 après repos) |
| `W($4BDC)` | 1000 | kcal absorbées (+880 pour 8 oz de fromage) |
| `W($4BDA)` | 600 | kcal dépensées (+494 pendant 3 h de repos) |
| `W($4BD8)` | 400 | Bilan = `$4BDC` − `$4BDA` |
| `W($4BD2)` | 1000 | Inconnu (−120 en mangeant) |
| `W($4BD4)` | 10 | Eau bue récemment (oz ?) |
| `W($4BE2)` | 7 | Énergie/réserve (3 après repos ; incertain) |
| `W($4BE8)` | 126 | Inconnu (47 après repos) |
| `W($4BF6)` | 165 | Poids du corps (lb) |
| `$4B9B`, `$4B9D` | 42, 31 | Température de l'air °F (affichée), autre température (min ?) ; 51/40 trois heures plus tard |
| `$4B9F` | 7 | Vent (mph) |

## Annexe : inventaire de la première partie

Valeurs du bloc d'état lu sur le disque (piste `$12`), mêmes colonnes que
plus haut (W5 poids/quantité oz, W6 volume, W7 sol, W8 sac/utilisations, W9
kcal/oz ou partie du corps, W10 et W11 voir le tableau des sens).

| id | Nom affiché | B1 lieu | W5 | W6 | W7 | W8 | W9 | W10 | W11 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | SLPNG BAG | — | 64 | 518 | 0 | 9 | 1 | 20 | 60 |
| 2 | DOWN PARKA | PACK | 24 | 180 | 0 | 3 | 2 | 20 | 60 |
| 3 | BALACLAVA | WEAR | 5 | 52 | 0 | 1 | 3 | 60 | 80 |
| 4 | WOOL PANTS | WEAR | 32 | 173 | 0 | 3 | 4 | 120 | 160 |
| 5 | BOOTS | WEAR | 80 | 104 | 0 | 3 | 5 | 100 | 150 |
| 6 | WOOL SOCKS | WEAR | 8 | 86 | 0 | 1 | 5 | 120 | 160 |
| 7 | MITTENS | WEAR | 10 | 35 | 0 | 1 | 6 | 60 | 80 |
| 8 | SWEATER | WEAR | 16 | 121 | 0 | 3 | 2 | 60 | 80 |
| 9 | TENT | PACK | 64 | 518 | 30 | 18 | 1 | 250 | 400 |
| 10 | ENSOL PAD | GND | 24 | 432 | 0 | 3 | 2 | 20 | 30 |
| 11 | GND COVER | GND | 45 | 200 | 0 | 15 | 2 | 300 | 400 |
| 12 | RAINCOAT | PACK | 16 | 60 | 0 | 6 | 2 | 500 | 600 |
| 13 | GAITERS | — | 5 | 52 | 0 | 2 | 5 | 250 | 500 |
| 14 | JERSEY | WEAR | 5 | 52 | 0 | 3 | 2 | 200 | 2000 |
| 15 | JEANS | GND | 24 | 121 | 0 | 3 | 4 | 150 | 1500 |
| 16 | SHORTS | GND | 4 | 40 | 0 | 2 | 4 | 200 | 2000 |
| 17 | SHOES | — | 26 | 40 | 0 | 2 | 5 | 350 | 600 |
| 18 | COTTN SOCKS | GND | 5 | 52 | 0 | 1 | 5 | 200 | 2000 |
| 19 | HAT | GND | 2 | 35 | 0 | 1 | 3 | 200 | 2000 |
| 20 | GLOVES | GND | 10 | 40 | 0 | 1 | 6 | 150 | 200 |
| 21 | BACKPACK | CARRY | 64 | 60 | 0 | 3 | 2 | 250 | 400 |
| 52 | TOPO MAP | CARRY | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 53 | COMPASS | PACK | 1 | 1 | 0 | 0 | 4 | 0 | 0 |
| 54 | WATCH | WEAR | 2 | 1 | 0 | 0 | 6 | 0 | 12 |
| 55 | ALTIMETER | PACK | 2 | 7 | 0 | 0 | 0 | 400 | 0 |
| 56 | STAR CHART | — | 0 | 0 | 0 | 0 | 6 | 0 | 0 |
| 60 | ROPE | PACK | 32 | 340 | 30 | 0 | 10 | 8 | 0 |
| 61 | PITONS/CARB | GND | 48 | 103 | 30 | 0 | 7 | 6 | 0 |
| 62 | CRAMPONS | — | 21 | 52 | 0 | 0 | 2 | 4 | 0 |
| 63 | SNOWSHOES | GND | 64 | 600 | 0 | 0 | 0 | 0 | 0 |
| 64 | 2QT CANTEEN | CARRY | 80 | 144 | 0 | 0 | 0 | 0 | 0 |
| 65 | SEWING KIT | — | 2 | 5 | 0 | 0 | 0 | 0 | 0 |
| 67 | FISHNG GEAR | PACK | 55 | 110 | 0 | 0 | 0 | 0 | 0 |
| 68 | BINOCULARS | — | 20 | 70 | 0 | 0 | 0 | 0 | 0 |
| 69 | THERMOMETER | PACK | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| 70 | RAFT | GND | 96 | 400 | 30 | 0 | 0 | 0 | 100 |
| 71 | STOVE | — | 32 | 120 | 30 | 0 | 0 | 0 | 0 |
| 72 | TRAP | GND | 48 | 100 | 0 | 0 | 0 | 0 | 0 |
| 73 | UTENSILS | PACK | 16 | 120 | 15 | 0 | 0 | 0 | 0 |
| 23 | NUTS | — | 48 | 1 | 48 | 0 | 160 | 5 | 2426 |
| 24 | EGGS | PACK | 16 | 1 | 0 | 16 | 168 | 0 | 2426 |
| 25 | CANDYBARS | GND | 16 | 1 | 16 | 0 | 141 | 25 | 808 |
| 26 | BACON | GND | 16 | 1 | 16 | 0 | 125 | 0 | 2426 |
| 27 | RICE | — | 48 | 2 | 48 | 0 | 110 | 0 | 2426 |
| 28 | CHEESE | GND+PACK | 48 | 2 | 16 | 32 | 110 | 20 | 116 |
| 29 | CARROTS | GND | 16 | 1 | 16 | 0 | 100 | 0 | 2426 |
| 30 | POTATOES | GND+PACK | 80 | 2 | 48 | 32 | 100 | 60 | 388 |
| 31 | PEAS | — | 32 | 1 | 32 | 0 | 93 | 0 | 2426 |
| 32 | RAISINS | GND+PACK | 24 | 1 | 8 | 16 | 81 | 20 | 1213 |
| 33 | BOLOGNA | GND+PACK | 48 | 1 | 32 | 16 | 80 | 50 | 38 |
| 34 | BREAD | — | 32 | 3 | 32 | 0 | 70 | 20 | 116 |
| 35 | TUNA | PACK | 16 | 2 | 0 | 16 | 47 | 80 | 2426 |
| 36 | BEANS | GND+PACK | 80 | 2 | 48 | 32 | 35 | 60 | 58 |
| 37 | APPLES | GND+PACK | 80 | 2 | 48 | 32 | 13 | 90 | 274 |
| 22 | WATER | GND+PACK | 128 | 2 | 64 | 64 | 0 | 0 | 0 |
| 38 | MATCHES | PACK | 1 | 2 | 0 | 24 | 0 | 0 | 0 |
| 39 | MAGNF GLASS | GND | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| 40 | FUEL | PACK | 8 | 69 | 0 | 8 | 0 | 0 | 1 |
| 41 | FRSTAID KIT | — | 4 | 35 | 30 | 0 | 1 | 9 | 116 |
| 42 | SNAKEBT KIT | PACK | 1 | 5 | 30 | 0 | 8 | -1 | 2426 |
| 43 | SUNGLASSES | PACK | 2 | 3 | 0 | 0 | 6 | -1 | 388 |
| 44 | SUNSCREEN | GND | 4 | 12 | 0 | 7 | 5 | -1 | 2426 |
| 45 | REPELLENT | PACK | 3 | 7 | 0 | 10 | -1 | 13 | 1213 |
| 46 | IODIN TAB | — | 1 | 2 | 30 | 12 | -1 | 12 | 38 |
| 47 | FLAGYL | PACK | 1 | 2 | 0 | 12 | -1 | 12 | 116 |
| 48 | SALT TAB | GND | 1 | 2 | 0 | 12 | -1 | 10 | 2426 |
| 49 | OXYGEN | GND | 320 | 900 | 15 | 17 | -1 | 4 | 58 |
| 50 | QUININE | GND | 2 | 3 | 0 | 14 | -1 | 13 | 274 |
| 51 | SOAP | — | 4 | 8 | 0 | 31 | 1 | 9 | 0 |
| 57 | GUN | — | 50 | 100 | 0 | 18 | 10 | 0 | 1 |
| 58 | AXE | PACK | 32 | 52 | 0 | 0 | 5 | 0 | 0 |
| 59 | KNIFE | PACK | 8 | 10 | 0 | 0 | 3 | 0 | 0 |
| 66 | FLASHLGHT | PACK | 11 | 43 | 0 | 6 | 0 | 0 | 0 |
| 74 | TRINKETS | GND | 12 | 12 | 0 | 6 | 0 | 0 | 0 |
| 75 | GOLD | — | 370 | 82 | 0 | 0 | 0 | 0 | 0 |

## Réimplémentation : charge

Les quatre capacités **restantes** lues dans `build/game.bin` au départ sont
43 oz en `$4BF8`, 1525 in³ en `$4BEE`, 4134 in³ en `$4BF0` et 2542 in³ en
`$4BF2`. Le maximum original de poids `$4BFA` vaut 815 oz ; la comptabilité
originale du sac et de la gourde est particulière et reste à établir.

Notre modèle (`src/game.s`, `load_totals`) additionne tous les équipements
transportés (WEAR, PACK, CARRY), y compris le sac et la gourde, et seulement
les onces transportées des aliments/eau. Le volume d'un équipement va dans
sa catégorie ; celui des aliments = onces dans le sac × volume par once.
L'eau suit l'emplacement de la gourde (sac ou main) et son volume par once.
Au départ, ces sommes sont 836 oz et 624/1866/332 in³. Les limites de notre
modèle = ces sommes + les capacités restantes mesurées de l'original :
879 oz et 2149/6000/2874 in³. **Cette calibration n'est pas une formule
retrouvée dans l'original.**

Les transferts sont refusés entièrement au-delà d'une limite. Les cinq
champs d'objet modifiés sont restaurés, y compris après un débordement de
quantité/volume sur 16 bits. Dépôt, repas et boisson recalculent les sommes.
Le sac et la gourde doivent être vidés avant dépôt. La dernière page
d'INVENTORY présente les quatre capacités restantes et leurs unités.
