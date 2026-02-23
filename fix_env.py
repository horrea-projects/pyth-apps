"""
Script pour corriger automatiquement le fichier .env.

Nettoie le ZENDESK_SUBDOMAIN pour enlever les URLs complètes.
"""

import re
from pathlib import Path

def fix_subdomain(value: str) -> str:
    """
    Nettoie le subdomain pour enlever l'URL complète.
    
    Args:
        value: Valeur du subdomain (peut être une URL complète)
        
    Returns:
        str: Subdomain nettoyé (ex: "horrea")
    """
    # Enlever les espaces
    value = value.strip()
    
    # Enlever https:// ou http://
    value = re.sub(r'^https?://', '', value)
    
    # Enlever .zendesk.com et tout ce qui suit
    value = re.sub(r'\.zendesk\.com.*$', '', value)
    
    # Enlever les slashes
    value = value.rstrip('/')
    
    # Enlever tout ce qui n'est pas alphanumérique ou tiret
    value = re.sub(r'[^a-zA-Z0-9-]', '', value)
    
    return value

def fix_env_file(env_path: Path = None):
    """
    Corrige le fichier .env en nettoyant le ZENDESK_SUBDOMAIN.
    
    Args:
        env_path: Chemin vers le fichier .env (défaut: .env dans le répertoire courant)
    """
    if env_path is None:
        env_path = Path(__file__).parent / ".env"
    
    if not env_path.exists():
        print(f"❌ Le fichier {env_path} n'existe pas")
        return False
    
    print(f"📝 Lecture du fichier {env_path}...")
    
    # Lire le fichier
    lines = []
    subdomain_found = False
    subdomain_old = None
    subdomain_new = None
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Vérifier si c'est la ligne ZENDESK_SUBDOMAIN
            if line.strip().startswith('ZENDESK_SUBDOMAIN='):
                subdomain_found = True
                # Extraire la valeur
                parts = line.split('=', 1)
                if len(parts) == 2:
                    old_value = parts[1].strip()
                    subdomain_old = old_value
                    # Nettoyer la valeur
                    new_value = fix_subdomain(old_value)
                    subdomain_new = new_value
                    # Reconstruire la ligne
                    lines.append(f"ZENDESK_SUBDOMAIN={new_value}\n")
                    print(f"   Ancienne valeur: {old_value}")
                    print(f"   Nouvelle valeur: {new_value}")
                else:
                    lines.append(line)
            else:
                lines.append(line)
    
    if not subdomain_found:
        print("⚠️  ZENDESK_SUBDOMAIN non trouvé dans le fichier .env")
        return False
    
    if subdomain_old == subdomain_new:
        print(f"✅ Le subdomain est déjà correct : {subdomain_new}")
        return True
    
    # Sauvegarder le fichier corrigé
    print(f"\n💾 Sauvegarde du fichier corrigé...")
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"✅ Fichier .env corrigé avec succès !")
    print(f"   {subdomain_old} → {subdomain_new}")
    return True

if __name__ == "__main__":
    import sys
    
    env_path = None
    if len(sys.argv) > 1:
        env_path = Path(sys.argv[1])
    
    success = fix_env_file(env_path)
    sys.exit(0 if success else 1)

