"""
ContentMux — AI Content Multiplexer
Premium dark UI. No Streamlit defaults.
"""

import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import plotly.graph_objects as go
from config import settings
from core.models import MultiplexResult, ContentVariant
from services.platform_rules import PLATFORMS, get_platform_spec, get_all_platforms
from services.scorer import ContentScorer
from services.ai_engine import transform_content
from services.content_store import (
    save_result, get_recent_results, get_result_with_variants,
    get_total_results, get_total_variants, save_feedback, get_user_preferences,
)

st.set_page_config(page_title="ContentMux", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

# ═══════════════════════════════════════════════════════════
# AGGRESSIVE CSS — Override EVERY Streamlit default
# ═══════════════════════════════════════════════════════════

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── GLOBAL RESET ── */
*, *::before, *::after { box-sizing: border-box; }

.stApp, .stApp * {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.stApp {
    background: #09090b !important;
    color: #ededef !important;
}

/* ── HIDE DEFAULT STREAMLIT UI ── */
#MainMenu, footer, header[data-testid="stHeader"],
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stSidebarNav"] {
    display: none !important;
    height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 1rem !important;
    max-width: 1080px !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: #0c0c0e !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
    display: none !important;
}

/* ── TEXTAREA / INPUT ── */
.stTextArea textarea, .stTextInput input {
    background: #111113 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    color: #ededef !important;
    font-size: 0.875rem !important;
    padding: 12px 14px !important;
    transition: border-color 120ms ease, box-shadow 120ms ease !important;
}
.stTextArea textarea:hover, .stTextInput input:hover {
    border-color: rgba(255,255,255,0.14) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #7c5bf5 !important;
    box-shadow: 0 0 0 3px rgba(124,91,245,0.12) !important;
    outline: none !important;
}

/* ── MULTISELECT — FORCE OVERRIDE RED TAGS ── */
[data-baseweb="multi-select"] {
    background: #111113 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
}
[data-baseweb="multi-select"]:hover {
    border-color: rgba(255,255,255,0.14) !important;
}
[data-baseweb="multi-select"]:focus-within {
    border-color: #7c5bf5 !important;
    box-shadow: 0 0 0 3px rgba(124,91,245,0.12) !important;
}

/* Multiselect tags/chips */
[data-baseweb="tag"] {
    background: rgba(124,91,245,0.15) !important;
    border: 1px solid rgba(124,91,245,0.25) !important;
    border-radius: 6px !important;
    color: #c4b5fd !important;
    font-size: 0.75rem !important;
    padding: 2px 8px !important;
}
[data-baseweb="tag"] span {
    color: #c4b5fd !important;
}
[data-baseweb="tag"]:hover {
    background: rgba(124,91,245,0.25) !important;
}

/* Tag remove button */
[data-baseweb="tag"] button {
    color: #c4b5fd !important;
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin-left: 4px !important;
}
[data-baseweb="tag"] button:hover {
    color: #a78bfa !important;
}

/* Multiselect dropdown */
[data-baseweb="popover"] {
    background: #18181b !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
}
[data-baseweb="select-option"] {
    background: transparent !important;
    color: #ededef !important;
}
[data-baseweb="select-option"]:hover, [data-baseweb="select-option"]:focus {
    background: rgba(124,91,245,0.12) !important;
}

/* Multiselect arrows/clear */
[data-baseweb="multi-select"] svg {
    color: rgba(255,255,255,0.3) !important;
}

/* ── SELECTBOX ── */
.stSelectbox > div > div {
    background: #111113 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    color: #ededef !important;
}

/* ── BUTTONS ── */
.stButton > button[kind="primary"],
.stButton > button {
    background: #ededef !important;
    color: #09090b !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.8125rem !important;
    letter-spacing: -0.01em !important;
    padding: 10px 20px !important;
    transition: all 120ms ease !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
    line-height: 1.4 !important;
}
.stButton > button:hover {
    background: rgba(255,255,255,0.9) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
}
.stButton > button:focus {
    box-shadow: 0 0 0 3px rgba(124,91,245,0.3) !important;
}

/* Small buttons (feedback) */
.stButton > button:not([kind="primary"]) {
    background: #18181b !important;
    color: #8a8a8e !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    padding: 6px 12px !important;
    font-size: 0.75rem !important;
    min-width: 36px !important;
}
.stButton > button:not([kind="primary"]):hover {
    background: #1f1f23 !important;
    color: #ededef !important;
    border-color: rgba(255,255,255,0.12) !important;
    box-shadow: none !important;
    transform: none !important;
}

/* Download button */
.stDownloadButton > button {
    background: #18181b !important;
    color: #8a8a8e !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    box-shadow: none !important;
}
.stDownloadButton > button:hover {
    background: #1f1f23 !important;
    color: #ededef !important;
    border-color: rgba(255,255,255,0.12) !important;
    box-shadow: none !important;
    transform: none !important;
}

/* ── EXPANDERS ── */
details[data-testid="stExpander"] {
    background: #111113 !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
    margin-bottom: 6px !important;
}
details[data-testid="stExpander"]:hover {
    border-color: rgba(255,255,255,0.1) !important;
}
details[data-testid="stExpander"] summary {
    color: #ededef !important;
    font-size: 0.8125rem !important;
    font-weight: 500 !important;
    padding: 12px 16px !important;
}
details[data-testid="stExpander"] summary:hover {
    color: #fff !important;
}
details[data-testid="stExpander"][open] summary {
    border-bottom: 1px solid rgba(255,255,255,0.04) !important;
}
/* Expander arrow */
details[data-testid="stExpander"] summary svg {
    color: rgba(255,255,255,0.3) !important;
}

/* ── METRICS ── */
[data-testid="stMetric"] {
    background: #111113 !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 8px !important;
    padding: 12px 14px !important;
}
[data-testid="stMetric"] label {
    color: rgba(255,255,255,0.3) !important;
    font-size: 0.6rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-weight: 500 !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #ededef !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    background: #111113 !important;
    border-radius: 8px !important;
    padding: 3px !important;
    gap: 2px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: rgba(255,255,255,0.3) !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    font-size: 0.8125rem !important;
    padding: 6px 12px !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: rgba(255,255,255,0.55) !important;
}
.stTabs [aria-selected="true"] {
    background: #1f1f23 !important;
    color: #ededef !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background: transparent !important;
}

/* ── DIVIDER ── */
hr {
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.06) !important;
    margin: 0 !important;
}

