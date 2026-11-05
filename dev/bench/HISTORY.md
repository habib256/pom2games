# Historique des mesures

Ces chiffres décrivent les versions successives, pas tous la version actuelle.
Les résultats actuels et leur protocole sont dans [README.md](README.md) ;
`baseline.json` conserve les références utilisées par le gate.

## Nouvelle série du 5 novembre 2026 : page zéro des rectangles HGR

Les deux colonnes et les quatre masques de bord du noyau pixel utilisent
`tmp3/tmp4` et `ptr3/ptr4`. Les arguments publics restent intacts et le
noyau ne fait aucun appel. Il conserve seulement l'octet privé de remplissage
intérieur : **six octets de page zéro sont libérés** par client, sans modifier
les instructions de tracé ni ajouter de stockage ailleurs.

Les 25 profils de rectangles, cellules et axes ciblés ne changent que par
ces six octets : cycles, code, RAM hors page zéro et piles sont identiques.
Les **752 remplissages/effacements** passent sur chaque CPU, avec toutes
les phases de bord, les largeurs 1..40 octets, le découpage, les deux pages,
les palettes et les trous vidéo. Les premiers appels avec tables ordinaires
ou regroupées passent également sur II+ et IIe.

## Nouvelle série du 5 novembre 2026 : scratch du texte 16×16

Les deux porteuses et les deux fragments supérieurs du glyphe utilisent
`ptr3/ptr4`, disponibles pendant ce noyau sans appel imbriqué. Cela retire
**quatre octets de page zéro** privés. Le doublement du numéro de ligne
(0..7) garantit déjà une retenue nulle : supprimer le `CLC` suivant retire
**un octet de code** et deux cycles par ligne non vide.

Le glyphe dense passe de **2 657 à 2 641 cycles**, « APPLE II » en blanc
de **14 720 à 14 622**, et en couleur de **14 839 à 14 741**. Aucun des
27 profils de texte ciblés ne régresse. Les 280 scènes de glyphes passent
sur 6502 et 65C02 ; elles couvrent les 256 motifs de ligne, 96 caractères,
cinq porteuses, sept phases, deux parités et deux pages. Les entrées C
passent sur tous les x et les valeurs de y/couleur, avec tables ordinaires
et regroupées. RAM hors page zéro et piles sont inchangées.

## Audit de la dixième session du 5 novembre 2026 — compteurs HGR

Après `019759b`, les commits `88ea461`, `a4469ff` et `6379c70` remplacent
les temporaires BSS des noyaux numériques par le scratch cc65 existant.
Le HUD 8×8 y conserve ses masques et sa base ; le 16×16 y place ses
fragments de glyphe, ses masques et sa ligne courante. Le contrôleur
restaure son pointeur de champ après chaque cellule. Les 81 profils
remesurés avant modification reproduisent exactement le rapport précédent,
avec le même compilateur et le même environnement.

Le gate complet `--dhgr --check` passe pour **697 cas**. Les **55 clients
concernés diminuent en taille** : 30 perdent **28 octets chargés et sept
octets de RAM**, 25 perdent **six octets chargés et trois octets de RAM**.
**52 durées diminuent**, deux sont identiques et la boucle avec attente
VBL passe de **34 050 à 34 053 cycles**, une hausse inférieure à 0,01 %.
Les **642 autres dictionnaires sont identiques**. Page zéro et piles
restent inchangées ; tous les budgets absolus de trame sont respectés.

Le chiffre 16×16 modifié passe de **3 930 à 3 770 cycles** (−4,1 %), son
champ froid de **22 027 à 21 145**, et les cinq chiffres modifiés prennent
**14 218..15 013 cycles** selon la phase, contre **15 034..15 890**.
Le chiffre 8×8 passe de **2 282 à 2 255**, son champ froid de **6 324 à
6 208**, et la scène compacte de **15 227 à 15 119**. Un champ inchangé
reste à 312 cycles dans les deux formats. **217 champs de référence sont
abaissés**, sans relever de seuil ni modifier les budgets absolus.

Pour chaque format et chaque CPU, les tests vérifient 168 mises à jour
avec historique par page, les sept phases, retenues et débordements,
invalidation, fonds colorés et 70 glyphes aux bords. Ils couvrent aussi
les 265/273 origines valides et toutes les largeurs 1..14/1..5. Les tests
généraux HGR, les 69 programmes de sélection d'archives, les scènes du
moteur et les 32 scènes de stress passent.

`make all` réussit ; la disquette HGR et son WOZ sont reconstruits et les
**18 paires disque/WOZ** correspondent. L'exemple HGR passe sur II+ et IIe.
Les exemples minimaux passent en HGR simple/double et en ProDOS, y compris
les chemins avec et sans /RAM. Sur 1 000 trames avec débordement du compteur,
la cadence double reste dans **34 050..34 070 cycles en NTSC** et
**40 550..40 570 en PAL**.

## Nouvelle série du 5 novembre 2026 : masques et lignes du HUD 16×16

Les masques de bord utilisent `ptr3` et les deux octets de `ptr4` ; le
compteur de lignes utilise `ptr3+1`. Le contrôleur restaure déjà son
pointeur de champ immédiatement après chaque cellule. Aucun appel
n'intervient pendant le tracé, et le contrat des temporaires est documenté.
Cette passe retire **quinze octets de code et quatre octets de RAM**
supplémentaires, soit **28 et sept** pour le noyau 16×16 sur cette session.
Page zéro et piles restent inchangées.

Le chiffre modifié passe de **3 833 à 3 770 cycles**, le champ froid de
**21 596 à 21 145**, et les cinq chiffres en phase zéro de **14 926 à
14 607**. Les modèles de pixels et d'historique passent sur 6502 et 65C02,
avec toutes les origines valides et les largeurs 1..14. Le gate complet
passe pour 697 cas ; par rapport au début de session, sa seule hausse
est la boucle avec attente VBL, de 34 050 à 34 053 cycles (moins de 0,01 %).

## Nouvelle série du 5 novembre 2026 : fragments du HUD 16×16 en page zéro

Les trois fragments du glyphe agrandi utilisent `tmp2..tmp4` après le
retour de `glyph_addr`. Aucun autre appel ne peut écraser ces valeurs
pendant le tracé. Cette passe retire **treize octets de code et trois
octets de RAM** par client 16×16, sans page zéro ni pile supplémentaires.

Le chiffre modifié passe de **3 930 à 3 833 cycles**, le champ froid de
**22 027 à 21 596**, et les cinq chiffres en phase zéro de **15 450 à
14 926**. Les 81 profils ciblés ne présentent aucune métrique en hausse.
Le modèle de pixels 6502 passe : 168 mises à jour, 70 glyphes aux bords,
les 265 origines valides et les largeurs 1..14.

## Nouvelle série du 5 novembre 2026 : scratch du HUD 8×8

Les deux masques de bord et l'adresse de base du noyau compact utilisent
`tmp2..tmp4`, déjà réservés par cc65. Ce noyau ne fait aucun appel et le
contrôleur conserve son état vivant en BSS. Cette passe retire **six octets
de code et trois octets de RAM**, sans allocation de page zéro ni pile ajoutée.

Le chiffre modifié passe de **2 282 à 2 255 cycles**, le champ froid de
**6 324 à 6 208**, et la scène compacte de **15 227 à 15 119**. Les 36 profils
ciblés ne présentent aucune métrique en hausse ; 25 clients diminuent en
taille. Les tests de pixels passent sur 6502 et 65C02 : 168 mises à jour,
70 glyphes aux bords, les 273 origines valides et les largeurs 1..5.

## Audit de la neuvième session du 5 novembre 2026 — propagation des dommages HGR

Après `8a13d73`, les commits `b81b8f3`, `884ed29` et `f017fe3` réutilisent
le scratch cc65 pour la géométrie, les indices et les indicateurs du mode
`HGR_SPR_DAMAGE`. Le noyau supprime ses onze octets BSS propres, tout en
conservant les rectangles persistants du moteur. Les deux anciens profils
remesurés correspondent au rapport précédent et au même environnement.
Huit nouveaux calculs isolés ont leurs références prises avant modification.

Le gate complet `--dhgr --check` passe pour **697 cas** : les **dix clients
concernés perdent chacun 43 octets chargés et onze octets de RAM**, avec
dix durées réduites et **aucune métrique en hausse**. Les 687 autres
dictionnaires restent identiques. Page zéro et piles sont inchangées.
La chaîne de huit sprites passe de **20 604 à 18 624 cycles**, le calcul
stable de **5 476 à 5 183**, et le rendu isolé par dommages de **14 092 à
13 890**. **40 champs de référence sont abaissés**, sans relever de seuil
ou de budget absolu ; tous les budgets de trame restent respectés.

Le modèle indépendant vérifie **512 états sur chaque CPU**, en comparant
les rectangles et l'accessibilité dans le graphe des recouvrements : un
à huit slots, les deux historiques, les quatre masques d'invalidation,
les formes non définies, le masquage, les bords et la propagation inverse.
Il passe aussi sur le noyau d'origine. Les tests de préfixes stables avec
dommages passent sur 6502 et 65C02 ; les images à quatre couches et les
gardes de tampon passent sur IIe. Les nouveaux contrôles sont intégrés à
`make test-hgr`.

`make all` réussit, les disquettes reconstruites restent identiques et les
**18 paires disque/WOZ** sont vérifiées. L'option reste désactivée par défaut.

## Nouvelle série du 5 novembre 2026 : indicateurs de dommages sans BSS

L'invalidation de page et le témoin de propagation utilisent les deux
octets de `ptr1`. Le constructeur des colonnes termine avant leur
initialisation ; les appels suivants ne les touchent pas. Le noyau n'a
plus de BSS propre. Cette passe retire **cinq octets de code et deux
octets de RAM supplémentaires**, soit **43 octets chargés et onze octets
de RAM** pour les trois passes, sans page zéro ni pile ajoutées.

Par rapport au début de session, le calcul stable passe de **5 476 à
5 183 cycles**, la chaîne inverse de **20 604 à 18 624**, le cas aux bords
de **12 500 à 11 489**, et le rendu isolé de **14 092 à 13 890**. Ce dernier
prend 15 cycles de plus que dans la passe intermédiaire précédente, tout
en restant plus rapide qu'à l'origine. Les modèles de rectangles et de
propagation, les préfixes stables et les images avec gardes restent valides.

## Nouvelle série du 5 novembre 2026 : indices de propagation HGR en page zéro

L'identifiant courant, l'autre slot et l'offset du rectangle utilisent
`tmp2..tmp4`. L'appel de visibilité modifiée ne détruit que `tmp1` ; ces
trois indices restent donc valides pendant toute leur durée d'utilisation.
La passe retire **21 octets de code et trois octets de RAM supplémentaires**,
sans allocation de page zéro ni pile ajoutée. Le cumul atteint **38 octets
chargés et neuf octets de RAM** par client du mode optionnel.

La propagation en sens inverse sur huit sprites passe de **20 373 à
18 813 cycles** pour cette passe, le calcul après invalidation complète
de **6 570 à 6 268** et le rendu isolé de **13 931 à 13 875**. Les 512 états
et les scènes de préfixes stables avec dommages passent sur les deux CPU.

## Nouvelle série du 5 novembre 2026 : géométrie temporaire des dommages HGR

Les dimensions et coordonnées temporaires du calcul optionnel des dommages
utilisent `ptr2..ptr4`. Le pointeur de forme dans `ptr3` devient la coordonnée
x seulement après lecture de ses dimensions ; `spr_visible` préserve ces
registres de travail. La passe retire **17 octets chargés et six octets de
RAM**, sans nouvelle allocation de page zéro ni pile. Le rendu isolé par
dommages passe de **14 092 à 13 931 cycles** ; le calcul sans changement
sur huit sprites de **5 476 à 5 258**.

Un modèle indépendant calcule les rectangles réunis et l'accessibilité dans
le graphe des recouvrements. Ses **512 états** couvrent les comptes 1..8,
les deux historiques, les quatre masques d'invalidation, les sprites
masqués/non définis, les limites et les chaînes en sens inverse. Il passe
sur l'ancien noyau puis sur le nouveau, ce dernier sur 6502 et 65C02.
Le test d'images avec quatre couches et gardes de tampon passe également.

## Audit de la huitième session du 5 novembre 2026 — moteur de sprites HGR

Après `e9dc693`, les commits `0058012`, `d14d064` et `5c91c14` suppriment
les temporaires persistants de visibilité et de déplacement, puis regroupent
les additions de pointeurs du tampon de fond. Les scènes remesurées avant
modification sont identiques au rapport précédent, avec le même environnement.
Huit nouveaux appels de déplacement ont leurs références prises avant les
trois passes ; le banc passe de **681 à 689 cas**.

Le gate complet `--dhgr --check` réussit : **48 clients plus petits de
17 octets chargés et quatre octets de RAM**, 641 dictionnaires inchangés,
**45 durées réduites** et trois augmentées de **deux à cinq cycles**, moins
de **0,02 %**. La page zéro et la pile C restent identiques ; les huit
clients de déplacement isolés gagnent un octet de pile matérielle. Le grand
stress passe de **37 855 à 37 577 cycles**, le rendu par dommages isolés de
**14 158 à 14 092**. Tous les budgets absolus de trame restent respectés.
**188 champs de référence sont abaissés**, sans relever de seuil ou de budget.

Les nouveaux tests passent sur chaque CPU : **20 480 déplacements** avec
tous les identifiants, coordonnées limites, formes non définies et contrôle
des deux piles ; **9 180 calculs de pointeur** avec toutes les capacités,
les comptes de slots, les passages de page et le retour modulo 65 536.
Les trois variantes d'intégration du moteur, le stress, les préfixes stables
sur les deux CPU avec/sans dommages, la propagation des dommages et HGR
passent aussi. Les nouveaux contrôles font partie de `make test-hgr`.

`make all`, l'exemple HGR et la campagne des cinq niveaux de LIGHT3DBALL
réussissent. Seule la disquette HGR change, avec son WOZ régénéré ; les
**18 paires disque/WOZ** sont vérifiées.

## Nouvelle série du 5 novembre 2026 : parcours du tampon de fond HGR

Le calcul de fin du tampon et celui du début du suffixe à redessiner
utilisent un seul appel pour additionner plusieurs capacités. L'octet bas
reste dans A jusqu'au stockage final. L'avancement d'un slot partage ce
même corps. Cette passe retire **un octet de code supplémentaire**, sans
RAM ni pile ajoutées. Le chemin d'un seul avancement coûte six cycles de
plus hors effets de placement ; les calculs de plusieurs slots évitent
les appels et accès mémoire répétés.

Entre cette passe et la précédente, la scène animée en phase zéro passe
de **23 846 à 23 748 cycles**, le grand stress de **37 623 à 37 577** et
le rendu par dommages isolés de **14 130 à 14 092**. La scène de jeu compact
coûte 23 cycles de plus dans cette passe, mais reste plus rapide qu'au début
de la session. Les trois passes retirent **17 octets chargés et quatre
octets de RAM** par client du moteur.

Un test dédié vérifie **9 180 appels par CPU** : capacités 1..255, comptes
1..8 et avancement unique, passages de page et retour modulo 65 536. Il
passe sur 6502 et 65C02. L'intégration, les recouvrements, le stress, les
préfixes stables et le calcul optionnel des dommages passent également.

## Nouvelle série du 5 novembre 2026 : déplacement HGR depuis les arguments C

`hgr_spr_move` lit directement les trois octets d'arguments dans la pile C,
valide l'identifiant avant de lire x, puis libère les arguments en une fois.
La position y reste dans `tmp1` jusqu'à son stockage ; les trois octets BSS
de transit disparaissent. Chaque client concerné perd **13 octets chargés
supplémentaires et trois octets de RAM**. Les déplacements valides gagnent
**29 cycles** et les identifiants rejetés **44 cycles**. Le pic matériel des
clients de déplacement isolés passe de six à cinq octets.

Le nouveau test passe d'abord sur l'ancienne entrée puis sur la nouvelle :
**20 480 appels** couvrent les 256 identifiants, les comptes 0/1/2/8,
les pointeurs de forme nuls ou avec un seul octet non nul, les coordonnées
limites sur 16 et 8 bits, l'intégrité des autres slots et les deux piles.
La nouvelle entrée passe sur 6502 et 65C02. Les trois variantes du test
d'intégration du moteur passent également.

## Nouvelle série du 5 novembre 2026 : visibilité HGR dans le scratch partagé

Le résultat temporaire de visibilité de `spr_changed` ne vit que jusqu'au
retour de cette routine. Il utilise maintenant `tmp1` au lieu d'un octet
BSS propre au moteur : **3 octets de code et un octet de RAM en moins**,
sans allocation de page zéro ni pile supplémentaires. Son contrat interne
indique ce registre temporaire détruit ; le moteur et le calcul optionnel
des dommages n'y conservent aucune valeur pendant l'appel.

Les tests de préfixes stables, recouvrements, masquage, invalidation et
présentation après changement externe de page passent sur 6502 et 65C02,
avec et sans le calcul optionnel des dommages.

## Audit de la septième session du 5 novembre 2026 — DHGR et générateur aléatoire

Après `8ed35bc`, les commits `89b4cdf`, `b2864af` et `b3bc5a2` gardent
les pointeurs DHGR dans A pendant les additions et rendent directement
l'état du générateur aléatoire C. Les anciennes mesures DHGR refaites
avant modification correspondent au rapport complet précédent. Quinze
nouveaux cas, mesurés avant modification, portent le banc à **681 cas**.

Le gate complet `--dhgr --check` passe : **25 clients plus petits** (15 à
−3 octets et 10 à −8), **21 durées réduites**, aucune métrique en hausse
et **656 dictionnaires inchangés**. La surimpression de 31 lignes passe
de **30 882 à 28 080 cycles** ; les appels C du générateur de **55/64 à
45/46 cycles**. La pile matérielle des dix clients PRNG perd deux octets ;
RAM, page zéro et pile C restent identiques. **77 champs de référence
sont abaissés**, sans relever de seuil ou de budget absolu.

Le test PRNG couvre les **65 536 états sur chaque CPU**, avec résultat
A/X, état stocké, graine initiale, Y et équilibre de pile ; les tests
mathématiques passent aussi. Le modèle DHGR étendu passe sur **IIe et IIc
dans les sept configurations** : 66 mises à jour, 67 en double page,
contrôle des écritures uniques, des accès auxiliaires sous interruptions
VIA et de la synchronisation VBL. Les cas hauts traversent une page source
et couvrent les formats CHUNKY/TILE, le miroir et la surimpression.

`make all` réussit. SNAKE passe ses tests de jeu, placement des fruits,
cadence NTSC/PAL et sauvegarde ; Robot Space Station passe le modèle,
le laboratoire et les zones sur IIe et IIc. Seules leurs disquettes
et leurs WOZ changent ; les **18 paires disque/WOZ** sont vérifiées.

## Nouvelle série du 5 novembre 2026 : générateur aléatoire C sans appel intermédiaire

`a2_rand16` applique directement la même transition LFSR `$B400` que
`rand8`, en gardant l'octet haut dans A jusqu'à l'application du retour.
Il rend ensuite l'état dans A/X, sans appel imbriqué. Le noyau passe de
**27 à 19 octets de code**, garde ses deux octets DATA et économise
**deux octets de pile matérielle** dans les clients mesurés. L'appel C
avec stockage du résultat passe de **55 à 45 cycles** pour un état pair
et de **64 à 46** pour un état impair, sur 6502 comme sur 65C02.

Le nouveau test compare les **65 536 états**, le résultat A/X et l'état
mémorisé, la graine initiale `$ACE1`, Y et l'équilibre de pile. Il passe
sur l'ancien noyau puis sur le nouveau, et sur les deux CPU pour celui-ci.
La suite mathématique, dont le générateur assembleur inchangé, passe aussi.
Les dix nouvelles mesures C couvrent les deux chemins, zéro, `$ACE1` et
`$FFFF` sur les deux CPU ; leurs références ont été prises avant modification.

## Nouvelle série du 5 novembre 2026 : adresse de surimpression DHGR en registre

La surimpression calcule maintenant son adresse de ligne dans A et ne
stocke le pointeur qu'à la fin, y compris pour la première ligne. X reste
préservé pour le compositeur. Cette passe retire **3 octets de code**, sans
modifier les allocations ou les piles. Une surimpression de 4 × 31 octets
passe de **30 882 à 28 080 cycles** ; celle de 4 × 6 de **6 564 à 6 465**,
et le déplacement de surimpression de **13 214 à 13 126**.

Le modèle étendu invalide explicitement toute la zone lorsqu'il l'élargit
à nouveau, afin de vérifier aussi la convergence des deux pages. Les
bitmaps hauts partagent leurs octets source entre les deux formats dans
la fixture ; la pile C de 512 octets reste inchangée.

## Nouvelle série du 5 novembre 2026 : saut de lignes des bitmaps DHGR

Le peintre CHUNKY/TILE garde l'octet bas du pointeur source dans A pendant
le saut des lignes masquées au-dessus de la zone de dessin. Le pointeur
est stocké une seule fois après les additions. Taille, RAM, page zéro et
piles restent identiques. Sauter 40 lignes de sept octets économise
**234 cycles** : **5 909 → 5 675** pour CHUNKY et **5 563 → 5 329** pour
TILE. La scène animée CHUNKY passe de **9 450 à 9 390 cycles**.

Le modèle du compositeur couvre désormais les deux bitmaps hauts, leur
découpage de 280 octets, la transparence, le miroir et une surimpression
de 31 lignes. Les **66 mises à jour** passent sur IIe et IIc, ainsi que sur
IIe avec interruptions VIA : images exactes, chaque octet écrit une seule
fois et aucune interruption pendant un accès à la mémoire auxiliaire.

## Audit de la sixième session du 5 novembre 2026 — découpage des sprites

Après `9616f46`, les commits `a294012`, `5c7ab37` et `cb864bb` simplifient
les limites horizontales et verticales des sprites, puis éliminent la copie
temporaire du stride masqué. Les 38 mesures ciblées refaites avant modification
sont identiques au rapport complet précédent, avec le même environnement.

Le gate complet `--dhgr --check` passe pour **666 cas** : **80 clients plus
petits** (61 à −16 octets, 19 à −14), 586 dictionnaires inchangés, 47 durées
réduites et 30 augmentées de moins de **0,60 %**. RAM, page zéro et piles
restent identiques. Le XOR prédécalé découpé passe de **695 à 678 cycles** ;
le cas masqué haut découpé en phase zéro de **399 à 389**. Les variations
de placement du code et des données produisent aussi les petites hausses
consignées ci-dessous. Tous les budgets absolus de trame restent respectés.
**204 champs de référence sont abaissés**, aucun seuil ni budget n'est relevé.

Sur chacun des CPU 6502 et 65C02, les préparations passent **1 827 868 appels
masqués** et **910 350 appels prédécalés**, couvrant toutes les dimensions
non nulles, les sept phases et les limites des pointeurs 16 bits. Les
200 scènes masquées passent sur les deux CPU ; les 1 304 trames prédécalées
et 160 appels à froid passent sur les deux CPU avec tables séparées puis
regroupées. Les tests du moteur, stress, suivi des modifications, dommages
et HGR réussissent aussi.

`make all`, les tests de l'exemple HGR et la campagne des cinq niveaux de
LIGHT3DBALL passent. Seules les disquettes HGR et LIGHT3DBALL changent,
avec leurs WOZ régénérés ; les **18 paires disque/WOZ** sont vérifiées.

## Nouvelle série du 5 novembre 2026 : stride masqué sans copie temporaire

La préparation masquée lit le stride dans son emplacement déjà nécessaire
aux boucles de lignes. La copie dans `tmp2` et son import disparaissent :
**2 octets de code supplémentaires** et une écriture en page zéro en moins
par appel. L'allocation de page zéro ne change pas. Les trois passes retirent
donc **16 octets** aux clients masqués et **14** aux clients prédécalés.

Par rapport au début de session, le dessin masqué de hauteur 255 découpé
en phase zéro passe de **399 à 389 cycles**, le stride 255 découpé à droite
de **409 à 398**, et le XOR prédécalé découpé de **695 à 678**.
Le déplacement du code et des données entraîne aussi de petites hausses :
le dessin masqué générique passe de 2 836 à 2 841 cycles, et le SET prédécalé
de 2 143 à 2 154. Les anciennes références sont conservées pour ces cas.
Les **1 827 868 préparations masquées** passent sur chacun des deux CPU,
avec **200 octets** de code de préparation au lieu de 216.

## Nouvelle série du 5 novembre 2026 : découpage vertical des sprites

Le même calcul par espace restant s'applique à la hauteur : comparer
`192-y` à la hauteur source élimine la somme et son débordement. Les deux
noyaux perdent chacun **7 octets supplémentaires**, soit **14 octets**
depuis le début de cette session. La hauteur complète reste disponible
pour sélectionner la banque de phase, même après découpage.

Entre ces deux passes, le sprite masqué de hauteur 255 découpé en phase
zéro passe de 397 à 391 cycles ; le XOR prédécalé découpé passe de 686 à
678 cycles. Les contrôles de préparation réussissent à nouveau, avec
202 octets de préparation masquée et 176 pour les sprites prédécalés.

## Nouvelle série du 5 novembre 2026 : découpage horizontal des sprites

Les préparations des sprites masqués et prédécalés comparent leur stride
à `40-colonne`, au lieu de calculer une somme puis de traiter séparément
son débordement. Chaque noyau perd **7 octets de code**, sans allocation
supplémentaire. La largeur initiale reste intacte lorsqu'elle tient à
l'écran, y compris en cas d'égalité ; seule la largeur visible est réduite.
Les dimensions source et le décalage des banques restent identiques.

Les contrôles de préparation passent pour tous les strides, sept phases,
deux placements et la sélection courante de hauteurs ; les sprites masqués
vérifient aussi les deux modes et les 256 indicateurs de cache.

## Audit de la cinquième session du 5 novembre 2026 — sprites masqués

Après `9812ef8`, les commits `22594f9`, `477b613` et `52ef795` partagent la
fin de ligne, évitent le produit en phase zéro et conservent le produit et
le cache dans les registres. Le gain cumulé est de **25 octets chargés**
par client concerné, sans changement de RAM, page zéro ou piles.

Le gate complet `--dhgr --check` passe avec **666 cas**, dont 15 nouveaux
mesurés avant modification. Par rapport au bilan précédent complété par
ces mesures : **61 clients plus petits**, 605 dictionnaires identiques,
26 durées réduites et 33 augmentées de moins de **0,36 %**. Ces petites
hausses comprennent quatre dessins d'une ligne à +2 cycles et des scènes
intégrées ; tous les budgets absolus de trame restent respectés.
**141 champs de référence sont abaissés** ; aucun ancien seuil ni budget
absolu n'est relevé, y compris pour les nouveaux cas qui ralentissent.

Les **1 827 868 préparations** et **200 scènes exactes** passent sur chacun
des deux CPU, 6502 et 65C02. Les tests du moteur, stress, suivi des sprites
modifiés, propagation des dommages et HGR passent également. `make all`,
les tests de l'exemple HGR et la campagne complète des cinq niveaux de
LIGHT3DBALL réussissent. Seules les disquettes HGR et LIGHT3DBALL changent ;
leurs WOZ sont régénérés et les **18 paires disque/WOZ** sont vérifiées.

## Nouvelle série du 5 novembre 2026 : produit des sprites masqués en registres

L'octet bas du produit reste dans A pendant toutes les additions ; seul
le résultat final est stocké. Le cache reste dans Y jusqu'à cette même
écriture finale. La préparation perd **5 octets supplémentaires**, de
221 à 216, sans RAM, page zéro ou pile ajoutées. Les trois passes économisent
donc **25 octets chargés** par client de sprites masqués.

| Appel | Cycles avant les trois passes → après |
|---|---:|
| Dessin générique | 2 876 → 2 836 |
| Sauvegarde et dessin génériques | 3 223 → 3 183 |
| Phase 0, stride 3, hauteur 16 | 3 565 → 3 252 |
| Phase 0, stride 1, hauteur 255, bas découpé | 5 251 → 399 |
| Phase 3, stride 1, hauteur 255, bas découpé | 5 384 → 3 862 |
| Phase 6, stride 3, hauteur 16 | 3 838 → 3 743 |
| Phase 6, bloc 48 mis en cache | 3 555 → 3 544 |

Les quatre cas d'une ligne en phase 3/6 coûtent deux cycles supplémentaires,
avec leurs références antérieures conservées. Sauvegarde et restauration
génériques gardent leurs durées. Les **1 827 868 préparations** passent à
nouveau sur chacun des deux CPU, ainsi que les **200 scènes exactes** des
quatre noyaux : pixels, palette, trous mémoire et tampons de sauvegarde.

## Nouvelle série du 5 novembre 2026 : phase zéro des sprites masqués

Le dessin consomme d'abord son indicateur de taille mis en cache, puis
rejette le travail de décalage lorsque la phase est zéro. Sauvegarde et
restauration continuent à préserver cet indicateur. La préparation perd
**4 octets supplémentaires**, de 225 à 221, sans état ni pile ajoutés.

| Dessin en phase zéro | Cycles avant → après cette passe |
|---|---:|
| Stride 2, hauteur 1 | 443 → 420 |
| Stride 3, hauteur 16 | 3 559 → 3 255 |
| Stride 1, hauteur 255, bas découpé | 5 251 → 402 |
| Stride 255, hauteur 1, droite découpée | 435 → 412 |
| Stride 3, hauteur 16 avec cache | 3 265 → 3 257 |

Les phases non nulles coûtent provisoirement 6 à 12 cycles supplémentaires ;
la passe suivante réduit le calcul de leur produit. Les deux modes de
préparation passent chacun dans le contrôle complet : **1 827 868 appels
par CPU**, sur 6502 et 65C02, dont tous les indicateurs de cache pour chaque
phase et placement. Les benchmarks réarment cet indicateur dans l'appel
mesuré : l'échauffement ne doit pas le consommer avant la mesure.

## Nouvelle série du 5 novembre 2026 : fin de ligne des sprites masqués

L'avancement du pointeur de sauvegarde et des compteurs de lignes est
partagé entre dessin, sauvegarde et restauration. Le chemin dessin continue
directement dans celui de sauvegarde, sans appel ni saut supplémentaire.
La suppression du doublon retire **16 octets chargés**, sans changement
de RAM, page zéro ou piles.

Les quatre clients génériques gardent exactement leurs durées : dessin
2 876 cycles, sauvegarde 1 782, restauration 1 793 et sauvegarde/dessin 3 223.
Les 200 scènes des quatre noyaux passent sur 6502 et 65C02, avec grands
strides, sept phases, deux pages, palette, trous et limites du tampon de fond.

