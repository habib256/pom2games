# DIRTBIKE

Moto-cross en vue de côté pour Apple II+ 48 Ko (HGR, disquette DOS 3.3),
inspiré de *Dirt Bike* de Brad Quick sur Macintosh et de la démo PHYSICS.
On roule contre la montre sur 30 circuits de 3 tours, du très simple au très
dur, et les sauts et saltos rapportent des points. Le jeu est en anglais. Il faut doser les gaz et pencher
la moto pour retomber sur ses roues : si le pilote touche le sol, c'est la
chute. Les meilleurs temps et scores restent sur la disquette.

    make             # ../dist/DIRTBIKE.dsk (hall of fame vide)
    make run         # dans POM2 (Apple II+)
    make test        # 30 parcours faisables, physique et points 6502 ==
                     # modèle, chargement exact, titre, démo, sauvegarde

## Commandes

| Manette | Souris | Clavier | Effet |
|---|---|---|---|
| X gauche / droite | gauche / droite | ← → ou J / L | se pencher en arrière / en avant |
| haut (plus ou moins) | vers le haut | A / ↑ plein gaz, Z / ↓ demi-gaz | gaz ; au clavier tant qu'on appuie : relâchés, ils retombent à zéro en ~1 s et la moto ralentit |
| bas, bouton 0 | vers le bas, bouton | ESPACE | frein |
| | | H | page d'aide (titre, menu) |
| | | R | recommencer le parcours |
| | | S | son coupé / remis |
| | | ESC | en course : le menu principal (depuis le menu des parcours : la page de titre) |
| | | Ctrl-RESET | la page de titre |

