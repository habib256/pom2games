# lib/hgr — texte, sprites et tables HGR (asm)

*[← dev](../../README.md)*

Modules assembleur pour la vidéo HGR native de l'Apple II, dérivés de
[POM1](https://github.com/habib256/pom1) (GPL v3) : pages `$2000`/`$4000`,
entrelacement standard des lignes et couleurs NTSC.
Les commutateurs vidéo et l'initialisation sont dans
[`../apple2/hgr.asm`](../apple2/hgr.asm).

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
| `hgr_scanline.inc` | `hgr_lo` / `hgr_hi` : adresse de chaque ligne 0..191 | arkabreakout, chess, demos, logo, maze3d, micro-sokoban |
| `hgr_plot_tables.inc` | `hgr_col` / `hgr_mask` : octet et bit de chaque colonne 0..279 | logo |
| `hgr_clear.asm` | `clear_hgr` : efface `$2000-$3FFF` (`HGR_CLEAR_LOOP`, sans ZP) | demos (life), logo |
| `hgr_flip.asm` | `hgr_draw_hidden` / `hgr_show_draw` / `hgr_set_draw_page` : double tampon en réécrivant `hgr_hi` sur place (`hgr_scanline.inc` dans un segment modifiable) | maze3d, micro-sokoban |
| `hgr_text8.asm` | `hgr_putc8` / `hgr_puts8` : texte 8x8 aligné sur l'octet, couleurs. `HGR_TEXT8_HGR_ORDER` (police en ordre HGR : plus de `ht_rev` ni de `rev7_tab`, −256 o), `HGR_TEXT8_NO_PUTS` | arkabreakout, maze3d |
| `hgr_sprite16.asm` | `hgr_spr16_x1/_x2/_x4` : sprites TMS 16x16 convertis à l’exécution | ancien chemin TMS |
| `hgr_sprite_packed.asm` | `hgr_sprite_packed` : lignes HGR précompactées, répétition verticale et bord masqué | maze3d |
| `hgr_sprite_color.inc` | attributs de couleur partagés par les deux blitters | moteurs de sprites |
| `hgr_line.asm` | `hgr_line8` : ligne OR rapide, X natif 0..255, Y 0..191 | maze3d |
| `hgr_span.asm` | `hgr_hspan` / `hgr_vspan` : spans par colonnes et masques d’octets, largeur HGR complète | maze3d |
| `hgr_clear_rows.asm` | effacement de lignes visibles, écran, HUD et viewport 160 lignes | maze3d |
| `rev7.inc` | `rev7_tab` : ordre des bits TMS → HGR | hgr_text8, hgr_sprite16 |
| `sprites/chess_cc65_pieces.asm` | pièces d'échecs de cc65-Chess (F. Gebhart, O. Schmidt) | chess |

Le blitter TMS historique `hgr_sprite16.asm` rogne à la ligne 192 et à la
colonne d'octets 40. Une origine verticale hors écran ne reboucle pas en haut,
et les sprites au bord droit préservent les octets hors affichage.

`hgr_puts8` parcourt la chaîne jusqu'au NUL, même au-delà de 256 caractères.
Il préserve le pointeur source et X ; le curseur continue d'avancer après le
bas de l'écran, sans écrire hors du framebuffer.

La police Beautiful Boot (8x8) n'est plus ici : `.include "bbfont.inc"` depuis
[`../font`](../font/README.md), qui découpe la table maîtresse à la plage de
caractères voulue (`BBFONT_FIRST` / `BBFONT_LAST`).

Voir l'en-tête de chaque fichier pour l'API détaillée et la zéro-page qu'il
réserve.

Auteur : VERHILLE Arnaud. Licence : [GPL-3.0](../../../LICENSE).

## Primitives extraites de Maze3D

Les nouveaux modules utilisent `hgr_lo/hi` et suivent la page sélectionnée par
`hgr_flip.asm`. Le code et les tables doivent résider en RAM : lignes, spans
verticaux et effacement du viewport modifient leurs instructions. Les appels
ne sont pas réentrants. Les entrées sont supposées valides ; aucun clipping
implicite n’est ajouté. Les en-têtes précisent les bornes et registres détruits.

`hgr_line8` travaille en coordonnées HGR natives sur les 256 premiers pixels.
L’adaptation des coordonnées TMS et les marges restent dans Maze3D ; ce noyau
ne remplace pas l’API C `hgr_line` à 280 pixels. Les spans couvrent les 40
colonnes. L’effacement visible préserve les trous mémoire et l’autre page ;
la variante 160 lignes préserve aussi le HUD.

Le blitter précompacté reçoit une colonne d’octet, une ligne, un pointeur,
une largeur (1..10 octets), un nombre de lignes source, une répétition
verticale et le masque du dernier octet. Il écrase le fond dans le rectangle,
y compris les pixels noirs, et conserve les pixels après le bord final.
Les tailles, palettes et placements propres au jeu restent chez l’appelant.
`hgr_sprite_color.inc` partage seulement les attributs ; il n’impose ni
l’ancien blitter TMS, ni la table `rev7_tab`.

Chaque module alloue son scratch par défaut. Les alias décrits dans les
en-têtes permettent de réutiliser le scratch d’un appelant sans augmenter
sa zéro-page. Inclure uniquement les familles nécessaires après les appels.
Le packer correspondant est `dev/tools/assets/pack_hgr_sprites.py`.

Vérification autonome : `python3 dev/tests/test_hgr_native.py` depuis la
racine (également dans `make test-hgr`). Elle utilise les allocations de
scratch par défaut, teste les deux pages et le bord droit des spans, et
vérifie une décompression LZ4FH de 8192 octets. Les tests de Maze3D gardent
la couverture des sept tailles, de la visibilité et des scènes complètes.

Les deux blitters assembleur peuvent être inclus ensemble, dans n’importe
quel ordre : leurs variables `sp_*` communes sont réservées une seule fois.
Ils partagent ce scratch et les attributs de couleur, donc leurs appels sont
séquentiels. Le texte `hgr_putc8` coupe les glyphes partiels en bas de l’écran
et conserve une position hors écran lors du retour à la colonne initiale.
Les régressions correspondantes sont dans `test_asm_boundaries.py`.
