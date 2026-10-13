# Réactions animales : preuves originales et adaptations

Les modules Journey T0F/S07 (commandes) et T06/S04 (réactions) sont chargés
à $5800. Les paramètres Sierra viennent des lignes de 32 octets de TOPO
à $6000, $6020 et $6040. `$4D1E` fournit la ligne de l’espèce.

`tools/re_animal_reactions_probe.py` extrait ces modules localement, conserve
leurs calculs et l’accès aux tables, puis les exécute sur la ROM Apple II+.
Il remplace seulement l’affichage `$4D2A` par RTS et arrête avant RND pour
lire le seuil calculé. Ses 45 cas vérifient les seuils ; trois autres exécutent la sélection d’arme
(hache seule, couteau seul, les deux). Vingt cas supplémentaires exécutent le calcul de gravité `$5C82-$5D21`
avec RND imposé, avant activation des conditions. Ils ne vérifient pas toute la transaction
native ni une aventure complète. Douze autres cas observent le relais
horloge/réactions `$4D56` : après la première phase, une présence `$4B72`
charge T06/S04 pour une durée de 1, 5 ou 60 minutes. Le relais charge
sinon T09/S05. Les chargements suivants sont arrêtés ; cette sonde ne prouve
pas la cadence complète d’une activité longue et le délai de 60 minutes
du port reste une adaptation. Résultats dans `build/re_animal_reactions/`.
Aucun octet d’image disque ou de sprite original n’est ajouté aux sources.

## Seuils mesurés

Contexte extérieur ordinaire `$0D5D=0`, `$0D5E=0`. Un RND supérieur au seuil
échoue ; l’égalité réussit. Les probabilités du port sont quantifiées sur
256 valeurs avec un LFSR ; les séquences aléatoires ne sont pas celles de la ROM.

| Action / seuil | Ours | Couguar | Crotale |
|---|---:|---:|---:|
| Bruit : `.8 - .03 × ligne[14]`, T0F/S07 `$586E` | 50 % | 50 % | -10 % (impossible) |
| Blessure après bruit raté : `.02 × ligne[14]` | 20 % | 20 % | 60 % |
| Blessure IGNORE : `.02 × ligne[15]` | 4 % | 4 % | 6 % |
| Blessure dans l’arbre : `.02 × ligne[16]` | 4 % | 4 % | 6 % |
| Blessure attente/repos/repas au sol : `.02 × ligne[13]` | 2 % | 2 % | 4 % |
| Blessure avec hache/couteau : `.02 × ligne[18]` | 70 % | 50 % | 40 % |
| Réussite hache/couteau : `.005 × ligne[24]` | 1,5 % | 5 % | 15 % |

T06/S04 `$589A-$58CF` calcule le risque de blessure, puis `$593A-$5974`
calcule séparément la réussite. Une blessure n’interdit donc pas une réussite.
Le bruit raté fixe le moyen 14 ; le module saute ensuite la tentative de
chasse (`$5931-$5937`). Le port conserve cette séparation des tirages. T0F/S07 `$590F-$593D`
regroupe AXE/KNIFE dans le moyen 18 ; les moyens 19 et 20 correspondent
à SPEAR et BOW, pas à une différence entre hache et couteau.

Le vol est autorisé seulement si `ligne[28]` est non nulle : ours/couguar,
pas crotale. `$5A94-$5AD4` donne 5 % en extérieur, 1 % avec `$4B4E`
(sac suspendu), 10 % avec `$4B46` (posture dans l’arbre sans sac suspendu).
`$5AE6-$5C67` parcourt les provisions et signale le vol.

## Posture et protection mesurées

T06/S04 `$584A-$5864` sélectionne le moyen 16 dans l’arbre (`$4B40`),
sinon le moyen 13 pour une commande inférieure à 22, ou 15 à partir de 22.
Les commandes WAIT/REST/EAT/DRINK du port utilisent ces mêmes codes ; IGNORE
vaut 37. Les lignes 15 et 16 coïncident en Sierra : grimper ne met pas hors
de portée des animaux. Les 24 cas de posture exécutent cette sélection sur
ROM pour les trois espèces, REST/IGNORE, arbre/sol et abri natif actif/inactif.
L’abri natif `$0D5E` multiplie le risque de blessure par 0,1 (`$5866-$5888`) ;
la protection absolue de la cabane du port reste une adaptation.

## Gravité mesurée

T06/S04 `$5CEF-$5D21` calcule `INT(1 + 5 × RND^ligne[22])` : exposant
1 pour l’ours, 2 pour le couguar. Les quatre premiers résultats désignent
coupures, bras cassé, jambe cassée et choc. Le cinquième passe par une branche
supplémentaire `$5D25-$5D50`, qui modifie aussi une durée ; ses suites ne sont
pas encore reproduites. Les sondes conservent l’arithmétique ROM, y compris
la puissance, et contrôlent les résultats des deux espèces.

Le port quantifie les limites sur 256 valeurs : 52/103/154 pour l’ours,
115/162/199 pour le couguar. Les deux résultats supérieurs deviennent un choc
avec les courbes et soins existants. Le couguar provoque ainsi plus souvent
une coupure que l’ours. La gravité est tirée après les deux décisions de combat
pour ne pas altérer leur indépendance. Une blessure déjà active conserve son
ancienneté et ses soins ; une nouvelle blessure efface un ancien état traité
et impose le recalcul de santé pendant la transaction.

## Adaptations explicites

- Le port reprend le risque extérieur 5 %, ou 10 % dans l’arbre. Il protège
  directement chaque stock suspendu au lieu de réduire globalement le risque
  à 1 %. Les stocks au sol accessibles restent exposés ; piles éloignées,
  eau et équipement sont conservés. Totaux 16 bits et charge restent cohérents.
- IGNORE évalue blessures et vol, puis un départ conditionnel : ours 50 %,
  couguar 25 %, crotale 75 %. Ces probabilités de départ sont des choix du port,
  pas une règle prouvée de l’original. L’animal peut rester après une décision.
- Sans décision, une réaction est évaluée à 60 minutes ; ce délai reste provisoire.
  Une décision réinitialise l’âge. Les animaux restent à leur case et disparaissent
  si le joueur quitte cette case. Les déplacements natifs manquent.
- Les blessures utilisent coupures, bras/jambe cassés et choc (conditions 1–4),
  ou morsure empoisonnée (condition 8), avec courbes et soins existants.
  La branche native du cinquième degré et la durée variable des morsures
  restent à porter.
- ATTACK exige hache/couteau accessible. Une réussite est interprétée comme
  défense et départ, alors que l’original peut tuer et créer des provisions.
  Chasse, carcasse, autres armes, feu, mode recherche et autres régions manquent.
- Les animaux peuvent blesser le joueur dans un arbre, comme dans la
  sélection native du moyen 16. CLIMB TREE l’annonce. La cabane empêche
  encore blessures et vol ; cette protection absolue reste une adaptation.
  SCARE/ATTACK exigent de descendre ou sortir, sans temps dépensé lors du refus.
- Le LFSR avance sept fois par tirage de réaction pour permettre les quatre
  combinaisons blessure/réussite. Il partage l’état faune, jamais le hasard météo
  ou celui de la contamination de l’eau.

`tests/test_animal_reactions.py`, inclus dans `test_journey.py`, teste les
commandes clavier : chaque espèce, moyens et refus, les quatre résultats du
combat, présence persistante, soins déclenchés, vol de stocks fractionnés de
plus de 255 OZ, postures au sol/dans l’arbre, morsure et soins en hauteur, provisions suspendues
conservées pendant une blessure, descente, interruption et rapport d’une attente prolongée.
