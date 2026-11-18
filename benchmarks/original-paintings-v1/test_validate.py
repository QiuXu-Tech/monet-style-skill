import hashlib
import copy
import json
import struct
import zlib
from pathlib import Path
import tempfile
import unittest

from validate import ROOT, read_json, validate_review, validate_suite


class BenchmarkChecks(unittest.TestCase):
    def setUp(self):
        self.suite = read_json(ROOT / 'cases.json')
        self.review = read_json(ROOT / 'review-template.json')

    def png(self, path, pixel):
        def chunk(tag, data):
            return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
        ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
        idat = zlib.compress(b'\x00' + bytes(pixel))
        path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b''))
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def completed_review(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / 'candidate.png'
        original = Path(temp.name) / 'original-fixture.png'
        review = copy.deepcopy(self.review)
        review.update({'status':'REVIEWED','case_id':'MOR-01','arm':'skill', 'generation_performed':True,
                       'output_image_path':str(path), 'output_sha256':self.png(path, (0, 0, 0))})
        case = self.suite['cases'][0]
        review['original_reference'].update({
            'institution_inventory': case['institution_inventory'], 'museum_url': case['museum_url'],
            'image_source_url': case['catalog_source_page'], 'image_path':str(original),
            'image_sha256':self.png(original, (255, 255, 255))})
        review['reviewer'] = {'kind':'human','id':'unit-test-reviewer','inspected_original':True,'inspected_output':True}
        review['hard_gates'] = dict.fromkeys(('single_painting', 'subject_class', 'time_and_weather', 'reference_leakage'), True)
        review['reference_leakage_review'] = {
            name: {'result': 'pass', 'evidence': 'Mock localized evidence for schema tests only.'}
            for name in ('signature', 'distinctive_composition')}
        review['scores'] = {'brushwork':7.5,'color':7.0,'atmosphere':8.5,'artifact_control':8.0}
        review['evidence_by_dimension'] = {k:'Mock evidence for local schema tests, not an artwork score.' for k in review['scores']}
        return review

    def test_three_paintings_have_sources_and_dates(self):
        validate_suite(self.suite)
        self.assertEqual([c['creation_year'] for c in self.suite['cases']], ['1872', '1875', '1890–1891'])

    def test_empty_review_does_not_produce_score(self):
        self.assertIsNone(validate_review(self.review, self.suite)['weighted_score'])

    def test_unrun_with_score_is_rejected(self):
        self.review['scores']['brushwork'] = 9
        with self.assertRaisesRegex(ValueError, 'NOT_RUN'):
            validate_review(self.review, self.suite)

    def test_original_as_generation_input_is_disallowed(self):
        self.suite['reference_policy']['target_original_as_generation_input'] = True
        with self.assertRaisesRegex(ValueError, 'evaluation-only'):
            validate_suite(self.suite)

    def test_user_defined_weights_cannot_silently_change(self):
        self.suite['weights'] = dict.fromkeys(self.suite['weights'], 0.25)
        with self.assertRaisesRegex(ValueError, '30/30/30/10'):
            validate_suite(self.suite)

    def test_cannot_score_without_image(self):
        self.review.update({'status':'REVIEWED', 'generation_performed':True,'case_id':'MOR-01','arm':'skill'})
        with self.assertRaisesRegex(ValueError, 'real image'):
            validate_review(self.review, self.suite)

    def test_valid_review_is_recorded_not_certified(self):
        result = validate_review(self.completed_review(), self.suite)
        self.assertEqual(result['status'], 'REVIEW_RECORDED_NOT_CERTIFIED')
        self.assertEqual(result['weighted_score'],7.7)
        self.assertEqual(result['protocol_version'], '1.1.0')
        self.assertFalse(result['legacy_protocol'])

    def test_original_provenance_binds_to_actual_file_and_case(self):
        for field, value, message in (
                ('image_sha256', '0' * 64, 'Original hash'),
                ('institution_inventory', 'wrong-artwork', 'Original identity'),
                ('museum_url', 'https://example.com/not-this-museum', 'Original identity'),
                ('image_source_url', None, 'source URL')):
            with self.subTest(field=field):
                review = self.completed_review()
                review['original_reference'][field] = value
                with self.assertRaisesRegex(ValueError, message):
                    validate_review(review, self.suite)

    def test_original_is_definition_anchor_not_sample(self):
        review = self.completed_review()
        review['original_reference']['definition_scores']['brushwork'] = 8
        with self.assertRaisesRegex(ValueError, '10-point definition'):
            validate_review(review, self.suite)
        review = self.completed_review()
        review['output_image_path'] = review['original_reference']['image_path']
        review['output_sha256'] = review['original_reference']['image_sha256']
        with self.assertRaisesRegex(ValueError, 'cannot be submitted'):
            validate_review(review, self.suite)

    def test_unknown_and_failed_gates_have_no_scores(self):
        for value, status in ((None, 'NEEDS_REVIEW'), (False, 'REJECTED')):
            with self.subTest(value=value):
                review = self.completed_review()
                review['hard_gates']['time_and_weather'] = value
                with self.assertRaisesRegex(ValueError, 'null style scores'):
                    validate_review(review, self.suite)
                review['scores'] = dict.fromkeys(review['scores'])
                result = validate_review(review, self.suite)
                self.assertEqual(result['status'], status)
                self.assertIsNone(result['weighted_score'])

    def test_signature_or_composition_failure_cannot_be_offset(self):
        for name in ('signature', 'distinctive_composition'):
            with self.subTest(check=name):
                review = self.completed_review()
                review['reference_leakage_review'][name]['result'] = 'fail'
                review['hard_gates']['reference_leakage'] = False
                review['scores'] = dict.fromkeys(review['scores'])
                result = validate_review(review, self.suite)
                self.assertEqual(result['status'], 'REJECTED')
                self.assertIsNone(result['weighted_score'])

    def test_uninspected_signature_cannot_be_marked_pass(self):
        review = self.completed_review()
        review['reference_leakage_review']['signature'] = {'result': 'unknown', 'evidence': None}
        with self.assertRaisesRegex(ValueError, 'must agree'):
            validate_review(review, self.suite)
        review['hard_gates']['reference_leakage'] = None
        review['scores'] = dict.fromkeys(review['scores'])
        self.assertEqual(validate_review(review, self.suite)['status'], 'NEEDS_REVIEW')

    def test_actual_inspection_and_local_evidence_are_required(self):
        review = self.completed_review()
        review['reviewer']['inspected_original'] = False
        with self.assertRaisesRegex(ValueError, 'actual inspection'):
            validate_review(review, self.suite)
        review = self.completed_review()
        review['reference_leakage_review']['signature']['evidence'] = ''
        with self.assertRaisesRegex(ValueError, 'localized evidence'):
            validate_review(review, self.suite)

    def test_human_and_model_identity_are_preserved(self):
        for kind in ('human', 'model'):
            review = self.completed_review()
            review['reviewer']['kind'] = kind
            self.assertEqual(validate_review(review, self.suite)['reviewer_kind'], kind)

    def test_numeric_values_cannot_impersonate_boolean_gate(self):
        review = self.completed_review()
        review['hard_gates']['single_painting'] = 1
        with self.assertRaisesRegex(ValueError, 'Invalid content'):
            validate_review(review, self.suite)

    def test_historical_protocol_is_readable_but_not_relabelled(self):
        review = self.completed_review()
        review['protocol_version'] = '1.0.0'
        del review['hard_gates']['reference_leakage']
        del review['original_reference']
        del review['reference_leakage_review']
        result = validate_review(review, self.suite)
        self.assertEqual(result['weighted_score'], 7.7)
        self.assertTrue(result['legacy_protocol'])
        self.assertIn('not verified under 1.1.0', result['note'])

    def test_unrun_cannot_claim_output_metadata(self):
        self.review['output_sha256'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'NOT_RUN'):
            validate_review(self.review, self.suite)


if __name__ == '__main__':
    unittest.main()
