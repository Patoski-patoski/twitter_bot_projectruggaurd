from dotenv import load_dotenv
import os


from bot import XBot

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    api_key  = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    bearer_token = os.getenv("X_BEARER_TOKEN")
    
    # Initialize core API client
    trusted_accounts = os.getenv("https://github.com/devsyrem/turst-list/blob/main/list")
    # analyzer = 
    
    # Initialize X Bot
    x_bot = XBot(
        api_key,
        api_secret,
        access_token,
        access_token_secret,
        bearer_token
    )
    
    print("X Bot initialized successfully.")
    x
