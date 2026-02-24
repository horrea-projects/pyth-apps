# Déployer Pyth-apps sur PythonAnywhere

Guide pour héberger **Pyth-apps** sur [pythonanywhere.com](https://www.pythonanywhere.com) (Zendesk, Sync Google Sheet, Calculs entre feuilles).

---

## En bref

1. **Consoles** → Bash : cloner le repo, créer le venv, installer les dépendances.
2. **Web** → Add a new web app → Manual configuration → Python 3.x.
3. **Web** → WSGI : pointer vers `wsgi.py` du projet.
4. **Web** → Environment variables : ajouter toutes les variables (Zendesk, optionnellement OAuth Google).
5. **Web** → Virtualenv : chemin vers `~/pyth-apps/venv` → **Reload**.

---

## 1. Cloner le projet

Onglet **Consoles** → **Bash** :

```bash
cd ~
git clone https://github.com/horrea-projects/pyth-apps.git
cd pyth-apps
```

(Si le repo est en SSH uniquement, utilisez l’URL HTTPS ci-dessus ou configurez une clé SSH sur PythonAnywhere.)

---

## 2. Environnement virtuel et dépendances

Dans la même console Bash :

```bash
cd ~/pyth-apps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Dossier pour l’OAuth (Sync / Calculs Google)

L’app stocke les tokens OAuth dans `data/oauth_data.json`. Créez le dossier :

```bash
mkdir -p ~/pyth-apps/data
```

---

## 4. Variables d’environnement

Vous n’uploadez **pas** le fichier `.env` sur le serveur. Configurez tout dans **Web** → **Environment variables**.

1. Onglet **Web** → votre application → section **Code** ou **Environment variables**.
2. Ajoutez chaque variable (nom + valeur). Exemple :

| Variable | Valeur (à adapter) |
|----------|--------------------|
| `ZENDESK_SUBDOMAIN` | `horrea` |
| `ZENDESK_EMAIL` | `votre-email@exemple.com` |
| `ZENDESK_API_TOKEN` | `votre-token-api` |
| `EXPORT_MODE` | `csv` (ou `gsheet` si vous utilisez le Service Account) |
| `EXPORT_OUTPUT_DIR` | `exports` |
| `GOOGLE_OAUTH_CLIENT_ID` | `xxx.apps.googleusercontent.com` |
| `GOOGLE_OAUTH_CLIENT_SECRET` | `GOCSPX-xxx` |

- **Redirect URI** configurée dans Google Cloud pour cette app :  
  `https://VOTRE_USER.pythonanywhere.com/auth/google/callback`  
  (ex. `https://leocarre.pythonanywhere.com/auth/google/callback`).

Optionnel (mode gsheet avec Service Account) :

| Variable | Valeur |
|----------|--------|
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | chemin vers le JSON sur le serveur (ex. `Pyth Apps IAM People.json`) |
| `GOOGLE_SHEET_ID` | ID de la feuille cible |

---

## 5. Web app et WSGI

### 5.1 Créer la Web app

1. **Web** → **Add a new web app**.
2. **Manual configuration** (pas Django/Flask).
3. Choisir **Python 3.10** (ou la version disponible).

### 5.2 Fichier WSGI

1. Dans **Web**, cliquez sur le lien du fichier **WSGI configuration** (ex. `/var/www/leocarre_pythonanywhere_com_wsgi.py`).
2. **Remplacez tout le contenu** par (en adaptant `leocarre` et `pyth-apps`) :

```python
import sys
import os

# Chemin du projet (adapter le nom d'utilisateur si besoin)
path = '/home/LeoCarre/pyth-apps'
if path not in sys.path:
    sys.path.insert(0, path)

# Important : définir le répertoire de travail pour data/, exports/, etc.
os.chdir(path)

from wsgi import application
```

3. Enregistrez.

**En cas d’erreur** : vérifiez que le dossier existe bien (onglet **Files** : vous devez voir `pyth-apps` avec `app.py`, `wsgi.py`, etc.). Vérifiez aussi que **Virtualenv** pointe vers `/home/LeoCarre/pyth-apps/venv`. Consultez l’onglet **Log** (Error log) pour voir le message d’erreur exact.

### 5.3 Virtualenv

Dans **Web** → **Virtualenv**, indiquez :

```
/home/LeoCarre/pyth-apps/venv
```

(Remplacez `leocarre` par votre nom d’utilisateur PythonAnywhere.)

### 5.4 Reload

Cliquez sur le bouton vert **Reload** pour recharger l’application.

---

## 6. Vérification

- **URL** : `https://leocarre.pythonanywhere.com` (adapter avec votre username).
- Vous devez voir la page d’accueil Pyth-apps (modules Zendesk, Calculs Google Sheets).
- Pour **Sync vers Google Sheet** et **Calculs** : connectez-vous avec Google ; le redirect doit être exactement l’URL configurée dans Google Cloud Console.

---

## 7. Fichiers sensibles (Service Account / OAuth)

- Ne commitez **jamais** `.env`, `credentials.json`, `*IAM*.json`, `*Client*Secret*OAuth*.json`.
- Sur PythonAnywhere, tout passe par les **Environment variables** (pas de `.env`).
- Si vous utilisez le **Service Account** (export direct gsheet), uploadez le fichier JSON du compte de service dans le dossier du projet (ex. `~/pyth-apps/`) et indiquez son nom dans `GOOGLE_SHEETS_CREDENTIALS_PATH`.

---

## 8. Mises à jour du code

Après un `git push` sur GitHub, sur PythonAnywhere :

```bash
cd ~/pyth-apps
git pull
source venv/bin/activate
pip install -r requirements.txt   # si requirements ont changé
```

Puis **Web** → **Reload**.

---

## Dépannage WSGI

- **Erreur au chargement** : ouvrez **Web** → **Error log** et regardez la dernière ligne (ImportError, ModuleNotFoundError, etc.).
- **Chemin** : le dossier doit s’appeler exactement `pyth-apps` si vous avez fait `git clone ... pyth-apps.git`. Sinon adaptez `path = '/home/LeoCarre/NOM_DU_DOSSIER'` dans le fichier WSGI.
- **Virtualenv** : **Web** → **Virtualenv** doit être renseigné : `/home/LeoCarre/pyth-apps/venv` (bouton vert pour créer/choisir le venv si besoin).
- **`a2wsgi` manquant** : dans une console Bash, `cd ~/pyth-apps && source venv/bin/activate && pip install a2wsgi` puis Reload.

### Erreur 502 et HARAKIRI (server.log)

Si vous voyez **502** (« Something went wrong ») et dans **Server log** des lignes du type :

- `HARAKIRI ON WORKER 1` puis `worker 1 died, killed by signal 9`

**Cause** : sous **a2wsgi + uWSGI** (single process), l’event loop asyncio n’est pas correctement piloté. Les routes déclarées en `async def` peuvent ne jamais terminer et rester en attente jusqu’à ce qu’uWSGI tue le worker (timeout ~30 s = HARAKIRI).

**Modifications dans l’app** :

- Les routes qui n’ont pas besoin d’`await` sont en **`def` (sync)** : `/`, `/favicon.ico`, `/zendesk`, `/zendesk/sync`, `/auth/google`, `/auth/google/callback`, `/auth/disconnect`, `/zendesk/sync/settings`, `/sync-now`, `/status/page`, `/status`, `/health`. Elles répondent correctement sous WSGI.
- La page d’accueil ne fait pas d’appel Zendesk/Google (statut détaillé sur `/status/page`).
- Le statut est mis en cache 60 s pour éviter les timeouts sur la page Statut.

Si la 502 apparaît encore sur une autre URL, vérifiez les logs et les credentials (OAuth, Zendesk).
