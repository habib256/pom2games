# Feu, lumière et eau (lot 2)

Ce document décrit le lot 2 de la fidélité à l'original
(inventaire `ORIGINAL_GAP.md` § 2.1, fiches F1, F2, F3, et la règle
M5 du § 2.6) : faire, utiliser et éteindre un feu, la lumière qui
conditionne la trousse de secours, et l'eau (sources, collecte,
contamination, ébullition, boisson, giardiase). Chaque règle est portée
depuis le code de la face Journey et vérifiée sur la ROM : module seul en
`$5800` avec les entrées du cœur remplacées par des relais, ou partie
réelle de l'original pilotée commande par commande
([`tools/re_camp_probe.py`](../tools/re_camp_probe.py),
[`tools/re_thermal_probe.py`](../tools/re_thermal_probe.py)). Aucun octet
original n'entre dans le dépôt ; les résultats chiffrés restent dans
`build/re_camp/results.json` et `build/re_thermal/results.json` (locaux).

Les textes affichés sont ceux de l'original (« msg n », table des 256
messages de [parser.md](logic/parser.md)), en majuscules, sans le mot
« discovery ».

## 1. Ce que le joueur peut faire

| Commande | Effet (original) |
|---|---|
| `USE MATCHES` | Une allumette sur 24 dépensée (W8), en main, « en usage » ; lumière ; aucun temps. Stock vide : « THE MATCHES HAS BEEN USED UP. » (msg 88), plus en usage |
| `USE FUEL` | Une once de combustible sur 8, en main, en usage ; aucune vérification |
| `USE GLASS` | Ciel clair, hors abri, soleil à 30° ou plus, sinon « SORRY, THERE IS INSUFFICIENT LIGHT. » (msg 53) ; 15 minutes, en main |
| `MAKE FIRE`, `BUILD FIRE` | Voir § 2.1 : refus 78, 76, 25, 79, 11 ; sinon « IT TOOK A WHILE TO MAKE YOUR FIRE. » (msg 15), 30 minutes d'effort |
| `USE FIRE` | Près du feu : +25 °F dans la thermique, lumière, pas de santé de 15 minutes ; aucun temps |
| `DOUSE FIRE`, `STOP FIRE` | Le feu s'éteint, aucun temps (même sans feu) |
| `MAKE STICKS`, `USE STICKS` | Bâtons sur la case (terrain dégagé ou bois), 30 minutes d'effort ; en main, 30 minutes ; ils n'allument rien |
| `MAKE MATCHES`, `MAKE GLASS`, `MAKE FUEL` | « YOU ALREADY HAVE. » (msg 11) ou « NO DOUBT POSSIBLE, BUT BEYOND THE SCOPE OF THE GAME. » (msg 75) |
| `USE FLASHLIGHT` | Une utilisation des piles sur 6, lumière ; piles vides : « SORRY, THE BATTERIES ARE USED UP. » (msg 83) |
| `USE FIRSTAID KIT` | Refusé sans lumière (msg 53) |
| `USE STOVE` | FUEL en usage et un feu près duquel on se tient ou des allumettes en usage, sinon « YOU NEED BOTH FUEL AND FIRE. » (msg 85) ; posé sur la case, 30 minutes |
| `USE UTENSILS` | Posés sur la case, 15 minutes |
| `USE GND COVER`, `USE RAINCOAT` | Tendus pour la condensation (en usage) |
| `GET RAIN`, `GET SNOW`, `GET ICE` | Pluie, neige qui tombe ou sol enneigé : 160 oz d'eau sûre sur la case, puis la gourde ; sinon msg 1 |
| `GET WATER`, `FILL CANTEEN`, `REFILL CANTEEN` | Réserve au sol de la case, sinon rivière ou lac (160 oz non traitées), sinon cactus, sinon recherche chronométrée ou indice de condensation (§ 2.3) |
| `MAKE WATER` | Condensation sous GND COVER ou RAINCOAT en usage (§ 2.3) |
| `BOIL WATER` | UTENSILS en usage, un STOVE en usage ou un feu ; 15 minutes ; l'eau bouillie de la gourde est posée sur la case ; prévention de la giardiase |
| `DRINK WATER`, `DRINK RAIN`… | Au plus 0,2 × poids du corps par gorgée (« DON'T BE RIDICULOUS! », msg 87) ; pluie, neige, rivière bues à la source |
| `WALK` et ses synonymes, `SWIM` | Refusés tant que le feu brûle : « SMOKEY THE BEAR SAYS TO DOUSE YOUR FIRE FIRST! » (msg 132) |

Grille de commandes ([MENUS.md](MENUS.md) § 4) : `MAKE` (liste `FIRE
STICKS WATER`) et `BOIL` (`BOIL WATER`) après `QUIT` ; `DOUSE` (`DOUSE
FIRE`) seulement quand un feu brûle ; `USE` nomme MATCHES, MAGNF GLASS,
FUEL, les produits médicaux, FLASHLIGHT, STOVE, UTENSILS et, quand un feu
brûle, `FIRE`. `GND COVER`, `RAINCOAT` et `USE STICKS` restent tapés.

## 2. Règles portées et preuves

Notations : B1, B2, W5, W7, W8 = tableaux d'objets de l'original
([state.md](logic/state.md)) ; second jeu : B1/B2 de STICKS `$45CC/$45E8`,
de FIRE `$45CD/$45E9`. `$0D5D` lumière, `$0D5E` abri, `$4B4C` ciel,
`$4B56` classe de terrain, `$4B57` sol enneigé, `$4B9F` vent, `$4BCC`
plafond du pas de santé, `$4C20` effort, `$4C43` fréquence des
précipitations du mois, `$4C7A` facteur de la boisson.

### 2.1 Feu (T11/S00 `$5964-$5B7D`, cœur `$51D3`, T08/S00 `$58B5`)

- **MAKE FIRE**, dans l'ordre : feu déjà présent → msg 11 ; dans l'eau
  (`$4B56` ≥ 3 hors rive) → msg 78 ; sol rocheux enneigé → msg 76 ;
  ni MATCHES ni GLASS en usage → « USE THE APPROPRIATE ITEM FIRST. »
  (msg 25) ; pluie (`$4B4C` = 2) ou vent ≥ 41 mph sans FUEL en usage ni
  abri → « SORRY, TOO MUCH RAIN OR WIND. » (msg 79). Succès : l'allumette
  en usage est dépensée (B2[38] = 0), le feu est sur la case (B1[FIRE] = 0),
  sélecteur de soins 24 (`$4B41` = 1, `$4B42` = 24), 30 minutes, effort
  `$4C20` = 1,65 + 0,02 × poids total en livres (corps + charge/16,
  `$5E33`) : **5,91** au départ (213 lb), mesuré.
- **USE MATCHES/STICKS/FIRE** : dans un abri « PLEASE BE CAREFUL. »
  (msg 77) puis plus aucune vérification ; dans l'eau msg 78 (les allumettes
  sur un radeau en usage : le radeau n'existe pas encore dans le port) ;
  pluie ou vent ≥ 41 sans FUEL → msg 79. USE FIRE : B2[FIRE] = 1, `$0D5D`
  = 1, `$4BCC` = 15, sélecteur 24, aucun temps. USE FIRE sans feu, USE
  STICKS sans bâtons : msg 1 (contrôle du cœur sur le second jeu).
- **Les drapeaux « en usage » s'effacent avec le temps** : après `WAIT 1`
  avec tous les B2 à 1, l'original a remis à zéro B2 de 38–42, 51, 52,
  54–57, 66, 68, 69, 74 (et du second jeu 87, 89–92), pas ceux de 22,
  71 (STOVE), 73 (UTENSILS), 11, 12 (couvertures) ni du feu. Conséquences
  reproduites : la lumière des allumettes ou de la lampe dure jusqu'au
  prochain passage du temps ; **USE GLASS** (15 minutes) efface son propre
  drapeau, si bien qu'après lui MAKE FIRE répond msg 25 (mesuré sur la ROM
  à 9 h 45 : la loupe n'allume jamais de feu).
- **USE STICKS** ne rend pas les bâtons « en usage » (B2[STICKS] reste 0
  après la transaction, mesuré) : ils n'allument rien. MAKE STICKS exige
  une classe de terrain < 2 (dégagé ou bois), sinon msg 76.
- **DOUSE/STOP FIRE** : B1[FIRE] = `$FF`, B2[FIRE] = 0, « OK, WHAT NEXT? »,
  aucun temps, aussi sans feu.
- **M5** (T08/S00 `$58B5`) : WALK, RUN, MOVE, CRAWL, SWIM sont refusés par
  msg 132 tant que B1[FIRE] = 0, sauf si un animal partage la case
  (`$4B72`). Aucun minuteur d'extinction n'existe : le feu brûle jusqu'à
  DOUSE ; comme on ne peut pas le quitter, il n'a pas besoin de
  coordonnées.
- **Thermique** (T0B/S02 `$5986`) : près du feu, l'octet `$EE` (air
  ressenti, ou abri : air + 15) reçoit +25 et vaut **127 quand le bit 7 de
  la somme est mis** — donc aussi en dessous de −25 °F (−26 + 25 = −1 →
  127 °F) et au-dessus de 102 °F. Sonde `re_thermal_probe.py`, onze airs
  avec `$45E9` = 1, isolement 47, 1,65 kcal/min, 60 minutes depuis
  98,6 °F :

  | Air °F | `$EE` | Taux °F/h | Corps après 60 min |
  |---:|---:|---:|---:|
  | −40, −26 | 127 | +0,4172296 | 99,01723 |
  | −25 | 0 | −0,3322524 | 98,267748 |
  | −20 | 5 | −0,3114867 | 98,288513 |
  | 0, 20 | 25, 45 | 0 | 98,6 |
  | 42 | 67 | +0,1256251 | 98,6 |
  | 60 | 85 | +0,2131064 | 98,6 |
  | 102, 103, 110 | 127 | +0,4172296 | 99,01723 |

  Le port (`thermal_rate`, `thermal_integrate` avec `fire_near` = 1)
  donne les mêmes taux à 2e-7 et les mêmes températures à 3e-7
  (`tests/test_camp.py`).

