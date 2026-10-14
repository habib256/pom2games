# Neowilderness

Port séparé de Wilderness pour Apple IIe enhanced 128 Ko et IIc, avec
rendu DHGR et modules préchargés en RAM. Le premier objectif est de supprimer
les lectures disque pendant les commandes et déplacements courants.

## État actuel

Les sources reprennent `../wilderness/` au 13 octobre 2026, synchronisées
avec sa tête Git (transitions texte/HGR, introduction conservée pendant le
chargement, correctifs de nage et de tests). Les lots 1 et 2 du [TODO](TODO.md)
sont en place : le jeu démarre sous ProDOS 8 sur Apple IIe enhanced ou IIc
128 Ko, précharge tous ses modules, la simulation vierge et la feuille TOPO
en RAM auxiliaire, puis ne lit plus jamais le disque pendant la partie.
Le paysage est dessiné en **DHGR 16 couleurs** (lot 3) : ciel en
zones tramées, sol, neige et eau en trois paliers de distance, bois, sprites
originaux colorés, soleil et Lune, dans dix humeurs choisies selon la hauteur
du soleil et de la Lune et la couverture nuageuse (jour, heure dorée,
coucher, crépuscules, nuit claire de pleine Lune…). L'interface est en DHGR
elle aussi (lot 4) : ruban de boussole et panneaux de survie en couleur,
avertissements sur bande rouge, messages en vrai texte 80 colonnes, carte
MAP en 80 colonnes, feuille TOPO calculée à l'ouverture depuis la carte en
mémoire, retours d'écrans sans redessin de la vue. Les quatre lignes du
bas sont une surface de commande (lot 8, étape 2) : à gauche la grille des
verbes et leurs listes (RETURN, flèche haut ou TAB l'ouvre, TAB la
referme, flèches, RETURN, Échap ; toute action s'y trouve, seuls les objets accessibles sont
proposés, les commandes tapées restent acceptées), à droite les
descriptions : le dernier message, la ligne de stock ou la commande telle
que le jeu la lira. Les règles sont
inchangées : l'état de simulation est identique, octet pour octet, à celui
de la version HGR/DOS 3.3 de référence, et aucune lecture disque n'a lieu
pendant la partie.

Mesures (secondes invitées à environ 1 MHz, [BASELINE_128K.json](docs/BASELINE_128K.json)
contre [BASELINE_HGR.json](docs/BASELINE_HGR.json)) : STATUS 8,90 → 0,24 s,
LOOK R 7,99 → 1,85 s, WALK 1 H 70,71 → 9,10 s ; premier écran jouable
45,1 → 28,9 s. Le DHGR coûte 2 à 5 % de plus que le HGR 128 Ko
([BASELINE_DHGR.json](docs/BASELINE_DHGR.json)) : LOOK R 1,93 s, rotation
22,5° 1,11 s, WALK 1 H 9,30 s, VIEW 5,85 s ; l'interface du lot 4 y ajoute
au plus 3 % (WALK 1 H 9,60 s), TOPO s'ouvre en 2,99 s et se referme en
0,24 s. Le plan mémoire et ces chiffres sont détaillés dans
[MEMORY.md](docs/MEMORY.md), le rendu dans [DHGR.md](docs/DHGR.md) et
[TOPO_DHGR.md](docs/TOPO_DHGR.md) ; captures du jeu par
`python3 tools/game_shots.py` (`build/dhgr/game_*.png`, interface
`game_ui_*.png`).

