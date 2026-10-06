# MICRO-SOKOBAN — TODO

État au 2026-10-06 : **aucune tâche ouverte**. Les fonctionnalités et corrections
ci-dessous sont réalisées. Les commandes et les détails techniques sont dans
le [README](README.md), les sources et solutions dans [levels/README.md](levels/README.md).

## Contraintes et limites connues

- Apple II+ 48 Ko, HGR, DOS 3.3 ; clavier et manette.
- Pas de défilement : chaque niveau tient dans 20 × 12 cases, hors des coins du HUD.
  Les niveaux trop hauts sont tournés si cela permet de les afficher ; les autres
  sont écartés. Leur numéro d’origine est conservé.
- L’alerte DEADLOCK détecte les cases mortes calculées depuis les cibles,
  y compris les coins et les bords de mur sans cible. Les blocages entre caisses
  (gel 2 × 2, par exemple) restent hors de cette détection ; le solveur les détecte.
- Undo/Redo garde les 1024 derniers coups en mémoire seulement. L’historique
  repart vide après redémarrage, changement de profil ou tutoriel rejoué en
  cours de partie (position et compteurs sont rendus). Si le début du niveau
  a été oublié, RESTART recharge le niveau au lieu de le rembobiner.
- Un fichier de records dont un secteur est illisible est abandonné en entier
  (profil vide, réécrit à la sauvegarde suivante) : les records des secteurs
  encore lisibles ne sont pas récupérés.
- À nombre égal de niveaux résolus, le classement compare le total des meilleurs
  coups ; le résultat dépend donc des niveaux choisis.

## Réalisé

- [x] **Affichage** : murs bleus, joueur blanc et repère sous les pieds sur cible ;
  caisses hors cible remplies en orange, caisses sur cible à cadre vert creux et
  coche blanche. Les sept tuiles restent distinctes en monochrome. COLOR MODE
  (OPTIONS, éteint par défaut) rend aux caisses placées leur corps vert plein.
- [x] **Lisibilité** : petit texte blanc, couleur réservée aux titres ×2 ; HUD
  avec coups, poussées, collection/numéro d’origine et meilleur résultat.
- [x] **Rendu HGR** : écrans complets dessinés sur la page cachée puis affichés ;
  seules les tuiles modifiées sont redessinées pendant les déplacements.
- [x] **Gameplay** : Undo/Redo au clavier et à la manette, répétition du manche,
  RESTART annulable avec Redo, compteurs de coups et poussées sur 16 bits
  (arrêtés à 65535),
  compteur de caisses restantes et alerte sonore DEADLOCK désactivable.
- [x] **Niveaux** : 454 niveaux Microban I à IV (150, 122, 92 et 90), conversion
  XSB avec rotation/filtrage, treize paquets de 2 Ko au plus, choix par grille,
  repérage des niveaux résolus et bilan en fin de collection.
- [x] **Solutions** : une solution vérifiée par niveau, solveur A* et complément
  YASS pour 33 niveaux ; lecture depuis MICROSOL et entrée SOLUTION conditionnée
  par CHEAT MODE, sans enregistrer de progression pendant la présentation.
- [x] **Tutoriel** : cinq leçons avec consignes, proposées à la première partie
  et rejouables ; achèvement enregistré par profil, sans effet sur le classement.
- [x] **Menu et aide** : PLAY / RESUME, TUTORIAL, PROFILES, RESTART, GO TO LEVEL,
  OPTIONS, HALL OF FAME, HELP et QUIT TO DOS ; H ouvre directement l’aide,
  quitter l’aide revient au menu.
- [x] **Profils** : dix profils indépendants, création/renommage au clavier ou
  à la manette, noms uniques ; sélectionner le profil actif conserve la partie
  et l’historique sans relire le disque.
- [x] **Records et classement** : records par niveau (coups, puis poussées),
  enregistrement automatique ; classement par niveaux résolus décroissants,
  puis total des meilleurs coups croissant sur 32 bits ; format HOF3 et migration
  des anciens HOF1/HOF2.
- [x] **Sauvegarde et reprise** : fichiers SOK2 indépendants par profil,
  1830 octets de records et 134 octets de position ; empreintes par collection,
  CRC-8 de position, sauvegarde au menu/HELP ou après environ six secondes
  sans entrée ; position invalide ignorée, disquette protégée respectée.
