"""
Safe Model Switch - Streamlit Evaluation Dashboard.
Implements all requirements from Section 9:
- KPI Top Cards: Requests compared, avg estimated cost (A vs B), avg latency (A vs B), avg quality, cost saving %
- Decision Banner: Green / Amber / Red with clear threshold labels
- Side-by-side Comparison Table: Prompt, Answer A, Answer B, Score, Reason (Highlight scores <= 3, show Uncertain)
- Controls: Number input for N, 'Run replay', 'Run scoring', and 'Refresh' buttons
"""
import sys
import os
import streamlit as st
import pandas as pd
import httpx

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models import RequestLog, Replay, Score
from app.config import settings
from app.report import calculate_report_data

st.set_page_config(
    page_title="Safe Model Switch Dashboard",
    page_icon="⚖️",
    layout="wide"
)

# Gateway base URL
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://127.0.0.1:8000")

# --- Custom Styling ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #e9ecef;
        text-align: center;
    }
    .verdict-banner-safe {
        background-color: #d4edda;
        color: #155724;
        padding: 18px;
        border-radius: 8px;
        border-left: 6px solid #28a745;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .verdict-banner-review {
        background-color: #fff3cd;
        color: #856404;
        padding: 18px;
        border-radius: 8px;
        border-left: 6px solid #ffc107;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .verdict-banner-unsafe {
        background-color: #f8d7da;
        color: #721c24;
        padding: 18px;
        border-radius: 8px;
        border-left: 6px solid #dc3545;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ Safe Model Switch — LLM Migration Evaluation")
st.caption(f"Comparing Current Model (**{settings.MODEL_A}**) vs Candidate Cheaper Model (**{settings.MODEL_B}**)")

# --- Top Action Controls ---
st.subheader("Controls")
col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns([2, 2, 2, 2])

with col_ctrl1:
    replay_n = st.number_input("Prompts to Replay (N)", min_value=1, max_value=100, value=20)

with col_ctrl2:
    if st.button("🚀 Run Replay (Model B)", use_container_width=True):
        with st.spinner("Replaying prompts on candidate model..."):
            try:
                res = httpx.post(f"{GATEWAY_URL}/replay", json={"n": replay_n}, timeout=120.0)
                if res.status_code == 200:
                    st.success(f"Successfully replayed {len(res.json())} prompts!")
                else:
                    st.error(f"Replay error ({res.status_code}): {res.text}")
            except Exception as e:
                st.error(f"Could not connect to gateway: {e}")

with col_ctrl3:
    if st.button("⚖️ Run Scoring", use_container_width=True):
        with st.spinner("Running exact match & LLM judge evaluations..."):
            try:
                res = httpx.post(f"{GATEWAY_URL}/score", timeout=120.0)
                if res.status_code == 200:
                    st.success(f"Evaluated {len(res.json())} unscored replays!")
                else:
                    st.error(f"Scoring error ({res.status_code}): {res.text}")
            except Exception as e:
                st.error(f"Could not connect to gateway: {e}")

with col_ctrl4:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

st.divider()

# --- Fetch Report Data ---
db = SessionLocal()
report = calculate_report_data(db)
db.close()

# --- Verdict Banner ---
verdict = report["verdict"]
uncertain = report["uncertain_count"]
retained_pct = report["quality_retained_pct"]

if verdict == "Safe to switch":
    st.markdown(f"""
    <div class="verdict-banner-safe">
        ✅ Verdict: SAFE TO SWITCH ({retained_pct}% quality retained | Uncertain rows: {uncertain})
    </div>
    """, unsafe_allow_html=True)
elif verdict == "Review needed":
    st.markdown(f"""
    <div class="verdict-banner-review">
        ⚠️ Verdict: REVIEW NEEDED ({retained_pct}% quality retained | Uncertain rows: {uncertain})
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="verdict-banner-unsafe">
        ❌ Verdict: NOT SAFE ({retained_pct}% quality retained | Uncertain rows: {uncertain})
    </div>
    """, unsafe_allow_html=True)

st.caption("Thresholds: **≥ 90%** = Safe to switch | **75% – 89%** = Review needed | **< 75%** = Not safe")

# --- Top Metric Cards ---
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Requests Compared", report["requests_compared"])

with col2:
    st.metric(
        "Estimated Cost / Req",
        f"${report['model_b']['avg_cost_usd']:.6f}",
        delta=f"-{report['cost_saving_pct']}% vs Model A",
        delta_color="inverse"
    )

with col3:
    st.metric(
        "Avg Latency",
        f"{report['model_b']['avg_latency_ms']:.0f} ms",
        delta=f"{report['model_b']['avg_latency_ms'] - report['model_a']['avg_latency_ms']:.0f} ms"
    )

with col4:
    st.metric(
        "Avg Quality Score",
        f"{report['model_b']['avg_score']} / 5.0" if report['model_b']['avg_score'] else "N/A"
    )

with col5:
    st.metric("Quality Retained", f"{report['quality_retained_pct']}%")

st.divider()

# --- Detailed Side-by-Side Comparison Table ---
st.subheader("Side-by-Side Response Comparison & Judge Reasoning")

db = SessionLocal()
scores = db.query(Score).order_by(Score.id.desc()).all()

if not scores:
    st.info("No comparisons recorded yet. Send chat requests and run replay + scoring to see side-by-side results.")
else:
    table_rows = []
    for s in scores:
        replay = s.replay
        req = replay.request if replay else None
        
        prompt_text = req.prompt if req else "N/A"
        ans_a = req.response if req else "N/A"
        ans_b = replay.candidate_response if replay else "N/A"
        
        if s.exact_match:
            score_display = "5 (Exact Match)"
        elif s.judge_score is not None and s.judge_parse_ok:
            score_display = f"{s.judge_score} / 5"
        else:
            score_display = "⚠️ Uncertain"

        table_rows.append({
            "Prompt": prompt_text,
            f"Answer A ({settings.MODEL_A})": ans_a,
            f"Answer B ({settings.MODEL_B})": ans_b,
            "Score": score_display,
            "Judge Reason": s.judge_reason or "N/A",
            "Raw Score": s.judge_score if s.judge_score is not None else (5 if s.exact_match else 0)
        })

    df = pd.DataFrame(table_rows)

    # Style rows: highlight scores <= 3 in soft red
    def highlight_low_scores(row):
        score_val = row["Raw Score"]
        if score_val > 0 and score_val <= 3:
            return ["background-color: #ffe6e6"] * len(row)
        elif row["Score"] == "⚠️ Uncertain":
            return ["background-color: #fff2cc"] * len(row)
        return [""] * len(row)

    styled_df = df.drop(columns=["Raw Score"]).style.apply(highlight_low_scores, axis=1)
    st.dataframe(styled_df, use_container_width=True, height=500)

db.close()
