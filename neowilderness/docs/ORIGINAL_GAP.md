# Neowilderness : ce qui manque par rapport à l'original

Inventaire au 13 octobre 2026 (branche `main`, après `b941346`), tableau du
§ 1.2 mis à jour le 14 octobre après les lots 1, 2, 7, 9, 13 et LOOK
UP/DOWN, de ce que
Wilderness (Electric Transit, 1985) fait et que Neowilderness ne fait pas,
ou fait seulement de façon provisoire. Il sert de base aux lots de
réalisation (§ 3). Les preuves sur l'original renvoient aux modules de la
face Journey (« T$xx/S$yy n » : piste et secteur SMALLDOS, n secteurs,
chargé en `$5800`), aux binaires de la face programme (`build/files/`) et
aux documents de [logic/](logic/ENGINE.md). Les adresses non vérifiées par
une sonde ROM sont marquées « (?) » ou « à confirmer ».

Ce document ne modifie aucune règle : il décrit ce qu'il faudrait porter,
où le code devrait vivre et ce que chaque ajout coûte.

## 1. Méthode et sources

### 1.1 Comparaison

- **État du port.** [README](../README.md), [TODO](../TODO.md) (direction 1),
  [TODO_HGR](../TODO_HGR.md) (cases non cochées), [IMPLEMENTATION.md](IMPLEMENTATION.md)
  (« Règles provisoires et écarts », « Conditions médicales », « Arbres »),
  [SCENARIOS.md](SCENARIOS.md), [REGIONS.md](REGIONS.md) § 7,
  [STARS.md](STARS.md) § 11, [HOF.md](HOF.md), [MENUS.md](MENUS.md),
  [MEMORY.md](MEMORY.md) § 9–11 ; table des verbes du port
  (`src/game.s`, `verbs`/`verb_lo`/`verb_hi`, `dispatch`), refus
  `m_notyet` (« NOT IN THIS VERSION YET. », `src/messages.inc`).
- **Original, déjà documenté.** [ANALYSE.md](ANALYSE.md),
  [logic/parser.md](logic/parser.md) (aiguillage `$5000`, 44 verbes,
  modules), [logic/environment.md](logic/environment.md),
  [logic/survival.md](logic/survival.md), [logic/animals.md](logic/animals.md),
  [logic/sites.md](logic/sites.md), [logic/trees.md](logic/trees.md),
  [logic/state.md](logic/state.md).
