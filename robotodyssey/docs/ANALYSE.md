# Robot Odyssey : analyse de l'original

*Robot Odyssey I*, version 2.0, The Learning Company, 1984, par Mike Wallace
et Leslie Grimm. Jeu éducatif de logique : tombé dans la ville souterraine de
Robotropolis, le joueur doit remonter ses cinq niveaux en programmant trois
robots (Scanner, Checkers, Sparky) avec des portes logiques câblées à la main,
puis avec des puces qu'il conçoit lui-même.

Ce document décrit ce qu'on a établi sur les disques originaux. Les analyses
détaillées par sous-système sont dans [logic/](logic/).

## Sources

| Fichier (dans `original/`, hors git) | Origine | Contenu |
|---|---|---|
| `A_ROBOTROPOLIS.woz` | woz-a-day (4am), disque 1 face A | « Robotropolis » : le jeu, amorçable |
| `B_LABS.woz` | idem, disque 1 face B | « Robotropolis Preview, Chip Designs, Innovation Lab and Chip Library » |
| `C_TUTORIAL.woz` | idem, disque 2 face A | « Robot Anatomy, Robot Wiring, Sensors, the Toolkit, Robot Circuits and Robot Teamwork » |

Copiés depuis `~/Emu/AppleII/Robot Odyssey I v2.0 (woz-a-day collection)/`.
Métadonnées WOZ : 64 Ko requis, II+ / //e / //c / IIgs, Applesauce 1.88.5.
`tools/extract.py` les décode dans `build/` (`.dsk` ordre DOS, `.po` ordre
des blocs, segments dans `build/files/<face>/BBB_AAAA.bin`).

## Disques

### Format physique

35 pistes standard 16 secteurs, prologues `D5 AA 96` / `D5 AA AD`, codage
6&2, volume 254 : `dev/tools/re6502/flux2dsk.py` (repris de Wilderness) décode les
560 secteurs de chaque face.

**Protection discrète** : à chaque affichage du menu, `$6205` cherche entre
les secteurs de la piste 7 une signature de nibbles (`D5`, `E7 E7 E7`, une
lecture de `$C08D` en plein flux, `EE`, `E7 FC EE E7 FC EE EE FC`) et met le
résultat dans le bit 7 de `$02CE` (puis `$9C4E`). Mesuré : `$80` avec le
`.woz`, `$00` avec le `.dsk` reconstruit, qui perd ces nibbles. Le `.dsk`
démarre pourtant et va jusqu'à la première salle : la sanction éventuelle
d'un échec n'est pas identifiée. Détails dans
[logic/loader.md](logic/loader.md).

### Pas de système de fichiers

Ni catalogue DOS 3.3 ni répertoire ProDOS. Le jeu lit des **blocs de
512 octets en ordre ProDOS** (bloc *b* = piste *b*/8, deux secteurs) avec sa
propre RWTS, à des numéros de bloc codés en dur.

- Bloc 0 (piste 0) : secteur d'amorçage. Son octet 2 identifie la face
  (`00` A, `01` B, `02` C) ; le reste est identique.
- Blocs 1-7 : RWTS et amorce (communs aux trois faces sauf le bloc 4).
- Blocs `$030-$038` : **module résident** chargé en `$4000-$51FF` (menu,
  chargeur, sauvegardes), identique sur les trois faces.
- Le reste dépend de la face (voir [logic/loader.md](logic/loader.md)).

### Amorçage