### 2.2 Lumière (T0D/S07 `$5BB7`)

À chaque pas de santé, `$0D5D` = 1 si `$4B49` = 1 (matin, après-midi), ou
si `$4B49` = 0 (aube, crépuscule) et ciel clair, ou si MATCHES ou
FLASHLIGHT sont en usage ; sinon 0. La fiche F2 de l'inventaire disait
« de nuit par temps clair » : c'est l'aube et le crépuscule ; la nuit
(`$4B49` < 0) n'a de lumière que par les objets. USE MATCHES, USE
FLASHLIGHT et USE FIRE posent `$0D5D` = 1 jusqu'au pas suivant ; le feu ne
compte pas dans le calcul (mesuré : feu fait, USE FIRE, REST 1 → plus de
lumière). Mesures de nuit (REST 13 depuis 7 h, 20 h, ciel nuageux) :
FIRSTAID refusé (msg 53) ; USE FLASHLIGHT (piles 6 → 5) puis FIRSTAID
accepté (30 minutes), après quoi FLASHLIGHT n'est plus en usage et la
lumière retombe à 0. Chaque USE FLASHLIGHT dépense une utilisation
(6 → 5 → 4) ; à zéro, msg 83. FIRSTAID KIT exige la lumière dans le port
(`care.s`) ; SEWING KIT, MAP, WATCH, ALTIMETER et STAR CHART l'exigent
aussi dans l'original mais n'ont pas encore d'action dans le port.

