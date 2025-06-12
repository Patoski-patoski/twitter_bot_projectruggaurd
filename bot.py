
# bot.py

import tweepy
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import pprint
import json
from datetime import datetime
from pathlib import Path

load_dotenv()



def save_tweets(tweets: List[Dict[str, Any]], filename: str = "cached_tweets.json") -> None:
    """Save tweets to a JSON file with timestamp."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "tweets": tweets
    }
    
    Path("cache").mkdir(exist_ok=True)
    with open(f"cache/{filename}", "w") as f:
        json.dump(data, f, indent=2)

def load_tweets(filename: str = "cached_tweets.json") -> List[Dict[str, Any]]:
    """Load tweets from cache if available and recent."""
    try:
        cache_file = Path("cache") / filename
        if not cache_file.exists():
            return []
            
        with open(cache_file) as f:
            data = json.load(f)
            
        # Check if cache is less than 15 minutes old
        cached_time = datetime.fromisoformat(data["timestamp"])
        age = (datetime.now() - cached_time).total_seconds() / 60
        
        if age < 15:  # Twitter's rate limit window
            return data["tweets"]
        return []
        
    except Exception as e:
        print(f"Error loading cached tweets: {e}")
        return []
    
    
    
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
    
def search_tweets(query: str):
    client: tweepy.Client = getClient()
    
    cached_tweets = load_tweets()
    if cached_tweets:
        print("Using cached tweet")
        return cached_tweets
    
    try:
        search_query = (
            f"{query}"           # Base query text
            " is:reply"          # Must be a reply
            " -is:retweet"       # Exclude retweets
            " -is:quote"         # Exclude quote tweets
        )
         
        tweets = client.search_recent_tweets(
            query=search_query,
            max_results=10,
        )
        
        tweet_data = tweets.data
        result = []
        for tweet in tweet_data:
            obj = {}
            obj['id'] = tweet.id
            obj['text'] = tweet.text
            obj['author_id'] = tweet.author_id
            obj['created_at'] = tweet.created_at
            result.append(obj)
        
        
            
        # tweet_data = [
        #     {
        #         "id": str(tweet.id),
        #         "text": tweet.text,
        #         "in_reply_to_tweet_id": tweet.in_reply_to_tweet_id,
        #         "author_id": tweet.author_id,
        #         "created_at": tweet.created_at,
        #     }
        #         for tweet in tweets.data
        # ]
        
        save_tweets(tweet_data)
        
        # Pretty print the formatted data
        pprint.pprint(tweet_data)
        return result
        
        # return tweet_data
        
    except Exception as e:
        print(f"Error searching tweets: {e}")
        return []
    


if __name__ == "__main__":
    tweets = search_tweets("@projectrugguard riddle me this")
    for x in tweets:
        print(x)

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

