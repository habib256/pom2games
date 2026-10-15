# Neowilderness — travail restant

Port de Wilderness (Electric Transit, 1985) pour Apple IIe enhanced 128 Ko et
IIc, ProDOS 8, paysage DHGR, en deux éditions : Neowilderness
(`dist/NEOWILDERNESS.po`, 5,25 pouces, 140 Ko, la Sierra seule) et
NeoWildernessXL (`dist/NEOWILDERNESSXL.po`, 3,5 pouces, 800 Ko, les six
scénarios). Ce fichier ne garde que ce qui reste. Il suit les lots de jeu
d'[ORIGINAL_GAP.md](docs/ORIGINAL_GAP.md) § 3 (numéros, tailles, nature
« ajout » ou « fidélité »), puis trois sections hors lots : interface,
image, qualité. Ce qui est fait est décrit dans [CHANGELOG.md](CHANGELOG.md).

**Prochain lot : 6, sites (reste)** : le lot 3, fabrication, est fait le
15 octobre 2026 (recettes de MAKE, page CRAFT, second jeu dans la grille,
sprites des abris sur XL : [CRAFT.md](docs/CRAFT.md), CHANGELOG.md). Le
lot 4 est fait (14 octobre 2026, CHANGELOG.md, [FORAGE.md](docs/FORAGE.md)
§ 17), la grille rationalisée aussi (15 octobre 2026,
[MENUS.md](docs/MENUS.md) § 4) ; le lot 6 en partie (sprites de site,
15 octobre 2026). TEXT (2 octets), WILDLO (0), RESIDENT (5), LOWPAGE (1)
et MENUSWAP (0) sont pleins, MENUCODE presque (4), WILDERNESS 2, WILDGAME
2 : l'état d'un lot futur ira dans un module ou demandera une récupération
([MEMORY.md](docs/MEMORY.md) § 16 à 28) ; l'édition de 140 Ko est pleine
(280 / 280 blocs), son NEOWILD.DAT 69 octets avant un bloc de plus ; le
stock de XL a 241 octets de place de tronc (§ 28, la grille compressée).

