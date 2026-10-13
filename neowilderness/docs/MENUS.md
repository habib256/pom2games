# Joystick, menus et fenêtres DHGR (lot 8)

Plan détaillé du lot 8 de [TODO.md](../TODO.md). Date : 13 octobre 2026.
Statut : étape 2 réalisée le 13 octobre 2026 (§ 4) ; étapes 1 (joystick) et 3 à 6 à réaliser.

Objectif : rendre Neowilderness jouable entièrement au joystick (ou au
clavier par les flèches, Entrée et Échap), avec une interface qui n'oblige
plus à taper les commandes, et des fenêtres DHGR dessinées sur le paysage au
lieu des écrans texte 40 colonnes. Le modèle est l'interface des jeux AGI de
Sierra sur Apple II 128 Ko (King's Quest, Space Quest) : fenêtres de texte
alignées sur les octets, posées sur l'image et effacées par recopie d'une
sauvegarde de l'image, barre de menus et déplacement au joystick.

Le lot s'appuie sur l'état du lot 7 ([MEMORY.md](MEMORY.md) § 8 et 9) et sur
l'ergonomie des lots 1 à 5 de
[NEOWILDERNESS_ERGONOMIE.md](NEOWILDERNESS_ERGONOMIE.md), qu'il ne remet pas
en cause : les commandes tapées restent reconnues et documentées.

## 1. Point de départ

Ce qui existe déjà dans l'arbre de travail et sert directement :

| Élément | Emplacement | Réutilisation |
|---|---|---|
| Boucle d'attente du prompt (`get_line` / `idle`), flèches gauche/droite = rotation de 22,5° sur une ligne vide, Échap = effacement | `src/game.s`, segment résident | Point d'entrée du pilote d'événements (§ 3) |
| Analyseur de commandes (vocabulaire `wildvoc.bin`, module INPUT `wildinp.bin`, 382 octets libres depuis le hall of fame) | fenêtre `$5800` | Les menus composent une ligne dans `inbuf` et appellent le même analyseur (§ 2) |
| Quatre lignes de texte 80 colonnes (rangées 20 à 23, primitives `t_*` de `src/dhgr.s`, LOWPAGE) | `$0200-$03B8` | Barre de verbes et listes de choix en inverse (§ 4) |
| Police DHGR de 7 rangées et rendu de champs colorés (`dhgr_pack`, panneaux de WILDHUD) | `tools/dhgr_font.py`, `wildhud.bin` 1 739 octets | Texte des fenêtres (§ 5) |
| Instantané de la vue (rangées 0 à 159, deux banques, 80 octets par rangée, 12 800 octets) posé par `topo_open` et restauré par `topo_close` en 0,24 s | carte langage auxiliaire, `src/topo_dhgr.s` | Fond de sauvegarde sous les fenêtres (§ 5) |
| Retour d'INVENTORY sans redessin (0,26 s), STATUS/HELP/MAP en 6 ms | `src/sites.s`, `src/inventory.s` | Référence de latence à ne pas dégrader |
| Émulateurs de test : `joy:X,Y` (axes dans [−1, 1]) et `btn:N,0|1` (boutons) | `dev/tools/a2run/a2run.c`, `dev/tools/a2shot/a2shot.cpp` | Tests du joystick sans matériel (§ 7) |

Ce qui manque : aucun code de lecture du port de jeu dans `neowilderness/`
(Arkabreakout lit la souris IIc par le firmware, pas les manettes), aucun
rectangle ni fenêtre DHGR, aucun menu en jeu.

Contraintes mémoire à la fin du lot 7 (MEMORY.md § 9.9) :

| Zone | Libre | Remarque |
|---|---:|---|
| RAM principale résidente | 86 octets | fragments de 2 à 40 octets (WILDLO 40, LOWPAGE 23, TEXT 11) ; les étoiles ont pris 172 octets de WILDLO |
| Stock des modules (RAM auxiliaire et banque 2 de la carte langage principale) | 1 313 octets (Burma), 2 557 (Sierra) | plus grand morceau 464 (Burma) à 1 244 (Sierra) : un nouveau module de 2 Ko n'y tient pas sans libérer de la place |
| Carte langage principale, banque 2 | 135 octets (`$DF79-$DFFF`) ; 1 octet depuis le ciel peuplé (liste de 160 étoiles et tracé en `$DE18-$DFFE`, MEMORY.md § 9.9) | à côté du code de tracé des étoiles, exécutable en place |
| Volume `NEOWILDERNESS.po` | 34 blocs | 17 Ko, suffisant pour un module chargé à la demande |
| Fenêtre SIM pendant TOPO | 1 860 octets | inutilisable pendant le jeu courant |

Conclusion : tout code d'interface nouveau vit dans un module de la fenêtre
`$5800` et, pour entrer dans le stock auxiliaire, doit **remplacer** les
écrans 40 colonnes (`wildscr.bin` 2 040 octets : STATUS, HELP, inventaire ;
rideau et primitives 40 colonnes résidentes, ≈ 245 octets) plutôt que s'y
ajouter.

## 2. Principes

- **Les menus produisent des commandes texte.** Un choix dans un menu écrit
  la même chaîne qu'au clavier (`WALK 30 MIN`, `GET AXE`, `LOOK N`) dans
  `inbuf`, puis appelle `module_input_command`. Rien ne change dans
  l'analyseur, la simulation, les tirages aléatoires ni les demi-pas.
  `test_reference_state.py` doit rester vert sans modification.
- **Le clavier reste complet.** Toute commande tapée reste acceptée ; les
  flèches, Entrée et Échap pilotent les menus exactement comme le joystick.
  Les tests existants, écrits au clavier, continuent de passer.
- **Aucune lecture disque pendant un pas.** Un chargement à l'ouverture d'un
  menu (geste du joueur, § 6) est acceptable et compté par `mli_reads` ; un
  chargement pendant WALK, SWIM, REST ou une rotation ne l'est pas.
- **Aucune avance du temps** pour ouvrir, parcourir ou fermer un menu ou une
  fenêtre, comme pour STATUS et INVENTORY aujourd'hui.
- **Une seule fenêtre à la fois**, sans recouvrement ni découpage : pas de
  gestionnaire de fenêtres général. Une fenêtre est un rectangle aligné sur
  les groupes d'octets, un bord, du texte, et une restauration par recopie.
- **Lisible sans couleur** : l'élément sélectionné est en inverse (texte) ou
  dans une bande de couleur contrastée (fenêtre), jamais signalé par la
  couleur seule.

## 3. Pilote d'événements : joystick et clavier

Une routine `ui_event` renvoie un code parmi : rien, haut, bas, gauche,
droite, bouton 0 (valider), bouton 1 (annuler), ou un caractère clavier.

Matériel du port de jeu (IIe, IIc) :

- Déclenchement des monostables par `$C070` (PTRIG), puis lecture des bits 7
  de `$C064` (PDL0, axe X) et `$C065` (PDL1, axe Y) **dans la même boucle**,
  avec un compteur par axe. Deux lectures séparées exigeraient 3 ms d'attente
  entre elles pour laisser les timers 558 se décharger. Coût maximal d'une
  lecture : environ 2,8 ms (255 tours de 11 cycles), ce qui bloque le
  processeur mais est sans effet au prompt, où rien ne tourne.
- Boutons : `$C061` (PB0, aussi pomme ouverte) et `$C062` (PB1, aussi pomme
  fermée), bit 7. Le IIc n'a pas de troisième bouton.
- Zone morte large : centre théorique 128, mais les manettes Apple II sont
  mal centrées et dérivent. Seuils retenus : < 64 et > 192, à revoir après
  essai sur une manette réelle ; prévoir un réglage par deux constantes.
- Répétition : un premier délai (environ 0,4 s) puis une cadence
  (environ 0,12 s) tant que l'axe reste engagé, mesurées en itérations de la
  boucle d'attente ; un retour au centre réarme. Un bouton n'est pris qu'une
  fois par pression (front descendant → montant).

Comportement au prompt, ligne vide :

| Geste | Clavier équivalent | Action |
|---|---|---|
| Gauche / droite | flèches | rotation de 22,5°, comme aujourd'hui |
| Haut | flèche haut | ouvre la barre de verbes (§ 4) |
| Bas | flèche bas | affiche STATUS (§ 5) |
| Bouton 0 | Entrée | ouvre la barre de verbes |
| Bouton 1 | Échap | ferme ce qui est ouvert ; au prompt vide, rien |

Avec du texte saisi, la manette ne fait rien : le joueur qui tape finit sa
ligne au clavier. Les touches des écrans existants (1 à 4, N, B, C, M, I, S,
T) restent.

Placement : la lecture brute du port (trigger, boucle double, boutons,
≈ 60 octets) doit être atteignable depuis la boucle `idle` résidente. Elle
tient dans les fragments résidents hors réserve des étoiles (31 octets en
`$03B1` et 12 en `$B9F4` sont trop petits : il faut d'abord libérer la
primitive 40 colonnes `t_cout` ou déplacer `get_line` entier dans le module
d'interface, § 6). La répétition, la zone morte et la table des gestes vont
dans le module d'interface.

Interdit : lire le port pendant la simulation ou pendant un tracé DHGR
(perte de 3 ms par lecture, et le ruban de boussole lit `heading` à chaque
rotation). Le pilote n'est appelé que depuis la boucle d'attente du prompt et
les boucles d'attente des écrans.

## 4. Barre de verbes et listes dans les lignes texte

**Réalisé le 13 octobre 2026 (étape 2, au clavier ; `src/menu.s`,
`tests/test_menu_bar.py`).** Les rangées 20 à 23 forment une surface de
commande en deux colonnes : la grille à gauche, les descriptions à droite.

```
WALK  SWIM  LOOK  REST  WAIT  EAT     | TRAVEL: 18 MINUTES.
DRINK GET   TAKE  WEAR  DROP  USE     | REQUESTED TRAVEL TIME ENDED.
CLIMB HANG  LOWER STATUS INVENT TOPO  |
MAP   HELP  QUIT                      | FOOD 192 OZ  WATER 64 OZ  HERE 0/0
```

- **Colonne gauche (rangées 20 à 23, colonnes 0 à 37) : la grille.** Au
  niveau 1, les verbes : d'abord les verbes contextuels quand ils
  s'appliquent (`EXIT` dans la cabane, `ENTER` sur sa case, `IGNORE SCARE
  ATTACK` avec un animal sur la case, mêmes conditions que le bandeau de
  survie), puis `WALK SWIM LOOK REST WAIT EAT DRINK GET TAKE WEAR DROP USE
  CLIMB HANG LOWER STATUS INVENT TOPO MAP HELP QUIT` ; un verbe à objets
  dont la liste serait vide n'est pas proposé (pas de médicament : pas de
  `USE` ; pas d'eau accessible : pas de `DRINK`). Six cases par rangée,
  largeur 6 proportionnelle (un libellé de six lettres prend une colonne de
  plus : toute suite de six verbes tient en 38 colonnes), quatre rangées
  visibles (les 21 verbes et jusqu'à trois contextuels sans défilement),
  défilement par rangée au-delà ; la colonne 38 porte le séparateur, `^` ou
  `V` quand des rangées sont hors de vue. La case choisie est en inverse.
  Au niveau 2, la liste du verbe ouvert remplace la grille : durées `10 MIN
  20 MIN 30 MIN 1 H 2 H 4 H 8 H` (WALK, SWIM, REST, WAIT), directions `LEFT
  RIGHT BACK AHEAD NORTH EAST SOUTH WEST` (LOOK), `TREE DOWN` (CLIMB), les
  objets accessibles ici en trois cases de 12 (EAT, DRINK, GET, TAKE, WEAR,
  DROP, USE : emportés, ou au sol ou pendus sur la case, dans un groupe que
  le verbe ne vise pas déjà ; EAT : provisions et médicaments ; DRINK :
  l'eau) ; au niveau 3 les onces `2 OZ 4 OZ 8 OZ 12 OZ 16 OZ 24 OZ 32 OZ
  48 OZ` (EAT d'une provision, DRINK WATER). `ENTER`, `EXIT`, `HANG`,
  `LOWER`, `INVENT` complètent leur commande (` SHELTER`, ` FOOD`, `ORY`).
- **Colonne droite (rangées 20 à 23, colonnes 40 à 78) : les
  descriptions.** `message` y place le dernier message mot par mot (retour
  à la ligne entre les mots, `|` force une rangée tant qu'il en reste une,
  sinon vaut une espace ; un mot plus long qu'une rangée est coupé à la
  rangée, la colonne 79 reste libre). Quand le message laisse la rangée 23
  vide, elle reçoit la ligne de stock `FOOD n OZ  WATER n OZ  HERE f/w`
  (provisions et eau emportées, puis au sol sur la case), et, pendant
  qu'une commande est tapée ou composée, `> ` suivi de la commande telle
  que l'analyseur la lira (sans curseur : le texte en tient lieu) ; l'invite
  numérique du module INPUT (`prompt`) y écrit `> ` et reçoit les chiffres.
  Le rapport de charge (poids, volume) occupe trois rangées.

Modes de `get_line` : ligne tapée (flèches gauche/droite = rotation sur une
ligne vide, RETURN, haut ou TAB ouvre la grille, bas affiche STATUS, Échap
vide la ligne) ; grille (flèches, RETURN choisit, Échap remonte d'un niveau
puis ferme, TAB ferme depuis n'importe quel niveau, une lettre revient à la
ligne tapée) ; une commande issue de la
grille la laisse ouverte pour la suivante, une commande tapée la referme.
Les menus produisent le texte du clavier dans `inbuf` (laissé intact entre
deux commandes, comme dans la référence : `test_reference_state.py` le
compare) ; l'objet choisi dans une liste est aussi transmis par
`menu_noun`, lu par `resolve_menu` avant `resolve_noun`, car les noms
affichés (`COTTN SOCKS`, `DOWN PARKA`) ne sont pas des mots du vocabulaire.
Aucune avance du temps, aucun tirage, aucune lecture disque pendant la
navigation (`test_menu_bar.py` compare l'état obtenu par la grille à celui
des mêmes commandes tapées).

Mémoire ([MEMORY.md](MEMORY.md) § 11) : la partie résidente (boucle
clavier, rangée 23, `prompt`, état) en `$BA00-$BDFF`, l'ancien tampon
d'entrées-sorties ProDOS du chargeur (qui lit désormais avec `$AB00`) ;
la grille, ses listes et ses tables (1 474 octets) dorment dans les lignes
HGR 176 à 191 des deux banques, jamais affichées ni dessinées, et sont
recopiées en `$B000-$B5FF` (haut de la fenêtre SIM, libre entre deux pas de
simulation) à chaque invite ; la colonne de résultat (`msg_*`) est dans
WILDGAME, treize octets de page zéro en `$F0-$FC`. Le pilote joystick (§ 3, étape 1) reste à faire : il s'insère
dans la boucle `idle` de `menu.s` (`prompt_key` / `menu_key` prennent déjà
les codes des flèches, RETURN et Échap).

Sous-menus, par verbe :

| Verbe | Niveau 2 | Niveau 3 | Commande produite |
|---|---|---|---|
| WALK, SWIM | durée : `10 MIN  30 MIN  1 H  2 H  4 H  …` | — | `WALK 30 MIN` |
| LOOK | `N  NE  E  SE  S  SW  W  NW  L  R  B` | — | `LOOK NE` |
| REST | durée | — | `REST 1 H` |
| EAT, DRINK | objets consommables accessibles (sac, main, sol) | quantité : `4 OZ  8 OZ  16 OZ  ALL` | `EAT CHEESE 8 OZ` |
| GET, TAKE, WEAR, DROP | objets admissibles pour ce verbe, selon leur emplacement | — | `GET AXE` |
| STATUS, INVENTORY, TOPO, MAP, HELP | écran ou fenêtre (§ 5) | — | `STATUS` |
| QUIT | confirmation existante | — | `QUIT` |

Les listes d'objets sont construites depuis les tables d'inventaire déjà
utilisées par INVENTORY (noms, emplacements, quantités) et ne dépassent pas
une rangée de 79 caractères par page ; au-delà, gauche/droite en bord de
rangée changent de page. Les durées et quantités sont des listes fixes ; la
saisie libre reste possible au clavier. Les verbes contextuels (ENTER
SHELTER, EXIT SHELTER, IGNORE, SCARE, ATTACK) apparaissent en tête de barre
seulement quand ils sont applicables, en reprenant les conditions du bandeau
de survie (`summary.s`).

Une commande refusée par l'analyseur affiche son refus comme aujourd'hui ;
la barre se referme et le prompt revient, avec le refus visible.

## 5. Fenêtres DHGR

Module WILDWIN (fenêtre `$5800`, ≤ 2 048 octets) avec quatre primitives :

- `win_open x, y, w, h, couleur` : rectangle plein aligné sur les groupes
  d'octets (un groupe = 4 octets sur deux banques = 7 pixels couleur ; `x`
  et `w` en groupes, `y` et `h` en rangées, dans les rangées 16 à 159), bord
  d'un pixel couleur dans une seconde couleur. Écriture par octets entiers
  avec `dhgr_pack`, comme le ruban : pas de lecture-modification-écriture.
- `win_text col, rangée, chaîne` : police de 7 rangées, avance de 4 pixels,
  encre et fond ; une ligne de fenêtre = 8 rangées (7 + 1 d'interligne).
  Capacité pleine largeur : 20 groupes × 7 / 4 = 35 caractères sur
  (160 − 16) / 8 = 18 lignes, soit l'équivalent des écrans 40 colonnes
  actuels sans leurs marges.
- `win_select ligne` : bande de sélection (fond inversé sur une ligne), pour
  les listes au joystick.
- `win_close` : recopie depuis l'instantané des seules rangées couvertes
  (80 octets par rangée, deux banques), au lieu des 160 rangées de
  `topo_close`. Pour une fenêtre de 100 rangées : 8 000 octets copiés,
  environ 0,15 s à 1 MHz.

L'instantané est pris à l'ouverture de la **première** fenêtre d'une séquence
(coût équivalent à `topo_open`), puis partagé : ouvrir STATUS, passer à
MEDICAL, revenir, fermer ne prend qu'un instantané. Il est invalidé par toute
rotation, déplacement ou changement d'humeur, comme le drapeau `tp_valid`
l'indique déjà pour TOPO. Si l'instantané n'est pas disponible (carte
langage occupée par TOPO), la fermeture redessine la vue, comme `topo_close`
avec C posé.

Palette : fond gris clair (10) ou blanc (15), bord bleu foncé (2), texte noir
(0), sélection blanc sur bleu foncé, avertissements blanc sur rouge (1),
comme les panneaux du lot 4. Les couleurs sont des constantes du module.

Fenêtres prévues, en remplacement des écrans 40 colonnes :

| Écran actuel | Fenêtre | Contenu |
|---|---|---|
| STATUS (40 colonnes, 24 lignes) | pleine largeur, 18 lignes | mêmes sections et unités (conditions, besoins, CARRIED/HERE, environnement) ; M bascule vers MEDICAL |
| INVENTORY (40 colonnes, groupes 1 à 4) | pleine largeur | quatre groupes à onglets choisis par gauche/droite, douze objets par page, capacités restantes en pied ; haut/bas sélectionnent un objet, bouton 0 ouvre `GET / TAKE / WEAR / DROP` pour cet objet |
| HELP (trois pages 40 colonnes) | pleine largeur | mêmes trois pages, gauche/droite tournent les pages |
| Messages longs (mort, victoire, bilan) | centrée, 6 à 8 lignes | texte existant, bouton 0 ferme |
| QUIT | centrée, 3 lignes | confirmation existante (Y / N) |

MAP reste en texte 80 colonnes (deux caractères par cellule, déjà adapté) et
TOPO reste plein écran : ils ne sont pas des fenêtres.

Coût de tracé estimé pour STATUS complet (≈ 600 glyphes à ≈ 200 cycles,
plus le rectangle) : environ 0,15 s, à mesurer. Le retour doit rester
inférieur à 0,3 s, le niveau d'INVENTORY aujourd'hui.

## 6. Plan mémoire du lot

| Contenu | Taille estimée | Où |
|---|---:|---|
| Lecture brute du port de jeu | ≈ 60 | résident (après libération, § 3) |
| Pilote : zone morte, répétition, table des gestes | ≈ 150 | module INPUT (446 libres) ou WILDWIN |
| Barre de verbes, sous-menus, listes d'objets, composition de `inbuf` | ≈ 900 | module WILDMENU ou WILDWIN |
| Primitives de fenêtre (rectangle, bord, texte, sélection, fermeture) | ≈ 700 | module WILDWIN |
| Contenu STATUS, INVENTORY, HELP réécrit pour `win_text` | ≈ 1 900 | remplace `wildscr.bin` (2 040) et le code 40 colonnes de `wildsta.bin` |
| Libéré : rideau, `t_cout` et primitives 40 colonnes, `text_mode40` | ≈ −245 | résident |

Bilan visé : un ou deux modules de 2 Ko de plus dans le stock auxiliaire,
compensés par la disparition de `wildscr.bin` et l'amaigrissement de
`wildsta.bin`. Si le bilan reste positif de plus de 676 octets (Burma), deux
options, dans l'ordre :

1. Charger WILDMENU depuis le disque à l'ouverture de la barre (4 blocs, une
   lecture MLI, ≈ 0,2 s) et le garder dans la fenêtre `$5800` jusqu'à la
   commande suivante. 36 blocs sont libres sur le volume. Compté dans
   `mli_reads` ; `test_resident.py` tolère cette lecture sur le seul geste
   d'ouverture.
2. Réduire l'instantané réservé (12 800 octets) : hors périmètre, à ne pas
   engager sans mesure, car TOPO et les fenêtres en dépendent.

Tout ajout résident est mesuré dans `build/wild.map` avant d'être retenu,
et la police de 7 rangées n'existe qu'en un exemplaire (celui de WILDHUD ou
une copie dans WILDWIN : pas les deux, à arbitrer selon la place dans le
module).

## 7. Tests

- `test_joystick.py` : `joy:` et `btn:` sur a2run et a2shot ; rotation
  gauche/droite par l'axe X (même `heading` qu'avec les flèches), zone morte
  (axe à ±0,2 : aucun événement), répétition (axe maintenu : n événements en
  t itérations), bouton 0 au prompt vide (barre ouverte), bouton 1
  (fermeture), aucune lecture du port pendant un WALK (sonde sur `$C070`
  si l'émulateur l'expose, sinon compteur `pdl_reads`).
- `test_menu_bar.py` : parcours de chaque verbe au clavier et au joystick ;
  chaque choix produit exactement la chaîne attendue dans `inbuf` ; l'état
  de simulation est identique à la même commande tapée
  (`test_reference_state`) ; aucune avance du temps pendant la navigation ;
  verbes contextuels présents ou absents selon la case (cabane, animal).
- `test_windows.py` : ouverture et fermeture de chaque fenêtre, image
  identique avant et après (comparaison des deux banques sur les 160
  rangées, comme `test_dhgr_video.py`), contenu de STATUS et INVENTORY
  identique au texte 40 colonnes du lot 7 (mêmes champs, mêmes valeurs),
  fermeture sans instantané (redessin), latence mesurée.
- Les tests existants (`test_interface.py`, `test_input.py`,
  `test_feedback.py`) sont adaptés pour lire les fenêtres DHGR à la place
  de la page texte 40 colonnes, par un décodeur `tools/dhgr_ui.py` étendu à
  la police de 7 rangées sur fond uni.
- Captures `build/dhgr/game_menu_*.png` et `game_window_*.png` par
  `tools/game_shots.py`.

## 8. Ordre de réalisation

| Étape | Contenu | Condition de fin |
|---|---|---|
| 1 | Pilote d'événements : port de jeu, zone morte, répétition, boutons ; rotation au joystick | `test_joystick.py` vert sur a2run et a2shot ; aucun octet de plus dans la simulation ; `build/wild.map` publié |
| 2 | **Fait (13 octobre 2026, au clavier)** : grille de verbes et listes dans les lignes texte 80 colonnes ; composition de `inbuf` | Toute commande du jeu accessible sans taper ; `test_menu_bar.py` et `test_reference_state.py` verts ; clavier inchangé |
| 3 | Module WILDWIN : rectangle, bord, texte, sélection, fermeture partielle depuis l'instantané | `test_windows.py` : image restaurée à l'identique ; latences mesurées |
| 4 | STATUS, HELP, QUIT et messages longs en fenêtres ; retrait de `wildscr.bin` et des primitives 40 colonnes | Bilan mémoire nul ou négatif en RAM principale ; `test_interface.py` adapté vert |
| 5 | INVENTORY en fenêtre avec actions par objet ; listes d'objets des sous-menus partagées avec elle | Un objet se prend, se porte et se dépose sans taper ; `test_feedback.py` adapté vert |
| 6 | Parcours d'un nouveau joueur au joystick seul (les douze étapes de NEOWILDERNESS_ERGONOMIE.md), mesure de la manette réelle, réglage de la zone morte | Parcours complété sans clavier ; constantes publiées ; CHANGELOG et MEMORY.md § 10 à jour |

Les étapes 1 et 2 ne touchent pas au plan mémoire des modules et sont
livrables seules : elles donnent un jeu jouable au joystick. L'étape 3 est
mesurée avant d'engager l'étape 4, qui est le seul point où le lot peut
échouer sur la place : si WILDWIN et le contenu réécrit ne tiennent pas dans
ce que libèrent les écrans 40 colonnes, le repli est l'option 1 du § 6
(chargement à l'ouverture), documenté comme tel.

**Terminé lorsque :** le jeu se joue du menu de démarrage à la fin de partie
au joystick seul et au clavier seul, les états de simulation restent
identiques à la référence pour les mêmes commandes, aucune lecture disque
n'a lieu pendant un pas, les latences d'ouverture et de fermeture des
fenêtres sont publiées, et la mémoire résidente n'a pas diminué par rapport
au lot 7.
