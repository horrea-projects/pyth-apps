# Guide de Configuration Google Sheets

## 📋 Étape 1 : Créer un Projet Google Cloud

1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Connectez-vous avec votre compte Google
3. Cliquez sur le sélecteur de projet en haut (à côté de "Google Cloud")
4. Cliquez sur **"NOUVEAU PROJET"**
5. Donnez un nom à votre projet (ex: "Zendesk Connector")
6. Cliquez sur **"CRÉER"**

## 🔌 Étape 2 : Activer les APIs nécessaires

1. Dans le menu latéral, allez dans **"APIs et services"** > **"Bibliothèque"**
2. Recherchez **"Google Sheets API"** et cliquez dessus
3. Cliquez sur **"ACTIVER"**
4. Retournez à la bibliothèque et recherchez **"Google Drive API"**
5. Cliquez sur **"ACTIVER"**

## 👤 Étape 3 : Créer un Service Account

1. Dans le menu latéral, allez dans **"IAM et administration"** > **"Comptes de service"**
2. Cliquez sur **"CRÉER UN COMPTE DE SERVICE"** en haut
3. Remplissez les informations :
   - **Nom du compte de service** : `zendesk-connector` (ou un nom de votre choix)
   - **Description** : `Service account pour connecter Zendesk à Google Sheets`
4. Cliquez sur **"CRÉER ET CONTINUER"**
5. Pour le rôle, vous pouvez laisser vide ou sélectionner "Éditeur" (optionnel)
6. Cliquez sur **"CONTINUER"** puis **"TERMINÉ"**

## 🔑 Étape 4 : Télécharger le fichier de credentials

1. Dans la liste des comptes de service, cliquez sur celui que vous venez de créer
2. Allez dans l'onglet **"CLÉS"**
3. Cliquez sur **"AJOUTER UNE CLÉ"** > **"Créer une nouvelle clé"**
4. Sélectionnez **"JSON"**
5. Cliquez sur **"CRÉER"**
6. Un fichier JSON sera téléchargé automatiquement
7. **IMPORTANT** : Notez l'email du Service Account (format : `nom-du-service@nom-du-projet.iam.gserviceaccount.com`)
   - Vous le trouverez dans le fichier JSON téléchargé, dans le champ `"client_email"`

## 📁 Étape 5 : Placer le fichier credentials.json

1. Renommez le fichier JSON téléchargé en `credentials.json`
2. Déplacez-le dans le dossier du projet : `/Users/leocarre/Documents/DEV/Horrea/Zendesk Connector/`
3. Vérifiez que le fichier est bien présent à la racine du projet

## 🔗 Étape 6 : Partager votre Google Sheet avec le Service Account

1. Ouvrez votre Google Sheet : https://docs.google.com/spreadsheets/d/1-0uyOH7xwU8OfFkm2gJKUZt-6pfx_ScTnfDmyW_BuuY/edit
2. Cliquez sur le bouton **"Partager"** en haut à droite
3. Dans le champ "Ajouter des personnes ou des groupes", collez l'email du Service Account
   - C'est l'email que vous avez noté à l'étape 4 (format : `xxxxx@xxxxx.iam.gserviceaccount.com`)
4. Assurez-vous que les permissions sont définies sur **"Éditeur"**
5. **DÉCOCHEZ** la case "Avertir les personnes" (le Service Account n'a pas besoin d'être notifié)
6. Cliquez sur **"Partager"**

## ✅ Étape 7 : Mettre à jour votre fichier .env

Ajoutez ou modifiez ces lignes dans votre fichier `.env` :

```env
GOOGLE_SHEETS_CREDENTIALS_PATH=credentials.json
GOOGLE_SHEET_ID=1-0uyOH7xwU8OfFkm2gJKUZt-6pfx_ScTnfDmyW_BuuY
GOOGLE_SHEET_NAME=Tickets
```

**Note** : Si vous voulez utiliser un onglet spécifique dans votre feuille, changez `GOOGLE_SHEET_NAME`. Sinon, l'application créera automatiquement un onglet nommé "Tickets".

## 🧪 Étape 8 : Tester la connexion

Vous pouvez tester la connexion en lançant l'application :

```bash
python app.py
```

Puis visitez : http://localhost:8000/status

Vous devriez voir que `gsheet_connected` est `true`.

## ❓ Dépannage

### Erreur : "FileNotFoundError: credentials.json"
- Vérifiez que le fichier `credentials.json` est bien dans le dossier du projet
- Vérifiez le chemin dans `.env` : `GOOGLE_SHEETS_CREDENTIALS_PATH=credentials.json`

### Erreur : "Permission denied" ou "403 Forbidden"
- Vérifiez que vous avez bien partagé la feuille avec l'email du Service Account
- Vérifiez que les permissions sont sur "Éditeur" (pas "Lecteur")
- Vérifiez que l'email du Service Account est correct (trouvable dans `credentials.json`)

### Erreur : "API not enabled"
- Vérifiez que les APIs Google Sheets et Google Drive sont bien activées dans Google Cloud Console

## 📝 Résumé des informations importantes

- **ID de votre feuille** : `1-0uyOH7xwU8OfFkm2gJKUZt-6pfx_ScTnfDmyW_BuuY`
- **Fichier credentials** : `credentials.json` (à placer à la racine du projet)
- **Email du Service Account** : Trouvable dans `credentials.json` sous `"client_email"`

