#!/usr/bin/env python3
"""Inspect one pinned upstream wrapper with shape-only stubs; never generate images.

Supply a separately obtained InstantStyle ip_adapter/ip_adapter.py matching the
SHA-256 below. No downloads, model imports, credentials or source writes occur.
Only that verified file's IPAdapterXL.generate AST is executed with inert stubs.
This is a narrow control-flow/shape audit, not a torch or image-quality test.
"""
import argparse
import ast
import contextlib
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

EXPECTED_SHA256 = "e7ab0279938947ff162866dfb4e427f4925806438233878011d4d968980c5e1b"


class Tensor:
    def __init__(self, shape):
        self.shape = tuple(shape)

    def repeat(self, *factors):
        return Tensor(tuple(a * b for a, b in zip(self.shape, factors)))

    def view(self, *shape):
        shape = list(shape)
        total = math.prod(self.shape)
        if -1 in shape:
            shape[shape.index(-1)] = total // math.prod(v for v in shape if v != -1)
        if math.prod(shape) != total:
            raise ValueError("view element count mismatch")
        return Tensor(shape)

    def __imul__(self, value):
        return self


class Image:
    pass


def cat(tensors, dim):
    shape = list(tensors[0].shape)
    for item in tensors[1:]:
        if any(item.shape[i] != shape[i] for i in range(len(shape)) if i != dim):
            raise ValueError(f"cat shape mismatch: {[t.shape for t in tensors]}")
    shape[dim] = sum(t.shape[dim] for t in tensors)
    return Tensor(shape)


class Pipe:
    def encode_prompt(self, prompt, num_images_per_prompt, **kwargs):
        batch = (len(prompt) if isinstance(prompt, list) else 1) * num_images_per_prompt
        return (Tensor((batch, 77, 2048)), Tensor((batch, 77, 2048)),
                Tensor((batch, 1280)), Tensor((batch, 1280)))

    def __call__(self, **kwargs):
        self.called = kwargs
        return SimpleNamespace(images=["symbolic-output-not-an-image"])


class Adapter:
    device = "symbolic-no-device"

    def __init__(self):
        self.pipe = Pipe()
        self.received = None

    def set_scale(self, scale):
        self.scale = scale

    def get_image_embeds(self, pil_image, content_prompt_embeds=None):
        self.received = content_prompt_embeds
        batch = 1 if isinstance(pil_image, Image) else len(pil_image)
        if content_prompt_embeds is not None:
            # For the tested single-image case, subtraction broadcasts the batch.
            batch = max(batch, content_prompt_embeds.shape[0])
        return Tensor((batch, 4, 2048)), Tensor((batch, 4, 2048))


def audit(source_file):
    source = source_file.read_bytes()
    if hashlib.sha256(source).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Source checksum mismatch; refusing to execute an unreviewed function")
    tree = ast.parse(source.decode("utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "IPAdapterXL")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "generate")
    method.decorator_list = []
    env = {"torch": SimpleNamespace(inference_mode=contextlib.nullcontext, cat=cat),
           "Image": SimpleNamespace(Image=Image), "List": list,
           "get_generator": lambda *args: None}
    code = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
    exec(compile(code, "verified_upstream_generate", "exec"), env)
    cases = [
        ("no_subtraction_batch2", {"num_samples": 2}),
        ("text_subtraction_single", {"num_samples": 1, "neg_content_prompt": "a cathedral"}),
        ("precomputed_subtraction_single", {"num_samples": 1, "neg_content_emb": Tensor((1, 1280))}),
        ("text_subtraction_batch2", {"num_samples": 2, "neg_content_prompt": "a cathedral"}),
        ("guidance_forwarding", {"num_samples": 1, "guidance_scale": 5.0}),
    ]
    results = []
    for name, kwargs in cases:
        adapter = Adapter()
        result = {"case": name}
        try:
            env["generate"](adapter, Image(), prompt="a modern railway station", **kwargs)
            result.update(ran=True, received_content_shape=(adapter.received.shape if adapter.received else None),
                          forwarded_guidance_scale=adapter.pipe.called.get("guidance_scale"))
        except ValueError as error:
            result.update(ran=False, exception_type=type(error).__name__, message=str(error))
        results.append(result)
    observed = (results[0]["ran"] and results[1]["ran"]
                and results[2]["received_content_shape"] is None
                and not results[3]["ran"] and results[3]["exception_type"] == "ValueError"
                and results[4]["forwarded_guidance_scale"] == 5.0)
    if not observed:
        raise AssertionError("Observed behavior differs from the recorded audit")
    return {"scope": "AST-extracted wrapper with symbolic shapes, NOT model inference or image validation",
            "revision": "6b40588e263c958653353ec24eb7eb990cfa3da7",
            "source_sha256": EXPECTED_SHA256, "observations_confirmed": 5,
            "upstream_behavior_risks_reproduced": 2, "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = audit(args.source_file)
    data = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.write_text(data, encoding="utf-8")
    print(data)
