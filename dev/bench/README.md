# Mesures cc65

```sh
make bench             # HGR, a2run portable
make bench-dhgr         # HGR + DHGR, a2shot IIe requis
make bench-check       # Budgets HGR, exécutés aussi dans make test / CI
python3 dev/bench/run.py --dhgr --check
python3 dev/bench/run.py --dhgr --out /tmp/apple2-metrics.json
```

Le script construit une archive, puis un petit programme par opération avec
`-Oirs`. Il démarre DOS et s’arrête sur deux marqueurs d’instruction : les cycles
mesurés comprennent les arguments et l’appel C, excluent l’initialisation et
les 12 cycles des deux appels de marqueur. HGR initialise ses tables avant
la mesure. HGR utilise un NMOS 6502 dans a2run ; DHGR un 65C02 dans a2shot.
Les adresses viennent du fichier de labels ld65, sans estimation de timing.

Les tailles sont celles du programme de mesure complet, CRT et bibliothèque
cc65 compris : CODE + STARTUP + LOWCODE + INIT + ONCE, RODATA, RAM (BSS/LOWBSS/DATA/ZPSAVE), ZEROPAGE
et fichier binaire. La pile C réservée et les pages vidéo ne sont pas comptées
comme BSS ; la RAM affichée ne représente donc pas toute la mémoire occupée.
Le compilateur, les options, le CPU, le modèle et les SHA256 du runner,
du cœur et des ROM sont enregistrés dans le JSON. Le gate vérifie le modèle,
le cœur CPU et la ROM ; les binaires hôtes peuvent différer entre Linux/macOS.

`baseline.json` conserve les mesures de référence. Une hausse des cycles de
plus de 5 % (minimum 16), des tailles de plus de 3 % (minimum 16 octets), ou
une hausse de ZP fait échouer `--check`. Un compilateur différent peut changer
ces résultats ; le rapport en conserve la version pour faciliter le diagnostic.
Le gate DHGR fonctionne localement et dans le job CI macOS ARM64 ;
le SDK a2shot fourni exige cette architecture. Le gate HGR reste portable.

Après examen d’une modification intentionnelle :

```sh
python3 dev/bench/run.py --dhgr --update
```

Cette commande remplace les références des cas mesurés. Une exécution normale
ou `--check` ne modifie jamais la référence.

Cas actuels : clear, segment pleine largeur, rectangle, texte, sprite HGR ;
clear, segment, rectangle, transfert de bloc, sprite masqué et texte DHGR.
Les cas supplémentaires couvrent une diagonale HGR complète et l'effacement
DHGR d'une ligne visible. Les mesures HGR préparent désormais chaque primitive
par un appel avant les marqueurs : seules ses tables nécessaires sont liées et
l'initialisation paresseuse n'est pas incluse dans le temps mesuré. Les mesures
historiques de performance sont conservées ; les deux nouveaux cas ont leurs
propres références.
Les résultats sont reproductibles pour un même compilateur et cœur CPU.

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
