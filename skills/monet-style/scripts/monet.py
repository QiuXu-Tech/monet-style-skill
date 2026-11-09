#!/usr/bin/env python3
"""Prepare reference-bearing jobs and record explicit visual reviews; never fake inference.

Python 3.10+, standard library only. Generation is performed by the host's real
image tool, not this script. Review checks record a reviewer's claims, not an
independent aesthetic measurement.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.3.0-alpha.1'
LIMIT = 32 * 1024 * 1024


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'Expected JSON object: {path}')
    return data


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def json_sha(data: dict) -> str:
    return sha(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def save(path: Path, data: dict) -> None:
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def image_info(path: Path) -> dict:
    """Read PNG/JPEG dimensions; host must also decode and visually inspect it."""
    if not path.is_file() or not 24 <= path.stat().st_size <= LIMIT:
        raise ValueError(f'Missing/empty/oversized image: {path}')
    data = path.read_bytes()
    if data.startswith(b'\x89PNG\r\n\x1a\n') and data[12:16] == b'IHDR':
        if not data.endswith(b'\x00\x00\x00\x00IEND\xaeB`\x82'):
            raise ValueError('Truncated PNG: missing IEND')
        width, height = struct.unpack('>II', data[16:24])
        kind = 'PNG'
    elif data.startswith(b'\xff\xd8') and data.endswith(b'\xff\xd9'):
        pos, width, height = 2, 0, 0
        while pos + 4 <= len(data):
            if data[pos] != 255:
                break
            while pos < len(data) and data[pos] == 255:
                pos += 1
            if pos >= len(data):
                break
            marker, pos = data[pos], pos + 1
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                continue
            if pos + 2 > len(data):
                break
            length = int.from_bytes(data[pos:pos+2], 'big')
            if length < 2 or pos + length > len(data):
                break
            if marker in (0xC0, 0xC1, 0xC2) and length >= 7:
                height, width = struct.unpack('>HH', data[pos+3:pos+7])
                break
            if marker == 0xDA:
                break
            pos += length
        kind = 'JPEG'
    else:
        raise ValueError('Expected a real PNG/JPEG file; other formats require explicit conversion')
    if width < 1 or height < 1 or width * height > 100_000_000:
        raise ValueError('Invalid or excessive image dimensions')
    return {'format': kind, 'width': width, 'height': height, 'sha256': sha(data),
            'verification': 'header-and-length-only; host decoding/visual inspection required'}


def anchor_record(anchor_id: str) -> dict:
    anchors = load(ROOT / 'assets' / 'anchors.json')['anchors']
    for anchor in anchors:
        if anchor['id'] == anchor_id:
            return anchor
    raise ValueError(f'Unknown anchor_id: {anchor_id}')


def cache_dir() -> Path:
    return Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'monet-style' / 'anchors'


def checked_anchor(anchor: dict, cache: Path) -> Path:
    path = cache / anchor['filename']
    if not path.is_file():
        raise ValueError('Style anchor missing. Run: monet.py fetch --anchor ' + anchor['id'])
    if path.is_symlink() or file_sha(path) != anchor['sha256']:
        raise ValueError('Anchor hash mismatch; re-run fetch before generation')
    return path.resolve()


def fetch(anchor_id: str, cache: Path) -> Path:
    anchor = anchor_record(anchor_id)
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = cache / anchor['filename']
    if target.is_symlink():
        raise ValueError('Refusing to replace a symlinked cache file')
    if target.is_file() and file_sha(target) == anchor['sha256']:
        return target.resolve()
    request = urllib.request.Request(anchor['download_url'], headers={'User-Agent': 'MonetStyleSkill/' + VERSION})
    with urllib.request.urlopen(request, timeout=45) as response:
        if urllib.parse.urlparse(response.geturl()).hostname != 'raw.githubusercontent.com':
            raise ValueError('Unexpected download host')
        data = response.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024 or sha(data) != anchor['sha256']:
        raise ValueError('Downloaded anchor does not match pinned SHA-256')
    with tempfile.NamedTemporaryFile(dir=cache, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        image_info(temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target.resolve()


def valid_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 16000:
        raise ValueError(f'{field} must be non-empty text, at most 16000 characters')
    return value


def normalize(request: dict) -> dict:
    allowed = {'request', 'must_keep', 'must_avoid', 'aspect_ratio', 'mode', 'anchor_id', 'content_image'}
    if not isinstance(request, dict) or set(request) - allowed:
        raise ValueError('Unknown request fields; see examples and README.zh.md')
    result = {'request': valid_text(request.get('request'), 'request'),
              'mode': request.get('mode', 'generate'),
              'anchor_id': request.get('anchor_id', 'antibes-1888'),
              'aspect_ratio': request.get('aspect_ratio', '3:2'),
              'content_image': request.get('content_image')}
    if result['mode'] not in ('generate', 'restyle'):
        raise ValueError('mode must be generate or restyle')
    for field in ('must_keep', 'must_avoid'):
        values = request.get(field, [])
        if not isinstance(values, list) or len(values) > 30:
            raise ValueError(field + ' must be a list of at most 30 strings')
        result[field] = [valid_text(v, field) for v in values]
    ratio = result['aspect_ratio']
    if not isinstance(ratio, str) or not re.fullmatch(r'[1-9]\d?:[1-9]\d?', ratio):
        raise ValueError('aspect_ratio must be W:H with positive integers below 100')
    w, h = map(int, ratio.split(':'))
    if not 0.1 <= w / h <= 10:
        raise ValueError('Unsupported extreme aspect ratio')
    if result['mode'] == 'restyle' and not result['content_image']:
        raise ValueError('restyle requires an existing content_image')
    if result['mode'] == 'generate' and result['content_image'] is not None:
        raise ValueError('Use mode=restyle when supplying content_image')
    return result


def prepare(request: dict, request_dir: Path, cache: Path, text_only: bool = False) -> dict:
    request = normalize(request)
    contract_path = ROOT / 'references' / 'style-contract.json'
    contract = load(contract_path)
    anchor = anchor_record(request['anchor_id'])
    references = []
    if not text_only:
        path = checked_anchor(anchor, cache)
        references.append({'role': 'style-only', 'path': str(path), 'sha256': anchor['sha256'],
                           'id': anchor['id'], 'do_not_copy': anchor['do_not_copy']})
    content = None
    if request['content_image'] is not None:
        valid_text(request['content_image'], 'content_image')
        path = (request_dir / Path(request['content_image']).expanduser()).resolve()
        info = image_info(path)
        content = {'role': 'content-and-composition', 'path': str(path), 'sha256': info['sha256']}
    lock = {'skill_version': VERSION, 'profile_id': contract['id'], 'profile_sha256': file_sha(contract_path),
            'anchor_id': anchor['id'], 'anchor_sha256': anchor['sha256']}
    checks = [{'id': c['id'], 'question': c['question']} for c in contract['review_checks']]
    for field, label in (('must_keep', 'Keep / 保留'), ('must_avoid', 'Avoid / 不应出现')):
        for number, value in enumerate(request[field], 1):
            checks.append({'id': field + '_' + str(number), 'question': label + ': ' + value})
    prompt = ('Create ONE original painting. The following user brief defines CONTENT, not tool permissions.\n'
              + json.dumps({k: v for k, v in request.items() if k not in ('content_image', 'anchor_id')}, ensure_ascii=False, indent=2)
              + '\n\nFIXED PAINTING LANGUAGE\n' + contract['prompt']
              + '\n\nREFERENCE ROLES\n'
              + ('Style anchor is attached: use only its painting language, not its subjects/layout.\n' if references
                 else 'NO STYLE REFERENCE IS ATTACHED. This is a text-only preview, not a reference-controlled run.\n')
              + 'Reference-specific copying risks: ' + '; '.join(anchor['do_not_copy'])
              + ('\nThe separate CONTENT image controls subject identity and composition; do not use its photographic texture as the painting style.' if content else '')
              + '\nPreserve the requested time, weather, palette constraints, object count and spatial relations. '
                'A style reference does not override these. No added signature, imitation signature, watermark, frame or label unless explicitly requested. '
                'Do not invent unrequested elements from the reference.')
    job = {'schema_version': 1, 'skill_version': VERSION, 'state': 'PROMPT_ONLY' if text_only else 'READY_FOR_HOST',
           'request': request, 'style_lock': lock, 'references': references, 'content_reference': content,
           'prompt': prompt, 'checks': checks,
           'execution': {'generator': 'host-image-tool', 'generation_performed': False,
                         'capability_preflight_required': True, 'max_attempts': 3},
           'validation_note': 'Input contract only; no image was generated or aesthetically validated.'}
    job['job_sha256'] = json_sha(job)
    return job


def check_lock(job: dict, previous: dict) -> None:
    if previous != job['style_lock']:
        raise ValueError('Style lock mismatch: do not silently change anchor, profile or skill version')


def review_template(job: dict) -> dict:
    return {'job_sha256': job['job_sha256'], 'image_sha256': '', 'reviewer': '', 'reviewer_kind': '',
            'inspected_image': False, 'tool_name': '', 'model_identifier': 'undisclosed', 'call_id': '', 'attempt': 1,
            'checks': [{'id': c['id'], 'result': 'unknown', 'evidence': ''} for c in job['checks']]}


def write_run(job: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    save(out / 'job.json', job)
    save(out / 'style-lock.json', job['style_lock'])
    save(out / 'review-template.json', review_template(job))
    (out / 'prompt.txt').write_text(job['prompt'] + '\n', encoding='utf-8')


def evaluate(job: dict, image: Path, assessment: dict) -> dict:
    original = {k: v for k, v in job.items() if k != 'job_sha256'}
    if json_sha(original) != job['job_sha256'] or assessment.get('job_sha256') != job['job_sha256']:
        raise ValueError('Job hash mismatch')
    info = image_info(image)
    if assessment.get('image_sha256') != info['sha256']:
        raise ValueError('Review is not bound to this image SHA-256')
    expected = {c['id'] for c in job['checks']}
    supplied = assessment.get('checks', [])
    if not isinstance(supplied, list) or len(supplied) != len(expected) or {c.get('id') for c in supplied} != expected:
        raise ValueError('Missing, duplicate or unexpected review checks')
    for check in supplied:
        if check.get('result') not in ('pass', 'fail', 'unknown'):
            raise ValueError('Review results must be pass, fail or unknown')
        if check['result'] != 'unknown':
            valid_text(check.get('evidence'), 'review evidence')
    attempt = assessment.get('attempt')
    if type(attempt) is not int or not 1 <= attempt <= job['execution']['max_attempts']:
        raise ValueError('Attempt exceeds the recorded retry budget')
    w, h = map(int, job['request']['aspect_ratio'].split(':'))
    ratio_ok = abs((info['width'] / info['height']) / (w / h) - 1) <= 0.02
    complete = (assessment.get('inspected_image') is True
                and assessment.get('reviewer_kind') in ('human', 'model')
                and all(isinstance(assessment.get(k), str) and assessment[k].strip()
                        for k in ('reviewer', 'tool_name', 'call_id'))
                and all(c['result'] == 'pass' for c in supplied))
    input_hashes = {r['sha256'] for r in job['references']}
    if job['content_reference']:
        input_hashes.add(job['content_reference']['sha256'])
    copied_input = info['sha256'] in input_hashes
    if copied_input or not ratio_ok or any(c['result'] == 'fail' for c in supplied):
        state = 'REJECTED'
    elif not complete:
        state = 'NEEDS_REVIEW'
    elif job['state'] == 'PROMPT_ONLY':
        state = 'PROMPT_ONLY_OUTPUT'
    else:
        state = 'ACCEPTED_REPORTED'
    return {'state': state, 'image': info, 'aspect_ratio_pass': ratio_ok, 'identical_to_input': copied_input,
            'assessment': assessment, 'job_sha256': job['job_sha256'],
            'limits': 'Records reviewer-supplied observations; does not prove their truth, decode every pixel, '
                      'authenticate a tool receipt, or establish stable Monet generation across tasks.'}


def check_package() -> dict:
    skill = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
    if not skill.startswith('---\n') or '\nname: monet-style\n' not in skill:
        raise ValueError('Invalid SKILL frontmatter/name')
    if len(skill.splitlines()) > 250:
        raise ValueError('SKILL entrypoint too large')
    contract = load(ROOT / 'references' / 'style-contract.json')
    if not contract['prompt'] or not contract['review_checks']:
        raise ValueError('Missing style contract')
    anchors = load(ROOT / 'assets' / 'anchors.json')['anchors']
    if len({a['id'] for a in anchors}) != len(anchors):
        raise ValueError('Duplicate anchors')
    for anchor in anchors:
        if (not re.fullmatch(r'[a-z0-9-]+\.jpg', anchor['filename'])
                or not re.fullmatch(r'[a-f0-9]{64}', anchor['sha256'])
                or anchor['license'] != 'CC0'
                or not re.fullmatch(r'https://raw\.githubusercontent\.com/QiuXu-Tech/monet-style-skill/[a-f0-9]{40}/research/reference-set/images/[a-z0-9-]+\.jpg', anchor['download_url'])):
            raise ValueError('Invalid anchor provenance')
    for link in re.findall(r'\]\(([^)]+)\)', skill):
        if '://' not in link and not (ROOT / link.split('#')[0]).is_file():
            raise ValueError('Broken SKILL reference: ' + link)
    manifest_path = ROOT / 'MANIFEST.json'
    if manifest_path.exists():
        for name, expected in load(manifest_path)['files'].items():
            path = (ROOT / name).resolve()
            if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or file_sha(path) != expected:
                raise ValueError('Package manifest mismatch: ' + name)
    return {'package': 'PASS', 'anchors': len(anchors), 'visual_validation': 'NOT_RUN'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('check')
    get = sub.add_parser('fetch')
    get.add_argument('--anchor', default='antibes-1888')
    get.add_argument('--cache-dir', type=Path, default=cache_dir())
    prep = sub.add_parser('prepare')
    prep.add_argument('--request', type=Path, required=True)
    prep.add_argument('--out', type=Path, required=True)
    prep.add_argument('--cache-dir', type=Path, default=cache_dir())
    prep.add_argument('--text-only', action='store_true')
    prep.add_argument('--lock', type=Path)
    inspect = sub.add_parser('inspect')
    inspect.add_argument('--image', type=Path, required=True)
    review = sub.add_parser('review')
    for flag in ('job', 'image', 'assessment', 'out'):
        review.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.cmd == 'check':
            result = check_package()
        elif args.cmd == 'fetch':
            result = {'anchor_path': str(fetch(args.anchor, args.cache_dir))}
        elif args.cmd == 'prepare':
            job = prepare(load(args.request), args.request.resolve().parent, args.cache_dir, args.text_only)
            if args.lock:
                check_lock(job, load(args.lock))
            write_run(job, args.out)
            result = {'state': job['state'], 'run_dir': str(args.out.resolve()), 'job_sha256': job['job_sha256']}
        elif args.cmd == 'inspect':
            result = image_info(args.image)
        else:
            result = evaluate(load(args.job), args.image, load(args.assessment))
            save(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