- **Original, relu pour ce document** (désassemblages `da65` locaux, hors
  dépôt ; aucun octet original n'entre dans Git) :
  - fabrication T$10/S$00 5 et T$10/S$05 7, dépeçage et gibier T$11/S$07 8 ;
  - eau T$0F/S$00 7, chasse et pêche T$0F/S$07 6, repas T$12/S$00 8,
    divers T$12/S$08 6 ;
  - USE T$11/S$00 7, verbes divers T$15/S$0A 1, déplacement T$08/S$00 1,
    T$08/S$01 6, T$08/S$07 8 ;
  - LOOK T$0F/S$0F 1 et T$10/S$0C 4 ;
  - SAVE T$13/S$0C 7, RESTORE T$14/S$03 5, HELP T$13/S$00 8,
    CLUE T$15/S$00 5 → T$15/S$05 5, événements T$06/S$02 2, statue
    T$07/S$07, score final T$0F/S$0D ;
  - préparation du voyage `GO1.B` (`$5800`), `GO2.B` (`$2000`), `GO3.B`
    (`$3000`), `MENU.A`, `TSAVE.A`, `TMAKE0.A` ;
  - balayage des lectures de `$603F` (niveau) sur les pistes `$00-$17`.
- **Version MS-DOS 1986** (`../wilderness/original/extras/`, extraite hors
  dépôt) : `WILD/MESSAGES.TXT` reprend les 256 messages Apple et ajoute
  en clair les questions de préparation, les textes CLUE et quelques
  messages propres au DOS ; `DISPCRSH.TXT`, `DISPCITY.TXT` (deux
  introductions) et `DISPHELP.TXT` (conseils d'équipement) confirment les
  deux scénarios. Aucun manuel n'est présent dans `original/` ni `build/`.

Les textes des 256 messages originaux sont dans
`../wilderness/build/re_parser/messages.txt` (local, `tools/messages.py`) ;
ils sont cités ici par numéro décimal (« msg 76 »).

### 1.2 Vocabulaire : original et port

Le port contient les **280 mots originaux** à l'identique
(`tools/gendata.py`, `VOCAB`, mêmes classes et numéros) plus `FILL` et
`REFILL` (verbe 1). Le module `VOCAB` (`wildvoc.bin`, fenêtre `$5800`)
fait **2 047 octets sur 2 048** : aucun mot ni aucune branche ne peut y
être ajouté sans déplacer du code (le vocabulaire est le seul contenu
indispensable ; `resolve_noun` et `dispatch` en sortiraient). Les mots
manquants ne sont donc pas un problème : ce sont les **branches** derrière
les mots qui manquent.
Depuis le 14 octobre, VOCAB est stocké en LZ dans le stock auxiliaire
(CHANGELOG « descriptions à gauche, grille à droite ») ; la fenêtre reste
pleine.

| N° | Verbe(s) original | Module original | Port |
|---:|---|---|---|
| 1 | CATCH, FIND, GET | eau T$0F/S$00, chasse T$0F/S$07, objets | objets 1–75 ; eau : GET RAIN, SNOW, ICE, rivière ou lac, cactus (lot 2) ; gibier, poisson (CATCH : piège, attirail), aliments sauvages, peau (PACK), BAIT, FOOD (lot 4, module FORAGE) |
| 2 | USE | T$11/S$00 (abris, feu, outils, lampe, crampons, appât, radeau, pacotilles…) | produits médicaux 41–51 ; MATCHES, FUEL, GLASS, FIRE, FLASHLIGHT (lot 2) ; MAP, COMPASS, WATCH, ALTIMETER, CHART, SHADOW (lot 7) ; SPLINT, PRESSURE, AXE, KNIFE (lot 13) ; abris, outils, appât, radeau, pacotilles : `m_notyet` |
| 3 | BUILD, MAKE | T$10/S$00, T$10/S$05, feu par T$11/S$00 | MAKE FIRE, MAKE WATER, MAKE STICKS (lot 2) ; abris, armes, outils, objets : `m_notyet` (lots 3 et 5) |
| 4 | SKIN | T$11/S$07 | carcasses d'animaux et de gibier (lot 4, FORAGE) |
| 5 | WEAR | T$0D/S$0F | porté |
| 6 | PACK, STORE | T$0D/S$0F | porté |
| 7 | CARRY, TAKE | temps / transaction | porté |
| 8 | DROP, REMOVE | T$0D/S$0F | porté |
| 9 | BOIL | eau, repas, dépeçage | BOIL WATER (ustensiles, réchaud ou feu, lot 2) ; repas : « PLEASE USE 'COOK' COMMAND » (lot 4) |
| 10 | DRINK | eau, remèdes T$12/S$08 | gourde, remèdes, eau de rivière ou de lac, pluie, neige, glace, cactus (lot 2), au plus 0,2 × poids ; giardiase de l'original |
| 11 | COOK, FRY | T$12/S$00 | feu ou réchaud, cuisson, détoxication (lot 4, FORAGE) |
| 12 | EAT | T$12/S$00, remèdes | provisions 23–37 et remèdes ; aliments sauvages, noix, viande, gibier et poisson (lot 4, FORAGE ; provisions selon l'original derrière `FORAGE_FIDELITY`) |
| 13 | DRY, WARM | T$15/S$0A → T$12/S$08 | messages 117/118 de l'original (lot 13) |
| 14 | COOL | T$12/S$08 | COOL BODY (lot 13) |
| 15 | CURE, HEAL, TREAT | messages seuls (17, 18, 36) | messages 18 et 36 pour la nourriture et les animaux (lot 4) ; ailleurs message générique |
| 16 | LOOK | T$0F/S$0F → T$10/S$0C | L/R/B/F, N/E/S/W, AZ, U/D (LOOK UP/DOWN) ; SUN, STARS, COMPASS, WATCH, ALTIMETER, méthodes montre et ombre (lot 7) |
| 17, 18, 37 | ATTACK/KILL, SCARE, IGNORE/SKIP | T$0F/S$07, T$06/S$04 | animaux de la région, hache/couteau seulement (carcasse : lot 4) ; GAME/FISH au fusil, à la hache, au couteau ; IGNORE/FLAG/GET FOOD (lot 4) |
| 19–21, 44 | WAIT/PAUSE, REST/SLEEP, CAMP, EXERCISE | T$15/S$0B | portés |
| 22–24, 27, 43 | GO/WALK, RUN, SWIM, MOVE, CRAWL | T$08/S$00 → S$01 → S$07 | marche et nage portées ; RUN et CRAWL = marche ; CLIMB de pente, rivière suivie, risques : absents |
| 25 | CLIMB | arbre, pente | arbre seulement |
| 26 | DOUSE, STOP | BLEEDING, FIRE, animaux | STOP BLEEDING, DOUSE FIRE (lot 2) ; animaux : absent |
| 28 | PADDLE, ROW | radeau T$08/S$07 | absent |
| 29, 30, 32 | LOWER, SHIELD, SUCK | T$15/S$0A, T$12/S$08 | LOWER HEAD, SHIELD EYES, SUCK VENOM portés ; LOWER FOOD/BACKPACK (alias du port) |
| 31 | CUT | T$12/S$08 → T$0F/S$07 | CUT BODY (lot 13) ; CUT GAME/FISH à la lame (lot 4) |
| 33 | WET | T$15/S$0A → T$0F/S$00 | WET BODY (lot 13) |
| 34 | HANG | T$15/S$0A → T$12/S$08 | HANG FOOD ; vêtements à sécher (lot 13) |
| 35 | SAMPLE, TASTE | T$12/S$08 | absent |
| 36 | PAN, SCAN | vue | porté (synonyme de LOOK) |
| 38 | FLAG | FOOD → interruption | absent |
| 39, 40 | EXIT/LEAVE, ENTER | T$12/S$08 | SHELTER (cabane du port) seulement |
| 41, 42 | SAVE, RESTORE | T$13/S$0C, T$14/S$03 | cinq parties, `NEOWILD.SAV` (lot 9) |
| — | noms d'écran T, V, STAT, INV, HELP, CLUE, NATURE | modules d'écran | HELP réécrit (3 pages fixes), CLUE : `m_notyet`, NATURE : animaux seulement |

Les noms de familles 10 (blessures), 13 (thèmes) et 15 (corps) n'ont
d'effet que par CURE/HELP dans l'original (msg 17/18) ; le port y répond
par un refus générique, ce qui est presque équivalent.

### 1.3 Contraintes de place (rappel)

Chiffres de [MEMORY.md](MEMORY.md) § 9.10 et § 11 :

- RAM principale résidente : **361 octets libres** au total, dont 19 dans
  WILDGAME (`$576D-$577F`), 135 dans WILDLO, 159 dans RESIDENT.
- Stock auxiliaire (modules de la fenêtre `$5800`, sprites, catalogue
  d'étoiles) : **266 à 278 octets libres en Burma**, 1 510 en Sierra.
- Fenêtre `$5800` : 2 048 octets par module ; VOCAB plein, STA plein,
  TRV 2 045, MED 2 045, SCR 2 040.
- Fenêtre SIM (`$9600-$B5FF`, 8 Ko) : simulation, plus le module des
  étoiles (ID 25) et TOPOGEN quand la vue est cachée.
- Carte langage auxiliaire `$D000-$FFF9` : instantané de vue sous TOPO
  (12,8 Ko) sur carte héritée, ou cache + code + atlas de géographie fine
  (≈ 7 Ko utiles) sur carte native.
- Ajouter un verbe au port coûte 3 octets résidents (`verbs`,
  `verb_lo`, `verb_hi` en GDATA) : toutes les nouvelles familles doivent
  partager **une seule entrée** de répartition vers un module.

Depuis la levée de la contrainte de 140 Ko (image ProDOS de 800 Ko
autorisée), **le disque n'est plus un obstacle** : six atlas de
géographie fine, sauvegardes, données et sprites par région tiennent. La
RAM reste la contrainte : 128 Ko, tout résident, **aucune lecture disque
pendant le jeu ordinaire**. Chaque élément du § 2 indique donc la RAM
nécessaire et la zone visée ; le § 3 distingue ce que le 800 Ko suffit à
débloquer de ce qui exige une récupération de RAM.

### 1.4 Activité disque de l'original pendant une partie

Pour peser une politique « lecture disque seulement à la sauvegarde, à la
reprise et au changement de région » :

| Famille de commandes | Lectures de l'original (secteurs) |
|---|---|
| chaque message | 1 (le secteur du message est relu à chaque affichage, `$4EA2`) |
| événement en attente (`$0D90` ≠ 0) | T$06/S$02 2 |
| TOPO | T$05/S$08 4 + T$01/S$0B 5 |
| STATUS | T$06/S$0A 7 → T$07/S$01 5 → T$14/S$08 8 |
| INVENTORY | T$07/S$08 8 |
| HELP | T$13/S$00 8 + jusqu'à 10 messages |
| CLUE | T$15/S$00 5 → T$15/S$05 5 |
| WEAR, PACK, DROP | T$0D/S$0F 3 → T$11/S$00 7 → T$0E/S$02 8 ou T$0E/S$0A 6 |
| EAT, COOK | T$12/S$00 8 |
| eau | T$0F/S$00 7 |
| chasse, pêche | T$0F/S$07 6 → T$06/S$04 6 |
| fabrication | T$10/S$00 5 ou T$10/S$05 7 |
| LOOK | T$0F/S$0F 1 → T$10/S$0C 4 |
| VIEW | aucune |
| pas de WALK/REST | T$09/S$05 3 → T$09/S$08 8 → (WALK : T$0A/S$00 5, T$09/S$00 5) → T$0A/S$05 7 ; à chaque intervalle de santé (≤ 240 min) en plus T$0A/S$0C 6 → T$0B/S$02 5 → T$0B/S$07 6 → T$0B/S$0D 6 → T$0D/S$07 8 (+ T$0C/S$03 8, T$0C/S$0B 5) |
| SAVE / RESTORE | 7 / 5 + 96 secteurs par partie, avec échanges de disquettes |

Soit 25 à 55 secteurs par pas de simulation ; un trajet épave → poste
représente des centaines de chargements ([GEOGRAPHY.md](GEOGRAPHY.md) en
cite au moins 177). L'état réel d'une partie originale ne fait que
`$4000-$4CFF`, la carte `$6000-$AFFF`, le bloc `$0D59-$0DBF` et la page
zéro (≈ 24 Ko) : tout le reste est du code ou du texte relu faute de
mémoire. Le changement de région n'existe pas en jeu (autre disquette
programme et retour au menu).

**Conséquence pour le port.** Une politique « disque à la sauvegarde, à la
reprise, à la fin de partie et au choix de région » est fidèle à l'esprit
de l'original et compatible avec le 800 Ko. Un assouplissement
supplémentaire — charger depuis le disque un module **rare** (préparation
du voyage, SAVE/RESTORE, CLUE, écran de fin) au moment de la commande,
comme `NEOWILD.END` le fait déjà — ne coûte aucune RAM résidente et ne
touche pas le jeu ordinaire ; il est proposé pour les seuls éléments
marqués « disque possible » au § 2.

## 2. Inventaire des manques

Chaque fiche donne : **Original** (preuve), **Port** (état), **Taille**
(estimation 6502, code + données, en supposant des entiers là où
l'original appelle la ROM flottante ; la ROM flottante reste disponible
dans le port), **Où** (zone visée), **Dépend de**, **Référence** (risque
pour `tests/test_reference_state.py`, qui compare l'état de simulation
avec la version HGR figée sur `tests/scenario.py` : STATUS, rotations,
WALK 1 H, SWIM 1 H, EAT CHEESE, DRINK WATER, USE SUNSCREEN, USE FIRSTAID
KIT, TOPO, MAP, LOOK R, REST, WALK 30 MIN, SLEEP × 6, faune coupée par
`nature_frequency` = 0 ; seules les variables présentes dans les deux
builds sont comparées) et **Test**.

« Ajout pur » : aucune branche du chemin de référence ne change.
« Correction de fidélité » : la simulation de la référence change ; il
faudra soit rebaser la référence HGR (nouvelle référence figée sur la
version corrigée), soit garder le test vert en limitant la correction
aux chemins non joués par le script.

### 2.1 Feu, lumière et eau

**F1. Faire du feu (MAKE/BUILD FIRE, USE MATCHES/GLASS/FUEL/FIRE).**
- Original : T$11/S$00 `$5964-$5B2E`. Refus dans l'eau (msg 78), sur sol
  rocheux enneigé (`$4B57` = 1, msg 76), sans allumage (MATCHES ou GLASS
  « en usage », msg 25), sous la pluie ou avec un vent ≥ 41 mph sans FUEL
  en usage ni abri (msg 79). Succès : feu présent à la case (`$45CD` = 0),
  allumette consommée (B2[38] effacé), 30 min, effort `$4C20 +=
  0,02 × poids`, msg 15. USE FIRE pose le drapeau « près du feu »
  (`$45E9` = 1 : +25 °F dans la thermique, T$0B/S$03), la lumière
  (`$0D5D` = 1) et le plafond de pas `$4BCC` = 15. GLASS exige ciel clair,
  hors abri et soleil ≥ 30°. Le feu dure jusqu'à DOUSE/STOP FIRE (cœur
  `$51D3`, sans temps) ; aucun minuteur d'extinction trouvé. MAKE STICKS
  (`$5998`, 30 min, terrain < 2) crée des bâtons ; le feu ne les exige ni
  ne les consomme.
- Port : aucun feu ; `MATCHES`, `GLASS`, `FUEL`, `STOVE` sont des objets
  inertes ; la thermique n'a pas le terme +25 °F (`thermal.s`).
- Taille : ≈ 450 octets (commandes) + 40 (thermique, terme feu) + 1 octet
  d'état résident et 2 coordonnées.
- Où : module de la fenêtre `$5800` nouveau « CAMP » (feu, eau, abris,
  § 2.2) ; terme thermique dans SIM (THERMAL).
- Dépend de : aucun. Prérequis de COOK/BOIL (F3, C2) et de la règle
  « éteindre avant de partir » (D5).
- Référence : ajout pur tant qu'aucun feu n'est allumé ; le terme
  thermique doit être une branche sautée quand `fire_in_use` = 0.
- Test : MAKE FIRE sans allumettes (msg 25), sous la pluie sans FUEL,
  dans l'eau ; USE FIRE puis REST au froid : température corporelle
  comparée à une exécution de `m0B2` sur ROM avec `$45E9` = 1 (étendre
  `tools/re_thermal_probe.py`) ; WALK refusée tant que le feu brûle.

**F2. Lumière et lampe.**
- Original : `$0D5D` (T$0D/S$0A `$5AB7`) vaut 1 de jour, de nuit par temps
  clair, ou avec MATCHES/FLASHLIGHT en usage. Elle conditionne FIRSTAID KIT
  (msg 53), SEWING KIT, les outils de navigation et le tir sur gibier.
  USE FLASHLIGHT exige des piles (W8[66] ≠ 0, msg 83) ; décompte des piles
  et allumettes non localisé (à confirmer : décrément générique des objets
  en usage).
- Port : pas de notion de lumière pour les actions ; FIRSTAID utilisable
  la nuit.
- Taille : ≈ 120 octets ; Où : résident (GCODE) ou module MVI (soins).
- Référence : correction de fidélité pour USE FIRSTAID KIT de nuit (le
  script l'utilise de jour : sans effet).
- Test : USE FIRSTAID KIT de nuit sans lampe → refus ; avec USE FLASHLIGHT
  → accepté ; piles à zéro → msg 83. Sonde : relever le décrément des
  piles sur une nuit de REST (`make test-original`).

**F3. Eau : sources, collecte, traitement, contamination.**
- Original : T$0F/S$00. Sources : pluie (`$4B4C` = 2) et neige/glace
  (`$4B4C` = 3 ou `$4B57` = 1) donnent 160 oz **sûres** ; rivière ou lac
  (`$4B56` ≥ 3, msg 61) 160 oz **non traitées** ; ailleurs, recherche en
  heures (msg 55, 27) avec probabilité `minutes × $4C43 × k` (k = 0,004 en
  bois tropical, 0,00083 en bois, 0,00033 ailleurs), cactus (RND < 0,5,
  msg 179), sinon condensation (COVER ou RAINCOAT, jour clair, avant le
  coucher : `INT(0,1 × minutes + 0,5)` oz, msg 63). GET exige la gourde
  (msg 57), capacité 64 oz (msg 186) ; mélanger de l'eau non traitée
  contamine la gourde (B2[22]). BOIL WATER exige UTENSILS en usage et
  STOVE ou feu (msg 25, 65), 15 min. DRINK refuse plus de `0,2 × poids`
  (msg 87) ; crédit hydrique `oz × (0,73 − 0,6 × $4C7A)` ; giardiase si
  l'eau n'est pas sûre et RND < `2 / (niveau + base)` (altitude en
  centaines de pieds / 10). WET BODY passe par ce module.
- Port : FILL/REFILL CANTEEN et GET WATER à la berge, 10 minutes,
  capacité 64 oz, risque de giardiase **1/8** (choix du port,
  [IMPLEMENTATION.md](IMPLEMENTATION.md) « Aventure ») ; pas de pluie,
  neige, condensation, cactus, ni traitement ; boire 4 oz à la gourde
  suit la conversion d'origine figée (« la variation avec la
  transpiration reste à porter »).
- Taille : ≈ 1 100 octets (collecte, condensation, recherche, ébullition)
  ; IODINE TABLETS (traitement) non localisé dans ces modules (à
  confirmer : USE TABLETS dans T$11/S$00 ne fait que poser l'usage ;
  chercher l'écriture de B2[22] dans le consommateur d'événements).
- Où : module « CAMP » (avec F1) ; la conversion hydrique `0,73 − 0,6 ×
  $4C7A` dans ENVIRON (`module_drink`).
- Référence : **correction de fidélité** pour la conversion de DRINK
  (le script boit 4 oz) et pour la giardiase ; la collecte n'est pas jouée.
- Test : sonde ROM du module T$0F/S$00 sur les six sources (RND imposé),
  comme `re_care_*` ; GET WATER sous la pluie → eau sûre ; BOIL sans
  ustensiles → msg 25 ; 100 tirages de giardiase à 2 000 ft et 10 000 ft.

### 2.2 Abris et fabrication

**A1. Abris fabriqués HUT, IGLOO, TRENCH et tente (MAKE, USE, ENTER).**
- Original : T$10/S$00 `$599C-$5A53`. Refus : dans l'eau (msg 92),
  `$D8`/`$D9` = `$7F` (msg 49, sens à confirmer : site déjà occupé ?),
  HUT hors bois (`$4B56` ≠ 1 et pas d'arbre `$D7`, msg 76), IGLOO sans
  neige au sol (`$4B57`, msg 76). Temps `4000 × k / ((d+2)(hache+2) ×
  santé)` avec k = 1 tranchée, 2 hutte, 3 igloo (≈ 127/254/381 min au
  départ), effort 0,023. État : B1' de l'abri, drapeaux `$0D89` hutte,
  `$0D8A` igloo, `$0D8B` tranchée (`$0D88` tente par USE TENT). USE
  HUT/IGLOO/TRENCH (T$11/S$00 `$585D`) : `$0D5E` = 1 (dedans), plafond de
  pas 15, msg 9 ; USE IGLOO pose `$45F1` (35 °F fixes sous igloo, sites.md).
  USE TENT : 20 min, tente posée au sol, `$0D5E` = 1. Le sprite suit le
  code de site `$0D84` (SURV3D `$1C68-$1CBC`, table `$1D0D`) : 1 tente
  `T16/S0`, 2 hutte `T16/S4`, 3 igloo `T16/S9`, 4 tranchée `T16/SD`,
  5 abri naturel (bille `T16/SF`, ou rocher `T17/S4` au-dessus de `$60A3`),
  6 poste `T01/S2`, 7 épave, 8 cité perdue `T00/S8`.
- Port : **fait le 15 octobre 2026** (lot 3, étape 1,
  [CRAFT.md](CRAFT.md) § 3 et § 8) : MAKE, USE, ENTER, EXIT des trois abris
  et USE TENT, temps et messages sondés sur la ROM, l'abri sur sa case
  (`cr_sx`, `cr_sy`), igloo à 35 °F, risque ×0,1 (D4, comme l'original :
  décision du 15 octobre 2026). Sprites (étape 3) faits le même jour sur
  NeoWildernessXL seul (CRAFT.md § 8.4) : l'ordre de T0D/SE `$5F4C` (igloo,
  hutte, tente, abri naturel, tranchée) ; l'édition de 140 Ko n'en a pas.
- Taille : ≈ 400 octets de commandes + 60 octets de thermique (igloo 35 °F)
  + sprites tente 969, igloo 859, tranchée 403 octets.
- Où : commandes dans le module « CAMP » ; un octet d'abri fabriqué par
  case (position + type : 3 octets résidents, ou en-tête de carte
  `MAP+28..63` s'il reste des octets libres — à vérifier, plusieurs sont
  pris) ; sprites dans le tronc commun (stock auxiliaire) ou chargés avec
  le paquet de région s'ils ne servent qu'au froid (igloo).
- Dépend de : sprites et projection d'un site de plus (S1).
- Référence : ajout pur. La protection ×0,1 (au lieu de totale) est une
  correction de fidélité hors script (faune coupée).
- Test : MAKE IGLOO sans neige → msg 76 ; MAKE HUT en forêt → temps
  comparé à la formule exécutée sur ROM (sonde T$10/S$00 avec santé
  imposée) ; ENTER HUT, REST au froid : 35 °F sous igloo, air + 15 sous
  hutte ; sprite visible depuis la case voisine.

**A2. Outils et armes : CLUB, SPEAR, BOW, AXE ; SPLINT ; visière et boue.**
- Original : T$10/S$00 `$5A54-$5C51`. Armes en forêt (msg 76) ; hors
  régions 3–5, corde ou GEAR requis pour AXE/BOW/SPEAR (msg 4) ; CLUB
  `60/√santé` min, AXE/SPEAR `600/(√santé × (3 × couteau + 1))`, BOW
  ×4 ; ROCK/GUN/KNIFE refusés (msg 21). SPLINT : `300/(√santé × (couteau
  + 1))` min, terrain < 2, bois et corde/GEAR (raccourci si SPEAR ou AXE
  présents). SUNGLASSES (visière d'écorce, msg 28) et SUNSCREEN (boue,
  msg 205) : 30 min. On ne fabrique que ce qu'on n'a pas (msg 10/11).
  Les armes fabriquées sont des objets du second jeu (B1' 14 arc, 15
  lance, 16 gourdin, 17 pierre, 18 attelle).
- Port : **fait le 15 octobre 2026** ([CRAFT.md](CRAFT.md) § 4, § 5, § 8) :
  module CRAFT sur NEOWILD.BLK, état de 12 octets en LOWPAGE et 6 en
  WILDERNESS (pas de tables `it_*` du second jeu : `cr_b1`, `splint_place`,
  `cr_cx/cr_cy`, bits de `fg_use`) ; moyens 20, 19, 17 de KILL GAME/FISH ;
  puis le même jour (CRAFT.md § 8.5) ROCK, GET/PACK/CARRY/DROP du second
  jeu, une case par objet laissé au sol, les armes contre les animaux.
- Taille : ≈ 700 octets + tables du second jeu (≈ 25 objets × 6 octets).
- Où : module « CRAFT » (nouveau) ; tables du second jeu en GDATA
  (résident, ≈ 150 octets) : **exige une récupération de RAM principale**.
- Dépend de : second jeu d'objets (aussi nécessaire à F1, C1, A3).
- Référence : ajout pur si les tables ajoutées ne déplacent aucune
  variable comparée (le test compare par nom : sans risque).
- Test : sonde ROM de chaque formule de temps (santé 2,5 / 7,87, couteau
  0/1) ; MAKE SPEAR hors forêt → msg 76 (déjà observé dans parser.md).

**A3. Fabrication 2 : corde, radeau, gourde/poterie, ustensiles, hameçons, raquettes, piège, pacotilles, vêtements de peau.**
- Original : T$10/S$05. ROPE (`$5809-$5A5D`) : matériau artificiel
  (menu msg 107/108 : un objet est détruit) ou naturel (peau ≥ 36, sinon
  fibres végétales en forêt, diamètre demandé msg 45 hors régions 3–5 :
  2d² oz, 48d² min ; corde faible si d < 4). RAFT : bois ou rive et
  matériau, 21 × poids oz, 4 × temps de base `180/((d+1)(couteau + hache
  + 1))`. CANTEEN (`$5C43-$5E4B`) : découpée dans un objet (menu msg
  114/115, 16 oz) ou poterie/peau (24 oz). UTENSILS (msg 206), GEAR
  (hameçons, msg 207), SNOWSHOES, TRAP : bois et matériau ou aiguille.
  TRINKETS : RND < 0,2 en 30 min. Vêtements, tente et sac en peau
  (T$10/S$00 `$584A-$599B`) : 12 × W8 de peau. Une partie du code
  (`$58EB-$58FF`) est **endommagée sur la disquette** livrée (sommes de
  contrôle valides) : la branche « naturel » est reconstituée d'après le
  code voisin.
- Port : rien ; recettes **mesurées** le 15 octobre 2026
  ([CRAFT.md](CRAFT.md) § 6 : temps de base 240 et 180 / ((lumière + 1)
  (outils + 1)), menus, tables, bizarreries du menu de la corde).
- Taille : ≈ 1 600 octets (dont menus de découpe) ; les objets découpés
  exigent la mise à jour des capacités (`load_totals`).
- Où : module « CRAFT2 » (fenêtre `$5800`).
- Dépend de : A2 (second jeu d'objets), C3 (peau).
- Référence : ajout pur.
- Test : MAKE ROPE → A → JEANS : jean détruit, corde créée, charge
  recalculée ; MAKE RAFT sans matériau → msg 76.

### 2.3 Chasse, pêche, cueillette et repas

**C1. Chasse, pêche, insectes (CATCH/GET, KILL/ATTACK, CUT sur GAME/FISH/INSECTS).**
- Original : T$0F/S$07. Arme en usage choisie dans l'ordre fusil (21),
  arc (20), lance (19), hache/couteau (18), gourdin/pierre (17) ; gibier
  tué avec p = 0,1 × (code − 18) (fusil 0,3, arc 0,2, lance 0,1, jamais au
  couteau), 15 min, nul sans lumière. CATCH GAME exige TRAP en usage, FISH
  exige GEAR (msg 66) : p = minutes × 0,0007 (gibier) ou 0,008 (poisson),
  durée en heures (msg 27). Prise : `4 + INT(64 × RND)` oz au sol,
  péremption `INT(18 × $4C48)` h (gibier) ou `6 ×` (poisson) ; qualité du
  poisson (msg 119–122) selon la latitude (p0 = 0,05 − 0,001 × |lat|).
  Effaroucher gibier/poisson : msg 39. Appât : USE BAIT (`$4B50`) en bois
  ou sur une rive.
- Port : la découverte des ressources est portée pour l'ordre des tirages
  (`resource_scan`, `module_resource_results` : quantités et qualités
  tirées en `MAP+26..39`) et nommée (« YOU FIND FISH. ») ; aucun moyen de
  les prendre : GET FISH → `m_notyet`.
- Taille : ≈ 700 octets.
- Où : module « FORAGE » (fenêtre `$5800`) avec C2.
- Dépend de : second jeu d'objets (arc, lance…), F2 (lumière), A3 (piège,
  hameçons) pour l'essentiel ; le fusil existe dans l'épave.
- Référence : ajout pur (les tirages de découverte sont déjà en place).
- Test : sonde ROM des probabilités (RND imposé) ; KILL GAME au fusil :
  quantité au sol, péremption, puis EAT.

**C2. Repas complets : aliments sauvages, gibier, cuisson, péremption, intoxication.**
- Original : T$12/S$00. EAT ≤ 48 oz, COOK ≤ 288 oz (msg 87), 2 min/oz,
  pack ou sol (msg 71). Aliment périmé (W11 ≤ 0) : intoxication si
  RND ≥ 0,5 ; NUTS et aliments sauvages : code de toxicité et pourcentage
  (ajusté par la latitude pour le code 3) ; intoxication = condition 11,
  sans calories. Sel : NUTS, BACON, BOLOGNA, gibier → compteur `$4A4A
  −= 200`. COOK : cuit si minutes > 15 + 0,6 × oz, péremption
  `48 × $4C48` h, détoxication RND < 0,75/0,85/0,2 selon l'aliment.
  EAT signale un besoin (msg 31). TASTE/SAMPLE (T$12/S$08 `$59D6`) :
  messages 123–126, 47, 89, 93, 94, 183, 184 selon le code de goût, sans
  temps. SKIN et repas de gibier : T$11/S$07 `$596F` (cuisson exige feu
  ou réchaud).
- Port : EAT des provisions 23–37 (crédits portés et comparés) ; pas de
  péremption, d'aliments sauvages, de cuisson ni de sel alimentaire.
- Taille : ≈ 1 000 octets (EAT sauvage, COOK, TASTE) + 30 octets de
  péremption par aliment au sol.
- Où : module « FORAGE » ou second module « MEAL » si FORAGE déborde ;
  le crédit commun reste dans ENVIRON.
- Dépend de : C1, F1.
- Référence : la péremption des **provisions de l'épave** au sol et le
  sel des aliments salés sont des corrections de fidélité (le script
  mange du fromage, non salé, depuis le sac : effet nul attendu ; à
  vérifier).
- Test : EAT MUSHROOMS crus → intoxication selon RND imposé ; COOK puis
  EAT → sans intoxication ; TASTE FRUIT → message de maturité.

**C3. SKIN et peau.**
- Original : T$11/S$07 `$5800-$596E`. Peau = 12 × octet 30 de la fiche
  animale (gibier : 6), pas de couteau requis ; temps `100 × V / ((d+1)
  (couteau + 1))` ; messages 35, 38, 198–200. La peau sert aux vêtements,
  à la corde, à la gourde (A3).
- Port : rien ; l'octet 30 des fiches est déjà dans les paquets de région
  mais marqué « inconnu » ([animals.md](logic/animals.md)).
- Taille : ≈ 300 octets. Où : module « FORAGE ».
- Dépend de : C1 (gibier tué) et D3 (animal tué).
- Référence : ajout pur.
- Test : KILL BEAR (réussi par RND imposé) puis SKIN BEAR : peau = 12 ×
  octet 30.

**C4. IGNORE FOOD / FLAG FOOD et réglage des ressources.**
- Original : IGNORE/SKIP FOOD pose `$4B75` = 1 (la marche ne s'arrête
  plus sur une ressource), FLAG FOOD le remet (msg 33). NATURE règle aussi
  la fréquence des ressources (`$4C52`, question « storm frequency » dans
  GO1, voir P1).
- Port : toute ressource découverte arrête la marche ; NATURE ne règle
  que la faune.
- Taille : ≈ 40 octets. Où : WILDOUT ou TRAVEL.
- Référence : ajout pur.
- Test : IGNORE FOOD puis WALK 1 H sur une zone riche : pas d'arrêt.

### 2.4 Sites et sprites non affichés

**S1. Poste de rangers, abri naturel (bille/rocher), cité perdue, abris fabriqués.**
- Original : table SURV3D `$1D0D` (§ A1) ; sprites décodés dans
  `build/original_graphics/` : poste 2 289, bille 1 216, rocher 1 158,
  cité 2 428, tente 969, igloo 859, tranchée 403 octets
  ([REGIONS.md](REGIONS.md) § 4).
- **Fait le 15 octobre 2026 (lot 6, en partie)** : poste des rangers
  (panneau et vue locale au but), rondin ou rocher de l'abri naturel
  trouvé sur carte native ([IMPLEMENTATION.md](IMPLEMENTATION.md)
  « Sprites de site », [MEMORY.md](MEMORY.md) § 19). Les abris fabriqués
  suivent le 15 octobre 2026 (lot 3, étape 3, XL seul, [CRAFT.md](CRAFT.md)
  § 8.4). Restent la cité perdue et plusieurs sites par vue (le site et
  l'animal d'une même case sont dessinés tous les deux depuis le
  15 octobre 2026 : D6). La cabane fixe
  des cartes générées est dessinée de même en rondin ou rocher (niveau de
  sa case, `tools/mkmap.py`) ; la hutte reviendra avec MAKE HUT (lot 3).
- Port (avant le lot 6) : épave et « cabane » seulement. La cabane utilise le sprite de la
  **hutte** (code 2) alors que l'abri trouvé de l'original est l'abri
  naturel (code 5 : bille sous `$60A3`, rocher au-dessus) ; la cabane
  fixe au tiers du trajet des cartes héritées est une invention du port
  (les cartes natives placent l'abri par découverte, `travel.s`). Un
  seul site projeté par vue.
- Taille : sprites 7,3 Ko pour l'ensemble ; projection : ≈ 60 octets par
  site supplémentaire (PROJECT).
- Où : poste et bille/rocher dans le tronc commun ; cité perdue avec le
  scénario 2 (G1) ; abris dans le tronc ou par région.
  Le stock auxiliaire n'a que 266 octets libres en Burma : **récupération
  de RAM auxiliaire obligatoire** (§ 3, lot 0). Le 800 Ko n'aide pas :
  les sprites doivent être résidents pour éviter un chargement à la vue.
- Référence : ajout pur (le rendu n'entre pas dans l'état comparé).
- Test : `test_projection.py` étendu au poste vu depuis huit directions ;
  abri naturel : bille à 5 000 ft, rocher au-dessus de `$60A3`.

### 2.5 Faune

**D1. Durée de présence et déplacements des animaux.**
- Original : la présence `$4B72` déclenche T$06/S$04 pour 1, 5 ou 60 min
  (relais `$4D56`, animals.md) ; le départ (msg 72) et la durée réelle
  restent à établir.
- Port : réaction après 60 minutes, départ après IGNORE à 25/50/75 %
  (règle du port), animal attaché à sa case.
- Taille : inconnue avant sonde (≈ 200 octets attendus). Où : WILDOUT.
- Référence : hors script (faune coupée).
- Test (sonde à écrire) : sur ROM, laisser un ours présent en REST 8 H et
  relever les chargements de T$06/S$04 et `$4B72` à chaque pas
  (`tools/re_animal_reactions_probe.py` étendu au relais complet).

**D2. Branche du cinquième degré de gravité et durée variable des morsures.**
- Original : T$06/S$04 `$5D25-$5D50` ; non porté (animals.md).
- Taille : ≈ 80 octets. Où : WILDOUT. Test : sonde RND imposé.

**D3. Animal tué, carcasse, armes fabriquées et fusil.**
- Original : ATTACK peut tuer (msg 70), la carcasse devient un stock
  (`$4AE0`), SKIN et EAT en tirent peau et viande ; moyens 17–21
  (gourdin/pierre, hache/couteau, lance, arc, fusil) avec leurs seuils.
- Port : seule hache/couteau ; une réussite fait partir l'animal.
- Taille : ≈ 250 octets (moyens 17, 19–21, création de viande) +
  5 seuils par espèce dans `fauna_reactions` (paquet de région).
- Où : WILDOUT (presque plein : 1 982 octets) → déplacer les textes ou
  scinder ; seuils dans les paquets (`build_disk.fauna_patches`).
- Dépend de : A2 (armes), C3.
- Référence : hors script.
- Test : `test_animal_reactions.py` étendu aux cinq moyens.

**D4. Protection de l'abri, RUN face à l'animal.**
- Original : abri = risque ×0,1 (`$5866-$5888`) ; RUN avec un animal
  présent affiche msg 182 et passe par les réactions (T$08/S$00).
- Port : abri = risque ×0,1, ATTACK et SCARE permis (**fait** le 15 octobre
  2026 avec le lot 3, `outdoor_hurt`, `test_animal_reactions.py` ; dans
  tout abri, l'abri naturel compris, comme l'original : décision du même
  jour) ; la vue
  de l'intérieur n'amène toujours aucun animal ; RUN = WALK (lot 11).
- Taille : ≈ 60 octets. Référence : hors script. Test : sonde existante
  (24 cas de posture) réutilisée avec abri actif.

**D5. Pacotilles et amitié du cannibale (New Guinea).**
- Original : USE TRINKETS en région 4 avec le cannibale présent : msg 171
  (T$11/S$05 `$5D78`) ; HELP place msg 223 en tête (T$13/S$00 `$586F`) ;
  T$06/S$06 `$5A2E` remet à zéro un octet 15 négatif de sa fiche après
  une action (sens à confirmer). La règle du second tirage < 0,02 avec
  TRINKETS portés est déjà portée.
- Port : règle du second tirage seulement ; USE TRINKETS → `m_notyet`.
- Taille : ≈ 60 octets. Où : WILDOUT ou module USE.
- Test (sonde) : exécuter T$06/S$06 avec le cannibale présent et
  TRINKETS en usage, relever l'octet 15 et la réaction suivante.

**D6. L'animal présent toujours visible (15 octobre 2026, fait).**
- Règle de l'utilisateur : « quand un animal est là, on doit voir son
  sprite sauf dans nos abris » ([LOOK_UPDOWN.md](LOOK_UPDOWN.md) § 4).
- Fidèle : site et animal de la même case tous deux dessinés (les deux
  emplacements `$0D84` et `$0D80`), l'animal devant ; aucune vue dans un
  abri ; aucun sprite en l'air (LOOK UP, SURV3D `$1C52`) : la seule vue
  sans l'animal, hors abris et pages.
- **Écarts voulus** : l'animal fait face au joueur quel que soit le cap
  (centré ; l'original le place au cap de son arrivée) ; il se voit à
  niveau même « au sol » (crotale, serpents : l'original incline la vue
  vers le bas à leur arrivée et ne dessine un sprite sans bit 7 que vers
  le bas, `$1C82`) ; la nuit sans pleine Lune et aux humeurs sans lumière,
  une silhouette de nuit (bleu foncé et gris) au lieu de rien ; avec un feu
  de camp (invention du port) sur la case, l'animal se pousse à côté du
  feu.
- Réalisé : PROJECT `module_animal` (+180 octets), résident −11 octets
  (clef du cache de scène sans l'animal, `animal_bearing` supprimé), SIM
  −12, SITES −5 ; [MEMORY.md](MEMORY.md) § 27. Test :
  `tests/test_animal_view.py`.

### 2.6 Déplacement et terrain

**M1. Pentes : CLIMB, crampons, piolet, corde et pitons, raquettes ; RUN, CRAWL.**
- Original : T$08/S$01 `$5D81` calcule le risque `$4B6D` (0–3) selon la
  pente `$DA` (rivière 5/10/16, terre 15/31, aggravé par pluie ou neige).
  T$08/S$07 : risque 1 sans crampons ni hache en usage → coût ×1,5, temps
  ×3 ; risque ≥ 2 en marche → « PLEASE USE 'CLIMB' COMMAND » ; CLIMB : ×5,
  ou ×2 avec corde et pitons en usage et corde solide ; neige avec
  raquettes : coût ×1,5 ; RUN 9 mph et effort 0,083 (`$4BCC` = 15),
  CRAWL 1 mph ; terrain rocheux ou jungle ×1,5 et effort ×1,2. Jambe
  cassée sans attelle : GO/RUN/CLIMB refusés (msg 95). CRAMPONS exigent
  des chaussures portées (msg 82).
- Port : la marche native suit les demi-pas, coûts, santé, charge, météo,
  diagonale et pente comparés sur ROM ; ni CLIMB de pente, ni crampons,
  ni raquettes, ni RUN/CRAWL distincts, ni refus de jambe cassée.
- Taille : ≈ 600 octets. Où : TRAVEL (2 045 octets, plein) → scinder en
  deux modules ou déplacer le tracé des caps.
- Référence : **correction de fidélité** si la pente du trajet de
  référence atteint le risque 1 (WALK 1 H depuis l'épave) ; à mesurer
  avant de corriger.
- Test : `make test-original` sur une pente raide (WALK refusée, CLIMB
  accepté), avec et sans crampons ; comparer les minutes.

**M2. Chutes, quasi-noyades, terrain dangereux.**
- Original : événements 11 (msg 146), 23 (chute, msg 158), 24 (noyade
  évitée, msg 159) tirés en T$0A/S$00 (`$599C`) avec une probabilité
  proportionnelle aux minutes (`$4C39`) ; le radeau évite la blessure
  (T$06/S$04 `$58FC`).
- Port : le tirage existe pour l'ordre du hasard (`travel.s`, « injury
  check, including zero risk »), sans effet.
- Taille : ≈ 200 octets (événements, blessure, perte de provisions).
- Où : TRAVEL ou ADV.
- Référence : correction de fidélité seulement si le risque est non nul
  sur le trajet de référence (`$4B6D` = 0 attendu sur terrain plat).
- Test : sonde ROM du tirage avec risque 1–3 ; perte de provisions
  après msg 159.

**M3. Radeau, PADDLE/ROW, suivre une rivière ou une rive.**
- Original : T$08/S$01 (≈ 1 500 octets) et T$08/S$07 : refus vers
  l'amont (msg 128), non navigable (129), questions « suivre l'aval »
  (130), « continuer » (133), « suivre la rive » (134), « en ligne
  droite » (127), courte étape prudente (131) ; vitesse du courant
  `2 × $4B6D + 3` ; radeau perdu en nageant hors rive (msg 135) ; USE
  RAFT exige l'eau. Lac : `$4B63` = 2, effort 0,04 × poids.
- Port : rien (SWIM seulement).
- Taille : ≈ 2 000 octets.
- Où : module « RIVER » ; il utilise la grille de carte (eau, hauteur) déjà
  résidente et la géographie fine sur carte native.
- Dépend de : A3 (radeau fabriqué) ou radeau de l'épave (absent du lot
  chilien) ; M1 (risque).
- Référence : ajout pur.
- Test : carte de contrôle avec une rivière orientée : PADDLE 2 H vers
  l'aval, refus vers l'amont ; comparer les positions à l'original
  (`make test-original`, scénario à ajouter à ADVENTURE_TESTS.md).

**M4. Messages de terrain et de lieux.**
- Original : événements 1–10 et 35 au changement de classe (msg 136–145,
  170 : rivière, lac, lac gelé, rocheux, dégagé, rive, **jungle** en
  régions 3–5 au lieu de forêt, broussailles au-dessus de `$60A6`),
  rivière proche (msg 208, une fois), odeur (msg 209, T$0D/S$0D, cause à
  confirmer), épave et poste proches (164, 165), cité proche (166),
  retour au départ (168), objet déjà déposé ici (157), objets au sol
  pillés (169), abri naturel trouvé (156).
- Port : arrêts nommés de faune et de ressources ; aucun de ces
  messages, sauf l'arrivée au poste.
- Taille : ≈ 350 octets (textes compris, ≈ 250 de texte).
- Où : textes dans un module de messages ou le paquet de région (mots
  JUNGLE/WOODS) ; logique dans TRAVEL/ADV.
- Référence : ajout pur si le message n'interrompt pas la marche ;
  l'original l'affiche sans arrêt (à confirmer pour 156, qui arrête).
- Test : WALK d'une forêt vers une rivière : messages 143 puis 136 ;
  Burma : 142.

**M5. Éteindre le feu avant de partir, refus divers de déplacement.**
- Original : T$08/S$00 : feu allumé → msg 132 ; sac de couchage porté et
  SWIM → msg 251 ; marcher sur l'eau → msg 22 ; épuisement → msg 95 ;
  RUN trop faible → msg 175 ; bord du monde msg 99.
- Port : bord du monde, nage hors de l'eau et arbre portés ; les autres
  absents.
- Taille : ≈ 120 octets. Où : résident (`do_walk`) ou TRAVEL.
- Référence : ajout pur pour 132/251 ; msg 95 (santé < 26 %) est une
  correction hors script.

### 2.7 Orientation

**O1. LOOK SUN, LOOK STARS, montre et bâton (ombre).**
- Original : T$10/S$0C. Dans un abri : message court « INSIDE SHELTER ».
  LOOK SUN : msg 41 si le soleil est caché, sinon la vue se tourne vers
  l'azimut du soleil. **LOOK STARS** (Apple II) : msg 52 si la nuit n'est
  pas claire (`$4B49 + $4B4C` ≥ 0), sinon la vue se tourne vers le pôle
  céleste (nord, ou sud si la latitude `$60A8` est négative) ; pas de
  catalogue nommé (celui-ci n'existe que dans la version DOS). LOOK N/E/S/W
  et AZ exigent une aide à l'orientation en usage (COMPASS, WATCH ou
  `$4B4A` ombre), sinon msg 42. Avec la boussole : msg 44 « magnétique ».
  Avec la montre et le soleil : msg 189/190 puis estimation de l'azimut
  (msg 13/14 ou 201/202 selon l'hémisphère). Avec le bâton (USE SHADOW,
  `$4B4A` = 1, jour clair) : msg 29/30 puis durée d'observation (msg 48),
  temps dépensé. Sinon msg 104. LOOK MAP/CHART → USE ; LOOK COMPASS →
  cap actuel (msg 256).
- Port : LOOK N/E/S/W sans exiger la boussole (précision aléatoire
  portée quand elle est en main) ; LOOK AZ exige la boussole ; ni SUN, ni
  STARS, ni montre, ni ombre ; spécification d'un LOOK STARS nommé
  ([STARS.md](STARS.md) § 11), qui est une extension.
- Taille : ≈ 700 octets (sans catalogue) ; LOOK STARS original seul
  ≈ 60 octets (tourner la vue vers le pôle).
- Où : module TREE (LOOK, 916 octets) pour SUN/STARS ; montre et ombre
  dans INPUT (1 442 octets) ou un module « NAV ».
- Référence : la règle « aide à l'orientation en usage » est une
  **correction de fidélité** hors script (le script ne fait que LOOK R).
- Test : LOOK STARS de jour → msg 52 ; de nuit claire en Bolivia → cap
  180 ; LOOK N sans boussole → msg 42 ; USE SHADOW puis LOOK N : sonde ROM
  de la durée et du cap.
- **Fait (lot 7)** : [ORIENTATION.md](ORIENTATION.md) (sondes, écarts
  conservés : hauteur de vue, saisie décimale, lampes).

**O2. USE MAP, outils de mesure, cap annoncé.**
- Original : USE MAP ouvre la carte (T$11/S$00 `$5BF9`, `$0D5B` = 4) ;
  ALTIMETER, WATCH, COMPASS passent en main ; la boussole et la montre
  s'excluent ; STATUS dépend des instruments (altitude LOW/MEDIUM/HIGH
  sans altimètre, environment.md).
- Port : TOPO et MAP sans objet requis ; STATUS affiche l'altitude
  chiffrée (à vérifier contre la règle sans altimètre).
- Taille : ≈ 150 octets. Référence : correction de fidélité de STATUS
  (le script l'affiche : variables d'écran seulement, hors état comparé
  à vérifier).
- **Fait (lot 7)** : USE MAP ouvre TOPO, instruments en main, exclusion
  boussole/montre ; l'altitude LOW/MEDIUM/HIGH était déjà portée (règle
  vérifiée sur la ROM) ; [ORIENTATION.md](ORIENTATION.md).

### 2.8 Blessures, maladies et soins

**H1. Déclencheurs manquants : infection, malaria, coups de chaleur et de froid.**
- Original : les modules d'action ne touchent pas directement les
  conditions ; ils postent un événement `$4B41` (genre), `$4B42`
  (sous-code), `$4B44` (condition) consommé ailleurs (à localiser :
  T$06/S$02 et la chaîne T$0B). Giardiase (eau) et intoxication (repas)
  sont localisées ; infection (9) et malaria (13) ne le sont pas.
  HELP propose msg 249 « nettoyer les coupures non traitées » et 224
  (malaria : couvrir la peau, répulsif, quinine).
- Port : coupures, fractures, choc, morsures, giardiase ont des
  déclencheurs propres au port ; infection et malaria jamais déclenchées.
- Taille : ≈ 250 octets. Où : WILDMED (2 045 octets, plein) → scinder.
- Référence : correction de fidélité (déclencheurs exécutés à chaque pas
  de santé) : à faire sur une référence rebasée.
- Test (sonde) : localiser le consommateur de `$4B41/$4B42/$4B44`
  (balayer la face Journey pour les lectures de `$4B44`), puis l'exécuter
  sur ROM avec coupure non soignée en Burma.

**H2. Soins non portés : SPLINT, soins thermiques, WET BODY, COOL, DRY/WARM, CUT BODY, SOAP, stérilisation.**
- Original : USE SPLINT (T$11/S$00 `$5B80`, sélecteur 3, WEAR) ;
  WET BODY (T$15/S$0A : sélecteur 9 dans l'eau ou sous la pluie, sinon
  module eau) ; DRY/WARM vêtements → T$12/S$08 (msg 117, 118 ; HANG des
  vêtements mouillés au soleil ou au feu) ; CUT BODY avec trousse, hache
  ou couteau (événement 1,7) ; messages de soin 210–230. Placement
  automatique des objets et stérilisation de la trousse : à porter
  (IMPLEMENTATION.md).
- Port : FIRSTAID, SNAKEBITE KIT, STOP BLEEDING, SHIELD EYES, LOWER HEAD,
  SUCK VENOM, prises orales.
- Taille : ≈ 400 octets. Où : MVI (878 octets, place disponible).
- Dépend de : A2 (attelle fabriquée) ; l'attelle de l'épave n'existe pas.
- Référence : ajout pur (commandes non jouées) ; les sélecteurs sont déjà
  dans les tables de prérequis T$06/S$00 portées.
- Test : `test_care.py --original` étendu (USE SPLINT sur bras cassé,
  WET BODY sur coup de soleil).

**H3. Sommeil forcé et alertes de santé.**
- Original : `$0B` ≠ 0 force REST sans saisie (épuisement, msg 178) ;
  msg 160, 173–177, 187, 203, 204 selon les jauges.
- Port : alertes de transition propres (`summary.s`), frissons et sueur
  affichés ; sommeil forcé non porté (à confirmer dans `game.s`).
- Taille : ≈ 120 octets. Référence : correction de fidélité si la fatigue
  du script atteint le seuil (peu probable).

**État (lot 13, 14 octobre 2026).** H1, H2 et H3 sont portés et vérifiés
sur ROM ([IMPLEMENTATION.md](IMPLEMENTATION.md) « Soins, alertes et
maladies (lot 13) ») : le consommateur des événements est T06/S00, déjà
porté ; infection et malaria viennent de T0B/S07 (`hz_diseases`,
interrupteur `disease_triggers`), sans effet sur la référence. Restent :
l'attelle fabriquée (lot 3, crochet `splint_place`), le feu (lot 2,
crochet `care_fire_here`), le sélecteur 6 de DRINK (lot 2), la recherche
d'eau de WET BODY (lot 2), l'effort de T0A/S0C `$5CB6` sur `A1[24]`
(modifie la référence : lot 12) et les chutes (T0D/S00, événement 23).

### 2.9 Préparation du voyage, niveaux et scénarios

**P1. Questions de préparation (GO1/GO3) et mode recherche.**
- Original : options 2 et 3 du menu (l'option 1 charge l'état figé de
  la Sierra, niveau 4) : scénario P/L (`$605F`), date et heure choisies
  ou tirées, jeu normal ou **mode recherche** (`$4B59`), sexe, poids
  50–350 lb (`$4BF6`), carrure, taille, âge, pouls au repos (verdict de
  forme GO2 `$24D6`, `$4C20`, `$4C25`, Hmax `$4C2F`), fréquence de la
  faune (`$4C4D`), fréquence des orages (`$4C52`). Le mode recherche
  saute les questions de corps, les risques de déplacement, les attaques,
  la chaîne thermique et de santé et le score, et donne boussole, montre,
  altimètre, lampe et thermomètre.
- Port : région et niveau seulement ; joueur fixe (165 lb) ; voyage
  libre réensemence le hasard.
- Taille : ≈ 1 500 octets de chargeur (questions, formules de corps),
  **sans coût résident** : le chargeur `NEOWILD.SYSTEM` tourne dans la
  fenêtre SIM avant la partie.
- Où : chargeur (menu). Le mode recherche demande des drapeaux dans SIM
  et WILDOUT (≈ 60 octets).
- Référence : ajout pur si le scénario classé garde l'état figé de
  l'option 1 (c'est le cas du test).
