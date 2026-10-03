# lib/gfx — géométrie commune (cc65)

*[← dev](../../README.md)*

La couche vectorielle de [POM1](https://github.com/habib256/pom1)
(`dev/lib/gfx`, GPL-3.0) : lignes, rectangles, cercles, ellipses et nombres, sur
un backend. Seul le backend HGR est repris (`gfx_backend_hgr*.c`, qui appelle
[`../hgrc`](../hgrc/)). Les algorithmes sont partagés avec les consommateurs du runtime HGR.

À compiler avec `-I dev/lib/hgrc -I dev/lib/apple2c -I dev/lib/gfx`, de
préférence dans une archive `ar65` pour que seules les fonctions appelées soient
liées (voir le `Makefile` de `../../../demos`).

## Apple II DHGR

Deux backends explicites : `gfx_backend_dhgr_color.c` (140×192, couleur LORES
0..15) ou `gfx_backend_dhgr_mono.c` (560×192, bit 0/1). Lier exactement un
backend avec les algorithmes partagés et la bibliothèque DHGR. La couleur
courante se règle par `dhgr_set_color`. Les coordonnées sont celles du backend
choisi ; les blocs et sprites natifs gardent leur API propre dans `dhgr.h`.
Les rectangles sont inclusifs, triés et rognés avant le calcul de dimensions.
