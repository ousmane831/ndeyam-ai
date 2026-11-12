# Guide utilisateur — NDEYAM AI

Ce guide s'adresse aux éleveurs et aux experts. Il décrit les écrans de l'application (version 0.1.0).

> NDEYAM AI est un prototype. Les calculs sont des estimations fondées sur les données enregistrées ;
> ils ne remplacent ni l'avis d'un technicien ni celui d'un vétérinaire.

## 1. Créer son compte

1. Ouvrez l'application et cliquez sur **Créer un compte éleveur**.
2. Renseignez vos informations, le nom de votre exploitation et un mot de passe d'au moins 10 caractères.
3. Votre exploitation est créée en même temps que votre compte : vous en êtes le **propriétaire**.

Les comptes **Expert** sont créés par un administrateur. Un expert ne voit que les exploitations qui l'ont invité,
en lecture seule.

Mot de passe oublié : lien **Mot de passe oublié ?** sur la page de connexion ; un lien valable une seule fois est
envoyé par e-mail.

## 2. Naviguer

| Menu | Contenu |
|---|---|
| Tableau de bord | Indicateurs de vos exploitations, graphiques, dernières pesées, rations en cours, alertes, activités récentes |
| Mes animaux | Liste, recherche, filtres, ajout, import / export CSV, fiche de chaque animal |
| Mes troupeaux | Lots (groupes d'animaux) |
| Suivi de croissance | Séances de pesée et GMD des lots |
| Ingrédients alimentaires | Catalogue, ingrédients privés, compositions, prix |
| Formulation des aliments | Formule rapide, calcul détaillé, ration saisie, formules enregistrées, comparaison |
| Historique des rations | Rations en cours, distributions |
| Saisons | Calendrier, disponibilité et prix habituels des aliments par saison, conseils de saison validés |
| Alertes et rappels | Alertes ouvertes, résolues ou ignorées |
| Références nutritionnelles | Besoins documentés utilisés par le moteur (consultation) |
| Base documentaire | Recherche dans les documents techniques validés |
| Traçabilité des données | Experts et administrateurs : sources, validations, imports, journal |
| Paramètres | Profil, exploitations et membres, réglages des alertes, mot de passe |

Si vous gérez plusieurs exploitations, choisissez celle à consulter dans la liste en haut de l'écran
(ou « Toutes les exploitations »). Sur téléphone et tablette, le menu s'ouvre avec le bouton ☰.
Dans les formulaires, l'exploitation proposée par défaut est celle sélectionnée, sinon une exploitation active.

**Langue (français / English).** Le sélecteur **FR | EN**, en haut de chaque écran et sur la page de connexion,
change la langue de toute l'application ; le choix est gardé sur l'appareil. En anglais, les messages du serveur
(refus de calcul, avertissements, alertes, erreurs) sont aussi traduits, y compris ceux enregistrés auparavant. Les
données saisies (noms d'animaux, d'aliments, observations) restent telles qu'elles ont été écrites.

**Installer l'application sur son téléphone.** Ndeyam AI s'installe comme une application, sans magasin
d'applications : sur Android (Chrome), touchez **Installer l'application** en bas du menu, ou *Menu ⋮ → Installer
l'application* ; sur iPhone (Safari), *Partager → Sur l'écran d'accueil*. L'icône du bélier apparaît alors sur l'écran
d'accueil, et l'interface s'ouvre plus vite, même avec une connexion faible.

**Sans réseau.** Cochez *Rester connecté* à la connexion. Ensuite, sans réseau :
- l'application se rouvre, avec les données déjà consultées (bandeau **Hors ligne** en haut de l'écran) ;
- les **pesées** (fiche d'un animal ou séance de pesée, même pour un lot jamais ouvert) sont gardées sur l'appareil ;
- la **formule rapide** calcule la ration sur l'appareil, avec les mêmes données et les mêmes règles que le calcul en
  ligne. Ce résultat est **provisoire** : au retour du réseau, le serveur le recalcule et l'enregistre (lien
  *Voir la formule officielle*), et c'est de cette formule que l'on demande la vérification d'un expert.

