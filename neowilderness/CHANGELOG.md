# Wilderness — historique

Les étapes ci-dessous décrivent les travaux présents dans l'arbre de travail.
Elles ne correspondent pas à des versions publiées. Les tâches à venir sont
suivies dans [TODO.md](TODO.md) et les limites du portage dans
[IMPLEMENTATION.md](docs/IMPLEMENTATION.md).

## Non publié

### Neowilderness : orientation (lot 7 de fidélité)

- Règles de T$0F/S$0F, T$10/S$0C et T$11/S$00 sondées sur la ROM
  (`tools/re_orientation_probe.py` : 22 portées, 14 exécutions du module,
  trois parties tapées) et portées (`src/orient.s`,
  [ORIENTATION.md](docs/ORIENTATION.md)) : aide en usage pour LOOK
  N/E/S/W/AZ (msg 42 ; aucune au départ, CARRY n'est pas USE), boussole
  (msg 44), montre (msg 189, 13 ou 201, estimation), bâton (msg 29, 48,
  durée passée), LOOK SUN (msg 41 ; visibilité ≥ 139, ≥ 163 à l'aube et au
  crépuscule), LOOK STARS (msg 52 hors nuit claire ; pôle ±33°, sud si la
  latitude est négative), LOOK COMPASS (msg 256), LOOK WATCH/ALTIMETER,
  INSIDE SHELTER, PAN + direction (msg 2), USE MAP/COMPASS/WATCH/
  ALTIMETER/CHART/SHADOW, exclusion boussole/montre, lumière (msg 53),
  montre et bâton rangés par le temps.
- Menu : LOOK SUN et LOOK STARS, USE liste aussi MAP…CHART.
- Tests : `tests/test_orientation.py` ; USE COMPASS ajouté aux scripts qui
  tapent LOOK N/E/S/W (`test_compass`, `test_hud`, `test_pan`,
  `test_sites`, `test_play`) avec l'erreur ±2° de la
  boussole originale ; LOOK B dans `test_tree` ; carte « patchy » de
  `test_geo_resident` à deux tuiles brutes (le volume 140 Ko est plein
  pour une carte native de niveau 10).
- Mémoire : WILDLO 1 718 → 276 octets libres, TREE 916 → 1 926, stock
  auxiliaire −1 023 octets par région, disque 261 → 265 blocs.

### Neowilderness : soins, alertes et maladies (lot 13 de fidélité)

- Commandes de soin de T11/S00, T12/S08 et T15/S0A : USE SPLINT (sélecteur
  3, attelle portée, 30 min ; crochet `splint_place` pour l'attelle du
  lot 3), USE PRESSURE (sélecteur 2), USE AXE/KNIFE (outil en usage),
  CUT/COOL BODY (sélecteur 7 avec un outil en usage), WET BODY (sélecteur 9 :
  front météo, eau, rivière à portée ou onces de la gourde), DRY/WARM
  (messages 117/118), HANG des vêtements (séchage au soleil ; crochet du feu
  pour le lot 2) ; placement automatique des objets utilisés (main, lunettes
  portées). Verbes 13, 14, 31 et 33 aiguillés sans entrée de table
  (`verb_more`), HANG passe par `care.s`.
- Alertes originales ajoutées sous le résultat : faim 173, soif 174 et
  fatigue 175 une fois par jour, frissons/sueur 203/204 et détérioration 187
  une fois par commande, état sérieux 160, santé sous 1 (176, remplace
  « YOU ARE VERY WEAK »), noyade 177 ; sommeil forcé (message 178) d'un
  joueur épuisé : REST de `180 + INT(RND × 300)` minutes sans saisie.
- Infection (coupures actives depuis 6 h) et malaria (régions 3 à 5) de
  T0B/S07, avec le générateur natif, derrière `disease_triggers`.
- `tests/test_care.py --original` : 957 cas ROM de plus (aiguillages WET/DRY,
  DRY/COOL/CUT/HANG, USE, placements, alertes, sommeil forcé, 528 tirages
  d'infection et de malaria) ; `tools/re_event_scan.py` (producteurs et
  consommateur des conditions). `test_reference_state.py` inchangé et vert.
- Mémoire : WILDLO 1 718 → 141 octets libres, WILDMVI 878 → 1 809 octets,
  SIM 573 → 265 libres ; volume 261 → 266 blocs. Les disques à carte native
  sont à 278–280 blocs sur 280 : `test_geo_resident.py` vérifie le décodage
  des tuiles brutes sur une carte plus légère (2 tuiles de bruit).

### Neowilderness : feu, lumière et eau (lot 2 de fidélité)

- Feu de l'original (T11/S00) : `USE MATCHES` (une allumette sur 24),
  `USE FUEL`, `USE GLASS` (soleil à 30°), `MAKE FIRE` avec ses refus (eau,
  sol rocheux enneigé, sans allumage, pluie ou vent de 41 mph sans
  combustible), 30 minutes d'effort, `USE FIRE` (+25 °F dans la thermique,
  127 °F quand l'octet déborde, comme la ROM), `DOUSE FIRE`, `MAKE STICKS` ;
  `WALK` et `SWIM` refusés tant que le feu brûle (« SMOKEY THE BEAR… »).
- Lumière (`$0D5D`) recalculée à chaque pas de santé ; `USE FIRSTAID KIT`
  refusé sans lumière ; `USE FLASHLIGHT` dépense une utilisation des piles.
- Eau (T0F/S00) : `GET RAIN`, `GET SNOW`, `GET ICE`, rivière ou lac
  (160 oz non traitées), cactus, recherche chronométrée, `MAKE WATER` par
  condensation, gourde de deux quarts, contamination durable de la gourde,
  `BOIL WATER` (ustensiles, réchaud ou feu), `DRINK` limité à 0,2 × poids,
  giardiase quand RND ≤ 2 / altitude en centaines de pieds (au lieu d'une
  chance sur huit) ; FILL/REFILL sans 10 minutes.
- Textes de l'original ; grille : `MAKE`, `BOIL`, `DOUSE` (feu allumé),
  objets de camp et `FIRE` dans `USE`. Module CAMP (1 617 octets) à la place
  de WATER ([CAMP.md](docs/CAMP.md), `tests/test_camp.py`,
  `tools/re_camp_probe.py`).

### Neowilderness : MAP de marche, ne dessiner que ce qui change

- Pendant WALK/SWIM, la fenêtre de MAP reste fixe au lieu d'être
  recentrée à chaque demi-pas : un demi-pas ne réécrit que la case quittée,
  la case de P et les caractères changés de l'étiquette (7 écritures au
  lieu de ~300 sur la carte réelle). La fenêtre avance d'un quart (10 × 6
  cases, bornée à la grille) quand P arrive à 4 cases d'un bord : un seul
  dessin complet, différentiel. Centrage unique si P est hors de la
  fenêtre au départ ; MAP, C et flèches inchangés. SITES +270 octets
  (424 libres), BSS +5 (partie sauvée inchangée), GCODE +5 ([IMPLEMENTATION.md](docs/IMPLEMENTATION.md)
  « MAP plein écran 80 × 24 », `tests/test_walk.py`,
  `tests/test_sites.py` `full_screen`).

### Neowilderness : SAVE et RESTORE, cinq parties (lot 9)

