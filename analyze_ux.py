import json
import pandas as pd
from datetime import datetime
import os
import sys
import time

# === Setup ===
version_dir = sys.argv[1] if len(sys.argv) > 1 else "artifacts"
REPORT_JSON = os.path.join(version_dir, "report.json")
META_FILE = os.path.join(version_dir, "report_meta.json")

# Wait for report.json (max 5 seconds)
for _ in range(10):
    if os.path.exists(REPORT_JSON):
        break
    time.sleep(0.5)

if not os.path.exists(REPORT_JSON):
    raise FileNotFoundError(f"Missing Lighthouse report: {REPORT_JSON}")

if not os.path.exists(META_FILE):
    raise FileNotFoundError(f"Missing metadata file: {META_FILE}")

# === Load Metadata ===
with open(META_FILE) as f:
    meta = json.load(f)

site = meta.get("site", "unknown")
timestamp = meta.get("timestamp", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
serial = meta.get("serial", "000000")

base_filename = f"ux_report_{site}_{timestamp}_{serial}"
report_dir = version_dir  # Output to same directory as report.json

csv_path = os.path.join(report_dir, f"{base_filename}.csv")
json_path = os.path.join(report_dir, f"{base_filename}.json")

# === Load Lighthouse JSON ===
with open(REPORT_JSON, "r") as file:
    data = json.load(file)

rows = []

# === Core Scores ===
categories = data.get("categories", {})
for cat in ["performance", "accessibility", "seo", "best-practices"]:
    score = categories.get(cat, {}).get("score")
    if score is not None:
        rows.append((f"Score: {cat.title()}", round(score * 100)))

# === Timing Metrics ===
audits = data.get("audits", {})
metrics = {
    "first-contentful-paint": "First Contentful Paint",
    "largest-contentful-paint": "Largest Contentful Paint",
    "total-blocking-time": "Total Blocking Time",
    "cumulative-layout-shift": "Cumulative Layout Shift",
    "speed-index": "Speed Index",
    "interactive": "Time to Interactive",
}
for key, label in metrics.items():
    value = audits.get(key, {}).get("numericValue")
    if value is not None:
        rows.append((label, round(value)))

# === Violations ===
violations = [val.get("title") for val in audits.values() if val.get("score") == 0 and val.get("title")]

# === Save Reports ===
df = pd.DataFrame(rows, columns=["Metric", "Value"])
df.to_csv(csv_path, index=False)

with open(json_path, "w") as f:
    json.dump({
        "Core Scores": dict(rows),
        "Violations": violations
    }, f, indent=2)

print(f"✅ Saved:\n- CSV: {csv_path}\n- JSON: {json_path}")