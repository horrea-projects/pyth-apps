"""
Client Zendesk pour récupérer les tickets avec pagination.

Ce module gère la connexion à l'API Zendesk et la récupération
de tous les tickets avec gestion de la pagination cursor-based.
"""

import requests
from typing import List, Dict, Optional, Iterator
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ZendeskClient:
    """Client pour interagir avec l'API Zendesk."""
    
    def __init__(self, subdomain: str, email: str, api_token: str):
        """
        Initialise le client Zendesk.
        
        Args:
            subdomain: Sous-domaine Zendesk (ex: 'monentreprise')
            email: Email de l'utilisateur Zendesk
            api_token: Token API Zendesk
        """
        self.subdomain = subdomain
        self.email = email
        self.api_token = api_token
        self.base_url = f"https://{subdomain}.zendesk.com/api/v2"
        self.session = requests.Session()
        self.session.auth = (f"{email}/token", api_token)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, full_url: Optional[str] = None) -> Dict:
        """
        Effectue une requête HTTP vers l'API Zendesk.
        
        Args:
            endpoint: Endpoint API (ex: '/tickets.json')
            params: Paramètres de requête optionnels
            full_url: URL complète (utilisée pour la pagination avec next_page)
            
        Returns:
            Dict: Réponse JSON de l'API
            
        Raises:
            requests.HTTPError: Si la requête échoue
        """
        if full_url:
            # Utiliser l'URL complète directement (pour la pagination)
            url = full_url
            # Ne pas passer params car ils sont déjà dans l'URL
            request_params = None
        else:
            url = f"{self.base_url}{endpoint}"
            request_params = params
        
        try:
            response = self.session.get(url, params=request_params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête à {url}: {e}")
            raise
    
    def get_all_tickets(self, 
                       page_size: int = 100,
                       include_fields: Optional[List[str]] = None) -> Iterator[Dict]:
        """
        Récupère tous les tickets avec pagination.
        
        L'API Zendesk utilise une pagination basée sur les liens "next"
        dans la réponse JSON pour naviguer entre les pages.
        
        Args:
            page_size: Nombre de tickets par page (max 100)
            include_fields: Liste des champs supplémentaires à inclure
            
        Yields:
            Dict: Ticket Zendesk normalisé
        """
        url = None
        page_count = 0
        
        while True:
            # Construire l'URL de la requête
            if url is None:
                # Première requête
                endpoint = "/tickets.json"
                params = {
                    "per_page": min(page_size, 100),  # Limite API Zendesk
                    "sort_by": "created_at",
                    "sort_order": "desc"  # Plus récents en premier
                }
                if include_fields:
                    params["include"] = ",".join(include_fields)
                full_url = None
            else:
                # Requêtes suivantes : utiliser l'URL complète du lien "next"
                # next_page contient déjà l'URL complète avec tous les paramètres
                endpoint = None
                params = None
                full_url = url
            
            try:
                if full_url:
                    data = self._make_request("", params=None, full_url=full_url)
                else:
                    data = self._make_request(endpoint, params=params)
                tickets = data.get("tickets", [])
                
                if not tickets:
                    logger.info("Aucun ticket trouvé ou fin de pagination")
                    break
                
                page_count += 1
                logger.info(f"Page {page_count}: {len(tickets)} tickets récupérés")
                
                # Normaliser chaque ticket
                for ticket in tickets:
                    yield self._normalize_ticket(ticket)
                
                # Vérifier s'il y a une page suivante
                # Zendesk peut utiliser soit "next_page" directement, soit "links.next"
                url = data.get("next_page")
                if not url:
                    links = data.get("links", {})
                    url = links.get("next") if links else None
                
                if not url:
                    logger.info("Fin de la pagination")
                    break
                    
            except requests.exceptions.HTTPError as e:
                logger.error(f"Erreur HTTP lors de la récupération des tickets: {e}")
                logger.error(f"Page: {page_count + 1}, Tickets récupérés jusqu'à présent: {count}")
                # Si c'est une erreur 429 (rate limit), on pourrait retry, mais pour l'instant on arrête
                if e.response and e.response.status_code == 429:
                    logger.warning("Limite de taux atteinte. Attendez quelques instants avant de réessayer.")
                raise
            except Exception as e:
                logger.error(f"Erreur inattendue lors de la récupération des tickets: {e}")
                logger.error(f"Page: {page_count + 1}, Tickets récupérés jusqu'à présent: {count}")
                import traceback
                logger.error(traceback.format_exc())
                raise
    
    def get_tickets_updated_since(self, 
                                  since_datetime: datetime,
                                  page_size: int = 100) -> Iterator[Dict]:
        """
        Récupère les tickets mis à jour depuis une date donnée.
        
        Utile pour les mises à jour incrémentales.
        
        Args:
            since_datetime: Date/heure de référence
            page_size: Nombre de tickets par page
            
        Yields:
            Dict: Ticket Zendesk normalisé
        """
        # Convertir en timestamp Unix pour l'API Zendesk
        since_timestamp = int(since_datetime.timestamp())
        
        url = None
        page_count = 0
        
        while True:
            # Construire l'URL de la requête
            if url is None:
                # Première requête
                endpoint = "/tickets.json"
                params = {
                    "per_page": min(page_size, 100),
                    "sort_by": "updated_at",
                    "sort_order": "desc",  # Plus récents en premier
                    "start_time": since_timestamp
                }
                full_url = None
            else:
                # Requêtes suivantes : utiliser l'URL complète du lien "next"
                endpoint = None
                params = None
                full_url = url
            
            try:
                if full_url:
                    data = self._make_request("", params=None, full_url=full_url)
                else:
                    data = self._make_request(endpoint, params=params)
                tickets = data.get("tickets", [])
                
                if not tickets:
                    logger.info("Aucun ticket mis à jour trouvé")
                    break
                
                page_count += 1
                logger.info(f"Page {page_count}: {len(tickets)} tickets mis à jour récupérés")
                
                for ticket in tickets:
                    # Filtrer les tickets réellement mis à jour après la date
                    ticket_updated = self._parse_datetime(ticket.get("updated_at"))
                    if ticket_updated:
                        # S'assurer que les deux dates sont timezone-aware
                        if ticket_updated.tzinfo is None:
                            from datetime import timezone
                            ticket_updated = ticket_updated.replace(tzinfo=timezone.utc)
                        if since_datetime.tzinfo is None:
                            from datetime import timezone
                            since_datetime = since_datetime.replace(tzinfo=timezone.utc)
                        
                        if ticket_updated > since_datetime:
                            yield self._normalize_ticket(ticket)
                    else:
                        # Si on ne peut pas parser la date, inclure le ticket par sécurité
                        yield self._normalize_ticket(ticket)
                
                # Vérifier s'il y a une page suivante
                # Zendesk peut utiliser soit "next_page" directement, soit "links.next"
                url = data.get("next_page")
                if not url:
                    links = data.get("links", {})
                    url = links.get("next") if links else None
                
                if not url:
                    break
                    
            except requests.exceptions.HTTPError as e:
                logger.error(f"Erreur lors de la récupération des tickets mis à jour: {e}")
                raise
    
    def _normalize_ticket(self, ticket: Dict) -> Dict:
        """
        Normalise un ticket Zendesk en structure plate pour Google Sheets.
        
        Args:
            ticket: Ticket brut de l'API Zendesk
            
        Returns:
            Dict: Ticket normalisé avec tous les champs nécessaires
        """
        # Traiter les custom_fields
        custom_fields = ticket.get("custom_fields", [])
        custom_fields_str = ""
        if custom_fields:
            # Format: "ID1:value1|ID2:value2|..."
            cf_parts = []
            for cf in custom_fields:
                cf_id = cf.get("id", "")
                cf_value = cf.get("value")
                if cf_value is not None and cf_value != "":
                    cf_parts.append(f"{cf_id}:{cf_value}")
            custom_fields_str = "|".join(cf_parts)
        
        return {
            "ticket_id": ticket.get("id"),
            "subject": ticket.get("subject", ""),
            "status": ticket.get("status", ""),
            "priority": ticket.get("priority", ""),
            "requester_id": ticket.get("requester_id"),
            "assignee_id": ticket.get("assignee_id"),
            "created_at": ticket.get("created_at", ""),
            "updated_at": ticket.get("updated_at", ""),
            "tags": ", ".join(ticket.get("tags", [])) if ticket.get("tags") else "",
            # Champs supplémentaires utiles
            "type": ticket.get("type", ""),
            "via": ticket.get("via", {}).get("channel", "") if ticket.get("via") else "",
            "url": ticket.get("url", ""),
            "description": str(ticket.get("description", ""))[:500],  # Limiter la longueur
            "custom_fields": custom_fields_str
        }
    
    def _parse_datetime(self, date_string: Optional[str]) -> Optional[datetime]:
        """
        Parse une chaîne de date Zendesk en objet datetime.
        
        Args:
            date_string: Chaîne de date au format ISO 8601
            
        Returns:
            datetime: Objet datetime ou None
        """
        if not date_string:
            return None
        
        try:
            # Format Zendesk: "2023-12-01T10:30:00Z"
            return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            logger.warning(f"Impossible de parser la date: {date_string}")
            return None
    
    def test_connection(self) -> bool:
        """
        Teste la connexion à l'API Zendesk.
        
        Returns:
            bool: True si la connexion réussit
        """
        try:
            data = self._make_request("/tickets.json", params={"per_page": 1})
            return True
        except Exception as e:
            logger.error(f"Échec du test de connexion: {e}")
            return False

