# Checking cited answers after a document update

This is a small Python prototype for a specific case: an AI-generated answer has already been saved with a citation, but the source document is later revised. The program checks whether that evidence has changed and creates a list of claims for a person to review.

It does not judge whether a claim is true or automatically change an answer. The sample policies are fictional, not tax guidance.

## Requirements

- Python 3.10 or newer
- No packages to install; only the Python standard library is used
- No API keys or online accounts

## Run the example

From the folder containing `aftercite.py`:

```bash
python aftercite.py analyze
```

You should see this summary:

```text
AfterCite: 6 claims | 5 review required | 1 unchanged
```

The command writes `output/report.json` and `output/report.html`. Open the HTML file in a browser to see each claim, why it was flagged, and the previous and current source text. The HTML is a report, not the implementation of the comparison logic.

A few useful examples in the included data:

- **C-101:** the upload deadline changes from 10 business days to 5, but the saved claim still says 10.
- **C-104:** the quoted sentence stays the same, but its surrounding section changes.
- **C-106:** the citation was already invalid in the original document. This is classified separately from a new change.
- **C-103:** the source section has not changed. That does not prove the claim is correct.

## Record a review decision

For example:

```bash
python aftercite.py review --claim C-101 --decision needs_followup --reviewer demo --note "Update the saved answer"
python aftercite.py analyze
```

A decision is appended to `output/reviews.jsonl`, and the latest one appears in the regenerated HTML report. For the example, `demo` is a placeholder reviewer name. The log is not a secure production audit system.

## Try an invalid input

The program also checks input files rather than silently continuing with bad data:

```bash
python aftercite.py analyze --old missing.json
```

Expected behavior: a readable file-not-found error and exit code 2. Another difficult case is C-106 in the normal sample, which has an incorrect original evidence quote.

## Use your own data

```bash
python aftercite.py analyze --old path/to/old.json --new path/to/new.json --claims path/to/claims.json --output path/to/results
```

The input files are:

- `sample_data/before.json` - original document version
- `sample_data/after.json` - revised version
- `sample_data/claims.json` - saved claims, each tied to a document ID, section ID, and verbatim evidence quote

Documents and sections must already have stable IDs. The prototype does not extract them from PDFs. You can inspect the sample JSON files for the expected format.

## Tests

```bash
python -m unittest discover -s tests -v
```

There are 16 tests for the comparison outcomes, malformed and duplicate inputs, HTML escaping, and the end-to-end review log.

## What the comparison does

1. Check that the quote appeared in the original section. Otherwise flag the original citation as invalid.
2. Check whether the source document or section was removed.
3. Compare the original and updated section text, ignoring case and whitespace differences.
4. If the section is unchanged, report that its **text** is unchanged. If the quote disappeared, flag changed evidence. If the quote remains but the rest of the section changes, flag changed context.
5. Report possible numeric differences as hints; leave interpretation and the final decision to a reviewer.

This is intentionally conservative. It will flag harmless wording changes and it may miss semantic errors that were already present in unchanged text. It also depends on upstream section IDs. I would validate review usefulness and false positives before building any larger system.

## Files

```text
aftercite.py               Comparison logic and CLI
sample_data/               Fictional source versions and claims
tests/test_aftercite.py    Automated tests
output/report.json         Generated machine-readable result (after running)
output/report.html         Generated report for a reviewer (after running)
case_study.pdf             Written problem choice and design reasoning
README.md                  This file
```

All sample data are synthetic. No employer code or customer information was included. AI assistance was used to develop this exercise and is disclosed in the written case study.


## Live browser demo (Streamlit)

The browser interface is in `streamlit_app.py`; the original `aftercite.py` CLI and the existing tests remain unchanged.

### Run the browser demo locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Streamlit opens a local URL (typically `http://localhost:8501`). The app loads the included fictional sample data, runs the same `read_sources`, `read_claims`, and `analyze` functions as the CLI, and displays reviewable results.

### Deploy with Streamlit Community Cloud

1. Open https://share.streamlit.io and sign in with GitHub.
2. Choose **Create app** and **Deploy a public app from GitHub**.
3. Select repository `sathwikreddyshamakuri/aftercite`, branch `main`, and entrypoint `streamlit_app.py`.
4. Deploy and wait for Streamlit to show a running app, then open the URL in a private/incognito browser window to confirm public access.
5. Share **the resulting live Streamlit URL**, not the GitHub source URL, with the reviewer.

The repository includes `requirements.txt`. No credentials, secrets, or paid external APIs are required for the demo.

### Quick demo walkthrough (2–3 minutes)

1. **Problem (0:00–0:25):** An AI-generated claim can become stale when its cited policy is updated; the answer may still look credible.
2. **Results (0:25–0:50):** Open the app, show 6 saved claims, with 5 flagged for review and 1 unchanged.
3. **Evidence (0:50–1:35):** Choose **C-101**. The original policy says **10 business days**; the revised policy says **5 business days**. Show the highlighted evidence change and review reason.
4. **Scenario (1:35–2:00):** In the sidebar select **7 business days**, then click **Analyze changes**. Reopen C-101 and show the updated comparison.
5. **Human review (2:00–2:25):** Enter a reviewer label, choose **Needs follow-up**, add a brief note, and record it. Explain this review is session-only in the public demo.
6. **Exports & limitations (2:25–2:50):** Download JSON/HTML, then explain this is conservative text-based change detection, **not** automatic tax-law validation.

Record your real browser as you interact with the deployed application. Upload the actual screen recording to YouTube as **Unlisted** and test the viewer URL in a private browser window. Don't upload invented footage or claim that an unrecorded demo is live.

### Hosting and privacy notes

- All sample content is fictional; the app does not accept customer uploads.
- The app does not persist review actions across visits or server restarts. Review notes exist only in the visitor's Streamlit session.
- The existing command-line review log is a *separate local mechanism*, not a secure centralized audit record.
- A changed quote or context warrants review; unchanged source text does not prove a claim is correct.
