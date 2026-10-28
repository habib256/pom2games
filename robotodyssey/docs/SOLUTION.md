# Robot Odyssey : comment gagner

*[← ANALYSE](ANALYSE.md)* · détail des énigmes : [niveau 2](logic/niveau2.md),
[niveau 3](logic/niveau3.md), [niveau 4](logic/niveau4.md),
[niveau 5](logic/niveau5.md)

Feuille de route tirée de l'analyse du code Apple II (*Robotropolis*, face
A). Chaque mécanisme a été vérifié dans l'émulateur, mais personne n'a
encore joué les cinq niveaux d'affilée au clavier. Positions en unités du
jeu : X de 0 à 133 (2 pixels par unité), Y de 0 à 176 compté depuis le bas.

Lancer depuis le `.woz` (protection de la piste 7) : menu **Robotropolis**,
RETURN, RETURN.

## À savoir avant de partir

- `I` `M` `J` `K` : se déplacer ; avec Ctrl, pas fin d'une unité,
  indispensable pour se poser **exactement** sur les repères de sortie.
  ESPACE : prendre ou poser. `R` : arrêter ou relancer tous les robots.
  `S` / `C` : prendre ou reposer le fer à souder (toucher une broche puis
  une autre pour câbler). `T` : boîte à outils. ESC : menu.
- **Prendre un robot : l'aborder par en dessous.** Le toucher d'un autre
  côté fait entrer dedans.
- **Seul ce que l'on tient passe au niveau suivant** ; tout le reste est
  perdu, robots compris. Pour emporter plusieurs robots, on les
  **emboîte** : porter un robot dans l'intérieur d'un autre, l'y poser,
  ressortir, prendre le robot extérieur.
- À garder jusqu'au bout : la **clé** (niveaux 1, 2, 4 et 5) et, si
  possible, l'**aimant** du niveau 1.

## Niveau 1 : les égouts

1. Dans la salle des trois robots, trouver la **clé** : elle est dans
   l'intérieur de Sparky, de Checkers ou de Scanner, au hasard (« The key
   to success lies within »).
2. La clé posée sur les dalles ouvre des portes de murs : salle « The City
   Sewer » en (17,17), salle « Congratulations! » en (87,81).
3. Éviter l'Ampire Bot, qui vide les batteries des robots (« Black crystals
   foil Ampire Bots »).
4. Avant de sortir : emboîter les robots (clé et aimant dans un
   intérieur), prendre le robot extérieur, se placer exactement en (32,32)
   dans la salle « Prepare for an experience… ».

## Niveau 2 : le métro

1. Clé sur la plaque → porte du **jeton** ; un robot prend le jeton (les
   gardes refoulent le joueur à pied).
2. Jeton sur la fente du tourniquet, passer pendant qu'il tourne. Il faut
   le reprendre pour chaque trajet.
3. Dépôt : tenir la poignée tirée à fond pendant qu'un robot appuie sur le
   bouton ; le train attend, monter.
4. Descendre à la station Laundrobot ; un robot seul prend le **ticket**.
5. Ticket sur la fente de la sortie, monter l'escalator, se placer
   exactement en (123,154).

## Niveau 3 : la ville

1. Mettre le **bouclier** dans un robot, l'alimenter par un fil chaud : il
   protège de l'orage. Ce robot va chercher le **jeton**, qui fuit le
   joueur.
2. Poser la ferraille sur sa silhouette : l'ascenseur s'ouvre.
3. Distributeur : un robot insère le jeton, un autre tient la tirette, on
   récupère le **Form-12**.
4. Poser le Form-12 sur le trajet de la sentinelle ; **tenir le bouclier en
   main** quand elle le détruit, sinon elle le confisque.
5. Un robot seul franchit le laser et touche sa cible ; se placer alors
   exactement sur le joueur fantôme en (35,80).

## Niveau 4 : le centre de calcul

1. Appuyer sur les 4 boutons, un par quart de la grande salle : conduits
   (robot seul), champ de mines invisible (un robot qui pousse plus de 7
   tours contre un mur explose), champs de force colorés et deux serrures
   (la clé passe de Checkers à Scanner), étincelle à faire toucher par un
   objet. L'ordinateur s'éteint et le 4ᵉ robot est libéré.
2. **Raccourci** : l'aimant gardé depuis le niveau 1, posé dans l'ascenseur,
   tient la porte ouverte (HOLD) sans éteindre l'ordinateur.
3. Sortie : exactement en (123,155) dans la cabine, en tenant les robots
   emboîtés.

## Niveau 5 : les voies aériennes

1. Clé sur sa dalle ; traverser le trafic ; passer la salle du véhicule
   **dans un robot**.
2. Disk-O-Tek : prendre le **disque**, qui ouvre les planchers où on le
   pose.
3. Faire émettre le motif radio 100110100110 par une antenne : la serrure
   sonore s'ouvre.
4. Le joueur sur STARTER, un robot presse les boutons 1, 3, 2, 4.
5. La grille bleue vide les batteries : un robot suit les flèches et coupe
   la grille ; 189 tours pour passer.
6. Transporteur : un robot dans chaque compartiment, le joueur sur STARTER,
   boutons 1 à 8 en alternant, « Press last », puis exactement en (70,20) :
   écran « CONGRATULATIONS! ».
