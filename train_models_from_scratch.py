"""
TravelPlannerAgent - Train Machine Learning Models From Scratch
Trains 3 genuine ML models on All-India datasets:
1. Trip Budget Regressor (Random Forest & Neural Network MLP) on 25,000 trips
2. Attraction Category & Recommendation Classifier on 1,560 places
3. Hotel Safety & Tier Clustering (K-Means) on 12,000 stays
"""

import os
import time
import joblib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error, accuracy_score, classification_report
from sklearn.cluster import KMeans

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_OUT_DIR = os.path.join(BASE_DIR, "backend", "agents_models", "trained_weights")
PLOTS_DIR = os.path.join(BASE_DIR, "ml_evaluation_charts")

os.makedirs(MODEL_OUT_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)

print("=" * 80)
print("     ALL-INDIA TRAVEL PLANNER: MACHINE LEARNING MODEL TRAINING PIPELINE")
print("=" * 80)

# ==============================================================================
# 1. MODEL 1: TRIP BUDGET & EXPENSE PREDICTOR (SUPERVISED REGRESSION)
# ==============================================================================
print("\n[MODEL 1/3] Training Trip Budget & Expense Predictor (25,000 Trip Dataset)...")
budget_csv = os.path.join(BASE_DIR, "datasets", "agent_3_budget", "trip_budget_ml_training_25000.csv")
if not os.path.exists(budget_csv):
    budget_csv = os.path.join(BASE_DIR, "FACULTY_EVALUATION_DATASETS", "6_Trip_Budget_Simulation_Dataset_25000.csv")
df_budget = pd.read_csv(budget_csv)
print(f"--> Loaded {len(df_budget):,} records from {os.path.basename(budget_csv)}")

X_budget = df_budget[["days", "travelers", "distance_km", "transport_mode", "hotel_tier"]]
y_budget = df_budget["total_cost_inr"]

X_train_b, X_test_b, y_train_b, y_test_b = train_test_split(X_budget, y_budget, test_size=0.20, random_state=42)
print(f"--> Train set: {len(X_train_b):,} samples | Test set: {len(X_test_b):,} samples (80/20 split)")

preprocessor_budget = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), ["days", "travelers", "distance_km"]),
        ("cat", OneHotEncoder(drop="first", sparse_output=False), ["transport_mode", "hotel_tier"])
    ]
)

# A. Neural Network (MLP Regressor) with training epochs
print("--> [A] Training Multi-Layer Perceptron (Neural Network) across 25 epochs...")
mlp_pipeline = Pipeline([
    ("prep", preprocessor_budget),
    ("mlp", MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=25, random_state=42, verbose=True, learning_rate_init=0.05))
])
mlp_pipeline.fit(X_train_b, y_train_b)
y_pred_mlp = mlp_pipeline.predict(X_test_b)
r2_mlp = r2_score(y_test_b, y_pred_mlp)
print(f"    [MLP Neural Net] R2 Score: {r2_mlp:.4f} | MAE: INR {mean_absolute_error(y_test_b, y_pred_mlp):.2f}")

# B. Random Forest Regressor
print("--> [B] Training Random Forest Regressor (100 Decision Trees)...")
rf_budget_pipeline = Pipeline([
    ("prep", preprocessor_budget),
    ("rf", RandomForestRegressor(n_estimators=100, max_depth=16, random_state=42, n_jobs=-1))
])
rf_budget_pipeline.fit(X_train_b, y_train_b)
y_pred_rf = rf_budget_pipeline.predict(X_test_b)

r2_rf = r2_score(y_test_b, y_pred_rf)
mae_rf = mean_absolute_error(y_test_b, y_pred_rf)
rmse_rf = np.sqrt(mean_squared_error(y_test_b, y_pred_rf))

print(f"    [Random Forest] R2 Score: {r2_rf:.4f} ({r2_rf*100:.2f}% accuracy)")
print(f"    [Random Forest] Mean Absolute Error: INR {mae_rf:.2f}")
print(f"    [Random Forest] Root Mean Squared Error: INR {rmse_rf:.2f}")

# Save Model
joblib.dump(rf_budget_pipeline, os.path.join(MODEL_OUT_DIR, "trip_budget_rf_model.pkl"), compress=3)
print(f"--> Saved trained model weights: trip_budget_rf_model.pkl")

# Plot Actual vs Predicted & Loss Curve
plt.figure(figsize=(10, 5))
plt.subplot(1, 2, 1)
plt.plot(mlp_pipeline.named_steps["mlp"].loss_curve_, color="#0062FF", lw=2)
plt.title("Neural Network Training Loss Curve")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.grid(True, linestyle="--", alpha=0.5)

plt.subplot(1, 2, 2)
plt.scatter(y_test_b[:200], y_pred_rf[:200], alpha=0.7, color="#6929C4", edgecolors="k", s=30)
plt.plot([y_test_b.min(), y_test_b.max()], [y_test_b.min(), y_test_b.max()], 'r--', lw=2)
plt.title(f"Random Forest Actual vs Predicted (R²={r2_rf:.3f})")
plt.xlabel("Actual Trip Cost (INR)")
plt.ylabel("Predicted Trip Cost (INR)")
plt.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()
plot_path_1 = os.path.join(PLOTS_DIR, "budget_model_performance.png")
plt.savefig(plot_path_1, dpi=300)
plt.close()
print(f"--> Saved evaluation chart: {plot_path_1}")


