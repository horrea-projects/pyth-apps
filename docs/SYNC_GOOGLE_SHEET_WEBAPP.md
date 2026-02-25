# Webapp « Sync vers Google Sheet »

Cette fonctionnalité permet de **vous connecter avec votre compte Google** (sans créer de projet Service Account), puis d’**envoyer le dernier export CSV** vers une **feuille Google Sheet** de votre choix. Vous pouvez changer de feuille, mettre à jour manuellement ou planifier des mises à jour.

---

## Principe

1. **Import complet** (page Zendesk) : exporte tous les tickets Zendesk vers **`exports/tickets_all.csv`** (fichier unique enrichi pour Looker Studio).
2. **Enrichissement incrémental** : à la fréquence choisie (24 h, 48 h, hebdo, mensuel), les tickets *mis à jour* depuis Zendesk sont fusionnés dans `tickets_all.csv` (mise à jour des lignes existantes, ajout des nouveaux).
3. Vous ouvrez la **webapp Sync** (`/zendesk/sync`), vous **connectez avec Google** (OAuth).
4. Dans **Paramètres** vous indiquez la feuille cible (ID + onglet) et la **fréquence d’enrichissement** (24 h, 48 h, hebdo, mensuel).
5. **« Enrichir maintenant »** : lance tout de suite une fusion incrémentale dans `tickets_all.csv`.
6. **« Mettre à jour la Google Sheet maintenant »** : envoie **`tickets_all.csv`** vers votre feuille Google (pour Looker Studio).
7. Optionnel : **cron** pour enrichissement automatique (`POST /zendesk/sync/run-incremental`) et/ou mise à jour de la feuille (`POST /sync-now`).

---

## Configuration requise

### 1. Google Cloud Console (OAuth uniquement)

- Allez sur [Google Cloud Console](https://console.cloud.google.com/).
- Créez un projet (ou utilisez un existant).
- **APIs** : activez **Google Sheets API** et **Google Drive API** (pour lister les fichiers si besoin).
- **Credentials** → **Create credentials** → **OAuth client ID**.
  - Type : **Web application**.
  - **Authorized redirect URIs** : ajoutez l’URL de callback de votre app, par exemple :
    - En local : `http://localhost:8000/auth/google/callback`
    - Sur PythonAnywhere : `https://VOTRE_USER.pythonanywhere.com/auth/google/callback`
- Notez le **Client ID** et le **Client Secret**.

### 2. Variables d’environnement

Dans votre `.env` (ou variables d’environnement sur PythonAnywhere) :

```env
# OAuth Google (webapp Sync)
GOOGLE_OAUTH_CLIENT_ID=votre_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=votre_client_secret

# Optionnel : URL de base (pour afficher le redirect URI à configurer dans Google)
# BASE_URL=https://votreuser.pythonanywhere.com
```

Aucun fichier `credentials.json` (Service Account) n’est nécessaire.

---

## Utilisation

### Accès à la webapp

- Depuis la page d’accueil : lien **« Sync vers Google Sheet »**.
- Ou directement : **`/sync-app`**.

### Connexion Google

1. Cliquez sur **« Se connecter avec Google »**.
2. Autorisez l’accès aux feuilles Google (et lecture Drive si utilisé).
3. Vous êtes redirigé vers le dashboard Sync.

### Paramètres

- **Paramètres (feuille, fréquence, mise à jour auto)** :
  - **ID de la feuille** : l’ID dans l’URL de votre Google Sheet  
    `https://docs.google.com/spreadsheets/d/ID_ICI/edit`
  - **Nom de l’onglet** : par ex. `Tickets` (sera créé s’il n’existe pas).
  - **Enrichissement tickets_all.csv** : fréquence des mises à jour incrémentales (24 h, 48 h, hebdo, mensuel). Les tickets Zendesk mis à jour depuis cette durée sont fusionnés dans `exports/tickets_all.csv`.
  - **Mise à jour auto de la Google Sheet** : si activée, prévoir un cron qui appelle `POST /sync-now` pour envoyer `tickets_all.csv` vers la feuille.

### Enrichissement et sync

- **« Enrichir maintenant »** : récupère les tickets Zendesk mis à jour (selon la fréquence configurée) et les fusionne dans `tickets_all.csv`. Utilisable avant d’envoyer la feuille vers Looker Studio.
- **« Mettre à jour la Google Sheet maintenant »** : envoie **`tickets_all.csv`** (prioritaire s’il existe) vers la feuille configurée.

### Mise à jour planifiée (cron)

- **Enrichissement** (fusion incrémentale dans `tickets_all.csv`) :  
  `POST /zendesk/sync/run-incremental`  
  Avec optionnel `CRON_SECRET` en variable d’environnement, les appels API (Accept: application/json) doivent envoyer `?secret=CRON_SECRET` ou l’en-tête `X-Cron-Secret`. Exemple :  
  `curl -X POST "https://VOTRE_USER.pythonanywhere.com/zendesk/sync/run-incremental?secret=VOTRE_SECRET" -H "Accept: application/json"`
- **Sync vers la feuille** :  
  `POST /sync-now`  
  Exemple : `curl -X POST https://VOTRE_USER.pythonanywhere.com/sync-now`

---

## Choix du framework sur PythonAnywhere

Vous pouvez garder **Manual configuration** et continuer à utiliser **FastAPI** comme aujourd’hui. La webapp Sync est une partie de la même app FastAPI (routes `/sync-app`, `/auth/google`, etc.). Aucun besoin de créer une app Django/Flask séparée : il suffit de déployer le projet actuel et de configurer le WSGI (ou ASGI) comme décrit dans `docs/PYTHONANYWHERE.md`.

---

## Sécurité

- Les **tokens OAuth** sont stockés dans `data/oauth_data.json` (dossier ignoré par git). Ne partagez pas ce fichier.
- En production, utilisez **HTTPS** et une **URL de redirect** en `https://` dans Google Cloud Console.
- Pour une mise à jour planifiée exposée sur internet, protégez l’endpoint `POST /sync-now` (par exemple par un token ou une IP autorisée).

---

## Dépannage

- **« OAuth non configuré »** : vérifiez `GOOGLE_OAUTH_CLIENT_ID` et `GOOGLE_OAUTH_CLIENT_SECRET` dans l’environnement.
- **Redirect URI mismatch** : l’URI dans Google Cloud (ex. `https://.../auth/google/callback`) doit être **exactement** celle utilisée par l’app (pas de slash en trop, même domaine).
- **Aucun fichier d’export** : lancez d’abord un **Import complet** depuis la page d’accueil pour générer un CSV dans `exports/`.