- Test : poids 250 lb → métabolisme et Hmax comparés à GO2 exécuté sur
  ROM avec les mêmes réponses (sonde à écrire, comme
  `re_region_fauna_probe.py`).

**P2. Effets du niveau de difficulté.**
- Original (balayage de `$603F` et GO1/GO2) :
  - carte (TMAKE) : forêts max(5, 1,5 L), densité de sommets
    ∝ √L, distance épave → poste ≥ 76 + 10 L, marge de l'épave 28 − L ;
  - faune √L, ressources 1/√L (porté) ;
  - **blessure du crash** (GO2 `$2024`, scénario 1, jeu normal) :
    n = ⌊0,45 × RND × L − 0,3⌋ borné à 0–3 : rien, coupures, bras, jambe
    (jamais aux niveaux 1–2, jambe à partir de 8) ;
  - **objets de l'épave** (GO2 `$25FC`) : neuf groupes, chacun garde
    environ (11 − L) × taille / 10 objets tirés ;
  - nombres d'usages des consommables ×1/√L (GO2 `$26C2`, à confirmer) ;
  - premier front météo `3000 / (L × $4C43) + 20` h et durée
    (GO1 `$5E0B`) ;
  - phase lunaire de départ `60 − 18 L` degrés (GO1 `$5935`) ;
  - date et heure de départ plus dispersées (GO1 `$5A38`) ;
  - verdict de STATUS ×0,85 (L ≥ 3), ×0,7 (L ≥ 8) (T$06/S$0C `$5A45`) ;
  - facteur de score `$4B99` et +L points au score final ;
  - mots de l'introduction : terrain MODERATE/VARIED/PUNISHING,
    difficulté LOW, LENIENT, RESPECTABLE, CHALLENGING, BACK-BREAKING.
