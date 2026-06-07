"""
Point d'entrée principal.
Orchestre : extraction SQL → features → ML → décision → JSON.
"""

import sys
from datetime import date

from data.loader import (
    load_mouvements_journaliers,
    load_mouvements_mensuels,
    load_mouvements_annuels,
    load_stock_actuel,
    load_parametre_stock,
)
from features.stock_features import (
    calculer_consommation_moyenne,
    calculer_jours_avant_rupture,
    enrichir_features_temporelles,
    etat_stock_journalier,
)
from models.prediction import entrainer_et_predire
from models.anomaly import detecter_pics_zscore, detecter_anomalies_isolation_forest
from engine.decision import generer_alertes, generer_recommandations, calculer_kpis
from output.json_generator import generer_rapport_json


def _etat_mensuel_json(df_mensuel) -> list:
    return [
        {
            "mois":          row["mois"].strftime("%Y-%m"),
            "entrees":       int(row["entrees"]),
            "sorties":       int(row["sorties"]),
            "stock_cumule":  int(row["stock_cumule"]),
        }
        for _, row in df_mensuel.iterrows()
    ]


def _etat_annuel_json(df_annuel) -> list:
    return [
        {
            "annee":         int(row["annee"]),
            "entrees":       int(row["entrees"]),
            "sorties":       int(row["sorties"]),
            "stock_cumule":  int(row["stock_cumule"]),
        }
        for _, row in df_annuel.iterrows()
    ]


def run(output_path: str = "rapport_stock.json"):
    print("[1/7] Extraction des données depuis PostgreSQL...")
    df_jour    = load_mouvements_journaliers()
    df_mois    = load_mouvements_mensuels()
    df_annee   = load_mouvements_annuels()
    stock_info = load_stock_actuel()
    param      = load_parametre_stock()

    stock_actuel  = stock_info["stock_actuel"]
    quantite_max  = param["quantite_max"]

    print("[2/7] Calcul des features...")
    df_jour = enrichir_features_temporelles(df_jour)
    conso_moy = calculer_consommation_moyenne(df_jour)
    jours_rupture = calculer_jours_avant_rupture(stock_actuel, conso_moy)

    print("[3/7] Prédiction de demande (Prophet)...")
    result_prediction = entrainer_et_predire(df_jour)

    print("[4/7] Détection d'anomalies et de pics...")
    pics        = detecter_pics_zscore(df_jour)
    anomalies   = detecter_anomalies_isolation_forest(df_jour)

    print("[5/7] Génération des alertes et recommandations...")
    alertes         = generer_alertes(stock_actuel, quantite_max, jours_rupture, conso_moy)
    recommandations = generer_recommandations(
        stock_actuel, quantite_max, conso_moy,
        result_prediction["demande_totale_prevue"]
    )

    print("[6/7] Calcul des KPIs...")
    kpis = calculer_kpis(df_jour, df_mois, df_annee,
                         stock_actuel, quantite_max, conso_moy, jours_rupture)

    etat_jour  = etat_stock_journalier(df_jour, stock_actuel, quantite_max, conso_moy)
    etat_mois  = _etat_mensuel_json(df_mois)
    etat_annee = _etat_annuel_json(df_annee)

    print("[7/7] Génération du rapport JSON...")
    chemin = generer_rapport_json(
        date_rapport     = date.today().isoformat(),
        kpis             = kpis,
        alertes          = alertes,
        recommandations  = recommandations,
        etat_journalier  = etat_jour,
        etat_mensuel     = etat_mois,
        etat_annuel      = etat_annee,
        predictions      = result_prediction,
        anomalies_zscore = pics,
        anomalies_if     = anomalies,
        output_path      = output_path,
    )

    print(f"\nRapport généré : {chemin}")
    print(f"  Stock actuel       : {stock_actuel:,} cartes")
    print(f"  Jours avant rupture: {jours_rupture}")
    print(f"  Alertes            : {len(alertes)}")
    print(f"  Pics détectés      : {len(pics)}")
    print(f"  Anomalies IF       : {len(anomalies)}")
    return chemin


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "rapport_stock.json"
    run(output)
