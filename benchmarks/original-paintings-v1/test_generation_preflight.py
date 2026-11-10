import json
import unittest

from generation_preflight import ROOT, build_prompt, diagnose_attempt, classify_context_route


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

    def test_compact_uses_same_canonical_compiler(self):
        import importlib.util
        script = ROOT.parents[1] / 'skills/monet-style/scripts/monet.py'
        spec = importlib.util.spec_from_file_location('monet_compact_preflight_test', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for case in json.loads((ROOT / 'cases.json').read_text())['cases']:
            for arm in ('baseline', 'regional-p0'):
                with self.subTest(case=case['id'], arm=arm):
                    job = build_prompt(case['id'], arm, 'compact-v1')
                    expected = module.prepare({'request': case['content_prompt'],
                        'mode': 'generate', 'aspect_ratio': case['aspect_ratio']},
                        ROOT, ROOT/'unused', ROOT, True, arm, 'compact-v1')
                    self.assertEqual(job['prompt'], expected['prompt'])
                    self.assertEqual(job['style_lock'], expected['style_lock'])
                    self.assertNotIn('NO STYLE REFERENCE IS ATTACHED', job['prompt'])
                    self.assertFalse(job['controlled_ab_qualified'])

    def test_chatgpt_reused_or_unknown_context_blocks_generation(self):
        self.assertEqual(classify_context_route('chatgpt-inferred', 'reused')['status'],
                         'BLOCKED_CONTEXT_REUSE')
        self.assertEqual(classify_context_route('chatgpt-inferred', 'unknown')['status'],
                         'BLOCKED_CONTEXT_UNVERIFIED')
        self.assertFalse(classify_context_route('chatgpt-inferred', 'reused')['controlled_ab_qualified'])

    def test_new_chat_is_exploratory_not_controlled_ab(self):
        gate = classify_context_route('chatgpt-inferred', 'fresh')
        self.assertEqual(gate['status'], 'FRESH_CHAT_EXPLORATORY_ONLY')
        self.assertFalse(gate['controlled_ab_qualified'])
        self.assertEqual(gate['isolation_provenance'], 'operator_reported')

    def test_cli_exports_fresh_chat_prompt_without_old_harbor_material(self):
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'scene'
            result = subprocess.run([
                sys.executable, str(ROOT / 'generation_preflight.py'), 'prepare',
                '--case', 'MOR-02', '--variant', 'baseline',
                '--prompt-variant', 'compact-v1', '--delivery-profile', 'chatgpt-inferred',
                '--conversation-state', 'reused', '--output', str(out),
            ], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'BLOCKED_CONTEXT_REUSE')
            prompt = (out / 'image-only-prompt.txt').read_text(encoding='utf-8')
            metadata = json.loads((out / 'generation-metadata.json').read_text(encoding='utf-8'))
            self.assertIn('撑着洋伞的女子', prompt)
            self.assertNotIn('港口', prompt)
            self.assertNotIn('harbor', prompt.lower())
            self.assertNotIn('MOR-02', prompt)
            self.assertNotIn('BLOCKED_CONTEXT_REUSE', prompt)
            self.assertEqual(metadata['launch_gate']['status'], 'BLOCKED_CONTEXT_REUSE')
            self.assertFalse(metadata['launch_gate']['controlled_ab_qualified'])
            self.assertNotIn('prompt', metadata)

    def test_generated_wrong_subject_is_rejected_before_scoring(self):
        record = {'tool_invoked': True, 'outcome': 'image_returned',
                  'hard_gates': {'single_painting': True, 'subject_class': False,
                                 'time_and_weather': False},
                  'aspect_ratio_pass': False}
        self.assertEqual(diagnose_attempt(record), 'CONTENT_GATE_REJECTED')
        record['hard_gates']['subject_class'] = None
        self.assertEqual(diagnose_attempt(record), 'CONTENT_GATE_REJECTED')
        record['hard_gates'] = {k: True for k in record['hard_gates']}
        record['aspect_ratio_pass'] = True
        self.assertEqual(diagnose_attempt(record), 'GENERATED_PENDING_STYLE_REVIEW')
        self.assertEqual(diagnose_attempt({'tool_invoked': True, 'outcome': 'image_returned',
                                           'aspect_ratio_pass': False}), 'CONTENT_GATE_REJECTED')
        with self.assertRaisesRegex(ValueError, 'hard_gates'):
            diagnose_attempt({'tool_invoked': True, 'outcome': 'image_returned',
                              'hard_gates': {'subject_class': True}})

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
