# ProDOS 8 pour les jeux Apple //e enhanced 128 Ko

`prodos.h`, `mli.s` : appel MLI à `$BF00`, constantes de fichiers, blocs,
préfixes et sortie. Fournir `prodos_command` et `prodos_params`, puis appeler
`prodos_call()` ; le résultat vaut zéro ou le code d'erreur ProDOS. Les listes
commencent par un octet de nombre de paramètres, suivi des champs du manuel.
Un tampon de lecture doit se trouver dans des pages disponibles du bitmap
système ; cette interface n'alloue pas de tampon et ne modifie pas sa protection.

`video.c` : prise de possession de la mémoire auxiliaire pour le DHGR et
reconstruction du disque `/RAM` vide à la sortie. Aucune vérification des
fichiers de `/RAM`, aucun dialogue avant le lancement du jeu.

Démarrage C : [`crt0_prodos.s`](../../cc65/crt0_prodos.s) et
[`apple2_dhgr_prodos_c.cfg`](../../cc65/apple2_dhgr_prodos_c.cfg). Le binaire à
`$6000` utilise les pages vidéo main/aux `$2000–$5FFF`. Le runtime sauvegarde
la page zéro, le vecteur RESET et le bitmap système, puis les restaure avant
l'appel MLI `QUIT`. Le jeu fournit `game_shutdown()` pour arrêter sa souris,
restaurer le mode texte et libérer la mémoire vidéo. RESET suit cette sortie.

Exemple complet : [`chromabreak`](../../../chromabreak/README.md).
L'amorce `CHROMA.SYSTEM` charge `CHROMA.SYS`, qui reloge le programme à `$6000`
en copiant depuis la fin, y compris lorsque source et destination se recouvrent.

Référence : [manuel technique ProDOS, programmes système](https://prodos8.com/docs/techref/writing-a-prodos-system-program/).