Au retour du réseau, tout est envoyé automatiquement, dans l'ordre. Si le serveur refuse une saisie (par exemple une
pesée déjà enregistrée ce jour-là), elle reste affichée avec le motif : corrigez-la ou retirez-la. Les données de calcul
hors ligne de chaque exploitation sont mises à jour à chaque connexion (*Paramètres → Hors ligne et consommation de
données*).

**Consommation de données** (mesurée sur la version de production) : environ 600 Ko à la première ouverture (une
fois par version), puis 4 à 5 Ko par écran ; une semaine d'usage quotidien consomme moins de 1 Mo.

## 3. Tableau de bord

Le tableau de bord s'ouvre sur **À faire aujourd'hui** : animaux à peser, croissance à surveiller, distributions
à enregistrer, formules en attente d'un expert, fiches à compléter. Chaque tâche a son bouton d'action direct
(par exemple **Peser**, qui ouvre la fiche de l'animal sur l'onglet des pesées).

Viennent ensuite les indicateurs, le troupeau, l'évolution du poids, les dernières pesées, les rations en cours et
les activités récentes. Tous les chiffres proviennent de vos données enregistrées. Lorsqu'il n'y a pas encore de
données, un message l'indique : aucune statistique n'est inventée.

- **Coût d'alimentation estimé** : somme des coûts des distributions des 30 derniers jours. Si certaines
  distributions n'ont pas de coût connu (formule sans prix), leur nombre est indiqué.
- **Évolution du poids** : moyenne des pesées de chaque mois, tous animaux confondus. Les animaux pesés changent
  d'un mois à l'autre : ce n'est pas la courbe d'un animal (voir sa fiche pour cela).

## 4. Animaux

### Ajouter un animal
**Mes animaux → Ajouter un animal.** Seuls le numéro, l'espèce et le sexe sont obligatoires.

- **Âge** : choisissez « Date de naissance connue », « Âge estimé » (la date est calculée et marquée
  « estimée ») ou « Inconnu ».
- **Race, catégorie, stade** : les listes dépendent de l'espèce choisie.
- **Lot** : facultatif.

Le numéro doit être unique dans l'exploitation.

