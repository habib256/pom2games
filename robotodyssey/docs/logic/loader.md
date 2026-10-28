# Module résident, menu, faces de disque, chargeur et sauvegardes

*[← ANALYSE](../ANALYSE.md)*

Ce document décrit le module résident `$4000-$51FF` (blocs `$030-$038`),
le pilote de blocs `$5200-$5FFF`, le menu, la carte des segments chargés par
mode et par face, et le format des sauvegardes (parties et puces).
Image de référence : `build/l4000_64k.bin` (RAM au saut en `$4000`).
Les preuves dynamiques viennent d'a2shot (`watch:52C8:0042:6`, qui affiche
commande, unité, tampon et numéro de bloc à chaque accès disque).
Ce qui reste incertain est signalé par **(?)**.

## Principe : un « système » rechargé à chaque service

Le module et le pilote de blocs vivent en `$4000-$5FFF`, c'est-à-dire dans
la page HGR 2 que le jeu utilise comme tampon de composition : en jeu, ils
n'existent plus. Quand le programme en cours a besoin d'un service (niveau
suivant, menu, sauvegarde, puce), il écrit une requête en page 2 et
**redémarre la machine** :

```
0AC9  BIT $C081            ; ROM
      LDA $02D0 / EOR #$A5 / STA $02CF   ; signature de démarrage à chaud
      LDA #niveau / STA $02D2            ; mode courant (0-4 niveau, 5 labo)
      JMP ($03F2)                        ; vecteur RESET = $Cs00 du contrôleur
```

(code du niveau 1 en `$0AA0-$0AE0`, bloc A `$0A2` ; le même motif existe
dans chaque code de niveau, `LDA #$00..#$04 / STA $02D2`, et dans le code du
labo, bloc B `$0E2`, `LDA #$05`.)

L'amorce relit la piste 0 (`$5100-$5FFF`), saute le sondage des unités
`$5F00` si `$02D0 EOR $A5 = $02CF` (`$08EC-$08FA`), recharge les blocs
`$030-$038` en `$4000` et y saute.

### Variables de communication (page 2)

