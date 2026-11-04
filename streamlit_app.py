"""Small browser demo for the AfterCite case study.

Uses the same comparison functions as the command-line prototype.
"""
import json
from pathlib import Path

import streamlit as st

from aftercite import (
    STATUS_LABELS,
    analyze,
    read_claims,
    read_sources,
    render_html,
)

DATA = Path(__file__).resolve().parent / "sample_data"

st.set_page_config(page_title="AfterCite", layout="centered")
st.title("AfterCite")
st.write(
    "A simple check for saved citations when their source documents change. "
    "The tool flags claims for a person to review."
)
st.caption("Sample data are fictional. This is not tax advice.")

# Keep the comparison logic in aftercite.py.
before = read_sources(DATA / "before.json")
after = read_sources(DATA / "after.json")
claims = read_claims(DATA / "claims.json")
report = analyze(before, after, claims)
summary = report["summary"]

c1, c2, c3 = st.columns(3)
c1.metric("Claims checked", summary["total"])
c2.metric("Need review", summary["review_required"])
c3.metric("Unchanged", summary["unchanged"])

st.subheader("Check a claim")
by_id = {claim["id"]: claim for claim in report["claims"]}
ids = list(by_id)
selected_id = st.selectbox(
    "Saved claim",
    ids,
    index=ids.index("C-101"),
    format_func=lambda claim_id: f"{claim_id} — {by_id[claim_id]['claim']}",
)
selected = by_id[selected_id]

if selected["needs_review"]:
    st.warning(STATUS_LABELS[selected["status"]])
else:
    st.success(STATUS_LABELS[selected["status"]])

st.write(selected["reason"])
st.caption(f"Source: {selected['source_title']} | Section: {selected['section_id']}")

if selected["status"] == "BROKEN_BASELINE":
    # This claim's evidence was missing even before the source was revised.
    st.write("**Claim's original evidence quote**")
    st.write(selected["evidence_quote"])
    st.write("**What the original source actually says**")
    st.write(selected["previous_section"] or "Section not found")
else:
    left, right = st.columns(2)
    with left:
        st.write("**Before**")
        st.write(selected["previous_section"] or "Section not found")
    with right:
        st.write("**After**")
        st.write(selected["current_section"] or "Section not found")

    numbers = selected["numeric_signals"]
    if numbers["removed"] or numbers["added"]:
        st.caption(
            "Changed numbers: "
            + ", ".join(numbers["removed"] or ["none"])
            + " → "
            + ", ".join(numbers["added"] or ["none"])
        )

if "reviews" not in st.session_state:
    st.session_state.reviews = {}

with st.expander("Record a review"):
    st.caption("Demo only — notes are kept in this browser session.")
    existing = st.session_state.reviews.get(selected_id)
    if existing:
        st.write(f"Last review: {existing['decision']} — {existing['note'] or 'No note'}")

    with st.form(f"review_{selected_id}"):
        reviewer = st.text_input("Reviewer", value="Demo reviewer")
        decision = st.selectbox(
            "Decision",
            ["needs_followup", "verified_updated", "dismissed_with_reason"],
            format_func=lambda value: {
                "needs_followup": "Needs follow-up",
                "verified_updated": "Verified / updated",
                "dismissed_with_reason": "Dismissed with reason",
            }[value],
        )
        note = st.text_area("Note")
        save = st.form_submit_button("Save review")

    if save:
        if not reviewer.strip():
            st.error("Enter a reviewer name.")
        elif decision == "dismissed_with_reason" and not note.strip():
            st.error("Add a reason for dismissing the change.")
        else:
            st.session_state.reviews[selected_id] = {
                "decision": decision,
                "reviewer": reviewer.strip(),
                "note": note.strip(),
            }
            st.success("Review saved for this session.")

with st.expander("Download results"):
    st.download_button(
        "JSON report",
        data=json.dumps(report, indent=2),
        file_name="aftercite-report.json",
        mime="application/json",
    )
    st.download_button(
        "HTML report",
        data=render_html(report, st.session_state.reviews),
        file_name="aftercite-report.html",
        mime="text/html",
    )

st.caption(
    "AfterCite checks whether cited text has changed. "
    "It does not decide if a claim is correct."
)
