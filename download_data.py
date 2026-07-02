import os
import zipfile
import requests

# ID de votre fichier partagé sur Google Drive
# Remplacez cette valeur par l'ID réel de votre fichier data.zip sur Google Drive
# Exemple d'URL de partage : https://drive.google.com/file/d/1A2b3C4d5E6fG7hI8jK9lMnOpQrStUvWx/view?usp=sharing
# L'ID est : 1A2b3C4d5E6fG7hI8jK9lMnOpQrStUvWx
GOOGLE_DRIVE_FILE_ID = "VOTRE_ID_DE_FICHIER_GOOGLE_DRIVE"

def get_confirm_token(response):
    """Récupère le jeton de confirmation pour les gros fichiers Google Drive."""
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value
    return None

def download_file_from_google_drive(file_id, destination):
    """Télécharge un fichier depuis Google Drive en gérant les gros volumes."""
    url = "https://docs.google.com/uc?export=download"
    session = requests.Session()

    print(f"🔄 Connexion à Google Drive pour récupérer le fichier...")
    response = session.get(url, params={'id': file_id}, stream=True)
    token = get_confirm_token(response)

    if token:
        params = {'id': file_id, 'confirm': token}
        response = session.get(url, params=params, stream=True)

    print(f"📥 Téléchargement en cours...")
    chunk_size = 32768
    with open(destination, "wb") as f:
        for chunk in response.iter_content(chunk_size):
            if chunk: # filtre les chunks de keep-alive
                f.write(chunk)
    print(f"✅ Téléchargement terminé : {destination}")

def main():
    if GOOGLE_DRIVE_FILE_ID == "VOTRE_ID_DE_FICHIER_GOOGLE_DRIVE":
        print("❌ ERREUR : Veuillez modifier 'download_data.py' et remplacer GOOGLE_DRIVE_FILE_ID par l'ID réel de votre fichier Google Drive.")
        return

    zip_filename = "data_temp.zip"
    
    try:
        # Téléchargement
        download_file_from_google_drive(GOOGLE_DRIVE_FILE_ID, zip_filename)
        
        # Extraction du ZIP
        print("🔓 Extraction des fichiers de données...")
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall(".")
        
        print("🎉 Données installées avec succès !")
        
        # Nettoyage du fichier zip temporaire
        os.remove(zip_filename)
        print("🧹 Nettoyage du fichier temporaire effectué.")
        
    except Exception as e:
        print(f"❌ Une erreur est survenue : {e}")
        if os.path.exists(zip_filename):
            os.remove(zip_filename)

if __name__ == "__main__":
    main()
