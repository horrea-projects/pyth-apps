"""
Application FastAPI principale – plateforme de webapps (modules).

- Page d'accueil : choix du module (Zendesk, Calculs Google Sheets, etc.)
- Module Zendesk : export tickets + sync vers Google Sheet
- Module Calculs : opérations entre deux Google Sheets
"""

import html
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, FileResponse
from pydantic import BaseModel
from pathlib import Path

from config import get_settings
from zendesk_client import ZendeskClient
from gsheet_client import GoogleSheetsClient
from export_client import ExportClient
from constants import MODULES
from templates import nav_html, home_page_html, pythapps_base_html, breadcrumb_fragment, status_page_html

# OAuth et modules optionnels
try:
    from google_oauth_flow import (
        get_auth_url,
        exchange_code_for_tokens,
        get_valid_credentials,
        load_oauth_data,
        save_oauth_data,
        is_google_connected,
        disconnect_google,
    )
    from sync_export_to_sheet import sync_csv_to_sheet, verify_sheet_access
    from sheets_calc_service import read_sheet, OPERATIONS as SHEETS_CALC_OPERATIONS
    SYNC_APP_AVAILABLE = True
    SHEETS_CALC_AVAILABLE = True
except ImportError as e:
    logging.warning("Modules optionnels non chargés: %s", e)
    SYNC_APP_AVAILABLE = False
    SHEETS_CALC_AVAILABLE = False
    SHEETS_CALC_OPERATIONS = {}

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialisation de l'application FastAPI
app = FastAPI(
    title="Pyth-apps",
    description="Plateforme d’outils : Zendesk export/sync, calculs entre Google Sheets",
    version="1.0.0"
)

# Chargement de la configuration
settings = get_settings()

# Initialisation des clients (seront créés à la première utilisation)
zendesk_client: ZendeskClient = None
gsheet_client: GoogleSheetsClient = None
export_client: ExportClient = None


def get_zendesk_client() -> ZendeskClient:
    """Récupère ou crée le client Zendesk."""
    global zendesk_client
    if zendesk_client is None:
        zendesk_client = ZendeskClient(
            subdomain=settings.ZENDESK_SUBDOMAIN,
            email=settings.ZENDESK_EMAIL,
            api_token=settings.ZENDESK_API_TOKEN
        )
    return zendesk_client


def _resolve_credentials_path() -> str:
    """Chemin vers le JSON Service Account (variable d'env ou fichiers par défaut)."""
    path = settings.GOOGLE_SHEETS_CREDENTIALS_PATH
    if path and Path(path).exists():
        return path
    # Fichiers par défaut à la racine du projet
    root = Path(__file__).resolve().parent
    for name in ("Pyth Apps IAM People.json", "credentials.json"):
        candidate = root / name
        if candidate.exists():
            return str(candidate)
    raise ValueError(
        "GOOGLE_SHEETS_CREDENTIALS_PATH non défini ou fichier introuvable. "
        "Définissez la variable dans .env ou placez le JSON (ex: Pyth Apps IAM People.json) à la racine."
    )


def get_gsheet_client() -> GoogleSheetsClient:
    """Récupère ou crée le client Google Sheets."""
    global gsheet_client
    if gsheet_client is None:
        if not settings.GOOGLE_SHEET_ID:
            raise ValueError("GOOGLE_SHEET_ID requis pour le mode Google Sheets")
        credentials_path = _resolve_credentials_path()
        gsheet_client = GoogleSheetsClient(
            credentials_path=credentials_path,
            sheet_id=settings.GOOGLE_SHEET_ID,
            sheet_name=settings.GOOGLE_SHEET_NAME
        )
    return gsheet_client


def get_export_client():
    """Récupère ou crée le client d'export selon le mode configuré."""
    global export_client
    if export_client is None:
        if settings.EXPORT_MODE == "gsheet":
            return get_gsheet_client()
        else:
            export_client = ExportClient(
                output_dir=settings.EXPORT_OUTPUT_DIR,
                file_format=settings.EXPORT_FILE_FORMAT if settings.EXPORT_MODE == "xlsx" else "csv"
            )
    return export_client


# Modèles Pydantic pour les réponses
class ImportResponse(BaseModel):
    """Réponse pour les opérations d'import."""
    success: bool
    message: str
    tickets_processed: int = 0
    error: str = None


class StatusResponse(BaseModel):
    """Réponse pour le statut de l'application."""
    status: str
    zendesk_connected: bool
    export_mode: str
    export_ready: bool
    export_info: str = ""


# ---------- Page d'accueil (choix du module : MODULES dans constants.py) ----------

# Cache du statut pour éviter d'appeler Zendesk à chaque requête (évite timeout HARAKIRI sur PythonAnywhere)
_status_cache: tuple = (0, None)
_STATUS_CACHE_TTL = 60  # secondes


def _get_status_data() -> dict:
    """Retourne un dict de statut (zendesk, google_oauth, overall). Mis en cache 60s pour éviter les timeouts."""
    global _status_cache
    now = time.time()
    if _status_cache[1] is not None and (now - _status_cache[0]) < _STATUS_CACHE_TTL:
        return _status_cache[1]
    google_connected = False
    if SYNC_APP_AVAILABLE:
        try:
            google_connected = is_google_connected(settings)
        except Exception:
            pass
    try:
        zendesk = get_zendesk_client()
        zendesk_ok = zendesk.test_connection()
    except Exception as e:
        logger.debug("Status zendesk: %s", e)
        zendesk_ok = False
    export_mode = settings.EXPORT_MODE
    export_ready = False
    export_info = ""
    if export_mode == "gsheet":
        try:
            gsheet = get_gsheet_client()
            export_ready = gsheet.test_connection()
            export_info = "Google Sheets connecté" if export_ready else "Non connecté"
        except Exception as e:
            export_info = str(e)[:80]
    else:
        try:
            get_export_client()
            export_ready = True
            export_info = f"Export {export_mode.upper()} – Répertoire prêt"
        except Exception as e:
            export_info = str(e)[:80]
    overall = "healthy" if (zendesk_ok and export_ready) else "degraded"
    data = {
        "overall": overall,
        "zendesk": {
            "connected": zendesk_ok,
            "export_ready": export_ready,
            "export_info": export_info,
        },
        "google_oauth": {"connected": google_connected},
    }
    _status_cache = (now, data)
    return data


