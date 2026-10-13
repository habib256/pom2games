# Neowilderness

Port séparé de Wilderness pour Apple IIe enhanced 128 Ko et IIc, avec
rendu DHGR et modules préchargés en RAM. Les commandes et déplacements de
la partie ne lisent plus jamais le disque.

## État actuel

Les sources reprennent `../wilderness/` au 13 octobre 2026, synchronisées
avec sa tête Git. Les lots 1 à 5 du [TODO](TODO.md) sont terminés et la
validation du lot 6 est faite sur IIe enhanced émulé :

- **ProDOS 8 et 128 Ko** : `NEOWILD.SYSTEM` refuse une machine sans 128 Ko
  ou un IIe non amélioré, garde l'introduction pendant le chargement, lit
  `NEOWILD.DAT` en 16 appels MLI, puis précharge tous les modules, les
  sprites, TOPO et la simulation vierge en RAM auxiliaire. Un chargement de
  module est une copie RAM (au plus 18,1 cycles par octet).
- **Zéro lecture disque en jeu** : aucun appel MLI entre le préchargement
  et QUIT, compteurs et entrée `$BF00` surveillés, sur le scénario ordinaire,
  un trajet crash → rangers complet (repas, eau, gourde à la rive, repos,
  cabane, rencontres, morsure soignée, traversée à la nage, nuit et
  changement de jour, arrivée) et chaque retour d'écran.
- **Paysage DHGR 16 couleurs** (lot 3) : ciel en zones tramées, sol, neige
  et eau en trois paliers de distance, bois, sprites originaux colorés,
  soleil et Lune, dans dix humeurs choisies selon la hauteur du soleil et de
  la Lune et la couverture nuageuse.
- **Bandeau couleur** (lot 4) : boussole et panneaux de survie en vrais
  pixels couleur, petite police DHGR, N rose, index jaune, jauges et alertes
  colorées, sans pixels HGR doublés ni franges. Les quatre lignes de
  messages restent du texte 40 colonnes imprimé dans les cellules impaires
  du mode 80 colonnes.
- **TOPO en DHGR** (lot 4), dessiné à l'ouverture depuis la carte en
  mémoire : teintes d'altitude, courbes tous les 400 pieds, eau, bois,
  épave, cabane, rangers, position du joueur et légende. MAP reste la carte
  locale textuelle, centrée sur le joueur, avec défilement et C.
- **Écrans** : STATUS (et sa page médicale), INVENTORY, HELP, MAP, TOPO et
  la confirmation de QUIT rendent la même image (deux banques DHGR) et le
  même état, sans avance du temps ni tirage aléatoire.
- **Géographie fine résidente** (lot 5) sur les cartes natives (carte
  Sierra de comparaison, `mkmap.py --native`) : atlas compressé de 154
  tuiles (6,1 à 6,7 Ko) et quatre tuiles décodées en cache dans la carte
  langage auxiliaire ; la carte livrée garde la grille 112 × 84.
- **Règles inchangées** : l'état de simulation est identique, octet pour
  octet, à celui de la version HGR/DOS 3.3 de référence après chaque étape
  du scénario ordinaire et pour chaque commande mesurée.

Limites : le IIc n'est pas émulé par a2shot et n'a pas été lancé dans POM2
(`make run APPLE2_PRESET=iic`), aucune machine réelle n'a été essayée ; les
messages ne sont pas en vrai texte 80 colonnes ; la carte livrée n'est pas
native, et le format natif refuse une eau au-dessus du niveau 63. Le double
tampon n'est pas possible dans le plan mémoire (16 Ko demandés). Mémoire
restante : 578 octets en RAM principale résidente, 285 en RAM auxiliaire
principale, 4 Ko en carte langage banque 2 ; 132 blocs libres sur le volume
([MEMORY.md](docs/MEMORY.md) § 11).

### Performances

