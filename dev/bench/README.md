# Mesures actuelles cc65

```sh
make bench
make bench-dhgr
make bench-check
python3 dev/bench/run.py --dhgr --check
python3 dev/bench/run.py --dhgr --out /tmp/apple2-metrics.json
make test-dhgr
```

Le script compile un programme par charge avec `-Oirs`, démarre DOS et mesure
entre deux marqueurs d'instruction. Les cycles incluent les arguments et appels
C, excluent l'initialisation et les 12 cycles des marqueurs. Les cas froids
incluent les tables paresseuses ; les cas chauds préparent les deux historiques.
HGR utilise a2run NMOS 6502 ; les variantes IIe utilisent le SDK POM2 65C02.
Les anciennes mesures sont regroupées dans [HISTORY.md](HISTORY.md).

## Cadence et budgets absolus

La cible est deux rafraîchissements par présentation : nominalement 30 FPS
NTSC et 25 FPS PAL. Le faisceau SDK mesure 17 030/20 280 cycles par refresh,
contrôlés par les fronts VBL. Les profils natifs POM2 ont des unités différentes
(17 045/20 313) : elles ne sont pas mélangées dans ces budgets.

`budgets.json` fixe une limite indépendante des régressions : deux périodes,
moins **6 000 cycles réservés** à davantage de logique, au son et aux IRQ.
`--check` échoue si la charge dépasse cette limite, même après un recalage de
baseline. La réservation est une enveloppe choisie, pas une mesure de toute
logique ou musique possible. Le rapport fournit limite, coût et marge.

| Charge actuelle | Cycles |
|---|---:|
| HUD 16×16, valeur inchangée | 312 |
| HUD 16×16, un chiffre changé | 4 739 |
| HUD 16×16, cinq chiffres changés, maximum de sept phases | 22 235 |
| HUD 8×8, valeur inchangée | 312 |
| HUD 8×8, cinq chiffres changés, maximum de sept phases | 7 850 |
| Jeu compact : deux sprites 7×8 mobiles, trois chiffres tous changés, clavier, positions, présentation | 16 774..17 040 |
| Quatre sprites 21×16 isolés, seul le premier mobile, moteur par défaut | 31 031 |
| Même scène, option `HGR_SPR_DAMAGE=1` | 14 662 |
| Stress : quatre sprites 21×16 tous mobiles + compteur + présentation | 39 217 |

Le jeu compact est mesuré dans les sept alignements, en NTSC et PAL. Les
limites après réservation sont **28 060/34 560 cycles** ; sa pire phase laisse
encore 11 020/17 520 cycles au-delà de la réservation. Les positions et valeurs
utilisent une période de trois pour que chaque page retrouve un état modifié.
La valeur HUD n'alterne pas seulement avec la page : ses trois chiffres changent
réellement dans le cas mesuré. Le modulo commun aux déplacements et au score
est calculé une fois par frame.

La scène isolée économise 52,8 % avec le calcul assembleur des intersections :
437 octets chargés et 43 octets BSS supplémentaires à huit slots. L'option
reste désactivée par défaut. Quatre grands sprites tous mobiles coûtent encore
39 217 cycles : ils dépassent deux périodes NTSC et la limite PAL après réserve.
Les stress surchargés restent des diagnostics.

Le compteur natif utilise les chiffres en cache pour +1/+2 ; le passage
9999 → 10000 coûte 7 109 cycles en HUD 8×8. Ses chiffres prédécalés prennent
1 386 octets de RODATA, partagés entre champs. Un client HUD seul évite les
LUT mutables de lignes/colonnes et la police générale ; un client qui affiche
également du texte paie les deux banques. Le jeu compact passe ainsi de
6 895 à 7 231 octets chargés et de 1 571 à 1 620 octets RAM, sans hausse ZP.

Le backend tilemap optionnel restaure huit tuiles 7×8 puis dessine deux sprites
masqués sans save-under en 9 546 cycles. La carte fait 960 octets, fournie par
l'application ; une reconstruction complète n'est pas présentée comme une
charge à 30 FPS. Les profils de région conservent la réserve de 6 000 cycles.

`test_cadence.py` teste 1 000 présentations par standard avec une IRQ VIA
alignée sur le VBL, une charge variable et deux dépassements volontaires :
deux ticks par frame normale, échéance sautée sur surcharge, aucun rattrapage
en rafale. Il vérifie aussi le VBL au flip, le wrap, les arguments invalides,
l'arrêt de l'horloge et I. L'application doit fournir la source IRQ ; la
bibliothèque n'installe ni carte ni vecteur.

`test_game_cadence.py` exécute aussi un jeu complet : quatre sprites mobiles,
collisions, clavier, HUD et musique AY sous IRQ, 1 000 images par standard.
Il vérifie 2 000 ticks musicaux, zéro échéance manquée, le flip VBL, les deux
piles et le wrap : 33 969..34 151 / 40 468..40 647 cycles entre présentations.
Les tables et historiques sont préparés avant le démarrage de l'horloge.
La cadence teste aussi seize suspensions longues : 10 000/32 760 ticks,
périodes 1..8. La division ASM en 16 étapes évite le faux timeout du rattrapage.

L'exemple minimal double tampon n'exige pas de carte : il répartit son dessin
et son HUD 8×8 sur deux phases VBL. Ses 1 000 images NTSC/PAL couvrent le
compteur 65535 → 0, avec **34 050..34 070 / 40 550..40 570 cycles** par image,
sans refresh manqué. Ce résultat est propre à cette charge sur POM2 IIe ; le
repli temporisé II/II+/IIc ajoute le rendu à son attente.

## Mémoire et piles

Les tailles couvrent le programme de mesure entier : CRT, runtime cc65,
CODE/STARTUP/LOWCODE/INIT/ONCE, RODATA, BSS/LOWBSS/DATA/ZPSAVE, ZP et binaire.
Code + données chargées sont confrontés à la taille réelle du binaire.
Les pages vidéo et la pile C réservée sont séparées de BSS.

Les compteurs C observent le pointeur cc65 aux frontières cohérentes d'appel,
retour, saut et accès `(sp),Y` ; a2run observe aussi les écritures de pile.
`hwstackwatch` suit S instruction par instruction ; la profondeur matérielle
inclut l'occupation initiale et les IRQ de la fenêtre. `hwstack` rapporte le
maximum `255-S` et un débordement sur passage sous zéro. Les sondes vérifient
37 poussées et un débordement volontaire sur les deux runners. Ces observations
couvrent les chemins exécutés, sans constituer une analyse statique universelle.
Le profilage n'ajoute aucun cycle CPU émulé.

## Références et reproductibilité

`baseline.json` conserve compilateur, flags, CPU, modèle, période du faisceau
et SHA256 des runners, cœurs et ROM. `--check` refuse une hausse des cycles
supérieure à 5 % (minimum 16), des tailles supérieure à 3 % (minimum 16 octets)
ou toute hausse ZP. Le gate vérifie cœur/ROM/modèle ; les binaires hôtes peuvent
varier entre systèmes. Les budgets absolus restent contrôlés indépendamment.
Les références historiques, `pre_incremental_references` et `pre_native_references` restent conservées. Les plafonds des primitives indépendantes ne sont pas recalés.

Après examen d'une modification intentionnelle :

```sh
python3 dev/bench/run.py --dhgr --update
```

Cela remplace les références des cas mesurés. Une exécution normale ou `--check`
ne les modifie pas. Le SDK fourni exige macOS ARM64 ; les cas HGR a2run restent
portables. L'évaluation des techniques alternatives est séparée dans
[tests/techniques](../tests/techniques/README.md), via `make test-techniques`.
