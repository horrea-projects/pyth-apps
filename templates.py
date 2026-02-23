"""
Fragments HTML partagés – design Pyth-apps.
Cohérence visuelle : typo, cartes, couleurs, nav.
"""
import html as html_module

# Design system Pyth-apps
PYTHAPPS_STYLES = """
    * { box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
        max-width: 900px;
        margin: 0 auto;
        padding: 24px 20px 48px;
        background: #fafafa;
        color: #1a1a1a;
        line-height: 1.5;
        font-size: 15px;
    }
    .pythapps-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 32px;
        padding-bottom: 20px;
        border-bottom: 1px solid #e8e8e8;
    }
    .pythapps-logo {
        font-weight: 700;
        font-size: 1.5rem;
        letter-spacing: -0.02em;
        color: #1a1a1a;
        text-decoration: none;
    }
    .pythapps-logo:hover { color: #0d47a1; }
    .pythapps-nav {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        color: #666;
    }
    .pythapps-nav a {
        color: #0d47a1;
        text-decoration: none;
        font-weight: 500;
    }
    .pythapps-nav a:hover { text-decoration: underline; }
    .pythapps-nav .sep { color: #ccc; user-select: none; }
    .pythapps-nav .current { color: #333; font-weight: 500; }
    .card, .container {
        background: #fff;
        padding: 28px 32px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        border: 1px solid #eee;
        margin-bottom: 24px;
    }
    .card h1, .container h1 {
        color: #1a1a1a;
        font-weight: 600;
        font-size: 1.5rem;
        margin: 0 0 8px 0;
        padding-bottom: 12px;
        border-bottom: 2px solid #0d47a1;
    }
    .card h2, .container h2 {
        color: #333;
        font-size: 1.1rem;
        font-weight: 600;
        margin: 20px 0 10px 0;
    }
    .card h2:first-of-type, .container h2:first-of-type { margin-top: 0; }
    .btn {
        display: inline-block;
        padding: 10px 20px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 500;
        border: none;
        cursor: pointer;
        font-size: 14px;
        transition: background 0.2s, box-shadow 0.2s;
    }
    .btn-primary { background: #0d47a1; color: white; }
    .btn-primary:hover { background: #0a3d8f; box-shadow: 0 2px 8px rgba(13,71,161,0.3); }
    .btn-success { background: #2e7d32; color: white; }
    .btn-success:hover { background: #1b5e20; }
    .btn-secondary { background: #546e7a; color: white; }
    .btn-secondary:hover { background: #455a64; }
    .btn-danger { background: #c62828; color: white; }
    .btn-danger:hover { background: #b71c1c; }
    .btn-blue { background: #1565c0; color: white; }
    .btn-blue:hover { background: #0d47a1; }
    .btn-green { background: #2e7d32; color: white; }
    .button { display: inline-block; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: 500; border: none; cursor: pointer; font-size: 14px; margin: 4px; }
    label { display: block; margin: 10px 0 6px; font-weight: 500; color: #333; }
    input[type="text"], input[type="number"], select {
        width: 100%;
        max-width: 480px;
        padding: 10px 14px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        font-size: 14px;
        transition: border-color 0.2s;
    }
    input:focus, select:focus { outline: none; border-color: #0d47a1; }
    .alert {
        padding: 14px 18px;
        border-radius: 8px;
        margin: 16px 0;
        font-size: 14px;
    }
    .alert-success { background: #e8f5e9; border-left: 4px solid #2e7d32; color: #1b5e20; }
    .alert-error { background: #ffebee; border-left: 4px solid #c62828; color: #b71c1c; }
    .alert-info { background: #e3f2fd; border-left: 4px solid #1565c0; color: #0d47a1; }
    .small { font-size: 13px; color: #666; margin: 6px 0; }
    .info { padding: 14px 18px; background: #e3f2fd; border-left: 4px solid #1565c0; border-radius: 8px; margin: 16px 0; }
    ul { margin: 8px 0; padding-left: 22px; }
    .module-card {
        background: #fff;
        padding: 28px 32px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        border: 1px solid #eee;
        transition: box-shadow 0.2s, border-color 0.2s;
        display: block;
        text-decoration: none;
        color: inherit;
    }
    .module-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        border-color: #0d47a1;
    }
    .module-card h2 { color: #0d47a1; font-size: 1.25rem; font-weight: 600; margin: 0 0 8px 0; }
    .module-card p { margin: 0; color: #666; font-size: 14px; line-height: 1.5; }
    .footer-links { margin-top: 32px; font-size: 13px; color: #999; }
    .footer-links a { color: #1565c0; text-decoration: none; }
    .footer-links a:hover { text-decoration: underline; }
    .status-in-card {
        margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee;
        font-size: 13px; color: #666; display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center;
    }
    .status-in-card .status-item { display: flex; align-items: center; gap: 6px; }
    .status-in-card .status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
    .status-in-card .status-ok .status-dot { background: #2e7d32; }
    .status-in-card .status-err .status-dot { background: #c62828; }
    .status-in-card .status-err { color: #b71c1c; }
    .status-page .status-block { margin-bottom: 20px; }
    .status-page .status-block h3 { font-size: 1rem; margin: 0 0 8px 0; color: #333; }
    .status-page .status-row { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #eee; font-size: 14px; }
    .status-page .status-row:last-child { border-bottom: none; }
    .status-page .status-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
    .status-page .status-dot.ok { background: #2e7d32; }
    .status-page .status-dot.err { background: #c62828; }
    .status-page .status-label { font-weight: 500; min-width: 140px; }
    table { border-collapse: collapse; width: 100%; font-size: 14px; }
    th, td { border: 1px solid #e0e0e0; padding: 10px 12px; text-align: left; }
    th { background: #f5f5f5; font-weight: 600; color: #333; }
"""


