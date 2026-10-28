# Le monde : salles, objets, fils, robots, niveaux

*[← ANALYSE](../ANALYSE.md)* · voir aussi [simulation.md](simulation.md)

Ce document décrit les structures de données du jeu (face A, *Robotropolis*)
telles qu'elles sont en mémoire pendant une partie. Tout a été établi sur les
octets de l'Apple II (segments `build/files/A_ROBOTROPOLIS/*`, vidages RAM
`build/ref/*.bin`, `build/ram_robots.bin`) ; la rétro-ingénierie de la
version PC par Micah Dowty (`robot-odyssey-rewired`, `src/engine/roData.h`)
n'a servi que de recoupement. **Résultat principal : l'Apple II et le PC
partagent exactement la même disposition** pour le monde (`$3500` octets) et
pour le circuit ; seules les adresses de base changent.

Outils : `tools/world.py` (décodage, cartes PNG), `tools/symbols.py` (noms
des tables), `tools/disasm.py` (désassemblage annoté). Exemples en fin de
document.

## Vue d'ensemble de la mémoire

| Zone | Bloc disque | Contenu | Persistance |
|---|---|---|---|
| `$0803-$1907` | `$0A1` (niv. 1) | code propre au niveau (boucle principale incluse) | rechargé à chaque niveau |
| `$1AB0-$1FFB` | `$072` | code commun « boîte à outils », compteurs affichés | chargé une fois avec le moteur |
| `$6000-$6DFF` | `$090` (niv. 1) | **objets** (10 tableaux de 256) + 64 sprites | chargé au niveau 1 seulement |
| `$6E00-$81FF` | `$090`, puis `$0AD/$0C1/$0D8/$0EE` | **salles** (listes, couleurs, liens, murs) + **textes** | rechargé à chaque niveau (`$6E40-$81FF`) |
| `$8200-$8617` | `$075` | tables fixes du moteur (robots, capteurs, broches) | chargé une fois |
| `$8618-$8DAB` | `$075` | **circuit** (fils, bascules, nœuds, puces, portes, boîte à outils) | chargé une fois |
| `$8DC9-$8E31` | `$075` | **état des 4 robots** (4 × 26 octets + `$FF`) | chargé une fois |
| `$8E32-$8ED4` | `$075` | accumulateurs de batterie, variables du moteur | |
| `$8EF0-$94xx` | `$0AA/$0C0/$0D5/$0EB/$102` | données (et un peu de code) propres au niveau | rechargé à chaque niveau |
| `$9500-$B8D6` | `$05B` | moteur commun | |
| `$B8E0-$BF98` | `$07C` | fils : déplacement des extrémités, soudure | |
| `$D000-$DFFD` banque 2 | `$080` | robots : capteurs, pinces, propulseurs, batteries, antennes | |
| `$F000-$FFF3` | `$088` | portes, bascules, fils, puces, entrée dans les robots | |
| `$D000-$EFFF` banque 1 | `$071`, `$06D`… | programmes des puces (hors de ce document) | |

