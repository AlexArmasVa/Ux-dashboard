import shutil
import streamlit as st
import pandas as pd
import glob
import json
import os
import subprocess
from weasyprint import HTML
import matplotlib.pyplot as plt
from datetime import datetime
from urllib.parse import urlparse
import uuid
import requests
import asyncio
from component_checker import check_components

ARTIFACTS_DIR = "artifacts"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
os.environ["CHROME_PATH"] = "/usr/bin/chromium"

st.set_page_config(page_title="Enterprise UX Dashboard", layout="wide")
st.title("📊 Enterprise UX Audit Dashboard")

def format_badge(value): return "✅ Pass" if value == "✅" else "❌ Fail" if value == "❌" else str(value)

def format_colored_score(value):
    try:
        val = float(value)
        return f"🟢 {val}" if val >= 90 else f"🟡 {val}" if val >= 50 else f"🔴 {val}"
    except: return value

def color_score(val):
    if pd.isnull(val): return ""
    val = float(val)
    return "🟢" if val >= 90 else "🟡" if val >= 50 else "🔴"

def format_percent_change(old, new):
    if pd.isnull(old) or old == 0: return ""
    return f"{((new - old) / old) * 100:+.1f}%"

def move_and_copy_report(json_path, html_path, version_dir, timestamp, serial):
    try:
        # Define final filenames inside versioned directory
        report_json_dest = os.path.join(version_dir, "report.json")
        report_html_dest = os.path.join(version_dir, "report.html")

        # Move Lighthouse output files
        shutil.move(json_path, report_json_dest)
        shutil.move(html_report, report_html_dest)

        # Copy standard versions to artifacts root
        shutil.copy(report_json_dest, os.path.join(ARTIFACTS_DIR, "report.json"))
        shutil.copy(report_html_dest, os.path.join(ARTIFACTS_DIR, f"lighthouse_{timestamp}_{serial}.html"))

        return True
    except Exception as e:
        st.error(f"❌ File move/copy failed: {e}")
        return False

# === Lighthouse Audit ===
with st.sidebar.expander("🌐 Run Lighthouse Audit from URL"):
    url = st.text_input("Paste site URL (e.g. https://example.com)")
    if st.button("🚀 Run Lighthouse"):
        parsed = urlparse(url)
        if parsed.hostname and any(parsed.hostname.startswith(p) for p in ["localhost", "127.", "192.168"]):
            st.warning("⚠️ Local audits may have limited results")

        site_name = parsed.netloc.replace(".", "_").replace("www_", "")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        serial = uuid.uuid4().hex[:6]
        base_name = f"{site_name}_{timestamp}_{serial}"
        version_dir = os.path.join(ARTIFACTS_DIR, base_name)
        os.makedirs(version_dir, exist_ok=True)

        output_prefix = os.path.join(version_dir, base_name)
        json_report = f"{output_prefix}.report.json"
        html_report = f"{output_prefix}.report.html"

        try:
            resp = requests.head(url, allow_redirects=True, timeout=5)
            if resp.status_code >= 400:
                st.error(f"❌ URL responded with status {resp.status_code}")
                st.stop()
        except Exception as e:
            st.error(f"❌ Failed to connect: {e}")
            st.stop()

        st.info("🔍 Running component functionality check...")
        try:
            components = asyncio.run(check_components(url))
            failed = [c for c in components if c['status'] != '✅']
            if failed:
                st.warning("⚠️ Some key components may be missing or not functional:")
                for comp in failed:
                    st.markdown(f"- `{comp['selector']}` → {comp['status']}")
                if st.button("🚫 Stop Audit Due to Component Issues"): st.stop()
        except Exception as e:
            st.error(f"❌ Component check failed: {e}")
            if not st.button("❌ Skip Component Check and Proceed"): st.stop()

        with open(os.path.join(version_dir, "report_meta.json"), "w") as f:
            json.dump({"site": site_name, "timestamp": timestamp, "serial": serial}, f)

        try:
            subprocess.run([
                "lighthouse", url,
                "--output=json", "--output=html",
                f"--output-path={output_prefix}",
                "--quiet",
                "--throttling-method=devtools",
                "--chrome-flags=--headless --no-sandbox --disable-gpu --disable-dev-shm-usage"
            ], check=True)
        except subprocess.CalledProcessError as e:
            st.error("❌ Lighthouse failed")
            st.code(str(e))
            st.stop()

        if not move_and_copy_report(json_report, html_report, version_dir, timestamp, serial): st.stop()

        try:
            subprocess.run(["python", "analyze_ux.py", version_dir], check=True)
        except subprocess.CalledProcessError as e:
            st.error("❌ analyze_ux.py failed")
            st.code(str(e))
            
        # Run heuristic review script
        try:
            subprocess.run(["python", "heuristic_review.py", url, version_dir], check=True)
        except subprocess.CalledProcessError as e:
            st.warning("⚠️ Heuristic review failed.")
            st.code(str(e))

        try:
            components = asyncio.run(check_components(url))
            with open(os.path.join(version_dir, "components.json"), "w") as f:
                json.dump(components, f)
        except Exception as e:
            st.warning(f"⚠️ Component check skipped: {e}")

        st.success("✅ Audit complete")
        html_report_path = os.path.join(version_dir, "report.html")
        st.download_button("📄 Download Lighthouse HTML", open(html_report_path, "rb"), file_name=os.path.basename(html_report_path), mime="text/html")
        st.info(f"👆 Downloaded to: `{html_report_path}`. Open manually in browser.")

