"""Test MAL OAuth2 authentication"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').absolute()))

from services.mal_oauth2_client import MALOAuth2Client
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

def test_auth():
    """Test MAL authentication"""
    client_id = "77dcb3ef6a0b47401c5d76e5957bc425"
    token_path = Path("test_tokens.json")
    
    print("Creating OAuth2 client...")
    client = MALOAuth2Client(client_id, token_path)
    
    print("\nStarting authentication flow...")
    print("1. A browser window will open")
    print("2. Log in to MyAnimeList")
    print("3. Authorize the application")
    print("4. You'll be redirected to localhost:8888")
    print("\nStarting in 3 seconds...")
    import time
    time.sleep(3)
    
    success = client.authorize()
    
    if success:
        print("\n✓ Authentication successful!")
        print("Testing API access...")
        
        # Test API call
        user_info = client.make_api_request("/users/@me")
        if user_info:
            print(f"✓ Connected as: {user_info.get('name', 'Unknown')}")
        else:
            print("✗ Failed to get user info")
    else:
        print("\n✗ Authentication failed")
        print("Please check:")
        print("1. You're logged in to MyAnimeList in your browser")
        print("2. Port 8888 is not blocked by firewall")
        print("3. The redirect URL is set to http://localhost:8888/callback in your MAL app settings")

if __name__ == "__main__":
    test_auth()