/* ── TOAST ── */
.stToast {
    background: #18181b !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    color: #ededef !important;
    font-size: 0.8125rem !important;
}
.stToast > div {
    color: #ededef !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.15); }

/* ── SELECTION ── */
::selection {
    background: rgba(124,91,245,0.3) !important;
    color: #fff !important;
}

/* ── PLOTLY OVERRIDES ── */
.js-plotly-plot .plotly {
    background: transparent !important;
}
.stPlotlyChart {
    background: transparent !important;
}

/* ── LABELS ── */
.stTextArea label, .stTextInput label, .stMultiSelect label, .stSelectbox label {
    color: rgba(255,255,255,0.3) !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-weight: 500 !important;
    margin-bottom: 4px !important;
}

/* ── CONTAINER / COLUMNS ── */
[data-testid="stHorizontalBlock"] {
    gap: 1.5rem !important;
}

/* ── FORM SUBMIT ── */
.stFormSubmitButton > button {
    background: #7c5bf5 !important;
    color: white !important;
}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# LAYOUT
# ═══════════════════════════════════════════════════════════

icons = {"linkedin": "💼", "twitter": "𝕏", "instagram": "📸", "facebook": "👤", "email": "✉", "ad": "📢"}

# ── Header ──
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;padding:0 0 20px 0;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:2rem">
    <div style="display:flex;align-items:center;gap:10px">
        <div style="width:28px;height:28px;background:#7c5bf5;border-radius:7px;display:flex;align-items:center;justify-content:center">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
        </div>
        <span style="font-size:0.9rem;font-weight:600;color:#ededef;letter-spacing:-0.02em">ContentMux</span>
    </div>
    <div style="display:flex;align-items:center;gap:6px">
        <div style="width:5px;height:5px;border-radius:50%;background:{'#22c55e' if settings.ai_configured else '#f97316'}"></div>
        <span style="font-size:0.7rem;color:rgba(255,255,255,0.35)">{'AI' if settings.ai_configured else 'Fallback'}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("""<div style="font-size:0.6rem;font-weight:600;color:rgba(255,255,255,0.25);text-transform:uppercase;letter-spacing:0.12em;margin-bottom:12px">Library</div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.metric("Docs", get_total_results())
    c2.metric("Vars", get_total_variants())

    st.markdown("""<div style="height:1px;background:rgba(255,255,255,0.06);margin:20px 0"></div>""", unsafe_allow_html=True)
    st.markdown("""<div style="font-size:0.6rem;font-weight:600;color:rgba(255,255,255,0.25);text-transform:uppercase;letter-spacing:0.12em;margin-bottom:12px">Taste</div>""", unsafe_allow_html=True)

    prefs = get_user_preferences()
    if prefs["total_ratings"] > 0:
        for platform, data in prefs["preferred_platforms"].items():
            ic = icons.get(platform, "·")
            total = data["likes"] + data["dislikes"]
            pct = (data["likes"] / total * 100) if total > 0 else 0
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                <span style="font-size:0.75rem;opacity:0.4">{ic}</span>
                <span style="font-size:0.75rem;color:rgba(255,255,255,0.5);flex:1">{platform.title()}</span>
                <div style="width:48px;height:3px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden">
                    <div style="width:{pct}%;height:100%;background:{'#22c55e' if pct>=60 else '#eab308' if pct>=40 else '#ef4444'};border-radius:2px"></div>
                </div>
                <span style="font-size:0.65rem;color:rgba(255,255,255,0.25);width:28px;text-align:right">{pct:.0f}%</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""<div style="font-size:0.75rem;color:rgba(255,255,255,0.2);padding:4px 0">No ratings</div>""", unsafe_allow_html=True)

    st.markdown("""<div style="height:1px;background:rgba(255,255,255,0.06);margin:20px 0"></div>""", unsafe_allow_html=True)
    st.markdown("""<div style="font-size:0.6rem;font-weight:600;color:rgba(255,255,255,0.25);text-transform:uppercase;letter-spacing:0.12em;margin-bottom:12px">Recent</div>""", unsafe_allow_html=True)

    for r in get_recent_results(8):
        topic = r.get("topic", "") or r["original_text"][:35]
        score = r.get("avg_score", 0)
        if st.button(f"·  {topic}", key=f"h_{r['result_id']}", use_container_width=True):
            st.session_state.view_history = r["result_id"]
            st.rerun()

# ── History ──
if "view_history" in st.session_state:
    data = get_result_with_variants(st.session_state.view_history)
    if data:
        st.markdown(f"""
        <div style="margin-bottom:20px">
            <div style="font-size:1.1rem;font-weight:600;color:#ededef;letter-spacing:-0.02em;margin-bottom:4px">{data.get('topic','Past Content')}</div>
            <div style="font-size:0.7rem;color:rgba(255,255,255,0.25)">{data['created_at'][:10]} · {data['variant_count']} variants · avg {data['avg_score']:.0f}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""<div style="background:#111113;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:14px 16px;margin-bottom:20px;font-size:0.8125rem;color:rgba(255,255,255,0.5);line-height:1.7">{data['original_text'][:500]}{'…' if len(data['original_text'])>500 else ''}</div>""", unsafe_allow_html=True)

        export_text = f"TOPIC: {data.get('topic','')}\nORIGINAL:\n{data['original_text']}\n\n{'='*60}\n\n"
        for v in data["variants"]:
            ic = icons.get(v["platform"], "·")
            with st.expander(f"{ic}  {v['platform'].title()}  ·  {v['score_overall']:.0f}"):
                st.text_area("c", v["content"], height=180, disabled=True, key=f"hv_{v['id']}")
                export_text += f"--- {v['platform'].upper()} ({v['score_overall']:.0f}) ---\n{v['content']}\n\n"

        st.download_button("↓ Export", export_text, file_name="content.txt", mime="text/plain")
        if st.button("← Back"):
            del st.session_state.view_history
            st.rerun()
    st.markdown("""<div style="height:1px;background:rgba(255,255,255,0.06);margin:2rem 0"></div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

col_in, col_out = st.columns([4, 7], gap="large")

with col_in:
    st.markdown("""<div style="font-size:0.6rem;font-weight:600;color:rgba(255,255,255,0.25);text-transform:uppercase;letter-spacing:0.12em;margin-bottom:10px">Create</div>""", unsafe_allow_html=True)

    topic = st.text_input("Campaign", placeholder="Campaign name (optional)", label_visibility="collapsed")
    original_text = st.text_area("Content", height=280, label_visibility="collapsed", placeholder="Paste your content…")
    target_platforms = st.multiselect("Platforms", get_all_platforms(), default=["linkedin", "twitter", "instagram"], label_visibility="collapsed")
    generate_btn = st.button("Generate  →", type="primary", use_container_width=True)

with col_out:
    if generate_btn and original_text.strip() and target_platforms:
        with st.spinner(""):
            original_score = ContentScorer.score_text(original_text, "linkedin")

        gc = "#22c55e" if original_score.overall >= 70 else "#eab308" if original_score.overall >= 50 else "#ef4444"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:20px">
            <div style="position:relative;width:48px;height:48px;flex-shrink:0">
                <svg width="48" height="48" viewBox="0 0 48 48">
                    <circle cx="24" cy="24" r="20" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="2.5"/>
                    <circle cx="24" cy="24" r="20" fill="none" stroke="{gc}" stroke-width="2.5"
                            stroke-dasharray="{original_score.overall * 1.257} 125.7"
                            stroke-linecap="round" transform="rotate(-90 24 24)"/>
                </svg>
                <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:0.85rem;font-weight:700;color:{gc}">{original_score.overall:.0f}</div>
            </div>
            <div>
                <div style="font-size:0.85rem;font-weight:500;color:#ededef">Original</div>
                <div style="font-size:0.7rem;color:rgba(255,255,255,0.3)">{original_score.grade} · {len(original_text.split())} words</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        bars = ""
        for label, val in [("Readability", original_score.readability), ("Engagement", original_score.engagement),
                           ("Sentiment", original_score.sentiment), ("Fit", original_score.platform_fit),
                           ("Hook", original_score.hook_strength), ("CTA", original_score.cta_presence)]:
            bc = "#22c55e" if val >= 70 else "#eab308" if val >= 50 else "#ef4444"
            bars += f"""<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                <span style="font-size:0.65rem;color:rgba(255,255,255,0.25);width:72px;text-align:right;font-variant-numeric:tabular-nums">{label}</span>
                <div style="flex:1;height:3px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden">
                    <div style="width:{val}%;height:100%;background:{bc};border-radius:2px;transition:width 0.5s ease"></div>
                </div>
                <span style="font-size:0.65rem;color:rgba(255,255,255,0.35);width:24px;font-variant-numeric:tabular-nums">{val:.0f}</span>
            </div>"""

        st.markdown(f"""<div style="background:#111113;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:14px 16px;margin-bottom:20px">{bars}</div>""", unsafe_allow_html=True)

        if original_score.issues:
            items = ""
            for x in original_score.issues:
                items += f'<div style="font-size:0.75rem;color:#f97316;padding:3px 0;display:flex;gap:6px"><span style="opacity:0.4">→</span>{x}</div>'
            for x in original_score.suggestions:
                items += f'<div style="font-size:0.75rem;color:#22c55e;padding:3px 0;display:flex;gap:6px"><span style="opacity:0.4">→</span>{x}</div>'
            st.markdown(f"""<div style="background:#111113;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:14px 16px;margin-bottom:20px"><div style="font-size:0.6rem;font-weight:600;color:rgba(255,255,255,0.25);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px">Analysis</div>{items}</div>""", unsafe_allow_html=True)

        st.markdown("""<div style="height:1px;background:rgba(255,255,255,0.06);margin:4px 0 20px 0"></div>""", unsafe_allow_html=True)

        result = MultiplexResult(original_text=original_text, topic=topic, original_score=original_score)
        generated = []

        for platform in target_platforms:
            spec = get_platform_spec(platform)
            ic = icons.get(platform, "·")

            with st.spinner(f"{platform.title()}..."):
                try:
                    loop = asyncio.new_event_loop()
                    transformed = loop.run_until_complete(transform_content(original_text, platform, spec, topic))
                    loop.close()
                except Exception:
                    transformed = original_text[:spec["max_chars"]]
                score = ContentScorer.score_text(transformed, platform)

            generated.append((platform, transformed, score))
            gc = "#22c55e" if score.overall >= 70 else "#eab308" if score.overall >= 50 else "#ef4444"

            with st.expander(f"{ic}  {platform.title()}  ·  {score.overall:.0f}  ·  {score.grade}", expanded=True):
                st.text_area(platform, transformed, height=170, disabled=True, key=f"c_{platform}")

                mb = ""
                for label, val in [("Read", score.readability), ("Engage", score.engagement),
                                   ("Fit", score.platform_fit), ("Hook", score.hook_strength)]:
                    bc = "#22c55e" if val >= 70 else "#eab308" if val >= 50 else "#ef4444"
                    mb += f"""<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px">
                        <span style="font-size:0.6rem;color:rgba(255,255,255,0.2);width:36px;text-align:right">{label}</span>
                        <div style="flex:1;height:2px;background:rgba(255,255,255,0.06);border-radius:1px;overflow:hidden">
                            <div style="width:{val}%;height:100%;background:{bc};border-radius:1px"></div>
                        </div>
                        <span style="font-size:0.6rem;color:rgba(255,255,255,0.2);width:20px">{val:.0f}</span>
                    </div>"""

                st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:flex-start"><div style="flex:1;margin-right:12px">{mb}</div><div style="font-size:0.65rem;color:rgba(255,255,255,0.2)">{len(transformed.split())}w · {len(transformed)}c</div></div>""", unsafe_allow_html=True)

                fc1, fc2, _ = st.columns([1, 1, 8])
                with fc1:
                    if st.button("↑", key=f"up_{platform}", help="Like"):
                        save_feedback(result.result_id, platform, 1)
                        st.toast(f"👍 {platform.title()}")
                with fc2:
                    if st.button("↓", key=f"down_{platform}", help="Dislike"):
                        save_feedback(result.result_id, platform, -1)
                        st.toast(f"👎 {platform.title()}")

        for p, c, s in generated:
            result.variants.append(ContentVariant(platform=p, content=c, score=s))
        save_result(result.to_dict())

        export_text = f"TOPIC: {topic}\nORIGINAL:\n{original_text}\n\n{'='*60}\n\n"
        for p, c, s in generated:
            export_text += f"--- {p.upper()} ({s.overall:.0f}) ---\n{c}\n\n"

        st.download_button("↓ Export All", export_text, file_name=f"mux_{result.result_id}.txt", mime="text/plain", use_container_width=True)

        st.markdown("""<div style="height:1px;background:rgba(255,255,255,0.06);margin:20px 0 12px 0"></div>""", unsafe_allow_html=True)

        fig = go.Figure()
        for i, metric in enumerate(["Overall", "Readability", "Engagement", "Platform Fit"]):
            fig.add_trace(go.Bar(
                name=metric,
                x=[p.title() for p, _, _ in generated],
                y=[getattr(s, metric.lower().replace(" ","_")) for _, _, s in generated]
                   if metric!="Platform Fit" else [s.platform_fit for _, _, s in generated],
                marker_color=["#7c5bf5","#22c55e","#eab308","#f97316"][i],
                text=[f"{v:.0f}" for v in (
                    [getattr(s, metric.lower().replace(" ","_")) for _, _, s in generated]
                    if metric!="Platform Fit" else [s.platform_fit for _, _, s in generated]
                )],
                textposition="auto",
                textfont=dict(size=9, color="rgba(255,255,255,0.5)"),
            ))
        fig.update_layout(
            barmode="group", template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=260, margin=dict(l=16,r=16,t=8,b=16),
            legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1,font=dict(size=9,color="rgba(255,255,255,0.3)")),
            xaxis=dict(gridcolor="rgba(255,255,255,0.04)",tickfont=dict(size=9,color="rgba(255,255,255,0.3)")),
            yaxis=dict(gridcolor="rgba(255,255,255,0.04)",tickfont=dict(size=9,color="rgba(255,255,255,0.3)")),
        )
        st.plotly_chart(fig, use_container_width=True)

    elif generate_btn:
        st.markdown("""<div style="text-align:center;padding:60px;background:#111113;border:1px solid rgba(255,255,255,0.06);border-radius:10px"><div style="font-size:0.8125rem;color:rgba(255,255,255,0.25)">Enter content to transform</div></div>""", unsafe_allow_html=True)

    else:
        st.markdown("""
        <div style="text-align:center;padding:80px 32px;background:#111113;border:1px solid rgba(255,255,255,0.06);border-radius:14px">
            <div style="width:44px;height:44px;background:#7c5bf5;border-radius:11px;display:flex;align-items:center;justify-content:center;margin:0 auto 20px">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
            </div>
            <div style="font-size:0.95rem;font-weight:600;color:#ededef;margin-bottom:6px;letter-spacing:-0.02em">Paste, pick, generate</div>
            <div style="font-size:0.8rem;color:rgba(255,255,255,0.3);line-height:1.7">
                One content → six platform versions.<br>Scored. Compared. 30 seconds.
            </div>
        </div>
        """, unsafe_allow_html=True)
