# LIGHT3DBALL

Prototype original inspiré de The Light Corridor, pour Apple II+ 48 Ko,
DOS 3.3 et HGR double tampon. Cinq longs niveaux, des murs latéraux larges,
des portes coulissantes et une case cible sur le mur du fond de chaque parcours.

    make -C light3dball
    make -C light3dball run
    make -C light3dball test

La disquette amorçable est `dist/LIGHT3DBALL.dsk`. Le programme se lance
automatiquement. `make run` utilise POM2 ; une carte AppleMouse permet de
jouer à la souris. Le clavier fonctionne également sans carte.

| Commande | Action |
|---|---|
| Souris | Déplacer la raquette en X et Y |
| Clic | Lancer la balle au début ou après une vie perdue |
| Bouton maintenu après lancement | Avancer ; relâcher pour s'arrêter |
| I / J / K / L, ou flèches | Déplacer la raquette au clavier |
| Retour | Lancer la balle au clavier |
| Clic / Retour après une cible touchée | Passer au niveau suivant et servir |
| 1 à 5 | Sélectionner un niveau et le recommencer |
| Espace | Lancer, puis activer/désactiver l'avancée au clavier |
| P | Pause / reprise |
| M | Activer / couper les sons |
| R | Recommencer le niveau ; après la dernière victoire, revenir au niveau 1 |
| Échap / Q | Retour propre à DOS |

Une fois lancée, la balle ne peut pas être capturée. La raquette la renvoie
automatiquement lorsqu'elle la touche. Un raté coûte une vie ; la nouvelle
balle attend alors un lancement. Un impact près du centre conserve le
mouvement latéral ; les bords ajoutent une correction d'angle limitée.
La boîte de contact conserve sa taille au centre et s'élargit progressivement
sur chaque axe lorsque la raquette se rapproche des bords de l'écran. Cette
tolérance compense la perspective sans modifier la position de la balle.
Un clic ou Retour pendant le vol ne recapture pas la balle. Après un raté,
un bouton souris resté enfoncé ne lance pas la balle suivante : relâcher,
puis cliquer à nouveau. Les clics pendant la pause sont consommés.

Les trois tailles de balle passent de 3/5/7 à 4/6/8 pixels. La petite balle
lointaine conserve douze pixels blancs dans une silhouette arrondie.
Le message `CLOSE! INTERCEPT BALL` avertit d'un retour proche. Des sons courts
distinguent lancement, rebond sur la raquette, choc contre un mur, vie perdue
et victoire. Le compteur des vies est séparé du libellé et actualisé sur les
deux pages, jusqu'à zéro.

La jauge à droite du compteur représente la profondeur du parcours : entrée
à gauche, mur final à droite. Le trait au-dessus indique la position du
joueur ; celui au-dessous indique celle de la balle. Le déplacement du
repère inférieur permet de voir son retour, même lorsqu'elle est masquée
par un obstacle. Sans vie restante, ce repère disparaît.

Lorsqu'une ouverture bloque la raquette, `MOVE LEFT` ou `MOVE RIGHT` indique
le déplacement nécessaire. Un service utilise la position actuelle de la
raquette, y compris lorsqu'on déplace la souris et clique dans la même image.

Le joueur avance seulement si la balle est suffisamment devant lui et si
la raquette passe entièrement dans l'ouverture. Le déplacement est de deux
unités par mise à jour, soit deux fois la première vitesse révisée. Il faut
**frapper la case du mur du fond avec la balle** pour gagner. Un tir à côté
rebondit ; atteindre le fond avec la raquette ne termine pas le niveau.

## Les cinq niveaux

| Niveau | Longueur | Obstacles | Parcours |
|---|---:|---:|---|
| 1 — Les chicanes | 1 536 | 8 | Murs droits/gauches alternés, passages de 48 unités |
| 2 — Les doubles virages | 1 792 | 10 | Groupes de murs du même côté ; passages resserrés à 40 unités |
| 3 — Les portes mobiles | 2 048 | 12 | Trois portes de 48 unités, avec des phases différentes |
| 4 — Les passages décalés | 2 560 | 14 | Passages de 40 et 48 unités ; groupes rapprochés et grandes chambres |
| 5 — Le grand corridor | 3 072 | 18 | Passages de 36 à 44 unités et quatre portes décalées |

Chaque niveau commence par deux murs fixes opposés à 128 et 256 unités.
Les niveaux pairs inversent leur côté. Ces ouvertures ne permettent aucune
trajectoire droite entre le départ et la cible : il faut réorienter la balle.
Les murs occupent généralement 80 à 92 unités sur une section de 128.

La dernière chambre mesure 256 unités. La cible apparaît et devient active
uniquement lorsque le joueur entre dans cette chambre ; un impact lointain
contre le mur du fond rebondit. Il faut donc parcourir le niveau. Après une
victoire, cliquer ou appuyer sur Retour commence le suivant. Chaque niveau
dispose de quatre vies ; la vitesse de la balle reste identique.

