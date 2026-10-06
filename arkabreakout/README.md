# ARKABREAKOUT

Casse-briques original inspiré des mécaniques d'Arkanoid, pour **Apple II+ 48 Ko**,
6502 NMOS à environ 1 MHz, HGR plein écran 280 × 192 et DOS 3.3.
Aucune carte langage ou mémoire auxiliaire n'est nécessaire.

![Titre ARKABREAKOUT](screenshots/title.png)

![Terrain de jeu dans le cœur de POM2](screenshots/game.png)

[Voir les briques résistantes et les blocs de métal au secteur 09](screenshots/sector-09.png)

```sh
make -C arkabreakout        # dist/ARKABREAKOUT.dsk, amorçable
make -C arkabreakout run    # POM2, profil ii+
make -C arkabreakout test   # tests sur Apple II+ 48 Ko émulé
```

Au titre, **espace** démarre au clavier ; **J** démarre au paddle.
**C** calibre le paddle : aller à gauche, appuyer sur une touche, puis aller à
droite et appuyer sur une touche. Échap annule ; une plage invalide revient au
réglage par défaut. La calibration est conservée lors des nouvelles parties,
jusqu'à la sortie du programme.

| Commande | Action |
|---|---|
| A / flèche gauche | Déplacement continu à gauche |
| D / flèche droite | Déplacement continu à droite |
| S | Arrêter la raquette |
| + / - pendant le jeu | Régler la vitesse au clavier, de 1 à 8 pixels par mise à jour |
| Espace / bouton 0 du paddle | Lancer la balle |
| P | Pause / reprise |
| Échap | Retour à DOS |
| Ctrl-RESET | Retour à DOS avec restauration de la page zéro |

Le clavier II+ envoie des touches et ne signale pas leur relâchement : le
mouvement continue jusqu'à S ou jusqu'à une commande dans l'autre direction.
En pause, la simulation et les pages graphiques restent fixes.

La campagne contient **12 tableaux**, trois vies, et un score sur cinq chiffres.
Les briques colorées demandent un impact, les blanches plusieurs. Les encoches
des briques blanches indiquent les impacts restants ; les briques hachurées de
métal sont indestructibles. Les briques ont un bord supérieur lumineux. Chaque impact sur une brique destructible
rapporte 10 points. Le point d'impact sur la raquette détermine la direction et
l'inclinaison du rebond ; les bords donnent les trajectoires les plus obliques.
Les huit zones de la raquette donnent des trajectoires symétriques, de presque
verticales au centre à environ 68° par rapport à la verticale aux extrémités.
Les zones s'adaptent à la raquette élargie. Les deux composantes de vitesse
varient ensemble pour garder une vitesse de déplacement comparable.
La vitesse augmente avec la progression et toutes les douze briques détruites,
avec un plafond de cinq petits pas par mise à jour.

Une vie supplémentaire est accordée tous les **1 000 points**, avec un maximum
de cinq vies en réserve. Le **record de session** apparaît au titre et à la fin
de partie ; il est conservé lors des reprises et disparaît en quittant le jeu.

Toutes les cinq briques détruites, une capsule tombe si aucune autre n'est déjà
présente. Les lettres blanches permettent de reconnaître les trois bonus :

| Capsule | Effet |
|---|---|
| W | Raquette élargie de 28 à 42 pixels |
| S | Vitesse ramenée à deux pas par mise à jour, puis progression habituelle |
| C | Raquette collante : la balle est retenue au prochain contact ; espace ou bouton la relance |

Une nouvelle capsule remplace le mode de raquette précédent. Les changements
de largeur conservent le centre de la raquette, dans les limites du terrain. Une perte de vie
ou un changement de tableau réinitialise les bonus et la vitesse de départ.
La capsule rapporte aussi 10 points. Le bandeau inférieur indique le bonus
actif, **READY** pour une balle prête à partir et **PAUSE** pendant la pause.
Les indications de déplacement et de lancement s'adaptent au clavier ou au paddle.

