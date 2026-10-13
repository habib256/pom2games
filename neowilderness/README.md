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
Le paysage est désormais dessiné en **DHGR 16 couleurs** (lot 3) : ciel en
zones tramées, sol, neige et eau en trois paliers de distance, bois, sprites
originaux colorés, soleil et Lune, dans dix humeurs choisies selon la hauteur
du soleil et de la Lune et la couverture nuageuse (jour, heure dorée,
coucher, crépuscules, nuit claire de pleine Lune…). Le bandeau de boussole
et les panneaux de survie sont dessinés en vrais pixels couleur (lot 4) :
petite police DHGR, N rose, index jaune, jauges en couleur et alertes sur
bandeau orange, sans pixels HGR doublés ni franges ; les quatre lignes de
messages sont affichées en cellules 80 colonnes ; TOPO reste en HGR simple
(lot 4). Les règles sont inchangées : l'état de simulation est
identique, octet pour octet, à celui de la version HGR/DOS 3.3 de référence,
et aucune lecture disque n'a lieu pendant la partie.

Mesures (secondes invitées à environ 1 MHz, [BASELINE_128K.json](docs/BASELINE_128K.json)
contre [BASELINE_HGR.json](docs/BASELINE_HGR.json)) : STATUS 8,90 → 0,24 s,
LOOK R 7,99 → 1,85 s, WALK 1 H 70,71 → 9,10 s ; premier écran jouable
45,1 → 28,9 s. Le DHGR coûte 2 à 5 % de plus que le HGR 128 Ko
([BASELINE_DHGR.json](docs/BASELINE_DHGR.json)) : LOOK R 1,93 s, rotation
22,5° 1,11 s, WALK 1 H 9,30 s, VIEW 5,85 s. Le plan mémoire et ces chiffres
sont détaillés dans [MEMORY.md](docs/MEMORY.md), le rendu dans
[DHGR.md](docs/DHGR.md) ; captures du jeu par `python3 tools/game_shots.py`
(`build/dhgr/game_*.png`).

Le [TODO](TODO.md) fixe l’ordre des lots et leurs critères de validation.
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
```

Le volume contient `PRODOS` (2.4.3), `NEOWILD.SYSTEM` (chargeur ; le nom
`NEOWILDERNESS.SYSTEM` dépasse 15 caractères) et `NEOWILD.DAT`, lu une seule
fois au démarrage (17 appels MLI). 127 blocs restent libres.
`BOOT_PACKING=raw|lz|auto` choisit la compression des enregistrements
(`auto` par défaut, mesuré le plus rapide). Une machine sans 128 Ko ou un IIe
non amélioré reçoit un message puis revient à ProDOS ; QUIT et Ctrl-RESET
rétablissent le texte, les banques, /RAM, le bitmap, le vecteur RESET et la
page zéro avant le retour au lanceur. Un /RAM contenant des fichiers n'est
effacé qu'après confirmation (Y).

La comparaison d'état utilise `build/reference-hgr/` (disque HGR/DOS 3.3 de
`../wilderness` et son fichier de symboles), local et ignoré par Git. Les
données originales requises suivent la procédure `make originals` /
`make extract` héritée ; elles restent locales et ignorées par Git.

## Cartes et règles

- TOPO/T : carte graphique globale ; le tracé actuel est reconstruit depuis
  la grille du port, il n’est pas une reproduction exacte du TOPO original.
- MAP : carte locale centrée sur le joueur, extension propre au port.
- Simulation : conserver les règles natives et leurs tests pendant la
  migration mémoire et vidéo.

Code sous GPL-3.0, voir [LICENSE](../LICENSE). Les références et données
originales conservent leurs droits et crédits existants.
