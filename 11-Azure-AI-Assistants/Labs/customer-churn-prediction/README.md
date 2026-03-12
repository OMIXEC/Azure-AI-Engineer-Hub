# Customer Churn Prediction - End-to-End ML Pipeline

## Overview

Production-ready machine learning pipeline demonstrating customer churn prediction for telecom industry using Azure AI and scikit-learn. Includes data generation, feature engineering, model training, and visualization.

## Business Use Case

Predict customer churn to enable proactive retention strategies, reducing customer acquisition costs and improving lifetime value.

## Architecture

```
Data Generation → Feature Engineering → Model Training → Evaluation → Visualization
       ↓                  ↓                   ↓              ↓             ↓
  Synthetic Data    Preprocessing      Logistic Reg    Metrics      PNG Charts
  (1000 rows)       Pipeline           Classifier      Report       + CSV Export
```

## Features

### Data Generation
- Synthetic telecom customer dataset (1,000 records)
- Realistic feature distributions
- Balanced churn scenarios

### Feature Engineering
- Categorical encoding (OneHotEncoder)
- Numerical scaling (StandardScaler)
- Pipeline-based preprocessing

### Model Training
- Logistic Regression classifier
- Train/test split (80/20)
- Reproducible random state

### Evaluation
- Accuracy metrics
- Confusion matrix visualization
- Classification report (precision, recall, F1)
- Feature importance analysis

### Outputs
- `churn_data.csv` - Generated dataset
- `feature_importance.png` - Top predictive features
- `churn_by_contract.png` - Churn rate by contract type
- Console metrics and reports

## Dataset Features

| Feature | Type | Description |
|---------|------|-------------|
| tenure_months | Numeric | Customer tenure (1-72 months) |
| monthly_charges | Numeric | Monthly bill amount ($20-$150) |
| contract | Categorical | Monthly, One year, Two year |
| internet_service | Categorical | DSL, Fiber optic, None |
| payment_method | Categorical | Electronic check, Mailed check, Credit card, Bank transfer |
| support_tickets_last_90d | Numeric | Recent support interactions |
| late_payments_last_year | Numeric | Payment history indicator |
| add_on_backup | Binary | Backup service subscription |
| add_on_security | Binary | Security service subscription |
| churn | Binary | Target variable (0/1) |

## Key Insights

### Churn Drivers
- **Contract Type**: Monthly contracts show 18% higher churn
- **Tenure**: Shorter tenure correlates with higher churn
- **Support Tickets**: More tickets indicate dissatisfaction
- **Late Payments**: Payment issues predict churn

### Model Performance
- Typical accuracy: 75-85%
- Balanced precision and recall
- Interpretable feature importance

## Usage

```bash
python customer_churn_demo.py
```

### Expected Output
```
Generating synthetic customer data...
Training churn prediction model...
Accuracy: 0.82

Classification Report:
              precision    recall  f1-score   support
           0       0.85      0.88      0.86       150
           1       0.78      0.73      0.75        50

Saved: churn_data.csv
Saved: feature_importance.png
Saved: churn_by_contract.png
```

## Skills Demonstrated

- End-to-end ML pipeline development
- Synthetic data generation
- Feature engineering with scikit-learn
- Model training and evaluation
- Data visualization with matplotlib
- Production-ready code structure
- Reproducible experiments

## Difficulty Level

**Intermediate** - Requires ML fundamentals and Python data science stack

## Technologies Used

- Python 3.10+
- scikit-learn
- pandas
- numpy
- matplotlib

## Azure Integration

This standalone demo can be integrated with:
- **Azure Machine Learning**: Model deployment and monitoring
- **Azure Synapse Analytics**: Large-scale data processing
- **Azure Data Factory**: Automated pipeline orchestration
- **Azure Monitor**: Performance tracking

## Production Enhancements

### Model Improvements
- Hyperparameter tuning (GridSearchCV)
- Advanced algorithms (XGBoost, Random Forest)
- Cross-validation
- Feature selection optimization

### MLOps Integration
- Model versioning (MLflow)
- A/B testing framework
- Real-time prediction API
- Automated retraining pipeline
- Drift detection

### Data Pipeline
- Real customer data integration
- Incremental learning
- Data quality validation
- Feature store implementation

## Business Impact

- **Retention**: Identify at-risk customers early
- **Cost Savings**: Reduce acquisition costs (5-25x cheaper to retain)
- **Personalization**: Targeted retention offers
- **Revenue**: Improve customer lifetime value

## Extension Ideas

- Customer segmentation clustering
- Survival analysis for churn timing
- Recommendation system for retention offers
- Real-time scoring API
- Dashboard for business users

---

**Related Projects**: Model Evaluation, Data Analytics, Code Interpreter
