# Survie et temps (original)

Modèle du corps du joueur et de l'avancée du temps dans le Wilderness
original, établi par désassemblage des modules (avec `tools/re_surv_fp.py`,
qui traduit les appels aux routines flottantes de la ROM Applesoft) et par
expériences dans a2shot (`tools/re_surv_run.py`, `re_surv_vars.py`,
`re_surv_chain.py`, `re_surv_prof.py`). Les adresses sont celles du jeu en
mémoire ; « Txx/Syy » désigne un module de la face Journey (piste/secteur
SMALLDOS, voir [`ENGINE.md`](ENGINE.md)). Tout le calcul se fait en flottants
Applesoft (5 octets). Ce qui reste incertain est marqué **(?)**.

## Organisation : une chaîne de modules

Une commande qui fait passer le temps n'appelle pas une routine résidente :
elle enchaîne des modules chargés en `$5800`, chacun finissant par
`JMP $03DB` (charger A secteurs depuis X/Y puis sauter en `$5800`).

| Module | Rôle |
|---|---|
| T15/S0B | Commande REST (puis SLEEP…) |
| T08/S00, S01, S07 | Commande WALK |
| T12/S00 | Commande EAT |
| T11/S00, T0E/S02, T0E/S0A | USE COMPASS |
| T09/S00, T0A/S00 | Déplacement d'un pas de marche |
| **T09/S05** (`m095`) | **Pas de temps** : horloge, compteurs d'heures |
| **T09/S08** (`m098`) | Énergie dépensée, température ambiante (heure, saison) |
| T0A/S0C | Météo et plafond du prochain pas de santé |
| **T0B/S02**, T0B/S07 (`m0B2`, `m0B7`) | Bilan thermique, température corporelle |
| **T0B/S0D** (`m0BD`) | **Santé** et choix du pas suivant |
| T0A/S05 | Fin de pas (vêtements, objets) (?) |
| T0D/S07 | Fin d'action, avertissements |
| T06/S0A → T07/S01 → T14/S08 | STATUS : codes affichés, puis écran |

REST *n* commence par T15/S0B puis répète les pas S05 → S08 → T0A/S05.
Les modules météo, thermiques et de santé s'exécutent lorsque l'intervalle
accumulé `$4C08` atteint `$4BCC`, puis remettent cet intervalle à zéro.
Ils peuvent donc tourner plusieurs fois pendant une seule commande.
T09/S08 saute T0A/S00 pour REST et EAT (`$4B5D`) : ces actions ne tirent
aucune rencontre. Les chaînes et dumps du pilote
[`test_adventure.py`](../../tests/test_adventure.py) confirment ces branches.

## Horloge et pas de temps (`m095`, T09/S05)

| Variable | Type | Sens |
|---|---|---|
| `$4C57` | flottant | Heure du jour (0-24) ; au-delà de 24 : −24, drapeaux `$4B6E`/`$4B6F` (nouveau jour) |
| `$4C61` | flottant | Heures écoulées depuis le départ |
| `$4C89` | flottant | Date en fraction d'année : += minutes × 1/525 600 (0,3444 = 6 mai) |
| `$4BC6` | mot | Durée du pas courant (minutes) |
| `$4BCC` | mot | Durée maximale d'un pas (choisie par `m0BD`, voir plus bas) |
| `$4C14` | mot | Minutes de l'action en cours (« TRAVEL TIME WAS … ») |
| `$4C08` | mot | Minutes depuis la dernière mise à jour de santé |

À chaque pas : `$4C14 += dt`, `$4C08 += dt`, `$4C61 += dt/60`,
`$4C57 += dt/60`, `$4C89 += dt/525600`. Quand le reste de la commande est plus
court que `$4BCC`, le dernier pas est raccourci. Mesuré : REST avance par pas
de 30 min au début de REST, puis utilise le pas recalculé par la santé,
jusqu'à 240 min. Les fronts météo peuvent le limiter à 120 ou 30 min.
Une marche se fait en sous-pas dont la durée dépend de son état et du terrain.

