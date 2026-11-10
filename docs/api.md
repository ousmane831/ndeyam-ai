# Documentation de l'API

- Documentation interactive : http://localhost:8000/api/docs/ (Swagger) · http://localhost:8000/api/redoc/
- Schéma OpenAPI exporté : [openapi.yaml](openapi.yaml) — régénérer avec
  `python manage.py spectacular --file ../docs/openapi.yaml --validate` (dossier `backend`).
- Préfixe : `/api/v1/`. Format : JSON. Langue des messages : français.

## Authentification

JWT (SimpleJWT). Envoyer `Authorization: Bearer <jeton d'accès>`.

| Jeton | Durée | Remarques |
|---|---|---|
| Accès | 15 min (`JWT_ACCESS_MINUTES`) | À renouveler via `/auth/refresh/` |
| Rafraîchissement | 7 jours (`JWT_REFRESH_DAYS`) | Remplacé à chaque renouvellement ; l'ancien est révoqué |

Les endpoints `register`, `login`, `password-reset` et `password-reset/confirm` sont limités à 10 requêtes / minute
et par adresse IP (réponse 429 au-delà).

| Méthode | Route | Accès | Description |
|---|---|---|---|
| POST | `/auth/register/` | public | Crée un compte **éleveur**, son exploitation et l'adhésion propriétaire. Renvoie `user`, `access`, `refresh` |
| POST | `/auth/login/` | public | `{email, password}` → `user`, `access`, `refresh` |
| POST | `/auth/refresh/` | public | `{refresh}` → nouvelle paire `access` / `refresh` |
| POST | `/auth/logout/` | connecté | `{refresh}` → révoque le jeton (205) |
| GET / PATCH | `/auth/me/` | connecté | Profil ; seuls `first_name`, `last_name`, `phone` sont modifiables |
| POST | `/auth/change-password/` | connecté | `{current_password, new_password}` ; révoque les autres sessions |
| POST | `/auth/password-reset/` | public | `{email}` ; réponse identique que le compte existe ou non |
| POST | `/auth/password-reset/confirm/` | public | `{uid, token, new_password}` ; lien à usage unique |

## Exploitations

| Méthode | Route | Accès |
|---|---|---|
| GET | `/farms/` | Exploitations dont l'utilisateur est membre actif (toutes pour un administrateur). Filtres : `is_active`, `country`, `region` ; `search`, `ordering`, `page`, `page_size` |
| POST | `/farms/` | Éleveur ou administrateur ; le créateur devient propriétaire |
| GET | `/farms/{id}/` | Membre de l'exploitation |
| PATCH | `/farms/{id}/` | Propriétaire, gestionnaire ou administrateur |
| GET | `/farms/{id}/members/` | Membre de l'exploitation |
| POST | `/farms/{id}/members/` | Propriétaire ou administrateur : `{email, role}` avec `role` = `MANAGER` ou `EXPERT` |
| PATCH / DELETE | `/farms/{id}/members/{membership_id}/` | Propriétaire ou administrateur ; le propriétaire ne peut pas être retiré |

Pas de suppression d'exploitation : désactivation via `is_active`.

## Administration des utilisateurs

| Méthode | Route | Accès |
|---|---|---|
| GET | `/admin/users/` | Administrateur. Filtres : `role`, `is_active` ; `search`, `ordering` |
| POST | `/admin/users/` | Administrateur : crée un compte de n'importe quel rôle (ex. experts) |
| GET / PATCH | `/admin/users/{id}/` | Administrateur : rôle, activation, informations. Un administrateur ne peut ni se désactiver ni se rétrograder |

Pas de suppression de compte : désactivation (les sessions en cours sont révoquées).

## Ressources métier (étape 4)

Toutes les listes sont paginées (`page`, `page_size` ≤ 100) et acceptent `search` et `ordering` lorsque c'est pertinent.
Les ressources d'exploitation acceptent le filtre `farm=<id>`.

### Nomenclatures (lecture seule, gérées dans l'administration)

`/species/` (espèces actives ; `?include_inactive=true`), `/breeds/?species=`, `/animal-categories/?species=`,
`/physiological-stages/?species=`, `/production-objectives/`, `/nutrition-systems/`, `/nutrients/?system=&category=`,
`/ingredient-categories/`.

