"""
Toute l'agrégation est faite en SQL côté PostgreSQL.
On ne charge jamais les 20M lignes brutes en mémoire.
"""

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from config.config import DB_CONFIG, STOCK_CONFIG


def _get_connection():
    return psycopg2.connect(**DB_CONFIG)


def load_mouvements_journaliers() -> pd.DataFrame:
    """
    Agrège les mouvements de stockage par jour.
    Retourne : date_jour, entrees, sorties, solde_jour
    """
    sql = """
        SELECT
            date_jour,
            SUM(CASE WHEN type_operation = %(reception)s THEN quantite ELSE 0 END) AS entrees,
            SUM(CASE WHEN type_operation = %(sortie)s    THEN quantite ELSE 0 END) AS sorties,
            SUM(CASE WHEN type_operation = %(reception)s THEN  quantite
                     WHEN type_operation = %(sortie)s    THEN -quantite
                     ELSE 0 END) AS solde_jour
        FROM stockage
        WHERE LOWER(type_matiere) = %(matiere)s
        GROUP BY date_jour
        ORDER BY date_jour;
    """
    params = {
        "reception": STOCK_CONFIG["type_reception"],
        "sortie":    STOCK_CONFIG["type_sortie"],
        "matiere":   STOCK_CONFIG["type_matiere"],
    }
    with _get_connection() as conn:
        df = pd.read_sql_query(sql, conn, params=params, parse_dates=["date_jour"])
    df["stock_cumule"] = df["solde_jour"].cumsum()
    return df


def load_mouvements_mensuels() -> pd.DataFrame:
    """
    Agrège par mois (YYYY-MM).
    """
    sql = """
        SELECT
            DATE_TRUNC('month', date_jour) AS mois,
            SUM(CASE WHEN type_operation = %(reception)s THEN quantite ELSE 0 END) AS entrees,
            SUM(CASE WHEN type_operation = %(sortie)s    THEN quantite ELSE 0 END) AS sorties
        FROM stockage
        WHERE LOWER(type_matiere) = %(matiere)s
        GROUP BY DATE_TRUNC('month', date_jour)
        ORDER BY mois;
    """
    params = {
        "reception": STOCK_CONFIG["type_reception"],
        "sortie":    STOCK_CONFIG["type_sortie"],
        "matiere":   STOCK_CONFIG["type_matiere"],
    }
    with _get_connection() as conn:
        df = pd.read_sql_query(sql, conn, params=params, parse_dates=["mois"])
    df["solde_mensuel"] = df["entrees"] - df["sorties"]
    df["stock_cumule"] = df["solde_mensuel"].cumsum()
    return df


def load_mouvements_annuels() -> pd.DataFrame:
    """
    Agrège par année.
    """
    sql = """
        SELECT
            EXTRACT(YEAR FROM date_jour)::integer AS annee,
            SUM(CASE WHEN type_operation = %(reception)s THEN quantite ELSE 0 END) AS entrees,
            SUM(CASE WHEN type_operation = %(sortie)s    THEN quantite ELSE 0 END) AS sorties
        FROM stockage
        WHERE LOWER(type_matiere) = %(matiere)s
        GROUP BY EXTRACT(YEAR FROM date_jour)
        ORDER BY annee;
    """
    params = {
        "reception": STOCK_CONFIG["type_reception"],
        "sortie":    STOCK_CONFIG["type_sortie"],
        "matiere":   STOCK_CONFIG["type_matiere"],
    }
    with _get_connection() as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    df["solde_annuel"] = df["entrees"] - df["sorties"]
    df["stock_cumule"] = df["solde_annuel"].cumsum()
    return df


def load_mouvements_horaires_recent(nb_jours: int = 90) -> pd.DataFrame:
    """
    Charge les mouvements horaires des N derniers jours uniquement.
    Utilisé pour la détection d'anomalies sur données récentes.
    """
    sql = """
        SELECT
            DATE_TRUNC('hour', date_operation) AS heure,
            type_operation,
            SUM(quantite) AS quantite
        FROM stockage
        WHERE LOWER(type_matiere) = %(matiere)s
          AND date_operation >= NOW() - INTERVAL '%(nb_jours)s days'
        GROUP BY DATE_TRUNC('hour', date_operation), type_operation
        ORDER BY heure;
    """
    # psycopg2 ne permet pas d'interpoler INTERVAL dynamiquement — on le fait manuellement (valeur entière contrôlée)
    sql = f"""
        SELECT
            DATE_TRUNC('hour', date_operation) AS heure,
            type_operation,
            SUM(quantite) AS quantite
        FROM stockage
        WHERE LOWER(type_matiere) = %(matiere)s
          AND date_operation >= NOW() - INTERVAL '{int(nb_jours)} days'
        GROUP BY DATE_TRUNC('hour', date_operation), type_operation
        ORDER BY heure;
    """
    params = {"matiere": STOCK_CONFIG["type_matiere"]}
    with _get_connection() as conn:
        df = pd.read_sql_query(sql, conn, params=params, parse_dates=["heure"])
    return df


def load_stock_actuel() -> dict:
    """
    Calcule le stock actuel en une seule requête d'agrégation.
    """
    sql = """
        SELECT
            SUM(CASE WHEN type_operation = %(reception)s THEN  quantite
                     WHEN type_operation = %(sortie)s    THEN -quantite
                     ELSE 0 END) AS stock_actuel
        FROM stockage
        WHERE LOWER(type_matiere) = %(matiere)s;
    """
    params = {
        "reception": STOCK_CONFIG["type_reception"],
        "sortie":    STOCK_CONFIG["type_sortie"],
        "matiere":   STOCK_CONFIG["type_matiere"],
    }
    with _get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
    return {"stock_actuel": int(row["stock_actuel"] or 0)}


def load_parametre_stock() -> dict:
    """
    Charge le seuil max de stock pour Edahabia.
    """
    sql = """
        SELECT quantite_max
        FROM parametre_stock
        WHERE LOWER(type_matiere) = %(matiere)s
        LIMIT 1;
    """
    params = {"matiere": STOCK_CONFIG["type_matiere"]}
    with _get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
    return {"quantite_max": int(row["quantite_max"]) if row else None}
