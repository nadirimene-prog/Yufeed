"""
Dataset builder for alert triage ML model.
Phase 4B: Task 4.1 - Historical Data Analysis
"""

import logging
import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.transaction_models import Alert, Transaction, RuleHit
from src.models.models import LegalDocument

logger = logging.getLogger(__name__)


class AlertTriageDatasetBuilder:
    """
    Build labeled training dataset from historical alerts.

    Features:
    - Alert metadata (type, severity, risk_score)
    - Transaction features (amount, currency, country)
    - User behavior features (velocity, volume)
    - Rule matching patterns
    - Temporal features (day of week, hour)
    """

    def __init__(self, db: Session):
        self.db = db

    def extract_historical_data(
        self, start_date: datetime, end_date: datetime, min_alerts: int = 100
    ) -> pd.DataFrame:
        """
        Extract historical alert data with outcomes.

        Args:
            start_date: Start date for historical data
            end_date: End date for historical data
            min_alerts: Minimum number of alerts required

        Returns:
            DataFrame with features and labels
        """
        logger.info(f"Extracting historical alerts from {start_date} to {end_date}")

        # Query resolved alerts with known outcomes
        alerts = (
            self.db.query(Alert)
            .filter(
                Alert.created_at >= start_date,
                Alert.created_at <= end_date,
                Alert.status == "resolved",
                Alert.resolution_status.in_(["false_positive", "confirmed", "sar_filed"]),
            )
            .all()
        )

        if len(alerts) < min_alerts:
            raise ValueError(
                f"Insufficient historical data: {len(alerts)} alerts found, "
                f"minimum {min_alerts} required"
            )

        logger.info(f"Extracted {len(alerts)} resolved alerts")

        # Build feature matrix
        features = []

        for alert in alerts:
            feature_dict = self._extract_features(alert)
            features.append(feature_dict)

        df = pd.DataFrame(features)

        logger.info(f"Dataset shape: {df.shape}")
        logger.info(f"Label distribution:\n{df['label'].value_counts()}")

        return df

    def _extract_features(self, alert: Alert) -> Dict[str, Any]:
        """
        Extract features from a single alert.
        """
        features = {}

        # Alert metadata features
        features["alert_id"] = alert.alert_id
        features["alert_type"] = alert.alert_type
        features["severity"] = alert.severity
        features["risk_score"] = float(alert.risk_score) if alert.risk_score else 0.0
        features["priority"] = alert.priority

        # Temporal features
        if alert.created_at:
            features["hour_of_day"] = alert.created_at.hour
            features["day_of_week"] = alert.created_at.weekday()
            features["is_weekend"] = int(alert.created_at.weekday() >= 5)

        # Transaction features
        if alert.transaction:
            txn = alert.transaction
            features["transaction_amount"] = float(txn.amount)
            features["currency"] = txn.currency
            features["transaction_type"] = txn.transaction_type
            features["country_code"] = txn.country_code or "UNKNOWN"
            features["has_counterparty"] = int(txn.counterparty_id is not None)
        else:
            # No transaction - fill with defaults
            features["transaction_amount"] = 0.0
            features["currency"] = "UNKNOWN"
            features["transaction_type"] = "UNKNOWN"
            features["country_code"] = "UNKNOWN"
            features["has_counterparty"] = 0

        # User behavior features (computed from historical transactions)
        if alert.user_id:
            user_features = self._compute_user_features(alert.user_id, alert.created_at)
            features.update(user_features)

        # Rule matching features
        rule_features = self._extract_rule_features(alert)
        features.update(rule_features)

        # Evidence features
        if alert.evidence:
            features["evidence_count"] = (
                len(alert.evidence) if isinstance(alert.evidence, dict) else 0
            )
        else:
            features["evidence_count"] = 0

        # Label: SAR filed = True Positive, False Positive = False Positive
        if alert.resolution_status == "sar_filed":
            features["label"] = 1  # True Positive
        elif alert.resolution_status == "confirmed":
            features["label"] = 1  # True Positive
        else:  # false_positive
            features["label"] = 0  # False Positive

        return features

    def _compute_user_features(self, user_id: str, alert_time: datetime) -> Dict[str, float]:
        """
        Compute user behavior features at the time of alert.
        """
        # Get transactions in past 30 days
        lookback_start = alert_time - timedelta(days=30)

        transactions = (
            self.db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.timestamp >= lookback_start,
                Transaction.timestamp < alert_time,
            )
            .all()
        )

        if not transactions:
            return {
                "user_txn_count_30d": 0,
                "user_total_volume_30d": 0.0,
                "user_avg_amount": 0.0,
                "user_unique_countries": 0,
                "user_prior_alerts": 0,
            }

        # Velocity features
        txn_count_30d = len(transactions)
        total_volume = sum(float(t.amount) for t in transactions)
        avg_amount = total_volume / txn_count_30d if txn_count_30d > 0 else 0

        # Geographic diversity
        unique_countries = len(set(t.country_code for t in transactions if t.country_code))

        # Prior alerts
        prior_alerts = (
            self.db.query(Alert)
            .filter(Alert.user_id == user_id, Alert.created_at < alert_time)
            .count()
        )

        return {
            "user_txn_count_30d": txn_count_30d,
            "user_total_volume_30d": total_volume,
            "user_avg_amount": avg_amount,
            "user_unique_countries": unique_countries,
            "user_prior_alerts": prior_alerts,
        }

    def _extract_rule_features(self, alert: Alert) -> Dict[str, Any]:
        """
        Extract features from matched rules.
        """
        if not alert.matched_rules_data:
            return {"num_rules_matched": 0, "has_high_severity_rule": 0, "has_velocity_rule": 0}

        rules_data = alert.matched_rules_data if isinstance(alert.matched_rules_data, list) else []

        num_rules = len(rules_data)

        # Check for specific rule types
        has_high_severity = any(
            r.get("severity") in ["high", "critical"] for r in rules_data if isinstance(r, dict)
        )

        has_velocity = any(
            "velocity" in str(r.get("rule_name", "")).lower()
            for r in rules_data
            if isinstance(r, dict)
        )

        return {
            "num_rules_matched": num_rules,
            "has_high_severity_rule": int(has_high_severity),
            "has_velocity_rule": int(has_velocity),
        }

    def analyze_false_positives(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze patterns in false positive alerts.

        Args:
            df: Dataset with features and labels

        Returns:
            Analysis results with common patterns
        """
        false_positives = df[df["label"] == 0]
        true_positives = df[df["label"] == 1]

        analysis = {
            "total_alerts": len(df),
            "false_positives": len(false_positives),
            "true_positives": len(true_positives),
            "false_positive_rate": len(false_positives) / len(df),
            "patterns": {},
        }

        # Analyze by alert type
        fp_by_type = false_positives["alert_type"].value_counts().to_dict()
        tp_by_type = true_positives["alert_type"].value_counts().to_dict()

        analysis["patterns"]["by_alert_type"] = {
            "false_positives": fp_by_type,
            "true_positives": tp_by_type,
        }

        # Analyze by severity
        fp_by_severity = false_positives["severity"].value_counts().to_dict()
        tp_by_severity = true_positives["severity"].value_counts().to_dict()

        analysis["patterns"]["by_severity"] = {
            "false_positives": fp_by_severity,
            "true_positives": tp_by_severity,
        }

        # Analyze by amount ranges
        amount_bins = [0, 1000, 5000, 10000, 50000, float("inf")]
        amount_labels = ["0-1K", "1K-5K", "5K-10K", "10K-50K", "50K+"]

        if "transaction_amount" in df.columns:
            false_positives["amount_bin"] = pd.cut(
                false_positives["transaction_amount"], bins=amount_bins, labels=amount_labels
            )
            fp_by_amount = false_positives["amount_bin"].value_counts().to_dict()
            analysis["patterns"]["by_amount"] = fp_by_amount

        logger.info(f"False positive analysis: {analysis}")

        return analysis

    def identify_predictive_features(self, df: pd.DataFrame) -> List[str]:
        """
        Identify most predictive features using correlation analysis.

        Args:
            df: Dataset with features and labels

        Returns:
            List of feature names ordered by predictiveness
        """
        # Select numeric features only
        numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()

        # Remove label and ID columns
        feature_cols = [c for c in numeric_cols if c not in ["label", "alert_id"]]

        if not feature_cols:
            return []

        # Calculate correlation with label
        correlations = df[feature_cols + ["label"]].corr()["label"].abs()
        correlations = correlations.drop("label").sort_values(ascending=False)

        top_features = correlations.head(15).index.tolist()

        logger.info(f"Top predictive features: {top_features}")

        return top_features

    def create_baseline_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate baseline metrics for comparison.

        Args:
            df: Dataset with labels

        Returns:
            Baseline metrics
        """
        total = len(df)
        positives = (df["label"] == 1).sum()
        negatives = (df["label"] == 0).sum()

        # Baseline: always predict majority class
        majority_class = 1 if positives > negatives else 0
        majority_accuracy = max(positives, negatives) / total

        return {
            "total_samples": total,
            "positive_samples": int(positives),
            "negative_samples": int(negatives),
            "class_balance": positives / total,
            "baseline_accuracy": majority_accuracy,
            "baseline_precision": 1.0 if majority_class == 1 else 0.0,
            "baseline_recall": 1.0 if majority_class == 1 else 0.0,
        }
