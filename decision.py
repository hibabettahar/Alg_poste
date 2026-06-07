"""
Moteur de décision : traduit les sorties ML en alertes et recommandations métier.
"""

from config.config import STOCK_CONFIG


def generer_alertes(stock_actuel: int, quantite_max: int,
                    jours_avant_rupture: float, conso_moyenne: float) -> list:
    alertes = []
    seuil = STOCK_CONFIG["seuil_alerte_rupture_jours"]

    if stock_actuel <= 0:
        alertes.append({
            "niveau": "CRITIQUE",
            "code":   "RUPTURE_STOCK",
            "message": "Stock Edahabia épuisé. Commande fournisseur urgente requise.",
        })
    elif jours_avant_rupture <= seuil:
        alertes.append({
            "niveau": "URGENT",
            "code":   "RUPTURE_IMMINENTE",
            "message": (
                f"Stock suffisant pour {jours_avant_rupture} jours seulement. "
                f"Déclencher commande fournisseur immédiatement."
            ),
        })

    if quantite_max and stock_actuel > quantite_max:
        exces = stock_actuel - quantite_max
        alertes.append({
            "niveau": "AVERTISSEMENT",
            "code":   "SURSTOCK",
            "message": (
                f"Stock Edahabia dépasse le seuil maximum ({quantite_max:,} unités). "
                f"Excédent : {exces:,} unités. Réduire les prochaines commandes."
            ),
        })

    if not alertes:
        alertes.append({
            "niveau": "OK",
            "code":   "STOCK_NORMAL",
            "message": "Niveau de stock Edahabia dans les limites normales.",
        })

    return alertes


def generer_recommandations(stock_actuel: int, quantite_max: int,
                             conso_moyenne: float, demande_totale_prevue: int) -> list:
    recommandations = []
    seuil = STOCK_CONFIG["seuil_alerte_rupture_jours"]
    horizon = STOCK_CONFIG["horizon_prediction_jours"]

    # Stock de sécurité = consommation moyenne × seuil d'alerte
    stock_securite = int(conso_moyenne * seuil)
    stock_cible    = int(conso_moyenne * horizon)

    deficit = max(0, demande_totale_prevue + stock_securite - stock_actuel)

    if deficit > 0:
        recommandations.append({
            "action":    "COMMANDER",
            "quantite":  deficit,
            "motif":     (
                f"Pour couvrir la demande prévue sur {horizon} jours "
                f"({demande_totale_prevue:,} unités) + stock de sécurité "
                f"({stock_securite:,} unités)."
            ),
        })

    if quantite_max and stock_actuel > quantite_max:
        recommandations.append({
            "action":  "REDUIRE_COMMANDES",
            "quantite": stock_actuel - quantite_max,
            "motif":   "Stock actuel dépasse le seuil maximum autorisé.",
        })

    if not recommandations:
        recommandations.append({
            "action":  "MAINTENIR",
            "quantite": 0,
            "motif":   f"Le stock couvre la demande prévue sur {horizon} jours sans action requise.",
        })

    return recommandations


def calculer_kpis(df_journalier, df_mensuel, df_annuel,
                  stock_actuel: int, quantite_max: int,
                  conso_moyenne: float, jours_avant_rupture: float) -> dict:
    dernier_mois  = df_mensuel.iloc[-1] if not df_mensuel.empty else None
    dernier_annee = df_annuel.iloc[-1]  if not df_annuel.empty  else None

    taux_couverture = round(jours_avant_rupture, 1) if jours_avant_rupture != float("inf") else None
    taux_surstock   = round(stock_actuel / quantite_max * 100, 1) if quantite_max else None

    nb_jours_rupture = int((df_journalier["stock_cumule"] <= 0).sum())
    nb_jours_surstock = int((df_journalier["stock_cumule"] > quantite_max).sum()) if quantite_max else 0

    return {
        "stock_actuel":              stock_actuel,
        "quantite_max_autorisee":    quantite_max,
        "consommation_moyenne_jour": round(conso_moyenne, 1),
        "jours_couverture":          taux_couverture,
        "taux_utilisation_stock_pct": taux_surstock,
        "nb_jours_en_rupture_historique":  nb_jours_rupture,
        "nb_jours_en_surstock_historique": nb_jours_surstock,
        "entrees_mois_en_cours":  int(dernier_mois["entrees"])  if dernier_mois  is not None else None,
        "sorties_mois_en_cours":  int(dernier_mois["sorties"])  if dernier_mois  is not None else None,
        "entrees_annee_en_cours": int(dernier_annee["entrees"]) if dernier_annee is not None else None,
        "sorties_annee_en_cours": int(dernier_annee["sorties"]) if dernier_annee is not None else None,
    }