Le mois et le jour affichés viennent de `$4C89` × 365 (seuils 32, 60, 91, 121,
152… jours), l'heure de `$4C57` (12 h, AM/PM).

### Coût en temps des actions (mesuré)

| Action | Temps |
|---|---|
| REST *n* / SLEEP *n* / WAIT *n* | *n* heures (durée demandée par « SPECIFY TIME IN HOURS ») |
| WALK *n* | Temps de marche effectif, souvent < *n* : 35 min pour WALK 1, 105 min pour WALK 2, 57 min pour WALK 1 (arrêt anticipé, cause **(?)** : terrain, eau, fatigue) |
| Vitesse de marche | ~6,1 à 6,2 unités de carte par heure (≈ 1,5 mile/h), sur terrain doux |
| STATUS, INVENTORY, USE COMPASS | Aucun temps |
| DRINK WATER depuis la gourde | Aucun temps |
| EAT CHEESE 8 depuis le sac | 16 minutes ; question quantité puis conteneur |

## Compteurs d'événements

Deux tableaux de 25 flottants : `A1` en `$4950` et `A2` en `$49CD` (accès par
`$4D1B` : X = indice 1..25, Y = 1 ou 2).

| Indice | `A1` | `A2` |
|---|---|---|
| 1-15 | — | Heures depuis le début de la condition *i* (voir Santé) |
| 16 | Heure du dernier verre (−2 au départ) | Heures depuis le dernier verre |
| 17 | Heure du dernier repas (−2) | Heures depuis le dernier repas |
| 18 | Heure du dernier repos/sommeil (−2) | Heures depuis (REST la remet à 0,5) |
| 19 | (−100) | 8 |
| 22 | Déficit cumulé (h) pour la condition 16 | Tolérance : 190,5 |
| 23 | Déficit cumulé (h) pour la condition 17 | Tolérance : 480 |
| 24 | Déficit cumulé (h) pour la condition 18 | Tolérance : 68 |

`m095` remet `A2[i] = max(0,5 ; $4C61 − A1[i])` pour les indices < 5,
8 et 14 à chaque pas, et les autres quand `$4C08 ≥ $4BCC`. Pour 16..18,
les compteurs et les déficits avancent donc à la cadence de santé : on ne
peut pas les remplacer par des additions à chaque commande.

Les crédits sont appliqués avant cette actualisation. REST soustrait
`0,05 × minutes demandées` au déficit de repos et date le dernier repos
à `elapsed + INT(minutes × 0,017)`. EAT soustrait `0,8 × kcal / poids` au
déficit alimentaire, avec apport d'eau selon l'humidité de l'aliment ; sa
date vaut `elapsed + 16 × 0,017`. Son compteur vaut d'abord 0, puis remonte
au minimum 0,5 lors de l'actualisation. Boire à la gourde crédite initialement
0,38 heure par once et remet son compteur à 0,5. La conversion hydrique
change avec la transpiration dans l'original, ce qui reste à porter.
Les déficits négatifs sont conservés jusqu'au calcul de santé, qui les borne
à zéro ; effacer un crédit dès la commande change le résultat du prochain pas.

## Énergie

| Variable | Sens |
|---|---|
| `$4BF6` | Poids du joueur, 165 (livres) |
| `$4C20` | Métabolisme (kcal/min), 1,65 au repos |
| `$4C25` | Métabolisme de base, 1,65 |
| `$4BDA` | Énergie dépensée (kcal), 600 au départ |
| `$4BDC` | Énergie disponible (kcal), 1000 au départ ; augmentée par les repas (?) |
| `$4BD8` | `$4BDC − $4BDA` (bilan, négatif = déficit) |
| `$4B87` | Drapeau « frissons » : ajoute 0,04 × poids au métabolisme |

Par pas (`m098`) : `$4BDA += INT(dt × ($4C20 + [$4B87] × 0,04 × $4BF6))`.
Mesuré : +49 par pas de 30 min au repos (98/h) ; ~5,2 kcal/min en marche
(le module de marche relève `$4C20`). La sauvegarde initiale a déjà `$4B87 = 1` : les 198 kcal supplémentaires
pour 30 minutes viennent de `30 × 0,04 × 165`, pas d'un rattrapage spécial.
Le repas utilise 2,31 kcal/min. Les crédits alimentaires ne se déduisent
pas du coût énergétique : ce sont deux compteurs distincts.

