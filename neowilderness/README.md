# Neowilderness

**Développement actif : NeoWildernessXL (800 Ko).** La version 140 Ko
est arrêtée depuis le 16 octobre 2026 ; `make` construit désormais XL seule.
Les descriptions de l’édition 140 Ko ci-dessous sont historiques.

**EQUIPMENT** : septième onglet, accessible avec les flèches du haut.
Entrée active sa liste ; chaque objet distingue porté, en mains et en usage,
avec actions, charge et préparation de la chasse.

Port séparé de Wilderness pour Apple IIe enhanced 128 Ko et IIc, avec
rendu DHGR et modules préchargés en RAM, en deux éditions (14 octobre
2026), même jeu et même chargeur : **Neowilderness**
(`dist/NEOWILDERNESS.po`, disquette 5,25" de 140 Ko, Disk II : la Sierra
Nevada seule, la préparation, cinq parties) et **NeoWildernessXL**
(`dist/NEOWILDERNESSXL.po`, disquette 3,5" de 800 Ko : IIe avec carte
contrôleur 3,5" (UniDisk 3.5/Liron, SuperDrive) ou IIc avec lecteur
SmartPort, IIc Plus ; les six scénarios). Le premier objectif est de
supprimer les lectures disque pendant les commandes et déplacements
courants.

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
mémoire, retours d'écrans sans redessin de la vue. Le paysage reste visible pendant
les calculs de repos et d'attente ; le rideau ne masque que le redessin. Les quatre lignes du
bas sont une surface de commande (lot 8, étape 2) : à gauche les
descriptions (le dernier message, la ligne de stock ou la commande telle
que le jeu la lira), à droite la grille des verbes et leurs listes
(depuis le 14 octobre ; RETURN, TAB ou la flèche bas l'ouvre, TAB ou haut
sur sa première rangée la referme, flèches, RETURN, Échap ; toute action
s'y trouve ; CATCH propose aussi sa durée, puis prépare l'appât et le piège
ou le matériel de pêche avant de lancer la capture ; seuls les objets accessibles sont proposés, les commandes
tapées restent acceptées). Navigation par pages : sur une ligne vide,
gauche et droite tournent la vue, la flèche haut retrouve la dernière page du haut ouverte
(STATUS, avec les affections et leurs soins ; OBJECTS, le sol de la case
à gauche, HANDS et PACK dans deux post-it à droite sur XL, chaque objet
avec son poids ; sélections et défilement mémorisés ; Entrée active les listes,
puis RETURN ouvre les actions, les quantités et la confirmation, H propose la main, la commande tapée
comme au clavier ; les jauges de poids, de volume PACK et HANDS et les vivres
emportés ; CRAFT ; HELP ; OPTIONS ; MENU, avec la distance aux
rangers ; en boucle par gauche/droite ; bas ou Échap revient à la vue ;
sur NeoWildernessXL chaque bloc est un post-it en MouseText), la flèche bas ouvre la
grille, puis, bas sous sa dernière rangée, les pages du bas (TOPO et MAP,
gauche/droite de l'une à l'autre ; haut ou Échap revient à la vue ; MAP
défile par I, J, K, L, C recentre).
**LOOK UP / LOOK DOWN** (`LOOK U`, `LOOK D`, `LOOK
AHEAD`, `PAN U`/`PAN D`, ou UP/DOWN dans la liste LOOK de la grille)
inclinent la vue de 96 lignes comme l'original : en l'air, le sommet
descend au bas de l'écran, le soleil haut devient visible, sans sprite ni
arbre ; vers le bas, le relief proche remplit l'écran et l'épave reste
entière. Trois angles, aucun temps de jeu, refus « NOT NOW. » devant un
ours au contact ; la marche remet la vue à niveau
([LOOK_UPDOWN.md](docs/LOOK_UPDOWN.md)). Les règles sont
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
choisie est lu (son paquet dans `NEOWILD.DAT`, 14 à 17 blocs) : la première vue
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

