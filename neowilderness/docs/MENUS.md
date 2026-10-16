# Joystick, menus et fenêtres DHGR (lot 8)

Plan détaillé du lot 8 de [TODO.md](../TODO.md) (section « Hors lots :
interface et expérience de jeu » ; à ne pas confondre avec le lot de jeu 8 d'ORIGINAL_GAP.md,
HELP et score). Date : 13 octobre 2026.
Statut au 14 octobre 2026 : étape 2 réalisée (§ 4 ; grille passée à
droite, navigation par pages du haut et du bas) ; étapes 3 et 4 (fenêtres
DHGR à la place des écrans 40 colonnes) remplacées par les pages
80 colonnes (`src/pages.s`, le module SCREENS supprimé) ; étape 5
(INVENTORY avec actions par objet) réalisée le 16 octobre 2026 par la
page OBJECTS de transfert (§ 5.1) ; étape 1 (joystick) raccordée le 16 octobre 2026 dans l'émulateur (§ 10),
validation sur manette réelle et étape 6 (parcours intégral) à terminer.

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
| Haut | flèche haut | pages du haut, STATUS d'abord (§ 5) ; flèche bas y revient à la vue |
| Bas | flèche bas | ouvre la grille des commandes (§ 4) ; dans la grille, bas descend les rangées, et sous la dernière ferme la grille et ouvre les pages du bas, TOPO d'abord (§ 5) ; flèche haut y revient à la vue, grille fermée |
| Bouton 0 | Entrée (ou TAB) | ouvre la barre de verbes (§ 4) |
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

Interdit : mesurer les axes pendant la simulation ou pendant un tracé DHGR
(perte de 3 ms par lecture, et le ruban de boussole lit `heading` à chaque
rotation). Le pilote n'est appelé que depuis la boucle d'attente du prompt et
les boucles d'attente des écrans.

## 4. Barre de verbes et listes dans les lignes texte

**Réalisé le 13 octobre 2026 (étape 2, au clavier ; `src/menu.s`,
`tests/test_menu_bar.py`) ; grille rationalisée le 15 octobre 2026
(`src/grid.s`, `tests/test_grid_play.py`).** Les rangées 20 à 23 forment
une surface de commande en deux colonnes : les descriptions à gauche, la
grille à droite.

```
IT TOOK A WHILE TO MAKE YOUR FIRE.     | WALK  LOOK  REST  WAIT  EAT   DRINK
                                       | GET   wear  drop  USE   MAKE  DOUSE
                                       | CARE  BOIL  CLIMB
FOOD 192 WATER 64 LOCAL 0/0 OZ         |
```

### 4.1 La grille : onze verbes fixes, puis les verbes du moment

- **Verbes de base, à case fixe.** Rangée 20 : `WALK` (ou `SWIM`, dans la
  même case, quand le joueur est dans l'eau ou que le prochain demi-pas du
  cap y entre : le test même de TRAVEL, `module_swim_land`, gardé en cache
  par position et cap), `LOOK`, `REST`, `WAIT`, `EAT`, `DRINK` ; rangée 21 :
  `GET`, `WEAR`, `DROP`, `USE`, `MAKE`. Un verbe de base qui ne peut rien
  ici reste à sa place, **grisé** : écrit en minuscules (`wear`, `drop`),
  il se choisit comme les autres mais RETURN ne fait que biper (`BELL1`)
  — la main du joueur retrouve chaque verbe au même endroit. Sont grisés :
  EAT sans rien à manger, DRINK sans eau accessible, GET sans rien à
  prendre ici, WEAR sans vêtement, DROP sans rien d'emporté, USE sans objet
  que USE traite, MAKE quand ni feu ni eau ne peuvent se faire ici
  (`kind_ok`, `mk_fire`, `mk_water`). Depuis le 15 octobre 2026 (lot 3)
  l'arc, la lance, le gourdin, la pierre et l'attelle comptent aussi : la
  pierre étant au sol de toute case de terre tant que le joueur n'en porte
  pas, GET et USE n'y sont plus grisés (le test résident de `member` est
  un sur-ensemble, les listes de GRID sont exactes).
- **Verbes contextuels, par urgence**, à la suite (`verb_table`, entrée
  marquée `K_BASE` ou non) ; ils n'apparaissent que s'ils peuvent aboutir :
  l'animal de la case (`KILL`, `SCARE`, `IGNORE`), le feu (`DOUSE FIRE`),
  les soins (`CARE` : une affection active), le travail du lot 4 et du
  lot 2 (`COOK` avec de la nourriture et un feu ou le réchaud, `BOIL` avec
  un feu ou le réchaud en usage, les ustensiles et de l'eau, `SKIN` une
  carcasse, `CATCH` et `KILL` du gibier ou du poisson présent), l'arbre
  (`CLIMB`, `HANG FOOD` avec le sac porté, `LOWER FOOD` avec le sac pendu
  ici), la cabane (`ENTER SHELTER`, `EXIT SHELTER`).
