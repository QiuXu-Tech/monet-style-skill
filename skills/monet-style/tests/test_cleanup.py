"""Standalone integration checks for the new cleanup preparation branch."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('monet', SKILL / 'scripts' / 'monet.py')
monet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monet)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image = self.root / 'scene.png'
        im = Image.new('RGB', (360, 540), (125, 133, 185))
        for y in range(300, 450):
            for x in range(90, 260):
                im.putpixel((x, y), (140 + (y - 300) // 6, 125, 161))
        im.save(self.image)
        self.request = {
            'request': '夜晚的单灯石阶；保留空气感，去除鳞纹。',
            'mode': 'restyle', 'content_image': 'scene.png',
            'aspect_ratio': '2:3', 'must_keep': ['只有一盏灯'],
            'must_avoid': ['图表', '额外路灯'],
            'cleanup': {'route': 'quantized+gaussian', 'colors': 30, 'max_side': 512}
        }

    def prepare(self, request=None, name='run'):
        return monet.prepare(request or self.request, self.root, self.root / 'cache', self.root / name, text_only=True)

    def test_cleanup_is_opt_in(self):
        r = {'request': '画现代车站', 'mode': 'generate', 'aspect_ratio': '3:2'}
        result = monet.normalize(r)
        self.assertIsNone(result['cleanup'])

    def test_cleanup_requires_restyle(self):
        r = copy.deepcopy(self.request)
        r['mode'] = 'generate'
        r.pop('content_image')
        with self.assertRaisesRegex(ValueError, 'cleanup is only supported'):
            monet.normalize(r)

    def test_cleanup_rejects_noninteger_colors(self):
        for value in [30.8, '30', True, 0]:
            with self.subTest(value=value):
                r = copy.deepcopy(self.request)
                r['cleanup']['colors'] = value
                with self.assertRaises(ValueError):
                    monet.normalize(r)

    def test_cleanup_rejects_unsupported_route(self):
        r = copy.deepcopy(self.request)
        r['cleanup']['route'] = 'raw-pixels'
        with self.assertRaises(ValueError):
            monet.normalize(r)

    def test_content_orientation_drift_rejected(self):
        r = copy.deepcopy(self.request)
        r['aspect_ratio'] = '3:2'
        with self.assertRaisesRegex(ValueError, 'source aspect ratio'):
            self.prepare(r)

    def test_default_cleanup_creates_both_references(self):
        job = self.prepare()
        self.assertEqual(job['state'], 'PROMPT_ONLY')
        self.assertEqual([ref['role'] for ref in job['references']], ['cleanup-structure-map', 'cleanup-lighting-support'])
        for ref in job['references']:
            self.assertEqual(ref['sha256'], monet.file_sha(Path(ref['path'])))
            self.assertEqual(ref['height'], 512)
            self.assertAlmostEqual(ref['width'] / ref['height'], 2 / 3, delta=0.02)
        self.assertFalse(job['execution']['generation_performed'])
        self.assertEqual(job['cleanup_reference_manifest']['source_sha256'], monet.file_sha(self.image))
        self.assertEqual(job['content_reference']['role'], 'analysis-only-original')
        self.assertIn('fish-scale', job['prompt'])
        self.assertIn('鳞纹', job['request']['request'])

    def test_quantized_route_omits_gaussian(self):
        r = copy.deepcopy(self.request)
        r['cleanup']['route'] = 'quantized'
        job = self.prepare(r)
        self.assertEqual([ref['role'] for ref in job['references']], ['cleanup-structure-map'])
        self.assertFalse((self.root / 'run' / 'cleanup' / 'gaussian-support.png').exists())

    def test_style_lock_rejects_parameter_change(self):
        first = self.prepare()
        changed = copy.deepcopy(self.request)
        changed['cleanup']['colors'] = 48
        second = self.prepare(changed, 'run-two')
        with self.assertRaisesRegex(ValueError, 'Style lock mismatch'):
            monet.check_lock(second, first['style_lock'])

    def test_style_lock_same_config_allows_new_scene(self):
        first = self.prepare()
        changed = copy.deepcopy(self.request)
        changed['request'] = '第二张作品：一样的夜雾，不同台阶'
        second = self.prepare(changed, 'run-two')
        monet.check_lock(second, first['style_lock'])

    def test_no_cleanup_preserves_regular_restyle(self):
        r = copy.deepcopy(self.request)
        r.pop('cleanup')
        job = self.prepare(r)
        self.assertIsNone(job['cleanup_reference_manifest'])
        self.assertEqual(job['content_reference']['role'], 'content-and-composition')
        self.assertFalse((self.root/'run'/'cleanup').exists())

    def test_review_template_unknown_cannot_approve(self):
        job = self.prepare()
        t = monet.review_template(job)
        self.assertTrue(all(x['result'] == 'unknown' for x in t['checks']))
        self.assertFalse(t['inspected_image'])

    def test_misgenerated_report_is_rejected_when_recorded_as_failure(self):
        job = self.prepare()
        t = monet.review_template(job)
        t['image_sha256'] = monet.file_sha(self.image)
        t['inspected_image'] = True
        t['reviewer_kind'] = 'model'
        t['reviewer'] = 'qa-model'
        t['tool_name'] = 'host-image-generator'
        t['call_id'] = 'bad-output-001'
        t['checks'][0].update(result='fail', evidence='生成了含文字表格的报告，不是夜景油画')
        result = monet.evaluate(job, self.image, t)
        self.assertEqual(result['state'], 'REJECTED')

    def test_bad_input_leaves_no_output_folder(self):
        r = copy.deepcopy(self.request)
        r['content_image'] = 'nonexistent.png'
        request_file = self.root/'request.json'
        request_file.write_text(json.dumps(r, ensure_ascii=False), encoding='utf-8')
        out = self.root/'output-should-not-exist'
        p = subprocess.run([sys.executable, str(SKILL/'scripts'/'monet.py'), 'prepare', '--text-only', '--request', str(request_file), '--out', str(out)], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(out.exists())

    def test_invalid_lock_leaves_no_output_folder(self):
        first = self.prepare()
        r = copy.deepcopy(self.request)
        r['cleanup']['colors'] = 48
        request_file = self.root/'request.json'
        request_file.write_text(json.dumps(r, ensure_ascii=False), encoding='utf-8')
        lock_path = self.root/'style-lock.json'
        lock_path.write_text(json.dumps(first['style_lock']))
        out = self.root/'output-should-not-exist'
        p = subprocess.run([sys.executable, str(SKILL/'scripts'/'monet.py'), 'prepare', '--text-only', '--request', str(request_file), '--out', str(out), '--lock', str(lock_path)], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('Style lock mismatch', p.stderr)
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
