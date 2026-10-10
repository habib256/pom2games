# Grille en perspective et échantillon PWM

```sh
make -C dev/examples/perspective
make -C dev/examples/perspective run
make -C dev/examples/perspective test
```

La disquette DOS 3.3 est `build/PERSPECTIVE.dsk` ; elle fonctionne dans le
profil Apple II+ 48 Ko et sur IIe. Une grille illustre la projection complète
sur 280 pixels. Espace joue un effet synthétique de 40 ms ; ESC revient à DOS.
Le son masque les IRQ et suspend le programme pendant sa lecture.

La caméra et le WAV sont générés dans `build/`. Aucun fichier audio extérieur
n'est requis. Modifier les paramètres de la règle `camera.h` pour régler la
perspective ; remplacer le WAV pour essayer un autre effet. Les bibliothèques
[perspective](../../lib/perspective/README.md) et
[audio](../../lib/audio/README.md) restent indépendantes et optionnelles.
