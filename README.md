# Pyth-apps — Zendesk to Google Sheets Connector

Connecteur Python léger pour synchroniser les tickets Zendesk vers Google Sheets (projet **Pyth-apps**).

> **Documentation** : pour le fonctionnement détaillé et comment activer/lancer le projet, voir **[docs/README.md](docs/README.md)**.

Application offrant un contrôle total sur la pagination, les champs, les filtres et les mises à jour, sans limite no-code sur les volumes.

## 📁 Structure du dépôt (pour GitHub)

```
Zendesk Connector/
├── app.py                 # Application FastAPI (serveur, imports, webapp Sync)
├── config.py              # Configuration (variables d'environnement)
├── zendesk_client.py      # Client API Zendesk (pagination, normalisation)
├── export_client.py       # Export CSV/Excel
├── gsheet_client.py       # Client Google Sheets (mode Service Account)
├── google_oauth_flow.py   # OAuth Google (webapp Sync)
├── sync_export_to_sheet.py # Sync dernier export → Google Sheet
├── wsgi.py                # Point d'entrée WSGI (PythonAnywhere)
├── requirements.txt
├── env.example             # Exemple de variables (copier en .env)
├── .gitignore
├── README.md
├── test_zendesk.py        # Test connexion Zendesk
├── test_google_sheets.py  # Test connexion Google Sheets (mode gsheet)
├── fix_env.py             # Utilitaire : corriger ZENDESK_SUBDOMAIN dans .env
├── docs/                   # Documentation
│   ├── README.md
│   ├── PYTHONANYWHERE.md
│   └── SYNC_GOOGLE_SHEET_WEBAPP.md
├── SETUP_GOOGLE_SHEETS.md
├── GUIDE_CSV_EXCEL.md
└── exports/               # Fichiers générés (ignorés par git)
```

## 🚀 Fonctionnalités

- **Import complet** : Récupération de tous les tickets Zendesk avec pagination automatique
- **Import incrémental** : Synchronisation basée sur `updated_at` pour les mises à jour régulières
- **Gestion de la pagination** : Support de la pagination cursor-based de Zendesk
- **Normalisation des données** : Structure plate optimisée pour Google Sheets
- **Interface web** : Interface minimale pour déclencher les imports
- **API REST** : Endpoints pour intégration avec d'autres systèmes

## 📋 Prérequis

- Python 3.8 ou supérieur
- Compte Zendesk avec accès API
- **Optionnel** : Compte Google Cloud avec Service Account (seulement pour le mode Google Sheets)

## 🔧 Installation

### 1. Cloner ou télécharger le projet

```bash
git clone ...
```

### 2. Créer un environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configuration Zendesk

1. Connectez-vous à votre instance Zendesk
2. Allez dans **Admin** > **Apps and integrations** > **APIs** > **Zendesk API**
3. Activez l'**API Token** et créez un nouveau token
4. Notez votre **sous-domaine Zendesk** (ex: `monentreprise` pour `monentreprise.zendesk.com`)

### 5. Configuration Google Sheets (OPTIONNEL - seulement si EXPORT_MODE=gsheet)

Si vous choisissez d'exporter vers Google Sheets, suivez ces étapes. Sinon, passez à l'étape 6.

#### Créer un Service Account

1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet ou sélectionnez un projet existant
3. Activez l'**API Google Sheets** et l'**API Google Drive**
4. Allez dans **IAM & Admin** > **Service Accounts**
5. Créez un nouveau Service Account
6. Téléchargez le fichier JSON de credentials
7. Renommez-le en `credentials.json` et placez-le à la racine du projet

#### Partager la Google Sheet

1. Ouvrez votre Google Sheet
2. Cliquez sur **Partager** (en haut à droite)
3. Ajoutez l'email du Service Account (trouvable dans le fichier `credentials.json`, champ `client_email`)
4. Donnez-lui les permissions **Éditeur**
5. Copiez l'**ID de la feuille** depuis l'URL :
   ```
   https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit
   ```

### 6. Configuration des variables d'environnement

Créez un fichier `.env` à la racine du projet (vous pouvez copier `env.example` vers `.env` puis modifier les valeurs) :

#### Option 1 : Export CSV/Excel (RECOMMANDÉ - Plus simple)

```env
# Zendesk Configuration
ZENDESK_SUBDOMAIN=votre-sous-domaine
ZENDESK_EMAIL=votre-email@exemple.com
ZENDESK_API_TOKEN=votre-token-api

# Export Configuration
EXPORT_MODE=csv
# ou EXPORT_MODE=xlsx pour Excel
EXPORT_OUTPUT_DIR=exports

# Application Configuration (optionnel)
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False
```

**Avantages** : Aucune configuration Google nécessaire, fichiers locaux faciles à partager.

#### Option 2 : Export Google Sheets

```env
# Zendesk Configuration
ZENDESK_SUBDOMAIN=votre-sous-domaine
ZENDESK_EMAIL=votre-email@exemple.com
ZENDESK_API_TOKEN=votre-token-api

# Export Configuration
EXPORT_MODE=gsheet

# Google Sheets Configuration
GOOGLE_SHEETS_CREDENTIALS_PATH=credentials.json
GOOGLE_SHEET_ID=votre-sheet-id
GOOGLE_SHEET_NAME=Tickets

# Application Configuration (optionnel)
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False
```

