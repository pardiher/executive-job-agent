import re
import requests
from dataclasses import dataclass
from typing import List

@dataclass
class Job:
    source: str
    company: str
    title: str
    location: str
    url: str
    description: str

def clean_html(text):
    return re.sub("<[^>]+>", " ", text or "")

def fetch_lever(url, company):
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            print(f"Skipping Lever source {company}: {r.status_code}")
            return []
        data = r.json()
        jobs = []
        for j in data:
            jobs.append(Job(
                "lever",
                company,
                j.get("text", ""),
                j.get("categories", {}).get("location", ""),
                j.get("hostedUrl", ""),
                clean_html(j.get("description", ""))
            ))
        return jobs
    except Exception as e:
        print(f"Lever error for {company}: {e}")
        return []

def fetch_greenhouse(url, company):
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            print(f"Skipping Greenhouse source {company}: {r.status_code}")
            return []
        data = r.json()
        jobs = []
        for j in data.get("jobs", []):
            jobs.append(Job(
                "greenhouse",
                company,
                j.get("title", ""),
                j.get("location", {}).get("name", ""),
                j.get("absolute_url", ""),
                clean_html(j.get("content", ""))
            ))
        return jobs
    except Exception as e:
        print(f"Greenhouse error for {company}: {e}")
        return []

def collect_jobs(cfg):
    jobs = []
    for s in cfg.get("sources", []):
        if s["type"] == "lever":
            jobs += fetch_lever(s["url"], s["company"])
        elif s["type"] == "greenhouse":
            jobs += fetch_greenhouse(s["url"], s["company"])
    return jobs
