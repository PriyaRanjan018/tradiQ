"""
TradiQ — XGBoost Model Training
Run this script once (or periodically) to train/update the model.

Usage:
    python -m ml.train

Training data: Historical feature vectors labeled by whether the
stock grew >40% in the following 9 months.
"""

import os
import json
import glob
import numpy as np
import pandas as pd
import joblib
import logging
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier
from ml.feature_engineering import FEATURE_COLUMNS
from config.settings import ML_MODEL_PATH, GROWTH_TARGET_PCT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRAINING_DATA_PATH = "data/training_data.jsonl"


def load_training_data() -> pd.DataFrame:
    """Load labeled training samples from JSONL file."""
    if not os.path.exists(TRAINING_DATA_PATH):
        logger.error(f"Training data not found at {TRAINING_DATA_PATH}")
        logger.info("Run the data collection script first: python -m ml.collect_training_data")
        return pd.DataFrame()

    records = []
    with open(TRAINING_DATA_PATH) as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    df = pd.DataFrame(records)
    logger.info(f"📊 Loaded {len(df)} training samples")
    return df


def train():
    df = load_training_data()
    if df.empty:
        logger.error("No training data available.")
        return

    # Features and label
    X = df[FEATURE_COLUMNS].fillna(0).values.astype(np.float32)
    y = df["label"].values.astype(int)   # 1 = grew >40% in 9 months, 0 = did not

    pos = y.sum()
    neg = len(y) - pos
    logger.info(f"Class balance: {pos} positive ({pos/len(y)*100:.1f}%), {neg} negative")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=neg / pos,  # Handle class imbalance
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    # Evaluate
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    logger.info("\n" + classification_report(y_test, y_pred))
    logger.info(f"AUC-ROC: {roc_auc_score(y_test, y_prob):.4f}")

    # Save model
    os.makedirs(os.path.dirname(ML_MODEL_PATH), exist_ok=True)
    joblib.dump(model, ML_MODEL_PATH)
    logger.info(f"✅ Model saved to {ML_MODEL_PATH}")

    # Feature importance
    import pandas as pd
    fi = pd.Series(model.feature_importances_, index=FEATURE_COLUMNS)
    fi = fi.sort_values(ascending=False)
    logger.info("\nTop 10 Feature Importances:\n" + fi.head(10).to_string())


if __name__ == "__main__":
    train()
