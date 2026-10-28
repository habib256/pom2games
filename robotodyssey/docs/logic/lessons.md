# Leçons, Innovation Lab et Robotropolis Preview

*[← ANALYSE](../ANALYSE.md)* · voir aussi [world.md](world.md),
[simulation.md](simulation.md), [chips.md](chips.md)

Ce document couvre les six leçons de la face C (*Odyssey Training*), la
leçon *Chip Design*, l'*Innovation Lab* et *Robotropolis Preview* (face B).
Tout est établi sur les octets de l'Apple II : segments
`build/files/<face>/BBB_AAAA.bin`, images mémoire reconstituées par
`tools/memimg.py`, et parties jouées dans a2shot (captures dans
`build/les/`). Les puces (format, gravure, bibliothèque) sont dans
[chips.md](chips.md).

Outils :

| Outil | Rôle |
|---|---|
| `tools/memimg.py OUT NOM` | image 64 Ko d'une leçon (module résident + segments dans l'ordre des appels du chargeur) ; `NOM` = `anatomy`, `wiring`, `sensors`, `toolkit`, `circuits`, `teamwork`, `preview`, `innovation`, `chipdesign` |
| `tools/lessons.py [NOM…]` | salles (parcours en largeur depuis la salle du joueur), sorties, et tous les textes de chaque salle |
| `tools/preview.py` | désassemblage du script de *Robotropolis Preview* |
| `tools/resdis.py IMAGE DÉBUT FIN` | listage 6502 qui suit les paramètres en ligne (`JSR $4920` texte, `JSR $4B03` chargeur) |
| `tools/hstrings.py SEGMENT` | chaînes ASCII bit 7 d'un segment |

## Du menu à la leçon

Le menu range l'entrée choisie dans `$02D2`. `$4582-$45BE` (module résident)
fait :

1. pour `$02D2` ≥ 7 sauf `$0D` (les six leçons de la face C), appel `$4590` :
   moteur commun `$9500` (bloc `$05B`) et la « base leçon » de la face C ;
2. saut indirect par la table `$45BD` (octet bas) / `$45C7` (octet haut)
   indexée par `$02D2` vers la routine de chargement propre à l'entrée ;
3. `$02CE → $9C4E`, carte langage banque 2 en lecture, `JMP $0803`.

| `$02D2` | Entrée du menu | Face | Routine | Segments chargés (bloc → adresse + longueur) |
|---|---|---|---|---|
| 4 | Robotropolis | A | `$45EF` + `$4602` + `$4615` | hors de ce document ([world.md](world.md)) ; `$4615` met deux puces de la bibliothèque en banque 1, voir [chips.md](chips.md) |
| 5 | Innovation Lab | B | `$4630` | `$05B→$9500+$23D7`, `$0C6→$6000+$3500` (monde), `$0E1→$0803+$02FB` (code), `$0A7→$0B00+$149B` (circuit, puces), `$0B2→$B8E0+$06A1`, `$0B6→$D000+$0FFA`, `$0BE→$F000+$0FF8` |
| 6 | Robotropolis Preview | B | `$45D5` | `$05B→$9500`, `$071→$0803+$0BAE`, `$077→$14C0+$0AF6`, `$07D→$6000+$1FF8` (monde), `$08D→$7F80+$0818`, `$092→$8880+$0440` (script), `$095→$9000+$0395` (entrées enregistrées), `$097→$D000+$0F65`, `$09F→$E000+$00CE`, `$0A0→$E470+$0BD0` (interprète) |
| 7 | Robot Anatomy | C | `$4590` + `$4662` | `$020→$0803+$0C9E`, `$027→$14C0+$0679`, `$06D→$6000+$3350` |
| 8 | Robot Wiring | C | `$4590` + `$466E` | `$020→$0803`, `$02B→$14C0+$0679`, `$087→$6000+$2EF9` |
| 9 | Sensors | C | `$4590` + `$467A` | `$020→$0803`, `$09F→$6000+$33D8` |
| `$0A` | The Toolkit | C | `$4590` + `$4684` | `$0B9→$0803+$0982`, `$0BE→$14C0+$0679`, `$0C2→$6000+$3165` |
| `$0B` | Robot Circuits | C | `$4590` + `$4690` | `$0DB→$0803+$0A46`, `$0E1→$14C0+$0679`, `$0E5→$6000+$30E0` |
| `$0C` | Robot Teamwork | C | `$4590` + `$469C` | `$0DB→$0803`, `$0FE→$6000+$30E2` |
| `$0D` | Chip Design | B | `$46A6` + `$46C8` | comme l'Innovation Lab, avec le monde `$0E3→$6000+$3500`, le code `$0FE→$0803+$02F3` et en plus `$100→$0B00+$0800` ; puis `$46C8` en banque 1 : `$06D→$D800+$0183`, `$0A6→$D000+$0013` |

