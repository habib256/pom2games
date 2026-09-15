# Snake — Apple II+ / DOS 3.3

Port Apple II du sketch `sketchs/gen2/game_snake_telemetry` de
[POM1](https://github.com/habib256/pom1) (GEN2Snake, VERHILLE Arnaud), écrit en
C (cc65). Le serpent traverse les bords gauche/droite, meurt contre les murs du
haut et du bas ; chaque pomme vaut 5 points et accélère le jeu, une gemme bonus
(20 points) apparaît toutes les 4 pommes pour un temps limité.

    make            # -> dist/SNAKE.dsk  (image DOS 3.3 5"1/4 amorçable)
    make run        # démarre l'image dans POM2 (profil Apple ][+)

Prérequis : cc65 (`brew install cc65`) et python3. Tout le reste est dans
`../dev`, pistes système DOS 3.3 comprises. `make run` lance POM2 installé
(`/Applications/POM2.app`, ou `make run POM2=chemin/vers/POM2`).

## Commandes

| Clavier                  | Action                    |
|--------------------------|---------------------------|
| I J K L, flèches         | diriger le serpent        |
| n'importe quelle touche  | démarrer / rejouer        |

Le titre démarre seul après ~4 s. Après GAME OVER, la partie repart seule ou à
la première touche. Sur un II+ seules les flèches gauche/droite existent.

Améliorations prévues : voir [`TODO.md`](TODO.md).

## Contenu

    src/snake.c          le jeu
    src/gen2c/           runtime C HGR de POM1 (dev/lib/gen2c), version Apple II
    src/hello.bas        HELLO : 10 PRINT CHR$(4);"BRUN SNAKE"
    dist/SNAKE.dsk       l'image produite

Bibliothèques : `../dev/lib/apple2c` (clavier), `../dev/lib/apple2/hgr.asm`
(commutateurs), `../dev/cc65/crt0_apple2.s` + `apple2_hgr_c.cfg`,
`../dev/tools/dos33.py`.

## Différences avec l'original Apple-1 / GEN2

- La télémétrie POM1 (`$C440-$C443`) est retirée : sur un Apple II c'est
  l'espace d'entrées/sorties du slot 4, où vit une Mockingboard.
- `src/gen2c` : commutateurs en `$C050` au lieu de `$C250`, plus de
  `gen2_wait_vbl` (pas de V-blank sur un II+). Les noms `gen2_*` sont gardés.
- Clavier Apple II et flèches ; titre « APPLE II ».
- La réinitialisation du mode vidéo à chaque trame (contournement propre à
  l'émulateur POM1) est retirée.
- Binaire de 8,8 Ko à `$6000`, zéro-page C en `$50`, pile C sous DOS
  (`$8E00-$95FF`).
