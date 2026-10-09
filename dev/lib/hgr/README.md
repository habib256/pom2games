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
| `hgr_plot_tables.inc` | `hgr_col` / `hgr_mask` : octet et bit des colonnes 0..255, ou 0..279 avec `HGR_FULL_WIDTH_TABLES=1` | logo |
| `hgr_clear.asm` | `clear_hgr` : efface `$2000-$3FFF` (`HGR_CLEAR_LOOP`, sans ZP) | demos (life), logo |
| `hgr_flip.asm` | `hgr_draw_hidden` / `hgr_show_draw` / `hgr_set_draw_page` : double tampon en réécrivant `hgr_hi` sur place (`hgr_scanline.inc` dans un segment modifiable) | maze3d, micro-sokoban |
| `hgr_text8.asm` | `hgr_putc8` / `hgr_puts8` : texte 8x8 aligné sur l'octet, couleurs. `HGR_TEXT8_HGR_ORDER` (police en ordre HGR : plus de `ht_rev` ni de `rev7_tab`, −256 o), `HGR_TEXT8_NO_PUTS` | arkabreakout, maze3d |
| `hgr_sprite16.asm` | `hgr_spr16_x1/_x2/_x4` : sprites TMS 16x16 convertis à l’exécution | ancien chemin TMS |
| `hgr_sprite_packed.asm` | `hgr_sprite_packed` : lignes HGR précompactées, répétition verticale et bord masqué | maze3d |
| `hgr_sprite_color.inc` | attributs de couleur partagés par les deux blitters | moteurs de sprites |
| `hgr_plot.asm` | `hgr_plot16` : pixel OR/XOR avec clipping, X 16 bits, palette optionnelle | logo |
| `hgr_line16.asm` | `hgr_line16` : Bresenham avec X signé 16 bits, raster historique LOGO | logo |
| `hgr_xor.asm` | rectangles natifs et glyphes précalés XOR, double tampon chez l’appelant | arkabreakout |
| `hgr_sprite_update.asm` | `ds_present` / `ds_hide` : sprite transparent par octets, sauvegarde et restauration du fond | logo |
| `hgr_line.asm` | `hgr_line8` : ligne OR rapide, X natif 0..255, Y 0..191 | maze3d |
| `hgr_span.asm` | `hgr_hspan` / `hgr_vspan` : spans par colonnes et masques d’octets, largeur HGR complète | maze3d |
| `hgr_wireframe.asm` | contours découpés en X, historique par page et effacement rapide des anciens traits en noir | light3dball |
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
y compris les pixels noirs, et conserve les pixels après le bord final,
même si les bits de remplissage de la source sont non nuls.
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
Les régressions correspondantes sont dans `test_asm_boundaries.py` : les
bords des sprites couvrent 256 combinaisons de pages, largeurs, parités,
palettes, couleurs, fonds et bits de remplissage.

## Contours en fil de fer

`hgr_wireframe.asm` dessine des traits horizontaux et verticaux blancs, puis
efface les anciens traits en noir. Il ne remplit aucun rectangle. Les spans
horizontaux effacent directement les octets complets par une suite de stores
déroulée ; les masques des extrémités préservent les pixels voisins.

Inclure `hgr_scanline.inc` et `hgr_plot_tables.inc`, puis le module, dans un
segment modifiable. Il inclut lui-même `hgr_span.asm`. Chaque appel utilise
la page désignée par `hgr_lo/hi`, compatible avec `hgr_flip.asm`.

| Entrée | Paramètres et effet |
|---|---|
| `hgr_wire_span` | `wf_x0/y0/x1/y1` : dessiner un trait sans découpage ni historique |
| `hgr_wire_line` | Dessiner un trait limité à `wf_clip_left..wf_clip_right`, puis avancer `wf_history` de quatre octets s'il est visible |
| `hgr_wire_rect` | Soumettre les quatre côtés du rectangle au même découpage et au même historique |
| `hgr_wire_erase` | `wf_history` au début de l'ancien historique, `wf_count` traits : les effacer, avancer le pointeur et ramener le compte à zéro |
| `hgr_wire_clear_span` | Effacer un seul trait, sans historique |

Les coordonnées doivent être ordonnées et valides : X 0..255, Y 0..191 ;
seuls les traits horizontaux et verticaux sont acceptés. Le découpage est
horizontal, sans bord supplémentaire à la limite de visibilité. Une fenêtre
avec gauche > droite ne dessine rien. Les rectangles dégénérés sont acceptés,
avec éventuellement plusieurs enregistrements du même trait.