La position de la manette au démarrage sert de centre. La souris
AppleMouse (carte du //e, souris intégrée du //c ; `dev/lib/mouse`) remplace
alors la manette : sa position compte comme celle du manche (centre 70, 96
du pilote) et son bouton freine. Les interruptions qu'active la souris du
//c sont masquées pendant les accès disque (`RWTS_SEI`). `make test-mouse`
le vérifie avec les vraies ROM (cartes AppleWin et MAME, //c 16 et 32 Ko)
dans le cœur POM2. Au clavier,
l'inclinaison et le frein durent 6 images après chaque appui ;
l'auto-répétition du //e les prolonge tant que la touche reste enfoncée.

**Titre et démo** (`src/title.inc`, image `tools/title.py`). Le jeu s'ouvre
sur une page de titre (fichier `TITLE`, LZ4FH, 1,8 Ko), avec le crédit du
portage (« APPLE II PORT: VERHILLE ARNAUD », sur une bande noire en bas) et
« PRESS ANY KEY » qui clignote sous le sous-titre ; une touche ou le bouton
mène au menu, H à la page d'aide. La musique du titre joue une fois : à sa
fin (~13 s), une démo se lance : les
3 tours d'un des circuits 5, 19, 10, 26, 22, 30 (à tour de rôle, 35 à 45 s)
rejoués au bit près depuis la solution du solveur, rangée à la fin du
fichier de la piste et copiée au chargement dans `$1000-$1FFF`, puis les
deux pages du hall of fame, puis le titre.

**Menu.** Les 30 parcours sur deux colonnes : flèches (ou I J K L) ou
manette pour choisir, RETURN, ESPACE ou bouton 0 pour partir. Seuls les
parcours déjà terminés (ceux qui ont un temps au hall of fame, donc sauvés
sur la disquette) se choisissent, et le premier pas encore terminé ; les autres montrent
leur numéro et des tirets. Une partie enchaîne ensuite les parcours : après
l'arrivée (et les initiales d'un record), une touche lance le suivant ; ESC
revient au menu ; après le 30, une page de félicitations (et l'envolée du
record). Sous la liste : le record et le temps de
référence, celui trouvé par le solveur.

**Course.** Compte à rebours « 3, 2, 1, GO! » (on peut déjà doser les gaz).
Ses images durent autant qu'en course (une attente de ~2 images vidéo) :
plus courtes, elles changeaient de page presque à chaque image vidéo, et le
rendu « beam racing » de POM2, qui relit la mémoire en fin d'image, montrait
la page en cours de redessin (la moto clignotait ; voir
`dev/tools/a2shot/LETTRE_POM2_AFFICHAGE_MANETTE.md`).

**Menu principal** (ESC en course, `src/mainmenu.inc`) : page de titre,
aide, périphérique d'entrée (clavier, joystick ou souris, parmi ceux
détectés au démarrage), hall of fame, retour à BASIC. Flèches (I / K) et
RETURN, ou les chiffres 1 à 5 ; ESC : la page de titre. Son code et ses
textes sont un overlay du fichier `TITLE` : lié pour s'exécuter en `$9C00`
(`build/menu.bin`, rangé par `tools/titlefile.py`), il arrive avec `TITLE`
dans le tampon de chargement, sur le parcours chargé (rechargé avant chaque
course de toute façon). « QUIT TO BASIC » coupe la souris, laisse la marque
« QU » en `$8000` et redémarre la disquette : HELLO la voit, l'efface et
s'arrête (« DIRTBIKE: BYE! ») au lieu de relancer le jeu ; on retrouve
BASIC avec DOS 3.3.
Après une chute, la moto repart à l'arrêt, après « 1, GO! », au début de la
dernière portion de sol plat où elle a roulé sur ses deux roues (`note_safe` :
une seule hauteur de sol sous la moto, à une roue près de chaque côté ; le
début, pour avoir toute la ligne droite pour reprendre de l'élan). Chaque
tour en compte 6 à 22, jamais plus de ~820 pixels d'écart. Le chrono a
tourné pendant la chute, le tour et le score restent, seuls les points en attente sont perdus
(R recommence la course).

**Son.** Pas de bruit de moteur. Une petite musique en boucle sur la page
de titre, un jingle à l'arrivée, prolongé d'une envolée pour un record. Choc
à la réception d'un saut, bip pour des points, arpège pour un salto, deux
bruits sourds pour une chute, bips de tour et du compte à rebours (`tone`,
lib `apple2/sound.asm` : la note bloque le jeu le temps qu'elle dure). Muet
dans la démo ; S le coupe.

Les airs sont écrits en notes dans `tools/music.py` (3 octets par note :
durée en ticks de 1/60 s, demi-période, et le nombre d'alternances qui
remplit un tick). `music_tick` (`src/title.inc`) joue une tranche d'un tick
à la place de l'attente de `tick_wait` : la page de titre clignote et répond
aux touches pendant la musique. L'air du titre est placé en tête du fichier
`TITLE`, avant les pages de texte et l'image LZ4FH, et se joue depuis le
tampon de chargement : il ne coûte pas de RAM. `tick_wait` s'arrête dès qu'il
finit : la démo démarre à la dernière note. Les jingles restent dans le programme.

**Points** (`src/tricks.inc`, modèle `tools/tricks.py`). Un saut d'au moins
12 ticks (0,4 s) rapporte 10 points par tick en l'air ; chaque salto (un tour
complet, avant ou arrière, compté par secteurs de 45° de l'axe des roues)
rapporte 1000 points × le nombre de tours au carré (4000 le double, 9000 le
triple). Un wheeling (roue arrière au sol, roue avant en l'air) d'au moins
15 ticks rapporte 10 points par tick quand il s'arrête. Les points attendent
20 ticks sur les roues avant de s'ajouter au score (« JUMP +nnn »,
« FLIP +nnnn », « WHEELIE +nnn ») : une chute les fait perdre.

**Ligne d'arrivée.** Un drapeau (mât de 2 pixels et fanion, `draw_flag`)
marque la ligne, qui est aussi celle des tours. Il est marqué comme la moto
(`bk_top`/`bk_bot`) : le rendu du sol lui rend son ciel quand il défile.
Il est tracé point par point sur toute la largeur (x de 0 à 279, coupé au
bord droit) : à l'époque où il passait par `hgr_line8` (x sur 8 bits), il
n'existait qu'en deçà de 244 et clignotait à cette limite quand la caméra
oscillait d'un pixel. Le numéro du tour (1 à 3) est écrit sous son fanion.

**Bandeau.** En haut : le chrono à gauche, le score à droite et, au milieu,
les messages (figures, tours, compte à rebours, CRASH, FINISH, DEMO),
centrés sur 14 caractères. Le bandeau ne redessine que les caractères qui
changent, page par page : un message plus court efface ce qui reste du
précédent sur les deux pages.

**Circuits.** Chaque parcours est une boucle (longueur multiple de 7, au
plus 3760 pixels) : 400 pixels plats au départ, une ligne droite plate de
300 pixels avant la ligne, et la boucle reprend. Pour l'écran et la moto, le
tableau répète les 336 premiers pixels après la fin ; 128 pixels après la
ligne, la moto et la caméra reculent ensemble d'un tour (`phys_wrap`,
identique dans le modèle) : rien ne change pour la physique ni pour l'image.
« LAP 2 », « FINAL LAP » ; après la ligne du 3e tour, la moto freine jusqu'à
l'arrêt sur la ligne droite de départ. Les deux tableaux d'une piste (hauteur
et motif par pixel) remplissent déjà les 8 Ko rendus par DOS : des tours
plutôt qu'une piste deux fois plus longue.

**Hall of fame** (`src/hof.inc`). Pour chaque parcours, le meilleur temps et
le meilleur score, chacun avec trois initiales. Après un record, on tape ses
initiales (lettres, ou manette haut/bas et gauche/droite, RETURN ou bouton) ;
le jeu réécrit alors les deux secteurs du fichier `DIRTHOF` par RWTS. Sur une
disquette protégée, il le dit et continue. `make` recrée un hall of fame vide.

## Comment ça marche

**Physique** (`src/physics.inc`, modèle `tools/physics.py`). La moto est
faite de trois points de Verlet : roue arrière, roue avant et pilote, reliés
par l'empattement (rigide, 24 px) et deux liaisons roue-pilote (la
suspension). Le pilote pèse un peu plus qu'une roue (9/7 : dans une liaison,
la roue prend `c + c >> 3` de la correction, le pilote `c - c >> 3`, `c >> 3`
arrondi vers zéro : arrondi vers le bas, la moto arrêtée reculait toute
seule ; à 3 fois, la moto devenait intenable dans les whoops). À chaque tick :
1. gravité, puis vitesses bornées : 18 px/tick le long de la piste, 8 en
   vertical ; la traction pousse jusqu'à 13,5 px/tick ;
