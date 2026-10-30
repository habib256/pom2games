# Robot Space Station : spécification

Jeu original de câblage de robots, pour Apple //e enhanced et //c 128 Ko,
ProDOS, DHGR, souris. Une station spatiale abandonnée ; le joueur, un
technicien coincé à bord, programme des drones de maintenance avec des
portes logiques et des puces qu'il fabrique lui-même.

Ce n'est pas une reprise de *Robot Odyssey* : monde, robots, énigmes, règles
de simulation et interface sont propres à ce jeu. Seuls les principes du
genre (capteurs, propulseurs, portes, bascules, fils) sont communs.

## Jalon 1 : labo de puces et zone d'essai

1. **Labo de fabrication** : un établi où l'on monte une puce (portes, fils),
   où l'on teste ses entrées et sorties en direct, puis que l'on *grave* dans
   l'un des 8 emplacements de puces.
2. **Zone d'essai** : une salle où le technicien marche, entre dans un drone,
   pose une puce gravée dans son support, la câble aux capteurs et aux
   propulseurs, ressort et regarde le drone se comporter.

Le modèle de référence est `tools/model.py` : le code 6502 doit lui être
identique au bit près (tests a2shot).

## La simulation

### Planche

Tout circuit est une **planche** : le labo (l'intérieur d'une puce) et
l'intérieur d'un drone sont deux planches.