## Santé (`m0BD`, T0B/S0D)

**HEALTH% = round(100 × `$4C34` / `$4C2F`)**, avec `$4C2F` = 7,8666 au départ
(Hmax, origine **(?)**, niveau de difficulté ?).

`$4C34 = Hmax × Π (Sᵢ / 100)` sur 21 conditions, où Sᵢ ∈ [0, 100] est l'état
de la condition *i* (100 = intacte), rangé dans `rec7` (`$4821 + i − 1`) pour
i = 1..15 et dans `$48A8 + (i − 16)` (table `$4D15` X=5) pour i = 16..21.

| H | Effet |
|---|---|
| < 0,3 | Mort (drapeau `$4B5F`, `$0D90 + $2D`) |
| passe sous 1 | Alerte critique (`$0D90 + $29`) ; pas de temps réduit à 30 min |

### Conditions 1 à 15 (blessures et maladies)

Ordre des libellés de STATUS ; paramètres dans les tables de 15 octets
`$47B8 + 15·k` (une colonne par condition) :

| i | Condition | Plancher `rec5` (%) | Incubation `rec6` (h) | Guérison sans soin `rec9` (h) | avec soin `rec8` (h) |
|---|---|---|---|---|---|
| 1 | Severe cuts | 75 | — | 240 | 60 |
| 2 | Broken arm | 70 | — | 1 008 | 672 |
| 3 | Broken leg | 40 | — | 1 344 | 672 |
| 4 | Shock | 20 | — | 336 | 72 |
| 5 | Sunburn | 75 | 8 | 96 | 48 |
| 6 | Snowblind | 75 | 3 | 24 | 8 |
| 7 | Frostbite | 60 | 6 | 336 | 48 |
| 8 | Poison bite | 20 | 3 | 168 | 24 |
| 9 | Infection | 50 | 4 | 336 | 48 |
| 10 | Salt deficiency | 70 | 24 | 30 000 | 24 |
| 11 | Food poisoning | 50 | 6 | 120 | 48 |
| 12 | Giardia | 85 | 24 | 336 | 48 |
| 13 | Malaria | 40 | 240 | 1 008 | 672 |
| 14 | (?) | 1 | 0 | 100 | 100 |
| 15 | (?) | 100 | 1 | 3 | 2 |

Autres colonnes : `rec0` gravité (1-3) (?), `rec1` maladie (1) / blessure (0)
(?), `rec3` soignée, `rec4` active.

Avec *h* = `A2[i]` (heures depuis le début), *f* = plancher, *t* =
incubation, *D* = durée de guérison (avec ou sans soin) :

- maladies (i ≥ 5, i ≠ 14), pendant l'incubation (h ≤ t) :
  **S = f + (100 − f) · (t − h) / t** (de 100 au plancher) ;
- puis, et dès le début pour les blessures (i < 5, i = 14) :
  **S = f + (100 − f) · (h − t) / D** (du plancher à 100) ;
- h ≥ t + D : guérie (`rec3 = rec4 = 0`, S = 100).

Messages : la première fois qu'une condition passe de ≥ 96 à < 95 %, message
`$BB` ; sous 50 % (depuis ≥ 51), drapeaux `$4B5F`, `$0D90`, `$0DA9`.

### Conditions 16 à 21

Les valeurs positives de 16..18 sont tronquées en pourcentages entiers
(`INT(100 × (1 − (déficit / tolérance)²))`) avant le produit de santé.
Un petit déficit suffit donc à passer de 100 à 99 %, ce qui expliquait
les premiers écarts du port. Un déficit non positif donne 100 %.