# === Upload Existing Report ===
with st.sidebar.expander("📥 Upload Lighthouse report"):
    uploaded = st.file_uploader("Upload report.json", type="json")
    if uploaded:
        try:
            data = json.load(uploaded)
            if not all(k in data for k in ("audits", "categories", "finalUrl")):
                st.error("❌ Invalid Lighthouse report structure.")
                st.stop()
            with open(os.path.join(ARTIFACTS_DIR, "report.json"), "w") as f:
                json.dump(data, f, indent=2)
            subprocess.run(["python", "analyze_ux.py"], check=True)
            st.success("✅ Uploaded and analyzed.")
        except Exception as e:
            st.error(f"❌ Upload failed: {e}")

# === Load Reports ===
csv_reports = sorted(glob.glob(os.path.join(ARTIFACTS_DIR, "**", "ux_report_*.csv"), recursive=True))
if not csv_reports:
    st.warning("❌ No UX reports found.")
    st.stop()

folders = sorted({os.path.relpath(os.path.dirname(f), ARTIFACTS_DIR) for f in csv_reports})
selected_folder = st.selectbox("📁 Select Report Folder", folders)

folder_reports = [f for f in csv_reports if os.path.relpath(os.path.dirname(f), ARTIFACTS_DIR) == selected_folder]
selected = st.selectbox("📄 Select Report", folder_reports)
selected_json = selected.replace(".csv", ".json")

df = pd.read_csv(selected)
if not os.path.exists(selected_json):
    st.error(f"❌ Missing JSON file for: {selected_json}")
    st.stop()
with open(selected_json) as f:
    detail = json.load(f)

st.success(f"✅ Loaded: {os.path.basename(selected)}")

# === Visualizations ===
score_df = df[df["Metric"].str.startswith("Score:")].copy()
score_df["Metric"] = score_df["Metric"].str.replace("Score: ", "")
score_df["Value"] = pd.to_numeric(score_df["Value"], errors="coerce")
score_df.set_index("Metric", inplace=True)

st.subheader("🚦 Core Scores")
st.bar_chart(score_df)

# === Downloads ===
with st.sidebar:
    st.markdown("### 📤 Download")
    st.download_button("⬇️ CSV", open(selected, "rb"), file_name=os.path.basename(selected), mime="text/csv")
    st.download_button("⬇️ JSON", open(selected_json, "rb"), file_name=os.path.basename(selected_json), mime="application/json")

