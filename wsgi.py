"""
Point d'entrée WSGI pour hébergement sur PythonAnywhere (ou tout serveur WSGI).

- GET / et GET /favicon.ico sont servis ici sans charger FastAPI (évite blocage / HARAKIRI).
- Toutes les autres requêtes passent par a2wsgi + FastAPI (chargement paresseux).
"""

# Référence à l'app FastAPI (chargée au premier hit sur une autre URL)
_fastapi_app = None


def _serve_home(environ, start_response):
    """Sert la page d'accueil sans importer app (évite config, Zendesk, OAuth)."""
    from home_render import get_home_html
    body = get_home_html().encode("utf-8")
    start_response("200 OK", [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


def _serve_favicon(environ, start_response):
    """Répond 204 No Content pour /favicon.ico sans charger app."""
    start_response("204 No Content", [])
    return []


def _get_fastapi_app():
    """Charge l'app FastAPI une seule fois (lazy)."""
    global _fastapi_app
    if _fastapi_app is None:
        try:
            from a2wsgi import ASGIMiddleware
            from app import app
            _fastapi_app = ASGIMiddleware(app)
        except ImportError:
            from app import app
            _fastapi_app = app
    return _fastapi_app


def application(environ, start_response):
    path = (environ.get("PATH_INFO") or "/").rstrip("/") or "/"
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if method == "GET":
        if path == "/":
            return _serve_home(environ, start_response)
        if path == "/favicon.ico":
            return _serve_favicon(environ, start_response)

    return _get_fastapi_app()(environ, start_response)
