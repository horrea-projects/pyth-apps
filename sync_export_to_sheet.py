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

        # Récupérer les onglets
        meta = spreadsheet.get(spreadsheetId=sheet_id).execute()
        sheet_titles = [s["properties"]["title"] for s in meta.get("sheets", [])]

        if sheet_name not in sheet_titles:
            spreadsheet.batchUpdate(
                spreadsheetId=sheet_id,
                body={
                    "requests": [
                        {
                            "addSheet": {
                                "properties": {"title": sheet_name},
                            }
                        }
                    ]
                },
            ).execute()
            logger.info(f"Onglet '{sheet_name}' créé")

        # Plage pour tout écrire (A1 jusqu'à la dernière colonne)
        num_cols = len(headers)
        end_col = _col_letter(num_cols)
        total_rows = 1 + len(rows)
        range_name = f"'{sheet_name}'!A1:{end_col}{total_rows}"

        # Construire la grille : [headers] + rows
        data = [headers] + rows

        # Écrire par batches si trop gros
        if len(data) <= 5000:
            spreadsheet.values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": data},
            ).execute()
        else:
            # Clear d'abord
            spreadsheet.values().clear(
                spreadsheetId=sheet_id,
                range=f"'{sheet_name}'!A1:Z",
            ).execute()
            # Puis append par batches
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
