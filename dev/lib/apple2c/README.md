# lib/apple2c — texte + clavier Apple II pour C (cc65)

*[← dev](../../README.md)*

L'équivalent Apple II de `dev/lib/apple1c` de POM1 : la base texte/clavier sur
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
| `apple2c.mk` | fragment Makefile : `APPLE2C_SRCS`, `APPLE2C_INCS` |

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
