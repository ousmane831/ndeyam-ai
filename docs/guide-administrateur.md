# Guide administrateur et expert — NDEYAM AI

Ce guide décrit la gestion de la plateforme (administrateurs) et du référentiel nutritionnel (experts et
administrateurs). Pour l'utilisation courante, voir le [guide utilisateur](guide-utilisateur.md).

## 1. Rôles

| Rôle | Peut |
|---|---|
| **Administrateur** | Tout : comptes, toutes les exploitations, référentiel, validation, journal d'activité, administration Django |
| **Expert** | Gérer et valider le référentiel (sources, ingrédients du catalogue, compositions, références, contraintes, plages de suivi) ; consulter les exploitations qui l'ont invité ; valider ou rejeter leurs formules |
| **Éleveur** | Gérer ses exploitations, animaux, pesées, prix, ingrédients privés, formules et rations |

## 2. Comptes (administrateurs)

**Administration → Utilisateurs** :

- **Créer un compte** : nécessaire pour les experts (l'inscription publique ne crée que des éleveurs).
  Un compte éleveur créé ici **n'a pas d'exploitation** : la personne la crée ensuite dans *Paramètres → Mes exploitations*.
- **Changer un rôle**, **désactiver / réactiver** un compte (les sessions en cours sont révoquées).
- Un administrateur ne peut ni se désactiver ni retirer son propre rôle.
- Les comptes ne sont jamais supprimés par l'application, afin de conserver la traçabilité.

L'**administration des données** (lien dans le menu) ouvre l'interface Django : toutes les tables, y compris les
nomenclatures (espèces, races, catégories, stades, objectifs, nutriments, systèmes nutritionnels).

Activer une nouvelle espèce (caprins, bovins) : *Administration des données → Espèces → Active*, puis saisir ses races,
catégories et stades. Aucun développement n'est nécessaire.

## 3. Constituer le référentiel (experts)

L'ordre recommandé :

1. **Sources documentaires** — *Traçabilité des données → Sources* : table de composition, analyse de laboratoire,
   article… Une source fictive doit être cochée **DEMO** : elle ne pourra jamais justifier une validation.
2. **Ingrédients et compositions** — *Ingrédients alimentaires* :
   - import CSV (*Importer des compositions*, avec la source du fichier), voir le [guide d'importation](import-donnees.md) ;
   - ou saisie dans la fiche de l'ingrédient (*Ajouter une valeur*).
   Unités : matière sèche en g/kg de produit **brut** ; tout le reste par kg de **MS**.
3. **Références nutritionnelles** — *Références nutritionnelles → Nouvelle référence* : profil (espèce, catégorie, stade,
   objectif, poids, âge), **système nutritionnel**, **bornes d'ingestion de MS** (obligatoires pour le moteur), puis les
   besoins (minimum, cible, maximum). Seuls les nutriments universels et ceux du système choisi sont proposés.
4. **Contraintes d'incorporation** — dans la fiche d'une référence : bornes en % de MS par ingrédient ou catégorie.
5. **Plages de suivi de croissance** — via l'API (`/api/v1/growth-ranges/`) ou l'administration des données.

### Documents techniques (RAG)

*Base documentaire → Importer un PDF* : titre, source, date de référence. Le document est découpé en passages et
indexé ; il reste en brouillon jusqu'à sa validation (source obligatoire). Les PDF scannés ne sont pas lus (pas d'OCR).
Après avoir configuré ou changé un fournisseur d'embeddings, cliquez sur **Réindexer** pour chaque document.
Voir [architecture-ia.md](architecture-ia.md).

## 4. Valider

Chaque donnée de référence suit le circuit **Brouillon → En attente → Validé / Rejeté**.

| Règle | Effet |
|---|---|
| Une donnée DEMO, sans source ou appuyée sur une source DEMO ne peut pas être validée | Le bouton *Valider* renvoie la raison |
| Une référence sans besoin ne peut pas être validée | Idem |
| Un rejet exige un motif | Conservé dans l'historique |
| Modifier une donnée validée (hors texte libre) la remet en brouillon | Elle doit être revalidée |
| Une seule valeur validée par ingrédient et nutriment | Le moteur sait toujours laquelle il utilise |

Seules les données **validées et non DEMO** sont utilisées par le moteur de formulation et par les alertes de croissance.
Toutes les décisions sont visibles dans *Traçabilité des données → Historique des validations*.

Les experts et administrateurs reçoivent une alerte « Données de référence à valider » dès qu'un élément est soumis ;
elle se met à jour ou disparaît dès la décision. De même, l'alerte « Formulation à vérifier » apparaît dès la demande
de vérification d'une formule.

## 5. Vérifier les formules

Un éleveur peut demander la vérification d'une formule (*Demander la vérification d'un expert*). L'expert invité sur
l'exploitation (ou un administrateur) ouvre la formule et choisit **Valider** ou **Rejeter** (motif obligatoire).
Une formule DEMO, refusée ou impossible ne peut pas être validée. Modifier une formule la remet en brouillon.

## 6. Traçabilité et supervision

*Traçabilité des données* :

| Onglet | Contenu | Accès |
|---|---|---|
| Sources documentaires | Création, suppression (refusée si la source est utilisée) | Experts, administrateurs |
| Historique des validations | Qui a validé / rejeté quoi, quand et pourquoi | Experts, administrateurs |
| Importations | Fichiers importés, lignes créées et en erreur | Chacun ses imports ; tout pour les administrateurs |
| Journal d'activité | Connexions, créations, modifications, validations, imports | Administrateurs |

## 7. Assistant IA

L'assistant est désactivé par défaut (`LLM_PROVIDER=none`). Pour l'activer, renseigner dans `backend/.env` :

```
LLM_PROVIDER=anthropic          # ou openai_compatible, ollama
LLM_MODEL=claude-opus-5-5       # obligatoire pour openai_compatible et ollama
LLM_API_KEY=...                 # jamais dans le code ni dans Git
LLM_BASE_URL=                   # openai_compatible / ollama (ex. http://localhost:11434)
LLM_FALLBACKS=True              # Claude : repli automatique si une réponse est refusée
```

puis redémarrer le backend. *État du système* et la page de l'assistant indiquent si la configuration est valide.
Chaque réponse conserve le fournisseur, le modèle, les jetons et la latence (administration des données →
Conversations IA) ; le journal d'activité trace les réponses et les erreurs.

## 8. Données de démonstration

`python manage.py load_demo_data` charge un jeu complet (comptes, exploitations, animaux, formules, rations,
alertes, document) **entièrement fictif et marqué DEMO** ; `--reset` le recharge, `--remove` le retire sans toucher
aux données réelles. Le mot de passe des comptes DEMO est généré et affiché une seule fois (ou fourni avec
`--password`). Détails : [donnees-demo.md](donnees-demo.md).

## 9. Exploitation courante

- **Alertes quotidiennes** : planifier `python manage.py evaluate_alerts` (voir les guides d'installation).
- **Sauvegardes** : sauvegarder régulièrement la base PostgreSQL (`pg_dump ndeyamai`).
- **E-mails** : configurer un serveur SMTP dans `backend/.env` pour l'envoi réel des liens de réinitialisation.
- **Sécurité** : en production, utiliser un rôle PostgreSQL non superutilisateur, un mot de passe fort,
  `DJANGO_DEBUG=False` et HTTPS (voir `config/settings/production.py`).