| Adresse | Rôle |
|---|---|
| `$02CE` | bit 7 = protection reconnue (voir [Protection](#protection-piste-7)) ; recopié dans `$9C4E` au lancement d'un mode |
| `$02CF` | signature = `$02D0 EOR $A5` ; incrémentée dès qu'elle a servi (`$403E`), donc un RESET manuel retombe en démarrage à froid |
| `$02D0` | requête (état) : index des tables `$4088`/`$408F` |
| `$02D1` | argument : niveau suivant (1-5) ou numéro de puce (0-7) |
| `$02D2` | mode : 0-4 Robotropolis niveau 1-5, 5 Innovation Lab, 6 Preview, 7-12 didacticiels, 13 Chip Design |
| `$02E0-$02F9` | drapeaux « emplacement occupé » du répertoire affiché |

Page zéro du module : `$0E` disque voulu (0, 1, 2 = PROGRAM-A/B/C ;
`$10+i` = STORAGE sur l'unité `$D0+$10+i`, soit `$E0+i`), `$0F` lettre
choisie (0 = A), `$00-$07`, `$10-$13` temporaires du chargeur,
`$42-$47` paramètres du pilote, `$E0-$EF` table des unités.

## Démarrage à chaud et répartiteur (`$4000-$408E`)

```
4000  JMP $4006            ; entrée après amorçage
4003  JMP $43CE            ; entrée « choix du menu » (A = entrée choisie)
4006  JSR $0310            ; réinitialise le pilote texte HGR
      $0E = 0, BIT $C010
      si $02CF EOR $A5 <> $02D0 -> 4033 (froid)
      somme de contrôle : A = $95, CLC, ADC de $9500 à $9BFF
      (7 pages, retenue propagée) ; si A <> $F5 -> 4033
4033  JSR $48F2 ; $02D0 = $02CF = 0
403E  INC $02CF            ; consomme la signature
      RTS vers ($4088[x] | $408F[x]<<8) + 1, x = $02D0
```

La somme de contrôle vaut `$F5` sur le moteur commun du disque (segment
`$05B`, identique sur les trois faces ; recalculée en Python sur le disque et sur
trois images de RAM en jeu). Elle vérifie que le moteur
`$9500-$B8D6` est encore en mémoire : le menu écrase cette zone
(`menu_data` va jusqu'à `$9BCA`), un démarrage à froid aussi.

| `$02D0` | Cible | Demandé par | Action |
|---|---|---|---|
| 0 | `$4059` | démarrage à froid | identifier le disque, charger le menu, `JMP $6000` (avec titre) |
| 1 | `$4059` | ESC dans un jeu | idem, `JMP $6003` (retour au menu) |
| 2 | `$4096` | sortie d'un niveau (`$0AA0`, Y = niveau suivant) | charger le niveau `$02D1` |
| 3 | `$4033` | aucun appel trouvé | démarrage à froid |
| 4 | `$4108` | « To save game, press S » (`$0ABE`, labo `$0A21`) | sauvegarder la partie |
| 5 | `$4260` | `L` en tenant une puce (`$0AAB`, labo `$0A03`), Y = puce | charger une puce |
| 6 | `$419C` | sauvegarde de puce au labo (`$0A0E`), Y = puce | sauvegarder une puce |

Mesuré : `regs:00:00:0Y go:0AA0` depuis la première salle provoque le
redémarrage puis la lecture des blocs du niveau Y+1 (tableau plus bas) ;
Y = 5 joue la fin (« Congratulations!! You are one of the few, true Robot
Masters »).

## Identification des faces

Bloc 0, octets 0-3 :

| Disque | Octets | Face (`$0802`) | Contrôle (`$0803`) |
|---|---|---|---|
| A ROBOTROPOLIS | `01 2C 00 A5` | `$00` | `$A5` |
| B LABS | `01 2C 01 A4` | `$01` | `$A4` |
| C TUTORIAL | `01 2C 02 A7` | `$02` | `$A7` |
| STORAGE (créée par le jeu) | `01 2C 11 B4` | `$11` | `$B4` |

`$2C` fait des octets 2-3 l'opérande d'un `BIT` : le code d'amorçage
en `$0801` passe dessus sans effet.

- `$4C84` lit le bloc 0 de l'unité `$0E` en `$0800` (descripteur `$4C9F`),
  renvoie A = face et Z = 1 si `face EOR $A5 = contrôle`.
- `$4C6C` donne la face voulue pour le mode `$02D2` : 0-4 → A, 5-6 et 13 →
  B, 7-12 → C.
- `$4CAA` boucle : disque programme de la bonne face → OK ; disquette
  STORAGE (face ≥ `$10`) quand on en veut une → l'unité est retenue
  (`$4CB5` l'échange avec `$E1`, `$0E = $11`) ; sinon message
  `Insert Robot Odyssey PROGRAM-<A+face> disk` / `STORAGE disk`
  (`$4D0F`) + `and press RETURN` (`$4955`) ; ESC abandonne (C = 1).
- Le menu (états 0/1) accepte n'importe quelle face programme : les
  segments du menu sont identiques sur A, B et C ; une face `$11` ou une
  signature fausse fait demander PROGRAM-A (`$4054`).

Lire le bloc 0 en `$0800-$09FF` écrase le début du code du mode
(`$0803`) : c'est pourquoi tout retour au jeu recharge ce code (`$437E`).

## Unités : sondage `$5F00` et pilote `$5200`

Au démarrage à froid, `$5F00` construit en `$E0-$EE` (fin = `$00`) la
liste des unités : `$E0` = unité d'amorçage, puis les emplacements 7 à 1 :

- carte Disk II (`$Cn01/03/05 = $20/$00/$03`, `$CnFF = $00`) : `$n0`
  (lecteur 1) ; le lecteur 2 est sélectionné et, si son registre de
  données bouge, ajouté avec le bit 7 (`$n0|$80`) ;
- carte 13 secteurs (`$CnFF = $FF`) ignorée ;
- SmartPort (`$Cn07 = $00`, `$CnFE` = `$BF`) : appel STATUS unité 0 puis une
  entrée `$n0|u` par unité `u`.

`$5200` reçoit A = entrée de la table et `$42` = commande. Quartet bas nul
→ Disk II, routine interne `$52C8` (commandes 1-2 ; 3 = formatage refusé
ici, voir `$5A00`) ; sinon appel SmartPort par `($CnFF)+3` : 0 STATUS,
1 READ, 2 WRITE, 3 FORMAT, avec l'unité `u` (codes d'erreur ProDOS
`$27` E/S, `$2B` protégé en écriture, `$2F` absent). Les disques programme
se lisent toujours sur `$E0` (le chargeur remplace un `$0E < $10` par
`$10`) ; la STORAGE peut être sur une autre unité (second lecteur, disque
3,5" ou dur) et est cherchée de proche en proche (`$4BEE`, `$4DF1`).
Le jeu sait donc sauvegarder sur une unité SmartPort, avec 26 emplacements
au lieu de 4 parties / 13 puces.

`$52C8` : lecture/écriture d'un bloc Disk II (blocs < `$118`, sinon `$27`).
Structure (tables de nibbles `$5496`, variables `$5656-$567C`, recherche de
piste `$5422`, champ d'adresse `$5698`, 64 essais puis recalibrage) proche
du pilote Disk II de ProDOS **(?)**, non comparé octet à octet.

## Le chargeur `$4B03`

`JSR $4B03`, puis en ligne : nombre de segments, commande, un pointeur par
segment vers un descripteur bloc/adresse/longueur (LE16 ×3).

- Commande bits 0-1 : 1 lecture, 2 écriture, 3 formatage (sans segment ;
  `$5A00` si l'unité est un Disk II, sinon FORMAT SmartPort). Bit 6 (`$41`,
  `$4DD8`) : lecture silencieuse ; en cas d'échec sur le bloc 0 sans autre unité,
  retour avec V = 1 et sans message.
- Lecture : quand il reste moins de 512 octets, le bloc passe par
  `$5E00-$5FFF` et seuls les octets utiles sont copiés (`$4BA2`).
- Erreurs (`$4BE0`) : `$2B` → `Write-protect error` + `Remove`/`Slide
  write-protect tab` (Disk II / SmartPort) ; échec du bloc 0 en cherchant
  une STORAGE → unité suivante ; sinon `Disk error--check drive and press
  RETURN` et nouvel essai (ESC = abandon, C = 1).
- Sortie par `$46FE` : retour après les paramètres, C = erreur.

Descripteurs remplis à l'exécution : `$4C9F` (bloc 0 → `$0800`), `$4ED8`
(blocs 0-2 ← `$5A00`), `$4FF1`/`$4FF7` (puce, `$477A`), `$500F`, `$5015`,
`$501B`, `$5021` (partie, `$4740`). Deux descripteurs sont modifiés avant
usage : `$5045` (bloc `$03E`, `$6300+$38CB` pour le menu, `$6200+$01CB`
pour la fin) et `$5051` (bloc `$06D`, `$D400` au niveau 1, `$D800` en
Chip Design). Les octets `$4FFD-$500E` ne sont pas des descripteurs mais
deux tables de 8 pointeurs (`$8045+$12B·k`, voir puces).

## Menu

Segments communs aux trois faces : `scenes` (`$039`, `$0803-$0DD5`),
`menu` (`$03C`, `$6000-$62A5`), `menu_data` (`$03E`, `$6300-$9BCA`).
`$0803` est un interpréteur appelé par `JSR $0803` suivi d'une commande et
de ses paramètres en ligne ; il dessine aussi les scènes d'intro et de fin
(non détaillé ici). Il contient les tables d'adresses de lignes HGR
(`$0806` octets bas, `$08C6` hauts).

`$6000` (froid) et `$6003` (retour) appellent la vérification de
protection `$6205` puis `ROR $02CE`, dessinent l'écran et entrent dans la
boucle `$6049` :

- `$6090` : entrée sélectionnée (0-9, 1 au départ) ; `$6091-$609A` :
  ordonnée du cadre de chaque entrée ; `$609B-$60A4` : ordonnée de la
  petite icône robot ; cadre tracé en XOR (`$60E7`).
- Touches (`$6156`) : ESPACE, → et ↓ = suivante ; ← et ↑ = précédente
  (bouclage 9 ↔ 0) ; RETURN ou un bouton = valider ; ESC = redémarrage par
  `($03F2)`. Manette 1 : axe Y ≥ `$C0` suivante, < `$40` précédente.
- Séquence cachée : Ctrl-A met `$03FF` à 1 (`$61C4`), Ctrl-L l'incrémente
  (`$61CB`), `T` avec `$03FF = 2` y écrit `$85` (`$61D1`). Le code des
  niveaux compare chaque touche à `$03FF` : Ctrl-E bascule le bit 0 de
  `$9C30` (`$0996`), soit les murs du joueur (voir
  [simulation.md](simulation.md)). **[vérifié]** en a2shot.

Validation : `JMP $4003` avec A = numéro de programme (mesuré en
a2shot, `watch:4003`) ; `$43CE` en déduit `$02D2` (0 → 0, sinon A+4).

| Entrée (ordre écran) | A | `$02D2` | Face | Écran intermédiaire |
|---|---|---|---|---|
| Robotropolis Preview | 2 | 6 | B | – |
| Robotropolis | 0 | 0 | A | `To go to the game, press RETURN` / `To load an old saved game, press O` |
| Innovation Lab | 1 | 5 | B | idem avec `lab` |
| Robot Anatomy | 3 | 7 | C | – |
| Robot Wiring | 4 | 8 | C | – |
| Sensors | 5 | 9 | C | – |
| The Toolkit | 6 | 10 | C | – |
| Robot Circuits | 7 | 11 | C | – |
| Robot Teamwork | 8 | 12 | C | – |
| Chip Design | 9 | 13 | B | – |

L'écran intermédiaire (`$43E5-$4456`) accepte RETURN ou un bouton (`$C061 EOR
$C062` négatif), `O` (chargement, `$445E`) et ESC (retour menu).

## Lancement d'un mode (`$4563`)

1. `$4CA5` : demander et vérifier la face du mode.
2. Mode 0 : charger l'intro (`scenes`, `intro`, `story_data`), `JSR $6000`
   (« Welcome, Traveler! », attend RETURN), revérifier la face A, puis
   mode 4.
3. Modes 7-12 : charger le socle commun des didacticiels.
4. `JMP` indirect par `$45BD/$45C7` (mode 4-13) vers la liste du mode,
   via `$44DA` (sélectionne la RAM de la banque 2 de la carte langage).
5. `$9C4E = $02CE`, puis `$45B5` : banque 2 en lecture/écriture,
   `JMP $0803`.

`$4EDE` (A = masque, bit 7 = puce 0) remplit les puces non chargées avec le
modèle vide `$4F10` (`00×8, 07 FF FF FF`) dans la banque 1 `$D000+$400·k`.

## Carte des segments

Chaque segment n'existe que sur la face indiquée : les numéros de bloc se
recouvrent d'une face à l'autre (`$008` est l'intro sur A, le premier
segment des didacticiels sur C, le répertoire de la bibliothèque sur B).
Sources : appels `$4B03` (`tools/loadcalls.py`) + traces a2shot de chaque
entrée du menu, des niveaux 2-5 et de la fin. Noms = rôle dans
`tools/extract.py`. LC1/LC2 = banques 1/2 de `$D000-$DFFF`.

| Blocs | Adresse | Longueur | Face | Rôle |
|---|---|---|---|---|
| `$000` | `$0800` | 1 bloc | toutes | identification de face |
| `$030-$038` | `$4000` | `$1200` | toutes | `module` |
| `$039-$03B` | `$0803` | `$05D3` | ABC | `scenes` : interpréteur de scènes |
| `$03C-$03D` | `$6000` | `$02A6` | ABC | `menu` |
| `$03E-$05A` | `$6300` | `$38CB` | ABC | `menu_data` |
| `$05B-$06C` | `$9500` | `$23D7` | ABC | `engine` : moteur commun |
| `$06E-$070` | `$5A00` | `$0600` | AB | `format` : formateur Disk II |
| `$06D` | `$D400` LC1 | `$0183` | A | `chip_preset` : puce 1 du niveau 1 |
| `$06D` | `$D800` LC1 | `$0183` | B | même bloc, puce 2 de Chip Design |
| `$008` | `$6000` | `$019A` | A | `intro` |
| `$009-$02D` | `$6300` | `$49BB` | A | `story_data` (intro et fin) |
| `$02E` | `$6000` | `$01AD` | A | `ending` |
| `$03E` | `$6200` | `$01CB` | A | début de `menu_data` pour la fin |
| `$072-$074` | `$1AB0` | `$054C` | A | Robotropolis `$1AB0-$1FFB` **(?)** |
| `$075-$07B` | `$8200` | `$0CD5` | A | Robotropolis `$8200-$8ED4` **(?)** |
| `$07C-$07F` | `$B8E0` | `$06B9` | A | Robotropolis `$B8E0-$BF98` **(?)** |
| `$080-$087` | `$D000` LC2 | `$0FFE` | A | Robotropolis, carte langage |
| `$088-$08F` | `$F000` | `$0FF4` | A | Robotropolis, carte langage |
| `$071` | `$D000` LC1 | `$01AA` | A | puce 0 du niveau 1 |
| `$090-$0A0` | `$6000` | `$2200` | A | monde, niveau 1 |
| `$0A1-$0A9` | `$0803` | `$1105` | A | code, niveau 1 |
| `$0AA-$0AC` | `$8EF0` | `$0505` | A | données, niveau 1 |
| `$0AD-$0B6`, `$0B7-$0BF`, `$0C0` | `$6E40`, `$0803`, `$8EF0` | `$13C0`, `$1092`, `$0142` | A | niveau 2 |
| `$0C1-$0CA`, `$0CB-$0D4`, `$0D5-$0D7` | idem | `$13C0`, `$1270`, `$05FB` | A | niveau 3 |
| `$0D8-$0E1`, `$0E2-$0EA`, `$0EB-$0ED` | idem | `$13C0`, `$108B`, `$0561` | A | niveau 4 |
| `$0EE-$0F7`, `$0F8-$101`, `$102-$104` | idem | `$13C0`, `$1253`, `$05DE` | A | niveau 5 |
| `$071-$076` | `$0803` | `$0BAE` | B | Preview, code |
| `$077-$07C` | `$14C0` | `$0AF6` | B | Preview |
| `$07D-$08C` | `$6000` | `$1FF8` | B | Preview |
| `$08D-$091` | `$7F80` | `$0818` | B | Preview |
| `$092-$094` | `$8880` | `$0440` | B | Preview |
| `$095-$096` | `$9000` | `$0395` | B | Preview |
| `$097-$09E` | `$D000` LC2 | `$0F65` | B | Preview |
| `$09F` | `$E000` | `$00CE` | B | Preview |
| `$0A0-$0A5` | `$E470` | `$0BD0` | B | Preview |
| `$0A6` | `$D000` LC1 | `$0013` | B | Chip Design, puce 0 |
| `$0A7-$0B1` | `$0B00` | `$149B` | B | Innovation Lab et Chip Design |
| `$0B2-$0B5` | `$B8E0` | `$06A1` | B | Lab et Chip Design |
| `$0B6-$0BD` | `$D000` LC2 | `$0FFA` | B | Lab et Chip Design |
| `$0BE-$0C5` | `$F000` | `$0FF8` | B | Lab et Chip Design |
| `$0C6-$0E0` | `$6000` | `$3500` | B | Innovation Lab |
| `$0E1-$0E2` | `$0803` | `$02FB` | B | Innovation Lab, code |
| `$0E3-$0FD` | `$6000` | `$3500` | B | Chip Design |
| `$0FE-$0FF` | `$0803` | `$02F3` | B | Chip Design, code |
| `$100-$103` | `$0B00` | `$0800` | B | Chip Design (recouvre `$0A7`) |
| `$008` | `$5A00` | 1 bloc | B | répertoire de la bibliothèque de puces |
| `$009-$026` | `$D000+$400·k` + `$5C00` | 3 blocs/puce | B | bibliothèque, puces A-J |
| `$008-$00D` | `$14C0` | `$0B1C` | C | socle des didacticiels |
| `$00E-$010` | `$B900` | `$0572` | C | socle des didacticiels |
| `$011-$018` | `$D000` LC2 | `$0FF2` | C | socle des didacticiels |
| `$019-$01F` | `$F000` | `$0C76` | C | socle des didacticiels |
| `$020-$026` | `$0803` | `$0C9E` | C | code : Anatomy, Wiring, Sensors |
| `$027-$02A` | `$14C0` | `$0679` | C | Robot Anatomy |
| `$06D-$086` | `$6000` | `$3350` | C | Robot Anatomy |
| `$02B-$02E` | `$14C0` | `$0679` | C | Robot Wiring |
| `$087-$09E` | `$6000` | `$2EF9` | C | Robot Wiring |
| `$09F-$0B8` | `$6000` | `$33D8` | C | Sensors |
| `$0B9-$0BD` | `$0803` | `$0982` | C | The Toolkit, code |
| `$0BE-$0C1` | `$14C0` | `$0679` | C | The Toolkit |
| `$0C2-$0DA` | `$6000` | `$3165` | C | The Toolkit |
| `$0DB-$0E0` | `$0803` | `$0A46` | C | code : Circuits, Teamwork |
| `$0E1-$0E4` | `$14C0` | `$0679` | C | Robot Circuits |
| `$0E5-$0FD` | `$6000` | `$30E0` | C | Robot Circuits |
| `$0FE-$116` | `$6000` | `$30E2` | C | Robot Teamwork |

Comparaison des trois faces bloc par bloc : 1-3, 5-7, `$02F`, `$030-$037`,
`$039-$059`, `$05B-$06C` identiques ; le bloc 0 ne diffère que par les
octets 2-3 et sa seconde moitié, le bloc `$038` qu'après `$51B2` (hors
table), `$05A` qu'après la fin de `menu_data` : ce sont des octets de
remplissage. `$06D-$070` sont identiques sur A et B.

## Mémoire par mode

Le module et le pilote (`$4000-$5FFF`) disparaissent dès que le mode
utilise la page HGR 2. `$0300-$07FF` reste le pilote de texte HGR (`$0300`
= sortie d'un caractère, codes de contrôle `< $1B` par la table `$044B`) et
sa police, copiés par l'amorce.

**Menu** : `$0803-$0DD5` scènes, `$6000-$62A5` menu, `$6300-$9BCA`
données. **Intro** : scènes, `$6000-$6199`, `$6300-$ACBA`. **Fin** :
scènes, `$6000-$61AC`, `$6200-$62FF` (début de `menu_data`),
`$6300-$ACBA`.

**Robotropolis, niveau 1** (`$45EF`, `$4602`, `$4615`) :

| Zone | Contenu |
|---|---|
| `$0803-$1907` | code du niveau |
| `$1AB0-$1FFB` | `$072` |
| `$6000-$81FF` | monde du niveau 1 ; les niveaux 2-5 ne remplacent que `$6E40-$81FF` |
| `$8200-$8ED4` | `$075` |
| `$8EF0-$93F4` | données du niveau (niveaux 2-5 : jusqu'à `$94EA`) |
| `$9500-$B8D6` | moteur commun |
| `$B8E0-$BF98` | `$07C` |
| LC2 `$D000-$DFFD`, `$F000-$FFF3` | `$080`, `$088` |
| LC1 `$D000-$EFFF` | 8 puces de 1 Ko ; niveau 1 : puce 0 = `$071`, puce 1 = `$06D`, 2-7 vides (masque `$3F`) |
| `$F008-$F047` | brochage des 8 puces (8 octets chacune) ; `$F008-$F017` ← `$464A` (`01 01 02 02 02 02 02 02`, `02 01 02 01 01 02 01 02`) |

Niveau suivant (`$40B6`, `$40C2`, `$40CE`, `$40DA`) : monde `$6E40`, code
`$0803`, données `$8EF0` seulement ; puces, moteur et le reste demeurent.
Mesuré pour les niveaux 2-5 et la fin (`$40E6`).

**Innovation Lab** (`$4630`) : `$0803-$0AFD` code, `$0B00-$1F9A`,
`$6000-$94FF`, moteur, `$B8E0-$BF80`, LC2 `$D000-$DFF9` et
`$F000-$FFF7`, 8 puces vides (masque `$FF`).

**Chip Design** (`$46A6`, `$46C8`) : comme le labo avec son propre code
`$0803-$0AF5`, `$6000-$94FF` (`$0E3`) et `$0B00-$12FF` (`$100`) par-dessus ;
puce 0 = `$0A6`, puce 2 = `$06D` (descripteur `$5051` porté à `$D800`),
masque `$5F` ; brochages `$F008` ← `$465A` (une seule sortie, broche 1),
`$F018` ← `$4652` (`02 01 02 01 01 02 01 02`, comme la puce 1 du niveau 1).

**Preview** (`$45D5`) : `$0803-$13B0`, `$14C0-$1FB5`, `$6000-$7FF7`,
`$7F80-$8797` (chargé après, recouvre), `$8880-$8CBF`, `$9000-$9394`,
moteur, LC2 `$D000-$DF64`, `$E000-$E0CD`, `$E470-$F03F`.

**Didacticiels** (`$4590` puis `$4662-$46A5`) : moteur,
`$14C0-$1FDB`, `$B900-$BE71`, LC2 `$D000-$DFF1`, `$F000-$FC75`, puis le
code en `$0803`, éventuellement `$14C0-$1B38` remplacé, et les données en
`$6000` (fin `$8EF8` à `$93D7` selon le didacticiel).

## Sauvegardes

Rien n'est jamais écrit sur les disques programme. Parties et puces vont
sur une **disquette STORAGE** que le jeu crée lui-même.

### Création d'une STORAGE

`$4CF9` : charger le formateur (`$4D46` : blocs `$06E-$070` en
`$5A00` depuis la face A ou B), puis `Insert Robot Odyssey STORAGE disk and
press RETURN OR to Create a New STORAGE disk insert a BLANK disk and press
C`. Avec `C` : lecture silencieuse du bloc 0 pour éviter d'effacer un disque
programme quand une autre unité existe (`$4DD8`), `WARNING: The next step
will erase your disk!`, RETURN, formatage (commande 3 → `$5A00`, routine
autonome d'écriture de pistes, **(?)** pour le détail), puis `$4EAF` remplit
`$5A00-$5FFF` d'`$A0`, y copie le secteur d'amorçage `$4F1C-$4FCA`
(signature `$11/$B4` et message `ROBOT ODYSSEY STORAGE DISKS / INSERT ROBOT
ODYSSEY PROGRAM DISK AND PRESS RETURN`) et écrit les blocs 0-2.

Le formatage n'a pas abouti dans a2shot sur une image `.dsk` vierge
(`Disk error--check drive`) ; les essais suivants utilisent une image
`.po` préparée avec ces trois blocs (`build/ldr/storage.po`).

### Disposition (Disk II, 280 blocs)

| Blocs | Contenu |
|---|---|
| `$000-$002` | amorçage STORAGE, `$A0` |
| `$003-$006` | inutilisés |
| `$007` | répertoire des parties |
| `$008` | répertoire des puces |
| `$009-$02F` | puces A-M (3 blocs chacune) |
| `$030-$10B` | parties A-D (`$37` = 55 blocs chacune) |
| `$10C-$117` | inutilisés |

Sur une unité SmartPort : parties A-Z en `$30+$37·n` (jusqu'à `$5BD`),
puces A-M au même endroit, N-Z en `$5C6+3·n` (jusqu'à `$613`).

**Répertoire** (bloc 7 ou 8, lu en `$5A00`) : 26 entrées de 15 caractères
ASCII bit 7 levé, complétées par `$A0`, 13 par page aux décalages
`$4FCB` = `$00, $12, … $D8` (pas de 18 octets) ; page `$5A` pour A-M, `$5B`
pour N-Z. Une entrée est occupée si l'un de ses octets est ≥ `$A1`. La
saisie du nom (`$4813`) écrit directement dans le tampon ; le répertoire est
réécrit avec la sauvegarde. Disk II : 4 parties (A-D, `$47E6`) et 13 puces
(A-M, `$47F1`) ; SmartPort : 26 de chaque.

### Partie (état 4, `$4108` ; chargement `$445E`)

Slot n (0 = A), base `b = $30 + $37·n` (`$4740`) :

| Blocs | Mémoire |
|---|---|
| `b … b+$0F` | LC1 `$D000-$EFFF` (les 8 puces) |
| `b+$10 … b+$2A` | `$6000-$94FF` (monde, objets, données du niveau) |
| `b+$2B … b+$35` | `$0B00-$1FFF` |
| `b+$36` | en-tête (`$5C00`) |

En-tête :

| Octets | Source / destination |
|---|---|
| `+$00-$3F` | `$F008-$F047`, brochage des 8 puces |
| `+$40-$41` | `$9C26-$9C27` : objet tenu, `$FF` = rien (`$9C26` racine de la chaîne de porteurs, celle qui bouge ; `$9C27` objet touché, `$A5E1`) |
| `+$42-$43` | `$A5C9-$A5CA` : décalage X/Y de la prise par rapport au joueur (`$A611`) |
| `+$44` | `$02D2` : niveau 0-4 ou 5 = labo |
| reste | contenu résiduel du tampon |

Écriture mesurée (slot A, « MYGAME ») : `cmd2` bloc `$007` ← `$5A00`,
`$066` ← `$5C00`, `$030-$03F` ← `$D000`, `$040-$05A` ← `$6000`,
`$05B-$065` ← `$0B00` ; en-tête `+$40` = `FF FF 00 00 00`.

Chargement (mesuré sur une STORAGE reconstruite à partir de la RAM de cette
sauvegarde) : bloc 7, choix de la lettre, en-tête `$066` ; refus `Not a
saved game/lab` si `+$44` ne correspond pas (5 seulement depuis le labo,
0-4 seulement depuis Robotropolis) ; puis `$0B00`, `$6000`, LC1 ; demande
du disque programme ; moteur `$05B`, `$07C`, `$080`, `$088` (A) ou `$0B2`,
`$0B6`, `$0BE` (B, labo) ; recopie de l'en-tête ; `$9C4E = $02CE` ; code du
niveau `+$44` par `$438F/$4395` (`$0A1`, `$0B7`, `$0CB`, `$0E2`, `$0F8`,
labo `$0E1`) ; `JMP $0803`. Le jeu reprend dans la salle sauvegardée. Le
moteur et `$0803-$0AFF` ne sont pas sauvegardés : ils sont rechargés.

### Puces

Puce k (0-7) en mémoire : 1 Ko en LC1 `$D000+$400·k`, brochage
`$F008+8·k` (un octet par broche : `01` entrée, `02` sortie, `00` absente),
au labo seulement un mot `$7A98,k`/`$7AA0,k` **(?)** et un texte de `$12B`
octets en `$8045+$12B·k` (tables de pointeurs `$4FFF`/`$5007`).

Emplacement n sur disque : `9+3n`, `10+3n` = les 1 Ko ; `11+3n` = en-tête
(`$477A`) :

| Octets | Contenu |
|---|---|
| `+$00-$07` | brochage |
| `+$08-$09` | mot `$7A98,k`/`$7AA0,k` **(?)** |
| `+$0A-$134` | texte : nom (15 car.) puis 8 lignes « broche / description » |

Sauvegarde (état 6, `$419C`, labo) : `cmd2` bloc 8, 2 blocs depuis LC1, en-tête.
Chargement (état 5, `$4260`) : `Insert Robot Odyssey or STORAGE disk with
saved chips and press RETURN OR To load a chip from the Library, press L`
(texte tel quel). `L` exige la face B : son bloc 8 est le **répertoire de la
bibliothèque** et ses blocs `$009-$026` dix puces dans le même format.
Hors du labo (`$02D2 ≠ 5`), seuls le Ko et le brochage sont copiés.

Bibliothèque (face B) :

| | Puce | Blocs |
|---|---|---|
| A | Clock Chip | `$009-$00B` |
| B | 4 Bit Counter | `$00C-$00E` |
| C | Bus Chip | `$00F-$011` |
| D | Delay Line Chip | `$012-$014` |
| E | Full Adder | `$015-$017` |
| F | One Shot Chip | `$018-$01A` |
| G | RS Flip-Flop | `$01B-$01D` |
| H | Count to N Chip | `$01E-$020` |
| I | Wall Hugger | `$021-$023` |
| J | Stereo Recorder | `$024-$026` |

Mesuré au labo (`regs:00:00:02 go:0A03`, `L`, `A`) : bloc 0, bloc 8 →
`$5A00`, `$009-$00A` → `$D800`, `$00B` → `$5C00`, `LOADED`, demande de
PROGRAM-B, retour au labo.

## Protection (piste 7)

L'analyse dit « pas de protection anti-copie » : c'est inexact.
`$6205` (segment `menu`, appelé à chaque affichage du menu) déplace la tête
sur la piste 7, attend le champ d'adresse du secteur 7, cherche `D5` puis
`E7 E7 E7`, relit le registre de données en cours de flot (`LDA $C08D,X`),
puis attend `EE` et les 8 nibbles `E7 FC EE E7 FC EE EE FC` (table `$629E`
lue à l'envers). C = 1 si trouvé ; `ROR $02CE`. Ces nibbles sont entre les
secteurs : `flux2dsk.py` décode bien les 560 secteurs, mais une image
`.dsk`/`.po` ne les contient plus.

Mesuré : `$02CE` = `$80` avec `A_ROBOTROPOLIS.woz`, `$00` avec
`build/A_ROBOTROPOLIS.dsk` ; `$9C4E` suit en jeu. Aucun accès absolu à
`$9C4E` hors du module : l'effet d'un échec n'est pas identifié **(?)**.
Après une sauvegarde ou un chargement de puce, `$436F` force le bit 7.

## Carte du module

| Adresse | Rôle |
|---|---|
| `$4000`, `$4003` | entrées (amorçage, choix du menu) |
| `$4006-$404C` | signature, somme de contrôle, répartiteur |
| `$4059` | états 0/1 : menu |
| `$4096` | état 2 : niveau suivant (table `$40AB`/`$40B0`, `$02D1` = 1-5) |
| `$40B6-$40FF` | listes niveaux 2-5 et fin |
| `$4108`, `$419C`, `$4260` | états 4, 6, 5 |
| `$422D`, `$4247`, `$435B` | `NOT SAVED`, `SAVED`, `LOADED` |
| `$436F` | retour au jeu après un service |
| `$43CE` | écran « To go to the… / To load an old saved… » |
| `$445E` | chargement d'une partie |
| `$44DA` | saut indirect avec LC2 en RAM |
| `$4563` | lancement d'un mode |
| `$45D5-$46E8` | listes de chargement par mode |
| `$46E9` | copie à paramètres en ligne (source, destination, longueur) |
| `$4705-$4734` | copies ; `$4735` octet en ligne suivant |
| `$4740`, `$477A`, `$47AE` | blocs d'une partie, d'une puce ; pointeur de brochage |
| `$47BB`, `$47CE` | touche (C = ESC), attente de RETURN |
| `$47E6`, `$47F1` | choix d'une lettre (parties, puces) |
| `$4813` | saisie d'un nom (15 car., ← et DEL effacent) |
| `$48F2` | efface HGR1, affiche HGR1 |
| `$4913-$4920` | affichage de texte en ligne (fin = octet à bit 7 levé) |
| `$4955-$4ABB` | textes, répertoires (`$4A42`) |
| `$4ABC` | `Replace old (X) (Y/N)?` |
| `$4B03` | chargeur |
| `$4C14` | erreur de protection en écriture |
| `$4C6C-$4D45` | face voulue, vérification, messages `Insert…` |
| `$4D46-$4EDD` | formateur, création de STORAGE |
| `$4EDE` | puces vides |
| `$4F10-$4FE4` | modèle de puce, amorçage STORAGE, décalages des noms |
| `$4FE5-$51AF` | descripteurs |

Pilote : `$5200` unité, `$52C8` bloc Disk II, `$5422` recherche de piste,
`$5698` champ d'adresse, `$5F00` sondage, `$5FBB` chargement du module.
Après le saut en `$4000`, `$5A00-$5FFF` ne sert plus que de tampon
(répertoire, en-tête, dernier bloc partiel, formateur).

## Reproduire

```sh
A=../dev/tools/a2shot/a2shot
# entrée n du menu (n ESPACE depuis Robotropolis), changement de face
$A --disk original/A_ROBOTROPOLIS.woz wait:2500 key:" " wait:40 \
   watch:52C8:0042:6 watch:4003 key:"\r" wait:300 \
   insert:original/B_LABS.woz key:"\r" wait:3000 shot:lab.png
# niveau Y+1 depuis la première salle
$A --disk original/A_ROBOTROPOLIS.woz wait:2500 key:"\r" wait:300 key:"\r" \
   wait:900 key:"\r" wait:3000 watch:52C8:0042:6 regs:00:00:01 go:0AA0 \
   wait:3000 shot:niveau2.png
# sauvegarde : ESC, S, STORAGE, lettre, nom
... key:"\e" wait:100 key:"S" wait:1500 insert:build/ldr/storage.po \
   key:"\r" wait:300 key:"A" wait:100 key:"M" ... key:"\r" wait:600
```

Les touches d'un nom se tapent une par une (`key:"M" wait:20 …`) ; plusieurs
caractères dans un seul `key:` se perdent. a2shot supprime sa copie privée
du disque à la sortie : pour relire une sauvegarde, on reconstruit l'image
STORAGE à partir de la RAM (`peek`, puis `peek:C088:1` deux fois pour lire
la banque 1).
