"""
Twitter API Handler for Project RUGGUARD
Handles all interactions with the X (Twitter) API with comprehensive caching.
"""

import os
import tweepy
import logging
import hashlib
from dataclasses import dataclass
from typing import List, Dict, Optional, Set, Any
from datetime import datetime

from .cache import JSONCache

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class TweetData:
    """Data class for tweet information."""

    id: str
    text: str
    author_id: str
    created_at: datetime
    public_metrics: Dict[str, int]
    in_reply_to_tweet_id: Optional[str] = None


@dataclass
class UserData:
    """Data class for user information."""

    id: str
    username: str
    name: str
    description: str
    created_at: datetime
    public_metrics: Dict[str, int]
    verified: bool = False
    profile_image_url: Optional[str] = None


class TwitterAPIHandler:
    """Handles all Twitter API interactions with caching."""

    def __init__(self) -> None:
        """Initialize Twitter API client."""
        self.bearer_token: str | None = os.getenv("X_BEARER_TOKEN")
        self.api_key: str | None = os.getenv("X_API_KEY")
        self.api_secret: str | None = os.getenv("X_API_SECRET")
        self.access_token: str | None = os.getenv("X_ACCESS_TOKEN")
        self.access_token_secret: str | None = os.getenv("X_ACCESS_TOKEN_SECRET")

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
        query_hash: str = hashlib.md5(query.encode()).hexdigest()
        cache_key: str = f"search_{query_hash}_{max_results}"

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
                    "conversation_id",
                    "referenced_tweets"
                ],
                expansions=["referenced_tweets.id", "author_id"]
            )

            if not response.data:
                return []

            # Create a lookup for referenced tweets
            referenced_tweets = {}
            if hasattr(response, 'includes') and hasattr(response.includes, 'tweets'):
                for tweet in response.includes.tweets:
                    referenced_tweets[tweet.id] = tweet

            tweets = []
            for tweet in response.data:
                # Get the actual reply tweet ID if this is a reply
                in_reply_to_tweet_id = None
                if hasattr(tweet, 'referenced_tweets') and tweet.referenced_tweets:
                    for ref in tweet.referenced_tweets:
                        if ref.type == 'replied_to':
                            in_reply_to_tweet_id = ref.id
                            break

                tweet_data: Dict[str, Any] = {
                    "id": tweet.id,
                    "text": tweet.text,
                    "author_id": tweet.author_id,
                    "created_at": tweet.created_at.isoformat()
                    if hasattr(tweet.created_at, "isoformat")
                    else str(tweet.created_at),
                    "public_metrics": tweet.public_metrics or {},
                    "in_reply_to_tweet_id": in_reply_to_tweet_id
                }
                tweets.append(tweet_data)

            self.cache.set(cache_key, tweets, ttl=300)
            return [
                TweetData(
                    id=t["id"],
                    text=t["text"],
                    author_id=t["author_id"],
                    created_at=datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")),
                    public_metrics=t["public_metrics"],
                    in_reply_to_tweet_id=t["in_reply_to_tweet_id"]
                )
                for t in tweets
            ]

        except Exception as e:
            logger.error(f"Error searching tweets: {e}")
            return []

    def get_tweet(self, tweet_id: str) -> Optional[TweetData]:
        """Get a specific tweet by ID."""
        cache_key: str = f"tweet_{tweet_id}"
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
                    "conversation_id",
                    "referenced_tweets",
                    "in_reply_to_user_id"
                ],
                expansions=["referenced_tweets.id", "author_id"]
            )

            if not response.data:
                logger.warning(f"No data returned for tweet {tweet_id}")
                return None

            tweet = response.data
            
            # Get the actual reply tweet ID if this is a reply
            in_reply_to_tweet_id = None
            if hasattr(tweet, 'referenced_tweets') and tweet.referenced_tweets:
                for ref in tweet.referenced_tweets:
                    if ref.type == 'replied_to':
                        in_reply_to_tweet_id = ref.id
                        break

            tweet_data: Dict [str, Any] = {
                "id": tweet.id,
                "text": tweet.text,
                "author_id": tweet.author_id,
                "created_at": tweet.created_at.isoformat()
                if hasattr(tweet.created_at, "isoformat")
                else str(tweet.created_at),
                "public_metrics": tweet.public_metrics or {},
                "in_reply_to_tweet_id": in_reply_to_tweet_id
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
                in_reply_to_tweet_id=tweet_data["in_reply_to_tweet_id"]
            )

        except tweepy.TweepyException as e:
            logger.error(f"Twitter API error fetching tweet {tweet_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching tweet {tweet_id}: {e}")
            return None

    def get_user(self, user_id: str) -> Optional[UserData]:
        """Get user information by user ID."""
        cache_key: str = f"user_id_{user_id}"
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
            user_data: Dict[str, Any] = {
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
        cache_key: str = f"user_name_{username.lower()}"
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
            user_data: Dict [str, Any] = {
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
                tweet_data: Dict[str, Any] = {
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
                user_data: Dict[str, Any] = {
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
