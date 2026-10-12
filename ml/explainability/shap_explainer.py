import pandas as pd
import joblib
import shap

MODEL_PATH = "ml/artifacts/bustout_xgboost.pkl"
FEATURES_PATH = "ml/artifacts/feature_names.pkl"
DATA_PATH = "ml/data/processed/customer_features.csv"

print("Loading XGBoost model...")

model = joblib.load(MODEL_PATH)

print("Model loaded successfully.")

feature_names = joblib.load(FEATURES_PATH)

print("Number of features:", len(feature_names))

data = pd.read_csv(DATA_PATH)

X = data[feature_names]

print("Creating SHAP explainer...")

explainer = shap.TreeExplainer(model)

# Use only 50 customers for faster SHAP calculation
X_sample = X.sample(
    n=min(50, len(X)),
    random_state=42
)

shap_values = explainer.shap_values(X_sample)

print("SHAP values calculated.")

importance = pd.DataFrame({
    "feature": feature_names,
    "importance": abs(shap_values).mean(axis=0)
})

importance = importance.sort_values(
    "importance",
    ascending=False
)

print("\n==============================")
print("TOP RISK FEATURES")
print("==============================")

print(
    importance.head(15).to_string(index=False)
)

importance.to_csv(
    "ml/artifacts/shap_feature_importance.csv",
    index=False
)

# Explain the first customer from the SHAP sample
customer_data = X_sample.iloc[[0]]

customer_shap = shap_values[0]

customer_explanation = pd.DataFrame({
    "feature": feature_names,
    "feature_value": customer_data.iloc[0].values,
    "shap_value": customer_shap
})

customer_explanation["impact"] = (
    customer_explanation["shap_value"].abs()
)

customer_explanation = customer_explanation.sort_values(
    "impact",
    ascending=False
)

print("\n==============================")
print("CUSTOMER RISK EXPLANATION")
print("==============================")

print(
    customer_explanation.head(10).to_string(index=False)
)