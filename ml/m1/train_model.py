"""
XGBoost College Football Score Predictor - Training Script

This script trains two XGBoost regression models to predict home and away scores
for college football games based on comprehensive team statistics and historical data.
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for saving plots
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import json
from datetime import datetime

# Set random seed for reproducibility
RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# Configuration
DATA_PATH = '../training_data/training_data.csv'
MODEL_DIR = 'models'
RESULTS_DIR = 'results'
TEST_SIZE = 0.15
VALIDATION_SIZE = 0.15


def create_directories():
    """Create necessary directories for saving models and results."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f"✓ Created directories: {MODEL_DIR}, {RESULTS_DIR}")


def load_and_preprocess_data(data_path):
    """
    Load and preprocess the training data.
    
    Args:
        data_path: Path to the training data CSV file
        
    Returns:
        X: Feature DataFrame
        y_home: Home score target series
        y_away: Away score target series
        feature_names: List of feature names
    """
    print("\n" + "="*70)
    print("LOADING AND PREPROCESSING DATA")
    print("="*70)
    
    # Load data
    print(f"\nLoading data from {data_path}...")
    df = pd.read_csv(data_path)
    print(f"✓ Loaded {len(df)} games")
    print(f"  Columns: {len(df.columns)}")
    print(f"  Date range: {df['season'].min()} - {df['season'].max()}")
    
    # Remove rows with missing target variables
    initial_rows = len(df)
    df = df.dropna(subset=['home_score', 'away_score'])
    print(f"\n✓ Removed {initial_rows - len(df)} games with missing scores")
    print(f"  Remaining games: {len(df)}")
    
    # Define columns to exclude (non-predictive or identifiers)
    exclude_columns = [
        'game_id', 'date', 'home_team', 'away_team',
        'home_score', 'away_score'  # Target variables
    ]
    
    # Get all feature columns
    feature_columns = [col for col in df.columns if col not in exclude_columns]
    
    print(f"\n✓ Selected {len(feature_columns)} features")
    
    # Extract features and targets
    X = df[feature_columns].copy()
    y_home = df['home_score'].copy()
    y_away = df['away_score'].copy()
    
    # Handle missing values in features
    # Strategy: Fill with median for numeric columns
    print("\nHandling missing values...")
    missing_before = X.isnull().sum().sum()
    
    for col in X.columns:
        if X[col].dtype in ['float64', 'int64']:
            median_val = X[col].median()
            X[col] = X[col].fillna(median_val)
        else:
            # For any non-numeric columns, fill with 0
            X[col] = X[col].fillna(0)
    
    missing_after = X.isnull().sum().sum()
    print(f"✓ Handled {missing_before} missing values")
    print(f"  Remaining missing values: {missing_after}")
    
    # Convert any remaining object columns to numeric
    for col in X.columns:
        if X[col].dtype == 'object':
            X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)
    
    print(f"\n✓ Final dataset shape: {X.shape}")
    print(f"  Features: {len(feature_columns)}")
    print(f"  Samples: {len(X)}")
    
    return X, y_home, y_away, feature_columns


def split_data(X, y_home, y_away, test_size, validation_size, random_state):
    """
    Split data into train, validation, and test sets.
    
    Args:
        X: Features
        y_home: Home score targets
        y_away: Away score targets
        test_size: Proportion of data for test set
        validation_size: Proportion of training data for validation set
        random_state: Random seed
        
    Returns:
        Tuple of (X_train, X_val, X_test, y_home_train, y_home_val, y_home_test,
                  y_away_train, y_away_val, y_away_test)
    """
    print("\n" + "="*70)
    print("SPLITTING DATA")
    print("="*70)
    
    # First split: separate test set
    X_temp, X_test, y_home_temp, y_home_test, y_away_temp, y_away_test = train_test_split(
        X, y_home, y_away, test_size=test_size, random_state=random_state
    )
    
    # Second split: separate validation set from training
    val_size_adjusted = validation_size / (1 - test_size)
    X_train, X_val, y_home_train, y_home_val, y_away_train, y_away_val = train_test_split(
        X_temp, y_home_temp, y_away_temp, test_size=val_size_adjusted, random_state=random_state
    )
    
    print(f"\nDataset splits:")
    print(f"  Training:   {len(X_train):5d} samples ({len(X_train)/len(X)*100:.1f}%)")
    print(f"  Validation: {len(X_val):5d} samples ({len(X_val)/len(X)*100:.1f}%)")
    print(f"  Test:       {len(X_test):5d} samples ({len(X_test)/len(X)*100:.1f}%)")
    
    return X_train, X_val, X_test, y_home_train, y_home_val, y_home_test, y_away_train, y_away_val, y_away_test


