#!/usr/bin/env python3
"""
Synchronize KoboToolkit responses to SQLite database
Formulaire: a3eBvSNuEVwn5EXffC7L8u (nouveau formulaire MFWA MTI Barometer)
"""

import json
import requests
import os
from dotenv import load_dotenv
from database import SessionLocal
from models import Outlet, Respondent, Response, MTIIndex

load_dotenv()

# ============================================================
# MAPPINGS
# ============================================================

# Conversion Likert 5 points → score 0-100
LIKERT_MAPPING = {
    "strongly_agree": 100,
    "agree": 75,
    "neither": 50,
    "disagree": 25,
    "strongly_disagree": 0,
    # Variantes possibles dans les réponses Kobo
    "1": 0,
    "2": 25,
    "3": 50,
    "4": 75,
    "5": 100,
}

# Déduire le type de média depuis le nom de l'outlet
OUTLET_TYPE_MAP = {
    "citifm": "Radio", "citi fm": "Radio",
    "joyfm": "Radio", "joy fm": "Radio",
    "peacefm": "Radio", "peace fm": "Radio",
    "adomfm": "Radio", "adom fm": "Radio",
    "asaase": "Radio",
    "omanfm": "Radio", "oman fm": "Radio",
    "univers": "Radio",
    "nhyirafo": "Radio",
    "kapital": "Radio",
    "metro tv": "TV", "metro": "TV",
    "adom tv": "TV",
    "ghone": "TV", "gh one": "TV",
    "tv3": "TV",
    "gbc": "TV",
    "angel tv": "TV",
    "citinewsroom": "Online",
    "myjoyonline": "Online",
    "ghanaweb": "Online",
    "pulse": "Online",
    "graphic online": "Online",
    "daily graphic": "Print", "graphic": "Print",
    "ghanaian times": "Print",
    "the chronicle": "Print",
    "daily guide": "Print",
}

def guess_outlet_type(outlet_name):
    """Devine le type de média depuis le nom de l'outlet"""
    name_lower = outlet_name.lower().strip()
    for keyword, media_type in OUTLET_TYPE_MAP.items():
        if keyword in name_lower:
            return media_type
    if any(x in name_lower for x in ["fm", "radio"]):
        return "Radio"
    if any(x in name_lower for x in ["tv", "television"]):
        return "TV"
    if any(x in name_lower for x in ["online", ".com", ".gh"]):
        return "Online"
    if any(x in name_lower for x in ["times", "graphic", "chronicle", "guide", "news", "paper"]):
        return "Print"
    return "Radio"  # Ghana = radio dominante

def kobo_to_score(value):
    """Convertit une réponse Likert Kobo en score 0-100"""
    if not value:
        return 50
    return LIKERT_MAPPING.get(str(value).lower().strip(), 50)