- Port : seul `MAP+22` change (faune, ressources) ; cartes générées au
  niveau 4 ; état de départ identique à tous les niveaux.
- Taille : ≈ 600 octets de chargeur (sans coût résident) ; cartes par
  niveau : une carte par (région, niveau) sur disque, **possible grâce au
  800 Ko** (≈ 9,5 Ko par carte, plus l'atlas fin s'il est retenu), ou un
  générateur hors ligne (`mkmap.py --level`).
- Référence : ajout pur au niveau 4 si le tirage de la blessure et de
  l'épave n'est appliqué qu'aux voyages autres que l'état figé ; sinon
  le niveau 4 lui-même change (n ∈ {0, 1}).
- Test : niveaux 1, 4, 10 : blessure, lot de l'épave et date comparés à
  GO2 exécuté sur ROM avec RND imposé.

**P3. Objets de l'épave et conteneurs.**
- Original : lot tiré dans une réserve commune (animals.md « Objets de
  l'épave ») selon le niveau (P2) ; comptabilité des conteneurs
  `$4BEE-$4BFC` (corps, sac, main) ; découpe d'objets (A3).
- Port : lot Sierra fixe pour toutes les régions ; modèle additif
  calibré des capacités (879 oz, 2149/6000/2874 in³), non original.
- Taille : ≈ 300 octets (formules des conteneurs) ; tirage du lot dans le
  chargeur.
- Référence : **correction de fidélité** (charge et marche changent sur
  le chemin de référence) ; à faire avec une référence rebasée.
- Test : capacités restantes de la première partie (43 oz, 1525/4134/2542)
  retrouvées par la formule, puis après PACK/DROP de chaque catégorie,
  comparées à `make test-original`.

**G1. Second scénario : la cité perdue, la statue d'or et CLUE.**
- Original : `$605F` = 2 ; départ au poste (rôles inversés : la cité est
  au point d'épave), équipement réuni au poste (`DISPHELP` DOS ; à
  confirmer sur Apple : objets au sol du poste), quadrant et altitude de
  la cité dans l'introduction. Onze vestiges autour de la cité
  (`$608B`, TMAKE) : crâne (msg 161), poterie (162), sépultures (163).
  Arrivée à la cité : statue (T$07/S$07, msg 96, 253–255), poids
  `2 × poids + 40` oz, but ramené au poste ; retour au poste = victoire
  (la statue n'a pas besoin d'être portée, +10 au score si trouvée).
  CLUE (T$15/S$00 → S$05, ≈ 2,2 Ko) : indice tiré (rivière, lac, forêt,
  jungle, montagne, vallée, distance en heures, cap du ranger), historique
  rejoué, coût 0–2 points par indice ; refus en scénario 1. Sprite de la
  cité (2 428 octets).
- Port : CLUE → `m_notyet` ; aucun second scénario.
- Taille : ≈ 3 Ko de code et de textes (CLUE ≈ 2,2 Ko, vestiges et
  statue ≈ 0,4 Ko, introduction dans le chargeur) + sprite 2,4 Ko +
  11 paires de vestiges par carte (générées par `mkmap.py`).
- Où : CLUE dans un module de la fenêtre `$5800` (≈ 2 Ko : un module
  plein) ou **chargé depuis le disque à la commande** (rare, coût
  résident nul ; politique à décider) ; vestiges dans TRAVEL/ADV ;
  sprite et module CLUE dans des paquets « cité » distincts des paquets
  de région (800 Ko : six paquets supplémentaires possibles).
- Dépend de : S1 (sprites de site), P1 (choix du scénario), HOF (une
  table par scénario × région : le fichier `NEOWILD.HOF` passe de 6 à 12
  tables).
- Référence : ajout pur.
- Test : carte de contrôle avec cité à 3 cases : vestige, statue,
  retour au poste, score ; CLUE en scénario 1 → refus.

### 2.10 HELP, score et fin de partie

**E1. HELP : conseiller classé.**
- Original : T$13/S$00 classe 27 besoins (conditions 1–15, eau,
  nourriture, repos, altitude, froid, chaleur, menace selon la meilleure
  parade de l'espèce présente, pente, rivière, désorientation avec cap
  vers le but, préventions) et affiche jusqu'à dix lignes (msg 210–250 ;
  « YOU DON'T NEED ANY HELP! ») ; premier HELP au départ : conseils pour
  réunir l'équipement. Chaque HELP coûte 2 % de GOAL et 10 points de
  score (`inc $4BDE`).
- Port : trois pages fixes de commandes (`module_help`, WILDSCR) ;
  aucune pénalité. Le résumé de survie du port (`summary.s`) donne déjà
  une partie de ces conseils.
- Taille : ≈ 1 500 octets de code + ≈ 2 000 octets de textes (41
  messages).
- Où : module de la fenêtre `$5800` dédié (ou disque à la commande) ;
  textes compressés dans le module.
- Dépend de : D1/D3 pour la menace, H1 pour l'infection.
- Référence : **le script appelle HELP** : la pénalité `$4BDE` modifie
  GOAL% et l'état comparé (variable nouvelle : invisible ; mais GOAL%
  dépend de la pénalité si elle est appliquée à une variable existante).
  Garder l'aide de commandes du port sous une autre touche et appliquer
  la pénalité seulement au conseiller.
