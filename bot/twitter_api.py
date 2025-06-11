"""
Twitter API Handler for Project RUGGUARD
Handles all interactions with the X (Twitter) API.
"""

import tweepy
import os
import time
import logging
from requests import Response
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .cache import TwitterCache
from .mock_data import MockDataProvider

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

        # Initialize cache
        self.cache = TwitterCache()
        
        # Initialize mock data provider
        self.mock_data = MockDataProvider()
        
        # Track API limit exhaustion
        self.exhausted_endpoints = set()

        logger.info("Twitter API client initialized")

    def _use_mock_data(self, endpoint: str) -> bool:
        """Check if we should use mock data for an endpoint."""
        return endpoint in self.exhausted_endpoints

    def _mark_endpoint_exhausted(self, endpoint: str) -> None:
        """Mark an endpoint as exhausted."""
        self.exhausted_endpoints.add(endpoint)
        logger.warning(f"Using mock data for {endpoint} - API limit exhausted")

    def make_api_call(self, api_method, *args, **kwargs):
        max_retries = 3
        for attempts in range(max_retries):
            try:
                return api_method(*args, **kwargs)
            except tweepy.TooManyRequests as e:
                wait_time = int(e.response.headers.get("Retry-After", 60)) # Default to 60 seconds if header not present
                logger.warning(f"Rate limit exceeded. Retrying in {wait_time} seconds\n Attempt {attempts + 1}/{max_retries}...")
                time.sleep(wait_time)
            except tweepy.TweepyException as e:
                logger.error(f"Tweepy API error: {e}")
                raise
        logger.error(f"Failed after {max_retries} attempts due to rate limiting.")
        raise tweepy.TooManyRequests("Rate limit consistently hit.") # Raise if all retries fail
        
    def search_recent_tweets(
        self, query: str, max_results: int = 10
    ) -> List[TweetData]:
        """
        Search for recent tweets matching a query.
        Falls back to mock data if API limit is exhausted.
        """
        if self._use_mock_data("search"):
            logger.info("Using mock data for search")
            return self.mock_data.get_mock_search_results(query, max_results)

        try:
            logger.info(f"Searching tweets with query: {query}")
            response = self.make_api_call(
                self.client.search_recent_tweets,
                query=query,
                max_results=max_results,
                tweet_fields=[
                    "author_id",
                    "created_at",
                    "public_metrics",
                    "in_reply_to_user_id",
                    "referenced_tweets",
                ],
                expansions=["author_id", "referenced_tweets.id"],
            )
            
            if response.data:
                logger.info(f"Found {len(response.data)} tweets in response")
                tweets = []
                for tweet_data in response.data:
                    in_reply_to_id = None
                    if hasattr(tweet_data, 'referenced_tweets') and tweet_data.referenced_tweets:
                        for ref_tweet in tweet_data.referenced_tweets:
                            if ref_tweet.type == "replied_to":
                                in_reply_to_id = ref_tweet.id
                                break
                    
                    tweet = TweetData(
                        id=str(tweet_data.id),
                        text=tweet_data.text,
                        author_id=str(tweet_data.author_id),
                        created_at=str(tweet_data.created_at),
                        public_metrics=tweet_data.public_metrics,
                        in_reply_to_tweet_id=in_reply_to_id,
                    )
                    tweets.append(tweet)
                return tweets
            return []

        except tweepy.TooManyRequests as e:
            self._mark_endpoint_exhausted("search")
            logger.warning("Search API limit exhausted, using mock data")
            return self.mock_data.get_mock_search_results(query, max_results)
        except Exception as e:
            logger.error(f"Error searching tweets: {e}", exc_info=True)
            return []

    def get_tweet(self, tweet_id: str) -> Optional[TweetData]:
        """
        Get a specific tweet by ID.

        Args:
            tweet_id: ID of the tweet to fetch

        Returns:
            TweetData object or None if not found
        """
        # Check cache first
        cached_tweet = self.cache.get_tweet(tweet_id)
        if cached_tweet:
            return cached_tweet

        try:
            response = self.make_api_call(
                self.client.get_tweet,
                id=tweet_id,
                tweet_fields=[
                    "author_id",
                    "created_at",
                    "public_metrics",
                    "in_reply_to_user_id",
                    "referenced_tweets",
                ],
            )
            if response.data:
                # Need to properly parse referenced_tweets to get in_reply_to_tweet_id
                in_reply_to_id = None
                if response.data.referenced_tweets:
                    for ref_tweet in response.data.referenced_tweets:
                        if ref_tweet.type == "replied_to":
                            in_reply_to_id = ref_tweet.id
                            break
                tweet_data = TweetData(
                    id=str(response.data.id),
                    text=response.data.text,
                    author_id=str(response.data.author_id),
                    created_at=str(response.data.created_at),
                    public_metrics=response.data.public_metrics,
                    in_reply_to_tweet_id=in_reply_to_id,
                )
                # Cache the tweet
                self.cache.set_tweet(tweet_id, tweet_data)
                return tweet_data
        except tweepy.TweepyException as e:
            logger.error(f"Error fetching tweet {tweet_id}: {e}")
        return None

    def get_user(self, user_id: str) -> Optional[UserData]:
        """
        Get user information by user ID.
        Falls back to mock data if API limit is exhausted.
        """
        if self._use_mock_data("user"):
            logger.info("Using mock data for user lookup")
            return self.mock_data.get_mock_user()

        # Check cache first
        cached_user = self.cache.get_user(user_id)
        if cached_user:
            return cached_user

        try:
            response = self.make_api_call(
                self.client.get_user,
                id=user_id,
                user_fields=["created_at", "public_metrics", "description", "verified", "profile_image_url"]
            )
            if response.data:
                user_data = UserData(
                    id=str(response.data.id),
                    username=response.data.username,
                    name=response.data.name,
                    created_at=str(response.data.created_at),
                    public_metrics=response.data.public_metrics,
                    description=response.data.description or "",
                    verified=getattr(response.data, "verified", False),
                    profile_image_url=getattr(response.data, "profile_image_url", None)
                )
                self.cache.set_user(user_id, user_data)
                return user_data
            return None

        except tweepy.TooManyRequests as e:
            self._mark_endpoint_exhausted("user")
            logger.warning("User API limit exhausted, using mock data")
            return self.mock_data.get_mock_user()
        except Exception as e:
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
            response = self.make_api_call(
                self.client.get_users_tweets,
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
                # Cache individual tweets
                self.cache.set_tweet(tweet.id, tweet_data)

            return tweets

        except tweepy.TweepyException as e:
            logger.error(f"Error fetching tweets for user {user_id}: {e}")
            return []

    def get_following(self, user_id: str, max_results: int = 100) -> List[UserData]:
        """
        Get list of users that a user is following.
        Falls back to mock data if API limit is exhausted.
        """
        if self._use_mock_data("following"):
            logger.info("Using mock data for following list")
            return self.mock_data.get_mock_following(user_id, max_results)

        # Check cache first
        cached_following = self.cache.get_following(user_id)
        if cached_following:
            return cached_following

        try:
            response = self.make_api_call(
                self.client.get_users_following,
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

            self.cache.set_following(user_id, users)
            return users

        except tweepy.TooManyRequests as e:
            self._mark_endpoint_exhausted("following")
            logger.warning("Following API limit exhausted, using mock data")
            return self.mock_data.get_mock_following(user_id, max_results)
        except Exception as e:
            logger.error(f"Error fetching following for user {user_id}: {e}")
            return []

    def create_tweet(
        self, text: str, in_reply_to_tweet_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new tweet.
        Note: No mock data for this as it's a write operation.
        """
        try:
            response = self.make_api_call(
                self.client.create_tweet,
                text=text,
                in_reply_to_tweet_id=in_reply_to_tweet_id
            )
            if response and response.data:
                if in_reply_to_tweet_id:
                    self.cache.invalidate_tweet(in_reply_to_tweet_id)
                return response.data['id']
        except tweepy.TooManyRequests as e:
            logger.error("Cannot create tweet - API limit exhausted")
            return None
        except Exception as e:
            logger.error(f"Error creating tweet: {e}")
            return None