def breadcrumb_fragment(breadcrumb: str) -> str:
    """Fragment HTML pour le fil d'Ariane dans le header (après Accueil)."""
    if not breadcrumb:
        return ""
    return f'<span class="sep">/</span><span class="current">{breadcrumb}</span>'


def nav_html(current_module: str = "", module_title: str = "") -> str:
    """Barre de navigation (pour usage inside card si besoin)."""
    bread = breadcrumb_fragment(module_title)
    return f'<nav class="pythapps-nav" style="margin-bottom:16px;"><a href="/">Accueil</a>{bread}</nav>'


def pythapps_base_html(title: str, nav_fragment: str = "") -> str:
    """Base HTML partagée (head + styles + body ouverture + nav)."""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} – Pyth-apps</title>
    <style>{PYTHAPPS_STYLES}</style>
</head>
<body>
    <header class="pythapps-header">
        <a href="/" class="pythapps-logo">Pyth-apps</a>
        <span class="pythapps-nav">
            <a href="/">Accueil</a>
            {nav_fragment}
        </span>
    </header>
"""


def _card_status_html(status_key: str, status_data: dict) -> str:
    """Fragment HTML du statut à afficher dans une carte module."""
    if not status_data:
        return ""
    if status_key == "zendesk":
        z = status_data.get("zendesk", {})
        z_ok = z.get("connected", False)
        exp_ok = z.get("export_ready", False)
        exp_info = z.get("export_info", "")
        lines = [
            ('Zendesk API', z_ok),
            ('Export', exp_ok),
        ]
        if exp_info and not exp_ok:
            safe_info = html_module.escape(exp_info)
            return f'<div class="status-in-card"><div class="status-item {"status-ok" if z_ok else "status-err"}"><span class="status-dot"></span>Zendesk API</div><div class="status-item {"status-ok" if exp_ok else "status-err"}"><span class="status-dot"></span>Export</div><span class="small" style="width:100%;margin-top:4px;">{safe_info}</span></div>'
        return '<div class="status-in-card">' + "".join(
            f'<div class="status-item {"status-ok" if ok else "status-err"}"><span class="status-dot"></span>{label}</div>' for label, ok in lines
        ) + "</div>"
    if status_key == "sheets_calc":
        go = status_data.get("google_oauth", {})
        ok = go.get("connected", False)
        return f'<div class="status-in-card"><div class="status-item {"status-ok" if ok else "status-err"}"><span class="status-dot"></span>Google {"Connecté" if ok else "Non connecté"}</div></div>'
    return ""


def home_page_html(modules: list, status_data: dict = None) -> str:
    """
    Page d'accueil : grille de modules avec optionnel statut dans chaque carte.
    modules: list of {"url", "title", "description", "status_key" (optionnel)}
    status_data: dict avec zendesk, google_oauth pour afficher le statut dans les cartes.
    """
    cards = ""
    for m in modules:
        status_key = m.get("status_key")
        status_html = _card_status_html(status_key, status_data) if status_key else ""
        cards += f"""
        <a href="{m['url']}" class="module-card">
            <h2>{m['title']}</h2>
            <p>{m['description']}</p>
            {status_html}
        </a>
        """
    return pythapps_base_html("Outils", "") + f"""
    <h1 style="font-size:1.75rem;margin-bottom:8px;">Outils & connecteurs</h1>
    <p class="subtitle" style="color:#666;margin-bottom:32px;">Connecter les données et les plateformes.</p>
    <div class="modules" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:24px;">
        {cards}
    </div>
    <p class="footer-links"><a href="/docs">Documentation API</a> &nbsp;·&nbsp; <a href="/status/page">Statut</a></p>
