# Warblade : référence vérifiée

Complément du 2026-10-27 : [progression et difficulté](warblade-difficulty.md),
avec audit du code et distinction entre règles documentées et adaptation.
Correction appliquée : le premier niveau spécial est **kamikaze (4)**,
le suivant **bonus (8)**, conformément à la FAQ et au guide des niveaux.

*[← WARGALAGA II](../README.md)*

Ce que WARGALAGA II reprend de Warblade (règles seulement). Chaque point
porte son statut : **confirmé** (source citée), **corrigé** (la source dit
autre chose que la note de départ), **non vérifié** (aucune source écrite
trouvée ; à revoir sur une vidéo ou en jouant). Recherche du 2026-10-22.

Sources :
- [W] [Wikipedia, *Warblade*](https://en.wikipedia.org/wiki/Warblade)
- [M] *Warblade Game Manual* v1.33 (Simon Quincey), sur
  [warblade.fandom.com/wiki/Game_Manual](https://warblade.fandom.com/wiki/Game_Manual)
- [F] *Warblade v1.2c FAQ / Walkthrough* (Johnny « ThunderPeel2001 » Walker),
  sur [warblade.fandom.com/wiki/Gameplay_Basics](https://warblade.fandom.com/wiki/Gameplay_Basics)
  et [Gameplay_Advanced](https://warblade.fandom.com/wiki/Gameplay_Advanced) ;
  [Bonuses](https://warblade.fandom.com/wiki/Bonuses)
- [R] Amiga Report 3.03, test de *Deluxe Galaga 2.5*
  ([copie](https://bigbookofamigahardware.com/amigareport/www.amigareport.com/ar303/review3.html))
- [A] [Aminet, DGalaga26C.readme](https://morphos.aminet.net/game/shoot/DGalaga26C.readme)
- [T] [TouchArcade, Warblade (iOS)](https://toucharcade.com/games/warblade) ;
  [Macworld](https://www.macworld.com/article/189839/warblade.html) ;
  [MyAbandonware](https://www.myabandonware.com/game/warblade-pgs) (sortie Windows 2003)

Les pages fandom ont été lues par l'API MediaWiki (`api.php?action=parse`),
le site renvoyant HTTP 402 aux navigateurs automatisés. La FAQ décrit la
version 1.2c ; le manuel la 1.33.

## Origine

- Shareware Windows / Mac OS X d'Edgar M. Vigdal (Norvège), réécriture de
  son *Deluxe Galaga* Amiga ; graphismes et sons restent proches de l'Amiga
  [W]. Sortie Windows 2003 [T]. **Confirmé.**
- *Deluxe Galaga* 2.5 : 75 niveaux puis boucle plus dure, 3 difficultés,
  boss, niveaux de défi, kamikaze, deux sortes de bonus ; capture du vaisseau
  (on le libère pour un double chasseur) ; boutique (vies, armes, vitesse,
  jusqu'à « War.I. Plasma » à 3 000) ; jeu de Memory [R]. Shareware 10 $ [A].
- Les 75 premiers niveaux de Warblade sont presque ceux de Deluxe Galaga [T].
- Suite *Warblade MK II* abandonnée à la mort de l'auteur (2015) [W].
- « Starblade » (titre proposé par la note) est un jeu Namco (1991) : nom à
  éviter. On garde **WarGalaga II**.

## Structure des niveaux

| Affirmation de la note | Statut | Détail et source |
|---|---|---|
| 100 niveaux qui bouclent plus durs | **confirmé, précisé** | 100 niveaux [M][T] ; après le 100, fin puis reprise avec les trajectoires inversées gauche/droite, un peu plus rapide, et ainsi de suite [F §7.1] |
| Boutique tous les 4 niveaux | **confirmé, précisé** | « Every 4th level there is a shop » [M] ; en fait après un niveau kamikaze, bonus ou Big Trouble, **si l'on a au moins 50 crédits** [F §2.1] |
| Boss tous les 25 niveaux | **confirmé** | [W] ; niveaux 25, 50, 75, 100 « Big Trouble » [F §7.1] |
| — | ajout | Paquets de 4 niveaux, un nouveau dessin d'alien par paquet ; niveaux 1-2 petits aliens, 3 avec gros aliens (qui lâchent les marques de rang), 4 alterne kamikaze et bonus [W][F §3.1] |
| — | ajout | Niveau bonus : aliens qui ne tirent jamais, prime si tous détruits (10 000 → 10 000 000 selon la série de « perfect ») ; kamikaze : vagues, prime doublée à chaque vague complète (2 000, 4 000, 8 000…) [F §3.1] |
| — | ajout | Vague détruite avant de se poser en formation : +10 000 [F, secrets] |
| — | ajout | Trop lent sur un niveau : le « Hurry Up ship » passe et tire des missiles à tête chercheuse [F §2.2] |

## Formation et attaques

| Affirmation | Statut | Détail |
|---|---|---|
| Les aliens se rangent en haut et « respirent » | **partiellement confirmé** | entrée en vague puis repos en formation (« before they rest ») [F] ; la respiration elle-même : **non vérifié** |
| Plongées sinusoïdales | **non vérifié** | aucune source écrite ; Wikipedia dit seulement qu'ils volent et tirent [W] |
| Danger surtout par collision | **corrigé** | le manuel parle d'éviter les **tirs** des aliens [M] ; les collisions existent (kamikaze) mais rien n'en fait la menace principale |

## Vaisseau et jauges

| Affirmation | Statut | Détail |
|---|---|---|
| Gauche/droite seulement | **confirmé** | [M] ; haut/bas seulement en boutique et Memory Station |
| Tirs à l'écran limités, 5 au départ | **confirmé** | « You start off with 5 bullets » [M] ; jauge B (rouge), monte avec les icônes B ou l'achat [M][F] |
| Vitesse lente au départ | **partiellement** | jauge S (bleue), icônes S et achat [M][F] ; valeur de départ **non vérifiée** |
| Armure 1-2 qui absorbe un tir mais pas une collision | **confirmé pour le tir, non vérifié pour la collision** | max 2 ; absorbe un tir d'alien puis donne un bouclier quelques secondes [M][F] ; rien sur les collisions |
| — | ajout | 3 vies au départ, 4 au plus [M][F] ; jauge T (verte) : durée des bonus temporaires et du temps en Memory Station, 30 s au départ, 90 s au plus [F] |
| — | ajout | Lettres E-X-T-R-A : vie supplémentaire [M] ; multiplicateurs ×2/×5 temporaires [M] |

## Bonus qui tombent

**Confirmé**, avec bien plus que la note [F §1.2, 43 icônes] : pièces
(argent 10, or 50, verte 100, bleue 200 crédits), S, B, temps, armes
(simple — le malus redouté —, double, triple, quadruple), tir automatique,
armure, vie, crânes (perte d'arme, de vitesse ou de tirs), lettres EXTRA,
×2/×5, bouclier, « scoop », miroir, « drunk » (gauche/droite inversés), gel,
bombes à gemmes ou à argent, doublement des crédits, marques de rang, et les
deux icônes qui lancent les sous-jeux.

## Boutique

**Confirmé** : vitesse, tirs, tir automatique, vies, armure, armes, secrets
[M]. Liste et prix de la v1.2c [F §2.1] :

| Objet | Prix | | Objet | Prix |
|---|---:|---|---|---:|
| Extra Speed | 50 | | Ship Armour (max 2) | 600 |
| Extra Bullet | 75 | | Plasma | 750 |
| Double Shot | 100 | | Extra Life | 800 |
| Less Speed | 150 | | Fire Balls | 990 |
| Triple Shot | 200 | | Game Secret | 1 000 |
| Quad | 300 | | Rank Marker | 1 250 |
| Auto Fire Unit | 400 | | Extra Time | 1 500 |
| Super Triple | 500 | | Laser Beam | 2 000 |
| | | | War. I. Plasma | 3 000 |

Plus trois objets cachés (Rocket Pack 5 000, Alien Lock 15 000, Super
Autofire 30 000). Le manuel ajoute une sauvegarde de partie en boutique
(v1.2f).

## Rangs

**Confirmé** : 6 marques de couleur (rouge, orange, jaune, vert, bleu,
violet) lâchées par les gros aliens ; les 6 réunies, on monte d'un rang à la
**prochaine sortie de boutique** (il faut donc pouvoir y entrer) [M][F].
Une marque violet sombre fait descendre d'un rang [F]. Les ramasser dans
l'ordre de l'arc-en-ciel débloque le Super Autofire [F, Advanced].

## Sous-jeux

| Affirmation | Statut | Détail |
|---|---|---|
| Meteor Storm : traverser un champ d'astéroïdes ; accélérer/freiner change le défilement des étoiles | **confirmé, précisé** | le tir accélère, le relâcher ralentit (on ralentit plus vite qu'on accélère) ; jauge de vitesse, pourcentage, distance restante ; gemmes et argent à ramasser ; un choc ramène au jeu **sans perte de vie** ; prime selon la vitesse moyenne [M][F §3.2]. L'effet sur les étoiles : non vérifié (c'est le défilement lui-même) |
| Memory Station : paires, chronométré | **confirmé, précisé** | temps = jauge T ; grille qui grandit à chaque réussite, prime +25 000 à chaque fois ; les paires donnent des bonus (S, B, vie, lettres, marques, crédits) ; le pavillon pirate termine le sous-jeu [M][F][R] |
| — | ajout | Troisième sous-jeu, *Gem Drop* (100 gemmes ramassées) [W] |
| On y entre par une icône lâchée par un alien | **confirmé** | seule façon d'y entrer [F §3.2] |

## Son

| Affirmation | Statut | Détail |
|---|---|---|
| Voix numérisées | **confirmé** | paquets de voix, réglage du volume des voix [M] ; Deluxe Galaga enregistré : voix « arcade » [R] |
| Bande-son techno | **non vérifié** | le jeu joue des MP3/MOD et a un juke-box [M] ; Wikipedia classe les compositeurs Peter Hajba et Yannis Brown, sans détail de style [W] |

## Ce que WARGALAGA II en garde (proposition)

Gardé : 100 niveaux en 25 paquets de 4 (4e = bonus/kamikaze en alternance),
boss aux niveaux 25/50/75/100, boucle avec trajectoires en miroir ;
formation + plongées ; pièces et une quinzaine de bonus ; jauges S, B, T,
armure (max 2, contre les tirs seulement : une collision avec un alien
tue), 3 vies (max 4), EXTRA ; boutique après chaque paquet si
≥ 50 crédits, ~12 objets ; 6 marques de rang ; Meteor Storm et Memory
Station.

Dessins : 6 petits aliens, 2 gros, 1 boss, en 4 teintes HGR, au lieu
d'un dessin par paquet.

Laissé de côté (au moins au départ) : profils, secrets à acheter, mode
deux joueurs, contre-la-montre, Gem Drop, scoop/miroir/drunk, missiles à tête
chercheuse, sauvegarde de partie, voix.