1. La PROM Disk II charge le secteur physique 0 en `$0800`.
2. `$0801` lit les secteurs physiques 1 à 15 de la piste 0 en `$5100-$5FFF`
   (RWTS + amorce), puis :
   - vérifie la carte langage (`$E000` écrit/relu, sinon message et arrêt) :
     **64 Ko obligatoires** ;
   - efface HGR1, affiche HGR plein écran ;
   - copie `$5A00` → `$0300` et `$5B00-$5EFF` → page texte `$0400-$07FF`
     (en sautant les trous d'écran) ;
   - vecteur RESET `$03F2` → `$xx00` de la ROM du contrôleur.
3. `$5FBB` lit les blocs `$030-$038` en `$4000-$51FF` et saute en `$4000`
   (`$5F00` est un sondage des emplacements, emprunté si `$02CF/$02D0` ne
   portent pas la signature de démarrage à chaud).

### RWTS et chargeur

- `$52C8` : lecture/écriture d'un bloc. Paramètres en page zéro
  `$42` commande (1 lecture, 2 écriture), `$43` emplacement×16,
  `$44/$45` tampon, `$46/$47` numéro de bloc.
- `$4B03` : chargeur de haut niveau, paramètres en ligne après le `JSR` :
  nombre de segments, commande (bits 0-1 : 1 lecture, 2 écriture,
  3 formatage ; bit 6 vu sur `$4DD8`), puis un pointeur par segment vers un
  **descripteur de 6 octets** : bloc (LE16), adresse (LE16), longueur
  (LE16). Une longueur non multiple de 512 passe par le tampon `$5E00` pour
  le dernier bloc.
- Table des descripteurs : `$4FE5-$51AF` du module résident. Les
  descripteurs de bloc 0 sont remplis à l'exécution (sauvegardes).
- `tools/loadcalls.py IMAGE` liste les 43 appels et leurs segments.

## Un « système » rechargé à chaque service

Le module résident et la RWTS occupent `$4000-$5FFF`, c'est-à-dire la page
HGR 2 : le jeu les écrase. Pour tout service (menu, niveau suivant,
sauvegarde, puce), le code en cours écrit une requête dans `$02D0`, un
argument dans `$02D1`, le mode dans `$02D2`, signe avec
`$02CF = $02D0 EOR $A5` et saute par le vecteur RESET : l'amorce recharge le
module, qui exécute la requête (`$403E` incrémente `$02CF` pour qu'elle ne
serve qu'une fois). Une somme sur `$9500-$9BFF` (doit valoir `$F5`) dit si
le moteur est encore en mémoire.

| `$02D0` | Requête |
|---|---|
| 0 / 1 | démarrage à froid avec titre / retour au menu |
| 2 | niveau suivant, `$02D1` = 1-5 (5 = fin) |
| 4 / 5 / 6 | sauvegarder la partie / charger une puce / sauvegarder une puce |

| `$02D2` | Mode | Face |
|---|---|---|
| 0-4 | Robotropolis niveaux 1-5 | A |
| 5 | Innovation Lab | B |
| 6 | Robotropolis Preview | B |
| 7-12 | leçons Anatomy, Wiring, Sensors, Toolkit, Circuits, Teamwork | C |
| 13 | Chip Design | B |

Une nouvelle partie (`$02D2` = 0) passe d'abord par l'intro (`$456D`),
puis l'entrée 4 de la table `$45BD/$45C7` charge le niveau 1. Les numéros de
bloc se recouvrent d'une face à l'autre (`$008` = intro sur A, catalogue de
la bibliothèque sur B, base des leçons sur C) : la carte complète
bloc → face → rôle et la mémoire de chaque mode sont dans
[logic/loader.md](logic/loader.md) ; `tools/extract.py` découpe chaque
segment depuis sa vraie face, nommé par son rôle
(`build/files/<face>/BBB_AAAA_rôle.bin`), et `tools/memimg.py` reconstruit
l'image mémoire d'un mode sans émulateur.

## Mémoire pendant une partie

| Zone | Bloc (face A) | Contenu |
|---|---|---|
| `$0300-$07FF` | amorce | pilote de texte HGR `$0300` et sa police (page texte) |
| `$0803-$1907` | `$0A1` | code du niveau 1 (boucle principale `$085B`, énigmes) |
| `$0B00-$1FFF` | – | circuit des puces, sauvegardé avec la partie |
| `$2000-$5FFF` | – | HGR pages 1 et 2, affichées en alternance |
| `$6000-$94FF` | `$090` + … | **le monde** (`$3500` octets, ce que la sauvegarde écrit) |
| `$9500-$B8D6` | `$05B` | moteur commun aux trois faces (police des salles en tête) |
| `$B8E0-$BF98` | `$07C` | moteur, suite |
| `$D000-$EFFF` banque 1 | `$071`, `$06D` | les 8 petites puces (1 Ko chacune) |
| `$D000-$DFFF` banque 2, `$F000-$FFF3` | `$080`, `$088` | robots, capteurs, fils, portes, puces |

Les niveaux 2 à 5 ne rechargent que `$6E40-$81FF` (salles et textes), leur
code `$0803` et leurs données `$8EF0` : objets, robots et circuits sont
chargés une fois au niveau 1 et persistent toute la partie.

## Le monde ([logic/world.md](logic/world.md))

La disposition est **exactement celle de la version PC** (`roData.h` de
Micah Dowty), à l'adresse de base près.

- **256 objets**, un tableau de 256 octets par champ : `$6000` suivant dans
  la salle, `$6100` sprite, `$6200` couleur, `$6300` salle (`$3F` = nulle
  part), `$6400` X, `$6500` Y, `$6600` attaché à, `$6700/$6800` décalage,
  `$6900` saisissable.
- **64 sprites** de 16 octets en `$6A00`.
- **64 salles** : tête de liste d'objets `$6E00`, couleurs `$6E40/$6E80`,
  liens haut/bas/droite/gauche `$6EC0/$6F00/$6F40/$6F80`, murs en `$7000`
  (30 octets par salle : grille 20 × 12 de cases 14 × 16 pixels).
- **128 textes** en `$7880-$7C7F` (salle, X, Y, type, couleur, pointeur),
  chaînes jusqu'à `$81FF`.
- **Circuit** en `$8618` : un fil par objet au plus, bascules en `$8AF3`,
  type de porte en `$8CB3` (1 AND, 2 OR, 3 XOR, 4 NOT), outil courant
  `$8DA6`, télécommande `$8DA7`, compteurs de la boîte à outils `$8DA8`.
- **Robots** : tables fixes en `$8200` (objets `F0 F2 F4 01`, salles
  intérieures `09 0A 0B 0D`, broches), état 4 × 26 octets en `$8DC9`.
- X va de 0 à 133 (pas de 2 pixels), Y de 0 à 176 vers le haut.

`tools/world.py` vide une partie (RAM ou segments) et dessine chaque salle et
la carte du niveau en PNG.

## La simulation ([logic/simulation.md](logic/simulation.md))

- **Le signal est une couleur** : couleur 5 (orange) = 1, toute autre = 0.
- Un passage de la boucle principale = un tic, 4 à 5 par seconde. Ordre :
  joueur, objets attachés, entrée/sortie de robot, cristaux, robots ; puis,
  télécommande allumée seulement, capteurs, pinces et antennes, batteries,
  fils, portes et bascules, puces ; affichage en dernier.
- Fils propagés en une passe par numéro d'objet croissant ; une porte met un
  tic à répondre ; bascules RS.
- Robots : test de mur devant chaque pare-chocs (le mur l'allume et
  bloque), propulseurs (0,−4), (−2,0), (0,+4), (+2,0) ; pas de collision
  entre robots ; batterie 30 par tic + 60 par propulseur actif ; capteurs
  par sprite ; antennes = radio partagée.
- Joueur : une case par touche (7 unités en X, 16 en Y), Ctrl = 1 unité ;
  toucher un robot fait entrer dedans, le coin haut droit de l'intérieur
  montre l'extérieur.

Vérifié dans a2shot : télécommande, changement de type de porte par `poke`,
pas du joueur, cadence.

## Niveaux

Sortie identique partout : condition propre au niveau (niveau 1 : joueur en
(32,32) dans la salle `$2A`), fanfare de 9 notes, objets non tenus envoyés
en `$3F`, placement des objets du niveau suivant, puis requête `$02D0 = 2`.
Le niveau 1 tire au hasard la place de la clé et du cristal, fait tourner
l'Ampire Bot qui vide les batteries et ouvre des portes par plaques au sol ;
les trois robots partent précâblés (Sparky avec la puce WALLHUGGER).

**Seul l'objet tenu passe au niveau suivant** : un robot non tenu est
perdu. Pour en emporter plusieurs, on les emboîte (un robot posé dans
l'intérieur du robot tenu). La clé `$FA` du niveau 1 sert jusqu'au niveau 5.
Feuille de route pour le joueur : [SOLUTION.md](SOLUTION.md).

| Niv. | Énigmes | Sortie |
|---|---|---|
| 2 métro ([niveau2](logic/niveau2.md)) | clé sur une plaque → jeton → tourniquet ; poignée + bouton tenu par un robot → train ; 3 gardes ; salle secrète `$03` | ticket sur la fente de `$02`, joueur en (123,154) |
| 3 ville ([niveau3](logic/niveau3.md)) | orage et bouclier, éditeur de capteur, jeton fuyant, ferraille → ascenseur, distributeur du Form-12, gardes et deux boutons, laser coupé par un robot seul, sentinelle | joueur en (35,80) salle `$2A` |
| 4 centre de calcul ([niveau4](logic/niveau4.md)) | 4 boutons, un par quart de `$26`, pour éteindre l'ordinateur : conduits (robot seul), champ de mines invisible (robot qui explose après 8 tours contre un mur), champs de force colorés et deux serrures (clé passée de robot en robot), étincelle ; disquettes, caméra, Sweeper 'Bot | ascenseur, joueur en (123,155) salle `$02` |
| 5 voies aériennes ([niveau5](logic/niveau5.md)) | 7 portes à dalles, trafic, Disk-O-Tek, serrure sonore (motif radio 100110100110), boutons 1-3-2-4, minuterie de 189 tours, grille qui vide les batteries, transporteur à 8 boutons | joueur en (70,20) salle `$2A` → « CONGRATULATIONS! », puis boucle infinie |

L'aimant `$03` du niveau 1, porté jusqu'au niveau 4, tient ouverte la
porte de l'ascenseur (HOLD). Défaut de l'original : l'animation de
dispersion du transporteur final n'est jamais jouée (`$8E7E` non
initialisé).

Raccourci a2shot pour arriver à un niveau : enchaîner les vraies sorties
(`until:085B go:0AE6`, ESC ; `go:0AEC`, ESC ; `go:9325`, ESC…). Charger un
niveau par `regs:00:00:N go:0AA0` saute la sortie 1 → 2, qui détache la
sentinelle `$22` (elle dérive alors de −1 par tour). Poser `$02D0/$02D1`
puis RESET ne marche pas.

## Graphismes et textes ([logic/graphics.md](logic/graphics.md))

- Chaque image redessine toute la salle dans la page cachée, puis bascule
  (`$AEED`) ; écran de jeu 280 × 192 entier, sans zone d'état.
- Fond : grille de murs + 21 motifs de couleur (`$9B91…`) ; sprites 7 × 16
  bits, chaque bit = 2 pixels, masque + OU (`$AF1F`), sept routines de
  décalage ; fils tracés en L.
- Police des salles en `$9500` (96 caractères), grand texte = mêmes
  caractères doublés ; le texte prend la couleur du fond (bit 7).
- Menu, intro et fin : interpréteur de scènes `$0803` (11 opcodes), images en
  tuiles 7 × 8 compressées ; le grand lettrage du menu est une image, pas une
  police.

`tools/re_graphics.py` exporte 79 PNG (polices, sprites et cartes des
14 mondes, menu, intro, fin) dans `build/original_graphics/` et les
930 textes de salle dans `build/texts/` ; `--verify RAM.bin` redessine la
salle d'un vidage : 0 octet d'écart sur la salle 40, sur les 8 images de
l'intro, et sur le menu hors cadre de sélection.

## Leçons, Innovation Lab, Preview ([logic/lessons.md](logic/lessons.md))

- **Pas d'interpréteur de leçon** : chaque leçon est un monde au format de
  Robotropolis, l'enseignement est spatial (textes, flèches, mécaniques
  normales) ; quelques routines liées à une salle (illustrations des
  capteurs, éditeur de capteur, porte et bouton PANIC). La dernière salle dit
  « Press ESC » : aucune réussite n'est testée.
- **Innovation Lab** : bac à sable sans but (3 robots, puce prototype,
  8 puces, boîte à outils complète, éditeur de formes, labyrinthe peint).
- **Preview** : démo qui rejoue un flux d'entrées enregistré (`$902F`,
  866 octets) et un script de bandeaux (`$8880`, interprète `$E470` à
  24 opcodes).