| i | Condition | S |
|---|---|---|
| 16 | Dehydration | 100 · (1 − (A1[22] / A2[22])²), tolérance 190,5 |
| 17 | Starvation | 100 · (1 − (A1[23] / A2[23])²), tolérance 480 |
| 18 | Exhaustion | 100 · (1 − (A1[24] / A2[24])²), tolérance 68 |
| 19 | Altitude sickness | 100 si A×10 < 5·H + 100 ; sinon 100 · (1 − 0,00144 · A²), A = altitude en milliers de pieds ; 100 aussi quand l'objet 49 (OXYGEN) est en usage (table `$4098`) |
| 20 | Hypothermia | 100 − 1,2 · d², d = 98,6 − T (d/2 si soignée) |
| 21 | Hyperthermia | 100 − 2,7 · d² (d/2 si soignée) |

T = température corporelle `$4C70` (°F). L'affectation 16 = déshydratation /
17 = inanition (tolérances 190,5 / 480 h) mérite confirmation **(?)** :
l'ordre suit les libellés, mais les durées surprennent.

Mesuré : santé 100 → 98 % à la première heure (vent et 42 °F au départ), puis
stable au repos ; 100 → 97 % après la première marche.

### Choix du pas suivant (`m0BD` `$5BC8`)

`$4BCC` (durée maximale du pas, minutes) = 240, puis le plus petit de :
plafond météo `$4C1C` (360, 120 ou 30) ; 30 si H < 1 ; 60 si l'octet 11 de la table `$4D15` X=5 est < 64 (?) ; 30 si une condition 6..11 est
active depuis moins de 8 h ; 300 × 1,65 / (`$4C20` + frissons) ; 30 × |écart
thermique| / |`$4C75`| (si < 240) ; 60 si `$B7` ≥ 31 (?) ; minimum 29.
En attente (`$4B59`) : 120, 240, 720 ou 1440 selon `$4C9D` (?).

## Thermique (`m0B2`, `m0B7`)

- Isolation vestimentaire : somme sur 5 parties du corps (coefficients 2, 7, 1, 1, 2 ;
  `m0B2` lit `$5CA5 + k` pour k = 1..5)
  des valeurs des vêtements portés (`$4AE6+2k` à sec, `$4AF2+2k` si
  `$4B70` ≠ 0, mouillé/immersion), pondérées par leurs surfaces puis divisées par `$4C1A` (Q).
  Combinaison globale R0 × Q / (R0 + Q), réduite par `$4BBE` :
  × (1 − `$4BBE` / poids) ; indice `$4BE8` (≥ 10).
- Température effective `$EE` : `$4B9D` (ressenti du vent), 70 − 0,3 × altitude/100
  (immersion, `$4B70` = 2), 35 ou ambiante + 15 sous abri, +25 près du feu.
- Besoin : fonction de `$EE`, de √(`$4C20` / 1,65), constantes 20, 55, 0,2, 80
  et 1e-7 × `$4C1A`. Trop chaud (besoin > indice) : `$EF` = 1, message
  `$CC` (sueur), `$4B7B`. Trop froid : `$EF` = −1, frissons (`$4B87`,
  message `$CB`) si 0,04 × poids > `$4C20`.
- `$4C75` est une vitesse signée. Si elle éloigne T de 98,6, une magnitude
  < 0,3 ne change pas T ; sinon T += vitesse × minutes/60. Si elle rapproche
  T de 98,6, le pas est appliqué même sous 0,3, puis borné à 98,6.
  En régime neutre, voir le pas proportionnel décrit ci-dessous.

## Jauges de STATUS (`m071`, T07/S01)

| Jauge | Code | Règle |
|---|---|---|
| HNGR (`$4B08`) | 1 VERY, 2 SO-SO, 3 OKAY, 4 FILLED | FILLED si mangé (`$4BD2`) > 5 × poids dans l'heure ; VERY si `A2[17]` > 12 h, ou bilan `$4BD8` très négatif ; SO-SO si `A2[17]` ≥ 6 h ; sinon OKAY |
| THRST (`$4B09`) | 1 VERY … 4 FILLED | FILLED si bu (`$4BD4`) > 0,15 × poids dans l'heure ; VERY si `A2[16]` × `$4C7A` (0,583) > 6 ; sinon selon un besoin en eau = 60 × heure × 1,65 (≥ 2) × … (?) |
| ENRG (`$4B0A`) | 1 BEAT, 2 TIRED, 3 OKAY, 4 GREAT | BEAT si `A2[18]` > 16 h ; sinon selon `$4BE2` (heures de repos) / `A2[18]` (< 0,25 : BEAT) et la santé (`$4C34` < 2 : OKAY au mieux) |
| Signe (`$4B0B`) | SWEATING / SHIVERING | 48,3 − 0,5 × T comparé à `$4C75` |
| GOAL | % | voir ci-dessous |

