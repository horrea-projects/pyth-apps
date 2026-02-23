# Webapp « Sync vers Google Sheet »

Cette fonctionnalité permet de **vous connecter avec votre compte Google** (sans créer de projet Service Account), puis d’**envoyer le dernier export CSV** vers une **feuille Google Sheet** de votre choix. Vous pouvez changer de feuille, mettre à jour manuellement ou planifier des mises à jour.

---

## Principe

1. Vous lancez les **exports Zendesk** comme d’habitude (page d’accueil → Import complet). Les CSV sont créés dans `exports/`.
2. Vous ouvrez la **webapp Sync** (`/zendesk/sync`).
3. Vous **vous connectez avec Google** (OAuth). Aucun Service Account : c’est votre compte personnel.
4. Vous indiquez **quelle feuille** mettre à jour (ID + nom de l’onglet) dans **Paramètres**.
5. Vous cliquez sur **« Mettre à jour la Google Sheet maintenant »** pour envoyer le **dernier export CSV** vers cette feuille.
6. Optionnel : vous pouvez **planifier** des mises à jour (cron qui appelle `POST /sync-now`).

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

- **Paramètres (feuille, mise à jour auto)** :
  - **ID de la feuille** : l’ID dans l’URL de votre Google Sheet  
    `https://docs.google.com/spreadsheets/d/ID_ICI/edit`
  - **Nom de l’onglet** : par ex. `Tickets` (sera créé s’il n’existe pas).
  - **Mise à jour automatique** : case à cocher. Si activée, il faut configurer une tâche planifiée (cron) qui appelle `POST /sync-now` à l’heure voulue.

### Mise à jour manuelle

- Sur le dashboard, cliquez sur **« Mettre à jour la Google Sheet maintenant »**.
- Le **dernier fichier CSV** dans `exports/` (par date de modification) est envoyé vers la feuille configurée.

### Mise à jour planifiée

- Sur PythonAnywhere : **Schedule** → nouvelle tâche qui exécute par exemple un `curl -X POST https://VOTRE_USER.pythonanywhere.com/sync-now` (en protégeant l’URL par un secret si besoin).
- En local : cron ou Task Scheduler qui fait la même requête POST.

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
