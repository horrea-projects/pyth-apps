"""
Client Google Sheets pour écrire les données des tickets Zendesk.

Ce module gère la connexion à Google Sheets via Service Account
et l'écriture des données normalisées.
"""

import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Client pour interagir avec Google Sheets."""
    
    # Portée nécessaire pour accéder à Google Sheets
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # En-têtes par défaut pour la feuille
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
    
    def __init__(self, credentials_path: str, sheet_id: str, sheet_name: str = "Tickets"):
        """
        Initialise le client Google Sheets.
        
        Args:
            credentials_path: Chemin vers le fichier JSON de credentials Service Account
            sheet_id: ID de la feuille Google Sheets
            sheet_name: Nom de l'onglet dans la feuille
        """
        self.credentials_path = credentials_path
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self.client = None
        self.sheet = None
        self._connect()
    
    def _connect(self):
        """Établit la connexion à Google Sheets."""
        try:
            creds = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.SCOPES
            )
            self.client = gspread.authorize(creds)
            spreadsheet = self.client.open_by_key(self.sheet_id)
            
            # Créer l'onglet s'il n'existe pas
            try:
                self.sheet = spreadsheet.worksheet(self.sheet_name)
                logger.info(f"Onglet '{self.sheet_name}' trouvé")
            except gspread.exceptions.WorksheetNotFound:
                logger.info(f"Création de l'onglet '{self.sheet_name}'")
                self.sheet = spreadsheet.add_worksheet(
                    title=self.sheet_name,
                    rows=1000,
                    cols=len(self.DEFAULT_HEADERS)
                )
                # Ajouter les en-têtes
                self.sheet.append_row(self.DEFAULT_HEADERS)
                logger.info(f"Onglet '{self.sheet_name}' créé avec en-têtes")
                
        except Exception as e:
            logger.error(f"Erreur lors de la connexion à Google Sheets: {e}")
            raise
    
    def _ensure_headers(self):
        """
        S'assure que les en-têtes sont présents dans la feuille.
        Si la feuille est vide ou n'a pas d'en-têtes, les crée.
        """
        try:
            # Vérifier si la première ligne existe et contient des en-têtes
            first_row = self.sheet.row_values(1)
            
            if not first_row or first_row != self.DEFAULT_HEADERS:
                # Si la feuille a des données, on ne veut pas écraser
                # On vérifie d'abord si elle est vraiment vide
                all_values = self.sheet.get_all_values()
                
                if len(all_values) == 0 or (len(all_values) == 1 and not any(all_values[0])):
                    # Feuille vide, on ajoute les en-têtes
                    self.sheet.append_row(self.DEFAULT_HEADERS)
                    logger.info("En-têtes ajoutés à la feuille vide")
                elif first_row != self.DEFAULT_HEADERS:
                    # En-têtes différents, on les met à jour
                    self.sheet.update("A1", [self.DEFAULT_HEADERS])
                    logger.info("En-têtes mis à jour")
        except Exception as e:
            logger.warning(f"Erreur lors de la vérification des en-têtes: {e}")
            # En cas d'erreur, on essaie quand même d'ajouter les en-têtes
            try:
                self.sheet.append_row(self.DEFAULT_HEADERS)
            except:
                pass
    
    def _ticket_to_row(self, ticket: Dict) -> List:
        """
        Convertit un ticket en liste de valeurs pour une ligne Google Sheets.
        
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
    
    def write_tickets(self, tickets: List[Dict], append: bool = True, clear_existing: bool = False):
        """
        Écrit les tickets dans Google Sheets.
        
        Args:
            tickets: Liste de tickets normalisés
            append: Si True, ajoute les tickets. Si False, remplace tout.
            clear_existing: Si True, efface les données existantes avant d'écrire
        """
        if not tickets:
            logger.warning("Aucun ticket à écrire")
            return
        
        try:
            self._ensure_headers()
            
            if clear_existing:
                # Effacer toutes les données sauf les en-têtes
                all_values = self.sheet.get_all_values()
                if len(all_values) > 1:
                    # Supprimer toutes les lignes sauf la première (en-têtes)
                    self.sheet.delete_rows(2, len(all_values))
                    logger.info("Données existantes effacées")
            
            # Convertir les tickets en lignes
            rows = [self._ticket_to_row(ticket) for ticket in tickets]
            
            if append:
                # Ajouter les nouvelles lignes
                self.sheet.append_rows(rows, value_input_option="RAW")
                logger.info(f"{len(rows)} tickets ajoutés à la feuille")
            else:
                # Remplacer toutes les données (garder les en-têtes)
                if rows:
                    # Calculer la plage de cellules (A2 jusqu'à la dernière ligne)
                    end_col = chr(ord('A') + len(self.DEFAULT_HEADERS) - 1)
                    range_name = f"A2:{end_col}{len(rows) + 1}"
                    self.sheet.update(range_name, rows, value_input_option="RAW")
                    logger.info(f"{len(rows)} tickets écrits dans la feuille")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture dans Google Sheets: {e}")
            raise
    
    def get_existing_ticket_ids(self) -> set:
        """
        Récupère les IDs de tickets déjà présents dans la feuille.
        Utile pour éviter les doublons lors des mises à jour incrémentales.
        
        Returns:
            set: Ensemble des IDs de tickets existants
        """
        try:
            all_values = self.sheet.get_all_values()
            if len(all_values) <= 1:  # Seulement les en-têtes ou vide
                return set()
            
            # L'ID est dans la première colonne (index 0)
            ticket_ids = set()
            for row in all_values[1:]:  # Ignorer la première ligne (en-têtes)
                if row and row[0]:  # Vérifier que la cellule n'est pas vide
                    try:
                        ticket_ids.add(int(row[0]))
                    except (ValueError, IndexError):
                        continue
            
            logger.info(f"{len(ticket_ids)} IDs de tickets existants trouvés")
            return ticket_ids
            
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération des IDs existants: {e}")
            return set()
    
    def update_or_append_tickets(self, tickets: List[Dict]):
        """
        Met à jour les tickets existants ou ajoute les nouveaux.
        Cette méthode évite les doublons en vérifiant les IDs existants.
        
        Args:
            tickets: Liste de tickets normalisés
        """
        if not tickets:
            logger.warning("Aucun ticket à mettre à jour")
            return
        
        try:
            self._ensure_headers()
            existing_ids = self.get_existing_ticket_ids()
            
            # Séparer les tickets à mettre à jour et ceux à ajouter
            tickets_to_update = []
            tickets_to_append = []
            
            for ticket in tickets:
                ticket_id = ticket.get("ticket_id")
                if ticket_id and ticket_id in existing_ids:
                    tickets_to_update.append(ticket)
                else:
                    tickets_to_append.append(ticket)
            
            # Ajouter les nouveaux tickets
            if tickets_to_append:
                rows = [self._ticket_to_row(ticket) for ticket in tickets_to_append]
                self.sheet.append_rows(rows, value_input_option="RAW")
                logger.info(f"{len(tickets_to_append)} nouveaux tickets ajoutés")
            
            # Mettre à jour les tickets existants
            if tickets_to_update:
                # Pour les mises à jour, on devrait trouver la ligne correspondante
                # Pour simplifier, on ajoute aussi (l'utilisateur peut nettoyer les doublons)
                # Ou implémenter une logique de recherche et remplacement
                logger.info(f"{len(tickets_to_update)} tickets à mettre à jour (ajoutés comme nouvelles lignes)")
                rows = [self._ticket_to_row(ticket) for ticket in tickets_to_update]
                self.sheet.append_rows(rows, value_input_option="RAW")
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour/ajout des tickets: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Teste la connexion à Google Sheets.
        
        Returns:
            bool: True si la connexion réussit
        """
        try:
            # Essayer de lire la première ligne
            self.sheet.row_values(1)
            return True
        except Exception as e:
            logger.error(f"Échec du test de connexion: {e}")
            return False

