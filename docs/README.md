# Documentation — Pyth-apps (Zendesk Export Connector)

Cette documentation décrit le fonctionnement du projet et comment l’activer et le lancer.

---

## Vue d’ensemble du projet

**Pyth-apps** est une plateforme d’outils web qui regroupe plusieurs modules :

- **Page d’accueil** (`/`) : choix du module (Zendesk, Calculs Google Sheets).
- **Zendesk – Export & Sync** (`/zendesk`) : connexion à l’API Zendesk, export des tickets en CSV/Excel, et **Sync vers Google Sheet** (OAuth utilisateur) sous `/zendesk/sync` et `/zendesk/sync/settings`.
- **Calculs entre deux Google Sheets** (`/sheets-calc`) : comparaison de deux feuilles (différences, lignes communes) selon une colonne clé, avec le même compte Google OAuth.

L’application :

- Se connecte à l’API Zendesk (authentification par token)
- Récupère les tickets avec pagination (tous les tickets, pas de limite artificielle)
- Exporte les données vers **CSV**, **Excel** ou **Google Sheets**
- Expose une interface web et une API REST pour lancer les exports

Les tickets sont triés par **date de création décroissante** (plus récents en premier) et incluent les **custom fields** Zendesk.

### URLs principales (webapp)

| URL | Description |
|-----|-------------|
| `/` | Page d’accueil – choix du module |
| `/zendesk` | Dashboard Zendesk (import complet / incrémental, lien vers Sync) |
| `/zendesk/sync` | Sync vers Google Sheet (connexion Google, mise à jour manuelle) |
| `/zendesk/sync/settings` | Paramètres : ID feuille, onglet, mise à jour auto |
| `/sheets-calc` | Calculs entre deux Google Sheets (formulaire + résultat) |
| `/auth/google?next=...` | Connexion Google OAuth (retour vers `next` après connexion) |
| `/docs` | Documentation API (Swagger) |
| `/status` | Statut des connexions (API JSON) |
| `/status/page` | Page Statut (interface) |

---

## Architecture et fonctionnement

### Structure du projet

```
Zendesk Connector/
├── app.py                 # Application FastAPI
├── config.py
├── zendesk_client.py
├── export_client.py
├── gsheet_client.py
├── google_oauth_flow.py
├── sync_export_to_sheet.py
├── wsgi.py
├── requirements.txt
├── env.example            # À copier en .env
├── test_zendesk.py / test_google_sheets.py / fix_env.py
├── docs/
└── exports/               # Générés (ignorés par git)
```

### Flux de données

1. **Lancement d’un import** (interface web ou API)
2. **Récupération Zendesk** : `zendesk_client` appelle l’API avec pagination (`next_page`)
3. **Normalisation** : chaque ticket est mis en forme (champs plats + custom_fields)
4. **Export** : selon `EXPORT_MODE` → CSV/Excel dans `exports/` ou écriture dans Google Sheets

### Modes d’export

| Mode     | Fichier / destination | Configuration requise                    |
|----------|------------------------|------------------------------------------|
| `csv`    | `exports/tickets_*.csv` | Zendesk uniquement — **aucun projet Google** |
| `xlsx`   | `exports/tickets_*.xlsx` | Zendesk uniquement — **aucun projet Google** |
| `gsheet` | Google Sheet cible     | Zendesk + projet Google Cloud + Service Account + Sheet partagée |

---

## Prérequis

- **Python 3.8+** (testé avec 3.13)
- **Compte Zendesk** avec accès API et token activé
- **Optionnel (Google Sheets)** : projet Google Cloud, Service Account, APIs Sheets + Drive activées

---

## Activer le projet (installation et configuration)

### 1. Aller dans le dossier du projet

```bash
cd "Zendesk Connector"
```

### 2. Créer et activer l’environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate   # Windows : venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d’environnement

Créer un fichier **`.env`** à la racine du projet.

**Exemple minimal (export CSV, recommandé) :**

