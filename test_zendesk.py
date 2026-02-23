"""
Script de test pour diagnostiquer la connexion Zendesk.

Ce script permet de tester la connexion à Zendesk et d'identifier
les problèmes de configuration.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire courant au path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import get_settings
    from zendesk_client import ZendeskClient
except ImportError as e:
    print(f"❌ Erreur d'import : {e}")
    print("Assurez-vous d'avoir installé toutes les dépendances : pip install -r requirements.txt")
    sys.exit(1)


def test_zendesk_connection():
    """Teste la connexion à Zendesk avec diagnostic détaillé."""
    print("🔍 Diagnostic de la connexion Zendesk...\n")
    
    # Charger la configuration
    try:
        settings = get_settings()
        print("✅ Configuration chargée")
        print(f"   - Subdomain: {settings.ZENDESK_SUBDOMAIN}")
        print(f"   - Email: {settings.ZENDESK_EMAIL}")
        print(f"   - API Token: {'*' * 10 if settings.ZENDESK_API_TOKEN else 'NON DÉFINI'}\n")
    except Exception as e:
        print(f"❌ Erreur lors du chargement de la configuration : {e}")
        print("\n💡 Vérifiez que votre fichier .env contient :")
        print("   - ZENDESK_SUBDOMAIN")
        print("   - ZENDESK_EMAIL")
        print("   - ZENDESK_API_TOKEN")
        return False
    
    # Vérifier que les valeurs sont présentes
    if not settings.ZENDESK_SUBDOMAIN:
        print("❌ ZENDESK_SUBDOMAIN n'est pas défini dans .env")
        return False
    
    if not settings.ZENDESK_EMAIL:
        print("❌ ZENDESK_EMAIL n'est pas défini dans .env")
        return False
    
    if not settings.ZENDESK_API_TOKEN:
        print("❌ ZENDESK_API_TOKEN n'est pas défini dans .env")
        return False
    
    # Vérifier le format du subdomain
    if ' ' in settings.ZENDESK_SUBDOMAIN or '/' in settings.ZENDESK_SUBDOMAIN:
        print(f"⚠️  Le subdomain semble incorrect : '{settings.ZENDESK_SUBDOMAIN}'")
        print("   Le subdomain ne doit contenir que des lettres, chiffres et tirets")
        print("   Exemple : 'monentreprise' pour monentreprise.zendesk.com")
    
    # Créer le client
    try:
        print("🔌 Création du client Zendesk...")
        client = ZendeskClient(
            subdomain=settings.ZENDESK_SUBDOMAIN,
            email=settings.ZENDESK_EMAIL,
            api_token=settings.ZENDESK_API_TOKEN
        )
        print(f"✅ Client créé")
        print(f"   - URL de base: {client.base_url}\n")
    except Exception as e:
        print(f"❌ Erreur lors de la création du client : {e}")
        return False
    
    # Tester la connexion
    print("🌐 Test de connexion à l'API Zendesk...")
    try:
        # Faire une requête simple pour tester
        import requests
        url = f"{client.base_url}/tickets.json"
        params = {"per_page": 1}
        
        print(f"   URL: {url}")
        print(f"   Authentification: {settings.ZENDESK_EMAIL}/token")
        
        response = client.session.get(url, params=params, timeout=10)
        
        print(f"\n📊 Réponse HTTP:")
        print(f"   - Status Code: {response.status_code}")
        print(f"   - Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            ticket_count = len(data.get('tickets', []))
            print(f"   - Tickets récupérés: {ticket_count}")
            print("\n✅ Connexion Zendesk réussie !")
            return True
        elif response.status_code == 401:
            print("\n❌ Erreur 401 - Non autorisé")
            print("\n💡 Vérifiez :")
            print("   1. Que l'email est correct")
            print("   2. Que l'API Token est correct et actif")
            print("   3. Que l'API Token est activé dans Zendesk (Admin > APIs > Zendesk API)")
            print(f"\n   Réponse: {response.text[:200]}")
            return False
        elif response.status_code == 404:
            print("\n❌ Erreur 404 - Not Found")
            print(f"\n💡 Le subdomain '{settings.ZENDESK_SUBDOMAIN}' semble incorrect")
            print("   Vérifiez que l'URL est correcte")
            print(f"   URL testée: {url}")
            print(f"\n   Réponse: {response.text[:200]}")
            return False
        elif response.status_code == 429:
            print("\n⚠️  Erreur 429 - Too Many Requests")
            print("   Vous avez dépassé la limite de taux de l'API")
            print("   Attendez quelques instants et réessayez")
            return False
        else:
            print(f"\n❌ Erreur HTTP {response.status_code}")
            print(f"   Réponse: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ Timeout - La connexion a pris trop de temps")
        print("   Vérifiez votre connexion internet")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Erreur de connexion : {e}")
        print("   Vérifiez :")
        print("   1. Votre connexion internet")
        print("   2. Que le subdomain est correct")
        print(f"   3. Que l'URL {client.base_url} est accessible")
        return False
    except Exception as e:
        print(f"\n❌ Erreur inattendue : {e}")
        import traceback
        print("\nDétails de l'erreur :")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_zendesk_connection()
    if success:
        print("\n🎉 Tout fonctionne ! Vous pouvez maintenant utiliser l'application.")
    else:
        print("\n❌ La connexion a échoué. Corrigez les problèmes ci-dessus et réessayez.")
    sys.exit(0 if success else 1)

