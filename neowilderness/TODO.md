# Neowilderness — directions de travail

Port de Wilderness (Electric Transit, 1985) pour Apple IIe enhanced 128 Ko et
IIc : ProDOS, tout résident en RAM, paysage DHGR 16 couleurs, une disquette
5,25 pouces de 140 Ko. Le point de départ est `../wilderness/` au 13 octobre
2026 (base `72af937`, synchronisée avec `d90a563` et `277d455`) ; le
[backlog HGR](TODO_HGR.md) conserve les travaux de gameplay hérités.

Ce fichier organise le travail restant en cinq directions. Les deux
premières sont prioritaires. La qualité (tests, documentation, mesures) est
transversale : chaque direction porte ses propres tests et ses chiffres ; la
direction 5 ne garde que ce qui est commun (commits, machines, livraison).

## Réalisé

Lots 0 à 4 et étapes 1 à 3 du lot 7 (13 octobre 2026) :

- ProDOS 8 : `NEOWILD.SYSTEM`, tronc commun `NEOWILD.DAT` et six paquets de
  région `NEOWILD.R1`…`R6` (15 à 18 blocs chacun) ; modules, simulation,
  carte, sprites et TOPO résidents en RAM auxiliaire ; zéro appel MLI
  pendant le jeu (`test_resident.py`) ; état de simulation identique à la
  référence HGR (`test_reference_state.py`) ; plan mémoire dans
  [MEMORY.md](docs/MEMORY.md).
- Paysage DHGR : 140 rayons, dix humeurs selon soleil et lune, sprites
  originaux colorés par asset, boussole et panneaux natifs, quatre lignes de
  texte 80 colonnes, TOPO calculée en RAM (3 s) avec retour par instantané
  (0,24 s), MAP 80 colonnes ([DHGR.md](docs/DHGR.md),
  [TOPO_DHGR.md](docs/TOPO_DHGR.md)).
- Six régions : en-têtes, 27 sprites et règles de rencontre sondés sur
  l'original ([REGIONS.md](docs/REGIONS.md), [animals.md](docs/logic/animals.md)),
  cartes reconstituées des cinq régions sans carte originale, menu de
  démarrage, voyage libre, retour au menu ([SCENARIOS.md](docs/SCENARIOS.md)).
- Faune à quatre espèces, palettes et textes par région ; l'arrêt d'une
  marche nomme sa cause (animal, ressource, site).
- Étoiles la nuit : 79 étoiles, module horaire (ID 25) et tracé en banque 2
  de la carte langage principale (`$D400-$DEFF`, libre sous ProDOS 2.4.3),
  toutes visibles en nuit noire, premières grandeurs sous la pleine lune,
  aucune de jour, sous les nuages ni au crépuscule ([STARS.md](docs/STARS.md)).
- Score et hall of fame : module de fin `NEOWILD.END`, fichier
  `NEOWILD.HOF`, meilleur score par scénario au menu, voyage libre non
  classé ([HOF.md](docs/HOF.md)).
- Suite complète `make test` verte (7 min), plus les bancs `dhgr.mk`,
  `stars.mk` et `hof.mk` ; 34 blocs libres sur la disquette, 86 octets
  libres en RAM principale, 1 313 octets auxiliaires libres au pire (Burma).

Mesures de référence (POM2, ≈ 1 MHz) : STATUS 8,9 s → 0,24 s, LOOK R 8,0 s
→ 1,9 s, WALK 1 H 70,7 s → 9,6 s ; menu 23 s après la mise sous tension,
9,2 à 9,8 s du choix à la première vue ([BASELINE_HGR.json](docs/BASELINE_HGR.json),
[BASELINE_128K.json](docs/BASELINE_128K.json),
[BASELINE_DHGR.json](docs/BASELINE_DHGR.json)).

## 1. Fidélité à l'original — prioritaire

Objectif : les règles, les tirages et les résultats sont ceux d'Electric
Transit 1985, dans les six régions.

- [ ] Conserver les règles natives, l'ordre des tirages aléatoires, les
  demi-pas et leurs coûts ; comparer les états avec la référence HGR à
  chaque changement du moteur (`test_reference_state.py` reste vert).
