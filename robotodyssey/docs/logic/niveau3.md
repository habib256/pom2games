# Niveau 3 : « Explore the Town! »

*[← ANALYSE](../ANALYSE.md)* · structures : [world.md](world.md) · boucle : [simulation.md](simulation.md)

Code `$0803-$1FFB` (bloc `$0CB`), données et code `$8EF0-$94EA` (bloc
`$0D5`), salles et textes `$0C1`. Désassemblage : `build/c_lvl3.txt`
(`$0803-$1FFF`) et, pour `$8EF0`, `tools/disasm.py build/lvl3.bin 8EF0 94EB`
avec `--region 8EF0-94EB` et les régions par défaut. Les points
**[vérifié]** l'ont été dans a2shot (voir [Méthode](#méthode-a2shot)).

## Vue d'ensemble

Le joueur arrive salle `$02` (« EXIT », au bout de l'escalator du niveau 2).
Il doit faire signer un **Form-12** par la sentinelle, puis rejoindre le
bureau du portier (salle `$2A`). Le chemin passe par six énigmes :

| # | Énigme | Salles | Routines |
|---|---|---|---|
| 1 | orage magnétique, bouclier, éditeur de capteur | `$05`, `$06 $07 $08 $19 $1A $1B $3C` | `$0AFC`, `$0C6A`, `$0D0A`, `$0D43`, `$0D8E`, `$0DB5` |
| 2 | jeton qui fuit le joueur | `$3C` | `$9065` |
| 3 | dalle « junk », porte, ascenseur, garde du puits | `$0F`, `$10`, `$11`, `$30` | `$1471`, `$92CA`, `$15EF`, `$16BE`, `$15AD`, `$1034` |
| 4 | distributeur : jeton, tirette, Form-12 | `$12` | `$910C`, `$9125`, `$9160`, `$9236`, `$927D` |
| 5 | deux boutons et garde | `$21` | `$8F89`, `$8F55`, `$1034` |
| 6 | barrière laser, cible `$FB`, fenêtre | `$22`, `$16` | `$1702`, `$1842` |
| 7 | sentinelle-portier, Form-12, sortie | `$2A` (et toute sa ligne) | `$0DF1`, `$0F59`, `$9325` |

Les routines de la boucle (`$0849-$094C`, même squelette qu'au niveau 1) :

| Appel | Rôle |
|---|---|
| `$0C6A` | orage : dégâts aux robots (batterie −2) |
| `$19B5` | placement aléatoire de 6 objets au premier départ de la salle `$02` |
| `$9058` | jeton (`$9065`), barrière du joueur salle `$12` (`$910C`), distributeur (`$9125`, `$9160`) |
| `$15EF` | ascenseur |
| `$8F89` | deux boutons de la salle `$21` |
| `$1471` | trois portes coulissantes |
| `$1702` | fenêtre `$22`→`$16`, cible `$FB`, barrière laser |
| `$1034` | deux gardes (salles `$10` et `$21`) |
| `$927D` | décor : silhouette de la dalle (`$0F`), distributeur (`$12`) |
| `$1842` | décor : fenêtre (`$22`), faisceaux laser |
| `$8F55` | dessin des deux boutons |
| `$9236` | dessin de la tirette du distributeur |
| `$0AFC` | orage : déplacement des nuages ; consommation du bouclier (`$0D0A`) |
| `$0D43` | halo du bouclier autour du robot protégé |
| `$15AD` | dessin de la cabine d'ascenseur (`$0F`, `$11`) |
| `$16BE` | intérieur de l'ascenseur : flèche de direction, porte |
| `$92CA` | tas de ferraille (`$0F`) : la ferraille `$F8` saute au hasard |
| `$0DF1` | Form-12, sentinelle, confiscation du bouclier, sortie |
| `$0D8E` | dessin de l'éditeur de capteur (`$05`) |
| `$0DB5` | éditeur de capteur |

## Objets du niveau

Placés par la sortie du niveau 2 (`$0B39/$0B49/$0B59/$0B69`) ; sprites et
couleurs hérités du niveau 1 et de la sortie 2 (`$F7` sprite `$2F`, `$04` et
`$F7` non saisissables). Relevé en RAM au chargement **[vérifié]** :

| Objet | Rôle au niveau 3 | Salle | X,Y | Sprite | Saisissable |
|---|---|---|---|---|---|
| `$04` | **jeton** (sprite cristal, couleur 4) | `$3C` | 61,95 | `$39` | non |
| `$05`, `$F7`, `$08` | **nuages d'orage** | `$07`, `$06`, `$3F` | | `$2F` | non |
| `$06` | **tirette** du distributeur (attachée à elle-même) | `$12` | 77,111 | `$04` | oui, mais attachée |
| `$07` | **Form-12** | `$12` | 22,145 | `$03` | oui |
| `$16`/`$17` | **bouclier** : décor `$16` attaché à `$17` (+0,+15) ; `$17` est une **broche d'entrée** | `$05` | 27,38 | `$2F` / `$06` | oui |
| `$18` | pinceau (couleur 5), sans rôle trouvé dans le code **(?)** | `$2A` | 16,51 | `$1F` | non |
| `$22`/`$23` | **sentinelle-portier** : `$22` attachée à elle-même (−1,0), `$23` à `$22` (+7,0) | `$2A` | 53,105 | `$29`/`$2C` | non |
| `$F8` | **ferraille** (« junk ») | `$0F` | 24,22 | `$3A` | oui |
| `$FB` | **cible** derrière le laser | `$16` | 67,99 | `$32` | non |
| `$0D` | capteur de direction 1, sprite `$32` = celui de `$FB` | aléatoire | | | |
| `$0E`, `$15` | capteur de direction 2, de contact 3 (sprite clé `$38`) | aléatoire | | | |
| `$EB`, `$EC` | puces 5 et 6, vierges | aléatoire | | | |
| `$F9` | cristal chargé | aléatoire | | | |

**Placement aléatoire (`$19B5`).** Tant que le joueur est salle `$02`,
l'index `$8F1B` tourne de 0 à 5 à chaque tour. Au premier tour hors de
`$02` (`$8F1A` passe à 1), les objets `$199D` = `0D 0E 15 EB F9 EC` (pris
de `$EC` à `$0D`) reçoivent les 6 positions suivantes, à partir de
`$8F1B`, en rotation **[vérifié]** :

| Index | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Salle `$19A3` | `$11` | `$1F` | `$26` | `$2B` | `$2A` | `$19` |
| X `$19A9` | 49 | 64 | 24 | 39 | 114 | 10 |
| Y `$19AF` | 96 | 125 | 52 | 87 | 92 | 40 |

**La sentinelle marche.** `$22` est son propre porteur avec un décalage
X de −1 : `$9C53` la recule d'une unité par tour, sans test de mur, et
`$9DB9` la fait passer dans la salle de gauche (`$2A` → `$16` → `$22` →
`$21` → …) **[vérifié]** (`$6422` −20 en 200 trames). C'était déjà le cas
au niveau 1.

## Énigme 1 : l'orage magnétique et le bouclier

Indice : « Weather the magnetic storm with a shield in a 'bot. (Turn it on.) »

**Salles d'orage** (`$9431`, 7 octets) : `$06 $07 $08 $19 $1A $1B $3C`.
**Nuages** (`$942E`) : `$05`, `$F7`, `$08`.

**Déplacement (`$0AFC`).** Pour chaque robot `r = 3…0` (`$8200` :
`F0 F2 F4 01`) dont la salle est une salle d'orage (`$0DDF`), un nuage lui
est affecté (`$08` d'abord, puis `$F7`, puis `$05`) et mis dans sa salle
(`$9E07`). Les nuages restants vont dans la salle affichée `$9C2D` si
c'est une salle d'orage (`$0B98`). Position : toutes les 12 tours
(`$8EFD`), cible aléatoire `$8EF4/$8EF7` (`$D414`, < 100) et pas
`$8EFA` ; entre-temps le nuage glisse en diagonale (`$0C51`) ; X = cible
+ 12, Y = cible + 32. Le nuage est dessiné en particules (`$D6BD`).
`$0BBC` détache chaque tour `$05`, `$08`, `$F7` de leur porteur : une pince
ne peut pas garder un nuage. **[vérifié]** capture `storm` : deux nuages
autour de Sparky et du joueur salle `$07`.

**Dégâts (`$0C6A`).** Pour chaque robot `r = 2…0` (Sparky, Checkers,
Scanner) dont la moitié gauche touche `$05`, `$08` ou `$F7` (collision
pixel `$A835`) : sauf si le bouclier `$17` est dans **son** intérieur
(`$8204[r]`) avec la couleur 5, son `$0C` et **batterie −2** (minimum 0 ;
`$8DE1`, `$8DFB`, `$8E15`). Le joueur n'est jamais touché. Le 4ᵉ robot
n'est pas testé. **[vérifié]** nuage `$08` posé sur Sparky, `call:0C6A` :
`$8DE1` 13 → 11 ; bouclier allumé dans `$09` : 11 → 11 ; bouclier éteint :
11 → 9.

**Le bouclier (`$0D0A`).** `$17` est une broche d'entrée (sprite `$06`) :
le joueur doit y **souder un fil chaud** dans l'intérieur du robot
(« Turn it on »). Allumé dans un intérieur de robot, il coûte `$64` (100)
par tour à l'accumulateur de batterie de ce robot (`$DE21/$DE3E/$DE5B`),
contre 30 au repos et 60 par propulseur. Télécommande coupée
(`$8DA7 ≠ 1`) : sa couleur est forcée à 7. **[vérifié]** `$8E32/$8E33`
`$385C` → `$38C0` ; avec `$8DA7 = 0`, `$6217` passe à 7. `$0D43/$0D6F`
dessine un halo (motif `$949B`) autour du robot protégé.

**L'éditeur de capteur (`$0DB5`, salle `$05`).** Si la salle affichée est
`$05`, tout capteur `$0D-$15` posé dans X 20-29, Y 123-132 (le cadre dessiné
par `$0D8E`, sprite `$2F` en (25,128)) prend le sprite `$2F`, celui des
nuages : il **détecte alors l'orage** (un capteur cherche les objets de
son sprite, voir simulation.md). Utilité : allumer le bouclier seulement en
présence d'un nuage (capteur de salle) ou fuir les nuages (capteur de
direction). **[vérifié]** capteur `$10` posé en (24,128) avec le joueur
salle `$05` : `$6110` `$38` → `$2F` ; sans le joueur dans la salle, rien.

## Énigme 2 : le jeton qui fuit (`$9065`, salle `$3C`)

« I never could hang onto money... » Le jeton `$04` est en salle `$3C`, salle
d'orage. Tant qu'il n'a pas été inséré (`$8F10 = 0`), qu'il est libre et
dans `$3C`, si le joueur est à moins de 30 en X **et** de 48 en Y, le jeton
saute : X = X joueur ± 30 (rebouclé dans 8-117), Y = Y joueur ± 48
(rebouclé dans 17-143), du côté opposé au joueur. **[vérifié]** joueur en
(48,95) : jeton (61,95) → (78,47). Il n'est pas saisissable par le joueur
(`$6904 = $FF`) : seul **un robot** (pince) peut le prendre, donc un robot
qui traverse l'orage avec son bouclier.

## Énigme 3 : ferraille, porte et ascenseur (salles `$0F`-`$11`, `$30`)

**Tas de ferraille (`$92CA`).** Si la salle affichée est `$0F`, `$9301` :
quand la ferraille `$F8` y est en Y < 48, elle saute à chaque tour en
X aléatoire < 63, Y aléatoire < 48 **[vérifié]** ((16,16) → (3,43)) ; puis
10 sprites aléatoires sont dessinés (le tas). Il faut la sortir du tas
(« The things robots throw away... »).

**Portes coulissantes (`$1471`).** Trois portes, tables à `$18F7` :

| Porte | Salle | Commande | Tuiles (colonne, rangées) | Course |
|---|---|---|---|---|
| 0 | `$0F` | objet `$1900` = `$F8` posé en X 89-93, Y 74-84 (`$1903/$1906` = 91,80) : **bascule** à chaque arrivée (`$8F4D` front) | colonne 15, rangées 6-8 → tassée en rangée 8 | 3 tuiles, pas 3, 0→6 |
| 1 | `$16` | code : `$177D` (cible `$FB`) | colonne 19, rangées 5-8 | 4 tuiles, 0→8 |
| 2 | `$30` | code : ascenseur | colonne 0, rangées 1-5 | 5 tuiles, 0→10 |

`$8F50[i]` = demande (1 ouverte), `$8F4A[i]` = position ; chaque tour la
porte avance d'un pas (`$1541` efface puis redessine les tuiles par
`$B3AA`). État initial `$8F50 = 00 00 01`. « Sometimes junk can open
doors... » : poser `$F8` sur sa silhouette (sprite `$3A` dessiné en (91,80)
couleur 6 par `$927D`) ouvre l'accès à l'ascenseur. **[vérifié]** `$F8`
posé en (91,80) : `$8F50[0]` → 1, `$8F4A[0]` → 6.