# ==============================================================================
# 2. MODEL 2: TOURIST ATTRACTION RECOMMENDATION CLASSIFIER (1,560 ATTRACTIONS)
# ==============================================================================
print("\n[MODEL 2/3] Training Tourist Attraction Classifier (1,560 Attractions)...")
attr_csv = os.path.join(BASE_DIR, "FACULTY_EVALUATION_DATASETS", "1_All_India_Tourist_Attractions_10025.csv")
df_attr = pd.read_csv(attr_csv)
print(f"--> Loaded {len(df_attr):,} records from {os.path.basename(attr_csv)}")

X_attr = df_attr[["Zone", "State", "Time Needed to Visit (hrs)", "Google Review Rating", "Entrance Fee in INR"]]
y_attr = df_attr["Type"]

X_train_a, X_test_a, y_train_a, y_test_a = train_test_split(X_attr, y_attr, test_size=0.20, random_state=42)

preprocessor_attr = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), ["Time Needed to Visit (hrs)", "Google Review Rating", "Entrance Fee in INR"]),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["Zone", "State"])
    ]
)

rf_attr_pipeline = Pipeline([
    ("prep", preprocessor_attr),
    ("clf", RandomForestClassifier(n_estimators=100, random_state=42, max_depth=12))
])
rf_attr_pipeline.fit(X_train_a, y_train_a)
y_pred_a = rf_attr_pipeline.predict(X_test_a)

acc_a = accuracy_score(y_test_a, y_pred_a)
print(f"--> [Attraction Classifier] Test Accuracy: {acc_a*100:.2f}%")
print("--> Classification Report Summary:")
print(classification_report(y_test_a, y_pred_a, zero_division=0))

joblib.dump(rf_attr_pipeline, os.path.join(MODEL_OUT_DIR, "attraction_classifier_rf.pkl"), compress=3)
print(f"--> Saved trained model weights: attraction_classifier_rf.pkl")


# ==============================================================================
# 3. MODEL 3: HOTEL SAFETY & TIER CLUSTERING (12,000 HOTELS)
# ==============================================================================
print("\n[MODEL 3/3] Training Hotel Safety & Tier Clustering (12,000 Indian Hotels)...")
hotels_csv = os.path.join(BASE_DIR, "datasets", "agent_4_accommodations_safety", "all_india_hotels_150000.csv")
if not os.path.exists(hotels_csv):
    hotels_csv = os.path.join(BASE_DIR, "FACULTY_EVALUATION_DATASETS", "2_All_India_Hotels_and_Accommodations_150000.csv")
df_hotels = pd.read_csv(hotels_csv)
if len(df_hotels) > 25000:
    df_hotels = df_hotels.sample(n=25000, random_state=42).reset_index(drop=True)
print(f"--> Loaded {len(df_hotels):,} records from {os.path.basename(hotels_csv)}")

features_hotel = df_hotels[["star_rating", "price_per_night_inr", "safety_score"]].dropna()
scaler_hotel = StandardScaler()
X_hotel_scaled = scaler_hotel.fit_transform(features_hotel)

kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
df_hotels["cluster"] = kmeans.fit_predict(X_hotel_scaled)

print("--> Hotel Cluster Breakdown:")
for c in range(3):
    sub = df_hotels[df_hotels["cluster"] == c]
    print(f"    Cluster {c}: {len(sub):,} hotels | Avg Price: INR {sub['price_per_night_inr'].mean():.0f} | Avg Safety: {sub['safety_score'].mean():.2f}/10")

joblib.dump((kmeans, scaler_hotel), os.path.join(MODEL_OUT_DIR, "hotel_kmeans_model.pkl"))
print(f"--> Saved clustering model weights: hotel_kmeans_model.pkl")

# Plot Hotel Clusters
plt.figure(figsize=(7, 5))
scatter = plt.scatter(df_hotels["price_per_night_inr"][:500], df_hotels["safety_score"][:500], c=df_hotels["cluster"][:500], cmap="viridis", alpha=0.7)
plt.title("Hotel Clustering: Price vs Safety Score (K-Means K=3)")
plt.xlabel("Price Per Night (INR)")
plt.ylabel("Safety Score (Out of 10)")
plt.colorbar(scatter, label="Cluster ID")
plt.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()
plot_path_3 = os.path.join(PLOTS_DIR, "hotel_clusters_evaluation.png")
plt.savefig(plot_path_3, dpi=300)
plt.close()
print(f"--> Saved evaluation chart: {plot_path_3}")

print("\n" + "=" * 80)
print("     [SUCCESS] ALL 3 MODELS SUCCESSFULLY TRAINED FROM SCRATCH!")
print(f"     Weights saved in: {MODEL_OUT_DIR}")
print(f"     Charts saved in:  {PLOTS_DIR}")
print("=" * 80)