Lot 7 ([SCENARIOS.md](docs/SCENARIOS.md), étapes 1 à 6 réalisées ; reste
la validation finale du lot 6) : au démarrage, après le chargement du tronc
commun, un **menu** propose les six scénarios originaux (British Columbia,
Sierra Nevada, Burma, New Guinea, Bolivia, Chile ; les cinq autres que la
Sierra sur des cartes reconstituées) avec leur meilleur score, un voyage
libre (région et niveau au choix, hasard renouvelé, jamais classé), le
**hall of fame** (`H` : cinq meilleurs voyages par scénario) et le retour à
ProDOS ; puis le niveau 1–10 (RETURN = 4). Seul le paquet de la région
choisie est lu (`NEOWILD.R1`…`R6`, 14 à 17 blocs) : la première vue
apparaît 9,2 à 9,8 s après le choix. Chaque région a sa faune (deux à
quatre espèces, règles de rencontre et de réaction de l'original), ses
couleurs de sol, d'eau et de végétation, son texte de départ ; un arrêt de
marche ou de repos nomme sa cause (« BEAR IN YOUR AREA! », « YOU FIND
FISH. »). La nuit, le ciel montre les **étoiles** d'un catalogue de 282
(jusqu'à la magnitude 3,5 ; jusqu'à 160 levées à la fois), calculées pour
la date, l'heure et la position (Polaris en Sierra, Croix du Sud en
Bolivia), aucune de jour, au crépuscule ni sous les nuages, seulement les
21 plus brillantes sous la pleine Lune. Une partie terminée (mort, arrivée, QUIT)
affiche le bilan et le **score**, enregistre le voyage dans `NEOWILD.HOF`
(saisie du nom s'il entre dans le top 5), puis ramène au menu. Captures :
`python3 tools/game_shots.py --regions` et `--stars`.

Le [TODO](TODO.md) organise le travail restant en cinq directions, fidélité à l’original et image en priorité, avec leurs critères de fin.
Le [README HGR hérité](README_HGR.md), le [backlog hérité](TODO_HGR.md)
et le [changelog](CHANGELOG.md) documentent le point de départ ; leurs
mentions HGR/DOS décrivent la version de référence.

## Construction

```sh
make            # ../dist/NEOWILDERNESS.po : volume ProDOS 5,25 pouces (280 blocs)
make run        # POM2, préréglage IIe enhanced
make inspect    # catalogue du volume, enregistrements et placement auxiliaire
make test       # tests a2shot sur //e : images DHGR, état comparé à la référence HGR
make -f dhgr.mk test   # banc DHGR indépendant (primitives, humeurs, disque de démonstration)
make -f stars.mk test  # banc des étoiles (référence Python, module horaire, tracé)
make -f hof.mk test    # banc du score et du hall of fame (fichier, écrans, disque protégé)
```

`make test` lance aussi les bancs des étoiles et du hall of fame
(≈ 7 minutes au total dans POM2).

Le volume contient `PRODOS` (2.4.3), `NEOWILD.SYSTEM` (chargeur et menu ; le
nom `NEOWILDERNESS.SYSTEM` dépasse 15 caractères), le tronc commun
`NEOWILD.DAT`, lu au démarrage, les six paquets de région `NEOWILD.R1`…`R6`
(carte, bois, sprites d'animaux, correctifs de faune, couleurs, textes), dont
un seul est lu après le choix au menu, le module de fin de partie
`NEOWILD.END` et le hall of fame `NEOWILD.HOF` (un bloc, réécrit en place).
36 appels MLI avant la partie, aucun pendant ; 9 en fin de voyage (module,
lecture et écriture du hall of fame). 34 blocs restent libres
(`make inspect` : blocs et mémoire libre par paquet). La construction
demande les en-têtes de région et les cartes reconstituées
(`make regions`, données originales locales). `BOOT_PACKING=raw|lz|auto`
choisit la compression des enregistrements (`lz` par défaut depuis les
étoiles : 23 blocs de moins qu'`auto` et une première vue plus rapide,
mesurés). Une machine sans 128 Ko ou un IIe non amélioré reçoit un message
puis revient à ProDOS. La fin d'une partie (QUIT, mort, arrivée) passe par
le score et le hall of fame, puis relance `NEOWILD.SYSTEM` : retour au
menu, partie neuve. `Q` au menu et Ctrl-RESET rétablissent le texte, les banques, /RAM, le
bitmap, le vecteur RESET et la page zéro avant le retour au lanceur. Un /RAM
contenant des fichiers n'est effacé qu'après confirmation (Y). Les tests
répondent au menu « 1, RETURN » (Sierra Nevada, première ligne, niveau 4 :
`tests/common.py`, `menu_keys`, qui traduit un numéro de région en touche ;
RETURN seul choisit aussi la Sierra).

La comparaison d'état utilise `build/reference-hgr/` (disque HGR/DOS 3.3 de
`../wilderness` et son fichier de symboles), local et ignoré par Git. Les
données originales requises suivent la procédure `make originals` /
`make extract` héritée ; elles restent locales et ignorées par Git.

## Cartes et règles

- TOPO/T : carte graphique globale en DHGR, calculée à chaque ouverture
  depuis la grille du port (≈ 3 s) ; elle n’est pas une reproduction exacte
  du TOPO original. Échap, Retour ou Espace rendent la vue intacte.
- MAP : carte locale centrée sur le joueur, en texte 80 colonnes plein
  écran (40 × 24 cases, animée pendant WALK/SWIM), extension propre au port.
  Étiquette en inverse en haut à gauche : minutes de marche, case, cap
  magnétique, site sous P. Symboles : `=` eau, `T` bois, `t` broussailles,
  `.,:;+*^#` relief du plus bas au plus haut, `P` joueur, `C` épave,
  `H` cabane, `R` rangers. Flèches/WASD font défiler, C recentre.
- Simulation : conserver les règles natives et leurs tests pendant la
  migration mémoire et vidéo.

Code sous GPL-3.0, voir [LICENSE](../LICENSE). Les références et données
originales conservent leurs droits et crédits existants.