L'appelant réserve quatre octets par trait visible, soit jusqu'à seize par
rectangle, et calcule le nombre de traits par `(pointeur_final-début)/4`.
Le module ne vérifie pas la capacité du tampon. Garder un historique séparé
pour chaque page : restaurer les sprites, effacer l'ancien historique de la
page de dessin, remettre le pointeur au début, puis dessiner les nouveaux
contours. La projection, l'ordre des objets et la mise à jour de la fenêtre
de visibilité restent chez l'appelant.

Le fond est monochrome ; les octets horizontaux complets réinitialisent le
bit de phase couleur. Pour réparer un décor fixe croisé par un ancien trait,
définir `HGR_WIRE_AFTER_HLINE` et/ou `HGR_WIRE_AFTER_VLINE` avant l'inclusion.
Ces routines sont appelées après l'effacement avec les extrémités dans
`wf_x0/y0/x1/y1` et doivent préserver `wf_history` et `wf_count`.
Light3dball utilise ces hooks pour restaurer les arêtes fixes du couloir.

Le module réserve son scratch par défaut ; des alias `wf_*` peuvent le
remplacer avant l'inclusion. `WF_COL_TABLE` et `WF_MASK_TABLE` permettent
de réutiliser d'autres tables X. Tous les appels détruisent A/X/Y et le
scratch ; le code est non réentrant et n'attend pas la synchronisation vidéo.

`python3 dev/tests/test_hgr_wireframe.py` vérifie le module seul sur les deux
pages, avec son scratch par défaut, des historiques traversant une frontière
de page, des bords, des fenêtres vides et des rectangles dégénérés. Chaque
octet du framebuffer est comparé à une référence après dessin et effacement.
Ce test fait aussi partie de `make test-hgr`.

## Noyaux natifs utilisés par LOGO

