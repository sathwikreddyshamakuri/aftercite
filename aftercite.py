"""AfterCite: evidence-change review for already published, source-grounded claims.

Python standard library only. This tool identifies potentially stale citations;
it does not assess semantic correctness or give tax advice.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import difflib
import html
import json
from pathlib import Path
import re
import sys
from typing import Any

STATUS_ORDER = {
    'BROKEN_BASELINE': 0, 'SOURCE_REMOVED': 1, 'SECTION_REMOVED': 2,
    'EVIDENCE_CHANGED': 3, 'CONTEXT_CHANGED': 4, 'UNCHANGED': 5,
}
STATUS_LABELS = {
    'BROKEN_BASELINE': 'Invalid original citation',
    'SOURCE_REMOVED': 'Source deleted',
    'SECTION_REMOVED': 'Section removed',
    'EVIDENCE_CHANGED': 'Cited evidence changed',
    'CONTEXT_CHANGED': 'Citation intact, context changed',
    'UNCHANGED': 'Citation and section unchanged',
}
REVIEW_STATUSES = set(STATUS_ORDER) - {'UNCHANGED'}
NUMERIC = re.compile(r'\$\s?\d[\d,]*(?:\.\d+)?|\b\d+(?:\.\d+)?\s*(?:business days?|days?|weeks?|months?|years?|%)\b', re.I)


class DataError(ValueError):
    pass


def normalize(value: str) -> str:
    """Whitespace and case normalization only: intentionally no semantic inference."""
    return ' '.join(value.split()).casefold()


def require_str(record: dict[str, Any], key: str, context: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DataError(f'{context}: {key!r} must be a non-empty string')
    return value.strip()


def load_json(path: Path) -> Any:
    try:
        with path.open(encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise DataError(f'File not found: {path}') from exc
    except json.JSONDecodeError as exc:
        raise DataError(f'Invalid JSON in {path}: {exc.msg} (line {exc.lineno})') from exc


def read_sources(path: Path) -> dict[str, dict[str, Any]]:
    obj = load_json(path)
    if not isinstance(obj, dict) or not isinstance(obj.get('documents'), list):
        raise DataError(f'{path}: expected {{"documents": [...]}}')
    docs = {}
    for i, document in enumerate(obj['documents']):
        context = f'{path} document #{i + 1}'
        if not isinstance(document, dict):
            raise DataError(f'{context} must be an object')
        doc_id = require_str(document, 'id', context)
        title = require_str(document, 'title', context)
        sections = document.get('sections')
        if not isinstance(sections, dict):
            raise DataError(f'{context}: sections must be an object mapping identifiers to text')
        if doc_id in docs:
            raise DataError(f'{context}: duplicate document id {doc_id!r}')
        for key, value in sections.items():
            if not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not value.strip():
                raise DataError(f'{context}: section ids and text must be non-empty strings')
        docs[doc_id] = {'title': title, 'sections': sections}
    return docs


def read_claims(path: Path) -> list[dict[str, str]]:
    obj = load_json(path)
    if not isinstance(obj, dict) or not isinstance(obj.get('claims'), list):
        raise DataError(f'{path}: expected {{"claims": [...]}}')
    result = []
    seen = set()
    for i, claim in enumerate(obj['claims']):
        context = f'{path} claim #{i + 1}'
        if not isinstance(claim, dict):
            raise DataError(f'{context}: must be an object')
        c = {k: require_str(claim, k, context) for k in ('id', 'claim', 'document_id', 'section_id', 'evidence_quote')}
        if c['id'] in seen:
            raise DataError(f'{context}: duplicate claim id {c["id"]!r}')
        seen.add(c['id'])
        result.append(c)
    return result


def numeric_signals(before: str, after: str) -> dict[str, list[str]]:
    a = set(NUMERIC.findall(before))
    b = set(NUMERIC.findall(after))
    return {'removed': sorted(a - b), 'added': sorted(b - a)}


def examine(claim: dict[str, str], old: dict, new: dict) -> dict[str, Any]:
    doc_id, section_id = claim['document_id'], claim['section_id']
    prior_doc = old.get(doc_id)
    current_doc = new.get(doc_id)
    prior = prior_doc['sections'].get(section_id) if prior_doc else None
    current = current_doc['sections'].get(section_id) if current_doc else None
    anchor = normalize(claim['evidence_quote'])
    result: dict[str, Any] = {**claim, 'source_title': (prior_doc or current_doc or {}).get('title', doc_id),
                              'previous_section': prior, 'current_section': current,
                              'numeric_signals': numeric_signals(prior or '', current or '')}

    if not prior or not anchor or anchor not in normalize(prior):
        result.update(status='BROKEN_BASELINE', reason='The supplied original citation cannot be found in the old section. Check the claim and anchor before any comparison.')
    elif not current_doc:
        result.update(status='SOURCE_REMOVED', reason='The cited document no longer exists in the new source set.')
    elif current is None:
        result.update(status='SECTION_REMOVED', reason='The cited section was removed from the new document version.')
    elif normalize(prior) == normalize(current):
        result.update(status='UNCHANGED', reason='The cited section is textually unchanged; the claim was not semantically re-verified.')
    elif anchor not in normalize(current):
        result.update(status='EVIDENCE_CHANGED', reason='The original evidence quote no longer appears in the revised section. Human re-verification is required.')
    else:
        result.update(status='CONTEXT_CHANGED', reason='The quoted evidence still exists, but surrounding section text changed; review for qualifiers or exceptions.')
    result['needs_review'] = result['status'] in REVIEW_STATUSES
    return result


def analyze(old_docs: dict, new_docs: dict, claims: list[dict[str, str]]) -> dict[str, Any]:
    results = [examine(c, old_docs, new_docs) for c in claims]
    results.sort(key=lambda x: (STATUS_ORDER[x['status']], x['id']))
    summary = Counter(x['status'] for x in results)
    return {'app': 'AfterCite', 'schema_version': 1, 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'summary': {'total': len(results), 'review_required': sum(x['needs_review'] for x in results),
                        'unchanged': summary['UNCHANGED'], 'statuses': dict(summary)},
            'claims': results,
            'limitations': [
                'Text comparison is not semantic entailment. UNCHANGED only means the cited section text did not change.',
                'Changed headings/section IDs require a human to re-anchor citations.',
                'A citation that was inaccurate but textually unchanged may pass through as UNCHANGED.',
                'Numeric tokens are review hints, not a proof that a claim is wrong.',
            ]}


def load_reviews(path: Path) -> dict[str, dict[str, Any]]:
    reviews = {}
    if not path.exists():
        return reviews
    try:
        for line_no, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict) or not isinstance(item.get('claim_id'), str):
                raise DataError(f'Invalid review record on line {line_no} in {path}')
            reviews[item['claim_id']] = item
    except json.JSONDecodeError as exc:
        raise DataError(f'Malformed review log {path}: {exc}') from exc
    return reviews


def escape(value: Any) -> str:
    return html.escape(str(value or ''), quote=True)


def markup_diff(before: str, after: str, which: str) -> str:
    """Underline added text and strike through removed text in the HTML report."""
    a, b = before.split(), after.split()
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    rendered = []
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        values = a[a1:a2] if which == 'old' else b[b1:b2]
        if not values:
            continue
        chunk = escape(' '.join(values))
        changed = (which == 'old' and tag in ('replace', 'delete')) or (
            which == 'new' and tag in ('replace', 'insert'))
        if changed:
            chunk = f'<del>{chunk}</del>' if which == 'old' else f'<ins>{chunk}</ins>'
        rendered.append(chunk)
    return ' '.join(rendered) or '<em>(section not present)</em>'


def render_html(report: dict, reviews: dict[str, dict]) -> str:
    """Render a plain, offline report. No scripts or external assets."""
    summary = report['summary']
    rows = []
    for item in report['claims']:
        signals = item['numeric_signals']
        hints = ''
        if signals['removed'] or signals['added']:
            old_values = ', '.join(signals['removed']) or 'none'
            new_values = ', '.join(signals['added']) or 'none'
            hints = f'<p><b>Number changes (review hints):</b> {escape(old_values)} -> {escape(new_values)}</p>'
        previous = item['previous_section'] or ''
        current = item['current_section'] or ''
        review = reviews.get(item['id'])
        last_review = ''
        if review:
            last_review = (f'<p><b>Last recorded review:</b> {escape(review["decision"])} by '
                           f'{escape(review["reviewer"])}. Note: {escape(review.get("note", ""))}</p>')
        rows.append(f"""<section>
          <h2>{escape(item['id'])}. {escape(item['claim'])}</h2>
          <p><b>Status:</b> {escape(STATUS_LABELS[item['status']])}</p>
          <p><b>Source:</b> {escape(item['source_title'])} / {escape(item['section_id'])}</p>
          <p>{escape(item['reason'])}</p>{hints}
          <p><b>Saved evidence quote:</b> {escape(item['evidence_quote'])}</p>
          <table><thead><tr><th>Before</th><th>After</th></tr></thead>
          <tbody><tr><td>{markup_diff(previous,current,'old')}</td>
          <td>{markup_diff(previous,current,'new')}</td></tr></tbody></table>
          {last_review}
        </section>""")
    body = '\n'.join(rows) or '<p>No claims provided.</p>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Source change review</title>
<style>
body {{ margin: 36px auto; padding: 0 20px; max-width: 980px; font: 15px/1.55 Arial, sans-serif; color: #202020; background: white; }}
h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 4px; }}
h2 {{ font-size: 17px; margin: 0 0 8px; }}
p {{ margin: 6px 0 10px; }} .intro {{ margin-bottom: 28px; }}
section {{ padding: 16px 0 22px; border-top: 1px solid #bbb; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin: 10px 0; }}
th, td {{ width: 50%; padding: 10px; border: 1px solid #bbb; text-align: left; vertical-align: top; overflow-wrap: anywhere; }}
th {{ background: #f4f4f4; font-weight: bold; }}
del {{ text-decoration: line-through; }} ins {{ text-decoration: underline; }}
.note {{ font-size: 13px; }}
@media (max-width: 640px) {{ body {{ margin-top: 14px; }} th, td {{ padding: 6px; }} }}
</style></head><body>
<h1>Source change review</h1>
<p class="intro">{summary['total']} saved claims checked; {summary['review_required']} need review; {summary['unchanged']} unchanged source sections.</p>
{body}
<p class="note">The data in this example are fictional. Text changes are review signals, not proof that a claim is right or wrong.</p>
</body></html>"""