</body>
</html>
"""


def status_page_html(status_data: dict) -> str:
    """
    Page Statut détaillée (design Horrea).
    status_data: { overall, zendesk: { connected, export_ready, export_info }, google_oauth: { connected } }
    """
    overall = status_data.get("overall", "unknown")
    overall_label = {"healthy": "Tout est opérationnel", "degraded": "Dégradé", "error": "Erreur"}.get(overall, overall)
    overall_class = "ok" if overall == "healthy" else "err"
    z = status_data.get("zendesk", {})
    go = status_data.get("google_oauth", {})
    blocks = f"""
    <div class="status-page">
        <div class="status-block">
            <h3>État global</h3>
            <div class="status-row">
                <span class="status-dot {overall_class}"></span>
                <span class="status-label">Plateforme</span>
                <span>{overall_label}</span>
            </div>
        </div>
        <div class="status-block">
            <h3>Zendesk</h3>
            <div class="status-row">
                <span class="status-dot {"ok" if z.get("connected") else "err"}"></span>
                <span class="status-label">API Zendesk</span>
                <span>{"Connecté" if z.get("connected") else "Non connecté"}</span>
            </div>
            <div class="status-row">
                <span class="status-dot {"ok" if z.get("export_ready") else "err"}"></span>
                <span class="status-label">Export</span>
                <span>{z.get("export_info", "-")}</span>
            </div>
        </div>
        <div class="status-block">
            <h3>Google (Sync & Calculs)</h3>
            <div class="status-row">
                <span class="status-dot {"ok" if go.get("connected") else "err"}"></span>
                <span class="status-label">OAuth utilisateur</span>
                <span>{"Connecté" if go.get("connected") else "Non connecté"}</span>
            </div>
        </div>
    </div>
    """
    return pythapps_base_html("Statut", breadcrumb_fragment("Statut")) + f"""
    <div class="card">
        <h1>Statut des services</h1>
        {blocks}
        <p style="margin-top:24px;"><a href="/" class="btn btn-secondary">Accueil</a></p>
    </div>
</body>
</html>
"""


def page_card_html(nav_breadcrumb: str, card_title: str, inner_html: str) -> str:
    """Une page type : base Pyth-apps + une card avec nav, titre, contenu."""
    nav_frag = f'<span class="sep">/</span><span class="current">{nav_breadcrumb}</span>' if nav_breadcrumb else ""
    return pythapps_base_html(card_title, nav_frag) + f"""
    <div class="card">
        <h1>{card_title}</h1>
        {inner_html}
    </div>
</body>
</html>
"""
