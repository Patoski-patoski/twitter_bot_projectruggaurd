"""
Report Generator for Project RUGGUARD
Generates trustworthiness reports based on analysis results.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

from .twitter_api import UserData
from .analysis import AnalysisResult

logger: logging.Logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates trustworthiness reports for analyzed accounts."""

    def __init__(self) -> None:
        """Initialize the report generator."""
        self.max_tweet_length = 280

    def generate_report(
        self, user: UserData, analysis: AnalysisResult, trust_score: Dict
    ) -> str:
        """
        Generate a comprehensive trustworthiness report.

        Args:
            user: UserData object
            analysis: AnalysisResult object
            trust_score: Trust score from trusted accounts check

        Returns:
            Formatted report string suitable for posting as a tweet
        """
        logger.info(f"Generating report for @{user.username}")

        # Determine overall trust level
        trust_level = self._calculate_trust_level(analysis, trust_score)

        # Generate the main report
        report_parts = []

        # Header with trust level
        header = f"🔍 RUGGUARD ANALYSIS: @{user.username}\n"
        report_parts.append(header)

        # Trust level indicator
        trust_indicator = self._get_trust_indicator(trust_level)
        report_parts.append(f"{trust_indicator}\n")

        # Key metrics
        metrics = self._format_key_metrics(user, analysis)
        report_parts.append(metrics)

        # Trusted network status
        if trust_score.get("is_vouched", False):
            report_parts.append("✅ Vouched by trusted network\n")
        elif trust_score.get("trust_connections", 0) > 0:
            count = trust_score["trust_connections"]
            report_parts.append(f"🤝 {count} trusted connections\n")

        # Warning flags
        if analysis.flags:
            flag_text = self._format_flags(analysis.flags)
            if flag_text:
                report_parts.append(flag_text)

        # Recommendations
        if analysis.recommendations:
            rec_text = self._format_recommendations(analysis.recommendations)
            if rec_text:
                report_parts.append(rec_text)

        # Footer
        footer = "\n#RUGGUARD #DeFiSafety #DYOR"

        # Combine and ensure it fits in tweet length
        full_report: str = "".join(report_parts) + footer

        # Truncate if necessary
        if len(full_report) > self.max_tweet_length:
            full_report = self._truncate_report(report_parts, footer)

        logger.info(
            f"Report generated for @{user.username}: {len(full_report)} characters"
        )
        return full_report

    def _calculate_trust_level(
        self, analysis: AnalysisResult, trust_score: Dict
    ) -> str:
        """
        Calculate overall trust level based on analysis and trust score.

        Returns:
            Trust level string: 'HIGH', 'MEDIUM', 'LOW', or 'CRITICAL'
        """
        # Start with analysis risk score (0-10, where 10 is highest risk)
        risk_score: int = analysis.overall_risk_score

        # Adjust based on trust network
        if trust_score.get("is_vouched", False):
            risk_score = max(0, risk_score - 4)  # Significant trust boost
        elif trust_score.get("trust_connections", 0) >= 2:
            risk_score = max(0, risk_score - 2)  # Moderate trust boost
        elif trust_score.get("trust_connections", 0) >= 1:
            risk_score = max(0, risk_score - 1)  # Small trust boost

        # Determine trust level
        if risk_score <= 2:
            return "HIGH"
        elif risk_score <= 4:
            return "MEDIUM"
        elif risk_score <= 7:
            return "LOW"
        else:
            return "CRITICAL"

    def _get_trust_indicator(self, trust_level: str) -> str:
        """Get emoji indicator for trust level."""
        indicators: Dict[str, str] = {
            "HIGH": "🟢 HIGH TRUST",
            "MEDIUM": "🟡 MEDIUM TRUST",
            "LOW": "🟠 LOW TRUST",
            "CRITICAL": "🔴 HIGH RISK",
        }
        return indicators.get(trust_level, "⚪ UNKNOWN")

    def _format_key_metrics(self, user: UserData, analysis: AnalysisResult) -> str:
        """Format key metrics for the report."""
        metrics: list[Any] = []

        # Account age
        age_days: int = analysis.account_age_days
        if age_days < 30:
            age_str = f"📅 {age_days}d old (NEW)"
        elif age_days < 365:
            age_str = f"📅 {age_days}d old"
        else:
            years: int = age_days // 365
            age_str: str = f"📅 {years}y old"
        metrics.append(age_str)

        # Followers
        followers: int = user.public_metrics.get("followers_count", 0)
        if followers >= 1000000:
            follower_str = f"👥 {followers // 1000000:.1f}M followers"
        elif followers >= 1000:
            follower_str: str = f"👥 {followers // 1000:.1f}K followers"
        else:
            follower_str = f"👥 {followers} followers"
        metrics.append(follower_str)

        # Follower ratio
        ratio: float = analysis.follower_following_ratio
        if ratio >= 10:
            ratio_str = "📊 Great ratio"
        elif ratio >= 1:
            ratio_str = f"📊 {ratio:.1f}:1 ratio"
        else:
            ratio_str: str = f"📊 {ratio:.2f}:1 ratio"
        metrics.append(ratio_str)

        return " | ".join(metrics) + "\n"

    def _format_flags(self, flags: List[str]) -> str:
        """Format warning flags for the report."""
        if not flags:
            return ""

        # Limit to most important flags
        important_flags: List[str] = flags[:2]
        flag_text: str = "⚠️ " + " | ".join(important_flags)

        if len(flags) > 2:
            flag_text += f" (+{len(flags) - 2} more)"

        return flag_text + "\n"

    def _format_recommendations(self, recommendations: List[str]) -> str:
        """Format recommendations for the report."""
        if not recommendations:
            return ""

        # Limit to most important recommendations
        important_recs: List[str] = recommendations[:1]
        rec_text: str = "✅ " + " | ".join(important_recs)

        return rec_text + "\n"

    def _truncate_report(self, report_parts: List[str], footer: str) -> str:
        """
        Truncate report to fit Twitter character limit.

        Args:
            report_parts: List of report sections
            footer: Footer text

        Returns:
            Truncated report string
        """
        # Essential parts that must be included
        essential_parts: List[str] = [report_parts[0], report_parts[1]]  # Header and trust level

        # Calculate available space
        essential_length: int = len("".join(essential_parts)) + len(footer)
        available_space: int = (
            self.max_tweet_length - essential_length - 10
        )  # Buffer for "..."

        # Add optional parts until we run out of space
        optional_parts: list[str] = report_parts[2:]
        truncated_parts:list[str] = essential_parts.copy()

        for part in optional_parts:
            if len(part) <= available_space:
                truncated_parts.append(part)
                available_space -= len(part)
            else:
                break

        # Add truncation indicator if needed
        if len(optional_parts) > len(truncated_parts) - 2:
            if available_space > 5:
                truncated_parts.append("...")

        return "".join(truncated_parts) + footer

    def generate_error_report(self, username: str, error_type: str = "analysis") -> str:
        """
        Generate an error report when analysis fails.

        Args:
            username: Username that failed analysis
            error_type: Type of error that occurred

        Returns:
            Error report string
        """
        error_messages: dict[str, str] = {
            "analysis": "❌ Analysis failed - please try again later",
            "not_found": "❌ Account not found or private",
            "rate_limit": "⏰ Rate limited - please wait before next request",
            "api_error": "❌ API error - please try again later",
        }

        message = error_messages.get(error_type, "❌ Unknown error occurred")

        return f"🔍 RUGGUARD: @{username}\n{message}\n\n#RUGGUARD #DeFiSafety"

    def generate_vouched_report(self, user: UserData, vouched_by: List[str]) -> str:
        """
        Generate a special report for vouched accounts.

        Args:
            user: UserData object
            vouched_by: List of trusted accounts that vouch for this user

        Returns:
            Vouched account report string
        """
        voucher_text = ", ".join(vouched_by[:3])  # Show up to 3 vouchers
        if len(vouched_by) > 3:
            voucher_text += f" +{len(vouched_by) - 3} more"

        followers = user.public_metrics.get("followers_count", 0)
        if followers >= 1000:
            follower_str = f"{followers // 1000:.1f}K"
        else:
            follower_str = str(followers)

        age_days = (datetime.now() - datetime.fromisoformat(user.created_at)).days
        if age_days >= 365:
            age_str = f"{age_days // 365}y"
        else:
            age_str = f"{age_days}d"

        report = f"""🔍 RUGGUARD: @{user.username}
🟢 TRUSTED ACCOUNT
✅ Vouched by: {voucher_text}
👥 {follower_str} followers | 📅 {age_str} old

This account is vouched for by trusted community members.

#RUGGUARD #DeFiSafety #Trusted"""

        return report