- Test : sonde ROM du classement avec un état préparé (soif + coupure +
  ours) : ordre des messages.

**E2. Score original, rangs et résurrection.**
- Original : mort → msg 180 puis msg 188 « RESURRECTED [R] OR JUST QUIT
  [Q] » ; R remet la santé, efface les conditions et divise le facteur de
  score par deux (msg 77). Victoire : score `10 × min(250, B − HELP −
  ⌊indices/2⌋ + 10 × statue) + L` et rangs TENDERFOOT, WEEKEND HIKER,
  GOOD SCOUT, SUPERB RANGER, EXPERT EXPLORER (T$0F/S$0D) ; GOAL% pénalisé
  par HELP et CLUE ([survival.md](logic/survival.md) § GOAL%).
- Port : score propre au port et hall of fame ([HOF.md](HOF.md)) ; pas de
  résurrection.
- Taille : ≈ 250 octets (résurrection dans le résident ou ADV ; rang dans
  `NEOWILD.END`, chargé depuis le disque, coût résident nul).
- Référence : ajout pur.
- Test : mort provoquée, R : santé pleine, score de fin divisé ; Q :
  bilan du port.

### 2.11 Sauvegarde et reprise

**V1. SAVE / RESTORE.**
- Original : disquette de sauvegarde distincte (type 3), cinq parties de
  95 secteurs (carte `$6000-$AFFF`, état `$4000-$4CFF`, `$0D59-$0DBF`,
  graine `$03B8-$03BC`, page zéro), catalogue (nom 32 caractères,
  région, niveau, scénario, drapeau R) ; RESTORE refuse une autre région ;
  T13/SF n'écrit que la région au catalogue.
