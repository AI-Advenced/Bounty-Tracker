"""
Advanced GitHub API service with comprehensive issue and repository tracking
"""
import os
import re
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import httpx
from sqlalchemy.orm import Session
from app.models import Issue, Repository, IssueComment, IssueLabel, RepositoryStats
from app.models.issue import IssueStatus
from app.models.repository import RepositoryType, RepositoryStatus

class GitHubService:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.search_url = f"{self.base_url}/search"
        
        # Rate limiting
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = None
        
        # HTTP client configuration
        self.client_timeout = httpx.Timeout(30.0)
        
        # Bounty detection patterns
        self.bounty_patterns = [
            r"\$([0-9,]+(?:\.[0-9]{2})?)",  # $100, $1,000.00
            r"(\d+)\s*(?:USD|dollars?)",     # 100 USD, 50 dollars
            r"bounty:?\s*\$?([0-9,]+)",      # bounty: $100, bounty 100
            r"reward:?\s*\$?([0-9,]+)",      # reward: $100
            r"prize:?\s*\$?([0-9,]+)",       # prize: $100
        ]
        
        self.logger = logging.getLogger(__name__)
    
    async def get_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "BountyTracker/1.0",
        }
        
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        return headers
    
    async def make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated request to GitHub API with rate limiting"""
        headers = await self.get_headers()
        
        try:
            async with httpx.AsyncClient(timeout=self.client_timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                
                # Update rate limit info
                self.rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
                reset_timestamp = response.headers.get("X-RateLimit-Reset")
                if reset_timestamp:
                    self.rate_limit_reset = datetime.fromtimestamp(int(reset_timestamp))
                
                if response.status_code == 403 and self.rate_limit_remaining == 0:
                    self.logger.warning("GitHub API rate limit exceeded")
                    return None
                
                if response.status_code == 404:
                    self.logger.warning(f"Resource not found: {url}")
                    return None
                
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            self.logger.error(f"Timeout requesting {url}")
            return None
        except Exception as e:
            self.logger.error(f"Error requesting {url}: {e}")
            return None
    
    def extract_bounty_amount(self, text: str) -> int:
        """Extract bounty amount from text (returns amount in cents)"""
        if not text:
            return 0
        
        text = text.lower()
        max_amount = 0
        
        for pattern in self.bounty_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean up the match (remove commas, etc.)
                    amount_str = match.replace(",", "").replace(" ", "")
                    amount = float(amount_str)
                    amount_cents = int(amount * 100)
                    max_amount = max(max_amount, amount_cents)
                except (ValueError, TypeError):
                    continue
        
        return max_amount
    
    def determine_bounty_source(self, text: str) -> Optional[str]:
        """Determine the source of the bounty from text"""
        if not text:
            return None
        
        text = text.lower()
        
        sources = {
            "bountysource": ["bountysource", "bounty source"],
            "gitcoin": ["gitcoin"],
            "algora": ["algora"],
            "console": ["console.dev"],
            "devcash": ["devcash"],
            "github_sponsors": ["github sponsors", "sponsor"],
            "custom": ["bounty", "reward", "prize"]
        }
        
        for source, keywords in sources.items():
            if any(keyword in text for keyword in keywords):
                return source
        
        return None
    
    async def search_bounty_issues(
        self, 
        db: Session,
        query: str = "bounty OR reward OR prize",
        language: str = None,
        min_amount: int = 5000,  # $50 minimum
        per_page: int = 100,
        max_pages: int = 10
    ) -> List[Issue]:
        """Search for issues with bounties"""
        
        search_query = f"{query} in:title,body"
        
        if language:
            search_query += f" language:{language}"
        
        # Add common bounty indicators
        search_query += " ($ OR USD OR dollars)"
        
        params = {
            "q": search_query,
            "sort": "updated",
            "order": "desc",
            "per_page": per_page
        }
        
        new_issues = []
        
        for page in range(1, max_pages + 1):
            if self.rate_limit_remaining < 10:
                self.logger.warning("Approaching GitHub API rate limit, stopping search")
                break
            
            params["page"] = page
            url = f"{self.search_url}/issues"
            
            data = await self.make_request(url, params)
            if not data or "items" not in data:
                break
            
            items = data["items"]
            if not items:
                break
            
            for item in items:
                issue = await self.process_issue_from_search(db, item, min_amount)
                if issue:
                    new_issues.append(issue)
            
            # Add delay to be respectful to GitHub API
            await asyncio.sleep(1)
        
        return new_issues
    
    async def process_issue_from_search(
        self, 
        db: Session, 
        github_data: Dict,
        min_amount: int = 0
    ) -> Optional[Issue]:
        """Process a single issue from GitHub search results"""
        
        github_id = str(github_data["id"])
        
        # Check if issue already exists
        existing_issue = db.query(Issue).filter(Issue.github_id == github_id).first()
        
        # Extract bounty information
        title = github_data.get("title", "")
        body = github_data.get("body", "") or ""
        bounty_amount = self.extract_bounty_amount(f"{title} {body}")
        
        # Skip if bounty amount is below minimum
        if bounty_amount < min_amount:
            return None
        
        # Get or create repository
        repo_data = github_data.get("repository_url", "").split("/")
        if len(repo_data) < 2:
            return None
        
        repo_owner = repo_data[-2]
        repo_name = repo_data[-1]
        repository = await self.get_or_create_repository(db, repo_owner, repo_name)
        
        if not repository:
            return None
        
        # Update existing issue or create new one
        if existing_issue:
            existing_issue.update_from_github(github_data)
            existing_issue.bounty_amount = bounty_amount
            existing_issue.has_bounty = bounty_amount > 0
            existing_issue.bounty_source = self.determine_bounty_source(f"{title} {body}")
            issue = existing_issue
        else:
            # Create new issue
            github_created_at = datetime.fromisoformat(
                github_data["created_at"].replace("Z", "+00:00")
            )
            github_updated_at = datetime.fromisoformat(
                github_data["updated_at"].replace("Z", "+00:00")
            )
            
            issue = Issue(
                github_id=github_id,
                github_number=github_data["number"],
                title=title,
                body=body,
                html_url=github_data["html_url"],
                api_url=github_data["url"],
                repository_id=repository.id,
                repository_full_name=f"{repo_owner}/{repo_name}",
                repository_owner=repo_owner,
                repository_name=repo_name,
                status=IssueStatus.CLOSED if github_data.get("state") == "closed" else IssueStatus.OPEN,
                is_pull_request=github_data.get("pull_request") is not None,
                bounty_amount=bounty_amount,
                has_bounty=bounty_amount > 0,
                bounty_source=self.determine_bounty_source(f"{title} {body}"),
                author_username=github_data["user"]["login"],
                author_avatar_url=github_data["user"]["avatar_url"],
                assignee_username=github_data["assignee"]["login"] if github_data.get("assignee") else None,
                comments_count=github_data.get("comments", 0),
                github_created_at=github_created_at,
                github_updated_at=github_updated_at,
                last_fetched_at=datetime.utcnow(),
                primary_language=repository.primary_language
            )
            
            db.add(issue)
        
        # Process labels
        await self.process_issue_labels(db, issue, github_data.get("labels", []))
        
        try:
            db.commit()
            self.logger.info(f"Processed issue: {issue.title} (${issue.bounty_amount/100:.2f})")
            return issue
        except Exception as e:
            db.rollback()
            self.logger.error(f"Failed to save issue {github_id}: {e}")
            return None
    
    async def get_or_create_repository(
        self, 
        db: Session, 
        owner: str, 
        name: str
    ) -> Optional[Repository]:
        """Get or create repository from GitHub API"""
        
        full_name = f"{owner}/{name}"
        
        # Check if repository already exists
        existing_repo = db.query(Repository).filter(
            Repository.full_name == full_name
        ).first()
        
        if existing_repo:
            # Update repository data if it's old
            if existing_repo.last_fetched_at and \
               (datetime.utcnow() - existing_repo.last_fetched_at).days >= 1:
                await self.update_repository_data(db, existing_repo)
            return existing_repo
        
        # Fetch repository data from GitHub
        url = f"{self.base_url}/repos/{owner}/{name}"
        repo_data = await self.make_request(url)
        
        if not repo_data:
            return None
        
        try:
            github_created_at = datetime.fromisoformat(
                repo_data["created_at"].replace("Z", "+00:00")
            )
            github_updated_at = datetime.fromisoformat(
                repo_data["updated_at"].replace("Z", "+00:00")
            )
            github_pushed_at = None
            if repo_data.get("pushed_at"):
                github_pushed_at = datetime.fromisoformat(
                    repo_data["pushed_at"].replace("Z", "+00:00")
                )
            
            repository = Repository(
                github_id=str(repo_data["id"]),
                full_name=full_name,
                name=name,
                owner=owner,
                description=repo_data.get("description"),
                html_url=repo_data["html_url"],
                clone_url=repo_data["clone_url"],
                ssh_url=repo_data["ssh_url"],
                repository_type=RepositoryType.PRIVATE if repo_data.get("private") else RepositoryType.PUBLIC,
                is_fork=repo_data.get("fork", False),
                is_archived=repo_data.get("archived", False),
                is_disabled=repo_data.get("disabled", False),
                primary_language=repo_data.get("language"),
                stars_count=repo_data.get("stargazers_count", 0),
                forks_count=repo_data.get("forks_count", 0),
                watchers_count=repo_data.get("watchers_count", 0),
                open_issues_count=repo_data.get("open_issues_count", 0),
                size_kb=repo_data.get("size", 0),
                github_created_at=github_created_at,
                github_updated_at=github_updated_at,
                github_pushed_at=github_pushed_at,
                last_fetched_at=datetime.utcnow()
            )
            
            # Set license information
            license_info = repo_data.get("license")
            if license_info:
                repository.license_name = license_info.get("name")
                repository.license_spdx_id = license_info.get("spdx_id")
            
            db.add(repository)
            db.commit()
            
            self.logger.info(f"Created repository: {full_name}")
            return repository
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Failed to create repository {full_name}: {e}")
            return None
    
    async def update_repository_data(self, db: Session, repository: Repository):
        """Update repository data from GitHub API"""
        
        url = f"{self.base_url}/repos/{repository.full_name}"
        repo_data = await self.make_request(url)
        
        if repo_data:
            repository.update_from_github(repo_data)
            
            # Update bounty statistics
            repository.update_bounty_stats(db)
            
            try:
                db.commit()
                self.logger.info(f"Updated repository: {repository.full_name}")
            except Exception as e:
                db.rollback()
                self.logger.error(f"Failed to update repository {repository.full_name}: {e}")
    
    async def process_issue_labels(
        self, 
        db: Session, 
        issue: Issue, 
        labels_data: List[Dict]
    ):
        """Process and associate labels with issue"""
        
        for label_data in labels_data:
            label_name = label_data.get("name", "").lower()
            label_color = label_data.get("color", "cccccc")
            
            # Get or create label
            existing_label = db.query(IssueLabel).filter(
                IssueLabel.name == label_name
            ).first()
            
            if not existing_label:
                label = IssueLabel(
                    name=label_name,
                    color=f"#{label_color}",
                    description=label_data.get("description")
                )
                db.add(label)
            else:
                label = existing_label
            
            # Associate label with issue
            if label not in issue.labels:
                issue.labels.append(label)
    
    async def fetch_issue_comments(
        self, 
        db: Session, 
        issue: Issue
    ) -> List[IssueComment]:
        """Fetch comments for an issue"""
        
        url = f"{self.base_url}/repos/{issue.repository_full_name}/issues/{issue.github_number}/comments"
        comments_data = await self.make_request(url)
        
        if not comments_data:
            return []
        
        comments = []
        
        for comment_data in comments_data:
            github_id = str(comment_data["id"])
            
            # Check if comment already exists
            existing_comment = db.query(IssueComment).filter(
                IssueComment.github_id == github_id
            ).first()
            
            if existing_comment:
                continue
            
            github_created_at = datetime.fromisoformat(
                comment_data["created_at"].replace("Z", "+00:00")
            )
            github_updated_at = datetime.fromisoformat(
                comment_data["updated_at"].replace("Z", "+00:00")
            )
            
            comment = IssueComment(
                github_id=github_id,
                issue_id=issue.id,
                body=comment_data.get("body", ""),
                html_url=comment_data["html_url"],
                author_username=comment_data["user"]["login"],
                author_avatar_url=comment_data["user"]["avatar_url"],
                author_association=comment_data.get("author_association"),
                github_created_at=github_created_at,
                github_updated_at=github_updated_at
            )
            
            db.add(comment)
            comments.append(comment)
        
        try:
            db.commit()
            self.logger.info(f"Fetched {len(comments)} new comments for issue {issue.github_number}")
        except Exception as e:
            db.rollback()
            self.logger.error(f"Failed to save comments for issue {issue.github_number}: {e}")
        
        return comments
    
    async def get_trending_repositories(
        self, 
        db: Session,
        language: str = None,
        timeframe: str = "week"  # "day", "week", "month"
    ) -> List[Repository]:
        """Get trending repositories with potential bounties"""
        
        # Build search query for trending repos
        date_ranges = {
            "day": datetime.utcnow() - timedelta(days=1),
            "week": datetime.utcnow() - timedelta(weeks=1), 
            "month": datetime.utcnow() - timedelta(days=30)
        }
        
        since_date = date_ranges.get(timeframe, date_ranges["week"])
        date_str = since_date.strftime("%Y-%m-%d")
        
        search_query = f"created:>{date_str} stars:>10"
        
        if language:
            search_query += f" language:{language}"
        
        params = {
            "q": search_query,
            "sort": "stars",
            "order": "desc",
            "per_page": 50
        }
        
        url = f"{self.search_url}/repositories"
        data = await self.make_request(url, params)
        
        if not data or "items" not in data:
            return []
        
        repositories = []
        
        for repo_data in data["items"]:
            repository = await self.get_or_create_repository(
                db, 
                repo_data["owner"]["login"], 
                repo_data["name"]
            )
            
            if repository:
                repositories.append(repository)
        
        return repositories
    
    def get_rate_limit_info(self) -> Dict:
        """Get current rate limit information"""
        return {
            "remaining": self.rate_limit_remaining,
            "reset_at": self.rate_limit_reset.isoformat() if self.rate_limit_reset else None,
            "authenticated": bool(self.github_token)
        }