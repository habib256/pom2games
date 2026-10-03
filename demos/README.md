# DEMO — cinq démos Apple II sur une disquette

Ports Apple II de démos GEN2 de [POM1](https://github.com/habib256/pom1)
(VERHILLE Arnaud), réunies sur `../dist/DEMO.dsk` avec un menu au démarrage.

    make            # -> ../dist/DEMO.dsk  (image DOS 3.3 5"1/4 amorçable)
    make run        # démarre l'image dans POM2 (profil Apple ][+)

Prérequis : cc65 (`brew install cc65`) et python3. Tout le reste est dans
`../dev`. Machine : Apple II+ 48 Ko (ou tout modèle ultérieur).

## Le menu

Au démarrage, le menu propose les cinq démos. On tape le chiffre ; **ESC dans une
démo revient au menu**, ESC dans le menu revient au prompt DOS.

| Touche | Programme | Ce que c'est | Original POM1 |
|---|---|---|---|
| 1 | `BOUNCES` | 4 balles XOR qui rebondissent et se percutent, décor vectoriel, compteur, double tampon HGR1/HGR2 | `demo_bounces/GEN2Bounces.c` |
| 2 | `ANIMALS` | 8 animaux en sprites couleur ×2, mouvement lisse, double tampon | `demo_sprite_animals/GEN2Animals.c` |
| 3 | `LIFE` | Jeu de la vie de Conway 40×40, 6 motifs (une touche : motif suivant) | `demo_life/HGR_Life.asm` |
| 4 | `PRESHIFT` | Moteur de sprites pré-décalés de Buzzard Bait : balle au pixel près, vaisseau (une touche : menu) | `demo_preshift/main.c` |
| 5 | `FONT` | Les 256 glyphes de la police Beautiful Boot 8×8 (une touche : menu) | `demo_hgr_bbfont_show/HGR_BBFontShow.asm` |

Le menu (`HELLO`) fait `BLOAD` puis `CALL 24576` : chaque démo rend la main au
BASIC par un `RTS`, en remettant la page zéro et l'écran texte. Il commence par
`MAXFILES 1` (DOS garde un seul tampon de fichier, ce qui libère 1,2 Ko sous DOS
pour ANIMALS) et `HIMEM: 4096` (ses chaînes restent sous `$1000`), et remet
`MAXFILES 3` en quittant.

## Différences avec les originaux Apple-1 / GEN2

- **Pas de V-blank sur un II+.** BOUNCES et ANIMALS basculent de page dès que la
  page cachée est dessinée ; PRESHIFT remplace l'attente du V-blank par une pause
  d'une trame (`WAIT` du Moniteur), comme Buzzard Bait sur un vrai Apple II.
- **Clavier Apple II et retour au menu** au lieu de Wozmon ; BOUNCES, qui
  tournait sans fin, s'arrête sur ESC.
- **LIFE** : grilles déplacées de `$0200`/`$0900` (vecteurs DOS, menu BASIC) vers
  `$1000`/`$1700`.
- **FONT** : les légendes allaient au terminal Apple-1 ; elles occupent les
  4 lignes de texte du mode mixte, la grille remonte au-dessus.
- **Légendes** de BOUNCES et ANIMALS raccourcies à 34 caractères, la largeur que
  `hgr_puts8` affiche vraiment (les originaux étaient coupés), avec
  l'indication ESC.
- **Runtime C** : `../dev/lib/hgrc` (API native `hgr.h` / `hgr_*`). Les trois
  démos C partagent une archive ; l'éditeur de liens extrait uniquement les
  familles de routines et les blocs de page zéro nécessaires.

## Contenu

    src/hello.bas            le menu
    src/bounces.c            BOUNCES
    src/animals.c            ANIMALS (+ animals_gen_x2.py, qui génère ses sprites)
    src/preshift.c           PRESHIFT (+ preshift_sprites.h / .txt)
    src/life.s               LIFE
    src/font.s               FONT
    src/demo_c.cfg           config ld65 des démos C (ci-dessous)
    ../dist/DEMO.dsk         l'image produite

LIFE et FONT utilisent `../dev/cc65/apple2_hgr.cfg` (code à `$6000`).

## Plan mémoire des démos C

    $0050-$00FF  zéro-page (runtime C + hgrc), restaurée au retour
    $0800-$0FFF  le menu BASIC (programme, variables, chaînes)
    $1000-$1FFF  BSS, tables, sauvegarde de la page zéro
    $2000-$5FFF  HGR pages 1 et 2
    $6000-$96A5  le programme (BOUNCES 12,3 Ko, ANIMALS 13,1 Ko, PRESHIFT 4,6 Ko)
    $96A6-$9AA5  pile C
    $9AA6-$BFFF  DOS 3.3 avec MAXFILES 1

## Crédits

Démos : VERHILLE Arnaud (GPL-3.0). Sprites des animaux : SCROLL-O-SPRITES de
Quale (CC-BY-3.0). Police : Beautiful Boot, Michael Pohoreski. Méthode des
sprites pré-décalés : Buzzard Bait (Sirius Software, 1983).