**Garde du puits (`$1034`, salle `$10`).** Voir [énigme 5](#gardes-1034) :
le puits `$0F` → `$10` → `$11` est gardé, il faut l'ascenseur.

**Ascenseur (`$15EF`), état `$8F0A`** (initial 1) :

| État | Condition | Effet |
|---|---|---|
| 1 | joueur salle `$0F` ou `$11`, X ≥ 104, 96 ≤ Y < 128 | → 2 ; salle d'origine dans `$8F0C` ; joueur mis en cabine `$30` (7,16) |
| 2 | joueur en X 4-11, Y 72-87 (bouton) | → 3, `$8F0B = 1`, son `$0D`, porte de cabine fermée (`$1580`) |
| 2 | joueur en Y < 80 et X < 7 (sortie) | → 1 ; joueur dans `$8F0C` en (102,96) |
| 3 | 10 tours (`$8F0D`) | porte ouverte (`$1575`), → 2, `$8F0C` alterne `$0F` ↔ `$11` |

Seul l'objet `$00` est testé : un robot ne prend l'ascenseur que tenu par
le joueur. Rester sur le bouton relance un trajet à chaque arrivée.
`$16BE` dessine la flèche (haut si `$8F0C = $0F`). **[vérifié]** `$0F`
(112,112) → cabine `$30` (7,16) ; bouton → état 3, `$8F0C` `$0F` → `$11` ;
sortie à la fin → salle `$0F` (102,96) (le joueur était resté sur le bouton,
d'où un aller-retour).

## Énigme 4 : le distributeur (salle `$12`)

Textes : « VENDING MACHINE », « 1) Insert Token », « 2) Pull ».

