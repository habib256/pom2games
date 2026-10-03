# dev — bibliothèques et outils Apple II

L'équivalent Apple II de l'arbre `dev/` de [POM1](https://github.com/habib256/pom1)
(bibliothèques Apple-1 + GEN2), pour écrire ou porter des programmes Apple II+
48 Ko / DOS 3.3 avec cc65. Les programmes de ce dépôt (`../chess`, `../maze3d`,
`../snake`, `../micro-sokoban`, `../logo`, `../demos`) l'utilisent.

    dev/
      lib/apple2/      asm : équivalent de dev/lib/apple1 (+ HGR, sortie DOS,
                       son, manette, commandes DOS)
      lib/apple2c/     C   : équivalent de dev/lib/apple1c (+ son, manette, DOS)
      lib/hgr/         modules HGR repris tels quels de dev/lib/gen2
      lib/hgrc/        runtime C HGR : le gen2c de POM1 en version Apple II
      lib/gfx/         géométrie C (lignes, rectangles, cercles) pour hgrc
      cc65/            configs ld65 (asm et C) + crt0 Apple II
      tools/dos33.py   fabrique une image DOS 3.3 amorçable (.dsk)
      tools/dos33_system.bin  pistes système DOS 3.3 (0-2) du disque maître Apple
      tools/a2shot/    exécutions sans interface, scriptées, avec captures PNG
      tools/a2run/     la même chose en C portable, avec écriture disque
      examples/hello/  programme de départ asm + C sur un disque

## Démarrer

    cd examples/hello
    make            # -> ../../../dist/HELLO.dsk (HELLOASM au boot, puis BRUN HELLOC)
    make run        # dans POM2, profil Apple ][+

Copier `examples/hello` pour commencer un nouveau programme ; à côté de
`micro-sokoban/`, mettre `DEV ?= ../dev` et `DIST ?= ../dist` dans son `Makefile`
pour que la disquette rejoigne les autres dans `dist/`.

`pom2games` ne dépend d'aucun autre dossier : il suffit de cc65 et de python3
pour construire les disques (et de libslirp pour a2shot). `make run` lance POM2
installé (`/Applications/POM2.app`, ou `make run POM2=chemin/vers/POM2`).

## Correspondance Apple-1 → Apple II

| POM1 (Apple-1 / GEN2)            | Ici (Apple II)                        |
|----------------------------------|---------------------------------------|
| `apple1.inc`                     | `lib/apple2/apple2.inc`               |
| `APPLE1_PREAMBLE`                | `APPLE2_PREAMBLE`                     |
| `zp.inc` (figé en $00-$07)       | `lib/apple2/zp.inc` (début du segment ZEROPAGE, $50 par défaut) |
| `print.asm` (ECHO $FFEF)         | `lib/apple2/print.asm` (COUT $FDED)   |
| `print_num.asm`, `delay.asm`     | mêmes noms, mêmes API                 |
| `kbd.asm` (PIA $D010/$D011)      | `lib/apple2/kbd.asm` ($C000 / $C010)  |
| `gen2_init.asm`                  | `lib/apple2/hgr.asm`                  |
| `JMP WOZMON`                     | `JMP apple2_exit` (`lib/apple2/exit.asm`) |
| `apple1c` (`woz_*`, `apple1_*`)  | `lib/apple2c` (`a2_*`, `apple2_*`)    |
| `gen2c`, `gfx`                   | `lib/hgrc`, `lib/gfx`                 |
| `crt0_pom1.s`                    | `cc65/crt0_apple2.s`                  |
| `apple1_gen2.cfg` / `_c.cfg`     | `cc65/apple2_hgr.cfg` / `apple2_hgr_c.cfg` |
| `emit_gen2_txt.py` (Wozmon hex)  | `tools/dos33.py` (disque DOS 3.3)     |
| `hgr_text8`, `hgr_sprite16`, …   | `lib/hgr/` (inchangés)                |

Ce qui change vraiment d'une machine à l'autre :

- **Clavier** : le verrou `$C000` ne se remet pas à zéro à la lecture, il faut
  toucher `$C010` (l'Apple-1 le faisait implicitement en lisant `$D010`).
- **Écran** : il n'y a pas de second terminal. Le texte (COUT) va sur la page
  texte, visible en mode TEXT ; les pages HGR sont une autre mémoire, on bascule
  sans rien perdre.
- **Commutateurs vidéo** en `$C050-$C057` (la GEN2 les décode en `$C250-$C257`).
- **Pas de V-blank** sur un II/II+ : on dessine directement, ou sur la page
  cachée puis on bascule.
- **Page zéro partagée** avec le Moniteur (`$20-$4F`), DOS et Applesoft
  (`$50-$FF`) : les programmes placent leur ZP en `$50+` et la sauvegardent au
  démarrage s'ils rendent la main à DOS.

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