- **Hors de la grille**, toujours tapables : `TAKE` (GET range au sac ou
  prend en main, voir les listes), `ATTACK` (le `KILL` de l'animal),
  `TASTE` (dans la liste d'EAT), `MAKE STICKS` (ne sert à rien en jeu),
  `PACK`, `CARRY`, `REMOVE`. STATUS, INVENTORY, TOPO, MAP, HELP et QUIT ont
  quitté la grille le 14 octobre 2026 : les flèches et la page MENU y
  mènent (§ 5).

Six cases par rangée, largeur 6 proportionnelle (un libellé de six lettres
prend une colonne de plus), quatre rangées visibles, défilement par rangée
au-delà ; la colonne 39 porte le séparateur, `^` ou `V` quand des rangées
sont hors de vue. La case choisie est en inverse. La grille est refaite à
chaque invite et après chaque rotation (`build_verbs`) ; elle n'est jamais
effacée : seules les cases qui changent sont réécrites.

### 4.2 Les listes

RETURN sur un verbe ouvre sa liste (niveau 2), qui remplace la grille ;
une liste d'une seule entrée est sautée (l'entrée est choisie d'office).

| Verbe | Liste (niveau 2) | Niveau 3 | Commande produite |
|---|---|---|---|
| WALK, SWIM, REST, WAIT | `10 MIN 20 MIN 30 MIN 1 H 2 H 4 H 8 H` | — | `WALK 30 MIN` |
| LOOK | `LEFT RIGHT BACK AHEAD UP DOWN NORTH EAST SOUTH WEST SUN STARS` | — | `LOOK UP` |
| GET | les sources d'eau, les piles du lot 4, les objets au sol, pendus ici ou en main ; l'arc, la lance, le gourdin, la pierre, l'attelle au sol ici (lot 3) | — | `PACK x`, ou `CARRY x` (sac, gourde, pas de sac, sac plein) ; `GET BOW` pour le second jeu (en main, le GET de l'original) |
| WEAR | les vêtements non portés, puis les portés précédés de `-` | — | `WEAR x` ; `-x` : `PACK x` (l'enlever) |
| EAT | les piles de nourriture d'abord, puis les provisions et les remèdes oraux | `TASTE`, puis les onces (au plus ce qu'il y a) | `EAT MUSHROOMS 8 OZ`, `TASTE MUSHROOMS` |
| DRINK | les sources (une seule : sautée) | onces, au plus min(eau ici, poids ÷ 5) | `DRINK WATER 8 OZ` |
| DROP | ce qui est emporté, second jeu compris (porté, sac, main) | — | `DROP AXE`, `DROP BOW` |
| USE | les objets que USE traite, puis l'arc, la lance, le gourdin, la pierre et l'attelle ici ou emportés, puis `FIRE` quand un feu brûle | — | `USE MATCHES`, `USE ROCK`, `USE FIRE` |
| MAKE | ce qui peut se faire ici : `FIRE`, `WATER` | — | `MAKE FIRE` |
| BOIL | les onces (au plus le contenu de la gourde, sinon la pile ici) | — | `BOIL WATER 8 OZ` |
| CATCH | GAME ou FISH présents ici | `10 MIN 20 MIN 30 MIN 1 H 2 H 4 H 8 H` | `CATCH FISH 30 MIN` (appât et matériel en usage d’abord) |
| KILL, SKIN, COOK | leurs cibles nommées (gibier, poisson, carcasse, pile) | — | `KILL GAME` |
| CLIMB | `TREE` ou `DOWN`, celle qui s'applique | — | `CLIMB TREE` |
| CARE | — : STATUS (ses rangées MEDICAL), focus sur la première affection active (§ 5) | — | `STATUS` |

CATCH ouvre sa liste de durées après la cible (16 octobre 2026). Le choix
ne lance aucune préparation avant RETURN sur la durée ; Échap revient sans
consommer ni avancer le temps. L'appât et le piège ou le matériel de pêche
sont ensuite mis en usage si nécessaire. Le dernier des cinq emplacements
de la file garde l'index de durée : CATCH n'utilise que trois étapes au plus.
La saisie directe accepte les mêmes durées ; sans durée, la question
originale permet toujours les fractions d'heure.

Les portions d'EAT, DRINK et BOIL commencent à **1 OZ**, puis 2, 4, 8,
12, 16, 24, 32 et 48 oz (16 octobre 2026). Seules celles qui respectent
le stock disponible et, pour DRINK, le plafond de la gorgée sont proposées.
Cela permet d'utiliser une dernière once sans saisie numérique ; avec un
seul choix, la grille le sélectionne comme les autres listes d'une entrée.
EAT garde TASTE avant les portions. Échap annule le choix sans consommer.

Les onces de BOIL sont tapées en ligne : l'analyseur accepte désormais
`BOIL WATER n OZ` comme `EAT` et `DRINK` (`src/input.s`), sans invite ;
`BOIL WATER` seul pose toujours la question. Les objets choisis sont aussi
transmis par `menu_noun`, lu par `resolve_menu` avant `resolve_noun`, car
les noms affichés (`COTTN SOCKS`, `DOWN PARKA`) ne sont pas des mots du
vocabulaire. Une rangée de liste déborde par pages : gauche/droite en bord
de rangée changent de page.

### 4.3 La file des prérequis (grille seule)

Un choix de la grille peut exiger d'abord des commandes de l'original. La
grille les tape une à une, exactement comme le clavier (même temps, mêmes
tirages, même état), avant la commande choisie :

| Choix | Étapes ajoutées avant (dans l'ordre) |
|---|---|
| MAKE FIRE | `USE FUEL` sous la pluie ou un vent de 41 mph et plus, `USE MATCHES` ; après : `USE FIRE` sous 50 °F ressentis |
| MAKE WATER | `USE GND COVER` (ou `USE RAINCOAT`) |
| BOIL WATER n OZ | `USE UTENSILS` |
| CATCH | `USE BAIT`, puis `USE TRAP` (gibier) ou `USE FISHNG GEAR` (poisson) |
| KILL (gibier, poisson) | la meilleure arme, dans l'ordre de l'original (FORAGE.md § 3.2) : `USE GUN`, `USE BOW`, `USE SPEAR`, `USE AXE` ou `USE KNIFE` ; rien quand une arme est déjà en usage (gourdin et pierre compris : le choix du joueur ; la grille ne les propose pas, ils ne tuent jamais : p = 0,1 × (17 − 18) de jour, 0 la nuit) |
| USE STOVE | `USE FUEL`, `USE MATCHES` |
| USE FRSTAID KIT dans le noir | `USE FLASHLIGHT` |
| CUT BODY (soins de STATUS) | `USE KNIFE` (ou `USE AXE`) |
| GET d'un objet d'équipement | `PACK x`, puis `CARRY x` si le sac le refuse (sac au sol, pendu ou perdu : `CARRY x` d'emblée) |

Une étape déjà faite est sautée (son drapeau est déjà posé : allumettes en
usage, ustensiles en usage…) ; une étape qui échoue (son drapeau ne se pose
pas) ou une nouvelle rencontre arrête la file, le refus de l'original
restant visible. La file (`mq_*`, MENUCODE) est reprise par `get_line` à
chaque invite : `grid_fetch` recopie le module GRID et `module_queue` vérifie
l'étape passée puis tape la suivante. Les commandes tapées au clavier
gardent les refus de l'original : la file n'appartient qu'à la grille.

### 4.4 Colonne gauche, modes et mémoire

- **Colonne gauche (rangées 20 à 23, colonnes 0 à 38) : les
  descriptions.** `message` y place le dernier message mot par mot (retour
  à la ligne entre les mots, `|` force une rangée tant qu'il en reste une,
  sinon vaut une espace ; un mot plus long qu'une rangée est coupé à la
  rangée, sans atteindre le séparateur). Quand le message laisse la rangée 23
  vide, elle reçoit la ligne de stock `FOOD n WATER n LOCAL f/w OZ`
  (provisions et eau emportées, puis au sol sur la case), et, pendant
  qu'une commande est tapée ou composée, `> ` suivi de la commande telle
  que l'analyseur la lira (sans curseur : le texte en tient lieu) ; l'invite
  numérique du module INPUT (`prompt`) y écrit `> ` et reçoit les chiffres.
  Le rapport de charge (poids, volume) occupe trois rangées.

Modes de `get_line` : ligne tapée (flèches gauche/droite = rotation sur une
ligne vide, RETURN (ligne vide) ou TAB ouvre la grille, haut ouvre les pages
du haut (STATUS), bas ouvre la grille, Échap vide la ligne) ; grille
(flèches, haut sur la première rangée de verbes revient à la vue, bas sous
la dernière rangée de verbes la ferme et tape `T` : TOPO, les pages du bas
(`grid_bottom` ; au-dessus d'une dernière rangée plus courte, bas va
d'abord à sa dernière case ; dans une liste, bas s'arrête), RETURN choisit,
Échap remonte d'un niveau puis ferme, TAB ferme depuis n'importe quel
niveau, une lettre revient à la ligne tapée) ; une commande issue de la
grille la laisse ouverte pour la suivante, une commande tapée la referme.
Les menus produisent le texte du clavier dans `inbuf` (laissé intact entre
deux commandes, comme dans la référence : `test_reference_state.py` le
compare). Aucune avance du temps, aucun tirage pendant la navigation
(`test_menu_bar.py` compare l'état obtenu par la grille à celui des mêmes
commandes tapées) ; la seule lecture est celle du module GRID, en RAM
auxiliaire.

`tests/test_grid_play.py` joue la grille aux seules touches d'un joystick
(gauche, droite, haut, bas, RETURN) sur les deux éditions : un feu (MAKE,
FIRE : `USE MATCHES`, `MAKE FIRE`, `USE FIRE`), de l'eau bouillie (BOIL,
8 OZ : `USE UTENSILS`, `BOIL WATER 8 OZ`), une pile de champignons (EAT,
MUSHROOMS, 8 OZ) et un saignement arrêté (CARE, puis RETURN sur `STOP
BLEEDING` des soins de STATUS).

Mémoire ([MEMORY.md](MEMORY.md) § 11 et § 18) : la partie résidente
(boucle clavier, rangée 23, `prompt`, état, file) en `$BA00-$BDFF`
(MENUCODE) ; la grille et ses tables (`verb_table`, MENUSWAP, 1 527
octets) dorment dans les lignes HGR 176 à 191 des deux banques, jamais
affichées ni dessinées, et sont recopiées en `$B000-$B5FF` (haut de la
fenêtre SIM, libre entre deux pas de simulation) à chaque invite ; ce que
fait RETURN (listes, composition, file : module GRID, entrée 32,
2 456 octets) est recopié du stock en `$A300` à chaque RETURN de la grille
et à chaque étape de la file, au-dessus des tampons du feu animé
(`$A000-$A2BB`) ; la colonne de résultat (`msg_*`) est dans WILDGAME, treize
octets de page zéro en `$F0-$FC`. Le pilote joystick (§ 3, étape 1) reste
à faire : il s'insère dans la boucle `idle` de `menu.s` (`prompt_key` /
`menu_key` prennent déjà les codes des flèches, RETURN et Échap).

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
| STATUS (80 colonnes depuis le 14 octobre 2026 : deux colonnes, jauges, tableau des provisions, blessures, direction des rangers avec la boussole ; `src/status.s`) | pleine largeur, 18 lignes | mêmes sections et unités ; M bascule vers MEDICAL |
| INVENTORY, devenue OBJECTS (80 colonnes depuis le 14 octobre 2026 ; page de transfert depuis le 16 octobre : § 5.1 ; `src/inventory.s`, module STATUS) | pleine largeur | LOCAL à gauche, CARRIED à droite ; haut/bas choisissent un objet, RETURN le passe de l'autre côté, H le prend en main |
| HELP (une page 80 colonnes, quatre blocs : TRAVEL, EQUIPMENT, SURVIVAL, HEALTH) | pleine largeur | même page |

**Navigation par pages (14 octobre 2026) : haut, vue, bas.** La vue est au
centre : sur une ligne vide, gauche et droite la tournent, RETURN ou TAB
ouvre la grille (§ 4), haut ouvre les pages du haut, bas ouvre la grille,
et bas sous sa dernière rangée ouvre les pages du bas.

- **Pages du haut** (restructurées le 15 octobre 2026, demande de
  l'utilisateur, les deux éditions) : STATUS, OBJECTS, CRAFT (lot 3 :
  [CRAFT.md](CRAFT.md) § 8.6), HELP, OPTIONS et MENU forment un cycle
  (`src/pages.s`, module STATUS dans la fenêtre SIM ; la page CRAFT est
  celle du module CRAFT, lu par-dessus). MEDICAL n'est plus une page : ses
  affections et leurs soins sont dans STATUS ; INVENTORY s'appelle OBJECTS
  et reçoit CARRYING (vivres et eau emportés, ici, à portée) ; RANGERS
  (distance, direction, `JOURNEY DONE` et sa jauge) passe dans MENU ; HERE
  et la ligne d'état deviennent LOCAL (date, heure, air, ressenti, ciel,
  vent, altitude, sol, situation). Une rangée d'onglets en haut (la page
  courante en inverse, sans rappel `S/O/R/H`), les flèches gauche et droite tournent en boucle, S, I
  ou O (OBJECTS), R (CRAFT), H et M (STATUS, l'ancienne MEDICAL) ouvrent
  une page (sauf sur MENU, dont les lettres sont les siennes), T ouvre
  TOPO, Échap, RETURN et espace reviennent à la vue ; les commandes tapées
  (`STATUS`, `INVENTORY`, `HELP`…) restent les mêmes ;
  la rangée 23 porte les touches propres à la page et, à droite,
  `ESC/DOWN: VIEW` sur les pages sans niveau, `ESC: VIEW` sur les autres.
- **Niveaux de focus des pages du haut** (`pg_focus`, `page_keys`) : à
  l'arrivée sur une page le focus est sur la rangée d'onglets, où gauche et
  droite changent de page. Haut depuis la vue retrouve la dernière page
  ouverte ; la commande STATUS reste explicite. Dans OBJECTS, bas depuis
  l'onglet revient à la vue et Entrée active les listes. Ailleurs, bas
  descend d'un niveau, haut remonte ; **haut
  sur les onglets ouvre TOPO** (demande de l'utilisateur du 15 octobre 2026 :
  l'étage des cartes est au-dessus des pages, la boucle verticale se ferme
  dans les deux sens), Échap revient à la vue de partout. Haut ne quitte
  la page que depuis la rangée d'onglets : sous elle, il remonte d'un
  niveau comme avant. Même chemin que T (`scr_topo` : SITES puis TOPOGEN,
  la vue gardée par l'instantané) ; dans `page_keys` pour STATUS, MEDICAL,
  INVENTORY, HELP, OPTIONS et MENU (+4 octets du module STATUS), dans la
  boucle de touches de CRAFT (`cp_key`, +2 octets). Sur XL, les pieds de page
  le disent : `↑ TOPO` (MouseText `$4B`, demande de l'utilisateur du
  15 octobre 2026) au lieu de `T TOPO` (un octet de STATUS par `XL_BYTE`,
  la chaîne d'INVENTORY de STATX) ; T marche toujours. 140 Ko garde
  `T TOPO` : « UP: TOPO » grandirait son image.
  HELP n'a pas de niveau : bas revient à la vue ; STATUS a les affections
  actives de ses rangées MEDICAL (voir plus bas ; sans affection active,
  bas revient à la vue).
  OBJECTS (page de transfert depuis le 16 octobre 2026, demande de
  l'utilisateur du 15 octobre, les deux éditions ; § 5.1) : Entrée met le
  focus sur les deux listes, le curseur `>` sur l'objet choisi du côté
  choisi ; gauche et droite changent de côté (LOCAL, CARRIED), haut et
  bas d'objet en objet (les en-têtes de groupe ne se choisissent pas),
  haut au-dessus du premier rend le focus aux onglets, bas sous le
  dernier revient à la vue. RETURN envoie l'objet de l'autre côté, H le
  prend en main (sur les onglets, H reste HELP) ; espace et Échap
  reviennent à la vue. OPTIONS et MENU : bas pose un curseur `>` en
  colonne 1 sur la première ligne (C, A, P, F ; S, R, Q), haut et bas le
  déplacent, bas sous la dernière ligne revient à la vue, haut sur la
  première rend le focus aux onglets ; RETURN et espace valent la lettre de
  la ligne (NATURE, bascules, SAVE, RESTORE, QUIT), les lettres marchent
  toujours. La ligne qui a le focus est en inverse (OPTIONS : du nom
  jusqu'à la colonne des états ; MENU : son texte). CRAFT (deux moitiés depuis le 15 octobre 2026 : à gauche les
  recettes en trois groupes, SHELTERS, WEAPONS AND TOOLS, PROTECTION, avec
  leur état en MouseText et leur temps ; à droite la recette choisie, ses
  contrôles, son effet, son temps : [CRAFT.md](CRAFT.md) § 8.6) : bas pose
  le curseur `>` sur la première recette, haut et bas vont de recette en
  recette (les en-têtes de groupe ne se choisissent pas), bas sous la
  dernière revient à la vue ; la rangée 23 dit ce que tape RETURN
  (`RETURN: MAKE HUT`, `RETURN: NOTHING (MISSING)`, `RETURN: VIEW` sur les
  onglets) ; RETURN (ou espace) tape `MAKE x`, bip sur une recette
  manquante ou déjà faite. Chaque
  déplacement du focus redessine la page en différentiel :
  seules les cellules qui changent sont écrites (deux pour le curseur, les
  crochets et l'inverse du groupe ; `tests/test_focus.py`,
  `tests/test_transitions.py`).
  STATUS montre dans ses rangées MEDICAL (15 à 20) les treize affections
  et le mal d'altitude en trois colonnes (pourcentage de gravité,
  `100 − x` de la valeur simulée : 0 % sans mal, demande du 15 octobre
  2026 ; affichage seul, ni la simulation ni les sauvegardes ne changent ;
  marque de soin :
  X inverse ACTIVE, `+` TREATED, `*` PROTECTED sur 140 Ko ; coche et
  losange MouseText sur XL ; la légende sur la rangée du titre) ; bas met
  le focus sur les affections actives tour à tour
  (le nom en inverse) et la rangée 23 montre les gestes de soin de
  l'affection (gauche et droite choisissent, le geste choisi en inverse ;
  RETURN le tape : `STOP BLEEDING`, `SUCK VENOM`, `CUT BODY`…, module
  MEDVIEW, `src/care.s`) ; CUT BODY sans lame en usage et la trousse dans
  le noir passent par la file de la grille (§ 4.3). Le verbe `CARE` de la
  grille ouvre STATUS, focus sur la première affection active
  (`pg_open`). OPTIONS tape pour le
  joueur `NATURE` (C, fréquence de la faune) et bascule deux options
  (`game_options`, GDATA, non sauvegardé) : A, le joueur sur TOPO (bit 7,
  masqué par défaut : `tp_sites`), P, MAP (bit 6 : `module_topo` répond
  `MAP IS OFF (OPTIONS PAGE).`) ; la ligne F (`FOOD SOURCES ON THE WAY`,
  lot 4) tape `IGNORE FOOD` ou `GET FOOD` selon `fg_ignore`. Depuis le
  15 octobre 2026, une option par rangée (3-6 : `C  WILDLIFE FREQUENCY`,
  `A  PLAYER ON TOPO`, `P  MAP PAGE`, `F  FOOD SOURCES ON THE WAY`), l'état
  aligné en colonne 31 (`PG_VAL` : la fréquence, ou `[X]` / `[ ]` ; sur XL
  une coche MouseText dans la case). MENU tape `SAVE`, `RESTORE` ou `QUIT` ;
  RANGERS en tête (rangées 2-4 : distance et direction, `JOURNEY DONE` et
  sa jauge), puis SAVE / RESTORE (6-8) et QUIT (rangée 11, sans titre sur
  140 Ko).
- **Pages du bas** : TOPO (`module_graphical_topo`) puis MAP
  (`module_topo`) ; gauche ou droite passe de l'une à l'autre, haut, Échap,
  RETURN ou espace revient à la vue. MAP défile par I, J, K, L (haut,
  gauche, bas, droite), C recentre ; les flèches ne la font plus défiler.
  Le passage ne recharge rien : TOPO → MAP écrit la page texte par-dessus la
  feuille DHGR (TOPOGEN reste dans la fenêtre SIM, `topo_over` = 1) ;
  MAP → TOPO réaffiche le mode mixte et la légende (`topo_frame`) sans
  recalculer la feuille ; le retour à la vue recopie l'instantané
  (`topo_close`, § 8.4 de MEMORY.md). MAP tapée depuis la vue (`M`, `MAP`)
  passe à TOPO par le chemin complet. Quand l'option coupe MAP, gauche et
  droite restent sur TOPO. **Bas** (demande de l'utilisateur du
  15 octobre 2026) ferme TOPO ou MAP comme haut, puis ouvre les pages du
  haut, STATUS d'abord (`topo_pages`, `src/sites.s`) : la navigation
  verticale fait le tour, pages du haut → vue → grille → TOPO / MAP →
  pages du haut. Les deux éditions (+19 octets dans SITES, rien de
  résident ; la légende de TOPO n'en parle pas, faute de place sur 140 Ko).
  Depuis le même jour, haut sur la rangée d'onglets d'une page du haut
  revient à TOPO (voir les niveaux de focus) : TOPO → bas → STATUS → haut
  → TOPO.
| Messages longs (mort, victoire, bilan) | centrée, 6 à 8 lignes | texte existant, bouton 0 ferme |
| QUIT | centrée, 3 lignes | confirmation existante (Y / N) |

MAP reste en texte 80 colonnes (deux caractères par cellule, déjà adapté) et
TOPO reste plein écran : ils ne sont pas des fenêtres.

Coût de tracé estimé pour STATUS complet (≈ 600 glyphes à ≈ 200 cycles,
plus le rectangle) : environ 0,15 s, à mesurer. Le retour doit rester
inférieur à 0,3 s, le niveau d'INVENTORY aujourd'hui.

### 5.1 OBJECTS : la page de transfert (16 octobre 2026)

Demande de l'utilisateur du 15 octobre 2026 : transférer les objets
vite. Les deux éditions (post-its MouseText sur XL, texte simple sur
140 Ko), `src/inventory.s` dans le module STATUS ; captures
`build/objects_v2_xl.png`, `build/objects_v2_140.png`.

```
 LOCAL _________________________________  HANDS ________________________________
▏> ENSOL PAD      24 OZ                ▕ ▏  BACKPACK       64 OZ               ▕
▏  GND COVER      45 OZ                ▕ ▏  TOPO MAP       0 OZ                ▕
▏  JEANS          24 OZ                ▕ ▏  2QT CANTEEN    80 OZ               ▕
▏  SHORTS         4 OZ                 ▕ ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
▏  COTTN SOCKS    5 OZ                 ▕ _ PACK ________________________________
▏  HAT            2 OZ                 ▕ ▏  DOWN PARKA     24 OZ               ▕
▏  GLOVES         10 OZ                ▕ ▏  TENT           64 OZ               ▕
▏  WATER          64 OZ                ▕ ▏  RAINCOAT       16 OZ               ▕
▏  CANDYBARS      16 OZ                ▕ ▏  WATER          64 OZ               ▕
▏  BACON          16 OZ                ▕ ▏  EGGS           16 OZ               ▕
▏  CHEESE         16 OZ                ▕ ▏  CHEESE         32 OZ               ▕
▏  CARROTS        16 OZ                ▕ ▏  POTATOES       32 OZ               ▕
‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾ MORE ‾‾‾‾ ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾ MORE ‾‾‾
 CARRYING ________FOOD_______WATER______  LOAD _________________________________
▏CARRIED          192 OZ     64 OZ     ▕ ▏█████████▒  772/815 OZ               ▕
▏LOCAL            248 OZ     64 OZ     ▕ ▏WALK TIME +28% FREE IN3 WEAR 1525    ▕
▏IN REACH         440 OZ     128 OZ    ▕ ▏PACK █▒▒▒▒▒ 4134 HANDS ▒▒▒▒▒▒ 2542   ▕
‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾ ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
                                         ↵ PACK ENSOL PAD
                                         H CARRY ENSOL PAD
 ←→ PAGE  ↵ LIST/ACT ←→↑↓ MOVE  H HANDS                               ESC VIEW
```

- **Les deux listes** (`ob_build`, dans `overlay_text`) : à gauche ce qui
  est au sol de la case (LOCAL), puis l'en-tête `LOCAL HUNG` et le sac
  pendu ici quand il y en a un ; à droite HANDS, PACK et WORN, toujours
  avec leur en-tête (inverse). HANDS et PACK sont deux post-it distincts
  sur XL ; leur séparation suit le défilement. CARRYING et LOAD occupent
  les rangées 16–20, les aides des transferts à droite les rangées 21–22.
  Un objet par rangée : son nom (colonne 3
  de la moitié), son poids (colonne 18 : W5 de l'équipement, les onces
  d'une provision ou d'une pile à sa place, le W5 du second jeu ; les
  remèdes 41-51 sauf les lunettes, leurs `USES` comme avant). Douze
  rangées par côté, la fenêtre suit le curseur (sa dernière rangée quand
  il est plus bas) ; les abris (95-97) n'y sont pas, ce ne sont pas des
  objets (la page CRAFT les montre).
- **La sélection** : `obj_side` et `obj_cur` conservent le côté et les
  positions de défilement ; `obj_selected` garde l'identité des deux objets
  dans deux octets BSS résidents, hors sauvegarde. À la reconstruction,
  `ob_restore` retrouve l'objet même si son indice a changé ; s'il a disparu,
  `ob_fix` choisit un voisin valide et `ob_remember` retient cette sélection.
  Une réouverture garde le focus sur les onglets, Entrée reprend la liste.
- **Le transfert** tape la commande du clavier (`ob_cmd`) : RETURN à
  gauche `PACK x` (`GET WATER` pour l'eau d'une pile, `CARRY BACKPACK`,
  `CARRY CANTEEN`), à droite `DROP x` ; H `CARRY x`. Le nom affiché est
  tapé (sans un premier mot à chiffre : `2QT CANTEEN` → `CANTEEN`, sinon
  INPUT y voit un nombre), l'objet passe par `menu_noun`. Temps, règles
  et refus sont ceux de la commande tapée (`tests/test_objects.py`
  compare l'état après la page à l'état après la ligne tapée). Le sac pendu et son contenu ouvrent désormais la confirmation
  LOWER FOOD (§ 13). HANG coûte 30 minutes ; LOWER est instantané.
- **Le retour** : la page met la commande dans `inbuf`, pose la file de la
  grille (§ 4.3) `S_CARRY` (sans contrôle) puis `S_OBJECTS` (qui tape
  `INVENTORY`), lève `obj_keep` et saute à `obj_type` (résident : SIM
  lue en silence, puis `do_command`). La page reste à l'écran pendant la
  commande ; `message` écrit la réponse dans les rangées 20-22, colonnes
  0-38, comme dans la vue ; `get_line` tape `INVENTORY` ; la page revient,
  le focus sur les listes, le curseur sur la même rangée (l'objet suivant
  y est venu), la réponse gardée (ses cellules sont sautées). Le bandeau
  de la vue (`summary_refresh`) attend la sortie de la page
  (`obj_keep`) : un transfert prend ≈ 1,1 s sur XL, ≈ 1,2 s sur 140 Ko
  (de RETURN à la page revenue).
- **LOAD** : la jauge du poids porté sur dix cellules jusqu'à la limite
  (`load_limits`, 815 oz : le `$4BFA` de l'original, mesuré par
  `tools/re_load_probe.py`), les onces portées et la limite ; `WALK TIME
  +n%` : 100 × INT(onces / 16) / (poids du corps + 2), le ralentissement
  de la marche (T08/S07 : le facteur `$4C84` = (`$4C02` + `$4BBE`) /
  `$4BF6`, proportionnel au poids dès la première livre, **aucun seuil**
  avant la limite). La rangée 18 garde le volume libre des vêtements sous
  `FREE IN3 WEAR`. La rangée 19 montre PACK et HANDS : six cellules de
  volume occupé (`floor(6 × utilisé / capacité)`, plafonné à six), puis
  le volume libre exact en pouces cubes. Une capacité nulle donne une jauge
  vide ; un dépassement remplit la jauge et affiche zéro libre.
  Mesures de la
  sonde : 772 oz portés au départ (43 restants), +28,7 % à 48 lb,
  +29,9 % à 50 lb ; au-delà de la limite tout objet pris au sol est
  refusé (GET ROCK avec 100 oz restants accepté, 99 refusé, msg 7) :
  la fin de la jauge est donc le seul seuil, celui du « trop lourd ».
- **CARRYING** : les vivres et l'eau portés, ici, à portée (inchangé).

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

## 9. Pages en MouseText (NeoWildernessXL, 15 octobre 2026)

Plan approuvé par l'utilisateur le 15 octobre 2026 : cadres et traits
MouseText dans les pages texte 80 colonnes, pour une interface aussi
claire que possible. **Décision de l'utilisateur du même jour : « le 140Ko
n'a pas besoin de mousetext ».** Tout ce qui suit est propre à
NeoWildernessXL (800 Ko) ; l'édition de 140 Ko garde ses pages 80 colonnes
sans cadre et son jeu de caractères primaire hors de la page CRAFT. Depuis
la restructuration des pages du même jour (§ 5 : MEDICAL dans STATUS,
OBJECTS, RANGERS dans MENU, LOCAL ; les deux éditions), le **contenu et
la disposition** des pages sont ceux du code partagé, sur les deux
disques : chaque bloc a son titre en inverse sur sa première rangée et ses
rangées à partir de la colonne 0 ou 41 ; XL n'y ajoute que les cadres
(§ 9.3, « post-it »).

### 9.1 Mécanisme : une queue et des octets propres à XL

Une seule édition de liaison sert les deux disques. Les images liées sont
celles de 140 Ko ; `tools/build_disk.py` (`XL_IMAGES`, `xl_files`) en
fait pour XL des copies `build/*-xl.bin` :

- une **queue** ajoutée à quatre images : STATUS (`STATX`, `$B100-$B5FF`
  depuis le 16 octobre 2026, `$AF00` avant la page OBJECTS de transfert,
  `src/mt_pages.s` ; elle déborde sur `$B000-$B5FF`, l'image de la grille,
  comme la simulation entre deux invites : `get_line` la reprend),
  CRAFT (`CRAFTX`, `$A640`, après les octets de travail de la page),
  MEDVIEW (`MEDVX`, `$5FC0`) et NEOWILD.END (`ENDX`, `$A200`) ;
- des **octets changés** dans les images partagées, notés dans le source
  par les macros de `src/mousetext.inc` (segment `XLPATCH`, jamais
  chargé) : `XL_IMM` (l'opérande d'une instruction), `XL_ABS` (une
  adresse : un `JSR page_foot` devient `JSR page_foot_x`), `XL_JMP` (trois
  octets deviennent un `JMP` vers la queue), `XL_TEXT`, `XL_ENTRY` (la
  queue saute dans un morceau du code partagé, dont la fin est un
  `XL_JMP` de retour ; plus utilisé par les pages depuis les post-its) ;
  `XL_ZERO` (segment `XLZERO`)
  met à zéro le code partagé que XL n'exécute jamais (il coûte alors
  presque rien dans le stock LZ) ;
- du **code résident** de XL copié sur du code résident que XL n'exécute
  jamais (`XL_COPIES`, segment `XLRES`, indépendant de sa position) :
  `xl_pad`, `xl_curtain` et `xl_padhook` (53 octets) remplacent
  `page_foot` (54 octets), que les pages de XL n'appellent plus. Aucun
  octet résident de plus. `xl_padhook` : le premier `STA` de `pad_to`
  (LOWPAGE, image `XI_LOWPG`) devient un `JMP` vers lui ; tant que le COUT
  est `mt_cout` (une page du haut se dessine), il passe à `mt_pad`.
- STATUS et sa queue sont lus de NEOWILD.BLK sur XL (15 blocs,
  `$9600-$B5FF` ; `status_fetch` appelle `sim_fetch`, image `XI_GAME` ;
  le chargeur laisse les pages `$B0-$B5` libres dans la table de ProDOS) :
  MEMORY.md § 29.

Aucune étiquette du code partagé ne bouge : les tests lisent la même table
de symboles sur les deux disques. Les disques de comparaison des tests
(`--map`, sans édition) gardent les pages sans cadre, comme 140 Ko, dont
ils partagent la pression sur le stock ; `--mousetext` leur donne celles
de XL.

### 9.2 Glyphes

`ALTCHARSET` (`$C00F`) est levé pour toute la partie sur XL : le chargeur
(`src/boot.s`, au menu puis de nouveau dans `start`, après SETVID, INIT et
HOME : le SETVID du IIc le baisse, rapport de l'utilisateur du 15 octobre
2026, `tests/test_altcharset.py`), la page CRAFT (ses deux `sta $C00E` deviennent `$C00F`) et
NEOWILD.END le laissent levé ; `prodos_restore` le baisse en sortant vers
ProDOS. Les codes `$40-$5F` sont donc des glyphes MouseText, jamais des
majuscules clignotantes : le jeu n'en écrit pas ailleurs (le curseur des
saisies est le texte lui-même) ; la vue et le panneau DHGR ne dépendent
pas du jeu de caractères. Le IIe amélioré et le IIc ont MouseText ; le
chargeur refuse déjà le IIe non amélioré (`$FBC0`).

| Code | Glyphe | Usage |
|---|---|---|
| `$4C` | trait en haut de la cellule | ligne sous les onglets (rangée 1), bas d'une boîte |
| `$DF` (`_` normal) | trait en bas de la cellule | haut d'une boîte, après son titre |
| `$5F` / `$5A` | barre à gauche / à droite de la cellule | côtés d'une boîte, bords d'un onglet, séparateur de la grille (`$5F`), fin d'une case de la grille (`$5A`) |
| `$53` | trait au milieu | ligne du pied de page (rangée 22), total du score |
| `$5C` | traits en haut et en bas | bande de titre d'une fenêtre (score) |
| `$4E` / `$56` | bloc plein / damier | jauges : partie pleine / reste |
| `$44` | coche | possible (CRAFT), soigné (MEDICAL, TREATED) |
| `$18` (X inverse) | — | manque (CRAFT), à soigner (MEDICAL, ACTIVE) |
| `$5B` | losange | fait (CRAFT), protégé (MEDICAL, PROTECTED) |
| `$48 $55 $4B $4A $4D` | ← → ↑ ↓ ↵ | touches du pied de page, défilement de la grille |
| `$43` | sablier | rideau d'une action longue |

Dans les chaînes des queues (`mt_str`, `mt_puts`), un glyphe est l'octet
`MS_* = MT_* ^ $50` (de `$00` à `$1F`) ; `topo_output` n'est pas modifié.

### 9.3 Post-its : la convention (15 octobre 2026)

Demande de l'utilisateur : « Inspire-toi de la présentation du panneau
STATUS pour généraliser cette présentation en POST-IT ». Chaque bloc d'une
page est un post-it : son titre en inverse posé sur le coin haut-gauche
(un espace de chaque côté), puis le trait `_` (`$DF`, bas de cellule)
jusqu'à sa dernière colonne ; ses rangées entre la barre `$5F` (à gauche
de sa première colonne) et `$5A` (à droite de sa dernière) ; sa dernière
rangée le trait `$4C` (haut de cellule) d'un bord à l'autre. Les quatre
traits se rejoignent aux coins. Deux post-its côte à côte : colonnes 0-39
et 41-79, la colonne 40 vide (CRAFT : 0-28 et 30-79).

