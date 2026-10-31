# Utilisation de dev/lib par les logiciels

Audit des neuf jeux et applications, de la disquette DEMO, des trois exemples
livrés dans `dist/`, des exemples minimaux et de la démo perspective/audio :
**15 projets utilisent des
ressources de `dev/lib`**. Les moteurs conservent aussi des routines locales.
La présence d'une bibliothèque ne signifie donc pas que tout leur rendu passe
par elle, ni que toutes les familles d'une archive sont liées dans le binaire.

| Logiciel | Ressources partagées effectivement intégrées |
|---|---|
| ARKABREAKOUT | `apple2` : HGR, clavier, joystick, son, sortie, DOS (`dos_cmd_line`) ; `hgr` : tables et texte (`hgr_puts8_at`, macro `PUTS8_AT`) ; `font` |
| MICRO-SOKOBAN | `apple2` : HGR, clavier, joystick, son, sortie, RWTS ; `hgr` : tables, pages et glyphes natifs ; sous-ensemble de `font` généré par les outils communs |
| CHESS | `apple2` : HGR, clavier, joystick (`stick_key`), son, délai, texte ; `hgr` : tables, glyphes natifs et bitmaps des pièces ; `font` |
| MAZE3D | `apple2` : HGR, joystick, son, DOS (`dos_cmd_line`), sortie et LZ4FH ; `hgr` : pages, texte, sprites compactés, lignes, spans et effacement de lignes |
| DIRTBIKE | `apple2` : HGR, clavier, manette rapide, son, musique par ticks (`tune.asm`), initiales (`ini_key`), LZ4FH, RWTS ; `hgr` : tables, texte (`hgr_puts8_at`), lignes, pages par patch ; `math` : produits, sommes, raccourcis de direction ; `physics` : points de Verlet, contraintes, sol en carte de hauteurs (`verlet*.asm`) ; `mouse` ; `font` |
| SNAKE | `hgrc` : rendu HGR, cellules, texte, nombres ; `apple2c` : entrées ; police partagée |
| PINBALL | `mouse` : pilote AppleMouse et contexte résident ; rendu et simulation historiques de Bill Budge conservés |
| LIGHT3DBALL | `hgrc`, `apple2c`, `mouse` ; `perspective` : couloir natif ; `hgr` : fil de fer et spans ; `apple2` : son ; `font` |
| CHROMABREAK | `hgrc` : DHGR et petit texte ; `apple2c` : entrées, cadence et horloge VBL (`apple2vbl`) ; `prodos` : chargeur `.SYSTEM`, relocateur SYS (`sysreloc.inc`, `SYSRELOC_DOWN_FAST`), fichiers entiers (`file.s`) ; `mouse` ; police dérivée de `font` |
| WARGALAGA II | `apple2` : duo, LZ4FH, Mockingboard, musique sous interruption (`mb_irq.asm` : ProDOS, `MB_IRQ_FRAME`, `MB_IRQ_GATE`, `MB_IRQ_SCAN`, `MB_IRQ_SPLIT`, inclus quatre fois), PT3, mémoire auxiliaire (`auxmem.asm` : `AUXMOVE`, `aux_fetch_chunked` avec `AUXMEM_FETCH_SCAN=1`, `aux_store`) ; `apple2c` : cadence et horloge VBL (`apple2vbl`, `A2_VBL_SCAN_SEI=1`) ; `prodos` : chargeur `.SYSTEM`, relocateur SYS (`sysreloc.inc`, `SYSRELOC_DOWN_FAST`), `/RAM`, fichiers entiers et `prodos_load_aux` (`file.asm`, deux fois : BOOT dans `.scope wgaux`, SHOPM) ; `mouse` ; `math` : hasard ; `font` |
| ROBOT SPACE STATION | `hgrc` : DHGR et petit texte ; `gfx` : lignes ; `apple2c` : entrées, rythme d’images (`apple2frame`), son et manette (`apple2game`), mémoire auxiliaire (`apple2aux` : `aux_store`, `aux_fetch_pages` des overlays) ; `prodos` : chargeur `.SYSTEM`, relocateur SYS (`sysreloc.inc`, `SYSRELOC_DOWN_FAST`), fichiers entiers et `prodos_load_aux` (`file_aux.s`) ; `mouse` |
| MB TRACKER | `apple2` : Mockingboard (`mockingboard.asm`, `MB_FAST_WRITE=1`), musique sous interruption (`mb_irq.asm` : ProDOS, `MB_IRQ_GATE`), lecteur AYS (`aysong.asm`, `AYSONG_CPU65C02=1`), le tout enveloppé pour le C dans `src/mbt_asm.s` ; `prodos` : chargeur `.SYSTEM`, `/RAM` (`prodos_video_claim`), MLI (`prodos_mli` : catalogue), fichiers entiers (`file.s` : `prodos_load`, `prodos_load_free`, `prodos_save`) ; outil `dev/tools/audio/aysong.py` (DEMO.AYS, oracle des tests) |
| LOGO | `apple2` : clavier, texte, HGR et sortie ; `hgr` : pixels, lignes, glyphes natifs, tables, effacement et composition des sprites ; `font` |
| DEMO | démos C : `hgrc`, `gfx` et `apple2c` selon les routines appelées ; démos assembleur : `apple2`, `hgr` et `font` |
| HELLO | parcours assembleur : `apple2` ; parcours C : `apple2c` |
| Exemple HGR | `hgrc`, `gfx`, `apple2c` et leurs noyaux assembleur |
| Exemple DHGR | `hgrc` DHGR, `gfx`, `apple2c` |
| Exemples minimaux | `hgrc`, `gfx`, `apple2c`, `prodos` selon le binaire |
| Exemple perspective/audio | `hgrc`, `gfx`, `apple2c`, `perspective`, `audio` ; disque local dans `build/` |