- **Barrière du joueur (`$910C`)** : dans `$12`, si X ≥ 7 et Y > 32, le
  joueur est ramené à Y = 32 (ligne pointillée dessinée par `$92A4`).
  **[vérifié]** (48,96) → Y = 32. Le joueur ne peut pas monter : ce sont les
  robots qui opèrent (le joueur peut être **dans** un robot : sa salle est
  alors l'intérieur, non bridé).
- **Insertion (`$9125`)** : jeton `$04` libre dans `$12` en X < 70,
  Y ≥ 96 (sous « Insert Token ») → `$04` en `$3F`, `$8F10 = 1`, la tirette
  `$06` est détachée (`$6606 = $FF`, elle était son propre porteur, donc
  insaisissable par une pince), son `$0E`. **[vérifié]**
- **Tirette (`$9160`)**, chaque tour après l'insertion : si un robot tient
  `$06` (`$8DAD-$8DAF`), Y tirette = 112 et le robot est remis à la même
  hauteur, X tirette ≥ 77 ; sinon X tirette = 77 (elle revient). La rangée 7
  (rangée écran 4, le plancher du compartiment du haut) est réécrite
  (`$B3AA`) selon `i = (X − 70) / 8` (tables `$9438-$948B`) : une barre de
  6 tuiles glisse des colonnes 1-6 (i = 0) aux colonnes 12-17 (i = 6).
  Tirette tirée à X ≥ 118 : le compartiment gauche, où est le **Form-12**
  `$07` (22,145), est ouvert par en dessous. **[vérifié]** captures `v1`
  (tirée, X = 122) et `v2` (relâchée, refermée, X = 77).
- Il faut donc **deux robots** : l'un tient la tirette à droite, l'autre
  monte prendre le Form-12 **(?)** (aucun autre moyen trouvé : le joueur
  est bridé et la tirette revient dès qu'on la lâche).

## Énigme 5 : les deux boutons et les gardes

### Boutons (`$8F89`, salle `$21`)

« Two buttons a day keep the sentry away. » Pour chaque robot `r = 2…0`
dans `$21` : bouton 1 si sa moitié gauche est en X 81-87, Y ≈ 14-25 ;
bouton 2 en X 81-87, Y 149-161 (`$8F06-$8F09`, bornes calculées sans
`SEC`, à ±1 près). Chaque bouton reste enfoncé (`$8F02`, `$8F03`),
devient orange (`$8F04/$8F05` = 5, dessin `$8F55`) avec le son `$0D`. Les
deux enfoncés : `$8F01 = 1`, **le garde de `$21` disparaît**
(`$8F1D = $3F`), le texte `$20` part en `$3F` et le texte `$0C`
« KLAATU BARADA NIKTO! » arrive salle `$21`. Seuls les robots comptent
(le joueur non). **[vérifié]** Sparky en (84,18) puis (84,156) :
`$8F01-$8F05 = 01 01 01 05 05`, `$8F1D = $3F`, capture `btn`. Les boutons
sont dans les ouvertures du haut et du bas de la salle.

### Gardes (`$1034`) {#gardes-1034}

Deux gardes dessinés (pas des objets) : salle `$8F1C` (`$10`, `$21`),
position `$8F1E/$8F20`, mode `$8F28` (3 et 3), couleur `$8F2A` (6), œil
`$8F2F` (5 en chasse, 7 sinon), sprites `$196D…` (3 images, `$18F1/$18F4`).

- Mode 1 : patrouille entre `$18DF/$18E3` et `$18E1/$18E5` (garde 0 :
  (42,144)↔(42,48) ; garde 1 : (21,128)↔(21,48)), pas de 2. Non utilisé
  au départ **(?)**.
- Modes 2 et 3 : surveille les intrus `$18E7` = `00 F0 F2 F4 01` (joueur
  et robots ; mode 3 suit aussi le joueur dans un robot, intérieurs
  `$18EC`). `$1227` note le **côté d'entrée** (gauche X < 7, droite
  X ≥ 127, bas Y < 16, haut Y ≥ 161) et la position. L'intrus devient
  cible quand il dépasse un seuil depuis son côté (`$1267`) : gauche
  X ≥ 28, droite X < 105, bas Y ≥ 48, haut Y < 128.
- Chasse (`$1314`) : le garde fonce (pas ≤ 28 en X, 39 en Y) ; à moins de
  29 (|dX|+|dY|) l'intrus est **figé** (`$8ED4` = son numéro : le joueur
  perd le clavier, un robot ne bouge plus) ; à moins de 9 : son `$0A`,
  capture. `$13BF` le **ramène à son point d'entrée** (pas de 2), son
  `$0B`, `$8ED4 = $FF`.

