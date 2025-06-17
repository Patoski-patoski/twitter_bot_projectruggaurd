# trusted_accounts.py
"""
Trusted Accounts Manager for Project RUGGUARD
Manages the list of trusted accounts and checks trust relationships.
"""

import logging
import requests
from typing import Dict, List, Set, Any
from dataclasses import dataclass
from bot.cache import JSONCache

logger: logging.Logger = logging.getLogger(__name__)

@dataclass
class TrustScore:
    """Data class for trust score results."""

    is_vouched: bool
    trust_connections: int
    vouched_by: List[str]


class TrustedAccountsManager:
    """Manages trusted accounts list and trust verification."""

    def __init__(self) -> None:
        """Initialize the trusted accounts manager."""
        self.trusted_list_url = (
            "https://raw.githubusercontent.com/devsyrem/turst-list/main/list"
        )
        self.trusted_accounts: Set[str] = set()
        self.cache = JSONCache(cache_dir="trusted_cache")
        self.update_trusted_list()

    def update_trusted_list(self) -> bool:
        """Update the trusted accounts list from GitHub."""
        cache_key = "trusted_list"
        cached = self.cache.get(cache_key)

        if cached and isinstance(cached, list):
            self.trusted_accounts = set(cached)
            logger.info(
                f"Loaded {len(self.trusted_accounts)} trusted accounts from cache"
            )
            return True

        try:
            logger.info("Updating trusted accounts list...")
            response: requests.Response = requests.get(self.trusted_list_url, timeout=10)
            response.raise_for_status()

            accounts = set()
            for line in response.text.strip().split("\n"):
                line: str = line.strip()
                if line and not line.startswith("#"):
                    username = line.split()[0].lstrip("@").lower()
                    if (
                        username
                        and username.replace("_", "").replace(".", "").isalnum()
                    ):
                        accounts.add(username)

            self.trusted_accounts = accounts
            self.cache.set(cache_key, list(accounts), ttl=86400)
            logger.info(f"Loaded {len(self.trusted_accounts)} trusted accounts")
            return True

        except Exception as e:
            logger.error(f"Failed to update trusted accounts list: {e}")
            return False

    def is_trusted_account(self, username: str) -> bool:
        """Check if an account is in the trusted list."""
        return username.lower().lstrip("@") in self.trusted_accounts

    def check_trust_score(self, username: str, twitter_api) -> Dict:
        """Check trust score based on connections to trusted accounts."""
        try:
            # First check if the account itself is trusted
            if self.is_trusted_account(username):
                return {
                    "is_vouched": True,
                    "trust_connections": len(self.trusted_accounts),
                    "vouched_by": ["trusted_list"],
                }

            # Get user data
            user = twitter_api.get_user_by_username(username)
            if not user:
                return {"is_vouched": False, "trust_connections": 0, "vouched_by": []}

            # Get who this user is following
            following = twitter_api.get_following(user.id, max_results=100)
            if not following:
                return {"is_vouched": False, "trust_connections": 0, "vouched_by": []}

            # Check connections to trusted accounts
            trusted_connections = []
            following_usernames = {user.username.lower() for user in following}

            for trusted_account in self.trusted_accounts:
                if trusted_account in following_usernames:
                    trusted_connections.append(trusted_account)

            # An account is "vouched" if followed by at least 2 trusted accounts
            is_vouched: bool = len(trusted_connections) >= 2

            return {
                "is_vouched": is_vouched,
                "trust_connections": len(trusted_connections),
                "vouched_by": trusted_connections[:5],
            }

        except Exception as e:
            logger.error(f"Error checking trust score for @{username}: {e}")
            return {"is_vouched": False, "trust_connections": 0, "vouched_by": []}