Une sauvegarde (`$4182`, voir l'analyse du chargeur) écrit `$6000+$3500`,
`$0B00+$1500` et `$D000+$2000` : monde + circuit + puces, comme le fichier
`.GSV` du PC.

## Coordonnées

- **X** : 0 à `$85` (133), en unités de 2 pixels HGR ; un objet occupe 7
  unités (14 pixels). `X ≥ $86` après un déplacement fait passer dans la salle
  de droite (`X − $86`), un `X` « négatif » (≥ `$D8`) dans celle de gauche
  (`X + $86`) : routine `$9DB9`.
- **Y** : 0 à `$B0` (176), **compté vers le haut** depuis le bas de l'écran ;
  c'est la ligne du bas du sprite (ligne écran ≈ `191 − Y`). Débordement :
  `Y ≥ $B1` → salle du haut (`Y − $B1`), `Y ≥ $D8` → salle du bas (`Y + $B1`).
- Vérification : vidage `build/ram_robots.bin` et capture `build/shots/robots.png`
  (joueur `X=21,Y=16` en bas à gauche, Sparky `X=98,Y=156` en haut).
- Pas clavier du joueur : `J`/`K` ±7 en X (une case), `I`/`M` ±16 en Y ;
  Ctrl-J/K/I/M ±1 (mesuré : `$72→$6B`, `$43→$53`, puis `+1`, `−1`).

## Salles (`$6E00-$7FFF`)

64 salles (`$00-$3F`), tableaux de 64 octets indexés par le numéro de salle :

| Adresse | Champ | Remarques |
|---|---|---|
| `$6E00` | tête de la liste des objets de la salle | `$FF` vide ; liste chaînée par `$6000` |
| `$6E40` | couleur du fond | index de motif, table `$9B91…$9BF1` (`$9CD0`) |
| `$6E80` | couleur des murs | idem |
| `$6EC0` | salle au-dessus | une salle qui pointe sur elle-même = bord fermé |
| `$6F00` | salle au-dessous | |
| `$6F40` | salle à droite | |
| `$6F80` | salle à gauche | |
| `$6FC0` | réservé | toujours 0 |
| `$7000` | murs : 30 octets par salle | adresse `$7000 + 30·salle` (`$9D56`) |
| `$7780` | 256 octets inconnus | `unknown` au PC ; au niveau 1 : 15 motifs de 16 octets puis `$FF` |

**Murs.** La salle est une grille de 20 × 12 cases de 7 unités × 16 lignes
(14 × 16 pixels). Les 30 octets forment 3 bandes de 4 lignes, 10 octets par
bande, chaque octet couvrant 2 colonnes × 4 lignes :

```
ligne écran R = 11 − rangée (rangée comptée vers le haut, comme Y)
octet  = 10·(R div 4) + (colonne div 2)
bit    = 4·(colonne mod 2) + (R mod 4)        ; bit à 1 = mur
```

Test d'une case : `$B40B` (colonne en `$02`, rangée en `$03`, pointeur de
salle en `$00/$01`) ; écriture : `$B3AA` (A=0 efface, ≠0 pose). Les **portes**
des niveaux sont des cases de mur posées ou effacées par le code de niveau
(niveau 1 : `$1740` ouvre progressivement une porte quand un objet est posé
sur une dalle). `tools/world.py --rooms` dessine les grilles en ASCII.

Colonne → octet HGR : table `$9B05` (= 2·X/7) ; la case est `$9B05[X]/2`.

### Salles spéciales (communes aux niveaux)

| Salle | Rôle |
|---|---|
| `$00` | écran « ESC » (menu, RETURN pour continuer, S pour sauver) |
| `$01` | titre du niveau et indices (touche `?`) |
| `$3E` | « insérez le disque » |
| `$3F` | **nulle part** : un objet dans `$3F` n'existe pas dans ce niveau |
| `$09`, `$0A`, `$0B`, `$0D` | intérieurs de Sparky, Checkers, Scanner et du 4ᵉ robot (`$8204`) |
| `$15-$1D` | au niveau 1 : intérieurs des puces (« Small chip 4 »…), vus dans le labo |

## Objets (`$6000-$69FF`)

256 objets (`$00-$FF`, `$FF` = aucun), un tableau de 256 octets par champ
(« structure de tableaux ») :

| Adresse | Champ | Valeurs |
|---|---|---|
| `$6000` | objet suivant dans la même salle | `$FF` fin ; listes **triées par numéro** (`$9E07`) |
| `$6100` | sprite | `$00-$3F`, sprites 16 octets en `$6A00` |
| `$6200` | couleur | 7 blanc, 5 orange, 6 bleu, 4 vert, 1 violet ; **sert aussi de niveau logique** (5 = 1) |
| `$6300` | salle | `$3F` = absent |
| `$6400` | X | |
| `$6500` | Y | |
| `$6600` | objet porteur | `$FF` libre ; sinon l'objet suit son porteur |
| `$6700` | décalage X par rapport au porteur | signé |
| `$6800` | décalage Y | signé |
| `$6900` | saisissable | `$00` oui, `$FF` non (broches, moitiés droites…) |

