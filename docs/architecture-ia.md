# Architecture IA de NDEYAM AI

NDEYAM AI combine trois briques aux responsabilités strictement séparées :

| Brique | Rôle | Ne fait jamais |
|---|---|---|
| **Moteur de formulation** (`formulations/engine`, PuLP) | Calculs nutritionnels et optimisation | Utiliser des données non validées ou DEMO dans une exploitation réelle |
| **Base documentaire RAG** (`knowledge_base`) | Retrouver des passages de documents techniques validés, avec leur référence | Inventer un contenu : elle ne renvoie que des extraits existants |
| **Assistant** (`assistant`) | Comprendre la question, appeler les outils autorisés, rédiger la réponse | Calculer lui-même une ration ou des besoins ; poser un diagnostic vétérinaire |

Voir aussi [moteur-formulation.md](moteur-formulation.md).

## 1. Base documentaire (RAG) — étape 9

```
PDF importé (expert)
   │  empreinte SHA-256 → refus des doublons
   ▼
Extraction du texte (pypdf, page par page) ── PDF scanné ? → statut « Échec » (pas d'OCR)
   ▼
Nettoyage et découpage en passages (~1 200 caractères, chevauchement 200,
coupure en fin de paragraphe / phrase, pages de début et de fin conservées)
   ▼
Index plein texte PostgreSQL (configuration « french », texte sans accents)
   ▼
Embeddings (si un fournisseur est configuré) → DocumentChunk.embedding (real[])
   ▼
Document en BROUILLON → validation par un expert (source obligatoire, indexation réussie)
   ▼
Recherche : documents VALIDÉS et non DEMO uniquement
```

### Recherche

1. **Sémantique** si un fournisseur d'embeddings est configuré et que des passages ont été vectorisés avec le
   même modèle : la question est vectorisée puis comparée aux passages (similarité cosinus, `NumpyVectorStore`).