### GOAL% (`m06A` `$5B61`)

Avec D₀ = distance initiale départ → poste (`$60BD`), d = distance actuelle,
h = heures écoulées :

- v = 0,6 × (D₀ − d) / h
- G = e^(−2,5 h / D₀′) + v × (1 − e^(−2,5 h / D₀′)), D₀′ = D₀ (×2 si `$605F` ≠ 1)
- **GOAL = 100 × G × (1 − (`$4C16` / 100 + 0,02 × `$4BDE`))**, borné à 0..100.

Vérifié : D₀ = 183, au repos 1 h → 98 %, 4 h → 94 %. GOAL mesure donc
l'avance vers le poste (≈ 1,7 unité/h attendue) ; `$4C16` et `$4BDE` sont des
pénalités (?) (aides demandées, sauvetage ?).

## Hasard

`$0321` : générateur de Lehmer, graine 32 bits en `$03B9`, graine × 2¹³ mod
67 099 547 (`$03FFDB9B`), résultat dans (0, 1).

## Reste à établir

- Cause de l'arrêt anticipé de la marche, effet de la pente, du terrain, de
  la charge (`$4BE6` = poids porté, 440 oz) et de l'énergie sur la vitesse.
- Repas et boissons : effet de EAT/DRINK sur `$4BDC`, `A1[16..17]`,
  `A1[22..23]`, FOOD/WATER (oz).
- Déclencheurs des conditions 1-15 (chutes, morsures, soleil, eau non bouillie…).
- Formule complète du besoin thermique ; conditions 14 et 15 ; `Hmax`.
- Effets du niveau de difficulté (`$603F`) sur ces constantes.

## Thermique : corrections et formules scalaires

Lecture de `m0B2` ($5800-$5C7C) et des textes numérotés locaux : **$CB =
« YOU ARE SHIVERING! », $CC = « YOU ARE SWEATING! »**. Les indications
précédentes de ces deux événements étaient inversées. `$4B7B` indique la
sueur, `$4B87` les frissons ; le supplément d'énergie de 0,04 × poids est
donc associé aux frissons, pas à la sueur. Le signe `$EF = +1` augmente la
température du corps ; −1 la diminue.

Avec E = température effective en °F, M = métabolisme, r = √(M/1,65),
I = indice vestimentaire (plancher 10), A = `$4C1A` et a = 1e−7 × A :

- Seuil B = r × (20 + (max(E, 0)/10)³) / 6. La routine `$EE94` calcule ici
  la puissance 3 ; ce n'est pas un logarithme.
- B > I : trop chaud, signe +1, déséquilibre |0,2 − 55·a·E·r/√I|
  (0,2 si E ≤ 0).
- 9B < I : trop froid, signe −1, déséquilibre
  −a·√I·|E − 80|·(1 + 0,5·`$4B70`).
- Entre ces deux seuils : retour vers 98,6 °F.

### Intégration confirmée sur la ROM

`tools/re_thermal_probe.py` charge les données originales locales et `m0B2`
sur une disquette DOS de test. Il appelle la sous-routine `$5811` ou la
branche `$5BFE`, en remplaçant seulement l'affichage des messages par RTS.
Aucune donnée originale n'est ajoutée au dépôt.

Onze expériences isolées confirment : vitesse −0,2 depuis 98,6 → 98,6 après
60 minutes ; −0,3 → 98,3 ; −0,4 → 98,2. Depuis 97, +0,2 → 97,2 ; depuis
100, −0,2 → 99,8. Un pas de récupération qui traverserait 98,6 s'arrête
exactement à 98,6. Le seuil 0,3 bloque donc une dérive qui éloigne de la
normale, jamais une récupération. Le produit vitesse × (T − 98,6) distingue
les deux cas.

