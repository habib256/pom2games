# Parseur, aiguillage des commandes et messages

Analyse du moteur original (face programme + face Journey). Adresses à
l'exécution ; « T$xx/S$yy n » désigne un module de *n* secteurs lu sur la
face Journey en piste SMALLDOS $xx (physique 34 − $xx), secteur $yy, chargé
en `$5800`. Sources : `build/re/*.s` (`tools/re_extract.py`), sondes
`tools/re_parser_probe.py` (une session par commande, modules et messages
observés) et `tools/re_parser_modules.py` (messages et chargements cités par
chaque module). Les textes complets des messages sont extraits en local par
`tools/messages.py` (extractions dans `build/`, hors git). « (?) » marque ce qui reste à confirmer.

## Boucle principale (parseur, `$B000`)

Le parseur est résident en `$B000-$B9FF` (module 9, T$22/S$01 10 secteurs,
rechargé après certains écrans). Points d'entrée : `$B000` → `$0DC0`
(retour d'un module), `$B003` → boucle, `$B006` → saisie seule.

Boucle `$B033` :

1. `$00` = 0 (nombre de messages déjà affichés ce tour).
2. Si `$0B` ≠ 0 (joueur inconscient ou endormi d'office) : verbe forcé à
   20 (REST/SLEEP), sans saisie, et on passe au cœur.
3. Sinon saisie (`$B0AC`), découpage (`$B146`).
4. Aucun mot reconnu (`$06` = 0) : `$0DD2` affiche « WHAT? » (table des
   messages courts de SURV3D, voir plus bas) et on recommence.
5. Verbe LOOK (16) ou PAN/SCAN (36) avec un nom U, D, R, L (149-152),
   F/AHEAD/FORWARD (156) ou B/BACK (157) : bit 7 de `$0D5C`, saut en
   `$0DC6` (SURV3D `$0F21`, réorientation de la vue).
6. Nom 103-108 (T/TOPO, V/VIEW, STAT/STATUS, INV/INVENTORY, HELP, CLUE),
   quel que soit le verbe : module n° nom − 100 via `$0DC3` (`$0DE3`),
   `$0D5F` = 1. 3 = TOPO (cas particulier `$0E03`), 4 = VIEW (redessin
   `$0F21`, pas de chargement), 5 = STATUS, 6 = INVENTORY, 7 = HELP,
   8 = CLUE (ne sert que dans le scénario de la cité perdue).
7. Sinon `$0DD5` (SURV3D `$1051`, préparation de l'écran (?)), chargement
   paresseux du cœur T$05/S$00 8 secteurs en `$5000` (une fois, drapeau
   `$02`) et `JMP $5000`.

### Saisie de la ligne (`$B0AC`)

- Ligne 21 de l'écran (VTAB 20), invite `?` puis espace, effacement de 37
  colonnes ; texte à partir de la colonne 2.
- Tampon `$0200-$0223` (36 caractères au plus, rempli d'espaces `$A0`),
  longueur en `$93`.
- Curseur clignotant : le caractère sous le curseur est affiché en vidéo
  inverse ; pendant l'attente, `$0DD8` (SURV3D `$13E1`) anime la vue quand
  elle est affichée (module 4 actif et `$B8` ≠ 0).
- Touches : → ($95) avance d'une colonne (espace), ← ($88) recule,
  RETURN valide, minuscules ramenées en majuscules ; seules les lettres A-Z
  et l'espace sont acceptés. **Les chiffres sont refusés** : « WALK 1 » est
  lu « WALK », la durée est demandée ensuite (5 NOP en `$B10B` : test
  retiré (?)).

### Découpage et reconnaissance (`$B146`, `$B181`)

- Les mots sont séparés par des espaces ; pour chacun : début `$94`,
  fin `$95`, longueur `$96`.
- La liste à parcourir dépend de la longueur : pointeurs en `$B009`
  (longueur × 2) ; longueurs 1 à 12 : `$B201`, `$B229`, `$B236`, `$B2BE`,
  `$B4B1`, `$B617`, `$B720`, `$B80B`, `$B8AC`, `$B952`, `$B9B3`, `$B9E8` ;
  au-delà, listes vides (`$FF`). Chaque entrée : lettres (bit 7), classe,
  numéro ; `$FF` termine la liste.
- Correspondance exacte du mot entier (pas d'abréviation hors vocabulaire,
  pas de tolérance).
- Résultat en page zéro : `$03` verbe (classe 0), `$04` qualificatif
  (classe 1), `$05` nom (classe 2), `$06` = 1 si au moins un mot reconnu.
  Un mot inconnu est **ignoré** ; un second mot de la même classe remplace
  le premier (« GET AXE KNIFE » → KNIFE).
- Le texte du nom reconnu est copié en `$0300` (terminé par 0) pour la
  substitution `{NOUN}` des messages.

## Cœur : aiguillage (`$5000`, T$05/S$00)

### Prétraitements

- Nom 177 NATURE : module T$12/S$0E (réglage « ENTER NEW WILDLIFE
  FREQUENCY », valeur actuelle 1).
- Qualificatifs : SOCKS (6) + WOOL → 6, + COTTON → **18** (chaussettes de
  coton) ; KIT (41) + FIRSTAID → 41, + SNAKEBITE → **42**, + SEWING →
  **65** ; TABLETS (46) + IODINE → 46, + SALT → **48**. Autre
  qualificatif : message 2 ; aucun : message 17. 18, 42, 48 et 65 sont des
  numéros d'objets absents du vocabulaire.
- Animaux (`$5049-$5089`) : les noms régionaux 180+ sont rangés par
  groupes de 4, région 2 pour 181-183 (COUGAR, RATTLER/RATTLESNAKE), 3 pour
  184-187 (TIGER, ELEPHANT, COBRA, PYTHON), 4 pour 188-191 (CANNIBAL/DANI,
  ADDER, CROC/CROCODILE), 5 pour 192-195 (PUMA, JAGUAR, FER/FERDELANCE,
  ANACONDA), 6 pour 196+ (CAT). Dans la bonne région (`$601F`), le nom est
  **remplacé par un emplacement générique 76-79** : nom − 179 ramené dans
  1-4 par pas de 4, plus 75 (TIGER → 76, ELEPHANT → 77… ; en région 2,
  COUGAR → 77, RATTLESNAKE → 78, BEAR restant 76) ; la région 6 accepte
  aussi PUMA (192). Sinon message 100 (« THE
  {NOUN} LIVES IN ANOTHER COUNTRY »). Les noms génériques 76-79 (BEAR,
  WOLF, MOOSE, 79) ne sont acceptés tels quels qu'en région 1 ; en
  région 2, BEAR (76) seulement. Les quatre emplacements 76-79 sont donc
  les quatre grands animaux de la région courante.
- Remise à zéro des indicateurs du tour (`$4B45`, `$4B77`, `$4B4B`,
  `$4B81`, `$0D90`, `$4B82`, `$4C14/15`), copie d'un flottant Applesoft
  (`$4C25` → `$4C20`) et calcul de `$4C02/03` (moyenne de `$4BF6..$4BFB`)
  : état pour le module du temps (voir survival.md).
- Pas de verbe : message 5 (« OOPS! I DON'T UNDERSTAND YOUR REQUEST… »).
- PACK ou EAT avec TREE (173), BAIT (175) ou SCRUB (176) : message 75.

### Familles de noms (`$06`, `$528E-$5408`)

| Famille | Noms | Remarque |
|---|---|---|
| 1 | 1-21 (vêtements, couchage, sac), 94-97 (HIDE, HUT, IGLOO, TRENCH) | |
| 2 | 22 WATER, 169-171 (RAIN, SNOW, ICE) | BUILD + pluie/neige/glace : msg 21 |
| 3 | 23-37 (nourriture), 82-86 (INSECTS…PLANTS) | |
| 4 | 38-40 (MATCHES, GLASS, FUEL), 87-88 (STICKS, FIRE) | |
| 5 | 41-51 (trousses, comprimés, médicaments, savon), 93 SPLINT | |
| 6 | 52-56 (MAP, COMPASS, WATCH, ALTIMETER, CHART) | |
| 7 | 57-59 (GUN, AXE, KNIFE), 89-92 (BOW, SPEAR, CLUB, ROCK) | |
| 8 | 60-63 (ROPE, PITONS, CRAMPONS, SNOWSHOES) | |
| 9 | 64-75 (CANTEEN…GOLD) | |
| 11 | 76-81 (BEAR…FISH : gibier) | |
| 12 | 98-100 (AIRPLANE, OUTPOST, CITY) | verbes 4-15 et 29-38 : msg 6 |
| 13 | 135-144 (FOOD…LAKE/RIVER : thèmes) | presque tout : msg 17 |
| 14 | 145-157 (directions) | seulement avec LOOK, sinon msg 2 |
| 10 | 110-134 (blessures, maladies) | CURE : msg 17, autres : msg 2 |
| 15 | 158-165 (BODY…HEAD) | selon le verbe |
| 16 | 166-168 (COLD, HEAT, WIND) | verbes 1-3 seulement |
| 17 | 172+ (TREE…, animaux sauvages) | verbes 1-3 seulement |

Les objets 1-81 sont contrôlés dans les tables d'inventaire (`$4D0C`,
`$4D0F`, bit 7 = absent) : message 1 (« SORRY, THAT ITEM IS NOT
AVAILABLE ») si l'objet n'est pas là (voir inventaire, autre analyse).

### Redirections (`$5711`)

Certaines combinaisons sont refusées avec « PLEASE USE '…' COMMAND » :

| Combinaison | Verbe proposé |
|---|---|
| PACK + eau ou CANTEEN ; WEAR/PACK + BACKPACK | CARRY |
| CARRY + HIDE, nourriture ou gibier | PACK |
| BOIL/DRY + nourriture ou gibier | COOK |
| COOK/DRY + eau | BOIL |
| EAT + eau | DRINK |

### Verbes

« Module » : gestionnaire chargé et exécuté en `$5800` par `$03DB`
(`$1E` = sélecteur passé au module). « Temps » : `$4D00`, le moteur qui fait
passer le temps et enchaîne les modules d'état (voir survival.md).

| N° | Mots | Aiguillage | Module | Observé |
|---:|---|---|---|---|
| 1 | CATCH, FIND, GET | eau → module eau ; gibier → chasse ; 98-100 → msg 21 ; objets 1-81 → CARRY ; sinon msg 17 ; FOOD → `$4B75` = 0, msg 33 | T$0F/S$00 7, T$0F/S$07 6 | GET WATER : « FROM THE GROUND [G] OR FROM YOUR CANTEEN [C] ? » |
| 2 | USE | `$1E` = 0 | T$11/S$00 7 | USE COMPASS : msg 10 |
| 3 | BUILD, MAKE | eau → module eau ; famille 17 → USE `$1E`=17 ; famille 4 (feu) → USE `$1E`=4 ; familles 1, 5, 7 → fabrication ; 8, 9 → fabrication 2 (`$1E`) ; sinon msg 21 | T$10/S$00 5, T$10/S$05 7, T$11/S$00 7 | MAKE SPEAR : msg 76 ; MAKE HUT : msg 49 |
| 4 | SKIN | gibier → dépeçage ; nourriture → msg 18 ; sinon msg 2 | T$11/S$07 8 | |
| 5 | WEAR | `$1E` = 0 | T$0D/S$0F 3 | WEAR PARKA : msg 10 |
| 6 | PACK, STORE | sac à dos requis (msg 194), `$1E` = 1 | T$0D/S$0F 3 | PACK AXE : msg 11 |
| 7 | CARRY, TAKE | eau → module eau ; sinon temps (transaction) | T$0F/S$00 ou `$4D00` | CARRY AXE : msg 10 |
| 8 | DROP, REMOVE | `$1E` = 1 | T$0D/S$0F 3 | REMOVE SOCKS : msg 17 (qualificatif requis) |
| 9 | BOIL | eau → module eau ; nourriture → repas ; gibier → dépeçage ; sinon msg 3 | T$0F/S$00, T$12/S$00 8, T$11/S$07 | |
| 10 | DRINK | eau → module eau ; famille 5 → divers `$1E`=10 ; gibier → msg 6 ; sinon msg 19 | T$0F/S$00, T$12/S$08 6 | DRINK WATER : choix G/C |
| 11 | COOK, FRY | comme BOIL | idem | COOK FISH : msg 1 sans poisson |
| 12 | EAT | comme BOIL ; famille 5 → `$1E`=10 | idem, T$12/S$08 | EAT CHEESE : msg 32 (quantité en onces) |
| 13 | DRY, WARM | divers | T$15/S$0A 1 | |
| 14 | COOL | `$1E` = 14 | T$12/S$08 6 | |
| 15 | CURE, HEAL, TREAT | eau → msg 17 ; gibier → msg 36 ; sinon msg 18 ; blessures → msg 17 (n'atteint aucun module) | — | CURE CUTS : msg 17 |
| 16 | LOOK | + U/D/R/L/F/B → vue ; + direction ou SUN… → module LOOK ; seul → msg 5 | T$0F/S$0F 1 → T$10/S$0C 4 | LOOK N : msg 42 sans boussole |
| 17 | ATTACK, KILL | gibier → chasse ; INSECTS → msg 10 ; sinon msg 20 | T$0F/S$07 6 | |
| 18 | SCARE | comme ATTACK | idem | |
| 19 | PAUSE, WAIT | durée en heures (msg 27) | T$15/S$0B 5 | |
| 20 | REST, SLEEP | idem ; forcé si `$0B` ≠ 0 | T$15/S$0B 5 | |
| 21 | CAMP | idem | T$15/S$0B 5 | |
| 22 | GO, WALK | déplacement, durée en heures ; avec une direction : msg 252 | T$08/S$00 1 → T$08/S$01 6 → T$08/S$07 8 | |
| 23 | RUN | idem | idem | |
| 24 | SWIM | idem ; hors de l'eau : msg 23 | idem | |
| 25 | CLIMB | sans nom ou U → déplacement ; D → seulement dans un arbre (`$4B40`) ; TREE : arbre proche (`$D7`, sinon msg 16), condition physique (flottant, sinon msg 59), puis `$4B40` = 1, msg 10 ; dans l'arbre, `$4B40` = 0 | T$08/S$00 | CLIMB TREE : msg 16 |
| 26 | DOUSE, STOP | BLEEDING → `$4B41` = `$4B42` = 1, 30 min, temps ; gibier → ATTACK ; FIRE → éteint, msg 10 ; météo → msg 21 ; sinon msg 2 | `$4D00` | STOP BLEEDING : chaîne du temps |
| 27 | MOVE | déplacement | T$08/S$00 | seul : msg 17 |
| 28 | PADDLE, ROW | déplacement | T$08/S$00 | hors de l'eau : msg 23 |
| 29 | LOWER | divers | T$15/S$0A 1 | |
| 30 | SHIELD | divers | T$15/S$0A 1 | SHIELD EYES : msg 10 |
| 31 | CUT | `$1E` = 14 (même sélecteur que COOL (?)) | T$12/S$08 6 | |
| 32 | SUCK | `$1E` = 32 | T$12/S$08 6 | SUCK VENOM : msg 2 sans morsure |
| 33 | WET | divers | T$15/S$0A 1 | |
| 34 | HANG | divers ; FOOD → famille 13 | T$15/S$0A 1 → T$12/S$08 | HANG FOOD : msg 16 sans arbre |
| 35 | SAMPLE, TASTE | eau → module eau ; sinon `$1E` = 35 | T$12/S$08 6 | |
| 36 | PAN, SCAN | + U/D/R/L/F/B → vue ; sinon divers ; seul → msg 5 | T$15/S$0A | |
| 37 | IGNORE, SKIP | FOOD → `$4B75` = 1, msg 10 | — | |
| 38 | FLAG | FOOD → `$4B75` = 0, msg 10 | — | |
| 39 | EXIT, LEAVE | `$1E` = 39 | T$12/S$08 6 | seul : msg 5 |
| 40 | ENTER | `$1E` = 40 ; SHELTER seulement si un abri existe (`$4BA1` = 1) | T$12/S$08 6 | ENTER SHELTER : msg 17 sans abri |
| 41 | SAVE | sauvegarde | T$13/S$0C 7 | |
| 42 | RESTORE | reprise | T$14/S$03 5 | |
| 43 | CRAWL | déplacement | T$08/S$00 | |
| 44 | EXERCISE | comme REST | T$15/S$0B 5 | |

`$4B75` vaut 1 quand le joueur demande d'ignorer les sources de nourriture
pendant la marche (message 33 : la marche est interrompue sinon).

### Modules et messages cités

| Module | Rôle | Messages | Enchaîne |
|---|---|---|---|
| T$08/S$00 1 | déplacement : état, arbre, feu | 95, 97, 132, 182 | T$08/S$01 6 (puis T$08/S$07 8), T$06/S$04 6 |
| T$0D/S$0F 3 | WEAR, PACK, DROP | 2, 11, 15, 32, 38, 49, 64, 87, 105, 109, 110 | T$11/S$00 |
| T$0F/S$00 7 | eau (sol, canteen, condensation, cactus) | 1, 2, 25, 27, 32, 50, 54-57, 60-65, 87, 179, 186, 192 | — |
| T$0F/S$07 6 | chasse, pêche, effaroucher | 0, 11, 25, 27, 39, 56, 66-68, 70, 72, 86, 120-122 | T$06/S$04 |
| T$0F/S$0F 1 | LOOK | 0, 12 | T$10/S$0C 4, T$11/S$00 |
| T$10/S$00 5 | fabrication (corde, peau, attelle, arme, abri) | 2, 4, 15, 21, 25, 35, 53, 76, 92, 101, 205 | — |
| T$10/S$05 7 | fabrication 2 (corde, couture, poterie, hameçons) | 2, 10, 21, 24, 26, 45, 51, 65, 67, 76, 107, 113, 114, 116, 206, 207 | — |
| T$11/S$00 7 | USE (abri, arbre, lampe, crampons, appât, feu) | 1, 2, 9-11, 15-18, 25, 53, 75-79, 82-85, 171 | T$12/S$08 |
| T$11/S$07 8 | dépeçage, nourriture du sac ou du sol | 2, 11, 27, 32, 38, 64, 65, 71, 87, 198-200 | — |
| T$12/S$00 8 | manger, cuisiner | 1, 2, 27, 31, 32, 64, 65, 71, 87 | — |
| T$12/S$08 6 | divers (`$1E`) : boire un remède, refroidir, sucer, goûter, sortir, entrer, pendre | 2, 6, 10-12, 16-19, 21, 25, 39, 49, 71, 87, 111, 117, 118, 124, 183, 184, 193 | T$0F/S$07 |
| T$12/S$0E 2 | NATURE (fréquence de la faune) | — | — |
| T$13/S$0C 7 | SAVE | — | lit T$11/S$0F |
| T$14/S$03 5 | RESTORE | — | relit carte et parseur |
| T$15/S$0A 1 | verbes divers | 2, 11, 17, 86 | un module en page `$58` (?) |
| T$15/S$0B 5 | WAIT, REST, CAMP, EXERCISE | 2, 9, 27, 95 | temps |
| T$0E/S$02 8, T$0E/S$0A 6, T$06/S$00 2 | transactions d'inventaire, poids et volume (après WEAR, PACK, DROP, CARRY, USE…) | 7, 10, 11, 17, 34, 88 ; 10, 34, 40 | — |
| T$06/S$04 6 | rencontres animales | 67, 69, 70, 73, 74, 132 | T$08/S$01 |
| T$09/S$05 3 → T$09/S$08, T$0A/S$05, T$0A/S$0C, T$0B/S$02, T$0B/S$07, T$0B/S$0D | passage du temps (survival.md) | — | — |

Écrans par nom : TOPO lit T$05/S$08 4 puis exécute T$01/S$0B 5 ; STATUS
lit T$06/S$0A 7 puis exécute T$07/S$01 5 et T$14/S$08 8 (libellés) ;
INVENTORY lit T$07/S$08 8 ; HELP T$13/S$00 8 ; CLUE T$15/S$00 5 ;
VIEW ne charge rien.

## Messages

### Messages courts (SURV3D `$0ED8`)

Table de chaînes terminées par 0, affichées par `$0EB4` (bip, ligne 21,
`>`) avec X = position du message : WHAT?, NOT ENOUGH LIGHT, INSIDE
SHELTER, NOT AVAILABLE, PLEASE WAIT, NOT NOW!.

### Messages numérotés (cœur `$4E78`)

- 256 messages de 64 octets, quatre par secteur, sur les pistes SMALLDOS
  $18-$1B de la face Journey. Message X : secteur k = (X − 1) >> 2, piste
  $18 + k / 16, secteur k mod 16, emplacement (X − 1) mod 4.
- Chaque affichage relit le secteur en `$0200` (`$03DE`, 1 secteur).
- Format : caractères avec bit 7 ; 0 termine ; un message sans 0 se
  poursuit dans l'emplacement suivant (13-14, 29-30, 107, 114…). Les
  lignes sont mises en page par des espaces pour 40 colonnes ; `$8D` force
  un retour à la ligne.
- Substitutions (octets 1-127) : 1 → le nom tapé (`$0300`) ; 2-3 → nom
  d'animal de la carte (`$60D0` + 12 × (`$0F` − 1) : BEAR, COUGAR,
  RATTLESNAKE…) ; 4 et plus → nombre `$0F:$0E` (LINPRT d'Applesoft).
- Affichage : ligne 21 (VTAB 21), effacement jusqu'en bas, `>`, espace,
  texte. Si un message a déjà été affiché pendant ce tour (`$00` ≠ 0),
  bip et attente d'une touche avant le suivant.
- Points d'entrée : `$4D21` affiche X puis revient à la boucle
  (`JMP $B000`) ; `$4D2A` affiche X et continue ; `$4D24` range A en
  `$0E` et Y en `$0F` puis affiche ; `$4D27` range Y en `$0F` puis
  affiche.

Exemples (citations courtes) : 1 « SORRY, THAT ITEM IS NOT AVAILABLE. »,
5 « OOPS! I DON'T UNDERSTAND YOUR REQUEST. CHECK PLAY MANUAL. », 10 « OK,
WHAT NEXT? », 17 « TRY TO BE MORE SPECIFIC. », 27 « SPECIFY TIME IN
HOURS. », 32 « PLEASE SPECIFY AMOUNT IN OUNCES. », 252 « USE SIMPLE VERB
TO MOVE IN DIRECTION YOU ARE FACING. ».

## Saisies complémentaires (cœur)

| Entrée | Rôle |
|---|---|
| `$4D2D` | Ligne de saisie : VTAB 20, `?`, 38 colonnes effacées, colonne 2 |
| `$4D30` | Nombre de 1 à 3 chiffres (`$96` = 3) : chiffres, ← → RETURN ; valeur en `$0F:$0E` (`$4F99`, ≤ 999) |
| `$4D33` | Même saisie, longueur `$96` fixée par l'appelant ; `$95` bit 6 autorise le point |
| `$4D36` | Conversion du tampon de chiffres en nombre |
| `$4D39` | Choix d'une touche : X = touche 0, Y = touche 1 ; renvoie A = 0 ou 1 (Y/N, G/C, A/N, E/W, P/G…) |

## État du portage du parseur

La réimplémentation dispose de la saisie, des 280 mots, de la reconnaissance
par longueur et mot exact, des qualificatifs et des écrans de base. Elle
n'implémente pas encore toutes les familles d'actions de l'aiguillage original.
Les commandes disponibles sont dans le [README](../../README.md#commandes).

Il reste à porter les familles d'actions, leurs saisies complémentaires,
HELP et les messages associés, avec les substitutions nécessaires. Les
textes originaux servent de référence locale ; les messages du jeu sont
réécrits. L'ordre de travail est dans le [TODO](../../TODO.md).

## Points ouverts

- `$0DD5` (SURV3D `$1051`) et `$0DD8` (`$13E1`) : rôle exact pendant la
  saisie (animation de la vue (?)).
- Verbe 7 CARRY sur un objet et verbe 1 sur un objet : passage direct au
  moteur du temps `$4D00` ; la transaction réelle est dans T$0E/S$02 (à
  confirmer avec l'analyse de l'inventaire).
- CUT reçoit le même sélecteur que COOL (`$1E` = 14) : erreur de l'original
  ou partage voulu (?). Vérifié sur ROM (lot 13) : COOL BODY et CUT BODY
  donnent tous deux le soin 7 avec un outil en usage ; seules les familles
  4-9 et le gibier les distinguent.
- T$15/S$0A charge T$12/S$08 6 (`$1E` = 13 ou 34) ou T$0F/S$00 7 (WET BODY
  hors pluie et hors de l'eau, nom WATER) ; résolu au lot 13
  ([IMPLEMENTATION.md](../IMPLEMENTATION.md) « Soins, alertes et maladies »).
- Noms 109 (sélecteur 9) et blessures 110-134 : sans gestionnaire atteint
  depuis l'aiguillage ; utilisés par HELP (?).
- Correspondance animaux / régions (`$5049-$5089`) à détailler.