### Données d'exploitation (isolées par exploitation)

| Ressource | Route | Particularités |
|---|---|---|
| Lots | `/groups/` | `animals_count` ; nom unique par exploitation |
| Animaux | `/animals/` | Filtres : `species`, `breed`, `sex`, `group`, `group__isnull`, `status`, `category`, `physiological_stage`, `is_demo`. Par défaut seuls les animaux présents sont listés. `estimated_age_months` (écriture) calcule une date de naissance estimée |
| | `POST /animals/{id}/archive/` | `{status: SOLD \| DEAD \| ARCHIVED, note?}` |
| | `POST /animals/{id}/restore/` | Remet l'animal parmi les présents |
| | `GET /animals/{id}/history/` | Chronologie : pesées, observations, rations, distributions |
| | `GET /animals/export/`, `POST /animals/import/` | CSV (voir [import-donnees.md](import-donnees.md)) |
| Observations | `/animals/{id}/observations/` | GET, POST, DELETE |
| Prix des ingrédients | `/ingredient-prices/` | Prix **par kg brut** ; `?latest=true` : dernier prix par ingrédient |
| Formules | `/formulas/` | Création manuelle : `manual_items: [{ingredient, quantity_as_fed_kg}]` → analyse (MS, apports, coût) à partir des seules données validées |
| | `POST /formulas/{id}/submit-review/` | Propriétaire / gestionnaire |
| | `POST /formulas/{id}/validate/`, `/reject/` | Expert invité sur l'exploitation ou administrateur (`comment` obligatoire pour un rejet) |
| | `GET /formulas/compare/?ids=1,2` | 2 à 5 formules |
| Rations | `/rations/` | Un animal **ou** un lot ; `POST /rations/{id}/end/ {end_date}`. Formule calculée : **validée par un expert obligatoire** (400 sinon) ; formule saisie : autorisée sauf rejet ; exploitation DEMO : non concernée |
| Historique alimentaire | `/feeding-records/` | Quantité calculée et coût dérivés automatiquement ; consommée = mesurée uniquement. `GET /feeding-records/summary/`, `/export/` |

### Référentiel (lecture par tous, écriture par les experts / administrateurs)

| Ressource | Route | Particularités |
|---|---|---|
| Sources documentaires | `/sources/` | Suppression refusée (409) si la source est utilisée |
| Ingrédients | `/ingredients/` | `category_code` ; `ready_for_engine` (liste) : matière sèche utilisable par le moteur. `?scope=catalog\|private`. Catalogue commun : experts ; ingrédient privé (`farm`) : éleveurs de l'exploitation. Le détail contient `composition_table` (une ligne par nutriment, valeur inconnue explicite) |
| Compositions | `/compositions/` | `POST /compositions/import/` (CSV, experts) |
| Références nutritionnelles | `/nutritional-references/` | Besoins inclus en lecture |
| Besoins | `/requirements/?reference=` | Toute modification remet la référence validée en brouillon |
| Contraintes d'incorporation | `/inclusion-constraints/` | Bornes en % de MS, ingrédient **ou** catégorie |

### Circuit de validation

Sur ingrédients, compositions, références et contraintes :
`POST …/{id}/submit/`, `…/validate/`, `…/reject/` (commentaire obligatoire), `…/revert/`.
Validation impossible pour une donnée DEMO, sans source ou dont la source est DEMO. Toute modification d'une donnée
validée (hors champs de texte libre) la remet en brouillon. Chaque décision est enregistrée.

### Gouvernance

| Route | Accès |
|---|---|
| `/validation-records/` | Experts et administrateurs |
| `/import-batches/` | Chacun ses imports ; tout pour les administrateurs |
| `/activity-logs/` | Administrateurs |

## Croissance et alertes (étape 5)

### Pesées et croissance