Lot 1 de fidélité ([SCENARIOS.md](docs/SCENARIOS.md) § 11) : `P` au menu
pose, après le choix de la région et du niveau, les questions de
préparation de l'original (date et heure choisies ou tirées, jeu normal ou
mode recherche, sexe, poids, carrure, taille, âge, pouls, fréquences de la
faune et des orages) et donne le verdict de forme ; tout voyage autre qu'un
scénario au niveau 4 tire selon le niveau, comme l'original, la blessure du
crash, le lot de l'épave, les usages des consommables, la date et l'heure,
le premier front et le vent, et annonce le terrain et la difficulté
(module de préparation compressé en fin de `NEOWILD.DAT`, lu seulement pour ces voyages). RETURN, RETURN garde le
premier voyage figé de l'original.
Lot 9 ([SAVE.md](docs/SAVE.md)) : **SAVE** et **RESTORE** gardent cinq
parties sur la disquette du jeu, comme l'original. Le numéro est demandé
(`SAVE THE JOURNEY AS GAME 1-5?`) ou tapé à la suite (`SAVE 2`,
`RESTORE 2`) ; une partie occupée est décrite (région, heures) avant
`REPLACE IT? Y/N`. RESTORE reprend la partie octet pour octet (horloge,
santé, météo, objets, faune, hasards) et redessine la vue ; il refuse une
partie d'une autre région (`GAME 1: SIERRA NEVADA ONLY.`), d'une autre
version du jeu ou abîmée, sans rien changer. Une disquette protégée
affiche `DISK WRITE-PROTECTED: NOT SAVED.`. Ce sont, avec la fin de
voyage, les seuls accès disque de la partie : SAVE ≈ 4,5 s, RESTORE 6 à
9 s (la vue est redessinée). L'aide (HELP) ne les mentionne pas encore :
son module est plein.

