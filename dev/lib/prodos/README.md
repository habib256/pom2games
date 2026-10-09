# ProDOS 8 pour les jeux Apple //e enhanced 128 Ko

`prodos.h`, `mli.s` : appel MLI à `$BF00`, constantes de fichiers, blocs,
préfixes et sortie. Fournir `prodos_command` et `prodos_params`, puis appeler
`prodos_call()` ; le résultat vaut zéro ou le code d'erreur ProDOS. Les listes
commencent par un octet de nombre de paramètres, suivi des champs du manuel.
Un tampon de lecture doit se trouver dans des pages disponibles du bitmap
système ; cette interface n'alloue pas de tampon et ne modifie pas sa protection.

`video.s` : prise de possession explicite de la mémoire auxiliaire pour le
DHGR et reconstruction du disque `/RAM` vide à la sortie.
`prodos_video_claim(PD_VIDEO_PRESERVE_RAM)` refuse tout `/RAM` installé,
même vide ; cette politique ne parcourt pas ses fichiers.
`PD_VIDEO_DISCARD_RAM` autorise explicitement leur destruction. Appeler ce
service avant le premier dessin auxiliaire et vérifier `PD_VIDEO_OK`.
Les autres statuts signalent un `/RAM` à préserver, une politique invalide ou
une liste de périphériques malformée. Un refus conserve la transaction
active ; une prise répétée conserve l'unité à restaurer. La libération appelle
FORMAT une seule fois. ChromaBreak choisit explicitement DISCARD.
La recherche reste dans les 14 entrées de `DEVLST` (`$BF32–$BF3F`) :
`DEVCNT` contient le nombre d'unités moins un, ou `$FF` si la liste est vide.
Les indices dépassant 13 sont ignorés et ne déclenchent aucun formatage.
`make test-tools` vérifie ces bornes sur le code cc65 avec un pilote FORMAT
de test qui enregistre l'unité demandée.

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
