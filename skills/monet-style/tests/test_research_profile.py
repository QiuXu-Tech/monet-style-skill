"""Offline preparation checks, not image generation or visual-quality evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('monet_research', ROOT / 'scripts' / 'monet.py')
monet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monet)


class ResearchProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.request = {
            'request': '深夜的河边小路，只有一位撑伞的人。',
            'must_keep': ['深夜', '恰好一人'], 'must_avoid': ['白昼'], 'aspect_ratio': '3:2'
        }

    def prepare(self, request=None, profile='research-v3', variant='baseline'):
        return monet.prepare(request or self.request, self.path, self.path / 'cache', self.path / 'run',
                             text_only=True, brushwork_variant=variant, profile=profile)

    def test_default_profile_is_research_without_p0(self):
        job = monet.prepare(self.request, self.path, self.path / 'cache', self.path / 'run', True)
        self.assertEqual(job, self.prepare())
        self.assertEqual(job['profile'], 'research-v3')
        self.assertEqual(job['style_lock']['anchor_id'], 'antibes-1888')
        self.assertNotIn('P0 REGIONAL BRUSHWORK CANDIDATE', job['prompt'])
        self.assertFalse(job['execution']['generation_performed'])

    def test_historical_v2_prompts_are_preserved(self):
        # SHA-256 of real text-only compiler output at a9721b98; no image scores.
        expected = {
            'baseline': '059900185e8cbe061a3ffa40b46c5392b99e0b15dc780994db6e8098313d326c',
            'regional-p0': '7d100553f8eba5086cd1572ad52490eac506d5a42e2a066953fb48d0a32a1211'
        }
        for variant, digest in expected.items():
            with self.subTest(variant=variant):
                self.assertEqual(self.prepare(profile='legacy-v2', variant=variant)['prompt_sha256'], digest)

    def test_profiles_and_p0_cannot_be_silently_mixed(self):
        with self.assertRaisesRegex(ValueError, 'requires --profile legacy-v2'):
            self.prepare(variant='regional-p0')
        with self.assertRaisesRegex(ValueError, 'Unknown profile'):
            self.prepare(profile='late-water-lilies')
        with self.assertRaisesRegex(ValueError, 'Style lock mismatch'):
            monet.check_lock(self.prepare(), self.prepare(profile='legacy-v2')['style_lock'])
        with self.assertRaisesRegex(ValueError, 'legacy-v2 cannot use'):
            self.prepare(dict(self.request, subject_modules=['water']), profile='legacy-v2')

    def test_only_selected_modules_enter_the_prompt(self):
        modules = monet.subject_modules()
        baseline = self.prepare()
        job = self.prepare(dict(self.request, subject_modules=['water', 'figures']))
        for module_id, module in modules.items():
            self.assertEqual(module['prompt'] in job['prompt'], module_id in ('water', 'figures'))
            self.assertNotIn(module['prompt'], baseline['prompt'])
        self.assertEqual([entry['id'] for entry in job['subject_module_evidence']], ['water', 'figures'])

    def test_unknown_duplicate_and_excessive_modules_are_rejected(self):
        for modules in [['water', 'water'], ['unknown'], ['water', 'figures', 'garden', 'snow'], 'water']:
            with self.subTest(modules=modules), self.assertRaises(ValueError):
                self.prepare(dict(self.request, subject_modules=modules))

    def test_painting_notes_are_explicit_and_bounded(self):
        note = '远处人物保留站姿；面部省略五官，水中反光保持暗。'
        job = self.prepare(dict(self.request, painting_notes=[note]))
        self.assertIn(note, job['prompt'])
        self.assertEqual(job['request']['painting_notes'], [note])
        for notes in ['', [''] , ['一区'] * 6]:
            with self.subTest(notes=notes), self.assertRaises(ValueError):
                self.prepare(dict(self.request, painting_notes=notes))

    def test_literal_request_weather_and_constraints_survive(self):
        literal = '深夜，只有一位撑伞的人。\n保留 ${scene} 与 {{test}} 原文。'
        request = dict(self.request, request=literal, subject_modules=['water', 'figures'])
        job = self.prepare(request)
        self.assertIn(literal, job['prompt'])
        self.assertIn('Required:\n- 深夜\n- 恰好一人', job['prompt'])
        self.assertIn('Exclude:\n- 白昼', job['prompt'])
        self.assertEqual(job['request']['request'], literal)

    def test_audit_metadata_and_anchor_subjects_stay_outside_new_prompt(self):
        job = self.prepare()
        for token in ('PROMPT_ONLY', 'research-v3', 'profile_sha256', 'study_ids',
                      'Reference-specific copying risks', 'NO STYLE REFERENCE IS ATTACHED',
                      'red-tiled cottage', 'Gardener\'s House at Antibes', 'NGA', '"cleanup":'):
            self.assertNotIn(token, job['prompt'])
        self.assertFalse(job['reference_delivery']['style_anchor_prepared'])
        self.assertFalse(job['reference_delivery']['style_anchor_attached'])

    def test_series_lock_tracks_rules_not_scene_notes(self):
        a = self.prepare()
        b = self.prepare(dict(self.request, subject_modules=['water'], painting_notes=['水面较平静。']))
        monet.check_lock(b, a['style_lock'])
        self.assertNotEqual(a['job_sha256'], b['job_sha256'])
        changed = copy.deepcopy(a['style_lock'])
        changed['subject_modules_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Style lock mismatch'):
            monet.check_lock(b, changed)

    def test_no_network_and_exact_prompt_file_hash(self):
        with patch.object(monet.urllib.request, 'urlopen', side_effect=AssertionError('network')):
            job = self.prepare()
        out = self.path / 'written'
        out.mkdir()
        monet.write_run(job, out)
        self.assertEqual(monet.file_sha(out / 'prompt.txt'), job['prompt_file_sha256'])
        self.assertEqual(monet.sha(job['prompt'].encode('utf-8')), job['prompt_sha256'])

    def test_cli_preserves_profile_and_rejects_invalid_combination(self):
        request = self.path / 'request.json'
        request.write_text(json.dumps(self.request, ensure_ascii=False), encoding='utf-8')
        out = self.path / 'cli'
        command = [sys.executable, str(ROOT / 'scripts' / 'monet.py'), 'prepare', '--text-only',
                   '--request', str(request), '--out', str(out)]
        done = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        job = json.loads((out / 'job.json').read_text())
        self.assertEqual(job['profile'], 'research-v3')
        invalid = self.path / 'invalid'
        command[command.index(str(out))] = str(invalid)
        failed = subprocess.run(command + ['--brushwork-variant', 'regional-p0'], text=True, capture_output=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertFalse(invalid.exists())

    def test_prompt_file_hash_survives_platform_newline_translation(self):
        # Model a native Windows text writer on any host. The exact prompt file
        # must use the bytes hashed at preparation, independent of text I/O.
        def windows_text_write(path, text, encoding=None, **kwargs):
            with path.open('w', encoding=encoding or 'utf-8', newline='\r\n') as stream:
                return stream.write(text)

        for profile in ('research-v3', 'legacy-v2'):
            with self.subTest(profile=profile):
                job = self.prepare(profile=profile)
                out = self.path / ('newline-' + profile)
                out.mkdir()
                with patch.object(Path, 'write_text', windows_text_write):
                    monet.write_run(job, out)
                self.assertEqual((out / 'prompt.txt').read_bytes(), (job['prompt'] + '\n').encode('utf-8'))
                self.assertEqual(monet.file_sha(out / 'prompt.txt'), job['prompt_file_sha256'])

    @unittest.skipIf(monet.Image is None, 'Pillow is optional; cleanup requires Pillow')
    def test_cleanup_references_do_not_impersonate_style_anchor(self):
        source = self.path / 'source.png'
        monet.Image.new('RGB', (48, 32), (60, 80, 110)).save(source)
        request = dict(self.request, mode='restyle', content_image='source.png', cleanup={'route': 'quantized'})
        for profile in ('research-v3', 'legacy-v2'):
            with self.subTest(profile=profile):
                job = monet.prepare(request, self.path, self.path / 'cache', self.path / profile, True,
                                    profile=profile)
                self.assertEqual([r['role'] for r in job['references']], ['cleanup-structure-map'])
                self.assertEqual(job['reference_delivery']['required_roles'], ['cleanup-structure-map'])
                self.assertNotIn('Style anchor is attached', job['prompt'])
                self.assertNotIn('Use the STYLE image', job['prompt'])
                self.assertFalse(job['reference_delivery']['style_anchor_prepared'])
                self.assertFalse(job['reference_delivery']['style_anchor_attached'])


if __name__ == '__main__':
    unittest.main()