`tools/lessons.py` liste salles, sorties et textes d'une leçon.

## Puces ([logic/chips.md](logic/chips.md))

- 8 emplacements en banque 1, `$D000 + $400·n` ; directions des broches en
  `$F008 + 8n` (0 aucune, 1 entrée, 2 sortie) ; ordre interne des broches
  1, 2, 3, 4, 8, 7, 6, 5.
- Code compilé : valeurs des broches, puis portes `01-04`, bascule `05`,
  puce imbriquée `06` (copiée en ligne), section `07` de copies terminée par
  `FF` ; chaque porte ajoute exactement un tic de retard.
- Gravure : code dans le monde du labo (`$8990-$94FF`, entrée `$9345`),
  limite `$3DF` octets.
- Bibliothèque de la face B : 10 puces (Clock, 4 Bit Counter, Bus, Delay
  Line, Full Adder, One Shot, RS Flip-Flop, Count to N, Wall Hugger, Stereo
  Recorder). Une nouvelle partie précharge Count to N et Wall Hugger.

`tools/chips.py` décode la bibliothèque en netlist et simule une puce tic
par tic.

## Sauvegardes

Rien n'est écrit sur les disques du jeu : tout va sur un disque STORAGE que
le jeu formate lui-même (signature `$11/$B4`), 4 parties et 13 puces sur
Disk II, 26 emplacements sur 3,5" ou disque dur via SmartPort. Partie =
55 blocs (puces en banque 1, monde `$6000-$94FF`, circuit `$0B00-$1FFF`,
en-tête) ; puce = 1 Ko de code + en-tête (broches, longueur, fiche de
299 octets). Détails dans [logic/loader.md](logic/loader.md).