Un nouveau test de préparation vérifie **1 827 868 appels** en mode complet :
toutes les dimensions non nulles, sept phases, deux placements, préparation
du dessin ou de la sauvegarde, et les 256 valeurs du cache. Les pointeurs
16 bits, le découpage et la consommation du cache sont comparés au modèle.
Le modèle passe également sur le noyau d'origine. La sélection courante
des hauteurs est ajoutée aux suites HGR et IIe ; `--full` étend le parcours.

## Audit de la quatrième session du 5 novembre 2026 — texte et tuiles

Après `f56a608`, les commits `13cd560` et `325c4b5` regroupent trois passes
mesurées : itérateur texte, état du restaurateur, puis indexation des tuiles.
Le banc passe de **642 à 651 cas**, avec deux chaînes longues et sept
restaurations isolées mesurées avant et après modification. Le gate complet
`--dhgr --check` passe : **32 clients plus petits**, 619 dictionnaires
identiques, 28 durées réduites et quatre augmentées de moins de 0,85 %.

La restauration économise trois octets de RAM ; le texte utilise moins
de pile C et davantage de pile matérielle pendant les appels au backend,
comme détaillé ci-dessous. La page zéro reste identique. **125 champs de
référence sont abaissés** ; aucune ancienne limite ni aucun budget absolu
n'est relevé. Les neuf nouveaux cas conservent leur référence antérieure
à l'optimisation lorsqu'une métrique augmente.

Les contrôles du curseur, de récursion et de texte numérique passent sur
6502 et 65C02, ainsi que les tests de tuiles sur les deux pages. L'intégration
HGR et les 69 clients minimaux vérifient aussi le rendu et la sélection des
membres de l'archive. `make all` ne modifie aucun disque livré ; les 18 WOZ
correspondent. Les interfaces publiques sont inchangées.

## Nouvelle série du 5 novembre 2026 : état et indexation des tuiles

Deux passes sont mesurées séparément. La première retire une copie privée
du pointeur de contexte et l'octet haut du nombre de tuiles, utilisé seulement
dans A pendant sa validation : **10 octets de code et 3 octets de RAM**
en moins. Le cas spécial 256 et le rejet avant toute écriture sont conservés.

La seconde ajoute la colonne au pointeur de destination une seule fois par
rangée, puis incrémente ce pointeur entre les tuiles. L'octet bas d'une
rangée HGR est au plus 208 et la colonne au plus 39 : aucun passage de page
mémoire n'est possible. Les huit stores de chaque tuile utilisent Y=0,
économisant un cycle chacun. Cette passe retire encore **un octet de code**.

| Restauration | Avant | État simplifié | Indexation simplifiée |
|---|---:|---:|---:|
| Une tuile au coin | 1 014 | 998 | 989 |
| Plein écran | 278 943 | 278 899 | 271 192 |
| Région 4×3 | 4 403 | 4 390 | 4 291 |
| Région découpée | 2 003 | 1 986 | 1 952 |
| Fond de huit tuiles et deux sprites | 6 703 | 6 689 | 6 623 |

Les clients gagnent au total **11 octets chargés et 3 octets de RAM**,
sans augmentation de page zéro ni des piles. Les sept nouveaux benchmarks
isolent la restauration, y compris dimensions vides, page invalide et ID
invalide dans la dernière tuile. Les tests vérifient les deux pages, le
plein écran, les bornes, bits de palette, trous mémoire, compte 256 et
l'absence de toute écriture partielle en cas d'erreur, sur 6502 et 65C02.

## Nouvelle série du 5 novembre 2026 : itérateur de texte sans cadre C

`gfx_text` sauvegarde son pointeur sur la pile matérielle pendant chaque
appel du renderer, puis le restaure et l'incrémente avec propagation de
retenue. Les temporaires restent libres pour le backend et ses appels
imbriqués. Le noyau passe de 54 à **36 octets**, sans cadre sur la pile C.
Les clients de chaînes seules économisent **44 octets chargés**, car ils
n'importent plus `pushax` ; les clients numériques en économisent **18**.

| Appel | Cycles avant → après | Pile C avant → après |
|---|---:|---:|
| Chaîne vide | 115 → 32 | 2 → 0 |
| GFX non signé 0 | 1 825 → 1 750 | 13 → 11 |
| GFX non signé 65535 | 8 678 → 8 625 | 13 → 11 |
| GFX signé −32768 | 10 238 → 10 165 | 14 → 12 |
| GFX hexadécimal FFFF | 6 195 → 6 125 | 12 → 10 |

RAM et page zéro sont inchangées. Le pic de pile matérielle des clients
numériques passe de 16 à 18 octets, celui des chaînes affichées de 14 à 16.
La chaîne vide passe de 7 à 4. Le compromis est aussi mesuré sur les chaînes
longues : 128 caractères prennent 221 453 cycles au lieu de 219 612
(+0,84 %), et 128 contrôles ignorés 9 376 au lieu de 9 348 (+0,30 %).
La chaîne froide « APPLE II » coûte 27 173 au lieu de 26 994 (+0,66 %).
Les limites précédentes restent conservées.

Les 786 432 cas du curseur et les passages de pages/pile passent sur les
deux CPU. Un nouveau contrôle vérifie **2 304 traces par CPU**, profondeurs
imbriquées 0…8, tous les alignements du pointeur, appels vides imbriqués,
temporaires hostiles et gardes. Les 199 680 entrées de texte numérique et
l'intégration graphique réelle passent également.

## Audit de la troisième session du 5 novembre 2026 — 3 séries

Après `ae41ace`, les commits `2e3fbc4`, `cb90bbc` et `577cca7` réduisent
la bascule LORES, les conversions décimales et les initialisations mathématiques.
Le banc complet `--dhgr --check` passe sur **642 cas** : **119 clients
gagnent 2 à 9 octets**, 523 dictionnaires restent identiques. Les cycles
baissent dans 86 cas, restent identiques dans 533 et augmentent dans 23.
Les écarts défavorables restent inférieurs à 0,8 % ; toutes leurs limites
précédentes sont conservées. Aucun pic de RAM, page zéro ou pile n'augmente.
**314 champs de référence sont abaissés**, aucun budget n'est relevé.

Les tests exhaustifs décimaux, des tables/racines et des pages passent sur
6502 et 65C02. Les entrées numériques passent leurs 199 680 appels par CPU,
avec 3 072 placements de pile ; les 1 144 champs numériques et l'intégration
HGR passent aussi. Les tests rapides CUTROPE, DIRTBIKE, LIGHT3DBALL et SNAKE,
le starter HGR, les démos lander/half-pipe/corde/catapulte et les variantes
des contacts physiques passent.

`make all` reconstruit les disques CUTROPE, DIRTBIKE, HGR, LIGHT3DBALL et
SNAKE, ainsi que leurs WOZ ; tous les autres disques restent identiques.
Les 18 jumeaux WOZ sont vérifiés. Les API et les résultats restent inchangés.

## Nouvelle série du 5 novembre 2026 : initialisation des tables mathématiques

Le constructeur des carrés compte ses deux demi-tables à rebours et
termine sur le signe du compteur. Le constructeur des graines de racine
réutilise le résultat déjà présent dans Y. Chaque initialiseur perd un
octet, sans changement des tables, de la page zéro ou de la pile.

| Initialiseur | Cycles avant → après | Code avant → après |
|---|---:|---:|
| `mul_init` | 37 691 → 37 687 | 110 → 109 |
| `sqrt_init` | 24 031 → 23 519 | 21 → 20 |
| Les deux | 61 722 → 61 206 | 131 → 129 |

Les **2 048 octets des tables**, 256 graines et **65 536 racines** passent
aux deux placements $0800/$4000, désormais sur 6502 et 65C02. Le noyau
des racines reste à 42 octets et son parcours exhaustif à 5 529 438 cycles.
Les 1 572 864 produits constants signés/non signés, les inclusions optionnelles
et les tests mathématiques généraux passent également.

## Nouvelle série du 5 novembre 2026 : compteurs et signe décimaux

`u16_to_dec` parcourt les puissances de dix avec un indice décroissant,
en terminant sur le signe de l'indice plutôt qu'une comparaison explicite.
Le noyau perd **2 octets** et quatre comparaisons de deux cycles par appel.
Le convertisseur signé réutilise la retenue du test du signe pour calculer
le complément à deux, sans incréments mémoire : **2 octets supplémentaires**
en moins, y compris pour −32768 et les mots dont l'octet bas est nul.
RAM, page zéro et piles restent inchangées.

| Texte numérique | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| GFX non signé 0 | 1 833 → 1 825 | 2 191 → 2 189 |
| GFX non signé 65535 | 8 686 → 8 678 | 2 191 → 2 189 |
| GFX signé −1 | 3 024 → 3 008 | 2 236 → 2 232 |
| GFX signé −32768 | 10 250 → 10 238 | 2 237 → 2 233 |
| Champ HGR zéro | 4 721 → 4 713 | 2 937 → 2 935 |

Les **131 072 chaînes signées/non signées** passent sur 6502 et 65C02,
avec longueurs, NUL et gardes. Le test IIe est ajouté à `test-hgr`.
Les conversions d'octets et les règles d'inclusions répétées restent
identiques et passent aussi les contrôles de `test_math.py`.

## Nouvelle série du 5 novembre 2026 : bascule des lignes LORES

Les octets hauts des lignes LORES sont dans 4…7 ou 8…11. Le gestionnaire
de page les échange avec `EOR #$0c`, sans calculer puis additionner une
différence de base. La préparation reste paresseuse, sans changement de
RAM, page zéro, piles ou page affichée. Le membre perd **7 octets**.

L'aller-retour page 2/page 1 avec LORES prêt passe de **5 615 à 5 487 cycles**,
et son client de 924 à **917 octets chargés**. L'aller-retour HGR seul coûte
4 700 cycles au lieu de 4 666 (+0,73 %) après déplacement du code ; sa limite
précédente est conservée. La sélection froide de la page 2 gagne 7 cycles,
les autres cas de sélection mesurés gardent leur durée.

Les 256 arguments de sélection sont vérifiés avec LORES froid puis prêt,
sur 6502 et 65C02 : adresses des 192 lignes HGR et 24 lignes LORES, valeurs
par défaut, invalides, appels sur la même page et préservation de l'affichage.

## Audit complémentaire du 5 novembre 2026 — 3 séries

Après `7cb6ceb`, les commits `e8f3b6a`, `d829b16` et `62fe7fe` optimisent
la conversion hexadécimale, les contrôles du curseur et les ellipses.
Le relevé final `--dhgr --check` conserve **642 cas** : **58 binaires
réduits**, 584 dictionnaires entièrement identiques. Les cycles baissent
dans 41 cas, restent identiques dans 596 et augmentent dans 5.
Outre les deux écarts décrits ci-dessous, trois textes numériques coûtent
1, 5 et 7 cycles supplémentaires (au plus +0,24 %). La conversion hexadécimale
augmente de deux octets sept pics de pile matérielle. Aucun pic de RAM,
page zéro ou pile C n'augmente.

Les 169 champs de référence améliorés sont abaissés ; les autres limites
et tous les budgets absolus restent conservés. Les interfaces sont inchangées.
Les contrôles exhaustifs décrits dans les séries passent sur les deux CPU,
ainsi que l'intégration `test_hgr.py` et les 1 144 scènes des champs numériques.
`make all` ne change aucun disque livré ; les 18 WOZ sont vérifiés.

## Série complémentaire du 5 novembre 2026 : cadre et parcours des ellipses

La boucle parcourt directement les angles 1…63,0, dans le même ordre,
sans second indice local. Les coordonnées y bornent le centre à 255 et
le rayon à 127 : centre, rayon et précédent y tiennent dans des octets.
Leurs sommes avec les offsets restent promues en `int` signé avant le clamp.
Le scaler natif applique la négation par complément et retenue, sans sauver
l'octet haut dans un temporaire supplémentaire.

Chaque client perd **24 octets chargés**. Les ellipses ordinaires passent
de **28 à 24 octets de pile C**, les dégénérescences de 28 à 25 et les
rejets de 19 à 16. RAM, page zéro et pile matérielle restent inchangées.

| Appel | Cycles avant → après |
|---|---:|
| Petite ellipse | 156 385 → 151 885 |
| Plein écran | 186 761 → 182 519 |
| Boîte maximale découpée | 190 971 → 186 388 |
| Boîte très large | 171 778 → 167 148 |
| Rayon 512 | 188 629 → 183 992 |
| Point | 1 910 → 1 851 |
| Segment horizontal | 2 328 → 2 251 |

Le segment vertical coûte 12 830 cycles au lieu de 12 738 (+0,72 %),
avec son ancienne référence conservée. Les sept ellipses non dégénérées
mesurées gagnent entre 4 242 et 4 637 cycles.

L'oracle des coordonnées passe de 60 boîtes sur 6502 à **126 par processeur**,
sur 6502 et 65C02, dans les trois dimensions de backend. Il vérifie l'ordre
exact des 64 segments, les sommes y supérieures à 255, coins inversés,
clipping, rejets et dégénérescences. Les sanitizers hôte et les gardes des
pages passent aussi. Le scaler vérifie à nouveau ses **4 227 072 couples**
rayon/coefficient et 2 048 placements de pile sur chacun des deux processeurs.

## Série complémentaire du 5 novembre 2026 : contrôles du curseur

`gfx_gotoxy` réutilise la retenue de la comparaison lors du clamp, et
`gfx_putc` détecte le passage de la ligne 255 à zéro avec le drapeau de
l'incrément. La ligne stockée ne déborde pas, même pour une grille vide.
Chaque membre perd deux octets : les clients de position seule gagnent
2 octets, ceux utilisant position et texte 4. RAM et piles sont inchangées.

| Appel | Cycles avant → après |
|---|---:|
| Position hors grille | 103 → 99 |
| Nouvelle ligne | 45 → 43 |
| Nouvelle ligne au bord inférieur | 42 → 40 |
| Caractère avec retour automatique | 17 243 → 17 241 |

Le caractère isolé coûte un cycle de placement supplémentaire
(16 629 → 16 630), avec sa référence précédente conservée.
Les 786 432 cas de coordonnées/contrôles passent sur chacun des deux
processeurs : quatre grilles dont 0×0 et 255×255, tous les caractères,
256 alignements de chaînes, 768 placements de pile, traces exactes et gardes.

## Série complémentaire du 5 novembre 2026 : conversion hexadécimale par octets

Le convertisseur saute l'octet haut nul et partage une routine de deux
chiffres. Les zéros internes restent présents ; le pointeur de destination,
la terminaison NUL et le nombre de chiffres gardent leur contrat.
Le noyau passe de 68 à **64 octets**, sans changement de RAM, page zéro
ou pile C. Le partage des sous-routines augmente de deux octets la pile
matérielle de certains clients : 6 → 8 pour les conversions de 2–4 chiffres,
et 8 → 10 pour le texte HGR rejeté hors écran. Les autres pics mesurés
restent identiques.

| Conversion | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| `gfx_hexstr(..., 0)` | 308 → 207 | 655 → 651 |
| `gfx_hexstr(..., 16)` | 312 → 230 | 657 → 653 |
| `gfx_hexstr(..., 256)` | 323 → 282 | 657 → 653 |
| `gfx_hexstr(..., 65535)` | 326 → 306 | 655 → 651 |
| Texte HGR d'un chiffre | 2 544 → 2 450 | 2 382 → 2 378 |

Les 65 536 entrées passent sur 6502 et 65C02, avec les longueurs, NUL et
gardes. Le parcours exhaustif prend 130 373 216 cycles, contre 131 796 307
pour le noyau précédent, boucle C et initialisation des gardes comprises.
Les 199 680 appels des entrées texte numériques passent aussi sur les deux
processeurs, avec 3 072 placements de pile et temporaires hostiles.

## Audit de la session du 5 novembre 2026 — 13 séries

Les 13 séries vont de `4cf79ff` à `207c806`, après la base `2813fa6`.
Le banc passe de **479 à 642 cas**. Tous les champs des 479 références
initiales sont conservés ou abaissés ; aucun budget absolu n'est relevé.
Les petits écarts de cycles liés au placement sont détaillés dans les séries
concernées, avec les anciennes limites conservées.

Un checkout détaché de `207c806` reconstruit a2run et a2shot, puis reproduit
**exactement les 642 dictionnaires de mesures** du relevé principal avec
`dev/bench/run.py --dhgr --check`. `make all` reconstruit tous les disques
sans aucune différence Git ; les 18 jumeaux WOZ correspondent. Seules les
images originales locales de Wilderness ont été copiées pour cette
reconstruction, sans objets ni autres résultats de compilation.

`make test-hgr` passe entièrement. Toutes les commandes de `test-dhgr`
passent également : après deux dépassements du délai réel de 120 secondes
pour les 526 336 appels du test de transferts IIe, ce seul délai hôte est
porté à 300 secondes. La suite reprend à ce test et termine ses 55 commandes
restantes ; assertions, nombres de cas et limites d'exécution émulée restent
inchangés. `make test-tools` passe après la dernière série ProDOS, ainsi que
les exemples minimaux, les tests rapides Robot Station et MB Tracker IIe/IIc.
La campagne complète de 20 missions et les essais aléatoires de Robot Station
passent sur IIe et IIc. Les démos DHGR action, lander, half-pipe, corde et
catapulte, ainsi que les contacts physiques et leurs variantes, passent aussi.

Les interfaces publiques sont conservées et les références C restent
accessibles. Les derniers changements ProDOS ne modifient aucune des 634
mesures graphiques précédentes. L'état des sources et des disques est
vérifié après reconstruction, y compris les règles de sélection des sources
assembleur homonymes des références C.

Les fichiers binaires réellement livrés dans les disques DOS passent de
8 576 à **8 417 octets** pour HGR et de 9 010 à **8 404** pour DHGR.
Les fichiers ProDOS concernés gardent leurs tailles réservées : les gains
de code n'impliquent pas une diminution des zones remplies par le linker.
MB Tracker libère notamment 64 octets de code dans OVL2 et 2 octets de BSS.
Les quatre disques modifiés sont HGR, DHGR, ROBOTSTATION et MBTRACKER,
avec leurs WOZ ; tous les autres restent identiques.

## Série du 5 novembre 2026 : validation des noms ProDOS isolée

Le membre natif `name_valid.s` vérifie les 1–15 caractères sans pile C,
état persistant, code MLI ni bloc de catalogue. Le premier caractère reste
une lettre majuscule ; les suivants acceptent aussi chiffres et point.
Le C original reste une référence explicite. `PRODOS_NAME_SRCS` permet
une sélection indépendante ; `PRODOS_DIR_SRCS` conserve les deux fonctions.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| « A » | 216 → 55 | 1 979 → 575 |
| « DEMO.AYS » | 980 → 265 | 1 986 → 582 |
| Nom valide de 15 caractères | 1 830 → 435 | 1 993 → 589 |
| Nom vide | 134 → 46 | 1 978 → 574 |
| Barre oblique invalide | 258 → 76 | 1 981 → 577 |
| Nom trop long | 1 818 → 453 | 1 994 → 590 |

Les clients isolés gagnent 1 404 octets chargés et 547 octets de RAM,
avec piles C/matérielle 2/7 → 0/4 et page zéro inchangée. Les huit nouveaux
cas s'améliorent ; les 634 précédents restent identiques, pour 642 mesures.
MB Tracker garde le validateur dans OVL2 : catalogue + validation y passent
de 645 à 581 octets, et leur BSS de 525 à 523.

La référence C et le natif passent 71 680 appels : tous les premiers/deuxièmes
octets, toutes les classes à chacune des 16 positions, les longueurs limites,
2 048 placements de pointeurs/pile, les gardes et l'extraction indépendante
de l'archive. Le natif passe sur II+ et IIe. Le catalogue passe aussi sur
hôte, 6502 et 65C02 avec données d'overlay ; les scénarios MB Tracker IIe/IIc
avec et sans carte passent. MBTRACKER.po et son WOZ sont reconstruits,
avec les 18 jumeaux vérifiés.

## Série du 5 novembre 2026 : échelle des rayons d'ellipse native

Le coefficient absolu est parcouru sur six bits, avec la récurrence
`acc = (acc + bit * rayon) >> 1`. Le rayon est au plus 32 767 : chaque
addition tient sur 16 bits. Les coefficients 0 et ±64 ont un chemin direct.
Le signe est appliqué après division, conservant la troncature vers zéro.
Le C portable reste disponible, y compris pour une référence cc65 explicite.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Petite ellipse | 205 861 → 156 385 | 3 356 → 3 084 |
| Boîte plein écran | 236 269 → 186 761 | 3 346 → 3 074 |
| Coins inversés | 236 453 → 186 945 | 3 346 → 3 074 |
| Boîte maximale découpée | 276 315 → 190 971 | 3 338 → 3 066 |
| Boîte très large | 257 622 → 171 778 | 3 348 → 3 076 |
| Rayon 511 | 243 199 → 188 320 | 3 348 → 3 076 |
| Rayon 512 | 268 701 → 188 629 | 3 342 → 3 070 |

Chaque client gagne 272 octets ; les sept ellipses non dégénérées mesurées
réduisent leur pile C de 33 à 28 octets. RAM, page zéro et pile matérielle
inchangées. La forme horizontale coûte un cycle de placement supplémentaire
(2 327 → 2 328), avec son ancienne référence conservée. Les 622 cas précédents
restent identiques ; les 12 nouveaux portent le banc à 634 mesures.
Les budgets relatifs et absolus du relevé complet restent respectés.

Référence C et natif vérifient les 4 227 072 couples rayon/coefficient,
les résultats signés, les gardes et 2 048 placements de pile. Le natif passe
sur II+ et IIe. Les 60 boîtes de l'oracle des coordonnées couvrent les
largeurs HGR et DHGR, coins inversés, dégénérescences et grands mots x.
La reconstruction et les 18 WOZ restent identiques. La documentation décrit
les familles natives et leurs références C.

## Série du 5 novembre 2026 : cercles GFX natifs et découpage

Le cercle garde sept octets privés sur la pile et choisit une boucle sans
vérification par point quand toute la forme est visible. L'autre boucle
rejette les coordonnées signées hors écran avant de pousser le point.
Les symétries, leur ordre et les égalités restent ceux du C, sans doublons.
Le cas x=y termine immédiatement après sa dernière symétrie.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Rayon zéro HGR | 769 → 317 | 2 214 → 1 951 |
| Rayon 16 intérieur HGR | 29 388 → 28 975 | 2 216 → 1 953 |
| Rayon 90 intérieur HGR | 159 075 → 158 542 | 2 216 → 1 953 |
| Découpage gauche HGR | 38 275 → 20 532 | 2 212 → 1 949 |
| Découpage haut HGR | 39 435 → 17 641 | 2 210 → 1 947 |
| Cercle au coin HGR | 61 494 → 23 331 | 2 206 → 1 943 |
| Rayon 255 HGR | 401 954 → 87 406 | 2 216 → 1 953 |
| Rayon 16 DHGR monochrome | 37 419 → 36 940 | 2 982 → 2 741 |
| Rayon 16 DHGR couleur | 35 684 → 35 307 | 3 115 → 2 852 |

Piles C HGR intérieur/découpé 14/18 → 9 ; rayon zéro/rejets 14 → 3.
Les cercles découpés gagnent deux octets de pile matérielle. RAM et page
zéro inchangées. Les 14 cas concernés gagnent en taille et vitesse ;
608 autres mesures restent identiques. Les 12 nouveaux cas donnent 622 mesures.

Référence C et natif passent 73 307 tracés exacts (13 010 830 pixels) :
toutes les paires rayon/y, tous les mots x rejetés à droite, centres sur et
hors écran, grilles vides/étroites, temporaires hostiles et 2 048 placements
de pile. Le natif passe sur II+ et IIe. L'oracle des pixels, l'intégration
HGR, la démo DHGR, les règles de construction, la reconstruction, les 18
jumeaux WOZ et le gate passent. DHGR.dsk et son WOZ changent.

La démo sélectionne explicitement le cercle assembleur, avec test des exports
et de la conservation des sources ; une règle C homonyme ne peut plus le
remplacer par son fichier temporaire. Le C reste la référence portable.

## Série du 5 novembre 2026 : lignes GFX génériques natives

Le Bresenham générique conserve ses comparaisons strictes et l'ordre des
pixels, avec 14 octets privés sur la pile C. Le double de l'erreur ne vit
dans les temporaires qu'entre deux appels au backend. Les axes réutilisent
le cadre original, et les diagonales invalides sont rejetées avant de créer
les temporaires. La version HGR spécialisée et le C de référence restent disponibles.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Grande diagonale DHGR monochrome | 433 885 → 300 683 | 3 336 → 3 085 |
| Grande diagonale DHGR couleur | 152 003 → 106 646 | 3 532 → 3 281 |
| Pente forte monochrome | 138 320 → 98 674 | 3 338 → 3 087 |
| Égalités de pente couleur | 25 960 → 17 951 | 3 536 → 3 285 |
| Horizontal découpé couleur | 2 674 → 2 518 | 3 531 → 3 280 |
| Vertical découpé couleur | 21 393 → 21 231 | 3 534 → 3 283 |
| Diagonale rejetée en x, couleur | 254 → 192 | 3 534 → 3 283 |

Piles C des diagonales mono/couleur 29/28 → 17/16 ; axes couleur 31 → 5 ;
rejets 26 → 5. Les axes gagnent aussi deux octets de pile matérielle.
RAM et page zéro inchangées. Les 24 cas concernés s'améliorent en taille
et vitesse ; 586 autres sont identiques. Les 22 nouveaux cas portent le
banc à 610 mesures.

La référence C et le natif passent 18 020 tracés exacts (3 601 461 pixels),
tous les mots x pour axes/rejets, toutes les paires y invalides, des grilles
vides ou réduites, des temporaires hostiles et 2 048 placements de pile.
Le natif passe sur II+ et IIe. Les images DHGR sont vérifiées sur les deux
pages et banques ; DHGR étendu, tests rapides Robot Station IIe/IIc,
reconstruction, 18 jumeaux WOZ et gate passent.

Robot Station sélectionne explicitement la famille vectorielle native,
avec vérification des objets et de la conservation des références homonymes.
Les disques et leurs 18 WOZ restent identiques.

## Série du 5 novembre 2026 : contours GFX natifs communs

Le contour trie les coins complets dans le cadre de l'appelant, puis prépare
les arguments des segments directement sur la pile. Les coins ne sont jamais
écrits deux fois ; les bords hors écran ne sont pas déplacés. Les backends
peuvent détruire tous les temporaires cc65 entre deux appels. Le C reste
la référence portable. Aucun octet de RAM ou de page zéro n'est ajouté.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Point HGR | 752 → 663 | 1 840 → 1 591 |
| Horizontal HGR | 1 208 → 1 091 | 1 834 → 1 585 |
| Rectangle HGR | 22 668 → 22 158 | 1 838 → 1 589 |
| Coins inversés HGR | 22 946 → 22 264 | 1 840 → 1 591 |
| Rectangle découpé HGR | 2 573 → 2 207 | 1 832 → 1 583 |
| Deux lignes adjacentes HGR | 1 485 → 1 332 | 1 840 → 1 591 |
| Contour DHGR monochrome | 47 350 → 47 553 | 3 014 → 2 770 |
| Contour DHGR couleur | 58 917 → 59 189 | 3 167 → 2 923 |

Les formes HGR réduites à un point/axe passent de 9–10 à 6 octets de pile C,
et de 10 à 8 octets de pile matérielle. Les autres pics restent identiques.
Les deux contours DHGR paient 0,43/0,46 % de cycles de placement ; leurs
anciennes références de cycles restent en vigueur. Les 12 nouveaux cas HGR
s'améliorent en taille et vitesse ; 574 autres mesures sont identiques,
pour 588 cas au total.

La référence et le natif passent 528 896 cas : mots x complets, toutes les
paires y, neuf dimensions d'écran, ordre exact des segments, temporaires
hostiles, gardes et 2 048 positions de pile. Le natif passe sur II+ et IIe.
Le contrôle des pixels vérifie 625 rectangles hôte et 158 scènes cc65,
avec cercles, découpage, pages et trous écran. Intégration HGR, DHGR étendu,
démo HGR, reconstruction et gate passent. HGR.dsk et son WOZ sont reconstruits.

## Série du 5 novembre 2026 : backend GFX DHGR couleur natif et séparé

Le backend distingue les dimensions, le réglage du crayon et chaque
primitive. L'état `dhgr_color_dot` est isolé du renderer, permettant un
réglage de couleur seul sans code de tracé. Le point vérifie x avant de
le réduire à un octet et conserve les effets du C lorsque seul y est invalide.
Les axes réutilisent leurs arguments pour le rectangle, qui trie/découpe
les coins avant de former les quatre arguments du remplissage couleur.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Crayon seul | 76 → 20 | 3 016 → 775 |
| Dimensions seules | inchangés | 3 029 → 785 |
| Point (139,191) | 330 → 264 | 3 052 → 1 781 |
| Horizontal découpé | 2 902 → 2 451 | 3 041 → 2 483 |
| Vertical découpé | 21 498 → 21 306 | 3 040 → 2 484 |
| Rectangle découpé | 4 381 → 4 025 | 3 048 → 2 460 |
| Effacement seul | 112 521 → 112 391 | 3 016 → 966 |
| Grande diagonale générique | 164 825 → 152 003 | 3 784 → 3 532 |
| Cercle de rayon 16 | 41 897 → 35 684 | 4 318 → 3 115 |

Piles C point/horizontal/vertical/rectangle 3/19/18/14 → 2/5/5/5 ;
piles matérielles des axes 11 → 7. Les clients point/cercle/crayon retirent
25 octets de RAM, dimensions/effacement 27 ; page zéro inchangée.
Les 21 cas couleur s'améliorent, 555 autres mesures restent identiques.

C et natif sont contrôlés sur les mots x, toutes les paires y/couleur et
les octets d'effacement ; le natif passe aussi 1 024 positions de pile.
Rectangles et axes couleur passent chacun 525 568 cas, dont 1 024 placements
de pile, avec temporaires hostiles. Sept clients minimaux excluent les
familles inutilisées. Lignes génériques, DHGR étendu, démo DHGR et tests
rapides Robot Station IIe/IIc passent, ainsi que le gate complet.

La démo et Robot Station sélectionnent désormais explicitement les sources
assembleur du backend : leurs anciennes règles vpath pouvaient préférer
la référence C homonyme. Un test reconstruit les objets isolés des deux
consommateurs, contrôle leurs exports et la conservation des sources.
DHGR.dsk et ROBOTSTATION.po sont reconstruits, avec leurs WOZ ; les 18
jumeaux correspondent. Les références C restent disponibles.

