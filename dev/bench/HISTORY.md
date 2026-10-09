# Historique des mesures

Ces chiffres décrivent les versions successives, pas tous la version actuelle.
Les résultats actuels et leur protocole sont dans [README.md](README.md) ;
`baseline.json` conserve les références utilisées par le gate.

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
