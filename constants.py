"""
Constantes partagées (ex. liste des modules) sans dépendance vers config ou clients.
Permet de servir la page d'accueil depuis le WSGI sans charger l'app FastAPI.
"""

MODULES = [
    {
        "url": "/zendesk",
        "title": "Zendesk – Export & Sync",
        "description": "Exporter les tickets Zendesk en CSV/Excel et synchroniser vers une Google Sheet.",
        "status_key": "zendesk",
    },
    {
        "url": "/sheets-calc",
        "title": "Calculs entre deux Google Sheets",
        "description": "Comparer deux feuilles, différences ou lignes communes selon une clé.",
        "status_key": "sheets_calc",
    },
]