**Sprites** (`$6A00`, 64 × 16 octets) : 16 rangées de 7 bits, rangée 0 en
bas, bit 0 à gauche, chaque bit = 2 pixels (`render_room` de `world.py`).
Le sprite 0 (joueur) est réécrit à chaque pas pour l'animation de marche
(`$DFA3`, 8 images en `$BEC9`). La numérotation des sprites est celle du PC
(`RO_SPR_*`) : `$06`, `$0F-$12`, `$15/$16` broches d'entrée ; `$07-$0E`
portes ET/OU/OUX/NON (haut/bas) ; `$13/$14` moitiés de bascule ; `$17/$18`,
`$34/$35` broches de sortie ; `$19` nœud ; `$1B` boîte à outils ; `$21-$28`
puces ; `$2A/$2B` moitiés de robot ; `$36` télécommande ; `$37` bouton ;
`$38` clé ; `$39` cristal.

**Type de broche par sprite** (`$8393`, 64 octets) : `0` rien, `1` entrée,
`2` sortie (corps de porte, broche de sortie), `$FE` moitié de bascule, `$FD`
nœud, `$F0` puce. Point d'attache du fil par sprite : `$83D3` (dX) et `$8413`
(dY).

**Attache.** `$9C53` parcourt les objets `$00-$FE` à chaque tour : tout objet
dont `$6600 ≠ $FF` est replacé à porteur + décalage (avec passage de salle
par `$9DB9`). Les chaînes fonctionnent parce que les éléments d'un ensemble
ont des numéros croissants (robot `$F0` → moitié `$F1`, porte `$67` → entrées
`$68/$69`, capteur → ses sorties). Le joueur porte la télécommande (`$FC`,
`+1,+17`) et le curseur `$FE` ; un objet tenu (`$9C26`) est attaché au joueur
(`$A5CD`).

### Rôle des numéros d'objet

Les numéros sont **fixés par le moteur** (mêmes que le PC, vérifiés dans les
tables `$8200…` et le code) :

| Objets | Rôle |
|---|---|
| `$00` | joueur |
| `$01/$02` | 4ᵉ robot (gauche/droite), absent au niveau 1 |
| `$03-$08` | objets du niveau (aimant `$03`, cristal, jeton…) ; cibles des capteurs |
| `$09/$0A`, `$0B/$0C` | 4ᵉ robot : pince entrée/sortie, antenne entrée/sortie |
| `$0D-$0F` | capteurs de direction 1-3 (corps) ; sorties `$5A-$5D`, `$5E-$61`, `$62-$65` |
| `$10-$12` | capteurs de salle 1-3 (corps) ; sorties `$19-$1B` |
| `$13-$15` | capteurs de contact 1-3 (corps) ; sorties `$1F-$21` |
| `$1C/$1D/$1E` | entrée de pince de Sparky / Checkers / Scanner |
| `$22/$23` | sentinelle (gauche/droite) |
| `$24` | objet de niveau (poignée du distributeur au niveau 2) |
| `$25-$38` | 10 bascules, deux moitiés chacune (`$25` gauche, `$26` droite…) |
| `$39-$40`, `$41-$48`, `$49-$50`, `$51-$58` | propulseurs 0-3 puis pare-chocs 0-3 du 4ᵉ robot, de Scanner, de Checkers, de Sparky |
| `$59/$66`, `$E5/$E6`, `$E2/$E3` | antenne entrée/sortie de Sparky, Checkers, Scanner |
| `$67-$CF` | 35 portes : corps (= sortie) puis entrées 1 et 2 |
| `$D0`, `$EF`, `$E4` | sortie de pince de Sparky, Checkers, Scanner (`$82E3`) |
| `$D1-$DF` | 15 nœuds |
| `$E1` | boîte à outils |
| `$E7-$EE` | puces 1 à 8 |
| `$F0/$F1`, `$F2/$F3`, `$F4/$F5` | Sparky, Checkers, Scanner (moitiés gauche/droite) |
| `$F6-$FB` | objets du niveau (cristaux, clés…) ; cibles des capteurs |
| `$FC` | télécommande (sprite `$36`, ou `$1A` vide quand elle est coupée) |
| `$FD` | fer à souder (échangé avec le joueur par la touche `S`) |
| `$FE` | curseur (main) qui accompagne le joueur |