## Version PC

Portage MS-DOS du jeu Apple II (TLC, vers 1985, CGA 4 couleurs), dernière
version 1.1 ; il existe aussi une version Color Computer. La version
Apple II 2.0 étudiée ici est proche mais pas identique.

### Confirmé par nos octets Apple II

- Les structures du monde ont la même disposition champ pour champ que celles
  du PC (`roData.h`, structure `ROCircuit`…), à l'adresse de base près :
  objets, sprites, salles, textes, circuit, robots
  ([logic/world.md](logic/world.md)). Les numéros de sprites et d'objets
  fixés par le moteur sont les mêmes. Seul écart vu : le tas de textes
  s'arrête en `$81FF` sur Apple II, la zone correspondante va jusqu'à
  `$94FF` sur PC. Sur Apple II, `$8200-$94FF` contient les tables du
  moteur, le circuit, l'état des robots et les données du niveau : le monde
  sauvegardé inclut donc le circuit, qui est un bloc à part sur PC.
- Le bloc `unknown[0x100]` du PC tombe en `$7780-$787F`, juste après les
  murs des 64 salles.
- Les 5 octets de fin de la sauvegarde PC (deux objets, un décalage X/Y,
  le monde) sont ceux de l'en-tête Apple II : `$9C27` objet touché, `$9C26`
  racine de sa chaîne de porteurs (ce qui bouge), `$A5C9/$A5CA` décalage
  de la prise par rapport au joueur (`$A611`), `$02D2` niveau (0-4, 5 labo ;
  le PC met 30 pour le labo).
