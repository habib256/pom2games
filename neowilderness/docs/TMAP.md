# TMAP XL et données de scénario

Première version : 16 octobre 2026. Entrée **T** au menu de NeoWildernessXL.
Le générateur est un programme séparé exécuté avant le moteur ; les décors
et les paramètres de l'archipel sont des données de scénario.

## Utilisation

1. Dans XL, choisir **T TMAP**, puis le niveau.
2. Choisir **2** ou **3** îles (Entrée : 3).
3. Saisir une graine de un à quatre chiffres hexadécimaux, ou Entrée pour
   garder la proposition. Retour arrière corrige la saisie.
4. L'aperçu place le nord en haut : `.` mer, `#` terre basse, `^` relief.
   C'est un échantillonnage du terrain ;
   TOPO montre les côtes complètes dans le jeu.
5. Entrée lance le voyage ; **R** essaie la graine suivante ; Échap revient
   au menu. Échap fonctionne aussi aux deux questions précédentes.

Le départ est sur la première île et le poste objectif sur la dernière.
Chaque chenal a une traversée rectiligne de une à trois cases, soit deux à
six unités du monde. Le moteur conserve ses coûts de nage et de santé :
une route courte ne garantit pas la survie d'un personnage épuisé ou chargé.
WALK s'arrête à l'eau ; SWIM rejoint l'autre rive. Une bande d'au moins
quatre cases d'océan entoure les terres. Le déplacement reste limité à deux
cases avant chaque bord, comme sur les autres cartes.

## Séparation des responsabilités

| Élément | Source | Fichier XL | Rôle |
|---|---|---|---|
| Moteur | `src/wild.s` et modules | `NEOWILD.SYSTEM`, `.DAT`, `.BLK` | Rendu, déplacements, simulation, commandes |
| Scénario | `scenarios/archipelago.json`, `tools/scenario.py` | `NEOWILD.SCN` | Climat, couleurs, végétation, faune, textes, en-tête |
| Générateur | `src/tmap.s`, `src/tmap.cfg` | `NEOWILD.TMP` | Questions, carte, bois, départ et objectif, aperçu |

SCN et TMP utilisent le format de chargement existant : une table de
256 octets puis les données de ses enregistrements. TMP est chargé brut à
`$2000`, dans la future page graphique, avant la préparation du voyage.
Il ne consomme aucune place résidente pendant la partie. Il rend la main
au chargeur ; ce n'est pas un SYSTEM lancé directement depuis ProDOS.

Le paquet SCN reprend la disposition du stock New Guinea et ses filtres
de ressources. Il remplace textes, climat de l'en-tête, palettes et profils
d'arbres. `animals: []` supprime les quatre taux de rencontre des grands
animaux ; poissons et petit gibier restent les ressources du moteur.
Les emplacements des anciens sprites sont réservés mais jamais rencontrés.
La création de fiches et de sprites animaux supplémentaires reste à faire.
L'identifiant technique de région reste 4 ; le voyage est libre, non classé.

Les profils prototypes des cocotiers restent dans le manifeste mais sont
**désactivés**, à la demande de l'utilisateur après examen du rendu.
`decor.enabled: false` produit une couverture boisée vide et l'indicateur
de forêt nul : aucun arbre sur les îles. Si un décor est activé, ses deux
profils de seize demi-colonnes et sa séparation feuillage/tronc sont des
données, repliées par le rendu existant. Chaque paquet classique XL rétablit
son décor et ses tables, y compris après une annulation de TMAP.

Le manifeste est une première version : seul le générateur d'archipel,
une faune de rencontre vide et l'objectif existant « rejoindre le poste »
sont implémentés. Les autres types de mission restent à développer.

## Carte et eau

TMAP produit directement la grille résidente 112 × 84, deux unités du monde
par case. Les îles ont un intérieur connexe, un relief arrondi et des côtes
variables. Le relief a été renforcé après demande utilisateur : pas de
quatre niveaux, sommets à 53 (trois îles) ou 61 niveaux (deux îles), au lieu
des huit niveaux du prototype. Les bois occupent les 294 octets habituels,
laissés à zéro. L'atlas fin 224 × 168 n'est pas employé en v1.

L'en-tête garde sa signature `W`. L'octet 1 contient la version dans les
sept bits bas (1) ; son bit 7 active le fond marin. Les cartes classiques
restent `W,1`, les archipels sont `W,$81`. Le fond utilise la couleur d'eau
lointaine sous l'horizon, même au-delà des limites des rayons et de la
carte. Il respecte les silhouettes des îles, les sprites et LOOK UP/DOWN ;
les limites de déplacement ne changent pas. Sur les cartes non natives :

| Octets | Contenu |
|---|---|
| 48–49 | Signature `TG` |
| 50, bit 7 | Eau de niveau zéro salée, exclue des sources de boisson |
| 51 | Version du générateur : 1 |
| 52–53 | Graine 16 bits, petit-boutiste |
| 54 | Nombre d'îles : 2 ou 3 |
| 55 | Niveau sélectionné |
| 56 | Décalage du relief : 2 signifie un pas de quatre niveaux |

Le bit de salinité vient du scénario. Les cartes classiques le laissent à
zéro. Les cartes natives utilisent déjà 40–63 pour les vêtements : elles
ne doivent pas recevoir ces métadonnées ; RESTORE les traite séparément.
TMAP v1 ne crée pas de source ni de lac. Pluie, condensation, provisions et
recherche d'eau restent disponibles. Pas de collecte d'eau salée ni de
dessalement. Une future eau douce utilisera un niveau distinct ou une
description plus précise.

## Reproductibilité et sauvegarde

Interface du programme : `$2000`, questions et génération (A/X = graine
proposée, Y = niveau), retour C=1 si annulation ; `$2003`, régénération
depuis l'en-tête. Le générateur ne touche ni au stock auxiliaire ni au
disque. Son LFSR 16 bits est indépendant du hasard de la simulation ; la
graine `0000` est acceptée.

SAVE garde déjà les 64 octets d'en-tête. RESTORE vérifie l'identité 48–55
avant de recopier l'état d'une carte non native. Un terrain différent est
refusé sans modifier le voyage. Après un redémarrage, sélectionner TMAP
avec les mêmes graine, nombre d'îles et niveau, puis RESTORE. La graine de
terrain ne fixe pas les conditions de départ du voyage libre ; RESTORE
rétablit ces dernières depuis la sauvegarde.

La carte générée n'est pas encore exportée dans un nouveau paquet de
scénario. La suite sera d'enregistrer le scénario complet pour le charger
directement, puis de généraliser faune, sites et objectifs.

## Vérification

`make` construit les deux éditions. `python3 tests/test_tmap.py` vérifie
96 archipels dans l'émulateur, deux générations identiques de chacun,
leurs îles, bords marins, sites secs et chenaux. Il joue une traversée
SWIM et vérifie absence d'arbres, relief renforcé, horizon marin à niveau
et vers le bas, salinité, SAVE/RESTORE, annulation vers la Sierra,
présence de SCN/TMP seulement sur XL et cinq sauvegardes sur les deux
éditions. Il est inclus dans `make test`.