**Règle de sortie.** Une entrée est faite quand son « Terminé quand » est
vrai, tests à l'appui ; le même jour, elle quitte ce fichier et devient une
puce de CHANGELOG.md (« Non publié », avec le commit ou la date). Aucune
case cochée ne reste ici. « En cours » : deux lots au plus (un agent par
lot, un seul qui construit dans l'arbre).

## Marges (MEMORY.md § 29, 15 octobre 2026, post-its et pages restructurées)

| Zone | Libre |
|---|---:|
| TEXT `$0A00-$0FFF` | 2 |
| WILDLO `$1000-$1FFF` | 0 |
| WILDGAME `$4000-$577F` | 11 |
| WILDERNESS `$6000-$6FFF` | 2 (XL : et 1 dans `page_foot`, code mort de XL) |
| RESIDENT `$B600-$B9FF` | 5 |
| MENUCODE `$BA00-$BDFF` | 4 |
| LOWPAGE `$0200-$03CF` | 1 |
| HICODE / MENUSWAP / banque 2 principale | 3 / 0 / 24 |
| SIM sous `$B500` | 156 |
| Stock auxiliaire, place du tronc : XL / 140 Ko | 6 114 / 679 |
| Disque occupé : XL / 140 Ko | 372 / 1 600 ; **280 / 280** blocs (`read_volume.py`) |
| NEOWILD.DAT de 140 Ko avant un bloc de plus | **95** octets |
| PROJECT (fenêtre `$5800`, 2 048) : XL / 140 Ko | **46** / 166 (queue des abris coupée) |
| CRAFT (fenêtre `$9600-$A5FF`, 8 blocs ; MAKE en lit 4 : 170 libres) / MEDICAL (`$5800`) | 13 / 25 |
| STATUS partagé (`$9600-$AEFF`, sous STATX) / TOPOGEN (`$9600-$A1FF`, avant `TOPOBSS`) | 94 / 75 |
| SUMMARY (`$5800`) / GRID (`$A300-$AFFF`) | 1 / 652 |
| Queues de XL (MENUS.md § 9.1) : STATX (`$AF00-$B5FF`) / CRAFTX (jusqu'à `$A7FF` pour 9 blocs ; au-delà, sous le tampon des cadres) / MEDVX / ENDX | 696 / 300 / 361 / 320 |
| STATUS de XL sur NEOWILD.BLK (`$9600-$B5FF`, 16 blocs au plus) | 696 octets (15 blocs) |

Les coûts du tableau ci-dessous viennent d'ORIGINAL_GAP.md § 3 et de
FORAGE.md § 15 ; « à chiffrer » veut dire qu'aucune mesure n'existe. Un lot
qui touche le chemin de référence rebase d'abord `test_reference_state.py`.

## Lots de jeu

| Lot | Contenu | État | Preuve | Résident | Stock 140 Ko | Stock XL | Disque |
|---|---|---|---|---:|---:|---:|---|
| 0 | Place | fait (§ 12 à 15) ; marges ci-dessus | MEMORY.md § 15 | — | — | — | — |
| 1 | Préparation et niveaux | fait ; reste relief par niveau, verdict de STATUS, mode recherche en jeu | `9642e39`, `test_prepare.py --original` | ≈ 60 (SIM) | 0 | 0 | XL : une carte par niveau, à chiffrer |
| 2 | Feu, lumière, eau | fait | `d0aebf5`, `test_camp.py` | — | — | — | — |
| 3 | Fabrication : recettes de MAKE (A1, A2, D4), page CRAFT, sprites des abris | fait (15 octobre 2026) | `test_craft.py --original`, `test_craft_page.py`, `test_sites.py`, CRAFT.md § 8 | 12 octets (LOWPAGE) + 6 (WILDERNESS) + 3 (WILDLO) ; page : 0 | grille et panneau : 287 octets ; pas de sprite d'abri | 287 octets ; sprites d'abri : 0 (NEOWILD.BLK) | CRAFT : 8 blocs sur les deux (page lisible, MEMORY.md § 25) ; abris : 8 blocs sur XL |
| 4 | Chasse, pêche, cueillette, repas | fait ; restent les seuils d'ATTACK selon la lumière (lot 11) ; arc, lance, gourdin, pierre faits (lot 3), contre les animaux aussi | `test_forage.py --original`, FORAGE.md § 17 | 989 | +1,4 Ko (TREE, ORIENT sur disque) | +1,4 Ko | FORAGE : 12 blocs sur les deux |
| 5 | Fabrication 2 et radeau | ouvert ; recettes mesurées (CRAFT.md § 6) | — | à chiffrer | non | à chiffrer | dans CRAFT (2 Ko de place dans sa fenêtre) ou CRAFT2 ; RIVER |
| 6 | Sites (socle « sprite de site », poste, bille, rocher), messages de terrain, JUNGLE | ouvert | sprites extraits | à chiffrer | non (sprites) | 2,4 à 4,7 Ko de sprites : en partie | à chiffrer |
| 7 | Orientation | fait | `5126d5b`, `test_orientation.py` | — | — | — | — |
| 8 | HELP classé, résurrection, score original (E1, E2), aide par région | ouvert | — | à chiffrer | 0 si HELP lu à la commande | idem | ≈ 3,5 Ko |
| 9 | SAVE / RESTORE | fait | `640e6e0`, `test_save.py` | — | — | — | — |
| 10 | Cité perdue (CLUE, vestiges, statue) | ouvert | — | à chiffrer | XL seul | sprite 2,4 Ko | ≈ 3 Ko |
| 11 | Faune complète (durée, déplacements, RUN, feu et animaux) | ouvert | — | 0,6 Ko (WILDOUT scindé) | à chiffrer | à chiffrer | — |
| 12 | Terrain, pentes, risques, REST interrompu par la météo | ouvert, **fidélité** | — | 1,0 Ko (TRAVEL, SIM) | à chiffrer | à chiffrer | — |
| 13 | Médecine | fait ; reste les chutes | `868d9fa`, `test_care.py --original` | — | — | — | — |
| 14 | Conteneurs et charge (P3) | ouvert, **fidélité** | — | 0,3 Ko (ITM, GDATA) | — | — | — |
| 15 | Régions : R1, R2, géographie fine (R3) | ouvert | REGIONS.md § 7 | 0,1 Ko | Sierra seule | atlas : partage `$D000-$F0FF` avec l'instantané TOPO | XL : ≈ 13 blocs par atlas |
| — | TMAKE, générateur de terrain | ouvert, XL | — | à chiffrer | — | à chiffrer | à chiffrer |

Ordre proposé : 3 → 6 → 8 → 5 → 10 → 11 → 15 → 12 → 14
(ORIGINAL_GAP.md § 3). Les lots de fidélité 12 et 14 viennent ensemble, en
dernier, sur une référence rebasée une seule fois.

### Lot 1 — reste : niveaux

- [ ] Relief par niveau : une carte par région et par niveau sur XL, choisie
  par le chargeur (`mkmap.py --level` applique déjà TMAKE).
- [ ] Facteur de niveau du verdict de STATUS (×0,85 dès 3, ×0,7 dès 8) ;
  effets en jeu du mode recherche (SCENARIOS.md § 11.4).

**Terminé quand :** un voyage au niveau 1 et au niveau 10 a le relief, le
verdict et le score de l'original (`test_prepare.py --original` étendu).

### Lot 6 — sites (reste)

Fait le 15 octobre 2026 : le socle « sprite de site », le rondin ou le
rocher de l'abri naturel trouvé sur carte native, le poste des rangers
(CHANGELOG.md, MEMORY.md § 19). Reste :

- [ ] Plusieurs sites projetés par vue (aujourd'hui le plus proche
  seulement), un sprite par code de site (table SURV3D `$1D0D`) : la
  tente, la hutte, l'igloo et la tranchée sont venus avec le lot 3 (XL),
  la cité perdue viendra avec le lot 10 (même chemin : NEOWILD.BLK,
  fenêtre SIM) ; la vue vers le bas à l'arrivée sur un site sans bit 7
  (`$E7` = −1, CRAFT.md § 8.4).
- [ ] Messages de terrain et mot JUNGLE (régions 3 à 5).

**Terminé quand :** les sites de l'original sont visibles dans la vue et
sur TOPO dans les six régions (`test_sites.py`, `test_sprites.py`).

### Lot 8 — HELP, score original, aide par région

- [ ] HELP classé de l'original (msg 223, 249, 224…), pénalité isolée ;
  phrase de faune et noms d'espèces par région.
- [ ] Résurrection et score original (E2), à côté du score du port.

**Terminé quand :** HELP rend les messages de l'original dans les six
régions (sonde ROM), le score original est affiché à la fin.

### Lot 5, 10, 11, 12, 14, 15 et TMAKE

- [ ] Lot 5 : fabrication 2 (recettes mesurées : [CRAFT.md](docs/CRAFT.md)
  § 6, cas A3 de `results.json` écartés de `test_craft.py`), radeau,
  PADDLE/ROW.
- [ ] Lot 10 : scénario de la cité perdue (CLUE, vestiges, statue,
  introduction, hall of fame à 12 tables) ; XL seul.
- [ ] Lot 11 : seuils d'ATTACK des animaux selon la lumière (`$19` = 2 −
  `$0D5D`, FORAGE.md § 3.4 : blessure ÷ 2 et réussite × 2 de jour ;
  OUTDOOR garde ceux de nuit, pour les cinq moyens : les armes du lot 3 et
  le fusil arment déjà ATTACK, CRAFT.md § 8.5) ; SCARE et vol de
  nourriture des cas `scare bear`, `kill bear gun light 1 rnd 0.3501` de
  `results.json`.
- [ ] Lot 11 : faune complète (durée de présence, déplacements, RUN) ;
  **à vérifier** d'abord : le feu n'a aucun effet sur les animaux dans le
  port (animals.md l. 95) ; sonde `re_animal_reactions_probe.py` avec
  B1[FIRE] = 0.
- [ ] Lot 12 : pentes, risques de déplacement, REST interrompu par la
  météo (**fidélité**).
- [ ] Lot 14 : capacités des conteneurs selon le poids (`$4BF8`, `$4BEE`,
  `$4BF2`) (**fidélité**) ; poids du second jeu, aujourd'hui nul (arc et
  lance 50 oz, gourdin et pierre 100, attelle 50 : CRAFT.md § 4.1 ;
  l'original refuse GET ROCK au départ).
- [ ] Lot 15 : terrain et altitude de base par région, gravité des
  blessures, branches non sondées (radeau, cannibales ; REGIONS.md § 7) ;
  géographie fine des six régions — décision de jeu (la simulation des
  cartes héritées changerait) ; pistes : résolution réduite (1–2 Ko) ou
  atlas de la Sierra seule.
- [ ] TMAKE, générateur de terrain, pour XL.
- [ ] Lot 13, reste : les chutes (IMPLEMENTATION.md, « Conditions
  médicales »).

**Terminé quand (fidélité, ensemble) :** un trajet crash → rangers
complet concorde avec l'original dans la Sierra (`make test-original`,
avec repas, eau, repos, cabane, rencontres, soins, nage et retour sur la
rive, variantes de mort et de blessures ; ADVENTURE_TESTS.md), les cinq
autres régions suivent leurs fiches sondées, et la géographie retenue est
documentée avec ses écarts mesurés. Règle permanente : l'ordre des tirages,
les demi-pas et leurs coûts restent ceux de l'original
(`test_reference_state.py` vert à chaque changement du moteur).

