# Guide d'Export CSV/Excel

## 🎯 Mode CSV/Excel (Recommandé)

Le mode CSV/Excel est **beaucoup plus simple** que Google Sheets car il ne nécessite aucune configuration Google Cloud.

## ⚙️ Configuration

Dans votre fichier `.env`, configurez simplement :

```env
# Zendesk Configuration
ZENDESK_SUBDOMAIN=votre-sous-domaine
ZENDESK_EMAIL=votre-email@exemple.com
ZENDESK_API_TOKEN=votre-token-api

# Export Configuration
EXPORT_MODE=csv
# ou EXPORT_MODE=xlsx pour Excel

# Répertoire de sortie (optionnel, défaut: exports)
EXPORT_OUTPUT_DIR=exports
```

## 📁 Fichiers générés

Les fichiers sont créés dans le répertoire `exports/` (ou celui spécifié) avec un nom basé sur la date/heure :

- **CSV** : `tickets_20231215_143022.csv`
- **Excel** : `tickets_20231215_143022.xlsx`

## 🚀 Utilisation

1. **Démarrer l'application** :

   ```bash
   python app.py
   ```

2. **Import complet** :

   - Via l'interface web : http://localhost:8000
   - Via l'API : `POST http://localhost:8000/import/full`

3. **Import incrémental** (dernières 24h) :
   - Via l'interface web : http://localhost:8000
   - Via l'API : `POST http://localhost:8000/import/incremental?hours=24`

## 📊 Format Excel

Les fichiers Excel incluent :

- ✅ En-têtes formatés (gras, fond gris)
- ✅ Colonnes ajustées automatiquement
- ✅ Onglet nommé "Tickets"
- ✅ Prêt à être ouvert dans Excel, Google Sheets, ou tout autre tableur

## 📋 Format CSV

Les fichiers CSV :

- ✅ Encodage UTF-8 (support des caractères spéciaux)
- ✅ Séparateur virgule
- ✅ Compatible avec Excel, Google Sheets, et tous les tableurs

## 🔄 Exports incrémentaux

Pour les exports incrémentaux, les fichiers sont nommés par date :

- `tickets_20231215.csv` (un fichier par jour)

Si vous relancez un export le même jour, les nouvelles données sont **ajoutées** au fichier existant (pour CSV uniquement).

## 💡 Avantages du mode CSV/Excel

- ✅ **Aucune configuration Google** nécessaire
- ✅ **Fichiers locaux** faciles à partager
- ✅ **Pas de limites API** Google
- ✅ **Plus rapide** (pas de requêtes réseau)
- ✅ **Compatible** avec tous les outils (Excel, Google Sheets, etc.)

## 📦 Installation des dépendances

Pour le mode CSV, aucune dépendance supplémentaire n'est nécessaire.

Pour le mode Excel, installez `openpyxl` :

```bash
pip install openpyxl
```

Ou installez toutes les dépendances :

```bash
pip install -r requirements.txt
```
