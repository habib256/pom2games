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
cc65 compris : CODE + STARTUP, RODATA, RAM (BSS/LOWBSS/DATA/ZPSAVE), ZEROPAGE
et fichier binaire. La pile C réservée et les pages vidéo ne sont pas comptées
comme BSS ; la RAM affichée ne représente donc pas toute la mémoire occupée.
La ligne compiler et les options sont enregistrées dans le JSON.

`baseline.json` conserve les mesures de référence. Une hausse des cycles de
plus de 5 % (minimum 16), des tailles de plus de 3 % (minimum 16 octets), ou
une hausse de ZP fait échouer `--check`. Un compilateur différent peut changer
ces résultats ; le rapport en conserve la version pour faciliter le diagnostic.
Le gate DHGR reste local car le SDK a2shot fourni est macOS arm64.

Après examen d’une modification intentionnelle :

```sh
python3 dev/bench/run.py --dhgr --update
```

Cette commande remplace les références des cas mesurés. Une exécution normale
ou `--check` ne modifie jamais la référence.

Cas actuels : clear, segment pleine largeur, rectangle, texte, sprite HGR ;
clear, segment, rectangle, transfert de bloc, sprite masqué et texte DHGR.
Les résultats sont reproductibles pour un même compilateur et cœur CPU.

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
