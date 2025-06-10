"""
Trusted Accounts Manager for Project RUGGUARD
Manages the list of trusted accounts and checks trust relationships.
"""

import logging
import requests
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TrustScore:
    """Data class for trust score results."""

    is_vouched: bool
    trust_connections: int
    vouched_by: List[str]


class TrustedAccountsManager:
    """Manages trusted accounts list and trust verification."""

    def __init__(self):
        """Initialize the trusted accounts manager."""
        self.trusted_list_url = (
            "https://raw.githubusercontent.com/devsyrem/turst-list/main/list"
        )
        self.trusted_accounts: Set[str] = set()
        self.last_update = None

        # Load initial trusted accounts
        self.update_trusted_list()

    def update_trusted_list(self) -> bool:
        """
        Update the trusted accounts list from GitHub.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Updating trusted accounts list...")

            response = requests.get(self.trusted_list_url, timeout=10)
            response.raise_for_status()

            # Parse the list (assuming one username per line)
            accounts = set()
            for line in response.text.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):  # Skip empty lines and comments
                    # Remove @ symbol if present
                    username = line.lstrip("@").lower()
                    if username:
                        accounts.add(username)

            self.trusted_accounts = accounts
            logger.info(f"Loaded {len(self.trusted_accounts)} trusted accounts")
            return True

        except Exception as e:
            logger.error(f"Failed to update trusted accounts list: {e}")
            # If we can't update, keep the existing list
            return False

    def is_trusted_account(self, username: str) -> bool:
        """
        Check if an account is in the trusted list.

        Args:
            username: Username to check (without @)

        Returns:
            True if account is trusted, False otherwise
        """
        return username.lower().lstrip("@") in self.trusted_accounts

    def check_trust_score(self, username: str, twitter_api) -> Dict:
        """
        Check trust score based on connections to trusted accounts.

        Args:
            username: Username to check
            twitter_api: TwitterAPIHandler instance

        Returns:
            Dictionary with trust score information
        """
        try:
            logger.info(f"Checking trust score for @{username}")

            # First check if the account itself is trusted
            if self.is_trusted_account(username):
                return {
                    "is_vouched": True,
                    "trust_connections": len(self.trusted_accounts),
                    "vouched_by": ["trusted_list"],
                    "is_on_trusted_list": True,
                }

            # Get user data
            user = twitter_api.get_user_by_username(username)
            if not user:
                logger.warning(f"Could not fetch user data for @{username}")
                return {"is_vouched": False, "trust_connections": 0, "vouched_by": []}

            # Get who this user is following
            following = twitter_api.get_following(user.id, max_results=100)
            if not following:
                logger.info(f"Could not fetch following list for @{username}")
                return {"is_vouched": False, "trust_connections": 0, "vouched_by": []}

            # Check connections to trusted accounts
            trusted_connections = []
            following_usernames = {user.username.lower() for user in following}

            for trusted_account in self.trusted_accounts:
                if trusted_account in following_usernames:
                    trusted_connections.append(trusted_account)

            # Determine if account is vouched
            # An account is "vouched" if followed by at least 2 trusted accounts
            is_vouched = len(trusted_connections) >= 2

            result = {
                "is_vouched": is_vouched,
                "trust_connections": len(trusted_connections),
                "vouched_by": trusted_connections[:5],  # Limit to top 5
                "is_on_trusted_list": False,
            }

            logger.info(
                f"Trust score for @{username}: {len(trusted_connections)} connections, vouched: {is_vouched}"
            )
            return result

        except Exception as e:
            logger.error(f"Error checking trust score for @{username}: {e}")
            return {"is_vouched": False, "trust_connections": 0, "vouched_by": []}

    def get_trusted_accounts_list(self) -> List[str]:
        """
        Get the current list of trusted accounts.

        Returns:
            List of trusted usernames
        """
        return list(self.trusted_accounts)

    def add_trusted_account(self, username: str) -> bool:
        """
        Manually add an account to the trusted list (for testing/admin purposes).

        Args:
            username: Username to add

        Returns:
            True if added successfully
        """
        try:
            clean_username = username.lower().lstrip("@")
            self.trusted_accounts.add(clean_username)
            logger.info(f"Added @{clean_username} to trusted accounts")
            return True
        except Exception as e:
            logger.error(f"Error adding trusted account: {e}")
            return False

    def remove_trusted_account(self, username: str) -> bool:
        """
        Manually remove an account from the trusted list (for testing/admin purposes).

        Args:
            username: Username to remove

        Returns:
            True if removed successfully
        """
        try:
            clean_username = username.lower().lstrip("@")
            if clean_username in self.trusted_accounts:
                self.trusted_accounts.remove(clean_username)
                logger.info(f"Removed @{clean_username} from trusted accounts")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing trusted account: {e}")
            return False

    def get_mutual_trusted_connections(
        self, username1: str, username2: str, twitter_api
    ) -> List[str]:
        """
        Get mutual trusted connections between two users.

        Args:
            username1: First username
            username2: Second username
            twitter_api: TwitterAPIHandler instance

        Returns:
            List of mutual trusted connections
        """
        try:
            # Get trust scores for both users
            trust1 = self.check_trust_score(username1, twitter_api)
            trust2 = self.check_trust_score(username2, twitter_api)

            # Find mutual connections
            connections1 = set(trust1.get("vouched_by", []))
            connections2 = set(trust2.get("vouched_by", []))

            mutual = list(connections1.intersection(connections2))

            logger.info(
                f"Found {len(mutual)} mutual trusted connections between @{username1} and @{username2}"
            )
            return mutual

        except Exception as e:
            logger.error(f"Error getting mutual connections: {e}")
            return []

    def validate_trusted_list_format(self, content: str) -> bool:
        """
        Validate the format of a trusted list.

        Args:
            content: Content to validate

        Returns:
            True if format is valid
        """
        try:
            lines = content.strip().split("\n")
            valid_lines = 0

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Check if it looks like a valid username
                username = line.lstrip("@")
                if username.replace("_", "").replace(".", "").isalnum():
                    valid_lines += 1
                else:
                    logger.warning(f"Invalid username format: {line}")
                    return False

            logger.info(f"Validated trusted list with {valid_lines} valid accounts")
            return valid_lines > 0

        except Exception as e:
            logger.error(f"Error validating trusted list: {e}")
            return False
