import urllib.parse
import sys
import requests

def get_pcloud_token(client_id: str, client_secret: str):
    print("="*60)
    print("pCloud OAuth 2.0 Token Generator")
    print("="*60)
    
    # Étape 1 : URL d'Autorisation
    auth_url = f"https://my.pcloud.com/oauth2/authorize?client_id={client_id}&response_type=code"
    
    print("\n1. Ouvrez ce lien dans votre navigateur web :")
    print(f"   {auth_url}")
    print("\n   => Connectez-vous à pCloud et autorisez l'application.")
    print("   => Vous serez redirigé vers une URL (qui peut échouer, c'est normal).")
    print("   => Regardez la barre d'adresse de votre navigateur : il y aura un paramètre '?code=...'")
    print("   => Copiez la valeur exacte de ce 'code'.")
    
    # Étape 2 : Récupérer le code
    code = input("\n2. Collez le 'code' ici : ").strip()
    
    if not code:
        print("Erreur: Code vide. Annulation.")
        sys.exit(1)
        
    print(f"\n3. Échange du code '{code}' contre un Access Token...")
    
    # Étape 3 : Échange
    token_url = "https://api.pcloud.com/oauth2_token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code
    }
    
    try:
        resp = requests.get(token_url, params=params)
        data = resp.json()
        
        if "access_token" in data:
            print("\n" + "="*60)
            print("🚀 SUCCÈS ! Voici votre Access Token Permanent :")
            print(f"PCLOUD_ACCESS_TOKEN={data['access_token']}")
            print("="*60)
            print("\nAjoutez cette ligne dans votre fichier backend/.env et redémarrez Uvicorn !")
        else:
            print("\n❌ ERREUR lors de l'échange :")
            print(data)
            
    except Exception as e:
        print(f"\n❌ Erreur réseau : {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        # Prompt if not provided via CLI
        client_id = input("Entrez votre Client ID (pCloud) : ").strip()
        client_secret = input("Entrez votre Client Secret (pCloud) : ").strip()
    else:
        client_id = sys.argv[1]
        client_secret = sys.argv[2]
        
    if client_id and client_secret:
        get_pcloud_token(client_id, client_secret)
    else:
        print("Client ID et Secret sont requis.")
