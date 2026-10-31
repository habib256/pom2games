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

## L'interface (refonte du 2026-10-30)

Tout ce que le jeu affiche est **en anglais** ; tous les textes sont dans
`tools/gen_text.py` (une seule source), compilés en `RSS.TEXT1/2` et lus au
démarrage dans la mémoire auxiliaire (`$6000-$A000`, `src/text.s`).

- **Briefing** : choisir une mission (titre, PLAY, NEXT) ouvre sa page :
  le but, ce qui est nouveau, pour la première les étapes une à une.
  HINT révèle un premier indice, puis un second, plus précis. PLAY va dans
  la salle. Dans la salle ou dans un drone, GOAL (ou H) y revient, et PLAY
  ramène là où l'on était, sans remettre la salle au départ.
- **La ligne du bas explique** (`src/hover.c`) : ce que montre le pointeur
  (capteur, moteur, pièce, broche, bouton, case de la salle, drone, objet,
  mission du titre) ; sur rien, ce qu'il faut faire ensuite (entrer dans le
  drone, prendre une pièce, finir le fil, sortir et lancer...). Un message
  du jeu (gravure, erreur, victoire) reste jusqu'à ce que le pointeur passe
  sur autre chose.
- **Moteurs** : à droite de la planche du drone, les propulseurs sont
  présentés par l'endroit où ils envoient le drone, dans l'ordre N E S W
  des capteurs : MOTOR E est le propulseur O (puits 3), qui pousse vers
  l'est. Les règles et les puits ne changent pas. Bornes de gauche :
  N E S W, H (la pince tient), R (radio reçue) ; de droite : N E S W,
  C (pince), R (radio émise).
- Pièces : AND, OR, XOR, NOT, MEM (la bascule : SET en haut, RESET en
  bas) ; puces 1-8, dans la rangée du bas, étiquetée TOOLBOX. Sur la
  planche, AND, OR, XOR et NOT ont leur symbole de schéma (D, bouclier,
  bouclier à double dos, triangle à rond ; src/symbol.s) ; MEM et les
  puces restent des boîtes étiquetées. L'aide (ELECTRONICS 3/6 et 4/6)
  montre chaque symbole à côté de sa table de vérité.
- **Alimentation** : la borne source 7 (POWER) vaut toujours 1 (dans le
  labo et les drones) ; elle est la dernière ligne de la colonne de gauche,
  « + », orange. Les valeurs la mettent à 1 dès la compilation. Gravée dans
  une puce, elle devient la source locale `CHIP_POWER` ($FE), qui redevient
  la POWER de la planche où la puce est posée ; + relié directement à une
  sortie de la puce passe par un TAMPON, comme une entrée. Avant, le seul 1
  constant était un NOT sans entrée (encore valable).
- **Aide** : dix pages (comment jouer, l'électronique en six : signaux,
  la boîte à outils, AND/OR, XOR/NOT avec leurs tables de vérité, MEM et le
  retard d'un tour, recettes ; le labo et les puces ; les touches ; les
  salles), NEXT / BACK / DONE (ou ESC). Ouverte par HELP au titre, GATES sur
  un briefing (retour au briefing), H au labo (la page du labo).
- Un fil en main se voit aussi sur le pointeur ; dans le drone, le
  technicien marche deux fois plus vite (6 pixels par image).

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
| 13 | LA CAISSE | la pince porte la caisse jusqu'à la plaque ; elle y tient la porte ouverte |
| 14 | LE TANDEM | A se gare sur la plaque et appelle ; B attend l'appel pour chercher la cellule |
| 15 | LE COMPTEUR | compter les ouvertures du puits (fronts du capteur O, par le retard des portes) ; tourner à la 2e |
| 16 | LA SPIRALE | quatre caps (trois bascules) : un choc devant, tourner à droite, jusqu'au centre |
| 17 | LE CONVOI | la pince tient la cellule pendant deux virages, la lâche en bas |
| 18 | DEUX CLES | la puce de LA CAISSE : caisse sur une plaque, drone sur l'autre, le technicien passe |
| 19 | LA PASSE | A pousse la cellule dans la fente des tunnels (trop basse pour un drone), la lâche et appelle ; B l'emporte |
| 20 | LES ETAGES | une OX rebouclée sur elle-même bascule est / ouest à chaque arrivée sur un étage (front de S) ; les fosses aux bouts piègent les rebonds |