**Note** : Pour Google Sheets, suivez le guide dans `SETUP_GOOGLE_SHEETS.md`

## 🎯 Utilisation

### Démarrer le serveur

#### Méthode 1 : Avec le script Python (Recommandé)

```bash
python3 app.py
```

Le serveur démarre automatiquement sur `http://localhost:8000` (ou le port configuré dans `.env`).

#### Méthode 2 : Avec uvicorn directement

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Ou avec rechargement automatique en mode développement :

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

#### Méthode 3 : En arrière-plan (Linux/Mac)

```bash
nohup python3 app.py > app.log 2>&1 &
```

Le serveur tourne en arrière-plan et les logs sont écrits dans `app.log`.

#### Vérifier que le serveur fonctionne

Une fois le serveur démarré, vous devriez voir :

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

L'application est alors accessible sur :

- **Interface web** : http://localhost:8000
- **Documentation API** : http://localhost:8000/docs
- **Statut** : http://localhost:8000/status

### Interface Web

Accédez à `http://localhost:8000` pour voir l'interface web avec :

- Bouton pour l'import complet
- Bouton pour l'import incrémental
- Lien vers la documentation API interactive

### API Endpoints

#### Vérifier le statut

```bash
curl http://localhost:8000/status
```

#### Import complet

```bash
curl -X POST http://localhost:8000/import/full
```

#### Import incrémental (24 dernières heures)

```bash
curl -X POST http://localhost:8000/import/incremental?hours=24
```

#### Documentation interactive

Accédez à `http://localhost:8000/docs` pour la documentation Swagger interactive.

## 📁 Fichiers exportés (mode CSV/Excel)

Lorsque vous utilisez le mode CSV ou Excel, les fichiers sont créés dans le répertoire `exports/` (ou celui spécifié dans `EXPORT_OUTPUT_DIR`).

- Format CSV : `tickets_YYYYMMDD_HHMMSS.csv`
- Format Excel : `tickets_YYYYMMDD_HHMMSS.xlsx`

Les fichiers Excel incluent :

- En-têtes formatés (gras, fond gris)
- Colonnes ajustées automatiquement
- Onglet nommé "Tickets"

## 📊 Structure des données

Les tickets sont normalisés avec les champs suivants :

- `ticket_id` : ID unique du ticket
- `subject` : Sujet du ticket
- `status` : Statut (new, open, pending, solved, closed)
- `priority` : Priorité (low, normal, high, urgent)
- `requester_id` : ID du demandeur
- `assignee_id` : ID de l'assigné
- `created_at` : Date de création
- `updated_at` : Date de mise à jour
- `tags` : Tags séparés par des virgules
- `type` : Type de ticket
- `via` : Canal de création
- `url` : URL du ticket
- `description` : Description (tronquée à 500 caractères)

## 🔍 Logs

Les logs sont affichés dans la console avec le format :

```
2023-12-01 10:30:00 - zendesk_client - INFO - Page 1: 100 tickets récupérés
```

## ⚙️ Configuration avancée

### Modifier les champs extraits

Éditez la méthode `_normalize_ticket()` dans `zendesk_client.py` pour ajouter ou modifier les champs extraits.

### Modifier la taille des batches

Dans `app.py`, modifiez la condition `if len(tickets) >= 100:` pour changer la taille des batches d'écriture.

### Personnaliser les en-têtes Google Sheets

Modifiez `DEFAULT_HEADERS` dans `gsheet_client.py` pour changer l'ordre ou ajouter des colonnes.

## 🐛 Dépannage

### Erreur de connexion Zendesk

- Vérifiez que le sous-domaine, l'email et le token API sont corrects
- Vérifiez que l'API Token est activé dans Zendesk
- Vérifiez les permissions de l'utilisateur Zendesk

### Erreur de connexion Google Sheets

- Vérifiez que le fichier `credentials.json` est présent et valide
- Vérifiez que le Service Account a accès à la feuille
- Vérifiez que l'ID de la feuille est correct

### Limites de l'API Zendesk

L'API Zendesk a des limites de taux. Si vous rencontrez des erreurs 429 (Too Many Requests), l'application gère automatiquement les retries, mais vous pouvez réduire `page_size` dans `get_all_tickets()`.

## 📝 Notes

- Les imports complets peuvent prendre du temps pour de gros volumes (milliers de tickets)
- L'import incrémental évite les doublons en vérifiant les IDs existants
- Les données sont écrites par batches pour optimiser les performances
- L'application crée automatiquement l'onglet et les en-têtes s'ils n'existent pas

## 🔒 Sécurité

- **Ne commitez jamais** le fichier `.env` ou `credentials.json`
- Utilisez des variables d'environnement en production
- Limitez les permissions du Service Account au strict nécessaire
- Utilisez HTTPS en production

## 📄 Licence

Ce projet est destiné à un usage interne.
