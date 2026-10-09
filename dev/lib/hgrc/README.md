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

Les noyaux assembleur sont séparés : initialisation (mode, effacement initial,
LORES, basculement des tables de lignes), effacement, rectangles en octets,
rectangles en pixels, cellules, pixels, coloration, texte ×1, texte ×2,
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
46 000 (boucle auto-modifiée de `HGR_CLEAR_LOOP`, lib/apple2), basculement de
page par `hgr_flip_rows` (boucle déroulée, un EOR par ligne), texte
8x8 `hgr_puts8` ~9 000 pour « APPLE II » (glyphe décalé en deux octets par
ligne), texte 16x16 `hgr_puts` par le blitter couleur avec les porteuses
blanches `$7F/$7F` (un seul blitter, ~5 fois plus rapide que l'ancien tracé
pixel par pixel). Les enveloppes C lisent `hgr_col7` / `hgr_phase7` /
`hgr_mask7` au lieu de diviser par 7, et les tables de lignes se calculent
sans multiplication.

## Intégration

`$(DEV)/cc65/apple2.mk` fournit `HGRC`, `GFX`, `APPLE2C`, `BUILD`, les outils
et la règle `$(DISK)` ; inclure ensuite `hgrc.mk` et `../apple2c/apple2c.mk`.
Les règles communes de `hgrc_build.mk` construisent `$(BUILD)/hgrc/hgrc.lib`
(`$(HGRC_LIB)`). Exemple :

```make
DEV ?= ../dev
include $(DEV)/cc65/apple2.mk
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
DISK := $(DIST)/GAME.dsk
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS)

all: $(DISK)

# Fournir les règles de compilation de crt0_apple2.o ($(A2_CRT0)) et main.o.
$(BUILD)/game.bin: $(BUILD)/crt0_apple2.o $(BUILD)/main.o $(HGRC_LIB)
	$(CL65) -t none -C $(A2_HGR_C_CFG) -o $@ $^

$(DISK): $(BUILD)/game.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin GAME=$(BUILD)/game.bin@$(LOAD)

# Après la première cible, pour conserver « all » comme cible par défaut.
include $(HGRC)/hgrc_build.mk
```

`HGRC_BUILD`, `HGRC_CFLAGS` et `HGRC_ASMFLAGS` sont personnalisables.
Les objets encodent leur répertoire et leur extension dans le nom du membre
d'archive. `config.json` enregistre les options, outils et sources ; changer
les flags invalide les objets sans nettoyage préalable. Une construction
identique laisse les objets et l'archive intacts.
Les listes `HGRC_*_SRCS` restent disponibles pour construire une archive
avec un sous-ensemble de familles. Voir les Makefiles de Snake, des démos et
de l'[exemple HGR](../../examples/hgr/Makefile).

## Taille mesurée

Comparaison historique avant/après le premier découpage, avec cc65 2.18 et `-Oirs`, sur
les mêmes sources de jeux (taille du fichier `.bin` et segment ZEROPAGE du
fichier `.map`). Cette mesure historique inclut les transitions vidéo IIe et les noyaux
assembleur du texte, de l'effacement et du basculement de page. La page zéro
inclut le runtime C du programme.

| Programme | Binaire avant → après | Page zéro avant → après |
|---|---:|---:|
| Snake | 10 218 → 8 573 octets | 99 → 80 octets |
| Bounces | 12 263 → 11 348 octets | 99 → 79 octets |
| Animals | 13 139 → 13 121 octets | 99 → 51 octets |
| Preshift | 4 611 → 4 247 octets | 99 → 60 octets |

Animals gagne surtout de la page zéro : le contrôle d'abscisse et la
restauration des commutateurs vidéo IIe lui avaient coûté 76 octets, que les
noyaux assembleur ont repris. Les autres programmes bénéficient aussi de
l'exclusion de routines jusque-là liées inutilement.

## Limites et vérification

