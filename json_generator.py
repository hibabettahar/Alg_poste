import json
from datetime import datetime, date
from pathlib import Path


def _serialisable(obj):
    """Convertit les types non-JSON-sérialisables."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type non sérialisable : {type(obj)}")


def generer_rapport_json(
    date_rapport: str,
    kpis: dict,
    alertes: list,
    recommandations: list,
    etat_journalier: list,
    etat_mensuel: list,
    etat_annuel: list,
    predictions: dict,
    anomalies_zscore: list,
    anomalies_if: list,
    output_path: str = "rapport_stock.json",
) -> str:
    rapport = {
        "meta": {
            "date_rapport":    date_rapport,
            "type_matiere":    "edahabia",
            "systeme":         "IA_Stock_AlgeriePoste",
            "version":         "1.0",
        },
        "kpis":              kpis,
        "alertes":           alertes,
        "recommandations":   recommandations,
        "predictions":       predictions,
        "anomalies": {
            "pics_zscore":       anomalies_zscore,
            "anomalies_complexes": anomalies_if,
            "total_anomalies":   len(anomalies_zscore) + len(anomalies_if),
        },
        "etat_stock": {
            "journalier": etat_journalier,
            "mensuel":    etat_mensuel,
            "annuel":     etat_annuel,
        },
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2, default=_serialisable)

    return output_path
