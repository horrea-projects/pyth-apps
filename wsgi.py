"""
Point d'entrée WSGI pour hébergement sur PythonAnywhere (ou tout serveur WSGI).

Permet d'exposer l'application FastAPI (ASGI) comme application WSGI.
"""

try:
    from a2wsgi import ASGIMiddleware
except ImportError:
    ASGIMiddleware = None

from app import app

if ASGIMiddleware is not None:
    application = ASGIMiddleware(app)
else:
    # Fallback : exposer l'app directement (fonctionne si le serveur gère ASGI)
    application = app