## Série du 5 novembre 2026 : backend GFX DHGR monochrome natif et séparé

Les dimensions, l'état du crayon, son réglage, le point, les deux axes,
le rectangle et l'effacement sont des membres indépendants. Les entrées
point/axes ajoutent seulement le crayon au cadre existant. Le rectangle
trie et découpe les mots complets puis transforme son cadre en celui du
remplissage de bits, avec un seul octet supplémentaire. Le C reste disponible.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Crayon non nul seul | 93 → 24 | 3 218 → 779 |
| Dimensions seules | inchangés | 3 231 → 785 |
| Point (559,191) | 432 → 322 | 3 256 → 1 672 |
| Segment horizontal | 2 380 → 2 234 | 3 246 → 2 300 |
| Segment vertical | 19 450 → 19 183 | 3 242 → 2 236 |
| Rectangle découpé | 3 300 → 2 963 | 3 250 → 2 339 |
| Effacement blanc | 112 525 → 112 400 | 3 218 → 975 |
| Grande diagonale générique | 496 434 → 433 885 | 3 986 → 3 336 |
| Cercle de rayon 16 | 47 424 → 37 419 | 4 520 → 2 982 |

Piles C point/horizontal/vertical/rectangle 6/11/10/15 → 3/6/6/6 ;
pile matérielle −2 pour ces appels. Crayon et effacement n'utilisent plus
la pile C. Point/cercle/crayon seuls gagnent 25 octets de RAM, dimensions
et effacement 26 ; page zéro inchangée. Les 42 nouveaux cas distinguent
les deux backends : 21 cas monochromes améliorés, 555 autres mesures identiques,
pour un banc de 576 cas.

Le C de référence est vérifié. Le natif passe sur II+ et IIe 525 568
rectangles avec 1 024 positions de pile, et 196 608 appels point/axes
sur les mots complets avec toutes les valeurs du crayon. Les 256 couleurs
d'effacement et l'indépendance du crayon sont contrôlées. Sept clients
minimaux excluent les familles inutiles ; lignes génériques, 48 étapes
DHGR étendues (pages/banques/texte/transitions), intégration HGR, gate et
reconstruction passent. Disques et 18 WOZ inchangés.

## Série du 5 novembre 2026 : entrée native du dessin de sprites doublés

L'entrée refuse les dimensions nulles, les coordonnées hors écran et les
sources dépassant 64 octets avant de réserver de pile supplémentaire.
Le produit est borné pendant son calcul binaire. Après conversion, les
arguments initiaux deviennent directement le cadre du blitter ; le mode,
la couleur et le pointeur source sont transmis sans altération. Le tampon
privé reste à 256 octets et la référence C est conservée.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Un octet blanc | 1 769 → 1 465 | 1 772 → 1 736 |
| Largeur source 64 | 13 917 → 13 591 | 1 782 → 1 746 |
| Hauteur source 64 | 16 385 → 16 206 | 1 790 → 1 754 |
| Sprite blanc 3×16 | 13 926 → 13 698 | 1 786 → 1 750 |
| Sprite bleu 3×16 | 12 403 → 12 183 | 1 788 → 1 752 |
| Taille trop grande | 570 → 152 | 1 774 → 1 738 |
| x hors écran | 584 → 198 | 1 782 → 1 746 |
| y hors écran | 594 → 187 | 1 782 → 1 746 |

Les clients économisent 36 octets, sans changer RAM ni page zéro.
Pile C valide/rejetée 18/11 → 14/8 ; pile matérielle rejetée 8 → 4.
Les dix nouveaux cas portent le banc à 534 : les 12 cas du wrapper
s'améliorent, les 522 autres restent identiques.

C puis assembleur passent 264 192 appels sur II+ et IIe : tous les couples
de dimensions, mots x/source, octets y/couleur/mode, séquence et arguments
exacts des deux moteurs, même tampon entre conversion et dessin, temporaires
hostiles et 2 048 positions de pile. Les x2 réels, ASan/UBSan hôte,
69 clients minimaux, intégration HGR, gate, reconstruction et 18 WOZ passent.
Les disques restent identiques.

## Série du 5 novembre 2026 : inflation native des sprites doublés

L'entrée calcule seulement l'octet haut du produit largeur × hauteur en
huit étapes pour refuser toute sortie dépassant 65 535 octets. Le noyau
convertit chaque octet avec la table de 16 valeurs existante, écrit les
deux lignes et ajoute la palette uniquement aux octets non nuls. Le stride
16 bits réutilise les deux anciens arguments du pointeur source ; aucune
nouvelle RAM/page zéro n'est réservée. Les versions C restent disponibles.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Un octet blanc | 1 834 → 599 | 1 497 → 1 106 |
| Sprite blanc 3×16 | 52 824 → 10 604 | 1 503 → 1 112 |
| Sprite bleu 3×16 | 44 748 → 9 137 | 1 505 → 1 114 |
| Source blanche 255×2 | 524 594 → 100 146 | 1 501 → 1 110 |
| Source bleue 255×2 | 438 833 → 84 593 | 1 503 → 1 112 |
| Source blanche 1×255 | 308 623 → 63 996 | 1 503 → 1 112 |
| Taille trop grande | 534 → 314 | 1 499 → 1 108 |
| Conversion + dessin blanc 3×16 | 56 150 → 13 926 | 2 163 → 1 786 |

L'inflation seule économise 391 octets, piles C/matérielle 23/8 → 5/6.
La conversion suivie du dessin gagne 377 octets, pile C 34 → 18.
Les 16 nouveaux cas portent le banc à 524 ; ces 16 cas s'améliorent et les
508 précédents restent identiques. Budgets absolus inchangés.

Les 65 536 couples octet/couleur, 1 536 alignements source/sortie et toutes
les dimensions nulles ou trop grandes sont contrôlés avec oracle pixel et
gardes, sur C de référence et noyau natif. L'entrée native passe aussi
198 144 appels sur II+ et IIe : tous les produits et mots pointeurs,
limite exacte 16 383/16 384, paramètres internes, scratch hostile et
1 536 positions de pile. Les anciens cas x2 (strides de 510, grands nombres
de lignes, blits découpés), 69 clients minimaux, intégration HGR,
ASan/UBSan hôte, gate et reconstruction passent. Les disques et 18 WOZ
restent identiques.

## Série du 5 novembre 2026 : curseur et chaîne GFX natifs séparés

Le curseur, le positionnement, le caractère et la chaîne deviennent quatre
membres d'archive indépendants. Positionner ne charge plus la police ni le
renderer. L'itérateur de chaîne reste privé sur la pile C et survit à tous
les temporaires écrasés par le backend. Les retours ligne/chariot, contrôles,
rebouclages en dernière ligne et règles de promotion des coordonnées restent
ceux du C, conservé comme référence.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Position (12,8) seule | 153 → 91 | 2 134 → 586 |
| Position (255,255) seule | 177 → 103 | 2 132 → 584 |
| Nouvelle ligne | 109 → 45 | 2 139 → 1 938 |
| Retour chariot | 88 → 29 | 2 139 → 1 938 |
| Contrôle ignoré | 96 → 27 | 2 129 → 1 889 |
| Chaîne vide | 123 → 115 | 2 132 → 1 972 |
| APPLE II, tables froides | 27 838 → 26 994 | 2 148 → 2 027 |
| Non signé 65535, chaud | 9 247 → 8 681 | 2 294 → 2 195 |
| Signé −32768, chaud | 10 880 → 10 292 | 2 340 → 2 241 |
| Hexadécimal FFFF, chaud | 6 635 → 6 244 | 2 269 → 2 170 |

Positionner seul économise 1 548 octets chargés, 950 de RAM et 12 de page
zéro ; piles C/matérielle 2/6 → 1/4. Les clients de nombres gagnent
99 octets et un octet de pile C, sans changer RAM/page zéro/pile matérielle.
Les 12 nouveaux cas portent le banc à 508 : les 29 cas concernés
s'améliorent, 479 restent identiques.

La référence C puis les entrées natives passent sur II+ et IIe 786 432 cas
coordonnées/caractères sur quatre grilles, 256 placements de chaînes et
768 positions de pile. Le flux de glyphes, les contrôles, les gardes et
les temporaires hostiles sont vérifiés. Les 67 clients minimaux, l'intégration
HGR, le starter et le gate complet passent ; reconstruction et 18 WOZ
validés, disques inchangés.

## Série du 5 novembre 2026 : rectangles GFX HGR natifs et effacement isolé

L'entrée trie les coordonnées complètes, découpe les maxima puis calcule
la hauteur inclusive. Elle utilise directement les cinq octets d'arguments
du client et le noyau de spans existant. L'effacement devient un alias
indépendant vers `hgr_clear`, sans importer le rectangle ni ses tables.
La référence C reste disponible.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Rectangle ponctuel | 612 → 492 | 1 392 → 1 136 |
| Rectangle 252×176 | 78 914 → 78 615 | 1 390 → 1 134 |
| Mêmes coins inversés | 79 190 → 78 652 | 1 392 → 1 136 |
| Rectangle découpé | 4 944 → 4 549 | 1 384 → 1 128 |
| Rejet x | 422 → 241 | 1 386 → 1 130 |
| Rejet y | 327 → 139 | 1 386 → 1 130 |
| Effacement seul | 46 414 → 46 346 | 1 317 → 608 |

Le rectangle économise 256 octets et réduit sa pile C de 6–8 à cinq octets,
avec RAM/page zéro identiques. L'effacement économise 709 octets de binaire,
947 de RAM et 14 de page zéro ; piles C/matérielle 1/6 → 0/4.
Les sept cas concernés s'améliorent ; les 489 autres restent identiques.

La référence C puis l'entrée native passent 525 568 appels sur II+ et IIe :
tous les mots x dans les deux ordres autour de trois ancres, toutes les
paires y, cas dégénérés, arguments du span, temporaires écrasés, gardes et
1 024 positions de pile. Les 64 clients minimaux, l'intégration HGR,
les 158 scènes de contours/remplissage sur deux pages, les starters II+/IIe
et le gate complet passent. Reconstruction et 18 WOZ validés, disques inchangés.

## Série du 5 novembre 2026 : aiguillage natif des lignes GFX HGR

L'entrée réutilise les cinq octets d'arguments du client. Elle conserve
la priorité horizontale, décale seulement les deux octets de x1 pour un
segment horizontal et retire x1 pour un segment vertical. Les diagonales
transmettent directement le cadre initial à `hgr_line`. Les axes gardent
leur découpage historique, y compris pour des extrémités hors écran.
La référence C reste disponible ; le backend DHGR garde son Bresenham C.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Horizontal découpé | 1 115 → 986 | 2 100 → 1 953 |
| Vertical découpé | 11 559 → 11 371 | 2 106 → 1 959 |
| Diagonale rejetée | 383 → 190 | 2 096 → 1 949 |
| Diagonale 280×192 | 21 310 → 21 447 | 2 100 → 1 953 |

Les clients économisent 147 octets, sans RAM ni page zéro supplémentaire.
Pile C horizontale/verticale/diagonale 10/9/11 → 5 ; pile matérielle −2.
Le déplacement du noyau dans le binaire augmente de 0,64 % le temps de
la grande diagonale mesurée ; son ancienne référence de cycles est
conservée. Trois cas gagnent en vitesse, deux diagonales identiques en
travail gagnent en taille/pile ; les 491 autres mesures restent identiques.

La référence C puis l'entrée native passent 918 528 appels sur II+ et IIe :
tous les mots x dans les deux ordres autour de trois ancres, toutes les
paires y, priorité des axes, arguments exacts, temporaires écrasés et
1 024 positions de pile. Les 464 lignes réelles, les backends DHGR mono et
couleur, l'intégration HGR, le starter et le gate complet passent.
La reconstruction ne change aucun disque ; les 18 WOZ restent cohérents.

## Série du 5 novembre 2026 : alias GFX HGR indépendants

Les entrées point et segments horizontal/vertical ont les mêmes signatures
cc65 que HGR : les symboles GFX deviennent des alias directs, dans trois
membres d'archive séparés. Les dimensions sont un quatrième membre sans
code de dessin. La référence C reste disponible.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Point (139,95) | 382 → 249 | 1 490 → 867 |
| Point rejeté | 248 → 114 | 1 488 → 865 |
| Segment horizontal | 1 021 → 853 | 1 502 → 1 106 |
| Horizontal trié/découpé | 1 089 → 919 | 1 494 → 1 098 |
| Segment vertical | 10 612 → 10 405 | 1 494 → 1 064 |
| Vertical trié/découpé | 11 529 → 11 312 | 1 492 → 1 062 |

Pile C point/horizontal/vertical 5/9/7 → 2/4/3, pile matérielle −2 octets.
Le point retire 14 octets de page zéro, les segments trois ; RAM identique.
Les 17 nouveaux cas portent le banc à 496 : 11 cas s'améliorent et
485 restent identiques. Les références de cycles antérieures ne sont pas
relevées et les budgets absolus restent inchangés.

Les 63 clients minimaux vérifient notamment l'égalité des adresses GFX/HGR
et l'absence des primitives inutilisées. Intégration HGR, lignes,
contours/rectangles, starter II+ et reconstruction complète passent ;
les 18 jumeaux WOZ correspondent. Seuls HGR.dsk et son WOZ sont reconstruits
avec un contenu différent.

## Audit final du 5 novembre 2026

Les 41 séries de cette session se terminent au commit `8ff9b1a`.
Les suites complètes `make test-hgr` et `make test-dhgr` passent.
Un checkout propre de ce commit, avec les outils reconstruits, reproduit
exactement les 479 dictionnaires de mesures du rapport final ;
`dev/bench/run.py --dhgr --check` passe sans assouplir les budgets absolus.
Après récupération des ressources historiques de Wilderness, `make all`
ne modifie aucun fichier suivi, et `make test-woz` confirme les 18 jumeaux
WOZ des disques livrés.

## Série du 5 novembre 2026 : backend de caractères GFX HGR natif et séparé

Le backend distingue ses dimensions constantes, son rendu de caractère et
sa couleur sans effet. La référence C complète reste disponible. Le rendu
réutilise les deux arguments du client comme chaîne caractère/NUL, avec
trois octets supplémentaires pour y/x. Les coordonnées gardent les règles
exactes du C : colonne × 8 sur 16 bits, ligne × 8 tronquée à un octet.
Le texte HGR consomme les trois coordonnées, puis l'entrée libère la chaîne.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Caractère à l'origine | 1 301 → 1 195 | 1 910 → 1 867 |
| Dernière cellule | 1 868 → 1 767 | 1 912 → 1 869 |
| Caractère NUL | 514 → 408 | 1 908 → 1 865 |
| Colonne invalide | 428 → 322 | 1 911 → 1 868 |
| Non signé 65535 | 9 777 → 9 247 | 2 319 → 2 294 |
| Signé −32768 | 11 601 → 10 880 | 2 365 → 2 340 |
| Hexadécimal FFFF | 7 087 → 6 635 | 2 294 → 2 269 |
| Couleur sans effet | 63 → 14 | 1 874 → 519 |

Les clients de glyphes économisent 43 octets, ceux de nombres 25.
Pile C du glyphe 8 → 5 ; nombres non signé/signé/hex 17/18/16 → 14/15/13.
RAM, page zéro et pics matériels identiques pour ces clients. Le client
couleur seul n'importe plus le renderer : RAM 1 247 → 297, page zéro
38 → 26, pile C 1 → 0 et matérielle 6 → 4. Les 26 cas concernés
s'améliorent, 453 sont identiques ; neuf nouveaux cas portent le banc à 479.

Le C puis les entrées NMOS/65C02 passent 197 632 appels : tous les couples
colonne/ligne, caractère/colonne et caractère/ligne, coordonnées exactes
et chaînes de deux octets, couleurs sans effet, scratch écrasé, gardes et
1 024 positions de pile. Deux nouveaux clients minimaux excluent le rendu
pour les dimensions seules et la couleur seule. Les 59 clients minimaux,
l'intégration HGR, le starter II+/IIe, `make all` et le gate passent.
Les disques livrés restent identiques.

## Série du 5 novembre 2026 : entrées natives des nombres GFX

Les trois formats gardent leurs membres d'archive séparés. L'entrée conserve
la valeur sur la pile matérielle pendant la réservation du tampon local et
le passage de son pointeur, puis restaure A/X avant la conversion. Le texte
reçoit le tampon via la pile C ; aucune adresse de travail ne doit survivre
à l'appel du moteur de texte. Les références C portables restent disponibles.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Non signé 0 | 2 129 → 2 056 | 2 325 → 2 319 |
| Non signé 65535 | 9 846 → 9 777 | 2 325 → 2 319 |
| Signé 0 | 2 134 → 2 069 | 2 367 → 2 364 |
| Signé −32768 | 11 630 → 11 601 | 2 368 → 2 365 |
| Hexadécimal 0 | 2 073 → 1 993 | 2 300 → 2 294 |
| Hexadécimal FFFF | 7 185 → 7 087 | 2 300 → 2 294 |

Piles C non signé/signé/hex 19/20/18 → 17/18/16, sans changement de RAM,
page zéro ou pic matériel. Les 17 nouveaux cas s'améliorent ; les 453
précédents sont identiques, soit 470 mesures.

Le C puis les entrées natives NMOS/65C02 passent 199 680 appels : tous les
mots 16 bits dans les trois formats, NUL et absence de caractères résiduels,
registres scratch du texte écrasés, gardes et 3 072 positions de pile.
L'intégration HGR rend les trois formats ; 57 clients minimaux, `make all`
et le gate complet passent. Aucun disque livré ne change.

## Série du 5 novembre 2026 : lecture et écriture de points DHGR indépendantes

Le calcul d'adresse/masque devient `dhgr_locate.s`, sans changement de son
corps. Un lecteur seul ne lie plus le code d'écriture. Les entrées passent
les coordonnées via le scratch existant ; le traceur libère directement
ses trois arguments, le lecteur incrémente deux fois la pile en gardant
son résultat octet dans A/X. L'accès bancaire et le masque IRQ sont inchangés.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Tracé auxiliaire, bit posé | 318 → 305 | 1 629 → 1 621 |
| Tracé principal, bit posé | 293 → 277 | 1 631 → 1 623 |
| Tracé du dernier point | 303 → 287 | 1 633 → 1 625 |
| Lecture auxiliaire | 285 → 279 | 1 900 → 1 801 |
| Lecture principale | 265 → 259 | 1 904 → 1 805 |
| Lecture du dernier point | 273 → 266 | 1 906 → 1 807 |
| Tracé hors écran | 171 → 155 | 1 633 → 1 625 |
| Lecture hors écran | 160 → 155 | 1 906 → 1 807 |

Les clients lecteurs gagnent 99 octets, les traceurs huit. RAM, page zéro
et pics de pile mesurés sont inchangés. Les 21 nouveaux cas s'améliorent ;
les 432 précédents restent identiques, soit 453 mesures au total.

La fixture passe avant/après sur IIe et IIc : 694 336 appels par machine,
tous les points des deux pages, les 256 sélecteurs, tous les mots x invalides
et octets y invalides, lecture indépendante des banques et des trous vidéo,
restauration des banques et du masque IRQ, résultat A/X et 2 048 placements
de pile. Les tests DHGR, étendus, renderer, intégration HGR et 57 clients
minimaux passent. Le client de lecture exclut explicitement le traceur.
`make all` et le gate complet passent ; les disques livrés sont identiques.

## Série du 5 novembre 2026 : préparation native des sprites DHGR

L'entrée native empile uniquement le pointeur de masque reçu en A/X :
les neuf octets sont tous des arguments, sans cadre local. Elle vérifie
l'étendue complète avant de clipper à droite. La banque utilise le produit
hauteur d'origine × pas en huit étapes, sans calcul pour la phase zéro ;
le décalage total de phase est appliqué une seule fois à chaque pointeur.
La hauteur visible est bornée ensuite. Le parcours de lignes adresse les
tables directement et réutilise les arguments pour les deux pointeurs,
la ligne, la hauteur restante et la colonne. Le noyau masqué est inchangé.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Petit sprite | 2 272 → 1 205 | 2 397 → 2 077 |
| 14×8, masque partiel | 12 210 → 10 442 | 2 477 → 2 251 |
| 14×8, masque opaque | 10 105 → 8 331 | 2 469 → 2 243 |
| Huit lignes, phase 0 | 5 839 → 4 062 | 2 399 → 2 079 |
| Huit lignes, phase 1 | 5 952 → 4 309 | 2 399 → 2 079 |
| Huit lignes, phase 6 | 6 525 → 4 435 | 2 399 → 2 079 |
| Hauteur 255, une ligne visible | 1 999 → 987 | 2 400 → 2 080 |
| Largeur 255 clippée à droite | 1 995 → 958 | 2 401 → 2 081 |
| Pas insuffisant | 467 → 304 | 2 399 → 2 079 |

Économies de 320 octets isolés, ou 226 lorsque d'autres helpers C sont
déjà liés. Pile C 18 → 9 (rejets 16 → 9), sans changement de RAM, page zéro
ou pic matériel. Les 17 cas concernés s'améliorent, 415 sont identiques ;
14 nouveaux cas portent le banc à 432.

Le C puis l'assembleur NMOS/65C02 passent 787 456 appels : tous les couples
x/largeur, largeur/pas et y/hauteur, tous les pointeurs source et masque,
tous les produits hauteur/pas aux sept phases, chaque paramètre de ligne
comparé à un oracle indépendant, états rejetés, scratch écrasé, gardes et
1 024 positions de pile. Les tests étendus et renderer comparent les pixels
aux sept phases, le clipping et les restaurations. Transferts/masques,
compositeur IIe/IIc/IRQ, intégration HGR et 57 clients minimaux passent aussi.
Le client sprite seul exclut le helper d'adresse et le contrôleur de blocs.
`make all` et le gate complet passent ; les disques livrés restent identiques.

## Série du 5 novembre 2026 : contrôleur natif des transferts DHGR

Les entrées lecture/écriture sont des membres d'archive indépendants ;
leur contrôleur commun réutilise les six arguments du client. Après la
validation, la largeur devient le pas du tampon et la colonne contient
aussi le bit lecture/écriture. Les adresses viennent directement des tables
immuables : aucun paramètre poussé par ligne, aucun cadre local. La sortie
libère les six octets directement, sans helper de pile. Les noyaux bancaires
restent identiques et conservent leurs paramètres partagés entre les lignes.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Lecture 8×8 | 6 990 → 5 664 | 1 957 → 1 634 |
| Écriture 8×8 | 6 678 → 5 328 | 1 957 → 1 634 |
| Écriture, colonne impaire | 6 222 → 4 928 | 1 959 → 1 636 |
| Lecture d'un octet | 1 132 → 500 | 1 954 → 1 631 |
| Écriture d'un octet | 1 115 → 487 | 1 954 → 1 631 |
| Lecture sur 192 lignes | 71 731 → 52 440 | 1 958 → 1 635 |
| Écriture sur 192 lignes | 72 115 → 53 592 | 1 958 → 1 635 |
| Hauteur nulle | 750 → 231 | 1 956 → 1 633 |
| Origine hors écran | 403 → 144 | 1 956 → 1 633 |

Économie de 323 octets par client isolé. Pile C 18 → 6 (rejets 16 → 6),
pile matérielle 11 → 9, ou 8/9 → 4 pour les appels rejetés/vides.
RAM/page zéro inchangées. Les 21 cas concernés s'améliorent, 397 sont
identiques ; 18 nouveaux cas portent le banc à 418 mesures.

Le C de référence puis l'assembleur NMOS/65C02 passent 526 336 appels :
tous les couples bx/largeur, largeur/pas, y/hauteur et pointeurs 16 bits,
chaque adresse/banque/compte/tampon de ligne comparé à un oracle indépendant,
ordre lecture/écriture, effets de bord des rejets et hauteurs nulles,
registres scratch écrasés, gardes et 2 048 positions de pile. Le test
physique couvre 640 transferts/masques, toutes les largeurs et 256 masques,
les deux pages/banques, passages de page des pointeurs et masques IRQ.

Les tests étendus, compositeur IIe/IIc/IRQ, intégration HGR et 56 clients
minimaux passent. Les clients lecture/écriture excluent l'autre entrée et
le helper d'adresse. `make all`, ROBOTSTATION IIe/IIc, les 18 WOZ et le gate
complet passent. Seuls ROBOTSTATION et son WOZ changent.

## Série du 5 novembre 2026 : entrées natives de l'effacement et du texte compact DHGR

L'effacement complet transmet directement A à la préparation du motif,
puis termine par un saut au noyau. Le texte compact écrit les coordonnées,
charge le pointeur et libère les trois arguments directement : l'octet bas
du pointeur reste dans Y pendant l'addition à la pile C. Les deux entrées
suppriment leur temporaire local et gardent les modifications de coordonnées
effectuées par le noyau de texte. Aucun ajout de RAM/page zéro.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Effacement, couleurs 0/9/15/255 | 112 456 → 112 391 | 1 005 → 966 |
| Texte « APPLE II » | 13 220 → 13 186 | 2 901 → 2 864 |
| Chaîne vide | 216 → 159 | 2 893 → 2 856 |
| Dernière cellule | 1 555 → 1 499 | 2 897 → 2 860 |
| Abscisse hors écran | 201 → 144 | 2 896 → 2 859 |
| Ordonnée hors écran | 209 → 152 | 2 896 → 2 859 |
| Chaîne tronquée à la dernière cellule | 1 555 → 1 498 | 2 898 → 2 861 |

Économies de 39/37 octets chargés pour les clients isolés d'effacement/texte.
Piles C 1/4 → 0/3 ; pics matériels réduits de deux octets, y compris les
chaînes vides et rejetées (6 → 4). Les dix cas concernés s'améliorent ;
390 restent identiques. Huit nouveaux cas portent le banc à 400.

Le C de référence puis l'assembleur II+/IIe passent 132 352 appels : tous
les pointeurs 16 bits, les 65 536 couples x/y, les 256 couleurs, ordre
préparation/effacement, coordonnées modifiées par le noyau, scratch écrasé,
gardes et 1 024 positions de pile. Validation réelle : DHGR, étendus,
renderer, texte compact déplacé, effacements avec IRQ, intégration HGR,
55 clients minimaux, `make all`, exemples et ROBOTSTATION IIe/IIc,
1 000 images par cadence PAL/NTSC, 18 WOZ et gate complet.
Seuls DHGR et ROBOTSTATION avec leurs WOZ changent.

## Série du 5 novembre 2026 : état et pages DHGR indépendants

L'état DHGR devient un membre de données seul ; les quatre fonctions de
page ont chacune leur membre d'archive natif. La sélection ne crée plus
de temporaire sur la pile C. Le basculement conserve l'ancienne page
affichée dans Y, préservé par les entrées internes de lecture et d'affichage,
puis termine par la sélection. Les deux lectures gardent leur séquence
et leurs cycles. Les sélecteurs invalides et l'état avant initialisation
conservent exactement le comportement du C.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Sélection page 1 | 93 → 25 | 885 → 792 |
| Sélection page 2 | 95 → 31 | 880 → 787 |
| Sélecteur invalide | 78 → 23 | 880 → 787 |
| Lecture dessin page 1 | 24 → 24 | 878 → 784 |
| Lecture dessin page 2 | 25 → 25 | 883 → 807 |
| Lecture page affichée | 18 → 18 | 883 → 778 |
| Basculement | 211 → 88 | 883 → 820 |
| Basculement sans page précédemment affichée | 189 → 79 | 883 → 820 |

Pile C sélection/basculement 1/2 → 0, pile matérielle 6/8 → 4/6.
Les autres clients DHGR gagnent 41..111 octets ; les cinq cas d'effacement
avant initialisation DHGR gagnent 409 octets et neuf octets de page zéro,
car ils n'importent plus le gestionnaire de mode. RAM inchangée partout.
Le placement du code modifie certains cycles de rendu : ligne complète
2 226 → 2 208, effacement complet 114 377 → 112 456, mais écriture de bloc
6 615 → 6 678 et rectangle couleur 11 790 → 11 809. Le plus grand recul
relatif est un rejet couleur, 368 → 373 (+1,36 %). Les anciennes références
de cycles restent conservées pour tous les reculs.

Le C de référence puis l'assembleur NMOS/65C02 passent 131 328 combinaisons :
tous les octets de base, sélecteur et affichage, état initial, ordre du
basculement, gardes et contrat X/Y des vraies entrées d'affichage/lecture.
Trois nouveaux clients minimaux vérifient l'absence des fonctions inutiles ;
l'effacement seul exclut aussi le gestionnaire de mode. Le relevé complet
comprend 392 cas (huit nouveaux), 78 changés et 314 identiques.

Les tests DHGR, étendus, renderer, compositeur IIe/IIc/IRQ et intégration
HGR passent, ainsi que les 55 clients minimaux. `make all` reconstruit
DHGR, ROBOTSTATION et CHROMABREAK avec leurs WOZ. CHROMABREAK absorbe les
23 octets de code lib économisés dans sa réserve RODATA : ses adresses
assembleur, tables et variables restent celles vérifiées par les assertions.
Les tests des disques, des profils CHROMABREAK, des WOZ et le gate passent.

## Série du 5 novembre 2026 : entrées natives séparées des axes DHGR

Les deux fonctions de `dhgr_span.c` deviennent deux membres d'archive
indépendants. Les entrées natives trient les extrémités sur leur largeur
complète, bornent la fin puis forment le cadre de six octets attendu par
le remplissage monochrome. L'horizontale ajoute un octet à ses arguments,
la verticale deux. Les valeurs modulaires de largeur/hauteur hors écran
restent celles du C ; le remplissage prépare donc toujours le même motif
avant le rejet final. Aucun octet de RAM/page zéro supplémentaire.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Horizontale courte | 1 323 → 1 191 | 2 560 → 2 372 |
| Horizontale inversée | 1 478 → 1 213 | 2 560 → 2 372 |
| Horizontale clippée | 1 438 → 1 154 | 2 558 → 2 370 |
| Horizontale hors écran | 523 → 370 | 2 559 → 2 371 |
| Horizontale complète | 2 340 → 2 226 | 2 558 → 2 370 |
| Verticale courte | 3 123 → 2 983 | 2 555 → 2 307 |
| Verticale inversée | 3 164 → 2 992 | 2 554 → 2 306 |
| Verticale clippée | 1 229 → 1 053 | 2 555 → 2 307 |
| Verticale hors écran | 422 → 282 | 2 553 → 2 305 |