**[vérifié]** joueur entré par la gauche de `$21` en (3,80) puis poussé à
X = 48 : `$8ED4 = 0`, garde à côté, puis joueur rendu en (3,80) et
`$8ED4 = $FF`.

Conséquence : on peut longer le bord par lequel on est entré sans
déclencher le garde ; les boutons de `$21` sont précisément au bord haut et
au bord bas. Le garde de `$10` interdit le puits (il faut l'ascenseur).

## Énigme 6 : le laser et la cible `$FB` (salles `$22`, `$16`)

- **Fenêtre (`$170C`)** : joueur salle `$22` en X ≥ 121, Y < 30 (coin bas
  droit, « Look into the next room. ---} ») : la salle affichée devient
  `$16` (`$8F18 = $16`, `$8F17 = 0`). **[vérifié]** capture `window` : la
  cible `$FB` dans un enclos de murs.
- **Laser (`$173A`)**, tant que `$8F19 = 1` (initial) : `$18BF` ne regarde
  que **le joueur**, ou le robot qui le contient : dans `$22`, le joueur
  est bridé à X < 126 (→ 123), le robot qui le porte à X < 127 (→ 123).
  Un robot **sans** le joueur passe. `$1842` dessine 5 faisceaux animés
  (Y 80-120, `$948C`) au bord droit de `$22` (et au bord gauche vu par la
  fenêtre). **[vérifié]** joueur poussé à X = 128 → 123 ; Sparky seul à
  X = 127 n'est pas ramené.
