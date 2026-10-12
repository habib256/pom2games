# Wilderness — état de la réimplémentation

Ce document décrit le code actuel et ses limites. Les adresses et formules
de l'original sont documentées dans [ANALYSE.md](ANALYSE.md) et
[logic/ENGINE.md](logic/ENGINE.md). Le [TODO](../TODO.md) organise les travaux
restants ; le [CHANGELOG](../CHANGELOG.md) conserve l'historique des étapes.

## Fonctionnalités en place

| Domaine | Implémentation actuelle | Vérification |
|---|---|---|
| Vue | Terrain par lancer de rayons, occlusion par pente, bandes de crêtes, rotations et défilement partiel | `test_view.py`, `test_fuzz.py`, `test_play.py` |
| Commandes | 280 mots, verbe/nom/qualificatif, durées et quantités demandées séparément | `test_play.py`, `test_items.py` |
| Simulation | Date, heure, lever/coucher du soleil, air, énergie, déficits eau/nourriture/repos, santé, mort et arrivée aux rangers | `test_sim.py` |
| Médecine | 15 progressions, prérequis de soins/prévention, doses et prises orales, gestes de soin, protection vestimentaire, altitude/oxygène, état médical paginé | `test_medical.py --original`, `test_care.py --original` |
| Expositions | Compteurs sel/froid, seuils et décroissance ; soleil/neige adaptés au milieu du port | `test_exposure.py --original` (sel/froid) |
| Objets | Inventaire groupé/paginé, corps, sac, main, positions au sol, reprise au retour et quantités accessibles | `test_items.py` |
| Charge | Poids et volumes, refus atomiques, sac/gourde, capacités restantes dans INVENTORY | `test_load.py` |
| Arbres | CLIMB TREE/DOWN, HANG FOOD, sac suspendu ancré et récupération atomique | `test_tree.py`, `tools/re_tree_probe.py` |
| Retours d'action | Refus précis, quantités accessibles/réelles, excédents et capacités, durée avec cause d'arrêt, résultats persistants sans confirmation intermédiaire | `test_feedback.py` |
| Résumé et état | Heure/santé/besoins, alertes de transition, conditions prioritaires, stocks transportés et au sol | `test_interface.py`, `test_sim.py` |
| Modules disque | Fenêtre BLOAD partagée et cache, préservation de la page zéro, du texte, de HGR et de l'état | `test_overlays.py` |
| Thermique | Couches sèches/mouillées, température corporelle, récupération et facteurs de santé | `test_thermal.py`, `test_wet.py` |
| Vent et frissons | Ressenti signé, coût entier en kcal par pas, supplément des frissons | `test_wind_energy.py` |
| Immersion | SWIM : entrée depuis la berge, effort original selon le poids total, immersion, sortie sur la rive opposée ; REST dans l'eau conserve l'immersion | `test_shore.py`, `test_wet.py`, `test_swim_energy.py` |
| Sprites | Épave, cabane, ours, couguar et crotale originaux, cap, transparence, pixels noirs et clipping | `test_sprites.py` |
| Ciel | Soleil à azimut géographique et hauteur saisonnière, lune nocturne datée (extension 1985), phase stylisée, occlusion par relief/nuages et rotations | `test_sky.py` ; géométrie solaire décrite dans `logic/environment.md` |
| Composition | Terrain et sprites par colonne, arrêt conservateur des rayons masqués | `test_scene_render.py` |
| Cabane et TOPO | Entrée/sortie, protection thermique, carte textuelle et défilement | `test_sites.py`, `tools/re_site_probe.py` |
| Sites voisins | Position fixe, projection, tailles, clipping et occlusion par le relief proche | `test_projection.py`, `scene_ref.py` |
| Faune | Six critères Sierra, tirages par pas, remplacement, interruption des actions et réglage NATURE | `test_fauna.py`, `test_fauna_steps.py`, `tools/re_fauna_probe.py`, `tools/re_fauna_accept_probe.py` |
| Limites de déplacement | Marche et nage arrêtées à deux cases du bord ; temps des seuls pas acceptés | `test_boundary.py` |

Les tests de sprites valident les pixels de l'image finale, les rotations,
le départ/retour, la nuit, l'expiration des rencontres, un REST réel et
la conservation de l'image après STATUS. `test_scene_render.py` arrête le
rendu après vingt colonnes pour contrôler leur composition, puis compare
les images finales et les pas de rayons sur cinq cartes de relief différent.

## Règles provisoires et écarts

### Déplacements et consommation

Une case de marche coûte 19 minutes plus 6 par niveau gravi. Une case de
nage est divisée en deux pas d'une demi-case. La durée de chaque pas suit
la formule de nage normale de l'original selon santé, charge et diagonale :
environ 28 minutes par unité au départ pour un cap cardinal. Un dernier pas
peut dépasser la durée demandée s'il reste au moins la moitié de son coût.
Son effort utilise la formule
originale : métabolisme basal + 0,06 × poids total en livres, soit environ
14,43 kcal/min au départ. Le tracé entier des caps obliques est porté,
avec 2 880 positions identiques aux routines originales sur les 360 caps.
Les vitesses de marche, les modificateurs de blessures/équipement et la synchronisation du recalcul
de la charge restent à établir. Les pas de nage de plus de 255 minutes
ne sont pas encore pris en charge par l'interface de simulation.
Manger et boire réduisent les déficits selon les conversions actuelles :
la nourriture crédite `0,8 × kcal / poids`, l'eau 0,38 heure par once au
départ, et l'humidité des aliments contribue à l'hydratation. La conversion
d'eau varie dans l'original avec la transpiration : cette variation reste
à porter. Boire à la gourde ne prend aucun temps ; un repas dure 16 minutes,
avec métabolisme 2,31 kcal/min. Les transferts d'objets ne consomment pas
encore de temps.

REST commence par 30 minutes puis utilise le pas choisi par la santé,
jusqu'à 240 minutes. Les compteurs d'événements et les déficits ne sont
actualisés que lorsque l'intervalle accumulé atteint ce pas. Le crédit de
repos porte sur la durée demandée ; les crédits négatifs sont bornés lors
du calcul de santé. Déshydratation, faim et fatigue sont converties en
pourcentages entiers avant multiplication, comme dans T0B/S0D.

