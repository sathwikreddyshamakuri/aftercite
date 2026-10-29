"""Run from project root: python -m unittest discover -s tests -v"""
import json
import tempfile
import unittest
from pathlib import Path

from aftercite import DataError, analyze, examine, load_reviews, normalize, numeric_signals, read_claims, read_sources, render_html, main


OLD = {'doc': {'title': 'Manual', 'sections': {'policy': 'Approval is required above $800. Owners are named.'}}}
NEW = {'doc': {'title': 'Manual', 'sections': {'policy': 'Approval is required above $650. Owners are named.'}}}


def claim(**overrides):
    result = {'id': 'C-1', 'claim': 'Approval is required above $800.', 'document_id': 'doc',
              'section_id': 'policy', 'evidence_quote': 'Approval is required above $800.'}
    result.update(overrides)
    return result


class AnalysisTests(unittest.TestCase):
    def test_changed_anchor_flags_review(self):
        item = examine(claim(), OLD, NEW)
        self.assertEqual(item['status'], 'EVIDENCE_CHANGED')
        self.assertTrue(item['needs_review'])
        self.assertEqual(item['numeric_signals']['removed'], ['$800'])
        self.assertEqual(item['numeric_signals']['added'], ['$650'])

    def test_unchanged_citation_does_not_claim_semantic_verification(self):
        item = examine(claim(), OLD, OLD)
        self.assertEqual(item['status'], 'UNCHANGED')
        self.assertFalse(item['needs_review'])
        self.assertIn('not semantically', item['reason'])

    def test_changed_context_same_quote_flags_review(self):
        newer = {'doc': {'title': 'Manual', 'sections': {'policy': OLD['doc']['sections']['policy'] + ' Escalate if risk flagged.'}}}
        item = examine(claim(), OLD, newer)
        self.assertEqual(item['status'], 'CONTEXT_CHANGED')

    def test_missing_section(self):
        item = examine(claim(), OLD, {'doc': {'title': 'Manual', 'sections': {}}})
        self.assertEqual(item['status'], 'SECTION_REMOVED')

    def test_missing_document(self):
        item = examine(claim(), OLD, {})
        self.assertEqual(item['status'], 'SOURCE_REMOVED')

    def test_bad_original_citation(self):
        item = examine(claim(evidence_quote='No manager is needed.'), OLD, NEW)
        self.assertEqual(item['status'], 'BROKEN_BASELINE')

    def test_missing_original_source(self):
        item = examine(claim(document_id='does-not-exist'), OLD, NEW)
        self.assertEqual(item['status'], 'BROKEN_BASELINE')

    def test_whitespace_and_case_are_normalized(self):
        self.assertEqual(normalize(' The  ANSWER\nIs Here '), 'the answer is here')
        newer = {'doc': {'title': 'Manual', 'sections': {'policy': 'approval is required above $800.\n owners are named.'}}}
        self.assertEqual(examine(claim(), OLD, newer)['status'], 'UNCHANGED')

    def test_numeric_hints_are_not_decisions(self):
        self.assertEqual(numeric_signals('Up to 30 days and $800', 'Up to 21 days and $650'),
                         {'removed': ['$800', '30 days'], 'added': ['$650', '21 days']})

    def test_summary_counts(self):
        r = analyze(OLD, NEW, [claim(), claim(id='C-2', evidence_quote='Owners are named.')])
        self.assertEqual(r['summary']['review_required'], 2)
        self.assertEqual(r['summary']['total'], 2)

    def test_html_escapes_document_and_claim_values(self):
        suspicious = '<img src=x onerror=alert(1)>'
        p = claim(claim=suspicious)
        html_text = render_html(analyze(OLD, NEW, [p]), {})
        self.assertNotIn(suspicious, html_text)
        self.assertIn('&lt;img', html_text)
        self.assertIn('<table>', html_text)
        self.assertNotIn('<script', html_text)


class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def put(self, name, data):
        path = self.base / name
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def test_reject_duplicate_claim_ids(self):
        path = self.put('claims.json', {'claims': [claim(), claim()]})
        with self.assertRaisesRegex(DataError, 'duplicate claim id'):
            read_claims(path)

    def test_reject_duplicate_documents(self):
        path = self.put('docs.json', {'documents': [{'id': 'd', 'title': 'A', 'sections': {}},
                                                    {'id': 'd', 'title': 'B', 'sections': {}}]})
        with self.assertRaisesRegex(DataError, 'duplicate document id'):
            read_sources(path)

    def test_reject_malformed_json_without_traceback(self):
        bad = self.base / 'bad.json'
        bad.write_text('bad-json', encoding='utf-8')
        self.assertEqual(main(['analyze', '--old', str(bad), '--new', str(bad), '--claims', str(bad)]), 2)

    def test_end_to_end_outputs_files_and_review_audit(self):
        old = self.put('old.json', {'documents': [{'id': 'doc', 'title': 'Manual', 'sections': OLD['doc']['sections']}]})
        new = self.put('new.json', {'documents': [{'id': 'doc', 'title': 'Manual', 'sections': NEW['doc']['sections']}]})
        claims = self.put('claims.json', {'claims': [claim()]})
        out = self.base / 'out'
        reviews = out / 'reviews.jsonl'
        self.assertEqual(main(['analyze', '--old', str(old), '--new', str(new), '--claims', str(claims),
                               '--output', str(out), '--reviews', str(reviews)]), 0)
        self.assertTrue((out / 'report.html').exists())
        self.assertEqual(json.loads((out / 'report.json').read_text())['summary']['review_required'], 1)
        self.assertEqual(main(['review', '--claim', 'C-1', '--decision', 'needs_followup',
                               '--reviewer', 'test', '--note', 'Escalate to owner',
                               '--report', str(out / 'report.json'), '--reviews', str(reviews)]), 0)
        self.assertEqual(load_reviews(reviews)['C-1']['decision'], 'needs_followup')
        self.assertEqual(main(['analyze', '--old', str(old), '--new', str(new), '--claims', str(claims),
                               '--output', str(out), '--reviews', str(reviews)]), 0)
        self.assertIn('Escalate to owner', (out / 'report.html').read_text())

    def test_unknown_review_id_is_rejected(self):
        report = self.put('report.json', {'claims': [claim()]})
        self.assertEqual(main(['review', '--claim', 'nonexistent', '--decision', 'needs_followup',
                               '--reviewer', 'test', '--report', str(report),
                               '--reviews', str(self.base / 'reviews.jsonl')]), 2)


if __name__ == '__main__':
    unittest.main()