```env
# Zendesk (obligatoire)
ZENDESK_SUBDOMAIN=horrea
ZENDESK_EMAIL=votre-email@exemple.com
ZENDESK_API_TOKEN=votre-token-api

# Export
EXPORT_MODE=csv
EXPORT_OUTPUT_DIR=exports
```

> **Important** : `ZENDESK_SUBDOMAIN` doit être uniquement le sous-domaine (ex. `horrea`), pas l’URL complète.

**Option Google Sheets :**

```env
EXPORT_MODE=gsheet
GOOGLE_SHEETS_CREDENTIALS_PATH=credentials.json
GOOGLE_SHEET_ID=id-de-votre-feuille
GOOGLE_SHEET_NAME=Tickets
```

Voir le guide à la racine : `SETUP_GOOGLE_SHEETS.md`.

### 5. Vérifier la connexion Zendesk (optionnel)

```bash
python3 test_zendesk.py
```

---

## Lancer le projet (démarrer le serveur)

### Méthode recommandée : script Python

```bash
python3 app.py
```

Le serveur écoute sur **http://localhost:8000** (ou le port défini dans `.env`).

### Avec uvicorn

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Avec rechargement automatique (développement) :

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### En arrière-plan (Linux/Mac)

```bash
nohup python3 app.py > app.log 2>&1 &
```

Les logs sont dans `app.log`.

---

## Vérifier que le serveur tourne

Au démarrage, vous devriez voir quelque chose comme :

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**URLs utiles :**

| URL                      | Description              |
|--------------------------|--------------------------|
| http://localhost:8000     | Interface web (boutons d’import) |
| http://localhost:8000/status | Statut Zendesk + export   |
| http://localhost:8000/docs | Documentation API (Swagger) |

---

## Utilisation après lancement

1. Ouvrir **http://localhost:8000**
2. **Import complet** : récupère tous les tickets et les exporte (CSV/Excel ou Google Sheet)
3. **Import incrémental** : récupère les tickets mis à jour dans les dernières 24 h (paramètre `hours` possible via l’API)

Les fichiers CSV/Excel sont créés dans le dossier **`exports/`**.

---

## Dépannage rapide

| Problème              | Vérification |
|-----------------------|--------------|
| Connexion Zendesk KO  | `.env` : `ZENDESK_SUBDOMAIN` = sous-domaine seul (ex. `horrea`), pas l’URL complète. Tester avec `python3 test_zendesk.py` |
| Moins de tickets que prévu | L’API Zendesk ne renvoie pas les tickets archivés/supprimés. Seuls les tickets actifs sont comptés. |
| Export Google Sheets  | Voir `SETUP_GOOGLE_SHEETS.md` et partage de la feuille avec l’email du Service Account. |

---

## Hébergement (sans Google)

Pour héberger sur **PythonAnywhere** en n’utilisant que l’export **CSV ou Excel**, aucun projet Google n’est nécessaire. Voir **[docs/PYTHONANYWHERE.md](PYTHONANYWHERE.md)**.

---

## Webapp « Sync vers Google Sheet »

Pour envoyer le dernier export CSV vers une **feuille Google Sheet** en vous connectant avec **votre compte Google** (sans Service Account) : voir **[docs/SYNC_GOOGLE_SHEET_WEBAPP.md](SYNC_GOOGLE_SHEET_WEBAPP.md)**. Accès dans l’app : lien **Sync vers Google Sheet** ou URL `/sync-app`.

---

## Référence des guides

- **README.md** (racine) — Présentation, installation détaillée, API, structure des données
- **docs/PYTHONANYWHERE.md** — Hébergement sur PythonAnywhere sans Google
- **docs/SYNC_GOOGLE_SHEET_WEBAPP.md** — Webapp Sync (connexion Google, mise à jour manuelle ou planifiée)
- **SETUP_GOOGLE_SHEETS.md** — Configuration Google Sheets (Service Account, optionnel)
- **GUIDE_CSV_EXCEL.md** — Utilisation du mode CSV/Excel

---

*Documentation du connecteur Zendesk — usage interne.*