### Importer plusieurs animaux
**Mes animaux → Importer**, puis choisissez un fichier CSV (modèle : `backend/templates/csv/modele_animaux.csv`).
Le compte rendu indique les lignes importées et, pour chaque ligne refusée, la raison. Voir aussi le
[guide d'importation](import-donnees.md).

### Fiche d'un animal
Cliquez sur le numéro de l'animal. La fiche comporte six onglets :

| Onglet | Contenu |
|---|---|
| Informations générales | Identité, âge, poids initial et dernier poids, classement |
| Pesées et croissance | Nouvelle pesée, courbe de poids, GMD, comparaison à une plage de suivi validée, historique des pesées |
| Historique alimentaire | Distributions : quantités calculées, distribuées, consommées (si mesurées), coût estimé |
| Rations | Rations associées à l'animal |
| Observations | Notes datées (alimentation, comportement, état de santé observé…) |
| Suivi et alertes | Alertes ouvertes concernant l'animal |

Actions : **Modifier**, **Sortie** (vendu, mort ou archivé — l'historique est conservé), **Remettre présent**,
**Supprimer** (définitif ; préférez la sortie).

## 5. Pesées et croissance

- **Une pesée** : fiche de l'animal → onglet *Pesées et croissance*.
- **Une séance pour tout un lot** : **Suivi de croissance**, choisissez le lot, saisissez les poids (laissez vide un
  animal non pesé) puis **Enregistrer la séance**. Si une ligne est incorrecte, rien n'est enregistré et la ligne
  est signalée.

**GMD (gain moyen quotidien)** = (poids final − poids initial) / nombre de jours écoulés, en grammes par jour.
Il faut au moins deux mesures à des dates différentes. Le poids initial saisi à l'enregistrement compte comme
première mesure. Les estimations visuelles sont signalées comme moins fiables.

La comparaison à une **plage de suivi** n'apparaît que si un expert a saisi et validé une plage applicable à l'animal.

## 6. Alertes et rappels

| Alerte | Quand |
|---|---|
| Rappel de pesée | Animal non pesé depuis l'intervalle choisi (30 jours par défaut) |
| Rappel de suivi | Ration en cours sans distribution enregistrée depuis le délai choisi (7 jours par défaut) |
| Information manquante | Date de naissance, poids, catégorie ou stade non renseignés |
| Croissance hors plage de suivi | Dernier GMD en dehors d'une plage validée par un expert |
| Formulation à vérifier | Formule en attente de l'avis d'un expert |

Chaque alerte explique sa cause (**Pourquoi cette alerte ?**). Vous pouvez la **prendre en compte**, la marquer
**résolue** ou l'**ignorer** (elle ne réapparaît pas tant que la situation ne change pas). Les alertes se ferment
automatiquement quand la situation redevient normale. **Aucune alerte n'est un diagnostic vétérinaire.**

Les délais se règlent dans **Paramètres → Réglages des alertes** ; ce sont des choix d'organisation, pas des
recommandations zootechniques.

## 7. Exploitations et membres

**Paramètres → Mes exploitations** : modifier l'exploitation, en ajouter une autre, gérer les membres.

| Rôle dans l'exploitation | Droits |
|---|---|
| Propriétaire | Tout, y compris la gestion des membres |
| Gestionnaire | Saisie et modification des données |
| Expert invité | Consultation uniquement (et avis sur les formules) |

Une personne doit d'abord avoir un compte pour être invitée.

## 8. Ingrédients et prix

**Ingrédients alimentaires** : catalogue commun (géré et validé par les experts) et ingrédients **privés** de votre
exploitation (par exemple un mélange local), invisibles des autres éleveurs.

La fiche d'un ingrédient montre, nutriment par nutriment, la **valeur utilisée** (validée) ou **« Inconnue »** :
une valeur absente n'est jamais remplacée par zéro. Vous y saisissez aussi vos **prix** (par kg de produit brut) et,
si vous le souhaitez, la quantité disponible.

## 9. Formulation des aliments

**Formulation des aliments** comporte quatre onglets.

**Formule rapide** (onglet ouvert par défaut) : trois gestes.
1. Touchez le **lot** à nourrir. Sa catégorie, son stade et son poids moyen sont repris des fiches de ses animaux
   (dernière pesée de chacun) ; un lot mixte retient la valeur la plus fréquente, et la formule le signale.
2. Choisissez l'**objectif** (par exemple *Préparation à la Tabaski*). Il est retenu pour ce lot sur votre appareil.
3. Cochez vos **aliments** (avec leur dernier prix connu) puis **Calculer la ration**. Vos aliments sont retenus
   pour la prochaine fois.

Le calcul est économique et la référence est choisie automatiquement. Pour un seul animal, un prix ou un stock à
préciser, utilisez le **Calcul détaillé**.

**Carte « À donner chaque jour »** : en tête du résultat, en gros, la quantité de chaque aliment par jour pour tout
le lot (avec un pictogramme par famille d'aliment), le total et le coût du jour, et le coût pour une semaine. Changez
le nombre d'animaux avec − et +. **Partager sur WhatsApp** envoie la ration en texte ; **Imprimer la fiche** imprime
la carte seule. La carte dit toujours ce que vous pouvez en faire : *à faire vérifier par un expert*, *vérifiée :
vous pouvez la distribuer*, ou *ne pas utiliser* (rejet, données DEMO). Le détail du calcul par animal suit.

**Calcul détaillé**
1. Nommez la formule et choisissez le mode : **Économique** (coût minimal) ou **Équilibré** (au plus près des cibles
   des experts).
2. Choisissez un animal (son profil est repris de sa fiche), un lot ou un profil type.
3. Laissez la référence en **Automatique** ou choisissez-en une.
4. Cochez les ingrédients disponibles ; remplacez le prix si besoin ; indiquez un stock (avec le nombre d'animaux
   et la durée) pour que le moteur en tienne compte.
5. **Calculer la formule**.

Sur téléphone, cochez un ingrédient pour faire apparaître son prix et son stock. Les ingrédients dont la matière
sèche n'est pas validée sont regroupés à part : ils seraient exclus du calcul. Avant de calculer, un encadré signale
ce qui risque d'être exclu (matière sèche non validée, prix manquant en mode économique).

Trois issues possibles :

| Résultat | Signification |
|---|---|
| **Estimation mathématique** | Une ration respecte toutes les contraintes : pourcentages, quantités, coût, apports comparés aux besoins, sources |
| **Aucune ration possible** | Les contraintes sont incompatibles avec vos ingrédients : le moteur indique lesquelles et de combien |
| **Calcul refusé** | Des données validées manquent (référence, valeurs, prix) : la raison est indiquée |

Un ingrédient sans valeur validée pour un nutriment requis est **exclu** (et signalé), jamais compté à zéro.
Après un refus ou une impossibilité, **Que faire maintenant ?** indique chaque ingrédient à compléter (avec un lien)
et propose **Modifier et recalculer**, qui reprend le profil, la référence et les ingrédients du calcul.
Une estimation n'est pas une recommandation : demandez la vérification d'un expert avant de l'utiliser.

**Ration saisie** : enregistrez la ration que vous distribuez déjà (kg brut par animal et par jour) pour en connaître
la matière sèche, les apports et le coût.

**Formules enregistrées** : historique, statut, et **comparaison** de 2 à 5 formules.

## 10. Historique des rations

- **Rations** : créez une ration à partir d'une formule (*Créer une ration* dans la formule, ou *Nouvelle ration*),
  associez-la à un lot ou à un animal, puis **terminez-la** à la fin de la période.
  **Une formule calculée par le moteur ne devient une ration qu'après validation par un expert** : une estimation ne
  nourrit jamais un animal. Une ration saisie (ce que vous distribuez déjà) peut être enregistrée directement.
- **Distributions** : enregistrez chaque distribution. La **quantité calculée** (prévue par la ration) et le
  **coût estimé** sont automatiques ; saisissez la **quantité distribuée** et, seulement si vous l'avez mesurée
  (pesée des refus), la **quantité consommée**. Une synthèse et un export CSV sont disponibles.

## 11. Base documentaire

**Base documentaire** : recherchez dans les documents techniques validés par les experts (guides, fiches,
rapports). Chaque résultat indique le document, les pages et la source. Vous pouvez télécharger le PDF.

## 12. Assistant NDEYAM AI

**Assistant Ndeyam AI** : cliquez sur le **bouton à tête de bélier, en bas à droite** de chaque écran. Un panneau de
discussion s'ouvre (en plein écran sur téléphone) ; la conversation reste ouverte quand vous changez de page.
Touche Échap ou ✕ pour le refermer ; l'icône d'agrandissement ouvre la vue plein écran avec l'historique de vos
conversations. Posez vos questions en français, par exemple « Quel est le poids de SN-001 ? »,
« Pourquoi ma formule a-t-elle été refusée ? », « Combien ont coûté les rations ce mois-ci ? ».

- L'assistant consulte **vos** données (uniquement les exploitations auxquelles vous avez accès), les résultats du
  moteur nutritionnel et les documents techniques validés.
- Sous chaque réponse, **Origine des informations** indique ce qui vient de vos données, du moteur nutritionnel,
  d'un document (avec la page) ou du modèle de langage.
- Il **ne calcule aucune ration** (utilisez *Formulation des aliments*), **ne pose aucun diagnostic vétérinaire** et
  signale les informations manquantes plutôt que de les inventer.
- La conversation est liée à l'exploitation sélectionnée en haut de l'écran ; vos conversations sont privées et
  peuvent être supprimées.
- Si l'assistant n'est pas encore activé sur l'installation, le bouton bélier ouvre un **guide** (les gestes
  essentiels, avec un lien vers chaque écran) et un **glossaire** (MS, brut, GMD, UFL, MAT…). Tous les autres
  modules restent utilisables.

## 13. Données de démonstration (DEMO)

Les éléments portant le badge **DEMO** ou le préfixe « [DEMO] » sont **fictifs** : ils servent à présenter
l'application. Une donnée DEMO n'est jamais validée et n'est jamais utilisée pour une exploitation réelle ;
une formule calculée dans une exploitation DEMO porte l'avertissement « Calcul de DÉMONSTRATION » et ne doit pas
servir à nourrir des animaux.

## 14. Glossaire

| Terme | Signification |
|---|---|
| **MS** (matière sèche) | Ce qui reste d'un aliment sans son eau. Les besoins et les teneurs sont exprimés par kg de MS |
| **Brut** | L'aliment tel qu'il est distribué (avec son eau). Les prix et les quantités distribuées sont en kg brut |
| **GMD** | Gain moyen quotidien, en grammes par jour |
| **UFL / UFV** | Unités fourragères (énergie) du système INRA |
| **EM** | Énergie métabolisable (système NRC) |
| **MAT** | Matières azotées totales (protéines brutes) |
| **PDI / PM** | Protéines digestibles (INRA) / protéines métabolisables (NRC) |
| **CB, NDF, ADF** | Fibres (cellulose brute et fractions) |
| **Ca, P** | Calcium, phosphore |
| **Estimation mathématique** | Résultat du moteur, non encore vérifié par un expert |
| **Référence nutritionnelle** | Besoins documentés et sourcés d'un type d'animal, validés par un expert |

Les nutriments d'un système (INRA ou NRC) ne sont jamais mélangés avec ceux de l'autre dans un même calcul.

## Saisons

Le menu **Saisons** montre le calendrier (saison sèche fraîche, saison sèche chaude ou soudure, hivernage), indicatif
et ajustable selon la zone par l'administration.

- **Disponibilité et prix habituels** : pour chaque saison, indiquez si un aliment est abondant, disponible, rare ou
  indisponible, et son prix habituel. La formule rapide affiche « Rare / Indisponible en cette saison » sur les
  aliments concernés, et le calcul utilise le prix habituel de la saison (sinon le dernier prix relevé).
- **Saison du calcul** : la formule rapide calcule pour la saison en cours ; touchez une autre saison pour préparer
  la suivante. Une référence de besoins propre à une saison (par exemple en saison chaude) n'est utilisée que pour
  cette saison, et seulement après validation par un expert.
- **Conseils de saison** (eau, horaires, abri, alimentation) : rédigés par un spécialiste, ils ne sont montrés aux
  éleveurs qu'une fois **validés**. L'accueil affiche la saison en cours et ses conseils validés.

## Spécialistes invités sur une exploitation

Dans **Paramètres → Mes exploitations → Membres**, le propriétaire invite :

| Rôle | Peut faire | Compte nécessaire |
|---|---|---|
| Gestionnaire | Modifier toutes les données | Éleveur |
| Nutritionniste / zootechnicien | **Valider ou rejeter les rations** ; consulter le reste | Expert |
| Vétérinaire | Enregistrer des observations de santé ; consulter le reste | Expert |
| Technicien d'élevage | Enregistrer pesées et observations ; consulter le reste | Éleveur ou Expert |

## Rations types validées et délai de vérification

**Rations types.** Un nutritionniste ou zootechnicien valide **une fois** une ration pour un cas courant (espèce,
catégorie, stade, objectif, saison, tranche de poids). Dans la **formule rapide**, dès que le lot et l'objectif
correspondent, l'encadré vert « Rations types pour ce lot » apparaît : **Utiliser cette ration type** crée une formule
**déjà validée**, et une ration peut être créée tout de suite. Seuls les quantités (selon la matière sèche validée
de vos aliments) et le coût (vos prix du jour) sont recalculés ; les proportions et l'ingestion validées ne changent
pas. Une ration type ne s'applique jamais hors de son cas (par exemple hors de sa tranche de poids).

Pour en créer une, le nutritionniste ouvre une formule validée, choisit **Enregistrer comme ration type** (nom,
tranche de poids, conditions d'emploi), puis la valide dans l'onglet **Rations types** de la formulation.

**Délai de vérification.** Une demande de vérification affiche la réponse attendue (48 h par défaut). Au-delà,
l'alerte passe en « Vérification en retard », les administrateurs de la plateforme sont relancés, et l'éleveur peut
inviter un autre nutritionniste ou utiliser une ration type validée. Une exploitation peut inviter plusieurs
nutritionnistes : le premier disponible se prononce.