- Triche : au PC, un octet de `joyfile.dat` autorise Ctrl-E (collisions
  coupées) ; sur Apple II, la séquence Ctrl-A, Ctrl-L, `T` du menu
  (`$61C4-$61DD`) écrit `$85` (Ctrl-E) en `$03FF`, et Ctrl-E inverse `$9C30`,
  lu seulement par le pas du joueur (`$A925`, `$AA07`) : robots et
  sentinelles gardent leurs murs.
- Robots : cycle d'animation des propulseurs 0, 1→2→3→1, batterie 0-15,
  accumulateurs 16 bits (poids fort d'abord) après l'octet `$FF` de fin
  des robots, comme au PC.
- Noms : l'objet `$03` est l'aimant, comme au PC (attraction vérifiée au
  niveau 2) ; son sprite `$37` porte le nom « bouton » dans l'énumération
  PC.
- Robotropolis Preview n'existe que sur Apple II (face B, démo rejouée,
  [logic/lessons.md](logic/lessons.md)).

### `SPECIFICATION.md` (trouvée sur le net)

Spécification de moteur en français, apportée par l'utilisateur. Elle
reprend presque mot pour mot nos documents (mêmes seuils, adresses Apple II
converties en décimal, même ordre du tour) et y ajoute le modèle PC
(identifiants de mondes, `joyfile`, format `.GSV`). Confrontée aux octets :

- **Faux pour l'Apple II** : « `0xE4` sortie de pince de Scanner, et aussi
  celle de Checkers ». La table `$82E3` vaut `D0 EF E4 0A` : Checkers a sa
  sortie en `$EF`. L'erreur vient d'un doublon de l'énumération PC.
- **Faux aussi** : « objets, robots, circuits et puces persistent d'un
  monde à l'autre ». Le tri de sortie (`$0AFB`) envoie en `$3F` tout robot
  que le joueur ne tient pas.
- **Propre au PC** : identifiants de mondes (0-4, 21-27, 30, 40 ; l'Apple II
  utilise `$02D2` = 0-4, 5 labo), sauvegarde brute de 24 389 octets (Apple
  II : blocs + en-tête, voir [logic/loader.md](logic/loader.md)), fichier
  de réglages de 16 octets, 28 effets sonores (12 sur Apple II).
