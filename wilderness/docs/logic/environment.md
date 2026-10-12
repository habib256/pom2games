# Wilderness : environnement (météo, heure, terrain, faune)

Rétro-ingénierie du moteur original (face Journey, Sierra Nevada, niveau 4,
« premier voyage »). Méthode : désassemblage (`da65`) des blocs résidents
(`tools/re_extract.py`) et des modules chaînés de la face Journey
(`tools/re_env_chain.py`), lecture des variables flottantes
(`tools/re_env_fp.py`), messages (`tools/re_env_msgs.py`), expériences dans
`a2shot`. Les valeurs entre crochets sont celles de la partie de départ
(6 mai, 7 h). **(?)** marque ce qui reste à confirmer.

## Organisation du code

Le jeu calcule en flottants Applesoft (routines de la ROM : `$E7BE` FADD,
`$E7A7` FSUB = mémoire − FAC, `$E97F` FMULT, `$EA66` FDIV = mémoire / FAC,
`$EAF9` charge, `$EB2B` range, `$EBB2` compare, `$E10C` entier, `$EFF1` SIN,
`$EFEA` COS, `$F03A` TAN, `$F09E` ATN, `$EE8D` SQR). Variables flottantes de
5 octets en `$4C00-$4CFF`, octets d'état en `$4AD0-$4BFF`, valeurs initiales
chargées avec le bloc `$4000-$4CFF` (disque de région).

Chaque commande qui fait passer le temps déclenche une chaîne de modules
chargés en `$5800` sur la face Journey (`JMP $03DB` = charger et lancer le
suivant ; piste SMALLDOS *t* = piste physique 34 − *t*). Pour un pas de marche :

| Module (piste, secteur, nb) | Rôle |
|---|---|
| T09 S00 (5) | Déplacement d'un pas (autre fork) |
| T09 S05 (3) | **Horloge** : heure, date, durées des effets |
| T0C S03 (8) | **Journée** (seulement au passage de minuit) : soleil, températures du jour |
| T09 S08 (8) | **Terrain** sous le joueur, **soleil**, **température de l'heure** |
| T0A S0C (6) | **Météo** : fronts, ciel, vent, tendance |
| T0A S00 (5) | Événements de terrain, pente, **faune et ressources** |
| T0A S05 (7) | Suite faune/actions (?) |
| T0D S07 (8) | Fin de chaîne, affichage |

Le module d'événements (T06 S02, chargé par `$0E62`) affiche les messages des
drapeaux `$0D91-$0DBF` (événement *x* → message *$87 + x*) et gère la mort
(événement 45, boucle infinie).

## Hasard

`$0321` (bas de SMALLDOS) : générateur multiplicatif de Lehmer,
S ← S × 2¹³ mod 67 099 547 (`$03FFDB9B`), état 32 bits en `$03B9-$03BC`,
renvoie FAC = S / 67 099 547 ∈ [0, 1).

## Temps et calendrier (T09 S05)

- Durée écoulée de la commande : `$4BC6/$4BC7` (minutes, 16 bits).
- Heure `$4C57` += min / 60 ; au-delà de 24 → −24 et drapeaux de nouveau jour
  `$4B6E`, `$4B6F` (la chaîne passe alors par T0C S03).
- Date `$4C89` = fraction d'année : += min / 525 600 (365 × 1440), −1 au-delà
  de 1. Jour de l'année = ⌊365 × `$4C89` + 1⌋ (mois par cumuls fixes, années
  de 365 jours). [0,344424 → 6 mai]
- Heures totales `$4C61` += min / 60 ; minutes depuis la dernière météo
  `$4C08` (remis à 0 en fin de chaîne par T0B S0D).

## Soleil et lumière

Calculés chaque jour (T0C S03) puis chaque pas (T09 S08) :

- Latitude φ = `$60A8` degrés signés (Sierra 38). Pas de longitude ni de
  fuseau : midi solaire = 12 h.
- Déclinaison : sin δ = 0,398 × sin(2π f − 1,378) (`$4CE8`), cos δ = √(1 − sin²δ)
  (`$4CED`) ; sin φ `$4CDE`, cos φ `$4CE3`. [sin δ 0,2816]