- [ ] Rejouer un trajet crash → rangers complet contre l'original (`make
  test-original`) avec repas, eau, repos, cabane, rencontres, soins et
  traversée à la nage avec retour sur la rive ; ajouter variantes de mort,
  blessures et soins ([ADVENTURE_TESTS.md](docs/ADVENTURE_TESTS.md)).
- [ ] Régions 1 et 3 à 6 au-delà des sondes de rencontre : terrain et
  altitude de base par région, gravité des blessures, branches non sondées
  (radeau, échanges avec les cannibales, mots JUNGLE ; [REGIONS.md](docs/REGIONS.md) § 7).
- [ ] Géographie fine native (224 × 168, rivières, lacs, cellules impaires)
  : choisir entre l'atlas `coarse` 16 × 16 résident pour la Sierra seule
  (6,4 Ko) et la résolution réduite pour toutes les régions (eau, lacs et
  bois exacts, hauteurs interpolées) ; mesurer les changements de bloc et
  l'absence de lecture disque sur un itinéraire complet
  ([GEOGRAPHY.md](docs/GEOGRAPHY.md)). Six atlas ne tiennent pas sur la
  disquette unique.
- [ ] Sites et abris originaux non portés : poste de rangers dessiné, tente,
  igloo, tranchée, bille, rocher (sprites déjà extraits).
- [ ] Niveau de difficulté : les cartes sont générées au niveau 4 quel que
  soit le niveau choisi ; seul `MAP+22` change. Vérifier ce que le niveau
  doit modifier dans l'original (blessures initiales, carte) et l'appliquer.
- [ ] Objets de l'épave : vérifier le tirage commun aux régions et la
  comptabilité exacte des conteneurs ([IMPLEMENTATION.md](docs/IMPLEMENTATION.md)).

**Terminé quand :** un trajet complet concorde avec l'original dans la
Sierra, les cinq autres régions suivent leurs fiches sondées, et la
géographie retenue est documentée avec ses écarts mesurés.

## 2. Image et ambiance — prioritaire

Objectif : le plus beau Wilderness possible en 16 couleurs à 1 MHz.

- [x] Étoiles la nuit : catalogue commun, module horaire (ID 25), un pixel
  par étoile masqué par la crête et la Lune, visibilité selon l'humeur ;
  Croix du Sud en Bolivia, Chile et New Guinea ([STARS.md](docs/STARS.md)).
- [x] Ciel plus peuplé : 282 étoiles jusqu'à la magnitude 3,5 (BSC5),
  liste de 160, module et catalogue dans la fenêtre SIM ; captures 2 → 10
  (Sierra nord), 7 → 31 (sud), 10 → 37 (Bolivia), pleine Lune inchangée
  ([STARS.md](docs/STARS.md) § 13).
- [ ] Optionnel : `LOOK STARS` (repères nommés, azimut et hauteur ;
  référence Python prête, pas de code 6502).
- [ ] Lune visible de jour et au crépuscule (le moteur ne calcule qu'un
  astre à la fois) ; règle de la lune gibbeuse graduée, si l'état comparé
  le permet.
- [ ] Retouche des humeurs et des palettes par région après visionnage sur
  les six cartes : nuits trop vertes, bleu foncé trop lumineux, dégradés.
- [ ] Vérification sur moniteur composite réel : franges, traits d'un pixel,
  texte 80 colonnes, gris identiques de POM2.
- [ ] Rendu : coût d'une vue (0,5 à 0,9 s de tracé), rotations, TOPO en 3 s
  (déroulage du compactage si 1,3 Ko sont trouvés) ; double tampon
  réévalué seulement si la direction 3 libère 16 Ko.
- [ ] Captures de référence par région et par humeur maintenues dans
  `build/dhgr/` et comparées par les tests d'image.

**Terminé quand :** les six régions ont leur palette validée à l'écran, les
étoiles sont testées sur les deux banques, et aucune commande d'affichage
n'est plus lente que la mesure publiée de plus de 5 %.

## 3. Mémoire, disque et vitesse

Objectif : tenir sur 128 Ko et 140 Ko sans lecture disque pendant le jeu.

- [ ] Réserves à conquérir : instantané TOPO (12,8 Ko) compressé ou réduit
  aux rangées utiles, tables Sierra retirées des modules, tronc commun
  recompressé ; publier le gain de chacune. La banque 2 de la carte langage
  principale (`$D400-$DEFF`) est déjà prise par les étoiles : sa liberté est
  une mesure sur ProDOS 2.4.3 dans POM2, pas une garantie documentée ; à
  vérifier avec d'autres versions de ProDOS et sur IIc.
- [ ] Budget par région tenu à jour dans [MEMORY.md](docs/MEMORY.md) § 9 :
  RAM principale, RAM auxiliaire (Burma au pire), blocs libres du volume.
- [ ] Démarrage : réduire les 21 s jusqu'au menu et les 10 s du choix à la
  première vue (lecture du paquet 3 s, initialisation 6,4 à 7,1 s).
- [ ] Transferts : supprimer la recopie de SIM à chaque activation si ses
  données sont prouvées immuables (0,68 s par WALK 1 H).
- [ ] Instrumentation conservée : appels MLI, octets transférés, cycles par
  phase ; `make`, `make run` et inspection du `.po` documentés.
- [ ] Politique disque : une image de 140 Ko ; documenter ce qui irait sur
  une seconde face ou une 800 Ko (six atlas de géographie fine, cartes de
  voyage libre, sauvegardes) sans l'engager.

**Terminé quand :** chaque région démarre avec une marge auxiliaire
documentée, le volume garde au moins dix blocs libres après les
sauvegardes, et les mesures sont publiées.

## 4. Expérience de jeu

Objectif : un jeu jouable sans documentation, au clavier ou au joystick,
qui garde la mémoire des parties.

- [x] Score et hall of fame : module de fin `NEOWILD.END`, fichier
  `NEOWILD.HOF`, meilleur score au menu, voyage libre non classé
  ([HOF.md](docs/HOF.md), [SCENARIOS.md](docs/SCENARIOS.md) § 7–8).
- [ ] Fin de partie : l'écriture du hall of fame coûte 1,9 s et une
  disquette protégée affiche un message à chaque voyage de scénario ;
  proposer de ne pas réécrire quand rien ne change.
- [ ] Anomalies vues en partie (13 octobre, POM2) : un voyage Sierra lancé
  par le menu finit en « FREE JOURNEY: NOT RANKED » (octet de région 0 de la
  carte Sierra historique pris pour un voyage libre par le module de fin) ;
  deux messages se collent sans séparateur (« BEAR IN YOUR AREAIT IS TOO
  DARK TO TRAVEL », « BEAR IN YOUR AREABEAR IN YOUR AREA! »).
- [ ] REST et les chargements de simulation doivent garder l'image DHGR à
  l'écran au lieu du rideau texte (`load_totals_quiet` existe déjà).
- [ ] Simplifier le menu de sélection au démarrage (forme à préciser).
- [x] Noms des auteurs originaux et du portage sur la page de chargement.
- [ ] Sauvegarde et reprise d'une partie (jamais implémentées) ; place
  disque à prévoir avec la direction 3.
- [ ] Messages : refus précis, retours persistants, causes d'arrêt nommées
  pour toutes les actions ; parcours avec un nouveau joueur
  ([NEOWILDERNESS_ERGONOMIE.md](docs/NEOWILDERNESS_ERGONOMIE.md)).
- [ ] Lot 8 ([MENUS.md](docs/MENUS.md)) : pilote d'événements joystick et
  clavier, barre de verbes et listes dans les quatre lignes 80 colonnes,
  fenêtres DHGR posées sur le paysage et effacées par l'instantané, à la
  place des écrans 40 colonnes ; les commandes tapées restent reconnues.
  Exigence à fixer avant de coder : exploiter bien mieux les quatre lignes
  de texte 80 colonnes du bas de l'écran pour ce contrôle (MENUS.md § 4,
  barre de verbes sur une ligne = premier jet).
- [ ] Aide en jeu par région (HELP, phrase de faune, noms d'espèces) et
  orientation nocturne (`LOOK STARS`).

**Terminé quand :** une partie complète se joue au joystick seul, une
partie sauvegardée reprend à l'identique, et chaque fin de partie inscrit
son score.

## 5. Qualité commune et livraison

Transversal : chaque direction maintient ses tests et sa documentation.
Reste ici ce qui est commun.

- [ ] Suite de tests (12 minutes) scindée en niveaux : rapide (modèles
  Python et bancs), complète (émulateur), originale (`test-original`) ;
  documenter ce que chaque test garantit.
- [ ] Garde-fous : page zéro, pile, banques, interruptions, RESET, QUIT,
  machine incompatible, `/RAM` existant.
- [ ] Machines : IIc jamais testé (a2shot n'émule que le IIe) ; une machine
  réelle avec carte vidéo DHGR ; `make run` dans l'application POM2.
- [ ] Git : tout est encore non commité ; découper en commits par direction,
  ignorer `build/` et `original/`, garder `dist/NEOWILDERNESS.po`.
- [ ] Livraison : README, CHANGELOG, relevé mémoire final, crédits des
  données originales et limites restantes ; `dist/NEOWILDERNESS.po`.

**Terminé quand :** la suite rapide passe en moins de deux minutes, la
suite complète est verte, le `.po` livré démarre sur IIe et IIc, et le
dépôt contient l'historique des directions.