En régime neutre : vitesse initiale v = −0,1 × (T − 98,6) ; déplacement
v × minutes × 0,017, borné à 98,6. Si 0 < |v| < 0,3, la vitesse publiée en
`$4C75` est remplacée par ±0,3, mais le déplacement utilise v avant cette
correction. Expériences : 97 → 97,1632 et 100 → 99,8572 en 60 minutes ;
un pas artificiel de 2400 minutes revient à 98,6 sans dépassement.

Le facteur d'activité est **√(M/1,65)** : `$EA66` divise la mémoire par FAC,
et non l'inverse. Les notes précédentes donnaient le rapport inversé.
Quatorze appels complets (E = −20, 0, 20, 42, 60, 80, 100 ; M = 1,65 ou
5,2 ; I = 47) confirment les formules à moins de 2e−7 °F/h. Par exemple,
E = 60, M = 5,2 donne +0,3176711707 °F/h et 98,91767117 °F après une heure.

### Reconstruction sèche utilisée dans le jeu

`src/thermal.s` recalcule les pertes de chaque partie du corps à partir des
vêtements WEAR, dans l'ordre des identifiants. La combinaison sèche suit
`m0EA` : nouvelle perte = arrondi(R × L / (R + L)), où L est W10 du vêtement.
Les pertes de peau nue sont notre reconstruction : 500 pour torse, jambes,
pieds et mains, 200 pour la tête. Les cinq surfaces × coefficients sont
2638, 2100, 790, 255 et 260 ; surface totale A = 6058.

Q = somme(surface × coefficient × perte) / A. La perte globale vaut 500 ;
l'indice sec est max(10, arrondi(500 × Q / (500 + Q))). Cette combinaison
harmonique globale, visible à `$58AC-$58DC`, manquait dans les premières
notes. L'original applique ensuite son facteur `$4BBE` / poids ; le sens
exact de ce compteur reste à confirmer et il n'est pas appliqué ici.

Ce recalcul donne I = 47 pour la tenue de départ, 36 avec la parka en plus,
221 sans vêtements. Il ne reproduit pas les cinq pertes préréglées de
l'original au départ : en particulier, les pieds y valent 70 alors que
notre combinaison BOOTS + SOCKS donne 49. Il évite de conserver un état
historique incohérent quand on dépose puis reprend des couches.

Le module utilise désormais la température ressentie signée et le métabolisme
de base (1,65 au repos, 5,2 en marche). Le refroidissement éolien et le coût
énergétique des frissons et les pertes mouillées sont portés. L'abri trouvé
utilise désormais l'air ambiant +15 °F, voir [sites.md](sites.md) ; le feu
et les abris fabriqués restent à intégrer.
La santé est multipliée par max(0, 1 − 0,012 × (98,6 − T)²) côté froid,
ou max(0, 1 − 0,027 × (T − 98,6)²) côté chaud. Les coefficients sont ceux
des conditions 20-21 ; leur activation continue est notre simplification,
en attendant les déclencheurs et les soins de l'original.

`tests/test_thermal.py` couvre les seuils, le signe, la récupération, six
tenues, les deux facteurs de santé et les commandes réelles sur des cartes
froides ou chaudes. STATUS affiche la température à une décimale,
SHIVERING / SWEATING et HYPOTHERMIA / HYPERTHERMIA quand le facteur passe
sous 95 %. La mort conserve le seuil global de santé 0,3.

## Énergie des frissons : portage vérifié

`tools/re_wind_energy_probe.py` appelle la branche `$5822-$587A` de `m098`,
avec un RTS remplaçant uniquement l'aiguillage disque qui suit. 84 cas
(poids 123, 165, 200 lb ; repos/marche ; frissons oui/non ; pas de 0, 1, 5,
19, 30, 60, 255 minutes) confirment la dépense entière par pas.

