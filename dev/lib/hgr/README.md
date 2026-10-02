# lib/hgr — texte, sprites et tables HGR (asm)

*[← dev](../../README.md)*

Modules HGR repris **sans modification** de `dev/lib/gen2` de
[POM1](https://github.com/habib256/pom1) (GPL v3). La carte GEN2 d'Uncle Bernie
est le sous-système vidéo de l'Apple II transplanté sur le bus Apple-1 : même
mémoire `$2000`/`$4000`, même entrelacement des lignes, mêmes couleurs NTSC.
Ces fichiers ne touchent aucun commutateur, ils tournent donc tels quels sur un
Apple II ; leurs commentaires parlent encore de GEN2. Les commutateurs vidéo et
l'initialisation sont dans [`../apple2/hgr.asm`](../apple2/hgr.asm).

**Règle impérative pour le texte d'interface : seuls les caractères agrandis
×2 peuvent être colorés. Tout texte à taille normale (×1), y compris les chiffres,
commandes et curseurs de menu, doit rester blanc.** Le passage du blanc à une
couleur HGR masque une partie des traits du petit glyphe et réduit sa lisibilité.
Pour `hgr_putc8` / `hgr_puts8`, utiliser les attributs blancs
`ht_cm_ev = $7F`, `ht_cm_od = $7F`, `ht_cbit = $00`.
Garder une marge noire autour du texte inséré dans un décor coloré pour éviter
les franges de couleur aux bords. Cette règle concerne le texte ; les sprites,
murs, caisses et autres éléments graphiques conservent leurs couleurs.

| Fichier | Contenu | Utilisé par |
|---|---|---|
| `hgr_scanline.inc` | `hgr_lo` / `hgr_hi` : adresse de chaque ligne 0..191 | chess, maze3d, logo |
| `hgr_plot_tables.inc` | `hgr_col` / `hgr_mask` : octet et bit de chaque colonne 0..279 | logo |
| `hgr_clear.asm` | `clear_hgr` : efface `$2000-$3FFF` (ZP `ptr_lo/hi`) | chess |
| `hgr_text8.asm` | `hgr_putc8` / `hgr_puts8` : texte 8x8 aligné sur l'octet, couleurs | maze3d |
| `hgr_sprite16.asm` | `hgr_spr16_x1/_x2/_x4` : sprites 16x16 format TMS9918, couleurs | maze3d |
| `rev7.inc` | `rev7_tab` : ordre des bits TMS → HGR | hgr_text8, hgr_sprite16 |
| `bbfont_ascii5f.inc` | police Beautiful Boot 8x8, ASCII `$20-$5F` | chess |
| `bbfont_cp437.inc` | police Beautiful Boot 8x8 complète (CP437, 256 glyphes) | logo |
| `sprites/chess_cc65_pieces.asm` | pièces d'échecs de cc65-Chess (F. Gebhart, O. Schmidt) | chess |

Voir l'en-tête de chaque fichier pour l'API détaillée et la zéro-page qu'il
réserve.
