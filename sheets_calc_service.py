"""
Service de calculs entre deux Google Sheets.

Permet de comparer, fusionner ou calculer des différences entre deux feuilles
en utilisant les credentials OAuth utilisateur.
"""

import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


def read_sheet(credentials, spreadsheet_id: str, sheet_name: str) -> Tuple[List[str], List[List]]:
    """
    Lit une feuille Google et retourne (en-têtes, lignes).
    """
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()
    range_name = f"'{sheet_name}'"
    try:
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
        ).execute()
        values = result.get("values", [])
    except HttpError as e:
        logger.exception("Erreur lecture sheet")
        raise

    if not values:
        return [], []
    headers = values[0]
    rows = values[1:]
    return headers, rows


def _row_key(row: list, key_col_index: int) -> str:
    """Clé unique pour une ligne (colonne d'index key_col_index)."""
    if key_col_index < 0 or key_col_index >= len(row):
        return ""
    return str(row[key_col_index]).strip()


def diff_left(
    headers_a: List[str], rows_a: List[List],
    headers_b: List[str], rows_b: List[List],
    key_col_index: int = 0,
) -> Tuple[List[str], List[List]]:
    """
    Lignes dans A qui ne sont pas dans B (clé = première colonne par défaut).
    Retourne (headers, rows).
    """
    keys_b = {_row_key(r, key_col_index) for r in rows_b}
    out_rows = [r for r in rows_a if _row_key(r, key_col_index) not in keys_b]
    return headers_a, out_rows


def diff_right(
    headers_a: List[str], rows_a: List[List],
    headers_b: List[str], rows_b: List[List],
    key_col_index: int = 0,
) -> Tuple[List[str], List[List]]:
    """Lignes dans B qui ne sont pas dans A."""
    keys_a = {_row_key(r, key_col_index) for r in rows_a}
    out_rows = [r for r in rows_b if _row_key(r, key_col_index) not in keys_a]
    return headers_b, out_rows


def common(
    headers_a: List[str], rows_a: List[List],
    headers_b: List[str], rows_b: List[List],
    key_col_index: int = 0,
) -> Tuple[List[str], List[List]]:
    """Lignes dont la clé est dans A et dans B (côté A)."""
    keys_b = {_row_key(r, key_col_index) for r in rows_b}
    out_rows = [r for r in rows_a if _row_key(r, key_col_index) in keys_b]
    return headers_a, out_rows


OPERATIONS = {
    "diff_left": ("Lignes dans Feuille A pas dans B", diff_left),
    "diff_right": ("Lignes dans Feuille B pas dans A", diff_right),
    "common": ("Lignes communes (clé dans A et B)", common),
}