Économies de 188/248 octets pour les clients horizontaux/verticaux isolés.
Pile C 14/12 → 6, pile matérielle 9 → 7 (rejets 7 → 5). Les onze cas
concernés s'améliorent, 373 restent identiques ; dix cas sont nouveaux.

La fixture de 527 104 appels passe sur le C puis l'assembleur II+/IIe :
les deux domaines d'extrémités horizontales 16 bits contre trois ancres,
toutes les abscisses verticales et paires d'ordonnées, sélecteurs octet,
tri et étendues clippées/modulaires, registres de travail écrasés, gardes
et 2 048 positions de pile. Les tests réels étendus et GFX vérifient les
deux pages/banques, inversions, clipping et pixels. Deux nouveaux clients
minimaux excluent l'autre axe du lien. Validation complémentaire :
52 clients minimaux, intégration HGR, `make all`, relevé complet de 384 cas
et gate. Les disques livrés restent identiques.

## Série du 5 novembre 2026 : préparation native du remplissage couleur DHGR

`dhgr_fill.s` borne la largeur en pixels couleur, prépare le motif puis
étend les quatre octets d'arguments en cinq octets de rectangle binaire.
La hauteur reste dans X pendant les deux multiplications 16 bits par
quatre ; un seul octet de pile supplémentaire suffit. L'abscisse invalide
ne modifie pas le motif. Une abscisse valide prépare toujours la couleur,
y compris pour une largeur/hauteur nulle ou une ordonnée hors écran.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Petit rectangle couleur | 1 355 → 1 143 | 2 463 → 2 388 |
| Passage de x=63 à x=64 | 1 289 → 1 080 | 2 465 → 2 390 |
| Origine x=128 | 1 104 → 893 | 2 465 → 2 390 |
| Dernier pixel, largeur/hauteur maximales | 1 124 → 898 | 2 465 → 2 390 |
| Largeur 255 à l'origine | 2 421 → 2 197 | 2 464 → 2 389 |
| Abscisse hors écran | 180 → 124 | 2 465 → 2 390 |
| Hauteur nulle | 540 → 329 | 2 465 → 2 390 |
| Rectangle de 16 lignes | 12 016 → 11 790 | 2 467 → 2 392 |

Chaque client isolé gagne 75 octets ; pile C 12 → 5 (abscisse rejetée
7 → 4), pile matérielle 9 → 7 (rejets 6 → 5 ou 7 → 6), sans RAM/page zéro
supplémentaire. Les onze cas concernés sont plus rapides, 363 restent
identiques ; dix cas sont nouveaux.

La fixture de 67 840 appels passe d'abord sur le C, puis l'assembleur
II+/IIe : toutes les paires x/largeur, toutes les valeurs de y/hauteur/couleur,
ordre des appels, paramètres binaires clippés, registres de travail écrasés,
gardes et 1 024 positions de pile. Les tests réels vérifient pixels,
320 lignes colorées, 48 étapes étendues, deux backends GFX et deux pages/banques.
Validation complémentaire : 50 clients minimaux, intégration HGR,
`make all`, exemples DHGR (1 000 images NTSC/PAL), ROBOTSTATION IIe/IIc,
WOZ, relevé complet de 374 cas et gate. DHGR.dsk, ROBOTSTATION.po et leurs
WOZ sont reconstruits.

## Série du 5 novembre 2026 : transmission native du remplissage monochrome DHGR

`dhgr_fill_bits.s` transforme zéro/non-zéro en quatre octets identiques
0/127, consomme le seul octet de hauteur puis saute vers `dhgr_bit_rect`.
Les cinq octets restants ont déjà l'ordre attendu ; aucun argument n'est
recopié et aucun cadre local n'est créé. Le motif est toujours préparé,
même si le helper rejette ensuite la géométrie, comme dans la version C.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Petit rectangle, effacer | 1 245 → 1 072 | 2 303 → 2 240 |
| Petit rectangle, tracer | 1 244 → 1 071 | 2 302 → 2 239 |
| Sélecteur 255 | 1 246 → 1 073 | 2 304 → 2 241 |
| Dernier pixel, largeur/hauteur maximales | 890 → 721 | 2 300 → 2 237 |
| Origine hors écran | 361 → 190 | 2 299 → 2 236 |
| Hauteur nulle | 340 → 169 | 2 294 → 2 231 |
| Ligne monochrome | 2 514 → 2 340 | 2 608 → 2 558 |

Les clients isolés gagnent 63 octets, la ligne 50. Pile C 12 → 6 pour le
remplissage, 20 → 14 pour la ligne ; pile matérielle 9 → 7 (rejets 7 → 5)
et 11 → 9 respectivement. RAM/page zéro inchangées. Les neuf cas concernés
s'améliorent, 355 restent identiques ; huit cas sont nouveaux.

La fixture de 133 120 appels passe d'abord sur le C, puis l'assembleur
II+/IIe : tous les bits x/largeur/y/hauteur, les 256 sélecteurs, paramètres
bruts et quatre octets de motif même pour les cas invalides, registres de
travail écrasés, gardes et 1 024 positions de pile. Les tests réels vérifient
pixels, 48 étapes étendues, lignes des deux backends GFX, deux pages/banques
et restauration DOS. Validation complémentaire : 50 clients minimaux,
intégration HGR, `make all`, relevé complet de 364 cas et gate. Les disques
livrés restent identiques.

## Série du 5 novembre 2026 : bornage natif des rectangles DHGR

`dhgr_bit_rect.s` remplace le bornage C commun aux remplissages couleur
et monochrome. Les validations précèdent toute écriture des paramètres
du noyau. L'addition x+largeur conserve la retenue du 17e bit pour saturer
à droite, puis produit la borne inclusive ; la hauteur est bornée à part.
Les cinq octets d'arguments sont libérés avant le saut vers le noyau de
span. Aucun tampon local, octet de RAM ou page zéro supplémentaire.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Petit rectangle, helper direct | 1 291 → 1 023 | 2 442 → 2 300 |
| Dernier pixel, largeur 65535 | 988 → 671 | 2 441 → 2 299 |
| Largeur 65535 à l'origine | 2 308 → 1 975 | 2 438 → 2 296 |
| x+largeur déborde 16 bits | 1 004 → 676 | 2 444 → 2 302 |
| Écran entier | 242 925 → 242 457 | 2 441 → 2 299 |
| Origine hors écran | 201 → 142 | 2 442 → 2 300 |
| Hauteur nulle | 236 → 122 | 2 439 → 2 297 |
| Rectangle couleur public | 12 267 → 12 016 | 2 593 → 2 467 |
| Ligne monochrome publique | 2 796 → 2 514 | 2 725 → 2 608 |

Le helper isolé économise 142 octets, le rectangle public 126, la ligne
117. Pile C 9 → 5 pour le helper (rejets 7 → 5), 16 → 12 pour le rectangle
couleur, 24 → 20 pour la ligne ; les pics matériels baissent aussi de un
ou deux octets. Les onze cas concernés sont plus rapides ; 345 cas restent
identiques, neuf cas directs sont nouveaux et initialisent le mode DHGR.

La fixture de 328 704 appels passe sur le C puis l'assembleur II+/IIe :
toutes les abscisses avec largeur 1/65535, toutes les largeurs aux deux
bords, toutes les paires y/hauteur, paramètres inchangés sur rejet,
registres de travail écrasés, gardes et 1 024 positions de pile. Les tests
réels vérifient pixels, 320 lignes colorées, 48 étapes étendues, deux
backends GFX, deux pages/banques, trous et restauration DOS.
Validation complémentaire : 50 clients minimaux, intégration HGR,
`make all`, exemples DHGR (1 000 images NTSC/PAL), ROBOTSTATION IIe/IIc,
WOZ, relevé complet de 356 cas et gate. DHGR.dsk, ROBOTSTATION.po et leurs
WOZ sont reconstruits.

## Série du 5 novembre 2026 : préparation native des effacements DHGR

`dhgr_clear_rows.s` remplace l'enveloppe C. La couleur reste dans X pendant
la vérification des deux arguments ; la hauteur clippée remplace le slot
de hauteur consommé. Après préparation du motif, A/X reçoivent y/hauteur,
la pile est libérée et l'entrée saute directement vers le noyau existant.
Les appels vides ou hors écran ne préparent pas le motif. Aucun noyau de
banque mémoire ou d'interruption n'est modifié.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Une ligne | 1 090 → 929 | 1 660 → 1 566 |
| 16 lignes | 11 725 → 11 549 | 1 661 → 1 567 |
| 192 lignes | 136 555 → 136 214 | 1 661 → 1 567 |
| Deux dernières lignes, hauteur 255 | 1 822 → 1 644 | 1 661 → 1 567 |
| Dernière ligne, couleur 255 | 1 113 → 934 | 1 707 → 1 613 |
| Hauteur nulle | 145 → 103 | 1 707 → 1 613 |
| Ordonnée hors écran | 136 → 114 | 1 707 → 1 613 |

Économie de 94 octets par client isolé ; pile C 5 → 2 (rejets 3 → 2),
pile matérielle 11 → 9 (rejets 6 → 5), sans RAM/page zéro supplémentaire.
Les neuf cas concernés sont plus rapides, les 338 autres cas restent
identiques ; cinq cas sont nouveaux. Le noyau reste à 688 cycles par ligne.

La fixture de 67 072 appels passe sur le C de référence puis sur les
versions natives II+/IIe : toutes les paires y/hauteur, toutes les couleurs,
arguments clippés, rejets, registres de travail écrasés, gardes et 1 024
positions de pile. L'oracle réel vérifie les seize couleurs sur les deux
pages et banques, les trous mémoire, l'affichage et le masque IRQ ; le
test VIA vérifie le service périodique réel avec gardes et pixels.
Validation complémentaire : 50 clients minimaux, intégration HGR, `make all`,
exemples DHGR (1 000 images NTSC/PAL), ROBOTSTATION IIe/IIc, WOZ, relevé
complet de 347 cas et gate. Les disques et leurs 18 WOZ restent identiques.

## Série du 5 novembre 2026 : validation native des cartes de tuiles

`hgr_tilemap_init` valide le nombre de tuiles sur 16 bits et les trois
pointeurs, puis parcourt les 960 indices en trois blocs de 256 et une fin
de 192 octets. A conserve `count-1` pendant les comparaisons indirectes ;
les boucles ne rechargent donc pas la limite à chaque case. L'incrément de
l'octet haut du pointeur conserve les cartes non alignées. Le cas de 256
tuiles saute le parcours, tous les indices octet étant alors valides.
Les six octets du contexte ne sont écrits qu'après validation complète.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Parcours complet, une tuile | 129 734 → 13 145 | 871 → 744 |
| Parcours complet, 255 tuiles | 129 734 → 13 169 | 877 → 750 |
| 256 tuiles, sans parcours | 478 → 317 | 877 → 750 |
| Premier indice invalide | 410 → 251 | 877 → 750 |
| Dernier indice invalide | 129 493 → 13 079 | 877 → 750 |
| Nombre nul | 281 → 159 | 871 → 744 |
| Contexte nul | 231 → 182 | 870 → 743 |
| Fond et deux dessins masqués | 6 692 → 6 701 | 3 122 → 3 021 |

Le parcours complet gagne 89,9 %, les clients isolés 127 octets, les pics
de pile C passent de 10 à 6 et matériels de 7 à 5. RAM/page zéro inchangées.
La scène combinée gagne 101 octets et coûte neuf cycles de plus (+0,13 %) ;
sa référence de cycles est conservée. Les dix nouvelles initialisations
mesurées sont toutes plus rapides. Sur les 342 cas du banc, douze changent
et 330 restent identiques.

La fixture de 69 120 appels passe d'abord sur le C, puis sur l'assembleur
II+/IIe : les 65 536 nombres de tuiles, chaque position d'indice invalide,
64 octets après la carte exclus du parcours, toutes les valeurs d'indice,
les limites de chaque nombre, les alignements de carte, combinaisons NULL,
écriture transactionnelle, gardes et 1 024 positions de pile. Les tests
réels de restitution passent sur les deux CPU. Validation complémentaire :
49 clients minimaux d'archive, intégration HGR, `make all`, relevé complet
et gate. Les disques livrés restent identiques.

## Série du 5 novembre 2026 : initialisation native des HUD

Les deux initialisations C deviennent des entrées assembleur séparées,
avec une routine commune de bornage horizontal et d'écriture. Les formats
conservent leurs limites de largeur/hauteur, leur pas de 18/8 pixels et
leurs structures de 37/19 octets. L'octet haut de x est contrôlé avant
l'addition de l'étendue, pour éviter un retour sur l'écran par débordement.
Seuls x, y, width et valid sont écrits ; les historiques restent intacts.
Les pointeurs nuls et les champs invalides ne modifient aucun octet d'état.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Initialisation 16×16 à l'origine | 870 → 301 | 985 → 698 |
| Initialisation 16×16 au bord | 878 → 310 | 990 → 703 |
| Pointeur nul 16×16 | 193 → 159 | 981 → 694 |
| Initialisation 8×8 à l'origine | 563 → 290 | 851 → 691 |
| Initialisation 8×8 au bord | 567 → 299 | 856 → 696 |
| Pointeur nul 8×8 | 169 → 159 | 847 → 687 |
| Compteur 16×16, un chiffre modifié | 3 919 → 3 940 | 3 044 → 2 805 |
| Compteur 8×8, un chiffre modifié | 2 283 → 2 282 | 3 417 → 3 283 |
| Jeu compact, phase zéro | 15 315 → 15 277 | 6 650 → 6 584 |

Les clients d'initialisation économisent 287/160 octets, leurs pics de
pile C passent de 10/8 à 5 et matériels de 8/7 à 5, sans RAM/page zéro
supplémentaire. Les clients HUD complets gagnent 239/134 octets, les scènes
16×16 combinées 88, le jeu compact 66. Les 18 initialisations mesurées sont
plus rapides. Le déplacement du code ralentit quelques rendus composés
jusqu'à 0,54 % ; leurs références de cycles antérieures restent inchangées.
73 cas changent dans le relevé de 332 cas, 259 restent identiques ;
18 cas d'initialisation sont nouveaux.

Le test de 268 288 appels passe sur les versions C puis assembleur II+/IIe :
toutes les abscisses 16 bits pour une cellule et la largeur maximale,
ordonnées/largeurs complètes, étendues exactes et dépassées d'un pixel,
pointeurs nuls, historique et gardes, pointeur d'état traversant une page,
2 048 positions de pile. Les tests de rendu des deux HUD passent sur les
deux CPU. Validation complémentaire : 48 clients minimaux d'archive,
intégration HGR, `make all`, exemple HGR II+/IIe, WOZ, relevé complet et gate.
HGR.dsk et son WOZ sont reconstruits.

## Série du 5 novembre 2026 : réservation directe des tampons décimaux

Les entrées signées et non signées sauvegardent déjà la valeur avant de
réserver leur tampon. La soustraction directe de six ou sept octets évite
la sauvegarde inutile des registres par `decsp6/7`. Le retour passe par
`addysp` avec la taille dans Y, sans tirer les enveloppes `incsp6/7`.

Chaque client isolé perd huit octets supplémentaires ; les appels chauds
mesurés gagnent 11 à 31 cycles, sans changement de RAM ni de pics de pile.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| 65535, grande police | 11 350 → 11 319 | 2 394 → 2 386 |
| 65535, petite police | 6 242 → 6 226 | 1 927 → 1 919 |
| −32768 | 12 348 → 12 325 | 2 421 → 2 413 |
| −12345 | 11 873 → 11 844 | 2 425 → 2 417 |
| Premier appel non signé, grande police | 26 664 → 26 697 | 2 373 → 2 365 |

Le dernier cas coûte 33 cycles de plus (+0,12 %) dans ce placement ; sa
référence de cycles reste inchangée. Les 24 autres cas concernés sont
plus rapides, les 289 autres cas du banc restent identiques.

Validation : toutes les valeurs signées/non signées, 512 positions de
pile non signées et 1 024 signées, rendu réel sur II+/IIe, intégration HGR,
46 clients minimaux, `make all`, relevé complet et gate. Les disques livrés
restent identiques.

## Série du 5 novembre 2026 : entrée native des champs numériques HGR

`hgr_num_field.s` remplace la préparation C du champ effacé puis aligné
à droite. La largeur et la longueur remplacent les deux octets de valeur
consommée, au-dessus du tampon local de six octets. Elles survivent ainsi
aux registres de travail écrasés par l'effacement. La conversion appelle
le noyau décimal directement ; le pointeur du tampon reste dans ses
paramètres pendant l'effacement. Les arguments de chaque appel graphique
sont préparés sur la pile C, puis les cinq arguments initiaux et le tampon
sont libérés ensemble. Aucun tampon global ou octet de RAM supplémentaire.

Les origines invalides et largeurs nulles sont rejetées avant allocation.
Le bornage à 14 cellules, la largeur effacée `18*width-2`, l'alignement
16 bits et le débordement historique d'un nombre trop long sont conservés.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Champ de 14 cellules, 42 | 13 022 → 12 654 | 3 106 → 2 949 |
| Débordement d'une cellule | 13 660 → 13 439 | 3 100 → 2 943 |
| Champ clippé | 3 639 → 3 276 | 3 114 → 2 957 |
| Zéro | 4 998 → 4 721 | 3 094 → 2 937 |
| Largeur 255, bornée à 14 | 19 574 → 19 201 | 3 098 → 2 941 |
| Dernier pixel, dernière ligne | 2 307 → 1 920 | 3 110 → 2 953 |
| Largeur nulle | 183 → 125 | 3 102 → 2 945 |
| Abscisse rejetée | 210 → 146 | 3 106 → 2 949 |
| Ordonnée rejetée | 220 → 169 | 3 102 → 2 945 |
| Premier champ | 29 022 → 28 584 | 3 074 → 2 917 |
| HUD chaud | 29 029 → 28 372 | 3 458 → 3 314 |

Économie de 157 octets dans les clients isolés, 144 dans les HUD combinés,
79 dans les scènes combinées. Pile C 17 → 15 (rejets 13 → 5), sans changement
de RAM/page zéro. Les cas clippés mesurés passent de 10 à 8 octets matériels,
les rejets de 6 à 5 ; les autres pics matériels restent identiques.

Le nouveau test compare 131 584 appels : toutes les valeurs et abscisses,
les 256 largeurs et ordonnées, chaîne/NUL, rectangle effacé puis texte et
alignement sans retour sur l'écran après débordement. Le récepteur d'effacement
écrase ptr1..ptr4 et tmp1..tmp4 pour vérifier la durée de vie des métadonnées.
512 positions de pile contrôlent les réservations/retours et les gardes,
pour un champ valide et un rejet. La fixture complète passe sur le C de
référence puis sur l'assembleur II+/IIe. L'oracle de 1 144 scènes passe
sur II+/IIe avec les tables normales/regroupées.

Validation : tests d'entrée/rendu, intégration HGR, 46 clients minimaux
d'archive, `make all`, SNAKE (cadence et sauvegarde incluses), WOZ, relevé
complet et gate. Les 16 cas concernés s'améliorent, 298 restent identiques ;
sept cas sont nouveaux. SNAKE.dsk et son WOZ sont reconstruits.

## Série du 5 novembre 2026 : préparation native de l'affichage hexadécimal HGR

`hgr_num_hex.s` remplace l'enveloppe C de `hgr_putx`. Une seule réservation
forme la pile `[pointeur du tampon][y/x][tampon de cinq octets]`. Le
convertisseur retire son pointeur de deux octets, le texte consomme les
trois coordonnées, puis l'entrée libère le tampon. L'octet fort de la valeur
reste dans X pendant toute la préparation ; l'octet faible utilise tmp3.
Le convertisseur conserve ptr1 au début du tampon, réutilisé pour le texte.
Le noyau de conversion est inchangé ; son commentaire précise ce contrat.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Zéro | 2 781 → 2 647 | 2 416 → 2 378 |
| F | 2 678 → 2 544 | 2 420 → 2 382 |
| FF | 4 762 → 4 618 | 2 420 → 2 382 |
| FFF | 6 677 → 6 527 | 2 422 → 2 384 |
| FFFF | 8 826 → 8 682 | 2 420 → 2 382 |
| Chaîne clippée | 2 954 → 2 819 | 2 430 → 2 392 |
| Origine rejetée | 716 → 582 | 2 418 → 2 380 |
| Premier appel | 24 147 → 24 013 | 2 399 → 2 361 |

Économie de 38 octets dans les clients isolés ; pile C 13 → 10. RAM,
page zéro et pics de pile matérielle restent inchangés. Le rendu et la
conversion hexadécimale sont identiques.

Le nouveau test passe sur l'ancien C puis sur l'entrée finale II+/IIe :
65 536 chaînes, NULs/queues et coordonnées ; 1 024 placements de pile pour
0/F/1000/FFFF, avec gardes et nettoyage des arguments. L'oracle graphique
compare 96 scènes par CPU aux frontières de longueur, avec clipping/rejet,
deux pages, palette et trous.

Validation : entrée et rendu II+/IIe, intégration HGR, 45 clients minimaux
d'archive (le client hexadécimal exclut tous les afficheurs décimaux),
`make all`, relevé complet de 307 cas et gate. Huit cas s'améliorent,
299 sont identiques ; cinq cas sont nouveaux. Aucun disque livré ne change.

## Série du 5 novembre 2026 : entrée native des nombres HGR signés

`hgr_num_signed.s` remplace la préparation C de `hgr_puti`. Le tampon
reste local, avec sept octets pour le signe éventuel, cinq chiffres et
le NUL. Les trois octets de coordonnées sont déplacés au nouveau sommet
de pile et seront consommés par l'afficheur. Le pointeur de texte existant
conserve le début du tampon ; seul le pointeur du convertisseur avance
après le signe moins. La négation non signée sur 16 bits traite −32 768.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| −32 768 | 12 469 → 12 348 | 2 487 → 2 421 |
| −12 345 | 11 987 → 11 873 | 2 491 → 2 425 |
| 32 767 | 11 445 → 11 381 | 2 491 → 2 425 |
| Zéro | 2 728 → 2 635 | 2 485 → 2 419 |
| −1 | 3 583 → 3 448 | 2 489 → 2 423 |
| −10 | 5 619 → 5 488 | 2 491 → 2 425 |
| Chaîne clippée | 2 367 → 2 218 | 2 499 → 2 433 |
| Origine rejetée | 1 408 → 1 264 | 2 491 → 2 425 |
| Premier appel | 27 793 → 27 687 | 2 467 → 2 401 |

Économie de 66 octets dans les clients isolés ; pile C 15 → 10. RAM,
page zéro et pics de pile matérielle restent identiques. Ni le noyau
décimal ni le rendu ne changent.

Le nouveau test passe avant/après et vérifie toutes les 65 536 chaînes
signées, les NULs, les queues non écrites et les coordonnées transmises.
Les valeurs 0/32 767/−32 768/−1 sont aussi appelées à chacune des 256
positions de pile : 1 024 vérifications des passages de page, du nettoyage
des arguments et des gardes appelants. L'ensemble passe sur II+ et IIe.
Le rendu de 272 scènes par CPU conserve les signes, frontières décimales,
clipping, pages, palettes et trous.

Validation : tests d'entrée et de rendu II+/IIe, intégration HGR, 44 clients
minimaux d'archive (le signé n'extrait ni préparation ni afficheurs non
signés), `make all`, relevé complet de 302 cas et gate. Neuf cas changent,
tous en amélioration ; les 293 autres sont identiques. Six cas sont nouveaux.
Aucun disque livré ne change.

## Série du 5 novembre 2026 : entrées natives séparées des axes HGR

`hgr_hline.s` et `hgr_vline.s` remplacent l'objet C commun `hgr_geom.c`.
Le tri et le clipping préparent directement les paramètres existants du
noyau de remplissage. Un client n'utilisant qu'un axe n'extrait plus l'autre.
L'horizontale compare les abscisses sur 16 bits avant de borner la droite
à 279 ; la verticale trie les octets d'ordonnée puis borne le bas à 191.
Le minimum validé garantit une retenue après la soustraction verticale,
réutilisée pour ajouter la dernière ligne inclusive.

| Appel C direct | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Horizontale complète | 984 → 893 | 1 337 → 1 102 |
| Horizontale inversée | 1 175 → 918 | 1 337 → 1 102 |
| Horizontale clippée | 1 181 → 912 | 1 339 → 1 104 |
| Point horizontal | 549 → 479 | 1 341 → 1 106 |
| Horizontale rejetée | 394 → 213 | 1 337 → 1 102 |
| Horizontale à froid | 16 601 → 16 344 | 1 310 → 1 075 |
| Verticale complète | 11 401 → 11 302 | 1 331 → 1 062 |
| Verticale inversée | 11 485 → 11 311 | 1 331 → 1 062 |
| Verticale clippée | 11 492 → 11 312 | 1 331 → 1 062 |
| Point vertical | 525 → 441 | 1 329 → 1 060 |
| Verticale rejetée | 176 → 120 | 1 327 → 1 058 |
| Verticale à froid | 26 887 → 26 713 | 1 307 → 1 038 |

Économies de 235/269 octets dans les clients horizontaux/verticaux isolés.
Les piles C inversées passent de 7/5 à 4/3 ; RAM, page zéro et pics matériels
des rendus ne changent pas. Les rejets descendent à cinq octets matériels.
Tous les appels directs aux axes s'améliorent.

Les clients `hgr_line` gagnent encore 122 octets (77 via GFX), mais le
placement continue d'influencer les temps des noyaux inchangés. La diagonale
avant passe de 21 128 à 20 927 cycles et l'horizontale de 1 339 à 1 083.
**Variations défavorables conservées explicitement :** GFX diagonal
21 194 → 21 316 (+0,58 %), petite diagonale 708 → 709, diagonale inverse
20 784 → 20 835, verticale via `hgr_line` 11 727 → 11 738 et diagonale à
froid 36 492 → 36 513. Les cinq références de cycles ne sont pas relâchées.

Le test d'entrée compare 524 544 appels à un oracle de tri/clipping :
les deux extrémités horizontales parcourent les 65 536 abscisses, avec
ancres 0/279/65 535 dans les deux sens ; les abscisses verticales, toutes
les paires d'ordonnées et toutes les ordonnées horizontales sont couvertes.
Un garde vérifie la pile appelante. Il passe avant/après et sur IIe.
Les 126 premiers appels réels par configuration vérifient pixels, palette,
trous, deux pages, tables et absence d'initialisation sur rejet, avant/après
puis sur II+/IIe avec tables normales/regroupées.

Validation : tests d'entrée et à froid, 464 lignes HGR/GFX sur II+/IIe,
contours, intégration HGR, 43 clients minimaux d'archive, `make all`,
démonstration HGR et WOZ, relevé complet et gate. Parmi 296 cas, 25 changent
et 271 sont identiques ; 13 cas d'axes sont nouveaux. HGR.dsk et son WOZ
sont reconstruits.

## Série du 5 novembre 2026 : entrée native des lignes HGR

`hgr_line.s` valide les deux extrémités, charge les paramètres existants
et appelle le même noyau Bresenham. Les axes réutilisent les arguments
empilés : un déplacement de x1 supprime y0 dans le cas horizontal ; retirer
x1 laisse directement les arguments verticaux. Les appels terminaux gardent
les routines d'axes existantes, donc leurs règles de tri et de palette.
Tout point hors écran est toujours rejeté avant construction des tables.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Petite diagonale | 811 → 708 | 2 127 → 2 011 |
| Diagonale avant | 21 009 → 21 128 | 2 117 → 2 001 |
| Diagonale inverse | 21 005 → 20 784 | 2 117 → 2 001 |
| Diagonale via GFX | 21 465 → 21 194 | 2 517 → 2 432 |
| Horizontale inversée | 1 445 → 1 339 | 2 121 → 2 005 |
| Verticale inversée | 11 618 → 11 727 | 2 125 → 2 009 |
| Point | 820 → 717 | 2 125 → 2 009 |
| Abscisse rejetée | 178 → 159 | 2 123 → 2 007 |
| Ordonnée rejetée | 227 → 129 | 2 123 → 2 007 |
| Diagonale à froid | 36 595 → 36 492 | 2 086 → 1 970 |
| Diagonale à froid, tables regroupées | 38 248 → 38 396 | 2 072 → 1 956 |

**Compromis explicite :** 116 octets économisés dans les clients isolés,
mais +119 cycles sur la diagonale avant (+0,57 %), +109 sur la verticale
(+0,94 %) et +148 sur la diagonale à froid regroupée (+0,39 %). Les autres
cas accélèrent. La pile C passe de 6 à 5 pour les diagonales, de 13 à 7
pour l'horizontale inversée et de 11 à 5 pour la verticale. La pile matérielle
des axes passe de 10 à 8. RAM et page zéro sont inchangées.

Le nouveau test passe d'abord sur le C d'origine, puis sur l'assembleur.
Il balaye séparément les deux domaines d'abscisse 16 bits et les deux
domaines d'ordonnée : 131 584 appels. Des récepteurs vérifient exactement
les arguments de chaque axe/noyau, les rejets, l'état paresseux des tables
et un garde de pile de l'appelant. Il passe sur II+/IIe avec les tables
normales/regroupées. Les quatre mêmes configurations passent l'oracle de
464 lignes HGR/GFX : octants, égalités, sens, bords, palette et deux pages.

Validation : tests d'entrée et de rendu, intégration HGR et 41 clients
minimaux d'archive, `make all`, relevé complet de 283 cas et gate. Onze
cas changent, 272 restent identiques. Les deux anciennes références de
cycles qui seraient relâchées restent à leur valeur antérieure ; les sept
nouveaux cas reçoivent leurs premières références. Aucun disque ne change.

## Série du 5 novembre 2026 : extraction directe des chiffres hexadécimaux

`gfx_hexstr` conserve son compteur de quatre chiffres, mais utilise sa
parité pour extraire le demi-octet supérieur ou inférieur de l'octet courant.
Après les deux premiers chiffres, un seul transfert sélectionne l'octet
faible. Les décalages répétés du mot 16 bits disparaissent. L'ajustement
ASCII laisse la retenue à zéro dans les deux branches, ce qui permet aussi
de supprimer le CLC avant l'addition de `'0'`.

La routine passe de 71 à **68 octets**, sans table, RAM, page zéro ni pile
supplémentaire. Les conventions restent identiques : majuscules, aucun
zéro initial sauf pour zéro lui-même, NUL, longueur dans A et X=0.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Conversion de 0 | 398 → 308 | 658 → 655 |
| Conversion de 16 | 404 → 312 | 660 → 657 |
| Conversion de 256 | 417 → 323 | 660 → 657 |
| Conversion de 4 096 | 430 → 334 | 660 → 657 |
| Conversion de 65 535 | 422 → 326 | 658 → 655 |
| Affichage HGR de 0 | 2 871 → 2 781 | 2 419 → 2 416 |
| Affichage HGR de 65 535 | 8 928 → 8 826 | 2 423 → 2 420 |
| Affichage HGR clippé | 3 049 → 2 954 | 2 433 → 2 430 |

