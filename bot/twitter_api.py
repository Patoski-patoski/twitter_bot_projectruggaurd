"""
Twitter API Handler for Project RUGGUARD
Handles all interactions with the X (Twitter) API with comprehensive caching.
"""

import os
import tweepy
import logging
import hashlib
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta

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
    """Handles all Twitter API interactions with comprehensive caching."""

    def __init__(self):
        """Initialize Twitter API client with caching."""
        # Load API credentials from environment
        self.bearer_token = os.getenv("X_BEARER_TOKEN")
        self.api_key = os.getenv("X_API_KEY")
        self.api_secret = os.getenv("X_API_SECRET")
        self.access_token = os.getenv("X_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

        # Initialize cache with specific TTL configurations
        self.cache = JSONCache()
        self.cache_ttl = {
            "user": 86400,  # 24 hours for user profiles
            "tweets": 3600,  # 1 hour for tweets
            "following": 43200,  # 12 hours for following lists
            "search": 600,  # 10 minutes for search results
        }

        # Validate credentials
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

        # Initialize Tweepy client
        self.client = tweepy.Client(
            bearer_token=self.bearer_token,
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
            wait_on_rate_limit=True,
        )

        logger.info("Twitter API client initialized with caching")

    def clear_user_cache(self, user_id: str) -> None:
        """
        Clear all cache entries for a specific user.

        Args:
            user_id: The user ID to clear cache for
        """
        cache_keys = [
            f"user_id_{user_id}",
            f"user_tweets_{user_id}_*",
            f"user_following_{user_id}_*",
        ]

        for key in cache_keys:
            if "*" in key:
                # Handle wildcard keys (would need cache backend support)
                logger.warning("Wildcard cache clearing not fully implemented")
            else:
                self.cache.clear(key)

        logger.info(f"Cleared cache for user {user_id}")

   
   
    
    def search_recent_tweets(self, query: str, max_results: int = 10) -> List[TweetData]:
        """
        Search for recent tweets matching a query with caching.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of TweetData objects
        """
        
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"search_{query_hash}_{max_results}"
        
        try:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for search: {query}")
                # Convert string timestamps back to datetime
                for tweet in cached:
                    tweet['created_at'] = datetime.fromisoformat(tweet['created_at'])
                return [TweetData(**tweet) for tweet in cached]
            
            logger.debug(f"Cache miss for search: {query}")
        
            response = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=["author_id", "created_at", "public_metrics", "in_reply_to_user_id"],
                expansions=["author_id"],
            )

            if not response.data:
                return []
            
            else:
                print("Response data\n\n", response.data)

            tweets = []
            for tweet in response.data:
                tweet_data = {
                'id': tweet.id,
                'text': tweet.text,
                'author_id': tweet.author_id,
                'created_at': tweet.created_at,
                'public_metrics': tweet.public_metrics,
                'in_reply_to_tweet_id': getattr(tweet, "in_reply_to_user_id", None)
            }
            tweets.append(tweet_data)

            self.cache.set(cache_key, tweets, ttl=self.cache_ttl['search'])
        
            # Convert back to TweetData objects for return
            return [TweetData(**t) for t in tweets]

        except Exception as e:
            logger.error(f"Error in search_recent_tweets: {str(e)}")
            return []
     

    def get_tweet(self, tweet_id: str) -> Optional[TweetData]:
        """
        Get a specific tweet by ID with caching.

        Args:
            tweet_id: ID of the tweet to fetch

        Returns:
            TweetData object or None if not found
        """
        cache_key = f"tweet_{tweet_id}"
        cached = self.cache.get(cache_key)

        if cached:
            logger.debug(f"Cache hit for tweet {tweet_id}")
            return TweetData(**cached)

        logger.debug(f"Cache miss for tweet {tweet_id}")

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
            tweet_data = TweetData(
                id=tweet.id,
                text=tweet.text,
                author_id=tweet.author_id,
                created_at=tweet.created_at,
                public_metrics=tweet.public_metrics,
                in_reply_to_tweet_id=getattr(tweet, "in_reply_to_user_id", None),
            )

            # Cache for 1 hour (tweets don't change often)
            self.cache.set(cache_key, tweet_data.__dict__, ttl=self.cache_ttl["tweets"])
            return tweet_data

        except tweepy.TweepyException as e:
            logger.error(f"Error fetching tweet {tweet_id}: {e}")
        return None

    def get_user(self, user_id: str) -> Optional[UserData]:
        """
        Get user information by user ID with caching.

        Args:
            user_id: ID of the user to fetch

        Returns:
            UserData object or None if not found
        """
        cache_key = f"user_id_{user_id}"
        cached = self.cache.get(cache_key)

        if cached:
            logger.debug(f"Cache hit for user ID {user_id}")
            return UserData(**cached)

        logger.debug(f"Cache miss for user ID {user_id}")

        try:
            response = self.client.get_user(
            id=user_id,
                user_fields=[
                    "created_at",
                    "description",
                    "public_metrics",
                    "verified",
                    "profile_image_url",
                ],
            )

            if not response.data:
                return None

            user = response.data
            user_data = UserData(
                id=user.id,
                username=user.username,
                name=user.name,
                description=user.description or "",
                created_at=user.created_at,
                public_metrics=user.public_metrics,
                verified=getattr(user, "verified", False),
                profile_image_url=getattr(user, "profile_image_url", None),
            )

            self.cache.set(cache_key, user_data.__dict__, ttl=self.cache_ttl["user"])
            return user_data

        except tweepy.TweepyException as e:
            logger.error(f"Error fetching user {user_id}: {e}")
        return None

    def get_user_by_username(self, username: str) -> Optional[UserData]:
        """
        Get user information by username with caching.

        Args:
            username: Username to fetch (without @)

        Returns:
            UserData object or None if not found
        """
        if not username:
            return None

        cache_key = f"user_name_{username.lower()}"
        cached = self.cache.get(cache_key)

        if cached:
            logger.debug(f"Cache hit for username @{username}")
            return UserData(**cached)

        logger.debug(f"Cache miss for username @{username}")

        try:
            response = self.client.get_user(
                username=username,
                user_fields=[
                    "created_at",
                    "description",
                    "public_metrics",
                    "verified",
                    "profile_image_url",
                ],
            )

            if not response.data:
                return None

            user = response.data
            user_data = UserData(
                id=user.id,
                username=user.username,
                name=user.name,
                description=user.description or "",
                created_at=user.created_at,
                public_metrics=user.public_metrics,
                verified=getattr(user, "verified", False),
                profile_image_url=getattr(user, "profile_image_url", None),
            )

            # Cache under both username and ID
            self.cache.set(cache_key, user_data.__dict__, ttl=self.cache_ttl["user"])
            self.cache.set(
                f"user_id_{user.id}", user_data.__dict__, ttl=self.cache_ttl["user"]
            )

            return user_data

        except tweepy.TweepyException as e:
            logger.error(f"Error fetching user @{username}: {e}")
            return None

    def get_user_tweets(self, user_id: str, max_results: int = 10) -> List[TweetData]:
        """
        Get recent tweets from a user with caching.

        Args:
            user_id: ID of the user
            max_results: Maximum number of tweets to return

        Returns:
            List of TweetData objects
        """
        cache_key = f"user_tweets_{user_id}_{max_results}"
        cached = self.cache.get(cache_key)

        if cached:
            logger.debug(f"Cache hit for user {user_id} tweets")
            return [TweetData(**tweet) for tweet in cached]

        logger.debug(f"Cache miss for user {user_id} tweets")

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
                tweet_data = TweetData(
                    id=tweet.id,
                    text=tweet.text,
                    author_id=user_id,
                    created_at=tweet.created_at,
                    public_metrics=tweet.public_metrics,
                )
                tweets.append(tweet_data)

            # Cache the serialized tweet data
            self.cache.set(
                cache_key,
                [tweet.__dict__ for tweet in tweets],
                ttl=self.cache_ttl["tweets"],
            )

            return tweets

        except tweepy.TweepyException as e:
            logger.error(f"Error fetching tweets for user {user_id}: {e}")
            return []

    def get_following(self, user_id: str, max_results: int = 100) -> List[UserData]:
        """
        Get following list for a user with caching.

        Args:
            user_id: ID of the user
            max_results: Maximum number of results

        Returns:
            List of UserData objects
        """
        cache_key = f"user_following_{user_id}_{max_results}"
        cached = self.cache.get(cache_key)

        if cached:
            logger.debug(f"Cache hit for user {user_id} following")
            return [UserData(**user) for user in cached]

        logger.debug(f"Cache miss for user {user_id} following")

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
                user_data = UserData(
                    id=user.id,
                    username=user.username,
                    name=user.name,
                    description=user.description or "",
                    created_at=user.created_at,
                    public_metrics=user.public_metrics,
                    verified=getattr(user, "verified", False),
                )
                users.append(user_data)

            # Cache the serialized user data
            self.cache.set(
                cache_key,
                [user.__dict__ for user in users],
                ttl=self.cache_ttl["following"],
            )

            return users

        except tweepy.TweepyException as e:
            logger.error(f"Error fetching following for user {user_id}: {e}")
            return []

    def create_tweet(
        self, text: str, in_reply_to_tweet_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new tweet.

        Args:
            text: Tweet text content
            in_reply_to_tweet_id: ID of tweet to reply to (optional)

        Returns:
            Tweet ID if successful, None otherwise
        """
        try:
            response = self.client.create_tweet(
                text=text, in_reply_to_tweet_id=in_reply_to_tweet_id
            )

            if response.data:
                logger.info(f"Tweet created successfully: {response.data['id']}")
                return response.data["id"]

            return None

        except tweepy.TweepyException as e:
            logger.error(f"Error creating tweet: {e}")
            return None