with st.sidebar.expander("🧾 Export Report"):
    chart_path = selected.replace(".csv", ".png")
    if not score_df.empty:
        score_df.plot(kind="bar", legend=False)
        plt.title("Core Scores")
        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close()
        st.download_button("📊 Chart Image", open(chart_path, "rb"), file_name=os.path.basename(chart_path), mime="image/png")
        if st.button("📄 Export PDF"):
            html = f"<h1>Enterprise UX Report</h1><p>{os.path.basename(selected)}</p><img src='{chart_path}' style='width:100%;max-width:600px;' />{df.to_html(index=False)}"
            pdf_path = selected.replace(".csv", ".pdf")
            HTML(string=html).write_pdf(pdf_path)
            st.download_button("⬇️ PDF", open(pdf_path, "rb"), file_name=os.path.basename(pdf_path), mime="application/pdf")

# === Metric Table ===
st.subheader("📋 Full Metrics")
st.dataframe(df, use_container_width=True)

# === Score Trends ===
with st.expander("📈 Score Trends"):
    trend_data = []
    for file in csv_reports:
        data = pd.read_csv(file)
        row = {"Date": os.path.basename(file).replace("ux_report_", "").replace(".csv", "")}
        for _, r in data.iterrows():
            if r["Metric"].startswith("Score:"):
                row[r["Metric"].replace("Score: ", "")] = r["Value"]
        trend_data.append(row)
    trend_df = pd.DataFrame(trend_data).set_index("Date").sort_index()
    st.line_chart(trend_df)

# === Deep Metrics ===
st.subheader("🧠 Deep Metrics")
for section, content in detail.items():
    with st.expander(section):
        if isinstance(content, dict):
            sec_df = pd.DataFrame(content.items(), columns=["Metric", "Value"])
            if section in ["Core Scores", "Load Timings", "Page Complexity"]:
                sec_df["Value"] = sec_df["Value"].apply(format_colored_score)
            elif section in ["Best Practices", "SEO Insights"]:
                sec_df["Value"] = sec_df["Value"].apply(format_badge)
            else:
                sec_df["Value"] = sec_df["Value"].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else str(x))
            st.dataframe(sec_df)
        elif isinstance(content, list):
            for i, item in enumerate(content, 1):
                st.markdown(f"- **Issue {i}:** {item}")
        else:
            st.write(str(content))

# === Heuristic Expert Review ===
heuristic_path = os.path.join(os.path.dirname(selected), "heuristic_review.json")
if os.path.exists(heuristic_path):
    with open(heuristic_path) as f:
        heuristics = json.load(f)
    with st.expander("Heuristic Expert Review"):
        for k, v in heuristics.items():
            st.markdown(f"**{k}**: {v}")
else:
    st.info("ℹ️ No heuristic review found for this report.")

# === Accessibility & SEO Summary ===
st.subheader("🔎 Accessibility & SEO Summary")

show_only_fails = st.checkbox("Show only failed checks")

a11y_issues = []
seo_issues = []

for section, content in detail.items():
    if isinstance(content, dict):
        if section.lower().startswith("accessibility"):
            a11y_issues += [(k, v) for k, v in content.items() if not show_only_fails or v == "❌"]
        elif section.lower().startswith("seo"):
            seo_issues += [(k, v) for k, v in content.items() if not show_only_fails or v == "❌"]

if a11y_issues or seo_issues:
    if a11y_issues:
        st.markdown(f"### ♿ Accessibility Checks ({len(a11y_issues)})")
        for key, val in a11y_issues:
            emoji = "❌" if val == "❌" else "✅"
            st.markdown(f"- {emoji} `{key}`")
    if seo_issues:
        st.markdown(f"### 🔍 SEO Checks ({len(seo_issues)})")
        for key, val in seo_issues:
            emoji = "❌" if val == "❌" else "✅"
            st.markdown(f"- {emoji} `{key}`")