| Route | Description |
|---|---|
| `/weighings/` | CRUD des pesées (`weight_kg`, unité `kg`, `method` : `SCALE`, `TAPE`, `VISUAL`). Filtres : `animal`, `animal__group`, `weighed_on__gte/lte`. Une pesée par animal et par jour ; pas de date future ni antérieure à la naissance |
| `POST /weighings/bulk/` | Séance de pesée `{weighed_on, method, entries: [{animal, weight_kg, observations?}]}` — tout ou rien, erreurs par ligne |
| `GET /weighings/export/` | CSV des pesées (base d'un futur jeu d'apprentissage) |
| `GET /growth/animals/{id}/` | Points de poids (dont poids initial déclaré), écarts, GMD par intervalle et global, plage de suivi applicable et position (`below` / `within` / `above`) |
| `GET /growth/groups/{id}/` | Dernier poids et GMD de chaque animal du lot, GMD moyen (animaux mesurables uniquement) |
| `GET /growth/overview/` | Dernières pesées, nombre de pesées sur 30 jours, animaux jamais pesés |
| `GET /growth/prediction-status/` | `available: false` : aucun modèle de prédiction n'est entraîné |
| `/growth-ranges/` | Plages de suivi du GMD (référentiel : experts, circuit de validation) |

**GMD = (poids final − poids initial) / nombre de jours écoulés**, en g/jour. Non calculé (avec la raison) si moins de
deux mesures à des dates différentes. Les estimations visuelles sont signalées comme moins fiables.

### Alertes

| Route | Description |
|---|---|
| `/alerts/` | Alertes des exploitations de l'utilisateur et alertes qui lui sont adressées ; ouvertes par défaut (`?status=` pour les autres). Chaque alerte contient `rule_code`, `trigger_data` (valeurs déclenchantes) et `target` |
| `POST /alerts/{id}/acknowledge/`, `/resolve/`, `/dismiss/` | Propriétaire / gestionnaire (ou destinataire). Une alerte ignorée n'est pas recréée tant que la situation est identique |
| `GET /alerts/summary/` | Nombre d'alertes ouvertes par niveau et par type |
| `POST /alerts/evaluate/` | Réévaluation immédiate (`{farm?}`) |
| `/alert-rules/` | Réglages par exploitation (propriétaire / gestionnaire) ou par défaut (administrateurs) : paramètres, activation |
| `GET /alert-rules/definitions/` | Types de règles, paramètres, valeurs par défaut et bornes |

| Type | Déclenchement | Paramètre (défaut) |
|---|---|---|
| `WEIGHING_REMINDER` | Animal non pesé depuis l'intervalle | `interval_days` (30) |
| `FOLLOW_UP_REMINDER` | Ration en cours sans distribution enregistrée | `days_without_record` (7) |
| `MISSING_DATA` | Date de naissance, poids, catégorie ou stade manquants | — |
| `GROWTH_OUT_OF_RANGE` | Dernier GMD hors d'une plage de suivi **validée** (jamais un diagnostic vétérinaire) | — |
| `FORMULA_TO_REVIEW` | Formule en attente de vérification | — |
| `REFERENCE_TO_VALIDATE` | Données de référence en attente (experts et administrateurs) | — |

Les valeurs par défaut sont des réglages de suivi modifiables, pas des recommandations zootechniques.
Les alertes sont réévaluées après chaque pesée, à la demande, et par la commande quotidienne `evaluate_alerts`.

## Moteur de formulation (étape 6)

| Route | Description |
|---|---|
| `GET /formulas/offline-pack/?farm=` | Paquet de calcul hors ligne (propriétaire ou gestionnaire ; 404 sinon) : références utilisables avec leurs critères et le problème préparé par `build_problem` (mêmes données et règles que le calcul en ligne), profil de chaque lot, objectifs, animaux présents avec leur dernier poids. Quelques Ko |
| `POST /formulas/calculate/` | Calcul par optimisation (`mode` : `ECONOMIC` ou `BALANCED`). Avec `group` (sans `animal`) : profil déduit des animaux présents du lot (espèce, race, catégorie et stade les plus fréquents, poids moyen des dernières pesées, âge moyen ; les valeurs transmises restent prioritaires), effectif dans `result_snapshot.profile.head_count`, explications dans `warnings`. Lignes de formule : `ingredient_category` (code). Profil d'animal, ingrédients avec prix et disponibilités facultatifs. Enregistre la formule (statut `ESTIMATED`, `INFEASIBLE` ou `REFUSED`) sauf `save: false`. Détail complet : [moteur-formulation.md](moteur-formulation.md) |

