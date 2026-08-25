"""
TradiQ — ML Inference
Loads the trained XGBoost model and returns probability scores.
Falls back to rule-based composite score if model not trained yet.
"""

import os
import joblib
import numpy as np
import logging
from ml.feature_engineering import features_to_array, FEATURE_COLUMNS
from config.settings import ML_MODEL_PATH, AI_SCORE_THRESHOLD

logger = logging.getLogger(__name__)

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    if os.path.exists(ML_MODEL_PATH):
        try:
            _model = joblib.load(ML_MODEL_PATH)
            logger.info(f"✅ XGBoost model loaded from {ML_MODEL_PATH}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to load model: {e}")
            _model = None
    return _model


def predict_ai_score(feature_dict: dict, composite_score: float) -> float:
    """
    Returns an AI score (0–100):
      - If model is trained: uses XGBoost probability × 100
      - If model not yet trained: returns composite_score (rule-based fallback)

    Args:
        feature_dict: Feature dict from feature_engineering.build_feature_vector()
        composite_score: Rule-based composite score (0–100) as fallback

    Returns:
        float: AI score 0–100
    """
    model = _load_model()

    if model is None:
        logger.debug("Model not found — using rule-based composite score as AI score")
        return float(composite_score)

    try:
        X = features_to_array(feature_dict).reshape(1, -1)
        # XGBoost predict_proba returns [[prob_class_0, prob_class_1]]
        prob = float(model.predict_proba(X)[0][1])
        score = round(prob * 100, 2)
        return score
    except Exception as e:
        logger.warning(f"Model prediction failed: {e} — falling back to composite")
        return float(composite_score)