def train_model(X_train, y_train, X_val, y_val, model_name):
    """
    Train an XGBoost regression model.
    
    Args:
        X_train: Training features
        y_train: Training targets
        X_val: Validation features
        y_val: Validation targets
        model_name: Name for the model (for display purposes)
        
    Returns:
        Trained XGBoost model
    """
    print(f"\nTraining {model_name} model...")
    
    # XGBoost parameters
    params = {
        'objective': 'reg:squarederror',
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 300,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 3,
        'gamma': 0.1,
        'random_state': RANDOM_STATE,
        'n_jobs': -1,
        'eval_metric': 'rmse',
        'early_stopping_rounds': 50
    }
    
    # Create and train model
    model = xgb.XGBRegressor(**params)
    
    # Train with early stopping
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        verbose=False
    )
    
    print(f"✓ {model_name} model trained successfully")
    print(f"  Best iteration: {model.best_iteration}")
    
    return model


def evaluate_model(model, X_train, y_train, X_val, y_val, X_test, y_test, model_name):
    """
    Evaluate model performance on train, validation, and test sets.
    
    Args:
        model: Trained model
        X_train, y_train: Training data
        X_val, y_val: Validation data
        X_test, y_test: Test data
        model_name: Name of the model
        
    Returns:
        Dictionary containing evaluation metrics
    """
    print(f"\n{'-'*70}")
    print(f"EVALUATING {model_name.upper()} MODEL")
    print(f"{'-'*70}")
    
    metrics = {}
    
    for split_name, X_split, y_split in [
        ('Training', X_train, y_train),
        ('Validation', X_val, y_val),
        ('Test', X_test, y_test)
    ]:
        y_pred = model.predict(X_split)
        
        mae = mean_absolute_error(y_split, y_pred)
        rmse = np.sqrt(mean_squared_error(y_split, y_pred))
        r2 = r2_score(y_split, y_pred)
        
        metrics[split_name.lower()] = {
            'mae': float(mae),
            'rmse': float(rmse),
            'r2': float(r2)
        }
        
        print(f"\n{split_name} Set Performance:")
        print(f"  MAE:  {mae:.2f} points")
        print(f"  RMSE: {rmse:.2f} points")
        print(f"  R²:   {r2:.4f}")
    
    return metrics


