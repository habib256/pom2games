# lib/gfx — géométrie commune (cc65)

*[← dev](../../README.md)*

La couche vectorielle de [POM1](https://github.com/habib256/pom1)
(`dev/lib/gfx`, GPL-3.0) : lignes, rectangles, cercles, ellipses et nombres, sur
un backend. Seul le backend HGR est repris (`gfx_backend_gen2*.c`, qui appelle
[`../hgrc`](../hgrc/)). Les fichiers sont inchangés.

À compiler avec `-I dev/lib/hgrc -I dev/lib/apple2c -I dev/lib/gfx`, de
préférence dans une archive `ar65` pour que seules les fonctions appelées soient
liées (voir le `Makefile` de `../../../demos`).