Le test exhaustif existant reçoit une option IIe. Avant/après, les 65 536
valeurs passent sur les deux CPU avec vérification de chaque chiffre,
longueur, NUL et octet de garde, y compris les tampons traversant une page.
La fixture complète, avec ses boucles C et initialisations inchangées,
passe de 138 079 027 à **131 796 307 cycles**, identiques sur II+ et IIe.
Son binaire passe de 705 à 702 octets. Les appels directs gagnent 22–23 %.

Validation : balayages avant/après II+/IIe, intégration HGR et 41 clients
minimaux d'archive, `make all`, relevé complet et gate. Les 12 nouveaux
cas s'améliorent ; les 264 mesures précédentes sont identiques. Aucun
disque livré ne change.

## Série du 5 novembre 2026 : préparation commune des nombres HGR non signés

`hgr_putu` et `hgr_putu8` ont désormais deux entrées assembleur indépendantes
et une préparation décimale commune. La valeur A/X va directement aux
paramètres du convertisseur. Après réservation de six octets sur la pile C,
les trois octets y/x sont déplacés au nouveau sommet ; leurs anciennes
cases appartiennent au tampon de six octets. L'afficheur consomme les trois
arguments, puis l'entrée numérique libère le tampon. Aucun tampon statique,
aucune nouvelle RAM ou page zéro. Les noyaux de conversion et de dessin
restent identiques.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Agrandi, 0 | 2 715 → 2 635 | 2 423 → 2 390 |
| Agrandi, 10 | 4 932 → 4 850 | 2 427 → 2 394 |
| Agrandi, 65 535 | 11 429 → 11 350 | 2 427 → 2 394 |
| Agrandi, clippé | 3 581 → 3 501 | 2 437 → 2 404 |
| Agrandi, origine rejetée | 1 340 → 1 262 | 2 425 → 2 392 |
| 8×8, 0 | 1 522 → 1 437 | 1 956 → 1 923 |
| 8×8, 10 | 2 415 → 2 337 | 1 960 → 1 927 |
| 8×8, 65 535 | 6 318 → 6 242 | 1 960 → 1 927 |
| 8×8, clippé | 4 101 → 4 006 | 1 970 → 1 937 |
| 8×8, origine rejetée | 1 327 → 1 249 | 1 958 → 1 925 |

Les clients isolés économisent 33 octets et leur pile C passe de 14 à
9 octets. Les pics de pile matérielle restent inchangés (10 en rendu,
8 sur l'origine rejetée). Les premiers appels gagnent également du temps.

Le nouveau test appelle les deux fonctions depuis C pour chacun des
65 536 nombres ; un récepteur assembleur vérifie les coordonnées, la
sélection de police et toutes les chaînes/NULs. Un garde local contrôle
la pile de l'appelant. Une deuxième passe déplace la pile sur chacune des
256 positions d'une page pour chaque fonction, vérifie les passages de
page, les octets de garde et le résultat 65 535. Le test de rendu compare
28 scènes : frontières décimales, deux polices/pages, sept phases,
clipping, coordonnées rejetées, palette et trous d'écran. L'ensemble
passe sur II+ et IIe ; le balayage C et le rendu passent aussi avant
l'optimisation.

Validation : intégration HGR, 41 clients minimaux d'archive (dont chaque
police numérique seule et les deux ensemble), `make all`, relevé complet
et gate. Les 16 nouveaux cas numériques s'améliorent ; les 248 autres
mesures sont identiques. Aucun disque livré ne change.

## Série du 5 novembre 2026 : entrées natives du texte HGR agrandi

`hgr_text.s` remplace les entrées C blanche/couleur en conservant un chemin
commun et le même noyau de rendu. L'entrée couleur récupère la chaîne sur
la pile C, puis les deux variantes chargent directement les paramètres.
Les couleurs hors 1..4 gardent le repli blanc. Le résultat du sélecteur est
testé dans A : ses drapeaux au retour ne représentent pas ce booléen.

Le calcul des cellules garde X pour l'accès colonne/phase. x=0..8 donne
quinze cellules, x=256..264 une seule ; entre les deux, les soustractions
bornées opèrent sur un octet. L'auxiliaire `hgr_text16_cells` reste disponible
et testé séparément, mais ces clients ne l'extraient plus de l'archive.
Les constructions paresseuses précèdent toujours le rejet des coordonnées.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| APPLE II blanc, phase 0 | 15 074 → 14 720 | 2 456 → 2 255 |
| APPLE II blanc, phase 3 | 15 307 → 14 990 | 2 460 → 2 259 |
| APPLE II orange, phase 0 | 15 104 → 14 839 | 2 489 → 2 275 |
| Huit espaces | 3 894 → 3 545 | 2 456 → 2 255 |
| Chaîne vide | 627 → 278 | 2 448 → 2 247 |
| Caractère au bord | 2 850 → 2 506 | 2 459 → 2 258 |
| Chaîne clippée | 2 846 → 2 501 | 2 464 → 2 263 |
| Couleur à froid, clippée | 18 242 → 17 948 | 2 459 → 2 245 |
| Abscisse 65 535 | 440 → 208 | 2 455 → 2 254 |
| Ordonnée 177, couleur | 462 → 295 | 2 490 → 2 276 |
| Couleur inconnue, repli blanc | 15 530 → 15 084 | 2 491 → 2 277 |
| HUD chaud | 29 780 → 29 029 | 3 638 → 3 458 |

Les clients isolés économisent 201 octets en blanc, 214 en couleur ;
pile C 10 → 3 et 11 → 5, pile matérielle des rendus 10 → 8. Le repli
blanc passe de 16 à 5 octets de pile C et de 12 à 8 sur la pile matérielle.
La RAM et la page zéro ne changent pas. Les nombres gagnent 175 octets,
les HUD/scènes 180, selon les auxiliaires C encore partagés.

Le nouveau test vérifie chaque entrée sur les 65 536 abscisses et les
256 ordonnées, les 256 valeurs de couleur et 240 appels à froid. Un
récepteur assembleur contrôle chaîne, fonte, ordonnée, nombre de cellules,
colonne/phase et porteurs. La fixture passe d'abord avec le C d'origine,
puis avec l'assembleur sur II+/IIe et tables normales/regroupées.
Le rendu réel couvre 280 scènes par CPU, tous les motifs de ligne/glyphes,
porteurs, phases, parités et pages. Les tests couleurs, nombres signés,
champs numériques et l'intégration avec 38 clients minimaux passent aussi.

Validation : `make all`, SNAKE (y compris cadence II+/IIe/PAL et sauvegarde),
HGR/LIGHT3DBALL, WOZ, relevé complet et gate. Parmi 248 cas HGR/DHGR,
27 s'améliorent et 221 sont strictement identiques. Seules ces 27 références
sont nouvelles/actualisées. SNAKE.dsk et son WOZ sont reconstruits.

## Série du 5 novembre 2026 : entrée native du texte HGR 8×8

`hgr_text8.s` remplace la préparation C des chaînes. Le pointeur passé dans
A/X est conservé dans les paramètres de texte pendant les constructions
paresseuses. Après validation de x≤273 et y≤184, le nombre de cellules
se calcule par `(281−x)>>3`, égal à `((273−x)>>3)+1`. Le poids fort de la
différence ne contient qu'un bit : une rotation et deux décalages du poids
faible suffisent après transfert de ce bit dans la retenue.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| APPLE II, phase 0 | 7 886 → 7 751 | 1 862 → 1 788 |
| APPLE II, phase 3 | 8 672 → 8 498 | 1 866 → 1 792 |
| APPLE II, phase 6 | 8 563 → 8 389 | 1 866 → 1 792 |
| Un caractère au bord | 1 246 → 1 090 | 1 865 → 1 791 |
| Chaîne clippée | 4 291 → 4 127 | 1 870 → 1 796 |
| Même chaîne à froid | 19 637 → 19 497 | 1 843 → 1 769 |
| Chaîne vide | 461 → 287 | 1 864 → 1 790 |
| Abscisse 65 535 | 247 → 195 | 1 861 → 1 787 |
| Ordonnée 185 | 225 → 181 | 1 865 → 1 791 |

Économie de 74 octets chargés dans les clients isolés, pile C 5 → 3,
pile matérielle des appels vides/rejetés 7 → 6. RAM et page zéro inchangées.
Le HUD combiné économise 43 octets, certains auxiliaires C restant partagés.
Les noyaux de glyphes, le traitement des caractères et l'avance de chaîne
restent inchangés. Les tables sont construites même en cas de rejet.

Le nouveau test intercepte l'entrée du noyau avec un récepteur assembleur :
les 65 536 abscisses, 256 ordonnées et 30 premiers appels vérifient le
nombre de cellules, colonne/phase, ordonnée, chaîne, fonte et tables.
Il passe avant/après, sur II+/IIe et avec les tables normales/regroupées.
Les tests graphiques réels comparent 1 344 glyphes, les 256 motifs de ligne,
les bords et les deux pages sur II+ et IIe. L'intégration couvre aussi les
chaînes et nombres dont le tampon est sur la pile C.

Validation : tests d'entrée sur quatre configurations, glyphes II+/IIe,
intégration HGR et 38 clients minimaux, `make all`, tests HGR/LIGHT3DBALL,
cohérence des WOZ, relevé complet de 242 cas HGR/DHGR et gate. Treize
références sont nouvelles/actualisées, toutes en amélioration ; les 229
autres cas sont identiques. HGR.dsk, LIGHT3DBALL.dsk et leurs WOZ sont
reconstruits.

## Série du 5 novembre 2026 : produit hauteur × pas source borné à huit étapes

Le produit hauteur × pas source compte le plus petit facteur. Pour un
facteur inférieur à dix, le résultat démarre avec une copie de l'autre
facteur et le poids faible reste dans A pendant les additions. Sinon,
huit rotations/additions produisent le résultat 16 bits. Chacune des deux
boucles exécute au plus huit étapes. La phase zéro conserve son raccourci.
Le calcul emploie les dimensions d'origine, avant clipping, puis applique
la phase à l'adresse source sur 16 bits.

**Compromis : 39 octets de code supplémentaires** (préparation 151 → 190),
sans RAM, page zéro ou pile supplémentaires. Les petits produits à un
facteur égal à un peuvent coûter quatre cycles de plus dans la fixture.

| Préparation seule, JSR/RTS inclus | Cycles avant → après |
|---|---:|
| Phase 0, pas 2, hauteur 16 | 176 → 176 |
| Phase 1, pas 2, hauteur 1 | 228 → 232 |
| Phase 3, pas 2, hauteur 16 | 563 → 297 |
| Phase 6, pas 3, hauteur 255 | 5 196 → 402 |
| Phase 6, pas 255, hauteur 255 | 6 210 → 530 |
| Phase 3, pas 255, hauteur 1 | 284 → 288 |
| Phase 3, pas 8, hauteur 8 | 411 → 371 |

Dans le banc C, le XOR 7×16 en phase 3 passe de 2 373 à 2 107 cycles ;
le XOR clippé de 962 à 695. La phase zéro reste à 1 986 cycles. Le coût
supplémentaire de 39 octets s'applique à tous les clients de cette famille,
y compris ceux qui ne l'appellent qu'en phase zéro ou avec des rejets.

Le nouveau test appelle le vrai `hgr_xs_setup` sans dessiner : il vérifie
l'adresse calculée même après débordement 16 bits, le pas original et les
dimensions clippées, ainsi que tmp4 et le mode préservés. Les 255 pas ×
255 hauteurs × sept phases × deux placements font 910 350 combinaisons,
passées sur II+ et IIe. La suite normale prend 18 hauteurs (64 260 cas) ;
`make test-preshift-setup-full` exécute le balayage complet. Les points
d'arrêt isolent les boucles et les appels mesurés du démarrage du simulateur.
Le balayage complet, boucles de vérification incluses, passe de 2 425 809 996
à 454 703 568 cycles (−81,3 %). Le relevé final est identique sur les deux CPU.

Validation : balayage exhaustif avant/après et sur IIe, oracle de dessin
avec tables normales/regroupées, variante regroupée IIe, intégration HGR
et 38 clients minimaux d'archive, `make all`, relevé complet de 236 cas
HGR/DHGR et gate. Dix-neuf références sont nouvelles/actualisées ; les
217 autres cas sont identiques. Aucun disque livré ne change.

## Série du 5 novembre 2026 : entrées natives des sprites précalculés

Les entrées `hgr_sprite` et `hgr_sprite_xor` deviennent deux membres
assembleur indépendants. Un troisième membre partage la validation du
descripteur et copie les coordonnées depuis leurs positions respectives
sur la pile C. Les descripteurs vides sont rejetés avant cette copie.
Chaque entrée construit d'abord les lignes ; un rejet ne construit
ni colonnes ni phases, comme auparavant.

La préparation des lignes reste hors du sous-programme partagé pour éviter
un niveau de pile supplémentaire. Les entrées appellent directement la
sélection de phase puis le noyau XOR, sans traverser le relais interne
`hgr_xs_run`. Ce relais reste disponible et inchangé pour ses utilisateurs.
Le mode général reste dans tmp4, désormais explicitement préservé par
`hgr_xs_setup` et ses générateurs de tables.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| XOR dédié 7×16, phase 0 | 2 080 → 1 986 | 1 712 → 1 531 |
| XOR dédié 7×16, phase 3 | 2 468 → 2 373 | 1 712 → 1 531 |
| XOR dédié 7×16, phase 6 | 2 546 → 2 448 | 1 712 → 1 531 |
| XOR dédié clippé | 1 070 → 962 | 1 712 → 1 531 |
| SET général, phase 3 | 2 483 → 2 424 | 1 730 → 1 572 |
| CLEAR général, phase 3 | 2 550 → 2 491 | 1 728 → 1 570 |
| XOR général, phase 3 | 2 471 → 2 416 | 1 730 → 1 572 |
| Les deux entrées | 4 978 → 4 802 | 1 797 → 1 671 |
| XOR dédié vide | 208 → 169 | 1 712 → 1 531 |
| Général vide | 207 → 204 | 1 730 → 1 572 |

Le pointeur du descripteur est copié dans ptr2 en même temps que dans
le bloc de paramètres, ce qui évite une copie ultérieure dans la validation.
Les clients économisent 181/158 octets pour XOR/général seuls, 126 pour les
deux ensemble. Pile C 5 → 3 / 6 → 5, pile matérielle
XOR 10 → 8 ; RAM et page zéro inchangées.

Le test utilise maintenant des points d'arrêt plutôt que des délais/clavier.
Il compare 1 304 images jumelées (entrée générale et XOR dédié sur des pages
opposées), tous les pas source et hauteurs sur un octet, phases, modes,
clipping et mémoire vidéo complète. Les cas limites croisent tous les
modes et les deux pages ; les balayages de dimensions alternent les modes.
Les 160 appels froids vérifient aussi les tables attendues, présentes ou
absentes selon la validité des arguments. Les 38 clients minimaux de
l'archive vérifient notamment l'exclusion de l'autre entrée publique.

Validation : oracle avant/après, II+/IIe avec tables normales/regroupées,
intégration HGR, `make all`, relevé complet de 232 cas HGR/DHGR et gate.
Quinze références sont nouvelles/actualisées ; les 217 autres mesures
sont identiques au relevé avant modification. Aucun disque livré ne change.

## Série du 5 novembre 2026 : interface native des bitmaps HGR

`hgr_sprites.s` remplace la préparation C de `hgr_blit`. La largeur source
non nulle donne directement son pas `((largeur-1)>>3)+1`. Le clipping
horizontal soustrait x de 280 sur 16 bits, puis réduit la largeur seulement
si l'espace restant tient dans un octet. Le clipping vertical compare la
hauteur demandée à 192−y. Le mode reste dans tmp4 pendant la construction
paresseuse des tables ; aucune donnée permanente n'est ajoutée.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| SET 16×8, phase 0 | 5 940 → 5 686 | 1 300 → 1 107 |
| CLEAR 16×8, phase 6 | 6 324 → 6 071 | 1 298 → 1 105 |
| XOR 16×8, phase 3 | 5 989 → 5 735 | 1 300 → 1 107 |
| XOR clippé | 1 206 → 930 | 1 300 → 1 107 |
| Un pixel SET | 824 → 583 | 1 296 → 1 103 |
| XOR clippé, dimensions 255 | 859 → 582 | 1 296 → 1 103 |
| Même appel à froid | 16 288 → 16 012 | 1 252 → 1 059 |
| Largeur nulle | 247 → 220 | 1 288 → 1 095 |
| Abscisse 65 535 | 284 → 244 | 1 292 → 1 099 |

Économie de 193 octets chargés et pile C 10 → 7 (8 → 7 pour les rejets),
sans changement de RAM, page zéro ni pile matérielle. Le noyau de dessin
et ses accès à la source ne changent pas.

Le test bitmap passe de 654 à 2 190 cas chauds, en ajoutant les 256 largeurs
sur un octet avec les trois modes, les deux pages et un clipping vertical.
Quarante cas froids vérifient les modes SET/CLEAR/XOR et le repli CLEAR,
les arguments, les refus et les tables lignes/colonnes/masques. La fixture
calcule le balayage de largeur à l'exécution pour tenir dans les 48 Ko.
L'oracle passe avant/après, puis sur II+ et IIe avec tables normales et
regroupées. La suite normale inclut désormais la variante regroupée.

Validation : quatre configurations de bitmaps, intégration HGR et 36
clients minimaux d'archive, `make all`, comparaison complète de 220 cas
HGR/DHGR et gate. Dix-sept mesures de bitmaps sont nouvelles/actualisées ;
les 203 autres restent identiques au relevé avant modification. Les disques
livrés restent identiques : les jeux actuels n'appellent pas cette entrée.

## Série du 5 novembre 2026 : interface native des sprites alignés HGR

`hgr_blit7.s` remplace le wrapper C. Les arguments sont lus directement
sur la pile C ; les dimensions sont bornées par l'espace restant, sans
addition sur huit bits susceptible de déborder. Le pas source garde la
largeur originale. Le mode survit aux générateurs de tables normaux et
regroupés. Les appels vides/hors écran conservent l'initialisation des
tables et l'absence de dessin, comme auparavant.

| Appel C | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| SET, 4 octets × 8 lignes | 1 646 → 1 525 | 1 114 → 1 022 |
| CLEAR, 4 octets × 8 lignes | 1 717 → 1 592 | 1 116 → 1 024 |
| XOR, 4 octets × 8 lignes | 1 653 → 1 523 | 1 118 → 1 026 |
| SET, un octet | 548 → 434 | 1 116 → 1 024 |
| XOR clippé, largeur/hauteur 255 | 578 → 434 | 1 116 → 1 024 |
| Même XOR à froid | 11 503 → 11 359 | 1 072 → 980 |
| Largeur nulle | 239 → 190 | 1 108 → 1 016 |
| Abscisse 65 535 | 288 → 225 | 1 112 → 1 020 |

Le client isolé économise 92 octets chargés et deux octets de pile C
(pic 9 → 7), sans changement de RAM, page zéro ou pile matérielle.
Le noyau de copie des pixels reste inchangé.

Le nouveau test compare 2 164 cas chauds et 18 cas froids à un oracle
Python : toutes les abscisses visibles, toutes les valeurs des dimensions
sur un octet, modes SET/CLEAR/XOR et repli CLEAR, pas source, deux pages,
bits de palette et trous vidéo. Il passe avec l'ancien wrapper, puis avec
le nouveau sur II+ et IIe, avec tables normales et regroupées. Les modes
et les deux pages sont croisés avec les cas limites ; le balayage général
alterne les modes. La suite normale ajoute les deux variantes de tables.

Validation : tests dédiés sur les quatre configurations, intégration HGR
et 35 clients minimaux d'archive, `make all`, relevé complet de 215 cas
HGR/DHGR puis gate. Huit mesures de sprites sont nouvelles/actualisées ;
les 207 autres cas sont identiques au relevé avant modification. Aucun
disque livré ne change, cette entrée n'est pas appelée par les jeux actuels.

## Série du 5 novembre 2026 : tables x/7 regroupées sans appels par pixel

La variante `HGRC_X7_FOLDED` produit les 256 premières positions dans une
boucle sans appel interne. Un tableau constant de sept masques remplace
le masque temporaire et son décalage. Les 24 dernières positions recopient
les positions 4..27, en ajoutant 36 aux colonnes : 256 = 36×7+4. La retenue
de l'addition reste nulle, garantie par les comparaisons de boucle.

Le générateur passe de **77 à 74 octets**, constantes incluses, et de
**15 084 à 10 327–10 350 cycles** selon l'alignement des tables (environ
−31 %). Il ne touche plus tmp2 et n'ajoute ni RAM ni page zéro. Les alias
colonnes/masques/phases, la garde chaude et les 841 octets de BSS restent
identiques. Les générateurs indépendants sont inchangés.

| Appel C à froid, variante regroupée | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Diagonale | 43 009 → 38 248 | 2 075 → 2 072 |
| HUD | 51 853 → 47 085 | 3 538 → 3 535 |
| Scène sprites | 32 491 → 27 734 | 6 193 → 6 190 |

Le pic de pile matérielle de la diagonale baisse de 8 à 6 octets ; les
autres pics restent inchangés. Pour trois tables, l'option économise
maintenant 56 octets de code et du temps face aux générateurs indépendants.
Pour deux tables, elle réserve encore une table inutile et la diagonale
reste 1 653 cycles plus lente : l'option conserve son caractère explicite.

Validation : les 280 valeurs de chaque table aux 256 alignements, gardes
mémoire et absence de reconstruction chaude, alignements frontières IIe ;
rectangles/cellules/recoloration à froid sur II+ et IIe avec l'option ;
options booléennes ; `make all` et gate complet HGR/DHGR. Aucun disque
ne change, les programmes livrés utilisent les générateurs indépendants.

## Série du 5 novembre 2026 : division 16/8 en deux étapes

Pour les quotients longs, le diviseur traite d'abord l'octet haut, puis
réutilise la boucle courte pour l'octet bas. La première étape ne peut
produire de neuvième bit de reste : chaque préfixe du numérateur sur un
octet est au plus 255. La branche de détection de débordement y disparaît.

Le noyau passe de 52 à 51 octets. Dans la fixture dont les branches restent
dans une page, **chaque quotient sur 16 bits gagne 92 cycles**, contre
**deux cycles supplémentaires pour chaque quotient court**. Pas de mémoire,
page zéro ni pile supplémentaires ; Y reste préservé.

| Division | Cycles avant → après, JSR/RTS compris |
|---|---:|
| 0 / 1 | 187 → 189 |
| 255 / 1 | 243 → 245 |
| 255 / 2 | 236 → 238 |
| 256 / 1 | 434 → 342 |
| 65 535 / 1 | 539 → 447 |
| 65 535 / 128 | 490 → 398 |
| 65 535 / 255 | 441 → 349 |
| 65 535 / 0 | 507 → 415 |

Les 16 777 216 couples numérateur/diviseur sont vérifiés contre Python,
avec conservation de Y. Le diviseur nul conserve le résultat existant :
quotient $FFFF et octet bas du numérateur comme reste. Le balayage complet,
boucles et sorties incluses, passe de 6 547 795 104 à 5 789 740 192 cycles
(−11,6 %). La suite normale utilise 16 diviseurs représentatifs sur tous
les numérateurs ; `make test-math-division-full` couvre les 256 diviseurs.
Les 765 frontières de sélection du chemin restent vérifiées par le test
mathématique existant.

Validation : comparaison exhaustive avant/après, test mathématique général,
suite de division normale et complète, `make all`. Aucun disque livré ne
change : les jeux actuels n'appellent pas cette entrée de la bibliothèque.

## Série du 5 novembre 2026 : wrapper natif de recoloration HGR

`hgr_colorize.s` charge les arguments C directement, garde la couleur
pendant les constructions paresseuses et calcule les colonnes gauche/droite
sans division. Le bord droit reste sur 16 bits jusqu'au clipping à 279.
Les dimensions et couleurs refusées gardent la même absence de dessin et
préservent les paramètres de couleur ; les tables sont toujours construites
avant le rejet. Le noyau de recoloration lui-même ne change pas.

| Cas | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Rectangle 140×16, x=7 | 8 946 → 8 612 | 1 160 → 980 |
| Rectangle 140×16, x=0 | 8 896 → 8 558 | 1 156 → 976 |
| Un octet sur une ligne | 788 → 450 | 1 158 → 978 |
| Rectangle clippé | 1 167 → 797 | 1 156 → 976 |
| Même rectangle à froid | 12 088 → 11 721 | 1 123 → 943 |
| Couleur refusée | 310 → 269 | 1 160 → 980 |
| Rectangle vide | 226 → 188 | 1 160 → 980 |

Cycles NMOS, arguments/appels C compris ; tailles des clients isolés en
octets. Économie de 180 octets de code, pile C 10 → 5, pile matérielle
7 → 6 ; autres RAM et page zéro inchangées. Le relevé complet HGR/DHGR
ne montre aucune hausse supérieure à 1 % ni augmentation de mémoire/pile.
Sept références nouvelles/modifiées sont enregistrées, 201 restent intactes.

Les tests à froid couvrent maintenant la recoloration et les deux variantes
de construction des tables, ainsi que les refus sans modification des
couleurs. Ils ont détecté un mauvais test des flags après le retour C du
sélecteur de couleur dans le premier essai ; la version finale teste sa
valeur de retour. Les 294 rectangles et 98 textes teintés/blancs passent
sur II+ et IIe, ainsi que les 35 clients minimaux de l'archive.

Validation : `make all`, tests de couleur II+/IIe, tests à froid normaux
et regroupés sur les deux cibles, contrôle d'archive, gate complet
`--dhgr --check`, `make test-snake test-woz`. SNAKE.dsk et son WOZ sont
reconstruits.

## Série du 5 novembre 2026 : tables x/7 par groupes de sept

Les générateurs indépendants de colonnes, masques et phases parcourent
40 groupes de sept pixels. Le pointeur est avancé une fois par groupe,
avec propagation de la retenue ; X garde la colonne ou le nombre de
groupes, Y parcourt les sept positions. Aucun temporaire de plus n'est
alloué ; ces entrées n'écrasent plus tmp1/tmp2/tmp3.

| Table | Code avant → après | Cycles froids avant → après |
|---|---:|---:|
| Colonnes x/7 | 59 → 44 octets | 7 029 → 4 040..4 044 (−42,5 %) |
| Masques 1<<(x%7) | 67 → 44 octets | 8 434 → 4 520..4 524 (−46,4 %) |
| Phases x%7 | 58 → 42 octets | 6 749 → 4 440..4 444 (−34,2 %) |

Mesure NMOS avec JSR/RTS. Les appels chauds gardent la même garde et le
même coût (18 cycles). Les trois générateurs économisent 54 octets de
code. RAM, tables, page zéro et pics de piles inchangés. En usage C à froid,
le rectangle en pixels passe de 23 104 à 16 199 cycles, le HUD de 59 180
à 49 924, la scène sprites de 39 907 à 30 375. Les petits écarts aux sommes
des noyaux viennent du placement du code et des tables.

Le nouveau test vérifie les 280 octets de chaque table à chacun des 256
alignements, les gardes avant/après BSS et l'absence de reconstruction à
chaud (un octet volontairement modifié reste intact). Sept alignements
aux frontières sont aussi exécutés sur IIe. La variante regroupée reste
strictement inchangée : 77 octets, 15 084 cycles. Elle économise encore du
code, mais les générateurs indépendants sont désormais plus rapides même
pour trois tables ; le tableau des options décrit ce nouveau compromis.

La comparaison complète HGR/DHGR ne relève aucune hausse supérieure à 1 %
ni augmentation de mémoire/pile. 112 cas nouveaux/modifiés actualisent la
référence ; 92 cas non touchés conservent leurs valeurs.

Validation : `make all`, `make test-hgr` (incluant les alignements et les
options), gate complet `--dhgr --check`, `make test-hgr-example test-frame
test-light3dball test-snake test-woz`. HGR.dsk, LIGHT3DBALL.dsk, SNAKE.dsk
et leurs WOZ sont reconstruits.

## Série du 5 novembre 2026 : wrappers natifs de rectangles HGR

Les entrées C des rectangles en octets, rectangles en pixels et cellules
préparent maintenant directement les blocs de paramètres existants.
Le clipping compare les dimensions à la place disponible, sans calcul
16 bits pour les axes bornés sur un octet. Le rectangle en pixels conserve
un bord droit sur 16 bits, borné à 279. Les tables sont toujours construites
avant le rejet d'un appel vide/hors écran, comme auparavant.

| Appel chaud | Cycles avant → après | Binaire avant → après |
|---|---:|---:|
| Rectangle en octets 40×16 | 7 178 → 7 097 | 879 → 801 |
| Un octet | 406 → 309 | 877 → 799 |
| Rectangle en octets clippé | 514 → 375 | 879 → 801 |
| Rectangle en octets vide | 171 → 172 | 871 → 793 |
| Rectangle en pixels 140×16 | 5 219 → 4 845 | 1 368 → 1 142 |
| Rectangle dans un seul octet | 1 692 → 1 319 | 1 366 → 1 140 |
| Rectangle en pixels clippé | 1 041 → 665 | 1 364 → 1 138 |
| Rectangle en pixels vide | 403 → 191 | 1 356 → 1 130 |
| Cellule 6×6 | 748 → 708 | 1 100 → 1 075 |
| Cellule hors écran | 238 → 192 | 1 102 → 1 077 |

Cycles NMOS, arguments/appels C compris ; tailles des clients isolés en
octets, runtime compris. RAM et page zéro allouées inchangées. Les pics
de pile C passent de 5/13/3 à 4/4/2 octets (octets/pixels/cellules), et
le pic matériel du rectangle en pixels de 9 à 6 ; les autres restent à 6.
Le nettoyage des arguments après le noyau évite un octet de pile matérielle
supplémentaire. L'appel vide en octets coûte un cycle de plus ; aucun
cas du relevé complet ne régresse de plus de 1 %.

Le nouveau test à froid vérifie les arguments après construction des tables,
les coordonnées non nulles et à 9/16 bits, les appels valides/vides/refusés,
les deux pages et leurs trous mémoire sur II+ et IIe. Les tests existants
comparent 2 204 rectangles en octets, 752 rectangles en pixels et toutes
les cellules à leurs modèles. Les 34 clients minimaux contrôlent aussi la
séparation des trois wrappers et de leurs noyaux. 28 références de mesure
nouvelles/modifiées sont enregistrées ; les 172 autres sont conservées.

