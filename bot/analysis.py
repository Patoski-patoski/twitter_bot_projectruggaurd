"""
Account Analysis Module for Project RUGGUARD
Analyzes Twitter accounts for trustworthiness indicators.
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .twitter_api import TwitterAPIHandler, UserData, TweetData

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Data class for analysis results."""
    account_age_days: int
    follower_following_ratio: float
    bio_score: int
    engagement_score: int
    content_score: int
    overall_risk_score: int
    flags: List[str]
    recommendations: List[str]

class AccountAnalyzer:
    """Analyzes Twitter accounts for trustworthiness indicators."""
    
    def __init__(self, twitter_api: TwitterAPIHandler):
        """
        Initialize the analyzer.
        
        Args:
            twitter_api: Twitter API handler instance
        """
        self.twitter_api = twitter_api
        
        # Suspicious keywords for bio analysis
        self.suspicious_keywords = [
            'guaranteed', 'risk-free', 'get rich', 'easy money', 'moonshot',
            'to the moon', '100x', 'guaranteed returns', 'no risk',
            'quick profit', 'instant wealth', 'diamond hands', 'hodl',
            'financial advice', 'not financial advice', 'dyor'
        ]
        
        # Trusted keywords
        self.trusted_keywords = [
            'developer', 'engineer', 'founder', 'ceo', 'cto', 'researcher',
            'university', 'phd', 'professor', 'verified', 'official'
        ]
    
    def analyze_account(self, user: UserData) -> AnalysisResult:
        """
        Perform comprehensive analysis of a Twitter account.
        
        Args:
            user: UserData object containing user information
            
        Returns:
            AnalysisResult object with analysis results
        """
        logger.info(f"Starting analysis for @{user.username}")
        
        # Initialize result
        flags = []
        recommendations = []
        
        # Analyze account age
        account_age_days = self._calculate_account_age(user.created_at)
        if account_age_days < 30:
            flags.append("Very new account (less than 30 days)")
        elif account_age_days < 90:
            flags.append("New account (less than 90 days)")
        
        # Analyze follower/following ratio
        follower_following_ratio = self._calculate_follower_ratio(user.public_metrics)
        if follower_following_ratio < 0.1:
            flags.append("Low follower-to-following ratio")
        elif follower_following_ratio > 10:
            recommendations.append("Good follower-to-following ratio")
        
        # Analyze bio content
        bio_score = self._analyze_bio(user.description)
        if bio_score < 3:
            flags.append("Bio contains suspicious content")
        elif bio_score > 7:
            recommendations.append("Professional bio content")
        
        # Analyze engagement patterns
        engagement_score = self._analyze_engagement(user)
        if engagement_score < 3:
            flags.append("Low engagement patterns")
        elif engagement_score > 7:
            recommendations.append("Good engagement patterns")
        
        # Analyze recent content
        content_score = self._analyze_content(user.id)
        if content_score < 3:
            flags.append("Suspicious content patterns")
        elif content_score > 7:
            recommendations.append("Quality content")
        
        # Calculate overall risk score (0-10, where 10 is highest risk)
        risk_factors = []
        if account_age_days < 30:
            risk_factors.append(3)
        elif account_age_days < 90:
            risk_factors.append(2)
        else:
            risk_factors.append(0)
        
        if follower_following_ratio < 0.1:
            risk_factors.append(2)
        elif follower_following_ratio < 0.5:
            risk_factors.append(1)
        else:
            risk_factors.append(0)
        
        risk_factors.append(max(0, 5 - bio_score))
        risk_factors.append(max(0, 5 - engagement_score))
        risk_factors.append(max(0, 5 - content_score))
        
        overall_risk_score = min(10, sum(risk_factors))
        
        result = AnalysisResult(
            account_age_days=account_age_days,
            follower_following_ratio=follower_following_ratio,
            bio_score=bio_score,
            engagement_score=engagement_score,
            content_score=content_score,
            overall_risk_score=overall_risk_score,
            flags=flags,
            recommendations=recommendations
        )
        
        logger.info(f"Analysis completed for @{user.username}, risk score: {overall_risk_score}")
        return result
    
    def _calculate_account_age(self, created_at: str) -> int:
        """Calculate account age in days."""
        try:
            # Parse the datetime string
            if isinstance(created_at, str):
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                created_date = created_at
            
            # Calculate age
            now = datetime.now(timezone.utc)
            age = now - created_date
            return age.days
        except Exception as e:
            logger.error(f"Error calculating account age: {e}")
            return 0
    
    def _calculate_follower_ratio(self, metrics: Dict[str, int]) -> float:
        """Calculate follower-to-following ratio."""
        followers = metrics.get('followers_count', 0)
        following = metrics.get('following_count', 1)  # Avoid division by zero
        
        if following == 0:
            return float('inf') if followers > 0 else 0
        
        return followers / following
    
    def _analyze_bio(self, bio: str) -> int:
        """
        Analyze bio content for trustworthiness indicators.
        
        Returns:
            Score from 0-10 (higher is more trustworthy)
        """
        if not bio:
            return 3  # Neutral score for empty bio
        
        bio_lower = bio.lower()
        score = 5  # Start with neutral score
        
        # Check for suspicious keywords
        suspicious_count = sum(1 for keyword in self.suspicious_keywords 
                             if keyword in bio_lower)
        score -= suspicious_count * 2
        
        # Check for trusted keywords
        trusted_count = sum(1 for keyword in self.trusted_keywords 
                          if keyword in bio_lower)
        score += trusted_count
        
        # Check for excessive use of emojis or special characters
        emoji_pattern = r'[😀-🙏🌀-🛿✀-➿]'
        emoji_count = len(re.findall(emoji_pattern, bio))
        if emoji_count > len(bio) * 0.2:  # More than 20% emojis
            score -= 1
        
        # Check for URLs (can be positive or negative)
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, bio)
        if len(urls) > 2:
            score -= 1
        elif len(urls) == 1:
            score += 0.5  # Professional link
        
        return max(0, min(10, score))
    
    def _analyze_engagement(self, user: UserData) -> int:
        """
        Analyze engagement patterns.
        
        Returns:
            Score from 0-10 (higher is better engagement)
        """
        metrics = user.public_metrics
        followers = metrics.get('followers_count', 0)
        tweets = metrics.get('tweet_count', 0)
        
        if tweets == 0:
            return 2  # Low score for no tweets
        
        score = 5  # Start with neutral
        
        # Analyze tweet frequency
        account_age_days = self._calculate_account_age(user.created_at)
        if account_age_days > 0:
            tweets_per_day = tweets / account_age_days
            
            if tweets_per_day > 50:  # Too many tweets per day
                score -= 2
            elif tweets_per_day > 20:
                score -= 1
            elif 1 <= tweets_per_day <= 10:  # Good range
                score += 1
        
        # Analyze follower engagement
        if followers > 1000 and tweets > 100:
            score += 2
        elif followers > 100 and tweets > 50:
            score += 1
        
        return max(0, min(10, score))
    
    def _analyze_content(self, user_id: str) -> int:
        """
        Analyze recent tweet content for quality and trustworthiness.
        
        Returns:
            Score from 0-10 (higher is better content)
        """
        try:
            # Get recent tweets
            tweets = self.twitter_api.get_user_tweets(user_id, max_results=20)
            
            if not tweets:
                return 3  # Neutral score for no tweets
            
            score = 5  # Start with neutral
            
            # Analyze tweet content
            spam_indicators = 0
            quality_indicators = 0
            
            for tweet in tweets:
                text = tweet.text.lower()
                
                # Check for spam indicators
                if any(keyword in text for keyword in self.suspicious_keywords):
                    spam_indicators += 1
                
                # Check for excessive hashtags
                hashtag_count = text.count('#')
                if hashtag_count > 5:
                    spam_indicators += 1
                
                # Check for repeated content
                if len(set(tweet.text.split())) < len(tweet.text.split()) * 0.7:
                    spam_indicators += 1
                
                # Check for quality indicators
                if len(tweet.text) > 100:  # Substantial content
                    quality_indicators += 1
                
                # Check engagement on individual tweets
                metrics = tweet.public_metrics
                if metrics.get('retweet_count', 0) > 0 or metrics.get('like_count', 0) > 0:
                    quality_indicators += 1
            
            # Calculate final score
            spam_ratio = spam_indicators / len(tweets)
            quality_ratio = quality_indicators / len(tweets)
            
            score += quality_ratio * 3
            score -= spam_ratio * 4
            
            return max(0, min(10, score))
            
        except Exception as e:
            logger.error(f"Error analyzing content for user {user_id}: {e}")
            return 5  # Return neutral score on error