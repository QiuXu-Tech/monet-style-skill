#!/usr/bin/env python3
"""Prepare image-only prompts and classify tool attempts without inventing refusals.

Does not generate images, override provider safety checks or inspect aesthetics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STYLE = (
    "绘制一幅原创油画，采用19世纪法国印象派的自然光色语言。"
    "主体由相邻色块和有方向变化的绘画笔触塑造，天空、水面、植物、织物的笔触应有区别；"
    "远景轮廓适度融入空气，保留必要的主体结构。"
    "色彩饱和度应随光照和局部焦点变化，避免均匀的粉紫滤镜、机械重复的鳞片纹理及全面高斯模糊。"
)

# These terms belong to evaluation metadata, not to an image-generation request.
METADATA_LEAKS = ("评测报告", "评分表", "MOR-01", "MOR-02", "MOR-03", "baseline", "R001", "对照结果")


def build_prompt(case_id: str) -> dict:
    suite = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    assert suite["reference_policy"]["target_original_as_generation_input"] is False
    matches = [case for case in suite["cases"] if case["id"] == case_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown case ID: {case_id}")
    case = matches[0]
    content = case["content_prompt"].strip()
    if not content:
        raise ValueError("Empty content prompt")
    # Only generation instructions are passed to the image tool. No museum, title,
    # scores, reference-image path, or previous result is included in the prompt.
    prompt = f"{STYLE}\n\n{content}"
    if any(token.lower() in prompt.lower() for token in METADATA_LEAKS):
        raise ValueError("Evaluation metadata leaked into generation prompt")
    return {
        "case_id": case_id,
        "prompt": prompt,
        "canvas_ratio_requested": case["aspect_ratio"],
        "reference_role": "EVALUATION_ONLY",
        "original_image_to_generator": False,
        "tool_called": False,
        "status": "READY_NOT_GENERATED",
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
    diagnose = sub.add_parser("diagnose")
    diagnose.add_argument("--record", type=Path, required=True)
    args = p.parse_args()
    if args.command == "diagnose":
        record = json.loads(args.record.read_text(encoding="utf-8"))
        print(json.dumps({"status": diagnose_attempt(record)}, ensure_ascii=False))
        return 0
    job = build_prompt(args.case)
    if args.output.exists():
        raise ValueError("Output directory already exists; refusing overwrite")
    args.output.mkdir(parents=True)
    (args.output / "image-only-prompt.txt").write_text(job["prompt"] + "\n", encoding="utf-8")
    meta = {key: val for key, val in job.items() if key != "prompt"}
    (args.output / "generation-metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": job["status"], "case_id": args.case,
                      "prompt_file": str(args.output / "image-only-prompt.txt")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