### 2.3 Eau (T0F/S00)

- **Effort** : tout le module ajoute 0,01 × poids total à `$4C20`
  (`$5D49`) : 3,78–3,79 au départ, compté pendant la recherche, la
  condensation et l'ébullition.
- **Sources** (sonde du module seul, `$4D39` et `$4D30` imposés) :

  | Source | Condition | Pile sur la case | Sûre |
  |---|---|---|---|
  | `RAIN` | `$4B4C` = 2 | +160 oz | oui |
  | `SNOW`, `ICE` | `$4B4C` = 3 ou `$4B57` = 1 | +160 oz | oui |
  | rivière, lac | `$4B56` ≥ 3, msg 61 « Y » | +160 oz | non |
  | cactus | B1[CACTI] sur la case, RND < 0,5 | +160 oz, msg 179 | oui |
  | recherche | msg 55 « Y », durée t, RND ≤ t × `$4C43` × k | +160 oz, msg 56 | non |
  | condensation | MAKE WATER, couverture en usage | INT(0,1 × t′ + 0,5) oz, msg 63 | oui |

  La pile ne gagne 160 oz que si elle en tient moins de 321 (`$5ABC`) ;
  mesuré : 224 + 160 = 384, puis 384 inchangé. k = 0,004 en bois des
  régions 3–5, 0,00083 dans les autres bois, 0,00033 ailleurs ; avec
  `$4C43` = 3,554 (mai, Sierra) et 120 minutes : p = 0,1407 à découvert,
  0,3540 en bois, 1,706 en bois tropical ; RND = 0,999 p trouve (msg 56),
  1,001 p échoue (msg 62). Cactus : 0,4999 trouve (msg 179), 0,5001 passe
  à la question de recherche (msg 55). Après un échec ou un refus de
  chercher, l'original donne l'indice de condensation : « WHY DON'T YOU TRY
  TO MAKE WATER BY CONDENSATION ? » (msg 50) si GND COVER ou RAINCOAT est
  présent, de jour (`$4B49` = 1), ciel clair et avant le coucher, sinon
  « IF YOU NEED WATER, EAT FOOD OR PLANTS HIGH IN WATER CONTENT. » (msg 58).
