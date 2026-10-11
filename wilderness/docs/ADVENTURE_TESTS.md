# Comparaison des aventures avec l'original

La parité d'une aventure complète n'est **pas validée**. La nouvelle suite
compare quatre séquences de commandes dans les deux jeux Apple II ; toutes
échouent encore lorsque la météo est incluse. Les tests du port contre un
modèle Python ne suffisent pas à établir cette parité.

## Exécution

Depuis `wilderness/`, avec les disques originaux déjà extraits localement :

```sh
make test
make test-original
python3 tests/test_adventure.py --scenario overnight
```

Les prérequis sont `build/SIERRA.woz`, `build/JOURNEY.dsk`,
`build/files/TOPO.B`, les modules du port et a2shot. `make extract` prépare
les données originales ; elles restent hors git. Un prérequis absent,
une question inattendue, un délai dépassé ou une différence fait échouer
la commande. Aucun scénario en erreur n'est présenté comme réussi.

## Méthode et preuves

L'original démarre depuis Sierra, puis utilise Journey sur une copie privée.
Le port démarre avec une carte convertie depuis le même TOPO. Une commande
est envoyée à chacun, puis le pilote attend l'invite ou une question,
inspecte l'écran et fournit sa réponse. Les questions de conteneur de
l'original sont des touches seules ; les quantités et durées se terminent
par RETURN. Le port sélectionne actuellement certains conteneurs implicitement :
cette différence d'interface est consignée dans les événements du rapport.
Le pilote ne force ni position, ni santé, ni équipement dans la RAM du jeu.

Chaque étape conserve mémoire, capture d'écran et état normalisé. On compare
heure, date, temps écoulé, santé, température corporelle, frissons/sueur,
compteurs de boisson/repas/repos, déficits, énergie, position, direction,
objets et stocks, air, vent, ressenti et intérieur/extérieur. Les flottants
ont une tolérance de 0,000002 ; la direction admet une demi-unité du port
(560 azimuts contre 360 degrés). Les autres différences sont rapportées.

L'original réutilise `$4000-$4FFF` comme seconde page HGR après avoir
sauvegardé l'état sur Journey T04. Le pilote observe `$103E` avant cette
pagination et restaure ce bloc **dans l'observation Python**, jamais dans
le jeu. La provenance de chaque état et les dumps bruts paginés sont conservés.
Voir [ENGINE.md](logic/ENGINE.md).

`build/adventure/` contient `index.json`, puis par scénario `report.json`,
`labels.json`, `manifest.json`, journaux et fichiers `original-*.bin/.png`
et `port-*.bin/.png`. Les symboles et empreintes SHA-256 permettent de relire
les observations après une recompilation. La suite utilise un seul disque
du port figé pour ses quatre scénarios. Ne pas recompiler pendant les tests.

## Scénarios et résultat actuel

Le départ commun utilise la boussole, porte la parka, boit 10 oz à la gourde,
mange 8 oz de fromage depuis le sac puis se repose une heure.

| Scénario | Suite | Points observés | Résultat |
|---|---|---:|---|
| `opening` | Départ commun | 5 | Air et survie identiques ; 5 écarts de vent/ressenti |
| `camp` | Boisson, repas, REST 3, boisson, repas, REST 6 | 11 | Air et survie identiques ; 11 écarts de vent/ressenti |
| `overnight` | REST 6, boisson, repas, REST 8 | 9 | Air et survie identiques ; 11 écarts de vent/ressenti |
| `travel` | LOOK E, WALK 1, boisson, repas | 9 | 203 écarts : boussole, marche, énergie, météo et représentation des stocks |

Ces mesures sont celles de `build/comparison-medical-20261011/`.
Le pilote reconnaît l'acquittement natif « YOUR TRAVEL TIME WAS … MINUTES » ;
les quatre scénarios sont terminés, mais restent différents.

Les corrections vérifiées portent sur DRINK sans temps, EAT en 16 minutes,
crédits d'eau/nourriture/repos, cadence différée des compteurs, repos
adaptatif, frissons initiaux, santé en pourcentages entiers et absence de
tirages de rencontres pendant REST/EAT. LOOK ajoute désormais la déclinaison
magnétique ; l'original ajoute aussi une erreur aléatoire de boussole.

## Ce qui empêche encore une validation complète

Les écarts de vent et de ressenti restent à résoudre dans les aventures.
L'onde lente `INT(5 × SIN(0,0187 × heures écoulées + phase))` est désormais
portée avec la phase initiale Sierra. `test_temperature_wave.py --original`
compare 405 cas à la routine T09/S08 sur ROM. Cette correction fait concorder
l'air au départ. Les trois segments quotidiens et 288 températures horaires
passent désormais les comparaisons ROM, ainsi que les fronts, 56 états
aléatoires, 112 évolutions bornées du vent et 24 fréquences Sierra. Ces tests isolés
ne certifient pas encore la chaîne complète du vent dans une partie.
Le pas de santé intègre les fronts et les conditions médicales récentes,
avec 80 cas de cadence comparés au moteur original. Les risques thermiques
complémentaires restent à porter. La marche du port conserve sa règle
reconstruite de 19 minutes par case avec surcoût de montée ; l'original
utilise des pas et arrêts dépendant de la santé, charge et terrain.

La nage fait aussi partie de la validation à terminer. Son métabolisme est
désormais corrigé et comparé séparément sur la ROM :
`python3 tests/test_swim_energy.py --original` vérifie 81 valeurs d'effort
identiques octet par octet, plus les calories avec et sans frissons.
`test_wet.py` vérifie SWIM, refroidissement, matériel transporté, repos dans
l'eau et sortie sur terre. `test_swim_cadence.py --original` compare 143 durées
à la préparation et au pas originaux : demi-cases, santé, charge et diagonales.
La commande réelle vérifie aussi qu'un dernier pas peut dépasser le temps
demandé. `test_swim_raster.py --original` compare 2 880 positions sur les
360 caps, préparés puis avancés par les routines originales. Les modificateurs
de blessures/équipement et la cadence de recalcul de charge restent à porter ; ces tests isolés ne
constituent pas une traversée identique dans une aventure native.

Le rapport brut des stocks distingue mal deux représentations : l'original
retire les objets au sol inaccessibles de ses tables courantes, alors que
le port conserve leur réserve avec des coordonnées. Il faut comparer aussi
l'inventaire accessible et le retour au lieu de dépôt avant de conclure
à une perte d'objets. Ces écarts restent visibles, sans exclusion silencieuse.

La conversion de TOPO réduit des blocs 2 × 2 (112 × 84 contre 224 × 168).
Elle conserve désormais l'eau aux coordonnées impaires, à sa hauteur,
mais élargit les cours d'eau fins. La cabane est placée par la règle du port
et le relief sec des cellules impaires est perdu. Les images et le trajet ne sont donc pas
identiques. Aucun des quatre scénarios ne rejoint les rangers, ne teste une
attaque avec soins, ni une reprise de sauvegarde. Les prochaines étapes
sont suivies en priorité dans [TODO.md](../TODO.md).