`spend_energy` conserve le métabolisme de base dans `s_metabolic` puis,
si le dernier bilan thermique indique des frissons, ajoute 0,04 ×
`body_weight` (165 lb au départ). La somme est stockée/arrondie au format
Applesoft avant multiplication par les minutes, comme dans l'original ;
INT est appliqué au produit. La sueur ne reçoit aucun supplément. Ce coût
s'ajoute au compteur énergétique sans modifier le temps écoulé ni le
métabolisme de base des seuils thermiques. Le déficit alimentaire progresse
à la cadence de santé et reçoit les crédits de repas décrits plus haut.

Le drapeau du **dernier bilan** s'applique au pas qui suit : le nouveau
bilan est calculé après ce pas. La sauvegarde initiale grelotte déjà.
Sur les cartes de contrôle de `test_wind_energy.py`, REST 3 dépense
494 kcal en climat tempéré (30 puis 150 minutes) et 1484 kcal au froid
(30, 60, 60, 30 minutes). Les valeurs incluent l'arrondi entier de chaque
pas ; avec les 600 kcal initiales, les compteurs valent 1094 et 2084.

L'arrondi compte aussi sans frissons : le flottant 1,65 est légèrement
inférieur à sa valeur décimale exacte, donc 30 min coûtent 49 kcal et
60 min coûtent 98 kcal. La phase précédente conservait un coût fractionnaire ;
ce portage applique maintenant INT par pas à toutes les activités.

### Clarification sur le compteur et les commandes d'humidité

`$4BBE` ne peut pas être interprété directement comme une quantité d'eau
sur les vêtements. `m0A5:$5913-$5932` lui ajoute la même variation de poids
que celle ajoutée au poids corporel `$4BF6` après le bilan nutritionnel.
Son rôle précis dans la composition corporelle reste à établir.

Le module divers T15/S0A montre aussi que WET n'agit ici que sur BODY
(nom 158, famille 15), pose le soin 9 ou rejoint la branche eau selon les
conditions. Les messages 214 et 230 le conseillent pour le coup de soleil
ou la chaleur. DRY/WARM rejoint un sélecteur du module divers pour les
objets de famille 1 ; les vêtements mouillés et leur séchage demandent
encore une analyse de ces conditions. Ces commandes restent à porter.

Le vrai sélecteur sec/mouillé est `$4B70` : `m087:$587F` lui donne 2 pendant
SWIM. `m0AC:$5BC0-$5BEC` conserve ce 2, sinon choisit 0/1 selon l'événement
`$4B47`, la protection `$4B86`, l'abri `$0D5E` et la météo `$4B4C` (≥ 2).
`m0B2` choisit alors la table sèche `$4AE6` ou mouillée `$4AF2` et double la
perte globale dans le cas 2. Les anciennes mentions de « grotte » et de
« sac de couchage » étaient erronées : le +25 vient du drapeau du feu,
second jeu d'objets B2[13] (nom FIRE = 88). Le sélecteur d’immersion est maintenant intégré ; les fronts de pluie et
leurs protections restent à relier au modèle météo.


### Vêtements mouillés et immersion vérifiés sur la ROM

`tools/re_wet_probe.py` appelle l'original `m0B2:$5811` sur 54 combinaisons
(sec, mouillé, immergé ; altitude 0/100/227 centaines de pieds ; air
−20/42/100 °F ; métabolisme 1,65/5,2). Il vérifie indépendamment l'indice,
la température effective et la vitesse thermique. Les données originales
locales restent dans `build/`, ignoré par git.

Le terme vestimentaire Q est multiplié par `$4B70` lorsqu'il est non nul :
1 mouillé, 2 immergé. Le global R0 initial vaut 500 sec ou 2000 mouillé ;
l'immersion double aussi R0, soit 4000. L'indice est arrondi après le facteur
lié à `$4BBE`/poids, avec un minimum de 10. Ce facteur reste absent de notre
reconstruction, son sens exact n'étant pas encore établi. Les pertes mouillées
W11 remplacent les pertes sèches W10 ; les couches se combinent de la même
façon. Par exemple PARKA 20→60, SWEATER 60→80, JERSEY 200→2000 et
JEANS 150→1500. La peau nue reconstruite reste 500/200 comme à sec.