- `gfx_filled_rect` accepte deux coins inclusifs, les remet dans l'ordre,
  les rogne à 280×192 et découpe les largeurs dépassant 255 pixels.
- `hgr_fill_pixrect` / `hgr_clear_pixrect` conservent une largeur sur 8 bits ;
  zéro ne dessine rien. Ces fonctions remettent le bit de palette à zéro
  dans les octets touchés, même aux bords du rectangle.
- `hgr_colorize` et `hgr_blit7` rejettent les abscisses hors écran avant
  toute conversion en colonne sur 8 bits.
- `hgr_blit` ne lit que les octets nécessaires aux pixels dessinés, y compris
  lorsque la dernière ligne finit exactement sur une limite d'octet.
- `hgr_sprite_xor` rogne aussi les lignes sources de grande largeur, jusqu'à
  un stride de 255 octets, sans débordement du calcul de colonne sur 8 bits.
- Les quatre noyaux ASM de `hgr_sprmask.s` rognent également les strides
  jusqu'à 255 octets lors d'un appel direct. `test_sprmask_bounds.py` vérifie
  les deux pages, les sept phases et les limites du tampon de sauvegarde ;
  le moteur C conserve sa limite de stride à 40 octets.
- `hgr_lores_clear` remplit les 960 octets visibles de la page de dessin et
  préserve les 64 octets réservés au firmware des périphériques.
- `hgr_lores_init` revient au mode natif 40 colonnes après un affichage DHGR
  ou 80 colonnes, avec `80STORE` désactivé et les lectures/écritures en RAM
  principale. La détection de modèle évite ces commutateurs sur Apple II+.

`make test-hgr` compile et exécute les routines dans **a2run**, sous Linux et
macOS. Les 21 étapes comparent les deux pages vidéo avec un modèle Python :
rectangles 256/280 pixels, limites, pixels, sprites SET/CLEAR/XOR et sept
phases, texte blanc/coloré, nombres, cellules, coloration. Quatre scènes supplémentaires vérifient le texte par cellules `gfx` sur
la page 2, le curseur et les conversions numériques. Seize programmes
minimaux vérifient aussi que l'archive exclut les noyaux et blocs de page zéro
inutilisés. Ce test fait partie de `make test` et de la CI.

L’agrandissement de sprites ×2 est disponible sur cc65 avec
[`hgr_x2.h`](hgr_x2.h). `hgr_inflate_x2` convertit une source monochrome
dans un tampon fourni par l’appelant ; `hgr_blit_x2` convertit et dessine
à la demande avec un tampon interne de 256 octets. Ces fonctions sont dans
`HGRC_X2_SRCS` et l’archive commune, extraites seulement si elles sont appelées.
Pour une animation, convertir une fois au démarrage, puis utiliser `hgr_blit7`
à chaque image. Placer le sprite à `x = 14*n` pour conserver sa teinte.
Les banques peuvent aussi être préparées avant compilation, comme avec
`demos/src/animals_gen_x2.py`.

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
bibliothèque contrôlent aussi seize consommateurs minimaux de l’archive.

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
pendant environ 189 000 cycles ; privilégier les blocs/segments en animation.

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
partagent les algorithmes `gfx` génériques pour DHGR ; les segments horizontaux/verticaux utilisent les accès
par octets avec masquage des extrémités.

### Outils et vérification

- [Convertisseur d’assets](../../tools/assets/README.md) : PNG/PPM, HGR/DHGR,
  sprites, masques, sept phases, aperçu et bilan mémoire.
- Les déclarations de conversion ×2 hôte sont dans `hgr_host.h`.
- [Mesures et budgets](../../bench/README.md) : cycles CPU, code, ROM, RAM et ZP.
- `make test-hgr` : 21 contrôles de primitives, quatre scènes de texte `gfx`,
  24 scènes du moteur de sprites et seize éditions de liens minimales.
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

