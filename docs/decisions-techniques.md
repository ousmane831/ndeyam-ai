# Décisions techniques

Chaque décision importante est consignée ici avec son contexte et sa justification.

## DT-01 — Monolithe Django modulaire
Une application Django par domaine métier (comptes, exploitations, animaux, nutrition, formulations,
croissance, alimentation, alertes, base documentaire, assistant). Pas de microservices pour le prototype :
déploiement et maintenance plus simples, transactions cohérentes. Les applications sont ajoutées
étape par étape, au moment où leurs modèles sont réellement développés.

## DT-02 — Modèle utilisateur personnalisé dès l'étape 1
Django impose de définir `AUTH_USER_MODEL` avant la première migration. Le modèle `accounts.User`
utilise l'e-mail comme identifiant et porte le rôle (`ADMIN`, `ELEVEUR`, `EXPERT`). Les endpoints
d'authentification arrivent à l'étape 3.

## DT-03 — Configuration par variables d'environnement
`django-environ` lit `backend/.env`. Les réglages sont découpés en `base`, `development`, `production`
et `test`. La configuration de test force `LLM_PROVIDER=none` : les tests n'appellent jamais un
fournisseur réel. `manage.py` utilise `development`, WSGI/ASGI utilisent `production`.

## DT-04 — Base PostgreSQL dédiée sans modification du serveur
Un rôle `ndeyamai` et une base `ndeyamai` dédiés sont créés par `scripts/init_db.py`. La configuration du
serveur (`postgresql.conf`, `pg_hba.conf`) et les autres bases ne sont pas touchées. Le rôle dispose de
CREATEDB uniquement pour la base de test temporaire `test_ndeyamai`.

## DT-05 — Pas de pgvector dans la première version
Les embeddings seront stockés dans PostgreSQL et la similarité calculée avec NumPy derrière une
interface `VectorStore` (`VECTOR_STORE_BACKEND=numpy`). Un adaptateur pgvector pourra être ajouté sans
modifier les documents ni les passages déjà indexés. Sans fournisseur d'embeddings, repli sur la
recherche plein texte PostgreSQL.

## DT-06 — LLM indépendant du fournisseur
Interface `LLMProvider` avec trois adaptateurs : `anthropic`, `openai_compatible`, `ollama`.
Sélection par `LLM_PROVIDER`. Avec `none` (défaut), l'assistant indique qu'il n'est pas configuré et
le reste de l'application fonctionne. L'endpoint `/api/v1/health/` expose uniquement l'état
« configuré / non configuré » et le nom du fournisseur, jamais la clé.

## DT-07 — Format d'erreur API unique
`core.exceptions.api_exception_handler` renvoie toujours `{detail, code, errors?}` en français.
Les erreurs inattendues sont journalisées côté serveur et masquées côté client (pas de fuite de détails).

## DT-08 — Authentification JWT
SimpleJWT : jeton d'accès de 15 min, jeton de rafraîchissement de 7 jours avec rotation et liste
noire. Throttling DRF activé (60 req/min anonymes, 600 req/min authentifiées).

## DT-09 — Frontend : proxy Vite et client HTTP centralisé
En développement, Vite relaie `/api` vers Django : aucune configuration CORS n'est requise dans le
navigateur. Un unique client Axios (`src/services/api.ts`) convertit toute erreur en `ApiError`
avec un message en français. TanStack Query gère cache, chargement et erreurs.

## DT-10 — Versions figées
Les versions Python sont figées (`==`) dans `requirements.txt` et les versions npm dans
`package-lock.json`, pour une installation reproductible.

## DT-11 — Systèmes nutritionnels multiples (implémenté à l'étape 2)
Aucun système (INRA, NRC…) n'est imposé. Chaque nutriment appartiendra à un système nutritionnel
et portera son unité et sa base d'expression (par kg de matière sèche ou par kg brut). Le moteur
refusera de combiner des valeurs de systèmes ou d'unités incompatibles. La matière sèche sera
utilisée pour toutes les conversions brut ↔ MS.

## DT-12 — Avertissement HSTS preload
`check --deploy` signale `SECURE_HSTS_PRELOAD` non activé. C'est volontaire : l'inscription à la
liste de préchargement des navigateurs est quasi irréversible et doit être décidée au déploiement réel.

## DT-13 — Application `governance` (au lieu de `validation`)
Les sources documentaires, l'historique des validations, l'historique des imports et le journal
d'activité sont regroupés dans une application `governance`. Elle contient aussi la base abstraite
`ValidatedReferenceModel`, commune à toutes les données de référence.

