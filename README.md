# pom2games

Programmes Apple II sur disquettes DOS 3.3 ou ProDOS, pour
[POM2](https://github.com/habib256/pom2) ou un vrai Apple II. Ce sont surtout des
ports de programmes de [POM1](https://github.com/habib256/pom1), adaptés à
la vidéo native de l'Apple II.

| Dossier | Programme | Machine | Disquette |
|---|---|---|---|
| [`chromabreak/`](chromabreak/) | Casse-briques DHGR 16 couleurs, souris AppleMouse et clavier | Apple //e enhanced ou //c 128 Ko / ProDOS | `dist/CHROMABREAK.po` |
| [`arkabreakout/`](arkabreakout/) | Casse-briques HGR : 60 secteurs, 6 bonus, combos, joystick/paddles/AppleMouse II | Apple II+ 48 Ko | `dist/ARKABREAKOUT.dsk` |
| [`micro-sokoban/`](micro-sokoban/) | MICRO-SOKOBAN, tutoriel de 5 niveaux + 454 Microban I à IV, Hall of Fame sauvegardé, manette ou clavier | Apple II+ | `dist/MICRO-SOKOBAN.dsk` |
| [`chess/`](chess/) | Échecs contre l'ordinateur ou à deux | Apple II+ | `dist/CHESS.dsk` |
| [`maze3d/`](maze3d/) | Dungeon crawler 3D en fil de fer, double tampon HGR | Apple II+ | `dist/MAZE3D.dsk` |
| [`light3dball/`](light3dball/) | Balle en couloir 3D HGR, cinq niveaux, souris ou clavier et cibles finales | Apple II+ 48 Ko | `dist/LIGHT3DBALL.dsk` |
| [`pinball/`](pinball/) | Pinball Construction Set de Bill Budge, éditeur et moteur 6502 adaptés à ca65/ld65 | Apple II+ 48 Ko ou //c, souris ou manette | `dist/PINBALL.dsk` |
| [`wilderness/`](wilderness/) | Réimplémentation de Wilderness (Electric Transit, 1985), en cours : vue 3D du terrain par lancer de rayons, cartes générées | Apple II+ 48 Ko / DOS 3.3 | `dist/WILDERNESS.dsk` |
| [`mcs/`](mcs/) | Éditeur musical inspiré de Music Construction Set : deux portées HGR, clavier, haut-parleur et sauvegarde | Apple II+ 48 Ko / DOS 3.3 | `dist/MCS.dsk` |
| [`snake/`](snake/) | Snake en C (cc65) | Apple II+ | `dist/SNAKE.dsk` |
| [`logo/`](logo/) | LOGO V2.6 : tortue HGR, texte / mixte / graphique, 40 ou 80 colonnes | Apple //e (80 col.) ou II+ (40 col.) | `dist/LOGO.dsk` |
| [`dev/examples/hgr/`](dev/examples/hgr/) | Exemple HGR animé : sprite masqué, compteur, clavier, cadence | Apple II+ / IIe / IIc | `dist/HGR.dsk` |
| [`dev/examples/dhgr/`](dev/examples/dhgr/) | Palette 16 couleurs et grille DHGR | Apple IIe 128 Ko / IIc | `dist/DHGR.dsk` |
| [`dev/examples/hello/`](dev/examples/hello/) | Programme de départ, assembleur et C sur la même disquette | Apple II+ | `dist/HELLO.dsk` |

Deux profils de jeux sont définis : **Apple II+ 48 Ko / DOS 3.3** pour
Arkabreakout et les ports classiques, et **Apple //e enhanced 128 Ko / ProDOS**
pour CHROMABREAK. Le premier utilise HGR et clavier/paddle ; le second utilise
DHGR 16 couleurs et AppleMouse II, avec prise en charge de la souris intégrée
du //c 128 Ko dans ce même profil ProDOS.

Toutes les disquettes sont rangées dans [`dist/`](dist/), prêtes à l'emploi : on
démarre dessus et le programme se lance. Chaque dossier a son `README.md`
(commandes, différences avec l'original) et, pour les jeux, un `TODO.md`
d'améliorations prévues.

MICRO-SOKOBAN 1.2 est disponible dans les
[releases GitHub](https://github.com/habib256/pom2games/releases/tag/1.2), avec
sa disquette amorçable et la [description de la version](docs/releases/1.2.md).
CHROMABREAK 1.0 l'est aussi, sous l'étiquette
[`chromabreak-1.0`](https://github.com/habib256/pom2games/releases/tag/chromabreak-1.0),
avec sa disquette ProDOS et sa [description](docs/releases/chromabreak-1.0.md).

## Construire

    make profile-ii-plus # jeux Apple II+ 48 Ko / DOS 3.3
    make profile-iie-prodos # CHROMABREAK, //e enhanced 128 Ko / ProDOS
    make test-chromabreak # volume ProDOS et tests //e lorsque a2shot est disponible
    make                 # toutes les disquettes, dans dist/
    make -C chess        # une seule (elle va aussi dans dist/)
    make -C chess run    # la lancer dans POM2 installé (/Applications/POM2.app)
    make test            # tout construire, puis CHROMABREAK, ARKABREAKOUT, CHESS,
                         # HGR, cadence, exemple HGR, assets, budgets de performance
                         # et les 454 niveaux de MICRO-SOKOBAN dans a2run
    make test-arkabreakout # collisions, bonus, niveaux, paddle et sortie DOS
    make test-chess      # roque, promotion, règle des 50 coups, matériel mort
    make test-mcs        # éditeur musical, sauvegarde/rechargement et son
    make test-hgr        # primitives, texte gfx, moteur de sprites et archive
    make test-frame      # cadence, délais et repli en cas de VBL bloqué
    make test-hgr-example # animation, pause/reprise et retour à DOS
    make test-dhgr       # validation DHGR dans a2shot (macOS arm64)
    make test-assets     # police (dev/tools/fonts.py --check) et conversion d'assets
    make test-techniques # comparaison fhpack, fdraw et sprites compilés (HGR/6502)
    make bench           # mesure les primitives (dev/bench), bench-check compare
                         # aux budgets de dev/bench/baseline.json
    make check           # tout reconstruire, échouer si dist/ ne correspond pas
    make clean           # efface les build/ (les disquettes restent)
    make distclean       # efface aussi dist/*.dsk et dist/*.po

Prérequis : [cc65](https://cc65.github.io/) (`brew install cc65`, ou
`apt install cc65`) et python3 ; des compilateurs C/C++ et zlib pour `make test`
(C pour `dev/tools/a2run`, C++ pour les tests fhpack). Les tests //e et DHGR passent par
`dev/tools/a2shot` (macOS arm64, libslirp via brew) : `make test-dhgr` l'exige,
`make test` les saute s'il manque.
Le dépôt ne dépend d'aucun autre dossier. La construction est déterministe : les
images de `dist/`, faites sous macOS, se reconstruisent à l'octet près avec le
cc65 2.19 d'Ubuntu 24.04.

L'intégration continue (`.github/workflows/build.yml`) lance `make check` puis
`make test` sous Ubuntu à chaque push : une modification des sources sans
`dist/` reconstruit et commité fait échouer le build.

## dev/

[`dev/`](dev/) est la boîte à outils commune pour développer sur Apple II :

- `dev/lib/apple2` et `dev/lib/apple2c` : clavier, texte, HGR, retour propre à
  DOS ou à un menu BASIC, son, manette, commandes DOS (BLOAD / BSAVE), en
  assembleur et en C ;
- `dev/lib/prodos` et `dev/lib/mouse` : MLI ProDOS, sortie SYS et AppleMouse II ;
- `dev/tools/prodos` : constructeur et lecteur de volumes ProDOS amorçables ;
- `dev/lib/font` : la police Beautiful Boot 8x8, une table maîtresse découpée
  à la demande (assembleur, C et `dev/tools/fonts.py`) ;
- `dev/lib/hgr` : texte, sprites et tables HGR (assembleur) ;
- `dev/lib/hgrc` et `dev/lib/gfx` : runtime graphique C HGR/DHGR et géométrie ;
- [`dev/examples/hgr`](dev/examples/hgr/) : exemple animé, clavier, compteur,
  sprites masqués, double tampon et cadence selon le modèle ;
- [`dev/examples/dhgr`](dev/examples/dhgr/) : palette et grille DHGR sur
  //e 128 Ko ou //c ;
- `dev/cc65` : configurations de l'éditeur de liens, démarrage C et
  `apple2.mk`, le fragment Makefile commun à tous les programmes ;
- `dev/tools/dos33.py` : fabrique les disquettes DOS 3.3 et relit leurs
  fichiers ;
- `dev/tools/a2test.py` : harnais commun des tests (labels ld65, lancement
  a2run/a2shot, décodage des dumps mémoire) ;
- `dev/tools/assets`, `dev/tests`, `dev/bench` : conversion PNG/PPM en
  HGR/DHGR, tests des bibliothèques et budgets de performance ;
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
