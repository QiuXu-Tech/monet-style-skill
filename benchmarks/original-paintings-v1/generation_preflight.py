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

# These terms belong to evaluation metadata, not to an image-generation request.
METADATA_LEAKS = ("评测报告", "评分表", "MOR-01", "MOR-02", "MOR-03", "baseline", "R001", "对照结果")


def build_prompt(case_id: str, variant: str = 'baseline', prompt_variant: str = 'full') -> dict:
    if variant not in ('baseline', 'regional-p0'):
        raise ValueError('Unknown brushwork variant')
    suite = json.loads((ROOT / 'cases.json').read_text(encoding='utf-8'))
    assert suite['reference_policy']['target_original_as_generation_input'] is False
    matches = [case for case in suite['cases'] if case['id'] == case_id]
    if len(matches) != 1:
        raise ValueError(f'Unknown case ID: {case_id}')
    case = matches[0]
    content = case['content_prompt'].strip()
    if not content:
        raise ValueError('Empty content prompt')

    # Compile exactly the same text-only job as the installable Skill, rather
    # than maintaining an alternate simplified prompt in the benchmark.
    script = ROOT.parents[1] / 'skills' / 'monet-style' / 'scripts' / 'monet.py'
    spec = importlib.util.spec_from_file_location('monet_style_preflight', script)
    if spec is None or spec.loader is None:
        raise ValueError('Skill compiler is unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    request = {'request': content, 'mode': 'generate', 'aspect_ratio': case['aspect_ratio']}
    job = module.prepare(request, ROOT, ROOT / 'not-used-cache', ROOT,
                         text_only=True, brushwork_variant=variant, prompt_variant=prompt_variant)
    prompt = job['prompt']
    if any(token.lower() in prompt.lower() for token in METADATA_LEAKS):
        raise ValueError('Evaluation metadata leaked into generation prompt')
    return {
        'case_id': case_id,
        'variant': variant,
        'prompt_variant': prompt_variant,
        'prompt': prompt,
        'prompt_file_sha256': hashlib.sha256((prompt + '\n').encode('utf-8')).hexdigest(),
        'style_lock': job['style_lock'],
        'canvas_ratio_requested': case['aspect_ratio'],
        'reference_role': 'EVALUATION_ONLY',
        'original_image_to_generator': False,
        'style_anchor_attached': False,
        'controlled_ab_qualified': False,
        'tool_called': False,
        'status': 'READY_NOT_GENERATED',
    }


def classify_context_route(delivery_profile: str, conversation_state: str = 'unknown') -> dict:
    """Preflight for prompt-from-conversation tools; cannot control their internals."""
    if delivery_profile not in ('generic', 'chatgpt-inferred'):
        raise ValueError('Unknown delivery profile')
    if conversation_state not in ('fresh', 'reused', 'unknown'):
        raise ValueError('Unknown conversation state')
    if delivery_profile == 'generic':
        if conversation_state != 'unknown':
            raise ValueError('Conversation state applies only to chatgpt-inferred delivery')
        return {'status': 'READY_NOT_GENERATED', 'controlled_ab_qualified': False,
                'isolation_provenance': 'not_applicable'}
    status = {'fresh': 'FRESH_CHAT_EXPLORATORY_ONLY',
              'reused': 'BLOCKED_CONTEXT_REUSE',
              'unknown': 'BLOCKED_CONTEXT_UNVERIFIED'}[conversation_state]
    return {'status': status, 'controlled_ab_qualified': False,
            'isolation_provenance': 'operator_reported',
            'instruction': 'Paste image-only-prompt.txt alone into a new chat; do not paste metadata or history.'}


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
        ratio = record.get('aspect_ratio_pass')
        if ratio is not None and type(ratio) is not bool:
            raise ValueError('aspect_ratio_pass must be boolean or null')
        gates = record.get('hard_gates')
        if gates is None:
            return "CONTENT_GATE_REJECTED" if ratio is False else "GENERATED_PENDING_VISUAL_REVIEW"
        expected = {'single_painting', 'subject_class', 'time_and_weather'}
        if not isinstance(gates, dict) or set(gates) != expected or any(
                type(v) not in (bool, type(None)) for v in gates.values()):
            raise ValueError('hard_gates must contain three inspected visual outcomes')
        if False in gates.values() or ratio is False:
            return "CONTENT_GATE_REJECTED"
        if any(v is None for v in gates.values()) or ratio is None:
            return "GENERATED_PENDING_VISUAL_REVIEW"
        return "GENERATED_PENDING_STYLE_REVIEW"
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
    prepare.add_argument("--variant", choices=("baseline", "regional-p0"), default="baseline")
    prepare.add_argument("--prompt-variant", choices=("full", "compact-v1"), default="full")
    prepare.add_argument("--delivery-profile", choices=("generic", "chatgpt-inferred"), default="generic")
    prepare.add_argument("--conversation-state", choices=("fresh", "reused", "unknown"), default="unknown")
    prepare.add_argument("--output", type=Path, required=True)
    diagnose = sub.add_parser("diagnose")
    diagnose.add_argument("--record", type=Path, required=True)
    args = p.parse_args()
    if args.command == "diagnose":
        record = json.loads(args.record.read_text(encoding="utf-8"))
        print(json.dumps({"status": diagnose_attempt(record)}, ensure_ascii=False))
        return 0
    job = build_prompt(args.case, args.variant, args.prompt_variant)
    gate = classify_context_route(args.delivery_profile, args.conversation_state)
    if args.output.exists():
        raise ValueError("Output directory already exists; refusing overwrite")
    args.output.mkdir(parents=True)
    (args.output / "image-only-prompt.txt").write_text(job["prompt"] + "\n", encoding="utf-8")
    meta = {key: val for key, val in job.items() if key != "prompt"}
    meta['launch_gate'] = gate
    (args.output / "generation-metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": gate["status"], "case_id": args.case,
                      "prompt_file": str(args.output / "image-only-prompt.txt")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
