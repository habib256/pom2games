# Évaluation de techniques HGR

Cette suite compare **fhpack**, **fdraw** et un prototype de **sprites compilés**
aux chemins existants de `pom2games`. Les prototypes restent dans les tests ;
aucune bibliothèque de production ne les utilise.

```sh
make test-techniques
python3 dev/tests/techniques/run.py --suite graphics
python3 dev/tests/techniques/run.py --suite sprites
python3 dev/tests/techniques/run.py --suite compression --out /tmp/compression.json
```

`make test` inclut `test-techniques`. La commande dédiée reconstruit les deux
disquettes utilisées pour les captures. Prérequis : cc65, Python 3, un
compilateur C pour a2run et un compilateur C++ pour fhpack. Aucun téléchargement
ni module Python externe n'est nécessaire. Les programmes, disquettes et
mesures générés sont dans `build/`, ignoré par Git.

## Résultats et décisions

Mesures du 7 octobre 2026 : cc65 V2.18, `-Oirs`, CPU **NMOS 6502 dans a2run**.
Les données détaillées sont dans [RESULTS.json](RESULTS.json).
La suite a validé **123 scénarios de comparaison, soit 304 exécutions mesurées**.
Les temps en millisecondes sont des cycles émulés convertis à 1 020 484 Hz,
pas des durées d'exécution sur le Mac.

| Technique | Résultat | Décision proposée pour `dev` |
|---|---|---|
| fhpack | Quatre captures de jeux : 8 Ko deviennent 637–1 747 octets ; chargement DOS avec décompression 2,57–3,19 fois plus rapide | **À intégrer comme option de la chaîne d'assets**, avec conservation du fichier brut si la compression l'agrandit |
| Lignes fdraw | 10,4–14,4 fois plus rapides sur les grandes diagonales de l'API C ; 2,4–2,7 fois face à l'assembleur de maze3d | **Portage ciblé des lignes à envisager** ; vérifier les choix de pixels et préserver le contrat des coordonnées |
| Rectangles et effacement fdraw | Environ 1,3–1,4 fois plus rapides ; package complet FAST de 5 108 octets | **Ne justifie pas un remplacement global** des primitives actuelles |
| Sprites compilés, dessin seul | Environ 2,6–4,4 fois plus rapides à la position représentative ; +1,3 à +4,6 Ko par forme à sept phases | **Option pour quelques sprites très fréquents**, quand le budget mémoire le permet |
| Sprites compilés avec sauvegarde/dessin/restauration | Rapport de vitesse 0,95–1,01 sur les trois formes synthétiques ; 0,99 sur le vaisseau des démos | **Conserver le moteur masqué actuel** pour l'animation sur décor |

### Compression et chargement

| Capture HGR | Brut | fhpack `-9 -h` | BLOAD brut | BLOAD + décompression |
|---|---:|---:|---:|---:|
| Arkabreakout, titre | 8 192 o | 1 373 o | 5 036 ms | 1 826 ms |
| Arkabreakout, après espace | 8 192 o | 637 o | 5 036 ms | 1 654 ms |
| Micro-sokoban, titre | 8 192 o | 1 747 o | 5 036 ms | 1 961 ms |
| Micro-sokoban, après espace | 8 192 o | 785 o | 5 036 ms | 1 580 ms |

Les captures viennent de la mémoire HGR des disquettes actuelles, après
`wait:1100`, ou `wait:1100 key:" " wait:60`. Leurs SHA-256 sont enregistrés.
« Après espace » désigne cette séquence exacte, sans supposer un état de jeu.
Le corpus ajoute une image vide, un motif répétitif et du bruit déterministe.
Le bruit grossit à **8 292 octets** : un futur outil doit conserver le brut
dans ce cas.