- Port : jamais implémentés.
- Taille : ≈ 900 octets de code (écran de choix, nom, écriture MLI)
  hors résident. État à sauver : GDATA/BSS, `it_*`, horloge, simulation
  persistante, en-tête de carte et octets modifiés de la carte (sites,
  abris, ressources), `shelter_inside`, `tree_in`, LFSR et graines,
  octets d'état de SIM et des modules (`s_temp_phase`…) : à inventorier
  ; probablement 3 à 5 Ko par partie (la grille 112 × 84 ne change pas,
  sauf abris et objets au sol, sauvés comme différences).
- Où : module chargé depuis le disque à la commande (`NEOWILD.SAV`,
  comme `NEOWILD.END`), tampon E/S `$BA00` (occupé par MENUCODE depuis le
  lot 8 : utiliser `LD_IOBUF` `$AB00` dans la fenêtre SIM, rechargée
  ensuite) ; fichier `NEOWILD.SAV` de 5 emplacements (≈ 25 Ko), **possible
  grâce au 800 Ko** (33 blocs libres sur 140 Ko : non).
- Dépend de : un inventaire exhaustif de l'état (le test
  `test_reference_state.py` liste déjà les variables nommées de GDATA,
  BSS et GZP : point de départ).
- Référence : ajout pur.
- Test : SAVE puis RESTORE au milieu d'un trajet : état comparé octet
  pour octet (même méthode que `test_reference_state.py`), puis WALK
  identique dans les deux sessions ; disquette protégée : message.

