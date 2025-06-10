# import tweepy
# import requests
# from requests import Response
# import os
# from dotenv import load_dotenv
# from typing import Optional, Dict, Any
# from dataclasses import dataclass

# @dataclass
# class UserDetails:
#     name: str
#     username: str
#     id: str
#     error: bool = False


# class TwitterBot:
#     def __init__(self) -> None:
#         load_dotenv()

#         # Load credentials
#         self.consumer_key: str | None  = os.getenv("X_API_KEY")
#         self.consumer_secret: str | None = os.getenv("X_API_SECRET")
#         self.access_token: str | None = os.getenv("X_ACCESS_TOKEN")
#         self.access_token_secret: str | None = os.getenv("X_ACCESS_TOKEN_SECRET")
#         self.bearer_token: str | None = os.getenv("X_BEARER_TOKEN")

#         # Initialize auth
#         self.auth = tweepy.OAuth1UserHandler(
#             self.consumer_key,
#             self.consumer_secret,
#             self.access_token,
#             self.access_token_secret,
#         )

#         # Initialize API v1.1 client
#         self.api = tweepy.API(
#             self.auth, 
#             retry_count=3, retry_delay=5, wait_on_rate_limit=True
#         )

#         # Initialize API v2 client
#         self.client = tweepy.Client(
#             self.bearer_token,
#             self.consumer_key,
#             self.consumer_secret,
#             self.access_token,
#             self.access_token_secret,
#         )

#     def update_profile_image(self, filename: str) -> None:
#         try:
#             self.api.update_profile_image(filename)
#         except FileNotFoundError:
#             print(f"File {filename} not found.")

#     def post_tweet(self, text: str) -> None:
#         try:
#             self.client.create_tweet(text=text)
#         except tweepy.TweepyException as e:
#             print(f"Error posting tweet: {e}")
            
#     def upload_media(self, text: str, filename: str) -> Optional[Dict | Response]:
#         try:
#             media: tweepy.models.Media = self.api.media_upload(filename)
#             self.client.create_tweet(text=text, media_ids=[media.media_id_strings])
#         except FileNotFoundError:
#             print(f"File {filename} not found")
    
#     def like(self, tweet_id: str | int) -> None:
#         try:
#             self.client.like(tweet_id=str(tweet_id), user_auth=True)
#             print(f"Successfully liked tweet {tweet_id}")
#         except TypeError:
#             print("Authentication failed: access token not set")

#     def retweet(self, tweet_id: str | int) -> None:
#         try:
#             self.client.retweet(tweet_id=str(tweet_id), user_auth=True)
#             print(f"Successfully retweeted tweet {tweet_id}")
#         except tweepy.TweepyException as e:
#             print(f"Failed to retweet:{e}")
#         except TypeError:
#             print("Authentication failed: access token not set")
            
#     def undo_retweet(self, tweet_id: str | int) -> None:
#         try:
#             self.client.unretweet(source_tweet_id=str(tweet_id), user_auth=True)
#             print(f"Successfully unretweeted tweet {tweet_id}")
#         except tweepy.TweepyException as e:
#             print(f"Failed to retweet:{e}")
#         except TypeError:
#             print("Authentication failed: access token not set")
    
#     def get_user_details(self, username: str) -> UserDetails:
#         try:
#             user = self.client.get_user(username=username)
#             if user.data:
#                 return UserDetails(
#                     name=user.data.name,
#                     username=user.data.username,
#                     id=user.data.id
#                 )
#             return UserDetails(name="", username="", id="", error=True)
#         except tweepy.TweepyException as e:
#             print(f"Error getting user ID: {e}")
#             return UserDetails(name="", username="", id="", error=True)
        
    
#     def reply(self, tweet_id: str | int) -> None:
#         tweet = self.client.get_tweet(id=str(tweet_id))
#         print(f"Replied to {tweet}")

# # Usage example:    

# # Usage
# if __name__ == "__main__":
#     bot = TwitterBot()
#     # bot.post_tweet("Hello World! X2")
#     # bot.upload_media("raise Forbidden error to the power of {e}", "image.png")
#     # bot.like("1931767738277540143")
#     # bot.retweet("1931809472638521695")
#     # user = bot.reply("1931809472638521695")
#     # print(user)
#     # bot.undo_retweet("1931809472638521695")
#     user = bot.reply("1931809472638521695")
#     # user = bot.get_user_details("GideonOkorie7")
#     # print(user)
#     # print(f"{user.username} and {user.id}")


# import requests
# from requests import Response
# import os
# import pprint

# id: str = "1931809472638521695"
# token = os.getenv("X_BEARER_TOKEN")

# url = f"https://api.twitter.com/2/tweets/{id}"
# # url = "GET /2/users/:id/followers"

# headers = {"Authorization": f"Bearer {token}"}

# response: Response = requests.request("GET", url, headers=headers)

# pprint.pprint(response)
# print("\n\n\n")
# pprint.pprint(response.text)