- **Confirmé** : décalage des sprites de pince entre aventure et
  labo/leçons, cinq octets de fin de sauvegarde, passe-muraille,
  limite de gravure `$3DE`, puce vide de 11 octets, toutes les règles de
  simulation (déjà dans [logic/simulation.md](logic/simulation.md)).
- **Absent de la spécification** : tenir un objet coûte 30 par tour à la
  batterie du robot et une batterie vide le fait lâcher (`$DB64`, `$DB26`).
- **Non vérifié ici** : « un sprite qui dépasserait l'écran n'est pas
  dessiné » ; « carte plus lente » au centre de calcul (rien de tel trouvé
  au niveau 4). Le choc qui fait clignoter le joueur aux passerelles existe
  (niveau 5, 99 tours, `$8F55`), sa couleur `$87` n'est pas vérifiée.

### Connu seulement par des sources PC (non vérifié ici)

- Micah Dowty (blog [scanlime.org](https://scanlime.org/tag/robot-odyssey/))
  a traduit le code 8086 en C avec un traducteur binaire statique (sbt86),
  pour un portage Nintendo DS puis un portage WebAssembly. En 2018, il a
  publié une partie complète jouée de bout en bout pour le tester.
- Le portage navigateur s'appelle *Robot Odyssey Rewired*. Il part des
  fichiers DOS 1.1, qui ne sont pas fournis, et propose des palettes
  imitant l'Apple II ou le CGA. Le dépôt d'origine `scanlime/robot-odyssey-rewired`
  n'est plus en ligne ; le projet vit à
  [trashburger/robot-odyssey-rewired](https://github.com/trashburger/robot-odyssey-rewired).
  Son README demande explicitement que ni son code ni sa documentation ne
  soient lus par des outils d'IA : ils ne sont pas exploités ici.
- Le PC découpe le programme en exécutables séparés (jeu, labo, leçons,
  menu), là où l'Apple II recharge des blocs fixes après un redémarrage
  logiciel.

## Commandes

Clavier lu en `$AA25`, table en `$9C13` : `I`/`M`/`J`/`K` haut, bas,
gauche, droite, Ctrl + la même touche pour un pas fin, ESPACE prendre/poser,
`R` télécommande, `ESC` menu ; joystick et bouton aussi. Menu : ESPACE,
flèches, joystick. Triche : Ctrl-A, Ctrl-L, `T` au menu arment Ctrl-E, qui
coupe ou rétablit les murs **pour le joueur seul** (vérifié en a2shot).

## Méthode

```sh
A=../dev/tools/a2shot/a2shot
$A --disk original/A_ROBOTROPOLIS.woz wait:2500 key:"\r" wait:900 key:"\r" \
   wait:6500 shot:salle.png peek:0000:0xC000 peek:D000:0x3000 \
   | python3 -I ../dev/tools/re6502/peek2bin.py > ram.bin
```

Ne jamais faire `peek:0000:0x10000` : la lecture de `$C0xx` actionne les
commutateurs logiciels et dérègle la machine. `watch:52C8:0040:16`
journalise chaque bloc lu, `insert:` change de face. Le cœur POM2 émule la
carte langage : le jeu démarre en II+ 64 Ko comme en //e. Tester depuis le
`.woz` (protection de la piste 7). Dumps de référence : `build/ref/`.

## Points encore ouverts

- Effet d'un échec de la protection.
- Bloc `$7780-$787F` du monde (`unknown` au PC) : 15 motifs de 16 octets,
  rôle inconnu.
- Niveaux 2 à 5 décodés et vérifiés par pokes (emboîtement des robots
  joué au clavier), jamais joués de bout en bout au clavier.
- Création d'un fil au fer à souder (`$F7BE`, `$F86A`, `$FC2C`) lue
  seulement en surface.
- Pièces des robots dessinées par la carte langage (`$D2BC-$D830`) non
  reproduites par `re_graphics.py` (340 octets d'écart dans la salle des
  robots) ; octets d'en-tête des images non compris.
- Fiches de la bibliothèque à confronter au jeu : Clock Chip (vitesse des
  sorties) et RS Flip-Flop (sortie allumée par le reset).
- Détails du formatage du disque STORAGE (le formatage échoue dans a2shot).