2. **Plein texte** sinon (ou en cas d'échec du fournisseur) : `websearch_to_tsquery('french', …)`, classement
   `ts_rank`, insensible aux accents (le texte et la question sont normalisés sans accents avant indexation).

Chaque résultat contient la **citation** complète : titre du document, pages, source documentaire.

### Fournisseurs d'embeddings (`.env`)

| `EMBEDDING_PROVIDER` | Appel | Variables |
|---|---|---|
| `none` (défaut) | — : recherche plein texte | — |
| `openai_compatible` | `POST {BASE_URL}/embeddings` | `EMBEDDING_MODEL`, `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL` |
| `ollama` | `POST {BASE_URL}/api/embed` (local) | `EMBEDDING_MODEL`, `EMBEDDING_BASE_URL` |

Après un changement de modèle, utilisez **Réindexer** sur chaque document : les vecteurs d'un ancien modèle ne sont
jamais mélangés avec ceux du nouveau (l'identifiant du modèle est stocké avec chaque passage).

### Stockage vectoriel

`VECTOR_STORE_BACKEND=numpy` (défaut) : vecteurs dans PostgreSQL (`real[]`), similarité calculée en mémoire,
adapté à quelques dizaines de milliers de passages. **pgvector** est prévu : l'interface `VectorStore` est en
place ; il suffira d'ajouter une colonne `vector` remplie à partir des vecteurs existants, sans réimporter les
documents.

### Limites connues

- Pas d'OCR : les PDF scannés sont refusés avec un message explicite.
- Traitement synchrone à l'import (PDF de 20 Mo et 1 000 pages au maximum).
- La recherche sémantique en mémoire convient au prototype ; au-delà, activer pgvector.

## 2. Assistant conversationnel — étape 10

### Principe

```
Question ─► orchestrateur ─► LLM (outils métier déclarés)
                               │ demande un outil
                               ▼
              ToolContext (droits de l'utilisateur, exploitations accessibles)
                 base de données · résultat du moteur nutritionnel · documents validés
                               │ résultat JSON + provenance
                               ▼
                      LLM rédige la réponse ─► enregistrée avec sa provenance
```

Le LLM ne reçoit jamais d'accès direct à la base : il ne voit que ce que renvoient les outils, exécutés avec les
droits de l'utilisateur connecté (et limités à l'exploitation de la conversation si elle en a une).

### Outils (`assistant/tools.py`)

| Outil | Données | Provenance |
|---|---|---|
| `list_my_farms` | Exploitations accessibles et rôle | base |
| `find_animals`, `list_groups` | Animaux présents (dernier poids), lots | base |
| `get_animal_growth` | Pesées, GMD (formule affichée), comparaison à une plage validée | base |
| `get_feeding_cost` | Distributions, coût estimé, consommation mesurée sur une période | base |
| `list_formulas` | Formules et statuts | base |
| `get_formula_result` | Résultat enregistré par le moteur : refus, contraintes bloquantes, apports, sources | moteur |
| `check_formulation_readiness` | Données validées manquantes pour un calcul | base |
| `search_documents` | Extraits des documents **validés**, avec citation | document |
| `list_open_alerts` | Alertes ouvertes | base |

Aucun outil ne calcule de ration : pour une nouvelle formule, l'assistant renvoie vers l'écran de formulation.
Les erreurs d'outil (objet inaccessible, arguments invalides) sont renvoyées au modèle, qui les explique.

### Règles imposées au modèle (`orchestrator.SYSTEM_PROMPT`)

Chiffres issus des outils uniquement ; information manquante signalée, jamais inventée ; origine de chaque
information indiquée ; une « Estimation mathématique » n'est pas une recommandation validée ; aucun diagnostic
vétérinaire ni prescription ; données DEMO signalées ; documents cités.

### Provenance et traçabilité

Chaque réponse (`AIMessage`) enregistre : la liste des sources (`database`, `engine`, `document`, `llm`),
les outils appelés et leur succès, le fournisseur, le modèle, les jetons consommés, la latence et, le cas échéant,
le code d'erreur. L'interface affiche la provenance sous chaque réponse. Les conversations sont strictement
privées (404 pour tout autre utilisateur). Les 20 derniers messages réussis servent d'historique.

### Fournisseurs LLM (`.env`)

| `LLM_PROVIDER` | Réglages | Notes |
|---|---|---|
| `none` (défaut) | — | Assistant désactivé ; message explicite (HTTP 503), le reste de l'application fonctionne |
| `anthropic` | `LLM_API_KEY`, `LLM_MODEL` (défaut `claude-opus-5-5`), `LLM_FALLBACKS` | SDK officiel `anthropic` |
| `openai_compatible` | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | `POST {base}/chat/completions`, outils au format « functions » |
| `ollama` | `LLM_BASE_URL`, `LLM_MODEL` | `POST {base}/api/chat`, modèle local, sans clé |

Avec Claude, le **repli côté serveur** (`LLM_FALLBACKS=True`, par défaut) est activé : si les classificateurs de
sécurité d'Anthropic refusent une réponse, la requête est automatiquement relancée sur un modèle de repli plutôt
que d'échouer. `LLM_FALLBACKS=False` le désactive. Un refus définitif est enregistré (`provider_refusal`).

Erreurs normalisées : `provider_auth`, `provider_rate_limited`, `provider_unreachable`, `provider_error`,
`provider_refusal`, `too_many_tool_calls` (6 tours d'outils au maximum). Débit limité à 20 questions par minute
et par utilisateur (`assistant`). `GET /assistant/conversations/status/` indique la configuration sans jamais
exposer la clé.

### Limites connues

- Réponses non diffusées en continu (affichage à la fin de la génération).
- Testé avec des fournisseurs simulés (formats de requête vérifiés) ; aucun fournisseur réel n'est configuré
  sur cette installation.
- La qualité des explications dépend du modèle choisi ; les chiffres, eux, viennent toujours des outils.
