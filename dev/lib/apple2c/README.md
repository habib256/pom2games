# lib/apple2c — texte + clavier Apple II pour C (cc65)

*[← dev](../../README.md)*

L'équivalent Apple II de `dev/lib/apple2c` de POM1 : la base texte/clavier sur
laquelle s'appuie un programme C, indépendante du mode graphique. La sortie
passe par COUT (`$FDED`) sur la page texte, l'entrée lit le verrou clavier
(`$C000`, acquitté par `$C010`). Le miroir asm est [`../apple2/`](../apple2/).

## Fichiers

| Fichier | Rôle |
|---|---|
| `apple2io.h` | l'API (ou `apple2c.h`) |
| `apple2io_asm.s` | les routines qui appellent la ROM ou lisent le clavier |
| `apple2io.c` | `a2_puts`, `a2_print_hexword` |
| `apple2c.h` | en-tête parapluie |
| `apple2c.mk` | fragment Makefile : `APPLE2C_SRCS`, `APPLE2C_INCS`, `APPLE2C_GAME_SRCS`, `APPLE2C_DOS_SRCS`, `APPLE2C_AFLAGS` |
| `apple2game.h` + `apple2game_asm.s` | haut-parleur, manette, boutons (optionnel) |
| `apple2dos.h` + `apple2dos_asm.s` | commandes DOS 3.3 : BLOAD, BSAVE… (optionnel) |

## API

| Apple-1 (`apple1c`) | Apple II (ici) | Effet |
|---|---|---|
| `woz_putc(c)` | `a2_putc(c)` | un caractère (`'\r'` = retour à la ligne) |
| `woz_puts(s)` | `a2_puts(s)` | chaîne terminée par 0 |
| `woz_print_hex(b)` | `a2_print_hex(b)` | octet en hexadécimal |
| `woz_print_hexword(w)` | `a2_print_hexword(w)` | mot 16 bits en hexadécimal |
| `woz_mon()` | `a2_dos()` | retour au prompt DOS `]`, ZP restaurée |
| — | `a2_home()` | efface l'écran texte |
| — | `a2_text()` | TEXT + plein écran + page 1 |
| — | `a2_wait(a)` | pause Moniteur `WAIT` (`a2_wait(A2_WAIT_FRAME)` ≈ une trame) |
| `apple1_iskeypressed()` | `apple2_iskeypressed()` | ≠ 0 si une touche attend |
| `apple1_getkey()` | `apple2_getkey()` | attend une touche, `& 0x7F`, majuscule |
| `apple1_readkey()` | `apple2_readkey()` | 0 ou la touche, sans attendre |

### Son, manette, DOS (objets optionnels)

Les mêmes routines que les modules asm `../apple2/sound.asm`, `joy.asm` et
`dos.asm`, appelées depuis C. Ce sont des objets à part (`apple2game_asm.s`,
`apple2dos_asm.s`, assemblés avec `-I dev/lib/apple2`) : un programme qui ne
s'en sert pas ne paie rien (ANIMALS tient tout juste sous DOS).

| Fonction | Effet |
|---|---|
| `a2_tone(flips, period)` | `flips` bascules du haut-parleur, ~(13 + 5·period) cycles chacune |
| `a2_read_stick()` | lit la manette (~6 ms) : `A2_JOY_NONE/UP/DOWN/LEFT/RIGHT`, valeurs brutes dans `a2_joy_x`, `a2_joy_y` |
| `a2_button(n)` | ≠ 0 tant que le bouton n (0-2) est enfoncé |
| `a2_dos_cmd("BLOAD HISCORE,A$1000")` | une commande DOS complète |
| `a2_dos_new()`, `a2_dos_add(s)`, `a2_dos_hex(b)`, `a2_dos_run()` | construire une commande avec des adresses calculées |
| `a2_disk_protected()` | 1 si la disquette du slot 6 est protégée en écriture |

`a2_dos_*` rendent à DOS la page zéro que `crt0_apple2.s` a sauvée au
démarrage (exportée sous le nom `apple2_zp_buf`, comme dans `exit.asm`). Une
erreur DOS arrête le programme au prompt : mettre les fichiers sur la
disquette et tester `a2_disk_protected()` avant d'écrire.

Macros : `puts_apple2(s)`, `println_apple2(s)`, `getchar_apple2()`, plus les
codes `KC_LEFT` `KC_RIGHT` `KC_UP` `KC_DOWN` `KC_RET` `KC_ESC`.

`a2_dos()` et le retour de `main()` reposent sur
[`../../cc65/crt0_apple2.s`](../../cc65/crt0_apple2.s) : il sauvegarde la page
zéro au démarrage et la remet avant de sauter en `$03D0`. Pendant l'exécution,
Ctrl-RESET passe aussi par ce chemin.

## Programme minimal

```c
#include "apple2c.h"

void main(void) {
    a2_text();
    a2_home();
    puts_apple2("HELLO WORLD\r");
    apple2_getkey();
}                                   /* retour à DOS */
```

    ca65 -t none -o crt0_apple2.o dev/cc65/crt0_apple2.s
    cl65 -t none -Oirs -I dev/lib/apple2c -c -o hello.o hello.c
    ...
    cl65 -t none -C dev/cc65/apple2_hgr_c.cfg -o hello.bin \
         crt0_apple2.o hello.o apple2io.o apple2io_asm.o      # crt0 en premier

Exemple complet : [`../../examples/hello`](../../examples/hello).