- **Cible (`$177D`)** : si `$FB` touche une moitié de Sparky, Checkers ou
  Scanner (`$A835`), ou est tenue par l'un d'eux : elle est relâchée et
  envoyée en `$3F`, `$8F19 = 0` (laser coupé), son `$0D`, **porte 1 de la
  salle `$16` ouverte** (colonne 19, vers `$2A`). **[vérifié]** Sparky
  posé sur `$FB` : `$8F19 = 0`, `$63FB = $3F`, `$8F4A[1]` 0 → 8.
- Le capteur de direction 1 (`$0D`) porte le sprite `$32` de `$FB` : il
  guide un robot autonome vers la cible.

Il faut donc programmer un robot pour passer seul de `$22` à `$16` et
toucher `$FB`, en le regardant par la fenêtre.

## Énigme 7 : la sentinelle, le Form-12 et la sortie (`$0DF1`)

État `$8F13` (initial 0) :

| État | Condition | Effet |
|---|---|---|
| 0 | `$07` dans la salle de `$23`, le touche (`$A835`), ni tenu par le joueur ni par un robot | `$07` attaché à `$23` (−4,−3), insaisissable → 1 |
| 1 | — | la sentinelle va vers (26,51) (`$0E50`, ±1 par tour en Y puis en X), quelle que soit la salle ; à l'arrivée : `$07` en `$3F`, son `$0E` → 3 |
| 3 | le joueur tient `$17` (bouclier) | → 2 |
| 3 | `$17` dans un robot (même imbriqué, `$1020`) qui est salle `$2A` | la sentinelle **chasse** ce robot (`$0FB4`, pas ≤ 7 / 16) ; au contact : fils de `$17` coupés, `$17` attaché à `$22` (−10,0) → 4 |
| 3 | sinon | → 4 |
| 4 | — | la sentinelle va vers (26,51) ; à l'arrivée `$17` en `$3F` (**bouclier confisqué**) → 2 |
| 2 | salle affichée `$2A` | dessine le joueur fantôme orange en (35,80) et un cadre (`$0F59`) ; si le joueur est **exactement** en (35,80), sprite normal (`$6100 = 0`) : **sortie** |

