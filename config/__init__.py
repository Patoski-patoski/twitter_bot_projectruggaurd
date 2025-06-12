# config/__init__.py
"""
Configuration Module for Project RUGGUARD
Contains configuration management and trusted accounts handling.
"""
from .trusted_accounts import TrustedAccountsManager, TrustScore


__all__: list[str] = ["TrustedAccountsManager", "TrustScore"]