Une formule `ESTIMATED` peut être soumise à un expert (`submit-review`) ; une formule refusée ou impossible ne le peut pas.

## Tableau de bord (étape 7)

`GET /dashboard/?farm=` : animaux présents (total, par espèce, catégorie, sexe), lots actifs, pesées des 30 derniers
jours et animaux jamais pesés, 5 dernières pesées, poids moyen mensuel des pesées (6 mois), rations en cours,
coût estimé des distributions sur 30 jours (avec le nombre de distributions sans coût connu), alertes ouvertes,
10 dernières activités. Toutes les valeurs proviennent des données enregistrées ; une valeur non calculable est vide.

`GET /alerts/?animal=<id>` : alertes concernant un animal.

Une exploitation inaccessible dans `?farm=` renvoie **404** (même règle que le reste de l'API). Les activités
récentes portent un libellé français (`label`) ; le journal `/activity-logs/` expose `action` et `action_label`.

## Base documentaire (étape 9)

| Route | Description |
|---|---|
| `GET /documents/` | Documents validés (tous les documents pour les experts et administrateurs) avec `chunks_count`, `embedded_chunks` |
| `POST /documents/` | Import d'un PDF (`multipart` : `file`, `title`, `description?`, `source?`, `reference_date?`, `is_demo?`) — experts / administrateurs. Doublon refusé (`duplicate_document`) |
| `PATCH / DELETE /documents/{id}/` | Experts / administrateurs |
| `POST /documents/{id}/submit/`, `/validate/`, `/reject/`, `/revert/` | Circuit de validation (source et indexation réussie obligatoires) |
| `POST /documents/{id}/reindex/` | Recalcul des passages et embeddings |
| `GET /documents/{id}/chunks/` | Passages indexés |
| `GET /documents/{id}/file/` | Téléchargement du PDF |
| `GET /documents/search/?q=&k=&include_unvalidated=` | Recherche (sémantique ou plein texte) avec citations ; `include_unvalidated` réservé aux experts |
| `GET /documents/status/` | Mode de recherche disponible (sans exposer de clé) |

Voir [architecture-ia.md](architecture-ia.md).

## Assistant (étape 10)

| Route | Description |
|---|---|
| `GET /assistant/conversations/status/` | `configured`, `provider`, `model`, `message` (jamais la clé) |
| `GET / POST /assistant/conversations/` | Conversations de l'utilisateur ; `farm` facultatif (doit être accessible) |
| `GET / PATCH / DELETE /assistant/conversations/{id}/` | Détail avec `messages` (provenance, outils, modèle) ; 404 pour un autre utilisateur |
| `POST /assistant/conversations/{id}/messages/` | `{"content": "…"}` (2 000 caractères max.) → `[question, réponse]` ; **201**, ou **503** avec `error_code=not_configured` si aucun fournisseur n'est configuré. Débit : 20/min |

Voir [architecture-ia.md](architecture-ia.md#2-assistant-conversationnel--étape-10).

## Codes de réponse et format des erreurs

```json
{ "detail": "Message lisible", "code": "code_machine", "errors": { "champ": ["message"] } }
```

| Code | Signification |
|---|---|
| 400 | Données invalides (`errors` détaille chaque champ). Les règles garanties par la base (contraintes `CHECK` : valeurs négatives, bornes inversées…) sont vérifiées avant l'enregistrement et renvoient aussi 400 avec un message en français |
| 401 | Non authentifié ou jeton invalide / expiré |
| 403 | Ressource visible mais action non autorisée (ex. expert qui tente une modification) |
| 409 | Suppression impossible : l'élément est encore utilisé (ex. source citée par des compositions) |
| 404 | Ressource inexistante **ou inaccessible** (on ne révèle pas l'existence des données d'un autre éleveur) |
| 405 | Méthode non autorisée (ex. suppression d'un compte) |
| 429 | Trop de requêtes |
| 500 | Erreur interne (détails journalisés côté serveur uniquement) |

## Santé

`GET /health/` (public) : état de PostgreSQL et configuration de l'assistant (sans jamais exposer de clé).
