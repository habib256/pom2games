# Wilderness — à faire

## Vue
- Vitesse (`tools/profile.py`, toujours au bit près contre `view_ref.py`) :
  une vue complète coûte ~2,5 M cycles (boucle de pas ~55 %, remplissage
  ~25 %). Écartés après mesure : arrêt anticipé par maxima de blocs (net
  1-2 %), RTS laissé en place entre segments (plus lent). Non exacts, à
  décider : pas doublé au-delà de 64 cases (−10 à 20 % de pas). Double
  tampon impossible tant que la page 2 tient la table de division.
- Forêts dans la vue et sur la carte (masque de bits par ligne, à ajouter au
  format de carte), soleil selon l'heure, portée réduite par mauvais temps.
- Images superposées (épave de l'avion au départ, objets, animaux).

## Carte
- Lacs moins étendus (le remplissage jusqu'au débordement fait de grandes
  nappes plates), rivières plus continues.
- Écran TOPO : courbes de niveau, eau, position et but, défilement.
- Les six régions (paramètres climatiques de l'en-tête original `$6000-$605F`).

## Jeu (à analyser dans l'original d'abord)
- Modèle de survie : faim, soif, énergie, température, blessures, maladies.
- Parseur verbe + nom (vocabulaire de 280 mots dans `docs/ANALYSE.md`).
- Temps, météo, saisons ; écrans STATUS et INVENTORY ; sauvegarde.
