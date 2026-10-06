# CHROMABREAK — TODO

- [x] Profil Apple //e enhanced 128 Ko, distinct du II+ 48 Ko / DOS 3.3.
- [x] Disquette ProDOS 2.4.3 amorçable et chargeur SYS autonome.
- [x] Bibliothèques communes ProDOS MLI, runtime et AppleMouse II.
- [x] DHGR 16 couleurs, deux pages, briques colorées et sauvegarde des fonds.
- [x] Exploiter la palette : briques à reflets, titre multicolore ; cadre sobre et raquette cyan.
- [x] Vérifier les raquettes normale/large et la balle blanche ronde dans les sept phases DHGR.
- [x] 12 tableaux, huit angles, résistance, acier, six capsules et vies bonus.
- [x] Souris par défaut pour clic et Espace ; clavier disponible avec K.
- [x] Souris intégrée native du //c : IRQ ROM actives, banques masquées brièvement.
- [x] Tests de démarrage et souris sur les ROMs //c de 16 et 32 Ko.
- [x] Retirer la vérification /RAM et le dialogue avant le lancement.
- [x] Remplacer le rendu C coûteux par l'assembleur et le score différentiel.
- [x] Tests ProDOS, clavier, transitions et firmware des deux souris POM2.
- [x] Balle ronde, collisions adaptées et sauvegarde du fond aux coins transparents.
- [x] Sons distincts, séquencés sans bloquer les IRQ souris ; silence en pause.
- [x] Départ 50 % plus rapide, accélération tous les huit blocs jusqu’à six sous-pas.
- [x] Renommer le projet, la page de garde et la disquette en ChromaBreak.
- [x] Démarrage en un clic/Espace/Entrée, avec balle lancée et clavier via K.
- [x] Mise à jour des seuls bords de raquette et suppression des divisions aux impacts.
- [x] VBL //e et IRQ VBL //c : cadence régulière NTSC/PAL et nettoyage à la sortie.
- [x] Un seul dessin de tableau, présentation complète puis copie main/aux cachée.
- [x] Retirer le fond diagonal et corriger la police (sept colonnes complètes).
- [ ] Valider sur Apple //e enhanced physique avec carte AppleMouse II et sur //c physique.
- [ ] Jouer une campagne complète avec un pilote automatique sans injection.
- [x] Sauvegarder les cinq records sur ProDOS, avec initiales et difficulté.
- [x] Ajouter des tableaux propres à la version DHGR ; conserver le fond noir demandé.

## ChromaBreak — évolution demandée

- [x] 1. Douze tableaux propres au jeu : motifs, passages et chemins de rebonds.
- [x] 2. Bonus multiballe (trois balles), double laser, balle traversante, avec acier conservé.
- [x] 3. Combos de destructions jusqu’à ×8, réinitialisés au contact raquette/perte de vie.
- [x] 4. Éclats colorés limités et flash bref des briques résistantes, sans traces.
- [x] 5. Cinq records ProDOS, trois initiales, mode affiché, rechargement après redémarrage.
- [x] 6. Détente, Arcade, Expert : vies, largeur, vitesse et progression distinctes.
- [x] Raquette cyan sobre, extrémités arrondies argentées, ombre et clavier réactif.
- [x] Vérifier chaque mécanique, sauvegarde réelle et gestion des erreurs de disque.
- [x] Vérifier souris //e et //c, PAL/NTSC, rendu des deux pages et cadence avec bonus.
- [x] Actualiser la disquette, les images et le mode d’emploi.
- [x] Rétablir la cadence NTSC régulière avec le firmware complet AppleMouse (MAME).
- [x] Optimiser les dix sprites simultanés à vitesse Expert : le test exige 30/25 images/s.

### Optimisation du rendu — validée