- Une planche a **8 bornes sources** (valeurs venues de l'extérieur) et
  **8 bornes puits** (valeurs envoyées à l'extérieur).
  - Labo : sources 0-3 = entrées E1-E4 de la puce, puits 0-3 = sorties S1-S4.
    Les bornes 4-7 ne servent pas.
  - Drone : sources 0-3 = capteurs de contact N, E, S, O, source 4 = TIENT
    (la pince tient un objet), source 5 = RADIO reçue ; puits 0-3 =
    propulseurs N, E, S, O (le propulseur N pousse vers le sud, comme une
    tuyère placée au nord), puits 4 = PINCE, puits 5 = RADIO émise. Les
    bornes 6-7 ne servent pas.
- Au plus **16 pièces** posées sur une grille de cases.
- Types de pièces :

  | Type | Code | Entrées | Sortie |
  |---|---|---|---|
  | ET | 1 | A, B | A et B |
  | OU | 2 | A, B | A ou B |
  | OUX | 3 | A, B | A ou exclusif B |
  | NON | 4 | A | non A |
  | BASCULE | 5 | M (mise à 1), Z (remise à 0) | Q |
  | PUCE n | 8+n | E1-E4 | S1-S4 |

- Un **fil** relie une source (borne source ou sortie de pièce) à un puits
  (borne puits ou entrée de pièce). Un puits a au plus un fil ; une source en
  alimente autant qu'on veut. Un puits sans fil vaut 0.

### Compilation : tout devient une liste plate de portes

À chaque modification, la planche est compilée en une **liste plate** d'au
plus 64 portes élémentaires, dans l'ordre des pièces. Une PUCE posée est
remplacée par sa liste gravée (déjà plate). Chaque porte a un type et deux
sources.

Numérotation des sources : 0-7 = bornes sources de la planche, 8-71 =
sorties des portes 0-63, `$FF` = constante 0.

Portes élémentaires : ET 1, OU 2, OUX 3, NON 4, BASCULE 5, TAMPON 6
(recopie A). Le tampon n'apparaît qu'à la gravure (voir plus bas).

### Le tour

Une simulation **synchrone** :

1. les bornes sources reçoivent leur valeur (capteurs, boutons du labo) ;
2. chaque porte calcule sa nouvelle sortie à partir des valeurs **d'avant
   le tour** ;
3. toutes les sorties changent en même temps ;
4. chaque borne puits prend la valeur de sa source (après le tour).

Chaque porte coûte donc un tour de retard ; c'est voulu, lisible et sans
boucle infinie possible. BASCULE : Q' = 1 si M, sinon 0 si Z, sinon Q (la
mise à 1 l'emporte). Un fil relié directement d'une borne source à une
borne puits ne retarde pas.

Au départ et après toute compilation, toutes les sorties valent 0. En
conséquence, un NON seul vaut 0 au tour 0 et 1 au tour suivant.

### Gravure

Graver la planche du labo dans l'emplacement *n* :

- compile la planche (les puces posées sont déjà plates) ;
- remplace toute sortie S*k* reliée directement à une entrée E*j* par un
  TAMPON, pour que toute sortie de puce soit une sortie de porte ;
- refuse au-delà de **32 portes** par puce ;
- enregistre la liste plate (portes + 4 numéros de porte de sortie, `$FF` =
  sortie à 0) et le plan modifiable de la planche (pour la rouvrir au labo).

Une puce posée dans une planche garde la liste gravée au moment de sa pose
dans la planche compilée ; regraver une puce ne change que les planches
recompilées ensuite (ce qui arrive à toute modification).

## Le labo (écran)

DHGR 140 × 192 couleurs.

- Haut (`y` 0-9) : titre, emplacement courant, nombre de portes.
- Planche (`y` 12-151) : 4 bornes d'entrée à gauche, 4 de sortie à droite,
  grille de 5 × 5 cases au milieu.
- Bas (`y` 156-191) : la palette (ET, OU, OUX, NON, BASCULE, puces gravées)
  et les boutons MARCHE/PAUSE, PAS, GRAVER, EFFACER, ZONE D'ESSAI.

Fils : traits droits, **orange = 1**, **bleu = 0**. Seuls les fils qui
changent sont redessinés.

### Souris et clavier

| Geste | Effet |
|---|---|
| clic sur une pièce de la palette | la pièce suit le pointeur |
| clic sur une case vide (pièce en main) | la pose |
| clic sur une pièce posée (main vide) | la reprend (la déplacer ou la jeter sur la palette) |
| clic sur une source puis sur un puits | tire un fil |
| clic sur un puits relié (main vide) | retire son fil |
| clic sur une borne d'entrée E*k* | bascule sa valeur (essai en direct) |
| boutons | marche/pause, pas à pas, graver, effacer |

Sans souris : flèches = pointeur, ESPACE = clic, ESC = lâcher ce qu'on tient.
Les deux sont actifs ensemble.

## La zone d'essai et les missions

Sept missions (`MISSIONS` dans `tools/model.py`, d'où `tools/gen_room.py`
tire `src/room.h`, tuiles à 4 bits). Une salle a un drone `D` (A) et
parfois un second `E` (B). Chaque salle fait 20 × 18 tuiles de
7 × 8 pixels (140 × 144) :

| Tuile | Drone | Technicien |
|---|---|---|
| `#` mur | bloque | bloque |
| `.` sol | passe | passe |
| `=` grille | passe | bloque |
| `X` chargeur | passe | passe |
| `\|` porte | passe si ouverte | passe si ouverte |
| `_` plaque | passe | passe |
| `!` porte, second groupe | passe si ouverte | passe si ouverte |
| `,` plaque, second groupe | passe | passe |
| `+` tunnel | bloque | passe |

Objets (7 × 8) : `C` cellule d'énergie, `B` caisse. Ils bloquent le drone
(sauf celui qu'il tient) et le technicien.

**Portes** : deux groupes indépendants, `_`/`|` et `,`/`!`. Les portes
d'un groupe sont ouvertes tant qu'une plaque du groupe est enfoncée (le centre du drone, d'un objet ou du technicien dans la
salle posé dessus) ou que quelque chose se tient dans l'embrasure d'une porte du
groupe (sa boîte touche une de ses tuiles) ; sinon ce sont des murs. Recalculées au début de
chaque tour, et à chaque pas du technicien.

**But** (par mission) : le centre du drone A sur un chargeur, une cellule
**lâchée** dont le centre est sur un chargeur, ou le centre du technicien
sur un chargeur.

| # | Mission | Leçon |
|---|---|---|
| 1 | TOUT DROIT | un NON sur le propulseur O |
| 2 | LE VIRAGE | le capteur E commande le propulseur N |
| 3 | LE PILIER | une bascule retient le choc (sans elle, le drone repart) |
| 4 | LA CELLULE | aller chercher la cellule derrière la grille et la lâcher au chargeur |
| 5 | LA PORTE | le technicien tient la plaque pendant que le drone passe |
| 6 | LE PARKING | le drone se gare sur la plaque pour que le technicien passe |
| 7 | LE RELAIS | A tient la plaque jusqu'à ce que B, garé sur la sienne, l'appelle par radio |
| 8 | LE ZIGZAG | poussée sud permanente, une bascule inverse est / ouest à chaque choc |
| 9 | LE COLIS | le technicien tient la porte, le drone rapporte la cellule (puce de la 4) |
| 10 | LE GARDIEN | le drone, par-dessus la grille, se gare sur la plaque (bascule du pilier) |
| 11 | LA RONDE | est, puis sud, puis ouest : deux bascules (sud-ouest d'un coup : le piège) |
| 12 | LE SAS | le technicien tient la porte du drone, qui se gare sur la plaque de l'autre porte |

Les tests (`tests/test_model.py`) prouvent qu'une solution existe pour
chacune, qu'une planche vide ne gagne rien, que le pilier exige une
bascule, qu'une cellule jamais lâchée ne compte pas, que la porte attend
le technicien, qu'un drone dans l'embrasure la bloque ouverte et que le
parking ouvre le passage, que le relais exige la radio (A parti trop tôt,
la porte se referme sous B), que deux drones se bloquent l'un l'autre, que
le zigzag exige l'alternance, que le colis attend le technicien, que le
gardien sans bascule ne se gare jamais, que la ronde exige deux bascules et
que le sas attend le technicien sur sa plaque.

Le labo et le drone ont chacun leur planche : passer de l'un à l'autre
recompile la planche (valeurs remises à 0). Choisir une mission
(touches 1-9 et 0 pour la dixième, ou l'écran titre en deux colonnes de 7, jusqu'à la première non réussie) ou REPLACER remet la salle,
les objets, le drone et le technicien au départ.

### Le drone

- Boîte de 10 × 12 pixels, position en pixels de la salle. Le dehors de la
  salle compte comme un mur.
- **Capteurs** N, E, S, O = 1 si un obstacle (mur, objet non tenu) touche
  ce côté. Trois points par côté (bords et milieu), plus serrés qu'une
  tuile ou un objet : rien ne passe entre eux.
- Chaque drone est un obstacle pour l'autre ; le technicien entre dans
  celui qu'il touche (A ou B).
- **Un tour** :
  0. les portes ;
  1. pour chaque drone : sources 0-3 = capteurs, source 4 = TIENT,
     source 5 = ce que l'autre drone a émis au tour précédent ;
  2. un tour de simulation de chaque planche, avant tout déplacement ;
  3. puis drone par drone (A, B) : puits 0-3 = propulseurs, puits 4 =
     PINCE, puits 5 = RADIO ; un propulseur pousse à l'opposé de son côté
     (O pousse vers l'est) ;
  4. PINCE à 0 : l'objet tenu est lâché ; à 1 sans rien tenir : le drone
     prend le premier objet qui le touche (et que l'autre ne tient pas) ;
  5. un pixel en `x` si le drone **et l'objet tenu** ont ce côté libre,
     puis un pixel en `y` ; l'objet tenu suit.
- Le drone fait environ 16 tours par seconde en MARCHE, même quand le
  technicien est à l'intérieur. La mission gagnée arrête la marche et
  sauvegarde.

### Le technicien

- Dans la salle : un clic l'envoie vers ce point (1,5 pixel par image, il
  s'arrête contre les murs). **Toucher le drone, c'est y entrer** ; un drone
  qui roule sur le technicien l'embarque aussi.
- À l'intérieur : la planche du drone (capteurs à gauche, propulseurs à
  droite), la palette et une porte jaune sous la grille. Un clic sur la
  planche envoie d'abord le technicien à cet endroit (3 pixels par image),
  et l'action (poser, tirer un fil, prendre) se fait quand il y arrive. Les
  clics sur la palette et les boutons sont immédiats. SORTIR : il va à la
  porte et ressort à côté du drone (est, ouest, sud ou nord, la première
  place libre).

### Boutons

| Écran | Boutons |
|---|---|
| Labo | MARCHE/PAUSE, PAS, GRAVE, EFFACE, ESSAI |
| Titre | JOUER (la prochaine mission), LABO ; clic sur une mission ouverte |
| Zone | MARCHE/PAUSE, PAS, REPLACER (salle au départ) ou SUITE (mission gagnée), LABO, MENU |
| Drone | MARCHE/PAUSE, PAS, SORTIR |

Clavier : flèches = pointeur, ESPACE ou RETURN = clic, ESC = lâcher,
M = marche/pause, P = un pas, G = graver, O = ouvrir une puce au labo,
1-9 et 0 = choisir une mission dans la zone (10 : touche 0), H = l'indice
de la mission (sur le disque, après la salle), S = son coupé ou actif,
Ctrl-Q = retour à ProDOS.

## La sauvegarde

Un fichier `RSS.SAVE` de 2 133 octets (`RSS2` ; un ancien `RSS1` de 2 013
octets, d'avant le drone B, est repris), image directe de `Persist`
(`src/sim.h`, en mémoire basse `$1400`) ; `save_bytes()` du modèle produit
la même. Contenu : `RSS1`, missions réussies, les 8 puces (comptes, portes
en trois tableaux, sorties, plans modifiables), la planche du labo, celles
des drones A et B. Écrite à chaque gravure et à chaque mission réussie ; lue au
démarrage (fichier absent ou invalide : tout à zéro). Le disque ne doit pas
être protégé en écriture ; sinon le message le dit et le jeu continue.

## Mémoire

Le jeu ne dessine qu'en page 1 du DHGR : la page 2 de la mémoire principale
(`$4000-$5FFF`) reçoit le code et les données de `zone.c`
(segments `HICODE`/`HIDATA`, `src/game.cfg`), recopiés par `startup.s`. Le
reste du programme va de `$6000` à environ `$A400` ; `$1000-$1FFF` porte le
tampon ProDOS, la sauvegarde et les tableaux de dessin de la planche.

La planche du drone B attend à côté (`src/swap.s`) : `board_swap()`
l'échange avec la planche chargée quand le technicien change de drone,
`board_swap_run()` n'en échange que les portes utilisées et leurs valeurs
autour de son tour (un tour à deux drones coûte environ 2,6 images).

## La souris

Le pointeur (`src/pointer.s`) sauve les 4 octets × 6 lignes sous lui et y
ajoute la flèche par OU ; il se redessine en une fraction d'image. Pendant
les longs dessins, `ui_latch()` relit la souris pour ne pas perdre un clic,
au plus une fois par trame sur le //e : deux lectures de la carte coup sur
coup lui font perdre une partie du mouvement. Sur le //c, la souris
intégrée compte par interruptions, masquées pendant les accès à la mémoire
auxiliaire : un clic très bref pendant un grand dessin peut s'y perdre.

Les tests des missions cliquent par un point d'entrée de test
(`test_click`, `test_x`, `test_y` dans `ui.c`, écrits par a2shot pendant
l'attente de trame) ; la souris elle-même est testée par
`tests/test_lab.py`, en sauts de 40 pixels au plus.
