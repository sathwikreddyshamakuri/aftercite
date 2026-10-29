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
