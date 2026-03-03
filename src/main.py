"""
main.py — Executive Job Agent
Collects → Filters → Scores → Emails top roles daily.
"""

import yaml
import os
import smtplib
import json
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collectors import collect_jobs
from scoring import score_job


# ── LOADERS ───────────────────────────────────────────────────────────────────

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


# ── FILTERS ───────────────────────────────────────────────────────────────────

def passes_filters(job, profile):
    filters = profile.get("filters", {})
    title_lower = (job.title or "").lower()
    desc_lower  = (job.description or "").lower()
    combined    = title_lower + " " + desc_lower

    # Reject by title keywords
    for kw in filters.get("reject_title_contains", []):
        if kw.lower() in title_lower:
            print(f"  ✗ Rejected [{kw} in title]: {job.company} — {job.title}")
            return False

    # Reject by role type
    for kw in filters.get("reject_role_types", []):
        if kw.lower() in title_lower:
            print(f"  ✗ Rejected [role type {kw}]: {job.company} — {job.title}")
            return False

    # Reject by body content
    for kw in filters.get("reject_if_contains", []):
        if kw.lower() in combined:
            print(f"  ✗ Rejected [body contains '{kw}']: {job.company} — {job.title}")
            return False

    return True


# ── SEEN JOBS DEDUPLICATION ───────────────────────────────────────────────────

SEEN_FILE = "seen_jobs.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


# ── EMAIL DELIVERY ────────────────────────────────────────────────────────────

def build_email_html(shortlisted, threshold, today):
    rows = ""
    for score, breakdown, job in shortlisted:
        bar_width = int(score * 100)
        bar_color = "#2563A8" if score >= 0.80 else "#D4A843" if score >= 0.72 else "#aaa"
        rows += f"""
        <tr>
          <td style="padding:12px 8px; border-bottom:1px solid #eee;">
            <strong style="color:#1B3A5C;">{job.title}</strong><br>
            <span style="color:#2563A8;">{job.company}</span>
            <span style="color:#999; font-size:12px;"> · {job.location or 'Location N/A'}</span><br>
            <div style="background:#eee;border-radius:4px;margin-top:6px;height:8px;width:200px;">
              <div style="background:{bar_color};width:{bar_width}%;height:8px;border-radius:4px;"></div>
            </div>
            <span style="font-size:12px;color:#666;">Score: {score:.2f} &nbsp;|&nbsp;
              Seniority: {breakdown['seniority_match']:.2f} &nbsp;|&nbsp;
              Payments: {breakdown['payments_domain']:.2f} &nbsp;|&nbsp;
              Transformation: {breakdown['transformation_scope']:.2f}
            </span><br>
            <a href="{job.url}" style="color:#2563A8;font-size:13px;">View Job →</a>
          </td>
        </tr>"""

    if not rows:
        rows = """<tr><td style="padding:20px;color:#999;text-align:center;">
            No roles above threshold today. The agent is running — the market just needs to catch up.
        </td></tr>"""

    return f"""
    <html><body style="font-family:Calibri,Arial,sans-serif;background:#f5f7fa;padding:20px;">
    <div style="max-width:640px;margin:auto;background:#fff;border-radius:8px;
                box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">
      <div style="background:#1B3A5C;padding:24px 28px;">
        <h2 style="color:#fff;margin:0;">Executive Opportunities</h2>
        <p style="color:#D4A843;margin:4px 0 0;">{today} · Threshold: {threshold}</p>
      </div>
      <table style="width:100%;border-collapse:collapse;">{rows}</table>
      <div style="padding:16px 28px;background:#f5f7fa;font-size:12px;color:#aaa;">
        Powered by executive-job-agent · github.com/pardiher/executive-job-agent
      </div>
    </div>
    </body></html>"""


def send_email(shortlisted, profile, threshold, today):
    sender   = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    receiver = os.environ.get("EMAIL_RECEIVER", sender)

    if not sender or not password:
        print("⚠️  EMAIL_SENDER / EMAIL_PASSWORD not set — skipping email.")
        return

    subject_prefix = profile.get("output", {}).get(
        "daily_email_subject_prefix", "Executive Opportunities"
    )
    subject = f"{subject_prefix} | {today} | {len(shortlisted)} role(s)"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = receiver

    html = build_email_html(shortlisted, threshold, today)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print(f"✅ Email sent to {receiver} with {len(shortlisted)} role(s).")
    except Exception as e:
        print(f"❌ Email failed: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    today   = date.today().isoformat()
    profile = load_yaml("config/profile.yaml")
    sources = load_yaml("config/sources.yaml")

    threshold   = profile["scoring"]["threshold_daily"]
    weights     = profile["scoring"]["weights"]
    max_results = profile.get("filters", {}).get("max_daily_roles", 5)

    print(f"\n{'='*60}")
    print(f"  Executive Job Agent — {today}")
    print(f"  Threshold: {threshold}  |  Max results: {max_results}")
    print(f"{'='*60}\n")

    # 1. Collect
    print("📡 Collecting jobs...")
    all_jobs = collect_jobs(sources)
    print(f"   → {len(all_jobs)} total jobs fetched\n")

    # 2. Deduplicate against seen jobs
    seen = load_seen()
    new_jobs = [j for j in all_jobs if j.url not in seen]
    print(f"   → {len(new_jobs)} new (unseen) jobs\n")

    # 3. Filter
    print("🔍 Applying filters...")
    filtered = [j for j in new_jobs if passes_filters(j, profile)]
    print(f"   → {len(filtered)} jobs passed filters\n")

    # 4. Score
    print("📊 Scoring jobs...")
    scored = []
    for job in filtered:
        score, breakdown = score_job(job, weights, sources_cfg=sources)
        if score >= threshold:
            scored.append((score, breakdown, job))
            print(f"   ✓ {score:.2f} — {job.company}: {job.title}")

    # 5. Sort and cap
    scored.sort(reverse=True, key=lambda x: x[0])
    shortlisted = scored[:max_results]

    # 6. Mark seen
    for _, _, job in shortlisted:
        seen.add(job.url)
    # Also mark filtered-out jobs as seen so they don't reappear
    for job in new_jobs:
        seen.add(job.url)
    save_seen(seen)

    # 7. Print summary
    print(f"\n{'='*60}")
    print(f"  TOP {len(shortlisted)} ROLE(S) TODAY")
    print(f"{'='*60}")
    for score, breakdown, job in shortlisted:
        print(f"\n  [{score:.2f}] {job.title}")
        print(f"         {job.company} · {job.location}")
        print(f"         {job.url}")
    if not shortlisted:
        print("  No roles above threshold today.")

    # 8. Send email
    print(f"\n{'='*60}")
    print("📧 Sending email digest...")
    send_email(shortlisted, profile, threshold, today)


if __name__ == "__main__":
    main()