Immergé, E = 70 − plancher(0,3 × altitude/100), indépendamment de l'air
et du vent. Notre soustraction signée sur 16 bits préserve les altitudes
extrêmes ; l'original additionne altitude et base sur un octet. La branche
froide est multipliée par 1 + 0,5 × sélecteur (1,5 mouillé, 2 immergé).
La zone chaude peut toujours réchauffer le corps, mais le drapeau de sueur
reste nul lorsque le sélecteur est non nul, comme dans l'original.

Dans le jeu, SWIM suit le cap sur les cases d'eau et s'arrête avant la
première case de terre. WALK permet de sortir vers la rive. Le déplacement
de nage se fait par demi-cases, soit une unité originale par pas cardinal.
T08/S07 `$5B51` prépare le facteur `180 × (poids total + 2) / poids du corps`
en nage normale ; T09/S00 `$5909-$59CC` calcule
`ENT(0,5 + base × facteur × 5 / (6 × RACINE(santé)))`, avec base 0,4
pour un pas droit et 0,567 pour une diagonale. Les coefficients 2, 5 et 6
correspondent aux modificateurs de départ (`$4BBE=2`, `$4B4C=0`, `$4B49=1`) ;
leurs évolutions avec équipement et blessures restent à porter.
`test_swim_cadence.py --original` compare 143 durées sur ROM, en exécutant
la préparation originale puis le calcul du pas, pour trois poids corporels,
six charges et quatre niveaux de santé. Le pas cardinal initial prend
28 minutes. La règle d'admission `$5A0F` accepte le pas si le temps restant
atteint `ENT(durée/2)` ; il est alors consommé entièrement. Un test réel
à santé initiale 4 vérifie deux pas de 39 et 28 minutes pour SWIM 1,
soit 67 minutes consommées. Le module disque WILDTRV porte ces calculs.
L'interface de simulation accepte encore seulement des durées de pas de
1 à 255 minutes ; les durées supérieures sont refusées. Le tracé des caps
obliques suit désormais T08/S07 `$5BFB-$5C94`, puis T09/S00 `$5B35` :
axe majeur entier, accumulateur mineur sinusoïdal et arrondi à chaque pas.
Le cap du port est ramené au degré entier original ; les seuils 46, 135,
226 et 315 sélectionnent l'axe et son signe. La durée utilise les axes
réellement modifiés par ce pas, au lieu de considérer tout cap oblique
comme diagonal. `test_swim_raster.py --original` compare 2 880 positions
(huit pas sur chacun des 360 caps) sur la ROM. L'état de l'accumulateur
reste résident pendant les chargements des autres modules.
L'effort est corrigé d'après T08/S07 `$5AE7/$5D3A` : le métabolisme basal
augmenté de 0,06 × poids total en livres. Avec le matériel initial : 14,43 kcal/min.
Le poids porté en onces est divisé par 16 avec troncature, comme les quatre
décalages de `$50A1`, puis ajouté au poids du corps. Le calcul retire le
double compte de l'eau dans notre représentation de la gourde. La constante
originale `$5CF6` (`7C 75 C2 8F 5D`) est conservée exactement : son dernier
bit diffère de l'arrondi de 0,06 par Python. `test_swim_energy.py --original`
compare 81 valeurs sur la ROM, octet par octet, et compare les dépenses
entières avec et sans frissons à la branche originale de `m098`.
Le premier intervalle de santé de SWIM est fixé à 15 minutes comme `$5AEE`,
même après un repos qui a allongé l'intervalle précédent.
La commande SWIM réelle est aussi vérifiée
sur une carte de lac dans `test_wet.py`. Ces tests isolés ne prouvent pas
encore une traversée complète identique à l'original. Le matériel reste
transporté et ne change pas de place ; les objets en usage et le radeau
restent à comparer dans un parcours réel.
Chaque pas de simulation choisit immersion 2 sur une case d'eau, sec 0
sur terre ; REST dans l'eau conserve donc son refroidissement. Le modèle
original utilise également un sélecteur instantané hors pluie ; aucun temps
de séchage progressif n'est ajouté. Le sélecteur 1 est calculable et testé,
mais attend les événements et fronts pluvieux pour être activé en partie.
