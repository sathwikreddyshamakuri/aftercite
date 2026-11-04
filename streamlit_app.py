"""AfterCite browser demo.

This uses the case-study comparison engine unchanged, with fictional sample data.
Review decisions live only in this visitor's Streamlit session.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import streamlit as st

from aftercite import (
    STATUS_LABELS,
    analyze,
    markup_diff,
    read_claims,
    read_sources,
    render_html,
)

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "sample_data"

st.set_page_config(
    page_title="AfterCite · Evidence Change Monitor",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.html(
    """
    <style>
      .block-container { max-width: 1200px; padding-top: 2rem; }
      .eyebrow { font-size: .78rem; text-transform: uppercase; letter-spacing: .12em;
                 color: #6b7280; font-weight: 700; }
      .hero { padding: 8px 0 15px; }
      .hero h1 { margin: .2rem 0 .6rem; font-weight: 790; letter-spacing: -.035em; }
      .hero p { color: #64748b; max-width: 740px; line-height: 1.55; }
      .diffbox { border: 1px solid #ced6e1; border-radius: 12px; padding: 17px 18px;
                 min-height: 145px; margin: 6px 0 12px; overflow-wrap: anywhere;
                 line-height: 1.75; }
      .diffbox del { background: #fee2e2; color: #991b1b; padding: 2px;
                     text-decoration: line-through; }
      .diffbox ins { background: #dcfce7; color: #166534; padding: 2px;
                     text-decoration: none; font-weight: 700; }
      .muted { color: #64748b; font-size: .91rem; }
    </style>
    """,
)

if "active_deadline" not in st.session_state:
    st.session_state.active_deadline = 5
if "reviews" not in st.session_state:
    st.session_state.reviews = {}

with st.sidebar:
    st.markdown("## 🔎 AfterCite")
    st.caption("Evidence-change monitoring · prototype")
    st.divider()
    st.markdown("### Try a policy update")
    chosen_deadline = st.selectbox(
        "Revised upload deadline",
        [5, 7, 10],
        index=[5, 7, 10].index(st.session_state.active_deadline),
        format_func=lambda d: f"{d} business days" + (" · original" if d == 10 else ""),
        help="Changes one fictional policy sentence. The baseline always says 10 business days.",
    )
    if st.button("Analyze changes", type="primary", use_container_width=True):
        if chosen_deadline != st.session_state.active_deadline:
            st.session_state.reviews = {}
        st.session_state.active_deadline = chosen_deadline
    st.caption(f"Analyzed scenario: {st.session_state.active_deadline} business days")
    st.divider()
    st.markdown("**What this checks**")
    st.markdown(
        "Source removal, section removal, changed evidence, changed context, "
        "invalid original citations, and unchanged source sections."
    )
    st.info(
        "Public demo with fictional records only. No uploads, accounts, or API keys."
    )

# Read through the exact validation and analysis functions used by the CLI.
old_docs = read_sources(DATA / "before.json")
new_docs = read_sources(DATA / "after.json")
claims = read_claims(DATA / "claims.json")

# The scenario control edits only the synthetic revised sample, never the source files.
source = new_docs["aster-intake-playbook"]["sections"]["intake-window"]
new_docs["aster-intake-playbook"]["sections"]["intake-window"] = source.replace(
    "5 business days",
    f"{st.session_state.active_deadline} business days",
    1,
)
report = analyze(old_docs, new_docs, claims)
summary = report["summary"]

st.html(
    """
    <div class="hero">
      <div class="eyebrow">CASE STUDY · AI ENGINEER (TAX)</div>
      <h1>AfterCite</h1>
      <p>What happens when an answer is saved with a citation, but its source
      changes later? AfterCite identifies evidence that deserves another look
      and keeps the final decision with a human reviewer.</p>
    </div>
    """,
)

a, b, c = st.columns(3)
a.metric("Saved claims", summary["total"])
b.metric("Need review", summary["review_required"])
c.metric("Unchanged source sections", summary["unchanged"])
st.caption(
    "These are text-level change signals, not a determination that a statement "
    "is accurate or that a tax rule applies."
)
st.divider()

st.subheader("Review queue")
filter_choice = st.radio(
    "Show",
    ["All claims", "Review required", "Unchanged"],
    horizontal=True,
    label_visibility="collapsed",
)
visible = [
    item for item in report["claims"]
    if filter_choice == "All claims"
    or (filter_choice == "Review required" and item["needs_review"])
    or (filter_choice == "Unchanged" and not item["needs_review"])
]
claim_by_id = {item["id"]: item for item in visible}
selected_id = st.selectbox(
    "Select a cited claim to inspect",
    [item["id"] for item in visible],
    format_func=lambda cid: (
        f"{cid}  ·  {STATUS_LABELS[claim_by_id[cid]['status']]}  "
        f"·  {claim_by_id[cid]['claim']}"
    ),
)
item = claim_by_id[selected_id]
status = item["status"]

if item["needs_review"]:
    st.warning(f"**{STATUS_LABELS[status]}** · Human review recommended")
else:
    st.success(f"**{STATUS_LABELS[status]}** · No source text change detected")

st.markdown(f"**Saved claim:** {item['claim']}")
st.markdown(f"**Why this result:** {item['reason']}")
st.caption(
    f"Source: {item['source_title']}  |  "
    f"Section: {item['section_id']}  |  Claim ID: {item['id']}"
)
st.markdown("**Original cited evidence**")
st.info(item["evidence_quote"], icon="📌")

left, right = st.columns(2)
before_text = item["previous_section"] or ""
after_text = item["current_section"] or ""
with left:
    st.markdown("#### Before · saved source")
    st.html(
        f'<div class="diffbox">{markup_diff(before_text, after_text, "old")}</div>',
    )
with right:
    st.markdown("#### After · revised source")
    st.html(
        f'<div class="diffbox">{markup_diff(before_text, after_text, "new")}</div>',
    )

signals = item["numeric_signals"]
if signals["removed"] or signals["added"]:
    st.caption(
        "Number-change hints (not conclusions): "
        + ", ".join(signals["removed"] or ["none"])
        + " → "
        + ", ".join(signals["added"] or ["none"])
    )

st.divider()
st.subheader("Human review")
st.caption(
    "Review notes are stored only in this browser session. They are not "
    "a production audit log and are cleared when the session ends."
)
existing = st.session_state.reviews.get(selected_id)
if existing:
    st.info(
        f"Recorded in this session: {existing['decision']} "
        f"by {existing['reviewer']}. "
        f"Note: {existing['note'] or '(none)'}"
    )

with st.form(f"review_{selected_id}"):
    reviewer = st.text_input("Reviewer", value="Demo reviewer", max_chars=80)
    decision = st.selectbox(
        "Review decision",
        ["needs_followup", "verified_updated", "dismissed_with_reason"],
        format_func=lambda s: {
            "needs_followup": "Needs follow-up",
            "verified_updated": "Verified / updated externally",
            "dismissed_with_reason": "Dismissed with reason",
        }[s],
    )
    note = st.text_area(
        "Review note", placeholder="Explain what should happen next",
        max_chars=1000,
    )
    submitted = st.form_submit_button("Record session review")
if submitted:
    if not reviewer.strip():
        st.error("Please enter a reviewer label.")
    elif decision == "dismissed_with_reason" and not note.strip():
        st.error("Please explain why this signal was dismissed.")
    else:
        st.session_state.reviews[selected_id] = {
            "claim_id": selected_id,
            "decision": decision,
            "reviewer": reviewer.strip(),
            "note": note.strip(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        st.success("Review recorded for this session.")
        st.rerun()

st.divider()
st.subheader("Export the results")
st.caption("Download the full generated report or an offline, human-readable copy.")
c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "Download JSON report",
        data=json.dumps(
            {**report, "review_decisions": list(st.session_state.reviews.values())},
            indent=2,
            ensure_ascii=False,
        ),
        file_name="aftercite-report.json",
        mime="application/json",
        use_container_width=True,
    )
with c2:
    st.download_button(
        "Download HTML report",
        data=render_html(report, st.session_state.reviews),
        file_name="aftercite-report.html",
        mime="text/html",
        use_container_width=True,
    )
st.divider()
st.caption(
    "Demonstration only · Entirely synthetic data · No real tax guidance · "
    "Text comparisons can flag harmless changes and cannot establish claim truth."
)
