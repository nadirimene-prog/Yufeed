"""
Time-Series Feature Engineering
Phase 4B: Task 5.1 - Advanced Time-Series Features

Computes sophisticated temporal features for ML models:
- Rolling window aggregations
- Trend detection (slopes)
- Z-scores for anomaly detection
- Exponential moving averages (EMA)
- Seasonality patterns (hourly, daily, weekly)
- Velocity acceleration
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta

from collections import defaultdict
from datetime import timezone

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.transaction_models import Transaction

logger = logging.getLogger(__name__)


class TimeSeriesFeatureExtractor:
    """
    Extract time-series features from transaction history.

    Features include:
    - Rolling window aggregations (sum, count, mean, std)
    - Trend features (slopes, acceleration)
    - Z-scores for anomaly detection
    - Exponential moving averages
    - Seasonality scores
    """

    def __init__(self, db: Session):
        self.db = db

    def extract_features(
        self, tenant_id: str, user_id: str, current_time: datetime, lookback_days: int = 90
    ) -> Dict[str, float]:
        """
        Extract all time-series features for a user.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            current_time: Reference time for feature calculation
            lookback_days: Historical window in days

        Returns:
            Dictionary of feature names to values
        """
        # DB timestamps are stored as naive datetimes; normalize inputs to naive UTC for comparisons.
        if current_time.tzinfo is not None:
            current_time = current_time.astimezone(timezone.utc).replace(tzinfo=None)

        start_time = current_time - timedelta(days=lookback_days)

        # Get user transactions
        transactions = (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.tenant_id == tenant_id,
                    Transaction.user_id == user_id,
                    Transaction.timestamp >= start_time,
                    Transaction.timestamp < current_time,
                )
            )
            .order_by(Transaction.timestamp.asc())
            .all()
        )

        if not transactions:
            return self._default_features()

        # Extract features
        features = {}

        # Rolling window features
        features.update(self._compute_rolling_windows(transactions, current_time))

        # Trend features
        features.update(self._compute_trends(transactions, current_time))

        # Z-scores
        features.update(self._compute_zscores(transactions))

        # Exponential moving averages
        features.update(self._compute_ema(transactions, current_time))

        # Seasonality features
        features.update(self._compute_seasonality(transactions, current_time))

        # Velocity acceleration
        features.update(self._compute_velocity_acceleration(transactions, current_time))

        return features

    def _compute_rolling_windows(
        self, transactions: List[Transaction], current_time: datetime
    ) -> Dict[str, float]:
        """
        Compute rolling window aggregations.

        Windows: 1h, 6h, 24h, 7d, 30d
        Metrics: count, sum, mean, std, max
        """
        features = {}

        windows = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }

        for window_name, window_delta in windows.items():
            window_start = current_time - window_delta

            # Filter transactions in window
            window_txns = [tx for tx in transactions if tx.timestamp >= window_start]

            if not window_txns:
                features[f"velocity_{window_name}_count"] = 0
                features[f"velocity_{window_name}_sum"] = 0.0
                features[f"velocity_{window_name}_mean"] = 0.0
                features[f"velocity_{window_name}_std"] = 0.0
                features[f"velocity_{window_name}_max"] = 0.0
                continue

            amounts = [float(tx.amount) for tx in window_txns]

            features[f"velocity_{window_name}_count"] = len(window_txns)
            features[f"velocity_{window_name}_sum"] = sum(amounts)
            features[f"velocity_{window_name}_mean"] = np.mean(amounts)
            features[f"velocity_{window_name}_std"] = np.std(amounts) if len(amounts) > 1 else 0.0
            features[f"velocity_{window_name}_max"] = max(amounts)

        return features

    def _compute_trends(
        self, transactions: List[Transaction], current_time: datetime
    ) -> Dict[str, float]:
        """
        Compute trend features using linear regression.

        Features:
        - velocity_trend_24h: Transaction count slope over last 24h
        - amount_trend_7d: Amount slope over last 7 days
        - amount_trend_30d: Amount slope over last 30 days
        """
        features = {}

        # 24h transaction count trend
        window_24h = current_time - timedelta(hours=24)
        txns_24h = [tx for tx in transactions if tx.timestamp >= window_24h]

        if len(txns_24h) >= 2:
            # Compute hourly counts
            hourly_counts = defaultdict(int)
            for tx in txns_24h:
                hour = tx.timestamp.hour
                hourly_counts[hour] += 1

            # Linear regression on counts
            hours = list(hourly_counts.keys())
            counts = [hourly_counts[h] for h in hours]

            if len(hours) >= 2:
                slope = self._linear_slope(hours, counts)
                features["velocity_trend_24h"] = slope
            else:
                features["velocity_trend_24h"] = 0.0
        else:
            features["velocity_trend_24h"] = 0.0

        # 7-day amount trend
        window_7d = current_time - timedelta(days=7)
        txns_7d = [tx for tx in transactions if tx.timestamp >= window_7d]

        if len(txns_7d) >= 2:
            # Group by day
            daily_amounts = defaultdict(float)
            for tx in txns_7d:
                day = tx.timestamp.date()
                daily_amounts[day] += float(tx.amount)

            days = sorted(daily_amounts.keys())
            amounts = [daily_amounts[d] for d in days]

            if len(days) >= 2:
                # Convert dates to numeric (days since first)
                day_nums = [(d - days[0]).days for d in days]
                slope = self._linear_slope(day_nums, amounts)
                features["amount_trend_7d"] = slope
            else:
                features["amount_trend_7d"] = 0.0
        else:
            features["amount_trend_7d"] = 0.0

        # 30-day amount trend
        window_30d = current_time - timedelta(days=30)
        txns_30d = [tx for tx in transactions if tx.timestamp >= window_30d]

        if len(txns_30d) >= 2:
            daily_amounts = defaultdict(float)
            for tx in txns_30d:
                day = tx.timestamp.date()
                daily_amounts[day] += float(tx.amount)

            days = sorted(daily_amounts.keys())
            amounts = [daily_amounts[d] for d in days]

            if len(days) >= 2:
                day_nums = [(d - days[0]).days for d in days]
                slope = self._linear_slope(day_nums, amounts)
                features["amount_trend_30d"] = slope
            else:
                features["amount_trend_30d"] = 0.0
        else:
            features["amount_trend_30d"] = 0.0

        return features

    def _compute_zscores(self, transactions: List[Transaction]) -> Dict[str, float]:
        """
        Compute Z-scores for anomaly detection.

        Z-score = (value - mean) / std
        """
        features = {}

        if not transactions:
            return {
                "amount_zscore_last": 0.0,
                "amount_zscore_max_30d": 0.0,
            }

        amounts = [float(tx.amount) for tx in transactions]
        mean_amount = np.mean(amounts)
        std_amount = np.std(amounts) if len(amounts) > 1 else 1.0

        # Z-score of last transaction
        if std_amount > 0:
            last_amount = amounts[-1]
            features["amount_zscore_last"] = (last_amount - mean_amount) / std_amount
        else:
            features["amount_zscore_last"] = 0.0

        # Maximum Z-score in last 30 days
        zscores = (
            [(amt - mean_amount) / std_amount for amt in amounts]
            if std_amount > 0
            else [0.0] * len(amounts)
        )
        features["amount_zscore_max_30d"] = max(zscores) if zscores else 0.0

        return features

    def _compute_ema(
        self, transactions: List[Transaction], current_time: datetime
    ) -> Dict[str, float]:
        """
        Compute Exponential Moving Averages.

        EMA gives more weight to recent transactions.
        """
        features = {}

        if not transactions:
            return {
                "amount_ema_7d": 0.0,
                "amount_ema_30d": 0.0,
                "amount_ema_ratio": 1.0,
            }

        # 7-day EMA
        window_7d = current_time - timedelta(days=7)
        txns_7d = [tx for tx in transactions if tx.timestamp >= window_7d]

        if txns_7d:
            ema_7d = self._calculate_ema([float(tx.amount) for tx in txns_7d], span=7)
            features["amount_ema_7d"] = ema_7d
        else:
            features["amount_ema_7d"] = 0.0

        # 30-day EMA
        window_30d = current_time - timedelta(days=30)
        txns_30d = [tx for tx in transactions if tx.timestamp >= window_30d]

        if txns_30d:
            ema_30d = self._calculate_ema([float(tx.amount) for tx in txns_30d], span=30)
            features["amount_ema_30d"] = ema_30d
        else:
            features["amount_ema_30d"] = 0.0

        # Ratio of short-term to long-term EMA (trend indicator)
        if features["amount_ema_30d"] > 0:
            features["amount_ema_ratio"] = features["amount_ema_7d"] / features["amount_ema_30d"]
        else:
            features["amount_ema_ratio"] = 1.0

        return features

    def _compute_seasonality(
        self, transactions: List[Transaction], current_time: datetime
    ) -> Dict[str, float]:
        """
        Compute seasonality scores.

        Measures deviation from typical hourly/daily/weekly patterns.
        """
        features = {}

        if not transactions:
            return {
                "hourly_pattern_score": 0.0,
                "weekly_pattern_score": 0.0,
                "is_weekend": 0.0,
                "is_business_hours": 0.0,
            }

        # Current hour and day
        current_hour = current_time.hour
        current_weekday = current_time.weekday()  # 0=Monday, 6=Sunday

        # Compute hourly distribution
        hourly_counts = defaultdict(int)
        for tx in transactions:
            hourly_counts[tx.timestamp.hour] += 1

        avg_hourly_count = np.mean(list(hourly_counts.values())) if hourly_counts else 0
        current_hour_count = hourly_counts.get(current_hour, 0)

        # Hourly pattern score (how unusual is this hour?)
        if avg_hourly_count > 0:
            features["hourly_pattern_score"] = (current_hour_count - avg_hourly_count) / (
                avg_hourly_count + 1
            )
        else:
            features["hourly_pattern_score"] = 0.0

        # Weekly distribution
        weekly_counts = defaultdict(int)
        for tx in transactions:
            weekly_counts[tx.timestamp.weekday()] += 1

        avg_weekly_count = np.mean(list(weekly_counts.values())) if weekly_counts else 0
        current_day_count = weekly_counts.get(current_weekday, 0)

        # Weekly pattern score
        if avg_weekly_count > 0:
            features["weekly_pattern_score"] = (current_day_count - avg_weekly_count) / (
                avg_weekly_count + 1
            )
        else:
            features["weekly_pattern_score"] = 0.0

        # Weekend indicator
        features["is_weekend"] = 1.0 if current_weekday >= 5 else 0.0

        # Business hours indicator (9 AM - 5 PM)
        features["is_business_hours"] = 1.0 if 9 <= current_hour < 17 else 0.0

        return features

    def _compute_velocity_acceleration(
        self, transactions: List[Transaction], current_time: datetime
    ) -> Dict[str, float]:
        """
        Compute velocity acceleration (change in velocity trend).

        Acceleration = (velocity_recent - velocity_older) / time_delta
        """
        features = {}

        # Split into two periods: last 12h and previous 12h
        window_12h_recent = current_time - timedelta(hours=12)
        window_24h = current_time - timedelta(hours=24)

        txns_recent = [tx for tx in transactions if tx.timestamp >= window_12h_recent]
        txns_older = [tx for tx in transactions if window_24h <= tx.timestamp < window_12h_recent]

        velocity_recent = len(txns_recent) / 12.0  # txns per hour
        velocity_older = len(txns_older) / 12.0

        # Acceleration (change in velocity)
        features["velocity_acceleration"] = velocity_recent - velocity_older

        return features

    # Helper methods

    def _linear_slope(self, x: List[float], y: List[float]) -> float:
        """
        Compute slope of linear regression line.

        slope = cov(x,y) / var(x)
        """
        if len(x) < 2:
            return 0.0

        x_arr = np.array(x)
        y_arr = np.array(y)

        try:
            slope = np.cov(x_arr, y_arr)[0, 1] / np.var(x_arr)
            return float(slope) if not np.isnan(slope) else 0.0
        except Exception:
            return 0.0

    def _calculate_ema(self, values: List[float], span: int) -> float:
        """
        Calculate Exponential Moving Average.

        EMA_t = α * value_t + (1-α) * EMA_(t-1)
        where α = 2 / (span + 1)
        """
        if not values:
            return 0.0

        alpha = 2.0 / (span + 1)
        ema = values[0]

        for value in values[1:]:
            ema = alpha * value + (1 - alpha) * ema

        return ema

    def _default_features(self) -> Dict[str, float]:
        """Return default feature values when no transactions exist."""
        return {
            # Rolling windows
            "velocity_1h_count": 0,
            "velocity_1h_sum": 0.0,
            "velocity_1h_mean": 0.0,
            "velocity_1h_std": 0.0,
            "velocity_1h_max": 0.0,
            "velocity_6h_count": 0,
            "velocity_6h_sum": 0.0,
            "velocity_6h_mean": 0.0,
            "velocity_6h_std": 0.0,
            "velocity_6h_max": 0.0,
            "velocity_24h_count": 0,
            "velocity_24h_sum": 0.0,
            "velocity_24h_mean": 0.0,
            "velocity_24h_std": 0.0,
            "velocity_24h_max": 0.0,
            "velocity_7d_count": 0,
            "velocity_7d_sum": 0.0,
            "velocity_7d_mean": 0.0,
            "velocity_7d_std": 0.0,
            "velocity_7d_max": 0.0,
            "velocity_30d_count": 0,
            "velocity_30d_sum": 0.0,
            "velocity_30d_mean": 0.0,
            "velocity_30d_std": 0.0,
            "velocity_30d_max": 0.0,
            # Trends
            "velocity_trend_24h": 0.0,
            "amount_trend_7d": 0.0,
            "amount_trend_30d": 0.0,
            # Z-scores
            "amount_zscore_last": 0.0,
            "amount_zscore_max_30d": 0.0,
            # EMA
            "amount_ema_7d": 0.0,
            "amount_ema_30d": 0.0,
            "amount_ema_ratio": 1.0,
            # Seasonality
            "hourly_pattern_score": 0.0,
            "weekly_pattern_score": 0.0,
            "is_weekend": 0.0,
            "is_business_hours": 0.0,
            # Acceleration
            "velocity_acceleration": 0.0,
        }