La base leçon `$4590` charge `$05B→$9500+$23D7`, `$008→$14C0+$0B1C`,
`$00E→$B900+$0572`, `$011→$D000+$0FF2`, `$019→$F000+$0C76` (banque 2). Elle
est commune aux six leçons : seuls le code `$0803`, le monde `$6000` et
éventuellement les premiers `$679` octets de `$14C0` changent.

Vérifié dans a2shot (`watch:4B03:01F0:16`, adresse de retour sur la pile) :
chaque entrée appelle d'abord `$4C8C` (lecture du bloc 0 pour reconnaître la
face, message « Insert Robot Odyssey PROGRAM-C disk and press RETURN » sinon),
puis exactement les routines ci-dessus. Ordre du menu : `ESPACE` part de
*Robotropolis* (défaut) ; *Robotropolis Preview* est la 9ᵉ pression.

Remarques :

- *Robot Anatomy*, *Robot Wiring* et *Sensors* partagent le même code
  (bloc `$020`) ; *Robot Circuits* et *Robot Teamwork* aussi (`$0DB`).
  *Sensors* et *Teamwork* ne rechargent pas `$14C0` et gardent la version
  du bloc `$008`.
- `$14C0-$1B38` : six pages de 256 octets indexées par numéro d'objet, qui
  diffèrent d'une leçon à l'autre d'une poignée d'octets (`$027` : 48,
  `$02B` : 5, `$0BE` : 92, `$0E1` : 29 par rapport à `$008`). Ce sont très
  probablement les fils et pièces du câblage initial de la leçon (même rôle
  que `$0B00-$1FFF` au labo) ; *à recouper avec [simulation.md](simulation.md)*.
- Pour *Chip Design*, `$46A6` écrit `$D8` dans `$5054` (octet haut de
  l'adresse du descripteur `$5051`) : le bloc `$06D`, qui va en `$D400` dans
  Robotropolis, va ici en `$D800` (puce n° 2, voir [chips.md](chips.md)).

## Le monde d'une leçon

Une leçon est un monde complet au format de Robotropolis
([world.md](world.md)) : objets `$6000-$6DFF`, salles `$6E00-$7FFF`, textes
`$7880-$7C7F`. La seule différence est la taille du tas de chaînes : il
déborde `$81FF` et va jusqu'à `$93xx-$94xx` (fin du segment), comme dans la
version PC.

| Leçon | Salle de départ | Salles atteignables | Textes (non vides) | Fin du tas |
|---|---|---|---|---|
| Robot Anatomy | `$3D` | 25 | 92 (69) | `$9324` |
| Robot Wiring | `$02` | 24 | 80 (59) | `$8EC7` |
| Sensors | `$2B` | 20 | 94 (52) | `$9402` |
| The Toolkit | `$30` | 37 | 126 (78) | `$913F` |
| Robot Circuits | `$02` | 22 | 69 (59) | `$90A4` |
| Robot Teamwork | `$17` | 20 | 74 (59) | `$90A1` |
| Chip Design | `$02` | 34 | 126 (93) | `$94AB` |
| Innovation Lab | `$02` | 13 | 106 (89) | `$89AA` |

Salles réservées, identiques d'une leçon à l'autre :

| Salle | Rôle |
|---|---|
| `$00` | écran `ESC` : « Be sure the Robot Odyssey disk is in the drive. Then press ESC. / To go back to the room you just left, press RETURN. » |
| `$01` | écran `?` : touches spéciales et rappel du thème de la leçon, « To continue, press RETURN. » |
| `$09`, `$0A`, `$0B` | intérieurs de Sparky, Checkers et Scanner (étiquettes BUMPER, THRUSTER, A…H, etc.) |
| `$3F` | rangement des textes inutilisés |

Les petits textes `-}`, `{-`, `~` (flèches) et les chaînes vides servent de
décor : ce sont les flèches qui guident d'une salle à l'autre.

## Comment une leçon est « scriptée »

**Il n'y a pas d'interprète de script.** Le déroulement est entièrement
spatial : chaque salle affiche ses textes (routine `$A2A2` du moteur, tous
les textes dont la salle = `$9C2D`), le joueur suit les flèches d'une salle à
l'autre, et la mécanique ordinaire du jeu (portes à clé, sentinelles,
robots, capteurs, télécommande) fait le reste. Le code `$0803` d'une leçon
est le même genre de code de niveau que celui de Robotropolis, avec
quelques routines liées à des numéros de salle.

### Boucle principale (code `$020`, `$0850-$0917`)

`$0816` installe la leçon (table de touches `$0809` → `$9C11`, 13 octets
identiques dans toutes les leçons : `I M J K`, ctrl, etc.) puis boucle sur :

- `$0981` touches de la leçon (`$9C3D`) :
  - `?` ou `/` → `$09B5` affiche la salle `$01` (`$9C2D = 1`, redessin
    `$9D03`/`$A2A2`/`$AEED`) et attend `RETURN` ;
  - `ESC` → affiche la salle `$00` ; `RETURN` revient à la salle courante,
    `ESC` sort par `$0A09` : `$02D0 = 1`, `$02CF = $02D0 EOR $A5` (signature de
    démarrage à chaud), carte langage banque 2, `JMP ($03F2)` → retour au menu
    ([ANALYSE](../ANALYSE.md), amorçage) ;