Les inclusions assembleur sont résolues par le compilateur, pas seulement par
une recherche de noms dans les sources. Les en-têtes C transitifs et les
sources des bibliothèques sont vérifiés de la même manière. Les cartes du
linker des programmes C permettent de distinguer les membres effectivement
extraits des archives. Aucune copie intégrale d'un fichier de code de `dev/lib`
n'a été trouvée dans les dossiers `src/` audités après retrait des commentaires.
Cette comparaison ne détecte pas toutes les variantes d'un même algorithme.

## Dépendances corrigées pendant l'audit

- CHESS déclare désormais le fichier partagé des bitmaps de ses pièces comme
  dépendance de `chess.o`. Le modifier déclenche la recompilation.
- `HGRC_HEADERS` inclut les en-têtes de `apple2c`, que `hgr.h` inclut
  transitivement. Cela couvre SNAKE, LIGHT3DBALL, CHROMABREAK et les exemples
  minimaux.
- LIGHT3DBALL déclare aussi le contrat public `mouse.h` pour son objet C.
- `APPLE2C_HEADERS` fournit la liste commune des en-têtes ; HELLO la déclare
  pour son objet C utilisant l'en-tête parapluie `apple2c.h`.

Ces corrections concernent la recompilation lors d'une modification des
ressources partagées. Elles ne remplacent pas les moteurs des logiciels.

## Mutualisations réalisées

Le nouveau noyau assembleur `hgr/hgr_glyph8.asm` fournit l'écriture brute,
la composition OR et le remplacement d'une cellule de huit pixels. CHESS
conserve son curseur et sa fenêtre ASCII ; LOGO conserve sa palette et met
à jour le fond sous les sprites ; MICRO-SOKOBAN conserve ses indices de
police, ses masques de cellules et ses titres blancs. Les captures des trois
logiciels sont identiques avant/après aux positions valides. LOGO corrige
aussi le débordement des glyphes en bas et à droite.

Mesures des seuls émetteurs sur le binaire 6502, appels inclus :

| Cas | Avant | Après |
|---|---:|---:|
| LOGO, « A », sept alignements | 5 328 cycles | 1 601–2 319 cycles |
| LOGO, espace | 1 758 cycles | 831 cycles |
| CHESS, « R », colonne 12 | 486 cycles | 476 cycles |
| MICRO-SOKOBAN, cellule dense, sept alignements | 1 175–2 359 cycles | 1 408–2 016 cycles |

Pour MICRO-SOKOBAN, la moyenne sur ces sept alignements baisse de 3,1 %,
mais les deux premiers alignements sont plus lents. Le texte agrandi et les
tuiles 14×16 conservent leurs boucles spécialisées ; leur remplacement par
un sprite générique n'est pas présenté comme un gain de vitesse.

## Mutualisations possibles

| Code local | Ressource pertinente | Adaptation à prévoir |
|---|---|---|
| Texte agrandi de MICRO-SOKOBAN | noyaux x2 de `hgrc`, police `font` | Conserver la teinte par parité et mesurer le coût des conversions ; le texte compact et les titres utilisent déjà le noyau partagé |
| Rendu des tuiles de MICRO-SOKOBAN | `hgr/hgr_sprite_packed.asm` | Tester une adaptation des tuiles 14×16, des couleurs et de la mise à jour des deux pages ; le rendu local est déjà spécialisé |
| Affichage de la police CP437 dans DEMO FONT | primitives de texte et `font` | Le texte natif actuel est limité à une fenêtre de 64 glyphes, tandis que la démo affiche les 256 caractères ; extension nécessaire |

Les règles, la physique, l'IA, les formats de sauvegarde et les scènes propres
aux jeux restent dans leurs moteurs. Pour PINBALL et le rendu DHGR spécialisé
de CHROMABREAK, un remplacement complet nécessiterait des mesures et des tests
spécifiques avant de pouvoir conclure à une amélioration.

## Reproduire la vérification

```sh
make all
make -C dev/examples/minimal
make audit-libs
# Facultatif : détail de chaque unité de compilation et de ses ressources.
python3 dev/tools/audit_lib_usage.py --json /tmp/dev-lib-usage.json
```

L'audit compile dans un dossier temporaire avec `--create-dep`, puis compare
les fichiers partagés utilisés au graphe développé de `make`. Il échoue si
un projet ne compile aucune ressource de `dev/lib`, ou si une dépendance
partagée manque dans le graphe de recompilation. Les familles compilées pour
une archive sont comptées, même si le linker n'extrait qu'une partie de leurs
membres. Les ressources générées doivent donc exister avant l'audit.