## DT-14 — Règles de validation garanties par PostgreSQL
Les règles critiques ne reposent pas seulement sur le code Python : des contraintes `CHECK` empêchent
qu'une donnée DEMO soit validée et qu'une donnée validée n'ait ni source ni date de validation.
Même une écriture directe en SQL ou un bogue applicatif ne peut pas les contourner.

## DT-15 — Une seule composition validée par ingrédient et nutriment
Plusieurs sources peuvent fournir une valeur pour un même couple ingrédient / nutriment (comparaison,
traçabilité), mais une seule peut être VALIDÉE à la fois (index unique partiel). Le moteur sait ainsi
toujours quelle valeur il utilise et peut la citer.

## DT-16 — Données initiales limitées aux nomenclatures
Les migrations de données ne créent que des listes (espèces, races, catégories, stades, objectifs,
catégories d'ingrédients, définitions de nutriments). Aucune composition, aucun besoin et aucune plage
de croissance ne sont créés. Les définitions INRA / NRC sont à faire vérifier par un expert.

## DT-17 — Date de naissance plutôt qu'âge
L'âge est stocké sous forme de date de naissance, avec un indicateur « estimée » lorsqu'elle provient d'un
âge approximatif. L'âge est ainsi toujours à jour, sans recalcul.

## DT-18 — Trois quantités distinctes pour l'alimentation
Calculée (formule), distribuée (mise à disposition) et consommée (mesurée, facultative). La quantité
consommée n'est jamais déduite de la quantité distribuée, et une contrainte impose consommé ≤ distribué.

## DT-19 — Stockage des jetons côté navigateur
Le jeton d'accès (15 min) reste uniquement en mémoire JavaScript. Le jeton de rafraîchissement est
conservé dans `localStorage` si l'utilisateur coche « Rester connecté », sinon dans `sessionStorage`
(effacé à la fermeture du navigateur). Il est remplacé à chaque renouvellement et révoqué à la déconnexion,
au changement de mot de passe et à la désactivation du compte. Alternative envisagée pour la production :
cookie `HttpOnly` + protection CSRF, qui supprime l'exposition du jeton à un éventuel script malveillant.

## DT-20 — 404 plutôt que 403 pour les données d'un autre éleveur
Une exploitation (et plus tard un animal, une pesée…) à laquelle l'utilisateur n'a pas accès renvoie 404 :
l'API ne confirme même pas son existence. Le 403 est réservé aux ressources visibles mais non modifiables
(expert invité en lecture seule, gestionnaire qui tente de gérer les membres).

## DT-21 — Inscription publique réservée aux éleveurs
L'inscription publique crée toujours un compte ÉLEVEUR (le champ `role` éventuellement envoyé est ignoré).
Les comptes EXPERT et ADMIN sont créés par un administrateur. Un expert n'accède qu'aux exploitations
qui l'invitent, toujours en lecture seule.

## DT-22 — Pas de suppression de comptes ni d'exploitations par l'API
Désactivation uniquement, pour préserver l'historique et la traçabilité. Un administrateur ne peut ni
désactiver son propre compte ni retirer son propre rôle (évite de verrouiller la plateforme).

## DT-23 — Règles d'accès centralisées
`farms/access.py` est le point de vérité unique des droits (lecture, écriture, gestion des membres).
Les classes de permission DRF (`core/permissions.py`) et les vues s'appuient sur lui, ce qui permettra
d'appliquer les mêmes règles aux animaux, pesées, rations et à l'assistant IA.

## DT-24 — Navigation limitée aux modules disponibles
La barre latérale n'affiche que les modules réellement fonctionnels, pour respecter la règle « aucun bouton
sans fonctionnalité ». Les entrées du cahier des charges (animaux, ingrédients, formulation…) sont ajoutées
au fil des étapes.

## DT-25 — Circuit de validation unique
`governance/workflow.py` porte toutes les transitions (soumettre, valider, rejeter, remettre en brouillon) pour
toutes les données de référence. La validation est refusée pour une donnée DEMO, sans source, ou dont la source est
DEMO. Toute modification d'une donnée validée (hors texte libre) la remet automatiquement en brouillon, avec une trace.

## DT-26 — Catalogue commun et ingrédients privés
Le catalogue commun est géré par les experts. Un éleveur peut créer des ingrédients privés à son exploitation
(par exemple un mélange local) ; ils restent invisibles des autres exploitations et doivent eux aussi être validés
par un expert avant d'être utilisés dans un calcul.

## DT-27 — Formules manuelles : analyse sans optimisation
L'étape 4 permet d'enregistrer une ration saisie par l'éleveur (quantités brutes). `formulations/analysis.py` calcule
la MS, les apports et le coût par simple arithmétique sur les compositions validées. Toute donnée manquante est
signalée (MS inconnue, prix absent, nutriment incomplet) et le total correspondant reste vide. Le moteur
d'optimisation (PuLP) est un module distinct, prévu à l'étape 6.

## DT-28 — Validation d'une formule par un expert invité
Un expert ne peut se prononcer que sur les formules d'une exploitation qui l'a invité. Ces actions n'exigent que le
droit de lecture sur l'exploitation (l'expert reste en lecture seule pour tout le reste).

