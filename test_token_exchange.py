"""Debug MAL token exchange"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').absolute()))

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from services.mal_oauth2_client import MALOAuth2Client

def test_auth():
    client_id = "77dcb3ef6a0b47401c5d76e5957bc425"
    token_path = Path("debug_tokens.json")
    
    print("\n" + "="*50)
    print("MAL OAuth2 Debug Test")
    print("="*50)
    print(f"Client ID: {client_id}")
    print(f"Redirect URI: http://localhost:8888/callback")
    print("="*50)
    
    client = MALOAuth2Client(client_id, token_path)
    
    print("\nStarting authentication...")
    print("Please complete the authorization in your browser.")
    print("Watch for any errors in the console below:")
    print("-"*50)
    
    success = client.authorize()
    
    print("-"*50)
    if success:
        print("\n✓ SUCCESS! Authentication completed.")
        print("Testing API access...")
        
        user_info = client.make_api_request("/users/@me")
        if user_info:
            print(f"✓ API working! Connected as: {user_info.get('name', 'Unknown')}")
        else:
            print("✗ API test failed")
    else:
        print("\n✗ FAILED! Check the error messages above.")
        print("\nCommon issues:")
        print("1. Check that your MAL app redirect URL is EXACTLY: http://localhost:8888/callback")
        print("2. Make sure you clicked 'Allow' on the MAL authorization page")
        print("3. Check if Windows Firewall is blocking port 8888")

if __name__ == "__main__":
    test_auth()