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

## Sprites TMS précompactés pour HGR (assembleur)

`pack_hgr_sprites.py` transforme des motifs TMS 16×16 (32 octets, colonne
gauche puis droite, bit 7 à gauche) en sept tailles : 8, 16, 32, 64, 4, 2 et
1 pixels. Le fichier ca65 produit contient les pointeurs et les tables
`_width`, `_height`, `_source_rows`, `_vertical` et `_last_mask`.
Les lignes répétées verticalement ne sont stockées qu’une fois ; les petites
tailles utilisent le maximum des blocs source pour conserver les silhouettes.

```sh
python3 dev/tools/assets/pack_hgr_sprites.py --out build/ship.inc --prefix ship art.asm:ship_pattern
```

Le runtime `dev/lib/hgr/hgr_sprite_packed.asm` dessine ces données sur une
colonne HGR alignée à l’octet. Ce format ne contient pas les sept phases du
convertisseur PNG/PPM : choisir le runtime correspondant au format produit.
Les crédits des motifs restent dans leurs sources originales.

## Compression HGR LZ4FH

Inclure `dev/cc65/fhpack.mk` après `apple2.mk` pour disposer de la cible
`$(FHPACK)` (compilateur C++ requis). Les sources et licences amont restent
épinglées dans `dev/tests/techniques/upstream/fhpack`.

```sh
build/fhpack -c -9 -h title.hgr build/title.lz4fh
build/fhpack -d build/title.lz4fh build/title.roundtrip.hgr
cmp title.hgr build/title.roundtrip.hgr
```

Conserver `-h` pour restituer aussi les trous de la page HGR. La décompression
6502 partagée se trouve dans `dev/lib/apple2/lz4fh.asm`. La limite du tampon
compressé, le chargement disque et les adresses restent propres au programme.

Le convertisseur propose la sélection automatique pour les images HGR :

```sh
python3 dev/tools/assets/convert.py title.png --mode hgr --kind frame \
    --out build/title --fhpack build/fhpack
```

Le `.bin` brut est conservé. `.load.bin` contient le flux LZ4FH uniquement
s'il est plus petit ; sinon il contient le brut. Le JSON indique `load_file`,
`load_encoding` (`lz4fh` ou `raw`) et `load_bytes`. Chaque compression est
décompressée et comparée aux 8 192 octets d'origine avant sélection. Cette
option refuse les sprites et DHGR : le décodeur cible travaille sur une page
HGR de 8 Ko alignée. Le chargeur applicatif choisit son tampon source et
ne doit appeler le décodeur que pour `load_encoding=lz4fh`.

## Tables HGR communes

`dev/tools/hgr_tables.py` fournit `hgr_offset(y)`, `scanline_tables(page)`,
`division_tables(width)` et `shift_tables()`. Le convertisseur PNG/PPM,
le harnais `a2test` et le constructeur Pinball partagent le calcul des
adresses HGR. Les tables de décalage contiennent six phases de 256 entrées,
avec conservation du bit de palette et suppression des octets `$80` isolés,
selon le contrat PCS. Le placement des tables dans la mémoire du jeu reste
chez l’appelant.