else:
    st.success("✅ No Accessibility or SEO issues found based on filter.")
    
# === Component Check Output ===
comp_file = os.path.join(os.path.dirname(selected), "components.json")
if os.path.exists(comp_file):
    with open(comp_file) as f:
        comp_data = json.load(f)
    with st.expander("🧩 Web Component Validation Results"):
        st.write("Semantic checks for header, nav, main, footer, buttons, etc.")
        st.dataframe(pd.DataFrame(comp_data))
else:
    st.info("ℹ️ No component validation available.")

# === Report Comparison ===
if len(csv_reports) >= 2:
    st.subheader("🆚 Compare Reports")
    c1, c2 = st.columns(2)
    file1 = c1.selectbox("📄 First Report", csv_reports, index=len(csv_reports)-2, key="cmp1")
    file2 = c2.selectbox("📄 Second Report", csv_reports, index=len(csv_reports)-1, key="cmp2")

    df1, df2 = pd.read_csv(file1), pd.read_csv(file2)
    merged = pd.merge(df1, df2, on="Metric", suffixes=("_Old", "_New"))
    merged["Value_Old"] = pd.to_numeric(merged["Value_Old"], errors="coerce")
    merged["Value_New"] = pd.to_numeric(merged["Value_New"], errors="coerce")
    merged["Δ"] = merged["Value_New"] - merged["Value_Old"]
    merged["Δ (Visual)"] = merged["Δ"].apply(lambda x: f"🔺 {x}" if x > 0 else f"🔻 {abs(x)}" if x < 0 else "➖ 0")

    st.dataframe(merged[["Metric", "Value_Old", "Value_New", "Δ", "Δ (Visual)"]])

    compare = merged[merged["Metric"].str.startswith("Score:")].copy()
    compare["Metric"] = compare["Metric"].str.replace("Score: ", "")
    compare.set_index("Metric", inplace=True)
    compare["Trend"] = compare.apply(lambda row: format_percent_change(row["Value_Old"], row["Value_New"]), axis=1)

    fig, ax = plt.subplots(figsize=(10, 5))
    compare[["Value_Old", "Value_New"]].plot(kind="bar", ax=ax)
    ax.set_title("Core Score Comparison")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 110)
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend(["First Report", "Second Report"], loc="lower right")

    for i, (old_val, new_val) in enumerate(zip(compare["Value_Old"], compare["Value_New"])):
        ax.text(i - 0.2, old_val + 1, f"{old_val:.0f}", color="blue", ha="center")
        ax.text(i + 0.2, new_val + 1, f"{new_val:.0f}\n({compare.iloc[i]['Trend']})", color="green", ha="center")
    ax.set_xticks(range(len(compare.index)))
    ax.set_xticklabels(compare.index, rotation=0)
    st.pyplot(fig)

    st.markdown("### 🧾 Summary Insights")
    improved = merged[merged["Δ"] > 0]["Metric"].tolist()
    declined = merged[merged["Δ"] < 0]["Metric"].tolist()
    neutral = merged[merged["Δ"] == 0]["Metric"].tolist()
    if improved: st.markdown(f"**📈 Improved ({len(improved)}):** {', '.join(improved)}")
    if declined: st.markdown(f"**📉 Declined ({len(declined)}):** {', '.join(declined)}")
    if neutral: st.markdown(f"**➖ No Change ({len(neutral)}):** {', '.join(neutral)}")

    if not merged.empty:
        max_gain = merged.sort_values("Δ", ascending=False).iloc[0]
        max_drop = merged.sort_values("Δ", ascending=True).iloc[0]
        st.markdown("---")
        st.markdown(f"**🏅 Biggest Gain:** {max_gain['Metric']} (+{max_gain['Δ']:.1f})")
        st.markdown(f"**📉 Biggest Drop:** {max_drop['Metric']} ({max_drop['Δ']:.1f})")

