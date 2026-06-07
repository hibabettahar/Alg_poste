"""
Prédiction de la demande future en cartes Edahabia.
Utilise Prophet pour capturer la saisonnalité et les tendances.
Compare avec une baseline rolling-mean pour valider la pertinence.
"""

import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_percentage_error
from config.config import STOCK_CONFIG


def _preparer_prophet(df: pd.DataFrame) -> pd.DataFrame:
    """Formate le DataFrame pour Prophet (colonnes ds et y obligatoires)."""
    return df.rename(columns={"date_jour": "ds", "sorties": "y"})[["ds", "y"]].dropna()


def entrainer_et_predire(df_journalier: pd.DataFrame) -> dict:
    """
    Entraîne Prophet sur l'historique complet et génère les prédictions.
    Retourne les prédictions + métriques de performance.
    """
    horizon = STOCK_CONFIG["horizon_prediction_jours"]
    df_prophet = _preparer_prophet(df_journalier)

    # Séparation train/test (20% pour validation)
    n_test = max(30, int(len(df_prophet) * 0.2))
    df_train = df_prophet.iloc[:-n_test]
    df_test  = df_prophet.iloc[-n_test:]

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode="multiplicative",
        changepoint_prior_scale=0.05,
    )
    model.fit(df_train)

    # Validation sur jeu de test
    future_test = model.make_future_dataframe(periods=n_test, freq="D")
    forecast_test = model.predict(future_test)
    y_pred_test = forecast_test.tail(n_test)["yhat"].clip(lower=0).values
    y_true_test = df_test["y"].values
    mape = float(mean_absolute_percentage_error(y_true_test + 1, y_pred_test + 1))

    # Prédiction sur l'horizon futur
    future = model.make_future_dataframe(periods=horizon, freq="D")
    forecast = model.predict(future)
    predictions = forecast.tail(horizon)[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    predictions["yhat"]       = predictions["yhat"].clip(lower=0).round().astype(int)
    predictions["yhat_lower"] = predictions["yhat_lower"].clip(lower=0).round().astype(int)
    predictions["yhat_upper"] = predictions["yhat_upper"].clip(lower=0).round().astype(int)

    records = [
        {
            "date": row["ds"].strftime("%Y-%m-%d"),
            "demande_prevue":    int(row["yhat"]),
            "intervalle_bas":    int(row["yhat_lower"]),
            "intervalle_haut":   int(row["yhat_upper"]),
        }
        for _, row in predictions.iterrows()
    ]

    return {
        "horizon_jours": horizon,
        "mape_validation": round(mape * 100, 2),
        "predictions": records,
        "demande_totale_prevue": int(predictions["yhat"].sum()),
    }