Les commandes de repos avec durée explicite (`SLEEP 8 H`, `WAIT 10 MIN`,
etc.) passent directement de l'analyse numérique au code résident, sans
charger le vocabulaire puis recharger l'analyse numérique. `SLEEP` seul
utilise également ce chemin et demande la durée. Les commandes qualifiées
conservent l'analyse complète. Sur la première scène à 1,023 MHz, un sommeil
de huit heures passe de 32,1 à 26,8 secondes et de sept à cinq lectures DOS.
La cadence de simulation et le redessin final restent identiques ; le test
`test_sleep.py` compare santé, inventaire et image à un REST avec invite.

Les tests différentiels [d'aventure](ADVENTURE_TESTS.md) vérifient ces règles
dans les deux exécutables. Les premiers compteurs concordent, mais le test
global échoue encore sur la météo et la marche. Le choix du pas ne porte
pas encore tous les plafonds météo, thermiques et pathologiques de l'original.
LOOK cardinal ajoute la déclinaison magnétique de l'en-tête ; l'erreur
aléatoire de précision de la boussole originale reste absente.

### Objets et charge

Une seule réserve au sol est conservée par aliment : si elle existe sur une
autre case, il faut la récupérer avant de déposer le stock du sac.
Les quantités affichées et consommées sont limitées à ce qui est accessible.

Le modèle additif compte tout équipement transporté ou porté, les onces
d'aliments/eau transportées et les volumes par catégorie. Les limites sont
879 oz et 2149/6000/2874 in³ pour corps/sac/main. Elles sont calibrées pour
retrouver les capacités restantes de la première partie originale :
43 oz et 1525/4134/2542 in³. Ce ne sont pas les formules originales des
conteneurs ; voir [state.md](logic/state.md#réimplémentation--charge).

Les transferts sont refusés entièrement au-delà d'une limite ou en cas de
débordement sur 16 bits. Le sac et la gourde doivent être vidés avant dépôt ;
le sac ne peut pas être rangé dans lui-même.

### Thermique

Les formules scalaires et les branches de récupération ont été comparées
aux routines originales exécutées avec la ROM Applesoft. La reconstruction
déterministe de la peau nue et de l'empilement des vêtements ne reproduit
pas tous les préréglages de départ ; le facteur original `$4BBE` / poids
reste absent. L'activation continue des conditions thermiques est simplifiée.
Les preuves et coefficients sont dans [survival.md](logic/survival.md).

Le ressenti du vent utilise un résultat signé sur 16 bits pour éviter les
retournements de signe de l'octet original. Les frissons ajoutent
0,04 × poids du joueur au coût en kcal/min du pas suivant : 6,6 pour les
165 lb de départ. Les pas consomment des kcal entières ; au repos, un pas de
30 minutes coûte 49 kcal sans frissons ou 247 avec frissons. La sueur ne
reçoit pas ce supplément.

L'air inclut l'onde lente originale `INT(5 × SIN(0,0187 × heures écoulées
+ phase))`. `s_temp_phase`, conservée en mémoire basse lors des changements
de module, reprend la sauvegarde initiale Sierra. Les calculs et l'entier
inférieur de la ROM sont comparés à T09/S08 dans 405 cas par
`test_temperature_wave.py --original`. Le cycle quotidien à trois segments
et 288 températures horaires passent `test_weather_cycle.py --original`.
Les fronts, la visibilité, les plafonds météo et le hasard ont leurs tests
ROM ; les aventures présentent encore des écarts de vent et de ressenti.

La température d'eau vaut 70 − plancher(0,3 × altitude/100) °F.
Chaque pas sélectionne immersion 2 sur l'eau, sec 0 sur terre. Aucun séchage
progressif n'est ajouté. La pluie sélectionne l'humidité ; cabane et raincoat
porté protègent de cette sélection. Abri fabriqué, feu, déclencheurs et
soins complets restent à intégrer. La cabane trouvée protège déjà du vent
et utilise l'air ambiant +15 °F ; les abris fabriqués restent à porter.

### Sites, sprites et rencontres

L'épave est ancrée à la case de départ et à son cap initial. La cabane est
placée sur une case sèche, au tiers du trajet vers les rangers ; sa présence
et son orientation sont stockées dans l'en-tête de carte. `ENTER SHELTER`
permet d'y entrer, `EXIT SHELTER` ou `LEAVE SHELTER` de ressortir, sans temps
consommé. Les commandes restent utilisables la nuit. `HUT` désigne les abris
fabriqués, encore absents.

L'état résident `shelter_inside` est conservé pendant le repos, les rotations,
STATUS, INVENTORY et TOPO. La marche et la nage sont refusées à l'intérieur.
La vue intérieure est noire avec une description textuelle ; la sortie
restitue la vue du site, ou le manque de lumière pendant la nuit. Le temps
passé à l'intérieur ne déclenche pas de rencontre à la sortie.

La thermique applique l'air ambiant +15 °F sous cet abri trouvé, au lieu du
ressenti du vent. L'immersion conserve la priorité sur l'abri. Comme le
ressenti extérieur, la température calculée reste signée sur 16 bits ;
le port évite le retournement de signe de l'octet original au-dessus de 127.
Les preuves sur l'original et les limites sont dans [sites.md](logic/sites.md).

TOPO montre une fenêtre textuelle de 32 × 14 cellules, centrée sur le joueur
à l'ouverture. Flèches ou WASD déplacent la fenêtre de 8 colonnes ou 4 lignes,
sans dépasser la grille. `P`, `C`, `H`, `R` repèrent le joueur, l'épave, la
cabane et les rangers ; `=` indique l'eau. Huit glyphes codent le niveau par
tranches de 16. Entrée, Espace ou ESC restituent le mode mixte et la même
page HGR. Ce premier écran n'est pas le tracé de courbes TOPO de l'original.
Les Y du monde augmentent vers le nord : les lignes sont donc dessinées par
Y décroissant, et défiler vers le haut augmente l'origine Y. Pendant WALK,
le module TOPO est chargé une fois puis actualisé à chaque pas, sans attente
de touche. La fenêtre temporaire 0–19 protège les quatre lignes de messages ;
le curseur est restauré et la simulation en page HGR reste intacte.

Le rendu TOPO ne passe plus par HOME. Pendant sa construction, le vecteur
COUT est temporairement dirigé vers `topo_output` : le caractère est comparé
à l'octet de RAM texte sous le curseur et n'est écrit qu'en cas de différence.
Le curseur avance dans les deux cas. Les fins de ligne et les lignes restantes
sont complétées par des espaces selon la même comparaison, sans effacement
ROM. Cela retire les anciens chiffres ou repères tout en préservant les points,
virgules, espaces et légendes déjà corrects. Le vecteur est restauré avant de
rendre la main ; aucun chargement disque n'intervient pendant son remplacement.
`test_sites.py` compte les instructions d'écriture lors du défilement et exige
zéro écriture pour une carte inchangée. `test_walk.py` exige exactement autant
d'écritures que d'octets visiblement modifiés sur chacun des douze pas réels.

Sur la case du site ou de l'animal, les images gardent leur azimut fixe et
leur taille originale. L'épave conserve ses lignes 67–158 ; les autres
sprites sont décalés de 10 lignes vers le haut pour tenir dans les 160 lignes.
Elles sont masquées la nuit et à l'intérieur de la cabane.

Depuis les cases voisines, l'épave et la cabane se projettent depuis leurs
coordonnées fixes : point de départ exact pour l'épave, centre de case pour
la cabane. L'azimut utilise atan2 et la distance euclidienne les fractions
8.8 du joueur. Le plan du sprite est au pas `floor(distance)+1`, limité à 8.
La taille est divisée par 1, 2, 4 ou 8 selon la plus grande puissance de deux
inférieur ou égal à ce pas. Les échantillons conservent les couleurs originales,
y compris le noir opaque, et la base suit la projection du niveau du site.
Ces paliers et la limite de distance sont des règles du port ; la projection
exacte de l'original reste à établir. Un seul site est sélectionné dans le
champ, selon le pas de distance ; à égalité, l'épave passe avant la cabane.
Le site ou l'animal de la case courante a priorité. Les animaux restent locaux.

`scene_prepare` charge WILDPRJ pour calculer la géométrie et les bornes,
puis le flux graphique avant `view_full`. Un cache de position, cap et état
de rencontre évite de recalculer une scène identique. Chaque
colonne décode ses 160 couleurs dans le tampon de texte BLOAD devenu libre,
peint immédiatement les runs opaques locaux, ou les garde en attente jusqu'au
plan de distance du site. Le terrain plus proche est calculé avant l'insertion :
ses lignes déjà remplies masquent les pixels du sprite. Les lignes restantes
peignent seulement le terrain derrière les zones transparentes. Aucun
chargement disque n'intervient dans cette boucle. La géométrie d'un site
distant unique est conservée même hors champ : elle se décale comme un sprite
local lors des rotations de 22,5° et 45°. Seules les 35 ou 70 colonnes
découvertes sont recalculées ; l'occlusion reste fonction de leur azimut absolu.
Un test conservateur des coordonnées repère la présence possible de deux sites
voisins ; dans ce cas seulement, la rotation conserve la reprojection complète
pour choisir le plus proche dans le nouveau champ. Les flèches ne chargent
aucun module pour les scènes défilables ; LOOK doit toujours remplacer le
vocabulaire partagé par le flux graphique. Un défilement invalide le cache de
projection afin qu'un retour direct à son ancien cap ne restaure pas une
géométrie décalée.

Le front restant du terrain saute les lignes déjà opaques. Une table de
128 distances, préparée avec la géométrie et les mêmes divisions et tables
de lignes que le terrain, borne la crête la plus haute possible à partir du
niveau maximal de carte. Le rayon s'arrête lorsque cette borne ne peut plus
atteindre les lignes encore visibles ; les trous transparents sont conservés.
Sur une ancienne carte sans plafond déclaré, le niveau maximal admis 125
sert de borne conservatrice.

Les rencontres appliquent les six paires centre/largeur Sierra : saison en
pourcentage entier, heure entière, groupe de terrain, altitude en centaines
de pieds, différence maximale de niveau dans le voisinage 3 × 3 et indice
climatique régional. Les bornes et les fenêtres horaires exclues ont été
comparées à 162 exécutions du filtre original T0A S00. Le format de carte
actuel distingue dégagé/rocheux/bois/maquis/eau, sans distinction rivière/lac.

La probabilité est `minutes × NATURE × √difficulté × taux × 10⁻⁵`, avec
les taux 80/40/100. Les calculs flottants ROM sont comparés à 45 mesures de
l'original ; le tirage utilise toujours le LFSR indépendant de la météo.
NATURE accepte des entiers 0–100 (initialement 1), alors que l'original accepte
aussi des fractions positives et règle séparément la fréquence des ressources.
La valeur zéro pour désactiver les nouvelles rencontres est une extension du
port. Les fenêtres nocturnes sont actives ; le rendu reste
noir dans l'obscurité. `spend` transmet la durée du pas à `scene_update`,
après l'horloge et le vent, avant la température, la thermique et la santé.
La faune lit l'horloge et le terrain : elle reste dans le module ENV déjà
chargé, ce qui évite un aller-retour disque avec THERM à chaque pas.
La marche et la nage affichent les minutes parcourues après chaque pas,
sans attendre une touche ; `test_walk.py` contrôle aussi le retour à la
commande après une longue marche et l'absence de lectures disque à l'arrêt. Repos et
repas ne déclenchent pas de tirage ; marche/nage gardent leur cadence reconstruite.
Il n'y a plus de cumul d'action plafonné à 255 minutes. `scene_update` bloque
les tirages sous abri et les appels sans temps écoulé ne tirent rien. Avec
NATURE zéro et aucune présence, il évite aussi lecture disque et hasard.

Toutes les espèces sont parcourues dans l'ordre ours/couguar/crotale. Si
un animal est déjà présent, un second tirage conserve sa présence pour
RND < 0,5 et le remplace sinon, même pour la même espèce. Une acceptation
fixe `fauna_alert` : WALK s'arrête après le pas consommé.
La sonde `re_fauna_accept_probe.py` vérifie 36 cas dans le point d'acceptation
original `$5B5A`, y compris le seuil exact 0,5 et les drapeaux d'arrêt.
Une rencontre reste à sa case pendant 60 minutes au plus ; attente, repos
et repas font aussi avancer son âge, sans tirage de nouvelle rencontre.
Cette durée est reconstruite ; mouvements, comportements et attaques
restent à porter.

Marche et nage refusent un prochain pas hors de `2 ≤ x < 110`,
`2 ≤ y < 82` (coordonnées en cases, fractions conservées). Elles laissent
une bande extérieure de deux cases ; seul un pas accepté consomme du temps.
Les quatre côtés, les diagonales et les débordements sont couverts par
`test_boundary.py`.

## Mémoire et modules disque

La carte mémoire est définie dans [`src/wild.cfg`](../src/wild.cfg).
La place disponible doit être mesurée dans `build/wild.map` après chaque
changement ; les anciens chiffres de marge ne sont pas des budgets actuels.
Les zones résidentes sont presque pleines.

| Zone | Contenu |
|---|---|
| `$0A00-$0FFF` | `WILDTXT` : messages, constantes et table de bornes des rayons |
| `$1000-$1FFF` | `WILDLO` : tables de lignes, remplissage/effacement déroulés, LOOK résident, noms et positions d'objets, raccourcis d'écran et compteurs de charge |
| `$2000-$3FFF` | HGR page 1 ; vue sur 0–159, bandeau de survie et ruban central sur 0–15, paysage sous le bandeau conservé en lignes invisibles 160–175 ; quatre lignes de texte en mode mixte |
| `$4000-$57FF` | `WILDGAME` : logique résidente, état et objets |
| `$5800-$5FFF` | Fenêtre partagée de 2 Ko pour les modules et sprites |
| `$6000-$6FFF` | `WILDERNESS` : démarrage, moteur de vue, décodeur de sprites et constantes |
| `$7000-$94FF` | `WILDMAP` : en-tête de 64 octets et grille 112 × 84 |
| `$9500-$95F0` | Sauvegarde du texte pendant BLOAD, réutilisée pour les couleurs de la colonne et les temporaires du ciel ; temporaires thermiques, géométrie des sprites, saisie, stock accessible et refus de charge |
| `$9600-$BFFF` | DOS 3.3 |

| ID du cache | Fichier | Contenu |
|---|---|---|
| 1 | `WILDVOC` | Vocabulaire et parcours des mots saisis |
| 2 | `WILDSCR` | INVENTORY groupé/paginé et texte HELP |
| 3 | `WILDSIM` | Soleil du jour, rencontres, compteurs, crédits de survie et santé |
| 4 | `WILDSIM` | Même binaire, air horaire et thermique |
| 5 | `WILDPLN` | Épave |
| 6 | `WILDBER` | Ours Sierra |
| 7 | `WILDCOU` | Couguar Sierra |
| 8 | `WILDRAT` | Crotale Sierra |
| 9 | `WILDHUT` | Cabane |
| 10 | `WILDSIT` | Entrée/sortie, vue intérieure et TOPO |
| 11 | `WILDPRJ` | Géométrie des sites et borne du relief |
| 12 | `WILDTRV` | Préparation, tracé, durée et rives de nage ; effort et poids dans WILDSIM |
| 13 | `WILDINP` | Arguments directs, saisie numérique, NATURE et confirmation de QUIT |
| 14 | `WILDITM` | Transferts, refus de charge et de conteneur, comptes rendus d'objets |
| 15 | `WILDHUD` | Résumé de survie et police monochrome |
| 16 | `WILDSTA` | STATUS : conditions, besoins, stocks et environnement |
| 17/18 | `WILDMED` | Blessures, maladies, soins et expositions ; un seul chargement partagé |
| 19 | `WILDMVI` | Commandes de soin et deuxième page de STATUS : conditions médicales et altitude |
| 20 | `WILDTRE` | Initialisation et interactions avec les arbres ; LOOK est résident |

Les modules restent sur la disquette pendant la partie. Un module
présent dans la fenêtre n'est pas relu. Simulation, thermique, effort de nage
et charge partagent WILDSIM à `$2000`, avec un cache séparé de la fenêtre `$5800`.
Les messages sont
rendus par le code résident, même lorsqu'un module affiche ses propres textes.
Les rotations par flèches n'appellent ni la saisie ni WILDITM. Les modules
ne doivent pas appeler un autre module en écrasant leur propre code.
Les identifiants ci-dessus appartiennent à la réimplémentation ; ceux du
moteur original sont décrits séparément dans [ENGINE.md](logic/ENGINE.md).

Après l'optimisation du 12 octobre 2026 : mesurer à nouveau
`build/wild.map` avant toute extension. WILDGAME conserve 8 octets libres,
WILDLO 6, WILDERNESS 2 et WILDSIM 14. Le résident reste presque plein.
L’initialisation est dans WILDTRE ; LOOK est dans WILDLO. Le calcul GOAL%
est dans WILDSIM, mais STATUS renvoie directement 100 avant la première
action et évite ainsi le chargement de la simulation et le redessin au retour.
STATUS occupe 2 041 octets, le résumé 1 639, SITES 1 538,
INVENTORY/HELP 1 957, WILDTRE 942, WILDMED 1 871 et WILDMVI 856.
Les chiffres viennent de `build/wild.map` ; toute extension exige une nouvelle mesure. Le résolveur des
qualificatifs et `dispatch` sont dans WILDVOC : `parse` doit garder ce module
chargé jusqu'à `dispatch`. NATURE passe par un relais résident avant de charger
WILDINP ; son retour va directement à la boucle principale. La borne du
relief et la géométrie sont dans WILDPRJ, appelé
avant le chargement graphique ; la ROM flottante réutilise la page zéro du
moteur de vue, donc l'œil est recalculé avant les divisions de projection.
Les transitions de SITES vers `show_view` sont des sauts terminaux : elles
ne reviennent pas à du code que le prochain BLOAD pourrait écraser.

L'organisation privilégie le code qui évite des lectures de disquette.
La table `row_n1` ne conserve que ses 86 valeurs visibles : les 170 entrées
suivantes valaient toutes `$FF`, et le moteur les rejette avant l'accès.
Cette place accueille LOOK et les raccourcis exacts WALK/REST/SWIM,
TOPO/VIEW/STATUS/INVENTORY/HELP. Les autres formes, qualificatifs et mots
inconnus passent toujours par WILDVOC. VIEW peut ainsi redessiner sans
remplacer le sprite courant par le vocabulaire puis le relire.

Les 68 octets temporaires de `sky_position`/`sky_lunar` partagent le début
du tampon `overlay_text` à `$9500`. Leur durée de vie se limite au calcul
astronomique, qui n'appelle jamais BLOAD. DOS a terminé sa restauration
avant ce calcul ; les temporaires sont inutiles dès qu'il revient. La sortie
utile (azimut, hauteur, phase) reste résidente. Ce partage ne concerne pas
les variables qui doivent survivre à un chargement ou à un rendu.

L'isolation `s_insul` reste résidente et reçoit une clé persistante de cinq
octets : 19 bits de vêtements portés, le mode sec/mouillé/immergé et un
indicateur de validité. Chaque changement de ces entrées recalcule les mêmes
opérations flottantes et arrondis ; autrement le résultat est réutilisé.
Un transfert entre sac et main ne modifie pas les bits WORN. Le cache survit
au redessin et à la relecture de WILDSIM. Aucun calcul de température,
d'énergie, de santé ou de temps n'est supprimé. `test_memory_cache.py`
compare 76 transitions au résultat d'un calcul frais, puis vérifie la
conservation du cache à travers DOS et la réutilisation de HGR.

`tools/profile_actions.py` mesure depuis `do_command` jusqu'à la nouvelle
invite, ou jusqu'au lecteur STATUS. Chaque essai part de la carte et de
l'équipement par défaut, avec NATURE=0 ; le clavier et le démarrage sont
hors de cette durée. Les secondes correspondent à 1 020 484 cycles/s.

| Commande | Avant (s) | Après (s) | Lectures avant → après |
|---|---:|---:|---:|
| VIEW | 12,471 | 6,200 | 2 → 0 |
| LOOK R | 10,425 | 8,276 | 3 → 2 |
| STATUS au départ | 12,272 | 3,761 | 3 → 1 |
| STATUS après REST 1 H | 12,358 | 9,563 | 3 → 2 |
| REST 1 H | 24,765 | 24,775 | 5 → 5 |
| SLEEP 8 H | 26,438 | 26,387 | 5 → 5 |
| WALK 1 H | 30,599 | 30,608 | 7 → 7 |

Les six essais de départ ont exactement les mêmes positions, horloge,
variables de survie, stocks, blessures et pixels visibles avant/après.
Le gain global du cache thermique est faible dans ces essais, dominés par
DOS et le rendu ; son calcul répété isolé est plus de dix fois plus rapide.
Les variations d'environ 0,01 seconde de REST/WALK restent indiquées.
Le démarrage contient désormais 25 271 octets résidents, comprimés en
17 040 octets : le compromis ajoute 11 octets résidents et 188 octets
comprimés par rapport à la mesure avant optimisation.
Mesuré sur les deux disquettes et leurs propres symboles, l'arrivée dans
`game_start` passe de 24,159 à 23,477 secondes ; la première invite jouable
de 47,472 à 46,445 secondes. La taille comprimée seule ne prédit pas ce
temps, qui inclut les rotations du disque et l'initialisation graphique.

Pour comparer un ancien binaire, fournir sa disquette **et ses symboles** :

```sh
python3 tools/profile_actions.py --disk old.dsk --labels old.lbl --out old.json
python3 tools/profile_actions.py --out new.json
python3 tools/profile_actions.py --setup 'REST 1 H' STATUS
```

## Carte de la réimplémentation

`tools/mkmap.py` produit une grille de 112 × 84 cellules de 2 unités. Chaque
case contient un niveau 0–125 et le bit 7 indique l'eau. Le plafond 125 garde
le calcul niveau − œil + 128 dans un octet. Les montagnes, le placement du
poste au bord et le crash éloigné sont inspirés de TMAKE. L'écoulement est
une reconstruction : remplissage par priorité depuis les bords pour établir
les niveaux de débordement et les exutoires, pente descendante quand elle
existe, puis drainage des plateaux sans boucle. Seules les cellules sous
leur niveau de débordement forment un lac ; sa surface est plane, sans
limite arbitraire à 300 unités. Les sources couvrant le crash ou les rangers
sont rejetées avant de modifier la carte, plutôt que de couper la rivière.
La conversion des blocs 2 × 2 conserve tous leurs points d'eau, à la hauteur
du point d'eau le plus bas ; les points aux coordonnées impaires ne
disparaissent plus. Le placement de la cabane utilise cette eau convertie.
Cette réduction élargit les cours d'eau les plus fins à une case de deux
unités : elle conserve leur continuité mais pas la finesse originale des
rives. `test_mapgen.py` vérifie les cuvettes, plateaux, sorties, rivières
fines, sites secs et 18 couples graine/difficulté, avec reproductibilité.
Les courbes TOPO de l'original utilisent un autre format.

| Octets de l'en-tête | Contenu |
|---|---|
| 0–1 | Signature `W`, version 1 |
| 2–5 | Départ x/y en cellules au format 8.8 |
| 6–7 | Cap initial 0–559, 0 = nord, 140 = est |
| 8–9 | Case du poste de rangers x/y |
| 10–11 | Altitude de base / 100 pieds, premier niveau enneigé |
| 12–15 | Latitude signée, températures hiver/été, vent maximal |
| 16–20 | Présence de la cabane, case x/y, azimut sur 16 bits |
| 21 | Niveau maximal + 1 ; zéro signifie absent (ancienne carte) |
| 22 | Difficulté 1–10 ; zéro signifie ancienne carte, niveau 4 |
| 23 | Indice climatique Sierra, 31 ; zéro reprend cette valeur |
| 24–63 | Réservés |

## Tests et outils

Depuis `wilderness/`, `make test` exécute les fichiers `test_*.py` listés
explicitement dans le Makefile avec a2shot. `make fuzz FUZZ_SEED=7` étend les
comparaisons aléatoires de terrain. `make test-original` compare les commandes
aux deux exécutables et échoue encore sur leurs différences ; sa portée
est précisée dans [ADVENTURE_TESTS.md](ADVENTURE_TESTS.md). Les tests utilisent aussi la carte
originale convertie lorsque `build/orig_map.bin` existe localement.

| Outil | Rôle |
|---|---|
| `tools/mkmap.py`, `tools/gentables.py`, `tools/gendata.py` | Générer carte, tables de rendu, vocabulaire, objets et constantes |
| `tools/view_ref.py` | Référence exacte du terrain 6502 |
| `tools/re_graphics.py` | Extraire les flux Journey, les PNG transparents et les empreintes SHA-256 |
| `tools/re_site_probe.py` | Vérifier les transitions SHELTER et les températures abri/igloo originales sur ROM |
| `tools/re_fauna_probe.py` | Exécuter les filtres Sierra et capturer les probabilités avant le tirage dans le code original |
| `tools/re_fauna_accept_probe.py` | Exécuter conservation/remplacement et vérifier les drapeaux d'interruption originaux |
| `tools/profile.py` | Mesurer les cycles par routine via `pcprof` |
| `tools/flux2dsk.py`, `tools/smalldos.py` | Décoder les images disque et lire les blocs/catalogues SMALLDOS |
| `tools/applesoft.py`, `tools/peek2bin.py` | Lister le BASIC tokenisé et convertir les dumps de l'émulateur |
| `tools/topo.py`, `tools/topo2map.py`, `tools/view3d.py` | Décoder TOPO, convertir une carte pour les tests, prototype flottant de la vue |
| `tools/re_*.py`, `tools/messages.py` | Sondes et extractions de l'original ; consulter l'en-tête du script pour ses données d'entrée |

```sh
make originals     # récupère les données originales locales
make extract       # décode WOZ/A2R et extrait les fichiers SMALLDOS
make run-original  # menu original et listing BASIC
make dump-game     # première partie originale et dump RAM
make topo          # carte et vue de départ originales recalculées
```

Les données originales et les résultats de sondes restent dans `original/`
et `build/`, ignorés par git. Les sprites sont ajoutés à la disquette locale,
sans incorporer leurs octets aux fichiers source.

## Performance

La correction des rotations est contrôlée dans `test_pan.py`, avec images
comparées à la référence, passages hors champ, tours complets dans les deux
sens, relief devant le site et deux sites concurrents. Sur la carte plate de
contrôle, 48 rotations de 22,5° et 45° près de la cabane passent de
417 970 883 cycles avec reprojection complète forcée à 96 251 258 cycles avec
défilement, soit 77,0 % de moins. La mesure commence à `turn_view`, inclut les
chargements déclenchés par cette routine et finit à l'invite ; la saisie et le
chargement initial du vocabulaire sont exclus. Les 32 rotations par flèches
n'ajoutent aucune lecture disque. Le rapport est dans `build/pan-profile.txt`.

L'effacement et le défilement parcourent directement les lignes physiques HGR
16 à 175 : terrain visible 16–159, puis cache 160–175 sous la boussole.
L'effacement évite ainsi l'appel au calcul de ligne et la sauvegarde de A pour
chaque octet. La boucle de rayon n'appelle l'activation d'un sprite distant que
lorsqu'un sprite attend effectivement son plan de profondeur.

Comparaison du rendu complet avant/après ces optimisations, avec les mêmes
images et le même nombre de pas de rayons (`test_scene_render.py`) :

| Carte | Terrain seul avant → après | Avec épave avant → après |
| --- | --- | --- |
| Générée | 4 245 988 → 3 928 085 | 5 874 917 → 5 558 493 |
| Plate | 4 903 196 → 4 592 479 | 4 886 280 → 4 632 263 |
| Falaises | 3 327 935 → 3 010 117 | 4 174 755 → 3 911 784 |
| Bruit | 2 779 126 → 2 458 266 | 3 852 713 → 3 597 665 |
| Plate sans plafond déclaré | 4 903 196 → 4 592 479 | 6 624 816 → 6 314 314 |

Ces mesures en cycles couvrent le rendu depuis `view_full`, sans préparation
géométrique ni chargement disque. Le gain va de 4,7 à 11,5 % selon la scène.
Le binaire reste dans les segments prévus pour l'Apple II+ 48 Ko.

Le profil `build/scene-render-profile.txt` est produit par
`test_scene_render.py`, du début de `view_full` au retour à la saisie, hors
chargement DOS et préparation géométrique dans `WILDPRJ`. Avec l'épave à sa hauteur d'origine, la carte plate de
contrôle passe de 10 776 à 5 641 pas de rayons (−47,7 %). Les cycles passent
de 4 567 063 pour le terrain seul à 4 600 249 avec l'épave
(après ciel, lots 4/5 et cadre) : le décodage et
le masquage ont leur coût, même lorsque les rayons sont fortement réduits.
Sur la carte générée montagneuse, 3 914 436 → 5 528 889 cycles
accompagnent un gain de 115 pas ; la borne globale
doit laisser les rayons rechercher les sommets visibles au-dessus du sprite.
Ces comparaisons mesurent le coût de l'ajout du sprite au terrain seul,
pas un gain global par rapport à l'ancienne superposition.

Mesures historiques du terrain seul : environ 2,5 M cycles pour une vue
complète, avec environ 55 % dans les pas de rayons et 25 % dans le remplissage.
Ces chiffres dépendent de la position et ne couvrent pas les chargements DOS
ou la composition actuelle des sprites ; les remesurer avant optimisation.

Les essais par maxima de blocs n'ont gagné que 1–2 % ; laisser les RTS
plantés entre les segments s'est révélé plus lent. La division déroulée
appelée en sous-routine a ajouté environ 16 % en marche lors du découpage.
La réintroduire aux deux endroits chauds dépend de la place disponible.
Doubler le pas au-delà de 64 cases change le rendu et demande une décision
explicite. La page HGR 2 est occupée par la logique de jeu : aucun double
tampon n'est actuellement disponible.

## Astres et orientation

`sky.s` projette les vecteurs horizontaux est/nord/haut sur les mêmes axes
que le terrain. Le soleil reprend sin δ = 0,398 sin(2π date − 1,378),
la latitude signée et l'heure solaire (12 h = passage au méridien).
Son azimut est géographique : la déclinaison magnétique de la boussole
ne déplace pas le soleil. Sa projection verticale utilise 95 − 48 tan(h),
comme le relief ; le dessin et cette projection ne revendiquent pas une
identité au bit près avec le disque original de SURV3D.

La lune est une extension, aucun modèle lunaire n'étant identifié dans
l'original. `tools/sky_ephemeris.py` applique les éléments orbitaux et les
perturbations lunaires de [Paul Schlyter](https://stjarnhimlen.se/comp/ppcomp.html),
puis échantillonne tous les deux jours de l'année de référence 1985.
L'heure solaire et la longitude MAP+25 donnent une heure UT approchée ;
la Sierra utilise −120°. La date saisonnière fournit le jour civil, l'heure
fournit la fraction journalière. L'ascension droite relative au soleil et
la déclinaison sont interpolées, puis transformées dans le repère local.
Une correction moyenne de parallaxe d'environ 1° abaisse la lune.
Le calendrier de 365 jours du jeu répète la même année de référence.
La lune est dessinée uniquement la nuit ; son terminateur est stylisé,
sans rotation précise de l'axe de phase ni réfraction atmosphérique.

La quantification/interpolation du tableau introduit au maximum 1,23°
d'écart angulaire par rapport au calcul orbital direct, mesuré toutes les
3 heures de l'année 1985. Ce chiffre ne certifie pas une précision globale
contre une éphéméride externe. Ce modèle sert à l'orientation du jeu,
pas à une observation astronomique précise.

Le calcul et ses données restent dans WILDSIM, sans lecture par colonne.
L'initialisation de la partie et de la boussole y est déplacée pour conserver
les 48 Ko. Le dessin travaille par colonne, seulement dans le ciel restant,
avec les masques des sprites. La nuit, les rayons ne colorent pas le terrain,
mais en conservent la silhouette pour masquer la lune. Le panorama conserve
ses rotations partielles de jour. `test_sky.py` couvre 216 positions,
les saisons/hémisphères, les nuages, les montagnes et l'égalité panorama/vue
complète de jour et de nuit. Les tests différentiels du terrain isolent
explicitement ce sous-système via `sky_enabled`.

## Résumé de survie et organisation des écrans (lots 4/5)

Les côtés du ruban central sont réservés sur les seize premières lignes HGR.
Un cadre d’un pixel entoure le compas (x = 91–188, y = 0–15), avec
les graduations et le curseur à l’intérieur. Quatre champs de treize
caractères utilisent une police 7 × 7 monochrome :
heure/santé, faim, soif, puis alerte ou état thermique/indication locale.
Le terrain reste calculé dans le cache invisible, mais ne recouvre aucun
champ. La simulation est terminée avant que le résumé réutilise sa page HGR ;
le démarrage traite aussi la faune avant de composer le bandeau.

`ui_monitor` classe les besoins après chaque pas sans écrire dans l'état de
survie : 6/12 heures pour faim/soif, bandes de santé de 20 %, facteur thermique
sous 0,95, immersion et seuils de conditions identiques à STATUS. Il conserve
un événement lors d'un changement de classe ; une apparition de condition
reste une aggravation même si une autre condition disparaît au même pas.
Une action longue affiche une seule alerte prioritaire (condition, immersion,
thermique, santé, soif, faim) au résultat. Une classe inchangée ne crée pas
d'événement supplémentaire. Les reprises d'état produisent aussi un libellé.
Le bandeau peut ensuite rappeler l'abri ou les objets au sol ; frissons et
sueur passent avant ces indications. STATUS conserve le détail complet.

Le résumé est chargé une fois après une action qui le modifie, puis l'actif
graphique est rétabli. Les flèches réutilisent le bandeau et ne chargent ni
WILDHUD ni WILDSTA. Le contrôle des événements reste dans WILDSIM déjà chargé
pendant les pas ; il n'introduit pas de lecture DOS à chaque pas. Avec les
sprites désactivés, démarrage/LOOK R/LOOK L/STATUS/GET PARKA/REST 3/INVENTORY
produisent respectivement 3/5/7/10/15/19/22 lectures cumulées, contrôlées par
`test_overlays.py` avec préservation de la page zéro, texte et états résidents.

STATUS place santé et conditions avant besoins, réserves CARRIED/HERE et
environnement. Les conditions thermiques commencent sur une nouvelle ligne
pour éviter de couper leur nom. Toutes les conditions médicales, frissons,
abri et immersion simultanés tiennent dans les 24 lignes du test. INVENTORY
a quatre groupes, des pages de douze objets et quatre capacités visibles ;
les provisions réparties apparaissent avec les onces propres à chaque groupe.
TOPO dispose de C, du cap magnétique en 0–559 avec huit directions et d'une
ligne identifiant le site sous le joueur. Les tests couvrent les déclinaisons
magnétiques positives et négatives, le recentrage, les groupes vides, deux
pages pleines, les quantités réparties et l'absence de temps/santé consommés
par ces consultations. L'observation d'un nouveau joueur reste à réaliser.

Mesure du démarrage après ciel, lots 4/5 et cadre : 21,63 s jusqu'à
`game_start`, 42,40 s jusqu'à l'invite, à la vitesse Apple II. Les valeurs
consignées avant ces ajouts étaient 20,89 et 36,86 s. Les chargements de
vocabulaire et de STATUS coûtent respectivement 2,75 et 2,65 s. Le résident
compressé reste dans deux fichiers (24 744 → 16 380 octets) ; aucun troisième
accès de démarrage n'est ajouté pour le cadre. Une carte peu compressible
nécessite toujours un fichier supplémentaire, couvert par `test_boot.py`.

## Conditions médicales

`medical.s` conserve dans le résident les états active/soignée/prévenue,
le pourcentage de santé et l'heure de début des 15 conditions Journey.
L'incubation et la récupération utilisent les coefficients et arrondis ROM
de T0B/S0D. La guérison désactive la condition dès `h ≥ t + D`.
Les deux dernières conditions restent sans nom : leurs paramètres sont
portés, sans leur attribuer un rôle que l'analyse n'a pas établi.

T06/S00 fournit les prérequis de prévention et de traitement des 13 conditions
nommées. Les soins acquis persistent ; les actions temporaires sont remises
à zéro à minuit. La protection des vêtements reprend T0E/S0A pour les
sélecteurs 8 et 27. L'état médical est consultable par M dans STATUS,
puis B pour revenir ; cette consultation ne consomme ni temps ni santé.

La santé multiplie les facteurs de ces conditions, de l'altitude, des
déficits et de la température corporelle. L'altitude reprend le seuil
`INT(5 × santé précédente) + 100`, la correction quadratique native et
l'oxygène. La santé critique ou une condition 6–11 active depuis moins de
huit heures limite le prochain pas à 30 minutes.

`hazards.s` porte les compteurs de perte de sel et de froid, leurs seuils
stricts et leur décroissance quand la condition est prévenue. Soleil et neige
utilisent encore la position solaire, les bois et la ligne de neige du port ;
leurs sélecteurs originaux ne sont pas validés par ces tests. Les déclencheurs
d'infection, de malaria, de contamination, de chutes et d'attaques restent à
porter. SPLINT et les soins thermiques manquent encore.

`care.s`, dans WILDMVI, traite les commandes avant un saut au relais résident
`medical_spend`, qui charge WILDMED, applique les prérequis et avance le temps.
USE des produits 41–51 applique l'action médicale et son temps. Les compteurs
W8 positifs sont diminués d'une unité, avec emprunt sur 16 bits ; zéro et les
valeurs signées négatives sont conservés. Les utilisations restantes sont
affichées dans INVENTORY. EAT/DRINK admettent FLAGYL, SALT TABLETS et QUININE ;
les autres produits sont refusés sans changement d'état ni durée.
SHIELD EYES et LOWER HEAD posent les sélecteurs 10 et 4 sans durée.
SUCK VENOM pose le sélecteur 23 en 15 minutes seulement avec une morsure active.

Une particularité native est reproduite : un stock vide ne décrémente plus,
mais le prérequis sélectionné reste appliqué par T06/S00. Six cas vérifient
directement la chaîne T11/S00 → T0E/S02 → T0E/S0A → T06/S00, avec stocks 0/1
de SUNSCREEN, FLAGYL et OXYGEN. L'oxygène repose sur un drapeau d'utilisation
distinct : la dernière dose l'active, une nouvelle utilisation à vide le
désactive. Cela ne valide pas toutes les transactions USE :
le déplacement automatique des objets et la stérilisation de la trousse
restent à porter. Les quantités sont conservées par les chargements d'overlays.

Les comparaisons directes au code original sur ROM couvrent 160 progressions,
66 combinaisons de soins, 60 altitudes/états d'oxygène, 80 cadences,
84 configurations vestimentaires et 59 expositions sel/froid, soit 509 cas.
Le test de commandes vérifie FIRSTAID, STOP BLEEDING, la pagination de STATUS
et la conservation des états lors des chargements.
`test_care.py --original` ajoute 90 compteurs signés, 12 gestes, 22 prises
orales et les 6 chaînes de stock vide/dernière dose, soit 639 cas médicaux
et d'exposition au total. Les refus, les durées, les doses et l'affichage sont
aussi vérifiés par les commandes du port.

## Arbres et forêts

`mkmap.py` reprend TMAKE 100–340 : au moins cinq contours, rayon 10,
quatre harmoniques d’amplitude maximale 3 et excentricité inférieure à 0,7.
Un flux aléatoire séparé préserve les reliefs et cours d’eau déjà générés ;
les graines Python ne reproduisent pas les tirages USR de l’original.
`topo2map.py` importe aussi les intervalles boisés du TOPO original pour
les comparaisons locales. La couverture est échantillonnée au centre de
cases de quatre unités, soit 56 × 42 bits.

L’extension MAP utilise les octets d’en-tête 26 (présence) et 27 (limite
des arbres, 110 centaines de pieds en Sierra). Ses 294 octets suivent le
terrain dans le fichier et sont chargés séparément à $0800–$0925 ; les
petites routines résidentes occupent $0926–$09FF. Ces adresses réutilisent
HELLO après son passage au chargeur natif, sans toucher aux vecteurs DOS.
Les cartes dépourvues d’extension chargent un masque vide.

Les deux profils symétriques Sierra de SURV3D $1F00 sont reconstruits
sans distribuer les images originales. Leur projection est adaptée au
moteur de rayons du port : huit pas proches, profil selon la coordonnée
transverse du monde, couronne centrée sur un quart de case et première
silhouette visible par colonne. Le feuillage opaque alterne le vert et le
noir, comme le tracé Sierra de SURV3D `$1B0D–$1B4F` ; sa phase reste liée
à l’arbre pendant les rotations. Les crêtes
au premier plan limitent sa base ; un sprite opaque plus proche reste
prioritaire. Les arbres masquent également les astres. Cette adaptation
ne reproduit pas la disposition et le cache des arbres du moteur original ;
elle peut omettre une silhouette lointaine disjointe derrière un arbre proche.
Les hauteurs natives du feuillage sont projetées sans l'ancien décalage de
18 unités : les couronnes proches remontent de 18 pixels divisés par le
nombre de pas. Les trois colonnes centrales prolongent un tronc noir
jusqu'au sol, sans déplacer la base de l'arbre. La limite entre feuillage
et tronc est bornée à l'écran pour les bases projetées au-delà de 255.
Le contour supérieur reste noir sur toutes les colonnes ; un liseré noir
à la base de la couronne renforce sa séparation du terrain vert.
La base du premier profil est aplatie à la hauteur native centrale (31),
pour supprimer les franges noires latérales sous le feuillage. Le deuxième
profil conserve son dessous natif, déjà situé à cette hauteur ou au-dessus.
Le calcul de pente rejette la retenue du produit sur 16 bits avant le
décalage : une falaise très abrupte ne peut pas ramener une projection
hors écran dans le ciel par débordement.
La végétation d’altitude reste classée SCRUB mais n’a pas de silhouette
d’arbre. CLIMB TREE/DOWN, HANG FOOD et la récupération du sac sont portés
dans WILDTRE ; voir [logic/trees.md](logic/trees.md) pour les preuves natives
et les adaptations de stockage.

`test_forest.py` compare les profils aux données locales de l’original et
le rendu à une référence indépendante : directions cardinales, deux tours
complets dans les deux sens, égalité des pixels entre rotation et redessin,
aucune lecture disque pendant une rotation, eau, limite d’altitude, anciens
fichiers, masque clairsemé, crête au premier plan, troncs jusqu'au sol et
feuillage des arbres proches sur les pentes descendantes.
