# Mise en ligne gratuite : Neon + Render + Netlify

```
Téléphone ──► Netlify (interface, HTTPS) ──► Render (API Django, HTTPS) ──► Neon (PostgreSQL)
                                                  ├──► Sama Agri Voice (voix)
                                                  └──► Gemini (assistant écrit, recherche par le sens)
```

Les fichiers de configuration sont dans le dépôt : [`render.yaml`](../render.yaml) (serveur) et
[`netlify.toml`](../netlify.toml) (interface). Aucune clé n'y figure : elles se saisissent dans les tableaux de bord.

| Service | Rôle | Offre gratuite : à savoir |
|---|---|---|
| Neon | Base PostgreSQL | 1 Go, pas d'expiration ; se met en veille et se réveille en environ 1 s |
| Render | API Django | S'endort après 15 min sans visite (réveil ≈ 1 min) : voir l'étape 5 ; fichiers importés (PDF) perdus au redémarrage |
| Netlify | Interface | HTTPS fourni (indispensable pour le micro) |

L'interface appelle Render **directement** (pas de relais Netlify, qui coupe les requêtes vers 26 s ; une question
vocale peut en prendre 25).

## 1. Base de données (Neon)
1. Créer un compte sur neon.com (connexion GitHub), puis un projet **ndeyam**, région **AWS Europe (Frankfurt)**.
2. Dans **Connect**, copier la chaîne de connexion **directe** (décocher *Connection pooling*). Elle ressemble à
   `postgresql://…@ep-….eu-central-1.aws.neon.tech/neondb?sslmode=require`. La garder pour l'étape 2.

## 2. API (Render)
1. Créer un compte sur render.com (connexion GitHub) et autoriser l'accès au dépôt `ndeyam-ai`.
2. **New → Blueprint**, choisir le dépôt : Render lit `render.yaml` et prépare le service **ndeyam-api**.
3. Saisir les valeurs demandées :

| Variable | Valeur |
|---|---|
| `DATABASE_URL` | la chaîne Neon de l'étape 1 |
| `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS` | provisoirement `https://exemple.netlify.app` (corrigé à l'étape 4) |
| `CSRF_TRUSTED_ORIGINS` | l'adresse du service, ex. `https://ndeyam-api.onrender.com` |
| `DEMO_PASSWORD` | mot de passe des comptes de démonstration remis au jury |
| `VOICE_SERVICE_URL`, `VOICE_SERVICE_API_KEY` | les valeurs du fichier `backend/.env` local |
| `LLM_API_KEY`, `EMBEDDING_API_KEY` | une **nouvelle** clé Gemini (aistudio.google.com) |

4. Lancer le déploiement (environ 5 min la première fois). Au démarrage, le serveur applique les migrations et
   charge le jeu de démonstration (une seule fois).
5. Vérifier : `https://<service>.onrender.com/api/v1/health/` répond `"status": "ok"`.

## 3. Interface (Netlify)
1. Créer un compte sur netlify.com (connexion GitHub). **Add new site → Import an existing project**, choisir le dépôt :
   les réglages viennent de `netlify.toml`.
2. Avant de déployer, ajouter la variable d'environnement
   `VITE_API_BASE_URL` = `https://<service>.onrender.com/api/v1`.
3. Déployer, puis **Site configuration → Change site name** : par ex. `ndeyam` → `https://ndeyam.netlify.app`.

## 4. Relier l'interface à l'API
Sur Render, remplacer `FRONTEND_URL` et `CORS_ALLOWED_ORIGINS` par l'adresse Netlify (`https://ndeyam.netlify.app`).
Render redéploie seul.

## 5. Garder l'API éveillée
Créer un moniteur gratuit (uptimerobot.com ou cron-job.org) qui appelle
`https://<service>.onrender.com/api/v1/health/` toutes les 10 minutes. Les 750 heures gratuites par mois de Render
suffisent pour un service allumé en permanence.

## 6. Vérifier en ligne
Sur un téléphone, en navigation privée : ouvrir l'adresse Netlify, se connecter avec
`eleveur@demo.ndeyam.example` et `DEMO_PASSWORD`, puis essayer la formule rapide, le bouton bélier (onglet Parler, le
micro doit être autorisé) et l'installation de l'application.

## Limites connues de cet hébergement
- Calcul quotidien des alertes non planifié (payant sur Render) : les alertes sont recalculées à chaque modification.
- E-mails non envoyés (réinitialisation du mot de passe) tant qu'aucun serveur SMTP n'est configuré.
- Pour un pilote réel : base et serveur payants ou VPS, sauvegardes automatiques, stockage durable des fichiers.
