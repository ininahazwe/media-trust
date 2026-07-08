"""
routers/dashboard.py - Dashboard stats, analytics et Kobo synchronization
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Outlet, Response, MTIIndex, Respondent
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# ============================================================
# HELPERS
# ============================================================

RESPONSE_MAPPING = {
    "strongly_agree": 100,
    "agree": 75,
    "neither": 50,
    "disagree": 25,
    "strongly_disagree": 0,
}

OUTLET_TYPE_MAP = {
    "citifm": "Radio", "citi fm": "Radio",
    "joyfm": "Radio", "joy fm": "Radio",
    "peacefm": "Radio", "peace fm": "Radio",
    "adomfm": "Radio", "adom fm": "Radio",
    "asaase": "Radio", "omanfm": "Radio", "oman fm": "Radio",
    "metro tv": "TV", "metro": "TV",
    "adom tv": "TV", "ghone": "TV", "gh one": "TV",
    "tv3": "TV", "gbc": "TV",
    "citinewsroom": "Online", "myjoyonline": "Online",
    "graphic": "Print", "daily graphic": "Print",
}

def guess_outlet_type(name):
    n = name.lower().strip()
    for k, v in OUTLET_TYPE_MAP.items():
        if k in n:
            return v
    if any(x in n for x in ["fm", "radio"]):
        return "Radio"
    if any(x in n for x in ["tv", "television"]):
        return "TV"
    if any(x in n for x in ["online", "news", ".com", ".gh"]):
        return "Online"
    return "Radio"

def kobo_to_score(value):
    if not value:
        return 50
    return RESPONSE_MAPPING.get(str(value).lower(), 50)


# ============================================================
# DASHBOARD GLOBAL
# ============================================================

@router.get("/")
async def get_dashboard(db: Session = Depends(get_db)):
    total_outlets = db.query(func.count(Outlet.id)).scalar() or 0
    total_respondents = db.query(func.count(Respondent.id)).scalar() or 0
    total_responses = db.query(func.count(Response.id)).scalar() or 0

    mti_scores = db.query(MTIIndex.mti_score).all()
    average_mti = sum(s[0] for s in mti_scores) / len(mti_scores) if mti_scores else 0

    top_outlets_query = db.query(
        Outlet.id,
        Outlet.outlet_name,
        Outlet.outlet_type,
        Outlet.region,
        MTIIndex.mti_score
    ).join(
        MTIIndex, Outlet.id == MTIIndex.outlet_id
    ).order_by(
        MTIIndex.mti_score.desc()
    ).limit(10).all()

    top_outlets = []
    for row in top_outlets_query:
        outlet_id, name, otype, region, score = row
        resp_count = db.query(func.count(Response.id)).filter(
            Response.outlet_id == outlet_id
        ).scalar() or 0
        top_outlets.append({
            "id": outlet_id,
            "name": name,
            "type": otype or guess_outlet_type(name),
            "region": region,
            "score": round(score, 2) if score else 0,
            "mti_score": round(score, 2) if score else 0,
            "responses_count": resp_count,
        })

    return {
        "total_outlets": total_outlets,
        "total_respondents": total_respondents,
        "total_responses": total_responses,
        "average_mti": round(average_mti, 2),
        "top_outlets": top_outlets,
        "status": "ok"
    }


# ============================================================
# DIMENSIONS BREAKDOWN
# ============================================================

@router.get("/dimensions")
async def get_dimensions_breakdown(db: Session = Depends(get_db)):
    responses = db.query(Response).all()

    if not responses:
        return {
            "accuracy": 0, "verification": 0, "independence": 0,
            "fair_balanced": 0, "public_interest": 0, "corrections": 0
        }

    n = len(responses)
    return {
        "accuracy":       round(sum(r.accuracy_score for r in responses) / n, 2),
        "verification":   round(sum(r.verification_score for r in responses) / n, 2),
        "independence":   round(sum(r.independence_score for r in responses) / n, 2),
        "fair_balanced":  round(sum(r.fair_balanced_score for r in responses) / n, 2),
        "public_interest": round(sum(r.public_interest_score for r in responses) / n, 2),
        "corrections":    round(sum(r.corrections_score for r in responses) / n, 2),
    }


# ============================================================
# ANALYTICS ENRICHIS (depuis raw_response_data)
# ============================================================

@router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """
    Statistiques enrichies extraites du raw_response_data :
    - distribution démographique (âge, sexe, éducation)
    - plateformes utilisées
    - biais politique perçu par outlet
    - score de confiance global moyen
    - score moyen par région
    """
    responses = db.query(Response).all()

    if not responses:
        return {"error": "No data"}

    demo_sex = {}
    demo_age_group = {}
    demo_education = {}
    demo_internet = {}
    demo_residence = {}
    demo_smartphone = {}
    platforms = {"radio": 0, "tv": 0, "online": 0, "social": 0, "whatsapp": 0, "youtube": 0, "print": 0, "podcast": 0}
    political_align = {}
    overall_trust_sum = 0
    overall_trust_count = 0
    region_scores = {}
    # Partisanship
    gov_influence_vals = []
    owner_influence_vals = []
    political_pressure_vals = []

    LIKERT_SCORE = {"strongly_agree": 100, "agree": 75, "neither": 50, "disagree": 25, "strongly_disagree": 0}

    for resp in responses:
        try:
            raw = json.loads(resp.raw_response_data or '{}')
        except Exception:
            continue

        # Démographie
        demo = raw.get("demo", {})
        sex = demo.get("sex", "")
        if sex:
            demo_sex[sex] = demo_sex.get(sex, 0) + 1

        age_group = demo.get("age_group", "")
        if age_group:
            demo_age_group[age_group] = demo_age_group.get(age_group, 0) + 1

        edu = demo.get("education", "")
        if edu:
            demo_education[edu] = demo_education.get(edu, 0) + 1

        inet = demo.get("internet_access", "")
        if inet:
            demo_internet[inet] = demo_internet.get(inet, 0) + 1

        residence = demo.get("residence", demo.get("residence_type", ""))
        if residence:
            demo_residence[residence] = demo_residence.get(residence, 0) + 1

        smartphone = demo.get("smartphone", "")
        if smartphone:
            demo_smartphone[smartphone] = demo_smartphone.get(smartphone, 0) + 1

        # Plateformes
        plat = raw.get("platforms", {})
        for key in ["radio", "tv", "online", "social", "whatsapp", "youtube", "print", "podcast"]:
            if plat.get(f"use_{key}") in ("yes", "1", True):
                platforms[key] += 1

        # Biais politique
        align = raw.get("outlet_align", "") or raw.get("party_link", "")
        if align:
            outlet = db.query(Outlet).filter(Outlet.id == resp.outlet_id).first()
            outlet_name = outlet.outlet_name if outlet else str(resp.outlet_id)
            if outlet_name not in political_align:
                political_align[outlet_name] = {}
            political_align[outlet_name][align] = political_align[outlet_name].get(align, 0) + 1

        # Score de confiance global
        trust_raw = raw.get("overall_trust")
        if trust_raw is not None:
            try:
                overall_trust_sum += float(trust_raw)
                overall_trust_count += 1
            except (ValueError, TypeError):
                pass

        # Scores par région
        geo = raw.get("geo", {})
        region = geo.get("region", "")
        if region:
            mti = (
                resp.accuracy_score * 0.20 +
                resp.verification_score * 0.20 +
                resp.independence_score * 0.20 +
                resp.fair_balanced_score * 0.15 +
                resp.public_interest_score * 0.15 +
                resp.corrections_score * 0.10
            )
            if region not in region_scores:
                region_scores[region] = {"total": 0.0, "count": 0}
            region_scores[region]["total"] += mti
            region_scores[region]["count"] += 1

        # Partisanship (nouveaux champs)
        for field, lst in [
            ("gov_influence", gov_influence_vals),
            ("owner_influence", owner_influence_vals),
            ("political_pressure", political_pressure_vals),
        ]:
            val = raw.get(field, "")
            score = LIKERT_SCORE.get(str(val).lower(), None)
            if score is not None:
                lst.append(score)

    region_avg = {
        r: round(v["total"] / v["count"], 1)
        for r, v in region_scores.items()
        if v["count"] > 0
    }

    def avg_or_none(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    return {
        "demographics": {
            "sex": demo_sex,
            "age_group": demo_age_group,
            "education": demo_education,
            "internet_access": demo_internet,
            "residence": demo_residence,
            "smartphone": demo_smartphone,
        },
        "platforms": platforms,
        "political_alignment": political_align,
        "average_overall_trust": round(overall_trust_sum / overall_trust_count, 2) if overall_trust_count else None,
        "trust_by_region": region_avg,
        "partisanship": {
            "gov_influence":      avg_or_none(gov_influence_vals),
            "owner_influence":    avg_or_none(owner_influence_vals),
            "political_pressure": avg_or_none(political_pressure_vals),
        },
        "total_responses": len(responses),
    }


# ============================================================
# MTI CALCULATION
# ============================================================

@router.post("/calculate-mti")
async def calculate_mti_for_all(db: Session = Depends(get_db)):
    outlets = db.query(Outlet).all()
    updated_count = 0

    for outlet in outlets:
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

        updated_count += 1

    db.commit()
    return {
        "status": "success",
        "message": f"MTI recalculated for {updated_count} outlets",
        "updated_outlets": updated_count
    }


# ============================================================
# KOBO SYNC
# ============================================================

@router.post("/sync-kobo")
async def sync_kobo_data(db: Session = Depends(get_db)):
    try:
        kobo_token = os.getenv("KOBO_TOKEN")
        form_uid = os.getenv("KOBO_FORM_UID", "aSSVtGFgeJti6Ln8KM5EzY")

        if not kobo_token:
            raise HTTPException(status_code=400, detail="KOBO_TOKEN not set in .env")

        url = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/data/"
        headers = {"Authorization": f"Token {kobo_token}"}

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Kobo API error: {response.text}")

        submissions = response.json().get("results", [])
        synced = 0

        for sub in submissions:
            try:
                kobo_id = str(sub.get('_uuid', ''))

                existing = db.query(Response).filter(Response.kobo_submission_id == kobo_id).first()
                if existing:
                    continue

                # ── Outlet ──────────────────────────────────────────
                # Nouveau champ: grp_outlets/rated_outlet (était: rating/outlet_name)
                outlet_name_raw = sub.get('grp_outlets/rated_outlet', '')
                if not outlet_name_raw or outlet_name_raw.lower() in ('other', 'nan', ''):
                    outlet_name_raw = sub.get('grp_outlets/rated_outlet_other', 'Unknown')
                outlet_name = outlet_name_raw.title().strip() if outlet_name_raw else 'Unknown'
                outlet_type = guess_outlet_type(outlet_name)
                # Région maintenant à la racine (était: geo/region)
                outlet_region = sub.get('region', 'Unknown')

                outlet = db.query(Outlet).filter(Outlet.outlet_name == outlet_name).first()
                if not outlet:
                    outlet = Outlet(outlet_name=outlet_name, outlet_type=outlet_type, region=outlet_region)
                    db.add(outlet)
                    db.flush()
                else:
                    if outlet.outlet_type == "Radio" and outlet_type != "Radio":
                        outlet.outlet_type = outlet_type

                # Respondent
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

                # ── Scores MTI ───────────────────────────────────────
                # Nouveaux chemins: grp_trust/mti_* (étaient: rating/outlet_grp/outlet_*)
                accuracy        = kobo_to_score(sub.get('grp_trust/mti_accurate'))
                verification    = kobo_to_score(sub.get('grp_trust/mti_verify'))
                independence    = kobo_to_score(sub.get('grp_trust/mti_independent'))
                fair_balanced   = kobo_to_score(sub.get('grp_trust/mti_fair'))
                public_interest = kobo_to_score(sub.get('grp_trust/mti_public'))
                corrections     = kobo_to_score(sub.get('grp_trust/mti_corrects'))

                # ── Champs additionnels structurés ───────────────────
                # Confiance globale: integer 0-10 (était select_one)
                overall_trust_raw = sub.get('grp_trust/overall_trust')
                try:
                    overall_trust_val = int(overall_trust_raw) if overall_trust_raw is not None else None
                except (ValueError, TypeError):
                    overall_trust_val = None

                # Partisanship (renommés)
                party_link         = sub.get('grp_partisanship/party_link', '')        # était: outlet_align
                pol_align          = sub.get('grp_partisanship/pol_align', '')          # était: outlet_polshape
                gov_influence      = sub.get('grp_partisanship/gov_influence', '')
                owner_influence    = sub.get('grp_partisanship/owner_influence', '')
                political_pressure = sub.get('grp_partisanship/political_pressure', '')

                enriched = {
                    # Clés conservées pour compatibilité avec dashboard existant
                    "outlet_align":    party_link,
                    "outlet_polshape": pol_align,
                    "overall_trust":   overall_trust_val,
                    # Nouvelles clés
                    "party_link":         party_link,
                    "pol_align":          pol_align,
                    "gov_influence":      gov_influence,
                    "owner_influence":    owner_influence,
                    "political_pressure": political_pressure,
                    "demo": {
                        "sex":            sub.get('grp_profile/sex', ''),
                        "age_group":      sub.get('grp_profile/age_group', ''),
                        "education":      sub.get('grp_profile/education', ''),
                        "employment":     sub.get('grp_profile/employment', ''),
                        "disability":     sub.get('grp_profile/disability', ''),
                        "residence":      sub.get('grp_profile/residence', ''),
                        "internet_access": sub.get('grp_profile/internet_access', ''),
                        "smartphone":     sub.get('grp_profile/smartphone', ''),
                    },
                    "platforms": {
                        "use_radio":    sub.get('grp_media_use/use_radio', ''),
                        "use_tv":       sub.get('grp_media_use/use_tv', ''),
                        "use_print":    sub.get('grp_media_use/use_print', ''),
                        "use_online":   sub.get('grp_media_use/use_online', ''),
                        "use_social":   sub.get('grp_media_use/use_social', ''),
                        "use_whatsapp": sub.get('grp_media_use/use_whatsapp', ''),
                        "use_youtube":  sub.get('grp_media_use/use_youtube', ''),
                        "use_podcast":  sub.get('grp_media_use/use_podcast', ''),
                        "freq_radio":   sub.get('grp_media_use/freq_radio', ''),
                        "freq_tv":      sub.get('grp_media_use/freq_tv', ''),
                        "freq_online":  sub.get('grp_media_use/freq_online', ''),
                        "freq_social":  sub.get('grp_media_use/freq_social', ''),
                        "main_source":  sub.get('grp_media_use/main_source', ''),
                    },
                    "geo": {
                        "region":    outlet_region,
                        "district":  sub.get('district', ''),
                        "community": sub.get('community', ''),
                    },
                    "reach": {
                        "outlet_days":         sub.get('grp_reach/outlet_days'),
                        "outlet_time_minutes": sub.get('grp_reach/outlet_time_minutes'),
                        "outlet_frequency":    sub.get('grp_reach/outlet_frequency', ''),
                    },
                    "trusted_journalist": sub.get('grp_outlets/trusted_journalist', ''),
                    "_raw": sub,
                }

                db.add(Response(
                    outlet_id=outlet.id,
                    respondent_id=respondent.id,
                    kobo_submission_id=kobo_id,
                    accuracy_score=float(accuracy),
                    verification_score=float(verification),
                    independence_score=float(independence),
                    fair_balanced_score=float(fair_balanced),
                    public_interest_score=float(public_interest),
                    corrections_score=float(corrections),
                    raw_response_data=json.dumps(enriched)
                ))
                synced += 1

            except Exception as e:
                print(f"[KOBO] Error processing submission: {e}")
                db.rollback()
                continue

        db.commit()
        await calculate_mti_for_all(db)

        return {
            "status": "success",
            "message": f"Synced {synced} new submissions from Kobo",
            "submissions_synced": synced,
            "last_sync": datetime.now().isoformat()
        }

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Kobo API timeout")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Cannot connect to Kobo API")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# OUTLETS DETAILS
# ============================================================

@router.get("/outlets-details")
async def get_outlets_details(db: Session = Depends(get_db)):
    outlets = db.query(Outlet).all()
    outlets_data = []

    for outlet in outlets:
        mti_index = db.query(MTIIndex).filter(MTIIndex.outlet_id == outlet.id).first()
        responses_count = db.query(func.count(Response.id)).filter(Response.outlet_id == outlet.id).scalar() or 0
        respondents_count = db.query(func.count(Respondent.id)).filter(Respondent.outlet_id == outlet.id).scalar() or 0

        # Agréger biais politique pour cet outlet
        responses = db.query(Response).filter(Response.outlet_id == outlet.id).all()
        align_counts = {}
        overall_trust_vals = []
        for r in responses:
            try:
                raw = json.loads(r.raw_response_data or '{}')
                align = raw.get("outlet_align", "")
                if align:
                    align_counts[align] = align_counts.get(align, 0) + 1
                trust = raw.get("overall_trust")
                if trust is not None:
                    overall_trust_vals.append(float(trust))
            except Exception:
                continue

        outlets_data.append({
            "id": outlet.id,
            "name": outlet.outlet_name,
            "type": outlet.outlet_type or guess_outlet_type(outlet.outlet_name),
            "region": outlet.region,
            "mti_score": mti_index.mti_score if mti_index else None,
            "responses_count": responses_count,
            "respondents_count": respondents_count,
            "political_alignment": align_counts,
            "average_overall_trust": round(sum(overall_trust_vals) / len(overall_trust_vals), 2) if overall_trust_vals else None,
            "created_at": outlet.created_at
        })

    return {
        "total": len(outlets_data),
        "outlets": sorted(outlets_data, key=lambda x: x["mti_score"] or 0, reverse=True)
    }