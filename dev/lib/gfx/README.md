# lib/gfx — géométrie commune (cc65)

*[← dev](../../README.md)*

La couche vectorielle de [POM1](https://github.com/habib256/pom1)
(`dev/lib/gfx`, GPL-3.0) : lignes, rectangles, cercles, ellipses et nombres, sur
un backend HGR ou DHGR. Le backend HGR (`gfx_backend_hgr*.c`) appelle
[`../hgrc`](../hgrc/). Les dimensions et couleurs dépendent du backend choisi.

À compiler avec `-I dev/lib/hgrc -I dev/lib/apple2c -I dev/lib/gfx`, de
préférence dans une archive `ar65` pour que seules les fonctions appelées soient
liées (voir le `Makefile` de `../../../demos`).

## Apple II DHGR

Deux backends explicites : `gfx_backend_dhgr_color.c` (140×192, couleur LORES
0..15) ou `gfx_backend_dhgr_mono.c` (560×192, bit 0/1). Lier exactement un
backend avec `HGRC_GENERIC_VECTOR_SRCS` et la bibliothèque DHGR. La couleur
courante se règle par `dhgr_set_color`. Les coordonnées sont celles du backend
choisi ; les blocs et sprites natifs gardent leur API propre dans `dhgr.h`.
Les rectangles sont inclusifs, triés et rognés avant le calcul de dimensions.

Auteur : VERHILLE Arnaud. Licence : [GPL-3.0](../../../LICENSE).

## Archive et texte

`HGRC_ALL_SRCS` inclut les conversions décimales et hexadécimales, `gfx_text.c`
et le backend texte HGR : `gfx_utoa`, `gfx_itoa`, `gfx_hexstr`, `gfx_gotoxy`,
`gfx_text`, `gfx_putu`, `gfx_puti` et `gfx_putx` se lient sans ajout manuel.
Le texte utilise une grille HGR 35×24 de glyphes blancs 8×8 sur la page de
dessin courante. Les appels passent à la ligne au bord droit ; la dernière
ligne ne défile pas. `gfx_cell_color` est sans effet avec ce backend.
Il n’existe pas de backend texte par cellules DHGR ; utiliser `dhgr_puts`.

`gfx_u16_digits` fournit cinq chiffres ASCII, avec zéros initiaux, pour une
valeur non signée de 0 à 65535. Son buffer statique est réutilisé au prochain
appel. Le noyau assembleur `gfx_u16_digits.s` est **réservé au 65C02** ; la
famille optionnelle `HGRC_65C02_NUM_SRCS` le sélectionne sans modifier les
conversions 6502 utilisées sur Apple II+. Il préserve les flags, notamment
les états des interruptions et du mode décimal.

Les segments diagonaux refusent les extrémités hors écran ; ils n’effectuent
pas de clipping de ligne complet. Les axes passent par les spans rognés. Les rectangles pleins trient et rognent
leurs coins ; les cercles rognent les points tracés. Un centre hors écran
reste accepté : les arcs proches du bord sont visibles, les cercles entièrement
à droite sont écartés avant la conversion signée des coordonnées sur 16 bits.
Les ellipses dont un rayon entier vaut zéro se réduisent à un segment ou
à un point dans leur boîte, sans déborder autour des formes très étroites.
Les boîtes entièrement à droite ou sous l’écran sont écartées avant le
calcul des points, sans tracer de ligne parasite sur le bord.
Les primitives HGR bas niveau peuvent avoir des largeurs sur 8 bits ;
`gfx_filled_rect` gère toute la largeur. Le choix du backend reste explicite
à la liaison.


L'archive HGR sélectionne `gfx_line_hgr.c` : les diagonales utilisent le noyau
assembleur 280 pixels de `hgr_line`. Le fallback C `gfx_line.c` reste destiné
aux backends génériques/DHGR. Ces deux fichiers définissent le même symbole :
choisir une implémentation à la liaison. Aucun pointeur de fonction n'est ajouté.
Les deux API HGR sont comparées sur 464 lignes ; le fallback est testé dans les
deux modes DHGR, sur les deux pages et banques, y compris les entrées refusées.
