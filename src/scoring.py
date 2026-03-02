import re

def norm(text):
    return (text or "").lower()

def title_score(title):
    t = norm(title)
    if any(k in t for k in ["director", "principal", "partner", "head", "vp"]):
        return 1.0
    if "manager" in t:
        return 0.5
    return 0.3

def payments_score(text):
    t = norm(text)
    keywords = ["payments", "cross-border", "iso 20022", "real-time", "rtp", "wires", "ach"]
    return min(1.0, sum(k in t for k in keywords) / 5)

def score_job(job, weights):
    text = job.title + " " + job.description
    return (
        weights["seniority_match"] * title_score(job.title) +
        weights["payments_domain"] * payments_score(text)
    )