Validation : `make all`, `make test-hgr`, rectangles en octets/pixels
également sur IIe, test à froid sur les deux cibles, 34 contrôles d'archive,
gate complet `--dhgr --check`, `make test-hgr-example test-frame
test-light3dball test-snake test-woz`. LIGHT3DBALL.dsk, SNAKE.dsk et leurs
WOZ sont reconstruits.

## Série du 5 novembre 2026 : sélection de page et état LORES séparé

Le gestionnaire C devient `hgr_set_draw_page.s` : normalisation de
l'argument, construction HGR à la première utilisation et déplacement
synchrone des tables gardent le même comportement. L'état LORES occupe
un objet indépendant ; un client LORES sans sélection explicite de page
n'importe plus les tables HGR ni le gestionnaire.

| Cas | Cycles avant → après | Binaire avant → après | RAM avant → après |
|---|---:|---:|---:|
| Page 2 à froid | 9 420 → 9 245 | 938 → 747 | 735 → 735 |
| Page 1 à froid | 7 145 → 6 978 | 938 → 747 | 735 → 735 |
| Page 2 déjà sélectionnée | 246 → 79 | 948 → 757 | 735 → 735 |
| Aller-retour page 2/page 1 | 5 018 → 4 666 | 953 → 762 | 735 → 735 |
| Même aller-retour, LORES prêt | 8 904 → 5 615 | 1 086 → 924 | 735 → 735 |
| Effacement LORES page par défaut | 5 442 → 5 442 | 1 046 → 626 | 735 → 347 |
| Écriture LORES chaude | 203 → 204 | 1 163 → 743 | 735 → 347 |
| Lecture LORES chaude | 148 → 148 | 1 097 → 706 | 735 → 347 |

Tailles en octets des clients isolés, runtime compris ; cycles NMOS avec
arguments et appels C. Le gestionnaire ne consomme plus de pile C
(4/5 octets auparavant). Page zéro et pic de pile matérielle inchangés.
Les déplacements de code expliquent le cycle ajouté au point LORES ;
aucun cas de la comparaison complète HGR/DHGR ne régresse de plus de 1 %.
66 cas nouveaux/modifiés remplacent leurs références, 126 restent intacts.

Le contrôle des pages vérifie maintenant les 256 arguments avec LORES
froid puis prêt sur II+ et IIe : tables basse/haute HGR et LORES,
normalisation, appels sans changement de page et maintien de PAGE2 à
l'affichage. Les 31 clients minimaux contrôlent notamment l'absence des
tables HGR et du gestionnaire dans les clients LORES indépendants.

Validation : `make all`, `make test-hgr`, gate complet `--dhgr --check`,
`make test-hgr-example test-frame test-light3dball test-woz`. Les disques
HGR et LIGHT3DBALL et leurs WOZ sont reconstruits.

## Série du 5 novembre 2026 : constantes par décalages

Les constantes 0, 1 et les puissances de deux jusqu'à 128 utilisent des
noyaux sans tables. Les petits facteurs décalent à gauche, ×16 assemble
les nibbles, ×32/64/128 décalent à droite une valeur placée un octet plus
haut. Pour ces trois grands facteurs signés, le signe est propagé pendant
le décalage : la correction finale disparaît.

| Facteur | Code non signé avant → après | Code signé avant → après | Cycles non signés avant → après |
|---|---:|---:|---:|
| 0 | 44 → 8 | 55 → 8 | 76 → 23 |
| 1 | 44 → 12 | 55 → 23 | 80 → 29 |
| 2 | 44 → 15 | 55 → 26 | 80 → 35 |
| 4 | 44 → 21 | 55 → 32 | 80 → 50 |
| 8 | 44 → 27 | 55 → 38 | 80 → 65 |
| 16 | 44 → 34 | 55 → 45 | 80 → 71 |
| 32 | 44 → 27 | 55 → 33 | 80 → 65 |
| 64 | 44 → 22 | 55 → 26 | 80 → 53 |
| 128 | 44 → 17 | 55 → 19 | 80 → 41 |

Octets de macro ; cycles NMOS pour x=$FFFF, JSR/RTS compris. Le minimum
théorique de l'ancien noyau non signé est 72 cycles avec l'appel : chaque
spécialisation gagne donc aussi hors de cet exemple. Les constantes
générales restent inchangées. Aucune allocation de RAM/page zéro ni pile
supplémentaire. Le test exhaustif couvre maintenant 1 572 864 produits,
dont tous les entiers 16 bits pour chaque chemin spécialisé en signé et
non signé, avec tables volontairement remplies de $A5, conservation de Y
et des portées d'étiquettes locales du code appelant.

La catapulte conserve exactement les mêmes états sur les quatre scénarios.
Sur les 404 ticks avec contacts, moyenne 20 925 → 20 889 cycles, maximum
34 261 → 34 213 ; sur les 1 842 ticks de vol sans contacts, moyenne
5 895 → 5 874. Ces petits gains incluent les effets du déplacement du code.

Validation : les deux tests mathématiques, `make all`,
`make test-verlet-contact test-catapult-example`, mesures complètes des
scénarios de catapulte. Aucun disque livré ne change dans cette série.

## Série du 5 novembre 2026 : produits constants et accumulateur

`MUL_K16` calcule la moitié haute du produit d'abord, comme le noyau
16×8 général. La moitié haute du second produit est alors directement
ajoutée au résultat intermédiaire. Une sauvegarde/relecture temporaire
et une remise à un redondante de la retenue disparaissent. `MUL_KS16`
bénéficie du même changement ; sa correction signée reste identique.

| Noyau | Octets avant → après | Cycles avant → après |
|---|---:|---:|
| Macro non signée | 49 → 44 | 84/88 → 76/80 pour x=$FFFF, appel compris |
| Macro signée | 60 → 55 | −8 par produit |
| Accumulateur puis /64 | 28 → 25 avec le décalage partagé | 63 → 60, appel compris |

Le décalage de l'accumulateur enchaîne directement sur le décalage commun.
Le test des références conditionnelles couvre les deux entrées seules,
ensemble et inutilisées. Table, page zéro allouée et piles inchangées ;
l'accumulateur est conservé.

`test_math_products.py` vérifie les 65 536 entrées pour huit constantes
(0, 1, 2, 64, 73, 128, 183, 255), en signé et non signé : 1 048 576
produits comparés à Python, avec conservation de Y. Les branches des
macros sont maintenues dans une page pour la mesure. Chaque balayage
d'une constante gagne exactement 1 048 576 cycles, soit huit par produit.
Les tests mathématiques existants vérifient aussi les deux placements
des tables, les sommes et les produits généraux/signés.

Validation : `make all`, les deux tests mathématiques, `test_verlet.py`,
`make test-verlet-contact test-halfpipe-example test-catapult-example
test-rope-example test-dirtbike test-woz`. Les modèles de physique et
les cadences passent ; DIRTBIKE.dsk et son WOZ sont reconstruits.

## Série du 5 novembre 2026 : tables HGR et séparation des pages

La génération des 192 adresses devient une boucle native sans pile C.
Les tables mutables, la requête `hgr_row` et l'affichage `hgr_show_page`
occupent chacun un objet indépendant. Les clients de dessin seuls
n'importent plus le gestionnaire de pages, sa boucle de bascule ni ses
50 octets d'état LORES. Les clients qui choisissent une page conservent
la mise à jour synchrone des tables HGR et LORES.

Mesures NMOS 6502 avec arguments/appels C, avant/après cette série :

| Cas | Cycles avant → après | Binaire avant → après | RAM avant → après |
|---|---:|---:|---:|
| Construction HGR à froid | 45 783 → 6 921 (−84,9 %) | 1 331 → 596 | 735 → 685 |
| Construction déjà faite | 19 → 19 | 1 334 → 599 | 735 → 685 |
| Adresse de la ligne 191 | 236 → 52 | 1 338 → 625 | 735 → 685 |
| Adresse hors écran | 78 → 23 | 1 338 → 625 | 735 → 685 |
| Affichage page 1 seul | 40 → 29 | 1 334 → 534 | 735 → 300 |
| Affichage page 2 seul | 42 → 30 | 1 339 → 539 | 735 → 300 |
| Sélection page 2 à froid | 48 271 → 9 420 | 1 333 → 938 | 735 → 735 |
| Point HGR chaud | 247 → 247 | 1 592 → 905 | 1 297 → 1 247 |
| Texte 8×8 « APPLE II » | 7 886 → 7 886 | 2 570 → 1 893 | 1 297 → 1 247 |

Tailles en octets, runtime compris ; page zéro inchangée. Le générateur
passe de 9 à 0 octet de pile C, de 10 à 4 octets de pile matérielle au pic.
Le déplacement du code change quelques franchissements de pages : la
ligne horizontale passe de 983 à 1 002 cycles (+1,9 %), la diagonale gfx
de 21 323 à 21 542 (+1,0 %). Aucun budget de trame n'est dépassé. Les
46 mesures non touchées gardent leur référence ; 142 cas nouveaux ou
modifiés sont enregistrés après comparaison complète HGR/DHGR.

Le nouveau test des lignes vérifie les 256 entrées (dont 64 invalides),
les tables basse/haute, les bases froides 0/$20/$40, les pages 0/1/2/255,
la garde d'initialisation et les drapeaux d'affichage 0/1/2/255 sur II+
et IIe. Les 30 clients minimaux de l'archive contrôlent aussi l'absence
du gestionnaire et des tables dans les clients qui n'en ont pas besoin.

Validation : `make all`, `make test-hgr`, mesure/gate complet avec `--dhgr`,
`make test-hgr-example test-frame test-snake test-light3dball test-woz`.
Les disques HGR, SNAKE et LIGHT3DBALL et leurs WOZ sont reconstruits.

## Série du 5 novembre 2026 : points LORES natifs

La lecture et l'écriture d'une cellule passent en assembleur, avec les
mêmes signatures C et les mêmes refus hors écran. L'adresse de ligne et
l'indice X servent directement à l'accès indirect, sans appeler la
fonction d'adresse C. La retenue issue du numéro de ligne conserve la
parité jusqu'à la sélection du nibble.

Mesures `python3 dev/bench/run.py --only lores`, avec arguments et appels
C sur NMOS 6502, par rapport à la série précédente :

| Cas | Cycles avant | Cycles après | Binaire avant → après |
|---|---:|---:|---:|
| Écriture, tables froides | 1 159 | 831 | 1 653 → 1 517 octets |
| Écriture, ligne impaire | 531 | 204 (−61,6 %) | 1 672 → 1 536 octets |
| Écriture, ligne paire | 519 | 187 (−64,0 %) | 1 668 → 1 532 octets |
| Écriture hors écran | 162 | 118 | 1 672 → 1 536 octets |
| Lecture, tables froides | 945 | 776 | 1 541 → 1 482 octets |
| Lecture, ligne impaire | 318 | 149 (−53,1 %) | 1 551 → 1 492 octets |
| Lecture, ligne paire | 312 | 140 (−55,1 %) | 1 547 → 1 488 octets |
| Lecture hors écran | 161 | 74 | 1 551 → 1 492 octets |

RAM et page zéro inchangées ; les tailles concernent les clients isolés,
runtime inclus. Les pics de pile C des appels valides passent de 7 à 2
octets en écriture et de 4 à 1 en lecture. Le pic matériel de l'écriture
passe de 7 à 6 octets ; celui de la lecture reste à 6. L'effacement, les
lignes et les rectangles gardent leurs mesures de la série précédente.

Le contrôle de tous les points vérifie maintenant les premières lectures
et écritures sur les deux pages, y compris des coordonnées non nulles
pendant l'initialisation, et les 256 valeurs de couleur dans chaque nibble.
Les 1 920 cellules, les changements de page, les voisins, les trous
firmware et les refus hors écran restent comparés au modèle sur II+ et
IIe. Le contrôle de l'archive vérifie que lecture et écriture n'importent
ni la fonction d'adresse C ni le noyau de rectangles ni l'autre primitive.

Validation : `make all`, `make test-hgr bench-check`, tests des coordonnées
à froid sur les deux processeurs et 28 programmes de contrôle de l'archive.
Aucun disque livré ne change dans cette série.

## Série du 5 novembre 2026 : lignes et rectangles LORES

Les trois entrées gardent leurs signatures C, leur clipping et leurs
objets indépendants, puis appellent un noyau assembleur commun. Deux
cellules verticales entièrement couvertes deviennent une écriture directe
d'octet. Seuls les nibbles du premier ou du dernier bord doivent être
préservés. La fonction d'adresse d'une cellule est extraite dans son
propre objet pour ne plus être liée par ces clients natifs.

Mesures `python3 dev/bench/run.py --only lores`, NMOS 6502 avec arguments
et appels C, avant/après cette série :

| Cas | Cycles avant | Cycles après | Binaire avant → après |
|---|---:|---:|---:|
| Ligne horizontale, 40 cellules | 5 728 | 1 175 (−79,5 %) | 1 707 → 1 615 octets |
| Ligne horizontale clippée | 729 | 335 | 1 707 → 1 615 octets |
| Ligne verticale, 48 cellules | 19 000 | 2 036 (−89,3 %) | 1 729 → 1 609 octets |
| Verticale, deux bords non appariés | 18 220 | 2 071 | 1 729 → 1 609 octets |
| Verticale clippée à une cellule | 684 | 304 | 1 729 → 1 609 octets |
| Rectangle 20×16, y impair | 51 594 | 3 273 (−93,7 %) | 1 943 → 1 635 octets |
| Rectangle 40×48 | 280 648 | 12 382 (−95,6 %) | 1 939 → 1 631 octets |
| Rectangle clippé en bas à droite | 2 108 | 329 | 1 939 → 1 631 octets |
| Rectangle vide | 175 | 155 | 1 935 → 1 627 octets |

Les tailles sont celles des programmes de mesure, runtime compris. RAM et
page zéro restent identiques. Les pics de pile C passent de 10/9/21 à
3/3/4 octets pour les lignes horizontale/verticale et le rectangle ; le
pic matériel du rectangle passe de 9 à 7 octets. Les coûts des points et
de l'effacement restent inchangés. Le découpage de l'adresse économise
19 octets supplémentaires dans les clients natifs ; ses déplacements de
branches font varier de quelques cycles les coûts du noyau.

Le nouveau `test_lores_spans.py` compare 2 208 cas par cible (II+ NMOS et
IIe 65C02) à un modèle par cellule : chaque ligne et colonne, bornes
inclusives, régions vides/inversées, clipping, tailles de 255, parités des
bords, conservation des autres nibbles, des trous firmware et de l'autre
page. Les contrôles de l'archive vérifient aussi que chaque famille omet
les autres wrappers et la fonction d'adresse inutilisée.

Validation : `make all`, `make test-hgr bench-check`, tests pixels et
spans sur les deux processeurs, 27 programmes de contrôle de l'archive.
Aucun disque livré n'est modifié par cette série.

## Série du 5 novembre 2026 : effacement et adressage LORES

Les boucles C d'effacement et de préparation des adresses sont remplacées
par deux objets assembleur indépendants. L'effacement écrit huit régions
entrelacées de 120 octets ; les 64 octets réservés au firmware restent
intacts. La table des 24 lignes est construite par paires, puis l'adresse
d'une cellule est retournée directement selon l'ABI cc65.

Mesures avec arguments et appels C (`python3 dev/bench/run.py --only lores`),
NMOS 6502, compilation `-Oirs` :

| Cas | Cycles avant | Cycles après | Binaire avant → après |
|---|---:|---:|---:|
| Effacement page 1 | 50 307 | 5 561 (−88,9 %) | 1 653 → 1 441 octets |
| Effacement page 2 | 50 307 | 5 444 (−89,2 %) | 1 658 → 1 446 octets |
| Premier point, tables froides | 11 796 | 1 159 (−90,2 %) | 1 873 → 1 653 octets |
| Point, tables prêtes | 806 | 531 (−34,1 %) | 1 892 → 1 672 octets |
| Ligne horizontale de 40 cellules | 6 001 | 5 728 (−4,5 %) | 1 927 → 1 707 octets |

RAM et page zéro inchangées. Les différences de taille concernent ces
clients isolés, runtime inclus. L'effacement n'utilise plus la pile C
(pic mesuré 14 → 0 octets) ; son pic matériel passe de 7 à 4 octets. Le
point gagne trois octets de pile C et la ligne quatre ; leur pic matériel
passe de 9 à 7. Le placement des branches explique la différence entre
les deux pages d'effacement.

`test_video_memory.py` vérifie les 256 valeurs de couleur sur chaque page,
le défaut à froid, les trous firmware et l'autre page. Le nouveau
`test_lores_pixels.py` compare chaque cellule écrite et relue au modèle,
y compris les nibbles voisins, les tables froides sur les deux pages,
trois changements de page et les coordonnées hors écran. Les deux tests
tournent sur NMOS II+ et 65C02 IIe. Les cinq nouveaux cas entrent dans
`baseline.json` sans réinitialiser les références HGR/DHGR existantes.

Validation : `make all`, `make test-hgr bench-check` et les 24 programmes
de contrôle de l'archive. La reconstruction ne change aucun disque livré.

## Série du 5 novembre 2026 : tables mathématiques et racine carrée

Mesures NMOS 6502 par `python3 dev/tests/test_math.py`, avec tables à `$0800`
puis `$4000`. L'initialisation fait progresser la différence des quarts de
carrés une entrée sur deux, compte en X/Y et copie les deux moitiés du
miroir dans une seule boucle. La racine détecte 255 par débordement du
candidat. Les 2 048 octets de tables, 256 graines et 65 536 racines sont
comparés aux calculs Python pour chacun des deux placements.

| Mesure | Avant | Après |
|---|---:|---:|
| `mul_init`, cycles avec JSR/RTS | 48 707 | 37 691 (−22,6 %) |
| `mul_init`, code | 128 octets | 110 octets |
| `sqrt_init`, cycles avec JSR/RTS | 25 049 | 24 031 (−4,1 %) |
| Noyau `isqrt16`, code | 44 octets | 42 octets |
| Parcours des 65 536 racines, boucle et stockage du test inclus | 5 727 330 cycles | 5 529 438 cycles (−3,5 %) |

RAM et page zéro inchangées. Chaque étape ordinaire de racine gagne deux
cycles ; le retour de la racine maximale 255 coûte deux cycles de plus.
Ces mesures dédiées ne modifient pas les références HGR/DHGR.

La réduction de taille a exposé un défaut préexistant de `vapor_sync_in` :
la retenue du compteur laissait 17 cycles entre deux lectures, ce qui pouvait
manquer un marqueur vidéo. Une lecture intermédiaire partage cet intervalle
en 12 puis 15 cycles. Cette correction coûte 18 octets de code, sans RAM
supplémentaire, et borne l'échec sans marqueur à 65 537 polls. Un nouveau
test de 4 096 timings d'entrée échoue avec l'ancien code (20 378 cycles
d'attente) et passe avec la correction (maximum 17 044 pour une période de
17 030). La corde retrouve 600/600 flips à trois périodes, contre 596/600
après la seule réduction mathématique. Les gains de taille mathématiques
restent indépendants ; les clients qui lient aussi ce synchroniseur paient
les 18 octets de la correction.

Validation : reconstruction `make all`, suite `make test-dev test-snake`
(budgets inclus), tests Dirtbike et Cutrope et exemples lander, halfpipe,
rope et catapult. Les disques DSK/WOZ modifiés sont reconstruits.

## Mesures initiales HGR/DHGR

Après découpage des tables, les programmes du benchmark mesurent 299 octets
de RAM pour un effacement HGR, 1 016 pour le blitter aligné et 1 297 pour le
texte ou les rectangles, contre 1 575 auparavant. Ces chiffres comprennent
la BSS du programme/CRT, pas les pages vidéo ni la pile C réservée. La nouvelle
diagonale `hgr_line(0,0,279,191)` prend 61 457 cycles et conserve exactement
les pixels du Bresenham C. Le noyau DHGR d'une ligne est contrôlé séparément
sous 1 300 cycles ; le benchmark C de `dhgr_clear_rows(40,1,9)` inclut aussi
la préparation du motif et l'adressage.

Optimisation des boucles d'effacement : huit `STA` par tour dans
`HGR_CLEAR_LOOP`, quatre paires par tour dans `dhgr_clear_asm`. Mesures avec
les mêmes appels et cœurs que ci-dessus :

| Opération | Avant (cycles) | Après (cycles) | Réduction | Code ajouté |
| --- | ---: | ---: | ---: | ---: |
| `hgr_clear(0)` | 51 514 | 46 346 | 10,0 % | 28 octets par expansion de la macro |
| `dhgr_clear(9)` | 207 865 | 189 494 | 8,8 % | 30 octets |

RAM et page zéro inchangées. DHGR conserve les écritures indirectes pour remplir la banque
auxiliaire sans modifier le code ; les interruptions restent protégées.
Les références historiques de `baseline.json` sont conservées et les budgets
`--dhgr --check` passent.

Les boucles de tracé ont aussi été simplifiées : `dhgr_span_asm` réserve
les contrôles de masque aux extrémités et utilise la retenue de `LSR` pour
choisir la banque des octets intérieurs. `hgr_pixrect_asm` réutilise la
colonne dans Y et teste la fin après chaque écriture intérieure.

| Opération | Avant (cycles) | Après (cycles) | Réduction | Variation de code |
| --- | ---: | ---: | ---: | ---: |
| Segment HGR, 280 pixels | 3 229 | 3 097 | 4,1 % | −4 octets |
| Rectangle HGR, 140 × 16 pixels | 6 884 | 6 132 | 10,9 % | −4 octets |
| Segment DHGR, 560 pixels | 12 117 | 9 590 | 20,9 % | +29 octets |
| Rectangle DHGR, 70 × 16 pixels couleur | 75 830 | 56 214 | 25,9 % | +29 octets |

Les deux opérations d'une même famille partagent leur noyau : la variation
de code ne s'additionne pas. RAM et page zéro restent inchangées.
`test_dhgr_spans.py` vérifie les extrémités et
intérieurs avec un modèle par pixel : 16 couleurs, deux pages et deux
banques, 320 lignes au total. Les tests d'intégration HGR/DHGR et les
budgets `--dhgr --check` passent.

Le rendu `hgr_text8_asm` décale le bas du glyphe dans l'accumulateur au lieu
de la page zéro et évite de recharger ce résultat. `dhgr_block_asm` intègre
l'avance des pointeurs dans les trois boucles (lecture, écriture, sprite)
et garde l'octet à écrire dans A pendant le choix de banque.

| Opération | Avant (cycles) | Après (cycles) | Réduction | Variation de code |
| --- | ---: | ---: | ---: | ---: |
| Texte HGR, « APPLE II » | 8 997 | 8 514 | 5,4 % | −3 octets |
| Écriture de bloc DHGR, 8 × 8 octets | 10 966 | 9 819 | 10,5 % | +30 octets |
| Sprite masqué DHGR du benchmark | 5 158 | 5 108 | 1,0 % | +30 octets |

Lecture, écriture et sprite DHGR partagent le même objet : les 30 octets
ajoutés ne s'additionnent pas. RAM et page zéro restent inchangées. Les
tests d'intégration HGR/DHGR et les budgets passent ; `test_hgr_glyphs.py`
compare les 96 glyphes aux pixels attendus pour les sept décalages et les
deux pages (1 344 glyphes), en vérifiant aussi la palette et les trous vidéo.

L'évaluation de fhpack, fdraw et des sprites compilés est dans
[`dev/tests/techniques`](../tests/techniques/README.md) : `make test-techniques`.
Elle mesure les alternatives et vérifie le framebuffer ; elle ne modifie pas
les références de performance des bibliothèques actuelles.


## Premier appel et scènes de rendu

Les budgets supplémentaires ne remplacent aucune référence historique.
Chaque cas compile un programme distinct avec cc65 ; le premier appel exclut
l'initialisation du mode mais inclut la construction des tables encore absentes.
Les cas chauds exécutent un appel avant les marqueurs, ou deux frames pour
remplir les historiques des deux pages du moteur de sprites.

| Cas | Cycles mesurés |
|---|---:|
| `gfx_diagonal`, noyau HGR préparé | 61 683 |
| `hgr_diagonal_cold`, premier appel | 122 725 |
| HUD : titre et deux champs numériques, premier appel | 106 922 |
| Même HUD préparé | 39 131 |
| Frame de quatre sprites chevauchants + compteur + présentation, première | 46 327 |
| Même scène, restauration des fonds des deux pages préparée | 29 633 |

La scène utilise quatre formes de 14×4 pixels, un pool externe de 64 octets et
deux pages. La présentation inclut la bascule et la sélection de la prochaine
page, sans attente VBL ni logique de jeu. Ces chiffres ne sont donc pas une
promesse de 60 FPS : une frame de 29 633 cycles dépasse déjà une période de
17 030 cycles du runner NTSC. Le motif, le clipping et les restaurations sont
validés séparément par les tests de primitives et de sprites. Le JSON conserve
les coûts complets du programme de mesure, y compris le code de préchauffage.
Les tailles binaires froid/chaud ne comparent donc pas uniquement la primitive.


## HUD différentiel et présentation

`hgr_hud_putu` conserve un historique par page. Un appel pour la même valeur
ne convertit ni ne dessine ; un changement ne traite que les cellules modifiées.

| Opération actuelle | Cycles |
|---|---:|
| Champ cache de cinq chiffres, valeur inchangée | 518 |
| Même champ, 12345 → 12346 | 13 805 |
| Changer de page + résoudre 192 adresses, boucle compacte de référence | 7 505 |
| Même travail, boucle déroulée retenue | 6 511 |
| Prototype à base fixe avec correction par ligne | 4 823 |

Le déroulement ajoute **54 octets de code**, sans RAM ni ZP supplémentaires.
Le prototype fixe ajoute un octet d'état et calcule les pointeurs sans muter
la table. Ses 192 adresses sont testées sur les deux pages, mais il ne respecte
pas le contrat actuel des accès directs à `hgr_rowhi`. Il reste un comparatif
isolé ; le gain ne représente pas celui d'un moteur complet porté à ce format.
La bibliothèque conserve son ABI et utilise la boucle déroulée.

## Scènes et boucle complète

Les scènes supplémentaires utilisent des sprites correctement prédécalés :
quatre formes 7×8 dans les sept phases, puis quatre formes 21×16 chevauchantes,
au centre et rognées au bord droit/bas. Chaque cas prépare les deux historiques.
Le maximum observé est **54 998 cycles**, sans attente ni logique de jeu.
Le test de stress compare 32 scènes aux pixels attendus, aux bits de palette,
aux trous mémoire et aux gardes du pool sur les deux pages.

La boucle complète lit le clavier, calcule quatre positions, restaure/dessine,
met à jour son compteur, attend, puis présente : **45 245 cycles** avec le
repli II+ WAIT(40), **51 077 cycles** avec VBL IIe. Ces deux runners ont des
CPU distincts ; ces mesures caractérisent les deux configurations et ne sont
pas une comparaison isolée du coût de l'attente. Le cas IIe inclut la phase
VBL déterminée par ses frames de préchauffage ; ce n'est pas une borne de toute
entrée possible dans l'attente. La charge dépasse une période de rafraîchissement.

## Comptage mémoire et pile

Le code inclut maintenant `ONCE`, `INIT` et `LOWCODE`. Une assertion confronte
code + RODATA + DATA à la taille de chaque binaire de benchmark pour détecter
un segment chargé non compté. `legacy_references` conserve les anciens budgets.
La migration ajoute les 12 octets ONCE du CRT aux références de code, puis les
54 octets de la nouvelle boucle là où elle est liée ; les budgets historiques
cycles, binaire, RAM et ZP restent inchangés.

`c_stack_peak_bytes` mesure la profondeur observée pendant la charge balisée,
`c_stack_reserved_bytes` sa réservation. Les runners observent le pointeur cc65
aux appels/retours/sauts et accès `(sp),Y`, évitant les valeurs transitoires
entre les écritures de ses deux octets. a2run observe également les écritures
réelles dans la zone réservée. Le test alloue exactement 1 puis 37 octets et
vérifie les deux runners. Le maximum des scènes actuelles est 37 octets ; le
segment DHGR monochrome utilise 38 octets dans sa charge de benchmark.
Cette observation ne prouve pas une borne statique pour toutes les branches
ou des noyaux ASM qui alloueraient sans appel ni accès via sp. La pile matérielle
est distincte. Le profilage n'ajoute aucun cycle à l'horloge CPU émulée.

## Rendu incrémental : références actuelles

Les anciennes scènes restent mesurées avec leurs appels inchangés. Une scène
dont les sprites sont immobiles peut maintenant garder ses couches et éviter
la restauration/redessin. Les nouvelles scènes suffixées `_moving` déplacent
chaque sprite avec `frame % 3` : chaque page retrouve ainsi une position
modifiée, contrairement à une alternance de période deux qui pourrait garder
le même contenu sur les deux historiques.

| Charge | Avant | Maintenant |
|---|---:|---:|
| HUD, une valeur inchangée | 518 | 519 cycles |
| HUD, un chiffre modifié | 13 805 | 10 813 cycles |
| Scène historique préparée | 29 633 (mesure précédente) | 18 410 cycles |
| Quatre grands sprites immobiles + compteur + présentation | 54 998 | 16 503 cycles |

Le dernier gain vient surtout du travail évité. La nouvelle scène de quatre
sprites 21×16 **tous mobiles** coûte 57 387 cycles, sans attente ni logique de
jeu. Cette charge ajoute les appels de déplacement et ne remplace pas le
cas immobile historique. Les scènes mobiles 7×8 couvrent les sept phases.
Le maximum de ces tests ne constitue pas une borne de tous les jeux possibles.

Le nouveau HUD mesure 3 978 octets de binaire, 1 344 de RAM et 42 de ZP,
contre 5 039, 1 615 et 68 auparavant : coût du programme entier de mesure,
CRT compris. Il économise 1 061 octets chargés, 271 de RAM et 26 de ZP.
Le premier appel du champ prend 85 165 cycles, initialisations paresseuses
incluses. Les sept cas `hgr_hud_changed_phaseN` changent plusieurs chiffres ;
le changement 12345 → 65432 modifie les cinq cellules. Leur maximum est
mesuré sur les sept alignements atteint 30 048 cycles, avec les mêmes
contrats de boîte opaque.
Préparer le champ et ses historiques avant l'animation évite le premier appel
pendant la boucle, sans masquer son coût dans les budgets.