**Une routine, une table par page.** Les pages ne dessinent pas les
cadres : la sortie le fait (`src/mt_pages.s`). Chaque page a une table de
six octets par post-it (`pf_pages` : première et dernière rangée, première
et dernière colonne, titre ; 0 : le titre est le texte que la page écrit
en inverse), CRAFT dans sa queue (`pf_craft`). `page_top_x` choisit la
table ; `pf_sync` construit le cadre de la rangée courante dans un tampon
de 80 octets (le corps mort de `page_top`, `$AAxx`, au-dessus des blocs de
CRAFT), réutilisé tel quel quand la rangée suivante a la même signature
(l'état de chaque post-it : aucun, titre, entre, bas). `mt_cout` (le COUT
des pages) écrit chaque caractère : sur une barre, la barre puis le texte
après elle (une rangée commence en colonne 0 ou 41, son texte tombe dans
le post-it) ; sur un trait, le texte l'emporte, sauf l'espace normal, mis
en attente (`pf_pend`) : il devient le trait si un remplissage suit, un
espace si du texte suit. `mt_pad` (tous les remplissages : `tab`, `vtab`,
CR, `topo_pad`, par `xl_padhook`) écrit les glyphes du cadre et des
espaces ailleurs (`clear_to`, par plages). Chaque cellule est écrite une
fois, avec sa valeur finale : un nouveau tracé de la page ne stocke que
les cellules qui changent (`tests/test_focus.py`,
`tests/test_transitions.py`).

