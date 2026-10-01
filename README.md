# pom2games

Programmes Apple II sur disquettes DOS 3.3, pour
[POM2](https://github.com/habib256/pom2) ou un vrai Apple II. Ce sont surtout des
ports des programmes Apple-1 + carte GEN2 de
[POM1](https://github.com/habib256/pom1) : la GEN2 est le sous-système vidéo de
l'Apple II transplanté sur le bus Apple-1, ce qui rend le passage à l'Apple II
naturel.

| Dossier | Programme | Machine | Disquette |
|---|---|---|---|
| [`sokoban/`](sokoban/) | Sokoban, 146 niveaux Microban, records sauvegardés, manette ou clavier | Apple II+ | `dist/SOKOBAN.dsk` |
| [`chess/`](chess/) | Échecs contre l'ordinateur ou à deux | Apple II+ | `dist/CHESS.dsk` |
| [`maze3d/`](maze3d/) | Dungeon crawler 3D en fil de fer, double tampon HGR | Apple II+ | `dist/MAZE3D.dsk` |
| [`snake/`](snake/) | Snake en C (cc65) | Apple II+ | `dist/SNAKE.dsk` |
| [`logo/`](logo/) | LOGO V2.6 : tortue HGR, texte / mixte / graphique, 40 ou 80 colonnes | Apple //e (80 col.) ou II+ (40 col.) | `dist/LOGO.dsk` |
| [`demos/`](demos/) | Menu de 5 démos : BOUNCES, ANIMALS, LIFE, PRESHIFT, FONT | Apple II+ | `dist/DEMO.dsk` |

Les disquettes sont prêtes à l'emploi : on démarre dessus et le programme se
lance. Chaque dossier a son `README.md` (commandes, différences avec
l'original) et, pour les jeux, un `TODO.md` d'améliorations prévues.

## Construire

    make                # toutes les disquettes
    make -C chess        # une seule
    make -C chess run    # la lancer dans POM2 installé (/Applications/POM2.app)

Prérequis : [cc65](https://cc65.github.io/) (`brew install cc65`) et python3.
Le dépôt ne dépend d'aucun autre dossier.

## dev/

[`dev/`](dev/) est la boîte à outils commune, l'équivalent Apple II des
bibliothèques Apple-1 de POM1 :

- `dev/lib/apple2` et `dev/lib/apple2c` : clavier, texte, HGR, retour propre à
  DOS ou à un menu BASIC, en assembleur et en C ;
- `dev/lib/hgr` : texte, sprites et tables HGR (assembleur) ;
- `dev/lib/hgrc` et `dev/lib/gfx` : runtime graphique C et géométrie ;
- `dev/cc65` : configurations de l'éditeur de liens et démarrage C ;
- `dev/tools/dos33.py` : fabrique les disquettes DOS 3.3 ;
- `dev/tools/a2shot` : fait tourner une disquette sans fenêtre sur le cœur de
  POM2, tape au clavier et prend des captures — c'est ainsi que les ports sont
  testés ;
- `dev/tools/a2run` : la même chose en C portable (Linux, macOS), avec
  l'écriture disque pour vérifier les sauvegardes ;
- `dev/examples/hello` : programme de départ en assembleur et en C.

## Licences et crédits

Code : GPL-3.0 ([LICENSE](LICENSE)), comme POM1 et POM2 dont il dérive
(VERHILLE Arnaud).

- Niveaux Microban : David W. Skinner.
- Pièces d'échecs : cc65-Chess de Stefan Wessels, portage Apple II Oliver
  Schmidt, dessins Frank Gebhart.
- Sprites des monstres et emotes : SCROLL-O-SPRITES de Quale (CC-BY-3.0).
- Police 8x8 : Beautiful Boot, Michael Pohoreski.

Les ROM Apple II / //e / Disk II (`dev/tools/a2shot/roms/`) et les pistes
système de DOS 3.3 (`dev/tools/dos33_system.bin`, présentes aussi sur chaque
disquette) sont des œuvres d'Apple Computer, Inc. Elles sont reprises de POM2,
où elles sont déjà publiées, pour que le dépôt se construise et se teste seul.
`dev/tools/a2shot/sdk/` contient le cœur de POM2 compilé (GPL-3.0).