**Le Form-12 se remet en le posant sur le trajet de la sentinelle** : elle
le ramasse au passage (« Submit a Form-12, please. OFFICIAL GATEKEEPER »
est le texte de `$2A`, sa salle de départ).

**Pas de blocage dans une vraie partie [vérifié].** Le recul de −1 par
tour vu dans les premiers essais venait du raccourci de chargement : au
niveau 1, la sentinelle `$22` est fixe et attachée à elle-même
(`$6622 = $22`, décalage −1), et c'est la sortie 1 → 2 (`$0BB7`) qui la
détache (`$6622 = $FF`). Charger le niveau 2 par `go:0AA0` saute cette
sortie et laisse la sentinelle dériver. Par la vraie chaîne de sorties
(`go:0AE6`, ESC, `go:0AEC`, ESC), Form-12 posé sur `$23` en (47,113) : état
1, la sentinelle descend puis va à gauche, arrive en (26,51), `$07` part en
`$3F` et l'état passe à 2 (sortie active). L'état 3 → 2 par « le joueur
tient le bouclier » reste la seule façon de garder le bouclier.

**Sortie (`$0EE9`, boucle bloquante `$0ECF`).** Joueur en couleur 4 ;
toutes les 6 images `$8F15 += 2` et une note montante (`$9F13`) ; à
`$8F15 ≥ 9` son 9 puis `JMP $9325`. **[vérifié]** joueur posé en (35,80)
salle `$2A` avec `$8F13 = 2` : animation, écran « Then press ESC », puis
chargement du niveau 4.

## Sortie 3 → 4 (`$9325-$942D`)

1. `$1DEA` (texte de la boîte à outils caché) ; l'objet tenu est mis en
   (0,0) et ses fils suivent (`$B8E6`).
2. `$6623 = $FF` : la moitié droite de la sentinelle est détachée.
3. Bouclier `$17` : s'il n'est pas tenu par le joueur, (0,0), fils coupés
   (`$B8ED`), `$3F`.
4. Tri `$FE…$01` (comme au niveau 2) : tout objet ni dans `$3F`, ni tenu,
   ni attaché, ni dans un intérieur de robot `$8204` part en `$3F`. `$22`,
   attachée à elle-même, reste.
5. Joueur couleur 7 (sa salle et sa position ne sont pas changées : il reste
   en (35,80) salle `$2A`).