2. rotation de l'axe des roues : le frein arrière fait plonger l'avant
   (réaction de la roue sur le cadre), sauf roue avant au sol : le sol
   tient l'avant (frein tenu, la moto arrêtée basculait) ; en l'air, l'inclinaison
   et les gaz (nez qui monte) la tournent aussi. En l'air ou sur une seule
   roue, la rotation s'amortit (`>> 4` par tick : plus de vrille sans fin) ;
3. contraintes de distance sans racine carrée. L'inclinaison déplace le
   pilote le long de la moto (1 px par cran, tables de longueurs de repos
   par cran dans `physconst.inc`) : au sol, c'est son poids qui lève ou
   pose l'avant, plus de rotation directe (la moto ne roule plus debout) ;
4. contact des roues avec le sol, en suivant la normale tirée de la pente
   `h[x+2] - h[x-2]` : rebond, puis traction (roue arrière), frein, frein
   moteur sans gaz (roue arrière, `vt -= vt >> 7`) et résistance au
   roulement (`vt -= vt >> 7`) : sans gaz, la vitesse baisse de ~30 % en
   ~1,5 s et de moitié en ~3 s sur le plat ;
5. les contraintes encore une fois, après le sol : l'empattement reste
   entre ~18 et 27 px (il tombait à 1 px avant, la moto se repliait) ;
   suspension ferme (raideur 0,9 ; 1,2 puis 1,0 rendaient le jeu un peu
   trop facile) : les grandes réceptions bien prises passent ;