L'accès optionnel aux tables immuables mesure 5 135 cycles pour changer la
base et résoudre 192 pointeurs en assembleur, contre 6 511 pour la stratégie
historique déroulée. L'enveloppe C appelée 192 fois coûte 28 441 cycles :
utiliser les tables directement dans un noyau natif si ce coût est sensible.
Cette alternative conserve l'ABI historique ; elle ne porte pas automatiquement
les blitters existants. Les offsets prennent 384 octets de RODATA, zéro BSS.

Le suivi des sprites ajoute un octet de BSS et environ 432 octets au programme
des scènes historiques sans HUD spécialisé. Les budgets des consommateurs
modifiés sont recalés explicitement sur cette version ; leurs références
précédentes sont conservées dans `pre_incremental_references`. Les références
historiques des primitives indépendantes restent inchangées. Les nouveaux cas
ont leurs propres budgets et identités d'émulation.

## Pile matérielle

`hwstackwatch` active l'observation de S à chaque instruction ; `hwstack`
rapporte le maximum `255 - S`, la limite conservatrice 255 avant bouclage,
et un drapeau de débordement. Ce maximum inclut les retours et octets déjà
présents lors de l'entrée de la charge, contrairement à une profondeur ajoutée
à cette entrée. Les IRQ exécutées pendant cette fenêtre sont incluses.
Les sondes vérifient 37 poussées et un contrôle négatif qui fait boucler S,
sur a2run et sur POM2. Les métriques `hardware_stack_peak_bytes` et
`hardware_stack_available_bytes` complètent celles de la pile C.

Ces observations décrivent les chemins exécutés. Le détecteur suppose un
usage normal des instructions de pile ; il n'analyse pas statiquement toutes
les manipulations de S ni toutes les interruptions possibles. Le profilage
n'ajoute aucun cycle CPU émulé.

## 2026-10-22 : tailles acceptées contre des cycles (branche lib-dhgr)

Références recalées par `run.py --dhgr --update` après examen. Les hausses
de taille dépassent le seuil de 3 % du gate ; elles sont acceptées pour les
gains de cycles suivants (sortie écran identique à la version précédente).

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après | Origine |
| --- | ---: | ---: | ---: | ---: | --- |
| `hgr_diagonal` | 61 457 | 21 200 | 3 028 | 3 241 | tracé de ligne rapide, +159 octets de code |
| `hgr_diagonal_cold` | 122 688 | 82 175 | 2 997 | 3 210 | idem |
| `gfx_diagonal` | 61 418 | 21 263 | 3 486 | 3 655 | idem, +115 octets de code |
| `hgr_hud_changed_phase0..6` | 20 211–22 235 | 18 450–19 552 | 3 550 | 3 795 | table de glyphes 16×16 pré-décalés |
| `hgr_hud_warm` | 39 172 | 37 118 | 4 571 | 4 821 | idem |
| `hgr_hud_cold` | 106 877 | 104 876 | 4 481 | 4 731 | idem |

La table `hgr_glyph_shift.s` (224 octets de RODATA, indexée par
bit × 16 + quartet) remplace jusqu'à six décalages de 3 octets par rangée de
glyphe 16×16 : `hgr_puts` passe de 22 541 à 19 982 cycles (−11 %). Les scènes
et boucles qui lient le HUD 16×16 (`hgr_scene*`, `hgr_loop_*`) prennent les
mêmes +245 octets, à cycles stables.

Les cas DHGR recalés en même temps proviennent des primitives à tables de la
même branche : `dhgr_text` 239 492 → 44 259 cycles (+146 octets),
`dhgr_rect` 75 830 → 15 034 (+176), `dhgr_span` 12 117 → 3 279 (+418),
`dhgr_block` 10 966 → 6 839 (+255), `dhgr_sprite` 5 158 → 2 314 (+458).
Autres gains de la branche, sans dépassement : `hgr_tile_background`
9 546 → 6 782 cycles (+76 octets).

## 2026-10-31 : compositeur DHGR, deux pages, VBL, passe de taille

