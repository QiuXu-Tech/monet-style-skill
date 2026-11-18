#!/usr/bin/env python3
"""Prepare image-only prompts and classify tool attempts without inventing refusals.

Does not generate images, override provider safety checks or inspect aesthetics.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SKILL_ROOT = ROOT.parents[1] / "skills" / "monet-style"
_spec = importlib.util.spec_from_file_location("monet_benchmark_compiler", SKILL_ROOT / "scripts" / "monet.py")
monet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(monet)

# These terms belong to evaluation metadata, not to an image-generation request.
METADATA_LEAKS = ("评测报告", "评分表", "MOR-01", "MOR-02", "MOR-03", "baseline", "R001", "对照结果")


def build_prompt(case_id: str, profile: str = "research-v3", variant: str = "baseline") -> dict:
    suite = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    assert suite["reference_policy"]["target_original_as_generation_input"] is False
    matches = [case for case in suite["cases"] if case["id"] == case_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown case ID: {case_id}")
    case = matches[0]
    content = case["content_prompt"].strip()
    if not content:
        raise ValueError("Empty content prompt")
    request = {"request": content, "mode": "generate", "aspect_ratio": case["aspect_ratio"],
               "must_keep": [], "must_avoid": []}
    # No source image, downloads or generation: compile the installed Skill's
    # actual text route. These paths are not written by a text-only generate job.
    job = monet.prepare(request, ROOT, ROOT / ".unused-cache", ROOT / ".unused-run",
                        text_only=True, brushwork_variant=variant, profile=profile)
    prompt = job["prompt"]
    if profile == "legacy-v2" and "REFERENCE ROLES" in prompt:
        raise ValueError("legacy-v2 preserves historical reference-object metadata in its prompt; "
                         "this benchmark will not emit it as an isolated image request. "
                         "Use the historical Skill checkout for archival reproduction, not a current clean-prompt A/B claim.")
    forbidden = (*METADATA_LEAKS, case["title_original"], case["museum_url"], case["catalog_source_page"])
    if any(token.lower() in prompt.lower() for token in forbidden):
        raise ValueError("Evaluation metadata leaked into generation prompt")
    if any(ref.get("role") == "style-only" for ref in job["references"]):
        raise ValueError("Text-only benchmark must not attach a style image")
    return {
        "case_id": case_id,
        "prompt": prompt,
        "prompt_sha256": job["prompt_sha256"],
        "compiler_job_sha256": job["job_sha256"],
        "style_lock": job["style_lock"],
        "profile": profile,
        "brushwork_variant": variant,
        "canvas_ratio_requested": case["aspect_ratio"],
        "reference_role": "EVALUATION_ONLY",
        "original_image_to_generator": False,
        "style_anchor_attached": False,
        "controlled_ab_qualified": False,
        "generation_performed": False,
        "tool_called": False,
        "status": "READY_NOT_GENERATED",
        "validation_note": "Offline prompt preparation only. The selected anchor in the style lock is not attached; no visual quality was tested.",
    }


def diagnose_attempt(record: dict) -> str:
    """Classify reported tool evidence, never infer provider refusals from assistant prose."""
    invoked = record.get("tool_invoked")
    if type(invoked) is not bool:
        raise ValueError("tool_invoked must be boolean")
    if not invoked:
        if record.get("provider_response"):
            raise ValueError("Provider response cannot be claimed without a tool invocation")
        return "NO_TOOL_CALL_EVIDENCE"

    outcome = record.get("outcome")
    if outcome == "image_returned":
        return "GENERATED_PENDING_VISUAL_REVIEW"
    if outcome == "invalid_arguments":
        return "TOOL_ARGUMENT_ERROR"
    if outcome == "error":
        if record.get("error_origin") == "provider_policy":
            response = record.get("provider_response")
            if not isinstance(response, str) or not response.strip():
                raise ValueError("Provider refusal requires actual provider error evidence")
            return "PROVIDER_REFUSAL_RECORDED"
        return "TOOL_ERROR_UNCLASSIFIED"
    raise ValueError("Unknown tool outcome; cannot assume copyright refusal")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--case", required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--profile", choices=("research-v3", "legacy-v2"), default="research-v3")
    prepare.add_argument("--variant", choices=("baseline", "regional-p0"), default="baseline")
    diagnose = sub.add_parser("diagnose")
    diagnose.add_argument("--record", type=Path, required=True)
    args = p.parse_args()
    if args.command == "diagnose":
        record = json.loads(args.record.read_text(encoding="utf-8"))
        print(json.dumps({"status": diagnose_attempt(record)}, ensure_ascii=False))
        return 0
    job = build_prompt(args.case, profile=args.profile, variant=args.variant)
    if args.output.exists():
        raise ValueError("Output directory already exists; refusing overwrite")
    args.output.mkdir(parents=True)
    prompt_file = args.output / "image-only-prompt.txt"
    prompt_file.write_bytes((job["prompt"] + "\n").encode("utf-8"))
    meta = {key: val for key, val in job.items() if key != "prompt"}
    meta["prompt_file_sha256"] = hashlib.sha256(prompt_file.read_bytes()).hexdigest()
    (args.output / "generation-metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": job["status"], "case_id": args.case,
                      "prompt_file": str(args.output / "image-only-prompt.txt")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
