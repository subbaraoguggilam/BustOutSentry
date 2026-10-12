import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
)

from xgboost import XGBClassifier


# ==========================================
# PATHS
# ==========================================

DATA_PATH = "ml/data/processed/temporal_features.csv"

MODEL_PATH = "ml/artifacts/temporal_xgboost.pkl"

FEATURE_PATH = "ml/artifacts/temporal_feature_names.pkl"


# ==========================================
# LOAD DATA
# ==========================================

print("Loading temporal feature dataset...")

data = pd.read_csv(DATA_PATH)

print("Dataset shape:", data.shape)


# ==========================================
# TARGET
# ==========================================

TARGET = "is_bustout"


# Columns that should NOT be used for training
DROP_COLUMNS = [
    "customer_id",
    "snapshot_time",
    "final_transaction_time",
    "risk_stage",
    TARGET
]


X = data.drop(
    columns=DROP_COLUMNS,
    errors="ignore"
)

y = data[TARGET]


print("\nNumber of features:", X.shape[1])

print("\nTarget distribution:")
print(y.value_counts())


# ==========================================
# TRAIN / TEST SPLIT
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


print("\nTraining samples:", len(X_train))
print("Testing samples:", len(X_test))


# ==========================================
# HANDLE CLASS IMBALANCE
# ==========================================

negative = (y_train == 0).sum()
positive = (y_train == 1).sum()

scale_pos_weight = negative / positive

print("\nClass imbalance:")
print("Normal:", negative)
print("Bust-out:", positive)
print("Scale Pos Weight:", scale_pos_weight)


# ==========================================
# XGBOOST MODEL
# ==========================================

print("\nTraining Temporal XGBoost...")

model = XGBClassifier(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.04,
    subsample=0.85,
    colsample_bytree=0.85,
    objective="binary:logistic",
    eval_metric="logloss",
    scale_pos_weight=scale_pos_weight,
    random_state=42
)


model.fit(
    X_train,
    y_train
)


print("Model training completed.")


# ==========================================
# PREDICTIONS
# ==========================================

probabilities = model.predict_proba(X_test)[:, 1]

predictions = (
    probabilities >= 0.50
).astype(int)


# ==========================================
# EVALUATION
# ==========================================

precision = precision_score(
    y_test,
    predictions,
    zero_division=0
)

recall = recall_score(
    y_test,
    predictions,
    zero_division=0
)

f1 = f1_score(
    y_test,
    predictions,
    zero_division=0
)

roc_auc = roc_auc_score(
    y_test,
    probabilities
)


print("\n======================================")
print("TEMPORAL XGBOOST RESULTS")
print("======================================")

print(f"Precision : {precision:.4f}")
print(f"Recall    : {recall:.4f}")
print(f"F1 Score  : {f1:.4f}")
print(f"ROC-AUC   : {roc_auc:.4f}")


print("\nClassification Report:")
print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)


print("Confusion Matrix:")
print(
    confusion_matrix(
        y_test,
        predictions
    )
)


# ==========================================
# FEATURE IMPORTANCE
# ==========================================

importance = pd.DataFrame({
    "feature": X.columns,
    "importance": model.feature_importances_
})

importance = importance.sort_values(
    "importance",
    ascending=False
)


print("\n======================================")
print("TOP TEMPORAL RISK FEATURES")
print("======================================")

print(
    importance.head(20).to_string(index=False)
)


# ==========================================
# SAVE ARTIFACTS
# ==========================================

joblib.dump(
    model,
    MODEL_PATH
)

joblib.dump(
    list(X.columns),
    FEATURE_PATH
)

importance.to_csv(
    "ml/artifacts/temporal_feature_importance.csv",
    index=False
)


print("\n======================================")
print("MODEL SAVED")
print("======================================")

print("Model:")
print(MODEL_PATH)

print("\nFeature names:")
print(FEATURE_PATH)

print("\nFeature importance:")
print("ml/artifacts/temporal_feature_importance.csv")