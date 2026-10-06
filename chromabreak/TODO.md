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
