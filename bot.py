
# bot.py

import tweepy
from requests import Response
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class UserDetails:
    name: str
    username: str
    id: str
    error: bool = False


class TwitterBot:
    def __init__(self) -> None:
        load_dotenv()

        # Load credentials
        self.consumer_key: str | None  = os.getenv("X_API_KEY")
        self.consumer_secret: str | None = os.getenv("X_API_SECRET")
        self.access_token: str | None = os.getenv("X_ACCESS_TOKEN")
        self.access_token_secret: str | None = os.getenv("X_ACCESS_TOKEN_SECRET")
        self.bearer_token: str | None = os.getenv("X_BEARER_TOKEN")

        # Initialize auth
        self.auth = tweepy.OAuth1UserHandler(
            self.consumer_key,
            self.consumer_secret,
            self.access_token,
            self.access_token_secret,
        )

        # Initialize API v1.1 client
        self.api = tweepy.API(
            self.auth,
            retry_count=3, retry_delay=5, wait_on_rate_limit=True
        )

        # Initialize API v2 client
        self.client = tweepy.Client(
            self.bearer_token,
            self.consumer_key,
            self.consumer_secret,
            self.access_token,
            self.access_token_secret,
        )

  def get_user_data(client: tweepy.Client, username: str) -> Dict[str, Any] | None:
    """
    Fetches user data for a given username.
    """
    try:
        response = client.get_user(username=username)
        if response.data:
            return response.data
        return None
    except tweepy.TweepyException as e:
        print(f"Error fetching user data: {e}")
        return None

def create_tweet(client: tweepy.Client, text: str, reply_to_tweet_id: str | None = None) -> Dict[str, Any] | None:
    """
    Creates a new tweet.
    """
    try:
        response = client.create_tweet(text=text, in_reply_to_tweet_id=reply_to_tweet_id)
        if response.data:
            return response.data
        return None
    except tweepy.TweepyException as e:
        print(f"Error creating tweet: {e}")
        return None

# Example usage (you'd get these from your .env file)
# bearer_token = "YOUR_BEARER_TOKEN"
# api_key = "YOUR_API_KEY"
# api_secret = "YOUR_API_SECRET"
# access_token = "YOUR_ACCESS_TOKEN"
# access_token_secret = "YOUR_ACCESS_TOKEN_SECRET"

# client = tweepy.Client(
#     bearer_token,
#     api_key,
#     api_secret,
#     access_token,
#     access_token_secret
# )

# user_info = get_user_data(client, "elonmusk")
# if user_info:
#     print(f"User ID: {user_info['id']}, Name: {user_info['name']}")

# new_tweet = create_tweet(client, "Hello from my #Python bot with type hints!")
# if new_tweet:
#     print(f"Tweet created: {new_tweet['id']}")


# Usage example:

# Usage
if __name__ == "__main__":
    bot = TwitterBot()
    # bot.post_tweet("Hello World! X2")
    # bot.upload_media("raise Forbidden error to the power of {e}", "image.png")
    # bot.like("1931767738277540143")
    # bot.retweet("1931809472638521695")
    # user = bot.reply("1931809472638521695")
    # print(user)
    # bot.undo_retweet("1931809472638521695")
    user = bot.reply("1931809472638521695")
    # user = bot.get_user_details("GideonOkorie7")
    # print(user)
    # print(f"{user.username} and {user.id}")

