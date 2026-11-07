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
| Formulation des aliments | Calcul optimisé, ration saisie, formules enregistrées, comparaison |
| Historique des rations | Rations en cours, distributions |
| Alertes et rappels | Alertes ouvertes, résolues ou ignorées |
| Références nutritionnelles | Besoins documentés utilisés par le moteur (consultation) |
| Base documentaire | Recherche dans les documents techniques validés |
| Traçabilité des données | Experts et administrateurs : sources, validations, imports, journal |
| Paramètres | Profil, exploitations et membres, réglages des alertes, mot de passe |

Si vous gérez plusieurs exploitations, choisissez celle à consulter dans la liste en haut de l'écran
(ou « Toutes les exploitations »). Sur téléphone et tablette, le menu s'ouvre avec le bouton ☰.
Dans les formulaires, l'exploitation proposée par défaut est celle sélectionnée, sinon une exploitation active.

## 3. Tableau de bord

Tous les chiffres proviennent de vos données enregistrées. Lorsqu'il n'y a pas encore de données, un message
l'indique : aucune statistique n'est inventée.

- **Coût d'alimentation estimé** : somme des coûts des distributions des 30 derniers jours. Si certaines
  distributions n'ont pas de coût connu (formule sans prix), leur nombre est indiqué.
- **Évolution du poids** : poids moyen des pesées enregistrées chaque mois, tous animaux confondus.

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

**Formulation des aliments** comporte trois onglets.

**Calcul optimisé**
1. Nommez la formule et choisissez le mode : **Économique** (coût minimal) ou **Équilibré** (au plus près des cibles
   des experts).
2. Choisissez un animal (son profil est repris de sa fiche), un lot ou un profil type.
3. Laissez la référence en **Automatique** ou choisissez-en une.
4. Cochez les ingrédients disponibles ; remplacez le prix si besoin ; indiquez un stock (avec le nombre d'animaux
   et la durée) pour que le moteur en tienne compte.
5. **Calculer la formule**.

Trois issues possibles :

| Résultat | Signification |
|---|---|
| **Estimation mathématique** | Une ration respecte toutes les contraintes : pourcentages, quantités, coût, apports comparés aux besoins, sources |
| **Aucune ration possible** | Les contraintes sont incompatibles avec vos ingrédients : le moteur indique lesquelles et de combien |
| **Calcul refusé** | Des données validées manquent (référence, valeurs, prix) : la raison est indiquée |

Un ingrédient sans valeur validée pour un nutriment requis est **exclu** (et signalé), jamais compté à zéro.
Une estimation n'est pas une recommandation : demandez la vérification d'un expert avant de l'utiliser.

**Ration saisie** : enregistrez la ration que vous distribuez déjà (kg brut par animal et par jour) pour en connaître
la matière sèche, les apports et le coût.

**Formules enregistrées** : historique, statut, et **comparaison** de 2 à 5 formules.

## 10. Historique des rations

- **Rations** : créez une ration à partir d'une formule (*Créer une ration* dans la formule, ou *Nouvelle ration*),
  associez-la à un lot ou à un animal, puis **terminez-la** à la fin de la période.
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
- Si l'assistant n'est pas configuré sur l'installation, la page l'indique et la saisie est désactivée : tous les
  autres modules restent utilisables.

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