import sys
import os
import json
import asyncio
from component_checker import check_components

def main(report_dir):
    if not os.path.isdir(report_dir):
        print(f"❌ Folder not found: {report_dir}")
        return

    # Attempt to extract URL from existing metadata
    meta_path = os.path.join(report_dir, "report_meta.json")
    if not os.path.exists(meta_path):
        print("❌ report_meta.json not found in the folder.")
        return

    with open(meta_path) as f:
        meta = json.load(f)

    site = meta.get("site")
    if not site:
        print("❌ site not found in metadata.")
        return

    url = f"https://{site.replace('_', '.')}"

    print(f"🔍 Running component check for: {url}")
    try:
        components = asyncio.run(check_components(url))
        with open(os.path.join(report_dir, "components.json"), "w") as f:
            json.dump(components, f, indent=2)
        print("✅ Component check complete and saved.")
    except Exception as e:
        print(f"❌ Component check failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_component_check.py <path/to/report_folder>")
    else:
        main(sys.argv[1])