Les portes, bascules et nœuds non utilisés sont dans `$3F` ou dans la boîte
à outils ; la boîte (`$8DA8` bascules, `$8DA9` nœuds, `$8DAA` portes restantes
— au départ 8, 14, 30) les en sort.

## Textes (`$7880-$81FF`)

128 textes, 8 tableaux de 128 octets : salle (`$7880`), X (`$7900`), Y
(`$7980`), style (`$7A00`, 0 normal, 2 grand), police (`$7A80`), couleur
(`$7B00`), pointeur bas/haut (`$7B80/$7C00`) vers des chaînes ASCII bit 7
mis, `$0D` = retour à la ligne, `$00` = fin. Le tas des chaînes va de `$7C80`
à `$81FF` (le PC le prolonge jusqu'à `$94FF`). Affichage : `$A2A2` (tous les
textes de la salle `$9C2D`). Le texte `$0F` sert de compteur de la boîte à
outils : `$1DFE` écrit les nombres restants dans sa chaîne.

## Le circuit (`$8618-$8DAB`)

Même disposition que la structure `ROCircuit` du PC, base `$8618` :

| Adresse | PC | Contenu |
|---|---|---|
| `$8618` | `obj_wires.output_obj` | **fil issu de l'objet n : objet destination** (0 = pas de fil) |
| `$8718`, `$8818` | `x1`, `x2` | extrémités du fil (X) |
| `$8918`, `$8A18` | `y1`, `y2` | extrémités (Y) ; (x1,y1) côté source, (x2,y2) côté destination |
| `$8AF3+n` (`$8B18-$8B2B`) | `ff.state` | état de chaque moitié de bascule (0/1), n = `$25-$38` |
| `$8B07+n` (`$8B2C-$8B3F`) | `ff.inputs` | entrée appliquée à chaque moitié |
| `$8A6F+n` (`$8B40`) | `node_wires.input_obj` | source du nœud n (`$D1-$DF`) |
| `$8A7E+n` (`$8B4F`) | `output2_obj` | **deuxième sortie** du nœud |
| `$8A8D/$8A9C/$8AAB/$8ABA` (+n) | `x1/x2/y1/y2` | extrémités du deuxième fil |
| `$8B9A`, `$8BDA`, `$8C1A`, `$8C5A` | `chip_wires.y1/y2/x1/x2` | 64 fils de puces (8 puces × 8 broches) |
| `$8C9A` | `output_obj` | objet relié à la broche (puce k, broche p : indice 8k+p, base `$8370+puce`) |
| `$8CDA` | `output_pin` | `$FF` objet ordinaire, sinon broche d'une autre puce |
| `$8CB3+n` (`$8D1A-$8D82`) | `allocation.gates` | **type de la porte** dont le corps est n : 0 libre, 1 ET, 2 OU, 3 OUX, 4 NON |
| `$8D83`, `$8D92` | `allocation.nodes`, `.ff` | nœuds et bascules sortis de la boîte |
| `$8DA6` | `saved_cursor` | outil : `$00` joueur, `$FD` fer à souder (touches `C`/`S`, `$BDE1`) |
| `$8DA7` | `remote_is_on` | **télécommande** : 1 robots en marche, 0 tout arrêté (touche `R`, `$BE86`) |
| `$8DA8-$8DAB` | `toolbox` | bascules, nœuds, portes restantes ; boîte fermée |