Les tests (`tests/test_model.py`) prouvent qu'une solution existe pour
chacune, qu'une planche vide ne gagne rien, que le pilier exige une
bascule, qu'une cellule jamais lâchée ne compte pas, que la porte attend
le technicien, qu'un drone dans l'embrasure la bloque ouverte et que le
parking ouvre le passage, que le relais exige la radio (A parti trop tôt,
la porte se referme sous B), que deux drones se bloquent l'un l'autre, que
le zigzag exige l'alternance, que le colis attend le technicien, que le
gardien sans bascule ne se gare jamais, que la ronde exige deux bascules,
que le sas attend le technicien sur sa plaque, que la caisse, sans pince,
reste où elle est et que B, parti sans attendre l'appel, revient les mains
vides. `make test-long` joue toute la campagne en C, chaque mission avec sa
solution, à l'identique du modèle (le jeu la joue aussi de bout en bout : `tests/test_zone.py`).

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

- Dans la salle : un clic l'envoie vers ce point (3 pixels par image, il
  s'arrête contre les murs). **Il entre dans un drone quand il le touche
  après un clic sur ce drone** ; sinon il passe devant ou derrière, et un
  drone qui roule sur lui passe aussi sans l'embarquer.
- À l'intérieur : la planche du drone (capteurs à gauche, moteurs à
  droite), la boîte à outils et une porte jaune sous la grille. Un clic sur
  la planche envoie d'abord le technicien à cet endroit (6 pixels par
  image), et l'action (poser, tirer un fil, prendre) se fait quand il y
  arrive. Les clics sur la boîte à outils et les boutons sont immédiats.
  EXIT : il va à la porte et ressort **derrière le drone**, hors de son
  chemin : la planche est jouée quatre tours d'avance (capteurs tels
  quels, puis tout est remis) pour savoir où il va ; il sort à l'opposé,
  sinon sur un côté, en dernier devant lui (première place libre, centrée
  sur le drone).
