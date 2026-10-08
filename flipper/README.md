# FLIPPER — Pinball Construction Set sur Apple II

Reconstruction de **Pinball Construction Set**, écrit par **Bill Budge**,
à partir des sources Apple II qu'il a publiées dans
[billbudge/PCS_AppleII](https://github.com/billbudge/PCS_AppleII).
La disquette amorçable est [`../dist/FLIPPER.dsk`](../dist/FLIPPER.dsk).
Elle démarre dans l'éditeur, avec la table vide de l'original.

## Origine et licence

Les fichiers de `upstream/source_disc1/` et `upstream/source_disc2/` sont les
neuf sources assembleur du dépôt de Bill Budge, **conservées sans modification**.
La révision utilisée est
[`615edfe43b7747ae9d7a390066b4ec0738950b53`](https://github.com/billbudge/PCS_AppleII/tree/615edfe43b7747ae9d7a390066b4ec0738950b53).
Leur licence est **MIT**, copyright 1982 Bill Budge ; le texte original est
conservé dans [`upstream/LICENSE`](upstream/LICENSE).

Le dépôt amont contient un README vide et aucune recette de construction.
Il ne fournit pas les bitmaps des pièces, la base de données de la table de
départ, ni les composants DOS nécessaires au démarrage et aux fichiers.
Pour compléter la reconstruction, quatre blocs ont été extraits de
[la disquette archivée « 055a - Pinball Construction Set - Side 1.dsk »](https://mirrors.apple2.org.za/ftp.apple.asimov.net/images/misc/3d0g_knight_collection/055a%20-%20Pinball%20Construction%20Set%20-%20Side%201.dsk).

| Fichier dans `assets/` | Rôle | Taille |
|---|---|---:|
| `bitmaps.bin` | Graphismes des pièces, à `$7000` | 1 792 octets |
| `initial-table.bin` | Deux polygones de la table vide, à `$4000` | 69 octets |
| `dos-file-manager.bin` | Gestionnaire de fichiers DOS, à `$A900` | 3 328 octets |
| `dos-rwts.bin` | Lecture/écriture Disk II, à `$B800` | 2 048 octets |

[`assets/origin.json`](assets/origin.json) enregistre l'URL, l'empreinte SHA-256
de la disquette de référence, les offsets, les tailles et les empreintes
de chaque bloc. `tools/extract_assets.py chemin/reference.dsk` permet de refaire
l'extraction et refuse une image dont l'empreinte diffère.
La disquette de référence complète n'est pas nécessaire à la construction.
Ces blocs binaires proviennent de l'archive, pas du dépôt MIT ; la licence
amont ne constitue donc pas une attribution de licence supplémentaire pour
ces blocs, notamment les composants Apple DOS.

**Le code de l'éditeur, du moteur de jeu, du câblage, des commandes de fichiers,
du chargeur secondaire et du changement de modules est assemblé depuis les
sources publiées.** Il n'est pas recopié depuis la disquette archivée.
Le premier chargeur utilise le code standard Apple DOS du fichier partagé
`../dev/tools/dos33_system.bin`, avec les paramètres de chargement de PCS.
Les tables graphiques sont recalculées par le constructeur.

## Adaptation au DEVBENCH CC65

La construction s'intègre au DEVBENCH du dépôt via
`../dev/cc65/apple2.mk` : variables `CA65`, `LD65`, `PYTHON`, `BUILD`, `DIST`,
`POM2`, `A2RUN`, et cibles `run`, `clean`, `distclean`.
Le pilote [`../dev/lib/mouse/mouse.s`](../dev/lib/mouse/mouse.s) est lié
directement au programme ; son adaptateur est [`src/mouse.s`](src/mouse.s).
Ces ajouts sont sous GPL-3.0, comme le DEVBENCH ; les sources amont restent MIT.
Elle utilise uniquement **cc65 (`ca65` et `ld65`) et Python 3**.
Aucun téléchargement n'est effectué pendant `make`.

`tools/translate.py` traduit la syntaxe de l'assembleur historique vers ca65
dans `build/*.s` et produit les configurations ld65 associées :

- `EQU`, `HEX`, `DA`, `DS`, `ORG` deviennent des constantes et directives ca65 ;
- les opérateurs `<` et `>` conservent leur portée sur l'expression entière ;
- les noms sont préfixés par `pcs_` pour éviter les mots réservés de ca65 ;
- `OBJ`, qui indiquait une adresse de stockage à l'assembleur historique,
  laisse place au placement des modules dans la disquette ;
- chaque module produit son binaire et ses symboles `build/*.lbl` avec ld65.

L'adaptateur initialise AppleMouse au démarrage et remplace les entrées de
lecture du curseur et des sélections sans déplacer les routines historiques.
Il conserve la page zéro de PCS pendant les appels au firmware. Les tables
qui occupaient `$0400-$077F` sont déplacées à `$6800-$6B7F` pour libérer les
boîtes de communication AppleMouse. Le tampon graphique `LOGO`, qui écrasait
également cette zone, est déplacé à `$6B80-$6FFF`.

Sur **Apple //c**, l'adaptateur conserve les coordonnées mises à jour par les
interruptions du firmware natif. Les accès au gestionnaire de fichiers DOS
échangent temporairement les boîtes de communication avec une copie des
buffers DOS et protègent ces échanges des interruptions. La souris fonctionne
ainsi après SAVE/LOAD, comme dans l'éditeur et le câblage. Le pilote reste
chargé pendant les changements de modules.

La limite de construction des polygones (`PBDX`) passe de `$6F40` à `$6240`
pour réserver cet espace. Cela réduit de **3 328 octets (3,25 Ko)** l'espace
disponible pour les données et les polygones de la table. Les coordonnées du
pilote commun (0–139) sont converties en pixels HGR (0–278) pour la main.

Le programme reste en **assembleur 6502**. Il n'a pas été réécrit en C et
conserve ses adresses fixes, son code automodifiant et ses modules superposés.
La factorisation vers les bibliothèques DEVBENCH sera une étape ultérieure.

PCS utilise une carte mémoire propre : tables à `$0800-$177F`, routines
graphiques à `$1780`, changement de modules à `$1E00`, HGR à `$2000`, données
de table à `$4000`, pilote souris à `$6300-$67FF`, tables du moteur à `$6800-$6B7F`,
tampon graphique à `$6B80-$6FFF`,
bitmaps à `$7000`, moteur à `$7700`, conversion de polygones
à `$8E20` et éditeur/câblage/fichiers à `$9500`. `RUN2` est le module pour les
tables jouables autonomes, chargé à `$8554` ; il remplace une partie du moteur.
La configuration habituelle d'un binaire DEVBENCH à `$6000` ne convient donc
pas à ce programme.

`tools/build_disk.py` utilise le constructeur DOS partagé
`../dev/tools/dos33.py` pour le catalogue et le bitmap d'allocation, puis
place les modules aux secteurs attendus par le chargeur de PCS.
Les pistes 0 à 15 sont réservées au programme : les sauvegardes ne peuvent
pas les réutiliser. Le disque fait **140 Ko**, en ordre DOS 3.3, et dispose
de **288 secteurs libres**. Le démarrage est propre à PCS, sans accueil BASIC.

## Construire et lancer

Depuis la racine du dépôt :

```sh
make -C flipper             # dist/FLIPPER.dsk
make -C flipper run         # POM2, Apple II+, AppleMouse en slot 4
make -C flipper run-iic     # POM2, Apple //c, souris native
make -C flipper test        # tests sur a2run
make -C flipper clean       # retire build/, conserve la disquette
```

`make` à la racine construit aussi FLIPPER. Le profil est **Apple II+ 48 Ko,
HGR et Disk II**, avec **AppleMouse II** optionnelle. `make run` installe une
carte `mouseaw` en slot 4. **La même disquette fonctionne sur Apple //c**
avec sa souris native ; `make run-iic` sélectionne ce profil dans POM2.
La carte `mouse` fonctionne également sur les machines à slots :

```sh
make -C flipper run APPLE2_RUN_FLAGS="--slot 4=mouse"
```

La souris déplace la main ; le bouton principal prend, déplace et dépose les
pièces, sélectionne les outils et pilote les menus de câblage et de fichiers.
Sans souris détectée, le programme garde les contrôles par paddles/manette.
La commande `PLAY` de la palette teste la table ; **Échap** revient à l'éditeur.
Les batteurs et le lanceur du moteur original gardent leurs commandes de
manette. Les commandes `SAVE` et `LOAD` utilisent les fichiers natifs `.PB`.
La table initiale est vide : placer une bille et les pièces avant de jouer.

Après une reconstruction, réinsérer la nouvelle image et redémarrer l'Apple II
pour charger le pilote. Pour un lancement manuel dans POM2, installer une
carte AppleMouse (`mouseaw` ou `mouse`) en slot 4 sur II+, ou sélectionner
le profil //c et sa souris native (`iicmouse`).

## Validation

`tests/test_flipper.py` utilise le harnais DEVBENCH `a2test.py` et `a2run`.
Il démarre la disquette, prend une bille dans la palette, la déplace dans
la table, vérifie qu'elle bouge pendant le jeu, revient par Échap, ouvre et
ferme le câblage, sauvegarde `TEST.PB`, recharge ses trois objets et revient
à l'éditeur. Il vérifie aussi les empreintes des blocs importés, la réservation
des pistes du programme et leur intégrité après la sauvegarde.
Les captures et la disquette de test modifiée restent dans `build/`.
Le démarrage et le passage au jeu ont également été vérifiés avec `a2shot`,
sur le cœur de POM2.

`make -C flipper test-mouse` valide les deux cartes `mouseaw` et `mouse` sur
Apple II+ 6502 avec leurs ROM réelles, ainsi que la souris native du //c
avec ses ROM de 16 et 32 Ko, son processeur 65C02 et son contrôleur IWM.
Ce test optionnel utilise la bibliothèque
`libpom2_core_test.a` d'un POM2 construit, avec `POM2_SRC=chemin/vers/pom2`.
Il injecte les mouvements et clics dans la carte, vérifie le curseur HGR,
le déplacement d'une bille, PLAY/Échap, les changements de modules,
SAVE/LOAD et le retour de la souris après les effacements des buffers DOS.
Le test ordinaire `make test` conserve sa validation sans carte souris.
