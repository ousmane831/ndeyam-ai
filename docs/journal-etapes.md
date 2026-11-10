# Journal des étapes

## Étape 1 — Initialisation complète du projet (07/11/2026) ✅

### Réalisé
- Dépôt Git initialisé (branche `main`), `.gitignore` excluant `.env`, environnements virtuels, `node_modules`, builds.
- **Backend** : projet Django 5.2.19 avec réglages découpés (`base`, `development`, `production`, `test`),
  configuration par `.env`, DRF, JWT (SimpleJWT + liste noire), OpenAPI (drf-spectacular), CORS, filtres,
  pagination, throttling, format d'erreur unique, journalisation.
- Application `core` : modèle abstrait `TimeStampedModel`, pagination, gestionnaire d'erreurs, endpoint `/api/v1/health/`
  (vérification réelle de PostgreSQL, état de configuration de l'assistant sans exposer de secret).
- Application `accounts` : modèle `User` personnalisé (e-mail comme identifiant, rôles ADMIN / ELEVEUR / EXPERT),
  administration Django. Endpoints d'authentification prévus à l'étape 3.
- Script `scripts/init_db.py` : création d'un rôle et d'une base dédiés sans toucher la configuration du serveur.
- **Frontend** : React 19, Vite 8, TypeScript 7 (mode strict), Tailwind CSS 4 (thème NDEYAM AI), React Router,
  TanStack Query, Axios centralisé, arborescence `src/` du cahier des charges, page d'état du système branchée
  sur l'API réelle, proxy de développement `/api` → Django.
- Outillage : pytest + pytest-django, Ruff (lint + format), Vitest + Testing Library, oxlint.
- Documentation : README, installation Windows et Linux, décisions techniques, ce journal.

### Base de données
- Base `ndeyamai` (utilisateur `ndeyamai`) fournie par le propriétaire du projet.
- Elle contenait le schéma d'un projet antérieur (02/11/2026 : 12 tables, 1 compte administrateur) incompatible
  avec le nouveau modèle `User`. Sur décision du propriétaire, ces 12 tables ont été supprimées et les migrations
  réappliquées. Aucune autre base n'a été modifiée.

### Vérifications
| Contrôle | Résultat |
|---|---|
| `manage.py check` | aucun problème |
| `manage.py check --deploy` (production) | 1 avertissement volontaire (HSTS preload, voir DT-12) |
| `makemigrations --check` | aucune migration manquante |
| `migrate` | toutes les migrations appliquées sur `ndeyamai` |
| Ruff | aucune erreur |
| pytest | 14 tests réussis |
| `tsc -b`, oxlint | aucune erreur |
| Vitest | 5 tests réussis |
| `vite build` | build de production réussi |
| Test de bout en bout | Django + Vite lancés : `/api/v1/health/` OK en direct et via le proxy, Swagger 200, admin 200 |

### Points d'attention
- Le rôle PostgreSQL `ndeyamai` est **superutilisateur** et son mot de passe est identique à son nom.
  Acceptable en développement local uniquement ; à remplacer par un rôle non superutilisateur et un mot de passe
  fort avant toute exposition réseau.
- Les e-mails (réinitialisation du mot de passe) s'affichent dans la console tant qu'aucun SMTP n'est configuré.

## Étape 2 — Modèles de données et migrations (07/11/2026) ✅

### Réalisé
- 10 nouvelles applications : `governance`, `farms`, `animals`, `nutrition`, `formulations`, `feeding`,
  `growth`, `alerts`, `knowledge_base`, `assistant` (+ `django.contrib.postgres`).
- 36 modèles couvrant les 22 entités du cahier des charges et les tables de support nécessaires
  (voir [schema-base-donnees.md](schema-base-donnees.md)).
- Base abstraite `ValidatedReferenceModel` : statut de validation, DEMO, source, validateur, avec contraintes PostgreSQL.
- Architecture multi-systèmes nutritionnels (INRA, NRC, extensible) sans mélange possible des unités.
- Prise en compte de la matière sèche : bases d'expression contraintes et module `nutrition/units.py`.
- Isolation par exploitation : `Farm.objects.accessible_by(user)`, adhésions OWNER / MANAGER / EXPERT.
- Interface d'administration couvrant les 36 modèles : 32 pages dédiées + 4 tableaux intégrés à leur parent
  (observations dans l'animal, besoins dans la référence, ingrédients dans la formule, messages dans la conversation).
  Les historiques sont en lecture seule.
- Migrations de données : nomenclatures uniquement (aucune valeur nutritionnelle).

### Vérifications
| Contrôle | Résultat |
|---|---|
| `manage.py check` | aucun problème |
| `makemigrations --check` | aucune migration manquante |
| `migrate` sur `ndeyamai` | 14 nouvelles migrations appliquées |
| Réversibilité | `migrate farms zero` puis `migrate` : annulation et réapplication sans erreur |
| Contraintes en base | 83 contraintes CHECK actives (plus les contraintes d'unicité) |
| Données nutritionnelles en base | 0 composition, 0 besoin, 0 référence (aucune valeur inventée) |
| Ruff | aucune erreur |
| pytest | **162 tests réussis**, aucun avertissement |

Les 162 tests couvrent : règles de validation et DEMO, isolation des exploitations, cohérence espèce / race / lot,
contraintes nutritionnelles, incompatibilité des systèmes, conversions MS, formules, rations,
quantités distribuées / consommées, pesées, alertes, documents RAG, conversations, et l'affichage
de chaque page d'administration (liste et ajout).

### Points d'attention
- Les définitions de nutriments INRA (UFL, UFV, PDI) et NRC (EM, PM) sont à faire vérifier par un expert.
- Les règles de cohérence applicatives (méthodes `clean()`) seront appelées par les sérialiseurs de l'API (étape 4).

## Étape 3 — Authentification et rôles (07/11/2026) ✅

### Backend
- Endpoints `/api/v1/auth/` : inscription (compte éleveur + exploitation + adhésion propriétaire, transaction
  atomique), connexion, renouvellement avec rotation, déconnexion avec révocation, profil, changement de mot de passe,
  réinitialisation par e-mail (lien à usage unique, sans divulgation de l'existence d'un compte).
- Révocation de toutes les sessions au changement / à la réinitialisation du mot de passe et à la désactivation.
- Limitation de débit des endpoints d'authentification (10 / min).
- Règles d'accès centralisées (`farms/access.py`) et permissions DRF (`core/permissions.py`).
- API des exploitations et de leurs membres (invitation d'experts en lecture seule, gestionnaires).
- API d'administration des utilisateurs (création d'experts, rôles, activation).
- Journal d'activité alimenté (inscription, connexion, déconnexion, profil, mots de passe, exploitations, membres, administration).
- Schéma OpenAPI sans avertissement, exporté dans `docs/openapi.yaml` ; documentation `docs/api.md`.

### Frontend
- Design system : boutons, champs (texte, mot de passe avec affichage, liste), alertes, badges, cartes, états vides,
  fenêtres modales, confirmations, pagination.
- Gestion de session : jeton d'accès en mémoire, renouvellement automatique mutualisé, fin de session propre.
- Pages : connexion, inscription, mot de passe oublié, nouveau mot de passe, tableau de bord (données réelles),
  paramètres (profil, mot de passe, exploitations et membres), administration des utilisateurs, page 404.
- Mise en page responsive avec barre latérale (tiroir sur mobile) et routes protégées par rôle.

### Vérifications
| Contrôle | Résultat |
|---|---|
| pytest | **217 tests réussis** (55 nouveaux sur l'API) |
| Ruff, `manage.py check`, `makemigrations --check` | aucun problème, aucune migration nécessaire |
| Schéma OpenAPI | validé, 0 avertissement |
| Vitest | **27 tests réussis** (22 nouveaux) |
| `tsc -b`, oxlint, `vite build` | aucune erreur ni avertissement de lint |
| Test de bout en bout (via le proxy Vite, vrais serveurs) | inscription avec accents, connexion, profil, isolation (404 sur la ferme d'un autre éleveur), 403 sur l'espace admin, rotation et révocation des jetons, déconnexion, réinitialisation tracée dans le journal ; données de test supprimées ensuite |

### Limites connues
- Sans SMTP configuré, l'e-mail de réinitialisation s'affiche dans la console du serveur Django.
- Un jeton d'accès déjà émis reste valide jusqu'à son expiration (15 min max.) après une révocation.
- Le build signale un paquet JavaScript > 500 ko (Recharts sera chargé à la demande quand les graphiques arriveront).

## Étape 4 — API métier (07/11/2026) ✅

### Réalisé (backend uniquement ; les pages arrivent aux étapes 7–8)
- Briques communes : vues isolées par exploitation (`core/viewsets.py`), application des règles `clean()` des modèles
  dans l'API, circuit de validation (`governance/workflow.py`), import / export CSV (`core/csv_io.py`).
- Animaux : CRUD, âge estimé, archivage / restauration, historique chronologique, observations, filtres, recherche,
  export et import CSV. Lots.
- Nutrition : nomenclatures, ingrédients (catalogue commun + privés), tableau de composition avec valeurs inconnues
  explicites, compositions, import CSV des compositions, export, prix (dernier prix), références, besoins,
  contraintes d'incorporation, sources documentaires.
- Formules manuelles avec analyse (MS, apports, coût) sur données validées uniquement, vérification par un expert
  invité, comparaison.
- Rations (animal ou lot, fin de ration), historique alimentaire (quantité calculée et coût dérivés, consommation
  uniquement mesurée), synthèse, export.
- Gouvernance : historique des validations, des imports, journal d'activité.
- Migration `formulations.0003` : quantités de MS facultatives dans une formule (MS inconnue).
- Modèles CSV vides (`backend/templates/csv/`) et guide [import-donnees.md](import-donnees.md).

### Vérifications
| Contrôle | Résultat |
|---|---|
| pytest | **289 tests réussis** (72 nouveaux) |
| Ruff, `check`, `makemigrations --check` | aucun problème |
| Schéma OpenAPI | 99 routes, validé, 0 avertissement ; exporté dans `docs/openapi.yaml` |
| Serveur de développement | nouvelles routes servies, protégées (401 sans jeton) |

Points couverts par les tests : isolation de chaque ressource (404), lecture seule de l'expert invité (403), choix
d'une exploitation, d'un lot ou d'une formule d'un autre éleveur refusé, cohérence espèce / race, numéros en double,
circuit de validation complet (source, DEMO, commentaire de rejet, remise en brouillon), import CSV ligne à ligne,
analyse exacte d'une ration sur valeurs de contrôle, MS et prix manquants signalés, données en brouillon ignorées.

### Limites connues
- Les pesées sont visibles dans l'historique mais leur API (saisie, GMD, alertes) est l'objet de l'étape 5.
- Les formules calculées par optimisation arrivent à l'étape 6.
- Aucune donnée nutritionnelle n'est présente en base : l'analyse des rations reste « incomplète » tant que des
  compositions n'ont pas été importées et validées.

## Étape 5 — Croissance et alertes (07/11/2026) ✅

### Réalisé (backend)
- Calculs purs (`growth/calculations.py`) : GMD par intervalle et global, écarts de poids, refus motivé si moins de
  deux mesures à dates différentes, signalement des estimations visuelles.
- Pesées : saisie unitaire, séance de pesée par lot (tout ou rien), export CSV ; poids initial déclaré pris en compte.
- Suivi individuel (courbe, GMD, comparaison à la plage validée la plus spécifique) et collectif (GMD moyen du lot).
- Plages de suivi du GMD : référentiel validé par les experts.
- Moteur d'alertes (`alerts/engine.py`) : 6 règles explicables, réglages par exploitation, résolution automatique,
  non-recréation des alertes ignorées, réévaluation après chaque pesée, à la demande et par commande quotidienne.
- API des alertes (consultation, prise en compte, résolution, ignorer, synthèse) et des règles.
- Point d'extension pour un futur modèle de prédiction (`growth/prediction.py`) : **aucun modèle n'est fourni**.
- Migration `alerts.0002` : une règle par type et par exploitation.

### Vérifications
| Contrôle | Résultat |
|---|---|
| pytest | **335 tests réussis** (46 nouveaux) |
| Ruff, `check`, `makemigrations --check` | aucun problème |
| Schéma OpenAPI | validé, 0 avertissement |
| Scénario réel sur le serveur de développement | animal → alertes « informations manquantes » et « pesée » ; 2 pesées (20 → 23 kg en 30 j) → GMD 100,0 g/j ; nouvelle pesée → rappel résolu automatiquement ; prédiction indisponible. Données de test supprimées |

### Limites connues
- Aucune plage de suivi n'est en base : les alertes de croissance ne se déclencheront qu'après saisie et validation
  de plages sourcées par un expert.
- Les données privées en attente (ingrédients d'exploitation) ne sont pas comptées dans l'alerte des experts.

## Étape 6 — Moteur de formulation (07/11/2026) ✅

### Réalisé (backend)
- Moteur en Python pur (`formulations/engine/`), indépendant de Django et de l'assistant :
  contrôles préalables (refus motivés, exclusions), programme linéaire PuLP / CBC, modes économique et équilibré,
  diagnostic d'infaisabilité par programme élastique, recalcul indépendant de chaque contrainte.
- Service de sélection des données (`formulations/engine_service.py`) : référence validée la plus spécifique,
  compositions validées du bon système uniquement, prix de l'exploitation, disponibilités, contraintes d'incorporation
  validées, séparation stricte des données DEMO.
- `POST /api/v1/formulas/calculate/` : préremplissage depuis un animal, enregistrement de toutes les tentatives
  (y compris refusées ou impossibles, pour pouvoir les expliquer), mode sans enregistrement.
- Documentation : [moteur-formulation.md](moteur-formulation.md).

### Vérifications
| Contrôle | Résultat |
|---|---|
| pytest | **364 tests réussis** (29 nouveaux : 15 sur le moteur seul, 14 sur la chaîne complète), y compris avec les avertissements d'obsolescence traités en erreurs |
| Ruff, `check`, `makemigrations --check` | aucun problème, aucune migration nécessaire |
| Schéma OpenAPI | validé, 0 avertissement |
| Essai réel sur la base `ndeyamai` (aucune donnée nutritionnelle) | calcul **refusé** avec raison explicite, solveur non lancé, formule enregistrée, soumission à un expert refusée |

### Défauts trouvés et corrigés pendant l'étape
- Le diagnostic d'infaisabilité ignorait les écarts : une variable PuLP était testée comme booléen (`écart or 0`).
- Passage aux API PuLP non obsolètes (`add_variable`).

### Limites connues
- Voir [moteur-formulation.md § 6](moteur-formulation.md#7-limites-connues) (rapports entre nutriments non gérés,
  diagnostic proposant une explication parmi d'autres, PuLP figé en version 3).

## Étape 7 — Frontend : animaux, croissance, tableau de bord, alertes (07/11/2026) ✅

### Réalisé
- **Backend** : endpoint `/dashboard/` (indicateurs réels uniquement) et filtre des alertes par animal.
- **Socle frontend** : sélecteur d'exploitation global (mémorisé), composants de page (en-tête, onglets, cartes
  d'indicateurs, listes de définitions), import CSV avec compte rendu ligne par ligne, export CSV authentifié,
  formatage à la française (« — » pour une valeur absente, jamais 0).
- **Pages** :
  - Mes animaux : recherche, filtres (espèce, race, sexe, lot, statut), pagination, export, import.
  - Ajout / modification d'un animal : âge connu, estimé ou inconnu ; listes dépendantes de l'espèce.
  - Fiche animal à 6 onglets : informations générales, pesées et croissance (saisie, courbe, GMD, plage de suivi),
    historique alimentaire, rations, observations, suivi et alertes ; sortie, retour, suppression avec confirmation.
  - Mes troupeaux : lots (création, modification, suppression avec confirmation).
  - Suivi de croissance : séance de pesée par lot (tout ou rien, erreurs par ligne), GMD du lot.
  - Alertes et rappels : filtres, explication de chaque alerte, prise en compte, résolution, ignorer, vérification
    immédiate.
  - Paramètres : réglages des alertes par exploitation.
  - Tableau de bord : indicateurs, répartition, évolution du poids, dernières pesées, rations en cours, alertes,
    activités récentes, avec états vides explicites.
- **Performance** : graphiques Recharts et pages chargés à la demande (paquet principal 493 Ko au lieu de 606 Ko).
- **Documentation** : [guide-utilisateur.md](guide-utilisateur.md).

### Vérifications
| Contrôle | Résultat |
|---|---|
| pytest | **367 tests réussis** (3 nouveaux : tableau de bord, filtre des alertes) |
| Vitest | **49 tests réussis** (22 nouveaux : formulaire animal, liste, tableau de bord, alertes, formatage, erreurs imbriquées) |
| `tsc -b`, oxlint, Ruff | aucune erreur ni avertissement |
| `vite build` | réussi, sans avertissement de taille |
| Parcours réel via le proxy Vite | tableau de bord vide sans valeur inventée ; lot, 2 animaux, 2 séances de pesée ; GMD du lot 91,7 g/j (vérifié à la main) ; tendance mensuelle ; séance invalide refusée avec l'erreur sur la ligne ; 5 pages servies. Données de test supprimées |

### Limites connues
- Aucun test de bout en bout dans un vrai navigateur (pas d'outil de pilotage de navigateur disponible) : les pages
  sont couvertes par des tests de composants et l'API par des parcours réels.
- La saisie des rations et des distributions arrive à l'étape 8 (les onglets de la fiche animal les affichent déjà).

## Étape 8 — Frontend : ingrédients, références, formulation, rations, traçabilité (07/11/2026) ✅

### Réalisé
- **Ingrédients** : liste filtrable, création (catalogue commun pour les experts, privé pour les éleveurs), import CSV
  des compositions avec choix de la source, export ; fiche avec tableau de composition (valeur utilisée ou
  « Inconnue », toutes les valeurs et leur source), ajout de valeurs, circuit de validation, prix de l'exploitation.
- **Références nutritionnelles** : liste, création, fiche avec besoins (nutriments limités au système de la référence),
  contraintes d'incorporation, circuit de validation.
- **Formulation** : calcul optimisé (mode, animal / lot / profil, référence automatique ou choisie, ingrédients avec prix
  et stocks), ration saisie, formules enregistrées, comparaison ; page de résultat pour les trois issues (estimation,
  impossible avec diagnostic, refus motivé), vérification par un expert, création de ration.
- **Historique des rations** : rations (création, fin, suppression) et distributions (saisie, synthèse, export).
- **Traçabilité des données** : sources, historique des validations, importations, journal d'activité.
- Navigation complète selon le cahier des charges ; composants partagés de validation.
- Documentation : [guide-administrateur.md](guide-administrateur.md), guide utilisateur complété.

### Défaut trouvé et corrigé
- La fenêtre modale reprenait le focus à chaque rendu : dans un champ contrôlé (motif de rejet, note de sortie,
  création de ration…), la saisie perdait le focus après chaque caractère. Corrigé dans `Modal` et couvert par un test
  de non-régression.

### Vérifications
| Contrôle | Résultat |
|---|---|
| Vitest | **68 tests réussis** (19 nouveaux) |
| `tsc -b`, oxlint | aucune erreur |
| `vite build` | réussi, paquet principal 435 Ko |
| pytest | 367 tests réussis (aucun changement backend) |
| Parcours réel via le proxy Vite, avec un expert et un éleveur | référentiel saisi et validé ; rejet par l'éleveur refusé (403) ; calcul économique 50 / 50 % pour 200 FCFA/j, contraintes « ok » ; ration et distribution à 10 animaux : calculée 10 kg, coût 2 100 FCFA ; tableau de bord à jour ; soumission à l'expert ; 8 pages servies. Toutes les données de test supprimées, y compris du référentiel |

### Limites connues
- Pas de test dans un vrai navigateur (outil indisponible) : couverture par tests de composants et parcours API réels.
- Les plages de suivi de croissance se gèrent par l'API ou l'administration des données (pas d'écran dédié).
- Les listes de choix (animaux, ingrédients, formules) sont limitées à 100 éléments.

## Étape 9 — Base documentaire RAG (07/11/2026) ✅

### Réalisé
- Import de PDF (doublons refusés par empreinte), extraction page par page (pypdf), PDF scanné signalé (pas d'OCR).
- Découpage en passages avec chevauchement, coupure en fin de phrase et pages conservées pour la citation.
- Index plein texte PostgreSQL français, insensible aux accents (normalisation en Python, sans extension).
- Fournisseurs d'embeddings `openai_compatible` et `ollama` ; repli automatique sur le plein texte s'ils sont absents
  ou en erreur ; identifiant du modèle stocké avec chaque passage ; réindexation.
- Stockage vectoriel `NumpyVectorStore` derrière une interface prête pour pgvector.
- Circuit de validation des documents (source et indexation obligatoires) ; seuls les documents validés et non DEMO
  sont interrogés.
- API complète et écran « Base documentaire » : recherche avec citations, import, passages, téléchargement,
  réindexation, validation.
- Documentation : [architecture-ia.md](architecture-ia.md).

### Défaut trouvé et corrigé
- Un passage commençant juste après une page vide était attribué à la page précédente (citation fausse) :
  le découpage commence désormais sur le premier caractère de texte.

### Vérifications
| Contrôle | Résultat |
|---|---|
| pytest | **393 tests réussis** (26 nouveaux : découpage, import, PDF scanné, doublons, validation, visibilité, recherche française sans accents, embeddings simulés, repli, stockage vectoriel, formats des fournisseurs, absence de clé dans les réponses, réindexation) |
| Vitest | **71 tests réussis** (3 nouveaux) |
| Ruff, `tsc -b`, oxlint, `check`, `makemigrations --check`, schéma OpenAPI | aucun problème, aucune migration nécessaire |
| Parcours réel via le proxy Vite | import et indexation ; invisible pour l'éleveur avant validation ; validation refusée sans source puis acceptée ; recherches sans accents trouvées avec citation « titre, p. 1-2 — source » ; téléchargement ; doublon et import par un éleveur refusés. Données et fichier de test supprimés |

### Incident pendant les essais
- Le serveur de développement s'était rechargé pendant la réécriture d'un fichier par le formateur et ne voyait pas
  les nouvelles routes : un simple `touch config/urls.py` a provoqué un rechargement propre.

### Limites connues
- Pas d'OCR ; traitement synchrone à l'import ; recherche sémantique non testée avec un vrai fournisseur
  (aucun n'est configuré) — les formats d'appel sont vérifiés par des tests avec un serveur simulé.

## Étape 10 — Assistant NDEYAM AI (07/11/2026) ✅

### Réalisé
- Adaptateurs LLM (`assistant/llm.py`) : Claude (SDK officiel `anthropic` 2.6.0, `claude-opus-5-5` par défaut,
  repli côté serveur, gestion du refus et de la troncature), API compatibles OpenAI et Ollama (httpx) ;
  erreurs normalisées ; configuration dans `.env` (`LLM_FALLBACKS` ajouté).
- 10 outils métier (`assistant/tools.py`) exécutés avec les droits de l'utilisateur, avec provenance.
- Orchestrateur : prompt système (pas de calcul, pas d'invention, pas de diagnostic vétérinaire, citations),
  historique, enregistrement de la provenance, des outils, des jetons et de la latence ; journal d'activité.
- API `/assistant/conversations/` (privée par utilisateur, débit 20/min) et `status/` sans clé.
- Écran « Assistant Ndeyam AI » : conversations, suggestions, provenance sous chaque réponse, avertissements,
  état non configuré explicite (saisie désactivée).
- Documentation : architecture IA, API, guides, décisions DT-54 à DT-58, OpenAPI régénéré.

### Vérifications
| Contrôle | Résultat |
|---|---|
| pytest | **431 tests réussis** (40 nouveaux : configuration, statut sans clé, réponse non configurée, provenance, historique, erreurs fournisseur, confidentialité des conversations, isolement des exploitations dans les outils, outils croissance / formule / données manquantes / coûts / documents / alertes, boucles d'outils Claude, OpenAI et Ollama, erreurs HTTP et SDK, boucle bornée) |
| Vitest | **74 tests réussis** (3 nouveaux) |
| Ruff, `tsc -b`, oxlint, build, `check`, `makemigrations --check`, schéma OpenAPI | aucun problème ; une migration (`assistant.0002_message_ordering`) appliquée |
| Parcours réel via le proxy Vite (sans fournisseur) | 401 anonyme ; statut « non configuré » ; question enregistrée et réponse explicite 503 ; liste ; suppression ; page `/assistant` servie. Données de test supprimées |

### Défaut trouvé et corrigé
- Sous Windows, deux messages créés dans la même milliseconde avaient le même horodatage : l'ordre de
  l'historique envoyé au modèle pouvait s'inverser (test instable). Les messages sont désormais triés par date
  puis par identifiant (migration `0002_message_ordering`, sans changement de données).

### Limites connues
- Aucun fournisseur réel configuré : les formats d'appel sont vérifiés avec des clients simulés.
- Réponses non diffusées en continu.

## Étape 11 — Intégration et vérification de bout en bout (07/11/2026) ✅

Méthode : vérifications réelles en HTTP sur le serveur de développement (via le proxy Vite) et dans Google Chrome
piloté par Playwright ; scripts de vérification hors du dépôt ; comptes `e2e-*` supprimés après chaque passage ;
aucune donnée existante supprimée, base `ndeyamai` jamais réinitialisée (sauvegarde `pg_dump` avant le jeu DEMO).

### Vérifications
| Sous-étape | Résultat |
|---|---|
| 1. Audit préalable | Aucun problème bloquant ; 48 migrations appliquées ; 431 + 74 tests verts au départ |
| 2. Parcours complets (10 parcours, e-mail de réinitialisation réel via un serveur temporaire) | **200/200** |
| 3. Sécurité (isolation, rôles, 401/403/404, jetons falsifiés, DEMO, débit) | **118/118** |
| 4. Jeu DEMO (commande `load_demo_data`) | 9 tests + **24/24** contrôles HTTP |
| 5. Moteur (recalcul indépendant + second solveur SciPy/HiGHS) | **56/56** ; sonde des contraintes de la base **31/31** |
| 6. Interface (Chrome, ordinateur 1366×820 et mobile 390×844) | **243/243**, 53 captures |
| Suites automatisées finales | pytest **455**, Vitest **75**, Ruff, `tsc`, oxlint, build, OpenAPI : sans erreur |

### Défauts trouvés et corrigés
| # | Défaut | Correction |
|---|---|---|
| 1 | Alertes « données à valider » et « formule à vérifier » créées seulement par la commande quotidienne (contrairement au guide) | Réévaluation immédiate (DT-61) |
| 2 | Saisies d'une exploitation DEMO non marquées DEMO : le moteur ignorait les prix saisis d'une ferme DEMO | Statut DEMO hérité de l'exploitation (DT-60) |
| 3 | `/dashboard/?farm=` d'une exploitation d'autrui : 200 avec des zéros au lieu de 404 | 404 |
| 4 | Erreurs 500 sur valeurs interdites par la base (teneur négative, ingestion négative, année de source, poids négatif d'une formule) | Contraintes vérifiées avant l'enregistrement (DT-59) |
| 5 | Tests écrivant dans `backend/media/` (36 PDF orphelins) | `MEDIA_ROOT` temporaire en test (DT-64) ; fichiers orphelins supprimés |
| 6 | Exploitation désactivée proposée par défaut dans les formulaires | Exploitation active préférée |
| 7 | Codes d'action bruts affichés (21 actions sans libellé) | Libellés centralisés (DT-63) |

Tests de non-régression ajoutés : 24 (backend 23, frontend 1).

### Restant (non bloquant)
- Assistant testé en réel uniquement sans fournisseur ; le cas configuré reste couvert par des clients simulés.
- Quantités affichées arrondies à 4 décimales : un besoin exactement atteint peut paraître manquer d'environ
  0,002 % si l'on recalcule à partir de l'affichage (le moteur vérifie sur les valeurs exactes).
- Rôle PostgreSQL `ndeyamai` superutilisateur en développement ; `SECURE_HSTS_PRELOAD` non activé (choix volontaire).
- Un expert envoyant une valeur invalide sur l'ingrédient privé d'un éleveur reçoit 400 avant 403 (écriture refusée
  dans tous les cas).

## Étape 12 — Documentation finale (07/11/2026) ✅

### Réalisé
- Contrôle des livrables de la phase 7 du cahier des charges : README, installation Windows et Linux, `.env.example`,
  documentation API (Markdown + OpenAPI), import des données, guides administrateur et utilisateur, architecture IA.
- Nouveau document [limites-et-evolutions.md](limites-et-evolutions.md) : couverture module par module,
  fonctionnalités volontairement non développées, limites connues, évolutions recommandées.
- Relecture de cohérence avec le code : commandes de test corrigées (enchaînement des dossiers), réévaluation des
  alertes décrite, jeu DEMO et dépannage ajoutés, navigation complète, glossaire et section DEMO du guide
  utilisateur, vérification indépendante du moteur, variables de production et `DEMO_PASSWORD` dans `.env.example`.
- Contrôles automatiques : les 36 modèles figurent dans le schéma documenté ; les variables lues par les réglages
  figurent dans `.env.example` ; chaque affirmation sur une limite vérifiée dans le code.
- Vérification complémentaire de l'interface sur **tablette** (820×1180), exigée par le cahier des charges :
  102/102 (passe navigateur totale : 345/345).

### Vérifications
| Contrôle | Résultat |
|---|---|
| pytest / Vitest | 455 / 75 réussis |
| Ruff, `tsc`, oxlint, build, migrations, OpenAPI | aucun problème |

## Identité visuelle (07/11/2026) ✅

- Recherche d'inspiration (projets agritech et élevage, identités agricoles éditoriales, textile sénégalais), puis
  planche de trois pistes ; retenue : « Indigo & Mil », avec les tampons de statut et les boucles d'identification.
- Mise en œuvre par jetons : palette, polices, composants de base, logo (tête de bélier Ladoum), favicon, menu,
  écran de connexion, tampons, boucles, graphiques.
- Défauts trouvés en revue visuelle et corrigés : logo illisible en petite taille (redessiné), axes tronqués et
  graduations irrégulières, tampons trop longs, indicateurs empilés sur mobile, couleurs d'avertissement
  hors palette ; courbes lissées remplacées par des segments droits (aucune valeur inventée entre deux mesures).
- Vérifications : Vitest 77 (2 nouveaux), `tsc`, oxlint, build ; parcours 200/200 ; interface 345/345 (ordinateur,
  tablette, téléphone).

## Assistant flottant (07/11/2026) ✅

- L'assistant quitte le menu latéral : bouton flottant en bas à droite (symbole du bélier), panneau de discussion
  (plein écran sur téléphone), Échap pour fermer, conversation conservée entre les pages, lien vers la vue plein
  écran et l'historique.
- Logique commune extraite (`useAssistantChat`, `ChatThread`) pour la page et le panneau.
- Défauts trouvés en revue et corrigés : focus perdu à l'ouverture quand l'assistant n'est pas configuré (désormais
  sur « Fermer »), accueil coupé par un défilement inutile, numéros de boucle coupés sur mobile.
- Vérifications : Vitest 80 (3 nouveaux), lint, build ; navigateur 18/18 (panneau) et 345/345 (application) ;
  parcours 200/200.

## Audit Impeccable et corrections (09/11/2026) ✅

- Audit : détecteur Impeccable sur 19 écrans rendus (1440 et 390 px), mesures d'accessibilité, revue design par un
  agent isolé (heuristiques de Nielsen 24/40, audit technique 14/20).
- Corrections appliquées (P1 à P3) : formulation utilisable sur téléphone, reprise après refus (« Que faire
  maintenant ? », « Modifier et recalculer »), règle serveur « pas de ration sans formule validée », jargon retiré
  (identifiant interne et détails moteur repliés, message d'assistant adapté au rôle, noms au lieu d'e-mails, « 10 kg »),
  contraste ≥ 4,5:1, textes ≥ 12 px, cibles tactiles agrandies, accueil « À faire aujourd'hui », guide et glossaire du
  bouton bélier, filtres repliables sur mobile, indicateur `ready_for_engine` (matière sèche utilisable).
- Mesure du détecteur : 54 → 20 constats (ordinateur) et 21 → 5 (téléphone), dont la bande tissée volontaire ;
  contraste insuffisant 19 → 0, textes trop petits 18 → 0, mots isolés 13 → 0.
- Vérifications : pytest 467, Vitest 82, lint, build, OpenAPI ; navigateur 345/345, nouveaux parcours 33/33, panneau
  22/22, parcours API 200/200.

## Lot 1 des retours clients (10/11/2026) ✅

- Formule rapide (lot → objectif → aliments), profil du lot déduit par le serveur, mémoire des choix sur l'appareil.
- Carte « À donner chaque jour » : quantités pour tout le lot en gros, pictogrammes, coût du jour et de la semaine,
  partage WhatsApp, impression de la carte seule.
- Application installable (manifeste, icônes, service worker de l'interface, bouton « Installer l'application »).
- Vérifications : pytest 469, Vitest 89, lint, build ; navigateur 33/33 (téléphone et ordinateur).

## Lot 2 des retours clients : hors ligne et données (10/11/2026) ✅

- Lecture hors ligne (copie locale des données, reprise de session sans réseau), bandeau de connexion.
- Pesées et séances de pesée hors ligne, file d'envoi automatique, refus affichés avec leur motif.
- Formule rapide hors ligne : paquet de calcul par exploitation, moteur porté dans le navigateur (parité testée sur
  15 cas du moteur Python), recalcul officiel par le serveur au retour du réseau.
- Interface préchargée par le service worker ; consommation mesurée (≈ 600 Ko à l'installation, 4 à 5 Ko par écran),
  affichée dans Paramètres.
- Vérifications : pytest 472, Vitest 114, lint, build, OpenAPI ; parcours hors ligne réel (version de production,
  coupure réseau, rechargement, pesée, calcul, retour du réseau) 18/18.

## Lot 3 des retours clients : anglais (10/11/2026) ✅

- Sélecteur FR | EN (en-tête et pages de connexion), langue gardée sur l'appareil, dates et nombres localisés.
- Interface entièrement traduite (≈ 1 250 textes), test de complétude ; messages du serveur traduits à la sortie de
  l'API (catalogue ≈ 540 entrées), y compris les avertissements et alertes déjà enregistrés.
- Vérifications : pytest 486, Vitest 119, lint, build, OpenAPI ; balayage réel de tous les écrans en anglais
  (éleveur sur téléphone et ordinateur, expert, administrateur, fenêtres et erreurs de formulaires) : seuls restent en
  français les noms et descriptions saisis dans la base ; parcours lot 1 33/33 et hors ligne 18/18 relancés.
