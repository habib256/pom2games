# DHGR — Apple IIe / IIc

Une première page présente les 16 couleurs, le texte blanc et un cercle `gfx`.
Une touche lance ensuite une animation DHGR de trois balles couleur sur une
grille, avec compteur de trames. Elles rebondissent sur les bords et entre
elles en échangeant leurs directions au contact (distance de 6 pixels).
Flèches : direction des trois balles ; espace : pause/reprise ; Échap : DOS
(également depuis la page d'introduction).
Les sprites masqués sauvegardent et restaurent le fond séparément sur les deux
pages, dans l'ordre inverse du dessin pour préserver les chevauchements.
Un II/II+ reçoit un message indiquant que le DHGR est indisponible.

Matériel : IIe **révision B**, carte 80 colonnes **étendue** avec 64 Ko
auxiliaires et cavalier DHGR adéquat, ou IIc. La RAM est sondée ; la révision
et le cavalier vidéo ne sont pas détectables en logiciel. La démo utilise
`a2_frame_init` / `a2_frame_wait` : VBLBAR sur IIe, temporisation sur IIc.
Les attentes sont bornées et la temporisation ne garantit pas une bascule
sans déchirure. Voir le [service de cadence](../../lib/apple2c/apple2frame.h).

```sh
make -C dev/examples/dhgr
make -C dev/examples/dhgr run
make -C dev/examples/dhgr assets
make -C dev/examples/dhgr test  # primitives et animation sur IIe
make test-dhgr
```

L'animation utilise les coordonnées couleur DHGR **140 × 192**, les sprites
DHGR et les transferts entre RAM principale et auxiliaire ; les primitives HGR
ne sont pas utilisées. Les modules de sprites et de transfert de blocs font
déjà partie de `HGRC_DHGR_SRCS`, lié avec le backend `gfx` DHGR couleur.

La boucle utilise `src/ball_render.s`, un rendu assembleur spécialisé pour les
trois sprites 6 × 6 (stride de 5 octets), avec tables d'adresses et de phases.
La sauvegarde du fond et le dessin masqué se font en un seul passage.
Le compteur utilise des chiffres DHGR précalculés depuis la police Beautiful Boot (`dev/tools/fonts.py`) dans
`src/digits.inc` et ne réécrit que les chiffres modifiés sur chaque page.
Les balles doivent rester entièrement dans l'écran : ce rendu ne fait pas de
clipping. Les primitives générales restent utilisées pour l'introduction et
la grille.

Mesure dans le cœur IIe de POM2 à environ 1 MHz : **299 trames en 10 secondes**,
contre 37 avant optimisation, soit environ **30 images/s et un gain de 8×**.
Le test d'animation impose au moins 20 images/s ; le test de rendu compare les
deux banques aux primitives DHGR générales, avec les sept phases de sprite,
les chevauchements, les bords et tous les chiffres.

La disquette est `dist/DHGR.dsk`. `a2shot` pour les tests se compile avec
`make -C dev/tools/a2shot` sur macOS arm64, avec libslirp et zlib.

```c
#include "dhgr.h"

if (!dhgr_init()) return 1;
dhgr_draw_page(2);
dhgr_clear(DHGR_BLACK);
dhgr_plot(559u, 191u, 1u);                     /* bits 560×192 */
dhgr_fill_rect(10u, 20u, 40u, 30u, DHGR_ORANGE); /* couleurs 140×192 */
dhgr_puts("APPLE II", 10u, 8u);                /* texte couleur blanc */
dhgr_flip();                                  /* attendre VBL avant si nécessaire */
dhgr_text_restore();                          /* avant routines texte ROM */
```

La configuration C place le code à `$6000`, au-dessus des **deux** pages vidéo.
Les détails des accès RAMRD/RAMWRT, du trampoline ZP et des backends sont dans
le [contrat mémoire de la bibliothèque](../../lib/hgrc/README.md#contrat-mémoire-et-transitions).
L’archive ne charge que les familles utilisées ; un backend `gfx` DHGR se lie
explicitement. Le [convertisseur](../../tools/assets/README.md) produit les
banques et masques de `src/ball.h` ; `src/ball.json` donne leur taille.
Le rendu assembleur lit les mêmes données dans `src/ball.bin`.

Sources matérielles : [Apple IIe Technical Note 3, Double High-Resolution Graphics](https://mirrors.apple2.org.za/ftp.apple.asimov.net/documentation/hardware/misc/Apple%20IIe%20Technical%20Notes.pdf)
et [Apple II Miscellaneous 7, Family Identification](https://mirrors.apple2.org.za/apple.cabi.net/FAQs.and.INFO/A2.TECH.NOTES.ETC/A2.CLASSIC.TNTS/a2misc007%281%29.htm).
