# lib/apple2 — équates Apple II + primitives partagées (asm)

*[← dev](../../README.md)*

Primitives assembleur pour l'Apple II : équates matériel, texte, clavier,
temporisation, son, manette et commandes DOS. `hgr.asm` initialise la vidéo
native ; `exit.asm` restaure la page zéro pour rendre la main à DOS proprement.

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
- **`kbd.asm`** — `wait_key` (bloquant), `poll_key` (non bloquant) et
  `kbd_upcase` (repli minuscules → majuscules).
- **`delay.asm`** — `delay_ms_a` : ~A millisecondes à 1,0205 MHz.
- **`hgr.asm`** — `hgr_init`, `hgr_init_clear`, `hgr_page1/2`, `text_restore`,
  `native_video` (sur IIe/IIc, remet les commutateurs 80STORE/80COL/RAMRD/
  RAMWRT/DHGR en vidéo native avant tout changement de mode ; rien sur II+),
  et la macro `HGR_CLEAR_LOOP` (8 Ko depuis la page X avec l'octet A, huit
  STA absolus auto-modifiés par tour, ~46 000 cycles, sans page zéro) que
  partagent `hgr_init_clear`, `clear_hgr` (lib/hgr) et `hgr_clear` (C).
- **`exit.asm`** — `apple2_zp_save`, `apple2_exit`, `apple2_return` ;
  sur IIe/c, désactive RAMRD/RAMWRT, 80STORE, 80 colonnes et DHGR avant de
  restaurer le vecteur RESET et la page zéro dans la mémoire principale.
  L'entrée suppose le code et la pile en banque principale ; les commutateurs
  étendus ne sont pas touchés sur II/II+. La fenêtre texte et le curseur sont
  conservés : rétablir sa largeur si le programme l'a modifiée pour 80 colonnes.
  `APPLE2_EXIT_HOOK` (défini avant l'include) nomme une routine appelée
  après la restauration, avant le retour à DOS (aussi sur Ctrl-RESET).
- **`sound.asm`** — `tone` : bip carré sur le haut-parleur.
- **`joy.asm`** — `read_stick`, `stick_dir` : manette (deux paddles).
- **`lz4fh.asm`** — `lz4fh_unpack` : décompression fhpack/LZ4FH vers une zone
  de 8 Ko alignée (notamment les pages HGR). Entrées `lz4fh_src/dst`, scratch
  configurable ; code en RAM, flux validé à la compilation. Une erreur de
  format passe au Moniteur, conformément au décodeur amont. Provenance et
  licence Apache-2.0 conservées dans `lz4fh-NOTICE.txt` / `lz4fh-LICENSE.txt`.
- **`dos.asm`** — `dos_cmd_*`, `disk_protected` : commandes DOS 3.3 (BLOAD,
  BSAVE…) depuis un programme BRUN ; suppose `exit.asm`. Les ajouts sont
  bornés à `DOS_CMD_MAX-1` caractères ; les deux chiffres hexadécimaux sont
  ajoutés ensemble ou refusés. Un dépassement renvoie carry=1 et interdit
  l’exécution de la commande partielle jusqu’au prochain `dos_cmd_new`.

`sound.asm`, `joy.asm` et `dos.asm` sont sortis de MICRO-SOKOBAN pour que les autres jeux (sons,
manette, sauvegarde dans leurs `TODO.md`) partagent le même code ; leur miroir
C est dans [`../apple2c/`](../apple2c/) (`apple2game.h`, `apple2dos.h`).

**Inclure après les appelants.** Les primitives historiques sont entourées de `.ifref` : une routine
n'est assemblée que si le code qui précède l'include la référence. Les jeux
mettent donc les `.include` en fin de source (LOGO, qui exporte `wait_key` vers
un autre module, aussi). Un objet C qui aliase une routine vers un import
(`hgr_init = _hgr_init`) la saute (`.ifndef`), voir `../hgrc/hgr_mode_clear_asm.s`.

## Routines

| Routine | Module | Entrée | Sortie | Écrase | ZP |
|---|---|---|---|---|---|
| `print_str_ax` | `print.asm` | A=lo, X=hi (ASCIIZ) | — | A, Y | `print_ptr_*` |
| `print_byte_dec` | `print_num.asm` | A = octet | "DDD" | A, X | — |
| `wait_key` | `kbd.asm` | — | A = touche & $7F, majuscule | A | — |
| `poll_key` | `kbd.asm` | — | A = touche ou 0, Z à jour | A | — |
| `kbd_upcase` | `kbd.asm` | A = touche | A = majuscule, Z/N à jour | A | — |
| `delay_ms_a` | `delay.asm` | A = ms (0 → 256) | — | A, X, Y | — |
| `hgr_init` | `hgr.asm` | — | GRAPHICS + HIRES + PAGE1 + plein écran | A | — |
| `hgr_init_clear` | `hgr.asm` | — | idem, page 1 effacée avant la bascule (`HGR_CLEAR_ROUTINE` pour la remplacer) | A, X, Y | — |
| `hgr_page1` / `hgr_page2` | `hgr.asm` | — | page affichée | A | — |
| `text_restore` | `hgr.asm` | — | TEXT + plein écran + PAGE1 | A | — |
| `native_video` | `hgr.asm` | — | IIe/IIc (ROM `$FBB3` = `$06`) : RAMRD/RAMWRT principaux, 80STORE, 80COL et DHGR coupés ; appelée par `hgr_init`, `hgr_init_clear` et `text_restore` | A | — |
| `apple2_zp_save` | `exit.asm` | — | copie $00-$FF (256 o de BSS, ou `apple2_zp_buf` défini par le programme avant l'include), RESET → `apple2_exit` | A, X | — |
| `apple2_exit` | `exit.asm` | — | vecteur RESET et ZP restaurés (fenêtre texte et curseur `$20-$29` gardés), écran texte, `JMP $03D0` | tout | — |
| `apple2_return` | `exit.asm` | — | même restauration, puis `RTS` vers le `CALL` BASIC (programme lancé par `BLOAD` + `CALL`) | tout | — |
| `tone` | `sound.asm` | A = bascules (0 → 256), X = demi-période (0 → 256) ; ~(13 + 5·X) cycles par bascule | — | A, X, Y | — |
| `read_stick` | `joy.asm` | — | `joy_x`, `joy_y` = 0 (gauche / haut) … ~60 (centre) … ~120 ; ~6 ms ; C = 1 si rien n'est branché (valeurs centrées) | A, X, Y | — |
| `stick_dir` | `joy.asm` | `joy_x`, `joy_y` | A = `JOY_NONE` (0, Z = 1) / `JOY_UP` / `JOY_DOWN` / `JOY_LEFT` / `JOY_RIGHT` ; zone morte `JOY_LO`–`JOY_HI` (30–90, à définir avant l'include pour changer) ; la verticale l'emporte | A | — |
| `dos_cmd_new` | `dos.asm` | — | tampon de commande vide | A | — |
| `dos_cmd_add` | `dos.asm` | A = lo, Y = hi (ASCIIZ) | chaîne ajoutée | A, X, Y | — |
| `dos_cmd_hex` | `dos.asm` | A = octet | deux chiffres hexadécimaux ajoutés | A, X | — |
| `dos_cmd_run` | `dos.asm` | tampon | DOS exécute la commande, page zéro de DOS remise pendant ce temps | tout | — |
| `disk_protected` | `dos.asm` | — | C = 1 si la disquette du slot 6 est protégée en écriture | A | — |

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
| `STORE80OFF/ON` `RAMRDOFF` `RAMWRTOFF` `COL80OFF/ON` `DHIRES_ON/OFF` | `$C000-$C00D`, `$C05E-$C05F` | commutateurs IIe/IIc (DHGR, `native_video`) |
| `KC_LEFT` `KC_RIGHT` `KC_UP` `KC_DOWN` `KC_RET` `KC_ESC` `KC_SPACE` | 7 bits | codes rendus par `kbd.asm` |

Les codes de touches ont le préfixe `KC_` exprès : les jeux ont souvent leurs
propres `KEY_*`.

## Page zéro

Sur l'Apple II, la page zéro appartient au Moniteur (`$20-$4F`), à DOS et à Applesoft (`$50-$FF`) : le
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
le programme, DOS conservant toujours son instantané complet. La longueur doit
valoir 1 à 256 et la plage rester dans `$00–$FF` ; l'assembleur rejette les
configurations invalides. Une erreur DOS (fichier
absent…) arrête le programme au prompt : le `Makefile` met sur la disquette
tous les fichiers lus, et `disk_protected` est testé avant d'écrire. MICRO-SOKOBAN
s'en sert pour ses paquets de niveaux (`BLOAD`), `MICROSAVE` et `MICROHOF`.

`DOS_CMD_MAX` règle la taille du tampon de commande (40 octets par défaut).
`dos_cmd_run` conserve le tampon et sa longueur : on peut répéter la commande
ou lui ajouter du texte et des chiffres hexadécimaux après son exécution.
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

Auteur : VERHILLE Arnaud. Licence : [GPL-3.0](../../../LICENSE).

## RGB Le Chat Mauve / Video-7

[`rgb.asm`](rgb.asm), extrait des routines vidéo d’A2FileCmd, arme le registre
COL140 par deux impulsions AN3 avec 80COL à 1. Les routines sont autonomes,
sans page zéro ni copie du framebuffer ; les inclure après les appelants.

- `rgb_col140` : sur IIe/c, arme COL140 et DHGR sans changer la page affichée,
  le mode texte/graphique, MIXED ou les banques RAM. À appeler après
  l’initialisation DHGR existante. Retour A=1, X=0 ; sur II/II+, A=0 et aucun
  commutateur n’est touché.
- `rgb_hgr` : HGR page 1, plein écran, banques principales sur IIe/c.
  Fonctionne aussi sur II/II+. Ne vide pas l’écran.
- `rgb_dhgr` : DHGR couleur page 1, plein écran, banques principales,
  80STORE désactivé. L’appelant vérifie la présence de RAM auxiliaire étendue
  avant cet appel. Sur II/II+, renvoie A=0 sans changer la vidéo.

Les entrées de mode renvoient A=1, X=0 en cas de succès. Toutes écrasent A et
X ; Y et le masque IRQ sont préservés. Code et pile doivent être en banque
principale. Programmer le registre RGB à l’entrée du mode, sans répéter les
impulsions lors des changements de page ou de MIXED. La sortie vers le texte
reste assurée par `text_restore` / `dhgr_text_restore`.

## Mockingboard : deux AY et timer par scrutation

[`mockingboard.asm`](mockingboard.asm) extrait la détection de carte et les
accès AY d’A2FileCmd (`src/mb_probe.s`, helpers de `src/plugins/duet.s`).
Il utilise uniquement des instructions 6502, trois octets de page zéro
(`mb_ptr`, `mb_probe_old`, chacun peut être aliasé), et un petit état résident.
Il ne dépend ni du gestionnaire de fichiers, ni d’un lecteur musical.

| Entrée | Contrat |
|---|---|
| `mb_detect` | Cherche dans les slots 7..1, sauf 3 ; initialise les deux AY ; A=slot ou 0. |
| `mb_init` | A=slot 1..7 sauf 3 ; initialise les directions VIA et remet les deux AY à zéro ; A=slot ou 0 si invalide. |
| `mb_write` | X=registre AY 0..15, A=valeur ; `mb_chip` sélectionne la première (0) ou seconde (1) puce. |
| `mb_silence` | Met les trois volumes à zéro sur les deux AY ; conserve `mb_chip`. |
| `mb_timer_start` | A=octet bas, X=octet haut de la valeur de rechargement T1. Timer libre, IRQ T1 masquée. |
| `mb_tick` | A=1 si une expiration est observée et acquittée ; sinon A=0. Aucun blocage. |
| `mb_stop` | Coupe les six voix, désactive la scrutation, restaure ACR et le bit d’autorisation IRQ T1 sauvegardés. |

`mb_init` choisit la première puce. Les opérations avant initialisation ou
après une détection sans carte sont inoffensives. Un registre hors 0..15 est
ignoré. Les valeurs de retour se testent dans A (`CMP #0`), sans supposer la
valeur du drapeau Z. Toutes les entrées peuvent écraser A/X/Y ; les transactions
matérielles conservent le masque IRQ. Appeler avec D=0, code/pile/ZP principaux
et ROM visible. Aucune commutation de banque langage ou auxiliaire n’est faite.

Le programme doit posséder les deux AY et le timer T1 de la première VIA :
aucun autre lecteur ou gestionnaire IRQ ne doit les utiliser simultanément.
Une nouvelle détection ou une initialisation avec un slot valide restaure
automatiquement le timer précédent et coupe ses voix avant de recommencer.
Un slot invalide conserve la session courante. Appeler `mb_stop` avant de
quitter. Le compteur et la période antérieurs du timer ne sont pas restaurés ;
les expirations manquées se regroupent dans le drapeau IFR. Les autres bits
IER ne sont pas modifiés par le service de scrutation.

Sur //c, la détection réveille la Mockingboard 4c à `$C403`. Ce réveil peut
masquer la ROM souris du slot 4 : détecter la Mockingboard **avant** d’initialiser
la souris. Le module fournit les accès matériels ; aucun lecteur PT3 n’est lié.

```asm
        JSR mb_detect
        CMP #0
        BEQ sans_carte
        LDX #7                  ; mélangeur : canaux tonaux actifs, bruit coupé
        LDA #$38
        JSR mb_write
        LDX #8                  ; volume de la voix A
        LDA #8
        JSR mb_write
        ; Programmer aussi les registres 0/1 de période de la voix A.
        ; ...
        JSR mb_stop             ; avant de rendre la main
sans_carte:
        ; ...
.include "mockingboard.asm"
```

`make test-hardware` exécute les modules ASM sur le cœur 6502 avec un bus
RGB/VIA/AY simulé et trace les accès : ordre des impulsions RGB, chemins
II+/IIe/IIc, slots, absence de carte, réveil 4c, deux AY, six volumes,
masque IRQ et état du timer. Les essais sur cartes physiques restent à faire.

## Extension PT3 : faisabilité et périmètre proposé

Le support musical PT3 peut être ajouté comme module optionnel, sans coût
pour les jeux qui ne le lient pas. Le matériel est déjà couvert par
`mockingboard.asm`, mais **le dépôt ne contient pas encore de décodeur PT3**.
La base à privilégier après examen d'A2FileCmd est son **port ca65 corrigé
du lecteur de GROUiK / French Touch** (`src/plugins/ppt3/`), traduction du
lecteur ZX de S.V. Bulba avec les générateurs de tables d'Ivan Roshin,
publiée sous GPL-3.0-or-later. A2FileCmd conserve l'original ACME, teste
l'identité du port non adapté, sépare le décodage des écritures AY et ajoute
des contrôles de lectures, de pile, de durée des flux de commandes ainsi que
des corrections de fréquences. Son bilan documenté compare 400 morceaux
sur 3 000 ticks : 394 donnent les mêmes registres que son pt3_lib corrigé,
avec six différences expliquées ; ce résultat ne démontre pas un gain CPU.

Ne pas copier son pilote AUX tel quel : son trampoline force LORES, masque
les IRQ pendant le décodage et place le moteur à AUX `$2000`, le morceau à
AUX `$4000`. Ces zones appartiennent aux pages DHGR de nos jeux. Prévoir une
implantation main RAM ou AUX hors vidéo, déplacer les constantes et mesurer
le coût des protections. Son image actuelle coûte 4 813 octets plus 613
octets de variables/tables, hors morceau et pilote. Cela rend le choix de
GROUiK pertinent pour réutiliser l'adaptation déjà testée, sans présumer
qu'il est plus petit ou plus rapide. Vince Weaver reste une alternative.

Le [lecteur de Vince Weaver](https://github.com/deater/dos33fsprogs/tree/1871fc43b57cc8cf4b2353ae115d0ca84a1a33ea/music/pt3_lib)
est une base ca65/6502 : son décodeur produit les registres AY séparément
de leur écriture matérielle. Sa licence propose 0BSD ou GPL-2.0-only ;
retenir l'option 0BSD pour une adaptation dans ce dépôt GPL-3.0.

Architecture proposée : un décodeur singleton avec initialisation d'un
morceau résident, décodage d'un tick, pause/reprise, boucle et arrêt ; des
wrappers cc65 ; puis une sortie AY utilisant le backend existant. Le registre
d'enveloppe R13 ne doit pas être réécrit lorsque le décodeur renvoie `$FF` :
ce marqueur conserve l'enveloppe en cours. Le lecteur amont duplique trois
voix sur les deux AY ; cela ne fournit pas six voix indépendantes.

Le [README amont](https://github.com/deater/dos33fsprogs/blob/1871fc43b57cc8cf4b2353ae115d0ca84a1a33ea/music/pt3_lib/README.pt3_lib)
annonce environ 3 Ko plus le morceau, 26 octets ZP et typiquement 10–15 %
du CPU à 50 Hz. Ce sont des estimations amont, pas des mesures dans nos jeux.
Il exige un morceau aligné sur 256 octets et comporte du code auto-modifié.
Ses adresses ZP fixes devront devenir des allocations ld65 ; son adresse
de morceau compilée devra être adaptée à l'API choisie. La conversion de
fréquences AY Spectrum/Mockingboard et la cadence musicale doivent être
explicites : un tick musical 50 Hz ne doit pas dépendre des FPS du jeu.

Conserver les IRQ sous responsabilité de l'application, comme la cadence
existante. Ne pas importer les installations IRQ, patches de slot ou
contournements ROM //c du lecteur amont. La scrutation `mb_tick` peut servir
à un premier exemple, mais fusionne les expirations manquées. Pour une
musique régulière en jeu, le lecteur devra utiliser un scratch dédié,
préserver le contexte interrompu et partager les timers avec la cadence et
la souris selon une politique explicite. Les appels graphiques restent hors IRQ.

Avant intégration dans un jeu : mesurer les cycles maximaux par tick, la ZP,
les deux piles et la place du morceau dans le map ld65 ; comparer les trames
AY à une référence et tester fin/boucle/pause, R13, absence de carte, sortie
DOS/ProDOS et interruptions pendant le rendu DHGR. Le test actuel
`test_game_cadence.py` valide un service AY simple pendant le jeu, sans
démontrer le budget CPU d'un décodeur PT3. Commencer par un exemple autonome
II+/IIe avant de choisir un jeu et d'ajouter le chemin //c.
