#!/usr/bin/env python3
"""Gate controlled image A/B experiments on observed host capabilities.

This never generates images or judges visual style. Unknown capabilities fail
closed. Passing this gate does not certify subsequent model outputs.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

REQUIRED = (
    "explicit_prompt_binding",
    "style_reference_bytes_verified",
    "reference_roles_verifiable",
    "aspect_ratio_control_available",
    "model_identifier_available",
    "real_image_output_accessible",
    "generation_receipt_available",
)

def qualify(capabilities: dict) -> dict:
    if not isinstance(capabilities, dict):
        raise ValueError("Capabilities must be an object")
    missing = [name for name in REQUIRED if capabilities.get(name) is not True]
    if capabilities.get("additional_paid_service") is True and capabilities.get("paid_use_approved") is not True:
        missing.append("paid_use_approved")
    return {
        "status": "QUALIFIED_FOR_CONTROLLED_AB" if not missing else "BLOCKED_HOST_CAPABILITY",
        "missing": missing,
        "validated_fields": list(REQUIRED),
        "note": "Preflight only. After each call, verify actual image content, dimensions, references and provenance. Never infer style success from this status.",
    }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capability_file", type=Path)
    args = parser.parse_args()
    cap = json.loads(args.capability_file.read_text(encoding="utf-8"))
    print(json.dumps(qualify(cap), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
