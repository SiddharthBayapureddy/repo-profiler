import os
import time
import jwt  # JSON Web Tokens
import httpx
from dotenv import load_dotenv
import base64

load_dotenv()

GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_INSTALLATION_ID = os.getenv("GITHUB_INSTALLATION_ID")
GITHUB_PRIVATE_KEY_MULTI = os.getenv("GITHUB_PRIVATE_KEY")
GITHUB_PRIVATE_KEY_B64 = os.getenv("GITHUB_PRIVATE_KEY_B64")

if GITHUB_PRIVATE_KEY_B64:
    print("Found Base64 private key. Decoding for Vercel.")
    try:
        GITHUB_PRIVATE_KEY = base64.b64decode(GITHUB_PRIVATE_KEY_B64).decode('utf-8')
    except Exception as e:
        print(f"FAILED to decode Base64 private key: {e}")
        raise
elif GITHUB_PRIVATE_KEY_MULTI:
    print("Found multi-line private key. Running locally.")
    GITHUB_PRIVATE_KEY = GITHUB_PRIVATE_KEY_MULTI
else:
    raise ValueError("Missing GitHub private key. Set GITHUB_PRIVATE_KEY (local) or GITHUB_PRIVATE_KEY_B64 (Vercel).")

# Check if all required variables are loaded
if not GITHUB_APP_ID or not GITHUB_INSTALLATION_ID or not GITHUB_PRIVATE_KEY:
    raise ValueError("One or more GitHub environment variables are not set in .env")

# --- Private Helper Function ---

def _create_jwt(app_id: str, private_key: str) -> str:
    # Creates a JSON Web Token (JWT) to authenticate as a GitHub App.
    
    # Get the current time
    now = int(time.time())
    
    # Define the payload
    payload = {
        # Issued at time (60 seconds in the past to account for clock drift)
        "iat": now - 60,  
        # Expiration time (10 minutes is the maximum)
        "exp": now + (9 * 60),
        # Issuer (your GitHub App ID)
        "iss": app_id
    }
    
    # Sign the JWT with the private key
    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256"
    )
    
    return token

# --- Public Function ---

async def get_installation_access_token() -> str:
    """
    Gets a 1-hour installation access token for your app.
    
    This token is what you'll use to make all your API calls.
    """
    
    # 1. Create the JWT
    jwt_token = _create_jwt(GITHUB_APP_ID, GITHUB_PRIVATE_KEY)
    
    # 2. Exchange the JWT for an Installation Access Token
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    url = f"https://api.github.com/app/installations/{GITHUB_INSTALLATION_ID}/access_tokens"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers)
            response.raise_for_status()  # Raises an error for 4xx/5xx responses
            
            # Parse the response and return the token
            data = response.json()
            return data["token"]
            
        except httpx.HTTPStatusError as e:
            print(f"Error getting installation token: {e.response.status_code}")
            print(f"Response: {e.response.text}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise

# --- Test Block ---
# You can run this file directly (python github_auth.py) to test it.

if __name__ == "__main__":
    import asyncio
    
    async def main_test():
        print("Attempting to get GitHub App Installation Token...")
        try:
            token = await get_installation_access_token()
            print("\n✅ Success! Got a token.")
            print(f"Token starts with: {token[:8]}...")
            print(f"Token length: {len(token)}")
        except Exception as e:
            print(f"\n❌ Failed to get token.")
            print(e)

    asyncio.run(main_test())