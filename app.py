"""
Application FastAPI principale – plateforme de webapps (modules).

- Page d'accueil : choix du module (Zendesk, Calculs Google Sheets, etc.)
- Module Zendesk : export tickets + sync vers Google Sheet
- Module Calculs : opérations entre deux Google Sheets
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel
from pathlib import Path

from config import get_settings
from zendesk_client import ZendeskClient
from gsheet_client import GoogleSheetsClient
from export_client import ExportClient
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
    from sync_export_to_sheet import sync_csv_to_sheet
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


# ---------- Page d'accueil (choix du module) ----------

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


@app.get("/zendesk", response_class=HTMLResponse)
def zendesk_dashboard():
    """Dashboard du module Zendesk : export + lien vers sync."""
    extra = f"""
    <div class="info"><strong>Mode d'export :</strong> {settings.EXPORT_MODE.upper()}</div>
    <p><strong>Export Zendesk</strong></p>
    <form method="POST" action="/import/full" style="display:inline;" onsubmit="return confirm('Import complet ?');">
        <button type="submit" class="button btn-green">Import complet</button>
    </form>
    <form method="POST" action="/import/incremental" style="display:inline;" onsubmit="return confirm('Import incrémental (24h) ?');">
        <button type="submit" class="button btn-blue">Import incrémental</button>
    </form>
    <p style="margin-top:20px;"><a href="/zendesk/sync" class="btn btn-blue">Sync vers Google Sheet</a></p>
    <p style="margin-top:24px;"><a href="/" class="btn btn-secondary">Accueil</a></p>
    """
    return HTMLResponse(_zendesk_page_html(extra))


# ---------- Zendesk : Sync vers Google Sheet ----------

def _list_export_files() -> list:
    """Liste les fichiers CSV dans le dossier exports, du plus récent au plus ancien."""
    export_dir = Path(settings.EXPORT_OUTPUT_DIR)
    if not export_dir.exists():
        return []
    files = list(export_dir.glob("tickets_*.csv"))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"name": p.name, "path": str(p), "modified": p.stat().st_mtime} for p in files]


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
    err = request.query_params.get("error")

    html = _sync_app_base_html("Zendesk / Sync")
    html += '<div class="card"><h1>Sync vers Google Sheet</h1>'
    if synced:
        html += f'<div class="alert alert-success">Feuille mise à jour : {synced} lignes envoyées.</div>'
    if err:
        html += f'<div class="alert alert-error">Erreur : {err}</div>'

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
        html += '<p><a href="/zendesk/sync/settings" class="btn btn-secondary">Paramètres (feuille, mise à jour auto)</a> '
        html += '<form method="post" action="/auth/disconnect" style="display:inline;"><button type="submit" class="btn btn-danger">Déconnexion</button></form></p>'
        html += '<h2>Mise à jour manuelle</h2>'
        if not sheet_id:
            html += '<div class="alert alert-info">Définissez l’ID de la feuille dans <a href="/zendesk/sync/settings">Paramètres</a>.</div>'
        else:
            if export_files:
                latest = export_files[0]
                html += f'<p class="small">Dernier export : <strong>{latest["name"]}</strong></p>'
                html += """
                <form method="post" action="/sync-now">
                    <p><button type="submit" class="btn btn-success">Mettre à jour la Google Sheet maintenant</button></p>
                </form>
                """
            else:
                html += '<div class="alert alert-info">Aucun fichier d’export trouvé dans <code>exports/</code>. Lancez d’abord un import complet depuis la page d’accueil.</div>'

    html += '<p><a href="/" class="btn btn-secondary">Retour à l’accueil</a></p>'
    html += "</div></body></html>"
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

    html = _sync_app_base_html("Zendesk / Sync / Paramètres")
    html += """<div class="card">
        <h1>Paramètres – Sync Google Sheet</h1>
        <form method="post" action="/zendesk/sync/settings">
            <label>ID de la feuille Google</label>
            <input type="text" name="sheet_id" value=\"""" + (sheet_id or "") + """\" placeholder="1-0uyOH7xwU8OfFkm2gJKUZt-6pfx_ScTnfDmyW_BuuY">
            <p class="small">Trouvable dans l’URL : docs.google.com/spreadsheets/d/<strong>ID_ICI</strong>/edit</p>
            <label>Nom de l’onglet</label>
            <input type="text" name="sheet_name" value=\"""" + (sheet_name or "Tickets") + """\" placeholder="Tickets">
            <label style="margin-top:12px;"><input type="checkbox" name="auto_update" """ + ("checked" if auto_update else "") + """> Mise à jour automatique (planifiée)</label>
            <p class="small">Si activé, configurez une tâche cron pour appeler POST /sync-now régulièrement.</p>
            <p style="margin-top:16px;"><button type="submit" class="btn btn-primary">Enregistrer</button></p>
        </form>
        <p><a href="/zendesk/sync" class="btn btn-secondary">Retour au dashboard</a></p>
    </div></body></html>"""
    return HTMLResponse(html)


@app.post("/zendesk/sync/settings")
def sync_app_settings_save(
    request: Request,
    sheet_id: str = Form(""),
    sheet_name: str = Form("Tickets"),
    auto_update: Optional[str] = Form(None),
):
    """Enregistre les paramètres (feuille, mise à jour auto)."""
    if not SYNC_APP_AVAILABLE:
        raise HTTPException(status_code=503, detail="Module non disponible")
    oauth_data = load_oauth_data(settings)
    oauth_data["sheet_id"] = sheet_id.strip()
    oauth_data["sheet_name"] = (sheet_name or "Tickets").strip()
    oauth_data["auto_update"] = auto_update == "on"
    save_oauth_data(settings, oauth_data)
    return RedirectResponse("/zendesk/sync", status_code=302)


@app.post("/sync-now")
def sync_now():
    """Lance la synchronisation : dernier export CSV → Google Sheet."""
    if not SYNC_APP_AVAILABLE:
        raise HTTPException(status_code=503, detail="Module sync non disponible")
    if not is_google_connected(settings):
        return RedirectResponse("/zendesk/sync")
    creds = get_valid_credentials(settings)
    if not creds:
        return RedirectResponse("/zendesk/sync?error=credentials")
    oauth_data = load_oauth_data(settings)
    sheet_id = oauth_data.get("sheet_id")
    sheet_name = oauth_data.get("sheet_name", "Tickets")
    if not sheet_id:
        return RedirectResponse("/zendesk/sync?error=no_sheet_id")

    export_files = _list_export_files()
    if not export_files:
        raise HTTPException(status_code=400, detail="Aucun fichier d'export trouvé. Lancez d'abord un import complet.")
    csv_path = export_files[0]["path"]

    result = sync_csv_to_sheet(creds, sheet_id, sheet_name, csv_path)
    if result["success"]:
        return RedirectResponse("/zendesk/sync?synced=" + str(result["rows_written"]))
    raise HTTPException(status_code=500, detail=result.get("message", "Erreur inconnue"))


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
    """Fonction d'arrière-plan pour l'import complet."""
    try:
        logger.info(f"Démarrage de l'import complet (mode: {settings.EXPORT_MODE})")
        zendesk = get_zendesk_client()
        export_client = get_export_client()
        
        # Collecter les tickets par batches
        tickets = []
        count = 0
        batch_size = 500  # Taille des batches pour CSV/Excel
        filename = None
        first_batch = True
        
        try:
            for ticket in zendesk.get_all_tickets():
                tickets.append(ticket)
                count += 1
                
                # Pour Google Sheets, écrire par batch de 100
                if settings.EXPORT_MODE == "gsheet" and len(tickets) >= 100:
                    export_client.write_tickets(tickets, append=True)
                    tickets = []
                    logger.info(f"Progression: {count} tickets traités")
                # Pour CSV/Excel, exporter par batches pour éviter les problèmes de mémoire
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
                    logger.info(f"Progression: {count} tickets traités")
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tickets: {e}")
            logger.error(f"Tickets récupérés jusqu'à présent: {count}")
            import traceback
            logger.error(traceback.format_exc())
            # Continuer pour exporter ce qui a été récupéré
            pass
        
        # Écrire/Exporter les tickets restants
        if tickets:
            if settings.EXPORT_MODE == "gsheet":
                export_client.write_tickets(tickets, append=True)
            else:
                if first_batch:
                    # Premier et seul batch
                    filename = export_client.export(tickets)
                    logger.info(f"Fichier créé: {filename}")
                else:
                    # Dernier batch : ajouter au fichier existant
                    if settings.EXPORT_MODE == "csv":
                        export_client.export_to_csv(tickets, filename=filename, append=True)
                    else:
                        filename = export_client.export(tickets)
                        logger.info(f"Nouveau fichier créé: {filename}")
        
        logger.info(f"Import complet terminé: {count} tickets traités")
        if filename:
            logger.info(f"Fichier final: {filename}")
        
        # Vérifier le count total depuis Zendesk pour comparaison
        try:
            status_data = zendesk._make_request("/tickets.json", params={"per_page": 1})
            total_count = status_data.get("count", 0)
            if count < total_count:
                logger.warning(f"⚠️  ATTENTION: {total_count - count} tickets manquants !")
                logger.warning(f"   Tickets récupérés: {count}")
                logger.warning(f"   Tickets attendus selon Zendesk: {total_count}")
            else:
                logger.info(f"✅ Tous les tickets ont été récupérés ({count}/{total_count})")
        except Exception as e:
            logger.warning(f"Impossible de vérifier le count total: {e}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'import complet: {e}")
        raise


@app.post("/import/full", response_model=ImportResponse)
async def import_full(background_tasks: BackgroundTasks):
    """
    Déclenche un import complet de tous les tickets Zendesk.
    
    Cette opération peut prendre du temps et est exécutée en arrière-plan.
    
    Returns:
        ImportResponse: Confirmation du démarrage de l'import
    """
    try:
        # Vérifier les connexions avant de démarrer
        zendesk = get_zendesk_client()
        
        if not zendesk.test_connection():
            raise HTTPException(status_code=503, detail="Connexion Zendesk échouée")
        
        # Vérifier le système d'export
        if settings.EXPORT_MODE == "gsheet":
            gsheet = get_gsheet_client()
            if not gsheet.test_connection():
                raise HTTPException(status_code=503, detail="Connexion Google Sheets échouée")
        else:
            # Pour CSV/Excel, vérifier que le répertoire est accessible
            try:
                get_export_client()
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"Erreur export {settings.EXPORT_MODE}: {e}")
        
        # Démarrer l'import en arrière-plan
        background_tasks.add_task(process_full_import)
        
        mode_info = f"vers {settings.EXPORT_MODE.upper()}"
        if settings.EXPORT_MODE in ["csv", "xlsx"]:
            mode_info += f" (dans le répertoire '{settings.EXPORT_OUTPUT_DIR}')"
        
        return ImportResponse(
            success=True,
            message=f"Import complet démarré en arrière-plan {mode_info}. Consultez les logs pour suivre la progression."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de l'import complet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