Un fil est donc **attaché à sa source** : au plus un fil part de chaque objet
(deux pour un nœud), et c'est la source qui le porte. Les extrémités sont
des coordonnées absolues : quand on déplace un objet, `$B8E6` cherche les fils
dont une extrémité est au point d'attache des broches de l'objet et la
déplace d'autant (`$8E84/$8E85` = déplacement du tour). Exemple, au niveau 1
(`world.py --circuit`) : `$4D` (pare-chocs 0 de Checkers) → `$26` (bascule 1
droite), extrémités (35,25)-(71,84).

## Les robots

### Tables fixes (`$8200`, bloc `$075`)

| Adresse | Contenu (Sparky, Checkers, Scanner, 4ᵉ) |
|---|---|
| `$8200` | objet du robot : `F0 F2 F4 01` |
| `$8204` | salle intérieure : `09 0A 0B 0D` |
| `$8208`/`$820C` | 4 points testés contre les murs pour entrer/sortir (`$FEEB`) |
| `$82DF` | entrée de pince : `1C 1D 1E 09` |
| `$82E3` | sortie de pince : `D0 EF E4 0A` |
| `$82E7`/`$82EB` | décalage X/Y de l'objet saisi, par côté |
| `$82EF` | sortie d'antenne : `66 E6 E3 0C` |
| `$82F3` | entrée d'antenne : `59 E5 E2 0B` |
| `$82FF` / `$8302` | capteurs de salle : corps `10 11 12`, sorties `19 1A 1B` |
| `$8305` / `$8308` | capteurs de direction : corps `0D 0E 0F`, 1ʳᵉ sortie `5A 5E 62` |
| `$830B` / `$830E` | capteurs de contact : corps `13 14 15`, sorties `1F 20 21` |
| `$8361`/`$8365` | déplacement par propulseur : côté 0 (0,−4), 1 (−2,0), 2 (0,+4), 3 (+2,0) |

### Enregistrement d'état (`$8DC9 + 26·r`, terminé par `$FF` en `$8E31`)

Identique au `RORobot` du PC :

| Octets | Champ |
|---|---|
| 0-1 | moitié gauche (deux fois) |
| 2-3 | moitié droite (deux fois) |
| 4-7 | objets propulseurs, côtés 0-3 |
| 8-11 | objets pare-chocs, côtés 0-3 |
| 12-15 | animation des propulseurs (0 arrêt, 1→2→3→1) |
| 16-19 | couleur des pare-chocs (5 = contact) |
| 20-23 | contact des pare-chocs : 0 libre, 1 premier tour (son 2, `$D237`), `$FF` contact qui dure ; remis à 0 quand le pare-chocs refroidit (`$D140`) |
| 24 | batterie, 0 à 15 (`$8DE1`, `$8DFB`, `$8E15`, `$8E2F`) |
| 25 | interrupteur des propulseurs (`$8DE2`…) |

Puis `$8E32-$8E39` : accumulateurs de décharge 16 bits (poids fort, poids
faible) par robot. `$8DAD-$8DB0` : objet saisi par chaque robot (0 = rien).

Le **côté** d'un propulseur est la direction du mouvement qu'il produit :
le propulseur 0 est en haut du robot et le pousse vers le bas ; le
pare-chocs 0 est en bas. Vérifié sur Sparky (salle `$09`) : propulseurs
`$51` (haut, Y=160), `$52` (droite), `$53` (bas, Y=8), `$54` (gauche) ;
pare-chocs `$55` (bas), `$56` (gauche), `$57` (haut), `$58` (droite).

### Intérieur et extérieur