6. chute si le pilote approche du sol, si sa tête (dessinée à pilote +
   3 × (dy/8, −dx/8), l'axe des roues tourné vers le haut) passe sous le
   sol, si une liaison pilote-roue tombe
   sous la moitié de sa longueur (pilote écrasé) ou si la moto passe sur le
   dos (une roue au sol, l'avant derrière l'arrière : wheeling bouclé).

Le wheeling : gaz et pilote en arrière lèvent l'avant ; le relâcher, pencher
en avant ou freiner le reposent ; insister le fait boucler. Les carrés des
contraintes se lisent dans la table des quarts de carrés (x² = 4·⌊x²/4⌋ +
(x & 1)) au lieu d'une multiplication : la physique coûte ~14 400 cycles
par image.

Les positions sont en virgule fixe : x en 16.8 (pixels du monde), y en 8.8.
Les produits passent par `dev/lib/math` (quarts de carrés, 2 Ko construits au
démarrage en `$0800`, raccourcis pour les normales ×0 / ±1,0). L'asm reproduit
le modèle Python au bit près : `tests/test_physics.py` le vérifie, points
compris, sur un script de 545 ticks (chute et culbutes comprises) et sur les
3 tours complets des circuits 1, 19 (un salto, des wheelings) et 30 tirés de
`tests/solutions.txt`.

**Parcours** (`tools/tracks.py`). Les parcours 1 à 3 sont écrits à la
main ; les autres sont tirés d'un vocabulaire d'éléments (bosses, collines,
tremplins, trous, tables, marches, à-pics, whoops, escaliers) dont la taille
et la sévérité croissent avec le numéro, selon une graine fixée par
parcours. Chacun est prouvé faisable : `tools/solver.py` cherche un trajet
dans le modèle physique (recherche en faisceau sur l'inclinaison, plein ou
demi-gaz et le frein ; à défaut, un faisceau qui garde toutes les vitesses,
pour les crêtes qu'il faut aborder freiné ; chaque tick penché en arrière
lui coûte un peu, sinon le pilote des démos restait assis en arrière) et
`tests/solutions.txt` le garde ;
`make test` le rejoue (`tools/trackcheck.py`). Les trajets (3 tours) durent
de 27 s à 49 s. Une nouvelle graine doit aussi tenir dans les limites du rendu
(`POOL_MAX`, 256 motifs : `make` le vérifie).

**Format** (`tools/track.py`, `tools/packtrack.py`). Pour chaque pixel du
monde, le jeu garde la hauteur du sol et le numéro du « motif » de la
fenêtre des 7 pixels qui commence là, c'est-à-dire ce qu'affiche un octet
HGR quand la caméra place ce pixel au bord d'un octet. Un parcours a au plus
165 motifs, dont les octets partiels se partagent une réserve (783 octets
au plus). Chaque parcours est un fichier `T01`..`T30` : un en-tête et deux
flux LZ4FH (de 596 octets à 2,3 Ko, 56 Ko en tout).

**Chargement** (`src/loader.inc`). Une fois lancé, le jeu ne garde de DOS
que son pilote de disque RWTS (`$B700-$BFFF`). Le parcours choisi est lu
secteur par secteur dans la zone libérée, puis décompressé :
hauteurs en `$9600`, motifs en `$A600`. La position de la liste de secteurs
de chaque fichier est écrite dans le jeu après la construction du disque
(`tools/patchdir.py`). `tests/test_tracks.py` vérifie que la mémoire après
chargement correspond exactement à la compilation Python.

**Rendu** (`src/render.inc`). Double tampon HGR, défilement au pixel. Une
colonne d'écran se calcule en quelques lectures de table (motif, hauteur,
octets partiels), quel que soit le décalage de la caméra. Chaque page retient ce qu'elle affiche, et seules
les lignes qui changent sont réécrites. Les suites d'au moins 4 lignes de
ciel ou de sol passent par un écrivain déroulé (`STA ligne,Y` pour chaque
ligne, 5 cycles par ligne) généré au démarrage pour chaque page. Les accès
aux lignes lisent la table de la page dessinée, choisie en patchant les
opérandes ; il n'y a plus de table réécrite à chaque image. La moto est
tracée en OR avec un Bresenham maison et des sprites déroulés. Les lignes
qu'elle couvrait sont repeintes deux images plus tard ; celles qui étaient
dans le sol blanc n'ont rien à effacer. Le HUD ne réécrit que les caractères
qui changent.

**Temps.** Le chrono compte les ticks (30 par seconde), donc un temps ne
dépend pas de la vitesse d'affichage (25 à 30 images par seconde). Les
courses (3 tours) durent de 27 s à 49 s. Les messages sous le bandeau ne sont
écrits que sur les premières images, puis 2 images sur 8 (le rendu du sol ne
touche pas au ciel).