Le décompresseur FAST occupe **194 octets**, contre **186** pour SMALL.
Sur les captures de jeux, la décompression seule prend environ
158–173 ms. Une copie RAM déroulée de l'image brute prend environ **74 ms**
(75 520 cycles). La compression accélère donc le **chargement disque** et
réduit le stockage ; elle ne remplace pas une copie RAM rapide pour chaque
image d'une animation.

Les tests disque utilisent réellement le BLOAD de DOS 3.3, avec un binaire de
démarrage de même taille dans les deux variantes pour conserver le placement
du fichier IMAGE. Le chemin comprimé charge en page 1, puis décompresse en
page 2. Il emploie donc une page vidéo comme tampon temporaire. Une intégration
doit choisir un tampon source compatible avec le jeu et le double tampon.
Les temps concernent le Disk II d'a2run et cette disposition de fichiers ;
ils ne prédisent pas les temps d'un disque dur ProDOS ou d'un autre chargeur.

### Primitives graphiques

| Opération, page 1 | Actuel | fdraw FAST | Rapport |
|---|---:|---:|---:|
| Ligne horizontale 280 px | 3 771 cycles | 903 | 4,18 |
| Ligne verticale 192 px | 13 215 | 8 581 | 1,54 |
| Diagonale (0,0) → (279,191), API C | 270 506 | 25 981 | 10,41 |
| Rectangle 140 × 16 | 6 867 | 5 317 | 1,29 |
| Effacement HGR | 53 561 | 39 789 | 1,35 |
| Grande diagonale de maze3d, assembleur extrait | 45 419 | 16 771 | 2,71 |

fdraw FAST et SMALL sont compilés à partir des sources Merlin épinglées.
`merlin.py` adapte les directives, les labels locaux et le placement à ca65.
Les instructions et les algorithmes sont conservés. Les 16 octets de scratch
privés de fdraw sont alloués hors du scratch cc65, et le segment est aligné.
Les deux variantes incluent ici **tout le package** : 5 108 octets pour FAST,
4 352 pour SMALL. Un portage d'une seule famille pourrait réduire ce coût ;
ce gain potentiel n'est pas mesuré ici.

Les lignes sont contrôlées pour leurs extrémités, leur nombre de points, leur
connexité et leur distance à la ligne idéale. Certains choix d'arrondi diffèrent
du Bresenham actuel : le cas inversé produit six pixels différents. Les tests
enregistrent cette différence sans la confondre avec une ligne incorrecte.
Les rectangles sont comparés octet par octet sur les lignes visibles.
L'effacement fdraw ne traite pas les trous mémoire comme `hgr_clear` : le
résultat visible est identique, mais 512 octets de trous diffèrent en FAST.

La comparaison maze3d extrait **la routine réellement utilisée par le jeu**.
Elle est aussi vérifiée contre un Bresenham indépendant. Le jeu transforme
ses coordonnées virtuelles de huit pixels en groupes de sept pixels HGR ;
fdraw travaille directement dans les coordonnées HGR. Les tracés diffèrent
donc davantage : un remplacement dans le jeu demande une validation visuelle,
même lorsque les extrémités coïncident.

### Sprites compilés

| Forme / opération, x=45 | Actuel | Compilé | Rapport | Binaire supplémentaire |
|---|---:|---:|---:|---:|
| Vaisseau 8 × 8, XOR | 1 198 cycles | 461 | 2,60 | 1 336 o |
| Vaisseau 16 × 16, masqué | 4 173 | 943 | 4,43 | 3 516 o |
| Tuile 16 × 16, masquée | 4 173 | 1 208 | 3,45 | 4 572 o |
| Vaisseau réel des démos 21 × 9, XOR | 1 759 | 584 | 3,01 | 1 821 o |
| Vaisseau 16 × 16, sauvegarde/dessin/restauration | 8 090 | 8 007 | 1,01 | 3 519 o |

Le prototype génère sept routines déroulées, avec données et masques immédiats
et omission des octets transparents. C'est une **implémentation originale de
la technique de HiSprite**, adaptée à notre ABI ; le générateur Python 2 de
HiSprite n'est ni copié ni exécuté.