- [x] **Accueil** : progression et profil actif, version, crédits blancs centrés
  (« APPLE II PORT BY » / « VERHILLE ARNAUD »), animation à environ 1,6 s par pas,
  puis classement pendant dix secondes et démo de sept niveaux ; présentation
  interrompue par touche ou bouton, sans sauvegarde.
- [x] **Sons** : pas, poussée sur cible, coup impossible, annulation, case morte
  et victoire ; sons de partie/menu/démo réglables séparément, partie et menu
  actifs par défaut ; musique d’accueil à deux voix (mélodie et basse, dix
  mesures, 24 s) sur le haut-parleur Apple II, arrêtée en quittant l’accueil,
  démo silencieuse par défaut.
- [x] **Chargement et disque** : bibliothèques partagées de ../dev, programme
  comprimé chargé à $6000, tampons déplacés en pages 2 et 3 pour libérer le
  résident, lectures RWTS avec cache des listes de secteurs,
  allocation DOS optimisée et écritures limitées aux secteurs modifiés.
- [x] **Retour BASIC** : QUIT TO DOS et Ctrl-RESET restaurent la page zéro
  et rechargent HELLO ; LIST et les relances par RUN fonctionnent.
- [x] **Corrections récentes** : fin des tables de textes sur deux octets
  (adresse de chaîne finissant par $FF acceptée), retours des menus et solutions
  sur la bonne page HGR, annulation de GO TO LEVEL depuis l’accueil sans lancer
  de partie, RESTART depuis l’accueil à zéro et PLAY / RESUME avec reprise.
- [x] **Partie quittée puis retrouvée** : le tutoriel rejoué depuis le menu rend
  le niveau en cours ; SOLUTION rend la position et l’historique Undo/Redo, même
  sur disquette protégée (solution lue hors de l’historique) ; renommer un autre
  profil ne change pas de profil actif ; un profil créé en cours de partie
  commence par le tutoriel.
- [x] **Manette** : après un rembobinage, le manche attend d’être recentré avant
  de déplacer le joueur ; port jeu ignoré (axes et boutons) sans manette branchée.
- [x] **Affichage et compteurs** : les tuiles sous « SAVING » (III:054, IV:036)
  sont redessinées après la sauvegarde ; coups et poussées s’arrêtent à 65535 ;
  le test de protection en écriture suit le slot du lecteur de DOS.
- [x] **Fichiers abîmés** : un fichier de records ou un classement illisible,
  absent ou de longueur impossible compte pour vide et le jeu continue ; une
  écriture qui échoue affiche « IO ERR » (sept caractères) sans quitter ; un
  fichier trop court ne laisse plus lire d’anciens octets comme des records ;
  `MICROHOF` est mis en accord avec ses dix profils au démarrage (profil actif,
  initiales, lignes sans profil ou en double, HOF2 compris).
- [x] **Écrans d’attente** : SUCCESS, BRAVO et HELP ignorent une touche tapée
  d’avance ou en répétition ; il faut un quart de seconde de clavier au repos.
- [x] **Mémoire** : le code du démarrage (lecture et contrôle de `MICROHOF`,
  migrations) quitte le résident pour le segment `BOOTCODE`, exécuté en `$1000`
  avant le premier paquet de niveaux.

## Vérification

`make test` construit la disquette et vérifie dans a2run la sortie vers BASIC,
les pages HGR et silhouettes monochromes, les textes des menus, la reprise,
le tutoriel, les options, les profils, le classement, les retours en partie
(tutoriel, SOLUTION, profils, manette, « SAVING », compteurs, touches en avance),
les fichiers abîmés (longueur impossible, fichier absent ou trop court,
classement incohérent) et les solutions des 454 niveaux. Les tests couvrent aussi les sauvegardes corrompues, migrations,
disquettes protégées et écritures sans changement.

Les captures et scénarios manette utilisent les outils partagés a2run/a2shot.
Les mesures de temps disque dans POM2 sont décrites dans le README ; elles
mesurent le processeur émulé et ne constituent pas des mesures sur machine physique.
