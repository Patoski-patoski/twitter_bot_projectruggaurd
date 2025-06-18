# analysis.py
"""
Account Analysis Module for Project RUGGUARD
Analyzes Twitter accounts for trustworthiness indicators.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from dataclasses import dataclass

from bot.twitter_api import TweetData

from .twitter_api import TwitterAPIHandler, UserData

logger: logging.Logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Data class for analysis results."""
    account_age_days: int
    follower_following_ratio: float
    bio_score: int
    engagement_score: int
    content_score: int | float
    overall_risk_score: int
    flags: List[str]
    recommendations: List[str]

class AccountAnalyzer:
    """Analyzes Twitter accounts for trustworthiness indicators."""
    
    def __init__(self, twitter_api: TwitterAPIHandler) -> None:
        self.twitter_api: TwitterAPIHandler = twitter_api
        
        self.suspicious_keywords: List[str] = [
            'guaranteed', 'risk-free', 'get rich', 'easy money', 'moonshot',
            'to the moon', '100x', 'guaranteed returns', 'no risk',
            'quick profit', 'instant wealth', 'diamond hands', 'hodl'
        ]
        
        self.trusted_keywords: List[str] = [
            'developer', 'engineer', 'founder', 'ceo', 'cto', 'researcher',
            'university', 'phd', 'professor', 'verified', 'official'
        ]
    
    def analyze_account(self, user: UserData) -> AnalysisResult:
        """Perform comprehensive analysis of a Twitter account."""
        logger.info(f"Starting analysis for @{user.username}")
        
        flags = []
        recommendations = []
        
        # Analyze account age
        account_age_days: int = self._calculate_account_age(user.created_at)
        if account_age_days < 30:
            flags.append("Very new account (less than 30 days)")
        elif account_age_days < 90:
            flags.append("New account (less than 90 days)")
        
        # Analyze follower/following ratio
        follower_following_ratio: float = self._calculate_follower_ratio(user.public_metrics)
        if follower_following_ratio < 0.1:
            flags.append("Low follower-to-following ratio")
        elif follower_following_ratio > 10:
            recommendations.append("Good follower-to-following ratio")
        
        # Analyze bio content
        bio_score: int = self._analyze_bio(user.description)
        if bio_score < 3:
            flags.append("Bio contains suspicious content")
        elif bio_score > 7:
            recommendations.append("Professional bio content")
        
        # Analyze engagement patterns
        engagement_score: int = self._analyze_engagement(user)
        if engagement_score < 3:
            flags.append("Low engagement patterns")
        elif engagement_score > 7:
            recommendations.append("Good engagement patterns")
        
        # Analyze recent content
        content_score: int | float = self._analyze_content(user.id)
        if content_score < 3:
            flags.append("Suspicious content patterns")
        elif content_score > 7:
            recommendations.append("Quality content")
        
        # Calculate overall risk score
        risk_factors = []
        if account_age_days < 30:
            risk_factors.append(3)
        elif account_age_days < 90:
            risk_factors.append(2)
        
        if follower_following_ratio < 0.1:
            risk_factors.append(2)
        elif follower_following_ratio < 0.5:
            risk_factors.append(1)
        
        risk_factors.append(max(0, 5 - bio_score))
        risk_factors.append(max(0, 5 - engagement_score))
        risk_factors.append(max(0, 5 - content_score))
        
        overall_risk_score: int = min(10, sum(risk_factors))
        
        return AnalysisResult(
            account_age_days=account_age_days,
            follower_following_ratio=follower_following_ratio,
            bio_score=bio_score,
            engagement_score=engagement_score,
            content_score=content_score,
            overall_risk_score=overall_risk_score,
            flags=flags,
            recommendations=recommendations
        )
    
    def _calculate_account_age(self, created_at: datetime) -> int:
        """Calculate account age in days."""
        try:
            now: datetime = datetime.now(timezone.utc)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age: timedelta = now - created_at
            return age.days
        except Exception as e:
            logger.error(f"Error calculating account age: {e}")
            return 0
    
    def _calculate_follower_ratio(self, metrics: Dict[str, int]) -> float:
        """Calculate follower-to-following ratio."""
        followers: int = metrics.get('followers_count', 0)
        following: int = metrics.get('following_count', 1)
        
        if following == 0:
            return int('inf') if followers > 0 else 0
        
        return followers / following
    
    def _analyze_bio(self, bio: str) -> int:
        """Analyze bio content for trustworthiness indicators."""
        if not bio:
            return 5
        
        bio_lower: str = bio.lower()
        score = 5
        
        # Check for suspicious keywords
        suspicious_count: int = sum(1 for keyword in self.suspicious_keywords if keyword in bio_lower)
        score -= suspicious_count * 2
        
        # Check for trusted keywords
        trusted_count: int = sum(1 for keyword in self.trusted_keywords if keyword in bio_lower)
        score += trusted_count
        
        return max(0, min(10, score))
    
    def _analyze_engagement(self, user: UserData) -> int:
        """Analyze engagement patterns."""
        metrics: Dict[str, int] = user.public_metrics
        followers: int = metrics.get('followers_count', 0)
        tweets: int = metrics.get('tweet_count', 0)
        
        if tweets == 0:
            return 2
        
        score = 5
        
        # Analyze tweet frequency
        account_age_days: int = self._calculate_account_age(user.created_at)
        if account_age_days > 0:
            tweets_per_day: float = tweets / account_age_days
            
            if tweets_per_day > 50:
                score -= 2
            elif tweets_per_day > 20:
                score -= 1
            elif 1 <= tweets_per_day <= 10:
                score += 1
        
        # Analyze follower engagement
        if followers > 1000 and tweets > 100:
            score += 2
        elif followers > 100 and tweets > 50:
            score += 1
        
        return max(0, min(10, score))
    
    def _analyze_content(self, user_id: str) -> int | float:
        """Analyze recent tweet content."""
        try:
            tweets: List[TweetData] = self.twitter_api.get_user_tweets(user_id, max_results=20)
            
            if not tweets:
                return 5
            
            score = 5
            spam_indicators = 0
            quality_indicators = 0
            
            for tweet in tweets:
                text: str = tweet.text.lower()
                
                if any(keyword in text for keyword in self.suspicious_keywords):
                    spam_indicators += 1
                
                hashtag_count: int = text.count('#')
                if hashtag_count > 5:
                    spam_indicators += 1
                
                if len(tweet.text) > 100:
                    quality_indicators += 1
                
                metrics: Dict[str, int] = tweet.public_metrics
                if metrics.get('retweet_count', 0) > 0 or metrics.get('like_count', 0) > 0:
                    quality_indicators += 1
            
            spam_ratio: float = spam_indicators / len(tweets)
            quality_ratio: float = quality_indicators / len(tweets)
            
            score += quality_ratio * 3
            score -= spam_ratio * 4
            
            return max(0, min(10, score))
            
        except Exception as e:
            logger.error(f"Error analyzing content for user {user_id}: {e}")
            return 5
        