Avec les huit slots par défaut, le pool statique réserve 1 536 octets même en simple tampon.
Cette réservation appartient uniquement à l'objet de compatibilité
`hgr_spr_init`. `hgr_spr_init_pool(dbuf, pool, taille, nombre, capacité)`
utilise un pool fourni par l'appelant et ne lie pas cet objet. Il faut
`nombre * capacité * (dbuf ? 2 : 1)` octets ; nombre vaut 1..8 et capacité
1..255 octets par sprite/page. L'exemple HGR utilise cette API pour trois
sprites. Une configuration invalide retourne zéro et conserve l'ancien
moteur ; les fonds doivent être propres avant une réinitialisation valide.
`hgr_spr_define()` retourne 1 si la définition est acceptée, 0 sinon.
Les pointeurs nuls, dimensions nulles, stride > 40, hauteur > 192 et
`stride * hauteur > capacité` sont refusés (96 avec le pool de compatibilité,
1..255 avec le pool externe). Une redéfinition encore dessinée sur
une page est refusée en gardant l’ancienne définition ; masquer et restaurer
chaque page avant de redéfinir. Les données de la forme doivent rester valides
pendant ces restaurations. Ne pas modifier le fond sous un sprite dessiné.

`make test-hgr` ajoute 24 scènes du moteur : chevauchements, sept phases,
deux pages, bord droit/bas, masquage, redéfinition et géométries invalides.
Les comparaisons couvrent aussi les bits de palette et les trous vidéo.
Les mêmes 24 scènes sont exécutées avec un pool externe de 24 octets,
gardes mémoire et configurations invalides. La carte de liaison vérifie
l'absence du pool de compatibilité.

## Tables et lignes HGR

Les tables de lignes, colonnes, masques et phases sont des objets séparés,
construits à la demande en RAM. Un effacement seul n'embarque aucune table ;
un blitter aligné ne réserve ni les masques ni les phases. L'initialisateur
`hgr_build_tables` reste disponible pour préparer toutes les tables.
La sélection de page prépare seulement les lignes. `hgr_row(y)` suit la page
de dessin et renvoie NULL hors écran. Les noyaux de sprites masqués et XOR
préparent aussi les tables X lorsqu'ils sont appelés directement.

`hgr_line` utilise un Bresenham assembleur pour les diagonales sur 280 pixels,
avec les mêmes choix de pixels que l'ancienne API C. Les axes gardent les
spans rapides. Les extrémités hors écran sont refusées ; aucun clipping de
segment implicite n'est ajouté. `gfx_line` sélectionne ce noyau sur HGR et le fallback C
sur les backends génériques/DHGR. `test_hgr_lines.py` compare 464 lignes via `hgr_line` et `gfx_line` aux pixels attendus sur les
deux pages, y compris les directions inverses, égalités et X >= 256.

## Effacement DHGR avec service des IRQ

`dhgr_clear_rows(y, rows, color)` remplit les lignes visibles de la page de
dessin, rogne à 192 et préserve les trous mémoire. Chaque ligne rétablit
RAMWRT principal et le masque IRQ de l'appelant ; les IRQ autorisées peuvent
être servies entre les lignes. Le noyau mesuré prend 1 177 cycles, sous une
borne testée de 1 300. Un test avec timer VIA Mockingboard vérifie aussi que des IRQ périodiques
sont réellement servies pendant les deux effacements de page, avec contrôle
des banques, gardes mémoire et pixels. Le service reste non réentrant. Employer de petites
tranches pour traiter aussi les entrées entre les appels. L'effacement complet
historique conserve son comportement et ses performances.