@app.get("/", response_class=HTMLResponse)
def root():
    """Page d'accueil : liste des modules. Sync pour éviter blocage a2wsgi+uWSGI (pas d'event loop)."""
    return HTMLResponse(home_page_html(MODULES, None))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Réponse immédiate pour éviter timeout HARAKIRI."""
    return Response(status_code=204)


# ---------- Module Zendesk ----------

def _zendesk_page_html(extra: str = "") -> str:
    """Layout Zendesk : base Pyth-apps + card."""
    return (
        pythapps_base_html("Zendesk", breadcrumb_fragment("Zendesk"))
        + '<div class="card"><h1>Zendesk – Export & Sync</h1>'
        + extra
        + "</div></body></html>"
    )


def _format_ts(ts: float) -> str:
    """Formate un timestamp (mtime ou epoch) pour affichage."""
    if not ts:
        return "—"
    try:
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "—"


@app.get("/zendesk", response_class=HTMLResponse)
def zendesk_dashboard(request: Request):
    """Dashboard du module Zendesk : statut, derniers runs, fichiers à exporter, lien sync."""
    try:
        status = get_status_data()
    except Exception as e:
        logger.exception("zendesk_dashboard get_status_data")
        status = {"zendesk": {"connected": False}, "google_oauth": {"connected": False}}

    try:
        oauth_data = load_oauth_data(settings) if SYNC_APP_AVAILABLE else {}
    except Exception as e:
        logger.warning("zendesk_dashboard load_oauth_data: %s", e)
        oauth_data = {}

    last_sync_at = oauth_data.get("last_sync_at")
    tickets_all_updated = None
    try:
        export_dir = Path(settings.EXPORT_OUTPUT_DIR)
        all_csv = export_dir / "tickets_all.csv"
        if all_csv.exists():
            tickets_all_updated = all_csv.stat().st_mtime
    except Exception as e:
        logger.warning("zendesk_dashboard tickets_all mtime: %s", e)

    zendesk_status = "OK" if status.get("zendesk", {}).get("connected") else "Erreur"
    google_status = "Connecté" if status.get("google_oauth", {}).get("connected") else "Non connecté"
    if oauth_data.get("sheet_id"):
        google_status += " · Feuille configurée"
    else:
        google_status += " · Feuille non configurée"

    all_files = _list_all_export_files()

    # Échapper les noms de fichiers pour l'URL (éviter caractères spéciaux dans le HTML)
    def _escape_url(s: str) -> str:
        return quote(s, safe="")

    extra = f"""
    <div class="info"><strong>Mode d'export :</strong> {settings.EXPORT_MODE.upper()}</div>
    <h2>Statut & derniers runs</h2>
    <table style="max-width:520px; border-collapse:collapse; font-size:14px;"><tbody>
        <tr><td style="padding:6px 12px 6px 0; vertical-align:top;">Fichier tickets_all.csv</td><td style="padding:6px 0;">Dernière mise à jour : {_format_ts(tickets_all_updated)}</td></tr>
        <tr><td style="padding:6px 12px 6px 0; vertical-align:top;">Google Sheet</td><td style="padding:6px 0;">Dernière sync : {_format_ts(last_sync_at)}</td></tr>
        <tr><td style="padding:6px 12px 6px 0; vertical-align:top;">Zendesk</td><td style="padding:6px 0;">{zendesk_status}</td></tr>
        <tr><td style="padding:6px 12px 6px 0; vertical-align:top;">Google (OAuth / feuille)</td><td style="padding:6px 0;">{google_status}</td></tr>
    </tbody></table>
    <h2>Fichiers d'export</h2>
    """
    if all_files:
        extra += "<p style=\"font-size:14px;\">Télécharger : "
        for f in all_files:
            name = f["name"]
            safe_name = _escape_url(name)
            extra += f'<a href="/zendesk/exports/download/{safe_name}" download>{html.escape(name)}</a> '
            extra += f'<span style="color:#666;">({_format_ts(f["modified"])})</span> '
        extra += "</p>"
    else:
        extra += '<p style="font-size:14px; color:#666;">Aucun fichier dans <code>exports/</code>.</p>'
    extra += """
    <p style="margin-top:20px;"><a href="/zendesk/sync" class="btn btn-blue">Sync vers Google Sheet</a></p>
    <p style="margin-top:24px;"><a href="/" class="btn btn-secondary">Accueil</a></p>
    """
    return HTMLResponse(_zendesk_page_html(extra))


# ---------- Zendesk : Sync vers Google Sheet ----------

def _import_progress_path() -> Path:
    """Fichier JSON de progression de l'import (data/import_progress.json)."""
    return Path(settings.OAUTH_DATA_FILE).parent / "import_progress.json"


def _write_import_progress(status: str, count: int = 0, message: str = "", error: str = ""):
    """Écrit l'état de l'import pour affichage sur la page de progression."""
    path = _import_progress_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"status": status, "count": count, "message": message, "error": error, "updated_at": time.time()}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("Impossible d'écrire import_progress: %s", e)


def _list_export_files() -> list:
    """Liste les fichiers CSV : tickets_all.csv en premier (base pour sync Looker Studio), puis les autres par date."""
    export_dir = Path(settings.EXPORT_OUTPUT_DIR)
    if not export_dir.exists():
        return []
    files = list(export_dir.glob("tickets_*.csv"))
    all_path = export_dir / "tickets_all.csv"
    rest = [p for p in files if p.name != "tickets_all.csv"]
    rest.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if all_path.exists():
        files = [all_path] + rest
    else:
        files = rest
    return [{"name": p.name, "path": str(p), "modified": p.stat().st_mtime} for p in files]


