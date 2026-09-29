# lib/hgrc — runtime C HGR (cc65), version Apple II

*[← dev](../../README.md)*

Le runtime C `gen2c` de [POM1](https://github.com/habib256/pom1)
(`dev/lib/gen2c`, VERHILLE Arnaud, GPL-3.0) pour la carte GEN2 d'Uncle Bernie,
adapté à l'Apple II. La GEN2 reprend la vidéo de l'Apple II : le dessin, les
tables et l'API sont les mêmes, les noms `gen2_*` sont gardés. Ce qui change :

- commutateurs en `$C050-$C057` (`gen2.h`, `gen2_blit.s` via
  `../apple2/hgr.asm`) ;
- pas de `gen2_wait_vbl` : un II/II+ n'a pas de V-blank (`gen2_init.c`,
  `gen2_sprengine.c`) ;
- base texte / clavier : [`../apple2c`](../apple2c/) au lieu d'`apple1c`.

Utilisé par [`../../../snake`](../../../snake/) et
[`../../../demos`](../../../demos/). Les fonctions de dessin vectoriel passent par
[`../gfx`](../gfx/).

## Familles de routines

Un programme serré peut laisser de côté ce qu'il n'appelle pas en recompilant la
bibliothèque avec des drapeaux `-D` (ld65 élimine par objet, et `gen2_blit.s` est
un seul objet). Sans drapeau, tout est présent.

| Drapeau | Retire |
|---|---|
| `HGRC_NO_TEXT16` | `gen2_hgr_puts`, `gen2_hgr_puts_color` (glyphes 16×16) |
| `HGRC_NO_TEXT8` | `gen2_hgr_puts8` (glyphes 8×8) |
| `HGRC_NO_UTOA` | conversion décimale (`gen2_hgr_putu*`) |
| `HGRC_NO_BLIT` | `gen2_hgr_blit` (blit au pixel près ; `blit7` reste) |
| `HGRC_NO_PRESHIFT` | `gen2_hgr_sprite`, `gen2_hgr_sprite_xor` |
| `HGRC_NO_PLOT` | `gen2_hgr_plot`, `gen2_hgr_unplot` |
| `HGRC_NO_PIXRECT` | `fill_pixrect`, `clear_pixrect`, `gen2_hgr_cell`, `hline`, `vline` |
| `HGRC_NO_COLORIZE` | `gen2_hgr_colorize` |
| `HGRC_NO_CIRCLE` / `HGRC_NO_ELLIPSE` | cercle / ellipse |

Un appel à une routine retirée donne une erreur d'édition de liens (pas un
plantage). Exemple complet : le `Makefile` de `../../../demos`, où ANIMALS
passe de 15,5 à 13,1 Ko.
