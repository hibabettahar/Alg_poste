"""
Détection d'anomalies sur les mouvements de stock.
Deux approches complémentaires :
  1. Z-Score sur les sorties journalières → pics inhabituels
  2. Isolation Forest sur features multivariées → anomalies complexes
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from config.config import STOCK_CONFIG


def detecter_pics_zscore(df_journalier: pd.DataFrame) -> list:
    """
    Détecte les jours où les sorties dépassent le seuil Z-Score.
    Retourne la liste des jours considérés comme pics.
    """
    seuil = STOCK_CONFIG["seuil_pic_zscore"]
    sorties = df_journalier["sorties"].copy()
    moyenne = sorties.rolling(30, min_periods=7).mean()
    ecart   = sorties.rolling(30, min_periods=7).std()

    zscore = (sorties - moyenne) / (ecart + 1e-9)
    df_journalier = df_journalier.copy()
    df_journalier["zscore"] = zscore

    pics = df_journalier[zscore.abs() > seuil]
    return [
        {
            "date":        row["date_jour"].strftime("%Y-%m-%d"),
            "sorties":     int(row["sorties"]),
            "zscore":      round(float(row["zscore"]), 2),
            "type":        "pic_hausse" if row["zscore"] > 0 else "chute_anormale",
        }
        for _, row in pics.iterrows()
    ]


def detecter_anomalies_isolation_forest(df_journalier: pd.DataFrame) -> list:
    """
    Détecte des anomalies multivariées (sorties + entrees + solde + rolling).
    Utilise Isolation Forest.
    """
    contamination = STOCK_CONFIG["contamination_anomalie"]

    features = ["entrees", "sorties", "solde_jour",
                "rolling_7", "rolling_30", "lag_7"]

    # S'assurer que les features existent (rolling/lag peuvent manquer si non calculées)
    df = df_journalier.copy()
    if "rolling_7" not in df.columns:
        df["rolling_7"]  = df["sorties"].rolling(7,  min_periods=1).mean()
    if "rolling_30" not in df.columns:
        df["rolling_30"] = df["sorties"].rolling(30, min_periods=1).mean()
    if "lag_7" not in df.columns:
        df["lag_7"]      = df["sorties"].shift(7)

    df_feat = df[features].fillna(0)

    scaler = StandardScaler()
    X = scaler.fit_transform(df_feat)

    clf = IsolationForest(contamination=contamination, random_state=42, n_jobs=-1)
    df["anomalie_if"] = clf.fit_predict(X)      # -1 = anomalie, 1 = normal
    df["score_if"]    = clf.score_samples(X)    # plus négatif = plus anormal

    anomalies = df[df["anomalie_if"] == -1]
    return [
        {
            "date":       row["date_jour"].strftime("%Y-%m-%d"),
            "sorties":    int(row["sorties"]),
            "entrees":    int(row["entrees"]),
            "score":      round(float(row["score_if"]), 4),
            "description": "Comportement inhabituel détecté (Isolation Forest)",
        }
        for _, row in anomalies.iterrows()
    ]
