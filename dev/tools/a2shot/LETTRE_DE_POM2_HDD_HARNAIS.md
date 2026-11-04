# À pom2games — le SDK POM2 monte les disques durs : ce qui vous revient

4 novembre 2026 — de POM2, à la suite de la demande de `pom2adventure`
(`SCOSWAMP/DOCS/LETTRE-POM2-SDK-HDD.md`).

Bonjour,

`a2shot` refusait tout volume de plus de 800 Ko, et traitait tout `.2mg` comme une
disquette de 3,5 pouces. Le SDK expose maintenant le disque dur et les primitives
qu'un banc de test demande, et `a2shot` s'en sert. POM2 est sur `main` au commit
`0d1d388e98b2268629cc65269c1aba161720585a` ; ce qui suit est commité chez vous.

## 1. Ce qui est déjà fait chez vous

Cinq fichiers, tous sous `dev/tools/a2shot/` :

| Fichier | Changement |
| --- | --- |
| `a2shot.cpp` | choix du périphérique, `--hdd[=N]`, nouvelles étapes |
| `sdk.mk`, `Makefile` | `POM2_SDK_HAS_HARNESS=1` sur macOS seulement, provenance |
| `sdk/include/pom2/core.hpp` | en-tête de POM2 à ce commit |
| `sdk/lib/darwin-arm64/libpom2_core.a` | archive de ce commit, debug retiré |

**Le choix du périphérique change.** Il se décide sur le contenu du fichier :

| Fichier | Avant | Maintenant |
| --- | --- | --- |
| `.2mg` de 800 Ko ou moins, brut de 819 200 octets | 3,5 pouces | inchangé |
| `.2mg` de plus de 800 Ko | refus du 3,5 pouces | disque dur, slot 7 |
| Brut de plus de 800 Ko | refus du Disk II | disque dur, slot 7 |
| WOZ ou MOOF de plus de 800 Ko | Disk II | inchangé |
| Tout autre fichier | Disk II | inchangé |

`--hdd[=N]` force le disque dur, quelle que soit la taille, dans le slot N. Sur un
//c, le slot est ignoré : les unités sont derrière le port arrière.

**Nouvelles étapes** (documentées en tête de `a2shot.cpp`) : `hddinfo`, `hddflush`,
`hddsave:FILE`, `hddprotect:0|1`, `text80`, `ram:BANK:ADDR[:LEN]`,
`ramset:BANK:ADDR:HEX`, `ramhash:BANK:ADDR:LEN`, `rawkey:HEX`, `keyinfo`,
`keywait:N`, `cpuset:PC[:P]`, `provenance`. `ram` lit la RAM par banque physique,
sans effet sur la machine ; `key:` fait avancer la machine, donc `press:` est
l'étape à placer avant `keywait:`.

## 2. Ce que nous avons vérifié, et ce qui ne l'est pas

Le cœur passe de `ba7f04da` à `0d1d388e`, soit 52 commits de POM2 d'un coup, en plus
du disque dur. L'en-tête ne change que par ses ajouts, mais
le comportement émulé peut changer ailleurs.

- `make -k test` depuis la racine : **code 0**, aucun échec, sur l'archive construite
  juste avant ce commit. Seule la chaîne du commit diffère dans celle-ci.
- `ctest` de POM2 : 434 tests sur 434.
- Depuis `pom2adventure`, `python3 ADVKIT/TESTS/run.py a2shot` et le banc
  `playtest.py --host a2shot` (79 scénarios, 1 133 assertions, 0 échec) passent.

**Pas vérifié :**

- `make test-long`, à lancer de votre côté : c'est là qu'un écart de cycles dû aux
  52 commits se verrait le plus.
- Linux : l'archive `linux-x86_64` reste `ba7f04da`. L'en-tête déclare des méthodes
  qu'elle n'a pas, ce qui reste sans effet tant que `POM2_SDK_HAS_HARNESS` n'y est
  pas défini. `a2shot` y compile sans ces étapes et refuse les disques durs. Sa
  compilation sous Linux n'a pas été essayée, et jusqu'à la nouvelle archive les deux
  hôtes n'exécutent pas le même cœur.
- Aucun test de `pom2games` n'exerce encore les nouvelles étapes : seuls les bancs
  de `pom2adventure` les utilisent.

## 3. Ce que nous vous demandons

Dans cet ordre :

1. Lancer `make test-long` et traiter les écarts éventuels.
2. Construire l'archive Linux : `gh workflow run pom2-core-linux.yml -f
   pom2_commit=0d1d388e98b2268629cc65269c1aba161720585a`, en mettant à jour le commit
   par défaut du workflow.
3. L'installer, puis retirer le `ifeq` de `sdk.mk` : `POM2_SDK_HAS_HARNESS=1` vaut
   alors pour les deux hôtes, et le paragraphe de provenance doit le dire.
4. Ajouter un test du côté `pom2games` : un petit volume ProDOS de plus de 800 Ko,
   amorcé, écrit, relu avec `hddsave`, et une lecture `ram:aux:` qui ne déplace ni le
   compteur de cycles ni `keyinfo`.

`tools/package_core_sdk.sh` de POM2 produit aussi, pour un hôte, une archive complète
avec un `MANIFEST.json` (commit, capacités, dépendances, empreintes). À vous de voir
si elle remplace la copie manuelle : le workflow actuel continue de fonctionner, car
le composant `pom2_core_sdk` n'a pas changé.

## 4. Ce qui ne change pas pour vous

Les étapes et options existantes gardent leur comportement, Disk II et 3,5 pouces
compris. `a2run` n'est pas concerné. Les ROM de `roms/` suffisent : le disque dur
n'en demande aucune.

Le contrat complet est dans `docs/SDK.md` de POM2 : § Hard disk, § Inspecting RAM and
the keyboard, § Rendering et § Delivery. À noter pour vos captures : `renderFrame`
reste la table composite de MAME, ni le composite OpenEmulator ni le passage CRT.

Merci.
