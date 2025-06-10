"""
Twitter API Handler for Project RUGGUARD
Handles all interactions with the X (Twitter) API.
"""

import os
import tweepy
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

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
    """Handles all Twitter API interactions."""

    def __init__(self):
        """Initialize Twitter API client."""
        # Load API credentials from environment
        self.bearer_token = os.getenv("X_BEARER_TOKEN")
        self.api_key = os.getenv("X_API_KEY")
        self.api_secret = os.getenv("X_API_SECRET")
        self.access_token = os.getenv("X_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

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

        logger.info("Twitter API client initialized")

    def search_recent_tweets(
        self, query: str, max_results: int = 10
    ) -> List[TweetData]:
        """
        Search for recent tweets matching a query.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of TweetData objects
        """
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
                tweet_data = TweetData(
                    id=tweet.id,
                    text=tweet.text,
                    author_id=tweet.author_id,
                    created_at=tweet.created_at,
                    public_metrics=tweet.public_metrics,
                    in_reply_to_tweet_id=getattr(tweet, "in_reply_to_user_id", None),
                )
                tweets.append(tweet_data)

            return tweets

        except tweepy.TweepyException as e:
            logger.error(f"Error searching tweets: {e}")
            return []

    def get_tweet(self, tweet_id: str) -> Optional[TweetData]:
        """
        Get a specific tweet by ID.

        Args:
            tweet_id: ID of the tweet to fetch

        Returns:
            TweetData object or None if not found
        """
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
            return TweetData(
                id=tweet.id,
                text=tweet.text,
                author_id=tweet.author_id,
                created_at=tweet.created_at,
                public_metrics=tweet.public_metrics,
                in_reply_to_tweet_id=getattr(tweet, "in_reply_to_user_id", None),
            )

        except tweepy.TweepyException as e:
            logger.error(f"Error fetching tweet {tweet_id}: {e}")
            return None

    def get_user(self, user_id: str) -> Optional[UserData]:
        """
        Get user information by user ID.

        Args:
            user_id: ID of the user to fetch

        Returns:
            UserData object or None if not found
        """
        try:
            response = self.client.get_user(
                user_id,
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
            return UserData(
                id=user.id,
                username=user.username,
                name=user.name,
                description=user.description or "",
                created_at=user.created_at,
                public_metrics=user.public_metrics,
                verified=getattr(user, "verified", False),
                profile_image_url=getattr(user, "profile_image_url", None),
            )

        except tweepy.TweepyException as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[UserData]:
        """
        Get user information by username.

        Args:
            username: Username to fetch (without @)

        Returns:
            UserData object or None if not found
        """
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
            return UserData(
                id=user.id,
                username=user.username,
                name=user.name,
                description=user.description or "",
                created_at=user.created_at,
                public_metrics=user.public_metrics,
                verified=getattr(user, "verified", False),
                profile_image_url=getattr(user, "profile_image_url", None),
            )

        except tweepy.TweepyException as e:
            logger.error(f"Error fetching user @{username}: {e}")
            return None

    def get_user_tweets(self, user_id: str, max_results: int = 10) -> List[TweetData]:
        """
        Get recent tweets from a user.

        Args:
            user_id: ID of the user
            max_results: Maximum number of tweets to return

        Returns:
            List of TweetData objects
        """
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

            return tweets

        except tweepy.TweepyException as e:
            logger.error(f"Error fetching tweets for user {user_id}: {e}")
            return []

    def get_following(self, user_id: str, max_results: int = 100) -> List[UserData]:
        """
        Get list of users that a user is following.

        Args:
            user_id: ID of the user
            max_results: Maximum number of results

        Returns:
            List of UserData objects
        """
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