6. `$9396[0-4]` = `04 06 07 F7 FB` : sprite `$33` (« keyhole » au PC),
   saisissables, détachés, couleurs `$939F` = `05 06 06 05 07`. Puis `$05`
   sprite `$32`, `$08` sprite `$3F` couleur 5 détaché (non placés : restent
   en `$3F`, pour le niveau 4 **(?)**).
7. Placement (`$9396/$93A4/$93AD/$93B6`, 9 entrées) :

   | Objet | Salle | X | Y | Remarque |
   |---|---|---|---|---|
   | `$04` | `$1B` | 102 | 158 | serrure, couleur 5 |
   | `$06` | `$2A` | 119 | 152 | serrure, couleur 6 |
   | `$07` | `$28` | 44 | 88 | serrure, couleur 6 |
   | `$F7` | `$31` | 108 | 62 | serrure, couleur 5 |
   | `$FB` | `$1C` | 68 | 32 | serrure, couleur 7 |
   | `$22` | `$3C` | 69 | 93 | sentinelle (moitié gauche seule) |
   | `$ED` | `$3C` | 112 | 38 | puce 7 |
   | `$EE` | `$3A` | 16 | 39 | puce 8 |
   | `$01` | `$26` | 64 | 88 | 4ᵉ robot (la moitié `$02` suit) |

8. `$0A37` avec X = 2 : écran `$3E` « Be sure the Robot Odyssey disk… Then
   press ESC » ; attente d'ESC (`$9B`), puis `$0AB3` : `$02D0 = 2`,
   `$02D1 = 3`, `$02D2 = 2`, saut RESET.

**[vérifié]** RAM au début du niveau 4 : `$04` `$1B` (102,158) sprite `$33`
couleur 5, `$06` `$2A` (119,152), `$07` `$28` (44,88), `$F7` `$31`
(108,62), `$FB` `$1C` (68,32), `$ED` `$3C` (112,38), `$EE` `$3A` (16,39),
`$01/$02` `$26` (64,88)/(69,88) ; joueur `$2A` (35,80). `$22` avait déjà
bougé (salle `$15`), le niveau 4 la déplace. Pas de boîte à outils placée
par cette sortie.

## Solution imposée par le code

1. Quitter la salle `$02` : capteurs `$0D $0E $15`, puces 5-6 et cristal
   `$F9` sont répartis (`$19B5`).
2. Salle `$05` : prendre le bouclier `$17`, le mettre dans un robot et y
   souder un fil chaud ; éventuellement passer un capteur dans l'éditeur
   pour qu'il détecte l'orage.
3. Envoyer ce robot à travers les salles d'orage jusqu'en `$3C` et lui
   faire saisir le jeton `$04` (le joueur ne peut pas, le jeton le fuit).
4. Salle `$0F` : sortir la ferraille `$F8` du tas et la poser sur sa
   silhouette (91,80) pour ouvrir la porte de l'ascenseur.
5. Ascenseur `$0F` → `$11` en tenant le robot (le puits `$10` est gardé),
   puis salle `$12`.
6. Distributeur : le robot lâche le jeton sous « Insert Token » (X < 70,
   Y ≥ 96) ; un robot tient la tirette à fond à droite, un second monte
   prendre le Form-12 `$07`.
7. Poser le Form-12 sur le trajet de la sentinelle `$22/$23`, qui marche
   vers la gauche à travers la ville ; elle l'emporte vers (26,51) et le
   détruit (attention au blocage décrit plus haut).
8. Garder le **bouclier en main** (joueur) au moment où le Form-12
   disparaît : état 2 direct, le bouclier passe au niveau 4. Sinon il est
   confisqué.
9. Programmer un robot pour franchir seul le laser `$22` → `$16` et toucher
   `$FB` (capteur de direction `$0D`), en regardant par la fenêtre : laser
   coupé, porte `$16` → `$2A` ouverte.
10. Les deux boutons de `$21` (par des robots, depuis les bords haut et
    bas) font partir le garde de `$21`, sur le chemin de `$22` **(?)**.
11. Salle `$2A` : se placer exactement sur le joueur fantôme (35,80), sous sa
    forme normale (pas le fer à souder).

L'ordre 7-11 n'est pas contraint par le code, seulement par le plan des
salles (non relevé en détail).

