import yaml
import datetime
from collectors import collect_jobs
from scoring import score_job
import os

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def main():
    profile = load_yaml("config/profile.yaml")
    sources = load_yaml("config/sources.yaml")
    jobs = collect_jobs(sources)

    threshold = profile["scoring"]["threshold_daily"]
    weights = profile["scoring"]["weights"]

    shortlisted = []
    for job in jobs:
        score = score_job(job, weights)
        if score >= threshold:
            shortlisted.append((score, job))

    shortlisted.sort(reverse=True, key=lambda x: x[0])

    print("High-fit roles today:")
    for score, job in shortlisted[:3]:
        print(score, job.company, job.title, job.url)

if __name__ == "__main__":
    main()