### 2.12 Régions

**R1. Branches de région non portées** ([REGIONS.md](REGIONS.md) § 7).
| Branche | Original | Port | Taille |
|---|---|---|---|
| Mot JUNGLE au lieu de WOODS, régions 3–5 | T$0A/S$00 `$589E`, événements 7/8, broussailles 35 | aucun message de terrain (M4) ; STATUS du port : à vérifier | ≈ 20 octets + texte |
| Corde sans diamètre et matériau de bambou, régions 3–5 | T$10/S$07 `$5981`, `$5AF9` | pas de fabrication (A3) | inclus dans A3 |
| Armes sans corde, régions 3–5 | T$10/S$00 | — | inclus dans A2 |
| Pluie du Chili ×6 sous −40° | T$0C/S$05 `$5A5A` | absent ; la carte chilienne reconstituée est à −25° : **sans effet** tant que la latitude reste > −40° | ≈ 30 octets dans SIM (WEATHER) |
| Cannibale | T$11/S$05, T$06/S$06, T$13/S$00 | D5 | inclus dans D5 |
| Légende régionale de TOPO | T$05/S$09 `$5917` (table `$B1A6`, à confirmer) | TOPO du port propre | ≈ 50 octets |
| Région au catalogue de sauvegarde | T13/SF | V1 | inclus |

**R2. Terrain et altitude de base par région.**
- Original : niveau rocheux `$60A3` (120 partout sur Apple), base
  d'altitude jungle = − niveau minimal (POSTP), broussailles `$60A6`.
- Port : cartes reconstituées générées au niveau 4 avec la base de
  `mkmap.region_header` (bornée à 0) ; règles de terrain sondées sur la
  seule Sierra (animals.md « Limites »).
- Taille : données de carte seulement. Référence : ajout pur.
- Test : sonde région par région du terrain sous le joueur (T09/S08) sur
  une carte patchée (méthode de `re_region_fauna_probe.py`).

**R3. Géographie fine des six régions.**
- TODO direction 1 : un atlas par région ne tenait pas sur 140 Ko ; avec
  le 800 Ko, **six atlas tiennent** (≈ 13 blocs chacun). La RAM reste
  l'obstacle : sur carte native, l'atlas remplace l'instantané TOPO dans
  la carte langage auxiliaire (déjà le cas pour la Sierra native) ; la
  simulation des cartes héritées change (référence à rebaser).

### 2.13 Divers

