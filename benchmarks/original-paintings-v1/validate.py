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
CURRENT_PROTOCOL = '1.1.0'
WEIGHTS = dict(zip(DIMENSIONS, (0.3, 0.3, 0.3, 0.1)))


def read_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        raise ValueError(f'Expected an object: {path}')
    return obj


def validate_suite(suite: dict) -> None:
    if suite.get('status') != 'NOT_RUN' or suite.get('models_or_apis_tested') != []:
        raise ValueError('Fixture must not claim that images have been generated')
    weights = suite.get('weights', {})
    if weights != WEIGHTS:
        raise ValueError('Weights must remain brushwork/color/atmosphere/artifact_control = 30/30/30/10')
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


def validate_image(path_value: object, expected_hash: object, label: str) -> None:
    image = Path(path_value or '')
    if not image.is_file():
        raise ValueError(f'Inspect the real image file for {label}; a description is not evidence')
    data = image.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError(f'{label} hash mismatch')
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


def validate_original(review: dict, case: dict) -> None:
    original = review.get('original_reference', {})
    if (original.get('institution_inventory') != case['institution_inventory'] or
            original.get('museum_url') != case['museum_url']):
        raise ValueError('Original identity must match this case inventory and registered museum source')
    source = original.get('image_source_url')
    if not isinstance(source, str) or not source.startswith('https://'):
        raise ValueError('Record the source URL of the actually inspected original reproduction')
    if original.get('role') != 'EVALUATION_ONLY':
        raise ValueError('Target original must remain evaluation-only')
    if original.get('definition_scores') != dict.fromkeys(DIMENSIONS, 10):
        raise ValueError('The original is the four-dimensional 10-point definition anchor, not a generated sample')
    validate_image(original.get('image_path'), original.get('image_sha256'), 'Original')
    if original.get('image_sha256') == review.get('output_sha256'):
        raise ValueError('The inspected original cannot be submitted as the generated output')


def validate_leakage(review: dict) -> bool | None:
    checks = review.get('reference_leakage_review', {})
    expected = {'signature', 'distinctive_composition'}
    if set(checks) != expected:
        raise ValueError('Inspect both signature and distinctive composition for reference leakage')
    results = []
    for name in sorted(expected):
        check = checks[name]
        if not isinstance(check, dict) or check.get('result') not in ('pass', 'fail', 'unknown'):
            raise ValueError('Leakage checks require pass/fail/unknown')
        result = check['result']
        if result != 'unknown' and not (isinstance(check.get('evidence'), str) and check['evidence'].strip()):
            raise ValueError('Signature and composition decisions require localized evidence')
        results.append(result)
    return False if 'fail' in results else None if 'unknown' in results else True


def validate_review(review: dict, suite: dict) -> dict:
    protocol = review.get('protocol_version', '1.0.0')
    if protocol not in ('1.0.0', CURRENT_PROTOCOL):
        raise ValueError('Unsupported review protocol version')
    current = protocol == CURRENT_PROTOCOL
    result_meta = {'protocol_version': protocol, 'legacy_protocol': not current}
    scores = review.get('scores', {})
    if review.get('status') == 'NOT_RUN':
        if (review.get('generation_performed') is not False or
                any(v is not None for v in scores.values()) or
                (current and any(review.get(k) is not None for k in ('output_image_path', 'output_sha256', 'actual_dimensions')))):
            raise ValueError('NOT_RUN cannot contain output or scores')
        return {'status': 'NOT_RUN', 'weighted_score': None, **result_meta}
    cases = {item['id']: item for item in suite['cases']}
    if review.get('case_id') not in cases:
        raise ValueError('Review has unknown case ID')
    if review.get('arm') not in ('baseline', 'skill'):
        raise ValueError('Review must identify a named experimental arm')
    if review.get('generation_performed') is not True:
        raise ValueError('Cannot review an ungenerated image')
    validate_image(review.get('output_image_path'), review.get('output_sha256'), 'Output')
    who = review.get('reviewer', {})
    if not (who.get('kind') in ('human', 'model') and who.get('id') and who.get('inspected_original') is True and who.get('inspected_output') is True):
        raise ValueError('Reviewer and actual inspection must be recorded')
    gates = review.get('hard_gates', {})
    expected_gates = (*GATES, 'reference_leakage') if current else GATES
    if set(gates) != set(expected_gates) or any(type(v) is not bool and v is not None for v in gates.values()):
        raise ValueError('Invalid content/format gates')
    if current:
        validate_original(review, cases[review['case_id']])
        if gates['reference_leakage'] is not validate_leakage(review):
            raise ValueError('reference_leakage gate must agree with signature/composition inspection')
    if any(v is not True for v in gates.values()):
        if current and any(v is not None for v in scores.values()):
            raise ValueError('Failed or unknown hard gates require null style scores')
        return {'status': 'REJECTED' if False in gates.values() else 'NEEDS_REVIEW', 'weighted_score': None, **result_meta}
    if set(scores) != set(DIMENSIONS):
        raise ValueError('Missing or extra score dimension')
    if any(type(scores[k]) not in (int, float) or not 0 <= scores[k] <= 10 or (scores[k] * 2) % 1 for k in DIMENSIONS):
        raise ValueError('All four scores must be in 0..10 at half-point increments')
    ev = review.get('evidence_by_dimension', {})
    if any(not isinstance(ev.get(k), str) or len(ev[k].strip()) < 10 for k in DIMENSIONS):
        raise ValueError('Scores require specific visual evidence for each dimension')
    result = sum(scores[k] * suite['weights'][k] for k in DIMENSIONS)
    return {'status': 'REVIEW_RECORDED_NOT_CERTIFIED', 'weighted_score': round(result, 2), **result_meta,
            'reviewer_kind': who['kind'],
            'note': ('Human/model observations only; file hashes bind declared evidence, not its authenticity or aesthetic truth. '
                     + ('Historical 1.0.0 record: original provenance and leakage gates were not verified under 1.1.0.' if not current else
                        'The original defines 10 in each dimension for this comparison; no visual improvement is certified.'))}


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
