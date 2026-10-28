# Niveau 4 : « Master Computer Center »

*[← ANALYSE](../ANALYSE.md)* · structures : [world.md](world.md) · boucle : [simulation.md](simulation.md) · niveau précédent : [niveau3.md](niveau3.md)

Code `$0803-$1FFB` (bloc `$0E2`), données et code `$8EF0-$945F` (bloc
`$0EB`), salles et textes `$0D8`. Désassemblage : `build/c_lvl4.txt`
(`$0803-$1FFF`) ; pour `$8EF0`, le code n'est pas trouvé tout seul :
`tools/disasm.py build/lvl4.bin 918C 9409 --entry 918C --entry 920F
--entry 931C --entry 9400 --region 8EF0-9500` (plus les régions par
défaut). Les points **[vérifié]** l'ont été dans a2shot (voir
[Méthode](#méthode-a2shot)).

## Vue d'ensemble

Le joueur arrive salle `$2A` (« MAIN OFFICE », (35,80), position de sortie
du niveau 3). La sortie est l'**ascenseur** (salle `$02`), dont la porte se
referme devant le joueur tant que l'**ordinateur central** marche. Pour
l'éteindre, il faut appuyer sur **quatre boutons**, un dans chaque quart de
la salle `$26` (« MASTER COMPUTER »). Chaque quart n'a qu'un accès, et
chaque accès est une énigme :

| # | Bouton (quart de `$26`) | Accès | Obstacle | Routines |
|---|---|---|---|---|
| 1 | haut gauche | `$1B` → conduits `$32…$35` → `$17` | le joueur est renvoyé ; un robot seul passe | `$0BD6` |
| 2 | bas gauche | `$24` → champ de mines `$2E…$2F` | mines invisibles ; tout ce qui porte le joueur explose | `$0C77` |
| 3 | haut droit | tunnel `$30`, porte à clé | champs de force par couleur ; deux serrures pour une clé | `$14EA`, `$1350`, `$1484` |
| 4 | bas droit | `$3B` → `$39` | barrière de `$3B` coupée par l'étincelle de `$39` | `$0E67`, `$0EFD`, `$0EDA` |

À côté : cinq **disquettes** (sprite `$33`) à lire au lecteur de la salle
`$1D` (« COMPUTER ROOM »), dont une **caméra** ; un **Sweeper 'Bot** qui
ramasse tout ce qui traîne dans les couloirs et le jette salle `$3C` ; le
4ᵉ robot, enfermé au centre de `$26` jusqu'à l'arrêt de l'ordinateur.

`$8EF0` vaut 1 quand l'ordinateur est éteint : toutes les énigmes sauf
l'étincelle et le Sweeper sont alors désactivées.

## Boucle principale (`$0853-$0952`)

Même squelette qu'au niveau 1 ([simulation.md](simulation.md)). Écarts :
`$DFA3` (marche), `$FE25` (entrer dans un robot) et `$A6AD` (contour de
l'objet visé) sont sautés en mode caméra (`$8F03 ≠ 0`) ; `$920F` est
appelé après la prise/dépose ; `$0C77` suit `$D000` **avant** les capteurs
et les fils.

| Appel | Rôle |
|---|---|
| `$1670` | `$8EF6` = joueur (0) ou robot qui le contient (le plus extérieur) |
| `$0999` | touches : `?` indices, ESC, `L` labo de puce, triche `$03FF` (comme niveau 1) |
| `$920F` | lecteur de disquettes, salle `$1D` |
| `$0E67` | barrière de la salle de sécurité `$3B` |
| `$0BD6` | conduits d'aération fermés au joueur |
| `$14EA` | champs de force du tunnel `$30/$31` |
| `$0C77` | champ de mines `$2C-$2F` |
| `$0EFD` | étincelle de la salle haute tension `$39` |
| `$12B0` | porte de l'ascenseur (salle `$02`) |
| `$1350` | deux serrures à clé (salles `$30`, `$31`) |
| `$931C` | mode caméra |
| `$0C33` | décor animé de la salle `$33` (conduit) |
| `$0FBB` | quatre boutons de `$26`, arrêt de l'ordinateur |
| `$10C8` | Sweeper 'Bot (sentinelle `$22`) |
| `$16B4` | icône de caméra dans chaque salle |
| `$1689` | dessin du chargeur de cristaux |
| `$918C` | dessin du décor du niveau (table `$910F`) |
| `$1484` | dessin des champs de force |
| `$0EDA` | éclair de la barrière de `$3B` |
| `$172A` | sortie : repère dans l'ascenseur, condition, animation |
| `$9400` | textes redessinés par-dessus en mode caméra |

Initialisation (`$0816-$0850`) : `$A66D` = `JSR $B8E6` (restauration
d'un appel), table des touches `$0809` → `$9C11`, `$9C51 = 0`, compteurs
de la boîte à outils (`$1DFE`), **chargeur de cristaux** salle `$39` en
(7,10) (`$8454-$8456`). Les variables `$8EF0…` sont rechargées avec le bloc
de données : ordinateur allumé, `$8EF1 = $FF`, caméra sur `$1D`.

## Salles

Nom de chaque salle : table `$91CF` (salle → numéro de texte), affiché par
la caméra.

| Salles | Nom (texte) |
|---|---|
| `$02` | ELEVATOR (`$18`) |
| `$03-$08`, `$0C`, `$0E-$15`, `$1E-$25`, `$27` | HALLWAY (`$1D`) |
| `$16`, `$32-$36` | VENTILATION SHAFT (`$1F`) |
| `$17` | NORTH CHAMBER (`$1C`) |
| `$18`, `$19` | TUNNEL BYPASS (`$13`) |
| `$1A-$1C` | LIBRARY (`$0E`) |
| `$1D` | COMPUTER ROOM (`$0D`) |
| `$26` | MASTER COMPUTER (`$1B`) |
| `$28` | MAP ANTEROOM (`$10`) |
| `$29`, `$2B`, `$37`, `$38` | MINEFIELD MAP (`$11`) |
| `$2A` | MAIN OFFICE (`$14`) |
| `$2C-$2F` | MINEFIELD (`$1A`) |
| `$30`, `$31` | FORCE FIELD TUNNEL (`$12`) |
| `$39` | HIGH VOLTAGE ROOM (`$16`) |
| `$3A` | LOBBY (`$19`) |
| `$3B` | SAFETY ROOM (`$17`) |
| `$3C` | TRASH DUMP (`$15`) |

Les couloirs font une boucle : `$03…$08` en haut, `$0C`, `$0E…$13` à
droite, `$14`, `$15`, `$1E…$21` en bas, `$22…$25`, `$27` à gauche. La
salle `$26` est au centre ; d'après les murs, ses quatre quarts ne
communiquent qu'avec `$17` (haut gauche, ouverture en haut), `$30` (haut
droit, ligne 8 à droite), `$2F` (bas gauche, à gauche) et `$39` (bas
droit, colonne 18 en bas). Le centre (colonnes 8-11, lignes 4-7) est fermé
et contient le 4ᵉ robot.

## Objets du niveau

Placés par la sortie du niveau 3 ([niveau3.md](niveau3.md#sortie-3--4-9325-942d)) ;
**[vérifié]** au début du niveau 4.

| Objet | Salle | Position | Rôle au niveau 4 |
|---|---|---|---|
| `$04` | `$1B` | (102,158) | disquette orange : « THE VENTILATION SHAFT » |
| `$06` | `$2A` | (119,152) | disquette bleue : « THE MASTER COMPUTER » |
| `$07` | `$28` | (44,88) | disquette bleue : « THE MINEFIELD » |
| `$F7` | `$31` | (108,62) | disquette orange : « THE FORCE FIELD TUNNEL » |
| `$FB` | `$1C` | (68,32) | disquette blanche : **caméra** |
| `$22` | `$3C` | (69,93) | Sweeper 'Bot (moitié gauche de la sentinelle seule) |
| `$ED`, `$EE` | `$3C`, `$3A` | (112,38), (16,39) | puces 7 et 8, vierges |
| `$01/$02` | `$26` | (64,88) | 4ᵉ robot, batterie 0, interrupteur coupé |
| `$05` | `$3F` | – | sprite `$32` : forme visible de l'étincelle (`$0EFD`) |
| `$FA` | – | – | **clé** du niveau 1 : seule clé des serrures ; le niveau 4 ne la fournit pas |

Ce qui vient des niveaux précédents n'est là que si le joueur l'a apporté
(voir [Robots](#robots-apportés)).

### Décor du niveau (`$910F`, 25 entrées)

Pseudo-objets dessinés par `$918C` (salle = salle affichée), qui ne sont
pas des objets du monde : sprite local `$910F+i` (16 octets en
`$8F0F + 16·sprite`), X `$9128`, Y `$9141`, salle `$915A`, couleur `$9173`.

| Entrées | Salle | Rôle |
|---|---|---|
| 0, 1 | `$3B` | flèches de part et d'autre de la barrière (8 et 126, Y 112) |
| 2 | `$39` | **étincelle** (mobile, couleur 7, 5 une fois court-circuitée) |
| 3-6 | `$26` | **quatre boutons** : (30,128) haut gauche, (50,31) bas gauche, (84,139) haut droit, (103,48) bas droit ; couleur 7 = relâché, 5 = appuyé |
| 7, 8 | `$30`, `$31` | **serrures** : (35,16) et (126,144) |
| 9-13 | `$1B`, `$17` | grilles des bouches d'aération, bord droit |
| 14-16 | `$1D` | terminal et lecteur de disquettes, (61-75,144) |
| 17, 18 | `$02` | flèche du bouton HOLD (126,24) |
| 19-22 | `$33` | ventilateur au bout du conduit (animé par `$0C33`) |
| 23, 24 | toutes | **icône de caméra** en haut à gauche (`$16B4`) |

## Disquettes et lecteur (`$920F`, salle `$1D`)

Condition, à chaque tour : joueur salle `$1D`, mains vides
(`$9C26 = $FF`), objet lâché au tour précédent (`$0955`) posé dans la fente
du lecteur, X ∈ [`$48`,`$50`), Y ∈ [`$88`,`$95`).

| Objet | Effet |
|---|---|
| `$04` | texte `$0C` « THE VENTILATION SHAFT » : *Counting chips can pick out air tubes. Be sure to pick the right tube.* |
| `$06` | texte `$06` « THE MASTER COMPUTER » : *Use the cameras to monitor robot progress. The computer can be turned off and the robot released by pressing the four buttons.* |
| `$07` | texte `$07` « THE MINEFIELD » : *The walls in the map room are in the same position as the mines in the minefield. Mines are set off when a robot thrusts against them for more than an instant. Additional mines keep out non-robots. Robot communication is helpful.* |
| `$F7` | texte `$09` « THE FORCE FIELD TUNNEL » : *Robot relays pass key items along. Plan ahead for the return journey.* |
| `$FB` | mode caméra (`$9322`) |
| autre | rien |

Lecture (`$925C`, `$9284`, `$92AC`, `$92D4`) : le texte est mis dans la
salle vide `$3D`, affiché, puis retiré ; le joueur est posé à
disquette + (4,−4) et le jeu boucle (`$930E` : clavier `$A97D`,
prise `$A5CD`) jusqu'à ce qu'il **reprenne la disquette**. Toute la
simulation est arrêtée pendant la lecture. **[vérifié]** `$06` posée en
(74,138) salle `$1D`, `$0955 = $06` : écran « THE MASTER COMPUTER », PC
dans `$930E`, ESPACE → `$9C26 = $06`, retour au jeu.

### Caméra (`$9322`, `$931C`, `$9345`)

Poser `$FB` dans le lecteur :

- `$8F03 = $FF` (caméra), `$8F04 = $1D` (salle vue), `$9C30 = 0` (murs du
  joueur coupés), `$FB` attachée à elle-même (immobile, ni saisissable par
  un robot ni balayable).
- À chaque tour, le joueur est remis à `$FB` + (4,−4) ; son pas du tour
  (`$8E84/$8E85`) choisit la salle voisine : X ≥ 3 droite, X ≤ −3 gauche,
  Y ≥ 5 haut, Y ≤ −6 bas (un pas normal, pas un pas fin). Lien `$3F` :
  pas de changement. La salle affichée `$9C2D` devient `$8F04` ; son nom
  (`$91CF`) y est écrit, couleur alternée 7/4 (`$8F05`) ; son `$10`.
- Le reste du jeu continue : on regarde les robots travailler ailleurs.
  L'icône de caméra clignote (5/7, `$16B4`).
- Sortie : bouton (`$8E3A = 1`) ou fer à souder (sprite du joueur ≠ 0) :
  `$8F03 = 0`, nom effacé, `$9C30 = 1` (le passe-muraille éventuel est
  perdu), `$FB` détachée.

**[vérifié]** `$FB` lue : `$8F03 = $FF`, `$8F04 = $1D` ; `K` → `$17`,
`M` → `$26` (capture : les quatre boutons et le 4ᵉ robot), `M` → `$39` ;
ESPACE → `$8F03 = 0`, `$9C30 = 1`, retour salle `$1D`.

## Énigme 1 : les conduits d'aération (`$0BD6`)

Active tant que `$8EF0 = 0`. Objet testé : `$8EF6` (le joueur, ou la
moitié droite du robot qui le contient).

| Salle de l'objet | Effet |
|---|---|
| `$17` ou `$1B` | X bloqué à `$7E` (moitié gauche à `$77`) : impossible de sortir à droite |
| `$35` | le **joueur** (objet 0, même s'il était dans un robot) est remis salle `$17`, X = `$7E` |
| `$32` | le joueur est remis salle `$1B`, X = `$7E` |

`$1B` (bibliothèque) et `$17` (chambre nord) sont les deux entrées du
conduit (`$1B` → `$32`, `$17` → `$35`). `$17` ne communique qu'avec ce
conduit et le quart haut gauche de `$26`. Seul un **robot sans le joueur**
peut donc aller de `$1B` à `$17` puis appuyer sur le bouton haut gauche.

Plan (`$1B $32 $33` en haut, `$17 $35` en dessous) : de `$1B`, un couloir
horizontal traverse `$32` et `$33` ; trois tubes montent et trois
descendent dans chacune. Seul le **premier tube descendant de `$33`**
(colonnes 2-4, X 14-34) arrive en `$35` à hauteur de l'ouverture vers
`$17` ; les autres mènent en `$36`, `$34`, `$16` (labyrinthe). D'où
l'indice : une puce qui compte les tubes.

**[vérifié]** joueur en `$1B` X = `$82` → X = `$7E` ; joueur posé en `$32`
→ salle `$1B`, X = `$7E` ; Sparky seul posé en `$35` y reste.

## Énigme 2 : le champ de mines (`$0C77`)

Salles `$2C-$2F` (carré 2 × 2 : `$2E $2F` en haut, `$2C $2D` en bas). Les
**mines sont les murs** de ces salles, dessinés de la couleur du fond
(`$6E40 = $6E80 = 4`) : invisibles. Les salles « MINEFIELD MAP » `$29 $2B /
$37 $38` ont exactement les mêmes murs, visibles. Entrée depuis `$24` (bord
gauche de `$2E`), sortie par le bord droit de `$2F` vers le quart bas
gauche de `$26`.

Active tant que `$8EF0 = 0` :

1. Si `$8EF6` (joueur ou robot qui le contient) est dans `$2C-$2F` :
   **explosion immédiate** (« Additional mines keep out non-robots »).
2. Sinon, pour Sparky, Checkers, Scanner (pas le 4ᵉ robot) dans le champ
   (`$0E06`, enregistrement `$8DC9+26·r`) : si un côté est en contact avec
   un mur (octets 20-23 ≠ 0, voir plus bas), les **pare-chocs sont remis
   à 0** (octets 16-19 et couleur des objets pare-chocs = 7) ; le robot ne
   sent donc jamais les mines. Si un côté a à la fois le contact et son
   propulseur actif (octets 12-15 ≠ 0), `$8EFC = 1`.
3. `$8EFB` compte les tours consécutifs où au moins un robot pousse contre
   une mine ; remis à 0 sinon. À **8** : explosion.

Explosion (`$0CCD`) :

- joueur dans le champ : salle `$2A` en (64,96), son `$0F` (`$0CD9`) ;
- chaque robot du champ non tenu par le joueur (`$0D03`) :
  - `$0D62` : chaque objet de son intérieur est déplacé en (`$84`,`$AF`),
    `$B8ED` coupe ses fils, il revient à sa place : **tout le câblage de
    l'intérieur est perdu** ;
  - `$0DA7` : les portes (`$67-$CF`), bascules (`$25-$38`) et nœuds
    (`$D1-$DF`) libres de l'intérieur **retournent dans la boîte à outils**
    (`$1C9E`) ; les puces restent ;
  - le robot passe salle `$2A` (même X, Y), son `$0F`.

**[vérifié]** joueur posé en `$2E` → `$2A` (64,96). Sparky (câblé
WALLHUGGER) posé en `$2E` (70,56) : en moins de 200 trames il est salle
`$2A`, les 8 fils de la puce 2 (`$8CA2-$8CA9`) sont à 0, la porte 6 (`$76`)
est en `$3F` et `$8DAA` passe de `$1E` à `$1F` ; la puce `$E8` reste dans
`$09`.

Note : les octets 20-23 de l'enregistrement d'un robot sont l'**état de
contact des pare-chocs** (`$8EB6+côté` dans `$D000` : 0 rien, 1 premier tour
de contact avec son 2, `$FF` contact maintenu, remis à 0 quand le pare-chocs
refroidit, `$D140`), pas le sprite de la pince comme l'indique
[world.md](world.md) (tableau de l'enregistrement d'état) : à corriger.

## Énigme 3 : tunnel, champs de force et clé

### Champs de force (`$14EA`, dessin `$1484`)

Salles `$30` (gauche, vers `$26`) et `$31` (droite, vers le couloir `$10`).
Active tant que `$8EF0 = 0`. Chaque champ est un trait vertical de la
couleur du robot qu'il arrête (Sparky orange 5, Checkers blanc 7, Scanner
bleu 6) :

| Qui | Salle | Interdit | Repoussé à | Trait (`$1484`) |
|---|---|---|---|---|
| joueur (`$00`, avec le curseur `$FE`) | `$30` | X > `$34` | `$34` | X = `$3B`, orange |
| joueur | `$31` | X < `$51` | `$51` | X = `$50`, orange |
| Sparky (toujours), Checkers ou Scanner s'ils contiennent le joueur | `$30` | X ≥ `$30` | `$2F` | idem |
| idem | `$31` | X < `$51` | `$51` | idem |
| Checkers | `$30` | X ∈ [`$4E`,`$78`) | `$4D` ou `$78` | X = `$59` et `$77`, blancs |
| Scanner | `$31` | X ∈ [`$09`,`$33`) | `$08` ou `$33` | X = `$14` et `$32`, bleus |

Le 4ᵉ robot n'est pas concerné. Si le joueur tient Sparky, sa position est
recalée avec lui (`$9C7C`).

Le tunnel se découpe donc ainsi, d'ouest en est : **A** `$30` X ≤ `$34`
(joueur, Sparky), **B** jusqu'au champ blanc, **C** du champ blanc au champ
bleu (fin de `$30`, début de `$31`), **D** jusqu'au champ orange de `$31`,
**E** `$31` X ≥ `$51` (joueur, Sparky). Checkers vit en A-B **ou** en C-E,
Scanner en A-C **ou** en D-E. Un objet passe de E à A seulement par
**relais** : Checkers (côté est) l'amène de E en C, Scanner (côté ouest) le
prend en C et l'amène en A. Aucun des deux ne peut revenir de l'autre côté
(« Plan ahead for the return journey »).

**[vérifié]** joueur posé `$31` X = `$40` → `$51` ; `$30` X = `$45` →
`$34` ; Sparky seul posé `$31` X = `$30` → `$51`.

### Serrures (`$1350`)

Seule la **clé `$FA`** compte (salle et position, qu'elle soit tenue ou non).

| Serrure (décor) | Zone de la clé | Effet |
|---|---|---|
| entrée 7, `$30` (35,16) | X ∈ [32,41), Y ∈ [14,19) | case (colonne 2, ligne 8) de `$30` effacée : **passage vers le quart haut droit de `$26`** ; remise dès que la clé part (`$8EF3`) |
| entrée 8, `$31` (126,144) | X ∈ [123,132), Y ∈ [138,151) | porte du bas de `$31` (colonnes 15-17, lignes 1-2) ouverte d'une colonne par tour, 3 tours (`$8EF4` 0→3, octets `$75D9/$75DA`) ; se referme de même quand la clé part |

La porte du bas de `$31` mène à `$18` puis `$19` (« TUNNEL BYPASS »),
qui remonte dans `$30` par le bas, en zone A. Sans la clé dans la serrure
de `$31`, la déviation est fermée ; la zone A n'est alors accessible
qu'aux robots du tunnel.

**[vérifié]** clé posée `$30` (35,16) : `$75A1` passe de `$1F` à `$17`,
`$8EF3 = 1` ; clé posée `$31` (126,144) : `$8EF4` 1 puis 3, `$75D9/$75DA =
$0E $00` ; clé retirée : `$8EF4 = 0`, `$6E $66`, `$75A1` revient à `$1F`.

### Ce que le joueur doit faire (d'après le code)

1. Clé dans la serrure de `$31` (côté est, accessible depuis `$10`) : la
   déviation s'ouvre ; le joueur (et un robot) descend `$18`, `$19`, remonte
   en zone A de `$30`.
2. La clé reste dans la serrure de `$31` tant que le joueur passe ; elle
   doit ensuite traverser le tunnel par relais Checkers (est) → Scanner
   (ouest), jusqu'en A.
3. Clé dans la serrure de `$30` : passage ouvert, le joueur entre dans le
   quart haut droit de `$26` et appuie sur le bouton.
4. Retour : la zone A ne ressort que par la déviation, fermée si la clé
   n'est plus dans la serrure de `$31` : la clé doit refaire le relais en
   sens inverse (ou attendre l'arrêt de l'ordinateur, qui ouvre `$26`).

Le passage exact de la clé d'un robot à l'autre (pinces, capteurs de
direction `$0D-$0F`) n'est pas imposé par le code du niveau.

## Énigme 4 : salle de sécurité et haute tension

### Barrière de `$3B` (`$0E67`, `$0EDA`)

Active tant que `$8EF0 = 0` et `$8F09 = 0`. Si `$8EF6` est salle `$3B` :
Y ≤ `$68` (bloqué sous le haut de la salle), et pour Y ≥ `$60`,
X ∈ [`$15`,`$70`]. Au tour du blocage, si la salle est affichée : son `$0E`
et trait blanc horizontal Y = `$78`, X `$0E-$7D` (`$0EDA`, `$A04C`).
`$3B` ouvre en haut sur `$39` (« HIGH VOLTAGE ROOM »), qui ouvre sur le
quart bas droit de `$26` : le joueur ne peut pas y monter, un **robot seul**
oui.

**[vérifié]** joueur posé `$3B` (60,128) → Y = `$68`.

### Étincelle de `$39` (`$0EFD`)

Tant que `$8F09 = 0`, à chaque tour (même ordinateur éteint) :

- 29 fois sur 30 (`$D414` sur 30 ≠ 0) : `$05` est retirée de `$39` ;
  l'étincelle (entrée 2) fait un pas de 2 (`$0E5F/$0E63` : haut, bas,
  droite, gauche ; 1 chance sur 3 de garder la direction `$8EF2`), dans
  X ∈ [`$0E`,`$77`), Y ∈ [`$10`,`$91`) ; puis `$A6F7` cherche un objet de
  `$39` (n'importe lequel, y compris le joueur et ses accessoires, sauf
  `$9C2A`) dont un pixel couvre (X+3, Y+8) de l'étincelle. Trouvé :
  **court-circuit**, `$8F09 = 1`, étincelle orange, fin de la routine pour
  le reste de la partie.
- 1 fois sur 30 : l'objet `$05` (sprite `$32`, non saisissable) apparaît à
  la place de l'étincelle, sauf s'il touche déjà un objet. C'est la seule
  forme de l'étincelle visible des capteurs **(?)**.

`$8F09 = 1` coupe la barrière de `$3B` : le joueur peut monter en `$39`
puis dans le quart bas droit de `$26`.

**[vérifié]** joueur posé en `$39`, étincelle mise sous lui : `$8F09 = 1`,
`$9175 = 5` (capture : étincelle orange) ; joueur posé ensuite `$3B` Y =
`$80` : plus bloqué. Le chargeur de cristaux est dessiné en bas à gauche de
`$39`.

## Les quatre boutons et l'arrêt de l'ordinateur (`$0FBB`)

Tant qu'un bouton (couleur `$9176-$9179`) vaut 7 :

- si le joueur est salle `$26`, chaque bouton non appuyé dont le point
  (X+3, Y+8) est couvert par un pixel du joueur (`$A747`) passe à 5 (la
  boucle part de l'indice du premier bouton relâché : `LDA #$03` en `$0FD3`
  au lieu de `LDY`, sans effet) ;
- même test pour les six moitiés `$F0-$F5` (Sparky, Checkers, Scanner, pas
  le 4ᵉ robot ni un objet).

Un bouton reste appuyé. Quand les quatre le sont (`$1083`, un pas par
tour, `$8EF5`) :

1. boutons retirés (salle `$3F`), 8 octets de murs de `$26` remplacés
   (`$0FA3` → indices 4, 5, 12, 13, 16, 17, 24, 25 ; valeurs `$0FAB`), son
   `$11` ;
2. au tour suivant, `$8EF0 = 1` (**ordinateur éteint**), seconds murs
   (`$0FB3`) : les quatre quarts et le centre de `$26` communiquent, **le
   4ᵉ robot est libre** ; son `$11`.

Ordinateur éteint : conduits ouverts, mines, champs de force et barrière
de `$3B` inactifs, champs plus dessinés, porte de l'ascenseur ouverte. Le
Sweeper et l'étincelle continuent.

**[vérifié]** joueur posé sur les boutons (30,128), (50,31), (84,139),
(103,48) : les couleurs passent à 5 une par une ; 60 trames après le
quatrième, `$8EF0 = 1`, `$8EF5 = 2`, murs `$7478-$7479 = $33 $33`… ;
capture : `$26` ouverte, 4ᵉ robot au centre.

## Le Sweeper 'Bot (`$10C8`)

Objet `$22` (sprite basculé `$2D` ↔ `$2E` à chaque tour), qui se déplace
d'une unité par axe et par tour avec `$9DB3`, **sans tenir compte des
murs**. `$8EF1` : 0 à vide, 1 chargé, `$FF` vient de vider.

Hors de `$3C` : il cherche dans sa salle le premier objet libre
(non attaché, saisissable `$6900 = 0`) qui n'est ni lui, ni la boîte à
outils `$E1`, ni l'objet tenu, ni `$8EF6`. Il s'en approche ; au contact
(`$A835`), l'objet part **salle `$00`** (sac invisible), `$8EF1 = 1`, son
`$0D`. Les **robots inoccupés sont des proies** (moitié gauche
saisissable) ; celui qui contient le joueur est épargné.

Sans proie, il fait le tour des couloirs (`$1166`) : vers la droite en
`$03-$0C` (`$03` : monter à Y `$58` d'abord ; `$0C` : jusqu'à X `$42`
puis descendre), vers le bas en `$0E-$13`, vers la gauche en `$14-$21`
(`$21` : X `$42` puis monter), vers le haut à partir de `$22`. En `$15`
chargé : centre (X `$42`) puis montée dans `$3C` (« TRASH DUMP ») ; en
`$3C` à Y ≥ `$58` : tous les objets libres de la salle `$00` sont posés en
`$3C` (même X, Y), `$8EF1 = $FF`, son `$0C`, puis redescente en `$15` et
départ à gauche (`$8EF1 = 0`). Dans `$3C` il ne ramasse rien.

**[vérifié]** sentinelle posée `$14` (40,88) et disquette `$07` en (60,88) :
`$6307 = $00`, `$8EF1 = 1` ; 1 500 trames plus tard `$6307 = $3C`,
`$8EF1 = $FF`. Sparky posé à côté, télécommande coupée : salle `$00`.
Télécommande allumée, Sparky s'éloigne plus vite (2 unités par tour) et
n'est pas pris.

Il faut donc garder les robots hors des couloirs ou en mouvement, et
récupérer en `$3C` ce qu'il a emporté ; les puces 7-8 y sont déjà (`$ED`).

## L'ascenseur et la sortie (`$12B0`, `$172A`)

Salle `$02` (accès par le hall `$3A`, lui-même depuis `$22`). Une cloison
colonne 11 sépare l'entrée de la cabine ; le **repère de sortie** (joueur
fantôme orange et cadre, `$17D4`) est dans la cabine en (123,155), le
bouton **HOLD** en bas à droite (texte `$1E`, flèche entrées 17-18).

Porte (`$12B0`, cases de la colonne 11, lignes 0-11, `$B3AA`) :

| Situation | Porte |
|---|---|
| `$8EF0 = 1` (ordinateur éteint) | grande ouverte (lignes 1-10) |
| objet `$03` dans la salle `$02` | grande ouverte, flèche HOLD enfoncée (X `$7B` au lieu de `$7E`) |
| `$8EF6` dans `$02`, colonne de X (`$9B05[X]/2`) ≤ 3 | ouverte, lignes 1-10 |
| colonnes 4, 5, 6, 7 | lignes 2-9, 3-8, 4-7, 5-6 |
| colonne ≥ 8 | **fermée** ; « Hold, please! » (texte 5) remplacé par « Going up! » (texte `$21`) |
| `$8EF6` hors de `$02` | inchangée |

Le joueur qui s'approche (seul ou dans un robot) referme donc la porte
avant d'arriver : il faut éteindre l'ordinateur (ou faire tenir la porte
par l'aimant `$03` apporté depuis le niveau 1 **[vérifié]**).

Sortie (`$172A`) : salle affichée `$02`, joueur exactement en
X = `$7B`, Y = `$9B`, sprite 0 (pas le fer à souder) → couleur 4, notes
montantes, son 9, `JMP $0AFF`.

**[vérifié]** joueur posé `$02` X `$10` : colonne 11 ouverte, « Hold,
please! » ; X `$2E` : lignes 2-9 ; X `$3A` : fermée, « Going up! »
(capture). Joueur posé en (123,155) : animation puis sortie 4 → 5.

## Sortie 4 → 5 (`$0AFF-$0BD3`)

1. `$1DEA` (texte de la boîte à outils caché) ; l'objet tenu est mis en
   (0,0), ses fils suivent (`$B8E6`).
2. Tri `$FE…$01` : tout objet ni en `$3F`, ni tenu, ni attaché, ni dans
   un intérieur de robot (`$8204`) part en `$3F`.
3. Joueur couleur 7, X = `$0E`, Y = `$20` ; sa salle reste `$02` : le
   niveau 5 commence salle `$02` en (14,32).
4. Objet `$08` (sprite `$3F`, couleur 5, préparé par la sortie 3 → 4) :
   saisissable, salle `$37`, (63,160).
5. Chargeur de cristaux : salle `$15`, (119,20) (`$8454-$8456`).
6. Sprites pour le niveau 5 (le niveau 5 ne charge pas `$6A00`) :

   | Source | Destination | Sprites | Dessin |
   |---|---|---|---|
   | `$1808-$1827` | `$6A30` | 3, 4 | bloc percé d'un losange ; fiche (prise) |
   | `$1828-$1857` | `$6CC0` | `$2C`, `$2D`, `$2E` | haut-parleur (?) ; panneau ; personnage |
   | `$1858-$1867` | `$6BF0` | `$1F` | personnage (variante de `$2E`) |

   Leur usage relève du niveau 5 **(?)**.
7. `$0A3D` avec X = 2 : écran `$3E` « Be sure the Robot Odyssey disk is
   in the disk drive. Then press ESC », attente d'**ESC**, puis `$0AB9` :
   `$02D0 = 2`, `$02D1 = 4`, `$02D2 = 3`, saut RESET.

**[vérifié]** après la sortie : joueur `$02` (14,32), `$08` salle `$37`
(63,160) saisissable, `$8454-$8456 = $15 $77 $14`, `$6A30` = les octets de
`$1808` ; après ESC `$02D0-$02D2 = 02 04 03` ; après RETURN, première salle
du niveau 5 (capture).

## Robots apportés

Le tri de sortie (même code aux niveaux 1, 3 et 4) envoie en `$3F` les
moitiés gauches des robots, qui ne sont pas attachées : **un robot ne
passe au niveau suivant que s'il est tenu** par le joueur. Ce qui est dans
un intérieur de robot (`$09 $0A $0B $0D`) est gardé. **[vérifié]**
`go:0AE6` (sortie du niveau 1) sans rien tenir : au niveau 2, `$F0-$F5` en
`$3F` ; même constat au début du niveau 4 après les trois sorties (en
accord avec [world.md](world.md#passage-au-niveau-suivant)).

Le niveau 4 suppose pourtant plusieurs robots : Checkers et Scanner pour
le relais du tunnel, un robot seul pour le conduit, les mines,
l'étincelle. Seule voie trouvée dans le code : **emboîter** les robots
(porter un robot dans l'intérieur d'un autre, puis tenir ce dernier en
sortant). `$1670` prévoit explicitement un joueur dans un robot lui-même
dans un robot. Non vérifié en jeu **(?)**.

La clé `$FA` n'existe au niveau 4 que si elle a voyagé depuis le niveau 1
(dans un intérieur de robot, comme au départ, ou tenue). Aucune sortie ne
la replace.

## Solution imposée par le code

Ordre libre pour les étapes 2-5.

1. Arriver au niveau 4 avec Checkers, Scanner, au moins un autre robot
   et la clé `$FA` (voir ci-dessus). Optionnel : lire les disquettes au
   lecteur de `$1D`, utiliser la caméra `$FB` pour suivre les robots.
   Récupérer les puces 7-8 (`$ED` en `$3C`, `$EE` en `$3A`) pour les
   programmer (compteur pour le conduit). Tenir les robots à l'écart du
   Sweeper.
2. **Bas droit** : envoyer un robot seul de `$1E` dans `$3B` puis `$39` ;
   qu'il touche l'étincelle (ou monte jusqu'au bouton par la colonne 18) ;
   ensuite le joueur peut monter à son tour et appuyer.
3. **Bas gauche** : faire traverser le champ de mines (`$24` → `$2E` →
   `$2F` → `$26`) par un robot seul, sans pousser plus de 7 tours contre
   un mur, guidé par la carte `$29 $2B $37 $38` et la radio des antennes ;
   il touche le bouton.
4. **Haut gauche** : un robot seul part de `$1B` vers la droite, prend le
   premier tube descendant de `$33`, sort en `$17` et touche le bouton.
5. **Haut droit** : clé dans la serrure de `$31`, passage du joueur par
   `$18`/`$19` en zone A, relais de la clé Checkers → Scanner à travers le
   tunnel, clé dans la serrure de `$30`, bouton ; prévoir le retour.
6. Les quatre boutons appuyés : ordinateur éteint, 4ᵉ robot libre
   (batterie à charger ; chargeur en `$39`).
7. Aller en `$02` par `$22` et `$3A`, entrer dans la cabine, se poser sur
   le repère (123,155) sous sa forme normale, en **tenant** le robot à
   emporter (les autres dedans).

## Variables du niveau (`$8EF0-$8F0F`, `$9100-$9208`, `$16A9`)

| Adresse | Rôle |
|---|---|
| `$8EF0` | ordinateur éteint |
| `$8EF1` | Sweeper : 0 vide, 1 chargé, `$FF` vient de vider |
| `$8EF2` | étincelle : dernière direction |
| `$8EF3` | serrure `$30` : passage ouvert |
| `$8EF4` | serrure `$31` : ouverture de la porte, 0-3 |
| `$8EF5` | arrêt de l'ordinateur : étape 0-2 |
| `$8EF6` | joueur ou robot qui le contient |
| `$8EF7`, `$8EF8`, `$8EFA`, `$8EFD-$8F01` | temporaires |
| `$8EF9` | barrière de `$3B` touchée ce tour (éclair) |
| `$8EFB`, `$8EFC` | mines : tours consécutifs, poussée ce tour |
| `$8F03`, `$8F04`, `$8F05` | caméra : active, salle vue, couleur du nom |
| `$8F09` | étincelle court-circuitée |
| `$8F0A`, `$8F0B` | porte de l'ascenseur : bornes de l'ouverture |
| `$8F0C`, `$8F0D` | animation de sortie |
| `$8F0E` | indice de dessin du décor |
| `$8F0F-$910E` | sprites locaux du décor |
| `$910F/$9128/$9141/$915A/$9173` | décor : sprite, X, Y, salle, couleur (25 entrées) |
| `$91CF` | salle → texte du nom |
| `$16A9-$16B3` | caméra : orientation, compte à rebours, clignotement, sprites |
| `$0C6A-$0C76` | ventilateur de `$33` : phase, sprites |
| `$1296`, `$12AA` | porte de l'ascenseur : colonne → état → borne haute |
| `$0FA3`, `$0FAB`, `$0FB3` | murs de `$26` : indices, étape 1, étape 2 |
| `$0E5F`, `$0E63` | étincelle : pas X, pas Y par direction |

## Méthode a2shot

Arriver au niveau 4 **[vérifié]** avec les objets placés par la vraie
sortie du niveau 3, en enchaînant les trois sorties :

```sh
A=../dev/tools/a2shot/a2shot
$A --disk original/A_ROBOTROPOLIS.woz wait:2500 key:$'\r' wait:900 key:$'\r' wait:6500 \
   go:0AE6 wait:300 key:$'\e' wait:3000 key:$'\r' wait:200 \
   go:0AEC wait:300 key:$'\e' wait:3000 key:$'\r' wait:200 \
   go:9325 wait:300 key:$'\e' wait:3000 key:$'\r' wait:200 ...
```

Chaque sortie attend ESC, puis le niveau affiche ses indices (RETURN).
Différences avec une vraie partie : joueur salle `$28` (celle du départ du
niveau 1) au lieu de `$2A` ; robots en `$3F` (non tenus) ; clé `$FA` dans
l'intérieur de Checkers. Raccourci `regs:00:00:03 go:0AA0` depuis le
niveau 1 : niveau 4 chargé mais objets du niveau 1 (et la sentinelle
`$22` reste attachée à elle-même, `$6622 = $22`, ce qui la bloque : la
sortie 1 → 2 la détache). Poser `$02D0 = 2`, `$02D1 = 3`, `$02CF = $A7`
puis `reset` ne marche pas : le jeu continue au niveau 1.

Déplacer un objet, au début de la boucle (sinon `$A90C` remet l'ancienne
salle) :
`until:0853:60 poke:9C2F:OBJ poke:9C2E:SALLE call:9E07:2 poke:64OBJ:X poke:65OBJ:Y`.
Un tour dure ≈ 9 trames dans ces salles.

## Non compris ou non vérifié

- **Objet `$03` et HOLD : résolu [vérifié]**. `$03` est l'aimant, posé au
  niveau 1 (salle `$22` ou `$23`) ; aucun niveau ne le replace, il passe
  donc s'il est tenu ou laissé dans un intérieur de robot. Tenu du niveau 2
  au niveau 4 puis apporté dans `$02` : « Hold, please! », flèche HOLD
  enfoncée, porte ouverte même joueur en X `$3A` (sans lui : « Going
  up! », fermée). Autre solution que d'éteindre l'ordinateur.
- **Objet `$05`** : visible un tour sur trente à la place de l'étincelle ;
  sert-il à un capteur (sprite `$32`, aucun capteur fourni avec ce
  sprite) ?
- `$A6F7` exclut l'objet `$9C2A`, dont la valeur à ce moment n'est pas
  maîtrisée.
- Arrivée des robots : par **emboîtement [vérifié au clavier]** (voir
  [world.md](world.md), passage au niveau suivant).
- Non vérifiés en jeu : traversée d'un robot par le conduit et le choix
  du tube, relais de la clé dans le tunnel, traversée du champ de mines,
  explosion par une poussée de 8 tours mesurée au tour près, invisibilité
  des mines à l'écran, robot qui court-circuite l'étincelle (seul le
  joueur posé l'a fait), passage d'un robot dans le trou de la serrure
  de `$30`.
- Le Sweeper traverse les murs ; ce qui arrive aux objets de la salle
  `$00` si on sauvegarde pendant qu'il les porte n'a pas été regardé.
- Rôle des sprites copiés pour le niveau 5 et de l'objet `$08`.