### 9.4 Les écrans

- **Onglets** (toutes les pages du haut, `page_top_x`) : rangée 0, chaque
  page entre `$5A` et `$5F`, la page montrée en inverse, `S/O/R/H` après
  elles (colonnes 58-64 : jamais le bord de l'écran, le `H` de
  `S/M/I/R/H` y était coupé) ; rangée 1, le trait `$4C`, ouvert sous la
  page montrée.
- **Pied de page** (`page_foot_x`, la page CRAFT, `med_foot_x`) :
  rangée 22, le trait `$53` ; rangée 23, `←→ PAGE`, puis les touches de
  la page (`↑↓ CHOOSE  ↵ SELECT`, `↑ TOPO`, les gestes de soin…), et en
  colonne 70 `ESC/↓ VIEW` (page sans niveau) ou `ESC VIEW`. OBJECTS
  (16 octobre 2026) : `page_foot23_x`, sans le trait de la rangée 22
  (les rangées 20-22 portent la réponse d'un transfert).
- **STATUS** (15 octobre 2026, les deux éditions) : CONDITION à gauche
  (rangées 2-14, titre : le mot du joueur ; HEALTH, ENERGY, HUNGER, THIRST
  en jauges de blocs et damiers suivies de leur pourcentage, `90% OKAY`,
  puis BODY, une rangée vide entre deux : rangées 4, 6, 8, 10, 12), à
  droite LOCAL (2-10 : DATE / TIME, AIR / FEELS, SKY / WIND, ALT / GROUND,
  la situation en rangées 7-9) et CONDITIONS dessous (11-14 :
  déshydratation, inanition, épuisement, hypo- ou hyperthermie, deux par
  rangée en colonnes 41 et 60), MEDICAL sur toute la largeur (15-21 : légende
  X inverse ACTIVE, coche TREATED, losange PROTECTED sur la rangée du
  titre ; les treize affections et le mal d'altitude en trois colonnes,
  pourcentage de gravité et marque ; le focus des soins).
- **OBJECTS** (16 octobre 2026, § 5.1) : quatre post-its, LOCAL et
  CARRIED (rangées 2-14, colonnes 0-39 et 41-79 : onze objets par côté,
  `MORE` en inverse sur le trait du bas d'une liste qui continue), puis
  CARRYING et LOAD (15-19 : FOOD et WATER sur le trait du titre de
  CARRYING ; la jauge de LOAD en blocs et damiers). Les rangées 20-22 ne
  sont pas encadrées : à gauche la réponse du jeu au dernier transfert
  (colonnes 0-38, la colonne de résultat de la vue), à droite ce que
  tapent RETURN (`↵ PACK ROPE`, glyphe `$4D`) et H ; la rangée 22 n'a
  pas le trait du pied (`page_foot23_x` : la réponse peut tenir trois
  rangées), la rangée 23 les touches (`←→ SIDE  ↑↓ CHOOSE  ↵ TO OTHER
  SIDE  H TO HANDS`, `ESC VIEW` en colonne 70).
- **CRAFT** : à gauche SHELTERS, WEAPONS AND TOOLS, PROTECTION (titres du
  cadre, `pf_craft`), à droite la recette choisie (rangées 2-20, son nom
  en inverse en titre, le verdict sur le trait), la légende en rangée 21.
- **HELP** : un post-it par bloc (TRAVEL, EQUIPMENT ; SURVIVAL, HEALTH ;
  rangées 2-9 et 11-19).
- **OPTIONS** : un seul grand post-it (rangées 2-9, toute la largeur,
  titre OPTIONS) : une option par rangée (3-6), l'état en colonne 31 (coche
  `$44` dans `[ ]`), la ligne du focus en inverse jusqu'à l'état, et en
  rangée 8 une phrase sur l'option choisie (`pg_desc_x`, XL seul : le
  module STATUS de 140 Ko n'a plus la place). **MENU** : RANGERS (2-5 :
  distance et direction, `JOURNEY DONE` et sa jauge), SAVE / RESTORE
  (6-9), QUIT (10-12, titre de la table).