| Élément | Original | Port | Taille, référence |
|---|---|---|---|
| Interruption de REST par la météo (msg 147) | REST s'arrête quand le temps se dégrade (ADVENTURE_TESTS.md : écart observé après quatre heures) | REST continue | ≈ 40 octets ; **correction de fidélité** (le script dort 48 h : à mesurer) |
| CURE/HEAL | messages 17, 18, 36 | refus générique | ≈ 20 octets, ajout pur |
| Messages d'objets déposés, pillage | msg 157, 169 | absents | M4 |
| NATURE fractionnaire | réel > 0 | entiers 0–100 | extension du port conservée |
| Taux Sierra | Apple 80/40/100 | idem | fidèle |
| Plusieurs sites dans la vue | l'original choisit un site (`$0D84`) et un animal (`$0D80`) | deux emplacements aussi depuis le 15 octobre 2026 : le site (local ou panneau le plus proche, `module_project`), puis l'animal de la case par-dessus (`module_animal`) ; avant, l'animal de la case prenait l'unique emplacement et un site local de la case le masquait | fidèle (D6) |

## 3. Ordre de lots proposé

Chaque lot représente 1 à 3 Ko de 6502, un agent. **Ajout** : pur
ajout, `test_reference_state.py` reste vert sans changement de la
référence. **Fidélité** : la simulation du chemin de référence change ;
le lot commence par rebaser la référence HGR (nouvelle référence figée,
documentée) ou se limite aux chemins non joués.

### Lot 0 — place (préalable à presque tout)

Fait le 14 octobre 2026 en quatre récupérations (MEMORY.md § 12 à 15) ;
marges actuelles : MEMORY.md § 15.2.

Sans ce lot, seuls les éléments « chargeur » (P1, P2), « disque à la
commande » (V1, E2, éventuellement CLUE) et les petits correctifs dans
MVI tiennent.

- RAM auxiliaire : décider le sort de l'instantané TOPO (12,8 Ko en carte
  langage auxiliaire sur carte héritée). Le remplacer par un redessin au
  retour (comme sur carte native, 0,24 s → coût d'une vue) libère 12,8 Ko
  sur les régions héritées ; rendre les six cartes natives (R3, possible
  grâce au 800 Ko) le remplace par l'atlas. Dans les deux cas, déplacer
  sprites et modules du stock `$4000-$BFFF` vers la carte langage libère
  le stock pour les nouveaux modules.
- RAM principale : la table de répartition et le second jeu d'objets
  (≈ 150 octets) n'ont pas de place (361 octets libres morcelés) : sortir
  `resolve_noun`/`dispatch` du module VOCAB plein, et déplacer des textes
  de TEXT/WILDLO vers un module.
- Résultat attendu : ≥ 10 Ko auxiliaires libres en Burma ; ≥ 400 octets
  principaux contigus.

### Lots de jeu, par valeur et faisabilité

| Lot | Contenu | Taille | Place | Nature | 800 Ko suffit ? |
|---|---|---:|---|---|---|
| 1 | **Préparation du voyage et niveaux** : P1 (questions, corps, mode recherche, fréquences), P2 (blessure du crash, lot de l'épave, front, lune, date), mots d'introduction | 2,1 Ko | chargeur, sans coût résident ; 60 octets SIM/OUT pour le mode recherche | Ajout (état figé conservé pour le scénario classé niveau 4) | oui ; cartes par niveau : oui (une carte par niveau sur disque) |
| 2 | **Feu, lumière, eau** : F1, F2, F3 (sans iodine), C4, M5 (éteindre avant de partir) | 2,2 Ko | module « CAMP » (2 Ko) + 40 octets SIM | Ajout, sauf conversion de DRINK et giardiase (Fidélité) | non : lot 0 |
| 3 | **Second jeu d'objets, outils, armes, abris** : A1, A2, sprites tente, igloo, tranchée ; protection d'abri ×0,1 (D4) | 2,5 Ko + 2,2 Ko de sprites | module « CRAFT », tables résidentes 150 octets | Ajout | non : lot 0 |
| 4 | **Chasse, pêche, cueillette, repas** : C1, C2, C3, D3 (tuer, carcasse, cinq moyens) | 2,8 Ko | modules « FORAGE » (+ « MEAL » si besoin), seuils dans les paquets | Ajout ; péremption des provisions au sol : Fidélité | non : lot 0 |
| 5 | **Fabrication 2 et radeau** : A3, M3 | 3,6 Ko (deux agents possibles : 5a fabrication, 5b rivière) | modules « CRAFT2 », « RIVER » | Ajout | non : lot 0 |
| 6 | **Sites** : S1 (poste, bille/rocher à la place de la hutte pour l'abri trouvé, plusieurs sites si la place le permet), M4 (messages de terrain, JUNGLE) | 0,6 Ko + 2,4 à 4,7 Ko de sprites | PROJECT, TRAVEL/ADV, tronc | Ajout (rendu, textes) | non : lot 0 (sprites résidents) |
| 7 | **Orientation** : O1 (SUN, STARS au pôle, montre, ombre, aide requise), O2 | 0,9 Ko | TREE, INPUT ou « NAV » | Fidélité hors script (LOOK N exige une aide) | partiellement (TREE a ≈ 1 Ko libre dans sa fenêtre) |
| 8 | **HELP classé, résurrection, score original** : E1, E2 | 3,5 Ko | module HELP (ou disque à la commande), `NEOWILD.END` | Fidélité (HELP joué par le script : pénalité à isoler) | oui si HELP est lu à la commande ; sinon lot 0 |
| 9 | **Sauvegarde et reprise** : V1 | 1 Ko de code + fichier ≈ 25 Ko | module disque `NEOWILD.SAV` | Ajout | **oui, grâce au 800 Ko** ; RAM : aucune résidente |
| 10 | **Scénario de la cité perdue** : G1 (CLUE, vestiges, statue, introduction, HOF à 12 tables) | 3 Ko + sprite 2,4 Ko | CLUE à la commande (disque) ou module ; paquets « cité » | Ajout | CLUE et paquets : oui ; sprite et vestiges résidents : lot 0 |
| 11 | **Faune complète** : D1 (durée, déplacements), D2, D5, RUN (D4) | 0,6 Ko | WILDOUT scindé | Fidélité hors script (faune coupée) ; sondes préalables | non : lot 0 |
| 12 | **Terrain, pentes, risques** : M1, M2, H3, interruption de REST par la météo | 1,0 Ko | TRAVEL scindé, SIM | **Fidélité** (WALK et SLEEP du script) : rebaser la référence | non : lot 0 |
| 13 | **Médecine** : H1 (infection, malaria via le consommateur d'événements), H2 (SPLINT, WET, COOL, DRY, CUT, SOAP) | 0,7 Ko | WILDMED scindé, MVI | H2 Ajout ; H1 Fidélité | H2 : oui (MVI) ; H1 : lot 0 |
| 14 | **Conteneurs et charge** : P3 | 0,3 Ko | ITM, GDATA | **Fidélité** (charge, marche) | non |
| 15 | **Régions** : R1, R2, R3 (atlas par région) | données + 0,1 Ko | paquets de région, SIM | R3 Fidélité (cartes héritées) | atlas : **oui, grâce au 800 Ko** ; RAM : instantané TOPO (lot 0) |

Ordre recommandé : 0 → 1 → 9 (deux lots sans coût résident, débloqués par
le 800 Ko, à faire en parallèle du lot 0) → 2 → 3 → 4 → 6 → 7 → 8 → 5 →
10 → 13 → 11 → 15 → 12 → 14. Les lots de fidélité 12 et 14 viennent en
dernier, ensemble, sur une référence rebasée une seule fois, et après une
nouvelle aventure complète comparée à `make test-original`.

Sondes à écrire avant les lots concernés (aucune n'a été lancée pour ce
document) :

1. consommateur des événements `$4B41/$4B42/$4B44` (H1, iodine F3) :
   balayage des lectures de `$4B44` sur la face Journey, puis exécution ROM ;
2. durée de présence animale (D1) : relais `$4D56` sur un REST complet ;
3. GO2 exécuté avec réponses et RND imposés (P1, P2) ;
4. formules de temps de fabrication (A1–A3) : **faite** le 15 octobre
   2026 (`tools/re_craft_probe.py`, [CRAFT.md](CRAFT.md)) ; « d » est
   `$0D5D`, la lumière ;
5. sens de `$D8`/`$D9` = `$7F` : **fait** (CRAFT.md § 3.1) : le joueur sur
   la case du poste (`$D8`) ou de l'épave (`$D9`) ;
6. équipement du poste en scénario 2 sur Apple II.

## 4. Ce qui est déjà fidèle

Ne pas refaire (preuves dans les documents cités) :

- Vocabulaire complet (280 mots, classes, numéros, qualificatifs SOCKS,
  KIT, TABLETS, animaux d'une autre région).
- Horloge, pas de santé, crédits de REST/EAT/DRINK à la gourde, déficits
  et pourcentages entiers, santé produit des 21 conditions, mort sous 0,3
  ([survival.md](logic/survival.md)).
- Courbes, prérequis, prévention et traitement des conditions 1–15,
  altitude et oxygène, compteurs sel/froid, doses et stocks vides
  (639 cas ROM, IMPLEMENTATION.md « Conditions médicales »).
- Thermique sèche, mouillée et immergée, vent ressenti, frissons,
  température de l'eau, abri trouvé +15 °F.
- Températures journalières et horaires, onde lente, fronts, visibilité,
  plafonds météo, vent (tests ROM).
- Marche native : demi-pas, tracé des 360 caps, coûts, nage et son effort,
  limites du monde ; boussole avec précision aléatoire et déclinaison.
- Filtres, taux et remplacements de rencontre des six régions, seuils de
  bruit, blessure, posture, arbre, vol et gravité, pacotilles
  ([animals.md](logic/animals.md)) ; découverte des ressources et ordre
  des tirages associés.
- Arbres : CLIMB TREE/DOWN, HANG FOOD et récupération du sac
  ([trees.md](logic/trees.md)).
- ENTER/EXIT SHELTER (messages et états), GOAL%, en-têtes et faune des six
  régions, 27 sprites extraits.
