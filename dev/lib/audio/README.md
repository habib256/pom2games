# Échantillons audio sur le haut-parleur Apple II

Module optionnel 6502/cc65 : `a2_sample_play(sample)` joue un clip PWM sur
le haut-parleur natif. Aucun matériel audio supplémentaire n'est nécessaire.
Le lecteur est dérivé du générateur de Colin Leroy-Mira utilisé par
[Shufflepuck](https://github.com/colinleroy/a2tools/tree/main/src/shufflepuck).
Attribution, révision et adaptations : [NOTICE.txt](../../tools/audio/NOTICE.txt).
Licence du lecteur et du générateur : GPL-3.0-or-later.

```make
include $(DEV)/cc65/apple2.mk
include $(AUDIO)/audio.mk
# Ajouter $(AUDIO_SRCS) aux sources et $(AUDIO_INCS) aux flags C.
```

Les configurations ld65 communes déclarent le segment optionnel `AUDIOCODE`,
aligné sur 256 octets. Sans le module, ce segment ne consomme aucune mémoire.
Une autre configuration doit déclarer ce segment en RAM principale modifiable,
avec `align=$100`. Le lecteur n'alloue aucune BSS ni nouvelle zéro-page ;
il emprunte `ptr1`, `ptr3`, le premier octet de `ptr4` et `tmp3` de cc65.
Son code coûte 1 950 octets, plus jusqu'à 255 octets d'alignement.

## Convertir et jouer

```sh
python3 dev/tools/audio/pack_wav.py effet.wav --out build/effet --name effet
```

Assembler `build/effet.s`, inclure `build/effet.h`, puis :

```c
#include "audio.h"
#include "effet.h"
a2_sample_play(effet);
```

Le convertisseur accepte les WAV PCM 8/16/24/32 bits, mélange les canaux,
rééchantillonne à 8 kHz nominaux et quantifie sur 48 niveaux. La décimation
utilise une moyenne par intervalle ; l'interpolation est linéaire en montée.
Un fondu de 2 ms atténue les extrémités (`--fade-ms 0` pour le désactiver).
Chaque échantillon coûte un octet ; la fin `$92` ajoute un octet. Les seuls
codes valides sont les octets pairs `$32..$90`, suivis de `$92`.
Un clip vide contient seulement la fin et ne touche pas le haut-parleur.

La lecture **bloque le CPU et masque les IRQ pendant tout le clip** ; elle
rétablit ensuite le masque d'entrée. La souris native du //c, une horloge IRQ
ou une réception série peuvent donc perdre des événements pendant la lecture.
Privilégier les effets courts et les jingles hors animation. Ce lecteur ne
fournit pas de mixage ni de lecture en arrière-plan.

Exiger D=0, RAM/ZP principales et CPU à sa vitesse nominale de 1 MHz.
Le module ne détecte ni ne configure les accélérateurs ou le IIgs.
Aucun commutateur vidéo, banque mémoire ou vecteur IRQ n'est modifié.
Un pointeur nul est accepté ; les autres buffers doivent être immuables,
terminés et ne pas franchir `$FFFF`. Il n'y a pas de validation du flux cible.

Deux périodes PWM de 63 cycles donnent **126 cycles par échantillon**.
« 8 kHz » est la fréquence nominale de conversion ; la fréquence effective
vaut horloge CPU / 126 (environ 8,1 kHz sur Apple II). Les clips longs occupent
vite la RAM : une seconde convertie coûte environ 8 Ko.

## Vérifier et régénérer

```sh
python3 dev/tools/audio/generate_player.py --check
python3 dev/tests/test_audio.py
python3 dev/tests/test_audio.py --iie
make -C dev/examples/perspective run
```

Le lecteur assemblable est livré : un compilateur C hôte sert uniquement à
sa régénération. Les tests exécutent les 48 niveaux, des transitions dans les
deux sens, plusieurs franchissements de pages, les masques IRQ et l'API cc65.
Sur a2run, le journal des impulsions est horodaté au début des instructions ;
sur POM2/65C02, les visites du code vérifient les intervalles d'échantillonnage.
La validation est émulée ; aucun essai sur machine physique n'est revendiqué.