def safe_int(value, default=None):
    """Convertit en int sans lever d'exception"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

# ============================================================
# SYNC PRINCIPAL
# ============================================================

def sync_kobo_responses():
    """Fetch from Kobo and save to SQLite"""

    token = os.getenv("KOBO_TOKEN")
    # ✅ Nouveau UID de formulaire
    form_uid = os.getenv("KOBO_FORM_UID", "a3eBvSNuEVwn5EXffC7L8u")

    url = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/data/"
    headers = {"Authorization": f"Token {token}"}

    print(f"Fetching data from: {url}")

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return

    submissions = data.get('results', [])
    print(f"Found {len(submissions)} submissions")

    if not submissions:
        print("No submissions to sync")
        return

    db = SessionLocal()
    synced = 0

    for sub in submissions:
        try:
            kobo_id = str(sub.get('_uuid', ''))

            # Vérifier si déjà synced
            existing = db.query(Response).filter(
                Response.kobo_submission_id == kobo_id
            ).first()
            if existing:
                print(f"  Skipping {kobo_id} (already synced)")
                continue

            # ── Outlet ──────────────────────────────────────────
            # Nouveau champ: grp_outlets/rated_outlet (était: rating/outlet_name)
            outlet_name_raw = sub.get('grp_outlets/rated_outlet', '')
            # Fallback: si le répondant a précisé "other"
            if not outlet_name_raw or outlet_name_raw.lower() in ('other', 'nan', ''):
                outlet_name_raw = sub.get('grp_outlets/rated_outlet_other', 'Unknown')
            outlet_name = outlet_name_raw.title().strip() if outlet_name_raw else 'Unknown'
            outlet_type = guess_outlet_type(outlet_name)

            # Région maintenant à la racine (était: geo/region)
            outlet_region = sub.get('region', 'Unknown')

            outlet = db.query(Outlet).filter(
                Outlet.outlet_name == outlet_name
            ).first()

            if not outlet:
                outlet = Outlet(
                    outlet_name=outlet_name,
                    outlet_type=outlet_type,
                    region=outlet_region
                )
                db.add(outlet)
                db.flush()
                print(f"  Created outlet: {outlet_name} ({outlet_type})")
            else:
                if outlet.outlet_type == "Radio" and outlet_type != "Radio":
                    outlet.outlet_type = outlet_type
                print(f"  Outlet exists: {outlet_name}")

            # ── Respondent ───────────────────────────────────────
            respondent_name = f"R{sub.get('_id', kobo_id[:8])}"

            respondent = db.query(Respondent).filter(
                Respondent.outlet_id == outlet.id,
                Respondent.respondent_name == respondent_name
            ).first()

            if not respondent:
                respondent = Respondent(
                    outlet_id=outlet.id,
                    respondent_name=respondent_name,
                    respondent_role="Survey Respondent",
                    phone=""
                )
                db.add(respondent)
                db.flush()

            # ── Scores MTI (6 dimensions) ────────────────────────
            # Nouveaux chemins: grp_trust/mti_* (étaient: rating/outlet_grp/outlet_*)
            accuracy        = kobo_to_score(sub.get('grp_trust/mti_accurate'))
            verification    = kobo_to_score(sub.get('grp_trust/mti_verify'))
            independence    = kobo_to_score(sub.get('grp_trust/mti_independent'))
            fair_balanced   = kobo_to_score(sub.get('grp_trust/mti_fair'))
            public_interest = kobo_to_score(sub.get('grp_trust/mti_public'))
            corrections     = kobo_to_score(sub.get('grp_trust/mti_corrects'))

            print(f"  Scores: acc={accuracy} ver={verification} ind={independence} "
                  f"fair={fair_balanced} pub={public_interest} cor={corrections}")

            # ── Confiance globale ────────────────────────────────
            # Nouveau: integer 0-10 (était: select_one trust11)
            overall_trust_raw = safe_int(sub.get('grp_trust/overall_trust'))
            # Normaliser en 0-100 pour cohérence (0-10 → 0-100)
            overall_trust_100 = (overall_trust_raw * 10) if overall_trust_raw is not None else None

            # ── Partisanship ─────────────────────────────────────
            # Renommés dans nouveau formulaire
            party_link        = sub.get('grp_partisanship/party_link', '')       # était: outlet_align
            pol_align         = sub.get('grp_partisanship/pol_align', '')         # était: outlet_polshape
            gov_influence     = sub.get('grp_partisanship/gov_influence', '')     # NOUVEAU
            owner_influence   = sub.get('grp_partisanship/owner_influence', '')   # NOUVEAU
            political_pressure = sub.get('grp_partisanship/political_pressure', '') # NOUVEAU

            # ── Démographie ──────────────────────────────────────
            # Groupe renommé grp_profile (était: demo)
            demo_sex        = sub.get('grp_profile/sex', '')
            demo_age_group  = sub.get('grp_profile/age_group', '')   # CHANGÉ: integer → select_one
            demo_education  = sub.get('grp_profile/education', '')
            demo_employment = sub.get('grp_profile/employment', '')
            demo_disability = sub.get('grp_profile/disability', '')  # NOUVEAU
            demo_residence  = sub.get('grp_profile/residence', '')   # était: residence_type
            demo_internet   = sub.get('grp_profile/internet_access', '')
            demo_smartphone = sub.get('grp_profile/smartphone', '')  # NOUVEAU

            # ── Plateformes ──────────────────────────────────────
            # Groupe renommé grp_media_use, plus de sous-groupes (était: platforms/xxx_grp/)
            use_radio    = sub.get('grp_media_use/use_radio', '')
            use_tv       = sub.get('grp_media_use/use_tv', '')
            use_print    = sub.get('grp_media_use/use_print', '')      # NOUVEAU
            use_online   = sub.get('grp_media_use/use_online', '')
            use_social   = sub.get('grp_media_use/use_social', '')
            use_whatsapp = sub.get('grp_media_use/use_whatsapp', '')   # NOUVEAU
            use_youtube  = sub.get('grp_media_use/use_youtube', '')    # NOUVEAU
            use_podcast  = sub.get('grp_media_use/use_podcast', '')    # NOUVEAU
            freq_radio   = sub.get('grp_media_use/freq_radio', '')
            freq_tv      = sub.get('grp_media_use/freq_tv', '')
            freq_online  = sub.get('grp_media_use/freq_online', '')
            freq_social  = sub.get('grp_media_use/freq_social', '')
            main_source  = sub.get('grp_media_use/main_source', '')    # NOUVEAU

            # ── Géo détaillée ────────────────────────────────────
            # district maintenant select_one (était text)
            district  = sub.get('district', '')
            community = sub.get('community', '')  # était: locality

            # ── Scores additionnels calculés par Kobo ────────────
            # Le nouveau formulaire calcule automatiquement plusieurs scores
            mri_score    = sub.get('grp_reach/mri_score', None)
            mti_score_kobo = sub.get('grp_trust/mti_score', None)
            ppi_score    = sub.get('grp_partisanship/ppi_score', None)

            # ── Reach (nouveau) ──────────────────────────────────
            outlet_days         = safe_int(sub.get('grp_reach/outlet_days'))
            outlet_time_minutes = safe_int(sub.get('grp_reach/outlet_time_minutes'))
            outlet_frequency    = sub.get('grp_reach/outlet_frequency', '')

            # ── Trust élargi (nouveaux indicateurs) ─────────────
            outlet_professional     = sub.get('grp_trust/outlet_professional', '')
            outlet_ethical          = sub.get('grp_trust/outlet_ethical', '')
            outlet_depth            = sub.get('grp_trust/outlet_depth', '')
            outlet_consistent       = sub.get('grp_trust/outlet_consistent', '')
            outlet_avoids_sensational = sub.get('grp_trust/outlet_avoids_sensational', '')
            outlet_accountability   = sub.get('grp_trust/outlet_accountability', '')
            outlet_civic_education  = sub.get('grp_trust/outlet_civic_education', '')
            outlet_local_relevance  = sub.get('grp_trust/outlet_local_relevance', '')
            recommend_outlet        = safe_int(sub.get('grp_trust/recommend_outlet'))
            continue_use            = safe_int(sub.get('grp_trust/continue_use'))

            # ── Journaliste de confiance (nouveau) ───────────────
            trusted_journalist        = sub.get('grp_outlets/trusted_journalist', '')
            trusted_journalist_reason = sub.get('grp_outlets/trusted_journalist_reason', '')

            # ── Créer la réponse ─────────────────────────────────
            response = Response(
                outlet_id=outlet.id,
                respondent_id=respondent.id,
                kobo_submission_id=kobo_id,
                accuracy_score=float(accuracy),
                verification_score=float(verification),
                independence_score=float(independence),
                fair_balanced_score=float(fair_balanced),
                public_interest_score=float(public_interest),
                corrections_score=float(corrections),
                raw_response_data=json.dumps({
                    # Confiance
                    "overall_trust": overall_trust_raw,
                    "overall_trust_100": overall_trust_100,
                    # Partisanship
                    "outlet_align": party_link,          # clé conservée pour compat dashboard
                    "outlet_polshape": pol_align,         # clé conservée pour compat dashboard
                    "party_link": party_link,
                    "pol_align": pol_align,
                    "gov_influence": gov_influence,
                    "owner_influence": owner_influence,
                    "political_pressure": political_pressure,
                    # Démographie
                    "demo": {
                        "sex": demo_sex,
                        "age_group": demo_age_group,
                        "education": demo_education,
                        "employment": demo_employment,
                        "disability": demo_disability,
                        "residence": demo_residence,
                        "internet_access": demo_internet,
                        "smartphone": demo_smartphone,
                    },
                    # Plateformes
                    "platforms": {
                        "use_radio": use_radio,
                        "use_tv": use_tv,
                        "use_print": use_print,
                        "use_online": use_online,
                        "use_social": use_social,
                        "use_whatsapp": use_whatsapp,
                        "use_youtube": use_youtube,
                        "use_podcast": use_podcast,
                        "freq_radio": freq_radio,
                        "freq_tv": freq_tv,
                        "freq_online": freq_online,
                        "freq_social": freq_social,
                        "main_source": main_source,
                    },
                    # Géo
                    "geo": {
                        "region": outlet_region,
                        "district": district,
                        "community": community,
                    },
                    # Reach
                    "reach": {
                        "outlet_days": outlet_days,
                        "outlet_time_minutes": outlet_time_minutes,
                        "outlet_frequency": outlet_frequency,
                        "mri_score": mri_score,
                    },
                    # Trust élargi
                    "trust_extended": {
                        "outlet_professional": outlet_professional,
                        "outlet_ethical": outlet_ethical,
                        "outlet_depth": outlet_depth,
                        "outlet_consistent": outlet_consistent,
                        "outlet_avoids_sensational": outlet_avoids_sensational,
                        "outlet_accountability": outlet_accountability,
                        "outlet_civic_education": outlet_civic_education,
                        "outlet_local_relevance": outlet_local_relevance,
                        "recommend_outlet": recommend_outlet,
                        "continue_use": continue_use,
                    },
                    # Scores Kobo calculés
                    "kobo_scores": {
                        "mti_score": mti_score_kobo,
                        "ppi_score": ppi_score,
                        "mri_score": mri_score,
                    },
                    # Journaliste
                    "trusted_journalist": trusted_journalist,
                    "trusted_journalist_reason": trusted_journalist_reason,
                    # Raw pour debug
                    "_raw": sub,
                })
            )
            db.add(response)
            synced += 1
            print(f"  Synced response for {outlet_name}")

        except Exception as e:
            print(f"  Error processing submission {sub.get('_uuid', '?')}: {e}")
            db.rollback()
            continue

    db.commit()

    # ── Recalculer les scores MTI ────────────────────────────────
    outlets_all = db.query(Outlet).all()
    for outlet in outlets_all:
        responses = db.query(Response).filter(Response.outlet_id == outlet.id).all()
        if not responses:
            continue

        n = len(responses)
        mti_score = (
            sum(r.accuracy_score for r in responses) / n * 0.20 +
            sum(r.verification_score for r in responses) / n * 0.20 +
            sum(r.independence_score for r in responses) / n * 0.20 +
            sum(r.fair_balanced_score for r in responses) / n * 0.15 +
            sum(r.public_interest_score for r in responses) / n * 0.15 +
            sum(r.corrections_score for r in responses) / n * 0.10
        )

        mti_index = db.query(MTIIndex).filter(MTIIndex.outlet_id == outlet.id).first()
        if mti_index:
            mti_index.mti_score = round(mti_score, 2)
        else:
            db.add(MTIIndex(outlet_id=outlet.id, mti_score=round(mti_score, 2)))

        print(f"  {outlet.outlet_name} ({outlet.outlet_type}) - MTI: {round(mti_score, 2)}")

    db.commit()
    db.close()

    print(f"\nSync complete! {synced} new responses saved.")


if __name__ == "__main__":
    print("Starting KoboToolkit sync...\n")
    sync_kobo_responses()