Cycles invités POM2 à fréquence nominale identique (1 020 484 cycles/s),
session fraîche par commande, NATURE 0, `tools/profile_actions.py --profile`
([BASELINE_DHGR.json](docs/BASELINE_DHGR.json)). La référence est le
disque HGR/DOS 3.3 figé (`build/reference-hgr/`, ][+) ; ses lectures sont
des chargements de modules (`overlay_reads`, le BLOAD direct de la feuille
TOPO n'y est pas compté). Pour Neowilderness, « disque » compte les appels
MLI, « transferts » les copies RAM de modules (nombre, octets, temps de la
boucle de copie) et « calcul » tout le reste. Le décodage n'apparaît qu'au
démarrage (LZ) et sur les cartes natives (tuiles de géographie fine,
comptées sous ROM par l'outil) : aucun sur la carte par défaut mesurée.

| Commande | Référence HGR : cycles (s) | dont DOS | Lectures | Neowilderness DHGR : cycles (s) | Disque | Transferts RAM | Calcul | Gain |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| VIEW | 5 785 423 (5,67 s) | 0,00 s | 0 | 5 905 667 (5,79 s) | 0 | 0 | 5,79 s | 0,98 |
| LOOK R | 8 152 218 (7,99 s) | 6,03 s | 2 | 1 938 673 (1,90 s) | 0 | 2 (3 947 o, 0,06 s) | 1,84 s | 4,21 |
| LOOK B | 11 528 728 (11,30 s) | 8,77 s | 3 | 2 515 344 (2,46 s) | 0 | 3 (5 081 o, 0,08 s) | 2,39 s | 4,58 |
| → (22,5°) | 1 078 846 (1,06 s) | 0,00 s | 0 | 1 105 803 (1,08 s) | 0 | 0 | 1,08 s | 0,98 |
| ← (22,5°) | 810 026 (0,79 s) | 0,00 s | 0 | 828 996 (0,81 s) | 0 | 0 | 0,81 s | 0,98 |
| STATUS | 9 219 190 (9,03 s) | 8,84 s | 3 | 243 464 (0,24 s) | 0 | 3 (6 078 o, 0,09 s) | 0,15 s | 37,87 |
| WALK 1 H | 71 492 409 (70,06 s) | 60,63 s | 20 | 9 417 362 (9,23 s) | 0 | 20 (43 989 o, 0,67 s) | 8,56 s | 7,59 |
| TOPO | 10 921 434 (10,70 s) | 10,65 s | 1 + BLOAD | 1 023 256 (1,00 s) | 0 | 1 (1 531 o, 0,02 s) | 0,98 s | 10,67 |
| Démarrage | 45,11 s jusqu'à l'invite | | | 28,26 s jusqu'à l'invite | 16 appels MLI, 50 982 o | | | 1,60 |

Le rendu DHGR coûte 2 % de plus que le HGR (VIEW, flèches) ; tout le reste
du gain vient de la disparition de DOS. TOPO est plus lent à dessiner que
l'ancienne copie de feuille (1,0 s contre 0,17 s au lot 3) mais ne lit plus
le disque. Démarrage : ProDOS 8,70 s, préchargement 12,56 s (disque 9,82 s,
décodage LZ 2,10 s, copies 0,64 s), initialisation et premier rendu 7,00 s
(`tools/profile_loading.py`) ; la valeur de référence (45,11 s) est la
mesure des lots 1–2 ([BASELINE_128K.json](docs/BASELINE_128K.json)), non
refaite. Les états de simulation après chaque commande sont identiques à
ceux de la référence.

Le [TODO](TODO.md) fixe l’ordre des lots et leurs critères de validation.
Le [README HGR hérité](README_HGR.md), le [backlog hérité](TODO_HGR.md)
et le [changelog](CHANGELOG.md) documentent le point de départ ; leurs
mentions HGR/DOS décrivent la version de référence. Le rendu est détaillé
dans [DHGR.md](docs/DHGR.md), la géographie dans
[GEOGRAPHY.md](docs/GEOGRAPHY.md), le plan mémoire et ses garde-fous dans
[MEMORY.md](docs/MEMORY.md) ; captures du jeu par
`python3 tools/game_shots.py` (`build/dhgr/game_*.png`).

## Construction

```sh
make            # ../dist/NEOWILDERNESS.po : volume ProDOS 5,25 pouces (280 blocs)
make run        # POM2, préréglage IIe enhanced
make run APPLE2_PRESET=iic   # POM2, préréglage //c (vérification manuelle, non faite)
make inspect    # catalogue du volume, enregistrements et placement auxiliaire
make test       # tests a2shot sur //e : images DHGR, état comparé à la référence HGR
make -f dhgr.mk test   # banc DHGR indépendant (primitives, humeurs, disque de démonstration)
```

Options : `SEED` et `LEVEL` choisissent la carte générée (1985 et 4 par
défaut), `BOOT_PACKING=raw|lz|auto` la compression des enregistrements
(`auto` par défaut, mesuré le plus rapide). Le Makefile ne construit que des
cartes héritées ; une carte native (géographie fine résidente) se construit
à la main :

```sh
python3 tools/mkmap.py --native --seed 1985 --level 4 build/native.bin
python3 tools/build_disk.py --out ../dist/NEOWILDERNESS.po --map build/native.bin
```

`build_disk.py` refuse un atlas de plus de 10 287 octets ; une carte native
générée occupe 162 blocs (12 enregistrements).

Le volume contient `PRODOS` (2.4.3), `NEOWILD.SYSTEM` (chargeur ; le nom
`NEOWILDERNESS.SYSTEM` dépasse 15 caractères) et `NEOWILD.DAT`, lu une seule
fois au démarrage (16 appels MLI, 50 982 octets). 132 blocs restent libres.
Une machine sans 128 Ko ou un IIe non amélioré reçoit un message puis
revient à ProDOS ; QUIT et Ctrl-RESET rétablissent le texte, les banques,
/RAM, le bitmap, le vecteur RESET et la page zéro avant le retour au
lanceur. Un /RAM contenant des fichiers n'est effacé qu'après confirmation
(Y).

La comparaison d'état et les mesures de référence utilisent
`build/reference-hgr/` (disque HGR/DOS 3.3 de `../wilderness` et son fichier
de symboles), local et ignoré par Git. Les sprites sont extraits de la face
Journey originale (`build/JOURNEY.dsk`, `make extract`) et la comparaison
Sierra (`test_geography.py`, `make test-original`) demande les données
originales ; elles suivent la procédure `make originals` / `make extract`
héritée et restent locales, ignorées par Git.

## Cartes et règles

- TOPO/T : carte graphique globale en DHGR, générée depuis la grille du port
  à chaque ouverture ; ce n’est pas une reproduction exacte du TOPO original.
- MAP : carte locale centrée sur le joueur, extension propre au port.
- Simulation : règles natives et tests conservés pendant la migration
  mémoire et vidéo ; états comparés à la référence HGR (`test_reference_state.py`).

## Crédits

*Wilderness: A Survival Adventure* (Electric Transit, 1985, © 1984) est
l'œuvre de Wesley Huntress, Charles Kohlhase et Peter Farson. Le moteur de
rendu 3D de Wilderness a été développé par Wesley Huntress et Charles
Kohlhase, deux chercheurs du JPL (NASA) ayant travaillé sur les
trajectoires et l'imagerie des missions Mariner et Voyager. L'algorithme
adapte les techniques de modélisation altimétrique spatiale aux contraintes
extrêmes du MOS 6502 (1,023 MHz, 64 Ko de RAM, aucun coprocesseur
mathématique). Neowilderness en conserve la projection et les 140 rayons
([ANALYSE.md](docs/ANALYSE.md)).

Code sous GPL-3.0, voir [LICENSE](../LICENSE). Les références et données
originales conservent leurs droits et crédits existants.
