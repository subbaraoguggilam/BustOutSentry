import pandas as pd
import numpy as np

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
import joblib


# ---------------------------------------------
# Load feature dataset
# ---------------------------------------------

DATA_PATH = "ml/data/processed/customer_features.csv"

data = pd.read_csv(DATA_PATH)


# ---------------------------------------------
# Separate features and target
# ---------------------------------------------

TARGET = "is_bustout"

DROP_COLUMNS = [
    "customer_id",
    "risk_stage",
    TARGET
]

X = data.drop(
    columns=DROP_COLUMNS,
    errors="ignore"
)

y = data[TARGET]


# ---------------------------------------------
# Train / test split
# ---------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


print("Training samples:", len(X_train))
print("Testing samples:", len(X_test))


# ---------------------------------------------
# Calculate class imbalance weight
# ---------------------------------------------

negative = (y_train == 0).sum()
positive = (y_train == 1).sum()

scale_pos_weight = negative / positive

print(
    "scale_pos_weight:",
    scale_pos_weight
)


# ---------------------------------------------
# XGBoost
# ---------------------------------------------

model = XGBClassifier(

    n_estimators=300,

    max_depth=5,

    learning_rate=0.05,

    subsample=0.8,

    colsample_bytree=0.8,

    objective="binary:logistic",

    eval_metric="logloss",

    scale_pos_weight=scale_pos_weight,

    random_state=42
)


# ---------------------------------------------
# Train
# ---------------------------------------------

model.fit(
    X_train,
    y_train
)


# ---------------------------------------------
# Predictions
# ---------------------------------------------

probabilities = model.predict_proba(X_test)[:, 1]

predictions = (
    probabilities >= 0.50
).astype(int)


# ---------------------------------------------
# Evaluation
# ---------------------------------------------

print("\n==============================")
print("MODEL PERFORMANCE")
print("==============================")

print(
    "\nPrecision:",
    precision_score(y_test, predictions)
)

print(
    "Recall:",
    recall_score(y_test, predictions)
)

print(
    "F1:",
    f1_score(y_test, predictions)
)

print(
    "ROC-AUC:",
    roc_auc_score(
        y_test,
        probabilities
    )
)

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions
    )
)

print("\nConfusion Matrix:")

print(
    confusion_matrix(
        y_test,
        predictions
    )
)


# ---------------------------------------------
# Save model
# ---------------------------------------------

joblib.dump(
    model,
    "ml/artifacts/bustout_xgboost.pkl"
)

print(
    "\nModel saved:"
    " ml/artifacts/bustout_xgboost.pkl"
)


# ---------------------------------------------
# Save feature names
# ---------------------------------------------

joblib.dump(
    list(X.columns),
    "ml/artifacts/feature_names.pkl"
)

print(
    "Feature names saved."
)