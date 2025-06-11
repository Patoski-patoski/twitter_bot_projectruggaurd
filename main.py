#!/usr/bin/env python3
"""
Project RUGGUARD - X Bot for Account Trustworthiness Analysis
Main entry point for the bot that monitors replies and analyzes accounts.
"""

import os
import time
import logging
# from datetime import datetime
from dotenv import load_dotenv

from bot.twitter_api import TwitterAPIHandler, TweetData, UserData
from bot.analysis import AccountAnalyzer
from bot.report_generator import ReportGenerator
from config.trusted_accounts import TrustedAccountsManager

from typing import List


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("rugguard_bot.log"), logging.StreamHandler()],
)
logger: logging.Logger = logging.getLogger(__name__)


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
        self.bot_username: str = os.getenv("BOT_USERNAME", "@projectrugguard")
        self.last_processed_id = None

        logger.info("RugguardBot initialized successfully")

    def monitor_replies(self) -> None:
        """
        Main monitoring loop that checks for trigger phrases in replies.
        """
        
        logger.info("Starting reply monitoring...")

        while True:
            try:
                logger.info(
                    f"Searching for tweets with query: "
                    f'@{self.bot_username} {self.trigger_phrase} is:reply -is:retweet -is:quote'
)
                # Get recent mentions of the bot or replies with trigger phrase
                mentions = self.twitter_api.search_recent_tweets(
                    query =(
                        f'@{self.bot_username} "{self.trigger_phrase}"'  # Must mention bot and phrase
                        ' is:reply'                                      # Must be a reply
                        ' -is:retweet'                                   # Exclude retweets
                        ' -is:quote'                                     # Exclude quote tweets
                    ),
                    max_results=10
                )
                logger.INFO(f"Found {len(mentions)} matching tweets")
                print("Mentions", mentions.data)

                if mentions:
                    for tweet in mentions:
                        if (
                            self.last_processed_id
                            and int(tweet.id) <= int(self.last_processed_id)
                        ):
                            continue

                        # Check if this is a reply containing trigger phrase
                        if self.is_valid_trigger(tweet):
                            self.process_trigger(tweet)

                        self.last_processed_id = max(
                            self.last_processed_id or 0, int(tweet.id)
                        )

                # Wait before next check (respect rate limits)
                time.sleep(600)  # Check every 10 minute

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error

    def is_valid_trigger(self, tweet) -> bool:
        """
        Check if a tweet is a valid trigger for analysis.

        Args:
            tweet: Tweet object to check

        Returns:
            bool: True if valid trigger, False otherwise
        """
        
        if f"@{self.bot_username}".lower() and self.trigger_phrase.lower() not in tweet.text.lower():
            return False

        # Check if this is a reply (has in_reply_to_tweet_id)
        if not hasattr(tweet, "in_reply_to_tweet_id") or not tweet.in_reply_to_tweet_id:
            return False

        return True

    def process_trigger(self, trigger_tweet) -> None:
        """
        Process a valid trigger tweet by analyzing the original author.

        Args:
            trigger_tweet: The tweet containing the trigger phrase
        """
        try:
            logger.info(f"Processing trigger tweet: {trigger_tweet.id}")

            # Get the original tweet being replied to
            original_tweet: TweetData | None = self.twitter_api.get_tweet(
                trigger_tweet.in_reply_to_tweet_id
            )
            if not original_tweet:
                logger.warning(
                    f"Could not fetch original tweet: {trigger_tweet.in_reply_to_tweet_id}"
                )
                return

            # Get the original author's details
            original_author: UserData | None = self.twitter_api.get_user(original_tweet.author_id)
            if not original_author:
                logger.warning(
                    f"Could not fetch original author: {original_tweet.author_id}"
                )
                return

            logger.info(f"Analyzing user: @{original_author.username}")

            # Perform analysis
            analysis_result = self.analyzer.analyze_account(original_author)

            # Check trusted accounts
            trust_score = self.trusted_accounts.check_trust_score(
                original_author.username, self.twitter_api
            )

            # Generate report
            report = self.report_generator.generate_report(
                original_author, analysis_result, trust_score
            )

            # Post reply
            self.twitter_api.create_tweet(
                text=report, in_reply_to_tweet_id=trigger_tweet.id
            )

            logger.info(f"Successfully posted analysis for @{original_author.username}")

        except Exception as e:
            logger.error(f"Error processing trigger: {e}")
            # Post error message
            try:
                self.twitter_api.create_tweet(
                    text="Sorry, I encountered an error while analyzing this account. Please try again later.",
                    in_reply_to_tweet_id=trigger_tweet.id,
                )
            except:
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
