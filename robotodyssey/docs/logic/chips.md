# Puces : format, gravure, stockage, bibliothèque

*[← ANALYSE](../ANALYSE.md)* · voir aussi [lessons.md](lessons.md) (leçon
Chip Design, Innovation Lab), [simulation.md](simulation.md) (moteur),
[world.md](world.md) (objets, textes)

Une **puce prototype** est un grand objet dans lequel on entre (une salle
avec 8 broches) et qu'on câble avec les pièces de la boîte à outils. La
**gravure** (*burn*) la compile en un **programme** rangé dans l'une des 8
**petites puces**, qui ne s'ouvrent plus mais s'utilisent comme une pièce à
8 broches, se sauvent sur disque, se rechargent et s'imbriquent. Ce document
décrit les données ; le moteur de simulation général est dans
[simulation.md](simulation.md).

Établi sur les octets de l'Apple II (face B : `build/B_LABS.po`, segments
`build/files/B_LABS/*`, images `tools/memimg.py innovation|chipdesign`) et
dans a2shot (Innovation Lab, écran de chargement de puce). La rétro-ingénierie
de la version PC (Micah Dowty) n'a pas été consultée pour ce document.

Outil : `tools/chips.py`

```sh
python3 -I tools/chips.py library            # bibliothèque complète (face B)
python3 -I tools/chips.py code build/files/B_LABS/0A6_D000.bin 0200000000000000
python3 -I tools/chips.py sim 3 9 1=1        # puce 3 de la bibliothèque, 9 cycles, broche 1 à 1
```

## Les 8 petites puces en mémoire

