import httpx
import base64
from github_auth import get_installation_access_token
from typing import Dict, List, Any
import asyncio

# Base url
GITHUB_API_URL = "https://api.github.com"

# --- Private Helper Function ---

async def _get_auth_headers() -> Dict[str, str]:
    """
    Generates the authentication headers needed for GitHub API calls.
    """
    try:
        # Get our 1-hour installation access token
        token = await get_installation_access_token()
        
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }
    except Exception as e:
        print(f"Error getting installation token: {e}")
        raise



# Fetcher functions
async def fetch_repo_details(repo_name: str) -> Dict[str, Any]:

    # Fetches the main repository data (stars, forks, description, etc.)
    print(f"Fetching repo details for: {repo_name}")
    url = f"{GITHUB_API_URL}/repos/{repo_name}"
    headers = await _get_auth_headers()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()  
            return response.json()
        
        except httpx.HTTPStatusError as e:
            print(f"GitHub API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise

async def fetch_contributors_list(repo_name: str) -> List[Dict[str, Any]]:

    # Fetches the list of contributors, sorted by commit count.

    print(f"Fetching contributors for: {repo_name}")
    url = f"{GITHUB_API_URL}/repos/{repo_name}/contributors"
    headers = await _get_auth_headers()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            return [] 
        except Exception:
            return []

async def fetch_all_issues(repo_name: str) -> List[Dict[str, Any]]:
    
    # Fetches all open and closed issues for the repo.

    print(f"Fetching all issues for: {repo_name}")
    # state=all gets both open and closed issues
    url = f"{GITHUB_API_URL}/repos/{repo_name}/issues?state=all&per_page=100"
    headers = await _get_auth_headers()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            return []
        except Exception:
            return []

async def fetch_commit_activity(repo_name: str) -> List[Dict[str, Any]]:
    
    # Fetches the last year of commit activity (weekly summary).
    
    print(f"Fetching commit activity for: {repo_name}")
    url = f"{GITHUB_API_URL}/repos/{repo_name}/stats/commit_activity"
    headers = await _get_auth_headers()
    
    async with httpx.AsyncClient() as client:
        try:
            # The stats API can sometimes take a moment
            # We'll set a longer timeout
            response = await client.get(url, headers=headers, timeout=20.0)
            
            # This API returns 202 if it's still calculating stats
            if response.status_code == 202:
                print("Stats are being calculated, retrying...")
                await asyncio.sleep(2) # Wait 2 seconds
                response = await client.get(url, headers=headers, timeout=20.0)
                
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            return []
        except Exception:
            return []

async def fetch_repo_root_files(repo_name: str) -> List[Dict[str, Any]]:
    # Fetches the list of files/dirs in the root of the repo.
   
    print(f"Fetching file list for: {repo_name}")
    url = f"{GITHUB_API_URL}/repos/{repo_name}/contents/"
    headers = await _get_auth_headers()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            return []
        except Exception:
            return []

async def fetch_file_content(repo_name: str, file_path: str) -> str:
    
    # Fetches the text content of a single file.

    print(f"Fetching content for: {file_path}")
    url = f"{GITHUB_API_URL}/repos/{repo_name}/contents/{file_path}"
    headers = await _get_auth_headers()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Content is base64 encoded
            if data['encoding'] == 'base64':
                content = base64.b64decode(data['content']).decode('utf-8')
                return content
            return ""
        except httpx.HTTPStatusError:
            return "" # Return empty string on failure
        except Exception:
            return ""