## Hors lots : interface et expérience de jeu

- [ ] Joystick (étape 1 de [MENUS.md](docs/MENUS.md) § 8) : pilote dans la
  boucle `idle` de `src/menu.s`, selon le modèle de navigation du
  14 octobre (vue, pages du haut, pages du bas, niveaux de focus).
- [ ] INVENTORY avec actions par objet (étape 5) ; parcours d'un nouveau
  joueur au joystick seul (étape 6).
- [ ] REST et les chargements de simulation gardent l'image DHGR au lieu du
  rideau texte (`load_totals_quiet` n'est utilisé que par INVENTORY).
- [ ] Fin de partie : ne pas réécrire le hall of fame quand rien ne change
  (1,9 s ; message à chaque voyage sur disquette protégée ; HOF.md l. 333).
- [ ] Messages : refus précis, retours persistants, causes d'arrêt nommées
  pour toutes les actions (NEOWILDERNESS_ERGONOMIE.md).
- [x] Pages en MouseText sur NeoWildernessXL (15 octobre 2026,
  [MENUS.md](docs/MENUS.md) § 9, MEMORY.md § 26) ; l'édition de 140 Ko
  garde ses pages sans cadre (décision de l'utilisateur). Restent sans
  cadre : HELP (onglets et pied de page seulement), l'écran H du menu de
  départ et la fin de partie d'ADVENTURE (40 colonnes, chargeur et stock :
  pas de place sans queue ni lecture) ; le stock de XL n'a plus que
  315 octets.
- [x] Bas sur TOPO ou MAP : les pages du haut (15 octobre 2026, les deux
  éditions, MENUS.md § 5).
- [ ] Mettre à jour le tableau des verbes d'ORIGINAL_GAP.md § 1.2, puis
  relever toutes les commandes qui aboutissent à `m_notyet`
  (liste exhaustive et chiffrée).

**Terminé quand :** une partie complète se joue au joystick seul, du menu
à la fin ; aucune commande d'interface ne montre le rideau texte ; la
liste `m_notyet` est publiée et ne contient que des lots ouverts.

## Hors lots : image et ambiance

- [ ] Optionnel : `LOOK STARS` enrichi (repères nommés, azimut et hauteur ;
  STARS.md § 11, référence Python prête) ; le LOOK STARS de l'original est
  porté (lot 7).
- [ ] Lune visible de jour et au crépuscule (le moteur ne calcule qu'un
  astre) ; lune gibbeuse graduée si l'état comparé le permet.
- [ ] Humeurs et palettes par région après visionnage sur les six cartes
  (nuits trop vertes, bleu foncé trop lumineux, dégradés).
- [ ] Moniteur composite réel : franges, traits d'un pixel, texte
  80 colonnes, gris de POM2.
- [ ] Rendu : coût d'une vue (0,5 à 0,9 s), rotations, TOPO en 3 s ; double
  tampon seulement si 16 Ko se libèrent.
- [ ] Captures de référence par région et par humeur dans `build/dhgr/`,
  comparées par les tests d'image (`test_dhgr_ref.py --refs` produit les
  PNG, rien ne les compare).