- **Grille** (vue, rangées 20-23) : chaque case nommée finit par `$5A`,
  le séparateur de la colonne 39 est `$5F`, les marques de défilement
  `↑` / `↓` ; la case choisie reste en inverse, un verbe impossible en
  minuscules (sémantique inchangée).
- **Rideau** des actions longues (simulation, vue refaite) : un sablier au
  milieu (rangée 9, colonne 39).
- **Score** (NEOWILD.END, 40 colonnes) : la bande de titre en double trait
  `$5C`, le détail du score en post-it (rangées 2-13 : titre la région et
  le niveau, rangées entre les barres, texte depuis la colonne 1), le
  trait `$53` au-dessus du total, le tableau des cinq meilleurs du
  scénario en post-it (rangées 14-20). L'écran H du menu de départ
  (chargeur, 40 colonnes) et la fin de partie d'ADVENTURE restent tels
  quels.

Captures : `build/postit_*.png` (`status`, `status_care`, `objects`,
`craft`, `help`, `options`, `menu`, `score`). Tests : `tests/common.py`
(`POSTITS`, `postit_errors` : les codes bruts de chaque post-it),
`tests/test_editions.py` (`pages` : les six pages de XL, et aucune cellule
MouseText sur les pages de 140 Ko hors CRAFT), `tests/test_focus.py`,
`test_interface.py`, `test_transitions.py`, `test_craft_page.py`
(les deux éditions), `test_grid_play.py` (`frame`, les deux éditions),
`test_editions.py` (`pages`), `test_hof_game.py` (`xl_end`),
`test_reference_state.py` (l'état laissé par STATUS est celui de 140 Ko).


## 10. Entrées communes de l'audit (16 octobre 2026)

Le premier lot raccorde `src/ui_event.s` à `idle`, `keyboard_wait`, au
menu du chargeur après le tronc et au lecteur de touches du score. Les
axes donnent les quatre directions, PB0 validation et PB1 retour. Les
axes sont échantillonnés ensemble, au plus environ 3 ms par lecture ; une
lecture toutes les 256 attentes, zone morte aux comptes 26 et 86 (mesure
sur la boucle, pas les unités de PDL ROM), répétition après 50 lectures
puis toutes les 15. Les valeurs exactes restent à calibrer sur une manette
réelle. Deux timers encore hauts après la lecture désignent un port sans
manette. Un bouton maintenu ne valide pas la prochaine étape. Les axes
sont suspendus lorsqu'une commande est en cours de frappe.

`UI_TWO` (`src/ui_choice.inc`) affiche le choix courant à l'invite et
conserve les lettres directes ; les directions le basculent, validation
répond, retour annule. Utilisé pour les sources P/G, les confirmations en
jeu et les choix Y/N et E/W d'orientation. Les invites entières communes
acceptent haut/bas sans changer la validation des unités et des plages.

MAP distingue la navigation entre pages et l'exploration : validation
entre, les directions font défiler, validation recentre, retour rend
le focus à la navigation des pages ; un second retour rend la vue. Sa
rangée 23 annonce le mode. Les raccourcis I/J/K/L/C restent accessibles.

Au score, haut/bas parcourt A–Z, 0–9, espace, point, tiret pour la dernière
lettre ; droite ajoute une nouvelle lettre A, gauche l'efface. Validation
garde un nom non vide, retour annule l'entrée. La frappe directe reste.

`tests/test_navigation.py` vérifie ces parcours sur 140 Ko et XL, dont le
maintien de PB0 au menu et dans la grille, la zone morte à ±0,2, la
rotation, la protection de la frappe, l'annulation P/G sans effet sur
l'état/hasard, SAVE 2 sans chiffres tapés, les confirmations, la carte et
l'enregistrement du nom AB sans lettres tapées. Les questions du mode P,
/RAM avant le tronc et les lecteurs particuliers restant à raccorder sont
suivis dans TODO.md ; la jouabilité intégralement sans clavier n'est pas
encore déclarée terminée.


## 11. OBJECTS : transaction et cible XL (16 octobre 2026)

Le développement de l’édition 140 Ko est arrêté à la demande de
l’utilisateur. Les comportements nouveaux sont réalisés et testés sur XL.
`make`, `make run`, `make inspect` et `make test` ciblent XL ; les anciennes
cibles et descriptions de comparaison restent historiques.

Depuis une liste, Entrée ouvre le menu de l’objet. Haut/bas choisissent
l’action : PACK, CARRY, DROP, WEAR, USE, EAT ou DRINK selon sa catégorie.
Le raccourci H ouvre le même éditeur en demandant la main lorsque l’action
est valable. Retirer un vêtement passe par CARRY/PACK/DROP. La sélection et
son côté sont conservés après exécution, avec la réponse du jeu.

Pour les provisions et piles, l’étape quantité propose haut +1, bas −1,
gauche 1 et droite TOUT. Le transfert démarre sur le stock entier de la
source ; EAT démarre à 1 OZ et n’accepte pas TOUT. L’étape suivante exige une
confirmation distincte ; Échap recule puis quitte sans temps, tirage ou
modification des stocks. Les équipements restent indivisibles.

L’aperçu AFTER montre le poids et les volumes PACK/HANDS libres après un
transfert d’équipement ou de provisions ; OVER indique le dépassement exact.
Les piles sauvages conservent leur règle native sans charge. Pour USE,
EAT/DRINK et les cas d’eau non encore calculés, NOW montre la capacité
actuelle, sans annoncer une projection. Les dépassements arithmétiques sont
signalés explicitement. La commande garde sa validation définitive : le
menu ne modifie jamais temporairement les stocks pour calculer une charge.

PACK/CARRY/DROP acceptent une quantité entière, éventuellement suivie de OZ,
pour les provisions. Sans quantité, leur transfert reste intégral. Une
quantité nulle, une unité de temps, un équipement quantifié ou un stock
source insuffisant sont refusés avant toute mutation. Les piles sauvages
acceptent aussi PACK explicite avec quantité. La source choisie reste celle
du repas même lorsqu’il existe simultanément un stock au sol et dans PACK.

Les cas d’eau, doses médicales, objets suspendus et refus CRAFT sont
détaillés aux § 12–13 ; les limites encore ouvertes sont au TODO. La navigation intégralement sans clavier reste un
objectif en cours, notamment pour CRAFT et CATCH.

## 12. EQUIPMENT et transferts d’eau (16 octobre 2026, XL)

Septième onglet après MENU, également ouvert par EQUIPMENT ou E sur les
onglets. À l’ouverture, le focus est sur l’onglet : bas revient à la vue,
Entrée active la liste. Haut au-dessus du premier objet rend les onglets.
La sélection mémorise l’objet ; les actions et leur annulation y reviennent.

WORN montre les vêtements et protections portés ; HANDS les objets tenus ;
IN USE les drapeaux effectifs de la simulation ; PACK les objets disponibles.
Un objet peut figurer dans plusieurs rôles. Un piège dans PACK n’est pas
préparé ; tenir un couteau ne l’active pas. Certains drapeaux natifs sont
partagés entre objets : la page le signale. Les actions proposées réemploient
les commandes natives et l’éditeur avec confirmation ; retirer un vêtement
se fait par CARRY ou PACK, selon la destination voulue.

Le panneau droit montre les trois états indépendants, le volume occupé en
mains, les capacités libres et les prérequis d’appât pour piège/pêche. Il
ne prépare pas automatiquement l’appât. Le panneau CATCH indique la
préparation réelle, également pilotable par la grille existante.

OBJECTS permet GET/DROP WATER en OZ, y compris TOUT, avec le volume requis,
la destination de la gourde et sa capacité restante. Un transfert explicite
qui dépasse 64 OZ est refusé sans prélèvement partiel. Les autres transferts
affichent également le volume nécessaire et la place WEAR libre. Les objets
fabriqués signalent séparément chaque limite dépassée (poids et contenant),
avec besoin et place libre ; les règles natives d’activation restent celles
du moteur. Les doses médicales et LOWER FOOD sont décrits au § 13.

## 13. Doses et sac suspendu (16 octobre 2026, XL)

USE sur les objets médicaux affiche « 1 USE », le nombre de doses restantes
et la durée native. EAT est également proposé pour les trois médicaments
oraux (47, 48, 50) ; l’oxygène reste appliqué avec USE. Les transferts de
ces équipements restent indivisibles. Aucun sélecteur d’onces ou TOUT n’est
proposé pour le soin : un usage confirmé applique une seule action native.
La durée vient de la même table que la simulation : trousses et traitement
concerné 30 minutes, oxygène 15 minutes, autres médicaments zéro minute.
Les règles natives des objets vides ou réutilisables restent conservées ;
afficher zéro dose ne crée pas une nouvelle interdiction de traitement.
Échap depuis une confirmation sans quantité retourne directement aux actions.

Depuis LOCAL HUNG, Entrée ou H sur le sac ou son contenu ouvre LOWER FOOD.
La confirmation indique la destination CARRIED, tous les contenus, zéro
minute et le contrôle de charge. L’aperçu NOW décrit la charge actuelle ;
il ne prétend pas calculer la charge de tout le sac après récupération.
Annuler ne change ni le stock ni le temps. La commande récupère l’ensemble
ou refuse sans mutation si les capacités natives sont dépassées, puis
revient à OBJECTS avec sa réponse et un objet valide sous le curseur.

Le curseur conserve sa position quand l’objet est toujours à cette position,
avant de rechercher son identité ailleurs. Il peut ainsi dépasser les
provisions présentes à la fois au sol et dans LOCAL HUNG, sans revenir sur
la première occurrence à chaque déplacement.