- Demi-excès du jour x = (12/π) · asin(tan φ · tan δ) ; lever `$4C66` = 6 − x,
  coucher `$4C6B` = 18 + x [5,12 h, 18,88 h] ; durée arrondie `$4B93`.
  Au-delà de |φ + δ| ≥ 80° : cas polaire (?).
- Crépuscule `$4CA7` (heures) calculé à partir de φ, δ [0,75 h] (formule
  exacte (?)).
- Phase `$4B01` / `$4B49` : NIGHT (−1) hors de [lever − crép., coucher + crép.],
  DAWN (0) avant le lever, AM (1) jusqu'à midi, PM (1) jusqu'au coucher,
  DUSK (0) ensuite. La nuit : `$E0` = 1 (vue noire, « NOT ENOUGH LIGHT »,
  message $35) et soleil masqué.
- Hauteur du soleil `$B7` (degrés) = asin(sin φ sin δ + cos φ cos δ cos H),
  H = (12 − heure) × 15° ; masqué (`$B7` = `$C0`) la nuit, ou si
  tan(hauteur) < 15 / visibilité. Dessiné dans la vue par SURV3D `$1B9B`
  (disque de 6 lignes, azimut `$B0/$B1`) si la portée `$E1` ≥ 44.
  [21° à 7 h, 64° à 13 h]

## Température de l'air

### Journée (T0C S03)

- Moyenne saisonnière au niveau de la mer :
  T₀ = (Tᵢ + Tₑ)/2 + (Tₑ − Tᵢ)/2 · sin(2π(f − 0,25)), Tᵢ = `$4BB0` (hiver, 41 °F),
  Tₑ = `$4BB1` (été, 77 °F), maximum le 1ᵉʳ juillet. Valeurs du bloc de région.
- Altitude : moyenne du jour Tm = ⌊T₀⌋ − ⌊`$4C2A` × A⌋, A = altitude/100 ft,
  `$4C2A` = 0,25 °F par 100 ft.
- Amplitude Δ = ⌊15 + 0,2·A + 0,15·|φ|⌋ ; minimum Tm − Δ/2, maximum Tm + Δ/2.
  [Tm 54, Δ 32 → 38/70 °F]
- Points du cycle : minimum au lever − 1 h (`$4CB1`), maximum au coucher − 4 h
  (`$4CB6`), fin d'après-midi au coucher + 2 h (`$4CBB`) ; pentes et
  décalages des trois segments `$4CC0/$4BB6`, `$4CC5/$4BBC`, `$4CCA/$4BB8`.

### Heure (T09 S08, `$4B9B`)

