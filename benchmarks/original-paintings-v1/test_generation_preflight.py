import json
import unittest

from generation_preflight import ROOT, build_prompt, diagnose_attempt


class ImagePromptPreflightTests(unittest.TestCase):
    def test_three_cases_produce_original_image_only_prompts(self):
        cases = json.loads((ROOT / 'cases.json').read_text(encoding='utf-8'))['cases']
        for case in cases:
            with self.subTest(case=case['id']):
                job = build_prompt(case['id'])
                prompt = job['prompt']
                self.assertIn(case['content_prompt'], prompt)
                self.assertNotIn(case['title_original'], prompt)
                self.assertNotIn(case['museum_url'], prompt)
                self.assertNotIn(case['id'], prompt)
                self.assertNotIn('评测报告', prompt)
                self.assertNotIn('评分', prompt)
                self.assertFalse(job['tool_called'])
                self.assertFalse(job['original_image_to_generator'])
                self.assertEqual(job['reference_role'], 'EVALUATION_ONLY')

    def test_uses_exact_skill_compiler_for_both_variants(self):
        import hashlib
        import importlib.util

        script = ROOT.parents[1] / 'skills/monet-style/scripts/monet.py'
        spec = importlib.util.spec_from_file_location('monet_skill_in_preflight_test', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        case = next(c for c in json.loads((ROOT / 'cases.json').read_text())['cases'] if c['id'] == 'MOR-01')
        for variant in ('baseline', 'regional-p0'):
            with self.subTest(variant=variant):
                got = build_prompt('MOR-01', variant)
                expected = module.prepare({'request': case['content_prompt'], 'mode': 'generate',
                    'aspect_ratio': case['aspect_ratio']}, ROOT, ROOT / 'not-used-cache', ROOT, True, variant)
                self.assertEqual(got['prompt'], expected['prompt'])
                self.assertEqual(got['style_lock'], expected['style_lock'])
                self.assertEqual(got['prompt_file_sha256'], hashlib.sha256((got['prompt'] + '\n').encode()).hexdigest())
                self.assertFalse(got['style_anchor_attached'])
                self.assertFalse(got['original_image_to_generator'])

    def test_bad_variant_is_rejected(self):
        with self.assertRaises(ValueError):
            build_prompt('MOR-01', 'unsupported-arm')

    def test_cli_keeps_evaluation_data_out_of_image_prompt(self):
        import hashlib
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'run'
            proc = subprocess.run([sys.executable, str(ROOT / 'generation_preflight.py'),
                'prepare', '--case', 'MOR-02', '--variant', 'regional-p0',
                '--output', str(out)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            image_prompt = (out / 'image-only-prompt.txt').read_text(encoding='utf-8')
            metadata = json.loads((out / 'generation-metadata.json').read_text(encoding='utf-8'))
            self.assertIn('P0 REGIONAL BRUSHWORK CANDIDATE', image_prompt)
            self.assertIn('NO STYLE REFERENCE IS ATTACHED', image_prompt)
            self.assertNotIn('MOR-02', image_prompt)
            self.assertNotIn('评测报告', image_prompt)
            self.assertNotIn('评分', image_prompt)
            self.assertEqual(metadata['variant'], 'regional-p0')
            self.assertEqual(metadata['prompt_file_sha256'], hashlib.sha256(image_prompt.encode()).hexdigest())
            self.assertFalse(metadata['style_anchor_attached'])
            self.assertFalse(metadata['controlled_ab_qualified'])
            self.assertNotIn('prompt', metadata)

    def test_unknown_case(self):
        with self.assertRaisesRegex(ValueError, 'Unknown case'):
            build_prompt('MOR-99')

    def test_no_tool_call_is_not_a_provider_refusal(self):
        self.assertEqual(diagnose_attempt({'tool_invoked': False}), 'NO_TOOL_CALL_EVIDENCE')

    def test_no_fabricated_provider_evidence(self):
        with self.assertRaises(ValueError):
            diagnose_attempt({'tool_invoked': False, 'provider_response': 'refusal'})
        with self.assertRaises(ValueError):
            diagnose_attempt({'tool_invoked': True, 'outcome': 'error',
                              'error_origin': 'provider_policy'})

    def test_bad_animation_args_are_not_copyright_refusal(self):
        self.assertEqual(diagnose_attempt({'tool_invoked': True, 'outcome': 'invalid_arguments'}),
                         'TOOL_ARGUMENT_ERROR')

    def test_explicit_provider_error_and_normal_return(self):
        self.assertEqual(diagnose_attempt({'tool_invoked': True, 'outcome': 'error',
                              'error_origin': 'provider_policy', 'provider_response': 'upstream refusal'}),
                         'PROVIDER_REFUSAL_RECORDED')
        self.assertEqual(diagnose_attempt({'tool_invoked': True, 'outcome': 'image_returned'}),
                         'GENERATED_PENDING_VISUAL_REVIEW')

    def test_cannot_guess_unknown_outcome(self):
        with self.assertRaisesRegex(ValueError, 'Unknown tool outcome'):
            diagnose_attempt({'tool_invoked': True, 'outcome': 'copyright_error_guessed'})


if __name__ == '__main__':
    unittest.main()