Nouveaux cas : `dhgr_spr_double_move` 16 697 cycles (`DHGR_SPR_DOUBLE`, le
drone d'un pixel par image en régime établi : ce déplacement et le
précédent réécrits sur la page cachée) et `dhgr_spr_vbl_move` 21 871
(`DHGR_SPR_VBL`, mesuré depuis un front de VBL : composé, puis écrit après
le front suivant ; un balayage d'attente compris). Recalé :
`dhgr_spr_move_chunky` 10 021 → 9 380 (les boucles de lignes de
`dhgr_cv_bitmap.s` n'appellent plus `dest`/`next_row`). Les autres cas du
compositeur restent dans ±2 % de leur référence (`dhgr_spr_move` 15 939,
`_wide` 20 667, `_cells` 18 776, `_solid` 11 025, `dhgr_spr_overlay_move`
13 196, `dhgr_cursor_move` 9 003) avec un cœur de 1 960 octets au lieu de
2 120 (palette et zone dans leurs propres membres, une boucle de découpe
pour les deux axes, une boucle de rectangles pour les deux chemins, fusion
des dégâts en O(n²)).

## 2026-11-03 : effacement DHGR complet, horloge vidéo plus courte

`dhgr_clear` : **187 309 → 114 377 cycles** (−39 %), 98 → 97 octets de code,
même page zéro (`ptr1`, `tmp1`). Chaque page de 256 octets est écrite en deux
passes (octets pairs, octets impairs) d'un seul octet de motif par huit
`sta abs,Y` (5 cycles l'octet) dont l'opérande de page est patché pendant que
RAMWRT est principal — sous RAMWRTON, l'écriture irait dans la copie
auxiliaire du code. Les IRQ ne sont plus masquées pendant tout l'effacement
(onze rafraîchissements) mais une page à la fois, environ 1 750 cycles.
`test_dhgr.py` et `test_dhgr_clear_rows.py` vérifient les seize couleurs sur
les deux pages et les deux banques, trous et commutateurs compris ; la
référence `dhgr_clear` est recalée (`run.py --dhgr --update --only dhgr_clear`).

`apple2vbl.s` (hors banc) : 166 → 149 octets de code à contrat constant,
après les +18 de la réutilisation du gestionnaire et de la libération sur
échec (`test_vbl_lifecycle.py`). CHROMABREAK relie les deux modules : +1 et −1,
le CODE de bibliothèque est inchangé et toutes les adresses de `spare.s`
tiennent sans retouche des réserves.

`dhgr_rect` (70×16) : **15 034 → 12 267 cycles** (−18 %), `dhgr_span` (560
points) : **3 279 → 2 796** (−15 %), +50 octets de code et 6 de BSS dans
`dhgr_span_asm.s`. L'intérieur de chaque banque est préparé une fois par appel
(première colonne, nombre de paires, colonne impaire finale, les deux octets
de motif dans l'ordre des colonnes) ; chaque ligne déroule une boucle par
paires sans comparaison de colonne, puis l'octet impair. Références recalées
pour ces deux cas.

`dhgr_clear_rows` : **1 177 → 712 cycles la ligne** (−40 %), cas de banc
`dhgr_clear_row` 1 579 → 1 115, 92 → 129 octets de code. Une ligne ne
traverse jamais de page et commence au plus à l'offset $D0 : quatre passes
(une par octet de motif) écrivent par cinq opérandes alignés sur la page,
Y parcourant la ligne deux octets par deux, cinq cycles l'octet ; seul l'octet
de page des opérandes est patché, RAMWRT principal. Référence recalée.

Nouveau cas `dhgr_small_text` : `dhgr_puts_small("APPLE II",0,0)`, le texte
compact de ROBOT SPACE STATION, **14 483 cycles** (1 810 le caractère, cinq
lignes lues-modifiées-écrites dans les deux banques), 2 994 octets de binaire.
Mesuré sans modification : une référence pour les passes suivantes.

Recalage des références HGR (`run.py --update`, a2run) : les commits de
bibliothèque du 2026-11-03 (préparation commune des remplissages inclusifs,
conversion hexadécimale native, décimal signé séparé, avance du crayon)
avaient amélioré treize cas sans recaler `baseline.json`. Les écarts :
`hgr_span` 3 101 → 1 096 cycles et 2 487 → 2 036 octets, `hgr_text`
8 547 → 8 448, `hgr_sprite7` 1 668 → 1 657, `hgr_diagonal` 3 241 → 2 803
octets (21 200 → 21 144 cycles), `gfx_diagonal` 3 655 → 3 217 octets
(21 263 → 21 379 cycles), `hgr_diagonal_cold` 3 210 → 2 772 octets
(82 175 → 82 801 cycles), `hgr_hud_cold` 104 439 → 103 829, `hgr_hud_warm`
36 655 → 36 100, `hgr_scene_cold` 42 598 → 42 484, `hgr_scene_warm`
15 097 → 14 956, et leurs variantes `_x7folded`. RAM et page zéro
inchangées ; les budgets absolus et le tableau du README du banc restent
valables.

Rectangles HGR : les octets pleins sont comptés une fois par appel (paires,
octet impair) et écrits deux par deux par ligne au lieu d'une comparaison de
colonne à chaque octet. `hgr_rect` (140×16) **6 117 → 5 213 cycles** (−15 %),
`hgr_byte_rect` (nouveau cas : `hgr_fill_rect(32,16,0,40,$7F)`, 40 colonnes
× 16 lignes) **9 266 → 7 824** (−16 %), `hgr_span` (ligne de 280 pixels)
1 096 → 993 (−9 %). `hgr_pixrect_asm.s` 225 → 253 octets, `hgr_byte_rect_asm.s`
39 → 60 ; RAM et page zéro inchangées. Références recalées pour ces trois cas.

Lot annulé le jour même : les −13 octets de `mouse.s`/`video.s` décalent
les membres de bibliothèque qui suivent dans l'édition de liens de
CHROMABREAK ; les franchissements de page changent le coût de quelques
images, et sa campagne déterministe de 193 minutes (`tests/test_mouse.py`,
tier long, en CI) diverge : combo x7 au lieu du x8 attendu, pour un gain
nul en RAM (les octets étaient mis en réserve). Revenu aux modules et aux
disques du commit précédent, que la CI avait validés de bout en bout. Toute
réduction de la bibliothèque liée par CHROMABREAK demande donc ce tier long,
pas seulement les asserts de `spare.s`.

## 2026-11-04 : texte compact DHGR, vitesse et taille

`dhgr_small_text` (`dhgr_puts_small("APPLE II",0,0)`, arguments C compris) :
**14 483 → 13 253 cycles** (−8,5 %), **2 994 → 2 990 octets** de binaire,
**328 → 326 octets** de RAM. Le moteur `dhgr_small_asm.s` passe de 323 à
319 octets de code et de 14 à 12 octets de BSS ; tables (1 653 octets),
page zéro et pics de piles inchangés.

La colonne de banque et la base de la table d'encre sont préparées une fois
par caractère. Chaque rangée indexe cette base avec le quartet du glyphe et
le numéro d'octet, sans recalculer le pointeur. Les masques des deux bords
sont posés directement ; seuls les deux emplacements intérieurs sont mis
à zéro. Un octet auxiliaire entièrement couvert est écrit sans lecture via
le trampoline. Les transactions restent protégées par rangée, RAMRD/RAMWRT
principaux au retour, masque d'interruptions conservé.

`test_dhgr_small_text.py` vérifie 256 entrées × 7 alignements × 2 pages ×
2 masques IRQ, sur fond non uniforme dans les deux banques, avec police
liée puis relocalisée à `$0800` et `$08D3`. Oracle par pixel, limites de
cellule et de chaîne, voisins et trous mémoire compris. Le même test passe
sur le moteur précédent. La référence de ce seul cas est recalée ; les
98 cas du banc HGR/DHGR passent leurs budgets.

ROBOT SPACE STATION lie ce moteur : ses disques ProDOS et WOZ sont reconstruits.
Ses tiers rapide et long passent sur //e et //c (campagne et fuzz), ainsi
que la suite complète `make test-dhgr`.
CHROMABREAK garde des règles de compilation pour lui, mais ne le lie plus :
son disque reste identique, sans ajustement de `spare.s`. Ses tiers rapide
et long passent aussi : 60 secteurs terminés sur //e et //c, combo x8.
`make all` réussit et les 18 images WOZ correspondent aux disques source.

## 2026-11-04 : pixels et sprites HGR

Mesures avant/après avec le même cc65 et a2run NMOS, arguments C compris,
tables déjà construites :

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| `hgr_plot` (`139,40`) | 271 | 247 | 1 606 | 1 592 |
| `hgr_unplot` (`279,191`) | 277 | 256 | 1 610 | 1 596 |
| `hgr_sprite7` (4 octets × 8 lignes) | 1 657 | 1 649 | 1 834 | 1 828 |
| `hgr_preshift_phase0` (7×16, XOR) | 2 424 | 2 078 | 2 404 | 2 398 |
| `hgr_preshift_phase3` | 2 497 | 2 465 | 2 404 | 2 398 |
| `hgr_preshift_phase6` | 2 572 | 2 540 | 2 404 | 2 398 |

`hgr_pixel_asm.s` : adresse de ligne préparée avant colonne/masque, pour
charger directement Y/A ; plus de sauvegarde dans `tmp1/tmp2`. L'entrée C
termine par un saut vers cette préparation, qui conserve la retenue effacée
annonçant une coordonnée valide. **−14 octets de code**, −24/−21 cycles
sur les deux cas, aucune modification de la RAM ou de la page zéro allouées.

`hgr_blit7_asm.s` : le départ de ligne a un octet bas au plus égal à `$D0`,
la colonne est bornée à 39 ; leur somme ne produit jamais de retenue.
Suppression du `ADC #0` sur l'octet haut dans les trois boucles SET/CLEAR/XOR :
**−6 octets de code**, deux cycles de moins par ligne hors effets de
placement des branches. L'ordre de lecture/écriture reste croissant.

`hgr_preshift_asm.s` : X conserve la phase pendant que Y compte les lignes
du produit hauteur × stride. Le test de phase zéro passe avant ce produit,
sans instruction supplémentaire ni modification des autres phases : le
cas 7×16 gagne **14,3 %**, allègement du blitter ci-dessus compris.
RAM, tables et page zéro inchangées.

Nouveaux cas de banc pour les points et les phases 0/3/6, référence du blit
aligné recalée. `test_hgr_pixels.py` couvre les entrées C/ASM, la surface
280×192 sur les deux pages, un effacement à motif, les appels hors écran,
le bit de palette et les trous mémoire. `test_preshift_bounds.py` couvre
désormais aussi les hauteurs jusqu'à 255, les sept phases, les sprites vides
et le découpage, contre un oracle indépendant pour les deux API XOR.

Les 103 cas HGR/DHGR passent les budgets. Les tests de la suite HGR,
l'exemple HGR sur II+ et IIe, les projections et les exemples minimaux
passent ; `make all` réussit. Seul `HGR.dsk` et son jumeau WOZ changent
dans `dist/` pour cette passe (les changements de ROBOT SPACE STATION
appartiennent au lot de texte compact ci-dessus).

## 2026-11-04 : contrôleurs des compteurs HUD

Le fichier partagé `hgr_hud_putu.inc` perd **24 octets de code par format**
(8×8 ou 16×16), sans changement de RAM, page zéro, tables ou structure
publique. La conversion décimale et la voie incrémentale donnent déjà le
nombre de chiffres dans Y : plus de parcours de la chaîne. Après la
réduction de l'origine modulo 56, la division finale par sept s'effectue
dans A ; la première soustraction négative est annulée par `ADC #7`.

Mesures avant/après, arguments C compris, même environnement :

| Charge | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| HUD 16×16, valeur identique | 312 | 312 | 3 692 | 3 668 |
| HUD 16×16, un chiffre modifié | 4 704 | 4 505 | 3 692 | 3 668 |
| HUD 16×16, cinq chiffres modifiés, pire phase | 19 372 | 19 161 | 3 692 | 3 668 |
| HUD 8×8, valeur identique | 312 | 312 | 3 488 | 3 464 |
| HUD 8×8, cinq chiffres modifiés, pire phase | 7 683 | 7 482 | 3 488 | 3 464 |
| HUD 8×8, 9999 → 10000 | 7 119 | 6 912 | 3 488 | 3 464 |
| Jeu compact, pire phase | 16 669 | 16 450 | 7 162 | 7 138 |

Le jeu compact prend désormais 16 182..16 450 cycles selon l'alignement.
Les 54 références des HUD et de leurs consommateurs sont recalées, après
validation des budgets sur les 103 cas. Les primitives indépendantes
gardent leurs références. Le cas avec attente VBL reste à deux balayages
(34 050 → 34 054 cycles, variation de la boucle d'attente).

`test_hgr_hud.py`, sur NMOS et 65C02, ajoute toutes les origines valides
d'un champ d'un chiffre (265/273), dont les frontières /56 et /7, et toutes
les largeurs 1..14/1..5 avec +1/+2, retenue décimale et rejet de débordement.
Les précédents cas de cache par page, invalidation, raccourcissement et
palette restent vérifiés. Le jeu complet avec quatre sprites et musique
IRQ passe 1 000 images NTSC et 1 000 PAL, sans échéance manquée ni problème
de pile : 33 972..34 147 / 40 470..40 653 cycles entre présentations.

La reconstruction complète et les exemples HGR sur II+/IIe passent.
L'exemple minimal à double page conserve ses 1 000 images par standard,
avec bouclage du compteur : 34 050..34 070 / 40 550..40 570 cycles.
Le disque HGR est reconstruit ; les 18 jumeaux WOZ correspondent à leurs
disques source.

## 2026-11-04 : recoloration HGR et sélecteur partagé

Mesures avant/après, arguments C compris, tables préparées, même cc65 et
a2run NMOS :

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| `hgr_colorize`, 140×16, départ x=7 | 11 571 | 8 947 | 1 896 | 1 848 |
| `hgr_colorize_even`, 140×16, départ x=0 | 11 572 | 8 896 | 1 892 | 1 844 |
| `hgr_colorize_narrow`, 7×1, départ x=7 | 830 | 789 | 1 894 | 1 846 |
| `hgr_text_color`, « APPLE II » orange ×2 | 19 961 | 19 987 | 3 333 | 3 279 |

La boucle de recoloration choisit la parité une fois par ligne puis alterne
deux corps pair/impair. Elle conserve l'ordre croissant des écritures et
traite une largeur d'un octet depuis les deux parités. **−22,7 % de cycles**
sur le rectangle principal, pour six octets de code supplémentaires.

Le sélecteur de porteuses partagé passe du C à l'assembleur : 91 octets
de code deviennent 33 octets de code et une table de quatre octets.
Les couleurs invalides sont rejetées avant toute modification des
paramètres. Le gain net est de **48 octets chargés** pour la recoloration,
54 pour les clients de texte coloré. RAM et page zéro sont inchangées ;
le pic de pile matérielle du rectangle baisse de huit à sept octets.
Le texte coloré mesure 26 cycles de plus (+0,13 %) malgré son binaire réduit.

Quatre cas sont ajoutés au banc ; les six scènes existantes qui lient le
sélecteur sont recalées après comparaison. Leur binaire perd 54 octets et
leurs variations de cycles vont de −75 à +268. Les budgets absolus restent
inchangés.

`test_hgr_color.py` vérifie les 256 entrées du sélecteur, dont la conservation
des paramètres sur rejet, 294 rectangles et 98 glyphes teintés ou blancs.
Il couvre les deux pages, les deux parités, les sept phases du texte, le
découpage, les appels vides/hors écran et les trous mémoire, sur NMOS et
65C02. Les tests HGR, glyphes et reconstruction d'archive passent aussi.
La reconstruction complète et les tests de Snake passent ; son disque
DOS et son jumeau WOZ sont reconstruits.
Les 107 cas HGR/DHGR passent le contrôle des régressions et des budgets
absolus ; les 18 images WOZ correspondent à leurs disques source.

## 2026-11-04 : préparation des rectangles HGR

`hgr_pixrect_asm.s` perd **42 octets de code**. Les rectangles d'un seul
octet utilisent la même préparation des masques que les autres ; leurs
compteurs d'octets intérieurs, inutilisés, ne sont plus calculés. Les
masques sont déjà bornés à sept bits : leurs compléments utilisent
`EOR #$7F`, sans `AND` supplémentaire. Le décalage du masque droit fournit
la retenue nécessaire à `SBC #0`, et la comparaison des colonnes ordonnées
fournit celle du calcul de largeur. RAM, page zéro et pics de pile mesurés
restent identiques.

Mesures avant/après, arguments C compris, tables préparées :

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| Ligne horizontale, 280 pixels | 993 | 983 | 2 064 | 2 022 |
| Rectangle 140×16, remplissage | 5 213 | 5 213 | 2 091 | 2 049 |
| Rectangle 140×16, effacement | 5 221 | 5 219 | 2 091 | 2 049 |
| Rectangle 3×16 dans un octet, remplissage | 1 688 | 1 687 | 2 089 | 2 047 |
| Rectangle 3×16 dans un octet, effacement | 1 691 | 1 693 | 2 089 | 2 047 |
| Rectangle 2×16 à cheval sur deux octets | 2 172 | 2 172 | 2 091 | 2 049 |
| Rectangle découpé à droite et en bas | 1 048 | 1 040 | 2 087 | 2 045 |
| Cellule 6×6 à la colonne 1 | 761 | 754 | 1 841 | 1 799 |

Les consommateurs perdent aussi 42 octets. Leurs temps ne baissent pas
tous : la diagonale HGR passe de 21 171 à 21 319 cycles (+0,7 %), celle
de GFX de 21 407 à 21 323. Le code de ligne est inchangé ; les variations
sont compatibles avec les effets du placement sur les accès et branches
6502. Les mesures de rectangles ci-dessus ne sont donc pas extrapolées
à tous les clients.

Six cas de banc sont ajoutés et les références des 18 charges affectées
sont recalées ; les budgets absolus restent inchangés. Le nouveau test
`test_hgr_rects.py`, intégré aux cibles HGR et IIe, vérifie 752 rectangles
par modèle CPU : toutes les combinaisons de phases de bord, les largeurs
de 1 à 40 octets, le remplissage et l'effacement, les modes natifs non nuls,
les deux pages, le découpage, les appels vides/hors écran, la palette et
les trous mémoire. L'oracle dessine pixel par pixel.

Les tests de rectangles NMOS/65C02, l'intégration HGR (dont les 840 cellules),
Snake, l'exemple HGR, les exemples minimaux et les projections passent.
`make all` réussit ; HGR et Snake sont reconstruits, et les 18 jumeaux WOZ
correspondent à leurs disques source.
Le contrôle final passe les 113 cas et les 16 budgets absolus ; ses mesures
reproduisent exactement le précédent passage complet.

## 2026-11-04 : compteur du remplissage DHGR par lignes

`dhgr_clear_rows_asm.s` passe de **129 à 117 octets de code**. Chaque
demi-motif effectue toujours quatre tours de cinq écritures ; X compte ces
tours, à la place de la comparaison de Y avec une limite calculée en page
zéro. L'octet haut de l'adresse de ligne passe directement dans A aux
opérandes automodifiées, sans stockage/relecture temporaire. Le noyau
n'utilise plus `tmp1` ni l'octet haut de `ptr1` ; la mémoire allouée reste
identique, comme les pics de pile.

La sonde native mesure **712 → 688 cycles** par ligne (−3,4 %) avec le même
test avant/après. Les changements ne modifient ni l'ordre des écritures,
ni les commutations de banques, ni la restauration du masque d'IRQ.

| Appel C | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| Une ligne à y=40 | 1 115 | 1 090 | 1 672 | 1 660 |
| 16 lignes à y=40 | 12 110 | 11 725 | 1 673 | 1 661 |
| 192 lignes visibles | 141 187 | 136 555 | 1 673 | 1 661 |
| 255 lignes demandées à y=190, découpées à deux | 1 870 | 1 822 | 1 673 | 1 661 |

Trois cas de banc sont ajoutés. Seules ces quatre mesures changent dans le
passage complet de 116 cas ; leurs références sont recalées sans modifier
les budgets absolus.

La sonde d'IRQ de `test_dhgr_clear_rows.py` initialise désormais explicitement
`dhgr_addr` vers une ligne vidéo valide déjà effacée, dont la ligne 191
(octet bas `$D0`) sur chaque page. Elle ne dépend plus d'une adresse globale
non préparée par l'API de remplissage multiple. Les seize couleurs, les
deux pages et banques, les trous mémoire, le découpage et les deux masques
d'IRQ passent avec l'ancien et le nouveau noyau. Les interruptions VIA
périodiques passent aussi, avec contrôle des banques, des gardes et des pixels.

Le contrôle final des 116 cas et 16 budgets absolus passe ; les mesures
reproduisent exactement le premier passage complet. `make all` réussit,
DHGR ACTION passe sur //e et //c, ainsi que les exemples minimaux ProDOS
(refus de /RAM et démarrage sans /RAM). Les 18 images WOZ correspondent
à leurs disques source.
ROBOT SPACE STATION est reconstruit et passe ses tiers rapide et long sur
//e et //c : les 20 missions de chaque campagne et les tests aléatoires
restent conformes aux modèles de référence.

## 2026-11-04 : bitmaps HGR MSB-first

Le noyau `hgr_bitmap_asm.s` perd **8 octets de code**. Le compteur de pixels
est décrémenté dès que le pixel est traité : une ligne terminée quitte la
boucle avant le compteur de bits source ou une éventuelle recharge. La
sélection SET/CLEAR/XOR passe par Y pour conserver l'accumulateur de pixels
dans A ; les trois modes partagent l'écriture finale. Dans SET, le masque
non nul garantit que le résultat de OR est non nul, ce qui permet un
branchement court vers cette écriture.

Mesures NMOS avec les arguments C, même bitmap mixte 16×8 et mêmes outils :

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| SET, phase 0 | 6 870 | 6 591 | 1 953 | 1 945 |
| CLEAR, phase 0 | 6 975 | 6 696 | 1 951 | 1 943 |
| XOR, phase 0 | 6 891 | 6 612 | 1 953 | 1 945 |
| SET, phase 3 | 6 900 | 6 618 | 1 953 | 1 945 |
| CLEAR, phase 3 | 7 010 | 6 728 | 1 951 | 1 943 |
| XOR, phase 3 | 6 922 | 6 640 | 1 953 | 1 945 |
| SET, phase 6 | 7 146 | 6 861 | 1 953 | 1 945 |
| CLEAR, phase 6 | 7 261 | 6 976 | 1 951 | 1 943 |
| XOR, phase 6 | 7 169 | 6 884 | 1 953 | 1 945 |
| Bitmap vide, phase 3 | 5 792 | 5 576 | 1 953 | 1 945 |
| XOR découpé à droite et en bas | 1 275 | 1 249 | 1 953 | 1 945 |

Les neuf cas de bitmap mixte gagnent **3,9..4,1 %**. RAM, page zéro et pics
de pile restent identiques. Ces onze mesures sont ajoutées au banc ; les
116 cas précédents restent strictement identiques dans le passage complet.
Les budgets absolus sont conservés.

`test_hgr_bitmap.py`, intégré aux cibles HGR et IIe, compare 612 rendus par
CPU à un oracle pixel par pixel : SET/CLEAR/XOR, les sept phases, les
largeurs autour des limites de sept et huit pixels, les dimensions jusqu'à
255, le stride source avant découpage, les bitmaps vides/pleins, les deux
pages, la palette et les trous mémoire. Il passe sur NMOS et 65C02, ainsi
que l'intégration HGR et la suite de comparaison des techniques de sprites.
`make all` réussit ; les 37 fichiers de distribution gardent exactement
leurs empreintes SHA-256 pour cette passe.
Le contrôle final passe les 127 cas et les 16 budgets absolus ; toutes les
mesures sont identiques au premier passage complet, y compris après le
remplacement du cœur IIe signalé par le banc pendant cette validation.

## 2026-11-04 : texte HGR agrandi

`hgr_text16_asm.s` perd **30 octets de code et 5 octets de page zéro** :
les quatre porteuses de colonnes se ramènent à deux valeurs alternées,
et trois temporaires utilisent les scratch cc65 déjà disponibles. Le
blitter ne fait aucun appel imbriqué. Les tables, l'autre RAM et les pics
de pile mesurés restent identiques.

Les lignes source vides sautent directement à la suivante. Y parcourt
les colonnes une seule fois, y compris quand une cellule est transparente.
Deux rotations assemblent les bits doublés 14..21 ; le bit de signe
restant décide directement de la quatrième cellule. Les masques de couleur
et le bit de palette sont appliqués comme auparavant, après le test du
masque de pixels non teinté.

Mesures avant/après avec le même cc65 et a2run NMOS, arguments C compris
sauf le glyphe plein, mesuré à l'entrée native :

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| « APPLE II » orange, phase 0 | 19 987 | 16 662 | 3 279 | 3 249 |
| Orange, phase 3 | 20 293 | 16 924 | 3 281 | 3 251 |
| Orange, phase 6 | 20 179 | 16 829 | 3 283 | 3 253 |
| « APPLE II » blanc, phase 0 | 19 887 | 16 737 | 3 246 | 3 216 |
| Blanc, phase 3 | 20 195 | 16 978 | 3 250 | 3 220 |
| Blanc, phase 6 | 20 072 | 16 880 | 3 250 | 3 220 |
| Huit espaces | 16 159 | 5 476 | 3 246 | 3 216 |
| Glyphe 16×16 entièrement plein, phase 6 | 2 873 | 2 641 | 2 142 | 2 112 |

Les chaînes mixtes gagnent **15,8..16,6 %**, les espaces **66,1 %** et le
glyphe plein **8,1 %**. La page zéro des huit cas passe de 50 à 45 octets.
Sept cas sont ajoutés au banc ; les six scènes existantes qui utilisent
aussi ce blitter gagnent toutes en cycles et perdent les mêmes 30 octets
de code et 5 de page zéro. Les 14 références affectées sont recalées,
avec les mêmes budgets absolus.

`test_hgr_text16.py` vérifie 280 scènes par modèle CPU : les 256 motifs
d'une ligne de glyphe (dont le huitième bit, qui peut atteindre une
quatrième colonne HGR), les 96 caractères intégrés, cinq couleurs, les
sept phases, les deux parités et les deux pages. Les tests couvrent les
lignes vides, le bas et la droite de l'écran, les bits de palette et les
trous mémoire. Ils passent sur NMOS et 65C02, ainsi que l'intégration HGR
et les tests de recoloration.
Le contrôle final passe les 134 cas et les 16 budgets absolus ; les mesures
sont identiques au premier passage complet. `make all` réussit. Seuls
`SNAKE.dsk` et son jumeau WOZ changent dans la distribution pour cette passe ;
Snake passe ses tests de jeu, de cadence PAL/NTSC et de sauvegarde. Les
18 images WOZ correspondent à leurs disques source.

## 2026-11-04 : texte HGR 8×8 et adresse des glyphes

`hgr_text8_asm.s` utilise X comme compteur de lignes et garde Y pour les
décalages et les accès écran. Cela remplace les incréments et comparaisons
du compteur en page zéro. Le masque du deuxième octet est inutile : un
motif source de huit bits décalé de zéro à six tient sur quatorze bits.
Le noyau perd **8 octets de code**, sans nouvelle allocation.

Le helper partagé `glyph_addr` calcule séparément `index >> 5` et
`index << 3`, puis ajoute la base de police avec sa retenue. Il perd
**3 octets de code** et passe de **61 à 54 cycles**, JSR/RTS compris,
en conservant X/Y. Le même test vérifie l'ancien et le nouveau helper.
Les clients 8×8 gagnent donc **11 octets**, les autres clients qui lient
le helper en gagnent trois. RAM, page zéro et pics de pile restent identiques.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| « APPLE II » 8×8, phase 0 | 8 448 | 7 886 | 2 581 | 2 570 |
| Phase 3 | 9 238 | 8 672 | 2 585 | 2 574 |
| Phase 6 | 9 129 | 8 563 | 2 585 | 2 574 |
| Huit espaces 8×8 | 4 746 | 4 282 | 2 581 | 2 570 |
| Glyphe 8×8 plein, phase 6, entrée native | 1 432 | 1 358 | 1 731 | 1 720 |
| « APPLE II » 16×16 blanc, phase 0 | 16 737 | 16 681 | 3 216 | 3 213 |
| « APPLE II » 16×16 orange, phase 0 | 16 662 | 16 606 | 3 249 | 3 246 |

Le texte 8×8 gagne **6,1..6,7 %**, les espaces **9,8 %** et le glyphe plein
**5,2 %**. Quatre cas sont ajoutés au banc ; 73 charges changent de taille
ou de temps. Les déplacements de code produisent aussi de petites hausses :
le jeu compact gagne trois octets mais prend 15..19 cycles de plus, soit
16 200..16 468 cycles selon la phase (+0,12 % au plus). Les budgets absolus
restent inchangés, avec 11 592/18 092 cycles de marge NTSC/PAL après réserve.

`test_hgr_glyph_addr.py` vérifie **147 456 appels** par CPU : les 96 indices,
tous les octets bas de police, trois bases hautes (dont `$FFxx` pour le
rebouclage sur 16 bits), les deux retenues entrantes et la conservation de
X/Y et de la base. `test_hgr_glyphs.py` conserve ses 1 344 glyphes publics
et ajoute tous les 256 motifs de ligne à l'entrée native, les sept phases,
les glyphes vides et les bords droit/bas, sur les deux pages. Ces tests
passent sur NMOS et 65C02, ainsi que le texte 16×16 et l'intégration HGR.

`make all` réussit. Snake et LIGHT3DBALL passent leurs tests, dont les cinq
niveaux de LIGHT3DBALL. Les exemples HGR, les exemples minimaux (1 000
présentations NTSC/PAL) et les projections passent aussi. Les disques HGR,
Snake et LIGHT3DBALL sont reconstruits ; les 18 jumeaux WOZ sont conformes.
Le contrôle final passe les 138 cas et les 16 budgets absolus, avec des
mesures identiques au premier passage complet.

## 2026-11-04 : HUD compact et dépendances de l'archive

Le noyau HUD 8×8 utilise X pour parcourir les 16 octets source du glyphe.
La division par deux fournit la ligne et efface la retenue avant l'ajout
de Y écran. Le scratch existant `tmp1` conserve l'offset pour les lectures.
Cela retire **18 octets de code et deux compteurs BSS**, sans élargir la
liste des registres et temporaires détruits.

Les arguments de glyphe, l'état de parcours des chaînes et le helper
`glyph_addr` occupent désormais trois membres indépendants de l'archive.
Le HUD8 ne lie plus les **26 octets de code et sept octets de page zéro**
inutilisés du texte général. Son gain total est donc **44 octets de code,
sept de page zéro et deux de BSS**. Le HUD16 conserve le helper mais
économise cinq octets de page zéro. Les clients mixtes partagent les mêmes
symboles, sans changement d'API ni duplication.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| HUD8, un chiffre changé | 2 442 | 2 283 | 3 461 | 3 417 |
| HUD8, cinq chiffres changés, phase 0 | 7 460 | 6 641 | 3 461 | 3 417 |
| HUD8, cinq chiffres changés, phase 6 (maximum) | 7 479 | 6 663 | 3 461 | 3 417 |
| HUD8, valeur inchangée | 312 | 312 | 3 461 | 3 417 |
| HUD8, premier affichage | 7 163 | 6 353 | 3 447 | 3 403 |
| HUD8, retenue 9999 → 10000 | 6 912 | 6 113 | 3 461 | 3 417 |
| Jeu compact, phase 1 (maximum) | 16 468 | 15 927 | 7 135 | 7 091 |

Le changement de cinq chiffres gagne environ **11 %**, celui d'un chiffre
**6,5 %**. Le jeu compact prend 15 672..15 927 cycles, avec 1 618 octets
de RAM et 49 de page zéro. La marge après réserve reste de
12 133/18 633 cycles NTSC/PAL, sans modifier les budgets absolus. Les
autres charges ne changent pas de temps d'exécution. Le nouveau cas à un
chiffre porte le banc à 139 cas ; 55 références sont ajoutées ou recalées.

Les tests HUD passent sur NMOS et 65C02 : 168 mises à jour, 70 glyphes
aux bords, 273 origines de cellule, largeurs 1..5, retenues et débordements,
sur les deux pages. Le helper conserve ses 147 456 appels vérifiés par CPU.
L'intégration HGR vérifie 22 clients d'archive, dont HUD8 seul, HUD16 seul
et HUD8 avec texte. Les configurations de compilation et les dépendances
transitives passent aussi. La cadence avec musique sous IRQ tient
1 000 images par standard sans échéance manquée.

`make all` réussit. Snake, les cinq niveaux de LIGHT3DBALL, les exemples
HGR et minimaux, ainsi que les projections passent leurs tests. Les
disques HGR, Snake et LIGHT3DBALL et leurs jumeaux WOZ sont reconstruits ;
les 18 images WOZ correspondent aux disques source.
Le contrôle final passe les 139 cas et les 16 budgets absolus ; les mesures
sont identiques au premier passage complet.

## 2026-11-04 : écritures opaques du HUD 16×16

La deuxième colonne d'une cellule de 16/18 pixels est toujours entièrement
recouverte, quel que soit l'alignement. Le noyau l'écrit directement dans
les deux lignes écran, sans relire le fond ni appliquer un masque nul.
Le masque correspondant et son initialisation disparaissent. Les colonnes
de bord conservent leurs masques et la remise à zéro du bit de palette.

Deux rotations assemblent les bits 14..21 du glyphe doublé ; le bit de
signe fournit ensuite le seul pixel pouvant atteindre la quatrième colonne.
Le décalage du numéro de ligne fournit déjà une retenue nulle. Enfin, les
trois routines d'écriture restantes, chacune appelée à un seul endroit,
sont développées dans la boucle : aucun code dupliqué, aucun JSR/RTS pour
ces écritures. Le noyau perd **42 octets de code et un octet de BSS**.
La page zéro, les tables et les pics de pile mesurés restent identiques.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| HUD16, un chiffre changé | 4 495 | 3 926 | 3 665 | 3 623 |
| Cinq chiffres, phase 0 | 18 545 | 15 393 | 3 665 | 3 623 |
| Cinq chiffres, phase 5 (maximum) | 19 115 | 15 819 | 3 665 | 3 623 |
| Valeur inchangée | 312 | 312 | 3 665 | 3 623 |
| Premier affichage avec initialisation des tables | 63 830 | 60 710 | 3 651 | 3 609 |
| Scène mobile, phase 0 | 24 988 | 24 393 | 6 927 | 6 885 |
| Quatre grands sprites mobiles et compteur | 39 170 | 38 578 | 7 594 | 7 552 |

Les cinq chiffres gagnent **16,8..17,2 %**, le chiffre isolé **12,7 %**.
Les 30 charges affectées perdent toutes 42 octets chargés et un de RAM.
Le client HUD isolé utilise 805 octets de RAM. La boucle synchronisée sur
VBL, attente comprise, passe de 34 048 à 34 055 cycles (+0,02 %) ; les
scènes mobiles mesurées sans attente gagnent toutes du temps. Le stress
des quatre grands sprites reste au-delà du budget ; les limites absolues
ne sont pas modifiées. Les autres charges gardent leurs mesures.

Les tests HUD passent sur NMOS et 65C02 : 168 mises à jour sur deux pages,
70 glyphes aux bords droit/bas, les 265 origines d'une cellule, les largeurs
1..14, les retenues décimales, l'invalidation et les débordements. Les
comparaisons de mémoire vérifient le fond coloré, la palette et les pixels
voisins. L'intégration HGR passe ses 22 clients d'archive, 21 scènes,
840 cellules, le texte GFX et les avances de chaînes.

`make all` réussit. Seuls `HGR.dsk` et son jumeau WOZ changent pour cette
passe. L'exemple HGR passe le démarrage, l'animation, la pause/reprise,
les flèches et le retour DOS sur II+ et IIe. Les 18 images WOZ sont conformes.
Les 139 mesures et les 16 budgets absolus passent le contrôle final ; les
résultats sont identiques au premier passage de la version finale.

## 2026-11-04 : rectangles HGR par octets

Le noyau `hgr_fill_rect_asm` ajoute la colonne de départ à l'adresse de
ligne, sans retenue possible pour une zone visible, puis parcourt les
octets à rebours. Y sert d'offset et de compteur ; une largeur impaire
entre directement sur la seconde écriture. La boucle passe de **21 à
19 cycles par paire**, sans compteur X ni traitement de fin séparé.
Le noyau perd **7 octets de code** ; RAM, page zéro et pics de pile restent
identiques. Les paramètres d'entrée ne sont pas modifiés.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| 40 colonnes × 16 lignes, `$7F` | 7 824 | 7 186 | 1 567 | 1 560 |
| 39 colonnes × 16 lignes, `$D5` | 7 568 | 7 074 | 1 567 | 1 560 |
| Un octet à droite/en bas, `$80` | 407 | 406 | 1 565 | 1 558 |
| Rectangle découpé à droite/en bas, `$A5` | 523 | 514 | 1 567 | 1 560 |

Les grandes zones paires/impaires gagnent **8,2 % / 6,5 %**. Trois cas
s'ajoutent au banc, soit 142 mesures ; les autres charges restent
identiques. Seules les quatre références de remplissage sont recalées.

Le nouveau `test_hgr_byte_rects.py`, intégré aux cibles de test NMOS et
65C02, vérifie **2 204 remplissages par CPU** : les 820 couples valides
colonne/largeur, les 256 valeurs d'octet, les rectangles vides et invalides,
les débordements découpés, les deux pages, les bits de palette et les trous
mémoire. Le même oracle passe avec l'ancien et le nouveau noyau sur NMOS,
puis avec le nouveau sur 65C02. L'intégration HGR et les exemples minimaux
passent aussi.

`make all` réussit. Snake passe les niveaux, la cadence PAL/NTSC et les
sauvegardes ; LIGHT3DBALL termine ses cinq niveaux. Seuls leurs deux
disques et jumeaux WOZ changent pour cette passe. Les 18 WOZ sont conformes.
Le contrôle final passe les 142 cas et 16 budgets absolus, avec des mesures
identiques au premier passage complet.

## 2026-11-04 : alternance des banques du texte DHGR standard

Le noyau de `dhgr_puts` traite explicitement les octets auxiliaires et
principaux en alternance. Y garde la colonne écran, avancée après chaque
octet principal : plus de division par deux ni de compteur d'octets en
BSS à chaque écriture. La sortie d'une ligne fonctionne pour les cinq ou
six octets d'un glyphe, quelle que soit sa banque de départ.

Le compteur de lignes utilise `tmp2`, scratch cc65 conservé par la routine
de lecture auxiliaire. Le tampon de ligne passe de sept à six octets :
les quatre paires de pixels ne peuvent écrire au-delà de l'indice cinq.
Le noyau perd **10 octets de code et trois octets de BSS**, sans changer
la page zéro, les tables ou les pics de pile mesurés. Les interruptions
restent masquées une ligne à la fois ; RAMRD/RAMWRT redeviennent principaux.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| « APPLE II », x=0 | 44 259 | 37 376 | 2 871 | 2 861 |
| x=3 | 44 524 | 37 721 | 2 873 | 2 863 |
| x=6 | 43 856 | 37 196 | 2 873 | 2 863 |
| Huit espaces, x=0 | 44 259 | 37 376 | 2 871 | 2 861 |

Le gain est de **15,2..15,6 %**. Le client isolé utilise 336 octets de RAM.
Les trois nouveaux cas portent le banc à 145 mesures ; seules ces quatre
références changent, et les 16 budgets absolus sont conservés.

Le test du texte ajoute 238 captures complètes des deux pages et banques :
les 255 octets d'entrée non nuls, les chaînes vides, les sept phases et
les deux états du masque IRQ. L'oracle par pixel vérifie aussi les bits
de palette, les voisins et les trous mémoire. Il passe avec l'ancien et
le nouveau noyau, en complément des caractères minuscules et inconnus et
des arrêts aux bords droit/bas. Les 48 points de contrôle DHGR étendus
passent également.

`make all` réussit ; seuls `DHGR.dsk` et son jumeau WOZ changent. L'exemple
DHGR passe l'animation, la pause/reprise, les flèches et le retour DOS.
Le rendu rapide vérifie les sept décalages, les chevauchements, les retenues
décimales et la restauration du fond. Les 18 WOZ sont conformes. Le contrôle
final passe les 145 cas et 16 budgets, avec des mesures identiques au
premier passage de la version finale.

## 2026-11-04 : sentinelle de lecture des bitmaps HGR

Chaque octet source entre dans le registre de décalage avec une sentinelle
en bit zéro et le premier pixel dans la retenue. Les décalages suivants
fournissent les sept pixels restants ; le registre devient nul seulement
quand la sentinelle en sort. Cela supprime le compteur de huit bits et son
décrément à chaque pixel. Le dernier pixel de la ligne reste traité avant
toute recharge source.

L'indice d'octet source utilise le haut de `ptr2`, dont seul le bas sert
à accumuler les pixels à dessiner. Le noyau perd **6 octets de code et un
octet de page zéro**, sans changer la RAM ordinaire ni les pics de pile.
L'ordre de lecture des pixels et les opérations SET/CLEAR/XOR sont conservés.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| Bitmap mixte 16×8 SET, phase 0 | 6 591 | 5 935 | 1 945 | 1 939 |
| CLEAR, phase 3 | 6 728 | 6 072 | 1 943 | 1 937 |
| XOR, phase 6 | 6 884 | 6 228 | 1 945 | 1 939 |
| Bitmap vide | 5 576 | 4 920 | 1 945 | 1 939 |
| Bitmap plein | 7 248 | 6 592 | 1 945 | 1 939 |
| XOR découpé à droite/en bas | 1 249 | 1 207 | 1 945 | 1 939 |

Les neuf cas mixtes gagnent **9,4..10,0 %**, le vide **11,8 %**, le plein
**9,1 %**. La page zéro passe de 36 à 35 octets dans ces clients. Un cas
plein s'ajoute au banc, soit 146 mesures ; seules les douze références
bitmap changent, sans modification des budgets absolus.

Le test bitmap ajoute les 256 valeurs source dans une image de 16×128
pixels, répétée dans les sept phases, trois modes et deux pages. Les
**654 cas** passent avec l'ancien noyau sur NMOS et avec le nouveau sur
NMOS et 65C02. Ils couvrent aussi le découpage, le stride source complet,
les débuts/fins d'octet, les images vides/pleines, la palette et les trous
mémoire. L'intégration HGR et `make all` passent ; aucune image distribuée
ne change pour cette passe.
Le contrôle final passe les 146 cas et les 16 budgets absolus ; ses mesures
sont identiques au premier passage complet.

## 2026-11-04 : transferts de blocs DHGR et fusion des masques

La préparation de l'adresse est intégrée dans `block_setup`, supprimant
un appel imbriqué. L'avancement des pointeurs garde la banque dans A :
les incréments ne la modifient pas, et le EOR final sélectionne directement
l'autre banque. Les tests de banque qui n'ont pas de donnée dans A utilisent
TXA. L'écriture de blocs conserve CPX pour préserver l'octet source.

La fusion d'un masque partiel calcule `~(~screen | write_mask)` puis ajoute
les bits source, au lieu de sauvegarder/recharger l'écran et d'inverser le
masque. Les bits de palette sont conservés comme auparavant. Le noyau
commun perd **15 octets de code et deux octets au pic de pile matérielle**.
RAM, page zéro et pile C ne changent pas.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| Écriture 8×8 octets, banque auxiliaire au départ | 6 839 | 6 615 | 2 054 | 2 039 |
| Lecture 8×8 octets | 7 207 | 6 987 | 2 054 | 2 039 |
| Écriture 7×8 octets, banque principale au départ | 6 427 | 6 219 | 2 056 | 2 041 |
| Sprite 14×8 pixels couleur, masques partiels | 12 683 | 12 208 | 2 574 | 2 559 |
| Même sprite, masques opaques | 10 315 | 10 095 | 2 566 | 2 551 |
| Petit sprite existant | 2 314 | 2 271 | 2 494 | 2 479 |

Les blocs gagnent **3,1..3,3 %**, les masques partiels **3,7 %**. Quatre
cas portent le banc à 150 mesures ; seules les six références de cette
famille changent, sans modification des budgets absolus.

Le nouveau `test_dhgr_blocks.py` vérifie 640 transferts C et sprites natifs :
largeurs 1..80, les 256 masques, départ dans chaque banque, deux pages,
croisements de page des buffers, garde du tampon de lecture, bits de
palette et les deux masques IRQ. L'oracle passe avec les deux versions.
Les 48 points de contrôle DHGR étendus passent également.

`make all` et les tests rapides Robot Space Station passent sur IIe et IIc,
dont les mises à jour des salles et les écritures auxiliaires sous masque IRQ.
Seuls `ROBOTSTATION.po` et son jumeau WOZ changent pour cette passe ; les
18 images WOZ correspondent aux disques.
Le contrôle final passe les 150 cas et les 16 budgets absolus, avec des
mesures identiques au premier passage complet.

## 2026-11-04 : calcul du nombre de cellules du texte HGR doublé

Le wrapper C de `hgr_puts` calculait `(264-x)/18+1` par une boucle de
soustractions sur des variables de pile. Le helper fastcall indépendant
`hgr_text16_cells` utilise A/X, sans mémoire ni changement du masque IRQ.
Les valeurs 256..264 donnent directement quinze cellules ; les autres
utilisent une courte boucle native. Le wrapper conserve son contrôle de
l'origine avant l'appel. Les clients natifs du blitter ne lient pas ce
nouveau membre d'archive.

Le C compilé passe de 330 à 277 octets et le helper en prend 19. La
suppression des dépendances de pile et de soustraction du runtime porte
le gain des clients isolés à **71 octets de code et trois octets au pic de
pile C**. Les clients composites gagnent 55 octets chargés. RAM, page zéro
et pics de pile matérielle restent identiques.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| « APPLE II » blanc, phase 0 | 16 681 | 15 052 | 3 213 | 3 142 |
| Phase 3 | 16 914 | 15 305 | 3 217 | 3 146 |
| Orange, phase 0 | 16 606 | 15 125 | 3 246 | 3 175 |
| Origine x=9, sous la frontière d'espace de 256 pixels | 16 823 | 15 316 | 3 217 | 3 146 |
| Huit espaces | 5 420 | 3 894 | 3 213 | 3 142 |
| Chaîne vide | 2 153 | 627 | 3 205 | 3 134 |
| Ancien HUD sans cache, à chaud | 32 828 | 31 213 | 4 629 | 4 574 |

Le texte blanc gagne **9,5..9,8 %**, le texte orange **8,5..8,9 %**, les
espaces **28,2 %** et la chaîne vide **70,9 %**. Le blitter natif dense
et les autres familles gardent leurs mesures. Deux cas portent le banc
à 152 mesures ; 15 références sont recalées avec les mêmes budgets.

`test_hgr_text_cells.py` vérifie les 265 valeurs d'espace par un appel C
réel sur NMOS et 65C02, dont toutes les frontières de 18 et 256 pixels.
Les 280 scènes du texte doublé passent sur les deux CPU, ainsi que
l'intégration HGR, les configurations d'archive et les tests hôtes.
La suite `make test-hgr` a également passé l'ensemble des tests de la série
précédente avant cette dernière modification du wrapper.
`make all`, Snake, les cinq niveaux de LIGHT3DBALL et l'exemple HGR sur
II+/IIe passent. Seuls `SNAKE.dsk` et son jumeau WOZ changent pour cette
passe ; les 18 WOZ sont conformes. Le contrôle final passe les 152 cas et
16 budgets absolus, avec des mesures identiques au premier passage complet.

## 2026-11-04 : temporaires de l'affichage HGR signé

`hgr_puti` affecte directement le pointeur de conversion au tampon ou à
son deuxième caractère après le signe. Le paramètre valeur porte ensuite
les bits de la magnitude ; la négation reste non signée pour −32768.
Les variables locales `dst` et `mag` disparaissent. Le C compilé perd
27 octets ; les dépendances de runtime supprimées portent le gain des
clients isolés à **40 octets chargés et quatre octets au pic de pile C**.
RAM, page zéro et pile matérielle restent identiques.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| −32768 | 12 943 | 12 810 | 3 388 | 3 348 |
| −12345 | 12 456 | 12 318 | 3 392 | 3 352 |
| 32767 | 11 921 | 11 800 | 3 392 | 3 352 |

Le gain est de **1,0..1,1 %**. Les trois nouveaux cas portent le banc à
155 mesures ; les autres références sont identiques. La pile C mesurée
passe de 26 à 22 octets dans les trois cas.

Le nouveau `test_hgr_signed.py` compare 272 scènes par CPU à des chaînes
décimales et un oracle par pixel : zéro, signes, frontières décimales,
−32768/32767, alignements, découpage droit/bas, origines invalides et deux
pages. Il passe avec l'ancien C sur NMOS, puis avec le nouveau sur NMOS
et 65C02. L'intégration HGR et `make all` passent. Aucune image distribuée
ne change et les 18 WOZ sont conformes.
Le contrôle final passe les 155 cas et les 16 budgets absolus, avec des
mesures identiques au premier passage complet. Les suites complètes
`make test-hgr` et `make test-dhgr` de cette série sont également passées.

## 2026-11-04 : scratch et compteurs des sprites HGR masqués

Le produit de dimensions utilisé par les banques de phase réutilise
`tmp4` pour l'octet bas et `tmp3` pour le haut. La hauteur complète est
chargée dans X avant de réutiliser son scratch. Deux branches remplacent
des JMP dont la condition est connue ; le calcul de ligne omet l'ADC de
retenue impossible pour une colonne découpée et un offset HGR visible.

Les quatre boucles génériques parcourent les colonnes à rebours : Y est
l'offset et le compteur. Les chemins spécialisés de largeur deux/quatre
restent déroulés. Les coûts par octet deviennent 26 cycles pour dessiner,
16 pour copier et 32 pour sauvegarder/dessiner, contre 29/19/35.
Le noyau perd **8 octets de code et deux octets de page zéro**, sans
changer la RAM ordinaire ni les pics de pile.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| Dessin générique, 7 octets × 8 lignes | 3 051 | 2 885 | 1 690 | 1 682 |
| Sauvegarde | 1 951 | 1 791 | 1 690 | 1 682 |
| Restauration | 1 962 | 1 802 | 1 690 | 1 682 |
| Sauvegarde et dessin | 3 398 | 3 232 | 1 690 | 1 682 |
| Jeu compact, phase 1 (maximum) | 15 927 | 15 865 | 7 091 | 7 083 |
| Fond de huit tuiles et deux dessins | 6 782 | 6 704 | 3 670 | 3 662 |

Les cas génériques gagnent **4,9..8,2 %**. Leur comparaison remplace le
même membre dans une archive temporaire, dans le même ordre ; les mesures
finales sont identiques au banc complet. Le jeu compact prend désormais
15 602..15 865 cycles avec 47 octets de page zéro, soit 12 195/18 695
cycles de marge NTSC/PAL après réserve. La scène historique stationnaire
avec champ numérique sans cache prend 14 cycles de plus (+0,11 %) ; les
autres scènes affectées gagnent du temps ou gardent leur mesure.

Le test des quatre noyaux passe de 88 à 200 scènes : grandes strides,
hauteurs 128/255, produit traversant 255, toutes les phases, deux pages,
découpage et gardes du tampon de sauvegarde. Il passe avec les deux versions
sur NMOS et avec la nouvelle sur 65C02. Les couches sales, chaînes de
chevauchement, tuiles, exemples HGR/minimaux et l'intégration HGR passent.
Le jeu complet tient 1 000 images par standard et 2 000 IRQ musicales,
sans échéance manquée. Snake et les cinq niveaux de LIGHT3DBALL passent.

`make all` réussit ; seuls les disques HGR et LIGHT3DBALL et leurs jumeaux
WOZ changent pour cette passe. Les 18 WOZ sont conformes. Quatre cas
génériques portent le banc à 159 mesures ; 46 références sont recalées.
Le contrôle final passe les 159 cas et les 16 budgets absolus, avec des
mesures identiques au premier passage complet de la version finale.
Les campagnes et le fuzz Robot Space Station passent aussi sur IIe et IIc.

## 2026-11-04 : arithmétique des champs numériques HGR

`hgr_putu_field` utilise directement `width*18-2` pour effacer le champ.
La largeur est déjà bornée à quatorze cellules : ce résultat tient dans
un octet. Après l'effacement, le paramètre largeur porte le nombre de
cellules de padding pour l'alignement à droite. Le temporaire 16 bits
disparaît, ainsi que le calcul inutilisé quand le nombre déborde le champ.

Le C compilé passe de 296 à 246 octets. Selon les dépendances de runtime
déjà liées, les clients gagnent **33..50 octets chargés et deux octets au
pic de pile C**. RAM, page zéro et pile matérielle restent identiques.
Les règles de largeur nulle, saturation à 14, débordement numérique et
découpage sont conservées.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| Champ de 14 cellules, valeur 42 | 14 078 | 13 763 | 4 174 | 4 141 |
| Une cellule, valeur 65535 | 14 695 | 14 384 | 4 168 | 4 135 |
| Champ découpé à droite | 4 544 | 4 239 | 4 182 | 4 149 |
| Ancien HUD sans cache, à chaud | 31 213 | 30 539 | 4 574 | 4 541 |
| Ancienne scène chaude avec champ numérique | 13 286 | 12 975 | 7 177 | 7 127 |

Les champs ciblés gagnent **2,1..6,7 %**. Les trois nouveaux cas portent
le banc à 162 mesures ; neuf références sont recalées et toutes les autres
mesures restent identiques. Les limites des 16 budgets absolus ne changent pas.

Le nouveau test compare **1 144 scènes par CPU** à des chaînes décimales
et un oracle par pixel : toutes les largeurs 1..14, largeur nulle et
saturation, frontières décimales, débordement, padding au-delà du bord
droit, origines invalides, découpage, palette et trous mémoire sur les
deux pages. Le même oracle passe avec l'ancien C sur NMOS, puis avec le
nouveau sur NMOS et 65C02. L'intégration HGR et `make all` passent aussi.

Snake passe les niveaux, la croissance, les cadences PAL/NTSC et les
sauvegardes avec la version finale. Seuls `SNAKE.dsk` et son jumeau WOZ
changent pour cette passe ; les 18 images WOZ sont conformes. Le contrôle
final passe les 162 cas et les 16 budgets, avec des mesures identiques au
premier passage de la version finale.

## 2026-11-04 : construction du tampon du texte DHGR

Les quatre groupes de deux pixels produisent chacun un octet bas et un
octet haut. Chaque octet haut occupe une nouvelle case du tampon ; seul
l'octet bas peut chevaucher le haut du groupe précédent. Le premier groupe
écrit donc directement ses deux octets, puis les suivants fusionnent leur
bas et écrivent directement leur haut.

Aux phases 4..6, un groupe démarre deux octets après son prédécesseur.
Une table de sept octets indique la seule case à remettre à zéro avant
chaque ligne ; aux autres phases elle désigne une case non affichée.
Le zéro complet du tampon et cinq lectures/OR inutiles disparaissent.
L'indice de cette case utilise `tmp3`, scratch déjà disponible.

Le noyau perd **16 octets de code**, ajoute **7 octets de table immuable**,
soit **9 octets chargés en moins**. RAM, page zéro et pics de pile restent
identiques. Le masque IRQ par ligne et les restaurations de banques sont
conservés.

| Cas | Cycles avant | Cycles après | Binaire avant | Binaire après |
| --- | ---: | ---: | ---: | ---: |
| « APPLE II », x=0 | 37 376 | 32 246 | 2 861 | 2 852 |
| x=3 | 37 721 | 32 566 | 2 863 | 2 854 |
| x=6 | 37 196 | 32 042 | 2 863 | 2 854 |
| Huit espaces | 37 376 | 32 288 | 2 861 | 2 852 |

Cette passe gagne **13,6..13,9 %**. Les deux passes du texte DHGR standard
de la série donnent ensemble **27,1 %** sur le premier cas, avec 19 octets
chargés et trois de BSS en moins. Seules les quatre références du texte
standard changent ; les autres mesures sont identiques.

Les 238 captures natives vérifient les 255 octets d'entrée non nuls, les
chaînes vides, tous les glyphes intégrés, sept phases, les deux pages et
banques et les deux masques IRQ. Les 48 points DHGR étendus passent aussi.
La géométrie des groupes est vérifiée séparément sur les **1 792 couples
phase/octet source**, en partant d'un tampon non nul et en comparant aux
32 points attendus : aucune case affichée ne dépend d'un ancien contenu.

`make all` réussit ; seuls `DHGR.dsk` et son jumeau WOZ changent pour cette
passe. Les 18 WOZ sont conformes. Le contrôle final passe les **162 cas et
16 budgets absolus**, avec des résultats identiques au premier passage.
Les suites complètes `make test-hgr` puis `make test-dhgr` passent également
en fin de série, ainsi que `git diff --check`.
Avant publication, un checkout isolé avec le SDK versionné reproduit les
162 mesures à l'identique et passe les 16 budgets ainsi que le test DHGR
du texte. Les métadonnées d'environnement du banc utilisent ce SDK.
