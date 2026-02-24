"""
Synchronise un fichier CSV d'export vers une Google Sheet.

Utilise les credentials OAuth (compte utilisateur) pour écrire dans la feuille.
"""

import csv
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000  # Limite API Sheets par requête


def read_csv_rows(csv_path: str) -> tuple[List[str], List[List]]:
    """
    Lit un fichier CSV et retourne (en-têtes, lignes).
    """
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        rows = list(reader)
    return headers, rows


def sync_csv_to_sheet(credentials, sheet_id: str, sheet_name: str, csv_path: str) -> dict:  # noqa: ANN001
    """
    Envoie le contenu du CSV vers la Google Sheet.

    - Crée l'onglet s'il n'existe pas
    - Efface le contenu puis écrit en-têtes + données par batches

    Returns:
        dict avec "success", "message", "rows_written"
    """
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    csv_path = Path(csv_path)
    if not csv_path.exists():
        return {"success": False, "message": f"Fichier introuvable: {csv_path}", "rows_written": 0}

    headers, rows = read_csv_rows(str(csv_path))
    if not headers:
        return {"success": False, "message": "CSV vide ou sans en-têtes", "rows_written": 0}

    try:
        service = build("sheets", "v4", credentials=credentials)
        spreadsheet = service.spreadsheets()

        num_cols = len(headers)
        total_rows = 1 + len(rows)
        # Au moins 1 ligne et colonnes A–Z pour éviter les erreurs API
        required_rows = max(1, total_rows)
        required_cols = max(26, num_cols)

        # Récupérer les onglets et redimensionner la grille si besoin
        meta = spreadsheet.get(spreadsheetId=sheet_id).execute()
        sheets_list = meta.get("sheets", [])
        sheet_titles = [s["properties"]["title"] for s in sheets_list]

        if sheet_name not in sheet_titles:
            spreadsheet.batchUpdate(
                spreadsheetId=sheet_id,
                body={
                    "requests": [
                        {
                            "addSheet": {
                                "properties": {
                                    "title": sheet_name,
                                    "gridProperties": {
                                        "rowCount": required_rows,
                                        "columnCount": required_cols,
                                    },
                                },
                            }
                        }
                    ]
                },
            ).execute()
            logger.info(f"Onglet '{sheet_name}' créé ({required_rows} lignes, {required_cols} colonnes)")
        else:
            # Onglet existant : redimensionner si la grille est trop petite
            sheet_props = next(
                (s["properties"] for s in sheets_list if s["properties"]["title"] == sheet_name),
                None,
            )
            if sheet_props:
                grid = sheet_props.get("gridProperties", {})
                current_rows = grid.get("rowCount", 1000)
                current_cols = grid.get("columnCount", 26)
                if current_rows < required_rows or current_cols < required_cols:
                    new_rows = max(current_rows, required_rows)
                    new_cols = max(current_cols, required_cols)
                    spreadsheet.batchUpdate(
                        spreadsheetId=sheet_id,
                        body={
                            "requests": [
                                {
                                    "updateSheetProperties": {
                                        "properties": {
                                            "sheetId": sheet_props["sheetId"],
                                            "gridProperties": {
                                                "rowCount": new_rows,
                                                "columnCount": new_cols,
                                            },
                                        },
                                        "fields": "gridProperties(rowCount,columnCount)",
                                    }
                                }
                            ]
                        },
                    ).execute()
                    logger.info(f"Grille redimensionnée : {new_rows} lignes, {new_cols} colonnes")

        end_col = _col_letter(num_cols)
        range_name = f"'{sheet_name}'!A1:{end_col}{total_rows}"
        data = [headers] + rows

        if len(data) <= 5000:
            spreadsheet.values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": data},
            ).execute()
        else:
            spreadsheet.values().update(
                spreadsheetId=sheet_id,
                range=f"'{sheet_name}'!A1:{end_col}1",
                valueInputOption="RAW",
                body={"values": [headers]},
            ).execute()
            for i in range(0, len(rows), BATCH_SIZE):
                chunk = rows[i : i + BATCH_SIZE]
                start_row = 2 + i
                end_row = start_row + len(chunk) - 1
                r = f"'{sheet_name}'!A{start_row}:{end_col}{end_row}"
                spreadsheet.values().update(
                    spreadsheetId=sheet_id,
                    range=r,
                    valueInputOption="RAW",
                    body={"values": chunk},
                ).execute()

        return {
            "success": True,
            "message": f"{len(rows)} lignes écrites dans '{sheet_name}'",
            "rows_written": len(rows),
        }
    except HttpError as e:
        logger.exception("Erreur API Google Sheets")
        return {
            "success": False,
            "message": str(e.content.decode() if hasattr(e, "content") else str(e)),
            "rows_written": 0,
        }


def _col_letter(n: int) -> str:
    """1 -> A, 27 -> AA, etc."""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s or "A"


def verify_sheet_access(credentials, sheet_id: str, sheet_name: str) -> dict:
    """
    Vérifie que la feuille existe, qu'on y a accès et que l'onglet existe.

    Returns:
        {"ok": True, "message": "..."} ou {"ok": False, "error": "..."}
    """
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    sheet_id = (sheet_id or "").strip()
    sheet_name = (sheet_name or "Tickets").strip()
    if not sheet_id:
        return {"ok": False, "error": "ID de la feuille manquant."}
    if not sheet_name:
        return {"ok": False, "error": "Nom de l'onglet manquant."}

    try:
        service = build("sheets", "v4", credentials=credentials)
        meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    except HttpError as e:
        content = e.content.decode() if hasattr(e, "content") and e.content else str(e)
        if e.resp and e.resp.status == 404:
            return {"ok": False, "error": "Feuille introuvable. Vérifiez l'ID et que le lien de partage inclut ce compte."}
        if e.resp and e.resp.status == 403:
            return {"ok": False, "error": "Accès refusé. Vérifiez que la feuille est partagée avec ce compte Google."}
        return {"ok": False, "error": content[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:500]}

    sheets_list = meta.get("sheets", [])
    titles = [s["properties"]["title"] for s in sheets_list]
    if sheet_name not in titles:
        return {
            "ok": False,
            "error": f"L'onglet « {sheet_name} » n'existe pas. Onglets trouvés : {', '.join(titles[:10])}{'…' if len(titles) > 10 else ''}.",
        }

    return {"ok": True, "message": f"Feuille et onglet « {sheet_name} » trouvés."}
