# Héberger le projet sur PythonAnywhere (sans Google)

Ce guide permet d’héberger le **Zendesk Export Connector** sur [www.pythonanywhere.com](https://www.pythonanywhere.com) en utilisant uniquement l’**export CSV ou Excel**. Aucun projet Google Cloud ni Google Sheets n’est nécessaire.

---

## Pourquoi sans Google ?

En configurant `EXPORT_MODE=csv` (ou `xlsx`), l’application :

- se connecte uniquement à **Zendesk** ;
- écrit les fichiers dans le dossier **`exports/`** sur le serveur ;
- ne nécessite **aucun compte Google**, ni Service Account, ni projet Cloud.

Vous pourrez télécharger les CSV/Excel depuis les fichiers du projet sur PythonAnywhere ou via une tâche planifiée qui les envoie par email (configuration optionnelle).

---

## Prérequis

- Un compte [PythonAnywhere](https://www.pythonanywhere.com) (gratuit ou payant)
- Vos identifiants Zendesk (sous-domaine, email, API token)

---

## 1. Créer un compte et ouvrir un projet

1. Inscrivez-vous sur [pythonanywhere.com](https://www.pythonanywhere.com).
2. Allez dans l’onglet **Files** et repérez votre répertoire utilisateur (ex. `/home/votre_username/`).

---

## 2. Envoyer le projet sur PythonAnywhere

### Option A : Upload manuel (ZIP)

1. Sur votre machine, créez une archive du projet **sans** le dossier `venv` et sans `.env` :
   - Inclure : `app.py`, `zendesk_client.py`, `export_client.py`, `config.py`, `requirements.txt`, `docs/`, etc.
   - Exclure : `venv/`, `.env`, `exports/*.csv` (optionnel)
2. Dans **Files**, uploadez le ZIP.
3. Clic droit sur le ZIP → **Extract**.

### Option B : Git (si votre projet est sur un dépôt)

Dans l’onglet **Consoles**, ouvrez un **Bash** :

```bash
cd ~
git clone https://github.com/votre-repo/zendesk-connector.git
cd zendesk-connector
```

(Adaptez l’URL à votre dépôt.)

---

## 3. Créer l’environnement virtuel et installer les dépendances

Dans une console **Bash** :

```bash
cd ~/ZendeskConnector   # ou le nom du dossier extrait / cloné
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Pour un hébergement **sans Google**, vous pouvez utiliser un `requirements.txt` allégé (sans gspread, etc.). Si votre fichier actuel contient déjà des dépendances optionnelles, l’installation fonctionnera quand même avec `EXPORT_MODE=csv`.

---

## 4. Variables d’environnement (remplacer le .env)

Sans créer de projet Google, configurez uniquement Zendesk et l’export :

1. Allez dans l’onglet **Web**.
2. Descendez jusqu’à **Environment variables** (ou **Code** puis lien vers la config WSGI selon l’interface).
3. Ajoutez les variables suivantes (remplacez par vos valeurs) :

| Variable | Valeur |
|----------|--------|
| `ZENDESK_SUBDOMAIN` | `horrea` (uniquement le sous-domaine) |
| `ZENDESK_EMAIL` | `votre-email@exemple.com` |
| `ZENDESK_API_TOKEN` | `votre-token-api` |
| `EXPORT_MODE` | `csv` |
| `EXPORT_OUTPUT_DIR` | `exports` |

Sur PythonAnywhere, les variables définies dans la section **Web** sont visibles par l’application. Vous n’avez pas besoin de fichier `.env` sur le serveur si tout est défini ici.

---

## 5. Lancer l’application (Web app)

### 5.1 Créer une Web app

1. Onglet **Web** → **Add a new web app**.
2. Choisir **Manual configuration** (pas Django/Flask).
3. Choisir **Python 3.10** (ou la version proposée).

### 5.2 Configurer le WSGI

Le projet contient un fichier **`wsgi.py`** qui adapte FastAPI (ASGI) en WSGI grâce à `a2wsgi`. Il faut que PythonAnywhere charge ce module.

1. Dans **Web**, cliquez sur le lien vers le fichier **WSGI configuration** (ex. `/var/www/votre_username_pythonanywhere_com_wsgi.py`).
2. **Remplacez tout le contenu** par (en adaptant le chemin) :

```python
import sys
path = '/home/VOTRE_USERNAME/ZendeskConnector'   # ← remplacer VOTRE_USERNAME
if path not in sys.path:
    sys.path.insert(0, path)

from wsgi import application
```

3. Enregistrez le fichier.

Le fichier `wsgi.py` à la racine du projet s’occupe d’exposer l’app FastAPI en WSGI.

### 5.3 Virtualenv et reload

1. Dans **Web**, section **Virtualenv**, indiquez le chemin vers votre venv :  
   `/home/votre_username/ZendeskConnector/venv`
2. Cliquez sur **Reload** pour recharger l’application.

Si PythonAnywhere exige une app WSGI classique, il faudra peut‑être utiliser un adaptateur ASGI→WSGI (voir section 7).

---

## 6. Utiliser l’application

- **URL** : `https://votre_username.pythonanywhere.com`
- Ouvrez cette URL : vous devriez voir l’interface avec les boutons **Import complet** et **Import incrémental**.
- Les fichiers CSV sont créés dans le dossier **`exports/`** du projet sur le serveur. Vous pouvez les consulter ou les télécharger depuis l’onglet **Files** (par ex. `~/ZendeskConnector/exports/`).

---

## 7. Alternative : lancer un export sans interface web (tâche planifiée)

Si vous préférez ne pas utiliser la Web app et lancer les exports à la main ou via un cron :

1. **Web** → vous pouvez ne pas créer de Web app, ou la désactiver.
2. **Consoles** → ouvrez un Bash.
3. Pour lancer un export à la demande :

```bash
cd ~/ZendeskConnector
source venv/bin/activate
export ZENDESK_SUBDOMAIN=horrea
export ZENDESK_EMAIL=votre-email@exemple.com
export ZENDESK_API_TOKEN=votre-token
export EXPORT_MODE=csv
python3 -c "
from zendesk_client import ZendeskClient
from export_client import ExportClient
from config import get_settings
s = get_settings()
z = ZendeskClient(s.ZENDESK_SUBDOMAIN, s.ZENDESK_EMAIL, s.ZENDESK_API_TOKEN)
e = ExportClient(output_dir=s.EXPORT_OUTPUT_DIR, file_format='csv')
tickets = list(z.get_all_tickets())
e.export(tickets)
print(f'Exporté {len(tickets)} tickets')
"
```

4. Vous pouvez en faire une **tâche planifiée** (onglet **Schedule**) pour exécuter un script similaire tous les jours.

---

## 8. Récapitulatif (sans Google)

| Étape | Action |
|-------|--------|
| 1 | Compte PythonAnywhere |
| 2 | Upload ou clone du projet |
| 3 | `venv` + `pip install -r requirements.txt` |
| 4 | Variables d’env (Zendesk + `EXPORT_MODE=csv`) |
| 5 | Web app + WSGI (ou tâche planifiée) |
| 6 | Accès à l’URL et aux CSV dans `exports/` |

Aucun projet Google, ni credentials, ni Google Sheets n’est nécessaire pour faire tourner le connecteur en mode CSV/Excel sur PythonAnywhere.
