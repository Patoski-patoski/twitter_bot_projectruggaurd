import tweepy

class XBot:
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_token_secret: str, bearer_token: str):
        self.client = tweepy.Client(
            bearer_token,
            api_key,
            api_secret,
            access_token,
            access_token_secret
        )