La référence est le noyau assembleur rapide des sprites prédécalés actuels,
avec la même préparation des paramètres. Pour le cycle sur décor, la référence
emploie `hgr_msu_run`, qui combine sauvegarde et dessin, puis restaure le décor.
Le prototype doit sauvegarder séparément, dessiner, puis restaurer : ce travail
efface presque tout le gain du dessin compilé.

Les sept phases, les coordonnées au-delà de 255, les deux pages, la conservation
du bit de palette et le clipping droit/bas sont vérifiés. Aux bords, le
prototype revient au noyau générique : ces cas ne gagnent pas en vitesse.
Les gains cités concernent le dessin seul, sans gestion d'un moteur complet
à plusieurs sprites, changement de page ou attente de VBL.

## Contrôles et limites

- Les marqueurs excluent l'initialisation et les douze cycles des appels de
  mesure. Les coûts des paramètres et des appels restent inclus.
- Les tests vérifient le framebuffer, la page inactive et, sauf pour
  l'effacement fdraw, les trous mémoire. La compression avec `-h` doit restituer
  les 8 192 octets exactement, en page 1 et en page 2.
- Les rapports conservent cycles, tailles liées, RAM et zéro-page, compilateur,
  révisions et empreintes des sources amont. Les tailles sont celles des
  programmes de test complets ; elles ne comptent pas les pages vidéo ni la
  pile C réservée. Le champ `code_bytes` inclut tout le segment FDRAW, donc ses
  tables et buffers internes aussi.
- Les tests échouent sur un résultat incorrect. Ils ne fixent pas de seuil
  automatique de vitesse : cette suite sert à évaluer des candidats, tandis
  que `make bench-check` garde les budgets des bibliothèques de production.
- Cette évaluation porte sur HGR / 6502. Aucun résultat n'est extrapolé à DHGR,
  au 65C02 ou au IIgs.

Les chargeurs qboot/prorwts et le prototype a2render ne sont pas inclus : les
trois priorités retenues sont compression HGR, primitives rapides et sprites
compilés. Évaluer les chargeurs demanderait un format disque et un contrat de
chargement précis ; a2render demanderait un prototype de rendu texturé distinct.

## Recherche DHGR — 8 octobre 2026

Une exploration séparée a confronté ces techniques au code DHGR du dépôt.
Les prototypes sont restés dans `/tmp/pom2-dhgr-research`, sans modification
des bibliothèques ni des références de performance. Les mesures ci-dessous
utilisent cc65 `-Oirs` et le 65C02 du cœur IIe d'a2shot.

### Effacement : gain mesuré

Un prototype déroule les écritures sur les 32 blocs de 256 octets d'une banque,
avec adressage absolu indexé et deux chemins pour les deux pages vidéo. Il
conserve les quatre octets du motif couleur et traite les trous mémoire comme
la routine actuelle. Comme elle, il masque les interruptions pendant l'opération.

| Effacement, couleur 9 | Actuel | Prototype | Rapport |
|---|---:|---:|---:|
| Page 1, main + aux | 207 861 cycles | 88 171 cycles | 2,36 |
| Page 2, main + aux | 207 861 cycles | 88 169 cycles | 2,36 |

Le programme lié gagne 393 octets de code, sans augmentation de RAM ni de
zéro-page. Chaque variante a passé 33 contrôles : les 16 couleurs sur chacune
des deux pages, puis un motif `$FF` conservant le bit 7. Les contrôles comparent
les 32 Ko vidéo (pages actives et inactives, main et aux, trous inclus) et
vérifient que RAMRD/RAMWRT reviennent en main. Ce gain concerne l'effacement,
pas la cadence complète d'un jeu ; CHROMABREAK ne redessine pas tout son écran
à chaque image.

### fhpack : compression possible, chargement non mesuré

