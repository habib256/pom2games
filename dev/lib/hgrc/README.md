# lib/hgrc — runtime C HGR (cc65), version Apple II

*[← dev](../../README.md)*

Runtime C pour la vidéo HGR native de l'Apple II, dérivé de
[POM1](https://github.com/habib256/pom1) (Arnaud Verhille, GPL-3.0).
L'API est déclarée dans `hgr.h` : fonctions `hgr_*`, constantes `HGR_*`.
Les commutateurs sont en `$C050-$C057`, les pages en `$2000` et `$4000`.
La base texte/clavier est [`../apple2c`](../apple2c/).

Utilisé par [`../../../snake`](../../../snake/) et
[`../../../demos`](../../../demos/). Les fonctions de dessin vectoriel passent par
[`../gfx`](../gfx/).

**Règle impérative : texte ×1 toujours blanc ; seule l'écriture agrandie ×2
peut être colorée.** Employer `hgr_puts8` pour le petit texte blanc et réserver
`hgr_puts_color` aux titres ×2. La coloration des petits glyphes supprime
des traits et dégrade leur lisibilité. Prévoir une marge noire si le texte
voisine avec un décor coloré. Voir aussi la règle dans [`../hgr`](../hgr/README.md).

## Compilation par archive

Les noyaux assembleur sont séparés : initialisation, effacement, rectangles
en octets, rectangles en pixels, cellules, pixels, texte ×1, texte ×2,
conversion décimale, sprites bitmap, sprites alignés et sprites prédécalés.
Les wrappers C suivent le même découpage. La police et les paramètres
partagés sont définis une seule fois dans leurs propres objets.

Compiler `HGRC_ALL_SRCS` dans une archive `ar65`, puis lier le programme à
cette archive. `ld65` extrait uniquement les objets nécessaires : les familles
inutilisées n'occupent ni code ni page zéro. Les drapeaux d'exclusion par
programme ont été supprimés. Les trois démos C partagent une seule archive.
Un lien direct de tous les `.o` embarquerait au contraire toutes les familles.

Trois objets portent les commutateurs de mode : `hgr_mode_asm.s` (toujours lié :
`hgr_init`, `hgr_text_restore`, `hgr_flip_rows`), `hgr_mode_clear_asm.s`
(`hgr_init_clear`) et `hgr_lores_init_asm.s` (`hgr_lores_init`). Un programme ne
paie que les points d'entrée qu'il appelle.

Coûts mesurés par `make bench` (cycles à 1,02 MHz) : effacement d'une page
51 000 (boucle auto-modifiée de `HGR_CLEAR_LOOP`, lib/apple2), basculement de
page 3 400 (`hgr_flip_rows` : un EOR par ligne au lieu d'une boucle C), texte
8x8 `hgr_puts8` ~9 000 pour « APPLE II » (glyphe décalé en deux octets par
ligne), texte 16x16 `hgr_puts` par le blitter couleur avec les porteuses
blanches `$7F/$7F` (un seul blitter, ~5 fois plus rapide que l'ancien tracé
pixel par pixel). Les enveloppes C lisent `hgr_col7` / `hgr_phase7` /
`hgr_mask7` au lieu de diviser par 7, et les tables de lignes se calculent
sans multiplication.

## Intégration

Définir `HGRC`, `GFX`, `APPLE2C` et `BUILD`, puis inclure `hgrc.mk` et
`../apple2c/apple2c.mk`. Les règles communes de `hgrc_build.mk` construisent
`$(BUILD)/hgrc/hgrc.lib`. Exemple :

```make
HGRC := $(DEV)/lib/hgrc
GFX := $(DEV)/lib/gfx
APPLE2C := $(DEV)/lib/apple2c
BUILD := build
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS)

all: $(BUILD)/game.bin

# Fournir les règles de compilation de crt0_apple2.o et main.o.
$(BUILD)/game.bin: $(BUILD)/crt0_apple2.o $(BUILD)/main.o $(HGRC_LIB)
	$(CL65) -t none -C $(DEV)/cc65/apple2_hgr_c.cfg -o $@ $^

# Après la première cible, pour conserver « all » comme cible par défaut.
include $(HGRC)/hgrc_build.mk
```

`HGRC_BUILD`, `HGRC_CFLAGS` et `HGRC_ASMFLAGS` sont personnalisables.
Les listes `HGRC_*_SRCS` restent disponibles pour construire une archive
avec un sous-ensemble de familles. Voir les Makefiles de Snake et des démos.

## Taille mesurée

Comparaison avant découpage / état actuel, avec cc65 2.18 et `-Oirs`, sur
les mêmes sources de jeux. L’état actuel inclut les transitions vidéo IIe. La page zéro inclut le runtime C du programme.

| Programme | Binaire avant → après | Page zéro avant → après |
|---|---:|---:|
| Snake | 10 218 → 8 674 octets | 99 → 81 octets |
| Bounces | 12 263 → 11 508 octets | 99 → 80 octets |
| Animals | 13 139 → 13 215 octets | 99 → 51 octets |
| Preshift | 4 611 → 4 446 octets | 99 → 60 octets |

Animals gagne surtout de la page zéro ; son binaire augmente de 76 octets,
avec le contrôle d'abscisse et la restauration des commutateurs vidéo IIe. Les autres programmes
bénéficient aussi de l'exclusion de routines jusque-là liées inutilement.

## Limites et vérification

- `gfx_filled_rect` accepte deux coins inclusifs, les remet dans l'ordre,
  les rogne à 280×192 et découpe les largeurs dépassant 255 pixels.
- `hgr_fill_pixrect` / `hgr_clear_pixrect` conservent une largeur sur 8 bits ;
  zéro ne dessine rien. Ces fonctions remettent le bit de palette à zéro
  dans les octets touchés, même aux bords du rectangle.
- `hgr_colorize` et `hgr_blit7` rejettent les abscisses hors écran avant
  toute conversion en colonne sur 8 bits.

`make test-hgr` compile et exécute les routines dans **a2run**, sous Linux et
macOS. Les 21 étapes comparent les deux pages vidéo avec un modèle Python :
rectangles 256/280 pixels, limites, pixels, sprites SET/CLEAR/XOR et sept
phases, texte blanc/coloré, nombres, cellules, coloration. Quatre scènes supplémentaires vérifient le texte par cellules `gfx` sur
la page 2, le curseur et les conversions numériques. Sept programmes
minimaux vérifient aussi que l'archive exclut les noyaux et blocs de page zéro
inutilisés. Ce test fait partie de `make test` et de la CI.

L’agrandissement de sprites ×2 (`hgr_x2.c`) est une référence pour les outils
hôtes ; le noyau assembleur cible n’est pas fourni. Préparer les banques
×2 avant compilation, comme `demos/src/animals_gen_x2.py`.

## DHGR (Apple IIe / IIc)

L’API [`dhgr.h`](dhgr.h) fournit les points 560×192, les couleurs 140×192,
les segments, rectangles, transferts de blocs, sprites masqués et texte blanc.
Les objets DHGR sont dans `HGRC_ALL_SRCS` et l’archive ; ils ne sont extraits
que lorsqu’une fonction DHGR est appelée. On peut aussi lier
`HGRC_DHGR_SRCS` directement. Le calcul des adresses de lignes est partagé
avec HGR dans `hgr_layout.h`.

- `dhgr_capabilities()` : bits `DHGR_CAP_EXTENDED` et `DHGR_CAP_AUX_VIDEO`.
  Le sondage conserve l’affichage et les octets utilisés dans les trous vidéo.
- `dhgr_init()` : retourne 1 si le modèle ROM et la RAM auxiliaire conviennent,
  0 sinon. Un II/II+ est refusé sans toucher aux commutateurs IIe.
  La révision B et le cavalier DHGR d’un IIe ne sont pas détectables en logiciel.
- `dhgr_draw_page(1/2)` et `dhgr_show_page(1/2)` sont indépendants.
  `dhgr_flip()` affiche la page de dessin et choisit l’ancienne page affichée
  pour le dessin suivant. La synchronisation VBL appartient à l’appelant.
- `dhgr_read_block` / `dhgr_write_block` : coordonnées en octets entrelacés
  0..79, ordre auxiliaire/principal ; `stride >= width`. Les parties hors
  écran ne sont pas transférées. Le buffer appartient à l’appelant.
- `dhgr_sprite` : x en **pixels couleur**, banques précalculées pour les sept
  décalages de bits, masque 1 = conserver le décor. Chaque banque contient
  `stride * hauteur` octets. Sauver puis restaurer un bloc permet le save-under.
- `dhgr_puts` : texte opaque blanc/noir, glyphes 8×8 **pixels couleur**,
  quatre bits DHGR par point de police, pour éviter une teinte d’artifact.
- `dhgr_puts_small` (famille optionnelle `HGRC_DHGR_SMALL_TEXT_SRCS`) : petite police opaque blanche, glyphes **4×5 pixels
  couleur**, avance de cinq colonnes. Accepte tous les alignements DHGR,
  convertit les minuscules en majuscules et conserve les pixels voisins.
  Une cellule incomplète au bord droit ou inférieur n’est pas dessinée.
- `dhgr_small_char` : même police, un caractère par appel rapide ; renseigner
  `dhgr_small_x` et `dhgr_small_y` pour un bandeau mis à jour progressivement.
  Les accès auxiliaires sont brefs et préservent l’état des interruptions.
  Par défaut, les tables sont liées avec la bibliothèque. L’option assembleur
  `DHGR_SMALL_FONT_EXTERNAL=1` permet de les reloger à `$0800` (ou à
  `DHGR_SMALL_FONT_BASE`) : l’application doit alors y copier les **1 653 octets**
  de données avant le rendu. `dev/tools/build_dhgr_font.py --out font.bin`
  produit une image de 2 Ko prête à charger ; `--base` et `--capacity` permettent
  de choisir son emplacement et sa taille. La base doit correspondre à celle
  utilisée pour assembler le moteur.
- `dhgr_small_string` : chaîne rapide aux coordonnées `dhgr_small_x/y`, utilisée
  aussi par `dhgr_puts_small`. L’option assembleur `DHGR_SMALL_USE_PROGRESS=1`
  appelle le point d’entrée applicatif `dhgr_small_progress` entre les caractères
  pour suivre la VBL ; ce callback doit préserver `ptr4`. Aucun callback n’est
  requis par défaut. L’appel caractère seul reste indépendant de ce suivi.

`dhgr_small_font` expose les glyphes pour les titres agrandis : 64 caractères
ASCII à partir de 32, six octets par glyphe (`DHGR_SMALL_FONT_STRIDE`). Les
constantes `DHGR_SMALL_ADVANCE` et `DHGR_SMALL_HEIGHT` décrivent la cellule.
Les tables `dhgr_row_lo/hi` et `dhgr_color_byte` peuvent être partagées avec un
moteur de sprites ; les deux tables de lignes sont contiguës et les indices de
colonnes incluent la borne 140. `dhgr_small_layout.inc` définit leur disposition
avec des assertions d’assemblage, et `dhgr_layout.inc` centralise les formules
d’adressage et de masquage.

Les objets DHGR sont séparés pour que l’archive ne lie que les fonctions utilisées.
Les consommateurs qui compilent directement les sources peuvent choisir :

| Famille Make | Contenu |
|---|---|
| `HGRC_DHGR_STATE_SRCS` | État vidéo, initialisation, trampoline auxiliaire et pages |
| `HGRC_DHGR_PIXEL_SRCS` | Points monochromes et lecture de pixels |
| `HGRC_DHGR_CLEAR_SRCS` | Effacement seul, sans rectangles ni lecture de pixels |
| `HGRC_DHGR_FILL_SRCS` | Effacement et rectangles couleur/monochromes |
| `HGRC_DHGR_CORE_SRCS` | Les trois familles précédentes |
| `HGRC_DHGR_TRANSFER_SRCS` | Blocs et sprites, avec un adressage partagé |
| `HGRC_DHGR_SMALL_TEXT_SRCS` | Petite police et chaînes rapides |

`HGRC_DHGR_SRCS` conserve l’ensemble historique des primitives, transferts et
texte 8×8. `dhgr_internal.h` centralise les paramètres et prototypes privés des
primitives bancaires. Lors d’une compilation manuelle, `dhgr.c` fournit maintenant
l’état et les pages : utiliser les listes de familles ci-dessus pour inclure
leurs dépendances. Les noyaux assembleur d’écriture masquée, de lecture,
d’effacement et de scanline sont des objets distincts. L’adresse de pixel et le
motif couleur sont partagés, tandis que chaque API de lecture, point, rectangle
et effacement garde son propre objet. Les paramètres de petite police sont
séparés du wrapper C : un HUD assembleur n’impose pas `dhgr_puts_small`.

La sélection des familles ne suffit pas à éliminer toutes les fonctions inutiles
si leurs objets sont passés directement à ld65. Construire une archive ar65 et
la placer après les objets applicatifs permet à ld65 d’extraire uniquement les
membres référencés et leurs dépendances. ChromaBreak suit cette règle avec
`platform.lib`, y compris pour les modules Apple II, ProDOS et souris. Son test
contrôle le fichier de liaison pour exclure les pixels, rectangles et transferts
génériques, le texte 8×8 et les wrappers de texte inutilisés. Les tests de
bibliothèque contrôlent aussi quinze consommateurs minimaux de l’archive.

### Contrat mémoire et transitions

| État | Convention |
|---|---|
| Pages vidéo | `$2000–$3FFF` et `$4000–$5FFF`, chacune en principal et auxiliaire |
| Code, pile C, buffers, sources | Hors `$2000–$5FFF`, en RAM principale |
| Entrée | `RAMRD/RAMWRT` principaux, `ALTZP` désactivé, ROM principale |
| Sortie des primitives | `RAMRD/RAMWRT` principaux, `80STORE` désactivé, page affichée conservée |
| Interruptions | État I conservé ; accès bancaires protégés, routines non réentrantes |
| Lecture auxiliaire | Petit trampoline exécutable de **9 octets de page zéro**, installé par init |

Le mode garde `80COL` actif et `80STORE` désactivé : `PAGE2` choisit ainsi
la page affichée. `RAMWRT` permet les écritures auxiliaires ; le trampoline
lit avec `RAMRD` sans perdre l’accès au code principal. Les primitives ne
sont pas appelables depuis une interruption. L’effacement bloque les IRQ
pendant environ 208 000 cycles ; privilégier les blocs/segments en animation.

`hgr_init`, `hgr_init_clear` et `hgr_text_restore` remettent les commutateurs
IIe en état HGR/texte natif. `dhgr_text_restore` prépare les routines texte ROM.
Le CRT C restaure aussi ces commutateurs lors du retour et du Ctrl-RESET.
Une initialisation HGR ne change pas automatiquement la page de **dessin** HGR :
utiliser `hgr_set_draw_page(1)` si l’on veut aussi réinitialiser ce choix.

### Backends gfx

Lier **un seul** backend, en plus des algorithmes `gfx` nécessaires :

| Backend | Coordonnées | `dhgr_set_color` |
|---|---|---|
| `HGRC_DHGR_COLOR_BACKEND` | 140×192 pixels couleur | Couleur LORES 0..15 |
| `HGRC_DHGR_MONO_BACKEND` | 560×192 bits | 0 = éteint, autre = allumé |

Le backend reste choisi à l’édition de liens. Le mode monochrome produit des
couleurs d’artifact sur un moniteur couleur. Les lignes/cercles/rectangles
partagent les algorithmes `gfx` existants ; les segments utilisent les accès
par octets avec masquage des extrémités.

### Outils et vérification

- [Convertisseur d’assets](../../tools/assets/README.md) : PNG/PPM, HGR/DHGR,
  sprites, masques, sept phases, aperçu et bilan mémoire.
- Les déclarations de conversion ×2 hôte sont dans `hgr_host.h`.
- [Mesures et budgets](../../bench/README.md) : cycles CPU, code, ROM, RAM et ZP.
- `make test-hgr` : 21 contrôles de primitives, quatre scènes de texte `gfx`,
  24 scènes du moteur de sprites et sept éditions de liens minimales.
- `make test-dhgr` : 21 contrôles historiques + 48 contrôles supplémentaires,
  deux pages/banques, deux backends, sprites, blocs, texte, transitions et refus II+.
  Le cœur IIe POM2 dans `a2shot` est requis (macOS arm64).
- `make test` inclut HGR, assets, budgets HGR et MICRO-SOKOBAN sous Linux/macOS.

Voir la [démo animée](../../examples/dhgr/README.md).

Auteur : VERHILLE Arnaud. Licence : [GPL-3.0](../../../LICENSE).

## Moteur de sprites et présentation

`hgr_spr_render()` restaure puis dessine les sprites sans attendre ni afficher.
`hgr_spr_present()` affiche la page rendue et sélectionne l’autre page de
dessin en double tampon ; en simple tampon, il ne fait rien.
`hgr_spr_update()` conserve le comportement immédiat render + present.
`hgr_get_draw_page()` retourne la page de dessin actuelle (1 ou 2).
Le programme doit attendre entre render et present s’il veut synchroniser la
bascule ; voir [`apple2frame.h`](../apple2c/apple2frame.h) et l’[exemple HGR](../../examples/hgr/README.md).

Le pool statique réserve 1 536 octets même en simple tampon.
`hgr_spr_define()` retourne 1 si la définition est acceptée, 0 sinon.
Les pointeurs nuls, dimensions nulles, stride > 40, hauteur > 192 et
`stride * hauteur > 96` sont refusés. Une redéfinition encore dessinée sur
une page est refusée en gardant l’ancienne définition ; masquer et restaurer
chaque page avant de redéfinir. Les données de la forme doivent rester valides
pendant ces restaurations. Ne pas modifier le fond sous un sprite dessiné.

`make test-hgr` ajoute 24 scènes du moteur : chevauchements, sept phases,
deux pages, bord droit/bas, masquage, redéfinition et géométries invalides.
Les comparaisons couvrent aussi les bits de palette et les trous vidéo.