- Sprites (`src/sprites.c`) : drone et technicien vus de profil, tournés
  du côté où ils sont allés en dernier (tables de rectangles, retournées
  vers l'ouest). Le drone : antenne (jaune quand la radio émet), dôme et
  visière, corps, bras et pince (blanche quand elle prend), réacteurs
  (orange quand un moteur tourne), échappement derrière quand il va de
  côté. Le technicien : casque, visière, sac, gant ; ses jambes
  alternent quand il marche.
- Dessin de la salle (depuis le 2026-10-31) : le compositeur DHGR sans
  scintillement (`dev/lib/hgrc` `dhgr_spr_*`). Les tuiles sont des formes
  de rectangles (`src/sprites.c`) sur la carte `tiles[]` ; objets (cases
  0-3), drones (4-5, couleurs 16-19 = leur palette, tournés par miroir) et
  technicien (6) sont ses sprites (`src/sprites_asm.s`). Après chaque tour
  (ou pas du technicien), une mise à jour recompose dans un tampon (les 255
  premiers octets du tampon ProDOS, libre à ce moment) les groupes de 7
  pixels qui ont changé, et écrit chaque octet de l'écran **une seule fois,
  avec sa valeur finale** : rien n'est effacé puis redessiné. Un changement
  de portes échange les tuiles porte/plaque et redessine leurs cases avec
  ce qui est dessus (un drone garé sur une plaque reste entier). Le
  pointeur, dans la salle, est la couche « overlay » du compositeur (ses
  lignes hors de la salle restent à `src/pointer.s`). `tests/test_zone.py`
  le vérifie (a2shot `storewatch` sur 120 mises à jour de deux missions).

### Boutons

| Écran | Boutons |
|---|---|
| Labo | RUN/PAUSE, STEP, BURN, CLEAR, TEST (retour à la mission jouée, sinon le briefing de la prochaine) |
| Titre | PLAY (le briefing de la prochaine mission), LAB, HELP (comment jouer, pièces et touches, la légende des salles ; ou H), RECORDS (le moins de portes par mission, la page du titre), PAGE (missions 15 et suivantes) ; clic sur une mission ouverte : son briefing |
| Briefing | PLAY, HINT (deux au plus), LAB, MENU |
| Zone | RUN/PAUSE, STEP, RESET (salle au départ) ou NEXT (mission gagnée : le briefing de la suivante), GOAL (le briefing), MENU |
| Drone | RUN/PAUSE, STEP, EXIT |

Clavier : flèches = pointeur, ESPACE ou RETURN = clic, ESC = lâcher,
M = marche/pause, P = un pas, G = graver, O = ouvrir une puce au labo,
1-9 et 0 = choisir une mission dans la zone (10 : touche 0), H = le
briefing de la mission (puis, sur le briefing, un indice), S = son coupé ou actif,
V = vitesse rapide (un tour par passage de boucle au lieu de deux),
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

Le jeu ne dessine qu'en page 1 du DHGR. Carte (au 2026-10-31) :

| Zone | Contenu | Libre |
|---|---|---|
| principale `$6000-$BE7F` | programme résident (`startup.s` l'y recopie), dont les appels et l'overlay du compositeur ; pile C de 128 octets ensuite | 448 o |
| principale `$4000-$5FFF` (page 2) | **fenêtre des overlays** : PLAY (avec le code du compositeur, `DHGRSPRCODE`) ou FRONT | PLAY 162 o, FRONT ~5,6 Ko |
| principale `$0C40-$0FFF` (L8) | résident : `hover.c`, symboles des portes (`symbol.s`) | ~260 o |
| principale `$0800-$0C3F` | page zéro sauvée, planche du drone B (`swap.s`), formes du pointeur | — |
| principale `$1000-$1FFF` | tampon ProDOS (aussi le canevas du compositeur pendant ses mises à jour), sauvegarde, tableaux de la planche | — |
| auxiliaire `$4000-$5FFF` | image de PLAY | — |
| auxiliaire `$6000-$905D` | textes (`RSS.TEXT1/2`, lus une ligne à la fois) | jusqu'à `$9FFF` |
| auxiliaire `$A000-$BFFF` | image de FRONT | — |
| auxiliaire `$0800-$1FFF`, carte langage auxiliaire | libres (`/RAM` est déconnecté) | 6 Ko + 16 Ko |

**Overlays** (`src/overlay.s`, `src/game.cfg`) : la fenêtre `$4000-$5FFF`
porte le code d'un seul groupe d'écrans à la fois. PLAY = `zone.c`,
`sprites.c`, `sprites_asm.s` et le cœur du compositeur DHGR (`DHGRSPRCODE` :
mise à jour, peintres, écriture, tuiles ; ce code se modifie lui-même mais
se recale à chaque appel, une recopie ne le gêne pas) (la salle,
l'intérieur des drones) ; FRONT = `title.c`, `help.c`,
le briefing et la lecture de la sauvegarde (`main.c`, `#pragma code-name`).
`RSS.OVL` (PLAY complété à 8 Ko, puis FRONT) est lu au démarrage et rangé en
auxiliaire ; `overlay_use(n)` recopie le groupe demandé s'il n'est pas déjà
là, une page à la fois par une boucle en page zéro (que RAMRD ne touche
pas) : PLAY en 0,11 s. Les fonctions résidentes qui ouvrent un écran
l'appellent (`enter_title`, `enter_help`, `enter_brief`, `start_mission`,
`enter_zone`, `enter_drone`). Règles :

- l'état des overlays est en BSS/DATA résidents : seuls le code et les
  tables constantes sont remplacés ;
- un code d'overlay ne provoque jamais un changement d'overlay (même par un
  appel) avant de continuer : il reviendrait dans l'autre groupe. Les
  fonctions qui changent d'écran restent donc résidentes ;
- `mission_count()` et `mission_goal()` sont résidentes (`hover.c`) : tous
  les écrans s'en servent.

La planche du drone B attend à côté (`src/swap.s`) : `board_swap()`
l'échange avec la planche chargée quand le technicien change de drone,
`board_swap_run()` n'en échange que les portes utilisées et leurs valeurs
autour de son tour (un tour à deux drones coûte environ 2,6 images).

## La souris

Le pointeur (`src/pointer.s`) sauve les 4 octets × 6 lignes sous lui et y
ajoute la flèche par OU ; il se redessine en une fraction d'image. Dans la
salle, ses lignes qui y sont passent par le compositeur (overlay, compilé
avec `DHGR_SPR_OVERLAY_INSIDE`) : composées avec les sprites en une passe,
elles ne se cachent plus pendant les dessins de la salle ; `pointer.s` ne
dessine que ses lignes au-dessus ou au-dessous (`hide()` ne cache que
celles-là). Pendant
les longs dessins, `ui_latch()` relit la souris pour ne pas perdre un clic,
au plus une fois par trame sur le //e : deux lectures de la carte coup sur
coup lui font perdre une partie du mouvement. Sur le //c, la souris
intégrée compte par interruptions, masquées pendant les accès à la mémoire
auxiliaire : un clic très bref pendant un grand dessin peut s'y perdre.

Les tests des missions cliquent par un point d'entrée de test
(`test_click`, `test_x`, `test_y` dans `ui.c`, écrits par a2shot pendant
l'attente de trame) ; la souris elle-même est testée par
`tests/test_lab.py`, en sauts de 40 pixels au plus.
