import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "alg_poste"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

STOCK_CONFIG = {
    "type_matiere": "edahabia",
    "type_reception": "reception",
    "type_sortie": "sortie",
    # Nombre de jours de consommation moyenne pour prédire la rupture
    "fenetre_consommation_jours": 30,
    # Horizon de prédiction
    "horizon_prediction_jours": 30,
    # Seuil alerte rupture imminente (jours restants)
    "seuil_alerte_rupture_jours": 5,
    # Pourcentage au-dessus duquel on considère une anomalie de pic
    "seuil_pic_zscore": 3.0,
    # Contamination pour Isolation Forest (proportion d'anomalies attendue)
    "contamination_anomalie": 0.03,
}