Les placements, largeurs et phases sont définis dans `levels.json` ; ils
sont convertis en cinq grilles compactes de 24 cases lors de la construction.

## Moteur

Logique en C cc65, rendu critique en assembleur 6502 : spans natifs,
contours en fil de fer, sprites HGR masqués prédécalés et sauvegarde du fond
séparée pour chaque page. Les quatre arêtes fixes du couloir sont
prérastérisées à la construction sous forme d'octets clairsemés. Les anciens
contours sont effacés par des lignes noires rapides, puis les nouveaux sont
dessinés dans les fenêtres laissées par les ouvertures proches. Aucun
rectangle noir ne masque les obstacles. Seules les portions des arêtes fixes
touchées par l'effacement ou un changement de visibilité sont réparées.
Le module réutilisable est
[`hgr_wireframe.asm`](../dev/lib/hgr/hgr_wireframe.asm), avec son
[API documentée](../dev/lib/hgr/README.md#contours-en-fil-de-fer).
Le décor n'examine que les quatre plans d'obstacles les plus proches et
conserve au plus 32 traits par page. Les collisions utilisent la grille du
niveau entier, en temps constant : les murs éloignés continuent à arrêter
la balle. La position de caméra mise en cache est exacte et sur 16 bits, sans retour
du décor après 1 024 unités. Après un arrêt, les deux pages convergent vers
les mêmes contours : aucun panneau ne reste dessiné à une ancienne position.
Les arêtes fixes exploitent la symétrie verticale pour partager leurs données entre le haut et le bas de l'écran.

Les coordonnées de la balle dans le monde sont indépendantes du rendu.
X/Y utilisent quatre bits fractionnaires. Quatre sous-pas vérifient les
murs, les deux faces des obstacles et le plan de la raquette. Les contacts
incluent un rayon de deux unités et la correction de dépassement. Des
tables précalculent la perspective et les trois tailles de balle.
La projection et les collisions critiques évitent les divisions C. Les
contacts de raquette et de cible conservent la précision fractionnaire ; la
balle est masquée pixel par pixel aux bords des ouvertures.
Les déplacements X/Y et la correction d'angle utilisent désormais
`src/physics.s`, séparé du rendu. La jauge garde ses anciens repères par page,
efface seulement leurs traits noirs et évite de redessiner une position fixe.

| Mémoire | Usage |
|---|---|
| `$0050–$00FF` | Page zéro C et assembleur, restaurée à la sortie |
| `$1000–$118F` | Sauvegardes du fond sous les sprites |
| `$1190–$1FFF` | Sprites, perspective, décor compact, cinq niveaux et police (`LCBALL`) |
| `$2000–$5FFF` | Les deux pages HGR |
| `$6000–$91FF` | Programme et état |
| `$9200–$95FF` | Pile C, 1 Ko |
| `$9600–$BFFF` | DOS 3.3 |

Les tests tournent sur le véritable binaire 6502 dans a2run : collisions des
deux côtés des panneaux, rebonds centraux et latéraux symétriques, absence
de contacts répétés, vies, passage du joueur, pause sur les deux pages,
cible finale, parcours complet et retour à DOS. Le rendu est comparé pixel
par pixel : projection exacte, contours sans remplissage, occultation
partielle de la balle et absence de traces après déplacement des obstacles.
Un test vérifie aussi, sur plusieurs images des deux pages, la stabilité des
panneaux après un arrêt entre deux anciennes positions de cache.
La physique native est contrôlée sur 663 cas aux frontières X/Y, 655 contacts
avec la tolérance de perspective et les 425 décalages d'impact de −212 à +212 ; les repères de profondeur sont
comparés pixel par pixel sur les deux pages.
`test_levels.py` vérifie les portes sur leurs 32 phases, l'impossibilité
d'un tir direct par calcul exact, les transitions entre niveaux et le
redémarrage de la campagne. Son pilote termine les cinq niveaux sur le vrai
binaire 6502, en injectant seulement les résultats de souris : aucune
modification de balle, de vies ou de progression. Le dernier essai a parcouru
la campagne en environ 14 minutes simulées, sans perdre de vie ; cette mesure
décrit le pilote et ne prédit pas la durée d'une partie humaine.

Mesure à 1,02 MHz : environ 27 000 cycles pour une image sans modification
du décor, délai inclus.
Le déplacement natif X/Y prend 85 à 199 cycles par sous-pas dans les tests.
La première version atteignait 299 000 cycles lors d'un redessin. La cadence
reste variable, en particulier près d'un grand obstacle ; le délai de
repli Apple II+ ne constitue pas une horloge matérielle.

Licence GPL-3.0, comme le dépôt. Les graphismes et le parcours sont originaux.
Les primitives partagées et leurs notices sont dans `../dev/lib/hgr`.