| Donnée | Adresse | Remarques |
|---|---|---|
| programme de la puce *n* | `$D000 + $400·n`, **banque 1** de la carte langage | 1 Ko par puce, `$D000-$EFFF` en tout ; table des octets hauts en `$F000-$F007` (`D0 D4 D8 DC E0 E4 E8 EC`) |
| sens des broches | `$F008 + 8·n` | 0 neutre, 1 entrée, 2 sortie (vues de l'extérieur) |
| longueur du programme | `$7A98+n` (bas), `$7AA0+n` (haut) | dans le monde du labo (= `$79B1/$79B9` indexés par l'objet `$E7+n`) |
| fiche (*record*) | `$8045 + $12B·n` | dans le tas de textes du labo (table `$4FFF/$5007` du module résident) : titre 19 octets + 8 lignes de 35 |
| objet | `$E7 + n` | sprite `$21 + n` (puces numérotées 1-8 dans la *Burner Room*) |

Le programme d'une puce commence par ses 8 broches : **l'adresse de base
d'une puce est l'adresse de la valeur de sa broche d'indice 0**.

### Broches : numérotation

Les broches sont numérotées comme un boîtier DIL vu de dessus : 1-4 en
descendant à gauche, 5-8 en montant à droite (8 en haut à droite ; texte
« 1/2/3/4 » et « 8/7/6/5 » de la salle `$07` de Chip Design). L'**indice**
dans les tables suit la position à l'écran, colonne gauche puis colonne
droite, de haut en bas :

| Indice | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| Broche | 1 | 2 | 3 | 4 | **8** | **7** | **6** | **5** |

Vérifié sur quatre puces de la bibliothèque dont la fiche décrit les
broches : Full Adder (somme sur 7, retenue sur 8), Delay Line (broche *k*
retardée de *k−1* cycles, simulation `tools/chips.py sim 3`), One Shot et
Wall Hugger (sens des broches alternés entrée/sortie conformes à la fiche).

## Format du programme

Toutes les références sont des **décalages de 16 bits, octet haut d'abord**,
relatifs à la base de la puce courante. Les valeurs (0/1) des entrées de
chaque porte sont stockées **dans le programme lui-même** : un « fil » est
simplement l'adresse de l'octet d'entrée qu'une sortie doit écrire.

```
+0..+7           valeurs des 8 broches (indices ci-dessus)
enregistrements :
  01 a b  SORTIES FF                 ET    (02 OU, 03 OU exclusif)
  04 a    SORTIES FF                 NON
  05 s r q /q  SORTIES(q) FF SORTIES(/q) FF     bascule
  06 <puce imbriquée : 8 broches, enregistrements, section 07>
  07 { SRC DST DST … FF } … FF       fin : copies
SORTIES = suite de décalages (2 octets) terminée par FF
```

Interprète : `$1BAF` au labo (bloc `$0A7`, `$0B00-$1F9A`), `$F208` dans
Robotropolis ([simulation.md](simulation.md)). Un octet d'opcode inconnu est
sauté (`$1BE4`).

| Code | Calcul | Détail |
|---|---|---|
| 1, 2, 3 | `a AND/ORA/EOR b` | `$1C09`, `$1C19`, `$1BF9` |
| 4 | `(a EOR 1) AND 1` | `$1BE8` |
| 5 | bascule | `$1C2A` : lit puis **remet à 0** les deux entrées ; `s=1,r=0` met `q=1,/q=0`, `s=0,r=1` met `q=0,/q=1` (seulement si `q`/`/q` étaient cohérents), `s=r` ne change rien ; envoie `q` puis `/q`. `q` et `/q` sont les deux moitiés de la bascule de la boîte à outils, `s` et `r` leurs entrées |
| 6 | puce imbriquée | `$1DBC` : empile la position (`$F049` profondeur, `$F072/$F04A` adresses), applique les écritures différées, prend la puce imbriquée comme nouvelle base et l'exécute ; à sa fin (`$1D5D`), la base du parent est restaurée et le parent continue après elle |
| 7 | fin | `$1D11` : pour chaque groupe, copie l'octet `SRC` dans chaque `DST`, immédiatement ; un `FF` en tête de groupe termine la puce |

**Écritures différées** (`$1C80-$1CDD`) : quand une sortie vise un octet
situé *à partir* de l'enregistrement courant (porte pas encore évaluée),
l'écriture est empilée et faite à la fin de la puce (`$1D92`, dernière
empilée appliquée en premier) ou avant une puce imbriquée ; sinon elle est
immédiate. La comparaison est faite octet par octet (haut puis bas), pas sur
16 bits. Effet : **chaque porte ajoute exactement un cycle de retard**,
quel que soit l'ordre des enregistrements. `tools/chips.py sim` reproduit ce
comportement.

Rôle de la section `07` produite par la gravure : distribuer aux portes les
valeurs qu'elles ne reçoivent pas d'une autre porte, c'est-à-dire les
**broches d'entrée** de la puce et les **sorties des puces imbriquées**.
Les portes écrivent elles-mêmes dans les broches de sortie et dans les
broches d'entrée des puces imbriquées.

Exemple : la petite puce de la leçon Chip Design (bloc `$0A6`, 19 octets,
broche 1 en sortie) est une porte NON rebouclée sur elle-même qui fait
clignoter la broche 1 :

```
00 00 00 00 00 00 00 00   broches
04 00 | 00 09 00 00 FF    NON : entrée +9 ; sorties +9 (elle-même) et +0 (broche 1)
07 FF                     fin
FF FF                     (reste, compté dans la longueur)
```

Taille maximale : la gravure refuse un programme de `$3DF` octets ou plus
(`$93FE`), il tient donc dans le Ko de la puce.

## Gravure (*burn*)

Code dans le monde du labo (`$8990-$94FF`, segment `$0C6` ou `$0E3`),
appelé à chaque trame par `$9345` (boucle `$0879` de l'Innovation Lab).

Conditions (`$935B-$93DA`, `$9449`, `$946F`, `$94BE`) :

- le joueur est dans la salle `$06` (*Burner Room*) ;
- la puce prototype (objet `$01`) est dans la salle `$06`, X ∈ [`$14`,`$3C`[,
  Y ∈ [`$38`,`$80`[, et ses 8 broches extérieures ne sont reliées à rien
  (`$0B01-$0B08`, `$F343`) ; le jeu la recale en (`$18`, `$5C`) ;
- une petite puce (`$E7-$EE`, `$1F74`) est dans la zone X ∈ [`$4C`,`$64`[,
  Y ∈ [`$28`,`$52`[ sans fil sur ses broches ; recalée en (`$58`, `$38`) ;
- le joueur est assis sur le bouton BURN (X ∈ [`$70`,`$81`[, Y ∈
  [`$10`,`$23`[) et appuie sur `ESPACE` (`$1300`).

Puis :

1. `$908D` lance l'animation (`$F048` = 7, couleurs de la puce `$70DC`) ;
2. `$90CC` parcourt le circuit de la salle intérieure du prototype (`$0C`)
   depuis ses broches et dresse la liste des portes et bascules (`$76B0`,
   ordre de parcours) et des puces imbriquées (`$7A80`) ;
3. `$89B0` calcule la taille et la position de chaque enregistrement (tables
   `$770C/$7768`) et de chaque puce imbriquée (`$7A88/$7A90`) ; si trop
   grand, `$7AEE = $0B` et abandon ;
4. banque 1 en écriture, `$8AA3` écrit les portes (`$8B4B` : opcode
   `$119B` selon le type de la pièce, valeurs d'entrée courantes, sorties
   vers les entrées de portes `$8BF6` et vers les broches `$8C41`) et les
   bascules (`$8BA0`, code 5, état courant des deux moitiés), puis chaque
   puce imbriquée (`06` + **copie intégrale** de son programme, `$8B28`) ;
5. `$8E20` écrit la section `07` (`$8FF1` broches d'entrée du prototype,
   puis sorties des puces imbriquées) et le `FF` final ; la longueur va en
   `$79B1/$79B9` ;
6. `$906D` copie l'état des 8 broches intérieures dans les 8 premiers
   octets, `$9319` écrit le sens des broches (`$F008+8n`) d'après le type
   des objets broches intérieurs (table `$7AEF` : 0, 2, 1).

Une puce imbriquée étant recopiée, graver une puce qui en contient une
autre fige la version de celle-ci au moment de la gravure. `$0A87` (appelé
par `$0A69`/`$0A77`) remet une puce à vide : 11 octets `$1F69`
(`00×8 07 FF FF`), longueur `$0B`, sens des broches à 0.

## Échanges avec l'extérieur

À chaque trame, si la télécommande est en marche (`$128F = 1`), `$1F12`
exécute les 8 programmes (puce 7 à 0, base `$F000+n`, `$20 = base+8`), puis
`$1DF4` (et `$1F46`) échange les broches avec les objets câblés : broche
d'entrée (`$F008 = 1`) ← couleur de l'objet relié (`$1182`, table `$1540`
couleur → 0/1) ; autre broche reliée → couleur de l'objet (`$1548`), ou
entrée de bascule (`$0FEF`) pour les objets `$25-$38`, ou octet de broche
d'une autre puce (`$1ECD`). `$1F50` remet la couleur 6 (bleu) aux puces
sauf celle en cours de gravure. Même schéma dans le jeu (`$F56B`/`$F44D`,
[simulation.md](simulation.md)).

## Stockage sur disque

Les puces sont lues et écrites par le **module résident** (`$4000`), pas par
le labo : `L` ou `S` en tenant une petite puce range le mode dans `$02D0`
(5 charger, 6 sauver) et le numéro de puce dans `$02D1`, puis redémarre à
chaud ([lessons.md](lessons.md)). Disposition (identique sur la bibliothèque
et sur un disque de stockage) :

| Bloc | Contenu |
|---|---|
| `$008` | **catalogue** : 26 noms de 18 octets (ASCII bit 7, 15 caractères saisis + espaces), 13 par moitié de bloc ; nom *k* en `$5A00 + (k div 13)·$100 + (k mod 13)·18` (table `$4FCB`) |
| `$009+3k`, `$00A+3k` | programme de la puce *k* (1 Ko, lu tel quel en `$D000+$400·slot`, banque 1) |
| `$00B+3k` | en-tête : `+0..+7` sens des broches, `+8/+9` longueur (LE), `+$0A..+$134` fiche (`$12B` octets : titre 19 + 8 × 35) |

Calcul des blocs : `$477A` (bloc = 6 + 3·(k+1)) ; pour *k* ≥ 13, base
`$5C3` au lieu de 6 (blocs `$5ED-$613`), ce qui suppose un support de plus
de 1 500 blocs : *probablement un disque 3,5" de 800 Ko*. Le choix offre 13
lettres (`A`-`M`) ou 26 (`A`-`Z`) selon le type du périphérique (`$47D9`,
table `$D0,x`) ; sur une disquette 5,25" on a donc **13 puces par disque**.

### Chargement (`$4260`, mode 5)

1. « Insert Robot Odyssey or STORAGE disk with saved chips and press RETURN
   OR To load a chip from the Library, press L » (vérifié en capture
   `build/les/inno10.png`) ; `RETURN` → `$4CA8` avec `$11`, `L` → avec `$01`
   (choix du lecteur, *détail : analyse du chargeur*) ;
2. lecture du catalogue (bloc 8 → `$5A00`), affichage « Chip Library » ou
   « Chip » + liste, « Press letter of chip to load » (`$47F1`) ;
3. lecture du programme (2 blocs → `$D000+$400·slot`, banque 1) et de
   l'en-tête (→ `$5C00`) ;
4. sens des broches `$5C00-$5C07` → `$F008+8·slot` ;
5. au labo seulement (`$02D2 = 5`) : longueur → `$7A98/$7AA0+slot`, fiche
   (`$12B` octets depuis `$5C0A`) → `$8045+$12B·slot` ;
6. « LOADED », relance de la leçon.

Dans Robotropolis (`$02D2 = 4`) le programme et les broches sont chargés
de la même façon, sans fiche ni longueur.

### Sauvegarde (`$419C`, mode 6)

Lecture du catalogue, « Press letter of chip », « Enter name of chip »
(`$4813`, 15 caractères, `←` efface), puis en-tête construit en `$5C00`
(broches depuis `$F008`, longueur depuis `$7A98/$7AA0`, fiche depuis
`$8045+$12B·slot`) et écriture en une fois des 3 descripteurs : catalogue
(bloc 8), programme (2 blocs, lus en banque 1 par `$C088`) et en-tête.
« SAVED » ou « NOT SAVED ».

## La bibliothèque (*Chip Library*, face B)

Dix puces aux blocs `$009-$026` de la face B. Sortie complète :
`tools/chips.py library`.

| k | Nom | Blocs | Broches (1→8) | Long. | Contenu (imbriquées comprises) | Fonction (fiche) |
|---|---|---|---|---|---|---|
| 0 | Clock Chip | `$009-$00B` | 8 sorties | `$06A` | 16 NON | 4 horloges, 2 sorties chacune : anneaux de 1, 3, 7 et 5 NON |
| 1 | 4 Bit Counter | `$00C-$00E` | 1 entrée, 2 remise à 0, 5-8 bits 0-3 (la fiche écrit « Bit 4 » pour le 4ᵉ) | `$151` | 4 puces imbriquées (4 bascules, 12 ET, 4 OU, 4 NON) | compteur binaire 0-15 |
| 2 | Bus Chip | `$00F-$011` | 1 entrée, 2-8 sorties | `$01B` | aucune porte | copie la broche 1 sur les 7 autres (section `07` seule) |
| 3 | Delay Line Chip | `$012-$014` | 1 entrée, 2-8 sorties | `$045` | 7 OU | broche *k* = entrée retardée de *k−1* cycles |
| 4 | Full Adder | `$015-$017` | 1-3 entrées, 7 somme, 8 retenue | `$03F` | 2 OUX, 2 ET, 1 OU | additionneur complet |
| 5 | One Shot Chip | `$018-$01A` | 4 × (entrée, sortie) | `$052` | 4 ET, 4 NON | 4 monostables : une impulsion par front montant |
| 6 | RS Flip-Flop | `$01B-$01D` | 1 *set*, 2 *reset*, 7 A, 8 B | `$044` | 1 bascule, 3 ET, 1 OU, 1 NON | bascule à bascule-retour (*toggle*) |
| 7 | Count to N | `$01E-$020` | 1 impulsions, 2 remise à 0, 3-8 sorties A-F | `$1AA` | 5 puces imbriquées, 7 bascules, 12 ET, 5 OU, 1 NON | chaque impulsion allume la sortie suivante (séquenceur à 6 sorties) |
| 8 | Wall Hugger | `$021-$023` | 1, 3, 5, 7 propulseurs ; 2, 4, 6, 8 pare-chocs | `$183` | 16 portes (11 OU, 4 ET, 1 NON) + 1 puce imbriquée (4 bascules, 20 OU) | longe les murs |
| 9 | Stereo Recorder | `$024-$026` | 1-2 sorties A/B, 5-6 effacement B/A, 7-8 entrées B/A | `$204` | 2 puces imbriquées, 68 OU, 2 ET, 2 NON | enregistre et rejoue 35 cycles par canal |

Le compte de Wall Hugger (« 16 logic gates and 1 nested chip », texte de
Chip Design salle `$17`) correspond aux portes du niveau supérieur. Beaucoup
de OU à une seule entrée utilisée servent de relais (retard d'un cycle).

Vérifications par `tools/chips.py sim` : Delay Line (escalier de 1 à 7
cycles), Full Adder (1+1+1 → somme 1, retenue 1), Clock (périodes 2, 6, 14,
10 cycles sur les broches 1-2, 3-4, 5-6, 7-8).

### Puces préchargées

| Contexte | Routine | Puce 0 (`$D000`) | Autre |
|---|---|---|---|
| Robotropolis, nouvelle partie | `$4615` (après `$4602`) | Count to N (face A bloc `$071`, `$1AA` octets, = bibliothèque n° 7) | puce 1 (`$D400`) : Wall Hugger (bloc `$06D`, = n° 8) ; sens des broches `$464A` (16 octets) → `$F008` |
| Chip Design | `$46C8` | puce à impulsions (bloc `$0A6`, 19 octets) ; broches `$465A` | puce 2 (`$D800`) : Wall Hugger (bloc `$06D`) ; broches `$4652` → `$F018` |

Les blocs `$06D` des faces A et B sont identiques entre eux et aux blocs
`$021-$022` de la bibliothèque ; `$071` (face A) est identique aux blocs
`$01E-$01F`. *Où ces deux puces apparaissent dans Robotropolis relève de
l'analyse du jeu.*

## Points ouverts

- **Clock Chip** : la fiche dit « Speed A est la plus rapide, D la plus
  lente », la simulation donne D (broches 7-8, anneau de 5) plus rapide que
  C (broches 5-6, anneau de 7). La numérotation des broches est confirmée
  par trois autres puces : la fiche est probablement approximative.
- **RS Flip-Flop** : la fiche dit que *reset* met A (broche 7) à 1 ; le
  modèle met la broche 8 à 1. À vérifier dans l'émulateur (puce chargée au
  labo, broches câblées) — soit la fiche, soit l'interprétation des
  entrées de la bascule (`$1C2A`) est en cause.
- Types de périphérique (`$D0,x`) et lecteur choisi par `$4CA8` (`$01`
  bibliothèque, `$11` stockage) : relèvent de l'analyse du chargeur.
- Les 3 octets de fin de chaque nom du catalogue (18 octets pour 15
  caractères) : toujours des espaces sur la bibliothèque.
