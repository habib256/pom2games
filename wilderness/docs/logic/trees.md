# Arbres : grimper, suspendre et récupérer le sac

## Preuves originales

Le résident `$5156–$51A4` traite CLIMB, nom TREE (173) ou DOWN (150).
Si `$4B40` est déjà non nul, TREE et DOWN le remettent à zéro, sans
recontrôler la santé ni l’environnement. Pour monter, `$D7` doit signaler
un arbre proche et la santé `$4C34` doit être strictement supérieure au
flottant 2,5 en `$570C`. Les refus sont les messages 16 et 59 ; la réussite
est le message 10. Le code ne lance pas l’horloge.
T08/S00 `$585B` refuse le déplacement lorsque `$4B40` est non nul (message 97).
Le rendu SURV3D ne consulte pas ce drapeau : grimper ne modifie pas la caméra.

T15/S0A route HANG FOOD vers T12/S08. L’entrée `$58F9` vérifie l’arbre,
puis `$594E` annonce la suspension du sac et de son contenu (message 111).
B1(21) négatif refuse l’action (message 193). Un sac au sol est accepté.
Le code choisit le sac (nom 21), DROP (verbe 8), 30 minutes en `$4BC6`,
marque `$4B4E=1` et entre dans la transaction d’horloge `$4D00`.
Le helper `$5D68` calcule le taux `$4C20` : taux au repos + poids corporel
entier `$4C02` × constante `$5CBE` (0,02). Ce coefficient n’est pas celui
d’un repas. GET BACKPACK dans le module `m0EA` efface `$4B4E`.

`python3 tools/re_tree_probe.py` exécute ces routines originales sur ROM
avec les seules sorties de message et d’horloge remplacées par des captures :
24 cas CLIMB TREE/DOWN (santé, proximité, montée/descente), puis 16 cas
HANG FOOD (proximité, sac absent/au sol/porté, deux poids). Les binaires
originaux et les disques de sonde restent dans `build/`, ignoré par Git.
Les cas HANG contrôlent l’état et le taux avant la transaction DROP/horloge ;
ils ne prouvent pas l’identité de toute une aventure ni des réactions animales.

## Adaptation au port

`tree.s`, module `WILDTRE` en `$5800`, contient les commandes et la rotation
LOOK. Seuls `tree_in` et le placement antérieur du sac restent résidents.
Un arbre est accessible sur la case boisée sèche sous la limite forestière,
hors cabane. La couverture forestière existante fournit cette proximité ;
elle ne distingue pas les troncs individuels à l’intérieur d’une case.
ENTER SHELTER exige de descendre de l'arbre avant d'entrer dans la cabane.

Le placement 5 (`HUNG`) représente le sac suspendu et chaque élément rangé
dans le sac. Les coordonnées du sac ancrent l’ensemble à la case courante.
Les stocks emballés et les stocks au sol restent distincts : suspendre ne
fusionne ni ne déplace une pile de nourriture au sol. L’eau suit la gourde :
une gourde en main reste utilisable, une gourde dans le sac est suspendue.
Le contenu suspendu est exclu du poids, du volume porté et des quantités
accessibles. DROP/GET/PACK/WEAR ne permettent pas de retirer un élément
suspendu ; une pile indépendante au sol reste consommable.

GET BACKPACK récupère l’ensemble à sa case. LOWER FOOD/BACKPACK et
HANG BACKPACK sont des alias ajoutés au port ; leur syntaxe n’est pas
présentée comme une comparaison complète des branches natives LOWER.
La récupération ne consomme pas de temps dans le port. Elle restaure le
placement antérieur du sac (ou le prend en main s’il était au sol), puis
vérifie les quatre capacités et les débordements. En cas de refus, tous
les placements et les totaux reviennent à leur état précédent. Les quantités
ne changent pas. Le sac peut rester suspendu pendant un déplacement et être
récupéré au retour. Suspendre à nouveau un sac déjà suspendu est refusé.

INVENTORY ajoute `5 HUNG` / `HUNG HERE`, visible seulement à la case du sac.
STATUS exclut les provisions suspendues des totaux transportés et accessibles,
et affiche `IN A TREE` / `BACKPACK HUNG`. Le résumé suggère CLIMB DOWN.
`tests/test_tree.py` couvre les seuils, le temps et le taux, les stocks,
les refus de déplacement, les conteneurs, la récupération et les écrans.
Les vols de nourriture et les réactions de l’ours restent à porter.
