# lib/apple2 — équates Apple II + primitives partagées (asm)

*[← dev](../../README.md)*

L'équivalent Apple II de `dev/lib/apple1` de POM1 : les mêmes routines, avec
les mêmes noms et les mêmes contrats, pour que le code écrit contre la
bibliothèque Apple-1 s'assemble ici en changeant d'include. S'y ajoutent deux
modules qui n'ont pas de raison d'être sur l'Apple-1 : `hgr.asm` (la vidéo est
intégrée à l'Apple II) et `exit.asm` (rendre la main à DOS proprement).

**Voisins :** [`../apple2c/`](../apple2c/) est le miroir C ;
[`../hgr/`](../hgr/) apporte le texte et les sprites HGR.

## Fichiers

- **`apple2.inc`** — équates matériel + ROM + DOS, macros `APPLE2_PREAMBLE`
  (programme `BRUN`) et `APPLE2_PREAMBLE_CALL` (programme lancé par `CALL`, qui
  ne touche pas à la pile).
- **`zp.inc`** — les 8 octets de ZP partagés (`tmp`, `tmp2`, `print_ptr_*`,
  `mul_*`, `prng_*`), en tête du segment ZEROPAGE.
- **`print.asm`** — `print_str_ax` : chaîne ASCIIZ via COUT.
- **`print_num.asm`** — `print_byte_dec` : octet en trois chiffres via COUT.
- **`kbd.asm`** — `wait_key` (bloquant) et `poll_key` (non bloquant).
- **`delay.asm`** — `delay_ms_a` : ~A millisecondes à 1,0205 MHz.
- **`hgr.asm`** — `hgr_init`, `hgr_init_clear`, `hgr_page1/2`, `text_restore`.
- **`exit.asm`** — `apple2_zp_save`, `apple2_exit`.
- **`sound.asm`** — `tone` : bip carré sur le haut-parleur.
- **`joy.asm`** — `read_stick`, `stick_dir` : manette (deux paddles).
- **`dos.asm`** — `dos_cmd_*`, `disk_protected` : commandes DOS 3.3 (BLOAD,
  BSAVE…) depuis un programme BRUN ; suppose `exit.asm`.

Les trois derniers sont sortis de MICRO-SOKOBAN pour que les autres jeux (sons,
manette, sauvegarde dans leurs `TODO.md`) partagent le même code ; leur miroir
C est dans [`../apple2c/`](../apple2c/) (`apple2game.h`, `apple2dos.h`).

## Routines