- [x] Sauvegarde des sprites séparée par banque ; boucle de dessin identique en RAM principale et auxiliaire.
- [x] Masques de la balle blanche, des tirs, capsules et éclats précalculés pour les sept alignements DHGR.
- [x] Pixels déroulés, paramètres et masques en page zéro ; fonds alignés sur 32 octets.
- [x] Scénario maximal à cadence régulière NTSC et PAL sur //e et //c.
- [x] Boucle multiballe en assembleur, état physique en page zéro, chaque sous-pas conservé.
- [x] Cache des zones vides par balle, réinitialisé avant chaque déplacement ; 328 640 positions comparées au modèle de collision.
- [x] HUD souhaité partagé, historique de dessin séparé pour chaque page, glyphes blancs accélérés.
- [x] Présentation sur un VBL frais après un long chargement ; revalidation des transitions.
- [x] Conversion du score bornée à 1 043 cycles, validée pour 65 536 valeurs ; copie directe vers le HUD.
- [x] Effacement des seules bandes laissées par la raquette, couleurs et arrondis conservés.
- [x] Cache des sept phases pour deux familles de largeur ; dessin direct depuis le cache.
- [x] Dessin des balles, capsules, tirs et éclats piloté en assembleur.
- [x] Éclats calculés en assembleur ; flash restauré sur les deux pages.
- [x] Revalider niveaux, police, silhouettes, bonus, records et erreurs ProDOS après ces changements.
- [x] Scénario maximal : dix objets à vitesse Expert, cadence 30 Hz NTSC / 25 Hz PAL.

Validation finale : les douze profils firmware/démarrage/sortie passent,
y compris les dix objets simultanés à 30 Hz NTSC et 25 Hz PAL. Les tests
ProDOS, clavier, douze transitions, victoire/reprise, les comparaisons exhaustives
de collision et les 65 536 conversions numériques passent également.
Les records sont vérifiés après redémarrage, avec fichier absent/corrompu
et disque protégé. Les captures du menu et du premier tableau sont actualisées.


## Espace à l’écran, petite police et anglais

- [x] Bandeau compact en haut ; aire de jeu de 180 lignes, raquette à y=184.
- [x] Remonter les huit rangées de briques à y=14, avec collisions cohérentes.
- [x] Ajouter `dhgr_puts_small` et l’entrée rapide par caractère dans la lib DHGR.
- [x] Police blanche 4×5, avance de cinq colonnes, sept alignements sans découpe.
- [x] Passer tous les écrans, niveaux, difficultés et messages en anglais.
- [x] Conserver le logo multicolore agrandi et adapter le curseur des initiales.
- [x] Tester les glyphes, la sauvegarde ProDOS et les transitions des 12 tableaux.
- [x] Conserver 30 Hz NTSC / 25 Hz PAL avec souris et dix objets sur //e et //c.


## Menus adaptés à la petite police

- [x] Centrer les textes avec l’avance de cinq colonnes.
- [x] Regrouper PLAY et les touches de lancement dans un seul cadre.
- [x] Réunir les trois difficultés et souligner le mode sélectionné.
- [x] Regrouper les commandes clavier, les records et la sortie sous le menu.
- [x] Aligner les colonnes des records et afficher le nom complet du mode.
- [x] Recentrer la fin de partie, le score et la saisie des initiales.
- [x] Actualiser les captures ; revalider clavier, souris, records et cadence //e / //c.


## Détails, raquette verticale, ennemis et capsules