- `SAVE` et `RESTORE` (jusqu'ici « NOT IN THIS VERSION YET ») gardent cinq
  parties, comme l'original : numéro demandé par l'invite numérique ou
  tapé à la suite (`SAVE 2`), question avant d'écraser une partie occupée
  (région et heures), refus d'une autre région (`GAME 1: SIERRA NEVADA
  ONLY.`), d'une autre construction, d'une partie vide ou abîmée
  (Fletcher-16), disque protégé et fichier absent signalés ; aucun refus
  ne change la partie ([SAVE.md](docs/SAVE.md)).
- Une partie = 32 octets d'en-tête versionné + 1 392 octets d'état
  (GDATA sans le cache des modules, la ligne tapée ni les tables
  constantes ; objets au sol ; en-tête de carte ; espèce nommée), inventaire
  établi par balayage des écritures et comparaisons de mémoire ; RESTORE
  redessine la vue (humeur, étoiles, scène), remet le menu à sa première
  case et la suite de la partie est identique octet pour octet.
- Code dans un module lu à la commande, `NEOWILD.SAV` (1 218 octets, fenêtre
  SIM, tampon d'E/S `$AB00`, bitmap `$96-$AF` libéré puis remis) ; relais
  résident de 237 octets (WILDLO), +6 octets de tables de verbes, +13 dans
  INPUT. Fichiers `NEOWILD.S1`…`S5` de longueur fixe créés à la
  construction : ni CREATE ni allocation. SAVE : 8 appels MLI, ≈ 4,5 s ;
  RESTORE : 6 appels, 6 à 9 s avec le redessin. Volume : 24 blocs, 4 libres.
- `DISK_BLOCKS=1600` / `make disk800` : le volume sur 800 Ko ; démarré et
  essayé (SAVE, RESTORE) dans POM2 sur sa carte SmartPort, hors de portée
  d'a2shot (Disk II seulement) : l'image livrée reste de 140 Ko.
- Tests : `tests/test_save.py` (partie de nuit, continuation identique,
  vue identique, autre région, redémarrage, fichier relu après éjection,
  défauts, WOZ protégé, gardes ProDOS), `tests/test_resident.py` (SAVE et
  RESTORE, seules commandes autorisées à appeler le MLI),
  `tests/test_prodos.py` et `tests/test_pack_boot.py` (catalogue).

### Neowilderness : LOOK UP / LOOK DOWN, flèches haut et bas

- `LOOK U`/`UP`, `LOOK D`/`DOWN`, `LOOK F`/`AHEAD`/`FORWARD`, `PAN` et
  `SCAN U`/`D` : trois angles de vue comme l'original (octet `$E7` de
  SURV3D, sondé) : LOOK fixe l'angle, PAN avance d'un cran et s'arrête au
  bout, PAN AHEAD ne fait rien ; aucun temps de jeu ; l'angle persiste à
  travers LOOK L/R/N/AZ, VIEW, STATUS, REST ; WALK, SWIM et LOOK B le
  remettent à niveau ; rien ne change dans la cabane ; « NOT NOW. » refuse
  de regarder en bas devant un animal debout au contact (l'ours en Sierra,
  règle de l'original par région et espèce).
- Rendu : chaque ligne projetée descend (haut) ou monte (bas) de 96 lignes,
  mesure sur l'original (le plan prévoyait 64 vers le bas) : relief, ciel en
  zones, soleil et Lune (un astre jusqu'à 76° de hauteur devient visible en
  regardant en l'air), étoiles, panneaux lointains, pieds des arbres ; en
  l'air, ni sprite ni arbre ; vers le bas, l'épave et les sprites locaux
  restent à leur place (l'original les montre là). 96 lignes = 512 unités de
  pente : `tilt_row` projette `tinc − 512 × tilt` avec les tables à niveau,
  sans toucher à la boucle des rayons (vue à niveau identique au bit près,
  +0,2 à +0,9 % de cycles). Oracles `view_ref`, `forest_ref`, `scene_ref`,
  `dhgr_ref`, `stars_ref` avec `tilt` ; `tests/test_tilt.py` (six cartes ×
  trois angles au bit près, arbres, panneau lointain, soleil à 68°,
  commandes, refus, rangées 176-191 des six régions), banc des étoiles à
  trois angles, scénario `look_tilt` de `test_adventure.py --original`
  (angle du port = `$E7` à chaque pas, horloge inchangée) ;
  `tools/re_tilt_probe.py` ([LOOK_UPDOWN.md](docs/LOOK_UPDOWN.md)).
- Grille : `UP` et `DOWN` dans la liste de LOOK. Ligne tapée : **flèche
  haut = STATUS, flèche bas = grille** (TAB reste un alias) ;
  [MENUS.md](docs/MENUS.md) § 4, `tests/test_menu_bar.py`.
- `tests/test_sim.py` « Night view » : le test supposait l'horizon en 95 ;
  le ciel descend jusqu'au dernier échantillon visible (règle de l'original
  et de l'oracle), que le brouillard du port rapproche (visibilité 24 :
  11 pas, ligne 104). Le test calcule désormais cette limite.

### Neowilderness : MAP plein écran 80 × 24

- MAP, et la carte animée de WALK/SWIM, occupent tout l'écran texte
  80 colonnes : 40 × 24 cases au lieu de 32 × 14 ; une étiquette en
  inverse au début de la rangée 0 garde case, cap magnétique, site sous P
  et, pendant la marche, les minutes (qui remplacent `TRAVELLING: # MIN.`) ;
  défilement par quart de fenêtre ; rangées 20 à 23 effacées à la fin de
  la marche, grille rendue au prompt ; SITES 299 octets plus court
  ([IMPLEMENTATION.md](docs/IMPLEMENTATION.md) « MAP plein écran 80 × 24 »,
  `tests/test_sites.py` `full_screen`).

### Neowilderness : intégrité du volume après le hall of fame

- Rapport POM2 du 13 octobre 2026 : après un voyage Sierra, l'EOF de
  `NEOWILD.DAT` dans le répertoire (bloc 2, octet `$41`, `$BC` → `$3F`)
  bloquait le démarrage suivant sur `NEOWILD DISK ERROR $4C`. ProDOS
  réécrit l'entrée d'un fichier ouvert avec le droit d'écriture depuis son
  FCB quand celui-ci est marqué modifié : un FCB de `NEOWILD.DAT` faussé
  donne exactement cet octet (injection a2shot). L'écriture parasite
  elle-même n'a pas été reproduite (a2shot et POM2 avec le profil de
  l'utilisateur). Correctif : tous les fichiers du volume sauf
  `NEOWILD.HOF` sont verrouillés (accès `$01`, `tools/build_disk.py`
  `lock_files`) ; ProDOS ne peut plus réécrire leurs entrées
  ([HOF.md](docs/HOF.md) § 10).
- Score : la région et le genre de voyage étaient lus en `MAP+32` et
  `MAP+33`, que le balayage des aliments sauvages réécrit à chaque marche ;
  un voyage de scénario devenait « FREE JOURNEY: NOT RANKED » dès la
  première marche. Le module lit `region_number` et `journey_kind` (nouvel
  octet résident écrit par le chargeur).
- `tests/test_hof_volume.py` (dans `make test`) : droits du volume, FCB
  faussé au CLOSE du chargeur, vrai voyage puis comparaison du volume
  entier après éjection, garde contre toute écriture du jeu dans la
  mémoire de ProDOS de QUIT au menu suivant. `ld_close` (chargeur)
  exporté pour les tests.
- a2shot : étape `storewatch:LO:HI` / `unstorewatch` (chaque écriture du
  processeur dans la plage, avec l'état carte langage, ALTZP, RAMRD,
  RAMWRT), compatible avec les scripts existants.

### Neowilderness : préparation du voyage et niveaux (lot 1 de fidélité)

- `P` au menu (« P PREPARATION     QUESTIONS, NOT RANKED ») : région, niveau,
  puis les questions de GO1/GO3 (date et heure choisies ou tirées, jeu
  normal ou mode recherche, sexe, poids 50–350 lb, carrure, taille, âge,
  pouls, fréquences de la faune et des orages) et le verdict de forme de
  GO2 ; poids, métabolisme `w/100`, repas `+0,004 w`, Hmax et santé, surface
  thermique Q, facteur de surpoids ; mode recherche : corps de l'original
  (175 lb), instruments à l'épave, aucune blessure. Voyage non classé.
- Tout voyage autre qu'un scénario au niveau 4 (`NEOWILD.PRE`, 5 005 octets,
  3 702 compressés, décodés à `$2000`, aucun octet résident en RAM principale ;
  volume 260/280 blocs) : date et heure tirées autour de
  l'été selon le niveau, phase de l'onde de température, blessure du crash
  `⌊0,45 RND L − 0,3⌋`, lot de l'épave en neuf groupes, usages ×1/√L,
  premier front `3000/(L F) + 20`, sa durée, le vent ; mots de
  l'introduction (terrain, difficulté, heure, blessure). Formules vérifiées
  octet pour octet contre l'original avec un RND imposé
  (`tools/re_prepare_probe.py`, `tests/test_prepare.py --original`, onze cas).
- RETURN, RETURN : premier voyage figé inchangé (`test_reference_state.py`).

### Neowilderness : les quatre lignes du bas, surface de commande (lot 8, étape 2)

- Rangées 20 à 23, colonnes 0 à 37 : grille des verbes (contextuels en
  tête : `EXIT`, `ENTER`, `IGNORE SCARE ATTACK` ; un verbe sans objet à
  nommer, `USE` sans médicament, `DRINK` sans eau accessible, n'est pas
  proposé), six cases par rangée sur quatre rangées, défilement par rangée
  au-delà (`^`/`V` en colonne 38), case choisie en inverse ; RETURN, flèche
  haut ou TAB l'ouvre, TAB la referme, flèches, RETURN, Échap ; un verbe
  ouvre sa liste
  (durées, directions, objets accessibles ici en cases de 12, onces) et
  compose la commande du clavier dans `inbuf` (`menu_noun` transmet l'objet
  choisi : `GET COTTN SOCKS`). Flèche bas sur la ligne vide : STATUS. Une
  commande issue de la grille la laisse ouverte. Les commandes tapées
  restent acceptées ([MENUS.md](docs/MENUS.md) § 4, `tests/test_menu_bar.py`).
- Colonnes 40 à 78, les descriptions : le dernier message, placé mot par
  mot sur quatre rangées (plus de texte coupé ni de rangées collées) ; sur
  la dernière rangée, quand le message la laisse libre, la ligne de stock
  `FOOD n OZ  WATER n OZ  HERE f/w`, ou `> ` et la commande telle que
  l'analyseur la lira pendant qu'elle est tapée ou composée (sans curseur) ;
  le rapport de charge y tient.
- Message de départ sans la liste des commandes (la grille les montre) ;
  `src/menu.s` résident en `$BA00` (842 octets), grille de 1 474 octets
  dormant dans les lignes HGR 176-191 et recopiée en `$B000` à chaque invite
  ([MEMORY.md](docs/MEMORY.md) § 11) ; le chargeur lit avec son propre
  tampon `$AB00`. Volume 250/280 blocs.
- Menu des scénarios : Sierra Nevada en première ligne (touche 1), RETURN
  seul la choisit (`CHOICE (RETURN = 1, 1-7, H, Q)?`), ordre de
  `tools/genmenu.py` `MENU_ORDER` ; l'écran H suit le même ordre ; les
  tests répondent par `menu_keys` (numéro de région traduit).
- Page de chargement : une ligne vide sous le titre.

### Neowilderness : page de chargement et menu allégés

- Page de chargement : titre, machine, auteurs, le but en deux lignes et
  « HELP LISTS THE COMMANDS. » ; les onze lignes de commandes sont parties
  (HELP les donne en jeu).
