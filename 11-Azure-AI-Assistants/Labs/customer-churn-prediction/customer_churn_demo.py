#!/usr/bin/env python3
"""
customer_churn_demo.py
----------------------
A self-contained demo script for teaching data analysis & ML in a sandbox.
- Generates a synthetic telecom churn dataset (1,000 rows).
- Saves: churn_data.csv, feature_importance.png, churn_by_contract.png
- Trains a logistic regression classifier and reports accuracy.
- Shows simple EDA and a confusion matrix.

Usage:
    python customer_churn_demo.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, ConfusionMatrixDisplay, classification_report
import os
import textwrap


def generate_synthetic_data(n=1000, random_state=42):
    rng = np.random.default_rng(random_state)

    # Categorical features
    contract_types = ["Monthly", "One year", "Two year"]
    internet_services = ["DSL", "Fiber optic", "None"]
    payment_methods = ["Electronic check", "Mailed check", "Credit card", "Bank transfer"]

    data = pd.DataFrame({
        "tenure_months": rng.integers(1, 73, size=n),
        "monthly_charges": rng.normal(75, 20, size=n).clip(20, 150),
        "contract": rng.choice(contract_types, size=n, p=[0.6, 0.25, 0.15]),
        "internet_service": rng.choice(internet_services, size=n, p=[0.35, 0.45, 0.20]),
        "payment_method": rng.choice(payment_methods, size=n),
        "support_tickets_last_90d": rng.poisson(1.2, size=n),
        "late_payments_last_year": rng.poisson(0.7, size=n),
        "add_on_backup": rng.choice([0, 1], size=n, p=[0.7, 0.3]),
        "add_on_security": rng.choice([0, 1], size=n, p=[0.65, 0.35]),
    })

    # Build churn probability from a simple rule-based model
    base = 0.2
    base += (data["contract"] == "Monthly") * 0.18
    base += (data["internet_service"] == "Fiber optic") * 0.05
    base += (data["support_tickets_last_90d"] >= 3) * 0.15
    base += (data["late_payments_last_year"] >= 2) * 0.12
    base += (data["monthly_charges"] > 100) * 0.08
    base -= (data["tenure_months"] > 24) * 0.10
    base -= (data["contract"] == "Two year") * 0.12
    base -= (data["add_on_security"] == 1) * 0.04

    # clamp and sample
    p = np.clip(base, 0.01, 0.95)
    data["churn"] = (np.random.random(size=n) < p).astype(int)

    return data


def train_and_report(df):
    X = df.drop(columns=["churn"])
    y = df["churn"]

    num_cols = ["tenure_months", "monthly_charges", "support_tickets_last_90d", "late_payments_last_year"]
    cat_cols = ["contract", "internet_service", "payment_method", "add_on_backup", "add_on_security"]

    preproc = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)
    ])

    model = LogisticRegression(max_iter=300, n_jobs=None)

    pipe = Pipeline([
        ("preproc", preproc),
        ("clf", model)
    ])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)

    pipe.fit(X_train, y_train)
    preds = pipe.predict(X_test)
    acc = accuracy_score(y_test, preds)

    print("\\n=== Model Performance ===")
    print(f"Accuracy: {acc:.3f}")
    print("\\nClassification Report:")
    print(classification_report(y_test, preds, digits=3))

    # Confusion matrix
    cm = confusion_matrix(y_test, preds)
    disp = ConfusionMatrixDisplay(cm, display_labels=["Stayed", "Churned"])
    disp.plot(values_format="d")
    plt.tight_layout()
    plt.savefig("confusion_matrix.png")
    plt.close()

    return pipe, acc


def eda_and_plots(df):
    # Churn by contract type
    churn_by_contract = df.groupby("contract")["churn"].mean().sort_values(ascending=False)
    churn_by_contract.plot(kind="bar")
    plt.ylabel("Churn rate")
    plt.title("Churn rate by contract type")
    plt.tight_layout()
    plt.savefig("churn_by_contract.png")
    plt.close()

    # "Feature importance" via logistic regression coefficients (approx, for demo)
    # Fit a quick model to extract coefficients after one-hot
    num_cols = ["tenure_months", "monthly_charges", "support_tickets_last_90d", "late_payments_last_year"]
    cat_cols = ["contract", "internet_service", "payment_method", "add_on_backup", "add_on_security"]

    preproc = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)
    ])

    X = df.drop(columns=["churn"])
    y = df["churn"]

    X_enc = preproc.fit_transform(X)
    clf = LogisticRegression(max_iter=300)
    clf.fit(X_enc, y)

    # Get feature names
    num_feats = num_cols
    cat_feats = list(preproc.named_transformers_["cat"].get_feature_names_out(cat_cols))
    feats = num_feats + cat_feats
    coefs = clf.coef_.ravel()

    # show top absolute coefficients
    order = np.argsort(np.abs(coefs))[::-1][:15]
    top_feats = [feats[i] for i in order]
    top_vals = [coefs[i] for i in order]

    plt.figure(figsize=(8,5))
    pd.Series(top_vals, index=top_feats).sort_values().plot(kind="barh")
    plt.title("Approx. feature importance (logistic coefficients)")
    plt.tight_layout()
    plt.savefig("feature_importance.png")
    plt.close()


def main():
    print(textwrap.dedent(\"\"\"
        Customer Churn Demo
        -------------------
        This script generates a synthetic dataset, runs a simple ML model,
        saves plots (PNG) and a CSV. Great for sandbox/code-interpreter demos!
    \"\"\"))

    df = generate_synthetic_data(n=1000, random_state=42)
    csv_path = "churn_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved dataset -> {csv_path} (rows={len(df)})")

    eda_and_plots(df)
    print("Saved plots -> churn_by_contract.png, feature_importance.png, confusion_matrix.png")

    _, acc = train_and_report(df)
    print(f"Done. Model accuracy ~ {acc:.3f}")


if __name__ == "__main__":
    main()