Un robot est fait de deux objets (gauche `$F0`, droite `$F1` attachée à
`+5,0`) dans une salle du monde ; son intérieur est une salle à part
(`$8204`) où se trouvent ses broches (propulseurs, pare-chocs, pinces,
antennes) et ce qu'on y câble. Le lien entre les deux n'est fait que par le
code : les capteurs et pinces lisent la salle **du robot** quand leur corps
est dans une salle intérieure (`$D8CA` : salle `$09` → salle de `$F0`,
etc.), et le joueur passe de l'un à l'autre par `$FE25` (voir
[simulation.md](simulation.md#entrer-dans-un-robot)). Au niveau 1, le joueur
trouve les trois robots déjà câblés :

- **Sparky** : puce 2 « WALLHUGGER » (`$E8`) reliée aux 4 pare-chocs et 4
  propulseurs (longe les murs) ; capteur de salle 1 → porte NON 6 → pince.
- **Checkers** : bascule 1 et portes NON/ET entre pare-chocs et propulseurs
  (va-et-vient) ; capteur de salle 2 → antenne.
- **Scanner** : bascule 2 commandée par les pare-chocs 1 et 3, sorties sur
  les propulseurs 1 et 3 (aller-retour horizontal) ; capteur de salle 3 →
  NON 5 → pince.

## Niveaux

| Niv. | Nom (salle `$01`) | Monde (salles+textes) | Code `$0803` | Données `$8EF0` |
|---|---|---|---|---|
| 1 | « Escape from the City Sewer! » | `$090` → `$6000+$2200` (avec les objets) | `$0A1`, `$1105` | `$0AA`, `$505` |
| 2 | « Ride the Subway to the Town! » | `$0AD` → `$6E40+$13C0` | `$0B7`, `$1092` | `$0C0`, `$142` |
| 3 | « Explore the Town! » | `$0C1` | `$0CB`, `$1270` | `$0D5`, `$5FB` |
| 4 | « Master Computer Center » | `$0D8` | `$0E2`, `$108B` | `$0EB`, `$561` |
| 5 | « Travel the Skyways to freedom! » | `$0EE` | `$0F8`, `$1253` | `$102`, `$5DE` |

Les niveaux 2 à 5 ne rechargent que `$6E40-$81FF` : couleurs, liens et murs
des salles, textes. **La table des objets et les sprites ne sont chargés
qu'au niveau 1** et restent en mémoire pour toute la partie, comme les
robots et le circuit (`$8200-$8ED4`, chargés avec le moteur par `$45EF`).
Les listes de salles (`$6E00`) ne sont pas rechargées non plus : elles sont
maintenues à jour par `$9E07`.

### Passage au niveau suivant

Chaque code de niveau contient la même séquence de sortie (niveau 1 :
`$10CC → $0AE6`, niveau 2 : `$8FE9 → $0AEC`, niveau 3 : `$942B`, niveau 4 :
`$17BF → $0AFF`) :

1. condition de victoire propre au niveau (niveau 1 : le joueur, sous sa
   forme normale, exactement en `X=$20, Y=$20` dans la salle `$2A`, la salle
   « Prepare for an experience that will transport you… » ; niveau 2 :
   ticket de sortie `$F7` posé près de (49,16) dans la salle `$02`, puis
   joueur en (123,154) au bout de l'escalator) ;
2. animation de montée : joueur en couleur 4, 9 notes montantes, son 9 ;
3. **tri des objets** : tout objet qui n'est ni tenu, ni attaché, ni dans
   une salle intérieure de robot (`$8204`) est envoyé en `$3F` (`$0AFB`).
   La moitié gauche d'un robot n'est attachée à rien : **un robot que le
   joueur ne tient pas est perdu** (sa moitié droite et ce qu'il porte le
   suivent en `$3F`). Seuls l'objet tenu (robot compris, avec ce qu'il
   porte) et le contenu des intérieurs passent au niveau suivant (« You CAN
   take it with you (if you hold on tight) »). **[vérifié]** par l'analyse
   du niveau 2 ([niveau2.md](niveau2.md)). Pour emporter plusieurs robots,
   on les emboîte : un robot posé dans l'intérieur du robot tenu passe
   aussi. **[vérifié au clavier]** : Scanner pris par en dessous (toucher
   un robot par en dessous le saisit, par ailleurs on entre dedans), porté
   dans Sparky, posé, sortie, Sparky pris ; au niveau 2, Sparky est avec le
   joueur, Scanner dans `$09`, Checkers en `$3F` ;
4. le joueur redevient le sprite 0 en `$3F` ; les objets du niveau suivant
   sont **placés par le niveau qui se termine**, à partir d'une table :

   | Niv. | Table (objet, salle, X, Y) | Objets placés |
   |---|---|---|
   | 1 → 2 | `$0B98/$0B9E/$0BA4/$0BAA`, 6 entrées | `$F7` ticket (`$20`), `$24` poignée (`$3D`), `$04` jeton (`$2C`), `$E9` puce 3 (`$32`), `$14` capteur de contact 2 (`$30`), `$EA` puce 4 (`$28`) |
   | 2 → 3 | `$0B39/$0B49/$0B59/$0B69`, 16 entrées | `$04-$07`, `$0D`, `$0E`, `$15`, `$17`, `$18`, `$22`, `$EB`, `$F7-$F9`, `$FB`, `$EC` |
   | 3 → 4 | `$9325`, tables `$9396/$93A4/$93AD/$93B6`, 9 entrées | `04 06 07 F7 FB` (sprite `$33`, disquettes), `$22` en `$3C`, puces 7-8, 4ᵉ robot `$01` en `$26` ([niveau3.md](niveau3.md)) |
   | 4 → 5 | `$172A → $0AFF` | `$08` disque en `$37` (63,160), chargeur en `$15` ; `$1808-$1867` = sprites copiés pour le niveau 5 ([niveau4.md](niveau4.md)) |

   puis la boîte à outils `$E1` est mise en (43,45) salle `$26` ;
5. `$02D0 = 2`, `$02D1 = numéro du niveau suivant − 1`, saut au vecteur
   RESET : le module résident (`$4093`) charge le niveau par `$40B6…$40DA`.

Autres commandes du même mécanisme `$02D0` (voir l'analyse du chargeur) :
1 menu, 4 sauvegarde, 5 édition de puce (`L` en tenant une puce `$E7-$EE`).

### Niveau 1 : les égouts (code `$0803-$1907`, données `$8EF0`)

- départ salle `$28` (« Welcome, Traveler! »), robots dans `$02` ;
  sortie salle `$2A` ; 42 salles utilisées.
- `$1115`, au premier tour où le joueur quitte les salles `$28` et `$02` :
  place des objets selon des index qui tournent à chaque tour tant qu'il y
  est (et `$D414`, pseudo-aléatoire) — les parties diffèrent donc :
  la clé `$FA` dans l'intérieur de Sparky, Checkers ou Scanner (`$11D6` :
  `09 0A 0B`, « The key to success lies within ») ; la puce `$E7` et le
  cristal `$04` dans l'une des salles `08 0C 07 06 17 16` (`$11D9`, X/Y en
  `$11DF/$11E5` et `$11EB/$11F1`) ; le cristal `$F6` et le bouton `$03`
  répartis entre les salles `$22` (Y=36) et `$23` (Y=96) (`$11F7/$11F9`).
- `$0CC5` : l'**Ampire Bot** (« Black crystals foil Ampire Bots »), automate
  à 5 états `$8F56` qui circule de salle en salle (`$10`, `$0F`, `$21`, `$15`,
  `$12`, `$11`) et poursuit une cible `$8F58` choisie parmi Sparky,
  Checkers, Scanner (s'ils ont de la batterie), le cristal `$F6` s'il est
  chargé et le cristal `$04` (table `$1237`). Quand il la tient 20 tours :
  batterie du robot −5, ou cristal `$F6` déchargé (couleur 7), ou `$04`
  pris (`$8F50`, état 5). Comportement exact du cristal noir (`$04` vert
  au départ) non vérifié en jeu.
- `$1740` : deux dalles (salle, objet attendu, position : `$1288-$129A`) ;
  y poser l'objet bascule une porte, ouverte ou fermée case par case par
  `$B3AA`.
- `$0C23` (`$0C77`, `$0CA7`, `$0C32`, `$0C68`) : animations de la salle `$18`
  et objets clignotants (tables `$8F2E-$8F3F`).
- pas de chargeur de cristal (`$8454 = $3F`) ; le niveau 2 en met un en
  salle `$32`, (110,96) (`$0976`).

### Niveaux 2 à 5

Même squelette de boucle principale (voir [simulation.md](simulation.md)) ;
les routines propres au niveau sont appelées au milieu (listes obtenues avec
`tools/disasm.py` sur `build/lvlN.bin`) :

| Niv. | Routines du niveau dans la boucle |
|---|---|
| 2 | `$0D80 $1784 $0C9E $0E55 $0ED7 $1426 $0BFF $0FE9 $1570 $0BD2 $0F29 $186F` |
| 3 | `$0C6A $19B5 $9058 $15EF $8F89 $1471 $1702 $1034 $927D $1842 $8F55 $9236 $0AFC $0D43 $15AD $16BE $92CA $0DF1 $0D8E $0DB5` |
| 4 | `$1670 $920F $0E67 $0BD6 $14EA $0C77 $0EFD $12B0 $1350 $931C $0C33 $0FBB $10C8 $16B4 $1689 $918C $1484 $0EDA` |
| 5 | `$17B9 $09D5 $0B1A $0C23 $0E18 $10D6 $8F9A $7294 $13B3` (`$7294` est dans la zone des textes) |

Le détail, routine par routine, est dans [niveau2.md](niveau2.md),
[niveau3.md](niveau3.md), [niveau4.md](niveau4.md) et
[niveau5.md](niveau5.md). Thèmes : niveau 2 métro
(jeton, tourniquet, bouton d'appel du train, stations, ticket de sortie,
escalators) ; niveau 3 ville (orage magnétique et bouclier à mettre dans un
robot, éditeur de capteur, distributeur, ascenseur, « Form-12 » pour le
portier, sentinelle et deux boutons) ; niveau 4 centre de calcul (robot
central à apprivoiser, « Sweeper 'Bot », ascenseur « Going up! ») ; niveau 5
voies aériennes (trafic, grille bleue que le robot doit traverser seul,
serrure sonore du « Disk-O-Tek », boutons dans l'ordre, transporteur,
interrupteur de garde avec minuterie). Les puces 3-4, 5-6, 7-8 sont
fournies vierges aux niveaux 2, 3, 4.

## Outils

```sh
# vidage complet d'une partie (salles, objets, textes, robots, circuit)
python3 -I tools/world.py --ram build/ram_robots.bin > build/l1.txt
# cartes : une image par salle + world.png (salles placées par leurs liens)
python3 -I tools/world.py --ram build/ram_robots.bin --png build/map_l1
# salles et textes d'un niveau sans émulateur (objets = ceux du niveau 1)
python3 -I tools/world.py --level 3 --rooms --text
# désassemblage annoté (noms des tables du monde en commentaire)
python3 -I tools/disasm.py build/eng.bin 9C53 9E7A
```

`build/eng.bin` = vidage `game_room0.bin` avec le bloc `$080` en `$D000`
(banque 2, le code) ; `build/lvlN.bin` = même image avec les blocs du
niveau N. `build/goto_robots.sh ÉTAPES…` démarre une partie et marche
jusqu'à la salle des robots avant d'exécuter les étapes a2shot données.

## Points incertains

- Couleurs `$6E40/$6E80` : index de motifs (`$9B91…`), correspondance exacte
  avec les teintes affichées laissée à l'analyse graphique.
- `$8208/$820C`, `$82D7/$82DB`, `$8317-$8357` : tables de décalages
  (entrée dans les robots, dessin des pinces, décor des robots) relevées
  mais pas toutes vérifiées.
- Noms d'objets `$03-$08`, `$24`, `$F6-$FB` : ce sont des emplacements
  libres que chaque niveau habille (sprite et couleur changés par le code de
  niveau).
