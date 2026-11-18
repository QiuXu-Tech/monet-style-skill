"""Offline guardrails for the opt-in short prompt; no image model calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compact_test_monet', ROOT / 'scripts/monet.py')
monet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monet)


class CompactPromptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.request = {
            'request': '清晨薄雾中的港口，水面有小船，远处有港口吊装设施。',
            'mode': 'generate', 'aspect_ratio': '4:3',
            'must_keep': ['两艘小船', '灰蓝色雾气'],
            'must_avoid': ['红瓦房', '多联画'],
        }

    def plan(self, arm='baseline', prompt_variant='full'):
        return monet.prepare(self.request, self.base, self.base/'cache',
                             self.base/'run', True, arm, prompt_variant)

    def test_default_unchanged(self):
        self.assertEqual(
            monet.prepare(self.request, self.base, self.base/'cache',
                          self.base/'run', True),
            self.plan()
        )
        self.assertNotIn('prompt_variant', self.plan()['style_lock'])

    def test_original_full_brief_hashes_remain_frozen(self):
        suite = json.loads((ROOT.parents[1] /
            'benchmarks/original-paintings-v1/cases.json').read_text(encoding='utf-8'))
        case = suite['cases'][0]
        req = {'request': case['content_prompt'], 'mode': 'generate',
               'aspect_ratio': case['aspect_ratio']}
        expected = {'baseline': 'd75e7ca93b693809c4b241d7351e0413acf9a2dd1d0dfb4b2db4ac83abfc4fc0',
                    'regional-p0': '629f302c3f9bb3db34357b98ec120f15386d527406b9a5c67e6465cb5acfd396'}
        for arm, digest in expected.items():
            with self.subTest(arm=arm):
                old = monet.prepare(req, self.base, self.base/'cache', self.base/'out', True, arm)
                self.assertEqual(hashlib.sha256(old['prompt'].encode()).hexdigest(), digest)

    def test_compact_keeps_brief_and_avoids_metadata(self):
        compact = self.plan(prompt_variant='compact-v1')
        prompt = compact['prompt']
        self.assertIn(self.request['request'], prompt)
        for item in self.request['must_keep'] + self.request['must_avoid']:
            self.assertIn(item, prompt)
        self.assertIn('4:3', prompt)
        self.assertIn('atmospheric', prompt)
        self.assertIn('fish-scale', prompt)
        self.assertIn('signatures', prompt)
        self.assertNotIn('Gardener', prompt)
        self.assertNotIn('red-tiled cottage', prompt)
        self.assertNotIn('NO STYLE REFERENCE IS ATTACHED', prompt)
        self.assertNotIn('MOR-01', prompt)
        self.assertEqual(compact['state'], 'PROMPT_ONLY')
        self.assertEqual(compact['references'], [])
        self.assertLess(len(prompt), len(self.plan()['prompt']) * .50)

    def test_compact_p0_changes_only_overlay(self):
        b = self.plan(prompt_variant='compact-v1')
        p = self.plan('regional-p0', 'compact-v1')
        overlay = (ROOT/'references/compact-regional-p0.txt').read_text().strip()
        self.assertEqual(p['prompt'], b['prompt'] + '\nRegional brushwork: ' + overlay)
        self.assertEqual(b['request'], p['request'])
        self.assertEqual(b['references'], p['references'])
        self.assertEqual(b['checks'], p['checks'])
        self.assertLess(len(p['prompt']), len(self.plan('regional-p0')['prompt']) * .50)
        self.assertNotIn('P0 REGIONAL BRUSHWORK CANDIDATE', p['prompt'])

    def test_lock_separates_both_prompt_and_brushwork_versions(self):
        full = self.plan()
        compact = self.plan(prompt_variant='compact-v1')
        p0 = self.plan('regional-p0', 'compact-v1')
        self.assertNotEqual(full['style_lock'], compact['style_lock'])
        self.assertNotEqual(compact['style_lock'], p0['style_lock'])
        self.assertEqual(compact['style_lock']['prompt_variant'], 'compact-v1')
        self.assertEqual(compact['style_lock']['compact_prompt_sha256'],
                         monet.file_sha(ROOT/'references/compact-prompt-v1.txt'))
        self.assertEqual(p0['style_lock']['brushwork_overlay_sha256'],
                         monet.file_sha(ROOT/'references/compact-regional-p0.txt'))
        with self.assertRaisesRegex(ValueError, 'Style lock mismatch'):
            monet.check_lock(compact, full['style_lock'])

    def test_unknown_variant_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown prompt variant'):
            self.plan(prompt_variant='magic')

    def test_cli_opt_in_and_original_default(self):
        req = self.base/'request.json'
        req.write_text(json.dumps(self.request, ensure_ascii=False))
        for variant in ('full', 'compact-v1'):
            with self.subTest(variant=variant):
                out = self.base/variant
                args = [sys.executable, str(ROOT/'scripts/monet.py'),
                        'prepare', '--request', str(req), '--out', str(out),
                        '--text-only', '--prompt-variant', variant]
                proc = subprocess.run(args, text=True, capture_output=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                job = json.loads((out/'job.json').read_text())
                self.assertEqual(job['prompt'], self.plan(prompt_variant=variant)['prompt'])


if __name__ == '__main__':
    unittest.main()