def _list_all_export_files() -> list:
    """Liste tous les fichiers du répertoire exports/ (pour téléchargement). Tri par date décroissante."""
    try:
        export_dir = Path(settings.EXPORT_OUTPUT_DIR)
        if not export_dir.exists() or not export_dir.is_dir():
            return []
        files = [p for p in export_dir.iterdir() if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [{"name": p.name, "path": str(p), "modified": p.stat().st_mtime} for p in files]
    except Exception as e:
        logger.warning("_list_all_export_files: %s", e)
        return []


def _sync_app_base_html(breadcrumb: str = ""):
    """Base HTML style Pyth-apps (header + styles). breadcrumb affiché dans le header."""
    return pythapps_base_html("Sync vers Google Sheet", breadcrumb_fragment(breadcrumb))


@app.get("/zendesk/sync", response_class=HTMLResponse)
def sync_app_dashboard(request: Request):
    """Tableau de bord de la webapp Sync vers Google Sheet."""
    if not SYNC_APP_AVAILABLE:
        return HTMLResponse(
            _sync_app_base_html()
            + """
            <div class="card">
                <h1>Sync vers Google Sheet</h1>
                <div class="alert alert-error">Module OAuth/Sync non disponible. Vérifiez les dépendances (google-auth-oauthlib, google-api-python-client).</div>
                <p><a href="/" class="btn btn-secondary">Retour</a></p>
            </div></body></html>""",
            status_code=500,
        )

    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        return HTMLResponse(
            _sync_app_base_html()
            + """
            <div class="card">
                <h1>Sync vers Google Sheet</h1>
                <div class="alert alert-info">
                    Configurez <code>GOOGLE_OAUTH_CLIENT_ID</code> et <code>GOOGLE_OAUTH_CLIENT_SECRET</code> dans votre fichier .env
                    (OAuth 2.0 Client ID type « Web application » dans Google Cloud Console).
                    Ajoutez l’URL de redirection : <code>""" + str(request.base_url).rstrip("/") + """/auth/google/callback</code>
                </div>
                <p><a href="/" class="btn btn-secondary">Retour</a></p>
            </div></body></html>"""
        )

    connected = is_google_connected(settings)
    export_files = _list_export_files()
    oauth_data = load_oauth_data(settings)
    sheet_id = oauth_data.get("sheet_id", "")
    sheet_name = oauth_data.get("sheet_name", "Tickets")
    auto_update = oauth_data.get("auto_update", False)

    # Messages query params
    synced = request.query_params.get("synced")
    already_updated = request.query_params.get("already_updated")
    last_ids = request.query_params.get("last", "")
    err = request.query_params.get("error")
    incremental_merged = request.query_params.get("incremental_merged")
    incremental_error = request.query_params.get("incremental_error")

    html = _sync_app_base_html("Zendesk / Sync")
    html += '<div class="card"><h1>Sync vers Google Sheet</h1>'
    if already_updated:
        msg = "Déjà à jour avec les derniers tickets intégrés."
        if last_ids:
            ids_list = last_ids.replace("%2C", ",").split(",")[:3]
            msg += " Derniers tickets : " + ", ".join(ids_list) + "."
        html += f'<div class="alert alert-success">{msg}</div>'
    elif synced:
        msg = f"Feuille mise à jour : {synced} ligne(s) envoyées."
        if last_ids:
            ids_list = last_ids.replace("%2C", ",").split(",")[:3]
            msg += " Derniers tickets intégrés : " + ", ".join(ids_list) + "."
        html += f'<div class="alert alert-success">{msg}</div>'
    if err:
        html += f'<div class="alert alert-error">Erreur : {err}</div>'
    if incremental_merged is not None:
        html += f'<div class="alert alert-success">Enrichissement : {incremental_merged} ticket(s) fusionnés dans tickets_all.csv.</div>'
    if incremental_error:
        html += f'<div class="alert alert-error">Enrichissement : {incremental_error}</div>'

    if not connected:
        redirect_uri = str(request.base_url).rstrip("/") + "/auth/google/callback"
        auth_url = get_auth_url(settings, redirect_uri, state="/zendesk/sync")
        html += """
        <div class="alert alert-info">
            Connectez-vous avec votre compte Google pour envoyer les exports Zendesk vers une feuille Google Sheet.
        </div>
        <p><a href=\"""" + auth_url + """\" class="btn btn-primary">Se connecter avec Google</a></p>
        """
    else:
        html += '<div class="alert alert-success">Compte Google connecté.</div>'
        html += '<p><a href="/zendesk/sync/settings" class="btn btn-secondary">Paramètres (feuille, fréquence, mise à jour auto)</a> '
        html += '<form method="post" action="/auth/disconnect" style="display:inline;"><button type="submit" class="btn btn-danger">Déconnexion</button></form></p>'
        html += '<h2>Enrichissement tickets_all.csv</h2>'
        html += '<p class="small">Récupère les tickets Zendesk mis à jour (selon la fréquence dans Paramètres) et les fusionne dans <code>exports/tickets_all.csv</code>. Fichier utilisé pour la sync vers la feuille et Looker Studio.</p>'
        html += '<p><button type="button" id="btn-enrich" class="btn btn-secondary">Enrichir maintenant</button> <span id="enrich-result" class="small" style="margin-left:8px;"></span></p>'
        html += '<h2>Mise à jour manuelle – Google Sheet</h2>'
        if not sheet_id:
            html += '<div class="alert alert-info">Définissez l’ID de la feuille dans <a href="/zendesk/sync/settings">Paramètres</a>.</div>'
        else:
            if export_files:
                latest = export_files[0]
                html += f'<p class="small">Base pour la sync : <strong>{latest["name"]}</strong></p>'
                html += """
                <form method="post" action="/sync-now">
                    <p><button type="submit" class="btn btn-success">Mettre à jour la Google Sheet maintenant</button></p>
                </form>
                <p class="small" style="margin-top:12px;">Télécharger : """
                for f in _list_all_export_files():
                    html += '<a href="/zendesk/exports/download/' + f["name"] + '" download>' + f["name"] + '</a> '
                html += """</p>
                """
            else:
                html += '<div class="alert alert-info">Aucun fichier d’export trouvé dans <code>exports/</code>. Lancez d’abord un import complet depuis la page d’accueil.</div>'

    html += '<p><a href="/" class="btn btn-secondary">Retour à l’accueil</a></p>'
    html += """<script>
    (function(){
        var btn = document.getElementById('btn-enrich');
        if (!btn) return;
        btn.onclick = function() {
            var out = document.getElementById('enrich-result');
            out.textContent = 'En cours...';
            out.style.color = '';
            btn.disabled = true;
            fetch('/zendesk/sync/run-incremental', { method: 'POST', headers: { 'Accept': 'application/json' } })
                .then(function(r) {
                    var ct = r.headers.get('Content-Type') || '';
                    if (!r.ok && ct.indexOf('json') === -1) return r.text().then(function(t) { throw new Error(t.slice(0, 200) || 'Erreur ' + r.status); });
                    return r.json();
                })
                .then(function(d) {
                    if (d.ok) { out.textContent = (d.merged !== undefined ? d.merged + ' ticket(s) fusionnés.' : (d.message || 'OK')); out.style.color = 'green'; }
                    else { out.textContent = 'Erreur : ' + (d.error || d.detail || 'inconnue'); out.style.color = '#c00'; }
                    btn.disabled = false;
                })
                .catch(function(e) { out.textContent = 'Erreur : ' + (e.message || e); out.style.color = '#c00'; btn.disabled = false; });
        };
    })();
    </script></div></body></html>"""
    return HTMLResponse(html)


@app.get("/auth/google")
def auth_google_start(request: Request, next: str = "/"):
    """Redirige vers Google OAuth. next = URL de retour après connexion."""
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(status_code=503, detail="OAuth non configuré")
    redirect_uri = str(request.base_url).rstrip("/") + "/auth/google/callback"
    url = get_auth_url(settings, redirect_uri, state=next or "/")
    return RedirectResponse(url=url)


@app.get("/auth/google/callback")
def auth_google_callback(request: Request, code: str = None, state: str = None):
    """Callback OAuth : échange le code contre les tokens, redirige vers state."""
    if not code:
        return RedirectResponse((state or "/") + "?error=no_code")
    redirect_uri = str(request.base_url).rstrip("/") + "/auth/google/callback"
    try:
        exchange_code_for_tokens(settings, code, redirect_uri)
    except Exception as e:
        logger.exception("OAuth callback error")
        return RedirectResponse((state or "/") + "?error=" + str(e).replace(" ", "%20")[:80])
    return RedirectResponse(state or "/", status_code=302)


@app.post("/auth/disconnect")
def auth_disconnect(request: Request):
    """Déconnexion du compte Google."""
    if SYNC_APP_AVAILABLE:
        disconnect_google(settings)
    referer = request.headers.get("referer", "/")
    return RedirectResponse(referer if referer else "/", status_code=302)


@app.get("/zendesk/sync/settings", response_class=HTMLResponse)
def sync_app_settings_page():
    """Paramètres Sync : feuille cible et mise à jour auto."""
    if not SYNC_APP_AVAILABLE:
        raise HTTPException(status_code=503, detail="Module non disponible")
    oauth_data = load_oauth_data(settings)
    sheet_id = oauth_data.get("sheet_id", "")
    sheet_name = oauth_data.get("sheet_name", "Tickets")
    auto_update = oauth_data.get("auto_update", False)
    sync_frequency = oauth_data.get("sync_frequency", "24h")
    freq_options = [("24h", "Toutes les 24 h"), ("48h", "Toutes les 48 h"), ("weekly", "Hebdo (7 j)"), ("monthly", "Mensuel (30 j)")]
    freq_select = "".join('<option value="%s"%s>%s</option>' % (v, " selected" if v == sync_frequency else "", l) for v, l in freq_options)

    html = _sync_app_base_html("Zendesk / Sync / Paramètres")
    html += """<div class="card">
        <h1>Paramètres – Sync Google Sheet</h1>
        <form id="sync-settings-form" method="post" action="/zendesk/sync/settings">
            <label>ID de la feuille Google</label>
            <input type="text" name="sheet_id" id="sheet_id" value=\"""" + (sheet_id or "") + """\" placeholder="1-0uyOH7xwU8OfFkm2gJKUZt-6pfx_ScTnfDmyW_BuuY">
            <p class="small">Trouvable dans l’URL : docs.google.com/spreadsheets/d/<strong>ID_ICI</strong>/edit</p>
            <label>Nom de l’onglet</label>
            <input type="text" name="sheet_name" id="sheet_name" value=\"""" + (sheet_name or "Tickets") + """\" placeholder="Tickets">
            <p id="verify-result" class="small" style="margin-top:8px;min-height:1.2em;"></p>
            <p style="margin-top:12px;"><button type="button" id="btn-verify" class="btn btn-secondary">Vérifier la feuille et l'onglet</button></p>
            <label style="margin-top:16px;">Enrichissement tickets_all.csv</label>
            <p class="small">Fréquence des mises à jour incrémentales Zendesk (fusion dans tickets_all.csv).</p>
            <select name="sync_frequency" style="padding:8px;min-width:200px;">""" + freq_select + """</select>
            <label style="margin-top:12px;"><input type="checkbox" name="auto_update" """ + ("checked" if auto_update else "") + """> Mise à jour automatique (planifiée)</label>
            <p class="small">Si activé, configurez une tâche cron pour appeler POST /sync-now régulièrement.</p>
            <p style="margin-top:16px;"><button type="submit" class="btn btn-primary">Enregistrer</button></p>
        </form>
        <p><a href="/zendesk/sync" class="btn btn-secondary">Retour au dashboard</a></p>
    </div>
    <script>
    document.getElementById('btn-verify').onclick = function() {
        var out = document.getElementById('verify-result');
        out.textContent = 'Vérification…';
        out.style.color = '';
        var fd = new FormData();
        fd.append('sheet_id', document.getElementById('sheet_id').value);
        fd.append('sheet_name', document.getElementById('sheet_name').value);
        fetch('/zendesk/sync/verify', { method: 'POST', body: fd })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (d.ok) { out.textContent = '✓ ' + (d.message || 'Feuille et onglet trouvés.'); out.style.color = 'green'; }
                else { out.textContent = '✗ ' + (d.error || 'Erreur'); out.style.color = '#c00'; }
            })
            .catch(function(e) { out.textContent = '✗ Erreur: ' + e.message; out.style.color = '#c00'; });
    };
    </script></body></html>"""
    return HTMLResponse(html)


@app.post("/zendesk/sync/verify")
def sync_verify_sheet(
    sheet_id: str = Form(""),
    sheet_name: str = Form("Tickets"),
):
    """Vérifie que la feuille et l'onglet existent et sont accessibles (retourne JSON)."""
    if not SYNC_APP_AVAILABLE:
        raise HTTPException(status_code=503, detail="Module non disponible")
    if not is_google_connected(settings):
        return JSONResponse({"ok": False, "error": "Compte Google non connecté."})
    creds = get_valid_credentials(settings)
    if not creds:
        return JSONResponse({"ok": False, "error": "Credentials invalides ou expirés."})
    result = verify_sheet_access(creds, sheet_id, sheet_name)
    return JSONResponse(result)


@app.post("/zendesk/sync/settings")
def sync_app_settings_save(
    request: Request,
    sheet_id: str = Form(""),
    sheet_name: str = Form("Tickets"),
    sync_frequency: str = Form("24h"),
    auto_update: Optional[str] = Form(None),
):
    """Enregistre les paramètres (feuille, fréquence enrichissement, mise à jour auto)."""
    if not SYNC_APP_AVAILABLE:
        raise HTTPException(status_code=503, detail="Module non disponible")
    if sync_frequency not in ("24h", "48h", "weekly", "monthly"):
        sync_frequency = "24h"
    oauth_data = load_oauth_data(settings)
    oauth_data["sheet_id"] = sheet_id.strip()
    oauth_data["sheet_name"] = (sheet_name or "Tickets").strip()
    oauth_data["sync_frequency"] = sync_frequency
    oauth_data["auto_update"] = auto_update == "on"
    save_oauth_data(settings, oauth_data)
    return RedirectResponse("/zendesk/sync", status_code=302)


@app.get("/sync-now")
def sync_now_get():
    """Si quelqu'un accède en GET (lien, favori), redirection avec message."""
    return RedirectResponse("/zendesk/sync?error=" + quote("Utilisez le bouton « Mettre à jour la Google Sheet maintenant » sur cette page."), status_code=302)


@app.post("/sync-now")
def sync_now():
    """Lance la synchronisation : tickets_all.csv (ou dernier CSV) → Google Sheet. Redirige toujours vers la page Sync (succès ou erreur)."""
    if not SYNC_APP_AVAILABLE:
        return RedirectResponse("/zendesk/sync?error=" + quote("Module sync non disponible"), status_code=302)
    if not is_google_connected(settings):
        return RedirectResponse("/zendesk/sync?error=" + quote("Compte Google non connecté"), status_code=302)
    creds = get_valid_credentials(settings)
    if not creds:
        return RedirectResponse("/zendesk/sync?error=" + quote("Credentials invalides ou expirés"), status_code=302)
    oauth_data = load_oauth_data(settings)
    sheet_id = oauth_data.get("sheet_id")
    sheet_name = oauth_data.get("sheet_name", "Tickets")
    if not sheet_id:
        return RedirectResponse("/zendesk/sync?error=" + quote("ID de feuille manquant. Renseignez les paramètres."), status_code=302)

    export_files = _list_export_files()
    if not export_files:
        return RedirectResponse("/zendesk/sync?error=" + quote("Aucun fichier d'export. Lancez d'abord un import complet."), status_code=302)
    csv_path = export_files[0]["path"]

    try:
        result = sync_csv_to_sheet(creds, sheet_id, sheet_name, csv_path)
    except Exception as e:
        logger.exception("sync-now")
        return RedirectResponse("/zendesk/sync?error=" + quote(str(e)[:200]), status_code=302)

    if result["success"]:
        try:
            oauth_data = load_oauth_data(settings)
            oauth_data["last_sync_at"] = time.time()
            save_oauth_data(settings, oauth_data)
        except Exception as e:
            logger.warning("Impossible d'enregistrer last_sync_at: %s", e)
        if result.get("already_up_to_date"):
            q = "already_updated=1"
            last = result.get("last_ticket_ids") or []
            if last:
                q += "&last=" + quote(",".join(last))
            return RedirectResponse("/zendesk/sync?" + q, status_code=302)
        q = "synced=" + str(result["rows_written"])
        last = result.get("last_ticket_ids") or []
        if last:
            q += "&last=" + quote(",".join(last))
        return RedirectResponse("/zendesk/sync?" + q, status_code=302)
    return RedirectResponse("/zendesk/sync?error=" + quote(result.get("message", "Erreur inconnue")[:200]), status_code=302)


def _sync_frequency_hours(sync_frequency: str) -> int:
    """Retourne le nombre d'heures pour la fréquence (24h, 48h, weekly, monthly)."""
    return {"24h": 24, "48h": 48, "weekly": 24 * 7, "monthly": 24 * 30}.get(sync_frequency, 24)


@app.get("/zendesk/exports/download/{filename}")
def zendesk_export_download(filename: str):
    """Télécharge un fichier du répertoire exports (ex. tickets_all.csv). Pas de path traversal."""
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Nom de fichier invalide")
    base = Path(settings.EXPORT_OUTPUT_DIR).resolve()
    path = (base / filename).resolve()
    if not path.is_file() or not str(path).startswith(str(base)):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    media_type = "text/csv" if path.suffix.lower() == ".csv" else "application/octet-stream"
    return FileResponse(path, filename=path.name, media_type=media_type)


@app.get("/zendesk/sync/run-incremental")
def sync_run_incremental_get():
    """Si accès en GET (lien, favori), redirection avec message."""
    return RedirectResponse("/zendesk/sync?error=" + quote("Utilisez le bouton « Enrichir maintenant » sur cette page."), status_code=302)


def _run_incremental_json(accept: str) -> dict:
    """Logique enrichissement incrémental ; retourne un dict pour JSON (ok, message/error, merged)."""
    zendesk = get_zendesk_client()
    if not zendesk.test_connection():
        return {"ok": False, "error": "Connexion Zendesk échouée", "merged": 0}
    oauth_data = load_oauth_data(settings)
    sync_frequency = oauth_data.get("sync_frequency", "24h")
    hours = _sync_frequency_hours(sync_frequency)
    since = datetime.now() - timedelta(hours=hours)
    export_client_csv = ExportClient(output_dir=settings.EXPORT_OUTPUT_DIR, file_format="csv")
    tickets = list(zendesk.get_tickets_updated_since(since))
    if not tickets:
        return {"ok": True, "message": "Aucun ticket mis à jour", "merged": 0}
    path = export_client_csv.merge_incremental_into_all(tickets)
    return {"ok": True, "message": "tickets_all.csv mis à jour", "merged": len(tickets), "path": path}


@app.post("/zendesk/sync/run-incremental")
def sync_run_incremental(request: Request):
    """
    Enrichit tickets_all.csv. Retourne toujours du JSON si Accept: application/json (évite erreur "is not valid JSON").
    """
    accept = (request.headers.get("Accept") or "").lower()
    if "application/json" in accept and settings.CRON_SECRET:
        secret = request.query_params.get("secret") or request.headers.get("X-Cron-Secret")
        if secret != settings.CRON_SECRET:
            return JSONResponse({"ok": False, "error": "Secret invalide", "merged": 0}, status_code=403)
    if "application/json" in accept:
        try:
            out = _run_incremental_json(accept)
            return JSONResponse(out)
        except Exception as e:
            logger.exception("run-incremental")
            return JSONResponse({"ok": False, "error": str(e)[:500], "merged": 0}, status_code=500)
    try:
        out = _run_incremental_json(accept)
        if out.get("ok"):
            return RedirectResponse("/zendesk/sync?incremental_merged=" + str(out.get("merged", 0)))
        return RedirectResponse("/zendesk/sync?incremental_error=" + quote(out.get("error", "Erreur")[:80]))
    except Exception as e:
        logger.exception("run-incremental")
        return RedirectResponse("/zendesk/sync?incremental_error=" + quote(str(e)[:80]))


# ---------- Module Calculs entre deux Google Sheets ----------

def _sheets_calc_base_html(breadcrumb: str = ""):
    """Base Pyth-apps pour le module Calculs Google Sheets."""
    return pythapps_base_html("Calculs Google Sheets", breadcrumb_fragment(breadcrumb))


@app.get("/sheets-calc", response_class=HTMLResponse)
async def sheets_calc_page(request: Request):
    """Page du module : formulaire pour choisir deux feuilles et une opération."""
    if not SHEETS_CALC_AVAILABLE:
        return HTMLResponse(
            _sheets_calc_base_html()
            + """
            <div class="card">
                <h1>Calculs entre deux Google Sheets</h1>
                <div class="alert alert-error">Module non disponible (dépendances manquantes).</div>
                <p><a href="/" class="btn btn-secondary">Retour à l'accueil</a></p>
            </div></body></html>""",
            status_code=503,
        )
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        return HTMLResponse(
            _sheets_calc_base_html()
            + """
            <div class="card">
                <h1>Calculs entre deux Google Sheets</h1>
                <div class="alert alert-info">Configurez OAuth Google dans .env (GOOGLE_OAUTH_CLIENT_ID / SECRET).</div>
                <p><a href="/" class="btn btn-secondary">Retour</a></p>
            </div></body></html>""",
        )
    connected = is_google_connected(settings)
    err = request.query_params.get("error")
    op_options = "".join(
        f'<option value="{k}">{v[0]}</option>' for k, v in SHEETS_CALC_OPERATIONS.items()
    )
    html = _sheets_calc_base_html("Calculs entre deux Google Sheets")
    html += '<div class="card"><h1>Calculs entre deux Google Sheets</h1>'
    if err:
        html += f'<div class="alert alert-error">Erreur : {err}</div>'
    if not connected:
        redirect_uri = str(request.base_url).rstrip("/") + "/auth/google/callback"
        auth_url = get_auth_url(settings, redirect_uri, state="/sheets-calc")
        html += """
        <div class="alert alert-info">
            Connectez-vous avec Google pour lire vos feuilles et effectuer les calculs.
        </div>
        <p><a href=\"""" + auth_url + """\" class="btn btn-primary">Se connecter avec Google</a></p>
        """
    else:
        html += '<div class="alert alert-success">Compte Google connecté.</div>'
        html += """
        <form method="post" action="/sheets-calc/run">
            <h2>Feuille A</h2>
            <label>ID de la feuille</label>
            <input type="text" name="sheet_a_id" required placeholder="1ABC...">
            <label>Nom de l'onglet</label>
            <input type="text" name="sheet_a_name" value="Feuille 1" placeholder="Feuille 1">
            <h2>Feuille B</h2>
            <label>ID de la feuille</label>
            <input type="text" name="sheet_b_id" required placeholder="1XYZ...">
            <label>Nom de l'onglet</label>
            <input type="text" name="sheet_b_name" value="Feuille 1" placeholder="Feuille 1">
            <h2>Opération</h2>
            <label>Type</label>
            <select name="operation">
            """ + op_options + """
            </select>
            <label>Index de la colonne clé (0 = première colonne)</label>
            <input type="number" name="key_col_index" value="0" min="0" style="width:80px;">
            <p style="margin-top:16px;"><button type="submit" class="btn btn-primary">Lancer le calcul</button></p>
        </form>
        <p><a href="/" class="btn btn-secondary">Retour à l'accueil</a></p>
        """
    html += "</div></body></html>"
    return HTMLResponse(html)


@app.post("/sheets-calc/run", response_class=HTMLResponse)
async def sheets_calc_run(
    request: Request,
    sheet_a_id: str = Form(...),
    sheet_a_name: str = Form("Feuille 1"),
    sheet_b_id: str = Form(...),
    sheet_b_name: str = Form("Feuille 1"),
    operation: str = Form("diff_left"),
    key_col_index: int = Form(0),
):
    """Exécute l'opération entre les deux feuilles et affiche le résultat."""
    if not SHEETS_CALC_AVAILABLE or operation not in SHEETS_CALC_OPERATIONS:
        raise HTTPException(status_code=400, detail="Opération non disponible")
    creds = get_valid_credentials(settings)
    if not creds:
        return RedirectResponse("/sheets-calc?error=credentials")
    try:
        headers_a, rows_a = read_sheet(creds, sheet_a_id.strip(), (sheet_a_name or "Feuille 1").strip())
        headers_b, rows_b = read_sheet(creds, sheet_b_id.strip(), (sheet_b_name or "Feuille 1").strip())
    except Exception as e:
        logger.exception("Erreur lecture sheets")
        return RedirectResponse("/sheets-calc?error=" + str(e).replace(" ", "%20")[:80])
    _, fn = SHEETS_CALC_OPERATIONS[operation]
    key_idx = max(0, key_col_index)
    out_headers, out_rows = fn(headers_a, rows_a, headers_b, rows_b, key_col_index=key_idx)
    # Affichage tableau HTML
    table_rows = "".join(
        "<tr>" + "".join(f"<td>{str(cell)}</td>" for cell in row) + "</tr>"
        for row in out_rows
    )
    thead = "<tr>" + "".join(f"<th>{h}</th>" for h in out_headers) + "</tr>"
    html = _sheets_calc_base_html("Résultat")
    html += '<div class="card"><h1>Résultat</h1>'
    html += f"<p class=\"small\">{SHEETS_CALC_OPERATIONS[operation][0]} — {len(out_rows)} ligne(s).</p>"
    html += "<div style=\"overflow-x:auto;\"><table border=\"1\" cellpadding=\"8\" cellspacing=\"0\" style=\"border-collapse:collapse; width:100%;\"><thead>" + thead + "</thead><tbody>" + table_rows + "</tbody></table></div>"
    html += '<p><a href="/sheets-calc" class="btn btn-secondary">Nouveau calcul</a> <a href="/" class="btn btn-secondary">Accueil</a></p>'
    html += "</div></body></html>"
    return HTMLResponse(html)


@app.get("/status/page", response_class=HTMLResponse)
def status_page():
    """Page Statut (UI) : état des services avec le design Pyth-apps."""
    try:
        data = _get_status_data()
    except Exception as e:
        logger.exception("Status page")
        data = {
            "overall": "error",
            "zendesk": {"connected": False, "export_ready": False, "export_info": str(e)[:100]},
            "google_oauth": {"connected": False},
        }
    return HTMLResponse(status_page_html(data))


@app.get("/status", response_model=StatusResponse)
def get_status():
    """API : statut des connexions Zendesk et export (JSON)."""
    try:
        data = _get_status_data()
        z = data["zendesk"]
        return StatusResponse(
            status=data["overall"],
            zendesk_connected=z["connected"],
            export_mode=settings.EXPORT_MODE,
            export_ready=z["export_ready"],
            export_info=z["export_info"],
        )
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut: {e}")
        return StatusResponse(
            status="error",
            zendesk_connected=False,
            export_mode=settings.EXPORT_MODE,
            export_ready=False,
            export_info=str(e)[:200],
        )


def process_full_import():
    """Fonction d'arrière-plan pour l'import complet (met à jour data/import_progress.json)."""
    try:
        _write_import_progress("running", 0, "Connexion à Zendesk...")
        logger.info(f"Démarrage de l'import complet (mode: {settings.EXPORT_MODE})")
        zendesk = get_zendesk_client()
        export_client = get_export_client()
        _write_import_progress("running", 0, "Récupération des tickets...")

        tickets = []
        count = 0
        seen_ids = set()
        batch_size = 500
        filename = None
        first_batch = True

        try:
            for ticket in zendesk.get_all_tickets():
                tid = ticket.get("ticket_id")
                if tid is not None:
                    try:
                        seen_ids.add(int(tid))
                    except (TypeError, ValueError):
                        seen_ids.add(tid)
                tickets.append(ticket)
                count += 1

                if count % 500 == 0:
                    _write_import_progress("running", count, f"{count} tickets récupérés...")

                # Pour Google Sheets, écrire par batch de 100
                if settings.EXPORT_MODE == "gsheet" and len(tickets) >= 100:
                    export_client.write_tickets(tickets, append=True)
                    tickets = []
                    logger.info(f"Progression: {count} tickets traités")
                # Pour CSV/Excel, exporter par batches
                elif settings.EXPORT_MODE in ["csv", "xlsx"] and len(tickets) >= batch_size:
                    if first_batch:
                        # Premier batch : créer le fichier avec en-têtes
                        filename = export_client.export(tickets)
                        first_batch = False
                        logger.info(f"Fichier créé: {filename}")
                    else:
                        # Batches suivants : ajouter au fichier existant (CSV uniquement)
                        if settings.EXPORT_MODE == "csv":
                            # Pour CSV, on peut ajouter les lignes
                            export_client.export_to_csv(tickets, filename=filename, append=True)
                        else:
                            # Pour Excel, créer un nouveau fichier avec timestamp
                            filename = export_client.export(tickets)
                            logger.info(f"Nouveau fichier créé: {filename}")
                    tickets = []
                    _write_import_progress("running", count, f"{count} tickets – export en cours...")
                    logger.info(f"Progression: {count} tickets traités")
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tickets: {e}")
            import traceback
            logger.error(traceback.format_exc())
            _write_import_progress("running", count, f"Erreur récupération, export de {count} tickets...")

        # Écrire/Exporter les tickets restants
        if tickets:
            if settings.EXPORT_MODE == "gsheet":
                export_client.write_tickets(tickets, append=True)
            elif settings.EXPORT_MODE == "csv":
                if first_batch:
                    export_client.export_to_csv(tickets, filename=filename)
                else:
                    export_client.export_to_csv(tickets, filename=filename, append=True)
                logger.info(f"Fichier final: {filename}")
            else:
                if first_batch:
                    filename = export_client.export(tickets)
                else:
                    filename = export_client.export(tickets)
                logger.info(f"Fichier final: {filename}")

        # Combler les trous : récupérer par ID les tickets manquants dans la plage [1, max_id] (mode CSV uniquement)
        gap_filled = 0
        if settings.EXPORT_MODE == "csv" and seen_ids:
            try:
                max_id = max(int(x) for x in seen_ids)
            except (ValueError, TypeError):
                max_id = 0
            if max_id > 0:
                seen_ints = set()
                for x in seen_ids:
                    try:
                        seen_ints.add(int(x))
                    except (TypeError, ValueError):
                        pass
                missing = [i for i in range(1, max_id + 1) if i not in seen_ints][:2000]
                if missing:
                    _write_import_progress("running", count, f"{count} tickets – récupération de {len(missing)} ticket(s) manquant(s)...")
                    export_client_csv = ExportClient(output_dir=settings.EXPORT_OUTPUT_DIR, file_format="csv")
                    gap_tickets = []
                    for i, tid in enumerate(missing):
                        try:
                            t = zendesk.get_ticket_by_id(tid)
                            if t:
                                gap_tickets.append(t)
                                gap_filled += 1
                            if (i + 1) % 100 == 0:
                                _write_import_progress("running", count + len(gap_tickets), f"Trous : {len(gap_tickets)}/{len(missing)} récupérés...")
                        except Exception as e:
                            logger.warning("get_ticket_by_id %s: %s", tid, e)
                        time.sleep(0.05)
                    if gap_tickets:
                        export_client_csv.merge_incremental_into_all(gap_tickets)
                        logger.info("Gap fill : %s tickets manquants fusionnés dans tickets_all.csv", gap_filled)
                    count += gap_filled

        logger.info(f"Import complet terminé: {count} tickets traités")
        try:
            status_data = zendesk._make_request("/tickets.json", params={"per_page": 1})
            total_count = status_data.get("count", 0)
            if count < total_count:
                msg = f"Import terminé : {count} tickets (attendu {total_count}, {total_count - count} manquants)"
            else:
                msg = f"Import terminé : {count} tickets exportés vers {filename or 'la feuille'}."
            if gap_filled:
                msg += f" ({gap_filled} trou(s) comblés par ID.)"
            _write_import_progress("done", count, msg)
        except Exception as e:
            logger.warning(f"Impossible de vérifier le count total: {e}")
            _write_import_progress("done", count, f"Import terminé : {count} tickets exportés.")

    except Exception as e:
        logger.error(f"Erreur lors de l'import complet: {e}")
        _write_import_progress("error", 0, "", error=str(e)[:500])
        raise


def _import_full_start(background_tasks: BackgroundTasks) -> str:
    """Vérifie les connexions, lance l'import en arrière-plan. Retourne le message de confirmation."""
    zendesk = get_zendesk_client()
    if not zendesk.test_connection():
        raise HTTPException(status_code=503, detail="Connexion Zendesk échouée")
    if settings.EXPORT_MODE == "gsheet":
        gsheet = get_gsheet_client()
        if not gsheet.test_connection():
            raise HTTPException(status_code=503, detail="Connexion Google Sheets échouée")
    else:
        try:
            get_export_client()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Erreur export {settings.EXPORT_MODE}: {e}")
    background_tasks.add_task(process_full_import)
    mode_info = f"vers {settings.EXPORT_MODE.upper()}"
    if settings.EXPORT_MODE in ["csv", "xlsx"]:
        mode_info += f" (répertoire '{settings.EXPORT_OUTPUT_DIR}')"
    return f"Import complet démarré en arrière-plan {mode_info}. Consultez les logs pour la progression."


@app.post("/import/full", response_model=ImportResponse)
async def import_full(request: Request, background_tasks: BackgroundTasks):
    """
    Déclenche un import complet. Redirige vers /zendesk si soumission formulaire, sinon JSON.
    """
    try:
        message = _import_full_start(background_tasks)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de l'import complet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    accept = (request.headers.get("Accept") or "").lower()
    if "application/json" in accept:
        return ImportResponse(success=True, message=message)
    return RedirectResponse("/zendesk/import-progress", status_code=302)


@app.get("/import/status")
def import_status():
    """État de l'import en cours ou dernier import (pour la page de progression)."""
    path = _import_progress_path()
    if not path.exists():
        return JSONResponse({"status": "idle", "count": 0, "message": "", "error": ""})
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(data)
    except Exception:
        return JSONResponse({"status": "idle", "count": 0, "message": "", "error": ""})


@app.get("/zendesk/import-progress", response_class=HTMLResponse)
def zendesk_import_progress():
    """Page qui affiche la progression de l'import en temps réel (polling)."""
    base = pythapps_base_html("Import en cours", breadcrumb_fragment("Zendesk / Import"))
    base += """
    <div class="card">
        <h1>Import complet Zendesk</h1>
        <p id="progress-msg">Chargement...</p>
        <p id="progress-count" class="small" style="margin-top:8px;"></p>
        <p id="progress-done" style="margin-top:16px;display:none;">
            <a href="/zendesk" class="btn btn-primary">Retour au module Zendesk</a>
        </p>
    </div>
    <script>
    var done = false;
    function poll() {
        if (done) return;
        fetch('/import/status')
            .then(function(r) { return r.json(); })
            .then(function(d) {
                document.getElementById('progress-msg').textContent = d.message || d.status || '';
                document.getElementById('progress-count').textContent = d.count ? d.count + ' ticket(s)' : '';
                if (d.status === 'done') {
                    document.getElementById('progress-msg').textContent = d.message || 'Import terminé.';
                    document.getElementById('progress-done').style.display = 'block';
                    done = true;
                } else if (d.status === 'error') {
                    document.getElementById('progress-msg').textContent = 'Erreur : ' + (d.error || '');
                    document.getElementById('progress-done').style.display = 'block';
                    done = true;
                }
            })
            .catch(function() { document.getElementById('progress-msg').textContent = 'Impossible de charger la progression.'; });
    }
    poll();
    setInterval(poll, 2000);
    </script>
    </body></html>"""
    return HTMLResponse(base)


@app.post("/import/incremental", response_model=ImportResponse)
async def import_incremental(hours: int = 24):
    """
    Déclenche un import incrémental des tickets mis à jour récemment.
    
    Args:
        hours: Nombre d'heures en arrière pour récupérer les tickets (défaut: 24)
    
    Returns:
        ImportResponse: Résultat de l'import incrémental
    """
    try:
        zendesk = get_zendesk_client()
        export_client = get_export_client()
        
        if not zendesk.test_connection():
            raise HTTPException(status_code=503, detail="Connexion Zendesk échouée")
        
        # Calculer la date de référence
        since_datetime = datetime.now() - timedelta(hours=hours)
        logger.info(f"Démarrage de l'import incrémental depuis {since_datetime}")
        
        # Collecter les tickets mis à jour
        tickets = []
        count = 0
        
        for ticket in zendesk.get_tickets_updated_since(since_datetime):
            tickets.append(ticket)
            count += 1
        
        if tickets:
            if settings.EXPORT_MODE == "gsheet":
                # Utiliser update_or_append pour éviter les doublons
                export_client.update_or_append_tickets(tickets)
                logger.info(f"Import incrémental terminé: {count} tickets traités")
            else:
                # Pour CSV/Excel, exporter avec un nom basé sur la date
                filename = export_client.export_incremental(tickets)
                logger.info(f"Import incrémental terminé: {count} tickets exportés vers {filename}")
        else:
            logger.info("Aucun ticket mis à jour trouvé")
        
        return ImportResponse(
            success=True,
            message=f"Import incrémental terminé: {count} tickets traités",
            tickets_processed=count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'import incrémental: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Endpoint de santé simple pour les vérifications de base."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )

