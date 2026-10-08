# LIGHT3DBALL

Prototype original inspiré de The Light Corridor, pour Apple II+ 48 Ko,
DOS 3.3 et HGR double tampon. Un court couloir, deux panneaux fixes,
une porte coulissante et une case cible sur le mur du fond.

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
| Espace | Lancer, puis activer/désactiver l'avancée au clavier |
| P | Pause / reprise |
| M | Activer / couper les sons |
| R | Recommencer le parcours |
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
| `$1190–$1FFF` | Sprites, perspective, décor clairsemé (`LCBALL`) |
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
La physique native est contrôlée sur 663 cas aux frontières X/Y, 655 contacts
avec la tolérance de perspective et les 425 décalages d'impact de −212 à +212 ; les repères de profondeur sont
comparés pixel par pixel sur les deux pages.

Mesure à 1,02 MHz : environ 26 000 cycles pour une image sans modification
du décor, contre 60 000 avec redessin dans la vue initiale, délai inclus.
Le déplacement natif X/Y prend 85 à 199 cycles par sous-pas dans les tests.
La première version atteignait 299 000 cycles lors d'un redessin. La cadence
reste variable, en particulier près d'un grand obstacle ; le délai de
repli Apple II+ ne constitue pas une horloge matérielle.

Licence GPL-3.0, comme le dépôt. Les graphismes et le parcours sont originaux.
Les primitives partagées et leurs notices sont dans `../dev/lib/hgr`.