1. Segment selon l'heure H : matin [`$4CB1`, `$4CB6`[ : ⌊H·2,97⌋ + 26 ;
   après-midi [`$4CB6`, `$4CBB`[ : ⌊H·(−3,556)⌋ + 123 ; nuit : H' = H (+24 si
   H ≤ lever), ⌊H'·(−1,475)⌋ + 80 (valeurs du 6 mai, continues aux jonctions).
2. + ⌊5 · sin(0,0187 · `$4C61` + `$4CCF`)⌋ : onde de 14 jours, ±5 °F.
3. + ⌊0,16 · A / √visibilité⌋ (terme faible, sens physique (?)).

Le port reproduit désormais le point 2 avec les routines flottantes de la
ROM et l'entier inférieur, y compris pour une onde négative. Sa phase
`s_temp_phase` est initialisée depuis le premier voyage Sierra (3,7921375772)
et reste constante ; elle ne reproduit pas encore l'initialisation aléatoire
des autres voyages. `test_temperature_wave.py --original` vérifie 405 cas
contre la branche `$5986-$59B0` de T09/S08. Les points 1 et 3 restent à porter.
   [7 h : 20 + 26 − 4 + 0 = 42 °F]

- Pente horaire `$4B9C` (1 près des extrêmes) (usage (?)).
- Température ressentie `$4B9D` = T − ⌊(√vent / 12) · (100 − T)⌋ (refroidissement
  éolien, vent `$4B9F` en mph). 42 °F et 7 mph donnent 30 °F.
- Mot TEMP sans thermomètre (`$4B05`) : FREEZE / COLD / NICE / WARM / HOT (seuils
  dans T0B S0x (?)).

## Météo (T0A S0C)

Fronts successifs sur une échelle de temps t = `$4C98` (+ minutes × 0,25 : une
unité = 4 min) :

| Variable | Rôle |
|---|---|
| `$4C9D` | début du prochain front [231 → 15,4 h] |
| `$4BFE/$4BFF` | durée du front courant [125] |
| `$4CA2`, `$4C00` | début et durée du front précédent |
| `$4B4D` | 1 avant le front, 2 pendant |
| `$4B7E`, `$4B7F` | fronts courts (< 120) précédent / courant |
| `$4C1C` | plafond météo du pas de santé : 360, 120 ou 30 minutes |

- Avant le front : tendance NO CHG, WORSE dans les 90 unités (6 h) qui
  précèdent.
- Pendant : tendance 4 − ⌊3·(t − début)/durée + 0,999⌋ (WORSE → BETTER).
- Après : nouveau front, durée 30 + ⌊RND × 180⌋ (2-14 h), écart
  max(40, RND × 20000 / `$4C43`) unités.
- Fréquence des précipitations du mois `$4C43` (calcul quotidien) :
  0,1 · `$4C52` · (`$60B0` + (`$60B2` − `$60B0`)/2 · (1 + sin((360 f + `$60B4`)°)))
  [Sierra : `$60B0` = 2, `$60B2` = 60, `$60B4` = 47 → 3,55 en mai] ; classe
  `$4B04` LIGHT (< 1), AVERAGE, HEAVY (> 4) ; Chili (région 6) corrigé selon
  la latitude.
- Visibilité `$4B91` : 240 par beau temps, réduite à l'approche et pendant
  le front (7 ou distance au front × 2,4), plancher 24.
- Ciel `$4B07` (`$4B4C` + 1) : avant le front CLEAR si visibilité 240, sinon
  CLOUDY ; pendant le front RAIN, ou SNOW si l'altitude dépasse la limite de
  gel `$4C0C` = A + arrondi((T − 32) / 0,25) (centaines de pieds).
  Début de pluie/neige → événement 12 « THE WEATHER HAS TAKEN A CHANGE FOR
  THE WORSE ». `$B4` pour la vue : −1 clair, 0 nuageux/pluie, 1 neige.
- Vent `$4B9F` (mph) : marche aléatoire, vent −= ⌊4·RND − 2 + 0,5⌋, borné à
  [2, `$60B9`] (Sierra 30). [7]
- Trop de pluie ou de vent interdit certaines actions (message $4F) (?).

## Terrain sous le joueur (T09 S08)

- Niveau `$D4` (fonction d'altitude SURV3D `$0DCC`), œil `$D5` = `$D4`/2 + 1.
- Altitude affichée = (`$D4` + `$60A1`) × 100 ft ; sans altimètre : LOW
  (< 3000 ft), HIGH (≥ 10100), sinon MEDIUM.
- Classe `$4B56` : drapeau d'eau de la fonction d'altitude (`$C0`) : `$80`
  rivière (3), `$01` lac (4) ; sinon bois si x tombe dans un segment de forêt
  de la ligne (TOPO `$6250`) (1), rocheux si niveau ≥ `$60A3` [96 = 12000 ft]
  (2), dégagé (0). Niveau < `$60A2` [29] lève un drapeau d'usage inconnu (?).
- Mot GRND : CLEAR, WOODS (JUNGLE en régions 3-5, SCRUB au-dessus de
  `$60A6` = 11000 ft), ROCKY, LAKE / FRZLAKE / LAKESHR, RIVER / RIVSHOR.
  Lac gelé si l'indice de gel du jour `$4C48` > 10 et `$4B57` (indice : degrés
  sous 32 °F intégrés sur la journée (?)).
- Voisinage 3×3 : pente max `$DA` (|Δniveau| max), rivière voisine →
  message $D0 (une fois), lac voisin → rive et direction.
- Pente affichée (SLOPE avant/max) : arrondi(4 · deg(atan(Δ/24))), Δ en
  niveaux ; « avant » = case voisine dans la direction du cap, secteurs
  N < 30° ou ≥ 331°, NE 30-60, E 61-120, SE 121-150, S 151-210, SO 211-240,
  O 241-300, NO 301-330.
- Changement de classe → événements 1-10, 35 (« YOU HAVE REACHED A RIVER »…).
- Risque de déplacement `$4B6D` (0-3) selon `$DA` : seuils 5/10/16 sur l'eau
  (classe 3), 15/31 ailleurs (plus sévère par pluie ou neige) → événement 11
  « TRAVELLING CONDITIONS ARE BECOMING DANGEROUS » ; chute (23) ou
  noyade (24) tirées avec une probabilité proportionnelle aux minutes
  (`$4C39`) (?).

## Lieux particuliers

- But `$6080/$6081` (poste de rangers en scénario 1, cité perdue en
  scénario 2 ; `$605F` = scénario), départ `$6083/$6084` (épave).
- Case voisine du but → événement 30 « RANGER STATION OUTPOST IS NEAR »,
  de l'épave → 29 ; sur la case du but → événement 47, sur l'épave en
  scénario 1 → 33 « BACK AT YOUR STARTING POINT ». Fin de partie gagnante
  non localisée (?).
- Sites `$608B…` (paires y, x) : vestiges du scénario 2 (crâne 26, poterie
  27, sépultures 28, cité 31), à 1 case près.
- GOAL% (STATUS) : distance au but rapportée à `$60BD` (autre fork).

## Ressources et faune (T0A S00)

Vecteur d'environnement `$4ADA-$4ADF` : saison (100 f), heure, groupe de
terrain (rocheux 0, dégagé 10, bois 20, rivière 30, lac 40), altitude /100,
pente max, indice climatique de la carte `$60BA` [Sierra 31]. Chaque type a
6 paires (centre c, largeur w) dans la table `$48B4` (12 octets par type) :
w > 0 exige |e − c| ≤ w, w < 0 exige |e − c| > |w|, w = 0 exige e ≠ c.

| Type | Saison | Heure | Terrain | Altitude | Pente | Indice |
|---|---|---|---|---|---|---|
| 1 animal (ours) | 16-84 % | hors 7-15 h | dégagé, bois | 3000-8000 | ≤ 50 | 10-50 |
| 2 animal (couguar) | toute | hors 7-17 h | rocheux, dégagé, bois | 1000-9000 | ≤ 70 | 10-50 |
| 3 animal (crotale) | 33-83 % | 6-18 h | rocheux, dégagé | ≤ 8000 | ≤ 60 | 10-50 |
| 5 petit gibier | 18-92 % | 4-22 h | dégagé, bois | ≤ 11000 | ≤ 60 | 10-140 |
| 6 poissons | toute | 4-22 h | rivière, lac | ≤ 12000 | ≤ 30 | 10-140 |
| 7 insectes | 18-92 % | 5-23 h | tous | ≤ 10000 | ≤ 90 | 10-140 |
| 8 fruits | 40-80 % | 4-22 h | dégagé, bois | ≤ 10000 | ≤ 60 | 15-135 |
| 9 cactus | toute | toute | rocheux, dégagé, bois | ≤ 10000 | ≤ 70 | 0-14 |
| 10 champignons | 23-87 % | 4-22 h | bois | ≤ 8000 | ≤ 30 | 20-140 |
| 11 plantes | 23-87 % | toute | dégagé, bois | ≤ 11000 | ≤ 60 | 15-135 |
| 12 noix | 38-78 % | 4-22 h | dégagé, bois | ≤ 10000 | ≤ 60 | 15-135 |
| 13 abri naturel | toute | 4-22 h | rocheux à bois | toute | ≤ 90 | 0-140 |

Les trois animaux et leurs fourchettes viennent de l'en-tête TOPO : 3
fiches de 32 octets en `$6000`, `$6020`, `$6040` (12 octets de fourchettes,
octet 12 = taux de rencontre [80, 40, 100], octet 29 = aquatique, autres
octets : comportement (?)), noms en `$60D0 + 12 k`.

- Probabilité par pas : animal = minutes × `$4C4D` × √difficulté (`$603F`) ×
  taux × 1,0·10⁻⁵ (≈ 10 %/h pour l'ours au niveau 4) ; ressources 5-12 :
  RND × 0,1 / √difficulté ; abri : 0,05 / √difficulté (jamais en terrain
  dégagé). Tirage RND < probabilité.
- Ressource trouvée → événement type + 8 (13 petit gibier … 21 abri).
- Animal → événement 32 « A <ANIMAL> HAS ENTERED YOUR AREA! », présence
  `$4B0E + type − 1`, animal courant `$0D81` (un nouvel animal remplace le
  précédent avec une chance sur deux). Suites (blessure $45, départ $48, vol
  de nourriture $49, coup fatal $4A, conseils $E7-$EF selon l'arme) dans
  T0A S05 et les modules d'action (?).

## Vérification des rencontres dans le port

`tools/re_fauna_probe.py` charge le filtre original `$5A2F`, les accesseurs
et les tables Sierra dans a2shot. Seul son point de succès `$5AA3` est
remplacé par un enregistreur : 162 cas couvrent les deux côtés des bornes
des six dimensions. Une seconde copie conserve le calcul de probabilité et
l'enregistre à `$5B46`, avant le tirage : 45 cas de durée, difficulté,
fréquence et espèce concordent avec la formule ci-dessus.

`re_fauna_accept_probe.py` exécute le point d'acceptation `$5B5A` : RND est
remplacé par un flottant contrôlé, puis les comparaisons ROM et les écritures
de présence/événement tournent normalement. Ses 36 cas montrent qu'en
présence d'un animal, RND < 0,5 le conserve et RND ≥ 0,5 le remplace, même
pour une nouvelle rencontre de la même espèce. Une acceptation fixe
`$4B5F` et l'événement 32 (`$0DB0`), une conservation ne les fixe pas.

`src/fauna.s` applique ces filtres, taux et remplacements. Le port tire
maintenant à chaque pas de simulation et interrompt marche/repos quand une
rencontre est acceptée. Il utilise encore un LFSR propre au port, une seule
présence. Après 60 minutes sans décision, une réaction interrompt l’action ;
arbre/cabane protègent le joueur. Les seuils de SCARE/ATTACK et de blessures
sont maintenant sondés dans les modules natifs ; le vol, les stocks suspendus
et les réactions IGNORE sont détaillés dans [animals.md](animals.md).
Les déplacements et la cadence originale restent à établir. La commande
NATURE porte le multiplicateur de faune ; le réglage des ressources manque.


## Messages

Message *m* (1-255) : 64 octets en piste $18 + (m − 1)/64, secteur
((m − 1)/4) mod 16, offset ((m − 1) mod 4) × 64 ; octet 1 = chaîne en `$0300`,
2 = nom d'animal, autres < $80 = nombre. Événements d'environnement :
1-10 terrains, 11 danger, 12 météo, 13-22 ressources, 23 chute, 24 noyade
évitée, 29/30 épave/poste proches, 32 animal, 33 retour au départ, 35 broussailles.

## Questions ouvertes

- Portée de vue `$E1` (128) : non modifiée par la visibilité au redessin ;
  qui l'écrit ?
- Seuils du mot TEMP, formule exacte du crépuscule et de l'indice de gel.
- Sens du terme d'altitude dans la température horaire et de `$4B9C`.
- Comportement des animaux après leur arrivée, fin de partie gagnante.
- Origine de `$4BB0/$4BB1` pour les autres régions (bloc `$4000-$4CFF` du
  disque de chaque région).

## Vent ressenti : portage vérifié

`tools/re_wind_energy_probe.py` appelle directement `$59E5` du module T09/S08
sur la ROM, avec les données originales locales. 35 couples température/
vent confirment la formule ci-dessus, y compris les températures négatives,
le vent nul et T > 100 °F. `$E10C` effectue INT vers −∞. Le coefficient 1/12
est stocké comme `$7D,$2A,$AA,$AA,$AB` (0,08333333334303461) ; près d'un
entier, son arrondi peut compter : 110 °F, 36 mph donne 116 °F.

`src/thermal.s:thermal_wind` utilise les mêmes opérations et le même arrondi.
La différence volontaire est la largeur du résultat : `felt_temp` conserve
les 16 bits signés de T − INT(...), alors que l'original ne garde que
l'octet bas dans `$4B9D`. Un froid très fort ne devient donc pas une valeur
positive après débordement. Exemple : −128 °F avec 100 mph donne −318 °F.
Ces valeurs extrêmes servent aux tests ; la première région limite le vent
à 30 mph.

Le calcul est appelé après chaque mise à jour de l'air et du vent, y compris
au démarrage. La thermique utilise `felt_temp`. STATUS conserve TEMP pour
l'air et affiche FEEL pour ce ressenti, signé, à côté de WIND.
