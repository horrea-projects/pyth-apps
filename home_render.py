"""
Rendu de la page d'accueil sans charger app (config, Zendesk, OAuth).
Utilisé par wsgi.py pour GET / afin d'éviter tout blocage au premier hit.
"""
from constants import MODULES
from templates import home_page_html


def get_home_html() -> str:
    """Retourne le HTML de la page d'accueil (sans statut)."""
    return home_page_html(MODULES, None)