## Moteur

Assembleur ca65/ld65 et bibliothèques communes `dev/lib/apple2` et `dev/lib/hgr`.
Le programme est chargé à `$6000` ; le binaire mesure environ 8 Ko, largement sous la limite de 13,5 Ko.
Les deux pages HGR sont réservées à `$2000–$5FFF`, et la grille, ses listes de
modifications et la table du paddle occupent 544 octets dans `$1000–$1FFF`.
DOS et le programme BASIC d'accueil sont conservés.

Le terrain utilise 12 × 8 cellules de 21 × 12 pixels, avec une surface de brique
visible de 18 × 8 pixels et des espaces entre briques. Les positions de la balle
comportent une fraction sur huit bits pour chacun des deux axes ; chaque petit
pas déplace au plus un pixel par axe. Les collisions testent les quatre coins et résolvent les deux
axes séparément. Le moteur reste indépendant des couleurs affichées.

Chaque page conserve les positions des objets qu'elle affiche. Sur la page
cachée, le moteur efface d'abord les anciens sprites par XOR, applique les
briques modifiées, puis dessine les nouveaux sprites. Les capsules utilisent des
glyphes blancs précalculés pour les sept alignements HGR. Le texte à taille
normale reste blanc. Le bandeau n'est redessiné que lorsqu'il change. Le titre ×2 est précalculé à
partir de la police partagée ; `make -C arkabreakout assets` le régénère.

Le II+ n'offre pas de signal VBL lisible : une temporisation CPU s'ajoute au
travail de simulation et de dessin. Les tests mesurent **environ 32 mises à jour
par seconde au clavier, balle au repos**, et environ **29 mises à jour/s en
jeu au clavier comme au paddle**, sur le CPU émulé à 1 MHz. Une attente plus
courte au paddle compense le coût de la lecture de ses temporisateurs. La cadence
varie avec les collisions, les sons et les mises à jour du bandeau ;
il n'y a pas de garantie de bascule synchronisée avec le balayage vidéo.

## Validation

`make test-arkabreakout` à la racine lance les tests dans `a2run` : démarrage,
commandes, pause et cohérence des deux pages, rebonds, vitesse maximale,
briques résistantes et métal, vies, les trois capsules, chargement de chaque
tableau, défaite/reprise, victoire, paddle et calibration, Échap et RESET.
Les tests couvrent aussi les huit zones de rebond sur les deux largeurs de
raquette, les contacts diagonaux, les vies bonus et le record de session.
Les cas difficiles sont préparés en mémoire pendant la pause, puis exécutés par
le véritable binaire 6502. Le disque d'origine n'est jamais modifié.

Les glyphes des capsules sont aussi vérifiés sur les sept alignements : leur
effacement doit restituer exactement les briques colorées des deux pages.
Le démarrage, le rendu et le retour à DOS ont également été contrôlés avec
`a2shot`, qui utilise le cœur de POM2 ; les captures sont dans `screenshots/`.

`make -C arkabreakout test-campaign` pilote une campagne entière sur la machine
48 Ko émulée. Il déplace uniquement la raquette et appuie sur espace pour
lancer ; il ne modifie ni la balle, ni les briques, ni les vies ou le score.
Les 12 tableaux ont été terminés et la victoire atteinte après 66 344 mises à
jour, soit environ 41 minutes de temps Apple II émulé. Ce test est également
inclus dans `make test-arkabreakout` et `make test`.

Ce pilotage automatique ne remplace pas des parties manuelles : équilibrage,
confort des commandes et validation sur un vrai Apple II+ figurent dans
[TODO.md](TODO.md).

Code et niveaux originaux : GPL-3.0, comme le dépôt. Police Beautiful Boot :
Michael Pohoreski. Aucun graphisme, niveau ou son du jeu d'arcade n'est repris.
