#!/usr/bin/env python3
# main.py
"""
Project RUGGUARD - X Bot for Account Trustworthiness Analysis
Main entry point for the bot that monitors replies and analyzes accounts.
"""

import os
import time
import logging
from typing import List
import tweepy
from dotenv import load_dotenv

from bot.twitter_api import TwitterAPIHandler, TweetData, UserData
from bot.analysis import AccountAnalyzer, AnalysisResult
from bot.report_generator import ReportGenerator
from config.trusted_accounts import TrustedAccountsManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("rugguard_bot.log"), logging.StreamHandler()],
)
logger: logging.Logger = logging.getLogger(__name__)
logger.info(f"Env variable for bot_username is {os.getenv("BOT_USERNAME")}")


class RugguardBot:
    """Main bot class that orchestrates the entire process."""

    def __init__(self):
        """Initialize the bot with all necessary components."""
        load_dotenv()

        # Initialize components
        self.twitter_api = TwitterAPIHandler()
        self.analyzer = AccountAnalyzer(self.twitter_api)
        self.report_generator = ReportGenerator()
        self.trusted_accounts = TrustedAccountsManager()

        # Bot configuration
        self.trigger_phrase = "riddle me this"
        self.bot_username: str = os.getenv("BOT_USERNAME", "projectrugguard")
        self.last_processed_id = None

        logger.info("RugguardBot initialized successfully")

    def monitor_replies(self) -> None:
        """
        Main monitoring loop that checks for trigger phrases in replies.
        """
        try:
            from bot.cache import JSONCache
            JSONCache().clear_all()
            logger.info("Cleared expired cache entries")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

        
        logger.info("Starting reply monitoring...")

        while True:
            try:
                logger.info(
                    f"Searching for tweets with query: "
                    f'@{self.bot_username} {self.trigger_phrase}'
)
                # Get recent mentions of the bot or replies with trigger phrase
                mentions: List[TweetData] = self.twitter_api.search_recent_tweets(
                    query=f'@{self.bot_username} {self.trigger_phrase} (is:reply OR is:quote) -is:retweet',
                    max_results=10
                )
                logger.info(f"Raw search returned {len(mentions)} tweets")
                
                # Filter out tweets that don't have in_reply_to_tweet_id
                valid_mentions: List[TweetData] = [t for t in mentions if hasattr(t, 'in_reply_to_tweet_id') and t.in_reply_to_tweet_id]
                logger.info(f"Found {len(valid_mentions)} valid reply tweets")
                
                if valid_mentions:
                    # Sort mentions by ID in descending order (newest first)
                    sorted_mentions = sorted(valid_mentions, key=lambda x: int(x.id), reverse=True)
                    logger.info(f"Processing {len(sorted_mentions)} tweets, newest first")
                    
                    for tweet in sorted_mentions:
                        logger.info(f"Checking tweet {tweet.id}: {tweet.text[:50]}...")
                        if (self.last_processed_id and int(tweet.id) <= int(self.last_processed_id)):
                            logger.info(f"Skipping already processed tweet {tweet.id} (last_processed_id: {self.last_processed_id})")
                            continue

                        # Check if this is a reply containing trigger phrase
                        if self.is_valid_trigger(tweet):
                            logger.info(f"Processing new trigger tweet {tweet.id}")
                            self.process_trigger(tweet)
                            # Update last_processed_id immediately after processing
                            self.last_processed_id = int(tweet.id)
                            logger.info(f"Updated last_processed_id to {self.last_processed_id}")
                        else:
                            logger.info(f"Tweet {tweet.id} is not a valid trigger")

                # Wait before next check (respect rate limits)
                time.sleep(60 * 16)  # Check every 16 minutes

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error

    def is_valid_trigger(self, tweet):
        """
        Check if a tweet is a valid trigger for analysis.

        Args:
            tweet: Tweet object to check

        Returns:
            bool: True if valid trigger, False otherwise
        """
        
        tweet_text = tweet.text.lower()
        bot_mention = f"@{self.bot_username}".lower()
        
        return (bot_mention in tweet_text and
                self.trigger_phrase.lower() in tweet_text and
                hasattr(tweet, 'in_reply_to_tweet_id') and
                tweet.in_reply_to_tweet_id)
        

    def process_trigger(self, trigger_tweet) -> None:
        """
        Process a valid trigger tweet by analyzing the author of the tweet being replied to.

        Args:
            trigger_tweet: The tweet containing the trigger phrase
        """
        
        logger.info(f"Processing trigger tweet: {trigger_tweet.id}")
        logger.info(f"Trigger tweet text: {trigger_tweet.text}")
        logger.info(f"Reply to tweet ID: {trigger_tweet.in_reply_to_tweet_id}")
        
        try:
            # Get the tweet being replied to (immediate parent)
            parent_tweet: TweetData | None = self.twitter_api.get_tweet(
                trigger_tweet.in_reply_to_tweet_id
            )
            if not parent_tweet:
                logger.warning(
                    f"Parent tweet not found or inaccessible: {trigger_tweet.in_reply_to_tweet_id}. "
                    f"This could be because:\n"
                    f"1. The tweet was deleted\n"
                    f"2. The tweet is from a private account\n"
                    f"3. The tweet ID is invalid\n"
                    f"4. The tweet is too old (Twitter API limitations)"
                )
                self.twitter_api.create_tweet(
                    text="⚠️ Could not fetch the tweet you're replying to. It may have been deleted, made private, or is too old to access.",
                    in_reply_to_tweet_id=trigger_tweet.id
                )
                return

            # Get the parent tweet's author details
            parent_author: UserData | None = self.twitter_api.get_user(parent_tweet.author_id)
            if not parent_author:
                logger.warning(
                    f"Could not fetch parent tweet author: {parent_tweet.author_id}"
                )
                self.twitter_api.create_tweet(
                    text="⚠️ Could not fetch the author of the tweet you're replying to.",
                    in_reply_to_tweet_id=trigger_tweet.id
                )
                return

            logger.info(f"Analyzing user: @{parent_author.username}")

            # Perform analysis
            analysis_result: AnalysisResult = self.analyzer.analyze_account(parent_author)

            # Check trusted accounts
            trust_score = self.trusted_accounts.check_trust_score(
                parent_author.username, self.twitter_api
            )

            # Generate report
            report: str = self.report_generator.generate_report(
                parent_author, analysis_result, trust_score
            )

            # Post reply
            self.twitter_api.create_tweet(
                text=report, in_reply_to_tweet_id=trigger_tweet.id
            )

            logger.info(f"Successfully posted analysis for @{parent_author.username}")

        except Exception as e:
            logger.error(f"Error processing trigger: {e}")
            # Post error message
            try:
                self.twitter_api.create_tweet(
                    text="Sorry, I encountered an error while analyzing this account. Please try again later.",
                    in_reply_to_tweet_id=trigger_tweet.id,
                )
            except tweepy.TweepyException as e:
                pass


def main():
    """Main function to start the bot."""
    logger.info("Starting Project RUGGUARD Bot...")

    try:
        bot = RugguardBot()
        bot.monitor_replies()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
