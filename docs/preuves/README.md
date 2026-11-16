# Preuves des résultats techniques

Chaque chiffre cité dans la fiche de projet et le document technique renvoie ici à son rapport. Ces résultats
prouvent que le calcul est juste et que l'application est fiable. **Ils ne prouvent pas un effet sur la croissance
des animaux** : c'est l'objet de l'essai pilote prévu ([protocole](../protocole-essai-pilote.md)).

| Chiffre cité | Preuve | Date | Comment le reproduire |
|---|---|---|---|
| 534 tests serveur, 0 échec | [pytest-backend.xml](pytest-backend.xml), [pytest-backend.txt](pytest-backend.txt) | 16/11/2026 | `cd backend && python -m pytest` |
| 125 tests d'interface, 0 échec | [vitest-frontend.xml](vitest-frontend.xml) | 16/11/2026 | `cd frontend && npm test` |
| Moteur : 56 contrôles sur 56 (recalcul indépendant, second solveur SciPy / HiGHS) | [moteur-verification.json](moteur-verification.json) | 07/11/2026 | Script de vérification hors dépôt (étape 11 du [journal](../journal-etapes.md)) |
| Contraintes de la base : 31 sur 31 | [contraintes-base.json](contraintes-base.json) | 07/11/2026 | Idem |
| 10 parcours complets d'utilisateur : 200 contrôles sur 200 | [parcours-utilisateur.json](parcours-utilisateur.json) | 09/11/2026 | Idem |
| Sécurité : 118 contrôles sur 118 | [securite.json](securite.json) | 07/11/2026 | Idem |
| Jeu de démonstration : 24 contrôles sur 24 | [jeu-demo.json](jeu-demo.json) | 07/11/2026 | Idem |
| Interface (ordinateur, tablette, téléphone) : 345 contrôles sur 345 | [interface-navigateur.json](interface-navigateur.json) | 09/11/2026 | Chrome piloté par Playwright, hors dépôt |
| Assistant vocal dans le navigateur : 17 contrôles sur 17 | Captures [captures/](captures/) ; détail dans le journal (13/11/2026) | 13/11/2026 | Faux micro lisant `backend/voice/tests/question_wolof.wav` |
| Parcours hors connexion : 18 contrôles sur 18 | Journal des étapes (lot 2, 10/11/2026) | 10/11/2026 | Pas de rapport conservé |
| Temps de réponse de l'assistant écrit (Gemini) : 4,3 s, 4,7 s, 6,7 s | Mesure ponctuelle du 14/11/2026 | 14/11/2026 | Pas de rapport conservé ; à refaire en production |

Les fichiers `.json` listent chaque contrôle avec son nom et son résultat (`"ok": true`). Les vérifications du 07 et
du 09/11 sont antérieures aux derniers ajouts (saisons, rations types, assistant vocal) ; ces ajouts sont couverts
par les tests automatiques ci-dessus.
