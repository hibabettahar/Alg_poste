import pandas as pd
import numpy as np
from config.config import STOCK_CONFIG


def calculer_consommation_moyenne(df_journalier: pd.DataFrame) -> float:
    """Consommation moyenne journalière sur la fenêtre glissante définie."""
    fenetre = STOCK_CONFIG["fenetre_consommation_jours"]
    recent = df_journalier.tail(fenetre)
    return float(recent["sorties"].mean()) if not recent.empty else 0.0


def calculer_jours_avant_rupture(stock_actuel: int, conso_moyenne: float) -> float:
    """Nombre de jours avant épuisement du stock au rythme actuel."""
    if conso_moyenne <= 0:
        return float("inf")
    return round(stock_actuel / conso_moyenne, 1)


def enrichir_features_temporelles(df: pd.DataFrame, col_date: str = "date_jour") -> pd.DataFrame:
    """Ajoute des features temporelles utiles pour les modèles ML."""
    df = df.copy()
    d = df[col_date]
    df["annee"]           = d.dt.year
    df["mois"]            = d.dt.month
    df["semaine"]         = d.dt.isocalendar().week.astype(int)
    df["jour_semaine"]    = d.dt.dayofweek          # 0=lundi
    df["est_weekend"]     = (df["jour_semaine"] >= 5).astype(int)
    df["trimestre"]       = d.dt.quarter
    df["lag_7"]           = df["sorties"].shift(7)
    df["lag_14"]          = df["sorties"].shift(14)
    df["lag_30"]          = df["sorties"].shift(30)
    df["rolling_7"]       = df["sorties"].rolling(7,  min_periods=1).mean()
    df["rolling_30"]      = df["sorties"].rolling(30, min_periods=1).mean()
    df["rolling_std_30"]  = df["sorties"].rolling(30, min_periods=1).std()
    return df


def etat_stock_journalier(df_journalier: pd.DataFrame, stock_actuel: int,
                           quantite_max: int, conso_moyenne: float) -> list:
    """
    Retourne l'état du stock jour par jour pour le JSON de sortie.
    Chaque ligne indique : date, stock_estime, statut (normal/surstock/risque_rupture/rupture).
    """
    seuil_rupture = STOCK_CONFIG["seuil_alerte_rupture_jours"]
    records = []
    for _, row in df_journalier.iterrows():
        s = int(row["stock_cumule"])
        jours = calculer_jours_avant_rupture(s, conso_moyenne)

        if s <= 0:
            statut = "rupture"
        elif jours <= seuil_rupture:
            statut = "risque_rupture"
        elif quantite_max and s > quantite_max:
            statut = "surstock"
        else:
            statut = "normal"

        records.append({
            "date": row["date_jour"].strftime("%Y-%m-%d"),
            "entrees": int(row["entrees"]),
            "sorties": int(row["sorties"]),
            "stock_estime": s,
            "statut": statut,
        })
    return records
