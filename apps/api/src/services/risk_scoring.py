"""
Risk Scoring Service
Calculates risk scores for transactions and user profiles.

Uses a combination of:
1. Transaction features (amount, type, geography)
2. User behavioral patterns
3. Historical risk indicators
4. Machine learning models (Phase 2)
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from src.models.transaction_models import (
    Transaction, UserRiskProfile, Alert, FeatureValue
)

logger = logging.getLogger(__name__)


class RiskScoringService:
    """
    Service for calculating transaction and user risk scores.
    """

    def __init__(self, db: Session):
        self.db = db

    def score_transaction(self, transaction_id: int) -> Decimal:
        """
        Calculate risk score for a transaction.

        Returns score from 0-100 where:
        - 0-30: Low risk
        - 31-60: Medium risk
        - 61-80: High risk
        - 81-100: Critical risk
        """
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()

        if not transaction:
            logger.error(f"Transaction {transaction_id} not found")
            return Decimal('0')

        score = Decimal('0')

        # 1. Amount-based scoring (0-25 points)
        score += self._score_amount(transaction)

        # 2. Geographic risk (0-25 points)
        score += self._score_geography(transaction)

        # 3. Transaction type risk (0-15 points)
        score += self._score_transaction_type(transaction)

        # 4. User behavioral risk (0-20 points)
        score += self._score_user_behavior(transaction)

        # 5. Velocity risk (0-15 points)
        score += self._score_velocity(transaction)

        return min(Decimal('100'), score)

    def _score_amount(self, transaction: Transaction) -> Decimal:
        """
        Score based on transaction amount.

        Higher amounts = higher risk (subject to thresholds).
        """
        amount = float(transaction.amount)

        if amount >= 100000:
            return Decimal('25')
        elif amount >= 50000:
            return Decimal('20')
        elif amount >= 10000:
            return Decimal('15')
        elif amount >= 5000:
            return Decimal('10')
        elif amount >= 1000:
            return Decimal('5')
        else:
            return Decimal('0')

    def _score_geography(self, transaction: Transaction) -> Decimal:
        """
        Score based on geographic risk indicators.
        """
        score = Decimal('0')

        if not transaction.country_code:
            return score

        # High-risk jurisdictions (FATF lists, sanctions)
        high_risk_countries = [
            'KP',  # North Korea
            'IR',  # Iran
            'SY',  # Syria
            'MM',  # Myanmar
            'AF',  # Afghanistan
            'YE',  # Yemen
            'IQ',  # Iraq
            'LY',  # Libya
            'SO',  # Somalia
        ]

        # Medium-risk jurisdictions
        medium_risk_countries = [
            'PK',  # Pakistan
            'TR',  # Turkey
            'AE',  # UAE
            'RU',  # Russia
            'BY',  # Belarus
        ]

        if transaction.country_code in high_risk_countries:
            score += Decimal('25')
        elif transaction.country_code in medium_risk_countries:
            score += Decimal('15')

        return score

    def _score_transaction_type(self, transaction: Transaction) -> Decimal:
        """
        Score based on transaction type.
        """
        if not transaction.transaction_type:
            return Decimal('0')

        risk_scores = {
            'withdrawal': Decimal('15'),
            'transfer': Decimal('12'),
            'cash_deposit': Decimal('10'),
            'wire_transfer': Decimal('10'),
            'payment': Decimal('5'),
            'deposit': Decimal('3')
        }

        return risk_scores.get(transaction.transaction_type, Decimal('5'))

    def _score_user_behavior(self, transaction: Transaction) -> Decimal:
        """
        Score based on user's historical behavior.
        """
        score = Decimal('0')

        # Get user risk profile
        user_profile = self.db.query(UserRiskProfile).filter(
            UserRiskProfile.user_id == transaction.user_id
        ).first()

        if not user_profile:
            # New user = slightly elevated risk
            return Decimal('5')

        # User's overall risk level
        if user_profile.risk_level == 'critical':
            score += Decimal('20')
        elif user_profile.risk_level == 'high':
            score += Decimal('15')
        elif user_profile.risk_level == 'medium':
            score += Decimal('10')

        # Enhanced due diligence flag
        if user_profile.enhanced_due_diligence:
            score += Decimal('5')

        # Sanctions match
        if user_profile.sanctions_match:
            score += Decimal('20')

        # Historical alerts
        if user_profile.critical_alerts > 0:
            score += Decimal('10')
        elif user_profile.total_alerts > 5:
            score += Decimal('5')

        return min(Decimal('20'), score)

    def _score_velocity(self, transaction: Transaction) -> Decimal:
        """
        Score based on transaction velocity (frequency/volume).
        """
        score = Decimal('0')

        # Get recent transactions (last 24 hours)
        start_time = datetime.utcnow() - timedelta(hours=24)

        recent_txs = self.db.query(Transaction).filter(
            and_(
                Transaction.user_id == transaction.user_id,
                Transaction.timestamp >= start_time,
                Transaction.id != transaction.id  # Exclude current
            )
        ).all()

        transaction_count = len(recent_txs)
        total_amount = sum(tx.amount for tx in recent_txs) + transaction.amount

        # Score based on transaction frequency
        if transaction_count >= 20:
            score += Decimal('10')
        elif transaction_count >= 10:
            score += Decimal('7')
        elif transaction_count >= 5:
            score += Decimal('4')

        # Score based on total volume
        if total_amount >= 500000:
            score += Decimal('5')
        elif total_amount >= 100000:
            score += Decimal('3')

        return min(Decimal('15'), score)

    def get_risk_level(self, risk_score: Decimal) -> str:
        """
        Convert numeric risk score to risk level category.
        """
        score = float(risk_score)

        if score >= 81:
            return 'critical'
        elif score >= 61:
            return 'high'
        elif score >= 31:
            return 'medium'
        else:
            return 'low'

    def update_user_risk_profile(self, user_id: str) -> UserRiskProfile:
        """
        Update or create user risk profile based on transaction history.
        """
        # Get or create profile
        profile = self.db.query(UserRiskProfile).filter(
            UserRiskProfile.user_id == user_id
        ).first()

        if not profile:
            profile = UserRiskProfile(user_id=user_id)
            self.db.add(profile)

        # Calculate statistics for last 30 days
        start_date = datetime.utcnow() - timedelta(days=30)

        transactions = self.db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.timestamp >= start_date
            )
        ).all()

        if transactions:
            # Transaction metrics
            profile.transaction_velocity_30d = len(transactions)
            profile.total_transaction_amount_30d = sum(tx.amount for tx in transactions)
            profile.average_transaction_amount = profile.total_transaction_amount_30d / len(transactions)

            # Calculate transaction pattern score
            profile.transaction_pattern_score = self._calculate_pattern_score(transactions)

            # Get most common country
            countries = [tx.country_code for tx in transactions if tx.country_code]
            if countries:
                profile.primary_country = max(set(countries), key=countries.count)

            # Identify high-risk jurisdictions
            high_risk = ['KP', 'IR', 'SY', 'MM', 'AF', 'YE', 'IQ', 'LY', 'SO']
            profile.high_risk_jurisdictions = list(set(c for c in countries if c in high_risk))

            # Update last activity
            profile.last_activity_at = max(tx.timestamp for tx in transactions)

        # Alert statistics
        alert_stats = self.db.query(
            func.count(Alert.id).label('total'),
            func.sum(func.case((Alert.severity == 'critical', 1), else_=0)).label('critical'),
            func.sum(func.case((Alert.status == 'resolved', 1), else_=0)).label('resolved')
        ).filter(Alert.user_id == user_id).first()

        profile.total_alerts = alert_stats.total or 0
        profile.critical_alerts = alert_stats.critical or 0
        profile.resolved_alerts = alert_stats.resolved or 0

        # Calculate overall risk score
        profile.overall_risk_score = self._calculate_user_risk_score(profile)
        profile.risk_level = self.get_risk_level(profile.overall_risk_score)

        # Build risk factors
        profile.risk_factors = self._build_risk_factors(profile)

        profile.last_calculated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Updated risk profile for user {user_id}: {profile.risk_level}")

        return profile

    def _calculate_pattern_score(self, transactions: list) -> Decimal:
        """
        Calculate a score based on transaction patterns.

        Looks for unusual patterns like:
        - Structuring (amounts just below reporting thresholds)
        - Rapid in-and-out
        - Round amounts
        """
        if not transactions:
            return Decimal('0')

        score = Decimal('0')

        amounts = [float(tx.amount) for tx in transactions]

        # Check for structuring (amounts clustered around $9,000-$9,999)
        structuring_count = sum(1 for amt in amounts if 9000 <= amt <= 9999)
        if structuring_count >= 3:
            score += Decimal('30')

        # Check for round amounts (potential money laundering indicator)
        round_count = sum(1 for amt in amounts if amt % 1000 == 0)
        round_ratio = round_count / len(amounts)
        if round_ratio > 0.7:
            score += Decimal('20')

        # Check for rapid transactions
        if len(transactions) > 20:
            score += Decimal('15')

        return min(Decimal('100'), score)

    def _calculate_user_risk_score(self, profile: UserRiskProfile) -> Decimal:
        """
        Calculate overall user risk score.
        """
        score = Decimal('0')

        # Transaction volume risk
        if profile.total_transaction_amount_30d:
            if profile.total_transaction_amount_30d > 1000000:
                score += Decimal('25')
            elif profile.total_transaction_amount_30d > 500000:
                score += Decimal('20')
            elif profile.total_transaction_amount_30d > 100000:
                score += Decimal('15')

        # Velocity risk
        if profile.transaction_velocity_30d:
            if profile.transaction_velocity_30d > 100:
                score += Decimal('20')
            elif profile.transaction_velocity_30d > 50:
                score += Decimal('15')
            elif profile.transaction_velocity_30d > 20:
                score += Decimal('10')

        # Alert history
        if profile.critical_alerts > 0:
            score += Decimal('25')
        elif profile.total_alerts > 10:
            score += Decimal('15')
        elif profile.total_alerts > 5:
            score += Decimal('10')

        # Pattern score
        if profile.transaction_pattern_score:
            score += profile.transaction_pattern_score * Decimal('0.2')

        # Geographic risk
        if profile.high_risk_jurisdictions:
            score += Decimal('15')

        # Sanctions
        if profile.sanctions_match:
            score += Decimal('30')

        # Enhanced due diligence
        if profile.enhanced_due_diligence:
            score += Decimal('10')

        return min(Decimal('100'), score)

    def _build_risk_factors(self, profile: UserRiskProfile) -> Dict[str, Any]:
        """
        Build a dictionary of risk factors for the user.
        """
        factors = {}

        if profile.total_transaction_amount_30d and profile.total_transaction_amount_30d > 100000:
            factors['high_volume'] = f"${profile.total_transaction_amount_30d:,.2f} in 30 days"

        if profile.transaction_velocity_30d and profile.transaction_velocity_30d > 20:
            factors['high_velocity'] = f"{profile.transaction_velocity_30d} transactions in 30 days"

        if profile.critical_alerts > 0:
            factors['critical_alerts'] = f"{profile.critical_alerts} critical alerts"

        if profile.high_risk_jurisdictions:
            factors['high_risk_countries'] = profile.high_risk_jurisdictions

        if profile.sanctions_match:
            factors['sanctions_match'] = "User matched sanctions list"

        if profile.enhanced_due_diligence:
            factors['edd_required'] = "Enhanced due diligence required"

        if profile.transaction_pattern_score and profile.transaction_pattern_score > 30:
            factors['suspicious_patterns'] = "Unusual transaction patterns detected"

        return factors