La référence hôte `hgr_inflate_x2` (`hgr_x2.c`) et la version cible
(`hgr_x2_target.c`) calculent les strides agrandis sans troncature à huit bits.
La cible transforme chaque octet avec une table de 16 octets, sans boucle
par pixel ni division. Réserver `4*wbytes*h` octets de sortie, sans
chevauchement avec la source ; la cible refuse les tailles supérieures
à 65535 octets. `hgr_host.h` reste un include compatible de `hgr_x2.h`.
`hgr_blit_x2` contrôle la
taille source avant de doubler les dimensions, afin de respecter son tampon
fixe même pour des entrées supérieures à 127. `test_hgr_host.py` vérifie les
couleurs et les gardes mémoire avec ASan/UBSan, ainsi que les 65 536 couples
de dimensions du wrapper. `test_hgr_x2.py` exécute le code cc65 et vérifie
les six couleurs, les strides de 510 octets, les gardes mémoire, les tailles
invalides et les dessins rognés sur la page 2. Les deux tests font partie
de `make test-hgr`.


## Choisir l'implémentation gfx

`HGRC_VECTOR_SRCS` et l'archive par défaut utilisent `gfx_line_hgr.c`, qui
route les diagonales vers `hgr_line` assembleur. Les axes de `gfx_line`
conservent leur clipping historique par les spans ; `hgr_line` refuse toute
extrémité hors écran, axes compris. Les pixels diagonaux valides sont identiques.
Pour DHGR ou un backend externe, utiliser `HGRC_GENERIC_VECTOR_SRCS`
(`gfx_line.c` + rectangles), avec exactement un backend explicite.
Ne pas lier directement les deux implémentations de `gfx_line`.

Les [exemples minimaux](../../examples/minimal/README.md) fournissent les trois
intégrations HGR simple/double tampon et DHGR ProDOS, avec un bilan mémoire
calculé depuis les cartes de liaison. Les contrats communs et les unités sont
dans [ABI.md](../ABI.md). Le protocole de [validation matérielle](../HARDWARE.md)
distingue les résultats émulés des essais physiques restant à effectuer.


## HUD avec historique par page

`hgr_hud_field_t` est un état fourni par l'appelant, de 37 octets sur cc65.
`hgr_hud_init(&champ,x,y,largeur)` accepte une boîte entière à l'écran,
largeur 1..14 cellules de 16×16, pitch 18 ; une entrée invalide conserve l'ancien
champ. `hgr_hud_putu(&champ,valeur)` renvoie le nombre de cellules redessinées,
0 pour une valeur inchangée, `HGR_HUD_INVALID` (255) si la valeur ne tient pas
ou le pointeur est nul. Contrairement au champ historique, il refuse le
débordement numérique sans modifier l'image ni l'historique.

Les chiffres sont blancs sur une boîte noire dont le champ possède le contenu.
Le passage à une valeur plus courte efface les cellules devenues vides.
Les pages 1 et 2 ont leur propre historique. Après un effacement ou une écriture
externe dans la boîte, appeler `hgr_hud_invalidate(&champ,page)` ; page 0 invalide
les deux. Ne pas superposer ce champ à une région de sprites sauvegardés sans
gérer aussi leur fond. L'état doit rester valide pendant son utilisation.

L'exemple animé utilise ce format ; les deux exemples HGR minimaux utilisent
sa variante compacte 8×8 décrite ci-dessous.
`test_hgr_hud.py` compare 168 mises à jour sur les sept phases, fonds colorés,
les deux pages, les valeurs qui raccourcissent et les refus de géométrie/overflow.
Les anciens champs restent disponibles pour du dessin sans historique.


## Dimensionner les métadonnées de sprites

`HGR_SPR_MAX` est une limite de compilation de 1..8 (8 par défaut). Passer le
même `-D HGR_SPR_MAX=N` au programme et à son archive dimensionne les tableaux
privés et le pool historique. La signature de build invalide l'archive si ce
flag change. Le moteur continue d'accepter un nombre runtime inférieur ou égal
à cette limite. Les deux historiques de page restent disponibles.

Un moteur à deux slots réserve 42 octets d’état de tableaux contre 132 à huit slots :
**90 octets économisés**, indépendamment du pool externe. Les 24 scènes de
régression sont aussi exécutées avec cette configuration. L'exemple de trois
balles compile programme et archive avec une limite de trois slots, soit
75 octets de métadonnées économisés. Les autres programmes gardent le défaut.

