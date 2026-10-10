# Wilderness

Réimplémentation de *Wilderness: A Survival Adventure* (Electric Transit,
1985), simulation de survie en 3D pour Apple II.

**État : la vue 3D du terrain est jouable.** `dist/WILDERNESS.dsk` démarre sur
une carte générée et permet de se promener : chaque déplacement recalcule la
vue avec le moteur de l'original (lancer de rayons, occlusion par la pente,
bandes de crêtes) : 1,2 à 2 s pour un pas, 0,4 à 1 s pour tourner (la vue
défile et seules les nouvelles colonnes sont calculées, comme le PAN de
l'original). L'original mettait plus de 10 s par vue. La
survie, le parseur et les menus restent à faire (voir [`TODO.md`](TODO.md)).
Ce qu'on sait de l'original est dans [`docs/ANALYSE.md`](docs/ANALYSE.md).

| Touche | Action |
|---|---|
| ← / J, → / K | Tourner de 22,5° |
| A, Z | Tourner de 45° |
| ↑ / I, ↓ / M | Avancer, reculer d'une cellule (2 unités, environ 0,5 mile) |
| V | Redessiner la vue |
| ESC / Q | Retour à DOS |

La ligne du bas donne la position (unités de carte, 224 × 168), le cap en
degrés et l'altitude.

## Construction

```sh
make               # ../dist/WILDERNESS.dsk
make run           # dans POM2
make test          # vue 6502 contre tools/view_ref.py au bit près, fuzz court, touches contre un modèle
make fuzz          # positions et cartes synthétiques aléatoires, plus long
make SEED=7 LEVEL=8   # une autre carte (niveau de difficulté 1-10)
```

Mémoire (Apple II+ 48 Ko, DOS 3.3) :

| Zone | Contenu |
|---|---|
| `$1000-$1FFF` | `WILDLO` (BLOAD par HELLO) : tables de lignes, code déroulé de remplissage et d'effacement |
| `$2000-$3FFF` | HGR page 1 : vue sur les lignes 0-159, 4 lignes de texte (mode mixte) |
| `$4000-$5FBF` | Table de division ⌊r·256/n⌋ (r < n < 128), calculée au démarrage |
| `$6000-$6FFF` | Programme `WILDERNESS` (`src/wild.s`, BRUN) |
| `$7000-$94FF` | Carte `WILDMAP` (BLOAD par HELLO) : en-tête de 64 octets, grille 112 × 84 |

La carte du jeu est une grille de 112 × 84 cellules de 2 unités, le pas du
rayon : un octet par cellule (niveau 0-127, bit 7 = eau), lu directement là où
l'original parcourait des listes de croisements de courbes par ligne. Les
niveaux s'arrêtent à 125 : le moteur calcule niveau − œil + 128 sur un octet. Elle est
produite par `tools/mkmap.py`, qui reprend l'algorithme de TMAKE (montagnes
gaussiennes sur quatre échelles, poste près d'un bord, crash sur une montagne
éloignée, rivières et lacs). Aucune donnée de l'original n'est sur la disquette.

## Analyse de l'original

Les images originales sont protégées par le droit d'auteur : elles restent
dans `original/`, ignoré par git.

```sh
make originals     # télécharge les images depuis archive.org
make extract       # décode WOZ/A2R en .dsk, extrait les fichiers SMALLDOS dans build/
make run-original  # démarre le jeu dans a2shot, liste le menu dans build/MENU.bas
make dump-game     # lance une partie et vide la RAM dans build/game.bin
make topo          # carte et vue 3D de départ recalculées : build/topo.png, build/view.png
```

`make test` ajoute la carte originale convertie (`build/orig_map.bin`, par
`tools/topo2map.py`) aux comparaisons quand elle existe en local.

## Outils

| Outil | Rôle |
|---|---|
| `tools/mkmap.py` | Génère une carte (algorithme TMAKE) au format du jeu, avec un aperçu PNG |
| `tools/view_ref.py` | Référence Python exacte du rendu 6502 |
| `tools/gentables.py` | Tables de sinus et de colonnes HGR pour `src/wild.s` |
| `tools/flux2dsk.py` | WOZ2 ou A2R2 → `.dsk` ordre DOS (pistes 16 secteurs 6&2) |
| `tools/smalldos.py` | Catalogue et extraction des disques SMALLDOS |
| `tools/applesoft.py` | Liste un programme Applesoft tokenisé |
| `tools/peek2bin.py` | Convertit les `peek:` d'a2shot en binaire |
| `tools/topo.py` | Décode une carte TOPO originale en image |
| `tools/topo2map.py` | Convertit une carte TOPO originale au format du jeu (tests locaux) |
| `tools/view3d.py` | Premier prototype flottant de la vue |
| `tools/profile.py` | Cycles par routine d'une vue (étape `pcprof` d'a2shot) |
