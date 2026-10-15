# Chasse, pêche, cueillette, repas et dépeçage (lot 4)

Ce document spécifie le lot 4 de la fidélité à l'original (inventaire
[`ORIGINAL_GAP.md`](ORIGINAL_GAP.md) § 2.3, fiches C1 à C4, et D3 du § 2.5) :
prendre du gibier et du poisson, tuer un animal et utiliser sa carcasse,
ramasser, goûter, cuire et manger les aliments sauvages, la péremption, les
intoxications, le sel, le dépeçage, l'appât et IGNORE/FLAG FOOD. Il sert de
cahier des charges au module 6502 « FORAGE ».

**État (14 octobre 2026) : lot réalisé, étapes 1 à 5** (§ 17 : découpage
retenu, écarts, tests). Le port joue 130 des 134 cas de la partie 1 (4
écartés, listés avec leur raison ; les cinq des moyens 20, 19 et 17 depuis
le lot 3, le 15 octobre 2026), les commandes de la partie 2 de
`results.json` et l'horloge de la partie 3 (`tests/test_forage.py
--original`).

Chaque règle vient du désassemblage des modules de la face Journey (`da65`
et [`tools/re_surv_fp.py`](../tools/re_surv_fp.py), locaux) et est vérifiée
sur la ROM par [`tools/re_forage_probe.py`](../tools/re_forage_probe.py) :

- **partie 1** : 134 cas, chaque module seul en `$5800` au-dessus d'une copie
  vierge de l'état sauvegardé (`build/game.bin`, remise à neuf avant chaque
  cas), RND (`$0321`) remplacé par une table de tirages imposés **qui compte
  les appels**, entrées de message, de saisie, du moteur du temps et de
  chaînage remplacées par des relais ;
- **partie 2** : 33 commandes de la vraie partie (`build/SIERRA.woz` +
  `build/JOURNEY.dsk`) avec quelques écritures en RAM et, pour trois
  commandes, RND forcé à une constante ;
- **partie 3** : l'horloge de péremption tracée (`watch:` d'a2shot) pendant
  WAIT 1, WAIT 4 et REST 3.

Aucun octet original n'entre dans le dépôt : les chiffres sont dans
`build/re_forage/results.json` (local, ≈ 20 s, `python3
tools/re_forage_probe.py`). Les textes cités sont les messages originaux
(« msg n », numérotation de [parser.md](logic/parser.md)).

Notations (celles de [state.md](logic/state.md)) : premier jeu d'objets
1–75, B1 `$404C` (lieu : `$FF` absent, 0 sol, 2 sac, 4 sol + sac), B2
`$4098` (« en usage »), B3 `$40E4`, B4 `$4130`, W5 `$417C` (total oz), W7
`$42AC` (sol), W8 `$4344` (sac), W9 `$43DC`, W10 `$4474`, W11 `$450C`,
mot i en base + 2i. Second jeu, indice k = nom − 75 (1–4 animaux de la
région, 5 GAME, 6 FISH, 7 INSECTS, 8 FRUIT, 9 CACTI, 10 MUSHROOMS,
11 PLANTS, 12 STICKS, 13 FIRE, 14 BOW, 15 SPEAR, 16 CLUB, 17 ROCK,
19 HIDE) : b1 `$45C0`, b2 `$45DC`, b3 `$45F8`, b4 `$4614`, w5 `$4630`,
w7 `$46A0`, w8 `$46D8`, w9 `$4710`, w10 `$4748`, w11 `$4780`. A1[i] =
`$4950 + 5(i−1)`, A2[i] = `$49CD + 5(i−1)` (compteurs de
[survival.md](logic/survival.md)). « fiche[n] » = octet n de la fiche
animale `$6000 + 32(k−1)` ([animals.md](logic/animals.md)).

## 1. Ce que le joueur peut faire (original)

| Commande | Module | Effet |
|---|---|---|
| `USE BAIT` (ou `GET BAIT`) | T11/S00 `$5DD4` | Appât posé (`$4B50` = 1) si l'on transporte de la nourriture, en bois ou sur une rive ; sinon msg 1 ; aucun temps |
| `USE TRAP`, `USE GEAR` | T11/S00 `$5CEE` | Exigent l'appât (« YOU NEED SOME BAIT. », msg 84) ; B2 = 1 ; durée W7 de l'objet (0) |
| `USE GUN/AXE/KNIFE/BOW/SPEAR/CLUB/ROCK` | T11/S00 `$5C42` | B2 = 1, durée W7 (0), puis transaction CARRY (l'arme passe en main) |
| `CATCH`/`GET`/`FIND GAME`, `… FISH` | T0F/S07 `$5B48` | Piège ou matériel de pêche en usage, durée demandée, prise probable (§ 3.1) |
| `KILL`/`ATTACK GAME`, `… FISH` ; `DOUSE`/`STOP` (→ ATTACK) ; `CUT GAME` | T0F/S07 `$58DE` | Arme en usage choisie, 15 minutes, prise probable (§ 3.2) |
| `KILL`/`ATTACK <animal>` | T0F/S07 → T06/S04 `$593A` | Carcasse : viande 65 × V² oz au sol (§ 3.4) |
| `SCARE GAME/FISH` | T0F/S07 | « THAT'S NOT VERY WISE. » (msg 39) |
| `PACK <aliment>` (`GET`/`CARRY` → « PLEASE USE 'PACK' COMMAND ») | T0D/S0F → T0E/S02 | Du sol au sac, la fiche de qualité du sol est copiée sur celle du sac (§ 9) |
| `DROP <aliment>` | T0D/S0F → T0E/S02 | Du sac au sol, la fiche du sol est gardée |
| `EAT <aliment>` | T12/S00 (familles 3), T11/S07 (gibier) | ≤ 48 oz, 2 min/oz, crédit, péremption, toxicité, sel (§ 5) |
| `COOK`/`FRY` (`BOIL`, `DRY` → « PLEASE USE 'COOK' COMMAND ») | T12/S00, T11/S07 | Feu ou réchaud, durée demandée, cuisson, détoxication (§ 6) |
| `TASTE`/`SAMPLE <aliment>` | T12/S08 `$59D6` | Message de goût ou de pourriture, aucun temps (§ 7) |
| `SKIN <animal>`, `SKIN GAME` | T11/S07 `$5848` | Peau = 12 × V oz, durée 100 × V / ((lumière + 1)(couteau + 1)) (§ 8) |
| `IGNORE FOOD` / `FLAG FOOD` / `GET FOOD` | cœur `$520A`, `$5229` | `$4B75` = 1 / 0 / 0 ; msg 10, 10, 33 (§ 11) |

## 2. Aiguillage du cœur (T05/S00)

Ordre des contrôles avant les modules (cœur `$5000`, adresses à
l'exécution) :

1. Noms régionaux d'animaux ramenés aux emplacements 76–79 (parser.md).
2. **Disponibilité** (`$523F-$5276`) : nom 1–75 (sauf 22 WATER) avec B1 < 0
   → « SORRY, THAT ITEM IS NOT AVAILABLE. » (msg 1) ; nom 76–102 : b1[k] ≥ 0
   passe ; sinon b2[k] < 0 → msg 1 ; sinon nom ≥ 82 → msg 1 (un aliment
   sauvage n'existe que par son lieu b1) ; 76–81 passent (animal ou gibier
   présent : b2 = 0).
3. **Redirections** (`$5408-$5478` → `$5711`, texte « PLEASE USE '…'
   COMMAND », retour à la boucle sans temps) : CARRY + nourriture (famille 3),
   gibier (famille 11) ou HIDE (94) → PACK ; GET/CATCH/FIND + nourriture ou
   HIDE → PACK ; BOIL/DRY + nourriture ou gibier → COOK ; COOK/DRY + eau →
   BOIL ; EAT + eau → DRINK.
4. `$4B73` = 1 (transaction d'inventaire à faire dans `$4D00`), puis
   répartition :

| Verbe | Famille 3 (23–37, 82–86) | Famille 11 (76–81) | Autres |
|---|---|---|---|
| 1 GET/CATCH/FIND | (redirigé PACK) | T0F/S07 | familles < 10 : CARRY ; 12 : msg 21 ; ≥ 13 : T11/S00 `$1E` = 17 (FOOD → `$4B75` = 0, msg 33 ; BAIT → USE BAIT) |
| 4 SKIN | « WHATEVER TURNS YOU ON! » (msg 18) | T11/S07 | msg 2 |
| 9 BOIL, 11 COOK, 12 EAT | T12/S00 | T11/S07 | eau → module de l'eau ; EAT + famille 5 → remèdes ; sinon « YOU CAN'T BE THAT HUNGRY! » (msg 3) |
| 15 CURE | msg 18 | « YOU MUST BE WITH THE SPCA! » (msg 36) | |
| 17 ATTACK/KILL, 18 SCARE | INSECTS : msg 10 ; sinon « PARDON THE OBSERVATION, BUT YOU ARE STRANGE! » (msg 20) | T0F/S07 | msg 20 |
| 26 DOUSE/STOP | | verbe changé en 17, puis comme ATTACK | |
| 31 CUT (et 14 COOL) | | T12/S08 `$1E` = 14 → T0F/S07 (`T12/S8+96`) | soins (lot 13) |
| 35 TASTE/SAMPLE | T12/S08 `$1E` = 35 | T12/S08 `$1E` = 35 | eau → module de l'eau |
| 37 IGNORE, 38 FLAG | FOOD (135) : `$4B75` = 1 / 0, msg 10 | | sinon msg 2 |
| 2 USE | msg 17 | msg 17 | T11/S00 |

PACK ou EAT avec TREE, BAIT, SCRUB : « NO DOUBT POSSIBLE, BUT BEYOND THE
SCOPE OF THE GAME. » (msg 75).

## 3. Chasse et pêche (T0F/S07, 6 secteurs)

Entrée `$5800` pour les noms 76–81. Effort de tout le module (`$5C47`) :
`$4C20` += 0,02 × W(`$4C02`) (poids total en livres : 213 au départ →
5,91) ; `$4B71` = 0 (relais des réactions animales, `$4D72`).

État d'un animal ou du gibier (b2[k], k = 1–6) : `$FF` absent, **0
présent vivant**, 1 tué (carcasse) ; b1[k] lieu de la viande.

Contrôles d'entrée (`$5800-$583C`), mesurés :

| b2[k] | Verbe | Réponse |
|---|---|---|
| ≥ 1 (tué) | GET | « PLEASE USE 'PACK' COMMAND » |
| ≥ 1 | autre | « YOU ALREADY HAVE. » (msg 11) |
| `$FF` | GET, b1 < 0 / b1 = 2 / autre | msg 1 / msg 11 / « PLEASE USE 'PACK' COMMAND » |
| `$FF` | autre | « YOU'RE NOT MAKING MUCH SENSE. » (msg 2) |
| 0, animal (76–79) | GET | « PLEASE USE 'KILL' COMMAND » |
| 0 | SCARE GAME/FISH | msg 39 |

### 3.1 CATCH (`$5B48`)

1. GAME exige TRAP en usage (B2[72] ≠ 0), FISH exige FISHNG GEAR (B2[67]
   ≠ 0) : sinon « USE THE PROPER DEVICE TO CATCH, OR WEAPON TO KILL. »
   (msg 66).
2. « SPECIFY TIME IN HOURS. » (msg 27) ; saisie `$5CCF` : chiffres et un
   point décimal (3 décimales au plus), minutes = INT(60 × h + 0,5) avec
   décimales, 60 × h sinon ; trois chiffres entiers ou plus, ou h ≥ 25 :
   « TOO LONG! » (texte du module, pas un message numéroté) et nouvelle
   saisie ; deux points : bip et nouvelle saisie. `$4BC6` = minutes. La même
   saisie sert à COOK (T12/S00 `$5E62`, T11/S07 `$5EE9`).
3. **Un tirage** : prise si RND ≤ p, p = minutes × 0,0007 (GAME) ou
   × 0,008 (FISH). Prise : « YOU WERE SUCCESSFUL! » (msg 56) puis § 3.3.
   Échec : « SORRY, BETTER LUCK NEXT TIME. » (msg 67), `$4B73` = 0.
4. Dans les deux cas (`$5BBE`) : crédit de repos A1[24] −= 0,025 × minutes,
   A1[18] (dernier repos) = `$4C61` + 0,01 × minutes ; puis `JMP $4D00`.

Mesuré : 120 min → p = 0,084 (RND 0,0839 prise, 0,0841 échec), A1[24] = −3,
A1[18] = 1,2 ; 30 min → 0,021 ; FISH 60 min → 0,48. Le piège et le matériel
restent en usage (aucun effacement par le temps, seulement en quittant la
case, § 10.3).

### 3.2 KILL/ATTACK/CUT sur GAME et FISH (`$58DE`)

1. Effort supplémentaire `$4C20` += 0,03 × W(`$4C02`) (total 0,05 ×
   213 + 1,65 = **12,30** mesuré).
2. **Moyen** (le premier trouvé, son drapeau « en usage » est **effacé** par
   l'attaque) : GUN B2[57] → 21 ; BOW b2[14] → 20 ; SPEAR b2[15] → 19 ;
   AXE ou KNIFE (B2[58] + B2[59] ≠ 0, les deux effacés) → 18 ; CLUB ou ROCK
   (b2[16] + b2[17], les deux effacés) → 17 ; aucun : « USE THE APPROPRIATE
   ITEM FIRST. » (msg 25).
3. CUT (verbe 31) exige le moyen 18 ou 19, sinon msg 25.
4. Animal (76–79) : `$04` = moyen, chaînage T06/S04 (§ 3.4).
5. GAME/FISH : `$4BC6` = 15 ; **un tirage**, prise si RND < p,
   p = 0,1 × (moyen − 18) si lumière (`$0D5D` ≠ 0), sinon 0 : fusil 0,3,
   arc 0,2, lance 0,1, hache/couteau 0, gourdin/pierre −0,1 (jamais).
   Prise : « ONE {NOUN} HAS JUST BITTEN THE DUST! » (msg 70), § 3.3,
   `JMP $4D00`. Échec : msg 67, `JMP $4D03` (temps sans transaction).

Mesuré pour les cinq moyens de part et d'autre du seuil (0,2999/0,3001,
0,1999/0,2001, 0,0999/0,1001, 0 pour 18 et 17, fusil de nuit 0,0001 :
échec).

### 3.3 La prise (`$59AA`)

`$4B73` = 0, `$0D5F` = 1 ; dans l'ordre :

- péremption **au sol** w11[k + 21] = INT(18 × `$4C48`) (GAME, 29 h au
  départ) ou INT(18 × `$4C48` × ⅓) (FISH, 9 h) ;
- `$4AE0`[k − 1] = 1 (dépeçable), b2[k] = 1 ;
- **tirage** de quantité : q = 4 + INT(64 × RND) oz (mesuré 4 et 67),
  w5[k] += q, w7[k] += q ; b1[k] = 4 si w8[k] > 0, sinon 0 ;
- FISH seulement, **tirage** de qualité (`$5A83`), p0 = 0,05 − 0,001 × |lat|
  (`$60A8` ; Sierra 0,012) ; W9[64] = 0 (goût), puis :

| RND r | Message | Code W10[64] | % W11[64] |
|---|---|---:|---:|
| r > 0,95 | « YOUR FISH HAS NO SCALES. » (121) | 3 | 15 |
| r < p0 | « YOUR FISH HAS FLABBY SKIN AND SUNKEN EYES. » (119) | 2 | 30 |
| 0,2 r < p0 | « YOUR FISH IS ODDLY SHAPED. » (120) | 2 | 30 |
| sinon | « YOUR FISH IS CONVENTIONAL IN SHAPE AND HAS SCALES. » (122) | 0 | inchangé |

Mesuré à 0,9501/0,9499, 0,0119/0,0121, 0,0598/0,0602.

**Tirages** : CATCH 1 (+ 1 quantité + 1 qualité pour FISH en cas de prise) ;
KILL échec 1, prise GAME 2, prise FISH 3 ; SCARE 1.

### 3.4 Animal tué (D3 ; T06/S04 `$593A-$5A45`)

Rappel : T06/S04 tire d'abord la blessure, puis la réussite
([animals.md](logic/animals.md)). Les deux seuils dépendent de la lumière :
`$19` = 2 − `$0D5D` (`$580F`), resté « sens non établi » dans animals.md
dont les sondes avaient `$0D5D` = 0 :

- blessure p = 0,01 × fiche[moyen] × `$19` × (0,1 en abri, sinon 1) ;
- réussite p = 0,01 × fiche[moyen + 6] / `$19` : **de jour, double de la
  valeur de nuit** (ours au fusil, fiche[27] = 35 : 0,35 de jour, mesuré
  0,3499/0,3501 ; 0,175 de nuit, 0,1749).

Réussite (aucun tirage de plus) : msg 70 ; b2[k] = 1, `$0D5F` = 1,
`$4AE0`[k − 1] = 1, `$0D80` = 0 (l'animal n'est plus dessiné) ;
w11[k + 21] = INT(18 × `$4C48`) ; viande **65 × V²** oz (V = fiche[30],
multiplications entières `$E2B6`) ajoutée à w7[k] et w5[k] ; b1[k] = 4 si
w8[k] > 0, sinon 0 ; New Guinea, première fiche (cannibale) : fiche[15]
négatif remis à 0 (D5) ; `$4B73` = 0, `JMP $4D00` (15 minutes posées à
l'entrée). Mesuré : ours 2 340 oz, couguar 585, crotale 65 ; partie réelle
(RND = 0,1) : 2 340 oz au sol, 29 h, dépeçable.

| Région | V (fiche[30]) par espèce | Viande 65V² (oz) | Peau 12V (oz) |
|---|---|---|---|
| 1 British Columbia | ours 6, loup 3, élan 6 | 2 340 / 585 / 2 340 | 72 / 36 / 72 |
| 2 Sierra Nevada | ours 6, couguar 3, crotale 1 | 2 340 / 585 / 65 | 72 / 36 / 12 |
| 3 Burma | tigre 4, éléphant 15, cobra 1, python 2 | 1 040 / 14 625 / 65 / 260 | 48 / 180 / 12 / 24 |
| 4 New Guinea | cannibale 3, vipère 1, crocodile 4 | 585 / 65 / 1 040 | 36 / 12 / 48 |
| 5 Bolivia | puma 3, jaguar 3, fer-de-lance 1, anaconda 4 | 585 / 585 / 65 / 1 040 | 36 / 36 / 12 / 48 |
| 6 Chile | puma 3, chat 2 | 585 / 260 | 36 / 24 |

(lus dans `build/re_regions/r1..r6_start.bin` ; l'original laisse manger et
dépecer le cannibale.)

## 4. Découverte des aliments (T0D/S00 `$585F`)

Les découvertes de la marche et des scans immobiles (événements `$0D90` +
x, x = `$0D`…`$14`, message `$87` + x : 148 à 155) sont matérialisées dans
l'ordre de x. Le port tire déjà ces RND (`module_resource_results`,
`src/adventure.s`) mais **ne stocke rien** et diverge sur deux points
(ci-dessous).

| x | Ressource | Tirages | Effet |
|---|---|---:|---|
| `$0D`, `$0E` | GAME, FISH (« THERE ARE SMALL GAME IN THE AREA. », « THERE ARE SIGNS OF FISH IN THE WATER. ») | 0 | b2[5] / b2[6] = 0 (présent) |
| `$0F`–`$13` | INSECTS, FRUIT, CACTI, MUSHROOMS, PLANTS (k = x − 8) | 1 + qualité | q = 4 + INT(32 × RND) : w7[k] = q, w5[k] = q + w8[k] ; péremption sol w10[k + 15] = INT(b2[k] × `$4C48`) (b2 = 6, 72, 96, 48, 120 h de base) ; b1[k] = 4 si b1 valait 2, sinon 0 |
| `$14` | **NUTS** (« AHA! YOU HAVE DISCOVERED SOME WILD NUTS. ») : l'objet 23 | 1 + 1 | W7[23] = q, W5[23] = q + W8[23], **W11[23] = 720** (les noix du sac deviennent périssables), B1[23] = 4 ou 0 |

Fiche de qualité **du sol**, premier jeu, indice i = nom − 17 (GAME 63,
FISH 64, INSECTS 65, FRUIT 66, CACTI 67, MUSHROOMS 68, PLANTS 69, NUTS 70) :
W9[i] = code de goût, W10[i] = code de toxicité, W11[i] = pourcentage.

| Ressource | Second tirage r | Goût W9 | Toxicité W10 | % W11 |
|---|---|---:|---:|---:|
| INSECTS | r < 0,1 / sinon | 1 / 0 | 1 / 0 | 80 / — |
| CACTI | r < 0,1 / sinon | 7 / 0 | 1 / 0 | 35 / — |
| MUSHROOMS | r < 0,3 / sinon | 0 / 0 | (bogue, voir § 12) | 80 / — |
| PLANTS | r < 0,1 / < 0,2 / < 0,3 / < 0,5 / sinon | 8 / 7 / 2 / 1 / 0 | 1 / 1 / 2 / 1 / 0 | 60 / 40 / 80 / 80 / — |
| NUTS | r < 0,1 / sinon | 1 / 0 | 1 / 0 | 80 / — |
| FRUIT | r < 0,2 | 1 | 1 | 80 |
| FRUIT | r ≥ 0,5 | 0 | 0 | — |
| FRUIT | 0,2 ≤ r < 0,5 : **troisième tirage** r2 ; m = 1 si mûr | 3 + m (r2 < 0,35) ou 5 + m | 2 (blanc) ou 3 (rouge) | 30 (vert) ou 10 (mûr) |

Mûr (`$5BEB`) : avec P = centre de saison de la fiche de ressource 8
(`$48B4 + 84`, 60 en Sierra) et S = indice de saison courant `$4ADA` :
latitude > 0 : mûr si P < S ; latitude ≤ 0 : mûr si S < P. Mesuré : saison
34 % (mai) → vert, goût 3/5, 30 % ; saison 70 → mûr, goût 4, 10 %.

**Écarts du port** (ordre des tirages, donc toute la météo qui suit) :
le port tire le troisième RND du fruit quand r ≥ 0,5 (`@other`,
`src/adventure.s`), l'original quand 0,2 ≤ r < 0,5 (mesuré : 3 appels pour
0,2001 et 0,4999, 2 pour 0,1999 et 0,5001) ; le port nomme STICKS la
huitième ressource et ne tire pas sa qualité, l'original tire 1 RND pour
les noix (2 appels mesurés). Ces deux corrections changent la référence dès
qu'un fruit ou des noix sont trouvés : à faire au début du lot, avec rebasage
si le chemin de référence en rencontre.

**Corrigé le 14 octobre 2026 (étape 1 du lot)** : `module_resource_results`
tire la qualité des noix et le troisième RND du fruit pour 0,2 ≤ r < 0,5 ;
`tests/test_forage.py` impose la valeur du tirage de qualité (graine résolue)
et compte les tirages : 2/3/3/2 pour le fruit à 0,1999/0,2001/0,4999/0,5001,
2 pour les noix et les quatre autres aliments, comme la ROM. Le chemin de
référence n'en rencontre pas : `test_reference_state`, `test_adventure`,
`test_play` inchangés.

**Étape 2 (même jour)** : les découvertes sont stockées (`forage_found`,
§ 17) : piles du sol, fiches de qualité, compteurs `INT(b2[k] × $4C48)`,
noix sur la case ; `module_resource_results` a quitté ADVENTURE pour ITEMS.

Le tableau « méthode » et « kcal » du port (`adv_leaf_method` 8, 7, 2, 1,
0 ; `adv_leaf_kcal` 60, 40, 80, 80) est en fait le goût et le pourcentage
des plantes.

## 5. Manger (EAT : T12/S00 pour 23–37 et 82–86, T11/S07 pour 76–81)

Les deux modules ont le même calcul (copié) ; T11/S07 n'a pas le msg 31.

Contrôles, dans l'ordre :

1. Quantité totale w5 (ou W5) ≤ 0 : msg 1 (T12/S00) ; « YOU MUST KILL THE
   {NOUN} FIRST. » (msg 38, T11/S07).
2. T12/S00 seulement : « NOURISHMENT MAKES A LOT OF SENSE. » (msg 31, puis on
   continue) si l'inanition `$48A9` < 95 % ou A2[17] > 12 h.
3. « PLEASE SPECIFY AMOUNT IN OUNCES. » (msg 32) ; 0 → msg 2 ; plus de
   48 oz → « DON'T BE RIDICULOUS! » (msg 87).
4. Source : b1 = 0 → sol ; 2 → sac ; 4 → « IS THE FOOD FROM YOUR PACK [P]
   OR FROM THE GROUND [G]? » (msg 71). Sol : `$4B82` = 1, disponible
   W5 − W8 ; sac : `$4B54` = 1, `$4B77` = 1, disponible W8.
5. Disponible < demandé : « YOU CANNOT EXCEED THE AVAILABLE AMOUNT OF {N}
   OUNCES. » (msg 64), retour sans temps.

Puis : effort `$4C20` += 0,004 × poids du corps `$4BF6` (2,31) ; `$4BC6` =
2 × oz ; `$4C3E` = 0,017 ; `$4B83` = 3 ; consommation (`$5ADE`) :

- **Péremption** de la pile choisie : sac W11[n] (1er jeu) ou w11[k] ; sol :
  W11[n] (23–27), **W11[n + 13]** (28–37), w11[k + 21] (76–81), w10[k + 15]
  (82–86). Compteur ≤ 0 : **un tirage**, RND ≥ 0,5 → intoxication (rien
  d'autre), sinon repas normal.
- **Toxicité** (compteur > 0, seulement NUTS et 81–86 : poisson et
  aliments sauvages ; jamais la viande ni les provisions 24–37) : code et %
  de la pile, sol W10[i]/W11[i] (i = n − 17, NUTS 70), sac b3[k] et
  w9[k + 15] (NUTS : B3[23] et W11[70]). p = % / 100 ; code 3 : p × (1 −
  |lat| / 64) ; code 0 : aucun tirage ; sinon **un tirage**, RND < p →
  intoxication. Mesuré : champignons code 2, 80 % : 0,7999/0,8001 ; insectes
  code 1 ; fruit code 3 à 38° : p = 0,121875 (0,1218/0,1220) ; à 0° : 0,3 ;
  à −64° : 0 ; poisson code 3, 15 % : 0,0609375.
- **Intoxication** (`$5C90`) : `$4B41` = 2, `$4B44` = 11, prévention de la
  condition 11 effacée (`$47E0` = 0) : la condition 11 démarre (même déjà
  active, T06/S00 `$590C`) ; **aucune calorie**, aucun autre crédit.
- **Repas** (`$5CA6`) : `$4B44` = 17 ; kcal = oz × W9 (entier 16 bits) ;
  `$4BDC` += kcal ; A1[23] −= 0,8 × kcal / `$4BF6` ; `$4BD2` += kcal si
  A2[17] < 2, sinon `$4BD2` = kcal ; A1[22] −= oz × W10 (eau %) × (0,73 −
  0,6 × `$4C7A`) × 0,007 ; A1[17] = `$4C61` + 0,017 × `$4BC6` ; A2[17] =
  0,5 (puis 0 par le consommateur T06/S00 `$5931`).
- **Sel** : NUTS (23), BACON (26), BOLOGNA (33) et viande 76–80 (pas le
  poisson) : `$4B41` = 3, `$4B42` = 25 (sélecteur de soins 25), W(`$4A4A`)
  −= 200 ; sinon `$4B41` = 2.

Fin : `$03` = 8 si la nourriture vient du sac, puis `JMP $4D00` : la
transaction T0E/S02 retire les onces (§ 9), puis le temps passe (`$4BC6`
minutes au métabolisme 2,31).

Mesuré (champignons 4 oz) : +100 kcal, A1[23] −0,4848, A1[22] −0,798,
A1[17] 0,136, 8 minutes ; noix 2 oz : +320, sel −200, sélecteur 25 ;
fromage du sac 8 oz : +880, 16 minutes, aucun tirage ; partie réelle : EAT
GAME 4 du sol : 10 → 6 oz, +300 kcal, sel −200, 8 minutes.

Valeurs par type (second jeu, identiques dans les six régions) :

| k | Nom | W9 kcal/oz | W10 eau % | w11[k] initial | b2[k] (base de péremption) |
|---:|---|---:|---:|---:|---:|
| 1–4 | viande d'animal | 75 | 40 | 24 | — |
| 5 | GAME | 75 | 40 | 18 | — |
| 6 | FISH | 40 | 75 | 6 | — |
| 7 | INSECTS | 40 | 50 | 6 | 6 |
| 8 | FRUIT | 30 | 75 | 72 | 72 |
| 9 | CACTI | 25 | 75 | 96 | 96 |
| 10 | MUSHROOMS | 25 | 75 | 48 | 48 |
| 11 | PLANTS | 10 | 90 | 120 | 120 |

## 6. Cuire (COOK/FRY : T12/S00, T11/S07)

1. Réchaud en usage (B2[71] = 1) ou feu sur la case (b1[13] = 0, `fire_on`
   du port) : sinon « YOU NEED A FIRE TO BOIL OR COOK THINGS » (msg 65),
   avant la quantité.
2. msg 32 ; 0 → msg 2 ; plus de **288 oz** (T12/S00) ou **848 oz**
   (T11/S07) → msg 87 ; source comme EAT (msg 71) ; msg 64.
3. Effort `$4C20` += 0,01 × W(`$4C02`) (3,78) ; `$4B73` = 1 si la nourriture
   vient du sac (la transaction la pose **au sol**), 0 sinon ; « SPECIFY TIME
   IN HOURS. » (msg 27), durée `$4BC6` (0 → msg 2).
4. **Cuit** si minutes > 15 + INT(0,6 × oz) (mesuré 10 oz : 22 min cuit,
   21 non) : `$4B83` = 1 ; le compteur **du sol** de la pile (W11[n] pour
   23–27, W11[n + 13] pour 28–37, w10[k + 15] pour 82–86, w11[k + 21] pour
   76–81) = INT(48 × `$4C48`) (77 h au départ), quelle que soit la quantité
   cuite. Non cuit : rien que le temps, aucun tirage.
5. **Détoxication** (cuit seulement) : T12/S00, code de la pile choisie
   (sac b3[k]/B3[23], sol W10[i]) : code 1 → **un tirage**, RND < 0,75
   (NUTS) ou < 0,85 (82–86) ; code 2 ou 3 (82–86 seulement) → RND < 0,2 ;
   NUTS de code ≠ 1, code 0, provisions : aucun tirage. T11/S07 : FISH
   cuit → **un tirage** toujours, RND < 0,3 ; viande : rien. Détoxiqué :
   W9[i] = W10[i] = 0 (fiche **du sol**), `$4B83` = 2. Mesuré : 0,1999/0,2001,
   0,8499/0,8501, 0,7499/0,7501, 0,2999/0,3001.
6. `$4B77` = 0 ; `JMP $4D00` : temps au métabolisme 3,78.

Partie réelle : COOK GAME 2 oz du sac, 0,5 h → 2 oz passent du sac au sol,
pile du sol 77 h, 30 minutes ; COOK MUSHROOMS 3 oz du sac (RND 0,9) → au sol,
le code 2 du sac est recopié sur la fiche du sol (T0E/S02 `$5E64`, `$4B83` =
1 : B3 → W10[i], B4 → W9[i], w9[k + 15] → W11[i] ; pour NUTS et 81–86) ;
COOK CHEESE 4 oz du sac, 1 h → au sol, pile du sol 72 h. Une pile du sol
déjà périmée (`$4C18` ≤ 0) est jetée quand on y pose la nourriture cuite
(T0E/S02 `$5EC4`).

## 7. Goûter (TASTE/SAMPLE : T12/S08 `$59D6`, aucun temps ni tirage)

- Famille 3 : NUTS et 82–86 → goût ; provisions 24–37 → péremption seule.
  Famille 11 → péremption (b1 < 0 → msg 38). FOOD → msg 17 ; IODINE,
  FLAGYL, QUININE → msg 10 ; autre → msg 2.
- Pile : b1 = 0 sol, 2 sac, 4 → msg 71 (touche 0 = G, 1 = P). Sol : goût
  W9[i], compteur w10[k + 15] (W11[23] pour NUTS) ; sac : goût b4[k]
  (B4[23]), compteur w11[k].
- Compteur ≤ 0 : « IT SMELLS AND TASTES LIKE SPOILED FOOD » (msg 124).
- Sinon, par code de goût : 0 → « ALTHOUGH NOT THE NECTAR OF THE GODS,
  THE TASTE IS OKAY. » (123) ; 1 → « THE TASTE IS VERY BITTER. » (125) ;
  2 → « THERE IS A SHARP STINGING SENSATION ON YOUR TONGUE. » (126) ;
  3 → « IT APPEARS TO BE UNRIPE WHITE FRUIT. » (93) ; 4 → « IT IS SOME FORM
  OF RIPE WHITE FRUIT. » (94) ; 5 → « HMM. UNRIPE RED FRUIT. » (47) ;
  6 → « AHA! NICE RIPE RED FRUIT. » (89) ; 7 → « THESE PLANTS HAVE A MILKY
  COLORED SAP. » (183) ; ≥ 8 → « YOU NOTICE SILKY WINDBORNE SEEDS. » (184).
  Les dix codes sont mesurés.

## 8. Dépecer (SKIN : T11/S07 `$5848`)

V = fiche[30] pour un animal (76–79), 0,5 pour GAME. Contrôles :

1. FISH : « SORRY. GET HIDE FROM WILD ANIMALS OR SMALL GAME. » (msg 198).
2. `$4AE0`[k − 1] = 0 : b2[k] ≤ 0 → msg 38 ; sinon (déjà dépecé) msg 11.
3. w7[k] (viande **au sol**) ≤ 12 × V : « THERE'S TOO LITTLE {NOUN} TO OBTAIN
   ANY HIDE. » (msg 200 ; mesuré 72 oz refusé, 73 accepté pour l'ours).

Puis : effort `$4C20` += 0,02 × W(`$4C02`) ; `$4BC6` = INT(100 × V /
((`$0D5D` + 1)(B2[59] + 1))) : **aucun outil requis**, le couteau en usage
divise par deux, la lumière aussi (ours : 300 min de jour, 150 avec couteau,
600 de nuit, 300 de nuit avec couteau ; couguar 150, crotale 50, GAME 25) ;
`$4B73` = 0 ; peau h = INT(12 × V) : w5[19] += h, w7[19] += h, w5[k] −= h,
w7[k] −= h (la peau est prise sur la viande) ; « YOU NOW HAVE SOME HIDE. SEE
INVENTORY FOR AMOUNT. » (msg 199) ; b1[19] = 4 si w8[19] > 0, sinon 0 ;
`$4AE0`[k − 1] = 0 ; `JMP $4D00`. Aucun tirage. Partie réelle : SKIN BEAR
après la prise : peau 72, viande 2 268, 5 heures.

## 9. Quantités : la transaction T0E/S02 (observée)

Les modules ne touchent pas aux quantités du repas ; la transaction lancée
par `$4D00` (`$4B73` ≠ 0) le fait. Observé dans la partie réelle :

| Commande | Effet |
|---|---|
| EAT n (sol) | w7, w5 −= n |
| EAT n (sac) | w8, w5 −= n |
| COOK n (sac) | n oz du sac au sol (w8 −= n, w7 += n) ; fiche du sac recopiée sur le sol si non détoxiqué (§ 6) |
| COOK n (sol) | rien ne bouge |
| PACK n | sol → sac, **aucun temps** ; fiche du sol copiée sur le sac (b3 ← W10[i], b4 ← W9[i], w9[k + 15] ← W11[i], w11[k] ← compteur du sol ; mesuré 2/80/50 puis 2/80/72) ; plus que le sol : msg 64 (16) |
| DROP n | sac → sol, aucun temps ; **la fiche du sol est gardée** (mesuré : sac 3/5/15 %/5 h, sol resté 2/0/80 %/72 h) |
| GET/CARRY d'un aliment | « PLEASE USE 'PACK' COMMAND » |

## 10. Péremption

### 10.1 Facteur du jour `$4C48` (T0C/S03 `$5AC2-$5B80`, à minuit)

D = ∫ max(0, T(h) − 32) dh sur les trois segments linéaires du cycle de
l'air du jour ([environment.md](logic/environment.md) : pente `$4CC0`,
décalage `$4BB6` de `$4CB1` à `$4CB6` ; `$4CC5`, mot `$4BBC`, jusqu'à
`$4CBB` ; `$4CCA`, `$4BB8`, jusqu'à `$4CB1` + 24), D ≥ 40 ;
**`$4C48` = 792 / D** (`$4C06` = INT(D)). Vérifié : intégrale numérique
489,69 degrés-heures → 1,61734 = la valeur sauvegardée. 792 = 24 × 33 : à
65 °F constants le facteur vaut 1 ; au plus 19,8 par grand froid. Le port a
ces segments (`src/weather.s`, cycle du jour) mais pas l'intégrale.

### 10.2 L'horloge (T09/S05 `$5A1D-$5ADC`)

À chaque **mise à jour de santé** (`$4C08` ≥ `$4BCC`), si l'air `$4B9B` ≥ 33
(comparaison non signée de l'octet), h = INT(`$4C08` / 60 + 0,5) heures sont
retirées de **tous** les compteurs, présents ou non : W11[23..37], W11[41..50]
(sol des provisions 28–37), w11[1..11] (sac), w11[22..27] (sol de la viande
et du poisson), w10[22..26] (sol des aliments sauvages). Tracé : WAIT 1 → une
mise à jour à 15 minutes, h = 0 (rien) ; WAIT 4 → 285 minutes, h = 5 ;
REST 3 → 30 puis 120 minutes, h = 1 + 2. Conséquences : un pas de 15 minutes
ne fait jamais périmer ; la péremption s'arrête de 0 à 32 °F (un octet de
température négatif, ≥ 128, la fait reprendre).

En fin d'action (T0D/S07 `$5E3F`), un aliment **du sac** (B1/b1 = 2 ou 4)
dont W11/w11 ≤ 0 donne « THERE IS A BAD SMELL IN THE AIR. » (msg 209).
INVENTORY affiche « SPOIL » (state.md).

### 10.3 Quitter la case (T0C/S0B `$58A7`, aussi T0A/S05 `$5AA1`)

- Viande, poisson et aliments sauvages **au sol** sont perdus (b1 = 2, w5 =
  w8, w7 = 0 ; b1 = `$FF` si plus rien) ; les provisions et objets restent
  sur la case (B3/B4 = coordonnées, événement « PREVIOUSLY DROPPED ITEM »).
- b2[1..6] non nuls → `$FF` (carcasses, prises) ; `$4AE0`[0..5] = 0 ;
  `$4B50` (appât) = 0.
- « En usage » effacé : B2 de 9, 46, 49, 53, 58, 59, 64, 65, 67, 71, 72, 73
  et b2 de 13, 19 (piège, matériel de pêche, hache, couteau, réchaud…). Le
  temps efface en plus GUN (57) et BOW, SPEAR, CLUB, ROCK ([CAMP.md](CAMP.md)
  § 2.1) : il faut tirer sans laisser passer le temps après USE GUN.

## 11. Appât, IGNORE FOOD, FLAG FOOD

- USE BAIT (T11/S00 `$5DD4`) : W(`$4BE6`) (FOOD transportée) ≠ 0, ou bois
  (`$4B56` = 1), ou terrain ≥ 3 avec rive `$4B6B` = 1 ou 2 → `$4B50` = 1,
  `$4B73` = 0, `$4D00` sans minutes : « OK, WHAT NEXT? » ; sinon msg 1.
  L'appât n'est jamais consommé (seulement effacé en quittant la case).
- IGNORE FOOD : `$4B75` = 1 ; FLAG FOOD : 0 ; tous deux msg 10 ; GET FOOD :
  0 et « I'LL INTERRUPT YOUR TRAVEL IF YOU COME ACROSS FOOD SOURCES. »
  (msg 33). Mesurés.
- Effet (T0A/S00 `$5A43`, T0A/S05 `$5D2F`) : avec `$4B75` ≠ 0, les types de
  ressource 5 à 12 (GAME … NUTS) **ne sont pas examinés du tout** : ni
  filtre, ni tirage, ni découverte ; animaux (1–4) et abri (13) le restent.
  Dans le port : `resource_scan` doit sauter les espèces 4 à 11 sans RND.

## 12. Bogues et bizarreries de l'original

- **Champignons** (T0D/S00 `$5A45-$5A5D`) : le code de toxicité est écrit
  avec l'Y laissé par FCOMP (`$EBB2` : 1 à 4 selon l'octet où RND diffère de
  0,3), pas à W10[68]. En pratique (Y = 1) : `$4475` = code, `$4476` = 0,
  donc **W10[1], la perte thermique sèche du sac de couchage, passe de 20 à
  0** (ou 2 si RND est très proche de 0,3) ; W11[68] = 80 quand r < 0,3 ;
  W10[68] n'est jamais écrit : les champignons trouvés ne sont **jamais
  toxiques** (sauf code laissé par un poisson ou une autre partie). Mesuré
  (W10[1] = 2 avec r = 0,2999, 0 avec 0,3001). Proposition : reproduire le
  tirage, ne pas reproduire l'écrasement (sauf décision contraire) et le
  dire dans IMPLEMENTATION.md.
- NUTS découvertes : W11[23] = 720 remplace 2 426 (« non périssable »).
- Cuire une partie d'une pile du sol remet à neuf toute la pile (§ 6).
- DROP mélange les onces du sac dans la fiche du sol ; PACK écrase la fiche
  du sac (§ 9).
- La viande d'un cannibale se mange et se dépèce.

## 13. Objets testés et état du port

| Original | Rôle ici | Lot de l'épave (Sierra) | Port |
|---|---|---|---|
| 57 GUN | moyen 21 | absent | objet existant, absent au départ (comme l'original) |
| 89 BOW, 90 SPEAR, 91 CLUB, 92 ROCK (b2[14..17]) | moyens 20, 19, 17 | fabriqués ; la pierre sur toute case de terre | faits (lot 3, CRAFT.md § 8.5) |
| 58 AXE, 59 KNIFE | moyen 18 ; couteau : SKIN ÷ 2 | sac | présents ; USE ne les met pas encore « en usage » |
| 72 TRAP | CATCH GAME | sol | présent |
| 67 FISHNG GEAR | CATCH FISH | sac | présent |
| 175 BAIT (nom) | appât | — | mot connu, sans action |
| 71 STOVE, 88 FIRE | COOK | réchaud absent ; feu (lot 2) | feu : `fire_on` ; réchaud : `U_STOVE` |
| 94 HIDE (b·[19]) | produit de SKIN | — | absent |

**Jouable avec le jeu d'objets actuel du port** : USE BAIT puis USE TRAP /
CATCH GAME, USE GEAR / CATCH FISH (seuls moyens d'avoir gibier et poisson :
hache et couteau donnent p = 0 sur GAME/FISH) ; tuer un animal de la région
à la hache ou au couteau (p = 0,01 × fiche[24] / (2 − lumière), ours 3 % de
jour), puis carcasse, SKIN, EAT, COOK ; ramasser (PACK), goûter, manger et
cuire au feu les aliments sauvages déjà découverts et les noix ;
IGNORE/FLAG/GET FOOD. Le fusil n'est jouable que si un lot d'épave le
fournit (lot 1, P2) ; arc, lance, gourdin, pierre attendent le lot 3.

## 14. Correspondance avec le port

| Original | Port |
|---|---|
| `$0D5D` lumière | `light` (`src/camp.s`) |
| b1[13] = 0 feu sur la case ; B2[71] réchaud | `fire_on` ; `camp_use` & `U_STOVE` |
| `$4C20` effort ; 1,65 + k × W(`$4C02`) | `s_metabolic` ; `camp_effort` (poids total, `camp_act`) |
| `$4BF6` poids du corps | `body_weight` |
| `$4C61`, `$4C57` | `s_elap`, `s_hour` |
| `$4BDC`, `$4BDA` | `s_eaten`, `s_spent` (flottants) |
| A1[16..18], A2[16..18] | `s_last` (+0, +5, +10), `s_drink`, `s_eat`, `s_rest` |
| A1[22..24] | `s_defw`, `s_deff`, `s_defr` |
| `$4C7A` | `s_sweat` |
| sélecteur `$4B42` (25 : sel) | `medical_actions` (indice 24) |
| `$4B44` = 11 | `module_injury_begin`, X = 10 |
| W(`$4A4A`) | `exposure_counter` (mot 0, « salt loss », `src/hazards.s`) |
| `$60A8` | `M_LAT` |
| B1, W5/W7/W8, W9 (provisions) | `it_place`, `it_oz`, `it_gnd`, `it_pack`, `it_kcal` |
| découvertes `$0D90 + x` | `MAP+36` (bits), `resource_seen`, `MAP+26..39` (quantités, tirages) |
| `$4B72`, b2[1..4] = 0 | état de la faune (`src/outdoor.s`, `src/fauna.s`) |
| `$4B75`, `$4B50`, `$4C48`, fiches de qualité, compteurs de péremption, `$4AE0` | absents (à créer) |

## 15. Plan d'implémentation

Le plan ci-dessous date d'avant la récupération de mémoire du 14 octobre
(MEMORY.md §§ 13-15) ; le découpage réalisé est au § 17.

### 15.1 Découpage

1. **NEOWILD.FRG**, module disque assemblé en `$9600`, chargé dans la
   fenêtre SIM (`$9600-$AAFF`, 5 376 octets), à la commande. Contenu :
   - `frg_catch` : T0F/S07 (contrôles, CATCH, KILL/ATTACK/CUT/DOUSE et
     SCARE sur GAME/FISH, prise, qualité du poisson) ≈ 700 octets ;
   - `frg_meal` : EAT et COOK des familles 3 et 11 (un seul code pour T12/S00
     et T11/S07 : contrôles, source P/G, péremption, toxicité, détox,
     nutrition, sel), et la transaction des onces (§ 9) ≈ 1 300 octets ;
   - `frg_skin` ≈ 200 ; `frg_taste` ≈ 200 ; `frg_pack` (PACK/DROP des
     aliments du second jeu et de HIDE, copie des fiches) ≈ 300 ;
     `frg_use` (BAIT, TRAP, GEAR, armes en usage) ≈ 150 ;
   - les 45 textes originaux du lot (≈ 1 600 octets), imprimés par `message`
     avec un pointeur (X ≠ 0), sans passer par la banque de textes (le
     stock de Bolivia n'a plus que 947 octets).
   Total ≈ 4,5 Ko. Protocole : le module décide, écrit l'état et une
   **demande de temps** (minutes, coefficient d'effort et base de poids,
   transaction faite ou non) puis rend la main ; la porte résidente recharge
   SIM (`overlay_load`, comme après STATUS) et fait passer le temps avec
   `spend` (`act` = 4, `s_metabolic` préparé), comme `do_eat`, puis `report`.
   Lecture disque : ≈ 0,4 s par commande ; le disque de 140 Ko n'a que
   3 blocs libres (MEMORY.md § 13.7) : le module (≈ 10 blocs) prend la place
   de la partie sauvegardée, ou ne figure que sur l'image de 800 Ko.
2. **Hors du module** (chaque passage du temps ou de la marche) :
   - SIM (177 octets libres sous `$B500`) : l'horloge de péremption (§ 10.2,
     ≈ 70 octets, au point de la mise à jour de santé, après l'air de
     l'heure) ;
   - cycle du jour (`src/weather.s`, à minuit) : `$4C48` = 792 / max(40, D)
     (≈ 150 octets ; intégrale exacte d'un segment linéaire tronqué à 32 °F) ;
   - ADVENTURE `module_resource_results` : quantités et fiches de qualité
     stockées, NUTS, corrections des tirages (§ 4) ≈ 150 octets ;
   - TRAVEL `resource_scan` : IGNORE FOOD (≈ 15 octets) ; départ de case
     (§ 10.3, ≈ 60 octets) ;
   - OUTDOOR : réussite d'ATTACK → carcasse (§ 3.4, ≈ 80 octets) et seuils
     dépendant de la lumière (`fauna_reactions` : deux jeux, jour et nuit,
     ou un décalage d'un bit) ;
   - INVENTORY et STATUS (FOOD) : piles du second jeu, HIDE, « SPOIL ».
3. **Paquets de région** : V = fiche[30] des quatre espèces (4 octets,
   `build_disk.fauna_patches`) ; le centre de saison du fruit (fiche de
   ressource 8, octet 0) s'il n'est pas déjà dans `fauna_travel`.

### 15.2 État résident (GDATA/WILDLO, sauvé par SAVE)

| Donnée | Octets |
|---|---:|
| Piles k = 1–11 et HIDE : lieu, sol, sac (12 × 5) | 60 |
| Compteurs de péremption k = 1–11 : sac, sol (11 × 4) | 44 |
| Fiches de qualité sol et sac : FISH, INSECTS, FRUIT, CACTI, MUSHROOMS, PLANTS, NUTS (7 × 6, un octet par champ) | 42 |
| Compteurs des provisions : sac 23–37, sol 28–37 (25 mots) — correction de fidélité | 50 |
| b2[1..6], dépeçable (bits), appât, IGNORE FOOD, « en usage » TRAP/GEAR/GUN/AXE/KNIFE (bits) | 10 |
| `$4C48` (flottant) | 5 |
| Total | **≈ 211** |

WILDLO a 274 octets libres, WILDGAME 128 : le lot tient à condition que la
porte résidente reste courte (≈ 50 octets) ; SAVE grandit d'autant (1 487 →
≈ 1 700 octets, toujours 4 blocs).

### 15.3 Aiguillage (une seule entrée résidente, `forage_gate`)

Le tableau des verbes coûte 3 octets par verbe : tout passe par
`verb_more`/`camp_verb` (verbes sans entrée) et par trois crochets dans les
gestionnaires existants.

| Verbe(s) | Noms | Point d'entrée du port |
|---|---|---|
| 4 SKIN | 76–81 ; famille 3 → msg 18 ; autres → msg 2 | `verb_more` → `forage_gate` |
| 11 COOK/FRY ; 9 BOIL, 13 DRY + aliment → « PLEASE USE 'COOK' » | 23–37, 76–86 | `verb_more` (BOIL : avant `camp_verb`) |
| 35 TASTE/SAMPLE | 23–37, 76–86, FOOD, remèdes | `verb_more` |
| 38 FLAG ; 37 IGNORE + FOOD | 135 | `verb_more` ; `do_outdoor` (IGNORE avec FOOD) |
| 1 GET/CATCH/FIND | 76–81 ; aliments → « PLEASE USE 'PACK' » ; FOOD ; BAIT | `do_get` (`item_noun` refuse aujourd'hui ≥ 76) |
| 6 PACK, 8 DROP ; 7 CARRY → « PLEASE USE 'PACK' » | 76–94 (second jeu), NUTS | `do_get`/`do_drop` |
| 12 EAT | 76–86 ; 23–37 si la fidélité des provisions est retenue | `do_eat` (`module_eat` refuse ≥ 38) |
| 17 KILL/ATTACK, 18 SCARE, 26 DOUSE/STOP | 80, 81 ; carcasse d'animal (b2 = 1) | `do_outdoor` |
| 31 CUT | 80, 81 (T12/S08 → T0F/S07) | `do_medical` (care.s) avant les soins |
| 2 USE | BAIT, TRAP, GEAR, GUN, AXE, KNIFE (BOW… au lot 3) | `camp_command`/`do_medical` |
| 15 CURE | 76–81 → msg 36 | `do_medical` |

Grille de commandes ([MENUS.md](MENUS.md) § 4) : **fait** (15 octobre
2026). CATCH, KILL, SKIN et COOK n'apparaissent que si l'objet visé existe
(gibier ou poisson présent, carcasse, pile, et un feu ou le réchaud pour
COOK) et ouvrent la liste de leurs cibles nommées ; la file de la grille
tape d'abord les prérequis (CATCH : `USE BAIT` puis `USE TRAP` ou `USE
FISHNG GEAR` ; KILL : la meilleure arme, `USE GUN`, `AXE` ou `KNIFE`).
TASTE a quitté la grille : c'est la première entrée de la liste d'EAT
d'une nourriture, avant les onces. GET d'une pile compose `PACK x` ; EAT
montre les piles avant les provisions. Reste (TODO.md) : les onces de COOK
et les heures de CATCH dans la liste, en ligne comme `BOIL WATER n OZ` ;
aujourd'hui l'invite numérique les demande.

### 15.4 Ordre de travail et fidélité

1. Corriger les tirages de `module_resource_results` (fruit, noix) : change
   la référence si le chemin du script trouve fruit ou noix ; sinon pur ajout.
   Vérifier avec `tests/test_reference_state.py`.
2. Stockage des découvertes et péremption (horloge, `$4C48`), INVENTORY.
3. FRG : PACK/DROP, TASTE, EAT/COOK des aliments sauvages.
4. Chasse, pêche, appât, carcasse, SKIN.
5. Provisions : péremption, P/G, sel (BACON, BOLOGNA, NUTS) : **Fidélité**,
   derrière un interrupteur comme `DRINK_FIDELITY` (CAMP.md § 6) : le script
   mange du fromage (non salé) depuis le sac ; il ne change que si le fromage
   est périmé (116 h à 33 °F et plus) au moment du repas.

### 15.5 Tests à écrire (`tests/test_forage.py`, émulateur, port contre ROM)

Les valeurs attendues sont celles de `build/re_forage/results.json` (ou
recalculées en Python avec les mêmes flottants) :

- **Tirages et seuils** (graine imposée dans `weather_random`, comme
  `test_camp.py`) : KILL GAME aux cinq moyens et de nuit ; CATCH GAME 2 h
  (0,084) et FISH 1 h (0,48) ; quantité 4 + INT(64 RND) ; qualité du poisson
  aux six bornes ; nombre de tirages consommés par commande (compteur du
  générateur avant/après).
- **Découverte** : un fruit avec r = 0,3 consomme 3 tirages, 0,6 en
  consomme 2 ; les noix 2 ; fiches de qualité et péremption (116, 155, 77,
  194, 720 au départ Sierra) ; IGNORE FOOD : aucune découverte ni tirage de
  type 5–12 pendant WALK 1 H sur une case riche.
- **EAT** : champignons code 2 à 80 % (deux graines encadrant 0,8) ; fruit
  rouge à 38° (0,121875) ; pile périmée (0,5) ; crédits (+100 kcal,
  −0,4848, −0,798, 8 minutes) ; sel (−200, sélecteur 25) ; msg 31, 87, 2, 64.
- **COOK** : msg 65 ; 21 et 22 minutes pour 10 oz ; 77 h ; détox 0,2 / 0,85 /
  0,75 / poisson 0,3 ; COOK du sac pose la nourriture au sol avec la fiche du
  sac ; 288/848 oz.
- **SKIN** : ours 300/150/600 minutes, peau 72, viande 2 268 ; msg 198, 38,
  11, 200 ; GAME 6 oz et 25 minutes.
- **TASTE** : les dix codes de goût et la pourriture.
- **Carcasse** : KILL BEAR au fusil de jour (0,35) et de nuit (0,175) :
  2 340 oz, 29 h ; KILL BEAR à la hache de jour : 3 %.
- **Péremption** : WAIT 4 retire 5 h, WAIT 1 rien, REST 3 retire 3 h ; rien à
  32 °F ; `$4C48` du départ = 1,61734 (et une valeur après minuit contre
  T0C/S03 exécuté seul) ; msg 209 ; perte des piles du sol en quittant la
  case.
- **Sonde ROM** : `tools/re_forage_probe.py` dans `make test-original`.

## 16. Incertitudes

- La transaction T0E/S02 n'est décrite que par ses effets observés (§ 9) ;
  ses autres chemins (eau, abris, HIDE) ne sont pas lus. DROP d'une pile du
  sac périmée et CARRY de HIDE n'ont pas été joués.
- Le consommateur T06/S00 avec `$4B44` = 17 date le repas (A1[17], A2[17] =
  0) ; son effet sur les autres compteurs n'est pas sondé.
- L'octet `$4B9B` est comparé sans signe : la reprise de la péremption sous
  0 °F est déduite du code, non mesurée.
- La table de vol de nourriture par un animal (T06/S04 `$5A94`, msg 73) n'est
  pas couverte ; avec RND = 0,5 la sonde a vu toutes les provisions volées,
  à revoir avec le lot 11 (faune complète).
- Le lot d'épave des régions autres que la Sierra n'a pas été relu pour
  GUN (animals.md : le Chili a un autre lot).

## 17. Réalisation (14 octobre 2026)

### 17.1 Découpage retenu

Les fenêtres de modules étant pleines et le stock de l'édition de 140 Ko
presque vide, les commandes du lot sont **un module disque** sur les deux
éditions, et le reste va dans les modules déjà chargés au moment où il sert
(mesures : [MEMORY.md](MEMORY.md) § 16) :

| Partie | Où | Rôle |
|---|---|---|
| `src/frg.s`, module FORAGE (entrée 31, 5 822 octets) | NEOWILD.BLK, lu à chaque commande dans la fenêtre SIM (`$9600`, 12 blocs) | toutes les commandes : CATCH, KILL/ATTACK/DOUSE/CUT et SCARE sur GAME/FISH, prise, qualité du poisson, EAT, COOK, TASTE, SKIN, PACK/DROP du second jeu, USE BAIT/TRAP/GEAR/GUN, IGNORE/FLAG/GET FOOD, CURE, redirections de T05/S00 ; 45 textes originaux ; sa propre copie du générateur de `weather_random` (même graine) |
| `forage_gate` (TEXT) | résident, appelé par `resolve_menu` en tête de `dispatch` | filtre `forage_wants` (masques de verbes par famille de noms), libère les pages `$90-$AF` du bitmap de ProDOS autour du READ_BLOCK (comme `module_save`), lance le module, puis son temps par `camp_done` avec l'effort demandé (`fg_eff` : 0,01, 0,02, 0,05 × le poids total, ou `s_metabolic` posé par le module) |
| `forage_state` (WILDLO, 221 octets) | sauvé par SAVE (`sv_ranges`) | piles k = 1-11 et HIDE (b1, sol, sac), b2[1..6], 47 compteurs (sac et sol du second jeu, provisions 23-37 et sol de 28-37), fiches de qualité sol et sac, dépeçables, appât, IGNORE FOOD, TRAP/GEAR en usage, `$4C48`, case des piles, V et nom des animaux tués |
| `forage_here` (WILDLO) | pas de marche, découverte, carcasse, porte, INVENTORY, grille | quitter la case (§ 10.3) : piles du sol perdues |
| `module_resource_results` + `forage_found` | ITEMS (déplacé d'ADVENTURE) | stockage des découvertes (§ 4) |
| `forage_kill` | OUTDOOR (`out_value` : V, rempli par les paquets) | carcasse de l'animal tué (§ 3.4) |
| `forage_clock`, `forage_news`, `module_forage_day` | ALERT (après chaque mise à jour de santé ; à minuit par `forage_day`) | horloge (§ 10.2), messages 209, 195, 196, facteur du jour (§ 10.1) |
| `forage_skip` | GCODE, appelé par TRAVEL | REST, CAMP et IGNORE FOOD : aucun tirage des types 5-12 |
| `forage_cond`, `forage_menu` | WILDERNESS (CODE), `verb_extra` | les verbes CATCH, KILL, SKIN, COOK, TASTE de la grille ([MENUS.md](MENUS.md)) |
| INVENTORY | STATUS | piles du second jeu (sac, sol ici), `SPOIL` |

Une commande du lot lit le module sur le disque (12 READ_BLOCK) : 102 826
cycles sur XL (8 568 par bloc, `test_transfers.py`) ; sur le vrai matériel
un lecteur 3,5" arrêté peut ajouter 0,5 à 1 s, un Disk II environ 0,6 à 1 s
pour les 12 blocs (non modélisé par l'émulateur). Les autres pas de marche,
vues et écrans n'y touchent jamais.

Pour faire de la place au stock de 140 Ko, TREE (20) et ORIENT (26) y sont
aussi lus sur NEOWILD.BLK, comme sur XL (USE COMPASS, CLIMB, HANG, LOOK
N/E/S/W/STARS : une lecture de 2 ou 3 blocs).

### 17.2 Fidélité des provisions (étape 5)

`fg_fidelity` (octet résident, valeur initiale `FORAGE_FIDELITY` = 0 dans
`src/forage.s`) fait passer EAT des provisions 23-37 par le module
(péremption, P/G, sel de BACON et BOLOGNA, message 31) et ajoute les
provisions à l'odeur de pourriture. Laissé à 0 dans l'image livrée : le
chemin de référence (`test_reference_state.py`, script HGR) mange du
fromage dont le sac et le sol ont tous deux : la question P/G du module
casserait le script ; les tests le mettent à 1 pour les six cas de la
partie 1. COOK et TASTE des provisions, et EAT des noix (23), passent
toujours par le module.

### 17.3 Écarts à l'original

- **Seuils d'ATTACK selon la lumière** (§ 3.4, D3) : OUTDOOR garde ses
  seuils de nuit (lot 11, faune) ; la carcasse elle-même est faite.
- **Moyens** : BOW, SPEAR, CLUB, ROCK (20, 19, 17) depuis le lot 3
  (15 octobre 2026, [CRAFT.md](CRAFT.md) § 4 et § 8.5 : bits de `fg_use`,
  la pierre partage celui du gourdin) ; ATTACK (OUTDOOR) prend aussi le
  premier moyen en usage, GUN compris, avec les seuils de la fiche par
  moyen ; sans moyen en usage, la hache ou le couteau accessibles (règle
  du port).
- **Champignons** : l'écrasement de W10[1] (§ 12) n'est pas reproduit.
- **Quitter la case** efface aussi le gibier et le poisson présents (b2 0 →
  `$FF`, l'original seulement les non nuls) et la peau au sol (le second jeu
  n'a pas de coordonnées).
- **Fuite du gibier** : le tirage `dt / 128` est celui que le port avait
  déjà (`resource_retention`, premier pas d'un repas, d'un repos et des
  actions du lot) ; les messages 195 et 196 viennent en fin de commande.
- **Message 209** en fin de commande, après une mise à jour de santé qui a
  trouvé de la nourriture gâtée dans le sac.
- **Horloge** : la règle de T09/S05 à chaque mise à jour de santé du port ;
  les totaux sont ceux de la ROM (8 h sur WAIT 1, WAIT 4, REST 3), la
  répartition suit la cadence du port (1, 1, 6 au lieu de 0, 5, 3).
- **Facteur du jour** : 792 / D sur le cycle de l'air du port. Le calcul
  rend exactement le 1,61734 de la partie sauvée de l'original à partir de
  ses coefficients ; le cycle du premier jour du port n'est pas celui de
  l'original (maximum 72 °F au lieu de 70, minimum 44 au lieu de 38 : D =
  590 au lieu de 489,69), écart du modèle de l'air antérieur au lot. Le
  1,61734 sauvé vaut jusqu'au premier minuit.
- **Poids** : les piles du second jeu ne pèsent pas dans la charge du port
  (ni dans l'effort `$4C02`).
- **NOIX** : PACK/DROP NUTS restent le transfert d'objets du port ; la
  fiche du sac des noix est celle du sol.
- **Provision cuite depuis le sac** : refusée (`m_pile`) si sa pile du sol
  est sur une autre case (une pile au sol par objet dans le port) ; une pile
  du sol périmée n'est jetée qu'après une cuisson réussie.
- **A2[17] après un repas** : 0 (convention du port,
  `module_meal_prepare`) au lieu de 0,5 ; `$4BD2` n'est pas tenu.
- **Saisie des heures** : chiffres et un point, TOO LONG comme l'original ;
  le bip d'un second point n'est pas reproduit (nouvelle saisie).
- **Grille** : un verbe choisi sans nom prend le premier objet possible
  (commodité du port).
- **Synonymes d'animaux** : SKIN, EAT, COOK d'une carcasse reconnaissent le
  nom de l'espèce de la région ou le mot qui l'a tuée (`fg_n`), pas les
  autres synonymes (PUMA pour COUGAR).
- **KILL d'un animal déjà tué** : OUTDOOR répond « aucun animal » au lieu
  du msg 11.

### 17.4 Tests

`tests/test_forage.py` : étape 1 (tirages des découvertes), puis les règles
autour du module (case quittée, facteur à minuit contre le même calcul en
Python sur le cycle du port, intégrale sur les coefficients sauvés de
l'original, odeur, IGNORE FOOD, grille), puis les cas de `results.json`
traduits dans l'état du port (`--original` : ceux-là seuls). L'aléa est
imposé par un relais posé sur `fr_rnd` (ou `weather_random` pour les
découvertes) qui compte aussi les tirages ; OUTDOOR tire ses propres jets
(générateur de faune). `tests/test_editions.py` joue appât, piège, prise,
feu, cuisson et repas de gibier sur les deux éditions et chronomètre la
lecture du module ; `tests/test_save.py` sauve et restaure une carcasse et
une pile du sac avec leurs compteurs.