**Terminé quand :** les six régions ont leur palette validée à l'écran, les
étoiles sont testées sur les deux banques, et aucune commande d'affichage
n'est plus lente que la mesure publiée de plus de 5 %.

## Hors lots : mémoire, qualité et livraison

- [ ] Démarrage : réduire les 21 s jusqu'au menu et les 10 s du choix à la
  première vue (chiffres du 13 octobre, Disk II) ; remesurer sur les deux
  éditions, XL sur SmartPort.
- [ ] **à vérifier** — banque 2 de la carte principale (`$D001-$D0FF`
  décodeur LZ, `$D100-$D3FF` relais B2, `$D400-$DFFF` lignes DHGR) sous
  d'autres versions de ProDOS et sur IIc (`test_prodos.py` avec un autre
  PRODOS).
- [ ] **à vérifier** — garde-fous pile et interruptions (page zéro,
  banques, RESET, QUIT, machine incompatible, `/RAM` : `test_prodos.py`).
- [ ] Suite de tests en niveaux : rapide (modèles Python et bancs, moins de
  deux minutes), complète (émulateur, ≈ 83 étapes), originale
  (`test-original`) ; ce que chaque test garantit.
- [ ] Machines : IIc (a2shot n'émule que le IIe), machine réelle avec carte
  DHGR et lecteur 3,5", `make run` des deux éditions dans POM2.
- [ ] Git : commiter le travail du 14 octobre, ajouter les fichiers non
  suivis, retirer `neowilderness/--help` (voir DOCS.fixes.md).
- [ ] Bogue latent possible : quand l'image du module ALERT dépasse $700
  octets, test_care (WARM PARKA) plantait dans le Moniteur (chemin MVI
  care_dry → have → t_update puis BRK), même avec la routine ajoutée
  réduite à RTS : cause non trouvée ; ALERT est à $6C2 aujourd'hui.
- [ ] Livraison : README, CHANGELOG, relevé mémoire final, crédits des
  données originales, limites restantes ; les deux `.po`.

**Terminé quand :** la suite rapide passe en moins de deux minutes, la
suite complète est verte, les deux `.po` démarrent sur IIe et IIc, chaque
région démarre avec une marge auxiliaire documentée, le volume XL garde au
moins dix blocs libres après les sauvegardes, et le dépôt contient
l'historique des lots.

## Décisions en attente

Revue des verbes du 14 octobre 2026 ; la grille rationalisée du
15 octobre a tranché GET/TAKE (un seul GET, destination automatique),
REST/WAIT (gardés tous deux), WEAR (bascule au lieu d'une page OUTFIT),
MAKE STICKS (hors grille) et BOIL (proposé seulement avec un feu ou le
réchaud) : CHANGELOG.md, MENUS.md § 4. Chaque réponse restante devient une
ligne de lot ou une ligne « Retiré ».

- **Sondes ROM de la revue des verbes.** `WEAR SLPNG BAG`, `WEAR TENT`,
  `WEAR GND COVER` : le modèle médical les suppose portés
  (`med_full_cover`, `game.s:1939-1952`) alors que WEAR les refuse ;
  destination de GET dans l'original (`GET AXE` puis B1[58] : main ou
  sac ?, `parser.md:148` ; mesuré le 15 octobre dans la vraie partie :
  B1[58] = 3, en main, comme GET du second jeu, CRAFT.md § 4.1 ; le port
  met la hache dans le sac) ; BOIL : une seule ébullition protège-t-elle de
  la giardiase pour tout le voyage (sélecteur 22 jamais remis à zéro alors
  que l'iode l'est ; puis +1 octet dans `hz_daily`) ?
- **Édition de 140 Ko : deux blocs libres.** CRAFT a pris 2 blocs (6 au
  lieu de 4) pour la page, le retrait de la durée de vie du feu en a rendu
  un (NEOWILD.DAT, 51 octets avant d'en reprendre un) ; la prochaine
  croissance du disque de cette édition (lot 6, 8, 10) demandera de la
  place reprise (NEOWILD.BLK : le module FIRE, 1 701 octets depuis le
  feu remonté, tiendrait en 3 blocs au-dessous de 1 536 ; ou moins de
  parties sauvées : 5 × 5 blocs).
- **Restes de la grille.** Garder le module FORAGE entre deux étapes de la
  file (aujourd'hui relu à chaque étape : 12 blocs sur 140 Ko) ; gestes
  DRY et HANG dans la page MEDICAL (`WET`, vêtements mouillés) ; onces de
  COOK et heures de CATCH en ligne dans les listes, comme `BOIL WATER n
  OZ` (aujourd'hui l'invite numérique les demande).
- **Petits défauts relevés le 14 octobre.** Pluriel « 1 HOURS »
  (`textbank.txt:21-22`) ; `MAKE` seul répond « NOT IN THIS VERSION
  YET. » au lieu de « WHAT? » (CAMP +6) ; l'invite de `BOIL WATER` tapé
  annonce 128 oz pour 64 disponibles (`w_avail`, CAMP +10) ; à
  revérifier depuis la bascule WEAR : la liste omet SUNGLASSES et WATCH,
  REMOVE jette au sol, PACK/TAKE d'un vêtement porté ne recalculent pas
  l'isolation.
- **Alerte en double.** « YOU ARE HUNGRY ENOUGH TO EAT A HORSE. » deux
  fois après deux `REST 8 H` (lot 13, à examiner).
- **Sondes ROM encore à lancer** (ORIGINAL_GAP.md § 3) : durée de présence
  animale (D1, relais `$4D56`), formules de temps de fabrication (A1–A3),
  sens de `$D8`/`$D9` = `$7F` (abris, tente), équipement du poste en
  scénario 2. Lesquelles avant les lots 3, 6 et 11 ?
- **Lot 4, provisions.** `FORAGE_FIDELITY` (`src/forage.s`, l'octet
  `fg_fidelity`) fait passer EAT des provisions par le module (péremption,
  question P/G, sel de BACON et BOLOGNA) ; laissé à 0 : le script de
  référence mange du fromage du sac et du sol et casserait sur la question.
  L'activer et rebaser `test_reference_state.py` une fois, avec les lots
  12 et 14 ?
- **Lot 4 sur 140 Ko.** Chaque commande du lot lit FORAGE (12 blocs, 1,3 s
  sur le Disk II émulé, 0,1 s sur XL) ; TREE et ORIENT y sont aussi lus
  sur le disque. Garder, ou scinder FORAGE (repas / chasse) pour lire
  moins ?
- **Numéros de lot.** « Lot 8 » désigne à la fois le joystick (MENUS.md)
  et HELP/score (ORIGINAL_GAP.md) ; « lot 7 » à la fois les scénarios et
  étoiles (CHANGELOG) et l'orientation. Ce fichier suit ORIGINAL_GAP.md ;
  renommer le joystick en « interface » ?

## Retiré le 15 octobre 2026

Décidé et fait, dans CHANGELOG.md (« feu jusqu'à DOUSE ») : alimenter le
feu. Le feu brûle jusqu'à DOUSE comme dans l'original (durée de vie
`FIRE_LIFE` retirée) ; il n'y a rien à entretenir, aucune commande n'est
ajoutée (CAMP.md § 8, CRAFT.md § 8.6).

Fait, dans CHANGELOG.md (« lot 3, étape 2 ») : la page CRAFT, l'arc, la
lance, le gourdin, la pierre et l'attelle dans les listes GET, DROP, USE et
la file de KILL de la grille, l'indice ITEMS du panneau (CRAFT.md § 8.6,
MEMORY.md § 23). ATTACK sans arme en usage : la règle du port (hache ou
couteau accessibles, sans USE) est gardée, écart voulu (décision du
15 octobre 2026, CRAFT.md § 8.2).

Fait, dans CHANGELOG.md (« lot 3, reste de l'étape 1 ») : GET, PACK, CARRY
et DROP des armes fabriquées ; ROCK ; une case par objet fabriqué laissé
au sol ; armes contre les animaux (avancé du lot 11) ; l'igloo à 35 °F des
dangers. EXIT SHELTER d'un abri fabriqué : gardé, écart voulu (décision du
15 octobre 2026, CRAFT.md § 8.2).

Fait, dans CHANGELOG.md (« menu d'actions rationalisé ») : les décisions
GET/TAKE, REST/WAIT, page OUTFIT (remplacée par la bascule WEAR), MAKE
STICKS et BOIL avec un feu de la revue des verbes du 14 octobre.

## Retiré le 14 octobre 2026

Fait, déjà dans CHANGELOG.md : trajet crash → rangers résident ;
géographie fine native résidente ; étoiles, constellations, ciel peuplé ;
score et hall of fame ; anomalie « FREE JOURNEY: NOT RANKED » (`103bee3`) ;
menu de démarrage simplifié ; auteurs sur la page de chargement ;
SAVE/RESTORE (lot 9) ; surface de commande (lot 8 de MENUS.md, étape 2) ;
réserves du § 12.8 (VOCAB et ADVENTURE en LZ, SCREENS supprimé, décodeur
LZ en banque 2, NEOWILD.BLK) ; budget par région ; instrumentation ;
garde-fous de `test_prodos.py` ; tirage commun de l'épave (lot 1) ; LOOK
STARS de l'original (lot 7) ; lot 4 (chasse, pêche, cueillette, repas) ;
le 15 octobre : messages collés (« AREAIT IS TOO DARK »), triangle des
arbres, feu animé (CHANGELOG.md, MEMORY.md § 17).
Fait, à ajouter au CHANGELOG : réserves de
la direction 3 (MEMORY.md § 12 ; CHANGELOG.additions.md).

Obsolète : politique disque « 140 Ko seulement » (800 Ko adoptée, deux
éditions) ; suppression de la recopie de SIM (écartée, MEMORY.md § 12.6,
au seuil de 5 %) ; « tout est encore non commité » ; fenêtres DHGR à la
place des écrans 40 colonnes (étapes 3-4 de MENUS.md, remplacées par les
pages 80 colonnes).
