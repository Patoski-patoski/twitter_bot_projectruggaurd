# bot/__init__.py
"""
Bot Logic Module for Project RUGGUARD
Contains core functionality for Twitter bot operations.
"""
from .twitter_api import TwitterAPIHandler, TweetData, UserData
from .analysis import AccountAnalyzer, AnalysisResult
from .report_generator import ReportGenerator

__all__ = [
    "TwitterAPIHandler",
    "TweetData",
    "UserData",
    "AccountAnalyzer",
    "AnalysisResult",
    "ReportGenerator",
]