"""Offline contract tests, not image-generation or aesthetic tests."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'monet-style'
spec = importlib.util.spec_from_file_location('monet', SKILL / 'scripts' / 'monet.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def png(width=48, height=32):
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress((b'\0' + b'\x80\x90\xa0' * width) * height)) + chunk(b'IEND', b'')


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.request = {'request': '恰好三只杯子：一红两白。', 'must_keep': ['恰好三只杯子', '一红两白'], 'must_avoid': ['人物'], 'aspect_ratio': '3:2'}

    def plan(self, request=None, text_only=True):
        return m.prepare(request or self.request, self.base, self.base / 'cache', self.base / 'prepared', text_only=text_only)

    def assessment(self, job, path):
        data = m.review_template(job)
        data.update({'image_sha256': m.file_sha(path), 'reviewer': 'unit-test-stub', 'reviewer_kind': 'model', 'inspected_image': True, 'tool_name': 'TEST_ONLY', 'call_id': 'stub-call', 'attempt': 1})
        for check in data['checks']:
            check.update({'result': 'pass', 'evidence': 'Synthetic test assertion; not visual evaluation.'})
        return data

    def test_01_literal_request_retained(self):
        job = self.plan()
        self.assertEqual(job['request']['request'], self.request['request'])
        self.assertIn(self.request['request'], job['prompt'])

    def test_02_same_input_same_job(self):
        self.assertEqual(self.plan(), self.plan())

    def test_03_text_only_is_not_ready_for_generation(self):
        self.assertEqual(self.plan()['state'], 'PROMPT_ONLY')
        self.assertEqual(self.plan()['references'], [])

    def test_04_reference_required(self):
        with self.assertRaisesRegex(ValueError, 'fetch'):
            self.plan(text_only=False)

    def test_05_empty_request_rejected(self):
        with self.assertRaises(ValueError):
            self.plan({'request': '   '})

    def test_06_unknown_keys_rejected(self):
        with self.assertRaises(ValueError):
            self.plan(dict(self.request, mystery='ignored?'))

    def test_07_invalid_ratio_rejected(self):
        for ratio in ['16:0', 'banana', '0:1', '100:1']:
            with self.subTest(ratio=ratio), self.assertRaises(ValueError):
                self.plan(dict(self.request, aspect_ratio=ratio))

    def test_08_constraints_must_be_list(self):
        with self.assertRaises(ValueError):
            self.plan(dict(self.request, must_keep='three cups'))

    def test_09_restyle_requires_content_image(self):
        with self.assertRaises(ValueError):
            self.plan(dict(self.request, mode='restyle'))

    def test_10_missing_content_image_rejected(self):
        with self.assertRaises(ValueError):
            self.plan(dict(self.request, mode='restyle', content_image='missing.png'))

    def test_11_source_path_relative_to_request(self):
        path = self.base / 'source.png'
        path.write_bytes(png())
        job = self.plan(dict(self.request, mode='restyle', content_image='source.png'))
        self.assertEqual(job['content_reference']['sha256'], m.file_sha(path))
        self.assertEqual(job['content_reference']['role'], 'content-and-composition')

    def test_12_empty_review_cannot_pass(self):
        job = self.plan()
        path = self.base / 'result.png'
        path.write_bytes(png())
        review = m.review_template(job)
        review['image_sha256'] = m.file_sha(path)
        self.assertEqual(m.evaluate(job, path, review)['state'], 'NEEDS_REVIEW')

    def test_13_passing_text_only_job_remains_preview(self):
        job = self.plan()
        path = self.base / 'result.png'
        path.write_bytes(png())
        self.assertEqual(m.evaluate(job, path, self.assessment(job, path))['state'], 'PROMPT_ONLY_OUTPUT')

    def test_14_different_image_hash_rejected(self):
        job = self.plan()
        path = self.base / 'result.png'
        path.write_bytes(png())
        review = self.assessment(job, path)
        review['image_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            m.evaluate(job, path, review)

    def test_15_different_job_rejected(self):
        job = self.plan()
        path = self.base / 'result.png'
        path.write_bytes(png())
        review = self.assessment(job, path)
        review['job_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            m.evaluate(job, path, review)

    def test_16_missing_requirement_rejected(self):
        job = self.plan()
        path = self.base / 'result.png'
        path.write_bytes(png())
        review = self.assessment(job, path)
        review['checks'].pop()
        with self.assertRaises(ValueError):
            m.evaluate(job, path, review)

    def test_17_failed_requirement_blocks_acceptance(self):
        job = self.plan()
        path = self.base / 'result.png'
        path.write_bytes(png())
        review = self.assessment(job, path)
        review['checks'][0]['result'] = 'fail'
        self.assertEqual(m.evaluate(job, path, review)['state'], 'REJECTED')

    def test_18_empty_pass_evidence_rejected(self):
        job = self.plan()
        path = self.base / 'result.png'
        path.write_bytes(png())
        review = self.assessment(job, path)
        review['checks'][0]['evidence'] = ''
        with self.assertRaises(ValueError):
            m.evaluate(job, path, review)

    def test_19_aspect_mismatch_fails(self):
        job = self.plan()
        path = self.base / 'result.png'
        path.write_bytes(png(32, 32))
        self.assertEqual(m.evaluate(job, path, self.assessment(job, path))['state'], 'REJECTED')

    def test_20_text_file_not_image(self):
        path = self.base / 'result.png'
        path.write_text('pretend image')
        with self.assertRaises(ValueError):
            m.image_info(path)

    def test_21_style_lock_detects_anchor_change(self):
        job = self.plan()
        changed = dict(job['style_lock'], anchor_id='pourville-1882')
        with self.assertRaises(ValueError):
            m.check_lock(job, changed)

    def test_22_style_lock_survives_content_change(self):
        a = self.plan()
        b = self.plan(dict(self.request, request='画一列高铁。'))
        m.check_lock(b, a['style_lock'])

    def test_23_no_unannounced_network_in_prepare(self):
        with patch.object(m.urllib.request, 'urlopen', side_effect=AssertionError('network')):
            self.plan()

    def test_24_do_not_overwrite_runs(self):
        output = self.base / 'run'
        output.mkdir()
        m.write_run(self.plan(), output)
        with self.assertRaises(FileExistsError):
            m.write_run(self.plan(), output)

    def test_25_integrity_check(self):
        m.check_package()

    def test_26_unknown_anchor_rejected(self):
        with self.assertRaises(ValueError):
            self.plan(dict(self.request, anchor_id='made-up'))

    def test_27_truncated_png_rejected(self):
        path = self.base / 'bad.png'
        path.write_bytes(png()[:-12])
        with self.assertRaises(ValueError):
            m.image_info(path)

    def test_28_reference_hash_check(self):
        cache = self.base / 'cache'
        cache.mkdir()
        anchor = m.anchor_record('antibes-1888')
        (cache / anchor['filename']).write_bytes(png())
        with self.assertRaises(ValueError):
            self.plan(text_only=False)

    def test_29_literal_template_text_not_executed(self):
        job = self.plan(dict(self.request, request='${shell} {{STYLE}} \n【内容】'))
        self.assertIn('${shell} {{STYLE}}', job['prompt'])

    def test_30_duplicate_check_ids_rejected(self):
        job = self.plan()
        path = self.base / 'result.png'
        path.write_bytes(png())
        review = self.assessment(job, path)
        review['checks'].append(copy.deepcopy(review['checks'][0]))
        with self.assertRaises(ValueError):
            m.evaluate(job, path, review)


    def test_31_verified_reference_is_ready(self):
        path = self.base / 'cache' / 'cma-1916-1044.jpg'
        path.parent.mkdir()
        path.write_bytes(png())
        record = dict(m.anchor_record('antibes-1888'), sha256=m.file_sha(path))
        with patch.object(m, 'anchor_record', return_value=record):
            job = self.plan(text_only=False)
        self.assertEqual(job['state'], 'READY_FOR_HOST')
        self.assertEqual(job['references'][0]['role'], 'style-only')
        output = self.base / 'candidate.png'
        output.write_bytes(png(96, 64))
        report = m.evaluate(job, output, self.assessment(job, output))
        self.assertEqual(report['state'], 'ACCEPTED_REPORTED')

    def test_32_museum_reference_cannot_be_submitted_as_output(self):
        path = self.base / 'cache' / 'cma-1916-1044.jpg'
        path.parent.mkdir()
        path.write_bytes(png())
        record = dict(m.anchor_record('antibes-1888'), sha256=m.file_sha(path))
        with patch.object(m, 'anchor_record', return_value=record):
            job = self.plan(text_only=False)
        report = m.evaluate(job, path, self.assessment(job, path))
        self.assertEqual(report['state'], 'REJECTED')
        self.assertTrue(report['identical_to_input'])

    def test_33_local_source_path_not_in_prompt(self):
        path = self.base / 'private-photo.png'
        path.write_bytes(png())
        job = self.plan(dict(self.request, mode='restyle', content_image=str(path)))
        self.assertNotIn(str(path), job['prompt'])
        self.assertIn(str(path), job['content_reference']['path'])

    def test_34_unknown_reviews_stay_pending(self):
        job = self.plan()
        path = self.base / 'result.png'
        path.write_bytes(png())
        review = self.assessment(job, path)
        review['checks'][0]['result'] = 'unknown'
        self.assertEqual(m.evaluate(job, path, review)['state'], 'NEEDS_REVIEW')

    def test_35_changed_job_invalidates_review(self):
        job = self.plan()
        path = self.base / 'result.png'
        path.write_bytes(png())
        review = self.assessment(job, path)
        job['prompt'] += ' alteration'
        with self.assertRaises(ValueError):
            m.evaluate(job, path, review)

    def test_36_examples_prepare(self):
        for path in sorted((SKILL / 'examples').glob('*.json')):
            with self.subTest(path=path.name):
                request = m.load(path)
                if request.get('content_image') and not (path.parent / request['content_image']).exists():
                    self.assertEqual(request['content_image'], 'night-source.png')
                    continue  # Example requires a user-provided image fixture, not bundled in the repo.
                job = m.prepare(request, path.parent, self.base / 'cache', self.base / 'prepared', text_only=True)
                self.assertEqual(job['state'], 'PROMPT_ONLY')
                self.assertGreater(len(job['checks']), 10)


if __name__ == '__main__':
    unittest.main(verbosity=2)
