"""
Flux OAuth Google pour la webapp "Sync vers Google Sheet".

Permet à l'utilisateur de se connecter avec son compte Google (sans Service Account).
Les tokens sont stockés localement pour accéder à l'API Google Sheets.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Scopes nécessaires pour Sheets et Drive (lister les fichiers)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_data_path(settings) -> Path:
    """Retourne le chemin du fichier de données OAuth."""
    path = Path(settings.OAUTH_DATA_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_oauth_data(settings) -> Dict[str, Any]:
    """Charge les tokens et préférences depuis le fichier."""
    path = get_data_path(settings)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Impossible de charger oauth_data: {e}")
        return {}


def save_oauth_data(settings, data: Dict[str, Any]) -> None:
    """Sauvegarde les tokens et préférences."""
    path = get_data_path(settings)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_auth_url(settings, redirect_uri: str, state: Optional[str] = None) -> str:
    """
    Construit l'URL d'autorisation Google OAuth.
    state: URL de retour après connexion (ex: /zendesk/sync ou /sheets-calc).
    """
    from urllib.parse import quote
    base = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state
    return f"{base}?{urlencode(params)}"


def exchange_code_for_tokens(settings, code: str, redirect_uri: str) -> Dict[str, Any]:
    """
    Échange le code d'autorisation contre des tokens.
    Retourne les tokens et les enregistre dans oauth_data.
    """
    import requests

    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(url, data=data, headers=headers, timeout=10)
    resp.raise_for_status()
    tokens = resp.json()

    oauth_data = load_oauth_data(settings)
    oauth_data["refresh_token"] = tokens.get("refresh_token")
    oauth_data["access_token"] = tokens.get("access_token")
    oauth_data["token_expiry"] = tokens.get("expires_in", 3600)  # secondes
    import time
    oauth_data["token_expiry_ts"] = time.time() + tokens.get("expires_in", 3600)
    save_oauth_data(settings, oauth_data)
    return oauth_data


def get_valid_credentials(settings):
    """
    Retourne des credentials valides pour l'API Google (Sheets).
    Rafraîchit l'access_token si nécessaire.
    """
    from google.oauth2.credentials import Credentials
    import requests
    import time

    oauth_data = load_oauth_data(settings)
    refresh_token = oauth_data.get("refresh_token")
    if not refresh_token:
        return None

    access_token = oauth_data.get("access_token")
    expiry_ts = oauth_data.get("token_expiry_ts", 0)
    if access_token and expiry_ts and time.time() < expiry_ts - 60:
        return Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=SCOPES,
        )

    # Rafraîchir
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    resp = requests.post(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=10)
    resp.raise_for_status()
    tokens = resp.json()
    oauth_data["access_token"] = tokens["access_token"]
    oauth_data["token_expiry_ts"] = time.time() + tokens.get("expires_in", 3600)
    save_oauth_data(settings, oauth_data)

    return Credentials(
        token=tokens["access_token"],
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=SCOPES,
    )


def is_google_connected(settings) -> bool:
    """Indique si un compte Google est connecté (refresh_token présent)."""
    data = load_oauth_data(settings)
    return bool(data.get("refresh_token"))


def disconnect_google(settings) -> None:
    """Supprime les tokens (déconnexion)."""
    save_oauth_data(settings, {})