- [x] Texte Beautiful Boot à la technique HGR (point HGR → deux points DHGR) : blanc et lisible en couleur, 40 cellules.
- [x] Bandeau de 37 cellules (lignes 1 à 7), nom du tableau ou du bonus aligné à droite.
- [x] Briques biseautées aux coins arrondis, fentes de résistance, acier à reflet diagonal, cadre en deux tons.
- [x] Logo en relief à partir des glyphes Beautiful Boot.
- [x] Raquette verticale jusqu’à mi-terrain, bloquée par les briques sur toute sa trajectoire.
- [x] Contact balle/raquette vérifié à chaque image (raquette qui glisse ou monte vers la balle).
- [x] Effet de la raquette sur le rebond ; la capture garde le point d’impact.
- [x] Deux ennemis à la Arkanoid : portes, contournement des briques, balle/laser/raquette, sortie par le bas.
- [x] Capsules en blocs 5 × 6 avec lettre noire E S C D L P.
- [x] Mémoire : tables communes sans la petite police, doublement calculé en `$0F00`, pile C de 768 octets.
- [x] Cadence 30/25 images/s conservée sur les douze profils, avec raquette en diagonale et scénario à ennemis.
- [x] Mode démo après 15 s d’inactivité (50/60 Hz détectés), pilote automatique silencieux.
- [x] Image de tables propre au jeu en `$0800` ; tableaux compactés à deux briques par octet.
- [x] Mode Chat Mauve toujours actif : texte 560 mono, graphismes en bit 7, verrou RVB (IOUDIS sur //c).
- [x] Banc //c : ports série intégrés branchés (la ROM lit l’état des ACIA à chaque IRQ).
- [x] Laser : canons rouges sur la raquette ; balle traversante rouge 4 × 7 (masques ronds en cache).
- [x] Bandeau moins cher : score BCD, messages préalignés, locales statiques ; scénario « balles traversantes » testé.
- [x] Balle traversante en sphère ombrée (encre précalculée), tirs à tête blanche.
- [x] Menu Échap : reprise, choix des douze tableaux, son, titre, ProDOS.
- [x] Soixante tableaux en ASCII (`levels.txt`), banque en RAM auxiliaire, sélecteur au menu.
- [x] Fonds par décennie au-dessus de la zone de la raquette ; plus de ligne basse.
- [x] Ennemis en bobines (barres colorées, noyau blanc), distincts des balles.
- [x] Second ennemi en chasseur TIE (ailes colorées, noyau blanc) qui ondule en vagues.
- [x] « SECTOR nn CLEAR » et jingle à chaque tableau terminé.
- [x] Finale après le tableau 60 : recouvrement ENDING en `$4000`, VICTORY, fanfare, feux d’artifice.
- [x] Difficultés au titre : seul le trait de sélection est redessiné.
- [x] Thème de titre (I-vi-IV-V), interrompu par une touche ; thème et jingle en RAM auxiliaire.
- [x] Progression (secteur le plus lointain) sauvegardée dans HIGHSCORES ; le menu ne propose que les secteurs atteints.
- [x] Fond dès le niveau 1 : six motifs, un par décennie (croix ajoutées pour 51-60).
- [x] Jingle de fin de tableau par décennie : six jingles (do, ré, mi, fa, sol, la), de plus en plus ornés.
- [x] Version 1.0 et nom de l’auteur sur la page de garde ; « 65C02 » dans le sous-titre.
- [x] Pile C ramenée à 256 octets (usage mesuré : 18 octets) ; test de marge dans le playtest.
- [x] Joystick et paddles (`J`) : axes absolus, boutons 0/1, lecture dans l’attente du VBL sans coût de cadence.
- [ ] Valider joystick et paddles sur machine réelle (calibrage des manettes).
- [x] //e d’origine (6502) : message clair et retour à ProDOS au lieu d’un plantage (testé dans POM2).
- [ ] Valider le rendu des capsules et du texte sur moniteur couleur réel.
- [x] Page d’aide (`?` au titre) : capsules, tuiles, points ; code dans le recouvrement ENDING.
- [x] Musique à deux voix (thème, airs de fin, fanfare) : lecteur en page 3, intonation juste.
- [x] Dix airs de fin de tableau à deux voix, un par tableau d’une dizaine, d’environ 2 s (3,3 s pour le dixième).
- [x] Adresses figées des modules assembleur : réserve et assertions de `spare.s`.
- [ ] Écouter les airs à deux voix sur //e et //c réels (porteuse à 31 kHz).
- [x] Score sur six chiffres jusqu’à 650 000 (compté en dizaines), vie tous les 5 000 points ; `HIGHSCORES` au format 2, le format 1 est converti.
- [x] Raquette en diagonale sous une brique de la dernière rangée, ou élargie entre une brique et un mur : elle reste sous les briques et dans le terrain (elle sortait du terrain et la machine se figeait).
- [x] `?` sans le fichier `ENDING` : la page de garde reste affichée ; démo de 60 s en PAL comme en NTSC.
- [ ] Refaire les trois captures POM2 : `game.png` et `game-sector-2.png` (bandeau encore sur cinq chiffres) et `title.png` (encore « V1.0 »).
- [x] Version 1.1 sur la page de garde.
- [x] Hauteur de la raquette à la souris en absolu (le firmware borne le pointeur à la course de la raquette) : plus de course perdue après une vie perdue.
- [x] Le joystick choisi par `J` reste le mode de jeu après une fin de partie (bouton ou Espace) et après une démo.
- [x] Une raquette qui monte d’un coup au-delà d’une capsule la ramasse.
