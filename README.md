# AfterCite — Detecting Outdated Evidence in AI-Generated Answers

**When a source document changes, can an AI-generated answer still be trusted?**

AfterCite is a lightweight Python prototype that checks previously saved AI-generated claims against updated source documents. It identifies citations that may no longer support the original answer and produces an explainable report for human review.

**[Try the live demo](https://aftercite-livedemo.streamlit.app/)** · [Quick start](#quick-start) · [How it works](#how-it-works) · [Run tests](#tests)

> **Scope:** AfterCite detects changes to cited evidence; it does not decide whether a claim is true or automatically rewrite an answer. All sample documents and policies are fictional.

## Why it matters

An AI assistant might answer a question correctly using a policy document today. If that policy changes next week, the saved answer can become outdated even though its citation still looks valid.

AfterCite helps surface those cases by comparing the **original source**, the **updated source**, and the **evidence quote saved with each claim**. It distinguishes changes to the quote itself from changes to its surrounding context—and from citations that were invalid from the start.

## Live demo

**[Launch the interactive AfterCite demo →](https://aftercite-livedemo.streamlit.app/)**

The Streamlit interface lets you:

- Review sample analysis results and the reasons claims were flagged.
- Compare original and updated source text side by side.
- Record reviewer decisions and notes during your browser session.

The interface uses the same core analysis functions as the command-line tool. Browser review notes are **session-only**, not stored in a shared audit log.

## Key capabilities

| Capability | What it does |
| --- | --- |
| Original citation validation | Checks whether the saved evidence quote appeared in the original section. |
| Document change detection | Identifies removed documents/sections and changes to source text. |
| Evidence and context checks | Distinguishes a missing/changed quote from changes around a still-present quote. |
| Numeric difference hints | Surfaces possible number changes for a reviewer to inspect. |
| Explainable reports | Writes structured JSON and a readable HTML review report. |
| Human review records | Saves CLI review decisions in an append-only JSONL file. |
| Automated tests | Includes 16 tests covering comparisons, invalid inputs, HTML escaping, and review logging. |

## How it works

```text
Saved claims + original document + updated document
                       |
                       v
             Validate original citation
                       |
                       v
            Check source/section existence
                       |
                       v
        Compare quoted evidence and context
                       |
                       v
          Flag claims that need human review
                       |
                       v
               JSON + HTML reports
```

The analysis follows these rules:

1. Confirm that the saved quote appeared in the original section. If not, flag the **original citation as invalid**.
2. Check whether the cited document or section was removed.
3. Compare old and new section text, ignoring case and whitespace differences.
4. If the section changed, determine whether the quote disappeared or remained while its surrounding context changed.
5. Include possible numeric differences as **review hints**, not conclusions.

**Important:** An unchanged section only means its text did not change under this comparison. It does *not* prove that the saved claim is correct.

## Quick start

### Prerequisites

- Python **3.10+**
- No API keys or online accounts
- No third-party dependencies for the command-line tool

From the repository folder, run:

```bash
python aftercite.py analyze
```

Expected summary:

```text
AfterCite: 6 claims | 5 review required | 1 unchanged
```

The command generates:

- `output/report.json` — machine-readable results
- `output/report.html` — a human-readable report with claim explanations and old/new evidence

Open `output/report.html` in your browser to explore the results. The HTML file is a presentation of the analysis, not the comparison engine itself.

## Example scenarios

The included fictional sample data demonstrates several important outcomes:

| Claim | Scenario | Why it matters |
| --- | --- | --- |
| **C-101** | A deadline changes from **10 business days to 5**, while the saved claim still says 10. | Previously cited evidence may be outdated. |
| **C-104** | The evidence quote remains, but the surrounding section changes. | Context can change without the quote disappearing. |
| **C-106** | The quote was already incorrect in the original document. | An invalid original citation should not be mistaken for a new update. |
| **C-103** | The source section remains unchanged. | No detected text change is **not** proof of factual correctness. |

## Record a review decision

The CLI supports recording a human review decision:

```bash
python aftercite.py review --claim C-101 --decision needs_followup --reviewer demo --note "Update the saved answer"
python aftercite.py analyze
```

Decisions are appended to `output/reviews.jsonl`, and the latest recorded decision appears in the regenerated HTML report. The reviewer name `demo` is only an example; this log is **not** a secure production audit system.

## Run the browser interface locally

The interactive interface requires Streamlit:

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Or use the hosted version: **[aftercite-livedemo.streamlit.app](https://aftercite-livedemo.streamlit.app/)**.

## Use your own data

Run the analyzer with your own structured JSON files:

```bash
python aftercite.py analyze --old path/to/old.json --new path/to/new.json --claims path/to/claims.json --output path/to/results
```

The example input files are:

- `sample_data/before.json` — original document version
- `sample_data/after.json` — updated document version
- `sample_data/claims.json` — saved claims with document IDs, section IDs, and verbatim evidence quotes

**Input assumption:** Documents and sections already have stable IDs. AfterCite does not extract text from PDFs or automatically map sections between versions. The sample JSON files show the expected input shape.

### Input validation

To see how the CLI handles a missing input file:

```bash
python aftercite.py analyze --old missing.json
```

Expected behavior: a readable file-not-found error and exit code **2**, rather than silently proceeding.

## Tests

Run the full test suite:

```bash
python -m unittest discover -s tests -v
```

The project includes **16 automated tests** covering comparison outcomes, malformed and duplicate inputs, HTML escaping, and the end-to-end review log.

## Project structure

```text
aftercite.py              Core comparison logic and command-line interface
streamlit_app.py          Interactive Streamlit browser interface
requirements.txt          Browser interface dependencies
sample_data/              Fictional before/after documents and saved claims
tests/test_aftercite.py   Automated tests
output/report.json        Generated machine-readable results (after running)
output/report.html        Generated review report (after running)
output/reviews.jsonl      CLI review decisions (after recording a decision)
case_study.pdf            Problem definition and design reasoning
README.md                 Project documentation
```

## Design decisions and limitations

AfterCite is deliberately conservative and keeps the reviewer in control:

- **Transparent comparison:** The core analysis is deterministic and uses only the Python standard library; it does not call an LLM.
- **Review, not automatic correction:** Changes are flagged for human judgment rather than treated as proof that the claim is false.
- **Potential false positives:** Harmless wording changes can trigger a flag.
- **Limited semantic understanding:** The tool may miss incorrect claims in unchanged text.
- **Structured input requirement:** Stable section IDs must be provided upstream; PDF extraction and section matching are outside this prototype.
- **Demo storage:** The Streamlit interface keeps reviewer notes only for the current browser session. The CLI writes a local JSONL review log, not a production-grade audit trail.

Before expanding the system, the next engineering step would be to evaluate review usefulness and false-positive rates against more diverse real-world document changes.

## Technology

**Python 3.10+ · Python standard library · Streamlit · JSON · HTML · `unittest`**

The same comparison functions power both the CLI and the browser demo, keeping the analysis separate from how results are displayed.

## Project context

AfterCite was developed as an independent AI engineering case-study prototype focused on the reliability of saved, cited AI-generated answers when underlying documents change.

All sample data is synthetic. No employer code or customer information was included. The fictional policies are **not tax or legal guidance**. AI assistance was used during development and is disclosed in `case_study.pdf`.

---

**[Explore the live demo](https://aftercite-livedemo.streamlit.app/)**