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
