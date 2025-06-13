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
# from datetime import datetime
from dotenv import load_dotenv

from bot.twitter_api import TwitterAPIHandler, TweetData, UserData
from bot.analysis import AccountAnalyzer
from bot.report_generator import ReportGenerator
from config.trusted_accounts import TrustedAccountsManager


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
        rate_limit_wait = 60  # Start with 1 minute wait

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
                
                # Filter out tweets that don't have in_reply_to_tweet_id and are not from the bot itself
                valid_mentions = [
                    t for t in mentions 
                    if (hasattr(t, 'in_reply_to_tweet_id') and 
                        t.in_reply_to_tweet_id and 
                        not t.text.startswith('2/') and  # Skip our own how-to tweets
                        not 'Usage:' in t.text)  # Skip our own error messages
                ]
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
                            try:
                                logger.info(f"Processing new trigger tweet {tweet.id}")
                                self.process_trigger(tweet)
                                # Update last_processed_id immediately after processing
                                self.last_processed_id = int(tweet.id)
                                logger.info(f"Updated last_processed_id to {self.last_processed_id}")
                                # Reset rate limit wait on successful processing
                                rate_limit_wait = 60
                            except Exception as e:
                                if "rate limit" in str(e).lower():
                                    logger.warning(f"Rate limit hit, increasing wait time to {rate_limit_wait} seconds")
                                    time.sleep(rate_limit_wait)
                                    # Increase wait time for next rate limit (up to 5 minutes)
                                    rate_limit_wait = min(rate_limit_wait * 2, 300)
                                else:
                                    logger.error(f"Error processing tweet {tweet.id}: {e}")
                        else:
                            logger.info(f"Tweet {tweet.id} is not a valid trigger")

                # Wait before next check (respect rate limits)
                time.sleep(rate_limit_wait)  # Use dynamic wait time

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
        

    def get_original_tweet_in_thread(self, tweet_id: str, max_depth: int = 5) -> TweetData | None:
        """
        Recursively fetch tweets in a thread to find the original tweet.
        Includes rate limit handling and caching.
        """
        current_depth = 0
        current_tweet_id = tweet_id
        max_retries = 3
        base_delay = 5  # Base delay in seconds
        
        while current_depth < max_depth:
            # Try to get the tweet with retries
            tweet = None
            for retry in range(max_retries):
                try:
                    tweet = self.twitter_api.get_tweet(current_tweet_id)
                    if tweet:
                        break
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        delay = base_delay * (2 ** retry)  # Exponential backoff
                        logger.warning(f"Rate limit hit, waiting {delay} seconds before retry {retry + 1}/{max_retries}")
                        time.sleep(delay)
                    else:
                        logger.error(f"Error fetching tweet {current_tweet_id}: {e}")
                        break
            
            if not tweet:
                logger.warning(f"Could not fetch tweet {current_tweet_id} at depth {current_depth} after {max_retries} retries")
                return None
                
            logger.info(f"Fetched tweet at depth {current_depth}: {tweet.id} by @{tweet.author_id}")
            
            # If this tweet is not a reply, it's the original
            if not hasattr(tweet, 'in_reply_to_tweet_id') or not tweet.in_reply_to_tweet_id:
                logger.info(f"Found original tweet: {tweet.id}")
                return tweet
                
            current_tweet_id = tweet.in_reply_to_tweet_id
            current_depth += 1
            
            # Add a small delay between requests to avoid rate limits
            time.sleep(2)
            
        logger.warning(f"Reached max depth {max_depth} without finding original tweet")
        return None

    def process_trigger(self, trigger_tweet) -> None:
        """
        Process a valid trigger tweet by analyzing the author of the original tweet in the thread.
        Includes rate limit handling and caching.
        """
        try:
            logger.info(f"Processing trigger tweet: {trigger_tweet.id}")
            logger.info(f"Trigger tweet text: {trigger_tweet.text}")
            logger.info(f"Reply to tweet ID: {trigger_tweet.in_reply_to_tweet_id}")

            # First try to get the immediate parent tweet with retries
            parent_tweet = None
            max_retries = 3
            base_delay = 5
            
            for retry in range(max_retries):
                try:
                    parent_tweet = self.twitter_api.get_tweet(trigger_tweet.in_reply_to_tweet_id)
                    if parent_tweet:
                        break
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        delay = base_delay * (2 ** retry)
                        logger.warning(f"Rate limit hit while fetching parent tweet, waiting {delay} seconds before retry {retry + 1}/{max_retries}")
                        time.sleep(delay)
                    else:
                        logger.error(f"Error fetching parent tweet: {e}")
                        break
            
            if not parent_tweet:
                logger.info("Parent tweet not found, attempting to find original tweet in thread...")
                # Try to find the original tweet in the thread
                original_tweet = self.get_original_tweet_in_thread(trigger_tweet.in_reply_to_tweet_id)
                
                if not original_tweet:
                    logger.warning(
                        f"Could not find any accessible tweet in the thread starting from {trigger_tweet.in_reply_to_tweet_id}. "
                        f"This could be because:\n"
                        f"1. The thread is too long (more than 5 tweets deep)\n"
                        f"2. Some tweets in the thread were deleted\n"
                        f"3. Some tweets are from private accounts\n"
                        f"4. The tweets are too old (Twitter API limitations)\n"
                        f"5. We hit Twitter API rate limits"
                    )
                    self.twitter_api.create_tweet(
                        text="⚠️ Could not access the tweet thread. This might be due to rate limits, thread length, or tweet age. Please try again in a few minutes.",
                        in_reply_to_tweet_id=trigger_tweet.id
                    )
                    return
                    
                parent_tweet = original_tweet
                logger.info(f"Found original tweet in thread: {parent_tweet.id}")

            # Get the parent tweet's author details with retries
            parent_author = None
            for retry in range(max_retries):
                try:
                    parent_author = self.twitter_api.get_user(parent_tweet.author_id)
                    if parent_author:
                        break
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        delay = base_delay * (2 ** retry)
                        logger.warning(f"Rate limit hit while fetching author, waiting {delay} seconds before retry {retry + 1}/{max_retries}")
                        time.sleep(delay)
                    else:
                        logger.error(f"Error fetching author: {e}")
                        break

            if not parent_author:
                logger.warning(f"Could not fetch parent tweet author: {parent_tweet.author_id}")
                self.twitter_api.create_tweet(
                    text="⚠️ Could not fetch the author of the tweet you're replying to. This might be due to rate limits. Please try again in a few minutes.",
                    in_reply_to_tweet_id=trigger_tweet.id
                )
                return

            logger.info(f"Analyzing user: @{parent_author.username} (original tweet author)")

            # Perform analysis
            analysis_result = self.analyzer.analyze_account(parent_author)

            # Check trusted accounts
            trust_score = self.trusted_accounts.check_trust_score(
                parent_author.username, self.twitter_api
            )

            # Generate report
            report = self.report_generator.generate_report(
                parent_author, analysis_result, trust_score
            )

            # Post reply
            self.twitter_api.create_tweet(
                text=report, in_reply_to_tweet_id=trigger_tweet.id
            )

            logger.info(f"Successfully posted analysis for @{parent_author.username}")

        except Exception as e:
            logger.error(f"Error processing trigger: {e}")
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