## Rendu incrémental et présentation robuste

Le moteur conserve les sprites inchangés au début de la liste de couches.
À partir du premier sprite modifié (position ou visibilité), il restaure les
couches suivantes en ordre inverse, puis les redessine dans l'ordre initial.
Cette stratégie conservatrice préserve les fonds en cas de chevauchement,
sans tables de collision supplémentaires. Une page entièrement inchangée
ne restaure et ne redessine aucun sprite. Les formes empruntées restent immuables.
Un déplacement invisible hors écran ne force pas un redessin.

`hgr_spr_present` sélectionne explicitement la page du moteur avant de l'afficher,
même si l'application a changé sa propre page après `render`. Il choisit ensuite
l'autre page pour le prochain rendu. Aucun état vidéo n'est ajouté en simple tampon.
`hgr_spr_invalidate(1/2)` force le prochain rendu de cette page ; 0 vise les deux,
les autres valeurs sont ignorées. L'invalidation ne permet pas de modifier un fond
sous des sprites dessinés : les masquer et restaurer les pages avant ce changement.
Les historiques restent séparés par page. Le contrôleur de rendu, les
déplacements et la présentation sont en ASM ; stride×hauteur est préparé lors
de la définition. Les restaurations ne recalculent ni phases ni pointeurs de
dessin ; les largeurs visibles de deux/quatre octets utilisent des boucles déroulées.

`test_sprengine_dirty.py` compare les pixels des deux pages et le coût des
frames immobiles, des changements de couche supérieure/inférieure, du masquage
et du clipping. Sur POM2 IIe, il vérifie aussi la page effectivement affichée
après un changement applicatif de la page de dessin.

## Noyau HUD opaque

Le chemin compact `hgr_hud8_init/putu/invalidate` utilise une structure
`hgr_hud8_field_t` de 19 octets, largeur 1..5, cellules 8×8, pitch 8.
La boîte entière doit tenir à l'écran : y≤184, x+8×largeur≤280.
Les mêmes règles de cache, retour, fond opaque et overflow s'appliquent.
Son objet séparé permet de ne lier que le format utilisé. Le changement des
cinq chiffres coûte au maximum 7 850 cycles sur les sept phases du benchmark,
contre 22 235 pour le format 16×16. Préparer les deux pages avant animation.

L'exemple minimal utilise ce format. En double tampon IIe, il répartit dessin
et HUD sur deux intervalles VBL ; chaque étape tient dans un rafraîchissement.
Son test POM2 suit 1 000 présentations par standard, y compris le débordement
du compteur : deux rafraîchissements par image, soit nominalement 30/25 FPS.
Pour une charge pouvant dépasser un intervalle, utiliser l'ordonnanceur
`a2_cadence_*` et une source IRQ déjà détenue par l'application. Voir les
contrats dans [apple2frame.h](../apple2c/apple2frame.h).

Le moteur compilé avec `-DHGR_SPR_DAMAGE=1` propage les changements par
intersections des boîtes anciennes/nouvelles, en octets sauvegardés plutôt
qu'en pixels visibles. Il peut conserver des couches immobiles isolées,
mais ajoute 43 octets de BSS au défaut de huit slots et du travail assembleur de
comparaison. La scène de quatre grands sprites isolés, dont seul le premier
bouge, passe de 31 031 à 14 662 cycles (+437 octets chargés).
L'option reste désactivée par défaut ; choisir à partir de scènes représentatives.
Les tests vérifient aussi les chaînes de quatre couches et les octets de padding.

