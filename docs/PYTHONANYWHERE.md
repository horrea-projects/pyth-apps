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
path = '/home/leocarre/pyth-apps'
if path not in sys.path:
    sys.path.insert(0, path)

from wsgi import application
```

3. Enregistrez.

### 5.3 Virtualenv

Dans **Web** → **Virtualenv**, indiquez :

```
/home/leocarre/pyth-apps/venv
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
