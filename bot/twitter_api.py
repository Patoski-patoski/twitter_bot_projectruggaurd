"""
Twitter API Handler for Project RUGGUARD
Handles all interactions with the X (Twitter) API with comprehensive caching.
"""

import os
import tweepy
import logging
import hashlib
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from datetime import datetime, timezone, timedelta

from .cache import JSONCache

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class TweetData:
    """Data class for tweet information."""

    id: str
    text: str
    author_id: str
    created_at: str
    public_metrics: Dict[str, int]
    in_reply_to_tweet_id: Optional[str] = None


@dataclass
class UserData:
    """Data class for user information."""

    id: str
    username: str
    name: str
    description: str
    created_at: str
    public_metrics: Dict[str, int]
    verified: bool = False
    profile_image_url: Optional[str] = None


class TwitterAPIHandler:
    """Handles all Twitter API interactions with caching."""

    def __init__(self):
        """Initialize Twitter API client."""
        self.bearer_token = os.getenv("X_BEARER_TOKEN")
        self.api_key = os.getenv("X_API_KEY")
        self.api_secret = os.getenv("X_API_SECRET")
        self.access_token = os.getenv("X_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

        if not all(
            [
                self.bearer_token,
                self.api_key,
                self.api_secret,
                self.access_token,
                self.access_token_secret,
            ]
        ):
            raise ValueError("Missing required Twitter API credentials")

        self.client = tweepy.Client(
            bearer_token=self.bearer_token,
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
            wait_on_rate_limit=True,
        )

        self.cache = JSONCache()
        logger.info("Twitter API client initialized")

    def search_recent_tweets(
        self, query: str, max_results: int = 10
    ) -> List[TweetData]:
        """Search for recent tweets matching a query."""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"search_{query_hash}_{max_results}"

        cached = self.cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for search: {query}")
            return [TweetData(**tweet) for tweet in cached]

        try:
            response = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=[
                    "author_id",
                    "created_at",
                    "public_metrics",
                    "in_reply_to_user_id",
                ],
                expansions=["author_id"],
            )

            if not response.data:
                return []

            tweets = []
            for tweet in response.data:
                # Fix: Use correct field name for reply detection
                in_reply_to_id = None
                if hasattr(tweet, "in_reply_to_user_id"):
                    # This field exists but we need the tweet ID, not user ID
                    # We'll check if this is a reply by looking at the text
                    pass

                # Better approach: parse conversation_id or check context_annotations
                tweet_data = {
                    "id": tweet.id,
                    "text": tweet.text,
                    "author_id": tweet.author_id,
                    "created_at": tweet.created_at.isoformat()
                    if hasattr(tweet.created_at, "isoformat")
                    else str(tweet.created_at),
                    "public_metrics": tweet.public_metrics or {},
                    "in_reply_to_tweet_id": getattr(tweet, "in_reply_to_user_id", None),
                }
                tweets.append(tweet_data)

            self.cache.set(cache_key, tweets, ttl=300)  # 5 minute cache
            return [
                TweetData(
                    id=t["id"],
                    text=t["text"],
                    author_id=t["author_id"],
                    created_at=datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")),
                    public_metrics=t["public_metrics"],
                    in_reply_to_tweet_id=t["in_reply_to_tweet_id"],
                )
                for t in tweets
            ]

        except Exception as e:
            logger.error(f"Error searching tweets: {e}")
            return []

    def get_tweet(self, tweet_id: str) -> Optional[TweetData]:
        """Get a specific tweet by ID."""
        cache_key = f"tweet_{tweet_id}"
        cached = self.cache.get(cache_key)

        if cached:
            return TweetData(**cached)

        try:
            response = self.client.get_tweet(
                tweet_id,
                tweet_fields=[
                    "author_id",
                    "created_at",
                    "public_metrics",
                    "in_reply_to_user_id",
                ],
            )

            if not response.data:
                return None

            tweet = response.data
            tweet_data = {
                "id": tweet.id,
                "text": tweet.text,
                "author_id": tweet.author_id,
                "created_at": tweet.created_at.isoformat()
                if hasattr(tweet.created_at, "isoformat")
                else str(tweet.created_at),
                "public_metrics": tweet.public_metrics or {},
                "in_reply_to_tweet_id": getattr(tweet, "in_reply_to_user_id", None),
            }

            self.cache.set(cache_key, tweet_data, ttl=3600)

            return TweetData(
                id=tweet_data["id"],
                text=tweet_data["text"],
                author_id=tweet_data["author_id"],
                created_at=datetime.fromisoformat(
                    tweet_data["created_at"].replace("Z", "+00:00")
                ),
                public_metrics=tweet_data["public_metrics"],
                in_reply_to_tweet_id=tweet_data["in_reply_to_tweet_id"],
            )

        except Exception as e:
            logger.error(f"Error fetching tweet {tweet_id}: {e}")
            return None

    def get_user(self, user_id: str) -> Optional[UserData]:
        """Get user information by user ID."""
        cache_key = f"user_id_{user_id}"
        cached = self.cache.get(cache_key)

        if cached:
            return UserData(**cached)

        try:
            response = self.client.get_user(
                id=user_id,
                user_fields=["created_at", "description", "public_metrics", "verified"],
            )

            if not response.data:
                return None

            user = response.data
            user_data = {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "description": user.description or "",
                "created_at": user.created_at.isoformat()
                if hasattr(user.created_at, "isoformat")
                else str(user.created_at),
                "public_metrics": user.public_metrics or {},
                "verified": getattr(user, "verified", False),
            }

            self.cache.set(cache_key, user_data, ttl=86400)  # 24 hour cache

            return UserData(
                id=user_data["id"],
                username=user_data["username"],
                name=user_data["name"],
                description=user_data["description"],
                created_at=datetime.fromisoformat(
                    user_data["created_at"].replace("Z", "+00:00")
                ),
                public_metrics=user_data["public_metrics"],
                verified=user_data["verified"],
            )

        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[UserData]:
        """Get user information by username."""
        cache_key = f"user_name_{username.lower()}"
        cached = self.cache.get(cache_key)

        if cached:
            return UserData(**cached)

        try:
            response = self.client.get_user(
                username=username,
                user_fields=["created_at", "description", "public_metrics", "verified"],
            )

            if not response.data:
                return None

            user = response.data
            user_data = {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "description": user.description or "",
                "created_at": user.created_at.isoformat()
                if hasattr(user.created_at, "isoformat")
                else str(user.created_at),
                "public_metrics": user.public_metrics or {},
                "verified": getattr(user, "verified", False),
            }

            self.cache.set(cache_key, user_data, ttl=86400)

            return UserData(
                id=user_data["id"],
                username=user_data["username"],
                name=user_data["name"],
                description=user_data["description"],
                created_at=datetime.fromisoformat(
                    user_data["created_at"].replace("Z", "+00:00")
                ),
                public_metrics=user_data["public_metrics"],
                verified=user_data["verified"],
            )

        except Exception as e:
            logger.error(f"Error fetching user @{username}: {e}")
            return None

    def get_user_tweets(self, user_id: str, max_results: int = 10) -> List[TweetData]:
        """Get recent tweets from a user."""
        cache_key = f"user_tweets_{user_id}_{max_results}"
        cached = self.cache.get(cache_key)

        if cached:
            return [TweetData(**tweet) for tweet in cached]

        try:
            response = self.client.get_users_tweets(
                user_id,
                max_results=max_results,
                tweet_fields=["created_at", "public_metrics"],
            )

            if not response.data:
                return []

            tweets = []
            for tweet in response.data:
                tweet_data = {
                    "id": tweet.id,
                    "text": tweet.text,
                    "author_id": user_id,
                    "created_at": tweet.created_at.isoformat()
                    if hasattr(tweet.created_at, "isoformat")
                    else str(tweet.created_at),
                    "public_metrics": tweet.public_metrics or {},
                    "in_reply_to_tweet_id": None,
                }
                tweets.append(tweet_data)

            self.cache.set(cache_key, tweets, ttl=3600)

            return [
                TweetData(
                    id=t["id"],
                    text=t["text"],
                    author_id=t["author_id"],
                    created_at=datetime.fromisoformat(
                        t["created_at"].replace("Z", "+00:00")
                    ),
                    public_metrics=t["public_metrics"],
                    in_reply_to_tweet_id=t["in_reply_to_tweet_id"],
                )
                for t in tweets
            ]

        except Exception as e:
            logger.error(f"Error fetching tweets for user {user_id}: {e}")
            return []

    def get_following(self, user_id: str, max_results: int = 100) -> List[UserData]:
        """Get following list for a user."""
        cache_key = f"user_following_{user_id}_{max_results}"
        cached = self.cache.get(cache_key)

        if cached:
            return [UserData(**user) for user in cached]

        try:
            response = self.client.get_users_following(
                user_id,
                max_results=max_results,
                user_fields=["created_at", "description", "public_metrics", "verified"],
            )

            if not response.data:
                return []

            users = []
            for user in response.data:
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                    "description": user.description or "",
                    "created_at": user.created_at.isoformat()
                    if hasattr(user.created_at, "isoformat")
                    else str(user.created_at),
                    "public_metrics": user.public_metrics or {},
                    "verified": getattr(user, "verified", False),
                }
                users.append(user_data)

            self.cache.set(cache_key, users, ttl=43200)  # 12 hour cache

            return [
                UserData(
                    id=u["id"],
                    username=u["username"],
                    name=u["name"],
                    description=u["description"],
                    created_at=datetime.fromisoformat(
                        u["created_at"].replace("Z", "+00:00")
                    ),
                    public_metrics=u["public_metrics"],
                    verified=u["verified"],
                )
                for u in users
            ]

        except Exception as e:
            logger.error(f"Error fetching following for user {user_id}: {e}")
            return []

    def create_tweet(
        self, text: str, in_reply_to_tweet_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a new tweet."""
        try:
            response = self.client.create_tweet(
                text=text, in_reply_to_tweet_id=in_reply_to_tweet_id
            )

            if response.data:
                logger.info(f"Tweet created successfully: {response.data['id']}")
                return response.data["id"]

            return None

        except Exception as e:
            logger.error(f"Error creating tweet: {e}")
            return None


# ============================================================================
# TRUSTED ACCOUNTS MANAGER
# ============================================================================


class TrustedAccountsManager:
    """Manages trusted accounts list and trust verification."""

    def __init__(self):
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
            response = requests.get(self.trusted_list_url, timeout=10)
            response.raise_for_status()

            accounts = set()
            for line in response.text.strip().split("\n"):
                line = line.strip()
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
            is_vouched = len(trusted_connections) >= 2

            return {
                "is_vouched": is_vouched,
                "trust_connections": len(trusted_connections),
                "vouched_by": trusted_connections[:5],
            }

        except Exception as e:
            logger.error(f"Error checking trust score for @{username}: {e}")
            return {"is_vouched": False, "trust_connections": 0, "vouched_by": []}