| Routine | Module | Entrée | Sortie | Écrase | ZP |
|---|---|---|---|---|---|
| `print_str_ax` | `print.asm` | A=lo, X=hi (ASCIIZ) | — | A, Y | `print_ptr_*` |
| `print_byte_dec` | `print_num.asm` | A = octet | "DDD" | A, X | — |
| `wait_key` | `kbd.asm` | — | A = touche & $7F, majuscule | A | — |
| `poll_key` | `kbd.asm` | — | A = touche ou 0, Z à jour | A | — |
| `delay_ms_a` | `delay.asm` | A = ms (0 → 256) | — | A, X, Y | — |
| `hgr_init` | `hgr.asm` | — | GRAPHICS + HIRES + PAGE1 + plein écran | A | — |
| `hgr_init_clear` | `hgr.asm` | — | idem, page 1 effacée avant la bascule | A, X | — |
| `hgr_page1` / `hgr_page2` | `hgr.asm` | — | page affichée | A | — |
| `text_restore` | `hgr.asm` | — | TEXT + plein écran + PAGE1 | A | — |
| `apple2_zp_save` | `exit.asm` | — | copie $00-$FF (256 o de BSS), RESET → `apple2_exit` | A, X | — |
| `apple2_exit` | `exit.asm` | — | vecteur RESET et ZP restaurés (fenêtre texte et curseur `$20-$29` gardés), écran texte, `JMP $03D0` | tout | — |
| `tone` | `sound.asm` | A = bascules (0 → 256), X = demi-période (0 → 256) ; ~(13 + 5·X) cycles par bascule | — | A, X, Y | — |
| `read_stick` | `joy.asm` | — | `joy_x`, `joy_y` = 0 (gauche / haut) … ~60 (centre) … ~120 ; ~6 ms | A, X, Y | — |
| `stick_dir` | `joy.asm` | `joy_x`, `joy_y` | A = `JOY_NONE` (0, Z = 1) / `JOY_UP` / `JOY_DOWN` / `JOY_LEFT` / `JOY_RIGHT` ; zone morte `JOY_LO`–`JOY_HI` (30–90, à définir avant l'include pour changer) ; la verticale l'emporte | A | — |
| `dos_cmd_new` | `dos.asm` | — | tampon de commande vide | A | — |
| `dos_cmd_add` | `dos.asm` | A = lo, Y = hi (ASCIIZ) | chaîne ajoutée | A, X, Y | — |
| `dos_cmd_hex` | `dos.asm` | A = octet | deux chiffres hexadécimaux ajoutés | A, X | — |
| `dos_cmd_run` | `dos.asm` | tampon | DOS exécute la commande, page zéro de DOS remise pendant ce temps | tout | — |
| `disk_protected` | `dos.asm` | — | C = 1 si la disquette du slot 6 est protégée en écriture | A | — |
| `apple2_return` | `exit.asm` | — | même restauration, puis `RTS` sur la pile de l'appelant (programme lancé par `CALL`, avec `APPLE2_PREAMBLE_CALL`) | tout | — |

## apple2.inc — symboles publics

| Symbole | Adresse | Rôle |
|---|---|---|
| `KBD` / `KBDSTRB` | `$C000` / `$C010` | verrou clavier (bit 7 = touche) / acquittement |
| `SPKR` | `$C030` | haut-parleur |
| `TXTCLR` `TXTSET` | `$C050` `$C051` | graphique / texte |
| `MIXCLR` `MIXSET` | `$C052` `$C053` | plein écran / 4 lignes de texte |
| `LOWSCR` `HISCR` | `$C054` `$C055` | page 1 / page 2 |
| `LORES` `HIRES` | `$C056` `$C057` | basse / haute résolution |
| `BUTN0-2`, `PADDL0-1`, `PTRIG` | `$C061-$C070` | manette |
| `TEXT1` `HGR1` `HGR2` | `$0400` `$2000` `$4000` | mémoire vidéo |
| `COUT` `CROUT` `PRBYTE` `PRHEX` | `$FDED` `$FD8E` `$FDDA` `$FDE3` | sorties Moniteur |
| `HOME` `VTAB` `RDKEY` `BELL` `WAIT` `SETTXT` | … | autres routines Moniteur |
| `CH` `CV` | `$24` `$25` | curseur texte |
| `DOSWARM` `SOFTEV` | `$03D0` `$03F2` | retour DOS / vecteur RESET |
| `KC_LEFT` `KC_RIGHT` `KC_UP` `KC_DOWN` `KC_RET` `KC_ESC` `KC_SPACE` | 7 bits | codes rendus par `kbd.asm` |

Les codes de touches ont le préfixe `KC_` exprès : les jeux ont souvent leurs
propres `KEY_*`.

## Page zéro

Sur l'Apple-1, `zp.inc` fige ses 8 octets en `$00-$07`. Sur l'Apple II la page
zéro appartient au Moniteur (`$20-$4F`), à DOS et à Applesoft (`$50-$FF`) : le
pool occupe simplement le début du segment ZEROPAGE, que
`dev/cc65/apple2_hgr.cfg` place en `$50`. COUT, HOME et RDKEY continuent donc
de marcher. Un programme qui revient à DOS appelle `apple2_zp_save` en tout
premier, et sort par `apple2_exit`. Entre les deux, Ctrl-RESET passe aussi par
`apple2_exit` : sans cela DOS reprendrait la main avec la page zéro du jeu, y
compris sur la routine CHRGET d'Applesoft (`$B1-$C8`).

## Son, manette, DOS

```asm
        LDA #$30                ; bip aigu court : $30 bascules, période $28
        LDX #$28
        JSR tone

        JSR read_stick          ; manette -> joy_x / joy_y
        JSR stick_dir           ; A = JOY_UP.. ou 0
        BEQ @centre
        LDA BUTN0               ; bouton 0 : bit 7 = 1 tant qu'il est enfoncé
        BMI @feu

        JSR dos_cmd_new         ; "BSAVE SCORE,A$1000,L$04"
        LDA #<str_bsave         ; .byte "BSAVE SCORE,A$1000,L$", 0
        LDY #>str_bsave
        JSR dos_cmd_add
        LDA #$04
        JSR dos_cmd_hex         ; ajoute "04"
        JSR disk_protected      ; disquette protégée : DOS arrêterait le jeu
        BCS @pas_de_sauvegarde  ; sur WRITE PROTECTED, on saute
        JSR dos_cmd_run
```

Pendant `dos_cmd_run`, DOS retrouve la page zéro sauvée au démarrage par
`apple2_zp_save` (obligatoire avant la première commande) ; celle du programme
est mise de côté dans 256 octets de BSS puis remise. Un programme qui
n'utilise qu'une plage de page zéro peut définir `DOS_ZP_START` et
`DOS_ZP_LEN` avant l'include : seule cette plage est alors sauvegardée pour
le programme, DOS conservant toujours son instantané complet. Une erreur DOS (fichier
absent…) arrête le programme au prompt : le `Makefile` met sur la disquette
tous les fichiers lus, et `disk_protected` est testé avant d'écrire. MICRO-SOKOBAN
s'en sert pour ses paquets de niveaux (`BLOAD`), `MICROSAVE` et `MICROHOF`.

`DOS_CMD_MAX` règle la taille du tampon de commande (40 octets par défaut).
Avec `DOS_CMD_WORKBSS = 1`, ce tampon et son index occupent le segment `WORKBSS`
du programme plutôt que `BSS`, pour libérer de la place à côté du code.

## Exemple

```asm
.include "apple2.inc"
.include "zp.inc"

.segment "CODE"
main:   APPLE2_PREAMBLE
        JSR apple2_zp_save
        LDA TXTSET
        JSR HOME
        LDA #<msg
        LDX #>msg
        JSR print_str_ax
        JSR wait_key
        JMP apple2_exit

msg:    .byte "HELLO!", $0D, 0

.include "print.asm"
.include "kbd.asm"
.include "exit.asm"
```

    ca65 -t none -I dev/lib/apple2 -o hello.o hello.s
    ld65 -C dev/cc65/apple2_hgr.cfg -o hello.bin hello.o      # BRUN à $6000
    python3 dev/tools/dos33.py --master dos33_master.dsk --out HELLO.dsk \
        --bas HELLO=hello.bas --bin HELLOBIN=hello.bin@0x6000

Exemple complet : [`../../examples/hello`](../../examples/hello).
