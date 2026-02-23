"""
Script de test pour vérifier la configuration Google Sheets.

Ce script permet de tester la connexion à Google Sheets avant de lancer
l'application complète.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire courant au path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import get_settings
    from gsheet_client import GoogleSheetsClient
except ImportError as e:
    print(f"❌ Erreur d'import : {e}")
    print("Assurez-vous d'avoir installé toutes les dépendances : pip install -r requirements.txt")
    sys.exit(1)


def test_google_sheets():
    """Teste la connexion à Google Sheets."""
    print("🔍 Vérification de la configuration Google Sheets...\n")
    
    # Charger la configuration
    try:
        settings = get_settings()
        print(f"✅ Configuration chargée")
        print(f"   - Credentials path: {settings.GOOGLE_SHEETS_CREDENTIALS_PATH}")
        print(f"   - Sheet ID: {settings.GOOGLE_SHEET_ID}")
        print(f"   - Sheet name: {settings.GOOGLE_SHEET_NAME}\n")
    except Exception as e:
        print(f"❌ Erreur lors du chargement de la configuration : {e}")
        print("\n💡 Vérifiez que votre fichier .env contient toutes les variables nécessaires.")
        return False
    
    # Vérifier que le fichier credentials.json existe
    credentials_path = Path(settings.GOOGLE_SHEETS_CREDENTIALS_PATH)
    if not credentials_path.exists():
        print(f"❌ Le fichier '{credentials_path}' n'existe pas !")
        print("\n📝 Étapes à suivre :")
        print("   1. Créez un Service Account dans Google Cloud Console")
        print("   2. Téléchargez le fichier JSON de credentials")
        print("   3. Renommez-le en 'credentials.json'")
        print("   4. Placez-le dans le dossier du projet")
        print("\n📖 Consultez SETUP_GOOGLE_SHEETS.md pour un guide détaillé")
        return False
    
    print(f"✅ Fichier credentials.json trouvé : {credentials_path.absolute()}")
    
    # Vérifier le contenu du fichier credentials
    try:
        import json
        with open(credentials_path, 'r') as f:
            creds_data = json.load(f)
        
        client_email = creds_data.get('client_email', 'N/A')
        print(f"✅ Email du Service Account : {client_email}")
        print(f"\n⚠️  IMPORTANT : Assurez-vous d'avoir partagé votre Google Sheet")
        print(f"   avec cet email et donné les permissions 'Éditeur'")
        print(f"   URL de votre feuille : https://docs.google.com/spreadsheets/d/{settings.GOOGLE_SHEET_ID}/edit\n")
    except Exception as e:
        print(f"⚠️  Erreur lors de la lecture du fichier credentials : {e}")
    
    # Tester la connexion
    print("🔌 Test de connexion à Google Sheets...")
    try:
        client = GoogleSheetsClient(
            credentials_path=str(credentials_path),
            sheet_id=settings.GOOGLE_SHEET_ID,
            sheet_name=settings.GOOGLE_SHEET_NAME
        )
        print("✅ Client Google Sheets créé avec succès")
        
        # Tester la connexion
        if client.test_connection():
            print("✅ Connexion à Google Sheets réussie !")
            print("\n🎉 Tout est configuré correctement. Vous pouvez maintenant lancer l'application avec :")
            print("   python app.py")
            return True
        else:
            print("❌ Échec de la connexion à Google Sheets")
            print("\n💡 Vérifiez que :")
            print("   1. La feuille est bien partagée avec l'email du Service Account")
            print("   2. Les permissions sont sur 'Éditeur' (pas 'Lecteur')")
            print("   3. L'ID de la feuille est correct dans votre .env")
            return False
            
    except FileNotFoundError:
        print(f"❌ Fichier credentials non trouvé : {credentials_path}")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de la connexion : {e}")
        print("\n💡 Erreurs courantes :")
        print("   - Fichier credentials.json invalide ou corrompu")
        print("   - Feuille non partagée avec le Service Account")
        print("   - APIs Google Sheets/Drive non activées")
        print("   - ID de la feuille incorrect")
        return False


if __name__ == "__main__":
    success = test_google_sheets()
    sys.exit(0 if success else 1)

