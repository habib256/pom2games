# dev — bibliothèques et outils Apple II

L'équivalent Apple II de l'arbre `dev/` de [POM1](https://github.com/habib256/pom1)
(bibliothèques Apple-1 + GEN2), pour écrire ou porter des programmes Apple II+
48 Ko / DOS 3.3 avec cc65. Les programmes de ce dépôt (`../chess`, `../maze3d`,
`../snake`, `../sokoban`, `../logo`) l'utilisent.

    dev/
      lib/apple2/      asm : équivalent de dev/lib/apple1 (+ HGR et sortie DOS)
      lib/apple2c/     C   : équivalent de dev/lib/apple1c
      lib/hgr/         modules HGR repris tels quels de dev/lib/gen2
      cc65/            configs ld65 (asm et C) + crt0 Apple II
      tools/dos33.py   fabrique une image DOS 3.3 amorçable (.dsk)
      tools/dos33_system.bin  pistes système DOS 3.3 (0-2) du disque maître Apple
      tools/a2shot/    exécutions sans interface, scriptées, avec captures PNG
      examples/hello/  programme de départ asm + C sur un disque

## Démarrer

    cd examples/hello
    make            # -> dist/HELLO.dsk (HELLOASM au boot, puis BRUN HELLOC)
    make run        # dans POM2, profil Apple ][+

Copier `examples/hello` pour commencer un nouveau programme.

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
    ./a2shot --disk ../../../chess/dist/CHESS.dsk \
        wait:900 shot:menu.png key:2 wait:60 shot:board.png peek:0800:2

| Étape             | Effet                                              |
|-------------------|----------------------------------------------------|
| `wait:N`          | exécute N trames (17 030 cycles chacune)           |
| `key:TEXTE`       | tape le texte (`\r` RETURN, `\e` ESC, `\<` `\>` flèches) |
| `shot:F.png`      | capture l'écran                                    |
| `peek:ADR[:LEN]`  | vide la mémoire (lecture bus)                      |
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

Licence : GPL v3, comme les sources POM1 dont ces bibliothèques dérivent.
