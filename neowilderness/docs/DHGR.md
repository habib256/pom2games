# Neowilderness — paysage DHGR (lot 3)

Ce document fixe les choix du rendu DHGR : contraintes matérielles, palette,
disposition de l’écran, format des sprites, primitives 6502 mesurées et plan de
portage de `src/wild.s`. **État : le jeu dessine désormais son paysage en
DHGR** (`src/dhgr.s`, § 10) ; les sections 1 à 9 décrivent la préparation et
le banc indépendant (`dhgr.mk`, `build/dhgr/`), toujours testés. Les écarts
entre le plan et l’intégration sont résumés au § 10.

| Fichier | Rôle |
|---|---|
| `tools/dhgr_palette.py` | 16 couleurs, octets TN #3, RGB mesurés sur POM2, humeurs et leur choix |
| `tools/dhgr_ref.py` | trame DHGR de référence (deux banques de 8 Kio) et aperçu PNG ; oracle des tests du jeu |
| `tools/forest_ref.py` | houppiers de `src/forest.s` (extrait de `test_forest.reference`) |
| `tools/gendhgr.py` | tables résidentes du jeu (`build/dhgr_tables.inc`) |
| `src/dhgr.s` | passes DHGR du jeu, humeur de la trame, texte 40 colonnes, modes vidéo |
| `tools/dhgr_sprites.py` | conversion des 5 sprites originaux, 4 échelles, PNG |
| `src/dhgr_cols.s` | primitives 6502 : effacement, colonnes, bandes, groupes, tampons |
| `src/dhgr_test.s`, `src/dhgr_test.cfg` | banc IIe autonome piloté par script (ProDOS) |
| `src/dhgr_boot.s`, `src/dhgr_boot.cfg` | `NEODHGR.SYSTEM`, chargeur SYS ProDOS du banc |
| `tests/test_dhgr_ref.py` | contrôles Python purs (palette, octets, sprites, géométrie) |
| `tests/test_dhgr_cols.py` | primitives exécutées sur le cœur POM2 IIe, octet par octet |

```sh
make -f dhgr.mk            # ../dist/NEODHGR_TEST.po (ProDOS) + variante page 2
make -f dhgr.mk test       # tests Python puis IIe (a2shot --iie, macOS)
make -f dhgr.mk refs       # captures build/dhgr/ref_*.png et palette.png
make -f dhgr.mk run        # démonstration dans POM2 (préréglage IIe)
```

### Disque de démonstration ProDOS

