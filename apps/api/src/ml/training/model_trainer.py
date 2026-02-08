"""
ML model trainer for alert triage.
Phase 4B: Task 4.2 - ML Model Training
"""

import logging
import joblib
import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_recall_curve,
    roc_curve,
)
import xgboost as xgb
import lightgbm as lgb

logger = logging.getLogger(__name__)


class AlertTriageModelTrainer:
    """
    Train and evaluate ML models for alert triage.

    Supports:
    - XGBoost
    - LightGBM
    - Random Forest
    - Gradient Boosting
    """

    def __init__(self, model_dir: str = "models/alert_triage"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.feature_names = []
        self.categorical_features = []
        self.numeric_features = []

    def prepare_data(
        self, df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Prepare data for training.

        Args:
            df: Raw dataset
            test_size: Proportion of data for testing
            random_state: Random seed

        Returns:
            X_train, X_test, y_train, y_test
        """
        logger.info(f"Preparing data: {df.shape}")

        # Identify feature types
        self.categorical_features = [
            "alert_type",
            "severity",
            "currency",
            "transaction_type",
            "country_code",
        ]

        self.numeric_features = [
            "risk_score",
            "priority",
            "transaction_amount",
            "hour_of_day",
            "day_of_week",
            "is_weekend",
            "has_counterparty",
            "evidence_count",
            "user_txn_count_30d",
            "user_total_volume_30d",
            "user_avg_amount",
            "user_unique_countries",
            "user_prior_alerts",
            "num_rules_matched",
            "has_high_severity_rule",
            "has_velocity_rule",
        ]

        # Filter to available features
        available_cat = [f for f in self.categorical_features if f in df.columns]
        available_num = [f for f in self.numeric_features if f in df.columns]

        # Encode categorical features
        df_encoded = df.copy()

        for col in available_cat:
            le = LabelEncoder()
            df_encoded[f"{col}_encoded"] = le.fit_transform(
                df_encoded[col].fillna("UNKNOWN").astype(str)
            )
            self.label_encoders[col] = le

        # Prepare feature matrix
        encoded_cols = [f"{col}_encoded" for col in available_cat]
        self.feature_names = available_num + encoded_cols

        X = df_encoded[self.feature_names].fillna(0)
        y = df_encoded["label"]

        # Train/test split stratified by label
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        # Scale numeric features
        self.scaler = StandardScaler()
        X_train[available_num] = self.scaler.fit_transform(X_train[available_num])
        X_test[available_num] = self.scaler.transform(X_test[available_num])

        logger.info(f"Train set: {X_train.shape}, Test set: {X_test.shape}")
        logger.info(f"Train labels: {y_train.value_counts().to_dict()}")
        logger.info(f"Test labels: {y_test.value_counts().to_dict()}")

        return X_train, X_test, y_train, y_test

    def train_xgboost(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        hyperparameters: Optional[Dict[str, Any]] = None,
    ) -> xgb.XGBClassifier:
        """
        Train XGBoost classifier.
        """
        logger.info("Training XGBoost model")

        params = hyperparameters or {
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "objective": "binary:logistic",
            "eval_metric": "auc",
            "random_state": 42,
        }

        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train)

        logger.info("XGBoost training completed")
        return model

    def train_lightgbm(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        hyperparameters: Optional[Dict[str, Any]] = None,
    ) -> lgb.LGBMClassifier:
        """
        Train LightGBM classifier.
        """
        logger.info("Training LightGBM model")

        params = hyperparameters or {
            "num_leaves": 31,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "objective": "binary",
            "metric": "auc",
            "random_state": 42,
        }

        model = lgb.LGBMClassifier(**params)
        model.fit(X_train, y_train)

        logger.info("LightGBM training completed")
        return model

    def train_random_forest(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        hyperparameters: Optional[Dict[str, Any]] = None,
    ) -> RandomForestClassifier:
        """
        Train Random Forest classifier.
        """
        logger.info("Training Random Forest model")

        params = hyperparameters or {
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 5,
            "min_samples_leaf": 2,
            "random_state": 42,
        }

        model = RandomForestClassifier(**params)
        model.fit(X_train, y_train)

        logger.info("Random Forest training completed")
        return model

    def hyperparameter_tuning(
        self, X_train: pd.DataFrame, y_train: pd.Series, model_type: str = "xgboost"
    ) -> Dict[str, Any]:
        """
        Perform hyperparameter tuning with GridSearchCV.
        """
        logger.info(f"Hyperparameter tuning for {model_type}")

        if model_type == "xgboost":
            model = xgb.XGBClassifier(random_state=42)
            param_grid = {
                "max_depth": [3, 5, 7],
                "learning_rate": [0.01, 0.1, 0.2],
                "n_estimators": [50, 100, 200],
                "min_child_weight": [1, 3, 5],
            }
        elif model_type == "lightgbm":
            model = lgb.LGBMClassifier(random_state=42)
            param_grid = {
                "num_leaves": [15, 31, 63],
                "learning_rate": [0.01, 0.1, 0.2],
                "n_estimators": [50, 100, 200],
                "min_child_samples": [5, 10, 20],
            }
        else:  # random_forest
            model = RandomForestClassifier(random_state=42)
            param_grid = {
                "n_estimators": [50, 100, 200],
                "max_depth": [5, 10, 15],
                "min_samples_split": [2, 5, 10],
            }

        grid_search = GridSearchCV(model, param_grid, cv=5, scoring="roc_auc", n_jobs=-1, verbose=1)

        grid_search.fit(X_train, y_train)

        logger.info(f"Best parameters: {grid_search.best_params_}")
        logger.info(f"Best CV score: {grid_search.best_score_:.4f}")

        return grid_search.best_params_

    def evaluate_model(self, model, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        """
        Evaluate model performance.
        """
        logger.info("Evaluating model")

        # Predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        # Metrics
        report = classification_report(y_test, y_pred, output_dict=True)
        cm = confusion_matrix(y_test, y_pred)
        auc = roc_auc_score(y_test, y_pred_proba)

        # Precision-Recall curve
        precision, recall, thresholds = precision_recall_curve(y_test, y_pred_proba)

        # Find optimal threshold (maximize F1)
        f1_scores = 2 * (precision * recall) / (precision + recall + 1e-10)
        optimal_idx = np.argmax(f1_scores)
        optimal_threshold = thresholds[optimal_idx] if optimal_idx < len(thresholds) else 0.5

        results = {
            "accuracy": report["accuracy"],
            "precision": report["1"]["precision"],
            "recall": report["1"]["recall"],
            "f1_score": report["1"]["f1-score"],
            "auc": auc,
            "confusion_matrix": cm.tolist(),
            "optimal_threshold": float(optimal_threshold),
            "classification_report": report,
        }

        logger.info(f"Model evaluation results:")
        logger.info(f"  AUC: {auc:.4f}")
        logger.info(f"  Precision: {results['precision']:.4f}")
        logger.info(f"  Recall: {results['recall']:.4f}")
        logger.info(f"  F1-Score: {results['f1_score']:.4f}")

        return results

    def get_feature_importance(self, model, top_n: int = 15) -> Dict[str, float]:
        """
        Get feature importance from trained model.
        """
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        else:
            logger.warning("Model does not support feature importance")
            return {}

        importance_dict = dict(zip(self.feature_names, importances))
        sorted_importance = dict(
            sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]
        )

        logger.info(f"Top {top_n} features:")
        for feature, importance in sorted_importance.items():
            logger.info(f"  {feature}: {importance:.4f}")

        return sorted_importance

    def save_model(self, model, model_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Save trained model and metadata.
        """
        timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
        model_path = self.model_dir / f"{model_name}_{timestamp}.joblib"
        scaler_path = self.model_dir / f"{model_name}_scaler_{timestamp}.joblib"
        encoders_path = self.model_dir / f"{model_name}_encoders_{timestamp}.joblib"
        metadata_path = self.model_dir / f"{model_name}_metadata_{timestamp}.json"

        # Save model
        joblib.dump(model, model_path)
        logger.info(f"Model saved to {model_path}")

        # Save scaler
        joblib.dump(self.scaler, scaler_path)
        logger.info(f"Scaler saved to {scaler_path}")

        # Save label encoders
        joblib.dump(self.label_encoders, encoders_path)
        logger.info(f"Encoders saved to {encoders_path}")

        # Save metadata
        metadata_full = {
            "model_name": model_name,
            "timestamp": timestamp,
            "feature_names": self.feature_names,
            "categorical_features": self.categorical_features,
            "numeric_features": self.numeric_features,
            "model_path": str(model_path),
            "scaler_path": str(scaler_path),
            "encoders_path": str(encoders_path),
        }

        if metadata:
            metadata_full.update(metadata)

        with open(metadata_path, "w") as f:
            json.dump(metadata_full, f, indent=2)

        logger.info(f"Metadata saved to {metadata_path}")

        return str(model_path)
