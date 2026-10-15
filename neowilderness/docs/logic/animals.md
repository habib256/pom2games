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
- ATTACK prend le premier moyen en usage de l'original (T0F/S07 `$590F` :
  fusil 21, arc 20, lance 19, hache ou couteau en usage 18, gourdin ou
  pierre 17 ; drapeau effacé ; seuils `fiche[moyen]` et `fiche[moyen + 6]`,
  lot 3, CRAFT.md § 8.5) ; sans moyen en usage, il exige hache/couteau
  accessible (règle du port, sans USE). Une réussite est interprétée comme
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

## Règles de rencontre des six régions

Les filtres Sierra de `fauna.s` ne sont qu'une des six régions. Les autres
n'ont pas de carte originale ; `tools/re_region_fauna_probe.py` (`make
region-probe`) les reproduit comme les « Country Disks » de l'original :
au point d'entrée de GO1 (`$5800`, après le chargement de TOPO par l'option
2 du menu), il remplace dans TOPO les octets de région par le secteur de la
région visée (fiches `$6000-$607E` sauf `$603F`/`$605F`, `$60A4-$60A7`,
`$60AA-$60BA`, noms `$60D0-$60FF`, latitude et déclinaison médianes de
TMAKE0), puis laisse GO1, GO2, GO3 et la face Journey préparer le voyage
(épave, 6 mai demandé, 7 h). Le relief reste celui de la Sierra (base 24,
sommet 10 800 ft). Contrôle de la méthode : la Sierra repatchée avec son
propre secteur donne la même RAM `$4000-$BFFF` que le voyage non patché.

Sur l'état de départ natif de chaque région, la sonde exécute ensuite :

- le filtre T0A/S00 `$5A2F` pour les 13 types (4 animaux et 9 ressources),
  de part et d'autre de chaque borne : 2 833 cas au total ;
- le calcul de probabilité jusqu'à `$5B46` (avant RND) : 342 cas, durée,
  difficulté, fréquence, et terrain/rive pour l'octet 29 ;
- les seuils de T0F/S07 et T06/S04 (bruit, blessure par moyen 14, 15,
  17-21, posture 13/15/16 avec et sans abri, réussite 17-21, vol) :
  429 cas, comme `re_animal_reactions_probe.py` ;
- la règle des pacotilles de New Guinea (8 cas, ci-dessous).

Toutes les valeurs mesurées suivent les formules de la Sierra appliquées
aux octets de la fiche : aucune règle de rencontre n'est propre à une
région, sauf les pacotilles et l'octet 29. Les fiches et formules sont
dans `build/regions/fauna.json` pour les paquets de région.

### Fiche animale (32 octets, `$6000 + 32 × (k − 1)`)

| Octets | Sens | Lecteur |
|---|---|---|
| 0-11 | six couples (centre, largeur signée) : saison, heure, terrain, altitude, pente, indice climatique | GO1 les copie dans `$48B4` |
| 12 | taux de rencontre | T0A/S00 `$5AF0` |
| 13-21 | risque de blessure × 0,02 par moyen : 13 sol (attente, repos, repas), 14 bruit raté, 15 IGNORE et commandes ≥ 22, 16 arbre, 17 gourdin/pierre, 18 hache/couteau, 19 lance, 20 arc, 21 fusil | T06/S04 `$5800` |
| 14 | aussi seuil du bruit : 0,8 − 0,03 × octet | T0F/S07 `$586E` |
| 22 | exposant de gravité : INT(1 + 5 × RND^octet) | T06/S04 `$5CEF` |
| 23-27 | réussite de l'attaque par moyen 17-21 : 0,01 × octet / `$19` (`$19` = 2 dans les sondes, sens non établi) | T06/S04 `$593A` |
| 28 | vol de provisions permis si non nul (5 %, 1 % sac suspendu, 10 % dans l'arbre) | T06/S04 `$5A94` |
| 29 | non nul : aucune rencontre dans l'eau (`$4B56` ≥ 3 et rive `$4B6B` 0 ou 3) | T0A/S00 `$5AB5` |
| 30 | inconnu (1 à 15, éléphant 15) ; non lu par les modules sondés | — |
| 31 | octets d'en-tête `$601F`, `$603F`, `$605F`, `$607F` | — |

Les moyens 17 à 21 viennent de T0F/S07 `$58DE-$5939` : fusil (objet 57),
arc et lance (fabrications 14 et 15), hache et couteau (objets 58, 59),
gourdin et pierre (fabrications 16, 17). Un filtre compare d = |e − c| et
a = |w| sur 8 bits (complément à deux) : w > 0 exige d ≤ a, w < 0 exige
d > a, w = 0 exige d > 0. La probabilité par pas reste minutes × fréquence
× √niveau × taux × 10⁻⁵.

Les tableaux traduisent les filtres en plages (altitude absolue = indice
× 100 ft ; terrain : rocheux 0, dégagé 10, bois 20, rivière 30, lac 40).
Les pourcentages de réaction sont les seuils sondés hors abri, au sol ;
au-delà de 100 % la blessure est certaine.

### 1. British Columbia (indice climatique 28)

Sondes : 471 cas de filtre, 54 de probabilité, 69 de réaction.

| Espèce (sprite) | Taux | Saison % | Heure | Terrain | Altitude (ft) | Pente | Indice | Eau |
|---|---:|---|---|---|---|---|---|---|
| BEAR (`grizzly_bc`) | 80 | 16–84 | 0–7, 17–23 | dégagé, bois, rivière | 0–5000 | 0–40 | 0–128 | exclu |
| WOLF (`wolf_bc`) | 100 | toute | toute | rocheux, dégagé, bois | 0–5000 | 0–60 | 0–128 | — |
| MOOSE (`moose_bc`) | 75 | toute | toute | bois, rivière, lac | 0–4000 | 0–40 | 0–128 | exclu |

| Espèce | Bruit | Sol | IGNORE | Arbre | Gourdin | Hache | Lance | Arc | Fusil | Réussite gourdin/hache/lance/arc/fusil | Gravité | Vol |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| BEAR | 20 % | 4 % | 6 % | 2 % | 100 % | 80 % | 60 % | 40 % | 20 % | 0,5 / 1,5 / 3,5 / 7,5 / 12,5 % | 1 | oui |
| WOLF | 68 % | 2 % | 2 % | 0 % | 50 % | 40 % | 30 % | 20 % | 10 % | 7,5 / 10 / 15 / 17,5 / 20 % | 3 | oui |
| MOOSE | 68 % | 2 % | 4 % | 0 % | 50 % | 40 % | 40 % | 20 % | 14 % | 2,5 / 5 / 7,5 / 12,5 / 16 % | 2 | non |

### 2. Sierra Nevada (indice climatique 31)

Sondes : 488 cas de filtre, 54 de probabilité, 69 de réaction.

| Espèce (sprite) | Taux | Saison % | Heure | Terrain | Altitude (ft) | Pente | Indice | Eau |
|---|---:|---|---|---|---|---|---|---|
| BEAR (`bear`) | 80 | 16–84 | 0–6, 16–23 | dégagé, bois | 3000–8000 | 0–50 | 10–50 | — |
| COUGAR (`cougar`) | 40 | toute | 0–6, 18–23 | rocheux, dégagé, bois | 1000–9000 | 0–70 | 10–50 | — |
| RATTLESNAKE (`rattlesnake`) | 100 | 33–83 | 6–18 | rocheux, dégagé | 0–8000 | 0–60 | 10–50 | — |

| Espèce | Bruit | Sol | IGNORE | Arbre | Gourdin | Hache | Lance | Arc | Fusil | Réussite gourdin/hache/lance/arc/fusil | Gravité | Vol |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| BEAR | 50 % | 2 % | 4 % | 4 % | 70 % | 70 % | 50 % | 30 % | 10 % | 0,5 / 1,5 / 3,5 / 10 / 17,5 % | 1 | oui |
| COUGAR | 50 % | 2 % | 4 % | 4 % | 50 % | 50 % | 40 % | 30 % | 14 % | 1,5 / 5 / 10 / 15 / 20 % | 2 | oui |
| RATTLESNAKE | 0 % | 4 % | 6 % | 6 % | 10 % | 40 % | 10 % | 20 % | 14 % | 30 / 15 / 30 / 7,5 / 17,5 % | 5 | non |

### 3. Burma (indice climatique 75)

Sondes : 470 cas de filtre, 72 de probabilité, 87 de réaction.

| Espèce (sprite) | Taux | Saison % | Heure | Terrain | Altitude (ft) | Pente | Indice | Eau |
|---|---:|---|---|---|---|---|---|---|
| TIGER (`tiger`) | 70 | toute | 0–7, 17–23 | bois, rivière | 0–2600 | 0–40 | toute | — |
| ELEPHANT (`elephant`) | 70 | toute | toute | bois, rivière, lac | 0–1000 | 0–30 | toute | exclu |
| COBRA (`cobra`) | 70 | toute | 0–7, 17–23 | dégagé, bois | 0–2000 | 0–30 | toute | — |
| PYTHON (`python`) | 75 | toute | 0–5, 19–23 | bois, rivière, lac | 0–3000 | 0–40 | toute | — |

| Espèce | Bruit | Sol | IGNORE | Arbre | Gourdin | Hache | Lance | Arc | Fusil | Réussite gourdin/hache/lance/arc/fusil | Gravité | Vol |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| TIGER | 20 % | 6 % | 8 % | 8 % | 100 % | 80 % | 60 % | 40 % | 20 % | 1,5 / 2,5 / 7,5 / 12,5 / 17,5 % | 1 | oui |
| ELEPHANT | 20 % | 4 % | 4 % | 2 % | 160 % | 150 % | 140 % | 100 % | 40 % | 0 / 0 / 1,5 / 2,5 / 5 % | 1 | non |
| COBRA | 20 % | 4 % | 8 % | 6 % | 20 % | 40 % | 14 % | 20 % | 14 % | 20 / 15 / 20 / 7,5 / 12,5 % | 4 | non |
| PYTHON | 71 % | 8 % | 2 % | 4 % | 70 % | 70 % | 50 % | 40 % | 30 % | 10 / 7,5 / 10 / 7,5 / 12,5 % | 2 | non |

### 4. New Guinea (indice climatique 130)

Sondes : 459 cas de filtre, 54 de probabilité, 66 de réaction.

| Espèce (sprite) | Taux | Saison % | Heure | Terrain | Altitude (ft) | Pente | Indice | Eau |
|---|---:|---|---|---|---|---|---|---|
| CANNIBAL (`dani`) | 50 | toute | toute | rocheux, dégagé, bois, rivière, lac | 1000–9000 | 0–60 | toute | — |
| ADDER (`adder`) | 80 | toute | 0–5, 19–23 | rocheux, dégagé, bois | 0–2000 | 0–50 | toute | — |
| CROCODILE (`crocodile`) | 120 | toute | 0–7, 19–23 | rivière, lac | 0–800 | 0–10 | toute | — |

| Espèce | Bruit | Sol | IGNORE | Arbre | Gourdin | Hache | Lance | Arc | Fusil | Réussite gourdin/hache/lance/arc/fusil | Gravité | Vol |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| CANNIBAL | 20 % | 30 % | 50 % | 50 % | 100 % | 80 % | 70 % | 60 % | 30 % | 7,5 / 10 / 15 / 17,5 / 30 % | 1 | oui |
| ADDER | 20 % | 4 % | 6 % | 6 % | 10 % | 40 % | 10 % | 20 % | 14 % | 30 / 15 / 30 / 7,5 / 15 % | 4 | non |
| CROCODILE | 20 % | 6 % | 10 % | 0 % | 120 % | 100 % | 70 % | 60 % | 30 % | 1 / 7,5 / 10 / 10 / 12,5 % | 1 | non |

### 5. Bolivia (indice climatique 40)

Sondes : 482 cas de filtre, 72 de probabilité, 90 de réaction.

| Espèce (sprite) | Taux | Saison % | Heure | Terrain | Altitude (ft) | Pente | Indice | Eau |
|---|---:|---|---|---|---|---|---|---|
| PUMA (`puma`) | 80 | toute | 0–6, 18–23 | rocheux, dégagé, bois | 5000–10000 | 0–60 | toute | — |
| JAGUAR (`jaguar`) | 100 | toute | 0–6, 18–23 | dégagé, bois, rivière | 1000–4000 | 0–30 | toute | exclu |
| FERDELANCE (`ferdelance`) | 80 | toute | 6–20 | dégagé, bois | 1000–6000 | 0–30 | toute | — |
| ANACONDA (`anaconda`) | 50 | toute | toute | rivière, lac | 1000–3000 | 0–20 | toute | — |

| Espèce | Bruit | Sol | IGNORE | Arbre | Gourdin | Hache | Lance | Arc | Fusil | Réussite gourdin/hache/lance/arc/fusil | Gravité | Vol |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| PUMA | 50 % | 2 % | 4 % | 4 % | 60 % | 50 % | 40 % | 30 % | 14 % | 1,5 / 5 / 10 / 15 / 20 % | 2 | oui |
| JAGUAR | 35 % | 6 % | 4 % | 6 % | 60 % | 50 % | 40 % | 30 % | 14 % | 2 / 5 / 10 / 15 / 20 % | 2 | oui |
| FERDELANCE | 59 % | 10 % | 4 % | 4 % | 10 % | 40 % | 6 % | 20 % | 14 % | 30 / 15 / 30 / 7,5 / 17,5 % | 4 | non |
| ANACONDA | 50 % | 6 % | 4 % | 6 % | 60 % | 70 % | 40 % | 50 % | 30 % | 15 / 12,5 / 20 / 12,5 / 22,5 % | 2 | non |

### 6. Chile (indice climatique 11)

Sondes : 463 cas de filtre, 36 de probabilité, 48 de réaction.

| Espèce (sprite) | Taux | Saison % | Heure | Terrain | Altitude (ft) | Pente | Indice | Eau |
|---|---:|---|---|---|---|---|---|---|
| PUMA (`puma`) | 100 | toute | 0–6, 18–23 | rocheux, dégagé, bois | 4000–12000 | 0–70 | toute | — |
| CAT (`cat`) | 100 | toute | 0–5, 19–23 | rocheux, dégagé | 6000–14000 | 10–70 | toute | — |

| Espèce | Bruit | Sol | IGNORE | Arbre | Gourdin | Hache | Lance | Arc | Fusil | Réussite gourdin/hache/lance/arc/fusil | Gravité | Vol |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| PUMA | 50 % | 2 % | 4 % | 4 % | 60 % | 50 % | 40 % | 30 % | 14 % | 1,5 / 5 / 10 / 15 / 20 % | 2 | oui |
| CAT | 71 % | 2 % | 4 % | 4 % | 50 % | 40 % | 30 % | 30 % | 10 % | 10 / 10 / 12,5 / 15 / 25 % | 3 | oui |

### Différences avec la Sierra

- Faune : British Columbia et New Guinea ont trois espèces, Burma et
  Bolivia quatre (la quatrième fiche, vide en Sierra, est filtrée et tirée
  comme les autres : présence `$4B11`), Chile deux. Les filtres d'indice
  climatique acceptent toujours l'indice de leur région.
- Octet 29 : grizzly, élan, éléphant et jaguar ne sont jamais rencontrés
  dans l'eau ; en Sierra l'octet est nul et le terrain suffit.
- Pacotilles (New Guinea, fiche 1, T06/S04 `$58DA-$58FA`) : après un tirage
  de blessure réussi, si le joueur possède TRINKETS (`$40E2`), la blessure
  n'a lieu que si un second RND est < 0,02 (constante `$5D9C`). Sondé avec
  RND imposé 0,01 et 0,5, avec et sans pacotilles, et en Burma (règle
  absente).
- Ressources : GO1 ajuste les saisons selon la latitude (voir
  [REGIONS.md](../REGIONS.md#3-formules-dérivées-des-en-têtes)) ; les
  tropiques (Burma à 19°, New Guinea, Bolivia) ont petit gibier, insectes,
  fruits, champignons, plantes et noix toute l'année ; le Chili à −38° a
  des saisons inversées. Les cactus (indice 0-14) n'existent qu'au Chili ;
  fruits, champignons, plantes et noix (indice ≥ 15 ou 20) y manquent.
- Les valeurs des réactions de la fiche Sierra restent celles du tableau
  « Seuils mesurés » plus haut.

### Objets de l'épave

Les objets de l'épave ne dépendent pas de la région. La sonde compare la
table de position des objets (`$404C`, un octet par objet : `$FF` au sol,
1 porté, 0 absent) et les pages INVENTORY des six départs :
British Columbia, Burma, New Guinea et Bolivia ont exactement le lot Sierra
(même table `$404C`, 26 entrées non nulles, mêmes provisions) ; Chile en a un autre
(BALACLAVA, MITTENS, RAINCOAT, GLOVES, COMPASS, ROPE… sans SLPNG BAG ni
RAFT). Mais changer seulement l'octet région de la Sierra (1, 3, 4, 5, 6)
garde le lot Sierra, et changer seulement sa latitude en −21 donne
exactement le lot chilien, avec le même décalage de date (MAY 11 au lieu
de MAY 17) : le lot est tiré au hasard dans une réserve commune et la
latitude ne fait que déplacer la suite des RND consommés avant le tirage.
Les mois 1, 11 et 12 ne changent pas le lot Sierra. Les autres octets de
`$4000-$47FF` qui diffèrent (table `$450C`, un mot par vêtement) dépendent
du climat, pas de l'inventaire. Le port peut garder un lot commun.

### Limites

- Le relief, la base et le niveau rocheux restent ceux de la carte Sierra ;
  les règles de terrain dépendantes de la carte ne sont pas sondées ici.
- La gravité (octet 22) n'est exécutée que pour la Sierra ; les autres
  régions utilisent la même instruction avec leur octet.
- Les branches de région hors rencontres (radeau, échanges avec le
  cannibale, mots JUNGLE) sont listées dans
  [REGIONS.md](../REGIONS.md#7-branches-de-région-du-code-original), non sondées.

## Portage : quatre espèces (étape 4)

Le port lit maintenant les règles de la région chargée ; les formules sont
celles de la Sierra appliquées aux octets des fiches (section précédente).
`tools/build_disk.py` (`fauna_patches`) dérive des fiches `$6000-$607F` de
l'en-tête les correctifs écrits par le paquet `NEOWILD.Rn` dans les images
auxiliaires des modules (détail : [MEMORY.md](../MEMORY.md) § 9.2, § 9.6) :

| Correctif | Module | Octets | Contenu |
|---|---|---:|---|
| `fauna_travel` | TRAVEL (balayage de production `resource_scan`) | 52 | taux (octet 12) et six filtres (octets 0-11) des quatre fiches |
| `fauna_table` | SITES (copies de référence des tests) | 52 | les mêmes octets |
| `fauna_reactions` | OUTDOOR | 40 | seuils ⌊256 p⌋ + 1 (0 jamais, 255 au plus) : bruit, blessure après bruit raté, hache, réussite, IGNORE (moyen 15), arbre (16), sol (13), départ ; nom du parseur ; `out_kind` (vol, venin, pacotilles, rangée de gravité) |
| `proj_sprites` | PROJECT | 12 | largeurs et bases des six sprites (épave, espèces 1-3, cabane, espèce 4) |
| `summary_quiet` | SUMMARY | 1 | espèce que le bruit ne chasse pas (octet 14 ≥ 27 : le crotale), 0 ailleurs |

- **Paquet de la Sierra Nevada** (15 octobre 2026) : ses quatre correctifs
  et ses couleurs DHGR, identiques au tronc, ne sont plus écrits par son
  paquet (le chargeur lit toujours le tronc d'abord ; `build_disk`
  l'affirme) ; les cinq autres paquets les écrivent.
- **Ordre des tirages inchangé** : la quatrième fiche était déjà filtrée et
  tirée (vide en Sierra : taux 0) ; Burma et Bolivia y mettent leur
  quatrième espèce (`animal_kind` 9, sprite du module 23), Chile a ses
  fiches 3 et 4 vides (taux nul, jamais acceptées).
- **Octet 29** : replié à la construction dans le filtre de terrain
  (`build_disk.fold_water` : la plage acceptée perd le terrain 40 ; élan
  et éléphant (30, 12) → (27, 12)) ; aucun octet de code.
- **Départ après IGNORE** : règle du port, pas un taux original : félins
  25 %, serpents venimeux (exposant de gravité ≥ 4) 75 %, autres 50 %.
- **Pacotilles** (New Guinea) : `outdoor_hurt` exige un second tirage
  < 0,02 si `out_kind` bit 5 et TRINKETS porté ; ailleurs un seul tirage.
- **Noms** : `region_species` (textes du paquet) dans les réactions (« THE
  TIGER INJURES YOU AND STAYS. ») et dans la cause d'arrêt (« TIGER IN YOUR
  AREA! », `module_fauna_cause` ; l'original disait « A <ANIMAL> HAS
  ENTERED YOUR AREA! », événement 32). PUMA reste synonyme de COUGAR en
  Sierra ; en Bolivia et Chile c'est le nom propre de l'espèce.

`tests/test_fauna.py` vérifie la Sierra inchangée, 90 à 166 cas de filtre
par autre région (`fauna_cases.region_cases`, octet 29 compris) et huit
probabilités, la quatrième espèce de Burma et Bolivia seule dans un lac de
nuit, l'absence d'élan dans l'eau en British Columbia, les pacotilles ;
`tests/test_menu.py` dessine chaque espèce près de l'épave et la nomme par
IGNORE dans les six régions.