`../dist/NEODHGR_TEST.po` (ProDOS 8 2.4.3, 280 blocs, volume `/NEODHGR`)
contient `PRODOS`, `NEODHGR.SYSTEM` (SYS, `$2000`), `DHGRTEST` (le banc, BIN
`$7400`), `SCENE` et `MOOD0`..`MOOD9` (scripts, BIN `$4000`). Au démarrage,
ProDOS lance `NEODHGR.SYSTEM`, qui se recopie en `$0800`, refuse un ][/][+,
fixe le préfixe sur le volume d’amorce (ON_LINE + SET_PREFIX) et charge
`DHGRTEST` puis `SCENE` à l’adresse de leur type auxiliaire (GET_FILE_INFO,
OPEN, READ, CLOSE) avant de sauter dans le banc. Le banc prend la mémoire
auxiliaire avec `dev/lib/prodos/video.s` (politique DISCARD : `/RAM` est
reformaté à la sortie), affiche l’heure dorée, puis chaque touche charge
l’humeur suivante (nom et seuils sur les lignes 80 colonnes) ; ESC ou Q
rétablit le texte 40 colonnes, les banques principales, `80STORE` et `AN3`,
reconstruit `/RAM` et appelle MLI QUIT (sélecteur Bitsy Bye). Aucun élément
DOS 3.3. `make -f dhgr.mk run` le démarre dans POM2 (préréglage IIe) ;
`tests/test_dhgr_cols.py` démarre aussi chaque test sur une image `.po`
construite à la volée et vérifie les 10 humeurs du disque octet par octet.

`build/dhgr/` est hors Git : carte régénérée (`mkmap.py --seed 1985
--level 4`, identique à `build/map.bin`), sprites convertis, binaires, captures.

## 1. Contraintes DHGR qui comptent

- **Mémoire.** Une page = 8 Kio principaux + 8 Kio auxiliaires à
  `$2000-$3FFF`, mêmes adresses de lignes que la HGR (`hgr_offset`). Une ligne
  = 80 octets entrelacés : aux 0, main 0, aux 1, main 1… soit 40 octets par
  banque. Seuls les 7 bits faibles sont affichés ; le bit 7 est ignoré et
  toujours écrit à 0 ici.
- **Pixels couleur.** 560 points par ligne, regroupés en 140 pixels de 4 bits.
  Le pixel `x` occupe les bits `4(x mod 7)` à `+3` du groupe `x / 7` de 28 bits
  (4 octets : aux pair, main pair, aux impair, main impair). La couleur LORES
  `c` s’écrit `rot(c) = (c >> 1 | c << 3) & 15`, bit 0 à gauche, comme
  `dev/lib/hgrc/dhgr_pattern.c` et la note technique IIe n° 3.
- **Une colonne = au plus un octet par banque.** Les phases `x mod 7` = 0, 2,
  4, 6 tiennent dans un seul octet ; 1, 3, 5 chevauchent un octet aux et un
  octet main. Une colonne isolée exige donc une lecture-modification-écriture
  (RMW) dans une ou deux banques : en moyenne 10/7 = 1,43 passe par ligne.
- **Écritures groupées.** Sept colonnes = 4 octets entiers : écrits sans
  lecture (STA seul), ils évitent tout masquage. C’est l’unité naturelle du
  rendu : une rotation de 22,5° (35 rayons) = 5 groupes = 10 octets par
  banque, exactement le décalage HGR actuel (10 octets).
- **Franges.** En DHGR, la couleur d’un pixel ne dépend plus de sa parité ni du
  bit de palette : plus d’incompatibilité violet/vert ou bleu/orange dans un
  même octet. Les transitions entre couleurs restent visibles sur un moniteur
  composite (artefacts NTSC sur 1 à 2 points de 560), mais aucune règle de
  placement n’est nécessaire. Le vrai coût est l’alignement par octets.
- **Commutateurs.** DHGR = `TXTCLR`, `HIRES`, `80COL` (`$C00D`), `AN3` à 0
  (`$C05E`). Avec `80STORE` et `HIRES` actifs, `PAGE2` (`$C055`/`$C054`)
  choisit la banque de `$2000-$3FFF` **et** de `$0400-$07FF` pour le CPU, sans
  changer la page affichée ; le code, la pile et les tables restent en
  mémoire principale, et le code automodifié fonctionne. `RAMRD`/`RAMWRT`
  basculent au contraire tout `$0200-$BFFF` : avec `RAMRD`, le code lui-même
  serait lu en auxiliaire.

### Convention retenue

Page 1, `80STORE` actif pendant tout le jeu (c’est aussi l’état attendu par le
firmware 80 colonnes), banque choisie par `PAGE2`. Chaque passe auxiliaire
tourne avec les IRQ masquées (`PHP/SEI … PLP`) : un gestionnaire verrait
sinon l’auxiliaire à `$0400-$07FF/$2000-$3FFF`. Les primitives entrent et
sortent avec la banque principale ; `dc_save_bank`/`dc_restore_bank`
préservent l’état d’un appelant qui aurait sélectionné l’auxiliaire.

La bibliothèque `dev/lib/hgrc` suppose `80STORE` inactif et écrit par
`RAMWRT` : pour l’appeler (texte DHGR, sprites masqués, effacement), encadrer
l’appel de `STA $C000` / `STA $C001`, comme le fait l’opération `$05` du banc.

La page 2 (`DHGR_BASE = $4000`) est assemblable : `80STORE` ne bascule pas
`$4000`, donc `RAMRD`+`RAMWRT` sont activés ensemble et le segment `DCROWS`
doit être recopié à la même adresse en auxiliaire (`dc_mirror`). Elle est
testée mais **déconseillée** : en mode mixte, la page 2 affiche le texte de la
page 2 (`$0800-$0BFF`), et les tampons de colonnes ne peuvent pas être lus
sous `RAMRD`.

## 2. Palette réelle

RGB relevés sur le rendu POM2 (`tests/test_dhgr_cols.py` les revérifie à chaque
exécution). Les octets sont ceux d’une couleur unie : aux pair, main pair,
aux impair, main impair.

| n° | Couleur | rot | Octets | RGB POM2 |
|---:|---|---|---|---|
| 0 | noir | 0000 | 00 00 00 00 | 0,0,0 |
| 1 | magenta | 1000 | 08 11 22 44 | 167,11,64 |
| 2 | bleu foncé | 0001 | 11 22 44 08 | 64,28,247 |
| 3 | violet | 1001 | 19 33 66 4C | 230,40,255 |
| 4 | vert foncé | 0010 | 22 44 08 11 | 0,116,64 |
| 5 | gris 1 | 1010 | 2A 55 2A 55 | 128,128,128 |
| 6 | bleu moyen | 0011 | 33 66 4C 19 | 25,144,255 |
| 7 | bleu clair | 1011 | 3B 77 6E 5D | 191,156,255 |
| 8 | brun | 0100 | 44 08 11 22 | 64,99,0 |
| 9 | orange | 1100 | 4C 19 33 66 | 230,111,0 |
| 10 | gris 2 | 0101 | 55 2A 55 2A | 128,128,128 |
| 11 | rose | 1101 | 5D 3B 77 6E | 255,139,191 |
| 12 | vert | 0110 | 66 4C 19 33 | 25,215,0 |
| 13 | jaune | 1110 | 6E 5D 3B 77 | 191,227,8 |
| 14 | aigue-marine | 0111 | 77 6E 5D 3B | 88,244,191 |
| 15 | blanc | 1111 | 7F 7F 7F 7F | 255,255,255 |

Les deux gris sont identiques sur POM2 (et très proches sur machine) : il y a
en pratique 15 teintes. `build/dhgr/palette.png` et `pom2_palette.png`
(capture réelle de 16 barres) les montrent.

## 3. Ce que le moteur HGR encode, et les humeurs DHGR

`tools/view_ref.py` (et `render` de `wild.s`) n’encode **ni pente ni
distance** : chaque échantillon visible du rayon peint la bande entre sa ligne
et le sommet précédent dans une couleur fixe selon la cellule — eau
(bit 7) violet, neige (niveau ≥ `MAP+11`) blanc, sinon vert — et laisse sa
propre ligne noire (la crête). Le ciel violet remplit le reste, noir la nuit.
Les forêts (`forest.s`) peignent en noir un houppier à pointillé vert une
ligne sur deux (`(ligne ^ cx) & 1`), tronc noir. Le soleil et la lune sont des
disques blancs (`sky_outer`, phases `sky_inner`), dessinés seulement sur le
ciel restant. Les sprites ont 4 codes (noir, violet, vert, blanc). La nuit est
binaire : `view_dark = 0` seulement si la phase vaut 11 (disque plein).

Le DHGR garde exactement ces bandes. Il ajoute deux informations déjà
disponibles : la distance `n` de l’échantillon (pas de rayon 1..128 ;
`n` + 127 dans `wild.s`), en trois paliers — proche `n ≤ 16`, moyen `n ≤ 48`,
lointain au-delà —, et une **humeur** choisie une fois par trame.

### 3.1 Humeurs : choix une fois par trame

Unité d’altitude **S8** = `round(128 × sin(altitude))`, soit `sky_up × 128`
(`sky_up` est déjà calculé par `sky_position`). `phase` = l’échantillon de
forme lunaire 0..11 de `sky_lunar` (11 = disque plein), `clouds` =
`weather_sky ≠ 0`. Comparaisons entières seulement
(`dhgr_palette.select_mood`) :

| Soleil S8 | Degrés | Clair | Couvert |
|---|---|---|---|
| ≥ 22 | ≥ 10° | `day` | `overcast` |
| 4..21 | 2°..10° | `golden` (heure dorée) | `overcast dusk` |
| −2..3 | −1°..2° | `sunset` (lever/coucher) | `overcast dusk` |
| −13..−3 | −6°..−1° | `civil` (crépuscule civil) | `nautical` |
| −27..−14 | −12°..−6° | `nautical` | `nautical` |
| < −27 | < −12° | nuit, selon la lumière lunaire | idem |

Dans le jeu, la règle HGR `view_dark` (seul le disque plein éclaire la nuit)
reste prioritaire, parce que la logique en dépend (préparation des sprites,
message « trop sombre », état `scene_cache_*` comparé à la référence HGR) :
`view_dark = 1` donne `night dark`. La gradation ci-dessous s’applique donc à
la pleine Lune (haute, basse, voilée, sous l’horizon) ; les gibbeuses restent
noires tant que la règle HGR n’est pas levée.

Lumière lunaire `L` = 0 si la Lune est sous l’horizon (S8 ≤ 0), sinon
`phase`, −2 si la Lune est basse (S8 < 22, sous 10°), −3 sous les nuages,
plancher 0. `L ≥ 9` → `night bright`, `L ≥ 6` → `night dim`, sinon
`night dark`. Ainsi la pleine lune haute (11) ou basse (9) éclaire, la
pleine lune voilée (8) ou un gros gibbeux (6..8) donne un paysage faible,
une demi-lune (5) laisse la nuit noire — la règle HGR « pleine lune =
paysage visible, sinon noir sauf la lune » est conservée aux extrémités et
graduée entre les deux. `night dark` remplace `view_dark` : terrain, bois et
sprites noirs, seule la lune est dessinée. Le disque lunaire est blanc, jaune
pâle sous 10° (S8 < 22). Les nuages masquent toujours soleil et lune.

### 3.2 Tables

Chaque humeur est une table de 19 entrées indexée par type de bande : ciel
(zénith, milieu, horizon), sol, neige, eau (3 paliers chacun), crête,
contour, tronc, houppier (lignes impaires/paires), soleil, ombrage des
sprites. Une entrée est une couleur ou une **paire tramée** `a/b` (damier :
`a` si ligne + colonne paire). En assembleur : un octet `a << 4 | b` (`a = b`
pour une couleur unie), donc une seule consultation par segment. Le ciel est
découpé aux lignes logiques 32, 48, 72 et 84 : zénith, trame
zénith/milieu, milieu, trame milieu/horizon, horizon (aussi sous l’horizon
quand on regarde vers le bas) — au plus cinq segments tramés, sans gabarit.
L’ombrage des sprites remplace la couleur de jour par une table de 16
octets : jour, chaud, silhouette (noir), lune, sombre ; `null` = masqués.
L'animal présent fait exception depuis le 15 octobre 2026
([LOOK_UPDOWN.md](LOOK_UPDOWN.md) § 4) : sous les nuances silhouette et
sombre et sans nuance (nuit noire), il prend une **silhouette de nuit**
lisible, le code 0 (noir de jour) en bleu foncé et les trois autres en
gris 1 (`dhgr_palette.Lighting.animal`, `src/project.s module_animal`) ;
les sites gardent la règle des sprites.

Taille résidente : 10 humeurs × 19 octets + 5 tables d’ombrage × 16 =
**270 octets** (`dhgr_palette.mood_table()`, vérifié ≤ 300 par le test).
Aucun asset par humeur, tout se calcule en RAM au changement d’humeur.

| Humeur | Ciel zénith · milieu · horizon | Sol proche · moyen · loin | Neige | Eau | Tronc ; houppier | Soleil | Sprites |
|---|---|---|---|---|---|---|---|
| day | bleu m. · bleu m. · bleu cl. | vert · vert f. · bleu f. | blanc · blanc · gris | aigue · bleu m. · bleu f. | brun ; vert, vert f. | jaune | jour |
| overcast | gris · gris · gris/bleu cl. | vert f. · vert f. · gris | gris · gris · gris/bleu f. | gris · bleu f. · bleu f. | brun ; vert f., noir | – | jour |
| golden | bleu m. · bleu cl. · rose/jaune | orange/brun · brun/magenta · violet | rose · rose · violet | orange/rose · rose/bleu cl. · violet | noir ; brun, vert f. | orange | chaud |
| sunset | violet · rose · orange | brun · magenta · violet | rose · rose · violet | orange · rose/orange · violet | noir ; noir, noir | magenta | silhouette |
| overcast dusk | bleu f. · gris · gris/rose | brun · bleu f. · bleu f. | gris · violet · bleu f. | gris · bleu f. · bleu f. | noir ; noir, noir | – | chaud |
| civil | bleu f. · violet · rose | bleu f./noir · noir · noir | bleu cl. · violet · bleu f. | rose · violet · bleu f. | noir ; noir, noir | magenta | silhouette |
| nautical | noir · noir/bleu f. · bleu f. | noir · noir · noir | bleu f. · bleu f./noir · noir | bleu f./noir · noir · noir | noir ; noir, noir | – | sombre |
| night bright | noir · noir · noir/bleu f. | vert f. · vert f./bleu f. · bleu f. | gris · bleu cl. · bleu f. | bleu f./blanc · bleu f. · bleu f. | noir ; vert f., noir | – | lune |
| night dim | noir · noir · noir | bleu f./noir · noir · noir | gris/noir · bleu f. · noir | noir/bleu f. · noir · noir | noir ; noir, noir | – | sombre |
| night dark | bleu f. · bleu f. · bleu f. | noir · noir · noir | noir · noir · noir | noir · noir · noir | noir ; noir, noir | – | masqués |

Partis pris :

- **Jour** : ciel bleu moyen, horizon bleu clair tramé ; perspective
  atmosphérique, les crêtes lointaines virent au bleu foncé, la neige
  lointaine au gris, l’eau d’aigue-marine à bleu foncé.
- **Couvert** : gris uniforme, trame gris/bleu clair à l’horizon ; sol vert
  foncé, lointains gris, eau grise.
- **Heure dorée** : horizon rose/jaune tramé (pêche), sol proche orange/brun
  tramé, moyen brun/magenta, lointains violets (alpenglow), neige rose, eau
  qui reflète le ciel (orange/rose puis rose/bleu clair) ; soleil orange.
- **Coucher** : ciel violet → rose → orange, sol brun → rouge (magenta) →
  violet, arbres et sprites en silhouettes noires, soleil rouge (magenta).
- **Crépuscule civil** : ciel bleu foncé → violet → rose, sol presque noir
  (trame bleu foncé/noir au premier plan), eau rose ; nautique : ciel noir
  tramé de bleu, seuls neige et eau proches ressortent.
- **Nuit claire** : ciel noir, lueur bleue tramée à l’horizon, sol vert
  foncé → bleu foncé, neige grise, reflet de lune (trame bleu foncé/blanc)
  sur l’eau proche ; nuit faible : trame bleu foncé/noir au premier plan,
  le reste noir.

Le « bleu foncé » (64,28,247) est vif sur POM2 : la nuit l’emploie surtout en
trame avec le noir. Les sprites passent par l’ombrage (épave blanche → gris à
la lune, bleu foncé la nuit faible). Couleurs de jour des sprites, codes
noir/violet/vert/blanc :

| Asset | Couleurs DHGR |
|---|---|
| épave | noir, magenta, vert, blanc |
| ours | noir, brun, brun, gris |
| puma | noir, brun, orange, jaune |
| crotale | noir, brun, jaune, blanc |
| cabane | noir, brun, vert foncé, jaune |

HUD : cadre et encre blancs, fond noir, index jaune, dans toutes les humeurs.

### 3.3 Variables moteur à ajouter

`sky_position` ne calcule aujourd’hui qu’**un** astre (le soleil le jour, la
Lune quand `night = 1`), et ses flottants vivent dans le tampon texte de DOS.
L’humeur demande, recalculés avec l’heure (pas par trame) :

| Variable proposée | Contenu | Origine |
|---|---|---|
| `sun_alt8` (signé) | `round(128 × sky_up)` du soleil, **même la nuit** | `sky_position` sans la branche lune |
| `moon_alt8` (signé) | idem pour la Lune (après parallaxe) | `sky_position` branche lune, aussi le jour/au crépuscule |
| `moon_phase` | `sky_sample` 0..11 de `sky_lunar` (aujourd’hui temporaire) | `sky_lunar` |
| `sky_mood` | 0..9, ordre de `dhgr_palette.MOODS` | `select_mood` (entiers) |

`weather_sky` et `sky_waxing` existent déjà. `view_dark` devient
`sky_mood = night dark`. Le choix de l’astre dessiné (`night`) reste celui
du moteur ; au crépuscule la Lune n’est pas dessinée tant que `night = 0`.

## 4. Disposition de l’écran (rangées 0..191)

| Rangées physiques | Contenu |
|---|---|
| 0..15 | HUD : ruban de boussole colonnes 45..94, panneaux de survie (lot 4) |
| 16..159 | vue, lignes logiques 16..159 |
| 160..175 | cache des lignes logiques 0..15 (terrain sous le HUD), comme en HGR |
| 176..191 | inutilisées, noires (couvertes par le texte) |

On garde le **mode mixte** : les rangées 160..191 ne sont jamais affichées,
donc le cache 160..175 et la convention de `scroll` restent valables, dans les
deux banques. Afficher le terrain jusqu’à 191 obligerait à dessiner le texte
dans le graphisme (voir ci-dessous) et à déplacer le cache.

Ruban de boussole proposé : bande cyclique de 140 pixels couleur (4 unités
d’azimut par pixel), lettres de la petite police DHGR de `dev/lib/hgrc`
(`dhgr_small_font.inc`, 4×5), index jaune colonne 70. Les 48 pixels intérieurs
couvrent 192 unités (196 en HGR). **Retenu au lot 3 :** le ruban et les
panneaux HGR existants, chaque pixel HGR doublé (§ 10), et l’index jaune ;
la refonte en couleur appartient au lot 4.

### Texte en mode mixte : 40 ou 80 colonnes ?

Le DHGR impose `80COL` : en mode mixte, les quatre lignes du bas sont du
**texte 80 colonnes** (colonnes paires en auxiliaire, impaires en principal à
`$0650/$06D0/$0750/$07D0`, écrites via `PAGE2` sous `80STORE`). Un texte 40
colonnes natif n’est pas possible en même temps que la DHGR ; les solutions
de remplacement (caractère + espace, ou police dessinée dans le graphisme)
coûtent de la place ou des cycles et perdent la netteté.

Recommandation de la préparation : **80 colonnes** pour les 4 lignes de
messages. **Retenu au lot 3 :** texte 40 colonnes inchangé, dont chaque
caractère occupe la cellule 80 colonnes impaire (§ 10). Elles
contiennent deux messages de 40 caractères par ligne, ou des messages plus
longs sans coupure ; le firmware 80 colonnes de l’IIe/IIc (COUT avec
`80STORE`) s’en charge directement. La capture `build/dhgr/pom2_demo_mixed80.png`
montre la vue DHGR avec 80 colonnes, une ligne espacée façon 40 colonnes et
une invite. POM2 affiche le texte sans franges ; sur un moniteur couleur
composite, le signal de chrominance reste actif en mode mixte et le texte
80 colonnes peut se franger : à vérifier sur machine.

## 5. Format des sprites DHGR

Le moteur dessine une seule vue par asset (aucune variante de cap ni
d’animation) ; la distance choisit une échelle 2^-shift, shift 0..3, avec la
règle de `sprites.s`/`scene_ref.py` : colonne réduite `j` = colonne originale
`j << shift`, lignes gardées si `(base − y) mod 2^shift = 0`. Les quatre
échelles sont précalculées à la construction (`build/dhgr/sprites/NOM_sS.bin`
+ `.png` ×2 horizontalement + `manifest.json`).

```
0  'D' 'S' 1     signature, version
3  largeur        colonnes couleur (= rayons) de cette échelle
4  hauteur        plus grand « up » + 1
5  shift          0..3
6  base           ligne opaque la plus basse de l’image originale
7  origin         relèvement local : 0 épave, 10 autres
8  offsets        (largeur + 1) mots LE ; colonne c = [off[c], off[c+1])
   segments       2 octets : up_haut, (longueur − 1) << 4 | couleur
                  (longueur 1..16, segments plus longs découpés), de haut en bas
```

Les lignes absentes sont transparentes : les segments forment le masque.
Placement : billboard lointain ligne = `ancre − up` ; local (profondeur 0)
ligne = `base − origin − up`.

### 5.1 Taille sur disque et en RAM

| Forme | Octets (5 assets) | Avec le codec `pack_overlay` |
|---|---:|---:|
| Segments DHGR, 4 échelles | 11 720 | 9 775 |
| Segments DHGR, échelle 0 seule | 8 208 | 6 304 |
| Flux originaux 2 bits (`original_graphics`) | 4 838 | 3 618 |

Recommandation pour une disquette ProDOS unique : **garder sur disque les
flux originaux** (3 618 octets compressés, déjà décodés colonne par colonne
par `sprite_column`) et 4 octets de couleurs par asset (20 octets) ; la
couleur DHGR est `ombrage[humeur][SPRITES[asset][code]]`, et la réduction
d’échelle reste celle du moteur. Le format de segments ci-dessus sert de
référence Python (`dhgr_ref`) et d’option si la décompression par colonne
devient trop lente ; ne charger alors que l’échelle 0 de l’asset courant
(au plus 2 762 octets, épave) et réduire en RAM.

## 6. Primitives 6502 (`src/dhgr_cols.s`)

Options d’assemblage : `DHGR_BASE` (`$2000` défaut, ou `$4000`), `DC_ROWS`
(192 ; 176 suffisent au jeu), `DC_GROUP_MIN` (4). Paramètres en page zéro
(27 octets), tous exportés.

| Routine | Effet |
|---|---|
| `dc_clear` | A = couleur : remplit les deux banques entières (trous compris) |
| `dc_vspan` | colonne `dc_x`, lignes `dc_y0..dc_y1−1`, couleur `dc_c`, RMW |
| `dc_band` | colonnes `dc_x..dc_x1−1` entre deux profils (`dc_top`, `dc_bot`) ; groupes de 7 colonnes alignés écrits en octets entiers, bords en `dc_vspan` |
| `dc_group` | lignes `dc_y0..dc_y1−1` du groupe `dc_g`, couleur `dc_c` : 4 passes STA |
| `dc_bspan` | tampon de colonne `dc_x` (0..6) du groupe `dc_g` : lignes = couleur ou paire tramée `a << 4 \| b` (page 1) |
| `dc_flush` | groupe `dc_g`, lignes `dc_y0..dc_y1−1`, depuis les 7 tampons (page 1) |
| `dc_save_bank` / `dc_restore_bank` | état de banque d’un appelant |
| `dc_mirror` | page 2 : recopie `DCROWS` en auxiliaire |

Mise en œuvre : code de lignes déroulé (`LDA ligne,Y / AND / ORA / STA
ligne,Y`, 10 octets, 15 cycles ; ou `STA ligne,Y`, 5 cycles) dans lequel un
`RTS` est posé à la ligne de fin, comme `span_rows` de `wild.s`. En page 1 un
même `RTS` sert aux deux banques. Tables par colonne générées à
l’assemblage ; tables de lignes de `dc_flush` par la macro `dhgr_row_tables`
de `dev/lib/hgrc/dhgr_layout.inc`.

Réutilisé de `dev/` : `dhgr_layout.inc` (adresses de lignes), le codage
des couleurs de `dhgr_pattern.c` et la table TN #3 de `dev/tests/test_dhgr.py`
(vérifiés par les tests), la petite police `dhgr_small_font.inc` (HUD de la
référence), `hgr_tables.hgr_offset`, `a2test`/`a2shot`, et
`dhgr_clear_asm.s`, lié dans le banc pour comparaison. Les primitives de
lignes, rectangles et sprites de `hgrc` ne conviennent pas au moteur : elles
supposent `80STORE` inactif et lisent l’auxiliaire par un trampoline en page
zéro (environ 25 cycles par octet), sans code automodifié possible sous
`RAMWRT`.

Taille (page 1, 192 lignes) : `DCCODE` 2 273 octets (dont 1 120 de tables de
colonnes et le code des tampons), `DCROWS` 3 634 octets (code déroulé et
tables), `DCBSS` 1 344 octets (7 tampons de 192 lignes).

### Coûts mesurés (POM2 IIe, cycles CPU)

Mesures `pcprof` d’a2shot entre deux points d’arrêt, en ne comptant que les
PC du code des primitives (l’interprète de script du banc est exclu ; il est
indiqué entre parenthèses quand il compte).

| Opération | Cycles |
|---|---:|
| `dc_clear`, deux banques (16 Kio) | 85 860 |
| `dhgr_clear_asm` de `dev/lib/hgrc`, même travail | 187 117 |
| `dc_vspan`, page 1 | 170 par appel + 15 par ligne et par banque (21,4 en moyenne) |
| `dc_group`, 20 groupes × 101 lignes | 50 700 (3,6 par pixel et ligne) |
| `dc_flush`, 20 groupes × 192 lignes | ≈ 595 300 (155 par ligne et groupe) |

Trames complètes de `dhgr_ref` (192 lignes, HUD compris), page effacée au
préalable, octets identiques à la référence. « Tampons » = `dc_bspan`
(segments unis ou tramés) ; `dc_flush` sur 192 lignes :

| Scène (humeur) | Segments | Spans par colonne | Zénith en bande + spans | Tampons + `dc_flush` |
|---|---:|---:|---:|---:|
| jour, soleil, épave | 3 199 | 953 153 | 940 458 | 588 511 + 595 736 |
| heure dorée, cap +140 | 12 026 | — | — | 611 961 + 595 329 |
| nuit claire, cap +280 | 1 764 | 581 725 | 618 513 | 403 146 + 595 334 |
| nuit faible, cap +140 | 3 391 | 659 416 | 694 849 | 178 935 + 595 344 |

Lecture : à 1 MHz, peindre une vue par spans coûte 0,6 à 1 s hors lancer de
rayons, dominé par le coût par appel. **Les trames rendent les spans
inutilisables** : une ligne tramée est un appel par ligne (12 026 segments à
l’heure dorée, script de 36 Ko non exécuté). Le tampon de colonne absorbe la
trame sans surcoût (une paire par segment) et `dc_flush` a un coût fixe
(≈ 496 000 cycles pour les 160 lignes 16..175). Le chemin retenu pour le
moteur est donc tampon + `dc_flush`. Pistes chiffrées :

1. écrire les couleurs (ou paires) dans le tampon directement depuis la
   boucle de rayons (code déroulé `STA tampon+ligne`, 5 cycles par ligne,
   deux points d’entrée pour la trame), puis `dc_flush` : ≈ 112 000 +
   496 000 cycles ;
2. `dc_flush` déroulé par ligne (adresses d’écran en opérandes absolus) :
   ≈ 105 cycles par ligne et groupe, soit ≈ 340 000 cycles ;
3. variante OR seule de `dc_vspan` (12 au lieu de 15 cycles par ligne et
   banque) pour les tracés isolés.

La variante page 2 est vérifiée octet par octet mais pas chronométrée.
La trame HGR n’a pas pu être profilée pendant ce lot : le disque
`NEOWILDERNESS.dsk` et `build/wild.lbl` étaient en cours de reconstruction
par un autre chantier.

## 7. Référence Python (`tools/dhgr_ref.py`)

La géométrie n’est pas recopiée. `terrain_events` remplace temporairement
`SKY/GROUND/SNOWC/WATER/RIDGE` de `view_ref` par des sondes : `render` les lit
au moment de peindre, et chaque sonde relève colonne, lignes et `n` dans les
cadres d’appel. Les arbres viennent de `tests/test_forest.reference` (crochets
`max`/`min` sur deux lignes précises), les billboards de
`tests/scene_ref.select/foreground` ; ces deux modules sont importés avec un
`common` minimal pour ne pas dépendre de `build/wild.lbl`.

`tests/test_dhgr_ref.py` vérifie qu’avec les codes HGR comme palette, la
référence DHGR reproduit **au bit près** (lignes 16..159) `view_ref.render`,
`scene_ref.render` et `test_forest.reference` sur 14 vues (départ, cabane,
positions aléatoires) et 12 scènes de faune : la palette ne peut pas masquer
une régression de projection.

Ordre de composition (celui du 6502) : bandes de terrain et ciel, sprite au-
dessus de sa ligne de front, astre sur le ciel restant hors pixels de sprite,
houppiers par-dessus sauf sous un sprite plus proche. Simplification
documentée : l’astre est rogné au sommet du terrain après `scene_trim`, sans
modéliser les lignes de ciel situées entre deux parties d’un sprite.

### Refactor proposé de `view_ref.py`

1. Extraire `columns(m, px, py, heading)` qui renvoie, par colonne, la liste
   ordonnée `(kind, r0, r1, n, cellule)` ; `render` ne fait plus que peindre
   ces événements. `dhgr_ref.terrain_events` deviendrait un simple appel et
   les sondes disparaîtraient.
2. Déplacer le calcul d’arbre de `tests/test_forest.reference` dans
   `tools/forest_ref.py` (`tree_column(...) -> (début, fin, cx, fin_houppier,
   n)`) ; le test et `dhgr_ref` l’importent.
3. Placer `select/foreground` de `scene_ref` dans `tools/` et un
   `sky_ref.py` avec `body_spans` (disque, phases) partagé par les tests HGR
   et DHGR, qui n’ont aujourd’hui aucun oracle Python du dessin des astres.

## 8. Plan de portage de `src/wild.s`

1. **Mode et mémoire** (après le lot 1) : réserver `$2000-$3FFF` dans les deux
   banques ; à l’entrée de la vue, `TXTCLR`, `MIXSET`, `HIRES`, `80COL`,
   `$C05E`, `80STORE` ; garder `PAGE2` inactif hors primitives.
2. **Couleurs** : remplacer `C_SKY/C_GROUND/C_SNOW/C_WATER/C_RIDGE` par
   l’octet de la table de l’humeur (`sky_mood`, § 3.3) au palier de `n`, dans
   `render_col`, `render_sky` et `sky_span` ; `view_dark` → `night dark`.
3. **Premier rendu exact par spans** : remplacer `column_masks`, `span`,
   `fill`, `span_rows`, `span_lo/hi` par `dc_vspan` (rangées logiques 0..15
   envoyées en 160..175 par l’appelant, comme `view_row`). `clear_rows`
   devient un effacement des octets des groupes concernés dans les deux
   banques, ou disparaît si chaque ligne 16..175 est peinte.
4. **`scroll`** : même boucle, exécutée deux fois (`$C054` puis `$C055`),
   `shift` = 10 octets par banque pour 35 rayons, 20 pour 70.
5. **Sprites** : `sprite_column` lit les segments DHGR (`dhgr_sprites`) au
   lieu de décoder le flux original ; `sprite_rows` garde $FF = transparent
   et reçoit des couleurs 0..15 ; `scene_emit/scene_span/scene_trim`
   inchangés hors couleur.
6. **Forêts** : `forest_paint` écrit contour/houppier/tronc (palette
   `TREE`) au lieu de manipuler `be/bo/me/mo`.
7. **Astres** : `sky_column` prend la couleur du soleil dans l’humeur, la
   Lune blanche ou jaune pâle selon `moon_alt8` ; ciel en cinq zones tramées.
8. **HUD** : `hud_draw`/`view_row` portés sur le ruban DHGR (lot 4 pour les
   panneaux). `HUD_ROWS` et le cache 160..175 restent.
9. **Tampon + `dc_flush`** : nécessaire dès que les trames sont utilisées
   (§ 6) ; une rotation de 35 rayons = 5 groupes entiers.

### Adapter `tests/test_view.py`

- Remplacer `view_rows(page)` par un relevé des deux banques : `peek:2000:8192`,
  `poke:C055:00`, `peek:2000:8192`, `poke:C054:00` (lecture auxiliaire par
  `PAGE2` sous `80STORE`, sans relancer le CPU entre les deux pokes).
- Comparer les rangées physiques 16..175 de `dhgr_ref.encode(dhgr_ref.frame(
  m, px, py, h, sky, animal))` (ou `decode` des banques contre
  `frame(...)` pour signaler le premier pixel faux en coordonnées couleur).
- Garder les assertions de cap et l’ordre de révélation : les colonnes en
  attente sont noires dans les deux banques ; avec `dc_flush`, l’unité de
  révélation devient le groupe de 7 colonnes.
- La concordance géométrique avec HGR reste couverte en Python par
  `tests/test_dhgr_ref.py` (palette de codes HGR), sans émulateur.

## 9. Captures de référence (`build/dhgr/`, hors Git)

- `ref_mood_<humeur>.png` et `ref_mood_<humeur>_east.png` : les 10 humeurs,
  vue de départ et vue vers l’est (page entière 280×192) ;
- `ref_woods_{day,golden,sunset,night_bright}.png`, `ref_cougar_golden`,
  `ref_cougar_moonlit`, `ref_cabin`, `ref_bear`, `ref_cougar`,
  `ref_rattlesnake` (`*_visible` : rangées 0..159) — `make -f dhgr.mk refs` ;
- rendu POM2 des trames peintes par `dc_bspan` + `dc_flush`
  (`tests/test_dhgr_cols.py --shots`) : `pom2_day`, `pom2_golden_hour`,
  `pom2_moonlit_bright`, `pom2_moonlit_dim` ;
- jeu réel (`python3 tools/game_shots.py`, lot 3) : `game_crash_day`,
  `game_turn_right`, `game_look_left`, `game_after_status`,
  `game_after_topo` (et `game_topo_hgr`, TOPO lui-même), `game_golden`,
  `game_sunset`, `game_civil`, `game_dawn_nautical`, `game_night_full_moon`,
  `game_night_full_moon_back`, `game_night_moon_disk` (pleine Lune levée à
  l’est), `game_woods_noon`, `game_woods_golden` ;
- `pom2_palette.png`, `pom2_demo_mixed80.png` (heure dorée + texte
  80 colonnes), `pom2_mood_<humeur>.png` (les 10 humeurs du disque de
  démonstration, relevées en le parcourant au clavier), `palette.png`,
  `sprites/*.png`.

## 10. Intégration au jeu (lot 3)

Le moteur `src/wild.s` garde sa projection, ses 140 rayons et l’ordre de
composition ; seules les écritures d’écran changent (`src/dhgr.s`).

**Passes.** Une colonne = un pixel couleur. `column_setup` calcule, une fois
par colonne, l’octet et le masque de la partie A (et B si le pixel chevauche
aux/main), les banques et la ligne de `dc_pat` (TN #3), et les inscrit dans
`dspan` (code automodifié). `dspan` (lignes Y..`sp_end`−1, entrée de
l’humeur `a << 4 | b`) plante un RTS dans `drows` (160 lignes logiques
déroulées, `LDA ligne,Y / AND dm / ORA dv0|dv1 / STA ligne,Y`, 15 cycles) et
fait une passe par banque. Les lignes paires utilisent `dv0`, les impaires
`dv1` : **une trame coûte autant qu’un aplat**, sans tampon de colonnes ni
`dc_flush`. Les lignes logiques 0–15 sont déroulées directement sur les
rangées physiques 160–175 (cache). Le terrain est effacé avant la passe ; les
crêtes restent noires comme en HGR.

**Trame ancrée au monde.** La phase du damier est `(ligne + azimut du
rayon)` et non la colonne d’écran : une rotation de 35 rayons (nombre
impair) fait défiler des pixels tramés qui restent exacts, et la trame ne
scintille pas pendant un panoramique. `dhgr_ref.dither_column` reproduit la
règle.

**Choix des couleurs.** `dhgr_frame` (une fois par trame) choisit l’humeur
(`select_mood`), recopie ses 19 entrées, calcule les cinq zones du ciel
(zénith, trame, milieu, trame, horizon), la couleur de l’astre (soleil de
l’humeur ; Lune blanche, jaune pâle sous 10°) et les couleurs des sprites
(`dhgr_assets` × ombrage de l’humeur). Bande de terrain : une consultation
par segment (type de cellule + palier de distance `n`). Bois : contour,
houppier tramé `(ligne ^ x cellule)`, tronc, en trois bandes sous le masque
d’un sprite plus proche. Sprites : flux originaux 2 bits inchangés,
`scene_emit` traduit le code 0..3 en couleur ombrée.

**Altitudes.** `sky_position` (résident) appelle la routine SIM
(`sky_position_core`), puis convertit `sky_up` (flottant ROM) en
`round(128 sin h)` par décalages entiers, sans toucher FAC/ARG ni `$A4`.
Le moteur ne calcule qu’un astre : `sun_alt8` le jour, `moon_alt8` et
`moon_phase` la nuit (l’autre vaut `$80`). De jour, le soleil sous −12°
donne `nautical` (jamais `night`). Ces variables sont nouvelles dans GDATA :
`test_reference_state.py` ne compare que les noms communs aux deux builds.

**Bandeau et panneaux.** Le ruban HGR (`hud_draw`) et les panneaux
(`module_summary`) écrivent toujours des octets HGR monochromes ; `dbl_put`
double chaque pixel (octet HGR y → aux y, main y). Encre blanche où deux
pixels sont allumés, franges bleues/orange ailleurs, comme les franges HGR ;
`tools/dhgr_ref.hud_banks` en est le modèle exact. L’index de la boussole est
un triangle jaune (lignes 11–13).

**Texte mixte.** Sous DHGR, les quatre lignes du bas sont du texte
80 colonnes. Or `COUT1` du IIe enhanced teste `RD80VID` (`$FC46 BIT $C01F`)
et passe alors en mise en page 80 colonnes (caractères répartis entre les
banques, `CH` réinterprété) ; `HOME`, `SCROLL`, `CLREOL` passent par le
micrologiciel interne. Le jeu installe donc dans `CSW` sa propre sortie
40 colonnes (`t_cout`) et appelle ses propres `t_vtab`, `t_home`,
`t_clreol`, `t_clreop` : la page texte principale garde exactement la
disposition 40 colonnes (tests, simulation et écrans inchangés), les
cellules paires (page auxiliaire, lignes 20–23) reçoivent des espaces à
chaque `show_dhgr`. Chaque caractère est affiché dans la cellule impaire :
texte fin, espacé, lisible. Un vrai texte 80 colonnes aurait demandé de
réécrire toutes les sorties du jeu, et il ne reste que 128 octets libres.

**Modes.** `show_dhgr` (vue : `80COL`, AN3 bas, `HIRES`, `MIXSET`,
`TXTCLR`), `show_text` (menus, rideau, MAP : `80COL` bas, `TXTSET`),
`show_hgr` (TOPO, HGR simple, AN3 haut). Au retour de TOPO la vue complète
est redessinée (TOPO a écrasé la moitié principale) ; MAP et les menus ne
touchent que la page texte : la vue revient sans redessin. QUIT et RESET
passent par `prodos_text` (`80STORE`, `80COL`, AN3 rétablis).

**Coûts mesurés** (cycles POM2, `tools/profile_actions.py --profile`,
`docs/BASELINE_DHGR.json`) contre la version HGR 128 Ko :

| Commande | HGR 128 Ko | DHGR | Écart |
|---|---:|---:|---:|
| VIEW (crash, épave) | 5,644 s | 5,845 s | +3,6 % |
| LOOK R | 1,847 s | 1,927 s | +4,3 % |
| LOOK B | 2,419 s | 2,490 s | +3,0 % |
| flèche droite (22,5°) | 1,058 s | 1,107 s | +4,6 % |
| flèche gauche (22,5°) | 0,794 s | 0,837 s | +5,4 % |
| STATUS | 0,241 s | 0,239 s | −0,8 % |
| WALK 1 H | 9,097 s | 9,300 s | +2,2 % |

Les états de simulation des sept commandes sont identiques à la version HGR
128 Ko. Le surcoût vient des deux banques : défilement de 2 × 30 octets par
ligne pour 22,5° (bandes de huit lignes de même octet bas, huit `LDA/STA
abs,X` modifiés par bande et une seule fois pour les deux banques :
86 400 cycles), effacement d'une vue complète des deux banques en 84 000
cycles (sous les 100 000 de l'effacement HGR d'une banque, même technique),
bandeau doublé (≈ 35 000 cycles). La passe `dspan` coûte à peu près le
`span`/`fill` HGR. Le chemin tampons + `dc_flush` du banc aurait ajouté
≈ 500 000 cycles par vue complète (`dc_flush` seul) et 7 Ko.

Premières mesures, avant optimisation des deux banques : flèche droite
1,324 s (+25 %), gauche 1,038 s (+31 %), LOOK R 2,149 s (+16 %), VIEW
6,011 s (+6,5 %). Les gains : défilement par bandes (−16 % sur une flèche),
un seul tracé du bandeau par trame au lieu de deux, lignes 2–9 du bandeau
non effacées avant leur copie, effacement par bandes.

## 11. Interface DHGR (lot 4)

**Bandeau (rangées 0..15).** Trois zones alignées sur les groupes d’octets
(7 pixels couleur = aux 2g, main 2g, aux 2g+1, main 2g+1) : panneau gauche
groupes 0..6 (pixels 0..48), ruban de boussole groupes 7..12 (49..90),
panneau droit groupes 13..19 (91..139). Chaque rangée est composée dans
`line_pix` (une couleur par pixel, `overlay_text + 96`, libre hors de la
boucle des rayons) puis emballée par **octets entiers** (`dhgr_pack`,
résident : un groupe uni est écrit directement depuis `dc_pat`, sinon chaque
pixel ajoute ses bits par les tables de phase). Aucune lecture-modification-
écriture, aucun doublage de pixels HGR : plus de franges.

**Ruban** (`src/hud.s`, résident). Bande cyclique de 140 colonnes
(`tools/genhud.py`, 4 unités d’azimut par pixel, nord magnétique en colonne
0) : bits 0..6 = rangées 1..7 des lettres, bit 7 = graduation (toutes les
8,75 colonnes). 42 colonnes visibles (168 unités, ±54°) autour du pointeur
fixe du pixel 70. Fond bleu foncé (2), lettres et graduations blanches,
pointeur jaune (rangées 11..13, sur noir). Une lettre ou une graduation
de couleur d’un pixel de large frange sur un écran composite et dans POM2
(le nord orange puis jaune a été essayé et écarté : rose/noir autour du N) ;
seul le blanc (4 points allumés) reste net sur le bleu. Coût : ≈ 23 000
cycles par trame (35 000 pour le ruban doublé du lot 3).

**Police** (`tools/dhgr_font.py`). 7 rangées, largeur 0 (espace) à 5 pixels
couleur, avance = largeur + 1 : un pixel couleur vaut 1,83 rangée en
largeur, une lettre de 3 × 7 a les proportions d’une majuscule ordinaire.
Les 13 caractères d’un champ tiennent dans 49 pixels (les libellés les plus
longs, « ENTER SHELTER », « NEW CONDITION », « HUNGER BETTER »,
« WATER LOW:INV », mesurent exactement 49 pixels).

**Panneaux** (`module_summary`, WILDHUD). Quatre champs de 8 rangées
(glyphe 0..6, fond 7) : à gauche la santé (`HEALTH 100%`) puis l'alerte ou
l'indication ; à droite l'heure et le jour du séjour (`7:00 DAY 1`, jour de
l'année de STATUS moins 125, plus 365 au passage de l'an : le crash du 6 mai
est le jour 1) puis le besoin le plus pressant, faim ou soif (`HUNGER OKAY`,
`THIRST SO-SO` ; la faim à égalité). Le panneau droit commence 4 pixels après
le ruban (`UI_GAP`, 45 pixels utiles : « NIGHT DAY 123 » en fait 43). Fond
noir ; libellés gris (10), heure et jour blancs ; valeurs bonnes aqua (14), moyennes
jaunes (13) ; **avertissements en blanc sur une bande rouge** (magenta 1,
la cellule et son interstice, un pixel de marge à gauche) au lieu de
l’inverse HGR ; reprises en aqua ; indications en bleu clair (7) ; repos /
aide en gris. Les encres ont 3 ou 4 points allumés par pixel : le vert (12)
et l’orange (9), à deux points, donnent des traits fins et cassés sur
composite (mesuré dans POM2 : « OKAY » vert illisible). Un caractère du
crochet COUT rejoint un tampon de champ (glyphe, largeur, encre, fond) ;
`field_flush` compose les 8 rangées et emballe 7 groupes par rangée.
`tools/dhgr_ui.py` est le modèle (rendu et lecture des champs, utilisé par
`test_interface.py` et `test_clock.py`).

**Texte 80 colonnes.** Les quatre lignes mixtes sont du vrai texte 80
colonnes (colonnes paires en page auxiliaire, impaires en principale,
`PAGE2` sous `80STORE`) : primitives du jeu dans `$0200-$03CF` (`t_update`
différentiel, `t_cout`, `t_scroll` des deux pages, `t_clear_row`,
`clear_to` octet par octet), choisies par `text80` (bit 7) et la largeur
`WNDWDTH`. Le rideau de la simulation et MAP sont aussi en 80 colonnes ;
STATUS, INVENTORY, HELP et la fin gardent 40 colonnes (`text_mode40`) :
glyphes deux fois plus larges, mêmes 24 lignes (un passage en 80 colonnes
n’ajoute aucune ligne, seulement de la largeur), mises en page et tests
inchangés. Les messages restent formatés pour 38 colonnes ; la ligne en
accepte 79 (dernière colonne réservée), pour les messages plus longs du plan
d’ergonomie. MAP : une cellule = deux caractères 80 colonnes (carrée à
l’écran), le symbole doublé, sites et joueur en une seule lettre inverse suivie du symbole de terrain de
leur case.
POM2 affiche ce texte sans franges ; sur composite couleur, le texte 80
colonnes peut se franger (à voir sur machine).

**TOPO** (`src/topo_dhgr.s`, module TOPOGEN dans la fenêtre SIM,
[TOPO_DHGR.md](TOPO_DHGR.md)) : feuille DHGR calculée à l’ouverture,
identique au bit près à `tools/topo_dhgr_ref.sheet` ; elle balaie la vue de
haut en bas (plus d’effacement ni de rideau) ; légende dans les quatre
lignes 80 colonnes ; instantané de la vue en carte langage auxiliaire pour
le retour (MEMORY.md § 8.4).

**Modes.** `show_dhgr` (vue et TOPO), `show_text` (80 colonnes si `text80`,
sinon 40) ; `show_hgr` (HGR simple) a disparu avec l'image TOPO.

**Coûts mesurés** (`tools/profile_actions.py`, POM2, contre
`BASELINE_DHGR.json` du lot 3) : voir `docs/BASELINE_DHGR.json` (clé
`lot4`) et le tableau de `CHANGELOG.md`.

## 12. Palettes par région (lot 7, étape 4)

**Données.** `tools/dhgr_palette.REGIONS` donne, pour chaque région et
chaque humeur, les entrées qui remplacent celles de la Sierra Nevada
(`MOOD`) : sol (trois paliers de distance), neige, eau, couronnes des arbres.
Le ciel (cinq zones), le Soleil, la crête (jamais peinte : `render_ridge`
garde le noir effacé), les contours, les troncs, les ombrages des sprites,
les deux crépuscules (sol déjà noir) et les quatre humeurs de nuit restent
ceux de `MOOD` dans toutes les régions. La région 2 est `MOOD` lui-même.
`dhgr_palette.mood(nom, région)` fusionne les deux.

| Région | Intention | Humeurs modifiées |
|---|---|---|
| 1 British Columbia | forêt boréale : épicéas sombres, lointain gris, neige basse bleutée | jour, couvert, doré, couvert du soir |
| 2 Sierra Nevada | référence du lot 3 (inchangée, empreinte vérifiée) | — |
| 3 Burma | jungle de mousson : canopée claire (vert/jaune), terre rouge, rivières boueuses | jour, couvert, doré |
| 4 New Guinea | forêt pluviale : verts profonds à reflet aqua, rivières boueuses | jour, couvert, doré |
| 5 Bolivia | altiplano : herbe ocre et paille, sommets blancs, yungas plus bas | jour, couvert, doré, coucher, couvert du soir |
| 6 Chile | Atacama à la Patagonie : sable, éboulis gris, cactus gris-vert | jour, couvert, doré, couvert du soir |

**Sprites.** `dhgr_palette.SPRITES` reçoit les couleurs de jour des 15
nouveaux animaux (codes 0 à 3 de chaque sprite original : grizzly, loup,
élan, tigre, éléphant, cobra, python, Dani, vipère, crocodile, puma,
jaguar, fer-de-lance, anaconda, chat des Andes) ; l'ombrage de l'humeur
s'applique par-dessus comme pour la Sierra. `REGION_ANIMALS` donne le
sprite de chaque fiche (modules 6, 7, 8, puis 23 pour la quatrième espèce) ;
`region_assets(r)` les six entrées de `dhgr_assets` (épave, espèces 1-3,
cabane, espèce 4).

**Tables.** `tools/gendhgr.py --regions build/dhgr` écrit
`dhgr_tables_rN.bin` (314 octets : 10 humeurs × 19 entrées et 5 tables
d'ombrage de 16 octets, soit 270, puis 44 octets de couleurs des six
assets) ; le paquet `NEOWILD.Rn` les
charge sur `dhgr_moods`…`dhgr_tables_end` de WILDGAME. Les 310 premiers
octets de la Sierra sont ceux du lot 3 (`build/dhgr_tables.inc`, lié dans
WILDGAME ; `build_disk.py` vérifie l'égalité avec `dhgr_tables_r2.bin`).
`dhgr_frame` donne au module 23 la sixième entrée de `dhgr_assets`.

**Référence et tests.** `tools/dhgr_ref.Sky(region=N)` peint une vue dans
la palette d'une région ; `test_dhgr_mood.py` vérifie 124 cas par région
(humeurs, ombrages, six assets) et l'empreinte des tables Sierra ;
`test_menu.py` compare la première vue de chaque scénario à `dhgr_ref` dans
sa palette, et chaque espèce dessinée près de l'épave. Captures :
`tools/game_shots.py --regions` → `build/dhgr/game_region_rN_{start,day,golden}.png`
et `game_region_r{3,5}_species4.png`.

**Étoiles (étape 5).** Les étoiles sont des pixels unis blanc (15), jaune
(13) ou bleu clair (7) posés sur les zones de ciel noires des humeurs de
nuit ; aucune entrée de palette n'est ajoutée ([STARS.md](STARS.md)).