`hgr_plot16` accepte X sur 16 bits (0..279 à l'écran) et Y sur 8 bits.
Les pixels hors écran sont ignorés avant tout accès aux tables. `hp_mode=0`
compose par OR ; les autres valeurs utilisent XOR, sans modifier le bit 7.
Le mode OR préserve aussi ce bit, sauf si `HP_COLOR_TABLE` est défini :
`hp_color` indexe alors la table de palette fournie par l'appelant.
Le hook optionnel `HP_OR_PLOT`, appelé avec A = octet composé et Y = colonne
mémoire, peut adapter A avant l'écriture ; il doit préserver Y et le scratch
`hp_*`. LOGO l'utilise pour dessiner les traits sous le sprite visible.

`hgr_line16` reçoit `h16_x0/y0` et `h16_x1/y1`. X est signé sur 16 bits,
Y non signé sur 8 bits, avec `|dx| <= 511`. Le raster conserve les égalités
historiques LOGO : pas X si `2*err >= -dy`, pas Y si `2*err < dx`.
Les extrémités et le scratch sont modifiés. `HGR_LINE16_PLOT` permet de
remplacer le plotter ; les alias `hp_*` et `h16_*` réutilisent le scratch
existant. Inclure les tables avec `HGR_FULL_WIDTH_TABLES=1` pour ces noyaux.

Le compositeur `hgr_sprite_update.asm` gère un sprite transparent, sur la
page désignée par `hgr_lo/hi`. Après `ds_init`, fournir `ds_col/y/w/h` :
colonne d'octet 0..39, ligne 0..191, largeur 1..6, hauteur 1..32, rectangle
entièrement dans l'écran. `ds_data` pointe vers des lignes de **six octets**,
avec le bit 7 toujours nul. `ds_color=0` conserve la palette du fond ;
`ds_color=1` applique `ds_palette` (0 ou 128) aux octets ayant du premier plan.
La composition utilise OR, et non XOR : un fond allumé ne troue pas le sprite.

`ds_present` conserve deux tampons de fond de 192 octets. Il rend un octet
allumé de la nouvelle image visible avant de retirer les anciens pixels,
compose directement le recouvrement, puis restaure le fond quitté. Un
rectangle identique utilise une boucle spécialisée. `ds_hide` restaure le
fond ; après un effacement externe, appeler `ds_init` pour invalider la
sauvegarde. Le moteur réserve huit octets de ZP ; il est non réentrant et
détruit A/X/Y. Le masque actif doit rester disponible entre les présentations.
Les écritures externes sous le sprite doivent mettre à jour le fond sauvegardé,
ou masquer le sprite avant ces écritures puis le présenter à nouveau.

Ce chemin évite la phase où le sprite était entièrement effacé. Il travaille
sur une seule page, sans synchronisation VBL : une déchirure pendant le balayage
reste possible. LOGO conserve ainsi son interpréteur en page HGR 2 et sa
console 80 colonnes, sur II+ comme IIe.

`test_hgr_logo.py` compare les lignes et pixels à une référence, avec le
scratch par défaut et l'adaptateur LOGO. `test_hgr_sprite_update.py` vérifie
les fonds colorés, le recouvrement, les transitions sans image vide,
l'effacement, les trous HGR et l'autre page. Ces tests font partie de
`make test-hgr` ; `make -C logo test` vérifie aussi les commandes réelles.

## Glyphes natifs sans curseur

`hgr_glyph8.asm` est le noyau utilisé par CHESS, LOGO et MICRO-SOKOBAN.
Il lit huit lignes à `hg_src` (pointeur ZP, bit 0 à gauche) et utilise
`hgr_lo/hi` pour la page cible. Ses entrées ne déplacent aucun curseur :

| Entrée | Coordonnées | Écriture |
|---|---|---|
| `hgr_glyph8_store` | `hg_col` : octet 0..39 ; `hg_y` : ligne | Un octet brut par ligne, palette comprise |
| `hgr_glyph8_or` | `hg_x` : pixel 16 bits 0..279 ; `hg_y` : ligne | Ajoute seulement les pixels allumés |
| `hgr_glyph8_cell` | mêmes coordonnées | Remplace une cellule de huit pixels, efface sa palette, conserve les pixels voisins |

Les huit bits de la source sont pris en compte, y compris le huitième pixel
dans l'octet suivant. Les entrées rejettent les coordonnées hors écran et
tronquent à droite/en bas sans retour en début de ligne. Source et coordonnées
sont préservées ; A/X/Y et le scratch sont détruits. Le module est non réentrant,
nécessite D=0 et ne touche aucun commutateur vidéo. Les alias `hg_*` permettent
de réutiliser le scratch du logiciel.

`HG_COLOR_TABLE[hg_color]` remplace la palette des seuls octets allumés en OR.
`HG_OR_HOOK` reçoit et retourne A=octet écran, Y=colonne d'octet ; il préserve
Y et `hg_*`. `HG_HOOK_Y` et `HG_HOOK_MASK` reçoivent la ligne et le masque
allumé. LOGO utilise ce crochet pour conserver le texte tracé sous une émote.
Sans table de couleur, OR préserve la palette existante.

`HG_STORE_ONLY` omet les entrées non alignées. `HG_STORE_UNCLIPPED` supprime
les contrôles de STORE : l'appelant garantit alors `hg_col<40`, `hg_y<=184`.
CHESS et les titres de MICRO-SOKOBAN utilisent ce contrat pour leur UI fixe.
CELL et OR restent toujours tronqués.

`test_hgr_glyph8.py` couvre les deux pages, les sept alignements, les palettes,
les cellules vides et les bords. `test_logo_glyphs.py` contrôle l'adaptateur
réel et ses caractères ; les tests LOGO vérifient aussi le texte sous un sprite.

## Rectangles et glyphes XOR natifs

`hgr_xor.asm` travaille sur les tables de lignes de la page 1 et reçoit
`hx_page = 0` pour `$2000`, ou `$60` pour `$4000`. Définir
`HGR_XOR_DIV7` et `HGR_XOR_MOD7` comme alias des tables X de 256 octets.

- `hgr_xor_rect` : `hx_x/y/w/h` en pixels, largeur et hauteur non nulles,
  `x+w <= 256`, `y+h <= 192`.
- `hgr_xor_sprite` : `hx_x/y` et `hx_data`, huit lignes de deux octets dont
  le bit 7 est nul. Le pointeur vise la variante déjà précalée selon `x % 7`.
  Les deux octets destination doivent rester dans les 40 colonnes visibles.

Les noyaux préservent le bit de phase couleur du fond. Dessiner deux fois le
même objet restaure exactement les octets initiaux. Ils détruisent A/X/Y et
leur scratch, et ne font ni clipping ni synchronisation vidéo. Pour un jeu,
conserver l’historique de chaque page, effacer tous les objets avant de
modifier le décor, puis dessiner la nouvelle scène sur la page cachée.
`dev/tests/test_hgr_xor.py` vérifie le raster, les sept alignements, les deux
pages, les extrémités et la restauration intégrale, trous mémoire compris.

Pour un HUD incrémental avec `hgr_text8.asm`, définir `HGR_TEXT8_FILTER` comme
l’adresse d’un callback. Il lit `ht_a/ht_col/ht_sl/ht_page` avant le tracé :
C=1 ignore le glyphe mais avance le curseur ; C=0 dessine normalement. A/X/Y
sont libres, `ht_a`, le curseur, la police et les attributs doivent être
préservés. Le callback d’Arkabreakout compare les caractères à un cache
indépendant pour chaque page, invalidé à chaque effacement de l’écran.
