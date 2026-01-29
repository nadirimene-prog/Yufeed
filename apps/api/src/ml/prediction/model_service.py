"""
ML Model service for real-time alert triage predictions.
Phase 4B: Task 4.3 - Model Serving Infrastructure
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)

try:
    import joblib
    import pandas as pd
    import numpy as np
    ML_DEPS_AVAILABLE = True
except ImportError:
    joblib = None
    pd = None
    np = None
    ML_DEPS_AVAILABLE = False
from sqlalchemy.orm import Session

from src.models.transaction_models import Alert, Transaction
from src.monitoring.tracing import traced, add_span_attributes

logger = logging.getLogger(__name__)


class AlertTriageMLModel:
    """
    ML Model service for alert triage predictions.

    Features:
    - Load trained model on startup
    - Real-time predictions with fallback
    - Model versioning support
    - Feature computation from alert data
    """

    def __init__(self, model_dir: str = "models/alert_triage"):
        self.model_dir = Path(model_dir)
        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.metadata = {}
        self.feature_names = []
        self.categorical_features = []
        self.numeric_features = []
        self.optimal_threshold = 0.5
        self.model_loaded = False

    def load_model(self, model_path: Optional[str] = None):
        """
        Load trained model from disk.

        Args:
            model_path: Path to model file (if None, loads latest)
        """
        if not ML_DEPS_AVAILABLE:
            logger.warning("ML dependencies not installed; skipping model load")
            self.model_loaded = False
            return
        try:
            if model_path is None:
                # Find latest model
                model_files = list(self.model_dir.glob("*.joblib"))
                if not model_files:
                    logger.warning("No trained models found")
                    return

                # Get most recent model
                model_path = max(model_files, key=lambda p: p.stat().st_mtime)

            logger.info(f"Loading model from {model_path}")

            # Load model
            self.model = joblib.load(model_path)

            # Extract base name and timestamp
            base_name = Path(model_path).stem.rsplit('_', 1)[0]
            timestamp = Path(model_path).stem.rsplit('_', 1)[1]

            # Load scaler
            scaler_path = self.model_dir / f"{base_name}_scaler_{timestamp}.joblib"
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)
                logger.info(f"Loaded scaler from {scaler_path}")

            # Load encoders
            encoders_path = self.model_dir / f"{base_name}_encoders_{timestamp}.joblib"
            if encoders_path.exists():
                self.label_encoders = joblib.load(encoders_path)
                logger.info(f"Loaded encoders from {encoders_path}")

            # Load metadata
            metadata_path = self.model_dir / f"{base_name}_metadata_{timestamp}.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)

                self.feature_names = self.metadata.get('feature_names', [])
                self.categorical_features = self.metadata.get('categorical_features', [])
                self.numeric_features = self.metadata.get('numeric_features', [])
                self.optimal_threshold = self.metadata.get('optimal_threshold', 0.5)

                logger.info(f"Loaded metadata from {metadata_path}")

            self.model_loaded = True
            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            self.model_loaded = False

    @traced(span_name="ml_predict_alert_triage")
    def predict(
        self,
        db: Session,
        alert: Alert,
        return_proba: bool = True
    ) -> Dict[str, Any]:
        """
        Predict if alert is false positive.

        Args:
            db: Database session
            alert: Alert to predict
            return_proba: Return probability score

        Returns:
            Prediction with confidence and recommendation
        """
        add_span_attributes({
            "alert_id": alert.alert_id,
            "alert_type": alert.alert_type,
            "model_loaded": self.model_loaded
        })

        # Fallback if model not loaded or dependencies missing
        if not self.model_loaded or not ML_DEPS_AVAILABLE:
            logger.warning("Model not loaded, using fallback logic")
            return self._fallback_prediction(alert)

        try:
            # Extract features
            features = self._extract_features_for_prediction(db, alert)

            # Prepare feature vector
            X = self._prepare_feature_vector(features)

            # Make prediction
            prediction_proba = self.model.predict_proba(X)[0]
            false_positive_prob = prediction_proba[0]
            true_positive_prob = prediction_proba[1]

            # Use optimal threshold
            is_false_positive = false_positive_prob > self.optimal_threshold

            # Determine recommendation
            if is_false_positive and false_positive_prob > 0.8:
                recommendation = "auto_close"
                confidence = "high"
            elif is_false_positive and false_positive_prob > 0.6:
                recommendation = "low_priority"
                confidence = "medium"
            else:
                recommendation = "manual_review"
                confidence = "high" if true_positive_prob > 0.8 else "medium"

            result = {
                "prediction": "false_positive" if is_false_positive else "true_positive",
                "false_positive_probability": float(false_positive_prob),
                "true_positive_probability": float(true_positive_prob),
                "confidence": confidence,
                "recommendation": recommendation,
                "threshold_used": self.optimal_threshold,
                "model_version": self.metadata.get('timestamp', 'unknown')
            }

            add_span_attributes({
                "prediction": result["prediction"],
                "confidence": confidence,
                "recommendation": recommendation
            })

            return result

        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            return self._fallback_prediction(alert)

    def _extract_features_for_prediction(
        self,
        db: Session,
        alert: Alert
    ) -> Dict[str, Any]:
        """
        Extract features from alert for prediction.
        """
        features = {}

        # Alert metadata
        features['alert_type'] = alert.alert_type
        features['severity'] = alert.severity
        features['risk_score'] = float(alert.risk_score) if alert.risk_score else 0.0
        features['priority'] = alert.priority

        # Temporal features
        if alert.created_at:
            features['hour_of_day'] = alert.created_at.hour
            features['day_of_week'] = alert.created_at.weekday()
            features['is_weekend'] = int(alert.created_at.weekday() >= 5)

        # Transaction features
        if alert.transaction:
            txn = alert.transaction
            features['transaction_amount'] = float(txn.amount)
            features['currency'] = txn.currency
            features['transaction_type'] = txn.transaction_type
            features['country_code'] = txn.country_code or 'UNKNOWN'
            features['has_counterparty'] = int(txn.counterparty_id is not None)
        else:
            features['transaction_amount'] = 0.0
            features['currency'] = 'UNKNOWN'
            features['transaction_type'] = 'UNKNOWN'
            features['country_code'] = 'UNKNOWN'
            features['has_counterparty'] = 0

        # User behavior features
        if alert.user_id:
            user_features = self._compute_user_features_realtime(
                db, alert.user_id, alert.created_at or utc_now()
            )
            features.update(user_features)

        # Rule matching features
        if alert.matched_rules_data:
            rules_data = alert.matched_rules_data if isinstance(alert.matched_rules_data, list) else []
            features['num_rules_matched'] = len(rules_data)
            features['has_high_severity_rule'] = int(any(
                r.get('severity') in ['high', 'critical']
                for r in rules_data
                if isinstance(r, dict)
            ))
            features['has_velocity_rule'] = int(any(
                'velocity' in str(r.get('rule_name', '')).lower()
                for r in rules_data
                if isinstance(r, dict)
            ))
        else:
            features['num_rules_matched'] = 0
            features['has_high_severity_rule'] = 0
            features['has_velocity_rule'] = 0

        # Evidence count
        if alert.evidence:
            features['evidence_count'] = len(alert.evidence) if isinstance(alert.evidence, dict) else 0
        else:
            features['evidence_count'] = 0

        return features

    def _compute_user_features_realtime(
        self,
        db: Session,
        user_id: str,
        current_time: datetime
    ) -> Dict[str, float]:
        """
        Compute user features in real-time for prediction.
        """
        lookback_start = current_time - timedelta(days=30)

        transactions = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.timestamp >= lookback_start,
            Transaction.timestamp < current_time
        ).all()

        if not transactions:
            return {
                'user_txn_count_30d': 0,
                'user_total_volume_30d': 0.0,
                'user_avg_amount': 0.0,
                'user_unique_countries': 0,
                'user_prior_alerts': 0
            }

        txn_count = len(transactions)
        total_volume = sum(float(t.amount) for t in transactions)
        avg_amount = total_volume / txn_count if txn_count > 0 else 0
        unique_countries = len(set(t.country_code for t in transactions if t.country_code))

        prior_alerts = db.query(Alert).filter(
            Alert.user_id == user_id,
            Alert.created_at < current_time
        ).count()

        return {
            'user_txn_count_30d': txn_count,
            'user_total_volume_30d': total_volume,
            'user_avg_amount': avg_amount,
            'user_unique_countries': unique_countries,
            'user_prior_alerts': prior_alerts
        }

    def _prepare_feature_vector(self, features: Dict[str, Any]) -> pd.DataFrame:
        """
        Convert features dict to model input format.
        """
        # Encode categorical features
        for col in self.categorical_features:
            if col in features and col in self.label_encoders:
                value = str(features.get(col, 'UNKNOWN'))
                encoder = self.label_encoders[col]

                # Handle unseen categories
                if value in encoder.classes_:
                    encoded_value = encoder.transform([value])[0]
                else:
                    # Use most common class for unknown
                    encoded_value = 0

                features[f'{col}_encoded'] = encoded_value

        # Create feature vector
        encoded_cols = [f'{col}_encoded' for col in self.categorical_features]
        feature_cols = self.numeric_features + encoded_cols

        X = pd.DataFrame([features])[feature_cols].fillna(0)

        # Scale numeric features
        if self.scaler:
            X[self.numeric_features] = self.scaler.transform(X[self.numeric_features])

        return X

    def _fallback_prediction(self, alert: Alert) -> Dict[str, Any]:
        """
        Fallback logic when ML model is not available.

        Uses simple heuristics:
        - Low risk score + low severity → likely false positive
        - High risk score + high severity → likely true positive
        """
        risk_score = float(alert.risk_score) if alert.risk_score else 50.0
        severity_scores = {'low': 25, 'medium': 50, 'high': 75, 'critical': 100}
        severity_score = severity_scores.get(alert.severity, 50)

        combined_score = (risk_score + severity_score) / 2

        if combined_score < 40:
            prediction = "false_positive"
            recommendation = "low_priority"
            confidence = "low"
        elif combined_score > 70:
            prediction = "true_positive"
            recommendation = "manual_review"
            confidence = "medium"
        else:
            prediction = "uncertain"
            recommendation = "manual_review"
            confidence = "low"

        return {
            "prediction": prediction,
            "false_positive_probability": (100 - combined_score) / 100,
            "true_positive_probability": combined_score / 100,
            "confidence": confidence,
            "recommendation": recommendation,
            "fallback": True,
            "reason": "ML model not loaded"
        }

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about loaded model.
        """
        return {
            "loaded": self.model_loaded,
            "model_type": type(self.model).__name__ if self.model else None,
            "version": self.metadata.get('timestamp', 'unknown'),
            "feature_count": len(self.feature_names),
            "optimal_threshold": self.optimal_threshold,
            "metadata": self.metadata
        }


# Global model instance
alert_triage_model = AlertTriageMLModel()
