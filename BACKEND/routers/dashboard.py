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
    # Depuis la migration du formulaire Kobo, l'API renvoie le code brut du
    # choix (XLSForm "name") plutôt que son label pour les questions Likert
    # grp_trust/mti_* : "5" = Strongly agree ... "1" = Strongly disagree.
    # Sans ça, kobo_to_score() retombait sur le défaut (50) pour quasiment
    # toutes les réponses synchronisées après la migration.
    "5": 100,
    "4": 75,
    "3": 50,
    "2": 25,
    "1": 0,
}

# Codes/valeurs qui signifient "l'outlet sélectionné est 'Other'" plutôt
# qu'un vrai nom d'outlet. Le formulaire renvoie parfois un code brut (ex:
# "999") pour ce choix plutôt que le mot "other" — d'où le faux outlet "999"
# qui apparaissait dans le dashboard.
OTHER_OUTLET_CODES = {"other", "nan", "", "999", "-999", "none"}

OUTLET_TYPE_MAP = {
    # NB: l'API Kobo renvoie le code XLSForm brut pour rated_outlet, qui est
    # un slug SANS espace (ex: "fourthestate", "graphiconline"), pas le nom
    # humain avec espace. On garde les deux formes : la version concaténée
    # pour matcher l'API, la version espacée pour les saisies manuelles via
    # l'API CRUD /api/outlets (outlets.py) ou d'anciens exports.
    "citifm": "Radio", "citi fm": "Radio",
    "joyfm": "Radio", "joy fm": "Radio",
    "peacefm": "Radio", "peace fm": "Radio",
    "adomfm": "Radio", "adom fm": "Radio",
    "asaase": "Radio", "omanfm": "Radio", "oman fm": "Radio",
    "metro tv": "TV", "metrotv": "TV", "metro": "TV",
    "adom tv": "TV", "adomtv": "TV", "ghone": "TV", "gh one": "TV",
    "tv3": "TV", "gbc": "TV", "utv": "TV",
    "citinewsroom": "Online", "myjoyonline": "Online",
    "joy news": "TV", "joynews": "TV",
    "the fourth estate": "Online", "fourth estate": "Online", "fourthestate": "Online",
    "ghanaweb": "Online",
    "graphic online": "Online", "graphiconline": "Online",
    "daily graphic": "Print", "dailygraphic": "Print", "graphic": "Print",
}

def guess_outlet_type(name):
    n = name.lower().strip()
    # Longest keys first so e.g. "graphic online" wins over the bare "graphic"
    for k in sorted(OUTLET_TYPE_MAP, key=len, reverse=True):
        if k in n:
            return OUTLET_TYPE_MAP[k]
    if any(x in n for x in ["fm", "radio"]):
        return "Radio"
    if any(x in n for x in ["tv", "television"]):
        return "TV"
    if any(x in n for x in ["online", "news", ".com", ".gh", "web"]):
        return "Online"
    # Unmatched name: don't silently guess "Radio", flag it for review instead
    return "Unknown"

def kobo_to_score(value):
    if not value:
        return 50
    return RESPONSE_MAPPING.get(str(value).lower(), 50)

def resolve_outlet_name(sub):
    """
    Détermine le nom d'outlet à partir d'une soumission Kobo brute, en gérant
    le cas où l'utilisateur a choisi "Other" (code parfois "999" plutôt que
    "other" selon le formulaire) : on retombe alors sur le champ texte libre
    grp_outlets/rated_outlet_other, ou sur un label explicite s'il est vide,
    plutôt que de laisser fuiter le code brut comme nom d'outlet.
    """
    outlet_name_raw = sub.get('grp_outlets/rated_outlet', '')
    outlet_other_raw = sub.get('grp_outlets/rated_outlet_other', '')

    if str(outlet_name_raw).strip().lower() in OTHER_OUTLET_CODES:
        if str(outlet_other_raw).strip().lower() not in ('', 'nan'):
            outlet_name_raw = outlet_other_raw
        else:
            outlet_name_raw = 'Unspecified Other Outlet'

    return outlet_name_raw.title().strip() if outlet_name_raw else 'Unknown'


# ============================================================
# DASHBOARD GLOBAL
# ============================================================

@router.get("/")
async def get_dashboard(db: Session = Depends(get_db)):
    total_outlets = db.query(func.count(Outlet.id)).scalar() or 0
    total_respondents = db.query(func.count(Respondent.id)).scalar() or 0
    total_responses = db.query(func.count(Response.id)).scalar() or 0

    # average_mti doit être pondéré par réponse individuelle, pas par outlet :
    # une simple moyenne des MTIIndex.mti_score par outlet donne le même poids
    # à un outlet avec 1 réponse qu'à un outlet avec 4 réponses, ce qui biaise
    # fortement le score global dès que les échantillons par outlet sont petits.
    all_responses = db.query(Response).all()
    if all_responses:
        n = len(all_responses)
        average_mti = sum(
            r.accuracy_score * 0.20 +
            r.verification_score * 0.20 +
            r.independence_score * 0.20 +
            r.fair_balanced_score * 0.15 +
            r.public_interest_score * 0.15 +
            r.corrections_score * 0.10
            for r in all_responses
        ) / n
    else:
        average_mti = 0

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
# MAINTENANCE: backfill outlet_type sur les outlets déjà en base
# ============================================================

