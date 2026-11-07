# Couverture du cahier des charges, limites et évolutions

État au 07/11/2026 — version 0.1.0. Ce document signale explicitement ce qui est livré, ce qui est partiel et ce qui
reste à faire. Les vérifications citées sont décrites dans le [journal des étapes](journal-etapes.md) (étape 11).

## 1. Couverture des modules

| Module du cahier des charges | État | Remarques |
|---|---|---|
| 1. Authentification, profils, rôles | ✅ Livré | Inscription, connexion, déconnexion, réinitialisation par e-mail, profil, rôles Administrateur / Expert / Éleveur, isolation par exploitation |
| 2. Tableau de bord | ✅ Livré | Indicateurs issus de la base uniquement, graphiques, états vides explicites |
| 3. Gestion des animaux | ✅ Livré | Fiche à six onglets, recherche, filtres, sortie / archivage, historique, import / export CSV |
| 4. Ingrédients alimentaires | ✅ Livré | Catalogue commun et privé, compositions sourcées, valeur inconnue affichée comme telle, import CSV, validation |
| 5. Référentiel des besoins | ✅ Livré | Profil (espèce, race, catégorie, âge, poids, stade, objectif), besoins min / cible / max, contraintes d'incorporation, sources, validation |
| 6. Moteur de formulation | ✅ Livré | PuLP / CBC, modes économique et équilibré, refus motivés, diagnostic d'infaisabilité, vérification indépendante, validation par un expert |
| 7. Suivi de croissance | ✅ Livré | Pesées, écarts, GMD, graphiques, alertes sur plages validées. Prédiction : **non développée** (voulu, voir § 2) |
| 8. Assistant conversationnel | ✅ Livré (⚠ non testé avec un fournisseur réel) | Orchestrateur, outils métier soumis aux permissions, RAG, provenance des informations, Claude / compatible OpenAI / Ollama |
| 9. Rations et alimentation | ✅ Livré | Quantités calculées, distribuées et consommées distinguées ; coûts ; comparaison de formules |
| 10. Alertes et rappels | ✅ Livré | Six règles explicables, réglables, traçables ; réévaluation immédiate et quotidienne |
| 11. Administration et qualité des données | ✅ Livré | Comptes, traçabilité, validations, imports, journal ; administration Django pour les nomenclatures |
| Base de données (§ 5) | ✅ Livré | Les 22 entités demandées et 14 complémentaires, contraintes en base, [schéma](schema-base-donnees.md) |
| Interface (§ 6) | ✅ Livré | Entièrement en français ; vérifiée dans Chrome sur ordinateur, tablette et téléphone |
| Tests (§ 7) | ✅ Livré | 455 tests backend, 75 tests frontend, vérifications de bout en bout |
| Données de démonstration (§ 8) | ✅ Livré | Commande `load_demo_data`, données marquées DEMO, jamais validées ([détails](donnees-demo.md)) |
| Documentation (phase 7) | ✅ Livré | Voir le [README](../README.md) |

## 2. Fonctionnalités volontairement non développées

| Élément | Raison | Ce qui est prêt |
|---|---|---|
| Modèle de prédiction de la croissance | Pas encore de données réelles en quantité suffisante ; le cahier des charges interdit un modèle fictif | Export des pesées (`/weighings/export/`), point d'entrée `growth/prediction.py`, endpoint `prediction-status` qui répond « non disponible » |
| Données nutritionnelles de référence réelles | Collecte en cours ; aucune valeur ne doit être inventée | Import CSV, circuit de validation, traçabilité des sources. **Tant qu'un expert n'a pas validé de références et de compositions, tout calcul réel est refusé** |
| Plages de suivi de croissance | Mêmes raisons | Saisie et validation par les experts ; la comparaison s'active dès qu'une plage est validée |

## 3. Limites connues

### Intelligence artificielle
- L'assistant et les embeddings n'ont été vérifiés qu'avec des **fournisseurs simulés** : aucune clé ni aucun modèle
  local n'étaient configurés. Les formats d'appel sont testés, pas la qualité des réponses d'un vrai modèle.
- Réponses de l'assistant affichées en une fois (pas de diffusion progressive).
- Stockage vectoriel en mémoire (NumPy) : adapté au prototype. Le passage à **pgvector** est prévu par l'interface
  `VectorStore`, mais l'adaptateur pgvector n'est pas implémenté.
- Pas d'OCR : les PDF scannés sont refusés avec un message explicite. Import traité de façon synchrone (20 Mo maximum).

### Moteur nutritionnel
- Les rapports entre nutriments (ex. Ca/P) ne sont pas pris en charge comme contraintes.
- Le diagnostic d'infaisabilité propose un ensemble de contraintes à relâcher ; d'autres combinaisons peuvent exister.
- Quantités affichées arrondies (4 décimales en kg) : un recalcul manuel à partir de l'affichage peut faire paraître
  un besoin exactement atteint manquant d'environ 0,002 %. Le moteur vérifie sur les valeurs exactes.
- PuLP est figé en version 3 ; le solveur intégré `PULP_CBC_CMD` devra être remplacé lors du passage à PuLP 4.

### Espèces
- Caprins et bovins : nomenclature créée mais **inactive** ; aucune race, catégorie ni référence n'est fournie.
  Activation dans l'administration des données, sans développement.

### Exploitation et déploiement
- **Mise en production non réalisée ni testée.** Les réglages de durcissement existent (`config/settings/production.py` :
  HTTPS, cookies sécurisés, HSTS), mais il reste à choisir et configurer : un serveur d'application (Gunicorn ou
  Waitress), un serveur web pour les fichiers statiques (`collectstatic`) et le HTTPS, l'envoi d'e-mails SMTP,
  la planification de `evaluate_alerts`, les sauvegardes PostgreSQL et un rôle PostgreSQL non superutilisateur.
- `SECURE_HSTS_PRELOAD` volontairement désactivé (inscription difficile à annuler).
- Pas de Docker (choix du projet) ; pas d'application mobile native ni de mode hors connexion ; pas de notification
  par SMS ou WhatsApp ; interface en français uniquement.

### Points mineurs
- Un expert qui envoie une valeur invalide sur l'ingrédient privé d'un éleveur reçoit l'erreur de saisie (400) avant
  le refus d'accès (403) ; l'écriture est refusée dans tous les cas.

## 4. Évolutions recommandées (par priorité)

1. **Saisie et validation des premières références réelles** par des experts (compositions des ingrédients locaux,
   besoins des ovins, plages de suivi), avec leurs sources : c'est ce qui rend le moteur utilisable en conditions réelles.
2. **Configuration d'un fournisseur d'IA** (Claude, API compatible OpenAI ou Ollama) puis évaluation des réponses de
   l'assistant sur des questions réelles d'éleveurs.
3. **Mise en production** d'un pilote (voir § 3) avec sauvegardes automatiques.
4. Adaptateur **pgvector** lorsque la base documentaire dépassera quelques milliers de passages.
5. Contraintes de **rapports entre nutriments** (Ca/P).
6. Activation des **caprins**, puis des **bovins**, avec leurs référentiels.
7. **Modèle de prédiction de croissance** lorsque suffisamment de pesées réelles auront été collectées.