## Variables du niveau (`$8EF0-$8F55`)

| Adresse | Rôle |
|---|---|
| `$8EF0-$8EF3` | orage : nuage courant, robot courant, nuages restants, salle |
| `$8EF4/$8EF7/$8EFA/$8EFD` | orage : X, Y, pas, compte à rebours, par nuage |
| `$8F00` | orage : pas de son au relâchement |
| `$8F01-$8F09` | boutons : fini, bouton 1, bouton 2, couleurs, fenêtre de test |
| `$8F0A-$8F0D` | ascenseur : état, en route, salle d'origine/destination, compte à rebours |
| `$8F0E`, `$8F0F` | compteurs de dessin (tas, tirette) |
| `$8F10` | jeton inséré |
| `$8F11/$8F12` | jeton : joueur proche en X / en Y |
| `$8F13` | état sentinelle / Form-12 / sortie |
| `$8F14/$8F15` | animation de sortie |
| `$8F16` | robot chassé par la sentinelle |
| `$8F17/$8F18` | X des faisceaux, salle vue par la fenêtre |
| `$8F19` | laser actif |
| `$8F1A/$8F1B` | placement aléatoire fait, index tournant |
| `$8F1C-$8F49` | gardes : salle, X, Y, phase, cible, sous-état, mode, couleur, index, entrées notées |
| `$8F4A/$8F4D/$8F50` | portes : position, front de la dalle, demande |
| `$8F53/$8F54` | portes : index, temporaire |

## Méthode a2shot

Arriver au niveau 3 **[vérifié]** sans jouer les niveaux 1 et 2 :

```sh
A=../dev/tools/a2shot/a2shot
$A --disk original/A_ROBOTROPOLIS.woz wait:2500 key:$'\r' wait:900 key:$'\r' wait:6500 \
   regs:00:00:01 go:0AA0 wait:3000 \
   go:0AEC wait:300 key:$'\e' wait:1500 ...
```

`go:0AA0` (Y = 1) est la sortie du niveau 1 : le niveau 2 est chargé.
**Attention** : ce raccourci saute la sortie 1 → 2 (`$0AE6`), qui détache
la sentinelle ; préférer `until:085B go:0AE6`, ESC.
`go:0AEC` exécute la sortie du niveau 2 (tri, table `$0B39`), qui attend
**ESC** (pas RETURN) ; le niveau 3 est alors chargé. Différences avec une
vraie partie : le joueur reste salle `$28` (salle de départ du niveau 1)
au lieu de `$02`, et les trois robots, non tenus, ont été envoyés en `$3F`
par le tri (dans le jeu, ils n'arrivent que s'ils sont tenus ou attachés
**(?)**). Poser `$02D0/$02D1` puis `reset` n'a pas été essayé : ce chemin
fait la même chose avec les objets placés.

Déplacer un objet (au début de la boucle, `until:0849:100`) :
`poke:9C2F:OBJ poke:9C2E:SALLE poke:64OBJ:X poke:65OBJ:Y call:9E07:5` ;
pour un robot, déplacer les deux moitiés. Un tour dure ≈ 12 trames : laisser
`wait:40` avant de relire.

## Non compris ou non vérifié

- Le blocage de la sentinelle en (25,51) : défaut réel du jeu ou artefact
  de mes positions de départ ; comment les joueurs le contournent.
- Le distributeur exige-t-il vraiment deux robots ?
- Les modes 1 et 2 des gardes ne sont jamais activés par le code lu
  (`$8F28` reste à 3) ; mode 2 sans doute résiduel.
- Le chemin exact entre les salles (murs, liens à sens unique comme
  `$14 → $03`, `$31`) n'est pas relevé ; l'utilité des boutons pour
  atteindre `$22`/`$2A` est déduite, pas tracée.
- Rôle de `$18` (pinceau, salle `$2A`), de `$05`/`$08` reconfigurés pour le
  niveau 4, et du sprite `$33` au niveau 4.
- Comment les robots arrivent du niveau 2 dans une vraie partie.
- Non vérifié en émulateur : la chasse du robot porteur du bouclier par la
  sentinelle (`$0FB4`), le dessin des faisceaux, la porte 2 de la cabine,
  les bornes exactes du bouton 1 (Y ≈ 14-25).
