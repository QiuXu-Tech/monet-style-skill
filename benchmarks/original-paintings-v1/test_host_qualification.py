import unittest
from host_qualification import qualify, REQUIRED

class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.ready = {field: True for field in REQUIRED}
        self.ready["additional_paid_service"] = False

    def test_success_when_all_evidence_is_available(self):
        self.assertEqual(qualify(self.ready)["status"], "QUALIFIED_FOR_CONTROLLED_AB")

    def test_unknown_fields_are_not_assumed(self):
        self.assertEqual(qualify({})["missing"], list(REQUIRED))

    def test_missing_explicit_prompt_blocks(self):
        value = self.ready | {"explicit_prompt_binding": False}
        self.assertEqual(qualify(value)["status"], "BLOCKED_HOST_CAPABILITY")
        self.assertIn("explicit_prompt_binding", qualify(value)["missing"])

    def test_unbound_reference_blocks(self):
        value = self.ready | {"style_reference_bytes_verified": False}
        self.assertIn("style_reference_bytes_verified", qualify(value)["missing"])

    def test_roles_not_verified_blocks(self):
        value = self.ready | {"reference_roles_verifiable": None}
        self.assertIn("reference_roles_verifiable", qualify(value)["missing"])

    def test_ratio_control_blocks(self):
        value = self.ready | {"aspect_ratio_control_available": False}
        self.assertIn("aspect_ratio_control_available", qualify(value)["missing"])

    def test_missing_model_blocks(self):
        value = self.ready | {"model_identifier_available": False}
        self.assertIn("model_identifier_available", qualify(value)["missing"])

    def test_image_or_receipt_missing_blocks(self):
        for key in ("real_image_output_accessible", "generation_receipt_available"):
            with self.subTest(key=key):
                self.assertIn(key, qualify(self.ready | {key: False})["missing"])

    def test_unapproved_paid_backend_blocks(self):
        value = self.ready | {"additional_paid_service": True}
        self.assertIn("paid_use_approved", qualify(value)["missing"])

    def test_approved_paid_backend_is_eligible(self):
        value = self.ready | {"additional_paid_service": True, "paid_use_approved": True}
        self.assertEqual(qualify(value)["status"], "QUALIFIED_FOR_CONTROLLED_AB")

    def test_bad_input_rejected(self):
        with self.assertRaises(ValueError):
            qualify([])

if __name__ == "__main__":
    unittest.main()