## DT-29 — Import CSV tolérant mais strict
Les lignes valides sont importées, les lignes invalides sont rapportées avec leur numéro. Les animaux importés passent
par le même sérialiseur que la saisie manuelle. Les compositions sont toujours importées en brouillon et un import
ne modifie jamais une valeur validée. Les modèles fournis ne contiennent que les en-têtes.

## DT-30 — Suppression d'un élément utilisé : 409
Les relations protégées (`PROTECT`) renvoient une erreur 409 explicite au lieu d'une erreur serveur, par exemple
pour une source documentaire citée par des compositions.

## DT-31 — GMD calculé uniquement sur mesures réelles
Le GMD n'est calculé qu'entre deux mesures à des dates différentes ; sinon la raison est renvoyée. Le poids initial
déclaré à l'enregistrement compte comme mesure (marqué `origin: initial`). Aucune interpolation ni valeur supposée.

## DT-32 — Plage de suivi la plus spécifique
Parmi les plages VALIDÉES non DEMO compatibles (espèce, race, catégorie, stade, sexe, âge), la plus spécifique est
retenue. Une plage bornée en âge ne s'applique pas si l'âge de l'animal est inconnu.

## DT-33 — Alertes explicables et idempotentes
Chaque alerte enregistre sa règle (`rule_code`), les valeurs déclenchantes et l'objet concerné. Sa clé d'unicité encode
la situation (ex. date de la dernière pesée) : la réévaluation ne crée pas de doublon, résout ce qui n'est plus vrai,
et ne recrée pas une alerte ignorée tant que la situation ne change pas.

## DT-34 — Seuils de suivi = réglages, pas recommandations
Les intervalles par défaut (30 jours entre pesées, 7 jours sans suivi alimentaire) sont des réglages d'organisation,
modifiables par exploitation, et présentés comme tels. Les alertes de croissance ne reposent que sur des plages
validées par un expert et rappellent qu'elles ne constituent pas un diagnostic vétérinaire.

## DT-35 — Prédiction de croissance : interface sans modèle
Une interface `GrowthPredictor` et un point d'enregistrement sont prévus ; l'API indique explicitement qu'aucun
modèle n'est disponible. L'export CSV des pesées prépare la constitution d'un futur jeu d'apprentissage.

## DT-36 — Moteur pur et vérification indépendante
Le moteur ne dépend pas de Django : il reçoit un problème entièrement décrit, ce qui le rend testable sur des jeux
contrôlés et réutilisable. Après résolution, les apports et chaque contrainte sont recalculés sans se fier au
solveur ; une contrainte non vérifiée empêche de présenter la ration comme conforme.

## DT-37 — Un ingrédient incomplet est exclu, jamais complété
Un ingrédient sans teneur validée pour un nutriment contraint (ou sans MS, ou sans prix en mode économique) est exclu
avec sa raison. Le compter à zéro reviendrait à inventer une composition.

## DT-38 — Ingestion de MS obligatoire
Sans bornes d'ingestion de matière sèche dans la référence, le calcul est refusé : dimensionner la ration sur une
ingestion supposée serait une invention. L'utilisateur ne peut pas la saisir lui-même dans cette version.

## DT-39 — Diagnostic d'infaisabilité élastique
En cas d'impossibilité, un second programme autorise un écart sur chaque contrainte et minimise la somme des écarts
relatifs : il désigne un ensemble minimal de contraintes à relâcher et chiffre l'écart. C'est une explication
possible, présentée comme telle.

## DT-40 — Toutes les tentatives de calcul sont enregistrées
Les formules refusées ou impossibles sont conservées avec leur diagnostic, pour l'historique et pour que l'assistant
puisse expliquer « pourquoi la formulation n'a pas pu être calculée ». Elles ne peuvent pas être soumises à un expert.

