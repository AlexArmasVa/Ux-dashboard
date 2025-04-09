import os
import sys
import json

# Step 1: Parse CLI args
if len(sys.argv) != 3:
    print("Usage: python heuristic_review.py <url> <output_path>")
    sys.exit(1)

url = sys.argv[1]
output_path = sys.argv[2]

# Step 2: Ensure output folder exists
os.makedirs(output_path, exist_ok=True)

# Step 3: Placeholder heuristic review result
results = {
    "URL": url,
    "Heuristic": "Aesthetic and minimalist design",
    "Result": "⚠️ Crowded UI",
    "Details": "Page has over 12 CTAs above the fold"
}

# Step 4: Save JSON
out_file = os.path.join(output_path, "heuristic_review.json")
with open(out_file, "w") as f:
    json.dump(results, f, indent=2)

print(f"✅ Saved: {out_file}")