- `$095E` : si `$9C3D = $03FF`, bascule `$9C30` (le « triche `$03FF` » de
  [simulation.md](simulation.md)) ;
- les routines du moteur et de la carte langage (robots, fils, capteurs,
  sentinelles…), voir [simulation.md](simulation.md) ;
- `$0A27` : choisit l'une des 8 silhouettes du joueur selon la direction
  (`$9C22/$9C23`) et la copie dans le sprite 0 (`$6A00`, 16 octets) ;
- `$0CD3` : jusqu'à trois sentinelles (`$124A` salle, `$124D/$1250` X/Y,
  `$125D` comportement 1 = patrouille entre deux points, 2 et 3 = poursuite
  d'objets listés en `$128F`) ; c'est la même mécanique que dans le jeu ;
- puis les routines « décor » attachées à une salle.

**Une leçon ne se termine jamais d'elle-même** : la dernière salle du
parcours affiche « Press ESC to return to the menu » et c'est l'`ESC` de
`$0981` qui ramène au menu. Aucun drapeau de réussite n'est testé.

### Routines liées à une salle

| Code | Routine | Salle | Effet |
|---|---|---|---|
| `$020` | `$0B06` | `$19`, `$1B` (Wiring) | si l'objet `$3B` (resp. `$3D`) a la couleur 5 (= 1 logique) et que la télécommande tourne (`$1ACF = 1`), anime un sprite à 3 images (`$1E5E/$1E6E/$1E7E`) en X=`$85`, Y=`$28` ; dessine aussi `$1F66` et `$1F86`. *Rôle exact non vérifié* (probablement la flamme du propulseur de démonstration) |
| `$020` | `$0BF8` | `$28` (Sensors) | dessine 9 sprites (les trois types de capteurs, vérifié en capture `build/les/s28.png`) et deux cadres (`$A281`) |
| `$020` | `$0C65` | `$39` (Sensors) | **éditeur de capteur** : tout objet `$0D-$15` posé en X ∈ [`$0D`,`$12`[, Y ≥ `$98` prend le sprite `$2E` (forme carrée) |
| `$020` | `$0C95` | `$39` | dessine l'éditeur (sprite `$6CE0`) |
| `$020` | `$0CB3` | salle `$1E2B` | sprite `$6C00` en X=`$1E2C`, Y=`$1E2D` ; `$0841` y met salle `$34`, (`$77`, `$92`) : le **rechargeur** de la salle `$34` d'Anatomy (texte « RECHARGERS like this one ») |
| `$0B9` | `$09DE` | `$1E`, `$20`, `$22`, `$24`, `$2A`, `$2C` (Toolkit) | dessine le symbole de la pièce étudiée (nœud, bascule, NON, ET, OU, OUX : sprites `$6A70-$6B90`) |
| `$0B9` | `$09DE` | `$06`, `$07`, `$1F` | même animation à 3 images que `$0B06`, conditionnée par les objets `$40`, `$3D`, `$3A`, `$39` |
| `$0B9` | `$0962` | toutes | dessine la boîte à outils (`$64FE/$65FE`, objet `$FE`) quand elle accompagne le joueur |
| `$0DB` | `$0E1B` | deux boutons | bouton appuyé par un objet (±2 autour de X/Y) → bascule un état, puis ouvre/ferme une porte en réécrivant les murs (`$1170-$1177`) ; sert à la porte et au *PANIC BUTTON* qui met la sentinelle hors service (Circuits, Teamwork). Les tables de l'image statique sont identiques pour les deux boutons : *probablement réécrites au lancement* |
| `$0DB` | `$0F57` | liste `$10B8` | sprites de décor par salle |

## Les leçons

Parcours dans l'ordre des flèches (salle `$xx`, direction de sortie). Les
textes complets : `python3 -I tools/lessons.py NOM`.

### Robot Anatomy (`anatomy`)

Visite guidée du niveau 1 (l'Égout) : se déplacer, prendre, entrer dans un
robot, connaître ses organes. Aucun câblage.

| Salle | Contenu |
|---|---|
| `$3D` | titre ROBOT ANATOMY, accueil, « Press K twice to begin » |
| `$03` | se déplacer (joystick, souris ou `I J K M`) ; « Follow the arrows » |
| `$0D` | prendre et poser un objet (`ESPACE` / bouton) ; prendre la clé |
| `$06` | clé dans la serrure (pas fins Ctrl-`IJKM`), porte secrète, libérer le *Police 'Bot* |
| `$15` | `S` (fer à souder) et `T` (boîte à outils) servent plus tard ; `C` revient au curseur |
| `$23` | Scanner : entrer dans un robot en se centrant dessus, ressortir, l'emporter |
| `$2E` | s'asseoir sur l'œil (périscope) |
| `$29` | un robot transporte des objets (aimant dans Scanner) ; laisser Scanner |
| `$17` | Sparky ; la télécommande (`R`) démarre et arrête les robots |
| `$1A` | dans l'Égout on ne recâble pas : choisir le bon robot ; voir les fils de Sparky |
| `$2A` | les **pare-chocs** (4 lignes blanches, croissants à l'intérieur) |
| `$08` | les 4 **propulseurs** (triangles), l'électricité les fait pousser |
| `$18` | l'**interrupteur de propulsion** d'un robot (orange fermé, blanc ouvert) |
| `$21` | télécommande = tous les robots, interrupteur = un seul ; Scanner dans Sparky |
| `$05` | les **sentinelles** ; passer caché dans un robot |
| `$04` | piloter assis sur l'œil, `R` marche/arrêt |
| `$32` | la **pince** (Sparky saisit ce que touche son corps) ; prendre le triangle |
| `$27` | Checkers ; **batterie** et niveau d'énergie, économiser l'énergie |
| `$30` | le **cristal d'énergie** recharge la batterie |
| `$2B` | l'**antenne** (Checkers bipe en présence d'un cristal) |
| `$34` | les **rechargeurs** de cristaux (absents de l'Égout) |
| `$35` | les **transporteurs** vers le niveau suivant |
| `$26` | conclusion : sauvegarder souvent, conquérir l'Égout ; « Press ESC » |
| `$2F` | raccourci (*SHORT CUT*) vers le départ |

### Robot Wiring (`wiring`)

Entrées, sorties, fer à souder ; premier circuit (robot qui longe les murs)
et signalisation par antenne.

| Salle | Contenu |
|---|---|
| `$02` | titre ; dans le métro et au-delà il faut recâbler |
| `$03` | un **circuit** = fils soudés entre **sorties** et **entrées** des organes |
| `$36` | les entrées (propulseurs, commande de pince, commande d'antenne) dans Scanner |
| `$23` | les sorties (commande de pince, 4 pare-chocs, antenne) ; l'électricité *sort* d'une sortie |
| `$2E` | un pare-choc qui touche un mur devient orange (dehors et dedans) ; laisser Scanner |
| `$17` | `S` : devenir le **fer à souder** (*Solderpen*) |
| `$19` | souder : `ESPACE` sur la sortie (la pointe rougeoie), tirer le fil jusqu'à l'entrée |
| `$1B` | dessouder |
| `$08` | `C` pour redevenir curseur ; emporter Sparky pour faire un robot qui longe les murs |
| `$18` | relier propulseur gauche (A) et pare-choc bas (B) |
| `$21` | Sparky contre le mur du bas : le pare-choc alimente le propulseur |
| `$05` | un propulseur pousse dans la direction opposée |
| `$0D` | propulseur bas (C) ↔ pare-choc droit (D) : Sparky monte |
| `$1A` | refaire C–D en partant de D : le premier tronçon d'un fil est horizontal |
| `$32` | E–F et H–G : premier circuit complet (sens anti-horaire) |
| `$3B` | défi : sens horaire ; solution en `$27` (A–F, D–G, E–B, H–C) |
| `$37` | antenne : pare-choc gauche de Checkers → entrée d'antenne |
| `$30` | raccourci, Scanner : sortie d'antenne → propulseur ; Checkers fait bouger Scanner |
| `$2B` | un signal d'antenne atteint tous les robots, même dans d'autres salles |
| `$38` | un seul canal radio |
| `$25` | conclusion : apprendre Sensors et la boîte à outils ; « Press ESC » |
| `$2F` | raccourci vers le départ |

### Sensors (`sensors`)

Les trois capteurs, la forme détectée, l'éditeur de capteur, le
« ralliement » (*homing*) d'un robot sur un objet.

| Salle | Contenu |
|---|---|
| `$2B` | titre SENSORS ; détecter des objets (ex. aller chercher un cristal) |
| `$28` | trois types : directionnel, même salle (*In-Same-Room*), contact (illustration dessinée par `$0BF8`) |
| `$25` | capteur de **contact** ; un capteur ne voit pas un objet tenu |
| `$32` | capteur dans Scanner relié à l'antenne ; le contact se fait par le corps du robot |
| `$36` | télécommande arrêtée = électricité figée |
| `$02` | le capteur ne voit que **sa forme** (triangle) ; défi : biper au contact d'un triangle |
| `$33` | capteur **même salle** (forme carrée) |
| `$03` | allumé/éteint selon la présence du carré |
| `$16` | dans Checkers, relié à l'antenne |
| `$26` | capteur **directionnel** : les sorties pointent vers l'objet |
| `$37` | ralliement : propulseur droit (A) ← sortie gauche du capteur |
| `$12` | câblage complet du ralliement (4 directions) |
| `$0D` | capteur même salle → commande de pince |
| `$10` | Checkers rejoint le jeton et le saisit |
| `$0F` | plus de carré dans la salle : la pince lâche |
| `$2D` | capteur directionnel dans Checkers ; un objet tenu n'est pas détecté |
| `$39` | l'**éditeur de capteur** change la forme (routine `$0C65`) |
| `$08` | les trois règles : objet non tenu, même forme, télécommande en marche |
| `$2F` | conclusion : Innovation Lab, puis Toolkit et Robot Circuits ; « Press ESC » |
| `$38` | raccourci |

### The Toolkit (`toolkit`)

Le curseur « chaud », la boîte à outils et ses pièces : nœuds, bascules,
portes ET, OU, NON, OUX. Le cœur de la leçon est un carrefour
(*CROSSROADS*, salle `$14`) d'où partent un couloir par pièce.

| Salle | Contenu |
|---|---|
| `$30` | titre THE TOOLKIT ; le curseur peut devenir « chaud » |
| `$02` | circuit de deux pièces ; la télécommande agit dedans et dehors |
| `$32` | déplacer une pièce étire les fils ; un fil casse s'il sort de la salle |
| `$0C` | la **boîte à outils** |
| `$0E` | `T` ouvre/ferme la boîte ; la laisser |
| `$10` | « NO TOOLKITS ALLOWED! » |
| `$11` | `T` fait venir la boîte (« dans votre poche ») |
| `$1C` | une pièce = une pile ; boîte pleine : 10 bascules, 15 nœuds, 35 portes |
| `$13` | sortir et ranger des pièces |
| `$12` | `H` rend le curseur chaud : il alimente une entrée (antenne) |
| `$05` | le curseur chaud fait bouger un robot (au labo seulement, « it would spoil the game ») |
| `$34` | annonce du carrefour |
| `$14` | **CROSSROADS** : nœuds et bascules en haut, portes à droite, sortie en bas |
| `$1E`, `$1F` | **nœud** : l'électricité se partage ; capteur de contact → nœud → deux propulseurs |
| `$20`, `$21` | **bascule** (*flipflop*) comme un interrupteur ; bascule dans un robot |
| `$26` | les 4 portes (35 au total, en toute combinaison) |
| `$22`, `$23` | **NON** ; l'antenne bipe quand le cristal ne touche *pas* le capteur |
| `$2A`, `$2B` | **OU** ; clé en haut OU à gauche du capteur |
| `$24`, `$25` | **ET** ; clé à gauche ET en haut du capteur directionnel |
| `$2C`, `$2D` | **OUX** ; clé ou cristal dans la salle, pas les deux |
| `$29` | fin des pièces ; aller à Robot Circuits |
| `$31` | résumé ; Robotropolis ou Innovation Lab ; « Press ESC » |
| `$38` | raccourci |

### Robot Circuits (`circuits`)

Circuits utiles construits pas à pas, puis un problème décomposé en
sous-problèmes : aller chercher un cristal dans une salle gardée.

| Salle | Contenu |
|---|---|
| `$02` | titre ROBOT CIRCUITS |
| `$03`, `$04` | circuit **ping-pong** (une bascule, deux propulseurs, deux pare-chocs) et son explication |
| `$05`, `$06` | défi **yo-yo** (haut/bas) : déplacer la bascule hors du robot casse tous ses fils |
| `$07` | ping-pong et yo-yo à la fois (deux bascules) |
| `$08` | le problème : rapporter un cristal d'une salle gardée ; pièces fournies |
| `$10` | décomposer : saisir/lâcher sur commande, puis aller et revenir |
| `$11` | NON → pince : Checkers saisit tout ce qu'il touche |
| `$12` | capteur même salle (clé) → NON → pince : poser la clé fait lâcher |
| `$1B` | aller jusqu'au cristal : quels circuits ? |
| `$13` | yo-yo + sortie gauche du capteur directionnel → propulseur droit |
| `$14` | essai : après la saisie le capteur s'éteint, Checkers ne revient pas |
| `$16` | sortie de pince → propulseur gauche : retour |
| `$17` | l'essai réel ; *PANIC BUTTON* (salle `$18`) arrête la sentinelle |
| `$19` | félicitations ; méthode « diviser le problème » ; le Labo pour tester ; puis Teamwork |
| `$38` | raccourci |

Les salles `$1C-$28` du même monde, non reliées au parcours, portent des
titres seuls (« BUTTON ONE CIRCUIT », « MOVE TO BUTTON, GO RIGHT », …,
« SUMMARY ») : *vraisemblablement des restes des schémas de la solution de
Teamwork*.

### Robot Teamwork (`teamwork`)

Deux robots coopèrent : Sparky tient un bouton qui ouvre une porte pendant
que Checkers va chercher le cristal, puis Checkers le rappelle par radio.

| Salle | Contenu |
|---|---|
| `$17` | titre ; certains défis demandent deux robots |
| `$19` | l'énigme : un robot appuie sur le bouton de la porte, l'autre prend le cristal ; la sentinelle refuse qu'on passe dans un robot ; énigme en `$1A` (porte, *PANIC BUTTON*) |
| `$1B` | un robot par tâche ; gabarit de robot du manuel ; *SOLUTION* |
| `$1C` | Sparky va à droite jusqu'au mur puis monte jusqu'au mur du haut, et y reste |
| `$1D` | bascule + nœud ; propulseur gauche sur le côté « chaud » |
| `$1E` | nœud sur le pare-choc droit… |
| `$16` | …une sortie vers l'entrée éteinte de la bascule (arrêt), l'autre vers le propulseur bas (montée) |
| `$1F` | retour sur signal : sortie d'antenne → entrée « froide » d'une seconde bascule |
| `$20` | nœud sur la sortie froide → propulseurs haut et droit |
| `$21` | test au curseur chaud, remise à zéro des bascules |
| `$22` | tâche de Checkers : NON → pince |
| `$23` | propulseur gauche sur le côté chaud d'une bascule |
| `$02` | ne pas utiliser le pare-choc droit (la porte peut être fermée) : la sortie de pince fait basculer et revenir |
| `$24` | test avec un cristal |
| `$25` | pare-choc gauche de Checkers → antenne : bip au retour |
| `$26`, `$27` | l'essai réel : Sparky sur S, Checkers sur C, *PANIC BUTTON* |
| `$28` | conclusion : la Ville, puis les puces (Chip Design) ; « Press ESC » |
| `$38` | raccourci |

### Chip Design (`chipdesign`, face B)

Présente les outils propres à l'Innovation Lab : puces, pinceau (`P`) et
éditeur de forme. Carrefour en `$1B`.

| Salle | Contenu |
|---|---|
| `$02` | titre ; puces, pinceau, éditeur de forme ; prérequis (les cinq premières leçons) |
| `$1B` | CROSSROADS : PAINTBRUSH à gauche, SHAPE EDITOR en haut, CHIPS à droite, sortie en bas |
| `$1C` → `$2E`, `$04`, `$2F` | éditeur de forme : changer la forme des capteurs et des objets ; robot qui bipe au contact d'un cristal, puis d'un triangle |
| `$2C`, `$05` | pinceau : peindre/effacer les murs des salles labyrinthe (`$0D`, `$0E`, `$11`, `$12`) |
| `$07` | la **puce prototype** : 8 broches numérotées 1-4 à gauche, 8-5 à droite ; non câblée, ses broches sont neutres |
| `$16` | on câble l'intérieur d'une puce (nœuds, portes, bascules) ; les broches deviennent entrées/sorties |
| `$1E` | prototype contenant un circuit (impulsions) ; broche 1 = entrée dedans, sortie dehors |
| `$1F` | broche 1 → entrée d'antenne : l'antenne clignote |
| `$20` | la **petite puce** gravée (*burned*) depuis le prototype ; même effet, mais on n'y entre pas |
| `$21`, `$06` | la salle de gravure (*Burner Room*) ; bouton BURN |
| `$15`, `$23`, `$18` | **imbrication** : petite puce dans le prototype (broche 1 ↔ 1, NON → broche 3) |
| `$25` | prototype dans un robot : broche 1 → antenne, broche 3 → propulseur gauche |
| `$17`, `$27`, `$28` | la puce WALLHUGGER (16 portes + 1 puce imbriquée) et son brochage ; labyrinthe `$2B` |
| `$1D` | usages : imbriquer, emporter dans Robotropolis, gagner de la place dans un robot |
| `$24`, `$19` | la fiche (*record*) d'une puce : `?` ; fiche exemple LEFTRIGHT PINGPONG |
| `$22` | recycler une petite puce ; `S` sauve le circuit d'une puce |
| `$26` | `L` charge une puce (liste des noms) ; au labo ou dans Robotropolis |
| `$1A` | renvoi au manuel |
| `$30` | conclusion : aller à l'Innovation Lab ; « Press ESC » |

État initial propre à la leçon : puce 0 (objet `$E7`, salle `$20`) = la
petite puce à impulsions (19 octets, bloc `$0A6`), puce 2 (objet `$E9`,
salle `$17`) = WALLHUGGER (bloc `$06D`, la n° 8 de la bibliothèque) ; le
prototype de la salle `$1E` contient déjà une porte NON rebouclée (salle
intérieure `$0C`).

### Progression pédagogique

| Ordre | Leçon | Notions |
|---|---|---|
| 1 | Robot Anatomy | déplacement, prise, clé/serrure, entrer dans un robot, œil, télécommande, interrupteur, pare-chocs, propulseurs, pince, batterie, cristal, antenne, sentinelle, transporteur |
| 2 | Robot Wiring | entrées/sorties, circuit, fer à souder, robot qui longe les murs, signal radio entre robots |
| 3 | Sensors | capteurs contact / même salle / directionnel, forme, éditeur de capteur, ralliement, pince commandée |
| 4 | The Toolkit | curseur chaud, boîte à outils, nœud, bascule, NON, OU, ET, OUX |
| 5 | Robot Circuits | ping-pong, yo-yo, combinaisons, décomposition d'un problème (aller chercher un cristal gardé) |
| 6 | Robot Teamwork | coopération de deux robots, mémoire par bascules, signal de retour |
| 7 | Chip Design | puce prototype, gravure, imbrication, fiche, sauvegarde/chargement de puces, pinceau, éditeur de forme |

Les conclusions renvoient de l'une à l'autre (Anatomy → l'Égout ; Wiring →
Sensors et Toolkit ; Toolkit → Robot Circuits ; Circuits → Métro puis
Teamwork ; Teamwork → la Ville puis Chip Design ; Chip Design → Innovation
Lab).

## Innovation Lab (`innovation`)

Un monde libre (13 salles reliées, plus les salles techniques) où tout est
disponible : les trois robots, la puce prototype, huit petites puces, la
boîte à outils pleine, tous les capteurs et objets, l'éditeur de forme et
des salles labyrinthe à peindre. Il n'y a aucun objectif.

| Salle | Contenu |
|---|---|
| `$02` | « Innovation Lab » : Scanner, Checkers, Sparky et la **puce prototype** (objets `$01-$0C` : broches `$01-$08`, corps `$09-$0C`) ; entrer dans le corps mène à la salle `$0C` |
| `$0C` | intérieur du prototype : 8 broches (objets `$39-$40`) |
| `$05` | boîte à outils (10-FF, 15-N, 35-G), « To Maze » |
| `$06` | **Burner Room** : les 8 petites puces (objets `$E7-$EE`, sprites `$21-$28` numérotés 1-8), emplacements du prototype et de la petite puce, bouton BURN |
| `$03` | réserve : capteurs (contact, même salle, directionnel) de chaque forme et objets (cristaux, carré, triangle, hexagone, clé) |
| `$04` | éditeur de forme (*Shape Icons*) |
| `$0D-$14` | labyrinthe peignable (8 salles) |
| `$09-$0B` | intérieurs des robots |
| `$16-$1D` | **fiches des puces** 1 à 8 : titre + 8 lignes de 34 caractères (textes `$8045 + $12B·n`) |
| `$15` | commandes de l'éditeur de fiche (Ctrl-I insérer, Ctrl-D effacer, Ctrl-C tout effacer, ← →, `RETURN`, `ESC`) |
| `$00`, `$01`, `$3E` | écrans `ESC` (« Press ESC to go to menu. Press S to save Lab. »), aide, et confirmation disque des opérations sur puce |

Touches propres au labo (code `$0E1`, `$0953`, et `$7400` dans le monde) :

| Touche | Effet |
|---|---|
| `?` `/` | en tenant une petite puce (`$9C26` ∈ `$E7-$EE`) : ouvre sa fiche (salle `$7322+obj` = `$16-$1D`, éditeur `$742B`) ; sinon aide (salle `$01`) |
| `ESC` | salle `$00` ; `ESC` → menu (`$02D0 = 1`) ; `S` → sauvegarde du labo (`$02D0 = 4`, `$02D1 = 5`) |
| `L` / `S` en tenant une petite puce | salle `$3E` (confirmation), puis `$02D0 = 5` (charger) ou `6` (sauver), `$02D1` = numéro de puce (objet − `$E7`) |
| `P`, `H`, `T`, `S`, `C` | pinceau, curseur chaud, boîte à outils, fer à souder, curseur (moteur) |

Ces opérations ne sont pas faites par le labo : `$0A2C` range le mode dans
`$02D0`, la signature dans `$02CF` et redémarre à chaud par `$03F2` ; le
module résident (`$4000`, relu en blocs `$030-$038`) exécute le mode (table
`$4088/$408F` : 4 → `$4108` sauvegarde, 5 → `$4260` chargement de puce,
6 → `$419C` sauvegarde de puce, voir [chips.md](chips.md)) puis relance la
leçon par `$4381` (« LOADED », `JMP $45B5`).

**Sauvegarde du labo** (mode 4, détail dans l'analyse du chargeur) : la même
routine `$4182` que pour une partie écrit l'en-tête `$5A00`, `$5C00`, la
banque 1 `$D000+$2000` (les 8 puces), le monde `$6000+$3500` (salles,
murs peints, objets, textes dont les fiches) et `$0B00+$1500` (circuit,
puces et code du labo). Le labo sauvé est donc une image complète de
l'état, rechargée par `O` à l'entrée du labo (« To load an old saved lab, press O », vérifié en capture).

## Robotropolis Preview (`preview`)

Une **démonstration automatique** : le joueur ne joue pas. Un monde réduit
(9 salles atteignables : Égout, Disk-O-Tek, métro, Skyways…) est joué par
**une séquence d'entrées enregistrée**, entrecoupée de bandeaux de texte.

### Entrées enregistrées (`$E005`, bloc `$09F`)

`$0816` appelle `$E005` avec A = 0, X/Y = `$9000` : table de 16 décalages
(16 bits) vers des flux d'entrées ; seul le flux 0 (`$902F`, 866 octets) est
non vide, les 15 autres pointent sur un `$77` isolé. `$E005` appelle la
trame de jeu `$0860` jusqu'à la fin du flux ; à chaque trame, `$E035` →
`$E047` lit un octet (`$E035` met la banque 1 en `$D000` le temps de l'appel) :

| Octet | Effet |
|---|---|
| `$77` | fin du flux → `$E005` revient, `JMP $09CE` : retour au menu |
| `$x7`, x ≠ 0 | bit 7 → `$9C3B`, bit 6 → `$9C3C` (boutons ; `$47` vu 6 fois : prendre/poser) |
| `$07 kk` | touche `kk` dans `$9C3D` (`P`, `R` télécommande, `X`) |
| autre | quartets haut/bas → déplacements X/Y par les tables `$ABCE`/`$ABBE` (`$99` = immobile) |

Le flux contient 9 `P` (`$D0`). `$0995` voit la touche `P` dans `$9C3D` et
appelle `$8880` : **chaque `P` fait avancer le script d'une étape** (un
bandeau). `Q` (`$D1`) quitte vers le menu.

### Script des bandeaux (`$8880`, interprète `$E470`)

`$8880` est une coroutine : elle reprend le script à l'adresse rangée en
`$8CBB/$8CBC` ; chaque étape se termine par `JSR $8CB2`, qui range l'adresse
de reprise et rend la main au jeu. Le script lui-même est du code-octet lu
par `$E470` (opcode → tables `$E60F`/`$E5F6`) :

| Code | Nom (`tools/preview.py`) | Opérandes |
|---|---|---|
| 1 | SAVEFRAME | lignes texte a..b sauvées (`$5000`), cadre couleur c |
| 2 | RESTORE | remet les lignes sauvées |
| 3 | DELAY | n (touches ignorées) |
| 4 | FRAME | couleur |
| 5 | PRINT | ligne, texte terminé par 0 |
| 6 | NATIVE | 6502 en ligne jusqu'au prochain `JSR $E470` |
| 7 | GETKEY | n, liste de touches terminée par 0 |
| 8 | IFKEY | adresse, liste de touches |
| 9 | GOTO | adresse |
| 10 | NOP | |
| 11 | SHAPE | X, Y, adresse (OU exclusif sur HGR1) |
| 12 | WAIT | n ; `ESPACE` abrège, `P` pause, `ESC` → menu (`$0806`) |
| 13 | SOUND | adresse d'une liste (hauteur, durée) |
| 14 | SPRITE | 4 octets |
| 15 | INVERT | rectangle inversé |
| 16-18 | POKE / ADD / SUB | valeur, adresse |
| 19 / 22 | IFEQ / IFNE | valeur, adresse, saut |
| 20 / 21 | CALL / RETURN | sous-script |
| 23 | MARQUEE | ligne, vitesse, options, texte |
| 24 | SCROLL | 4 octets (défilement du bandeau) |

Le script de la Preview n'emploie que SAVEFRAME, SOUND, PRINT, WAIT, SCROLL,
RESTORE et NATIVE. Les 8 étapes, dans l'ordre :

1. « Welcome to the subterranean city of Robotropolis! » / « Your only hope
   of escape is to learn to control the few friendly robots. »
2. « We need that energy crystal, but the sentry won't let us pass. » /
   « This looks like a job for a friendly robot! »
3. « Now we are inside the robot. » / « The robot is wired to move to the
   crystal, grab it, and come back. »
4. « This subway car will take us through more scenes from Robotropolis. »
5. « The robot sends a coded signal to open the door. »
6. « Will you get caught in the giant disk drive? »
7. « These robots signal each other to get form F-12: your passport to the
   Master Control Center! » / « Make robots run mazes, open doors, and fetch
   valuable objects as you (try to) escape from Robotropolis. »
8. « And now, it's time for your visit to Robotropolis. Good Luck! »

Le flux contient 9 `P` pour 8 étapes : après la 8ᵉ, la reprise tombe sur
`JMP $8889`, qui reboucle sur la première. *Non vérifié si le 9ᵉ `P` arrive
avant la fin du flux.* Le langage est plus riche que ce qu'utilise la
Preview (saisie de touches, tests, sous-scripts) : *peut-être partagé avec
un autre programme de la gamme*.

Vérifié dans a2shot : sans aucune touche, la salle change toute seule
(`$01 → $02 → $0B → $06 → $02 → $03…`), captures `build/les/pv*.png`.

## Points ouverts

- Rôle exact de l'animation à 3 images de `$0B06`/`$09DE` (salles `$19`,
  `$1B` de Wiring, `$06`, `$07`, `$1F` de Toolkit).
- Tables des boutons de `$0E1B` (Circuits/Teamwork) : identiques pour les deux
  boutons dans l'image statique, à relire en cours de partie.
- `$14C0-$1B38` des leçons : contenu exact (câblage initial ?) à recouper
  avec [simulation.md](simulation.md).
- Touche `X` (`$D8`) injectée une fois dans le flux de la Preview.
- Opcodes 14 et 24 de l'interprète de la Preview, non utilisés, décrits
  sommairement.