## DT-41 — Mode démonstration réservé aux exploitations DEMO
Une exploitation DEMO n'utilise que des données DEMO (même non validées) et produit des formules DEMO, non
validables. Une exploitation réelle n'utilise jamais de données DEMO. Les deux mondes ne se mélangent pas.

## DT-42 — PuLP figé en version 3
Le solveur CBC fourni avec PuLP 3 fonctionne hors ligne sous Windows sans installation supplémentaire. Son interface
`PULP_CBC_CMD` est annoncée obsolète pour PuLP 4 : la version reste figée (`PuLP==3.3.2`) et la migration est prévue.

## DT-43 — Exploitation consultée choisie globalement
Un sélecteur dans l'en-tête (mémorisé dans le navigateur) filtre toutes les pages ; « Toutes les exploitations »
est proposé aux utilisateurs qui en ont plusieurs. Les formulaires de création proposent par défaut l'exploitation
sélectionnée si l'utilisateur peut y écrire. L'API reste l'unique garante des droits.

## DT-44 — Chargement à la demande
Les pages et les graphiques (Recharts) sont chargés à leur première ouverture (`React.lazy`), ce qui ramène le
paquet initial sous 500 Ko et accélère l'ouverture sur les connexions mobiles.

## DT-45 — Indicateurs agrégés côté serveur
Le tableau de bord appelle un seul endpoint qui calcule les indicateurs en base (agrégations PostgreSQL) sur les
exploitations accessibles. Chaque indicateur partiel indique sur combien d'enregistrements il repose.

## DT-46 — Valeur absente affichée « — »
Dans toute l'interface, une valeur inconnue s'affiche « — » ou avec un libellé explicite (« Non mesurée »,
« Non calculable »), jamais 0.

## DT-47 — Composants de validation partagés
Un seul composant (`WorkflowActions`) affiche les actions du circuit de validation pour toutes les données de
référence ; il n'affiche que les actions plausibles pour le rôle et le statut, l'API restant seule juge.
Le rejet exige un motif dans l'interface comme dans l'API.

## DT-48 — Le résultat de formulation est affiché tel que calculé
La page de résultat n'ajoute ni ne recalcule aucune valeur : elle présente l'instantané enregistré par le moteur
(apports, contraintes vérifiées, diagnostic, sources, avertissements). Les trois issues ont chacune leur présentation.

## DT-49 — Nutriments proposés selon le système de la référence
Dans la saisie des besoins, seuls les nutriments universels et ceux du système de la référence sont proposés, en plus
du contrôle côté serveur.

## DT-50 — Recherche insensible aux accents sans extension PostgreSQL
Le texte indexé et les questions sont normalisés sans accents en Python avant `to_tsvector('french', …)`.
L'extension `unaccent` n'est pas nécessaire : aucune modification de la configuration de la base.

## DT-51 — Repli systématique sur le plein texte
Sans fournisseur d'embeddings, avec un fournisseur en erreur ou des passages vectorisés avec un autre modèle, la
recherche bascule sur le plein texte et le signale. L'application reste utilisable sans aucun service d'IA externe.

## DT-52 — Pas d'OCR, refus explicite
Un PDF sans texte extractible est marqué « Échec » avec la raison. Aucune reconnaissance approximative n'est tentée
dans cette version : un texte mal reconnu pourrait produire des citations fausses.

## DT-53 — Documents validés uniquement pour la recherche
Comme toute donnée de référence, un document doit être sourcé, indexé et validé par un expert avant d'être
interrogé. Les experts peuvent prévisualiser les brouillons dans la recherche.

## DT-54 — Assistant par outils, sans accès direct à la base
Le LLM n'interroge ni SQL ni l'ORM : il appelle des outils métier qui appliquent les mêmes règles d'accès que l'API
(`farms.access`). Une conversation liée à une exploitation restreint les outils à celle-ci.

## DT-55 — Le LLM explique, le moteur calcule
Aucun outil ne produit de ration ; `get_formula_result` lit le résultat enregistré par le moteur PuLP. Le prompt
système interdit tout calcul nutritionnel, toute donnée inventée et tout diagnostic vétérinaire.

## DT-56 — Provenance enregistrée avec chaque réponse
Chaque outil déclare l'origine de ses données (`database`, `engine`, `document`) ; la rédaction est marquée `llm`.
La provenance, les outils appelés, le modèle, les jetons et la latence sont stockés dans `AIMessage`.

## DT-57 — Claude via le SDK officiel, autres fournisseurs via HTTP
`anthropic` (SDK officiel, modèle par défaut `claude-opus-5-5`, repli côté serveur activé par défaut et
désactivable par `LLM_FALLBACKS`). Les API compatibles OpenAI et Ollama sont appelées avec `httpx`, sans
dépendance supplémentaire. Chaque adaptateur gère la boucle d'outils dans son format natif ; 6 tours au maximum.

