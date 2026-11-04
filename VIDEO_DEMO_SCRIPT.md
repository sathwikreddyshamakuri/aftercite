# AfterCite | Screen-recording script (2–3 minutes)

**Format:** Record the real Streamlit app in your browser, using your own voice. Keep the pointer visible and enlarge the browser to 110–125%. Do not show personal data or credentials.

## 0:00–0:25 — Intro

"Hi, I'm Sathwik. This is AfterCite, a small prototype I built for the MiraFlores AI case study. The problem I'm addressing is what happens after an AI-generated answer is saved with a citation, but the document behind that citation gets updated. The answer may still look credible, even though its evidence has changed."

**On screen:** Live Streamlit dashboard.

## 0:25–0:50 — Summary

"The prototype compares original and revised source sections against previously saved claims. In this fictional sample, there are six claims. Five need a human review, and one has an unchanged source section. This is a conservative flagging system; it doesn't decide whether the claims are true."

**On screen:** Three summary metrics. Select C-101 from the dropdown.

## 0:50–1:35 — Evidence change

"Here's a simple example. The saved answer says clients have ten business days to upload their documents. The revised policy now says five days. AfterCite notices that the original evidence quote is no longer present, marks the citation for review, and shows exactly what changed in the source text."

**On screen:** C-101, review reason, 10 vs 5 highlighted in before/after columns.

## 1:35–2:00 — Interactive change

"I can also test an alternate revision. I'll change the example policy to seven business days and analyze again. The source comparison updates using the same analysis engine as the command-line version."

**On screen:** Choose 7 in sidebar, click Analyze changes; reopen C-101.

## 2:00–2:25 — Human in the loop

"Instead of automatically editing published answers, AfterCite keeps the final decision with a reviewer. I'll flag this claim for follow-up and record a note. In this public demo, review entries are session-only, not a production audit system."

**On screen:** Fill reviewer / decision / note, submit.

## 2:25–2:55 — Outputs and close

"Reviewers can download both JSON and HTML reports. I kept the solution intentionally lightweight: standard-library Python for the comparison logic, plus a Streamlit interface. The trade-off is that it catches text and evidence changes, but it doesn't verify tax-law correctness or understand every semantic change. That's where human review remains important. Thank you!"

**On screen:** Download buttons, then scroll back to the summary.

## Before sending to Cami

- [ ] Open live demo in an incognito window and confirm it works without logging in.
- [ ] Confirm C-101 displays 10 → 5 before the scenario is changed.
- [ ] Confirm the dashboard shows 6 claims, 5 review required, 1 unchanged in its default state.
- [ ] Test that downloads work and the sample data are fictional.
- [ ] Upload the *actual screen recording* to YouTube as Unlisted.
- [ ] Test the YouTube video URL from a signed-out browser.
- [ ] Send both **live app** and **YouTube video** URLs in the same recruiter reply.
