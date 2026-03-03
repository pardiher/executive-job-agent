"""
scoring.py — Full 5-dimension scorer for executive payments roles.
All weights from profile.yaml are now implemented.
Max possible score = 1.0
"""

import re

def norm(text):
    return (text or "").lower()

# ── 1. SENIORITY MATCH (weight: 0.30) ─────────────────────────────────────────
def title_score(title):
    t = norm(title)
    if any(k in t for k in [
        "managing director", "md ", "partner", "principal",
        "head of", "head,", "vp ", "vice president",
        "chief", "coo", "cto", "cpo", "cfo"
    ]):
        return 1.0
    if any(k in t for k in ["director", "senior director", "executive director"]):
        return 0.85
    if "manager" in t or "lead" in t:
        return 0.4
    return 0.1

# ── 2. PAYMENTS DOMAIN (weight: 0.25) ─────────────────────────────────────────
def payments_score(text):
    t = norm(text)
    keywords = [
        "payments", "payment", "cross-border", "iso 20022", "iso20022",
        "real-time", "real time", "rtp", "fednow", "fed now",
        "swift", "ach", "wires", "wire transfer", "remittance",
        "fintech", "payment gateway", "acquiring", "issuing",
        "card network", "mastercard", "visa", "stablecoin",
        "digital assets", "correspondent banking", "fx", "foreign exchange",
        "orchestration", "payment rail", "open banking"
    ]
    hits = sum(1 for k in keywords if k in t)
    return min(1.0, hits / 6)

# ── 3. P&L / REVENUE SCOPE (weight: 0.15) ─────────────────────────────────────
def pnl_score(text):
    t = norm(text)
    score = 0.0
    # Revenue / P&L ownership language
    if any(k in t for k in ["p&l", "profit and loss", "revenue ownership", "revenue target"]):
        score += 0.5
    # Scale indicators
    if any(k in t for k in ["billion", "$1b", "$500m", "global portfolio", "enterprise"]):
        score += 0.3
    # Growth / commercial language
    if any(k in t for k in ["revenue growth", "commercial", "go-to-market", "gtm", "business development"]):
        score += 0.2
    return min(1.0, score)

# ── 4. TRANSFORMATION SCOPE (weight: 0.15) ────────────────────────────────────
def transformation_score(text):
    t = norm(text)
    keywords = [
        "transformation", "modernization", "modernisation",
        "migration", "program management", "programme",
        "roadmap", "target operating model", "tom",
        "multi-year", "multi year", "workstream",
        "strategic initiative", "change management",
        "digital transformation", "system implementation"
    ]
    hits = sum(1 for k in keywords if k in t)
    return min(1.0, hits / 4)

# ── 5. CONSULTING PRACTICE FIT (weight: 0.10) ─────────────────────────────────
def consulting_score(text):
    t = norm(text)
    score = 0.0
    if any(k in t for k in [
        "consulting", "advisory", "consultant", "advisor",
        "client delivery", "client engagement", "thought leadership"
    ]):
        score += 0.5
    if any(k in t for k in [
        "practice lead", "practice development", "business development",
        "proposal", "rfi", "rfp", "sme", "subject matter"
    ]):
        score += 0.3
    if any(k in t for k in ["financial services", "banking", "financial institution", "tier 1"]):
        score += 0.2
    return min(1.0, score)

# ── 6. INSTITUTIONAL BRAND FIT (weight: 0.05) ─────────────────────────────────
def brand_score(company, sources_cfg):
    c = norm(company)
    big4     = [norm(x) for x in sources_cfg.get("big4", [])]
    tier2    = [norm(x) for x in sources_cfg.get("tier2", [])]
    retained = [norm(x) for x in sources_cfg.get("retained_search", [])]
    pe_fin   = [norm(x) for x in sources_cfg.get("pe_backed_fintech_allow", [])]

    if any(b in c for b in big4):     return 1.0
    if any(b in c for b in tier2):    return 0.8
    if any(b in c for b in retained): return 0.7
    if any(b in c for b in pe_fin):   return 0.6
    return 0.3   # unknown company

# ── MASTER SCORER ─────────────────────────────────────────────────────────────
def score_job(job, weights, sources_cfg=None):
    """
    Returns a float 0.0–1.0.
    weights must contain all 5 keys from profile.yaml.
    """
    text = (job.title or "") + " " + (job.description or "")
    sources_cfg = sources_cfg or {}

    breakdown = {
        "seniority_match":        title_score(job.title),
        "payments_domain":        payments_score(text),
        "pnl_revenue":            pnl_score(text),
        "transformation_scope":   transformation_score(text),
        "consulting_practice_fit":consulting_score(text),
        "institutional_brand_fit":brand_score(job.company, sources_cfg),
    }

    total = sum(weights.get(k, 0) * v for k, v in breakdown.items())
    return round(total, 4), breakdown
