import hashlib
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

    def test_cannot_score_without_image(self):
        self.review.update({'status':'REVIEWED', 'generation_performed':True,'case_id':'MOR-01','arm':'skill'})
        with self.assertRaisesRegex(ValueError, 'real image'):
            validate_review(self.review, self.suite)

    def test_valid_review_is_recorded_not_certified(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'candidate.png'
            def chunk(tag, data):
                return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
            ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
            idat = zlib.compress(b'\x00\x00\x00\x00')
            path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b''))
            self.review.update({'status':'REVIEWED','case_id':'MOR-01','arm':'skill', 'generation_performed':True,
                                'output_image_path':str(path), 'output_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            self.review['reviewer'] = {'kind':'human','id':'test-reviewer','inspected_original':True,'inspected_output':True}
            self.review['hard_gates'] = {'single_painting':True,'subject_class':True,'time_and_weather':True}
            self.review['scores'] = {'brushwork':7.5,'color':7.0,'atmosphere':8.5,'artifact_control':8.0}
            self.review['evidence_by_dimension'] = {k:'mock evidence for local unit tests' for k in self.review['scores']}
            result = validate_review(self.review, self.suite)
            self.assertEqual(result['status'], 'REVIEW_RECORDED_NOT_CERTIFIED')
            self.assertEqual(result['weighted_score'],7.7)


if __name__ == '__main__':
    unittest.main()
