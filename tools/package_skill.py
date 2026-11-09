#!/usr/bin/env python3
"""Build a deterministic lightweight ZIP; no research corpus or user outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skills' / 'monet-style'


def build(output: Path) -> dict:
    files = {}
    for path in sorted(SOURCE.rglob('*')):
        if path.is_symlink():
            raise ValueError('No symlinks allowed in package: ' + str(path))
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            files[path.relative_to(SOURCE).as_posix()] = path.read_bytes()
    manifest = {'version': '0.3.0-alpha.1', 'files': {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}}
    files['MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo('monet-style/' + name, date_time=(2026, 11, 9, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return {'file': str(output), 'bytes': output.stat().st_size, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'entries': len(files)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(build(parser.parse_args().output), indent=2))
