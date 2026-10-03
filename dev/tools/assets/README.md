# Assets Apple II

Convertisseur sans dépendance Python externe : PNG 8 bits non entrelacé
(gris, RGB, palette ou RGBA) et PPM P3/P6. L’image doit tenir dans 280×192
pour HGR monochrome ou 140×192 pour DHGR couleur. Pas de redimensionnement
implicite. Alpha < 128 = transparent ; une image plein écran est composée
sur du noir. La conversion HGR est un seuil monochrome, sans palette
couleur ni dithering. DHGR choisit la couleur LORES la plus proche en RGB ;
les deux gris identiques sont représentés par le numéro 5.

```sh
python3 dev/tools/assets/convert.py image.png --mode dhgr --kind sprite --out build/ship --name ship
python3 dev/tools/assets/convert.py image.ppm --mode hgr --kind frame --out build/screen
```

## Sorties

| Fichier | Contenu |
|---|---|
| `.h` (sprite) | Constantes WIDTH/HEIGHT/STRIDE, tableaux `<name>_data` et `<name>_mask` |
| `.bin` (sprite) | Les sept banques de données, puis les sept banques de masques |
| `.bin` (image) | HGR : 8 Ko ; DHGR : 8 Ko principaux puis 8 Ko auxiliaires, adresses relatives à la page |
| `.png` | Aperçu quantifié ; les franges NTSC réelles dépendent du moniteur |
| `.json` | Dimensions, stride, ROM totale, masque et taille du buffer save-under |

Les tableaux ont sept banques `stride * hauteur` consécutives, pour les
phases 0..6. Chaque octet représente sept bits, bit 0 à gauche ; masque 1 =
conserver le décor. Les bords et la transparence sont masqués. Le bit 7 du
masque reste à 1 et celui des données à 0.

- HGR : créer `hgr_mspr_t {data, mask, stride, hauteur}` et l’utiliser dans
  l’API `hgr_spr_define` ; les banques simples conviennent à `hgr_sprite_t`.
- DHGR : passer WIDTH, HEIGHT, STRIDE et les deux tableaux à `dhgr_sprite`.
  x est un pixel **couleur** ; la routine choisit `(x * 4) % 7`.
- Une banque de phases dépassant 65 535 octets est refusée. Le budget réel
  de ROM du programme est généralement beaucoup plus petit ; consulter le JSON
  et découper les grandes images en tuiles.

Choisir un préfixe de sortie différent de l’image source pour conserver
l’original. Les déclarations des anciennes conversions ×2 de référence sont
dans `dev/lib/hgrc/hgr_host.h`, hors de l’API cible.

`make test-assets` vérifie les cinq filtres PNG, PPM, les dispositions des
framebuffers et les masques de toutes les phases. Le test DHGR utilise un
sprite produit par ce convertisseur et le compare au dessin attendu.