def plot_predictions(model, X_test, y_test, model_name, save_dir):
    """
    Create visualization plots for model predictions.
    
    Args:
        model: Trained model
        X_test: Test features
        y_test: Test targets
        model_name: Name of the model
        save_dir: Directory to save plots
    """
    y_pred = model.predict(X_test)
    
    # Create figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    
    # Actual vs Predicted scatter plot
    axes[0].scatter(y_test, y_pred, alpha=0.5, s=20)
    axes[0].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 
                 'r--', lw=2, label='Perfect Prediction')
    axes[0].set_xlabel('Actual Score', fontsize=12)
    axes[0].set_ylabel('Predicted Score', fontsize=12)
    axes[0].set_title(f'{model_name} - Actual vs Predicted', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Residual plot
    residuals = y_test - y_pred
    axes[1].scatter(y_pred, residuals, alpha=0.5, s=20)
    axes[1].axhline(y=0, color='r', linestyle='--', lw=2)
    axes[1].set_xlabel('Predicted Score', fontsize=12)
    axes[1].set_ylabel('Residuals', fontsize=12)
    axes[1].set_title(f'{model_name} - Residual Plot', fontsize=14, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    filename = f"{model_name.lower().replace(' ', '_')}_predictions.png"
    filepath = os.path.join(save_dir, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Saved prediction plot: {filepath}")


def plot_feature_importance(model, feature_names, model_name, save_dir, top_n=20):
    """
    Plot feature importance.
    
    Args:
        model: Trained model
        feature_names: List of feature names
        model_name: Name of the model
        save_dir: Directory to save plot
        top_n: Number of top features to display
    """
    # Get feature importance
    importance = model.feature_importances_
    feature_importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    # Plot top N features
    plt.figure(figsize=(12, 8))
    top_features = feature_importance_df.head(top_n)
    
    sns.barplot(data=top_features, y='feature', x='importance', palette='viridis')
    plt.xlabel('Importance Score', fontsize=12)
    plt.ylabel('Feature', fontsize=12)
    plt.title(f'{model_name} - Top {top_n} Feature Importance', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    # Save plot
    filename = f"{model_name.lower().replace(' ', '_')}_feature_importance.png"
    filepath = os.path.join(save_dir, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Saved feature importance plot: {filepath}")
    
    return feature_importance_df


def save_model_and_metadata(model, feature_names, metrics, feature_importance, model_name, model_dir):
    """
    Save trained model and associated metadata.
    
    Args:
        model: Trained model
        feature_names: List of feature names
        metrics: Evaluation metrics dictionary
        feature_importance: Feature importance DataFrame
        model_name: Name of the model
        model_dir: Directory to save model
    """
    # Save model
    model_filename = f"{model_name.lower().replace(' ', '_')}_model.json"
    model_path = os.path.join(model_dir, model_filename)
    model.save_model(model_path)
    print(f"✓ Saved model: {model_path}")
    
    # Save feature names
    features_filename = f"{model_name.lower().replace(' ', '_')}_features.json"
    features_path = os.path.join(model_dir, features_filename)
    with open(features_path, 'w') as f:
        json.dump(feature_names, f, indent=2)
    print(f"✓ Saved feature list: {features_path}")
    
    # Save metrics
    metrics_filename = f"{model_name.lower().replace(' ', '_')}_metrics.json"
    metrics_path = os.path.join(model_dir, metrics_filename)
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Saved metrics: {metrics_path}")
    
    # Save feature importance
    importance_filename = f"{model_name.lower().replace(' ', '_')}_feature_importance.csv"
    importance_path = os.path.join(model_dir, importance_filename)
    feature_importance.to_csv(importance_path, index=False)
    print(f"✓ Saved feature importance: {importance_path}")


def main():
    """Main training pipeline."""
    print("\n" + "="*70)
    print("XGBOOST COLLEGE FOOTBALL SCORE PREDICTOR")
    print("Training Pipeline")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create directories
    create_directories()
    
    # Load and preprocess data
    X, y_home, y_away, feature_names = load_and_preprocess_data(DATA_PATH)
    
    # Split data
    X_train, X_val, X_test, y_home_train, y_home_val, y_home_test, y_away_train, y_away_val, y_away_test = split_data(
        X, y_home, y_away, TEST_SIZE, VALIDATION_SIZE, RANDOM_STATE
    )
    
    # Train Home Score Model
    print("\n" + "="*70)
    print("TRAINING HOME SCORE MODEL")
    print("="*70)
    home_model = train_model(X_train, y_home_train, X_val, y_home_val, "Home Score")
    home_metrics = evaluate_model(
        home_model, X_train, y_home_train, X_val, y_home_val, X_test, y_home_test, "Home Score"
    )
    plot_predictions(home_model, X_test, y_home_test, "Home Score", RESULTS_DIR)
    home_feature_importance = plot_feature_importance(
        home_model, feature_names, "Home Score", RESULTS_DIR
    )
    save_model_and_metadata(
        home_model, feature_names, home_metrics, home_feature_importance, "Home Score", MODEL_DIR
    )
    
    # Train Away Score Model
    print("\n" + "="*70)
    print("TRAINING AWAY SCORE MODEL")
    print("="*70)
    away_model = train_model(X_train, y_away_train, X_val, y_away_val, "Away Score")
    away_metrics = evaluate_model(
        away_model, X_train, y_away_train, X_val, y_away_val, X_test, y_away_test, "Away Score"
    )
    plot_predictions(away_model, X_test, y_away_test, "Away Score", RESULTS_DIR)
    away_feature_importance = plot_feature_importance(
        away_model, feature_names, "Away Score", RESULTS_DIR
    )
    save_model_and_metadata(
        away_model, feature_names, away_metrics, away_feature_importance, "Away Score", MODEL_DIR
    )
    
    # Summary
    print("\n" + "="*70)
    print("TRAINING COMPLETE")
    print("="*70)
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nTest Set Performance Summary:")
    print(f"\nHome Score Model:")
    print(f"  MAE:  {home_metrics['test']['mae']:.2f} points")
    print(f"  RMSE: {home_metrics['test']['rmse']:.2f} points")
    print(f"  R²:   {home_metrics['test']['r2']:.4f}")
    print(f"\nAway Score Model:")
    print(f"  MAE:  {away_metrics['test']['mae']:.2f} points")
    print(f"  RMSE: {away_metrics['test']['rmse']:.2f} points")
    print(f"  R²:   {away_metrics['test']['r2']:.4f}")
    
    print("\n" + "="*70)
    print("Models saved in:", MODEL_DIR)
    print("Results saved in:", RESULTS_DIR)
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