## DT-58 — Assistant facultatif
Sans fournisseur configuré, l'API répond 503 avec un message explicite enregistré dans la conversation ;
l'interface désactive la saisie. Aucune autre fonctionnalité n'en dépend.

## DT-59 — Contraintes de la base vérifiées avant l'enregistrement
`ModelCleanMixin` évalue les contraintes `CHECK` du modèle (en plus de `clean()`) et renvoie 400 avec un message
français (`CHECK_MESSAGES`). Sans cela, une valeur interdite seulement par PostgreSQL remontait en 500. Un test
échoue si une nouvelle contrainte atteignable par une saisie n'a pas de message.

## DT-60 — Statut DEMO hérité de l'exploitation
Toute donnée créée dans une exploitation l'est avec `is_demo = exploitation.is_demo` (`FarmScopedViewSet`,
ingrédients privés, formules manuelles) : ni mélange ni contournement possible par la saisie.

## DT-61 — Alertes réévaluées après chaque décision
Soumission, validation, rejet (référentiel) et demande de vérification ou décision (formules) réévaluent
immédiatement les alertes concernées ; une erreur de réévaluation est journalisée sans bloquer l'action, la commande
quotidienne rattrapant l'état.

## DT-62 — Jeu DEMO sous forme de commande versionnée
`load_demo_data` (et non un script ponctuel) : rejouable (`--reset`), réversible (`--remove`) sans toucher aux
données réelles, sans mot de passe dans le code, refusée en production sans `--allow-production`, couverte par des
tests. Valeurs nutritionnelles fictives, jamais validées.

## DT-63 — Libellés d'activité centralisés
`governance.activity.ACTION_LABELS` est l'unique source des libellés des actions journalisées (tableau de bord,
journal). Un test parcourt le code et échoue si une action émise n'a pas de libellé.

## DT-64 — Tests isolés du dossier media/
En configuration de test, `MEDIA_ROOT` pointe vers un dossier temporaire : aucun fichier de test ne subsiste dans
`backend/media/` après le retour arrière de la base.

## DT-65 — Identité visuelle « Indigo & Mil » par jetons
L'identité (couleurs, polices, formes) est définie au niveau des jetons Tailwind (`index.css`) et des composants de
base, pas page par page : les 61 écrans en héritent. Trois motifs encodent une information (tampon = statut,
boucle = identifiant d'animal, bande tissée = signature unique). Polices : Bricolage Grotesque, Atkinson Hyperlegible
Next (lisibilité), IBM Plex Mono. Courbes en segments droits (aucune valeur dessinée entre deux mesures).
Référence : [identite-visuelle.md](identite-visuelle.md).

## DT-66 — Assistant en bouton flottant plutôt que dans le menu
À la demande du porteur du projet, l'assistant quitte la barre latérale (le cahier des charges l'y plaçait) pour un
bouton flottant en bas à droite, au symbole du bélier, disponible sur tous les écrans. Le panneau reste monté : la
conversation survit à la navigation. La vue plein écran `/assistant` est conservée pour l'historique. Une seule
logique (`useAssistantChat`, `ChatThread`) sert aux deux vues.

## DT-67 — Une estimation ne devient jamais une ration
Décision du porteur du projet. Le serveur (`feeding.serializers.ration_blocker`) refuse une ration fondée sur une
formule calculée non validée par un expert ; une formule saisie (ration déjà distribuée) reste autorisée sauf rejet ;
les exploitations DEMO ne sont pas concernées (leurs formules ne sont jamais validables). L'interface applique la même
règle (`rationRules.ts`) pour ne jamais proposer une action refusée.

## DT-68 — Accueil orienté tâches, guide quand l'assistant est éteint
L'écran d'accueil d'un outil quotidien commence par « À faire aujourd'hui », construit à partir des alertes ouvertes,
chaque tâche avec son action directe. Quand aucun fournisseur d'IA n'est configuré, le bouton bélier ouvre un guide et
un glossaire au lieu d'un message technique ; l'indication d'activation n'est montrée qu'aux administrateurs.

## DT-69 — Skills de design installés pour le projet seulement, sans hook
Impeccable, emil-design-eng, taste-skill et unslop sont installés dans `.claude/skills/` (exclus de Git localement).
Le hook automatique d'Impeccable (exécution après chaque modification de fichier) n'est pas activé sans accord explicite.
