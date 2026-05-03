"""
dashboard/app.py

MediaFlow Simulator — Streamlit Dashboard
Connects to the FastAPI backend and displays live pipeline state.

Run with: streamlit run dashboard/app.py
Requires the FastAPI backend to be running on http://127.0.0.1:8000
"""

import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────
API_BASE = "http://127.0.0.1:8000"

# Cost simulation — realistic per-stage processing costs in GBP
# In a real ITV system these would reflect actual compute/storage costs
STAGE_COSTS = {
    "INGESTED":            50,
    "METADATA_VALIDATION": 30,
    "QC_CHECK":           120,
    "TRANSCODING":        400,
    "RIGHTS_COMPLIANCE":   80,
    "ARCHIVING":          200,
    "DISTRIBUTION_READY": 360,
}

# Colour coding for each stage status
STATUS_COLOURS = {
    "DISTRIBUTION_READY": "🟢",
    "ARCHIVING":          "🔵",
    "RIGHTS_COMPLIANCE":  "🔵",
    "TRANSCODING":        "🔵",
    "QC_CHECK":           "🟡",
    "METADATA_VALIDATION":"🟡",
    "INGESTED":           "⚪",
}


# ── API helpers ───────────────────────────────────────────────────

def fetch_pipeline_summary() -> dict:
    """Fetch high-level pipeline counts from the backend."""
    try:
        r = requests.get(f"{API_BASE}/pipeline/summary", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the MediaFlow API. Is it running?")
        st.code("uvicorn app.main:app --reload", language="bash")
        st.stop()
    except Exception as e:
        st.error(f"API error: {e}")
        st.stop()


def fetch_assets(title: str = "", source: str = "", stage: str = "") -> list:
    """Fetch assets with optional search/filter parameters."""
    params = {}
    if title:
        params["title"] = title
    if source:
        params["source"] = source
    if stage and stage != "All":
        params["stage"] = stage

    try:
        r = requests.get(f"{API_BASE}/pipeline/search", params=params, timeout=5)
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception:
        return []


def fetch_asset_history(asset_id: int) -> dict:
    """Fetch the full workflow history for a single asset."""
    try:
        r = requests.get(f"{API_BASE}/assets/{asset_id}/history", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def advance_asset(asset_id: int) -> dict:
    """Call the API to advance an asset to the next stage."""
    try:
        r = requests.post(
            f"{API_BASE}/workflow/{asset_id}/advance",
            json={},
            timeout=5
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def calculate_pipeline_cost(summary: dict) -> int:
    """
    Simulates total pipeline cost based on how many assets
    have passed through each stage.
    """
    total = 0
    for stage, count in summary.get("by_stage", {}).items():
        total += STAGE_COSTS.get(stage, 0) * count
    return total


# ── Page config ───────────────────────────────────────────────────

st.set_page_config(
    page_title="MediaFlow Simulator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS — tightens up Streamlit's default spacing
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .metric-label { font-size: 0.85rem; }
    div[data-testid="stMetricValue"] { font-size: 2rem; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────

with st.sidebar:
    st.title("🎬 MediaFlow")
    st.caption("ITV Content Supply Pipeline Simulator")
    st.divider()

    st.subheader("🔍 Search & Filter")

    search_title = st.text_input("Search by title", placeholder="e.g. Coronation")
    
    filter_stage = st.selectbox(
        "Filter by stage",
        options=[
            "All",
            "INGESTED",
            "METADATA_VALIDATION",
            "QC_CHECK",
            "TRANSCODING",
            "RIGHTS_COMPLIANCE",
            "ARCHIVING",
            "DISTRIBUTION_READY",
        ]
    )

    filter_source = st.text_input("Filter by source", placeholder="e.g. ITV Studios")

    refresh = st.button("🔄 Refresh Dashboard", use_container_width=True)

    st.divider()
    st.caption("Stage cost simulation (GBP)")
    for stage, cost in STAGE_COSTS.items():
        st.caption(f"`{stage}` — £{cost}")


# ── Fetch data ────────────────────────────────────────────────────

summary = fetch_pipeline_summary()
assets = fetch_assets(
    title=search_title,
    source=filter_source,
    stage=filter_stage,
)
pipeline_cost = calculate_pipeline_cost(summary)


# ── Header ────────────────────────────────────────────────────────

st.title("🎬 MediaFlow Simulator")
st.caption(
    "Live view of the ITV content supply pipeline — "
    "from ingest through to Linear, ITVX, and B2B distribution."
)
st.divider()


# ── Metric cards ──────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Assets",
        value=summary.get("total_assets", 0),
    )

with col2:
    st.metric(
        label="🟢 Distribution Ready",
        value=summary.get("distribution_ready_count", 0),
    )

with col3:
    failed = summary.get("failed_count", 0)
    st.metric(
        label="🔴 Failed Stages",
        value=failed,
        delta=f"-{failed} need attention" if failed else None,
        delta_color="inverse",
    )

with col4:
    st.metric(
        label="💷 Est. Pipeline Cost",
        value=f"£{pipeline_cost:,}",
    )


# ── Stage bar chart ───────────────────────────────────────────────

st.subheader("📊 Assets by Pipeline Stage")

by_stage = summary.get("by_stage", {})
stages = list(by_stage.keys())
counts = list(by_stage.values())

# Colour bars — green for distribution ready, red if stage has failures
bar_colours = []
for stage in stages:
    if stage == "DISTRIBUTION_READY":
        bar_colours.append("#4ade80")
    else:
        bar_colours.append("#60a5fa")

fig = go.Figure(
    data=[
        go.Bar(
            x=stages,
            y=counts,
            marker_color=bar_colours,
            text=counts,
            textposition="outside",
        )
    ]
)

fig.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="#e2e8f0",
    margin=dict(t=20, b=20, l=20, r=20),
    height=280,
    xaxis=dict(
        tickfont=dict(size=10),
        gridcolor="rgba(255,255,255,0.05)",
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.05)",
        dtick=1,
    ),
)

st.plotly_chart(fig, use_container_width=True)

st.divider()


# ── Asset table ───────────────────────────────────────────────────

st.subheader(f"📋 Assets ({len(assets)} shown)")

if not assets:
    st.info("No assets match your current filters.")
else:
    for asset in assets:
        stage = asset["current_stage"]
        icon = STATUS_COLOURS.get(stage, "⚪")

        with st.expander(
            f"{icon} **{asset['title']}** — {stage}",
            expanded=False,
        ):
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.markdown(f"**Asset ID:** `{asset['id']}`")
                st.markdown(f"**Source:** {asset['source']}")

            with col_b:
                st.markdown(f"**Current Stage:** `{stage}`")
                ingested = asset.get("ingest_timestamp", "")[:10]
                st.markdown(f"**Ingested:** {ingested}")

            with col_c:
                # Advance button — lets you drive the pipeline from the dashboard
                if stage != "DISTRIBUTION_READY":
                    if st.button(
                        f"▶ Advance to next stage",
                        key=f"advance_{asset['id']}"
                    ):
                        result = advance_asset(asset["id"])
                        if "error_message" in result and result["error_message"]:
                            st.error(f"Stage failed: {result['error_message']}")
                        else:
                            st.success(f"Advanced to {result.get('new_stage', '')}")
                        st.rerun()
                else:
                    st.success("✅ Ready for distribution")

            # Workflow history
            st.markdown("**Workflow history:**")
            history = fetch_asset_history(asset["id"])

            for step in history.get("history", []):
                status = step["status"]
                if status == "PASSED":
                    status_icon = "✅"
                elif status == "FAILED":
                    status_icon = "❌"
                elif status == "IN_PROGRESS":
                    status_icon = "🔄"
                else:
                    status_icon = "⏳"

                started = step.get("started_at", "")[:19].replace("T", " ")
                line = f"{status_icon} `{step['stage_name']}` — {status} — {started}"

                if step.get("error_message"):
                    line += f"\n> ⚠️ {step['error_message']}"
                if step.get("notes"):
                    line += f"\n> 📝 {step['notes']}"

                st.markdown(line)


# ── Distribution ready panel ──────────────────────────────────────

st.divider()
st.subheader("🚀 Distribution Ready")
st.caption("Assets cleared for delivery to Linear TV, ITVX (VoD), and B2B partners")

try:
    r = requests.get(f"{API_BASE}/pipeline/distribution-ready", timeout=5)
    ready_assets = r.json().get("assets", [])

    if not ready_assets:
        st.info("No assets have reached distribution ready yet.")
    else:
        for a in ready_assets:
            expiry = a.get("rights_expiry", "")[:10] if a.get("rights_expiry") else "N/A"
            st.success(
                f"🎬 **{a['title']}** | "
                f"Format: `{a['format']}` | "
                f"Territory: `{a['rights_territory']}` | "
                f"Rights expire: `{expiry}`"
            )
except Exception:
    st.warning("Could not load distribution-ready assets.")


# ── Footer ────────────────────────────────────────────────────────

st.divider()
st.caption(
    "MediaFlow Simulator · Built with FastAPI + SQLAlchemy + Streamlit · "
    "Inspired by ITV's Content Supply & Distribution pipeline"
)