def cmd_analyze(args: argparse.Namespace) -> int:
    prior = read_sources(Path(args.old))
    current = read_sources(Path(args.new))
    claims = read_claims(Path(args.claims))
    report = analyze(prior, current, claims)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report_file = output / 'report.json'
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    rows = load_reviews(Path(args.reviews))
    html_file = output / 'report.html'
    html_file.write_text(render_html(report, rows), encoding='utf-8')
    print(f"AfterCite: {report['summary']['total']} claims | {report['summary']['review_required']} review required | {report['summary']['unchanged']} unchanged")
    for item in report['claims']:
        print(f"  {item['id']:5s} {item['status']:18s} {item['claim'][:70]}")
    print(f'Reports: {report_file} | {html_file}')
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    report = load_json(Path(args.report))
    if not isinstance(report, dict) or not isinstance(report.get('claims'), list):
        raise DataError('Run analyze first to generate a valid report.json')
    valid_ids = {x.get('id') for x in report['claims'] if isinstance(x, dict)}
    if args.claim not in valid_ids:
        raise DataError(f'Unknown claim {args.claim!r}; known claims: {", ".join(sorted(valid_ids))}')
    decision = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'claim_id': args.claim,
                'decision': args.decision, 'reviewer': args.reviewer, 'note': args.note}
    path = Path(args.reviews)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(decision, ensure_ascii=False) + '\n')
    print(f'Recorded reviewer action for {args.claim}; rerun analyze to refresh HTML.')
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='AfterCite: review which cited claims need attention after a source-document revision.')
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('analyze', help='Compare document versions against existing cited claims')
    check.add_argument('--old', default='sample_data/before.json', help='Original documents JSON')
    check.add_argument('--new', default='sample_data/after.json', help='Revised documents JSON')
    check.add_argument('--claims', default='sample_data/claims.json', help='Original claim/citation records JSON')
    check.add_argument('--output', default='output', help='Output directory for JSON and HTML reports')
    check.add_argument('--reviews', default='output/reviews.jsonl', help='Optional local reviewer-action log')
    check.set_defaults(run=cmd_analyze)
    rev = commands.add_parser('review', help='Record a human review decision in an append-only local log')
    rev.add_argument('--claim', required=True, help='ID of a claim from report.json')
    rev.add_argument('--decision', required=True, choices=['needs_followup', 'verified_updated', 'dismissed_with_reason'])
    rev.add_argument('--reviewer', required=True)
    rev.add_argument('--note', default='')
    rev.add_argument('--report', default='output/report.json')
    rev.add_argument('--reviews', default='output/reviews.jsonl')
    rev.set_defaults(run=cmd_review)
    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except (DataError, OSError) as exc:
        print(f'AfterCite input error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