@router.post("/recalc-outlet-types")
async def recalc_outlet_types(db: Session = Depends(get_db)):
    """
    sync-kobo ne réévalue outlet_type que pour les NOUVELLES soumissions
    (les réponses déjà synchronisées sont "continue"-ées avant d'atteindre
    ce code). Cet endpoint corrige les outlets déjà en base sans attendre
    une nouvelle soumission Kobo.
    """
    outlets = db.query(Outlet).all()
    changes = []
    for outlet in outlets:
        new_type = guess_outlet_type(outlet.outlet_name)
        if outlet.outlet_type != new_type:
            changes.append({"outlet": outlet.outlet_name, "old": outlet.outlet_type, "new": new_type})
            outlet.outlet_type = new_type
    db.commit()
    return {"status": "success", "updated": len(changes), "changes": changes}


@router.post("/recalc-response-scores")
async def recalc_response_scores(db: Session = Depends(get_db)):
    """
    Recalcule les 6 scores de dimension de chaque réponse déjà en base à
    partir de raw_response_data._raw (la soumission Kobo brute, conservée
    telle quelle au sync), et réassigne l'outlet si le nom résolu change
    (fix du bug outlet "999"). Nécessaire car sync-kobo ignore les
    submissions dont le kobo_submission_id existe déjà : corriger
    kobo_to_score()/resolve_outlet_name() ne suffit pas à corriger les
    lignes déjà importées, il faut les retraiter explicitement.
    """
    responses = db.query(Response).all()
    updated_scores = 0
    reassigned_outlets = 0

    for resp in responses:
        try:
            raw = json.loads(resp.raw_response_data or '{}')
            sub = raw.get('_raw', {})
        except Exception:
            continue
        if not sub:
            continue

        new_scores = {
            "accuracy_score":        float(kobo_to_score(sub.get('grp_trust/mti_accurate'))),
            "verification_score":    float(kobo_to_score(sub.get('grp_trust/mti_verify'))),
            "independence_score":    float(kobo_to_score(sub.get('grp_trust/mti_independent'))),
            "fair_balanced_score":   float(kobo_to_score(sub.get('grp_trust/mti_fair'))),
            "public_interest_score": float(kobo_to_score(sub.get('grp_trust/mti_public'))),
            "corrections_score":     float(kobo_to_score(sub.get('grp_trust/mti_corrects'))),
        }
        if any(getattr(resp, k) != v for k, v in new_scores.items()):
            for k, v in new_scores.items():
                setattr(resp, k, v)
            updated_scores += 1

        correct_name = resolve_outlet_name(sub)
        current_outlet = db.query(Outlet).filter(Outlet.id == resp.outlet_id).first()
        if current_outlet and current_outlet.outlet_name != correct_name:
            new_outlet = db.query(Outlet).filter(Outlet.outlet_name == correct_name).first()
            if not new_outlet:
                new_outlet = Outlet(
                    outlet_name=correct_name,
                    outlet_type=guess_outlet_type(correct_name),
                    region=current_outlet.region,
                )
                db.add(new_outlet)
                db.flush()
            resp.outlet_id = new_outlet.id
            reassigned_outlets += 1

    db.commit()

    # Nettoie les outlets devenus orphelins (0 réponses) suite aux réassignations
    orphans_removed = []
    for outlet in db.query(Outlet).all():
        count = db.query(func.count(Response.id)).filter(Response.outlet_id == outlet.id).scalar() or 0
        if count == 0:
            orphans_removed.append(outlet.outlet_name)
            db.query(MTIIndex).filter(MTIIndex.outlet_id == outlet.id).delete()
            db.query(Respondent).filter(Respondent.outlet_id == outlet.id).delete()
            db.delete(outlet)
    db.commit()

    await calculate_mti_for_all(db)

    return {
        "status": "success",
        "responses_scores_updated": updated_scores,
        "responses_outlet_reassigned": reassigned_outlets,
        "orphan_outlets_removed": orphans_removed,
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
                outlet_name = resolve_outlet_name(sub)
                outlet_type = guess_outlet_type(outlet_name)
                # Région maintenant à la racine (était: geo/region)
                outlet_region = sub.get('region', 'Unknown')

                outlet = db.query(Outlet).filter(Outlet.outlet_name == outlet_name).first()
                if not outlet:
                    outlet = Outlet(outlet_name=outlet_name, outlet_type=outlet_type, region=outlet_region)
                    db.add(outlet)
                    db.flush()
                else:
                    # Toujours réaligner sur le résultat du guesser (déterministe,
                    # basé uniquement sur le nom) plutôt que de figer le premier
                    # type deviné, qui pouvait rester faux à vie (ex: "Radio" par
                    # défaut) puisqu'on ne le recorrigeait que Radio -> autre chose.
                    if outlet.outlet_type != outlet_type:
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