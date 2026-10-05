# dev — bibliothèques et outils Apple II

Bibliothèques et outils pour écrire des programmes Apple II+ 48 Ko / DOS 3.3
avec cc65. Dérivés de [POM1](https://github.com/habib256/pom1) (GPL v3), ils
utilisent la vidéo native de l'Apple II. Tous les jeux du dépôt les partagent.

    dev/
      lib/apple2/      asm : matériel, texte, clavier, HGR, sortie DOS,
                       son, manette, commandes DOS
      lib/apple2c/     C   : texte, clavier, son, manette, DOS
      lib/hgr/         texte, sprites et tables HGR en assembleur
      lib/hgrc/        runtime C HGR : hgr.h, fonctions hgr_*
      lib/gfx/         géométrie C (lignes, rectangles, cercles) pour hgrc
      cc65/            configs ld65 (asm et C) + crt0 Apple II
      tools/dos33.py   fabrique une image DOS 3.3 amorçable (.dsk)
      tools/dos33_system.bin  pistes système DOS 3.3 (0-2) du disque maître Apple
      tools/a2shot/    exécutions sans interface, scriptées, avec captures PNG
      tools/a2run/     la même chose en C portable, avec écriture disque
      examples/hello/  programme de départ asm + C sur un disque
      examples/hgr/    démarrage HGR animé : sprites, compteur, clavier, cadence
      examples/dhgr/   DHGR 560×192 / 16 couleurs, Apple IIe 128 Ko ou IIc

## Démarrer

    cd examples/hello
    make            # -> ../../../dist/HELLO.dsk (HELLOASM au boot, puis BRUN HELLOC)
    make run        # dans POM2, profil Apple ][+

Copier `examples/hello` pour commencer un programme texte, ou
[`examples/hgr`](examples/hgr/README.md) pour une animation avec sprites,
compteur, clavier et double tampon. Pour placer le nouveau dossier à côté de
`micro-sokoban/`, mettre `DEV ?= ../dev` et `DIST ?= ../dist` dans son `Makefile`
pour que la disquette rejoigne les autres dans `dist/`.

`pom2games` ne dépend d'aucun autre dossier : il suffit de cc65 et de python3
pour construire les disques (et de libslirp pour a2shot). `make run` lance POM2
installé (`/Applications/POM2.app`, ou `make run POM2=chemin/vers/POM2`).

## Matériel Apple II

- Clavier : lire `$C000`, puis toucher `$C010` pour acquitter la touche.
- Vidéo : commutateurs `$C050-$C057`, texte et deux pages HGR indépendantes.
- Pas de drapeau V-blank lisible sur II/II+ : dessiner sur la page cachée,
  puis basculer l'affichage.
- Page zéro partagée avec le Moniteur et DOS : sauvegarde/restauration par
  les routines de démarrage et de sortie.

## Rendre la main

Deux façons de quitter, selon la façon dont le programme a été lancé :

- **`BRUN` (un jeu)** : `APPLE2_PREAMBLE` puis `apple2_exit`, qui revient au prompt
  DOS. En C : le `crt0_apple2.s` par défaut.
- **`BLOAD` + `CALL` depuis un menu BASIC** : `APPLE2_PREAMBLE_CALL` (la pile de
  l'appelant n'est pas touchée) puis `apple2_return`, qui fait un `RTS` vers le
  BASIC. En C : `__EXIT_RTS__ = 1` dans la config ld65 (voir
  `../demos/src/demo_c.cfg`). Un `BRUN` depuis un programme BASIC, lui, ne
  revient pas proprement : c'est pour ça que le menu utilise `CALL`.

Dans les deux cas, Ctrl-RESET revient au prompt DOS avec la page zéro restaurée.

## Carte mémoire (Apple II+ 48 Ko, DOS 3.3)

    $0000-$004F  Moniteur / DOS          — laissé tranquille (COUT fonctionne)
    $0050-$00FF  ZEROPAGE du programme   — à restaurer si on revient à DOS
    $0100-$01FF  pile 6502
    $0200-$02FF  tampon d'entrée         — libre pendant l'exécution
    $0300-$03FF  vecteurs DOS / Moniteur — ne pas toucher ($03F2 = RESET)
    $0400-$07FF  page texte 1
    $0800-$0FFF  programme BASIC d'accueil (HELLO) — gardé par DOS, ne pas écraser
    $1000-$1FFF  libre (LOWBSS)
    $2000-$3FFF  HGR page 1
    $4000-$5FFF  HGR page 2
    $6000-$95FF  le binaire BRUN (13,8 Ko max), puis BSS / pile C
    $9600-$BFFF  DOS 3.3

## a2shot

Démarre un disque sur un Apple II+ émulé (cœur de POM2, sans fenêtre, sans
horloge murale, donc déterministe) et déroule un script :

    cd tools/a2shot && make
    ./a2shot --disk ../../../dist/CHESS.dsk \
        wait:900 shot:menu.png key:2 wait:60 shot:board.png peek:0800:2

| Étape             | Effet                                              |
|-------------------|----------------------------------------------------|
| `wait:N`          | exécute N trames (17 030 cycles chacune)           |
| `key:TEXTE`       | tape le texte (`\r` RETURN, `\e` ESC, `\<` `\>` flèches) |
| `shot:F.png`      | capture l'écran                                    |
| `peek:ADR[:LEN]`  | vide la mémoire (lecture bus)                      |
| `poke:ADR:OCTET` | écrit un octet en mémoire (valeurs hexadécimales) |
| `joy:X,Y`, `btn:N,0\|1` | manette                                      |
| `reset`           | appuie sur RESET                                   |
| `pc`              | affiche le PC                                      |

`--iie` démarre un Apple //e enhanced (65C02, carte 80 colonnes et mémoire
auxiliaire) au lieu du ][+ : c'est ce qui permet de tester LOGO en 80 colonnes.

a2shot démarre une **copie** du disque : POM2 réécrit les images modifiées, et
un test ne doit pas altérer le disque qu'il vérifie.

a2shot est autonome : `sdk/` contient le SDK du cœur de POM2 (`core.hpp` et
`libpom2_core.a`, arm64, sans symboles de débogage) et `roms/` les ROM Apple ][+,
Apple //e (+ ROM caractères) et Disk II, copiés depuis POM2 (`--roms DIR` pour en prendre d'autres). Seules
libslirp (brew) et zlib viennent du système.
Un DOS 3.3 met environ 900 trames à lancer un jeu de 8-12 Ko.

## a2run

L'équivalent portable d'a2shot (Linux et macOS, C99 + zlib, sans le cœur de
POM2) : un 6502 NMOS (validé par la suite de tests fonctionnels de Klaus
Dormann), 48 Ko, clavier, haut-parleur, manette et un Disk II au niveau des
quartets, en lecture **et en écriture**. Mêmes ROM (`a2shot/roms`), même
syntaxe de script, plus quelques étapes pour les tests :

    cd tools/a2run && make
    ./a2run --disk ../../../dist/MICRO-SOKOBAN.dsk \
        wait:900 shot:titre.png key:" " wait:30 key:LLK spk dsk:apres.dsk

| Étape             | Effet                                              |
|-------------------|----------------------------------------------------|
| `wait:N`, `key:`, `shot:`, `peek:`, `joy:`, `btn:`, `reset`, `pc` | comme a2shot (`\^` `\v` : flèches haut/bas) |
| `text`            | affiche la page texte 40×24                        |
| `poke:ADR:VAL`    | écrit un octet en RAM                              |
| `spk`             | nombre de basculements du haut-parleur depuis le dernier `spk` |
| `dsk:F.dsk`       | écrit la disquette telle que le programme l'a laissée (sauvegardes) |

Le disque passé à `--disk` n'est jamais modifié. Un DOS 3.3 met environ
400 trames à lancer un jeu. Pas de carte langage, pas de 80 colonnes : pour
LOGO sur //e, a2shot reste l'outil.

Licence : GPL v3, comme les sources POM1 dont ces bibliothèques dérivent.

## Assets et mesures

- [Conversion PNG/PPM HGR/DHGR](tools/assets/README.md) : banques, masques, aperçus et tailles.
- [Benchmarks et budgets de régression](bench/README.md) : `make bench`, `make bench-dhgr`.
- `make test-assets` et `make bench-check` font partie de `make test`.
- `make test-dhgr` vérifie les deux pages, les deux banques et les deux backends.

## Cadence et exemple animé

Le service optionnel [`lib/apple2c/apple2frame.h`](lib/apple2c/apple2frame.h)
attend le prochain VBL sur IIe, ou utilise une temporisation sur II/II+ et
IIc. Les attentes sont bornées ; le service ne configure aucune interruption.
Lier `APPLE2C_FRAME_SRCS` et appeler `a2_frame_init()` avant la boucle.
La temporisation ajoute un délai au dessin ; elle ne garantit pas une fréquence
fixe. Voir l’[exemple HGR](examples/hgr/README.md) pour les contrats par modèle.

`make test-frame` et `make test-hgr-example` font partie de `make test`.
Les tests du moteur de sprites font partie de `make test-hgr`.
