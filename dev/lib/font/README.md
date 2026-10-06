# lib/font — la police Beautiful Boot, une seule source

*[← dev](../../README.md)*

Tous les programmes du dépôt écrivent avec la même police 8x8 de Michael
Pohoreski (Beautiful Boot, `apple2_hgr_font_tutorial`), complétée par les
symboles CP437. Elle n'existe qu'une fois, dans `bbfont_glyphs.inc` ; tout le
reste en est découpé ou dérivé automatiquement.

| Fichier | Rôle |
|---|---|
| `bbfont_glyphs.inc` | **maîtresse** : 256 glyphes, une ligne `bbglyph code, 8 octets` chacun. Bit 0 = pixel de gauche, 8 lignes de haut en bas, bit 7 toujours à 0 (7 px de large). C'est le seul fichier à éditer. |
| `bbfont.inc` | asm : `.include` après avoir choisi `BBFONT_FIRST` / `BBFONT_LAST` ; émet la table `bbfont`, `BBFONT_COUNT` et `BBFONT_BYTES_PER_GLYPH` dans le segment courant. |
| `bbfont_c.inc` | C : les 96 glyphes ASCII `$20-$7F`, générés — c'est `hgr_font[]` de `lib/hgrc` (`hgr_font.c`). |
| `../../tools/fonts.py` | Python : `glyph()`, `glyphs()`, `double7()` (x2 HGR), `dhgr_cells()`, `asm_bytes()`, `write_if_changed()` ; en ligne de commande, régénère les tables dérivées (`--check` en test). |

## Quelle police, dans quelle situation

| Situation | À utiliser | Coût mémoire |
|---|---|---|
| asm, texte HUD majuscules et chiffres (le cas courant) | `.include "bbfont.inc"` tel quel : ASCII `$20-$5F`, puis `hgr_text8.asm` (`ht_font_lo/hi = bbfont`) ou une boucle STA de 8 lignes comme `chess` | 512 o |
| asm, avec minuscules | `BBFONT_LAST = $7F` avant l'include | 768 o |
| asm, n'importe quel code (LOGO, démo FONT) | `BBFONT_FIRST = $00`, `BBFONT_LAST = $FF` | 2 Ko |
| asm, résident serré : seulement les glyphes imprimés | un générateur Python par jeu qui pioche dans `fonts.glyph()` et émet ses propres indices, comme `micro-sokoban/tools/hud_font.py` (45 glyphes, 360 o) | ~8 o/glyphe |
| C, HGR | `hgr_puts8` (8x8 natif, blanc) ou `hgr_puts` / `hgr_puts_color` (16x16) de [`lib/hgrc`](../hgrc/README.md) : `hgr_font[]` est tiré de `bbfont_c.inc` | 768 o, lié à la demande |
| C, DHGR | `dhgr_puts` (mêmes glyphes, cellules blanches) ou `dhgr_small` (police compacte 4x5, propre à DHGR, `lib/hgrc/dhgr_small_font.inc`) | 768 o / 1,6 Ko |
| DHGR, texte fin double-largeur | plans générés par `chromabreak/tools/generate_fine_font.py` à partir de `fonts.glyph()` | 448 o |
| titres x2 ou chiffres précalculés | `fonts.double7()` (ex. `arkabreakout/tools/generate_title.py`), `fonts.dhgr_cells()` (`dev/examples/dhgr/src/digits.inc`) | selon le texte |

Règle d'interface, rappelée dans [`lib/hgr`](../hgr/README.md) : le texte à taille
normale reste blanc ; seul le texte x2 peut être coloré.

## Modifier un glyphe

1. Éditer la ligne `bbglyph` dans `bbfont_glyphs.inc`.
2. `python3 dev/tools/fonts.py` régénère `bbfont_c.inc` et `dev/examples/dhgr/src/digits.inc` ;
   `make` relance les générateurs des jeux (titre ARKABREAKOUT, police fine
   CHROMABREAK, sous-ensemble MICRO-SOKOBAN) dont les Makefiles dépendent de la
   maîtresse.
3. `make test-assets` (dans `make test`) échoue si une table dérivée est en retard.

Maze3D garde sa propre police 8 px (ordre de bits TMS9918, `maze3d/src/maze3d.s`,
`font_base`) : c'est un choix graphique du jeu, pas une copie de Beautiful Boot.

Auteur : VERHILLE Arnaud. Licence : [GPL-3.0](../../../LICENSE). Glyphes
Beautiful Boot : Michael Pohoreski.