Lot 7 de fidélité, orientation ([ORIENTATION.md](docs/ORIENTATION.md)) :
LOOK N/E/S/W et LOOK AZ exigent, comme l'original, une aide en usage
(« FIRST PUT DIRECTION AID IN USE. » sinon ; au départ, aucune) :
`USE COMPASS` (cap magnétique), `USE WATCH` (estimation par la montre et le
soleil, Y/N puis un azimut) ou `USE SHADOW` (bâton par jour clair : E/W
puis la durée d'observation, qui passe). La boussole et la montre
s'excluent ; le temps qui passe range la montre et le bâton. `LOOK SUN`
tourne la vue vers le soleil, `LOOK STARS` vers le pôle céleste (sud au
sud de l'équateur) par nuit claire, `LOOK COMPASS` donne le cap
magnétique, `LOOK WATCH`/`ALTIMETER` renvoient à STATUS, `USE MAP` (ou
`LOOK MAP`) ouvre la carte TOPO. Sans lumière, montre, carte et altimètre
refusent (« INSUFFICIENT LIGHT »).

Le [TODO](TODO.md) organise le travail restant en cinq directions, fidélité à l’original et image en priorité, avec leurs critères de fin.
Le [README HGR hérité](README_HGR.md), le [backlog hérité](TODO_HGR.md)
et le [changelog](CHANGELOG.md) documentent le point de départ ; leurs
mentions HGR/DOS décrivent la version de référence.

## Feu, lumière et eau (lot 2)

Les commandes de camp suivent l'original, messages compris
([CAMP.md](docs/CAMP.md)) :

| Commande | Effet |
|---|---|
| `USE MATCHES`, `USE FUEL`, `USE GLASS` | Mettre en usage : une allumette, une once de combustible ; la loupe exige ciel clair, plein air et soleil à 30° (15 minutes). Les allumettes, le combustible, la loupe et la lampe cessent d'être en usage dès que le temps passe |
| `MAKE FIRE`, `BUILD FIRE` | Allumettes (ou loupe) en usage ; ni dans l'eau ni sur un sol rocheux enneigé ; sous la pluie ou par vent de 41 mph et plus, combustible en usage ou abri ; 30 minutes |
| `USE FIRE` / `DOUSE FIRE`, `STOP FIRE` | Se tenir près du feu (+25 °F, lumière) / l'éteindre ; on ne quitte pas un feu allumé |
| `MAKE STICKS`, `USE STICKS` | Bâtons (sol dégagé ou bois), 30 minutes |
| `USE FLASHLIGHT`, `USE FIRSTAID KIT` | Lumière (une utilisation des piles) ; la trousse exige de la lumière |
| `USE STOVE`, `USE UTENSILS`, `BOIL WATER` | Réchaud (combustible et feu ou allumettes en usage), ustensiles, puis eau bouillie en 15 minutes (prévient la giardiase) |
| `GET RAIN`, `GET SNOW`, `GET ICE`, `GET WATER`, `FILL CANTEEN` | Eau sûre de pluie ou de neige, eau non traitée de rivière ou de lac (160 oz posées sur la case), cactus, sinon recherche d'une durée donnée ; gourde de 64 oz |
| `USE RAINCOAT`, `USE GND COVER`, `MAKE WATER` | Condenser de l'eau, de jour par ciel clair |
| `DRINK WATER`, `DRINK RAIN` | Au plus 0,2 × poids du corps (33 oz) par gorgée ; l'eau non traitée peut donner la giardiase, d'autant plus bas qu'on est |

## Fabrication (lot 3)

Les recettes de MAKE suivent l'original, temps et messages compris
([CRAFT.md](docs/CRAFT.md)) ; les objets fabriqués restent sur la case :

| Commande | Effet |
|---|---|
| `MAKE HUT`, `MAKE IGLOO`, `MAKE TRENCH` | Hutte (en forêt), igloo (sur la neige), tranchée ; ni dans l'eau, ni à l'épave, ni au poste ; 4 000 k / ((lumière + 2)(hache en usage + 2) × santé) minutes, k = 2, 3, 1 (169, 254, 84 de jour au départ) |
| `USE HUT`, `ENTER HUT`, `EXIT HUT` (IGLOO, TRENCH) | Entrer, sortir ; dedans, l'air + 15 °F (l'igloo : 35 °F) et le risque animal × 0,1 |
| `USE TENT`, `EXIT TENT` | Monter la tente sur la case (30 minutes) et y entrer, en sortir |
| `MAKE CLUB`, `MAKE SPEAR`, `MAKE BOW`, `MAKE AXE` | En forêt ; lance, arc et hache demandent une corde ou le matériel de pêche (sauf Birmanie, Nouvelle-Guinée, Bolivie) ; 21 à 852 minutes selon la santé, le couteau en usage et la lumière |
| `USE BOW`, `USE SPEAR`, `USE CLUB`, `USE ROCK` | L'arme en main et en usage pour `KILL GAME` ou `KILL FISH` (p = 0,2 ; 0,1 ; jamais) et pour `ATTACK` d'un animal (seuils de l'original par arme), jusqu'à ce que le temps passe |
| `GET`, `CARRY`, `PACK`, `DROP` (BOW, SPEAR, CLUB, ROCK, SPLINT) | En main, dans le sac, au sol de la case ; l'arc, la lance et l'attelle restent sur leur case, le gourdin se perd en partant ; une pierre attend sur toute case de terre ; `WEAR SPLINT` |
| `MAKE SPLINT` | Attelle, 53 minutes avec la hache ou à l'épave, sinon en forêt avec une corde |
| `MAKE SUNGLASSES`, `MAKE SUNSCREEN` | Visière d'écorce, boue ; sol dégagé ou forêt, 30 minutes |

Sur NeoWildernessXL, la hutte, l'igloo, la tranchée et la tente posée se
voient dans le paysage (sprites de l'original, sur leur case et de loin
jusqu'à 8 cases) ; l'édition de 140 Ko n'a pas la place de ces sprites et
ne les dessine pas. Vêtements de peau, corde, radeau, gourde et ustensiles :
lot 5.

La page **CRAFT** (lettre R, entre OBJECTS et HELP) range ces recettes en
trois groupes, avec leur état en MouseText (coche : possible ici, X
inverse : il manque quelque chose, losange : déjà fait) et le temps que
MAKE passerait maintenant ; à droite, la recette choisie : son effet, ce
qu'il faut (coché ou non), ce dont dépend le temps et ce qui le ralentit ;
RETURN tape `MAKE x`.

Le joystick pilote désormais la vue, la grille, les pages et le menu de
choix du voyage (bouton 0 : valider, bouton 1 : retour). Les dialogues P/G
et les confirmations en jeu se choisissent aux directions ; haut/bas règle
les invites numériques. Dans MAP, Entrée ouvre l'exploration : directions
pour défiler, Entrée pour recentrer, retour pour quitter ce mode. Le nom
du score peut se composer avec haut/bas et droite. La préparation
personnalisée et quelques attentes particulières restent à raccorder ; le
plan complet, dont les actions et quantités d'OBJECTS, est dans le TODO.

## Construction

```sh
make            # ../dist/NEOWILDERNESS.po (140 Ko, 280 blocs) et ../dist/NEOWILDERNESSXL.po (800 Ko, 1 600 blocs)
make run        # POM2, préréglage IIe enhanced
make inspect    # catalogue du volume, enregistrements et placement auxiliaire
make test       # tests a2shot sur //e : images DHGR, état comparé à la référence HGR
make -f dhgr.mk test   # banc DHGR indépendant (primitives, humeurs, disque de démonstration)
make -f stars.mk test  # banc des étoiles (référence Python, module horaire, tracé)
make -f hof.mk test    # banc du score et du hall of fame (fichier, écrans, disque protégé)
```

`make test` lance aussi les bancs des étoiles et du hall of fame
(≈ 7 minutes au total dans POM2).

Les deux volumes contiennent `PRODOS` (2.4.3), `NEOWILD.SYSTEM` (chargeur
et menu ; le nom `NEOWILDERNESS.SYSTEM` dépasse 15 caractères),
`NEOWILD.DAT` (tronc commun, paquets de région et préparation du voyage
dans un seul fichier ; un seul paquet est lu après le choix au menu), le
module de fin de partie `NEOWILD.END`, le hall of fame `NEOWILD.HOF` (un
bloc, réécrit en place), le module de SAVE/RESTORE `NEOWILD.SAV` et les
cinq parties `NEOWILD.S1`…`S5` (réécrites en place, lot 9) ; XL ajoute
`NEOWILD.BLK` (CAMP, MEDVIEW, TREE et ORIENT, rarement chargés, lus par
bloc dans leur fenêtre au lieu d'occuper le stock auxiliaire ; une copie
fichier par fichier qui déplacerait ce fichier est refusée au démarrage,
docs/MEMORY.md § 14). 36 appels MLI avant la partie ; pendant la partie,
aucun sauf SAVE (8), RESTORE (6) et, sur XL, les lectures de
`NEOWILD.BLK` ; 9 en fin de voyage (module, lecture et écriture du hall of
fame). Volumes : 140 Ko, 224 blocs sur 280 ; XL, 305 blocs sur 1 600
(`make inspect` : blocs et mémoire libre par paquet). POM2 et a2shot
démarrent XL sur la carte SmartPort 3,5" du slot 5 (a2shot choisit le
contrôleur d'après la taille de l'image), le 140 Ko sur Disk II. La construction
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
  du TOPO original. Flèche haut, Échap, Retour ou Espace rendent la vue
  intacte ; gauche ou droite passe à MAP.
- MAP : carte locale centrée sur le joueur, en texte 80 colonnes plein
  écran (40 × 24 cases, animée pendant WALK/SWIM), extension propre au port.
  Étiquette en inverse en haut à gauche : minutes de marche, case, cap
  magnétique, site sous P. Symboles : `=` eau, `T` bois, `t` broussailles,
  `.,:;+*^#` relief du plus bas au plus haut, `P` joueur, `C` épave,
  `H` cabane, `R` rangers. I, J, K, L font défiler, C recentre ; gauche
  ou droite passe à TOPO, flèche haut revient à la vue.
- Simulation : conserver les règles natives et leurs tests pendant la
  migration mémoire et vidéo.

## Commandes de soin (lot 13)

En plus de USE *produit médical*, EAT/DRINK FLAGYL, SALT TABLETS, QUININE,
STOP BLEEDING, SHIELD EYES, LOWER HEAD et SUCK VENOM
([../wilderness/README.md](../wilderness/README.md#commandes)) :

| Commande | Effet |
|---|---|
| USE SPLINT | Poser une attelle (bras ou jambe cassés), 30 minutes ; MAKE SPLINT la fabrique |
| USE PRESSURE | Compresser une coupure, 30 minutes |
| USE AXE / USE KNIFE | Mettre l'outil en usage sur la case (en main) |
| CUT BODY / COOL BODY | Inciser une morsure avec la hache ou le couteau en usage ; sans durée |
| WET BODY [*n* OZ] | Se mouiller : déjà fait sous un front météo ou dans l'eau ; sinon eau de rivière ou de lac à portée, ou *n* onces versées de la gourde ; soigne le coup de soleil avec l'eau bue |
| DRY / WARM *vêtement* | Conseil de l'original : suspendre le vêtement au soleil ou près d'un feu |
| HANG *vêtement* | Suspendre un vêtement à un arbre (il est déposé) ; mouillé, hors de la pluie, il sèche au soleil |

Les objets utilisés passent en main (les lunettes de soleil sur le visage).
Les alertes de l'original (faim, soif, fatigue, frissons, sueur,
détérioration, état sérieux, noyade, sommeil forcé) s'ajoutent sous le
résultat ; un joueur épuisé s'endort de lui-même de 3 à 8 heures.
L'infection des coupures non soignées et la malaria (Birmanie,
Nouvelle-Guinée, Bolivie) peuvent se déclarer
([IMPLEMENTATION.md](docs/IMPLEMENTATION.md) « Soins, alertes et maladies
(lot 13) »).

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
