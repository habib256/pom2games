# MCS — éditeur musical Apple II

Version **0.1**, réimplémentation originale inspirée de **Music Construction
Set** de Will Harvey. Elle utilise les bibliothèques du dépôt et fonctionne
sur Apple II+ 48 Ko avec DOS 3.3. Disquette amorçable :
[`../dist/MCS.dsk`](../dist/MCS.dsk).

## Recherche des sources

Recherche effectuée le 9 octobre 2026. Aucun dépôt public des sources de
l'éditeur Apple II complet n'a été trouvé. Cela ne prouve pas que ces sources
n'existent pas ailleurs. Deux projets voisins ont été identifiés :

- [cybernesto/mcs-player](https://github.com/cybernesto/mcs-player) : sources
  du lecteur à interruptions pour Mockingboard, Echo+ et Cricket. Le README
  précise qu'il s'agit du code fourni avec la première version compatible
  Mockingboard, initialement incomplet, et d'une reconstruction du lecteur.
  Ce n'est pas le code de l'éditeur complet.
- [chjmartin2/MCS-Convert](https://github.com/chjmartin2/MCS-Convert) : lecteur,
  éditeur et documentation issus de la rétro-ingénierie de la version
  **IBM PC**. Son format n'est pas une spécification des fichiers Apple II.

Le [manuel Apple II original](https://mirrors.apple2.org.za/ftp.apple.asimov.net/documentation/applications/misc/EA_Music_Construction_Set_1987.pdf)
reste une référence pour les fonctions du logiciel historique.

Cette version ne contient ni code, ni graphismes, ni morceaux extraits des
disquettes Electronic Arts. Le code ajouté est GPL-3.0, comme le dépôt.
L'exercice musical de départ est une gamme ascendante puis descendante avec
accompagnement, créée pour cette version. Police et composants Apple DOS :
voir les crédits du [dépôt](../README.md#licences-et-crédits).

## Construire et utiliser

```sh
make -C mcs           # produit dist/MCS.dsk
make -C mcs run       # démarre la disquette dans POM2
make test-mcs         # tests dans a2run
```

Prérequis : cc65 2.19 et Python 3 ; compilateur C pour reconstruire a2run.
Aucun téléchargement pendant la construction. La disquette charge
automatiquement la partition `SONG` au démarrage.

L'écran affiche deux portées, 16 positions par page et quatre pages. Le cadre
indique la hauteur d'insertion ; le soulignement indique le pas courant.
`T` représente la portée aiguë (clé de sol) et `B` la portée basse (clé de fa).
Les lettres de notes sont internationales : C = do, D = ré, E = mi,
F = fa, G = sol, A = la, B = si. `*` signale les modifications non sauvegardées.

| Touche | Action |
|---|---|
| J / K ou gauche / droite | Pas précédent / suivant ; changement de page automatique |
| I / M ou haut / bas | Hauteur précédente / suivante dans la gamme de do majeur |
| + / - | Monter / descendre d'un demi-ton, avec dièse à l'écran |
| Tab ou V | Changer de voix / portée |
| Entrée | Poser ou remplacer la note au pas courant ; étendre la partition si nécessaire |
| R ou X | Effacer la note de cette voix : silence |
| D | Durée commune aux deux voix : 1, 2, 4 ou 8 croches |
| [ / ] | Tempo -5 / +5 BPM, entre 40 et 240 |
| F | Fixer la fin au pas courant, inclus |
| A | Écouter la hauteur sélectionnée |
| Espace | Jouer depuis le début ; toute touche arrête la lecture |
| S / L | Sauvegarder / recharger `SONG` sur la disquette |
| N | Nouvelle partition vide de 16 pas |
| ? | Aide ; une touche revient à l'éditeur |
| Échap | Retour à DOS |

Pour N, L et Échap, une partition modifiée déclenche une confirmation.
O ou Y confirme, toute autre touche annule. Les positions après la fin restent
en mémoire et sauvegardées ; F permet de les inclure à nouveau. Un pas occupe
le temps indiqué sous la portée, quelle que soit la présence de notes.

## Son et limites de la version

Deux oscillateurs carrés 16 bits sont combinés par XOR sur le haut-parleur
un bit de l'Apple II, sans carte son. Le timbre des accords est rugueux ; ce
n'est pas la synthèse de l'original ni une sortie Mockingboard. Les unissons
sont ramenés à un oscillateur pour éviter leur annulation. La portée aiguë
couvre C4–B5, la basse C2–B3. La boucle assembleur est alignée sur une page,
à 68 cycles par échantillon et 256 échantillons par bloc. La table de hauteurs
est calculée pour 1 020 484 Hz ; la machine doit tourner à vitesse Apple II.

Le tempo est approximatif : arrondi à un bloc d'environ 17 ms, avec un peu
de temps supplémentaire pour le contrôle et le dessin lors du changement
de page. Le test d'audition mesure environ 435 Hz pour le la 440 Hz nominal,
en incluant les interruptions entre blocs. Le CPU est occupé par le son ;
le clavier est vérifié entre les blocs.

Cette version propose 64 pas, deux notes simultanées et une durée commune
par pas. Elle ne propose pas encore de souris, glisser-déposer, armures,
liaisons, rythmes indépendants, impression ou instruments supplémentaires.
Elle sauvegarde une seule partition nommée `SONG`, dans son propre format :
**les fichiers historiques MCS ne sont pas compatibles**.

La disquette doit conserver un fichier `SONG` lisible. Un contenu au format
invalide est refusé sans remplacer les modifications en cours. La protection
en écriture est détectée avant sauvegarde. Les autres erreurs DOS, comme un
fichier supprimé ou un disque plein, sont traitées par DOS et peuvent ramener
au prompt BASIC. Conserver une copie de la disquette pour chaque composition.

## Format et mémoire

`SONG` est un fichier binaire DOS 3.3 de 200 octets, chargé à `$1000`.
Son en-tête DOS de quatre octets n'est pas inclus dans ces offsets.

| Offset | Taille | Contenu |
|---|---:|---|
| 0 | 4 | Signature ASCII `P2MC` |
| 4 | 1 | Version : 1 |
| 5 | 1 | Tempo : 40–240 BPM |
| 6 | 1 | Nombre de pas : 1–64 |
| 7 | 1 | Réservé : 0 |
| 8 | 64 | Notes MIDI de la voix aiguë : 60–83, ou 0 pour silence |
| 72 | 64 | Notes MIDI de la voix basse : 36–59, ou 0 pour silence |
| 136 | 64 | Durées : 1, 2, 4 ou 8 croches |

Le rechargement utilise un tampon à `$1100`, validé avant copie. Le Makefile
dérive la configuration commune `apple2_hgr_c.cfg` pour placer les BSS à
`$1200–$1FFF` et aligner CODE à 256 octets. Les pages HGR restent à
`$2000–$5FFF`, le programme à `$6000`, la pile C à `$8E00–$95FF` et DOS à
`$9600–$BFFF`. Les bornes sont contrôlées par ld65.

## Validation

`make test-mcs` démarre la vraie disquette et vérifie l'écran HGR, les deux
voix, durées, tempo, dernière page, confirmations, sortie DOS, sauvegarde,
redémarrage et rechargement, rejet de données invalides et protection en
écriture. Les accès réels à `$C030` vérifient le son et la hauteur du la,
les silences et l'arrêt de la lecture. Validation sous émulation ; essais
sur matériel physique encore à effectuer.