- Menu des scénarios : une ligne par région (numéro, nom, terrain et
  température, meilleur score en colonne `BEST`) au lieu de trois ; plus de
  phrase de faune ni de limite des neiges, plus d'astérisque ; `7 FREE
  JOURNEY`, `H HALL OF FAME`, `Q QUIT TO PRODOS` sur deux lignes ; invites
  sur la ligne 12 (`MENU_ROW`). `hm_best` écrit le score à la colonne 35
  de la ligne du scénario.

### Neowilderness : constellations entières et nuit noire

- Catalogue **par figures** : 42 constellations complètes (262 étoiles,
  jusqu'à V 4,95 : bol de la Petite Ourse, Hyades, Gémeaux, Faucille, Lyre,
  Clé de voûte, Couronne boréale…) ; les 44 étoiles ajoutées remplacent les
  44 étoiles isolées les plus faibles (toujours 282 étoiles, 846 octets).
- Classe de sélection = figure (classe 0 : figures et V < 2,0 ; 1 et 2 :
  remplissage) : la pleine Lune montre les figures entières ; une liste
  pleine perd le remplissage d'abord ; indice comparé sur 16 bits.
- Magnitude dans le pixel : trois rangées pour la première grandeur (deux
  entrées), deux rangées teintées sous V 3,0, une rangée grise au-delà.
- Projection comprimée au-dessus de 45° (égale en sin h jusqu'à 86°) : la
  Grande Ourse et Cassiopée restent visibles à leur culmination ; la Lune
  garde sa perspective.
- Ciel **bleu foncé** en nuit noire : la crête se découpe en silhouette.
- Les rotations **défilent en nuit noire** comme le jour (`turn_view` ne
  redessine plus la vue entière) : 35 colonnes par pas de 22,5°.
- Module 2 367 octets (+30), `SKYRES` 482 (tables en WILDLO) ; référence,
  banc IIe, tests en jeu et [STARS.md](docs/STARS.md) § 14 à jour.

### Neowilderness : bandeau réorganisé

- Panneau gauche : `HEALTH 100%` seul en haut, l'alerte ou l'indication
  (SHIVERING, ITEMS: INV, TOPO / HELP…) en dessous. Panneau droit : l'heure
  (ou la période sans montre) suivie du jour du séjour (`7:00 DAY 1` ; jour
  de l'année de STATUS moins 125, plus 365 au passage de l'an) en haut, le
  besoin le plus pressant en dessous (`HUNGER OKAY`, `THIRST SO-SO` : celui
  des deux qui va le plus mal, la faim à égalité ; l'autre reste dans
  STATUS). Le panneau droit commence 4 pixels après le ruban (`UI_GAP`).
- Module `wildhud.bin` : 1 941 → 2 021 octets (80 de moins dans le stock de chaque région) ; `tools/dhgr_ui.py` (largeur
  par panneau), `test_interface.py`, `test_clock.py` (jour du séjour, dont
  le passage de l'an) mis à jour.

### Neowilderness : intégration de la branche parallèle

Une seconde implémentation du port (branche `worktree-neowilderness-lot4`,
même base, 78 conflits textuels) a été relue ; ses apports sont
transplantés à la main, sans fusion ([IMPLEMENTATION.md](docs/IMPLEMENTATION.md)
« Intégration de la branche parallèle »).

- **Géographie fine résidente** (lot 5 de la branche, `9795a58`) : sur une
  carte native (comparaison Sierra, `mkmap.py --native`), un atlas
  `coarse` de 154 tuiles 16 × 16 (Sierra 6 379 octets, carte générée
  6 113) et son décodeur `src/geoaux.s` (843 octets) sont chargés par
  `NEOWILD.R2` en carte langage auxiliaire (vue banque 1) ; 4 tuiles en
  cache ; 203 cycles par requête, ≤ 46,5 ms par décodage ; partie Sierra
  vers les rangers : 53 commandes, 14 décodages, aucun appel MLI.
  `NEOWILD.GEO` et `geo_load` disparaissent.
- **Verdict mémoire** ([GEOGRAPHY.md](docs/GEOGRAPHY.md) § 9) : l'atlas ne
  tient pas dans le stock de modules (≤ 1,75 Ko libres par région) ; il
  partage la zone de l'instantané TOPO selon la carte : les six régions
  livrées (cartes héritées) gardent l'instantané (retour 0,24 s), une
  carte native prend l'atlas et TOPO redessine la vue (6,1 s). Rien n'est
  retiré aux étoiles, aux régions ni au hall of fame. Une carte native,
  inconstructible avant (97 blocs de `NEOWILD.GEO` en plus des paquets),
  tient en 260/280 blocs ; `make test-original` (`test_adventure.py
  --scenario all`, 83 points, 0 écart) redevient jouable.
- Mémoire ([MEMORY.md](docs/MEMORY.md) § 9.10) : RAM principale résidente
  libre 181 → **361 octets** ; stock auxiliaire +12 octets par région
  (Burma 278) ; disque livré inchangé, 247/280 blocs.
- Tests ajoutés à `make test` : `test_journey_resident` (crash → rangers
  au clavier, zéro MLI, copies RAM, pile, nouveau jour, soins, nage, puis
  hall of fame après la touche de fin ; rejoué en carte native),
  `test_screen_returns` (neuf retours d'écran identiques, modules exacts),
  `test_geo_resident`, `test_geo_atlas` ; `test_prodos` vérifie page zéro,
  bitmap et vecteur RESET au QUIT final ; `test_resident` et
  `test_graphical_topo` rejouent sur une carte native ; `test_walk`,
  `test_interface` et `test_weather_front` reprennent les corrections de
  la branche (lecture par étiquette de `weather_day_level`).
- Outils : `mkmap.py --fine/--native`, `inspect_disk.py` (zone de
  géographie), `profile_actions.py` (requêtes et décodages),
  `profile_loading.py --map` ; `build_disk.py` paquette en `lz` par défaut,
  comme le Makefile.
- Écartés : bandeau, TOPO et repère P du joueur de la branche (`main` a
  les siens et suit l'original), rebaselines et README de la branche
  (autre architecture).

### Neowilderness : ciel plus peuplé (lot 7)

- Catalogue de **282 étoiles jusqu'à V = 3,50** (79 Hipparcos inchangées +
  203 du *Bright Star Catalogue* 5ᵉ éd., CDS V/50 ; T CrB et Mira écartées),
  3 octets par étoile (classe déduite de l'indice, ascension droite en
  quarts d'unité de vue) ; liste visible de **160** entrées de 2 octets en
  36 seaux de 16 unités ([STARS.md](docs/STARS.md) § 13).
- Module horaire dans la fenêtre SIM (`$97CE`) avec la tête du catalogue
  (entrée 24 du répertoire, 462 octets, au trou de la carte auxiliaire) ;
  quarts de carrés, produits de l'heure et table des lignes en BSS ; liste
  et tracé en banque 2 de la carte principale (`$DE18-$DFFE`).
- Étoiles dessinées dans les captures `game_stars_*` : Sierra nord 2 → 10,
  Sierra sud 7 → 31, Bolivia 10 → 37 ; pleine Lune inchangée (2 : Antares,
  Spica, règle de la première grandeur conservée).
- Coûts : calcul horaire 0,33–0,34 s en jeu (0,38 s au pire cas du banc ;
  avant 0,17–0,21 s), tracé 1,4–1,5 % d'une vue de nuit noire.
- Mémoire : RAM principale libre 86 → 181 octets ; stock de modules −1 047
  octets par région (Burma 266, Sierra 1 510 ; MEMORY.md § 9.9) ; volume
  247/280 blocs.

### Neowilderness : étoiles, score et hall of fame (lot 7, étapes 5–6)

- Étoiles de nuit en jeu ([STARS.md](docs/STARS.md)) : module horaire
  `wildsky.bin` (ID 25, 1 984 octets) recalculé à la première vue de nuit
  après chaque `sky_position` (`stars_stale`) ; liste de 32 étoiles en
  WILDLO ; tracé par colonne (`stars_frame`, `stars_column`) **exécuté dans
  la banque 2 de la carte langage principale** (`$DF00`) ; Polaris en
  Sierra, Croix du Sud en Bolivia. Aucune étoile de jour, au crépuscule ni
  sous les nuages ; première grandeur sous la pleine Lune ; toutes en nuit
  noire. Rotations : seules les colonnes révélées sont retracées.
- Mémoire : ProDOS 8 ne garde que son code QUIT (`$D100-$D3FF`) dans la
  banque 2 principale (mesuré) ; `$D400-$DEFF` rejoint le stock de modules
  (nouvelle source de `mem_fetch`, bit 5 du type d'enregistrement du
  chargeur) et `$DF00` reçoit le code de tracé. RAM auxiliaire libre :
  1 313 octets avec Burma (pire cas), 2 557 avec la Sierra ; RAM principale
  86 octets (`docs/MEMORY.md` § 9.7, § 9.9).
- Coûts mesurés : +1,6 à 1,9 % par vue de nuit noire, 0,1 % de jour,
  0,17 à 0,21 s par heure de jeu la nuit (`BASELINE_DHGR.json`,
  `lot7_stars`).
- Score et hall of fame ([HOF.md](docs/HOF.md)) : correctif
  `docs/hof_integration.diff` appliqué. Toute fin (mort, arrivée, QUIT puis
  Y) lit `NEOWILD.END` (module `wildhof.bin`, 3 044 octets, `$9600`) :
  bilan, score, saisie du nom, écriture de `NEOWILD.HOF` (un bloc, réécrit
  en place), puis retour au menu ; le menu affiche les `BEST` lus dans le
  fichier et l'écran `H` les six tables. Le voyage libre n'est jamais
  classé, un score nul non plus.
- Volume : paquetage `lz` par défaut (`BOOT_PACKING`) : 246/280 blocs,
  **34 libres** (11 avec `auto`) ; choix → première vue 9,2 à 9,8 s, menu à
  23,3 s de la mise sous tension.
- Tests : `test_stars_game.py` (liste résidente et vues contre
  `stars_ref`/`dhgr_ref`, Polaris, nuages, midi, pleine Lune, rotations,
  zéro MLI), `test_stars_ref.py` et `make -f stars.mk test`,
  `test_hof_game.py` et `make -f hof.mk test` dans `make test` ;
  `dhgr_ref.Sky(stars=...)` ; `test_sky.py`, `test_moonlight.py` et
  `test_sprites.py` (les vues de nuit comparées contiennent les étoiles),
  `test_prodos.py` (une touche à `hof_key_wait` après QUIT, neuf flèches dans
  Bitsy Bye), `test_menu.py` (hall of fame vide, six `BEST -`),
  `test_pack_boot.py` (`NEOWILD.END`, `NEOWILD.HOF`, carte principale),
  `test_boot.py` (source 3, contenu de la banque 2 principale à côté du
  code QUIT de ProDOS). Captures `build/dhgr/game_stars_*.png`
  (`tools/game_shots.py --stars`).
- Lot 8 : exigence notée dans [MENUS.md](docs/MENUS.md) § 4 — le contrôle
  au joystick devra exploiter bien mieux les quatre lignes de texte 80
  colonnes.

### Neowilderness : faune, couleurs et textes par région (lot 7, étape 4)

- Quatre espèces chargées : le balayage de TRAVEL lit les taux et filtres
  des quatre fiches du paquet (`fauna_travel`), OUTDOOR ses seuils de
  réaction, noms et drapeaux (`fauna_reactions`), PROJECT les tailles des
  sprites (`proj_sprites`) ; quatrième espèce de Burma et Bolivia
  (module 23) ; ordre des tirages inchangé (`docs/logic/animals.md`).
- Palettes par région (`dhgr_palette.REGIONS` : sol, neige, eau, couronnes
  par humeur ; ciel et nuit inchangés) et couleurs des 15 nouveaux animaux,
  tables `dhgr_tables_rN.bin` chargées par le paquet ([DHGR.md](docs/DHGR.md)
  § 12).
- Textes : message de départ avec la région et sa faune, noms des espèces
  dans les réactions (« THE TIGER INJURES YOU AND STAYS. »).
- **Cause d'arrêt nommée** : une marche, une nage, un repos ou une attente
  interrompus ne disent plus « A DISCOVERY INTERRUPTS YOUR ACTION. » mais
  ce qui est arrivé : l'espèce de la région (« BEAR IN YOUR AREA! »), la
  ressource trouvée (« YOU FIND FISH. », gibier, insectes, fruits, cactus,
  champignons, plantes, noix) ou l'abri naturel (« YOU FIND SHELTER. »)
  (`module_fauna_cause`, PROJECT ; `test_feedback.py`).
- Mémoire : −131 octets auxiliaires par région (tables de faune −69, cause
  nommée +200) ; volume 246/280 blocs (`docs/MEMORY.md` § 9.6).
- Tests : `test_fauna.py` (cas de filtre des cinq autres régions,
  quatrième espèce, pacotilles), `test_dhgr_mood.py` (humeurs des six
  régions), `test_menu.py` (textes, correctifs, couleurs, chaque espèce
  dessinée), `test_feedback.py` (causes nommées). Captures
  `build/dhgr/game_region_rN_*.png` (`tools/game_shots.py --regions`).

### Neowilderness : paquets de région et menu de démarrage (lot 7, étapes 2–3)

- `NEOWILD.DAT` devient un tronc commun ; six paquets `NEOWILD.R1`…`R6`
  (15 à 18 blocs) portent la carte, les bois, les 2 à 4 sprites d'animaux
  (module 23 pour la quatrième espèce), les fiches animales de l'en-tête de
  région (dans l'image auxiliaire de SITES), les tables DHGR, les textes de
  région (`$5780-$57FF`) et le répertoire des modules ; un seul est lu.
  Épave et cabane restent communes. Volume : 37 blocs libres.
- Menu de démarrage dans `NEOWILD.SYSTEM` après le tronc : six scénarios
  (nom, terrain, climat, faune, meilleur score « - »), voyage libre (région,
  niveau, hasard renouvelé ; `MAP+33` = 1), hall of fame en attente, ProDOS ;
  niveau 1–10 (RETURN = 4, écrit en `MAP+22`). L'introduction revient avec
  la région pendant la lecture du paquet. Choix → première vue : 9,5 à
  10,2 s ; menu à 21,4 s de la mise sous tension.
- Fin de partie (QUIT, mort, arrivée) : retour au menu par relance de
  `NEOWILD.SYSTEM` après restauration du système, sans état conservé.
- Répertoire des modules : 26 entrées (23 quatrième espèce, 24 hall of fame,
  25 étoiles) ; géographie fine native aux IDs 32–55. Longitude de carte
  bornée à ±127 (New Guinea).
- RAM auxiliaire libre : 676 octets avec Burma, 1 920 avec la Sierra ; le
  module des étoiles (1 984) n'y tient pas encore (`docs/MEMORY.md` § 9.3).
  RAM principale : 340 octets libres.
- Tests : `test_menu.py` (six scénarios au clavier, voyage libre, niveau,
  `H`, `Q`), `test_boot`, `test_prodos` (retour au menu), `test_pack_boot`,
  `test_transfers`, `test_transitions` adaptés ; `common.py` répond au menu
  (`MENU_SKIP`). Outils de profil adaptés ; `tools/genmenu.py`.

### Neowilderness : plan des scénarios (lot 7)

- Relevé du 13 octobre 2026 : les six régions originales sont déjà sur les
  disques Apple II (en-têtes piste 0, secteurs 9–14 ; 27 sprites sur la
  Journey) ; la version MS-DOS ne sert qu’à la vérification croisée.
- Plan du lot 7 dans [SCENARIOS.md](docs/SCENARIOS.md) : menu de démarrage,
  paquets de région chargés sélectivement, étoiles dessinées la nuit, score
  par scénario, hall of fame.

### Neowilderness : interface DHGR, texte 80 colonnes et TOPO en RAM (lot 4)

- Bandeau natif DHGR, dessiné par octets entiers (`dhgr_pack`) : ruban de
  boussole bleu foncé, repères et graduations blancs, pointeur jaune
  (bande de 140 colonnes, 4 unités d'azimut par pixel) ; panneaux de survie
  noirs dans une police DHGR de 7 rangées (`tools/dhgr_font.py`) : libellés
  gris, valeurs aqua/jaunes, avertissements blanc sur bande rouge au lieu de
  l'inverse HGR, indications bleu clair. Plus de pixels HGR doublés ni de
  franges ; mêmes informations et mêmes règles d'alerte.
- Les quatre lignes de messages, le rideau de la simulation et MAP sont en
  vrai texte 80 colonnes (primitives du jeu en `$0200-$03CF`, page libre de
  ProDOS et du Moniteur pendant la partie) ; une ligne accepte 79 caractères.
  STATUS, INVENTORY, HELP et la fin restent en 40 colonnes. MAP : deux
  caractères par cellule, sites et joueur en inverse.
- TOPO calculée à l'ouverture depuis la carte résidente (TOPOGEN,
  `src/topo_dhgr.s`, fenêtre SIM) : teintes hypsométriques, courbes de
  400 ft et maîtresses de 2 000 ft, eau, rives, bois, repères, flèche et
  échelle ; identique au bit près à `tools/topo_dhgr_ref.py`
  (`docs/TOPO_DHGR.md`). L'image TOPO de 8 Ko et `graphical_topo.py`
  quittent le volume.
- Retours d'écrans sans lancer de rayons : instantané de la vue en carte
  langage auxiliaire sous TOPO (retour 0,24 s au lieu d'un rendu complet),
  INVENTORY sans rideau (retour 6,1 → 0,26 s) ; STATUS, HELP et MAP
  inchangés (6 ms). Aucune lecture disque, aucune avance du temps.
- Nom : introduction « NEOWILDERNESS » (titre inverse), aide
  « NEOWILDERNESS - HELP ».
- Mémoire (`docs/MEMORY.md` § 8) : 528 octets libres en RAM principale
  (128 au lot 3) ; stock auxiliaire 40 246 octets, 1 738 libres, 12 800
  réservés à l'instantané ; `NEOWILD.DAT` 53 847 octets, 125 blocs libres.
- Mesures contre le lot 3 (`docs/BASELINE_DHGR.json`, clé `lot4`) : VIEW
  −0,3 %, LOOK R +0,4 %, LOOK B +0,5 %, rotations +0,8/+1,5 %, STATUS
  +1,0 %, WALK 1 H +3,2 % (MAP et messages en 80 colonnes) ; TOPO 2,99 s
  à l'ouverture, 0,24 s au retour ; états identiques.
- Tests : `common.py` lit les deux pages texte et `RD80VID`
  (`text_screen` en 80 colonnes, `map_rows`, `text_writes`,
  `text_changes`) ; `test_hud` contre le ruban natif ; `test_interface` et
  `test_clock` par `tools/dhgr_ui.py` ; `test_graphical_topo` contre la
  référence TOPO ; `test_reference_state` exclut les compteurs de
  chargement de modules. Captures `build/dhgr/game_ui_*.png`.

### Neowilderness : paysage DHGR (lot 3)

- Le paysage est dessiné en DHGR 16 couleurs sur une page unique
  (`$2000-$3FFF` principale et auxiliaire, `80STORE`, banque choisie par
  `PAGE2`) : même projection, mêmes 140 rayons, un rayon par pixel couleur.
- Dix humeurs choisies à chaque trame (`select_mood`) d'après `sun_alt8`,
  `moon_alt8` et `moon_phase` (nouveaux, calculés à chaque heure par
  `sky_position` en entiers) et les nuages : ciel en cinq zones tramées,
  sol, neige et eau en trois paliers de distance, bois tramés, soleil
  coloré, Lune blanche ou jaune pâle, sprites originaux colorés et ombrés.
- Nuit : la règle HGR (`view_dark`, seul le disque plein éclaire) est
  conservée pour le jeu ; la lumière de la pleine Lune est graduée (haute,
  basse, voilée, sous l'horizon).
- Passes en lecture-modification-écriture par colonne, deux registres OR
  pour les lignes paires/impaires : la trame ne coûte rien ; damier ancré
  à l'azimut pour des rotations exactes. Défilement et effacement par bandes
  de huit lignes, dans les deux banques.
- Bandeau de boussole et panneaux de survie : dessins HGR, pixels doublés,
  index jaune. TOPO reste en HGR simple ; STATUS, INVENTORY, HELP et MAP en
  texte 40 colonnes ; les quatre lignes de messages en cellules 80 colonnes,
  imprimées par des primitives 40 colonnes propres au jeu (le Moniteur
  bascule en 80 colonnes dès que `80COL` est actif).
- Mémoire : le code HGR retiré (≈ 2,4 Ko) paie le code DHGR ; 128 octets
  restent libres en RAM principale, la RAM auxiliaire est inchangée ;
  `NEOWILD.DAT` 53 031 octets, 127 blocs libres. Double tampon impossible
  (16 Ko demandés), mesures dans `docs/MEMORY.md`.
- Mesures à 1 MHz contre HGR 128 Ko (`docs/BASELINE_DHGR.json`) : VIEW
  +3,6 %, LOOK R +4,3 %, LOOK B +3,0 %, rotations +4,6/+5,4 %, WALK 1 H
  +2,2 %, STATUS inchangé ; états identiques à la référence HGR.
- Tests : toutes les comparaisons d'images lisent les deux banques et
  suivent `tools/dhgr_ref.py` dans l'humeur relevée ; `tools/view_ref.columns`
  et `tools/forest_ref.py` fournissent les événements de bande et les
  houppiers ; nouveaux `test_dhgr_mood.py` et `test_dhgr_video.py` ;
  captures `tools/game_shots.py` → `build/dhgr/game_*.png`.

### Neowilderness : ProDOS 8, 128 Ko et modules en RAM (lots 1–2)

- Synchronisation avec la tête de `../wilderness` (transitions texte/HGR,
  introduction conservée pendant le chargement, SIM chargé avant les sondes
  de rive de SWIM, attentes de tests mises à jour).
- Volume ProDOS `dist/NEOWILDERNESS.po` (280 blocs, 132 libres) :
  `NEOWILD.SYSTEM` vérifie IIe enhanced/IIc 128 Ko, garde l'introduction,
  prend la mémoire auxiliaire (`dev/lib/prodos/video.s`, /RAM effacé
  seulement s'il est vide ou après Y) et lit `NEOWILD.DAT` en 17 appels MLI.
  Compression choisie par mesure : premier écran jouable 45,1 → 28,9 s.
- Tous les modules, la simulation vierge et TOPO préchargés en RAM
  auxiliaire ; `overlay_load` copie l'image vierge (au plus 17,2 cycles par
  octet) ; WILDSIM quitte `$2000-$3FFF` pour `$9600`, réservé à la future
  page DHGR. Plus aucun appel DOS 3.3 ni lecture disque en jeu.
- QUIT et Ctrl-RESET : texte, banques, /RAM reformaté, bitmap, vecteur RESET
  et page zéro rétablis, retour au lanceur ProDOS.
- Compteurs `mli_calls`, `mli_reads`, `mli_bytes`, `xfer_count`,
  `xfer_bytes` ; `overlay_reads` compte les chargements de modules.
- STATUS 8,90 → 0,24 s, LOOK R 7,99 → 1,85 s, WALK 1 H 70,71 → 9,10 s,
  état et image identiques à la référence HGR (`docs/BASELINE_128K.json`).
- Tests : démarrage sur //e, zéro accès disque, transferts, cycle ProDOS,
  comparaison d'état à la référence HGR ; plan mémoire `docs/MEMORY.md`.

### Transitions texte et HGR

- Le texte d’explication HELLO reste affiché pendant la décompression,
  l’initialisation et le premier rendu. DOS ne peut plus faire défiler
  les vingt lignes d’accueil ; le rideau vide commence après cette première vue.

- Le démarrage, VIEW, les changements complets de scène et le retour de TOPO
  masquent le dessin jusqu’à la dernière colonne ; les rotations partielles
  conservent leur défilement progressif.
- Avant un chargement SIM ou TOPO, les vingt lignes supérieures sont nettoyées
  avant la bascule texte. Les anciennes pages STATUS/HELP ne réapparaissent
  plus pendant les calculs ; la commande, les résultats et le curseur restent.
- STATUS, le détail médical, INVENTORY, HELP et le bilan final préparent leur
  première page derrière le paysage. Le clavier révèle la page terminée.
- Les menus partagent les écritures différentielles de MAP, avec effacement
  des fins de ligne, espaces de tabulation et lignes inutilisées. Une page
  identique n’écrit aucun caractère ; une page courte ne garde aucun ancien objet.
- Le retour des menus nettoie les quatre lignes texte avant de montrer HGR.
  La restauration après simulation partage le rendu jour/nuit/cabane et
  préserve les résultats d’action, sans confirmation ni délai supplémentaire.
- L’initialisation vidéo et le cache de projection sont déplacés dans ADV ;
  les données et le retour d’écran inutilisés sont retirés pour tenir en 48 Ko.
- `test_transitions.py` vérifie les captures des étapes intermédiaires,
  la conservation de l’état et les écritures exactes des menus. Les points
  d’arrêt des tests attendent maintenant le clavier après préparation de page.
- Le contrat disque de SLEEP est corrigé à quatorze lectures, mesurées aussi
  sur la référence locale avant ces changements ; les transitions n’en ajoutent pas.

- SWIM charge SIM avant sa première sonde de rive, y compris sans déplacement ;
  lancer ou répéter SWIM sur terre ferme ne saute plus dans la mémoire HGR.
- Les fixtures de parcours, de faune et de poids utilisent le raster, le
  générateur de hasard et les charges natifs déjà présents.

### Premières minutes et aide intégrée

- L’accueil propose INVENTORY, STATUS, TOPO et HELP pour rejoindre les rangers.
- HELP sépare déplacement, équipement et survie en trois pages : exemples
  de commandes, emplacements et avertissement sur DROP des provisions.
- Sélection 1/2/3, navigation circulaire N/Espace/B et retour Échap/Entrée,
  dans le module d’écran de 2 Ko sans modifier les règles de simulation.


### Visibilité à la pleine lune

- Les nuits où le disque lunaire est entièrement éclairé conservent un ciel
  noir, avec relief, arbres, épave, cabane et animaux visibles. Les autres
  phases gardent l'obscurité. Les calculs de survie conservent la nuit.
- Régression indépendante des pixels du terrain et des sprites, sous ciel
  clair ou nuageux ; les bois restent visibles à la pleine lune.

### Direction des sites cohérente avec TOPO

- Projection distante de la cabane et de l’épave : axe nord/sud corrigé
  pour suivre le terrain, la marche et les repères de la carte TOPO.
- Régression indépendante du modèle de projection : huit directions par
  site, repères TOPO lus à l’écran, boussole, pixels visibles devant
  et absence du sprite quand on regarde derrière.


### Réactions animales inspirées du moteur original

- Seuils Sierra de bruit, blessure et combat vérifiés sur ROM : bruit inefficace
  sur le crotale, ours/couguar sensibles au bruit, hache/couteau regroupés comme
  dans le choix d’arme natif.
- Gravité ours/couguar vérifiée sur ROM : coupures, bras/jambe cassés et choc,
  reliés aux courbes de santé et aux soins ; issue supérieure regroupée en choc.
- Tirage de contamination corrigé : l’état évolue à chaque consommation
  d’eau non traitée, sans utiliser le hasard animal.
- SCARE et ATTACK peuvent échouer ; deux tirages de combat permettent une
  défense réussie avec blessure. IGNORE peut laisser l’animal présent.
- Ours/couguar peuvent voler la nourriture exposée : stocks suspendus, eau,
  équipement et piles éloignées conservés ; charge et totaux recalculés.
- Risques de blessure selon la posture vérifiés sur ROM : attente/repos/repas
  au sol, IGNORE et arbre. Grimper n’empêche plus les blessures ; avertissement
  affiché, provisions suspendues conservées et soins possibles dans l’arbre.
- Cabane protectrice pour joueur/provisions ;
  réaction signalée et action interrompue après une heure sans décision.
- Sondes `re_animal_reactions_probe.py`, scénarios clavier
  `test_animal_reactions.py` ; adaptations et limites dans `docs/logic/animals.md`.

### Aventure, ravitaillement et bilan

- `DONE` et distance restante remplacent l’ambigu `GOAL` dans STATUS ;
  distances avec fractions de case, progression bornée et score natif conservé.
- `FILL/REFILL CANTEEN`, berge voisine, capacité 64 OZ, coût 10 minutes et
  refus atomique de surcharge ; contamination de l’eau bue et hasard séparé.
- Réactions SCARE/IGNORE/ATTACK, ciblage par espèce, outils, coupures/morsures
  et attaque après une heure sans réaction ; provisions suspendues et protection par cabane.
  Ces réactions et la contamination sont des règles documentées du port.
- Bandeau pour faible réserve d’eau et réaction à une rencontre ; HELP enrichi.
- Écran d’arrivée/mort dédié : durée, pas, rencontres, santé, provisions et
  score d’efficacité natif, conservé jusqu’à une touche.
- Deux modules disque supplémentaires, WILDADV et WILDOUT ; simulation et
  commandes existantes restent dans leurs fenêtres et le démarrage en deux paquets.
- Palette violet/vert confirmée comme choix du moteur, couleurs des sprites
  et rendu de terrain conservés.


### Réduction des transferts de modules

- Simulation et sprites épave/ours/cabane compressés, décompression LZ
  résidente en place : 32→22, 8→6, 4→2 et 5→3 secteurs de données lus.
- Allocations conservées, longueurs BLOAD réduites : placement des fichiers
  suivants préservé. Petits modules gardés bruts après mesure du coût natif.
- Tables de projection réduites à une table stockée et un cache reconstruit
  au démarrage ; 24 976 octets résidents, paquet de 16 303 octets en deux fichiers.
- LOOK R à 7,26 s ; repos/sommeil presque inchangés à 21,11/22,70 s,
  marche à 26,96 s. La décompression absorbe presque tout le gain disque.
- 20 chargements natifs vérifiés octet par octet, avec texte, page zéro/FAC
  et bornes mémoire conservés ; états et images de six commandes identiques.
- Durées directes 1–255 H/MIN de REST/SLEEP/WALK/SWIM validées en résident ;
  lecteur complet conservé pour saisie au clavier, autres formes et erreurs.
- Une lecture WILDINP évitée : REST 1 H à 21,12 s, SLEEP 8 H à 22,71 s,
  WALK 1 H à 26,95 s ; états et images identiques.
- Deux tables graphiques redondantes retirées (280 octets) pour loger la
  saisie résidente ; coût du rendu supplémentaire de 0,004 s.
- Dictionnaire de compression partagé entre régions voisines : démarrage
  maintenu dans deux fichiers (16 369 octets) ; résident réduit de huit octets.
- 799 durées natives et les 140 paires de pixels vérifiées ; zéro, erreurs,
  annulation, saisie générale, mémoire DOS et restitution intégrale conservés.

### Audit des coûts et copies natives

- Copies LZ du chargeur par index Y ; mise à jour des pointeurs et compteurs
  une fois par séquence. Moteur prêt à 19,42 s ; première invite à 40,91 s.
- Division de pente nulle immédiate ; suppression du double effacement et
  du second bandeau lors de la restauration nocturne extérieure.
- VIEW à 5,62 s ; DRINK nocturne gagne 0,14 s. Résident : 25 261 octets,
  comprimés en 16 276 octets dans deux fichiers ; quatre octets nets ajoutés.
- Profilage des commandes par zone mémoire : DOS absorbe encore 68 % du
  sommeil et 77 % de la marche. États et pixels comparés sans différence.
- 8 256 divisions et 40 copies testées nativement, ainsi que l'effacement
  nocturne unique ; franchissements de page et chevauchements couverts.

### Chargement Disk II

- Compression LZ optimisée par bloc avec prise en compte des drapeaux,
  fenêtre complète de 4 095 octets et suppression des coupures de sortie
  arbitraires à 4 Ko. Décompresseur et mémoire Apple II identiques.
- Démarrage compacté en 16 272 octets dans deux fichiers au lieu de trois ;
  entrelacement de neuf secteurs avec décalage physique d'un secteur entre pistes.
- Arrivée dans le moteur : 23,48 → 20,83 secondes ; première invite :
  45,89 → 43,26. LOOK R : 8,08 → 7,36 ; sommeil de huit heures : 25,83 → 25,30.
- Mesures Disk II corrigées pour arrêter la saisie avant le premier BLOAD.
  1 023 cas de compression comparés à une recherche exhaustive, limites
  de format et fenêtre, intégrité DOS et restitution native vérifiées.

### Parcours mémoire du rendu

- Recherche des arbres arrêtée pour le reste du rayon après sa limite de
  distance ou la sélection d'une couronne ; réactivation au rayon suivant.
- Effacement par lignes contiguës, avec adresses HGR calculées une fois
  par ligne ; bandeau, cache, trous mémoire et colonnes conservées protégés.
- 32 octets de pointeurs redondants supprimés, sans nouveau calcul d'indice
  dans le remplissage déroulé ; résident total réduit de 14 octets.
- VIEW : 6,20 → 5,64 secondes, LOOK R : 8,28 → 8,08, sommeil de huit heures :
  26,39 → 25,83. États et pixels identiques, lectures DOS inchangées.
- Régressions sur chaque octet d'une page HGR, effacements partiels/complets,
  budget de recherche des arbres et réactivation entre les images.

### Vitesse et durée de vie des données en mémoire

- 170 octets d'une table de rendu hors écran récupérés pour LOOK résident
  et les raccourcis d'écran, avec conservation des pixels. VIEW ne recharge
  plus le vocabulaire et le sprite : 12,47 → 6,20 secondes. LOOK R passe
  de 10,43 à 8,28 ; STATUS au départ de 12,27 à 3,76.
- Temporaires astronomiques réutilisant 68 octets du tampon DOS en dehors
  des chargements ; sorties du ciel toujours résidentes. Cache d'isolation
  de cinq octets, invalidé par les vêtements portés ou le mode d'humidité.
- Mesures reproductibles en cycles et lectures avec profile_actions.py,
  comparaison des états et pixels avant/après, 76 transitions thermiques
  et tests de conservation à travers les chargements.
- L'Apple II+ 48 Ko reste la cible ; les routines flottantes et les arrondis
  de la simulation sont conservés. Le sommeil reste proche de 26,4 secondes.

### Bandeau de survie et accès direct aux écrans

- Alertes de danger, faim/soif VERY et santé sous 40 % en vidéo inverse ;
  améliorations en texte normal pour distinguer leur importance sans couleur.
- Indications TOPO/HELP de jour, REST/HELP la nuit et LOWER FOOD près du sac
  suspendu, après les dangers et les indications d'abri ou d'arbre.
- Raccourcis affichés pour passer directement entre HELP, INVENTORY,
  STATUS et TOPO. Navigation de STATUS fixée aux deux dernières lignes.
- Vérification des pixels d'alerte et des neuf transitions directes,
  avec conservation du temps, des réserves et de l'image visible.

### Aide et inventaire plus lisibles

- HELP affiche deux pages, déplacements et survie, avec exemples de commandes,
  unités et touches de navigation. Les touches 1/2 sélectionnent une page,
  N/Espace et B changent de page, Échap/Entrée réaffichent le paysage.
- Titres d'aide et groupe d'inventaire en vidéo inverse ; nombre d'objets,
  capacités FREE et commandes de pagination affichés explicitement.
- Consultation vérifiée au clavier, sans avancer le temps ni modifier
  les réserves, la santé ou le paysage.

### Alertes rétablies avant affichage

- Une amélioration remplace désormais l'alerte d'aggravation encore en
  attente pour la même catégorie, au lieu d'afficher un avertissement périmé.
- Régressions pour faim, soif, santé, température et immersion ; les alertes
  encore actives d'autres catégories gardent leur priorité. Le classement
  reste sans effet sur la simulation.

### Résultat des commandes d'attente

- WAIT et PAUSE annoncent « YOU WAITED » en heures ou minutes, au lieu de
  « YOU RESTED » ; leur absence de crédit de repos est conservée.
- Régressions sur les deux unités, les effets identiques de WAIT/PAUSE,
  le crédit distinct de REST et l'annulation d'une durée nulle.
- Réorganisation des textes en mémoire sans lecture disque supplémentaire
  pour le sommeil ; ses cinq lectures et son état final restent vérifiés.

### Limite des forêts dans les écrans d'information

- TOPO et STATUS utilisent la limite d'altitude des arbres de la carte,
  comme la vue 3D et CLIMB TREE, au lieu d'une constante de 11 000 pieds.
- La valeur zéro conserve la limite historique de 11 000 pieds.
  Régressions sous la limite et exactement à celle-ci, pour trois limites,
  en vérifiant les symboles T/t, WOODS/SCRUB et l'accès aux arbres.

### Valeur directe de NATURE

- `NATURE 0` désactive désormais les nouvelles rencontres, comme la valeur
  zéro saisie à l'invite ; la commande directe était refusée par la liste
  des actions numériques et conservait la fréquence précédente.
- Valeurs 0–100, espaces et saisie à l'invite vérifiés. Les nombres hors
  limites, décimales et unités sont refusés sans changer l'état du joueur,
  la fréquence, le paysage ou le hasard.

### Objets au sol dans le bandeau

- « ITEMS: INV » disparaît après récupération du dernier objet ou
  consommation de la dernière réserve au sol, comme dans l'inventaire.
- Le résumé ne prend plus les compteurs de corde et d'autres équipements
  pour des réserves au sol ; les aliments épuisés ne comptent plus non plus.
- Régressions par commandes réelles sur corde, hache, œufs et eau.

### Projection des sites au pied des falaises

- Une cabane très en dessous de la vue ne réapparaît plus à l'écran
  lorsque le calcul de sa hauteur dépasse 16 bits.
- Régression sur neuf hauteurs de falaise et trois orientations, comparées
  pixel par pixel au modèle de projection indépendant.

### Durée des rencontres pendant les actions immobiles

- Les rencontres déjà présentes vieillissent aussi pendant WAIT, les
  repas et le sommeil ; elles expirent à 60 minutes, même sans déplacement.
- Aucun nouveau tirage de faune pendant ces actions. Régression sur une
  attente, un repas et deux repos, avec présence à 59 minutes, disparition
  à 60 minutes et générateur de hasard inchangé.
- NATURE rejoint le module de saisie ; cela libère la place nécessaire
  dans le module de simulation et évite son chargement pour ce réglage.

### Alertes après une boisson

- DRINK actualise immédiatement l'état de soif et de déshydratation utilisé
  par le bandeau, sans attendre une action qui avance le temps.
- Une déshydratation effacée par la boisson ne reste plus affichée ; tests
  de guérison, d'amélioration de la soif et de déshydratation persistante,
  avec stocks débités une seule fois et heure/santé conservées.

### Retour entre groupes de l'inventaire

- Depuis la première page d'un groupe, B revient à la dernière page du
  groupe précédent, au lieu de sauter directement à sa première page.
- Régression sur le passage sac → sol → retour au sac, avec deux pages
  d'objets dans chaque groupe ; heure et stocks conservés.

### Alerte de maladie devenue périmée

- Une maladie disparue avant le rafraîchissement du bandeau affiche
  « ILL IMPROVED », au lieu de provoquer une fausse alerte « EXHAUSTION ».
- Régressions sur les trois guérisons, une déshydratation persistante et
  les remplacements de maladie entre deux affichages.

### Minute de l'horloge

- Le bandeau et STATUS arrondissent le total des minutes avant d'extraire
  heure/minute : WALK 19 MIN depuis 7 h affiche désormais 7:19, au lieu
  de 7:18 quand le flottant est légèrement inférieur à la minute entière.
- Retenues vers l'heure suivante, midi et minuit gérées ensemble, sans
  modifier le temps simulé. Régression sur une marche réelle et sept
  valeurs proches des limites de minute et d'heure.
- Minuit s'affiche 12:00A dans STATUS ; le format 12 heures affichait
  auparavant 0:00A à cause du drapeau zéro laissé par la comparaison à 12.

### Fin exacte de la durée de voyage

- Après le dernier pas demandé, WALK/SWIM s'arrêtent sans tester un pas
  supplémentaire. Le résultat indique la fin de la durée plutôt qu'un
  obstacle (eau, falaise ou bord de carte) situé au-delà du voyage terminé.
- Les interruptions du pas accompli (animal, nuit, rive, décès, arrivée)
  conservent leur priorité. Régressions sur trois obstacles après exactement
  19 minutes, sur une fin de nage au bord de carte, sur l'eau rencontrée
  avec une minute restante et sur animal/nuit au dernier pas demandé.

### Arguments numériques des médicaments

- `EAT FLAGYL 0 OZ` ne consomme plus une dose malgré la quantité nulle.
  Les médicaments refusent désormais les nombres et unités ajoutés à
  EAT/DRINK, au lieu de les ignorer et d'appliquer une dose unique.
- Le refus conserve stocks, heure et état médical ; il explique de retirer
  le nombre et l'unité. Une prise normale reste disponible après le refus.

### Chasse aux bugs : saisie et lancement des tests

- Les commandes numériques acceptent les espaces en tête comme l'analyse
  ordinaire : `  SLEEP 1 MIN` ne produit plus un refus de valeur invalide.
  Régressions sur repos, marche trop courte et DRINK WATER qualifié.
- `make test` reconstruit a2shot avec son Makefile et ses chemins SDK,
  au lieu d'utiliser la règle C++ implicite qui échouait sur `pom2/core.hpp`.

### Attente réduite pendant SLEEP

- Suppression du détour par le vocabulaire et du rechargement de l'analyse
  numérique pour les commandes de repos avec durée, ainsi que SLEEP seul.
- Sommeil de huit heures sur la scène initiale : 32,1 → 26,8 secondes à
  1,023 MHz, avec cinq lectures de disquette au lieu de sept.
- Santé, météo et durée simulée conservées ; comparaison de l'état et du
  paysage avec REST, et vérification des six verbes de repos et d'attente.

### Corrections sur falaises et entrée dans la cabane

- Rejet du débordement du quotient de pente multiplié par trois : les
  arbres situés très bas sous une falaise ne réapparaissent plus dans le ciel.
- ENTER SHELTER refuse l'entrée depuis un arbre ; il faut CLIMB DOWN avant
  d'entrer dans la cabane. Le refus conserve heure, position et inventaire.
- Message de refus dans l'arbre corrigé : son point d'exclamation était
  interprété comme une substitution du motif d'arrêt de voyage. Même
  correction pour le rapport de victoire sans déplacement.
- Régressions sur cinq falaises ascendantes/descendantes et sur la chaîne
  grimper → entrée refusée → descendre → entrer → sortir.

### Doses et gestes de soin

- Décompte signé des utilisations des produits médicaux, sans débordement
  des stocks nuls ou négatifs ; quantités affichées dans INVENTORY.
- Prises orales de FLAGYL, SALT TABLETS et QUININE par EAT/DRINK ;
  refus de l'oxygène, du savon, des crèmes, lunettes et trousses.
- SHIELD EYES et LOWER HEAD sans durée ; SUCK VENOM exige une morsure
  active et prend 15 minutes. LOWER FOOD/BACKPACK conserve la récupération
  du sac suspendu.
- Commandes déplacées dans WILDMVI, avec retour résident avant le calcul
  des soins et du temps ; les progressions restent dans WILDMED.
- 130 cas supplémentaires sur ROM : 90 compteurs signés, 12 gestes de soin,
  22 prises orales et 6 chaînes USE/inventaire/soins sur la dernière dose
  ou un stock vide. Le prérequis natif reste sélectionné même sans dose
  positive ; ce comportement est conservé.
- L'oxygène dépend du drapeau d'utilisation distinct : la dernière dose
  protège, mais réutiliser une bouteille vide désactive cette protection.
- Restent à porter : SPLINT, soins thermiques, placement/stérilisation
  propre à USE et les déclencheurs de blessures/maladies.

### Conditions médicales et expositions

- État résident des 15 conditions Journey : incubation, santé, guérison
  avec/sans soin et produit des pourcentages entiers.
- Prérequis de prévention et de traitement, protection vestimentaire,
  réinitialisation quotidienne des soins temporaires.
- Compteurs sel/froid, seuils stricts et décroissance protégée ; exposition
  solaire et neige raccordées aux données du port.
- Mal d'altitude, oxygène et plafond de 30 minutes en santé critique ou
  pendant les huit premières heures des conditions 6–11.
- USE médical, STOP BLEEDING et page médicale de STATUS.
- WILDTRV pour la nage, WILDMED pour les soins/expositions, WILDMVI pour
  l'état médical, calcul de charge déplacé dans WILDSIM.
- Comparaisons sur ROM : 160 progressions, 66 combinaisons de soins,
  60 cas d'altitude, 80 cadences, 84 protections vestimentaires et
  59 expositions sel/froid, soit 509 cas.
- Restent à porter : soins complémentaires, déclencheurs par
  attaques/chutes/contamination et sélecteurs solaires/neige exacts.
- TOPO : légende raccourcie pour préserver la progression en marche.
- Bandeau invalidé quand WILDSIM emprunte HGR ; retour de STATUS restaure
  les pixels affichés et le cache du terrain. Les tests distinguent ce dessin
  des octets graphiques inutilisés servant aux calculs temporaires.
- Pilote d'aventures : acquittement du temps de marche natif pris en charge,
  quatre scénarios terminés avec écarts toujours signalés ; 112 évolutions
  bornées du vent comparées au moteur original.

### Correction du rendu des arbres

- Dessous du premier profil ramené à la hauteur du feuillage central :
  suppression des pointes noires latérales qui descendaient vers le sol.
- Couronnes séparées, centrées dans leurs cases : le profil natif de
  32 colonnes ne couvre plus deux cases entières.
- Motif de feuillage vert/noir rétabli, avec pixels opaques et occlusion
  des astres ; les profils ne sont plus remplis entièrement en noir.
- Troncs noirs sous le centre du feuillage, ancrés au terrain ; couronnes
  relevées de 18 pixels divisés par la distance pour les arbres proches.
- Contour supérieur noir continu et liseré inférieur du feuillage pour
  détacher les couronnes du ciel violet et du terrain vert.
- Limite du feuillage conservée quand la base projetée dépasse l'écran,
  sans débordement vers un remplissage noir sur les pentes descendantes.
- Stockage de cette limite hors de l'octet d'arrondi Applesoft, pour
  conserver les calculs exacts de durée après l'affichage des arbres.
- Contrôle visuel en émulateur et régression contre les bandes noires
  continues, en plus des comparaisons de pixels et des rotations.

### Grimper et suspendre la nourriture

- `CLIMB TREE` / `CLIMB DOWN` : arbre proche, santé > 2,5 pour monter,
  marche et nage refusées dans l’arbre ; aucun temps ajouté.
- `HANG FOOD` suspend le sac et son contenu pendant 30 minutes, avec
  le coût natif de 1,65 + 0,02 × poids corporel kcal/min.
- `GET BACKPACK`, `LOWER FOOD` et `LOWER BACKPACK` récupèrent le sac à sa
  case ; charge vérifiée et restauration atomique en cas de refus.
- INVENTORY affiche `HUNG HERE` ; STATUS signale l’arbre et le sac suspendu.
- Sonde de 24 cas CLIMB et 16 cas HANG dans le code original sur ROM ;
  tests du port sur les stocks partagés, les conteneurs, les écrans et les refus.

### Arbres et forêts

- Zones boisées issues des contours TMAKE et profils d’arbres Sierra portés.
- Projection attachée au monde, clipping par le relief, priorité aux sprites proches.
- TOPO, STATUS et filtres de faune reconnaissent bois et maquis d’altitude.
- Extension MAP de 294 octets, import des forêts TOPO, compatibilité des cartes anciennes.
- Tests du dessin, des rotations et du chargement.


### Neowilderness lots 4 et 5 Survie, inventaire et orientation

- Compas encadré sur toute sa hauteur, conservé pendant les rotations.
- Résumé monochrome autour de la boussole : heure/période, santé, faim, soif,
  alerte de transition ou état thermique ; abri et objets récupérables ici.
- Alertes aux seuils existants, sans répétition à classe inchangée ni changement
  des règles ; les activités longues conservent une alerte prioritaire.
- STATUS réorganisé, avec conditions avant besoins/environnement et réserves
  CARRIED/HERE distinctes ; cas maximal lisible sans couper un nom de condition.
- INVENTORY regroupé par emplacement, douze objets/page, réserves réparties
  affichées séparément, capacités permanentes et navigation explicite.
- TOPO : C pour recentrer, huit caps magnétiques et site sous le joueur nommé.
- WILDHUD/WILDSTA dans la fenêtre de 2 Ko ; bandeau conservé pendant rendu
  et rotations, faune traitée avant sa composition au démarrage.
- `test_interface.py` vérifie affichage, transitions, groupes/pages/quantités,
  STATUS maximal, orientation/recentrage et consultations sans dépense.
- Validation : suite complète `make -C wilderness test` réussie après le cadre ;
  disquette reconstruite, contrôles de rendu et mémoire inclus.


### Soleil et lune comme repères géographiques

- Soleil calculé selon latitude, saison et heure solaire, indépendant de
  la déclinaison magnétique ; projection dans les axes du terrain.
- Lune nocturne à partir d'une éphéméride de référence 1985, avec phase
  stylisée et correction moyenne de parallaxe ; extension identifiée du port.
- Masquage par nuages, relief et sprites ; conservation du panorama partiel
  de jour et de la vue sombre la nuit, qui ne révèle pas le terrain.
- Initialisation déplacée dans WILDSIM pour respecter la mémoire résidente.
- `test_sky.py` vérifie positions, hémisphères/saisons, masquage et rotations.


### Neowilderness lot 2 Refus et résultats lisibles

- Suppression des confirmations cachées entre messages : la commande suivante
  conserve sa première touche. Le résultat reste lisible au retour à la vue,
  pendant la saisie, après Échap et après une ligne vide.
- Déplacement : durée effective et arrêt par eau, rive, nuit, limite, animal,
  Échap, manque de temps ou terrain/rythme réunis. Mort, victoire et faiblesse
  gardent la priorité ; les résultats de voyage conservent leur durée.
- Verbe inconnu signalé avec HELP ; objet manquant accompagné d'exemples
  disponibles ; objet inaccessible distingué d'une commande non implémentée.
- Consommation : stock accessible avant la réponse, puis quantité réellement
  consommée et stock initial. Les transferts nomment l'objet comme dans
  INVENTORY et son nouvel emplacement, y compris les objets qualifiés.
- Refus de charge : poids, volume ou les deux, excédent et capacité après
  annulation en OZ/IN3 ; distinction des volumes portés, du sac et de la main.
  Dépassement arithmétique distingué d'une capacité simplement insuffisante.
  Sac/gourde absents, conteneurs non vides et sac rangé dans lui-même séparés.
- WILDITM regroupe les transferts dans 2 Ko pour libérer la mémoire résidente.
  Le moteur garde les textes dans trois lignes, sans défilement provoqué par
  un nom long. `test_feedback.py` couvre la matrice de refus, les valeurs
  maximales, la persistance, le stock et les arrêts pour animal/nuit.
- Validation : `make -C wilderness test` complet réussi, avec préservation
  des optimisations de rotation, des écritures TOPO et des traversées de rives.

### Traversée des rives WALK / SWIM

- WALK indiquait l'eau une case avant celle-ci, puis SWIM refusait son premier
  demi-pas encore sur terre. Deux SWIM successifs restaient donc sur place.
  Ce demi-pas est désormais autorisé si le suivant entre dans l'eau, avec
  vérification du trajet sans déplacement ni dépense pendant la vérification.
- SWIM réalise le dernier demi-pas vers la terre et s'arrête sur la rive,
  avec le bilan du temps réellement passé et la fin de l'immersion. WALK
  permet ensuite de poursuivre. SWIM sans eau devant reste sans effet.
- `test_shore.py` couvre les quatre directions, une position fractionnaire,
  un trajet diagonal et deux SWIM successifs jusqu'à la rive opposée.
- Validation : suite complète `make -C wilderness test` réussie, y compris
  trajectoires et durées de nage, bilan thermique, Échap, TOPO et rotations.

### Neowilderness lot 1 Commandes et annulation

- Échap efface la commande ou annule une saisie numérique, sans quitter le
  jeu ; QUIT exige Y après avertissement de perte de progression.
- La flèche gauche supprime un seul caractère dans les quantités et durées.
  Une saisie vide ou zéro annule l'action ; NATURE conserve son réglage zéro.
- Arguments directs et unités : WALK 10 MIN, REST 1 H, DRINK WATER 4 OZ et
  EAT CHEESE 8 OZ. Les anciennes questions restent utilisables ; absence
  d'unité = heures ou onces. Les unités, plages et dépassements sont vérifiés.
- Échap interrompt WALK et SWIM après un pas terminé, avec position, santé,
  réserves et temps effectif conservés. Le repos accepte les minutes ; son
  interruption pendant l'activité reste une suite facultative.
- Échap quitte immédiatement chaque page d'inventaire, sans attendre une
  seconde touche. STATUS et TOPO conservent leur retour à la vue.
- Module WILDINP à $5800 ; déplacement du parcours des mots dans WILDVOC et
  du texte HELP dans WILDSCR pour rester dans les 48 Ko, sans lecture ajoutée
  au chemin des rotations par flèches.
- `test_input.py` couvre les annulations, refus atomiques, unités, correction
  de chiffres, sorties des écrans, confirmation de QUIT et arrêts marche/nage.
- Validation : `make -C wilderness test` complet réussi.

### TOPO écrit seulement les caractères modifiés

- Suppression de HOME et de la réécriture systématique de la carte à chaque
  pas ou défilement. Comparaison directe avec la RAM texte avant chaque écriture,
  pour le relief, les repères, les coordonnées, les légendes et les espaces.
- Retrait des anciens caractères en fin de ligne sans réécrire les espaces
  déjà présents ; conservation des messages et du curseur pendant la marche.
- Tests des écritures réellement exécutées : une écriture par caractère modifié
  sur douze pas de WALK et les défilements ; zéro écriture si la carte ne change pas.

### Présentation pendant le chargement

- Après le titre Apple II+, l'écran présente le crash, l'objectif de rejoindre
  les rangers, les besoins de survie et les commandes principales.
- Les durées en heures, les quantités en onces et les rotations sur une ligne
  vide sont expliquées. Le chargement continue sans attente de touche.
- Présentation intégralement en anglais, limitée à vingt lignes de moins de quarante
  caractères pour rester visible pendant les lectures DOS.
- Vérification du texte au début et à la fin du chargeur, de l'arrivée à
  l'invite jouable et de la restitution des données résidentes par `test_boot.py`.

### Défilement près des sites et accélération du rendu

- Les rotations de 22,5° et 45° réutilisent désormais la géométrie d'un site
  distant unique, même hors champ. Les flèches ne chargent aucun module ;
  seules les colonnes découvertes sont rendues. Les scènes à plusieurs sites
  potentiellement voisins conservent la sélection par reprojection.
- Invalidation du cache de cap après défilement pour éviter de réutiliser une
  ancienne projection avec une origine de sprite déjà décalée.
- Parcours direct des lignes physiques pour l'effacement et le défilement ;
  suppression des appels d'activation de sprite inutiles dans les rayons.
- Mesures : 77,0 % de cycles en moins sur 48 rotations près de la cabane,
  comparées au rendu complet forcé ; 4,7 à 11,5 % de gain sur le rendu complet
  des cinq cartes de contrôle, avec images identiques à la référence.
- Tests de rotation étendus aux sites distants, au masquage par une crête,
  aux sites concurrents, aux tours complets et aux compteurs de lectures disque.
- Validation : `make test` complet réussi, plus rotations de l'épave distante
  et sélection de deux sites à des azimuts différents ; disquette reconstruite.

### Ciel, orientation et carte pendant la marche

- Le ciel et le relief occupent à nouveau les côtés du ruban. Le paysage
  sous le ruban est conservé dans des lignes HGR invisibles pour éviter les
  traces lors des rotations, sans allocation de mémoire supplémentaire.
- TOPO affiche maintenant les Y décroissants : le nord est réellement en
  haut, comme les déplacements et la boussole. Les touches de défilement
  suivent cette orientation.
- À chaque pas de WALK, TOPO se recentre et se rafraîchit dans les vingt
  premières lignes. Les messages, leur curseur et la simulation sont préservés ;
  aucun rechargement ni attente de touche entre les pas.
- Vérifications : déplacements réels N/E/S/W et douze rafraîchissements
  consécutifs pendant WALK, avec contrôle des zones préservées.

### TOPO : actualisation avant affichage

- La carte est reconstruite avant de passer en mode texte à l'ouverture,
  pour éviter l'apparition fugace du précédent écran TOPO ou STATUS.
- Vérification de la réouverture après défilement, marche et rotation :
  recentrage, position/cap, relief et repères relus depuis l'état courant ;
  la vue 3D et son ruban de boussole restent intacts au retour.

### Boussole permanente en haut de la vue

- Suppression de l'activation `USE COMPASS` : les points cardinaux sont
  disponibles dès le départ, sans désactivation lors des transferts d'objets.
- Ruban de 98 pixels centré en haut, avec N/NE/E/SE/S/SW/W/NW, graduations
  tous les 22,5° et curseur fixe. Défilement continu à un pixel pour deux
  unités d'azimut, avec prise en compte de la déclinaison magnétique.
- En-tête réservé sur 16 lignes ; il reste visible la nuit et à la cabane,
  et n'est pas entraîné par le défilement du terrain. Pas de chargement disque
  ni de calcul flottant pour mettre à jour le ruban lors des rotations.
- Vérification des 560 azimuts, du raccord nord, du centrage magnétique,
  des commandes de rotation et des retours depuis STATUS.

### Rotations de la vue

- Défilement du terrain et des sprites locaux pour les rotations de 22,5°
  et 45° ; seules les colonnes entrantes sont recalculées. Géométrie et
  masquage des sites distants conservent le rendu complet.
- Restauration de l'image du sprite après le chargement du vocabulaire de
  LOOK ; les flèches évitent ce chargement lorsque l'image est déjà en mémoire.
- Boucle de défilement raccourcie et suppression d'une table sinusoïdale
  de 141 octets, avec conservation exacte des arrondis des directions.
- Test des cinq sprites, sorties/retours dans le champ et tours complets
  dans les deux sens. Sur 52 rotations autour de l'épave : 435 480 947 →
  98 301 942 cycles, soit 77,4 % économisés, pixels et texte identiques.

### Température : variation lente originale

- Ajout de `INT(5 × SIN(0,0187 × heures écoulées + phase))`, avec la phase
  sauvegardée du premier voyage Sierra et les arrondis de la ROM Applesoft.
- 405 cas comparés à la routine T09/S08 originale : phases, durées,
  températures signées et passage de la limite d'un octet.
- L'air concorde désormais aux six points du scénario de départ ; les
  écarts passent de 13 à 6, encore sur le vent et le ressenti. Le cycle
  quotidien, la visibilité et les fronts météo restent à porter.

### Marche : attente et accès disque

- Regroupement de la faune avec les calculs d'environnement : deux lectures
  de modules par pas ordinaire au lieu de trois quand la faune est active.
- Affichage des minutes parcourues après chaque pas, sans touche à presser.
- Test d'une marche de quatre heures : progression, nombre de lectures,
  retour à la commande et absence de lectures supplémentaires à l'arrêt.

### Terrain : rivières et lacs

- Les plateaux s'écoulent désormais vers un exutoire au lieu de déclencher
  des lacs artificiels. Les véritables cuvettes sont remplies jusqu'au
  niveau de débordement, avec une surface plane et une sortie continue.
- Suppression du remplissage tronqué à 300 unités et des carrés d'eau
  effacés après génération autour du crash et des rangers. Une source
  couvrant ces lieux est rejetée avant modification du terrain.
- Conversion 224 × 168 vers 112 × 84 : chaque bloc garde ses points d'eau,
  y compris aux coordonnées impaires, à la hauteur de l'eau. La cabane
  évite aussi ces cases converties. Les autres marqueurs TOPO ne sont
  plus interprétés comme des rivières.
- Tests des plateaux, petites/grandes cuvettes, rivières fines et de
  18 couples graine/difficulté : continuité, descente et reproductibilité.
  L'écoulement reste une reconstruction, à comparer au générateur original.

### Nage : tracé des caps obliques

- Remplacement des vecteurs continus par l'axe majeur entier et l'accumulateur
  sinusoïdal de l'original ; la durée distingue désormais chaque pas réellement
  droit ou diagonal. État du tracé conservé pendant les changements de module.
- 2 880 positions sur 360 caps comparées aux routines originales sur ROM.

### Nage : effort et charge

- Remplacement des 19 minutes par case par la durée de nage normale de
  l'original, dépendant de la santé, de la charge et du caractère diagonal
  du pas. SWIM avance maintenant d'une demi-case ; un dernier pas peut
  dépasser le temps demandé s'il reste au moins la moitié de sa durée.
- 143 durées identiques aux routines originales exécutées sur ROM ; tests
  de la commande réelle, du dépassement de durée et du retour sur la rive.
  Nouveau module `WILDTRV` pour préserver la place mémoire résidente.

- SWIM utilise désormais le coût original lié au poids total : environ
  14,43 kcal/min avec l'équipement initial. L'eau de la gourde n'est plus
  comptée deux fois dans ce calcul ; les frissons s'ajoutent à cet effort.
- 81 cas de poids, charge et durée vérifient la dépense calorique ; les
  métabolismes sont également comparés octet par octet au helper original
  exécuté sur la ROM, et les calories à sa routine énergétique. Premier
  intervalle de santé de nage rétabli à 15 minutes. Test de la commande réelle,
  immersion, repos dans l'eau et sortie sur la rive. Les modificateurs de
  blessures/équipement restent à reproduire.

### Comparaison de commandes avec le jeu original

- Nouveau pilote différentiel sur les deux exécutables Apple II : départ,
  équipement, boissons, repas, repos répétés, nuit et première marche.
  Questions inspectées avant réponse ; erreurs et différences font échouer
  le test. Dumps, images, journaux, symboles et rapports restent dans `build/`.
- Observation de l'état original avant sa pagination sur Journey T04,
  pour éviter de confondre la seconde page HGR avec la physiologie.
- Boire à la gourde ne consomme plus de temps ; manger prend 16 minutes,
  avec crédits alimentaires et hydriques originaux. Les frissons de la
  sauvegarde initiale contribuent aux premières calories dépensées.
- Repos adaptatif après le premier pas de 30 minutes ; compteurs et
  déficits actualisés à la cadence de santé, pourcentages entiers et Hmax
  initial conservé à sa précision originale.
- Correction de la règle de rencontres précédente : repos et repas ne
  tirent aucune faune. Les tirages et interruptions restent actifs en marche.
- Directions cardinales corrigées par la déclinaison magnétique de la carte.
  La précision aléatoire de la boussole reste à porter.
- `make test-original` reste en échec sur les écarts météo/nuit/marche.
  Aucune aventure complète jusqu'aux rangers n'est encore validée.

### Rencontres pendant les actions

Cette étape précédait les corrections différentielles ci-dessus ; les
tirages pendant REST et sa cadence fixe ont depuis été remplacés.

- Tirage à chaque pas de simulation : repos de 30 minutes, marche/nage
  selon la durée du pas ; suppression du cumul limité à 255 minutes.
- Toutes les espèces sont testées dans l'ordre Sierra, même si un animal
  est présent ; conservation ou remplacement à 50 %, vérifiés dans l'original.
- Une rencontre acceptée interrompt marche/repos après le pas écoulé,
  avec temps exact et message d'interruption du repos.
- Aucun tirage extérieur sous abri ; VIEW/STATUS ne dépensent ni temps
  ni hasard. Les interruptions laissent le sprite disponible pour l'action suivante.
- Sondes des drapeaux originaux et scénarios déterministes de repos long,
  marche interrompue, remplacements et protection de la cabane.
  Durée de présence de 60 minutes et déplacements des animaux restent provisoires.

### Faune Sierra et limites de déplacement

- Filtres des trois espèces : saison, heure, terrain, altitude, pente
  maximale du voisinage 3 × 3 et indice climatique régional.
- Probabilité `minutes × NATURE × √difficulté × taux × 10⁻⁵`, avec les
  taux originaux 80/40/100 et un générateur indépendant de la météo.
- Commande NATURE : multiplicateur entier 0–100, valeur initiale 1, refus
  des valeurs supérieures ; les animaux nocturnes restent invisibles la nuit.
- Difficulté et indice Sierra dans l'en-tête de carte ; anciennes cartes
  compatibles avec les valeurs par défaut 4 et 31.
- Marche et nage arrêtées avant la bande extérieure de deux cases, avec
  message explicite et aucun temps facturé pour le pas refusé.
- Sondes du code original, scénarios par espèce et tests des quatre côtés.
  Cadence des tirages, durée de présence, déplacements et réactions restent
  provisoires ; NATURE n'accepte pas encore les valeurs fractionnaires.

### Sites visibles à distance

- Épave et cabane projetées à moins de huit cases : azimut depuis leurs
  coordonnées fixes, tailles par paliers et ancrage sur leur altitude.
- Insertion du sprite au pas de rayon correspondant à sa distance ; le relief
  situé devant le masque, celui situé derrière conserve le sprite visible.
- Composition toujours par colonne, sans chargement disque dans les rayons,
  avec les couleurs, la transparence et les pixels noirs des flux originaux.
- Module WILDPRJ pour préparer la géométrie et les bornes du terrain ; cache
  réutilisé quand position, cap et rencontre restent identiques.
- Rotations complètes près des sites, y compris lorsqu'ils sont hors champ,
  pour éviter les apparitions manquées et les traces du défilement partiel.
- Comparaisons exactes et parcours d'approche/retour à pied. Limite actuelle :
  un seul site par vue, sélectionné par distance dans le champ ; les animaux
  restent locaux et la projection est une règle propre au port.

### Cabane et TOPO

- `ENTER SHELTER`, `EXIT SHELTER` et `LEAVE SHELTER` à la cabane ; état
  intérieur conservé pendant REST, rotations et écrans STATUS/TOPO.
- Protection thermique de l'abri trouvé : air ambiant +15 °F, sans vent,
  comparée à la branche originale ; HUT reste une fabrication distincte.
- Refus de marche/nage à l'intérieur, absence de rencontres pendant le
  repos sous abri et restitution de la vue extérieure à la sortie.
- Première carte TOPO textuelle de 32 × 14 cases : relief, eau et repères
  joueur/épave/cabane/rangers, avec défilement borné par flèches ou WASD.
- Nouveau module disque WILDSIT ; résolution des qualificatifs déplacée
  dans WILDVOC pour préserver la petite marge de mémoire résidente.
- Parcours testé sans changement de position en mémoire : repérage, marche,
  entrée, repos au froid, sortie et retour ; tests supplémentaires de nuit
  et sondes locales des commandes et températures originales.

### Rendu par colonne

- Composition du sprite et du terrain dans chaque colonne, sans passe de
  superposition après la vue complète ; chargement disque avant le rendu.
- Remplissage limité aux zones transparentes et arrêt des rayons lorsque
  le relief maximal ne peut plus contribuer aux lignes encore visibles.
- Réutilisation du tampon de texte BLOAD pour les 160 couleurs de la colonne,
  avec conservation des pixels noirs opaques et des rotations.
- Épave descendue de dix lignes pour retrouver ses coordonnées verticales
  d'origine, sans empiéter sur le texte.
- Test de l'image intermédiaire, comparaisons exactes sur cinq cartes et
  profilage des pas de rayons et cycles hors chargement DOS.

### Documentation

- Réorganisation du TODO en lots ordonnés, avec la correction du rendu
  terrain/sprites en première priorité.
- README recentré sur l'état jouable, les commandes et la construction.
- Référence du portage regroupée dans `docs/IMPLEMENTATION.md` : règles
  provisoires, mémoire, format de carte, tests et outils.
- Nettoyage des mentions périmées dans les analyses et ajout de cet historique.

### Graphismes originaux

- Extraction des flux Journey de l'épave, de la cabane et des animaux,
  avec PNG transparents et manifeste des positions/empreintes.
- Branchement des sprites épave, cabane, ours, couguar et crotale Sierra
  dans la fenêtre de chargement disque de 2 Ko.
- Épave ancrée au départ, cabane placée sur terre et premières rencontres
  graphiques avec un générateur aléatoire indépendant.
- Préservation des couleurs, des pixels noirs et de la transparence ;
  clipping, suivi du cap, masquage nocturne et effacement au départ de la case.
- Tests des cinq images au pixel près et d'une rencontre après REST.
- La cabane est visuelle et les comportements des animaux restent à porter.

### Immersion

- SWIM traverse les cases d'eau et s'arrête avant la rive ; WALK rejoint la terre.
- Pertes des vêtements mouillés, température d'eau liée à l'altitude et
  bilan thermique immergé ; sueur supprimée dans l'eau.
- REST conserve l'immersion ; STATUS affiche IMMERSED. Un pas sur terre
  remet le sélecteur à sec. La cadence de nage reste reconstruite.

### Vent et énergie

- Température ressentie signée affichée dans STATUS et utilisée par la thermique.
- Dépense entière en kcal par pas ; supplément des frissons selon le poids,
  avec effet sur le déficit alimentaire et conservation du métabolisme de base.
- Comparaisons des formules de vent et d'énergie aux routines originales sur ROM.

### Thermique sèche

- Température corporelle selon air, activité et vêtements ; récupération
  bornée à 98,6 °F et seuil de dérive vérifié sur la ROM.
- Reconstruction déterministe des couches vestimentaires et facteurs de santé
  froid/chaud ; arrêt de l'activité lorsque la santé devient fatale.
- STATUS affiche température corporelle, frissons/sueur et hypo/hyperthermie.

### Modules disque

- Découpage du vocabulaire, des écrans et de l'environnement dans une fenêtre
  BLOAD partagée, avec cache du module courant.
- Préservation de la page zéro, du texte visible, de HGR et de l'état du jeu.
- Air horaire et thermique regroupés pour limiter les lectures pendant REST.

### Objets et charge

- WEAR, GET/PACK, CARRY/TAKE et DROP/REMOVE : corps, sac, main et sol.
- Positions au sol, reprise au retour, quantités accessibles et qualificatifs
  des noms partagés ; désactivation de la boussole lorsqu'elle est déposée.
- Poids et volumes par catégorie, refus atomiques de surcharge/débordement,
  vidage des conteneurs avant dépôt et capacités restantes dans INVENTORY.
- Limites du modèle calibrées sur les capacités de départ de l'original ;
  comptabilité exacte des conteneurs encore à établir.

### Socle jouable

- Vue de terrain 3D, cartes générées, rotations et défilement partiel,
  comparés au bit près à une référence Python.
- Parseur de 280 mots, marche, repos, repas, boisson, boussole,
  STATUS et INVENTORY.
- Horloge, date, soleil, air, énergie, déficits de survie, santé, mort
  et arrivée au poste de rangers.
- Tests des commandes aléatoires, refus de marche nocturne et calcul du temps
  sur les fortes pentes.

### TOPO graphique et MAP locale

- TOPO/T affiche une feuille HGR de l’ensemble du terrain : courbes de niveau
  interpolées tous les 400 pieds, eau, bois et repères C/H/R, nord en haut.
- MAP conserve la fenêtre textuelle centrée sur le joueur, son défilement,
  son recentrage et ses écritures différentielles pendant les déplacements.
- Chaque disque contient une feuille calculée depuis sa propre carte ; fermer
  TOPO restaure la vue sans modifier le temps, la position ou les provisions.

### Tests de déplacement alignés sur les règles natives

- Correction des attentes devenues obsolètes dans les tests de saisie,
  de cabane/orientation et de marche longue : demi-cases et cadence calculée.
- Vérification explicite des budgets refusés, exacts et dépassés par le
  dernier pas admis, du retour à la cabane après repos et des lectures disque.
- Documentation des déplacements mise à jour ; le moteur natif est conservé.
