"""
GitHub Service - Fetches public repos and portfolio data.
"""
import os
import base64
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API = "https://api.github.com"


def get_headers() -> Dict:
    """Get request headers with optional auth."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    else:
        print("⚠️ No GITHUB_TOKEN. Rate limit: 60 requests/hour")
    return headers


def fetch_user_repos(username: str, limit: int = 10) -> List[Dict]:
    """
    Fetch public repositories for a GitHub user.
    """
    url = f"{GITHUB_API}/users/{username}/repos"
    params = {
        "sort": "updated",
        "direction": "desc",
        "per_page": limit,
        "type": "public"
    }
    
    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            print("⚠️ GitHub rate limit reached")
        elif response.status_code == 404:
            print(f"⚠️ GitHub user '{username}' not found")
        return []
    except Exception as e:
        print(f"❌ GitHub API error: {e}")
        return []


def fetch_file_content(username: str, repo: str, path: str) -> Optional[str]:
    """
    Fetch a specific file from a repository.
    """
    url = f"{GITHUB_API}/repos/{username}/{repo}/contents/{path}"
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'content' in data:
                return base64.b64decode(data['content']).decode('utf-8')
        return None
    except Exception as e:
        print(f"⚠️ Failed to fetch {repo}/{path}: {e}")
        return None


def detect_tech_stack(username: str, repo_name: str, language: str) -> List[str]:
    """
    Detect technologies used in a repository by checking dependency files.
    """
    tech_files = {
        "Python": ["requirements.txt", "pyproject.toml", "Pipfile", "setup.py"],
        "JavaScript": ["package.json"],
        "TypeScript": ["package.json"],
        "Java": ["pom.xml", "build.gradle"],
        "Go": ["go.mod"],
        "Rust": ["Cargo.toml"],
    }
    
    files_to_check = tech_files.get(language, [])
    files_to_check.extend(["Dockerfile", "docker-compose.yml", ".github/workflows"])
    
    tech_stack = [language] if language else []
    
    for file_path in files_to_check:
        content = fetch_file_content(username, repo_name, file_path)
        if content:
            # Parse technologies from file content
            tech_stack.extend(extract_dependencies(file_path, content))
    
    return list(set(tech_stack))


def extract_dependencies(filename: str, content: str) -> List[str]:
    """
    Extract dependency names from various config files.
    """
    deps = []
    
    if filename == "requirements.txt":
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                pkg = line.split("==")[0].split(">=")[0].split("[")[0].strip()
                if pkg:
                    deps.append(pkg)
    
    elif filename == "package.json":
        import json
        try:
            pkg = json.loads(content)
            deps.extend(pkg.get("dependencies", {}).keys())
            deps.extend(pkg.get("devDependencies", {}).keys())
        except:
            pass
    
    elif filename == "pyproject.toml":
        # Simple extraction
        if "fastapi" in content.lower():
            deps.append("FastAPI")
        if "django" in content.lower():
            deps.append("Django")
        if "flask" in content.lower():
            deps.append("Flask")
    
    elif filename == "Dockerfile":
        deps.append("Docker")
    
    elif ".github/workflows" in filename:
        deps.append("GitHub Actions")
    
    return deps


def fetch_portfolio_data(username: str) -> Dict:
    """
    Fetch comprehensive portfolio data for a GitHub user.
    
    Returns:
        {
            "username": "...",
            "profile": {...},
            "repositories": [...],
            "tech_stack": [...],
            "languages": {...}
        }
    """
    if not username:
        return {"error": "No GitHub username provided"}
    
    print(f"🔍 Fetching GitHub data for {username}...")
    
    # Fetch user profile
    profile_url = f"{GITHUB_API}/users/{username}"
    try:
        profile_resp = requests.get(profile_url, headers=get_headers(), timeout=10)
        profile = profile_resp.json() if profile_resp.status_code == 200 else {}
    except:
        profile = {}
    
    # Fetch repositories
    repos = fetch_user_repos(username, limit=15)
    
    # Process repositories
    repo_data = []
    all_tech = set()
    languages = {}
    
    for repo in repos:
        repo_name = repo.get("name")
        language = repo.get("language")
        
        if language:
            languages[language] = languages.get(language, 0) + 1
        
        # Get tech stack for top repos
        if len(repo_data) < 5 and not repo.get("fork"):
            tech_stack = detect_tech_stack(username, repo_name, language)
            all_tech.update(tech_stack)
        else:
            tech_stack = [language] if language else []
        
        repo_data.append({
            "name": repo_name,
            "description": repo.get("description"),
            "url": repo.get("html_url"),
            "language": language,
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "tech_stack": tech_stack,
            "updated_at": repo.get("updated_at")
        })
    
    result = {
        "username": username,
        "profile": {
            "name": profile.get("name"),
            "bio": profile.get("bio"),
            "company": profile.get("company"),
            "location": profile.get("location"),
            "blog": profile.get("blog"),
            "public_repos": profile.get("public_repos", 0),
            "followers": profile.get("followers", 0)
        },
        "repositories": repo_data,
        "tech_stack": list(all_tech),
        "languages": languages
    }
    
    print(f"✅ Found {len(repos)} repos, {len(all_tech)} technologies")
    return result


# ============================================
# GITHUB SERVICE CLASS
# ============================================

class GitHubService:
    """
    Service class for GitHub operations.
    Provides portfolio fetching and repository analysis.
    """
    
    def __init__(self, username: str = None):
        """Initialize with optional username."""
        self.username = username
        self.cached_portfolio: Optional[Dict] = None
    
    def set_username(self, username: str):
        """Set or update the GitHub username."""
        self.username = username
        self.cached_portfolio = None  # Clear cache
    
    def fetch_portfolio(self, force_refresh: bool = False) -> Dict:
        """
        Fetch portfolio data for the user.
        
        Args:
            force_refresh: Whether to bypass cache
            
        Returns:
            Portfolio data dictionary
        """
        if not self.username:
            return {"error": "No GitHub username set"}
        
        if self.cached_portfolio and not force_refresh:
            return self.cached_portfolio
        
        self.cached_portfolio = fetch_portfolio_data(self.username)
        return self.cached_portfolio
    
    def get_repos(self, limit: int = 10) -> List[Dict]:
        """Fetch user repositories."""
        if not self.username:
            return []
        return fetch_user_repos(self.username, limit)
    
    def get_file(self, repo: str, path: str) -> Optional[str]:
        """Fetch a file from a repository."""
        if not self.username:
            return None
        return fetch_file_content(self.username, repo, path)
    
    def get_tech_stack(self) -> List[str]:
        """Get aggregated tech stack from portfolio."""
        portfolio = self.fetch_portfolio()
        return portfolio.get("tech_stack", [])