- **Condensation** (`$5A09`) : couverture en usage (msg 25 sinon), durée t,
  t′ = min(t, 60 × (coucher − heure − 0,5)), INT(0,1 × t′ + 0,5) oz posées
  sur la case, t + 30 minutes. Mesuré : 120 min à 9 h → 12 oz ; 600 min à
  14 h → 26 ; 55 min → 6 ; 90 min à 17 h 30 → 5 (coucher 18,88 h).
- **Collecte** : la gourde est requise (« YOU CANNOT CARRY WATER WITHOUT A
  CANTEEN. », msg 57) ; plus de 160 oz demandées : « YOU CANNOT EXCEED THE
  AVAILABLE AMOUNT OF 160 OUNCES. » (msg 64) ; au-delà de 64 oz dans la
  gourde, la quantité est réduite et « YOUR CANTEEN CANNOT HOLD MORE THAN
  TWO QUARTS. » (msg 186) ; aucun temps. La gourde devient contaminée dès
  qu'elle reçoit de l'eau non traitée (B2[22] ← B2[22] ET `$4B48`, mesuré
  0 après une rivière, 1 après la pluie) et **le reste** : rien ne remet
  B2[22] à 1. L'eau au sol est toujours sûre (`$587C`) sauf dans la
  commande qui la tire d'une rivière ou d'une recherche.
- **Ébullition** (`$5BD4`) : la quantité est demandée, puis UTENSILS en
  usage (msg 25), STOVE en usage ou feu sur la case (« YOU NEED A FIRE TO
  BOIL OR COOK THINGS. », msg 65) ; 15 minutes ; sélecteur de soins 22
  (`$4B42` = 22 : la prévention de la giardiase de T06/S00) ; l'eau bouillie
  de la gourde est posée sur la case (`$03` = 8 : mesuré gourde 64 → 54,
  sol 380 → 390).
- **Boisson** (`$5C26`) : plus de 0,2 × poids du corps (`$4BF6`, 165 lb :
  33 oz) refusé par msg 87 ; crédit hydrique oz × (0,73 − 0,6 × `$4C7A`),
  0,38 oz⁻¹ avec la valeur sauvegardée 70/120 (mesuré : 4 oz → −1,52 h,
  33 oz → −12,54 h) ; sélecteur de soins 6 (`$4B42` = 6). Voir § 6 pour
  ces deux derniers points.
- **Giardiase** (`$5CF7`) : eau non sûre bue et RND ≤ 0,2 / ((`$D4` +
  `$60A1`) / 10), soit 2 / l'altitude en centaines de pieds : 0,1 à
  2 000 ft, 0,02 à 10 000 ft (sonde : 0,0999 infecte, 0,1001 non ;
  0,01998 infecte, 0,02002 non ; `$4B41` = 3, `$4B44` = 12, condition 12).
  Le tirage est celui du jeu (`weather_random`, générateur de Lehmer de
  `$0321`) ; la prévention (BOIL : sélecteur 22, IODINE TABLETS : 16) est
  appliquée par `module_injury_begin`.
- **IODINE TABLETS** : USE TABLETS (`$5BBC`) ne fait que poser B2[46] et
  le sélecteur 16 (`$4B42` = noun − 30), une prévention de la giardiase,
  déjà portée par `care.s`. Aucun traitement de l'eau elle-même n'existe
  dans T0F/S00 ni dans le consommateur T06/S00 : la fiche F3 est close.

## 3. Écarts d'interface et restes

