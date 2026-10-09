# Trois intégrations minimales

Construire depuis la racine :

```sh
make -C dev/examples/minimal
make test-minimal
make test-dhgr
```

Les fichiers restent dans `build/`, sans ajouter de disquette à `dist/`.
Les programmes sont compilés en 6502 NMOS ; aucun kernel 65C02 n'est requis.

| Image | Machine / système | Comportement |
|---|---|---|
| `build/hgr-single.dsk` | II/II+/IIe/IIc, DOS 3.3 | Une page, bande animée, compteur ; le dessin est visible pendant son exécution |
| `build/hgr-double.dsk` | II/II+/IIe/IIc, DOS 3.3 | Deux pages, dessin puis attente puis présentation |
| `build/dhgr-prodos.po` | IIe avec RAM auxiliaire vidéo compatible / IIc, ProDOS 8 | Deux pages DHGR, prise explicite de l'auxiliaire et nettoyage via `game_shutdown` |

ESC termine le programme. Le CRT DOS restaure la vidéo et la page zéro ; le
CRT ProDOS appelle `game_shutdown`, restaure son état système puis MLI QUIT.
Le chargeur `DEMO.SYSTEM` reloge son petit code à `$0800` et charge `DEMO.BIN`
à `$6000`, son adresse de liaison. Le nom de volume est résolu par ONLINE.

L'exemple ProDOS choisit **PRESERVE_RAM** : si `/RAM` est installé, il affiche
un refus en texte puis revient à ProDOS après une touche. Ce refus est attendu,
y compris pour un disque RAM vide. Pour tester l'animation, utiliser un
ProDOS sans `/RAM` installé. Le test émulé vérifie les deux chemins ; il retire
l'entrée `/RAM` uniquement dans sa machine temporaire. Une application qui
choisit `PD_VIDEO_DISCARD_RAM` assume explicitement la destruction des fichiers.

## Contrats d'intégration

Code, pile C, ZP et sources restent en RAM principale, ROM visible, D=0.
Aucune primitive de dessin n'est appelée depuis une IRQ. Les routines partagent
leur scratch cc65. Les pages vidéo ne servent pas de stockage applicatif.
HGR prépare ses tables à la demande ; `gfx_line` choisit ici le noyau ASM.
Le DHGR initialise ses capacités avant dessin et utilise des effacements de
huit lignes, qui rendent la main au programme entre les tranches.

Le HGR double tampon utilise un HUD 8×8 et, sur IIe, répartit le dessin puis
le HUD entre deux attentes VBL. Le test POM2 suit 1 000 images en NTSC et
1 000 en PAL : intervalles respectifs de 34 050..34 070 et 40 550..40 570
cycles, y compris le compteur 65535 → 0, sans rafraîchissement manqué.
Cela correspond à deux rafraîchissements par image, nominalement 30/25 FPS.
Cette répartition exige que chaque étape reste sous un rafraîchissement.
Le repli II/II+/IIc ajoute un délai au rendu ; sa cadence dépend de la charge.
Le simple tampon expose les écritures. L'exemple DHGR conserve son attente simple.

## Bilan mémoire reproductible

`build/memory.json` est calculé depuis chaque `.map`, `.lbl` et `.bin`.
Il sépare les segments liés, la ZP, la pile C réservée et les pages vidéo.
Avec le compilateur utilisé pour cette vérification :

| Exemple | Binaire | Segments main liés | ZP | Pile C réservée | Vidéo utilisée |
|---|---:|---:|---:|---:|---:|
| HGR simple | 8 152 | 9 763 | 64 | 2 048 | 8 192 |
| HGR double | 8 182 | 9 793 | 64 | 2 048 | 16 384 |
| DHGR ProDOS | 5 295 | 5 618 | 35 | 256 | 32 768 main+aux |

Les segments main comprennent le binaire résident, BSS et sauvegardes du CRT.
Le fichier HGR réserve toute la fenêtre `$2000–$5FFF`, même si le simple tampon
n'utilise que la page 1. La pile matérielle `$0100–$01FF` et la mémoire du
système hôte ne sont pas comptées dans ces colonnes. La pile réservée n'est
pas une mesure de sa profondeur réellement utilisée. Un autre cc65 peut
changer les tailles ; le JSON produit localement est la référence de la build.

Les tests contrôlent les pixels de la bande animée, les pages de dessin,
la présentation sur IIe, le retour au système et le refus de `/RAM`.
La [validation matérielle](../../lib/HARDWARE.md) reste distincte des tests émulés.

Les compteurs HGR utilisent maintenant un champ différentiel de 19 octets,
avec un historique par page. Le JSON compte aussi tous les segments de code,
y compris ONCE/INIT/LOWCODE ; la pile utilisée est mesurée séparément dans les
benchmarks, sans confondre sa profondeur observée avec sa réservation.

Les champs HGR et leurs tables sont préparés sur chaque page pendant le
chargement, avant la première frame animée. Le noyau HUD opaque évite de
lier les paramètres du texte agrandi général pour ces exemples. La banque
numérique prédécalée s’ajoute à la police générale utilisée par les titres ;
les tailles ci-dessus comprennent les deux banques.
