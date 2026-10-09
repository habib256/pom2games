# HGR — exemple de départ animé

*[← dev](../../README.md)*

Programme C pour Apple II/II+ 48 Ko sous DOS 3.3, également utilisable sur
IIe et IIc. Il montre trois balles masquées sur une grille, un compteur de trames,
le clavier non bloquant et les deux pages HGR. Son archive ne charge que les
familles utilisées. Auteur : VERHILLE Arnaud ; licence [GPL-3.0](../../../../LICENSE).

```sh
make -C dev/examples/hgr
make -C dev/examples/hgr run
make -C dev/examples/hgr test
```

Les balles démarrent à des positions et dans des directions différentes,
rebondissent sur les bords et les unes contre les autres. Une collision
échange les directions des deux balles lorsqu'elles se rapprochent ;
la détection utilise une distance entre leurs centres de 7 pixels.
La disquette est `dist/HGR.dsk`. Flèches : direction des trois balles ; espace :
pause/reprise ; Échap : retour à DOS. Sur II+, Ctrl-K/Ctrl-J remplacent les
flèches haut/bas. Ctrl-RESET passe aussi par la restauration du CRT.

## Boucle d'animation

1. Initialiser la vidéo et `a2_frame_init()`.
2. Dessiner le fond sur **les deux pages**, puis `hgr_spr_init_pool` avec un
   pool dimensionné pour les trois sprites et leurs deux fonds.
3. Définir les trois sprites et vérifier le résultat de `hgr_spr_define`.
4. Lire le clavier et calculer la position de chaque balle.
5. `hgr_spr_render()` restaure l'ancienne position et dessine sur la page cachée.
6. Dessiner le compteur sur cette même page, hors de la zone des sprites.
7. `a2_frame_wait()` attend ; `hgr_spr_present()` affiche et sélectionne
   l'autre page pour le prochain dessin.

Ne pas changer le fond sous un sprite déjà dessiné : sa sauvegarde doit rester
valide jusqu'à sa restauration. Pour changer sa forme, le masquer et mettre
à jour chaque page avant de le redéfinir. Les textes ×1 restent blancs.

## Cadence selon le modèle

| Modèle | Comportement |
|---|---|
| IIe / IIe enhanced | Attente du prochain début de VBL via `$C019`, puis bascule |
| II / II+ | Temporisation CPU ; pas de VBL lisible |
| IIc / IIc Plus | Temporisation ; aucun changement aux sources d'interruption |
| IIgs | Temporisation ; sa polarité VBL différente n'est pas utilisée |

La temporisation s'ajoute au temps de dessin. L'exemple utilise WAIT(70),
environ 13 ms à 1,02 MHz, à ajuster selon le programme et un éventuel
accélérateur. Elle ne garantit ni 60 images/s ni une bascule sans déchirure.
Sur IIe, une trame trop coûteuse peut manquer un VBL et réduire la cadence.
Les attentes VBL sont bornées : si le signal reste fixe, le service passe en
temporisation jusqu'à une nouvelle initialisation.

## Adapter et vérifier

Copier le dossier ; pour le placer à côté des jeux, définir `DEV ?= ../dev`
et `DIST ?= ../dist`. Garder `crt0_apple2.o` en premier à la liaison. Le
Makefile ajoute `APPLE2C_FRAME_SRCS` à l'archive pour le service de cadence.
Le sprite et ses masques sont précalculés, sans conversion pendant l'animation.

```sh
make -C dev/examples/hgr assets  # régénère ball.h/.bin/.png/.json depuis ball_source.png
make test-hgr                  # primitives, archive et moteur de sprites
make test-frame                # temporisation et repli borné, portable
make test-hgr-example          # animation, pause/reprise, commandes et sortie
python3 dev/tests/test_frame.py --iie
python3 dev/tests/test_hgr_example.py --iie
```

Les deux dernières commandes nécessitent `a2shot` (SDK POM2 macOS arm64).
Les tests avec signatures ROM IIc/IIgs vérifient seulement la sélection du
mode ; ils ne constituent pas une validation sur le matériel IIc/IIgs.

Références Apple : [Identification de la famille, note Miscellaneous #7](https://mirrors.apple2.org.za/apple.cabi.net/FAQs.and.INFO/A2.TECH.NOTES.ETC/A2.CLASSIC.TNTS/a2misc007%281%29.htm),
[polarité VBL, note IIGS #40](https://apple2.gs/technotes/tn-iigs-040/),
[IIc #9, Detecting VBL](https://mirrors.apple2.org.za/Apple%20II%20Documentation%20Project/Computers/Apple%20II/Apple%20IIc/Documentation/Apple%20IIc%20Technical%20Notes.pdf).

Le compteur utilise `hgr_hud_field_t`, avec un historique par page : seules
les cellules modifiées sont effacées/redessinées. Invalider ce champ après
toute modification externe de son fond.

Le programme et son archive utilisent `HGR_SPR_MAX=3`, ce qui réduit aussi
les métadonnées du moteur, en plus du pool externe de 84 octets.