Chaque capture DHGR de 16 Ko a été séparée en deux banques de 8 Ko, compressées
avec `fhpack -c -9 -h`, puis décompressées sur l'hôte et comparées octet par
octet, bit 7 et trous inclus.

| Capture de la page affichée | Brut | Deux flux comprimés |
|---|---:|---:|
| Introduction de DHGR.dsk | 16 384 o | 1 212 o |
| Animation de DHGR.dsk | 16 384 o | 1 490 o |
| Titre de CHROMABREAK.po | 16 384 o | 2 511 o |
| CHROMABREAK après espace | 16 384 o | 3 559 o |

Séquences : `wait:2600`, puis pour l'animation `key:" " wait:1800`, et pour
CHROMABREAK après espace `key:" " wait:600`. La page est sélectionnée selon
le softswitch PAGE2. Ces noms décrivent les séquences, sans vérifier l'état
interne du jeu.

Le décodeur 6502 amont lit les références LZ dans la destination : activer
seulement RAMWRT aux ne suffit donc pas. Une première intégration pourrait
décompresser chaque banque dans un tampon main compatible avec `$2000` ou
`$4000`, puis transférer la banque auxiliaire. Un décodeur direct aux exigerait
une gestion distincte des lectures de source, des lectures de références et
des écritures, ainsi qu'une exécution sûre lors des commutations RAMRD.
Le chargement ProDOS complet, le tampon et le transfert aux restent à mesurer.
Ces écrans sont aujourd'hui construits par du code : les compresser serait une
nouvelle stratégie de présentation, pas l'accélération d'un chargement d'image
brute déjà présent dans CHROMABREAK.

### Lignes, rectangles et sprites : pistes de portage

fdraw cible le HGR 280 × 192. Ses principes (adresses incrémentales, masques
préparés, boucles spécialisées) peuvent guider un moteur DHGR, mais ses routines
ne se substituent pas directement aux nôtres. `gfx_line.c` passe encore par
`gfx_plot` pour chaque point diagonal ; le backend couleur passe ensuite par
un rectangle 1 × 1. C'est une cible plausible, sans facteur de vitesse mesuré.
Les spans génériques commutent aussi les écritures aux octet par octet : un
traitement séparé de main et aux mérite un prototype préservant les bords.

Les sprites compilés pourraient spécialiser les données et les masques et
regrouper les écritures par banque. Leur intérêt doit être mesuré avec
sauvegarde, dessin et restauration. CHROMABREAK dispose déjà d'un moteur
assembleur avec boucle miroir main/aux, masques précalculés et sauvegarde
combinée au dessin : les gains HGR ne s'y transposent pas automatiquement.
Ses contraintes d'adresses figées et son bit 7 de mode RGB mixte doivent être
préservés.

Sources techniques : [manuel fdraw](https://github.com/fadden/fdraw/blob/master/docs/manual.md),
[fhpack](https://github.com/fadden/fhpack),
[format des sprites DHGR de Bmp2DHR](https://www.appleoldies.ca/bmp2dhr/sprites/).

## Provenance

- [fdraw](https://github.com/fadden/fdraw/tree/a1657e8e4d4b19f62497228d070c699c19e96cde),
  Andy McFadden, Apache-2.0, sources et licence conservées dans `upstream/fdraw`.
- [fhpack](https://github.com/fadden/fhpack/tree/18988e93ea7da79f837453e361b84395c4bd06a1),
  Andy McFadden ; décompresseur optimisé par Peter Ferrie, Apache-2.0,
  sources et licence conservées dans `upstream/fhpack`.
- [HiSprite](https://github.com/blondie7575/HiSprite), Quinn Dunki : référence
  pour le principe des sprites compilés. Aucune licence explicite repérée dans
  ce dépôt ; aucun de ses fichiers n'est repris.
- Les formes des démos et la routine maze3d viennent de ce dépôt, GPL-3.0.
  Les scripts et prototypes nouveaux suivent la licence GPL-3.0 de pom2games.