- **Questions de l'original** : le port ne pose pas « DO YOU WANT RIVER OR
  LAKE WATER [Y/N]? » (msg 61, réponse « oui » implicite à la berge) ni le
  choix sol/gourde (msg 192 : la gourde d'abord, comme DRINK) ni « YOU HAVE
  SOME. DO YOU WANT MORE [Y/N]? » (msg 54). La question de recherche
  (msg 55) et la durée (« SPECIFY TIME IN HOURS. », msg 27) sont posées.
- **Messages successifs** : l'original attend une touche entre deux
  messages ; le port les enchaîne dans la colonne de droite. « YOU WERE
  SUCCESSFUL! » et « THESE CACTI ARE LOADED WITH WATER! » sont affichés
  comme résultat de la collecte, après la quantité (l'original les donne
  avant).
- **Une pile d'eau par objet** : une source loin d'une pile existante la
  déplace sur la case du joueur (la pile ancienne est perdue) ; les bâtons
  ne sont pas attachés à une case.
- **STOVE et UTENSILS** sont posés sur la case comme dans l'original ;
  GND COVER et RAINCOAT, que l'original pose aussi, restent où ils sont
  (un vêtement porté changerait l'isolement).
- **Terrain** : la classe rocheuse est celle de STATUS (sol nu, niveau ≥ 96)
  et le sol enneigé `$4B57` est approché par la ligne de neige de la carte
  (`M_SNOW`), comme pour l'insolation ; le cactus est la découverte
  « cacti » de la case (`resource_seen`).
- **HELP** : SCREENS est plein (2 047 octets sur 2 048) ; les pages d'aide
  ne mentionnent pas ces commandes.
- **Restent hors du lot** : radeau (USE MATCHES sur l'eau), tente et
  abris (T11/S00 `$58E4`), SEWING KIT, outils de navigation, tir, COOK,
  WET BODY, TASTE WATER, recherche d'eau en buvant.

## 4. Mémoire

Mesures `make inspect` et `build/wild.map`, base `d64afbb` (main) → lot 2 :

| Zone | Avant | Après | Contenu ajouté |
|---|---:|---:|---|
| Module 4 (fenêtre `$5800`) | WATER 495 | **CAMP 1 617** | feu, lumière, eau (code) |
| SIM `$9600-$B4FF` | 7 619 (fin `$B3C2`) | 7 874 (fin `$B4C1`, **62** octets sous `$B500`) | terme +25 °F, piles d'eau et source de boisson, effacement des drapeaux |
| WILDLO `$1000-$1FFF` | 1 718 libres | **70** libres | messages originaux (1 047), table des messages (56), relais et aides partagées (≈ 500), état (`camp_state`, 11 octets) |
| WILDERNESS (`CODE`/`RODATA`) | 318 libres | 212 libres (112 avec le § 6) | `camp_light`, limite de boisson et msg 87 |
| WILDGAME | 18 libres | 57 libres | `do_get` passé en WILDLO, `water_quantity` retiré |
| VOCAB | 2 047 | 2 043 | `@later` → `camp_verb` |
| MVI (`care.s`) | 878 | 890 | lumière de FIRSTAID |
| OUTDOOR | 2 006 | 2 003 (2 008 avec le § 6) | giardiase originale |
| MENUSWAP / MENUCODE | 62 / 182 libres | 17 / 57 libres | MAKE, BOIL, DOUSE, USE |
| Stock, Burma (pire cas) | 2 943 (pièce 2 494) | **1 610** (pièce 1 128) | CAMP + SIM |
| Stock, Sierra | 4 187 (2 494) | 2 854 (1 244) | |

L'état résident à sauvegarder (lot 9) est `camp_state..camp_state_end`
(`camp_use`, `fire_on`, `fire_near`, `sticks_on`, `light`, puis
`s_sweat`, `sweat_day` du § 6) ; l'eau garde `water_untreated` (GDATA).

La simulation doit finir avant `$B500`, où le chargeur relit sa table
d'enregistrements (`boot.s` `TABLE`) : une première version, qui la
dépassait de 35 octets, plantait la fin de partie de `test_thermal.py`.
`camp_light` et la limite de boisson sont pour cela dans `CODE`.

Le stock d'un disque **natif** de la Sierra (atlas de géographie fine) est
la contrainte la plus serrée : le test de charge de
`tests/test_geo_resident.py` (atlas bruité) passe de six à cinq tuiles de
bruit (atlas ≈ 7,8 Ko au lieu de 8,1 Ko) ; CAMP ne peut plus guère
grandir (quelques dizaines d'octets de marge pour ce test, ≈ 190 avec
quatre tuiles).
L'atlas réel de la Sierra (6 379 octets) laisse plus de 1 Ko. C'est
pourquoi les textes et les aides partagées sont résidents et les piles
d'eau dans SIM : déplacer 1 Ko de textes dans le stock, ou les compresser
(≈ 25 % au plus), sont les deux pistes si WILDLO doit être rendu.

## 5. Sondes

- `python3 tools/re_camp_probe.py` (≈ 20 s) : 19 cas du module T0F/S00
  seul (giardiase à 2 000 et 10 000 ft, recherche sur trois terrains,
  cactus, quatre condensations, pluie, neige, rivière), puis trois parties
  réelles : feu et eau (44 commandes), nuit (lumière, lampe, allumettes),
  et les drapeaux effacés par `WAIT 1`. Résultats dans
  `build/re_camp/results.json`.
- `python3 tools/re_thermal_probe.py` : onze cas « près du feu » ajoutés
  aux 30 cas existants de `m0B2`.
- Les deux sondes sont dans `make test-original`.

## 6. Correction de fidélité isolée (dernier commit du lot)

Deux règles de DRINK changent le chemin de référence (`DRINK WATER 4 OZ`
du script) ; elles sont dans le dernier commit du lot, derrière
l'interrupteur `DRINK_FIDELITY = 1` de `src/game.s` (0 rend le
comportement figé, octet pour octet) :

- **Crédit hydrique** oz × (0,73 − 0,6 × `$4C7A`) calculé par les mêmes
  opérations ROM et les constantes de T0F/S00 (`$5D95`, `$5D9A`), au lieu
  du littéral 0,38. `$4C7A` (`s_sweat`, résident) garde la valeur
  sauvegardée 70/120 jusqu'au premier minuit, puis vaut chaque jour le
  maximum de la journée / 120 (T0C/S03 `$5C9B` : `$1B` × 1/120 au
  changement de jour ; mesuré : 0,38 oz⁻¹ toute la première journée).
- **Sélecteur de soins 6** après chaque gorgée (`$4B41` = 1, `$4B42` = 6,
  mesuré : la liste des sélecteurs contient 6 après DRINK) ; il entre dans
  le traitement des conditions 4, 5 et 11.

`tests/test_reference_state.py` diffère alors à partir de `DRINK WATER
4 OZ` sur deux variables seulement : `medical_actions` (octet 5 : 0 → 1,
jusqu'à la fin) et `s_defw` (dernier bit de mantisse : référence
`81 B7 65 FD 8B`, port `…8A` après la gorgée ; `00 07 FC B9 20` contre
`…18` après `REST 3 H`, puis identique). La référence HGR n'est pas
rebasée. Coût : `CODE` +100 octets (`drink_credit`, `drink_care`,
`sweat_update`), WILDLO 6 (`s_sweat`, `sweat_day`), OUTDOOR +5, SIM −5.
Le même `$4C7A` sert à l'eau des aliments (EAT, T12/S00) : laissé au
lot 4.

## 7. Tests

`tests/test_camp.py` (≈ 70 s, dans `make test`) : grille (MAKE, BOIL,
DOUSE, USE MATCHES/FIRE, liste de USE) ; feu (msg 25, 79 sous la pluie et
à 41 mph, FUEL, 78 dans l'eau, 76, 11, 1, 30 minutes, effort 5,91, pas de
83 minutes puis 15, sélecteur 24, WALK refusé sans pas ni temps, DOUSE) ;
loupe (msg 53 à 7 h ; à 10 h, 15 minutes puis msg 25) ; thermique près du
feu contre la ROM (onze airs) ; nuit (lumière 0, FIRSTAID refusé puis
accepté avec la lampe, piles et allumettes épuisées) ; eau (pluie 186,
msg 1, 87, crédit 1,52, 64, BOIL 25/65/85 puis 15 minutes, sélecteur 22) ;
berge (pile d'abord, rivière 160 oz non traitées, contamination durable,
refus de charge atomique) ; recherche avec graine imposée (RND 0,61 :
msg 62 ; 0,031 : trouvée, pile 150 oz après 10 oz pris) ; condensation
12 oz en 150 minutes ; giardiase : 100 gorgées à 2 000 ft et à 10 000 ft,
graines imposées, même nombre d'infections que le générateur recalculé
en Python (6 et 1). `tests/test_reference_state.py` reste identique.
