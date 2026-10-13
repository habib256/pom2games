# Sites et abris

Cette page sépare les branches observées de l'original des choix actuels du
port. L'interface et la mémoire sont décrites dans
[IMPLEMENTATION.md](../IMPLEMENTATION.md#sites-sprites-et-rencontres).

## Entrer et sortir dans l'original

Le vocabulaire utilise ENTER (40), EXIT/LEAVE (39), SHELTER (137) et HUT (95).
CABIN n'est pas reconnu. HUT appartient aux objets fabriqués ; SHELTER désigne
un abri trouvé. Les commandes passent par Journey T$12/S$08, six secteurs,
chargé en `$5800`.

- ENTER SHELTER à `$5C7E` vérifie `$4BA1` (abri présent) et `$0D5E`
  (intérieur). Sans abri : message 17. Déjà dedans : message 11. Sinon,
  `$0D5E` devient 1 et le message 10 confirme l'action.
- EXIT SHELTER à `$5BC7` vérifie la présence, puis `$5BF1` remet `$0D5E`
  à zéro si nécessaire. Déjà dehors : message 11 ; sortie réussie : 10.
- Ces branches ne passent pas par la chaîne d'avancement du temps.

`tools/re_site_probe.py` exécute ces branches sur ROM avec six combinaisons
présence/intérieur/commande. Seul le point d'affichage `$4D21` est remplacé
par une capture du numéro du message. Les résultats restent dans
`build/re_sites/results.json` ; aucun octet original n'entre dans les sources.

## Température effective

Dans `m0B2`, `$5948` commence par le ressenti `$4B9D`. L'immersion a priorité
sur les abris. Sur terre, `$5972-$5984` vérifie `$0D5E` :

- dehors : le ressenti du vent est conservé ;
- sous un abri ordinaire : `$4B9B` (air ambiant) +15 °F ;
- avec l'indicateur d'igloo `$45F1` non nul : 35 °F.

Le feu est un ajustement distinct après `$5986`. La sonde arrête la branche
avant ce calcul et teste douze combinaisons air/intérieur/igloo : −20, 0, 42
et 100 °F, avec un ressenti extérieur fixé à air −20. Elle confirme que
l'abri ordinaire utilise l'air ambiant et supprime le vent.

## Port actuel et travaux restants

La cabane générée à une case sèche fournit l'abri trouvé. Le port conserve
un seul octet résident `shelter_inside` ; les nouvelles actions et TOPO sont
dans WILDSIT, un module DOS de 2 Ko. Les transitions vers le rendu extérieur
sont des sauts terminaux, puisque celui-ci peut charger un autre module.

Le repos conserve l'intérieur et ne déclenche pas de faune extérieure.
La marche et la nage demandent de sortir d'abord : c'est une règle explicite
du port, pas une reconstruction des déplacements originaux sous abri.
La température effective reste signée sur 16 bits pour éviter le retour
à une valeur négative quand air +15 dépasse 127 °F.

`test_sites.py` trouve la cabane sur une carte de contrôle, s'y rend par
WALK, entre, se repose, sort et revient sans changer la position en mémoire.
Il contrôle le froid intérieur/extérieur, les refus, les rotations, les
écrans et la nuit. Les formules scalaires sont vérifiées aux limites signées.

TOPO est pour l'instant une carte textuelle de cellules, avec relief, eau,
repères et défilement. L'épave et la cabane se projettent aussi dans la vue
depuis les cases voisines, avec occlusion par le relief proche et une taille
par paliers ; cette projection est une règle du port, contrôlée par
`test_projection.py`. Un seul site est affiché par vue, à moins de huit cases.
Restent le tracé original des courbes, les scènes avec plusieurs sites, les
abris fabriqués (HUT/IGLOO/TRENCH) et le feu.
