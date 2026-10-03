# DHGR — Apple IIe / IIc

Démo animée : 16 couleurs, texte blanc, tracé `gfx`, sprite masqué avec
save-under et alternance des deux pages. Une touche revient à DOS.
Un II/II+ reçoit un message indiquant que le DHGR est indisponible.

Matériel : IIe **révision B**, carte 80 colonnes **étendue** avec 64 Ko
auxiliaires et cavalier DHGR adéquat, ou IIc. La RAM est sondée ; la révision
et le cavalier vidéo ne sont pas détectables en logiciel. La démo attend le
VBLBAR sur IIe ; sur IIc, dont C019 est un registre d’interruption différent,
elle utilise une temporisation et ne garantit pas une bascule sans déchirure.

```sh
make -C dev/examples/dhgr
make -C dev/examples/dhgr run
make -C dev/examples/dhgr assets
make test-dhgr
```

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

Sources matérielles : [Apple IIe Technical Note 3, Double High-Resolution Graphics](https://mirrors.apple2.org.za/ftp.apple.asimov.net/documentation/hardware/misc/Apple%20IIe%20Technical%20Notes.pdf)
et [Apple II Miscellaneous 7, Family Identification](https://mirrors.apple2.org.za/apple.cabi.net/FAQs.and.INFO/A2.TECH.NOTES.ETC/A2.CLASSIC.TNTS/a2misc007%281%29.htm).