Les chiffres du champ différentiel utilisent un noyau assembleur dédié :
il remplace le fond et écrit le glyphe blanc dans le même parcours des lignes.
Il efface aussi les deux pixels d'espacement des cellules internes, conserve
les pixels voisins et remet à zéro la palette des octets touchés.
Le format 16×16 utilise la police existante et une LUT de 16 octets. Le format
8×8 utilise une banque espace/chiffres prédécalée aux sept phases : 1 386 octets
chargés, tables de pointeurs comprises. Il évite les LUT mutables et la police
générale quand seul le HUD est lié. Les contrôleurs de chiffres sont en ASM ;
les pas +1/+2 réutilisent les caractères en cache avec propagation des retenues. Les règles d'invalidation du
champ restent identiques. Le noyau n'impose plus le texte agrandi général
ni les paramètres des rectangles en pixels à un client HUD seul.

Les tests vérifient 168 mises à jour avec retenue décimale et wrap et 70 chiffres placés
contre les bords droit et inférieur, dans les sept phases. Le même oracle
est exécuté avec a2run et POM2 IIe. Les exemples préparent les deux historiques
HUD avant leur boucle, pour déplacer ce coût vers le chargement.

## Adressage explicite optionnel

`hgr_row_on_page(page,y)` retourne une adresse pour la page 1/2 et la ligne
0..191, ou NULL si une entrée est invalide. Il ne change ni la page de dessin,
ni celle affichée, ni les tables historiques. Les offsets immuables occupent
384 octets de RODATA, dans un membre d'archive séparé ; aucun tableau de lignes
mutable n'est lié par cet accès seul. Ce n'est pas une substitution automatique
pour les noyaux existants qui lisent `hgr_rowhi`.

En assembleur, `hgr_fixed_rowlo/hi` exposent les offsets (HI sans base vidéo).
Combiner HI avec $20/$40 via OR pour former les adresses. Les données seules
n'importent aucun runtime C. `hgr_rowptr_on_page` offre également un point
d'entrée A=page, Y=ligne, résultat A/X, NULL pour entrée invalide ; ce noyau
partage tmp2 cc65 et le membre de l'enveloppe C, donc exige le runtime cc65.
Le parcours natif et l'enveloppe C sont mesurés séparément : le coût des appels
C répétés ne constitue pas une optimisation de scanline.

## Dépendances réelles des consommateurs

Les fichiers `.d` de cc65/ca65 suivent les includes transitifs, y compris ceux
de `HGRC_EXTRA_SRCS`. Pour la compilation C en deux étapes, la dépendance est
réattribuée de l'assembleur généré à l'objet final. Les tests modifient un
header imbriqué et un include assembleur situés hors de la bibliothèque,
puis vérifient la reconstruction, le changement du binaire et le no-op suivant.

## Fond reconstruit depuis une tilemap

`hgr_tilemap_init` valide un contexte emprunté : carte 40×24 de 960 IDs,
1..256 tuiles de 7×8 pixels, huit octets HGR par tuile avec leur palette.
`hgr_tile_restore(&fond,page,col,row,largeur,hauteur)` reconstruit une région
en coordonnées de tuiles, rognée à droite/en bas, sans modifier la page de
dessin ni l'affichage. La validation de tous les IDs précède toute écriture ;
un refus laisse l'image intacte. Carte et banque doivent rester valides hors
vidéo ; l'initialisation invalide conserve l'ancien contexte.

L'application restaure toutes ses anciennes/nouvelles régions sales avant
le dessin des couches touchées, et conserve un historique distinct par page.
Ce backend optionnel s'utilise avec le blitter masqué `hgr_ms_run` (contrat
interne explicite dans `hgr_internal.h`) pour éviter le pool save-under.
Le moteur historique conserve sa restauration de fonds sauvegardés.
Une région de huit tuiles avec deux dessins masqués coûte 9 546 cycles dans
le benchmark ; le coût d'une page entière reste à budgéter pour chaque jeu.
La famille `HGRC_TILEMAP_SRCS` est extraite uniquement lorsqu'elle est appelée.

Les dépendances `HGRC_HEADERS` comprennent aussi les en-têtes de `apple2c`,
inclus transitivement par `hgr.h`, pour recompiler les consommateurs C lors
des changements du contrat de la plateforme.
