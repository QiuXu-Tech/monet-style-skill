#!/usr/bin/env python3
"""Offline fixture and review validator; never generates or grades images."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIMENSIONS = ('brushwork', 'color', 'atmosphere', 'artifact_control')
GATES = ('single_painting', 'subject_class', 'time_and_weather')


def read_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        raise ValueError(f'Expected an object: {path}')
    return obj


def validate_suite(suite: dict) -> None:
    if suite.get('status') != 'NOT_RUN' or suite.get('models_or_apis_tested') != []:
        raise ValueError('Fixture must not claim that images have been generated')
    weights = suite.get('weights', {})
    if set(weights) != set(DIMENSIONS) or abs(sum(weights.values()) - 1) > 1e-9:
        raise ValueError('Weights must cover four dimensions and sum to 1')
    cases = suite.get('cases', [])
    if len(cases) != 3 or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Expected three unique artwork cases')
    for case in cases:
        if not case['museum_url'].startswith('https://') or not case['catalog_source_page'].startswith('https://'):
            raise ValueError('Artwork record requires verifiable HTTPS source links')
        if not isinstance(case['catalog_preview_sha256'], str) or len(case['catalog_preview_sha256']) != 64:
            raise ValueError('Reference preview hash missing')
        if not case['content_prompt'].strip() or not case['content_gates'] or not case['review_questions']:
            raise ValueError('Incomplete content prompt or evaluation brief')
        if case.get('skill_1880s_profile_match') is not False:
            raise ValueError('Cross-period test must not be called an in-profile benchmark')
    if suite.get('reference_policy', {}).get('target_original_as_generation_input') is not False:
        raise ValueError('Original paintings must be evaluation-only references')


def validate_review(review: dict, suite: dict) -> dict:
    valid_ids = {item['id'] for item in suite['cases']}
    if review.get('status') == 'NOT_RUN':
        if review.get('generation_performed') is not False or any(v is not None for v in review.get('scores', {}).values()):
            raise ValueError('NOT_RUN cannot contain output or scores')
        return {'status': 'NOT_RUN', 'weighted_score': None}
    if review.get('case_id') not in valid_ids:
        raise ValueError('Review has unknown case ID')
    if review.get('arm') not in ('baseline', 'skill'):
        raise ValueError('Review must identify a named experimental arm')
    if review.get('generation_performed') is not True:
        raise ValueError('Cannot review an ungenerated image')
    image = Path(review.get('output_image_path') or '')
    if not image.is_file():
        raise ValueError('Inspect the real image file; a description is not evidence')
    actual_hash = hashlib.sha256(image.read_bytes()).hexdigest()
    if actual_hash != review.get('output_sha256'):
        raise ValueError('Output hash mismatch')
    data = image.read_bytes()
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        valid = (len(data) >= 45 and data[12:16] == b'IHDR' and
                 data[-12:] == b'\x00\x00\x00\x00IEND\xaeB`\x82' and
                 0 < struct.unpack('>I', data[16:20])[0] <= 100000 and
                 0 < struct.unpack('>I', data[20:24])[0] <= 100000)
    elif data.startswith(b'\xff\xd8\xff'):
        valid = len(data) >= 40 and data.endswith(b'\xff\xd9')
    else:
        valid = False
    if not valid:
        raise ValueError('Expected a structurally complete PNG or JPEG; visual decoding and review are still mandatory')
    who = review.get('reviewer', {})
    if not (who.get('kind') in ('human', 'model') and who.get('id') and who.get('inspected_original') is True and who.get('inspected_output') is True):
        raise ValueError('Reviewer and actual inspection must be recorded')
    gates = review.get('hard_gates', {})
    if set(gates) != set(GATES) or any(gates[k] not in (True, False, None) for k in GATES):
        raise ValueError('Invalid content/format gates')
    if any(gates[k] is not True for k in GATES):
        return {'status': 'REJECTED' if False in gates.values() else 'NEEDS_REVIEW', 'weighted_score': None}
    scores = review.get('scores', {})
    if set(scores) != set(DIMENSIONS):
        raise ValueError('Missing or extra score dimension')
    if any(type(scores[k]) not in (int, float) or not 0 <= scores[k] <= 10 or (scores[k] * 2) % 1 for k in DIMENSIONS):
        raise ValueError('All four scores must be in 0..10 at half-point increments')
    ev = review.get('evidence_by_dimension', {})
    if any(not isinstance(ev.get(k), str) or len(ev[k].strip()) < 10 for k in DIMENSIONS):
        raise ValueError('Scores require specific visual evidence for each dimension')
    result = sum(scores[k] * suite['weights'][k] for k in DIMENSIONS)
    return {'status': 'REVIEW_RECORDED_NOT_CERTIFIED', 'weighted_score': round(result, 2),
            'note': 'Human/model observations only; not an automated art-historical benchmark.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, help='An actual filled sample review')
    args = parser.parse_args()
    suite = read_json(ROOT / 'cases.json')
    validate_suite(suite)
    review = read_json(args.review or ROOT / 'review-template.json')
    print(json.dumps({'fixture': 'PASS', **validate_review(review, suite)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
