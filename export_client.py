"""
Client d'export pour écrire les données des tickets Zendesk en CSV ou Excel.

Ce module gère l'export des données normalisées vers des fichiers locaux.
"""

import csv
import os
from typing import List, Dict, Optional
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# En-têtes par défaut pour les fichiers
DEFAULT_HEADERS = [
    "ticket_id",
    "subject",
    "status",
    "priority",
    "requester_id",
    "assignee_id",
    "created_at",
    "updated_at",
    "tags",
    "type",
    "via",
    "url",
    "description",
    "custom_fields"
]


class ExportClient:
    """Client pour exporter les tickets vers CSV ou Excel."""
    
    def __init__(self, output_dir: str = "exports", file_format: str = "csv"):
        """
        Initialise le client d'export.
        
        Args:
            output_dir: Répertoire où sauvegarder les fichiers
            file_format: Format de fichier ('csv' ou 'xlsx')
        """
        self.output_dir = Path(output_dir)
        self.file_format = file_format.lower()
        
        # Créer le répertoire s'il n'existe pas
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if self.file_format not in ['csv', 'xlsx']:
            raise ValueError(f"Format non supporté: {file_format}. Utilisez 'csv' ou 'xlsx'")
    
    def _get_filename(self, prefix: str = "tickets") -> str:
        """
        Génère un nom de fichier avec timestamp.
        
        Args:
            prefix: Préfixe du nom de fichier
            
        Returns:
            str: Nom de fichier complet avec chemin
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = "csv" if self.file_format == "csv" else "xlsx"
        filename = f"{prefix}_{timestamp}.{extension}"
        return str(self.output_dir / filename)
    
    def _ticket_to_row(self, ticket: Dict) -> List:
        """
        Convertit un ticket en liste de valeurs pour une ligne.
        
        Args:
            ticket: Ticket normalisé
            
        Returns:
            List: Liste de valeurs dans l'ordre des en-têtes
        """
        return [
            ticket.get("ticket_id", ""),
            ticket.get("subject", ""),
            ticket.get("status", ""),
            ticket.get("priority", ""),
            ticket.get("requester_id", ""),
            ticket.get("assignee_id", ""),
            ticket.get("created_at", ""),
            ticket.get("updated_at", ""),
            ticket.get("tags", ""),
            ticket.get("type", ""),
            ticket.get("via", ""),
            ticket.get("url", ""),
            ticket.get("description", ""),
            ticket.get("custom_fields", "")
        ]
    
    def export_to_csv(self, tickets: List[Dict], filename: Optional[str] = None, append: bool = False) -> str:
        """
        Exporte les tickets vers un fichier CSV.
        
        Args:
            tickets: Liste de tickets normalisés
            filename: Nom de fichier personnalisé (optionnel)
            append: Si True, ajoute les données au fichier existant (sans en-têtes)
            
        Returns:
            str: Chemin du fichier créé
        """
        if not filename:
            filename = self._get_filename()
        
        try:
            mode = 'a' if append else 'w'
            with open(filename, mode, newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                
                # Écrire les en-têtes seulement si c'est un nouveau fichier
                if not append:
                    writer.writerow(DEFAULT_HEADERS)
                
                # Écrire les données
                for ticket in tickets:
                    writer.writerow(self._ticket_to_row(ticket))
            
            action = "ajoutés à" if append else "exportés vers"
            logger.info(f"✅ {len(tickets)} tickets {action} {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export CSV: {e}")
            raise
    
    def export_to_excel(self, tickets: List[Dict], filename: Optional[str] = None) -> str:
        """
        Exporte les tickets vers un fichier Excel.
        
        Args:
            tickets: Liste de tickets normalisés
            filename: Nom de fichier personnalisé (optionnel)
            
        Returns:
            str: Chemin du fichier créé
        """
        try:
            import openpyxl
        except ImportError:
            raise ImportError(
                "openpyxl n'est pas installé. Installez-le avec: pip install openpyxl"
            )
        
        if not filename:
            filename = self._get_filename()
        
        try:
            # Créer un nouveau workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Tickets"
            
            # Écrire les en-têtes
            ws.append(DEFAULT_HEADERS)
            
            # Style les en-têtes (gras, fond gris)
            from openpyxl.styles import Font, PatternFill
            header_font = Font(bold=True)
            header_fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
            
            # Écrire les données
            for ticket in tickets:
                ws.append(self._ticket_to_row(ticket))
            
            # Ajuster la largeur des colonnes
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Max 50 caractères
                ws.column_dimensions[column_letter].width = adjusted_width
            
            # Sauvegarder le fichier
            wb.save(filename)
            
            logger.info(f"✅ {len(tickets)} tickets exportés vers {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export Excel: {e}")
            raise
    
    def export(self, tickets: List[Dict], filename: Optional[str] = None) -> str:
        """
        Exporte les tickets selon le format configuré.
        
        Args:
            tickets: Liste de tickets normalisés
            filename: Nom de fichier personnalisé (optionnel)
            
        Returns:
            str: Chemin du fichier créé
        """
        if not tickets:
            logger.warning("Aucun ticket à exporter")
            return None
        
        if self.file_format == "csv":
            return self.export_to_csv(tickets, filename)
        elif self.file_format == "xlsx":
            return self.export_to_excel(tickets, filename)
        else:
            raise ValueError(f"Format non supporté: {self.file_format}")
    
    def export_incremental(self, tickets: List[Dict], base_filename: str = "tickets") -> str:
        """
        Exporte les tickets avec un nom de fichier basé sur la date.
        Utile pour les exports incrémentaux quotidiens.
        
        Args:
            tickets: Liste de tickets normalisés
            base_filename: Nom de base du fichier
            
        Returns:
            str: Chemin du fichier créé
        """
        date_str = datetime.now().strftime("%Y%m%d")
        extension = "csv" if self.file_format == "csv" else "xlsx"
        filename = self.output_dir / f"{base_filename}_{date_str}.{extension}"
        
        # Si le fichier existe déjà, on ajoute les nouvelles données
        if filename.exists() and self.file_format == "csv":
            # Pour CSV, on ajoute les nouvelles lignes (sans les en-têtes)
            try:
                with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    for ticket in tickets:
                        writer.writerow(self._ticket_to_row(ticket))
                logger.info(f"✅ {len(tickets)} tickets ajoutés à {filename}")
                return str(filename)
            except Exception as e:
                logger.error(f"Erreur lors de l'ajout au fichier CSV: {e}")
                raise
        else:
            # Nouveau fichier ou format Excel (Excel ne supporte pas l'ajout facilement)
            return self.export(tickets, str(filename))

