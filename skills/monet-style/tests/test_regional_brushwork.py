"""Deterministic, offline checks; no calls to an image generator."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('monet', ROOT / 'scripts' / 'monet.py')
monet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monet)


class RegionalP0Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.request = {
            'request': '画一幅清晨薄雾中的港口，只有一轮朝阳与小船，保留横向水面。',
            'mode': 'generate', 'aspect_ratio': '4:3',
            'must_keep': ['清晨薄雾', '小船和一轮朝阳'], 'must_avoid': ['报告海报', '拼图']
        }

    def prepare(self, variant='baseline'):
        return monet.prepare(self.request, self.dir, self.dir / 'cache', self.dir / 'run', True, variant)

    def test_baseline_remains_default(self):
        self.assertEqual(monet.prepare(self.request, self.dir, self.dir / 'cache', self.dir / 'x', True), self.prepare())
        self.assertNotIn('P0 REGIONAL BRUSHWORK CANDIDATE', self.prepare()['prompt'])

    def test_p0_is_only_prompt_overlay(self):
        b = self.prepare()
        p = self.prepare('regional-p0')
        self.assertEqual(b['request'], p['request'])
        self.assertEqual(b['references'], p['references'])
        self.assertEqual(b['content_reference'], p['content_reference'])
        self.assertEqual(b['checks'], p['checks'])
        self.assertEqual(b['cleanup_reference_manifest'], p['cleanup_reference_manifest'])
        overlay = (ROOT / 'references' / 'regional-brushwork-p0.txt').read_text().strip()
        self.assertEqual(p['prompt'], b['prompt'].replace('\n\nREFERENCE ROLES\n', '\n\nP0 REGIONAL BRUSHWORK CANDIDATE\n'+overlay+'\n\nREFERENCE ROLES\n'))

    def test_style_lock_prevents_cross_variant_series(self):
        b = self.prepare();p=self.prepare('regional-p0')
        self.assertEqual(b['style_lock']['brushwork_variant'], 'baseline')
        self.assertIsNone(b['style_lock']['brushwork_overlay_sha256'])
        self.assertEqual(p['style_lock']['brushwork_overlay_sha256'], monet.file_sha(ROOT / 'references' / 'regional-brushwork-p0.txt'))
        with self.assertRaisesRegex(ValueError, 'Style lock mismatch'):
            monet.check_lock(p, b['style_lock'])

    def test_same_candidate_is_deterministic(self):
        self.assertEqual(self.prepare('regional-p0'), self.prepare('regional-p0'))

    def test_bad_variant_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown brushwork variant'):
            self.prepare('experimental-other')

    def test_artistic_overlay_keeps_material_differentiation(self):
        overlay = (ROOT / 'references' / 'regional-brushwork-p0.txt').read_text()
        for word in ('SKY', 'WATER', 'GRASS', 'FABRIC', 'GRAINSTACKS'):
            self.assertIn(word, overlay)
        self.assertIn('color', overlay)

    def test_cli_preparation_uses_variant(self):
        req = self.dir / 'request.json'
        req.write_text(json.dumps(self.request, ensure_ascii=False), encoding='utf-8')
        out = self.dir / 'prepared'
        proc = subprocess.run([sys.executable,str(ROOT/'scripts/monet.py'),'prepare','--request',str(req),'--text-only','--brushwork-variant','regional-p0','--out',str(out)],capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        job = json.loads((out/'job.json').read_text())
        self.assertEqual(job['state'], 'PROMPT_ONLY')
        self.assertFalse(job['execution']['generation_performed'])
        self.assertEqual(job['style_lock']['brushwork_variant'], 'regional-p0')
        self.assertIn('P0 REGIONAL BRUSHWORK CANDIDATE', (out/'prompt.txt').read_text())

if __name__ == '__main__':
    unittest.main()
