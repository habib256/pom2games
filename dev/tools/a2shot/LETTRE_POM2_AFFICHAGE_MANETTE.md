# Lettre à POM2 : deux corrections demandées (affichage des pages HGR, manette de l'hôte)

De : pom2games (jeu DIRTBIKE, Apple II+ 48 Ko, DOS 3.3)
Date : 21 octobre 2026

> **État :** transmise et corrigée dans POM2 (`28700c39` journal des écritures
> vidéo, `37f5316c` stick 1 → joystick Apple II). a2shot reconstruit avec ce
> core : le compte à rebours sans l'attente ne clignote plus.

Bonjour,

En testant DIRTBIKE dans POM2 (et dans `a2shot`, qui embarque `pom2_core`),
nous avons trouvé deux comportements qui diffèrent d'un vrai Apple II. Le jeu
contourne le premier, mais d'autres programmes en souffriront. Voici les
détails, de quoi les reproduire, et ce que nous proposons.

---

## 1. Le rendu « beam racing » montre une page déjà redessinée

### Symptôme

Un programme en double tampon HGR (dessin sur la page cachée, puis bascule
`$C054` / `$C055`) clignote dans POM2 : des images affichées montrent la page
en cours de redessin, avec la moto à moitié effacée. Sur un vrai Apple II,
ce programme ne clignote pas : chaque page est complète au moment où elle
devient visible.

### Cause probable

`Apple2Display` rejoue en fin d'image vidéo le journal des bascules de
l'image (`getDisplayStateAtFrameStart()` puis `forEachBeamSegment` dans
`Apple2Display_Beam.cpp`). Chaque bande est peinte avec la page qui était
affichée à ce moment-là, ce qui est juste, **mais avec le contenu de la
mémoire en fin d'image**.

Or, juste après une bascule (page A → page B), le programme commence à
redessiner la page A, devenue cachée. Le haut de l'écran, balayé avant la
bascule, montrait la page A. POM2 la peint pourtant avec la page A telle
qu'elle est à la fin de l'image : à moitié effacée. Sur la machine réelle,
le faisceau a lu la page A avant qu'on la modifie.

Le défaut apparaît dès qu'une bascule et des écritures dans la page
précédemment visible tombent dans la même image vidéo. C'est presque
systématique quand le programme bascule plus d'une fois par image
(17 030 cycles).

### Reproduction

- Disquette : `dist/DIRTBIKE.dsk` du dépôt pom2games, à la révision qui
  précède notre contournement (le compte à rebours ne contient pas encore
  `LDA #79 / JSR WAIT`).
- Pendant le compte à rebours « 3, 2, 1 », une image du jeu dure environ
  16 000 cycles : une bascule par image vidéo. La moto clignote fortement.
- Dans `a2shot` : à la ligne qui suit `LDA HISCR` dans la boucle principale,
  poser un bloc blanc dans la page 1 seulement, puis faire `shot`. Le bloc
  est visible alors que la page 2 vient d'être sélectionnée, et l'image
  montre la page 1 pendant qu'elle est redessinée.
- Nous avons mesuré 40 images consécutives (pixels de la moto) : sans le
  contournement, de 0 à 180 pixels au lieu de 744.

### Ce que nous proposons

Peindre chaque bande avec la mémoire telle qu'elle était quand le faisceau
l'a balayée. Plusieurs façons d'y arriver :

1. **Rendu progressif** : peindre les lignes au fil de l'exécution, au
   moment où le faisceau les atteint. C'est le plus exact.
2. **Instantané aux bascules** : à chaque événement `Page2` (ou de mode),
   copier les 8 Ko de la page qui cesse d'être affichée (ou seulement les
   lignes déjà balayées), et peindre les bandes d'avant l'événement depuis
   cette copie.
3. **Journal des écritures vidéo** : enregistrer les écritures dans
   `$2000-$5FFF` (et le texte) avec leur cycle, et les annuler à rebours
   pour les bandes balayées avant elles.

L'option 2 coûte peu : rien quand aucun programme ne bascule, une copie
de 8 Ko par bascule sinon.

### Contournement côté jeu (déjà fait)

DIRTBIKE allonge les images du compte à rebours jusqu'à environ deux images
vidéo, comme en course. Les bascules sont moins fréquentes et le
clignotement disparaît dans nos mesures. Le défaut reste possible en course
dès qu'une bascule tombe juste avant le haut de l'écran.

---

## 2. La manette de l'hôte : premier stick analogique → joystick Apple II

### Demande

Sans configuration, le premier stick analogique de la manette de l'hôte
(stick gauche) doit piloter le joystick analogique de l'Apple II :

- axe X → PDL(0) (`$C064`), axe Y → PDL(1) (`$C065`), sur toute la plage
  0..255, centre à 127 ou 128 ;
- boutons A et B (ou 1 et 2) → PB0 (`$C061`) et PB1 (`$C062`).

C'est le comportement que les jeux attendent : DIRTBIKE lit PDL(0) pour se
pencher, PDL(1) pour les gaz et le frein, et PB0 pour freiner.

### Ce qui a été observé

L'utilisateur constate que, par défaut, la manette est associée aux
**paddles** et non au joystick analogique. `JoystickInput.h` annonce bien
l'axe X sur PADL(0) et l'axe Y sur PADL(1), mais nous n'avons pas trouvé ce
qui produit le comportement observé. Nous n'avons rien modifié dans
`~/src/pom2`.

À vérifier de votre côté :

- quel mode est actif par défaut quand une manette est branchée
  (`autoBindIfUnconfigured()`, `PaddleInputs`) ;
- si un mode « paddles » (deux potentiomètres indépendants, ou le
  pilotage par la souris ou le clavier) prend le pas sur le joystick ;
- la plage et le centrage des axes : un joystick au repos doit lire
  environ 127 sur les deux axes.

### Ce que nous proposons

Faire du « joystick analogique » le mode par défaut dès qu'une manette est
détectée, avec la correspondance ci-dessus. Garder le mode « paddles »
accessible dans la configuration, comme choix explicite.

---

Merci ! Nous pouvons fournir la disquette, les scripts de mesure
(`a2test.Session`, captures et comptage de pixels) et retester toute
correction avec la batterie de tests de pom2games.
