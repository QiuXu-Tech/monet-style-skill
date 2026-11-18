import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from generation_preflight import ROOT, build_prompt, diagnose_attempt, monet


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
                self.assertFalse(job['generation_performed'])
                self.assertFalse(job['original_image_to_generator'])
                self.assertFalse(job['style_anchor_attached'])
                self.assertFalse(job['controlled_ab_qualified'])
                self.assertEqual(job['reference_role'], 'EVALUATION_ONLY')

    def test_preflight_uses_canonical_skill_compilation(self):
        case = json.loads((ROOT / 'cases.json').read_text(encoding='utf-8'))['cases'][0]
        request = {'request': case['content_prompt'].strip(), 'mode': 'generate',
                   'aspect_ratio': case['aspect_ratio'], 'must_keep': [], 'must_avoid': []}
        canonical = monet.prepare(request, ROOT, ROOT / '.unused-cache', ROOT / '.unused-run',
                                  text_only=True, profile='research-v3')
        actual = build_prompt(case['id'])
        self.assertEqual(actual['prompt'], canonical['prompt'])
        self.assertEqual(actual['style_lock'], canonical['style_lock'])
        self.assertEqual(actual['prompt_sha256'], hashlib.sha256(actual['prompt'].encode()).hexdigest())
        self.assertEqual(actual['compiler_job_sha256'], canonical['job_sha256'])

    def test_research_profile_rejects_historical_p0_overlay(self):
        with self.assertRaises(ValueError):
            build_prompt('MOR-01', profile='research-v3', variant='regional-p0')

    def test_historical_metadata_prompt_is_not_relabelled_as_clean(self):
        with self.assertRaisesRegex(ValueError, 'historical reference-object metadata'):
            build_prompt('MOR-01', profile='legacy-v2')

    def test_cli_separates_prompt_and_hashed_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'prepared'
            proc = subprocess.run([sys.executable, str(ROOT / 'generation_preflight.py'), 'prepare',
                                   '--case', 'MOR-02', '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            prompt = (output / 'image-only-prompt.txt').read_bytes()
            metadata = json.loads((output / 'generation-metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(metadata['prompt_file_sha256'], hashlib.sha256(prompt).hexdigest())
            self.assertEqual(metadata['prompt_sha256'], hashlib.sha256(prompt[:-1]).hexdigest())
            self.assertTrue(prompt.endswith(b'\n'))
            self.assertNotIn('prompt', metadata)
            self.assertFalse(metadata['generation_performed'])
            self.assertFalse(metadata['style_anchor_attached'])

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
