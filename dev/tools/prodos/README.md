# Fabriquer un disque ProDOS

    python3 build_volume.py stage dist/GAME.po --volume GAME --boot boot.bin --blocks 280
    python3 read_volume.py dist/GAME.po

Image brute en ordre de blocs ProDOS, 280 blocs de 512 octets pour une
disquette 5,25 pouces. Dates fixes et allocation déterministe. Le lecteur
permet de vérifier le contenu produit sans monter le disque.

Dans `stage`, utiliser par exemple `PRODOS#FF0000` et
`CHROMA.SYSTEM#FF2000` et `CHROMA.SYS#FF2000` : suffixe `#TTAAAA` pour le type
et l'adresse auxiliaire. Le suffixe est retiré sur le volume. `CHROMA.SYSTEM`
est le chargeur de type SYS (`$FF`) lancé automatiquement par ProDOS ; il
charge ensuite le jeu `CHROMA.SYS`.

`PRODOS` est ProDOS 8 **2.4.3**, redistribué en tant que système Apple, et
`boot.bin` contient ses deux blocs d'amorce. Ces deux fichiers proviennent des
ressources ProDOS locales utilisées par A2 File Cmd ; le système est identique
à celui du disque officiel ProDOS 2.4.3. Ils conservent leurs droits Apple et
les crédits de leurs auteurs, distincts de la licence du code du dépôt.
[ProDOS 2.4.3 et ses crédits](https://prodos8.com/releases/prodos-243/).

Les deux scripts sont adaptés des outils GPL-3.0 d'A2 File Cmd, de VERHILLE
Arnaud (`tools/mkvolume.py` et `tools/prodos_read.py`). Aucune dépendance à ce
projet n'est nécessaire pour construire un jeu.
