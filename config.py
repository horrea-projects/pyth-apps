"""
Configuration module for Zendesk to Google Sheets connector.

This module handles environment variables and configuration settings.
All sensitive data should be provided via environment variables.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env si présent
load_dotenv()


class Settings(BaseSettings):
    """Configuration settings for the application."""
    
    # Zendesk Configuration
    ZENDESK_SUBDOMAIN: str
    ZENDESK_EMAIL: str
    ZENDESK_API_TOKEN: str
    
    # Export Configuration
    # Mode d'export: 'gsheet', 'csv', ou 'xlsx'
    EXPORT_MODE: str = "csv"
    
    # Google Sheets Configuration (requis seulement si EXPORT_MODE='gsheet')
    GOOGLE_SHEETS_CREDENTIALS_PATH: Optional[str] = None
    GOOGLE_SHEET_ID: Optional[str] = None
    GOOGLE_SHEET_NAME: str = "Tickets"
    
    # Export File Configuration (utilisé si EXPORT_MODE='csv' ou 'xlsx')
    EXPORT_OUTPUT_DIR: str = "exports"
    EXPORT_FILE_FORMAT: str = "csv"  # 'csv' ou 'xlsx'
    
    # Application Configuration
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False
    
    # Google OAuth (pour la webapp "Sync vers Google Sheet" - connexion avec votre compte)
    # Créer un "OAuth 2.0 Client ID" (Web application) dans Google Cloud Console
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    # URL de base de l'app (ex: https://votreuser.pythonanywhere.com) pour le redirect OAuth
    BASE_URL: Optional[str] = None
    
    # Fichier de stockage des tokens et préférences (webapp sync)
    OAUTH_DATA_FILE: str = "data/oauth_data.json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


def get_settings() -> Settings:
    """
    Récupère la configuration de l'application.
    
    Returns:
        Settings: Instance de configuration
    """
    return Settings()

