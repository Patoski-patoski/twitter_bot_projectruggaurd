
# bot.py

import tweepy
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import pprint


load_dotenv()

print("Data loaded!!!")

@dataclass
class UserDetails:
    name: str
    username: str
    id: str
    error: bool = False
    
    
def getClient() -> tweepy.Client:
    client = tweepy.Client(
        bearer_token=os.getenv("X_BEARER_TOKEN"),
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
    )
    
    return client
    
def search_tweets(query: str)-> List[Any]:
    client: tweepy.Client = getClient()
    
    try:
        tweets = client.search_recent_tweets(
            query=query,
            max_results=10,
        )
        # pprint.pprint("tweets\n\n", tweets)
        print(f"Found {len(tweets.data) if tweets.data else 0} tweets")
            
        if not tweets.data:
            return []
            
        tweet_data = [
            {
                "id": str(tweet.id),
                "text": tweet.text,
                "in_reply_to_tweet_id": tweet.in_reply_to_tweet_id,
                "author_id": tweet.author_id,
                "created_at": tweet.created_at,
                "public_metrics": tweet.public_metrics
            }
                for tweet in tweets.data
        ]
        
        # Pretty print the formatted data
        pprint.pprint(tweet_data)
        return tweet_data
        
    except Exception as e:
        print(f"Error searching tweets: {e}")
        return []
    


if __name__ == "__main__":
    tweets = search_tweets("@projectrugguard riddle me this")
    print(f"\nFound {len(tweets)} matching tweets")

    # bot.upload_media("raise Forbidden error to the power of {e}", "image.png")
    # bot.like("1931767738277540143")
    # bot.retweet("1931809472638521695")
    # user = bot.reply("1931809472638521695")
    # print(user)
    # bot.undo_retweet("1931809472638521695")
    # user = bot.reply("1931809472638521695")
    # user = bot.get_user_dat("GideonOkorie7")
    # print(user)
    # print(f"{user.username} and {user.id}")