**Mémoire.** `$0200-$03CF` : tampon de saisie et page utilisateur, inutiles
ici (ni BASIC ni commande DOS) : `hgr_lo` / `hgr_hi`, calculées au démarrage
(`dev/lib/hgr/hgr_scanline_ram.asm` : 384 octets de moins dans le fichier).
`$0400-$07FF` : la page texte 1, jamais affichée (le jeu ne revient pas à
DOS) ; ses huit bandes de 120 octets (segments `TXT0`-`TXT7`) reçoivent des
tables du rendu, les tampons du HUD et deux routines (le menu, l'affichage
d'un parcours dans le menu : `TXTC5`, `TXTC7`, recopiées au démarrage) ; les
trous d'écran (`$x78-$x7F`, `$xF8-$xFF`, où RWTS, la souris et les cartes
gardent leur état) sont laissés tranquilles. `$0800-$0FFF` : tables de
multiplication (là où dormait le programme HELLO). `$1000-$1FFF` :
écrivains de lignes, tables du rendu et des motifs, entrées de la démo,
hall of fame. `$6000-$91FF` : le jeu (code, données, BSS ; ~250 octets
libres). `$9200-$95FF` : le code de démarrage (segment `INIT` : init, tables
du rendu, des lignes HGR et de multiplication, détection de la souris,
lecture du hall of fame) et les images des routines de la page texte, la
fin du fichier, exécutés une fois puis recouverts par la réserve de motifs
du parcours (`pool`) au premier chargement ; ~60 octets y restent.
Le fichier `TITLE` porte l'air du titre, les pages de texte (aide,
félicitations : `tools/pages.py`), le menu principal (en `$9C00`) et
l'image (`tools/titlefile.py`) : relu à la demande, il ne coûte pas de RAM.
Les variables du jeu (BSS) sont dans une bande de la page texte (`TXT6`).
`$9600-$B5FF` : le parcours (à la place de DOS ; le titre et le hall of fame
y passent aussi). `$B700-$BFFF` : RWTS. La page zéro du jeu (`$50-$FB`) est
presque pleine.

## Outils

| Fichier | Rôle |
|---|---|
| `tools/physics.py` | modèle de référence ; `python3 tools/physics.py` le fait rouler plein gaz |
| `tools/physconst.py` | génère `src/physconst.inc` (constantes et tables) depuis le modèle |
| `tools/tracks.py` | les 30 parcours : noms, éléments, graines |
| `tools/track.py` | compilation en motifs de 7 pixels ; `track1`, parcours du test physique |
| `tools/solver.py` | trouve un trajet par parcours (`--all tests/solutions.txt` après un changement de parcours ou de physique) |
| `tools/trackcheck.py` | rejoue les solutions, vérifie les limites du format |
| `tools/packtrack.py` | fichiers `T01`..`T30` (LZ4FH) et données du menu |
| `tools/patchdir.py` | écrit dans le jeu où sont les fichiers sur la disquette (parcours, titre, hall of fame) |
| `tools/tricks.py` | modèle des points (sauts, saltos), rejoué par le test physique |
| `tools/title.py` | l'image de titre (`OUT.hgr [aperçu.png]`) |
| `tools/hof.py` | le fichier `DIRTHOF` vide |
| `tools/music.py` | les airs : `src/music.inc` (jingles) et `build/tune.bin` (titre) |
| `tools/titlefile.py` | le fichier `TITLE` : air, pages, menu principal (`$9C00`), image |
| `tools/pages.py` | pages d'aide et de félicitations : `src/pages.inc` et `build/pages.bin` (dans `TITLE`) |
| `tests/test_mouse.py` | `make test-mouse` : la souris avec les vraies ROM, dans le cœur POM2 (`POM2_SRC`) |
| `tools/sprites.py` | génère `src/sprites.inc` : roue (4 positions de rayons × 7 décalages), tête |
| `tools/autopilot.py` | pilote automatique simple (réglé pour l'ancienne vitesse ; le test physique rejoue désormais les solutions) |
| `tools/profile.py` | profil a2shot : cycles par image et par routine |

Les bibliothèques de `dev/lib` utilisées sont `apple2` (HGR, clavier,
manette, LZ4FH, RWTS), `hgr` (tables, texte 8×8, lignes, pages), `math` et
`font` ; `fhpack` compresse les parcours et le titre.
