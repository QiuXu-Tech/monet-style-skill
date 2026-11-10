#!/usr/bin/env python3
"""Explicit, local-only ComfyUI executor for a prepared Monet generation job.

This optional adapter never reads chat history or evaluation reports. It requires
an exported API workflow with a connected style-image node. It cannot prove the
model has semantically applied that reference: all outputs need visual review.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
import uuid

import monet

MAX_BYTES = 32 * 1024 * 1024
NODE_TYPES = {
    "positive": "CLIPTextEncode",
    "latent": "EmptyLatentImage",
    "sampler": "KSampler",
    "style": "LoadImage",
    "save": "SaveImage",
    "checkpoint": "CheckpointLoaderSimple",
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def document(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return monet.load(path)


def require_local_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "http" or parts.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("Only explicit HTTP loopback ComfyUI endpoints are supported")
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ValueError("Endpoint must be a bare local server URL without credentials or paths")
    if parts.port is None:
        raise ValueError("Endpoint must specify the local port")
    return url.rstrip("/")


def verify_job(job: dict) -> dict:
    if job.get("state") != "READY_FOR_HOST" or job.get("execution", {}).get("generation_performed") is not False:
        raise ValueError("Job must be READY_FOR_HOST, not PROMPT_ONLY or already executed")
    claimed = job.get("job_sha256")
    if not isinstance(claimed, str) or monet.json_sha({k: v for k, v in job.items() if k != "job_sha256"}) != claimed:
        raise ValueError("Prepared job integrity mismatch")
    req = job["request"]
    if req["mode"] != "generate" or req.get("content_image") is not None or req.get("cleanup"):
        raise ValueError("This first adapter supports only a single text-to-image job with a style anchor")
    refs = job.get("references")
    if not isinstance(refs, list) or len(refs) != 1 or refs[0].get("role") != "style-only":
        raise ValueError("Exactly one verified style-only reference is required")
    reference = refs[0]
    path = Path(reference["path"])
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("Invalid style reference path")
    if monet.file_sha(path) != reference["sha256"]:
        raise ValueError("Style reference SHA-256 mismatch")
    anchor = monet.anchor_record(reference["id"])
    if reference["sha256"] != anchor["sha256"]:
        raise ValueError("Style reference does not match the pinned anchor")
    lock = job["style_lock"]
    contract = monet.ROOT / "references" / "style-contract.json"
    if (lock["skill_version"] != monet.VERSION or
            lock["profile_sha256"] != monet.file_sha(contract) or
            lock["anchor_sha256"] != anchor["sha256"] or
            lock["anchor_id"] != anchor["id"]):
        raise ValueError("Stale or inconsistent style lock")
    variant = lock.get("brushwork_variant")
    overlay = monet.ROOT / "references" / "regional-brushwork-p0.txt"
    if variant not in ("baseline", "regional-p0"):
        raise ValueError("Unknown brushwork variant")
    if variant == "regional-p0":
        if lock.get("brushwork_overlay_sha256") != monet.file_sha(overlay):
            raise ValueError("P0 overlay SHA-256 mismatch")
    elif lock.get("brushwork_overlay_sha256") is not None:
        raise ValueError("Baseline must not include a P0 overlay")
    if not isinstance(job.get("prompt"), str) or not job["prompt"].strip():
        raise ValueError("Empty prepared prompt")
    return reference


def ancestors(graph: dict, node_id: str) -> set[str]:
    seen: set[str] = set()
    todo = [node_id]
    while todo:
        current = todo.pop()
        if current in seen or current not in graph:
            continue
        seen.add(current)
        for value in graph[current].get("inputs", {}).values():
            if isinstance(value, list) and len(value) == 2 and str(value[0]) in graph:
                todo.append(str(value[0]))
    return seen


def prepare_workflow(job: dict, workflow: dict, nodes: dict, width: int, height: int,
                     seed: int, image_name: str) -> tuple[dict, str]:
    if not 256 <= width <= 2048 or not 256 <= height <= 2048:
        raise ValueError("Dimensions must be between 256 and 2048")
    if type(seed) is not int or not 0 <= seed < (1 << 64):
        raise ValueError("Seed must be an unsigned 64-bit integer")
    target_w, target_h = map(int, job["request"]["aspect_ratio"].split(":"))
    if abs((width / height) / (target_w / target_h) - 1) > 0.02:
        raise ValueError("Configured size is inconsistent with requested aspect ratio")
    if not isinstance(workflow, dict) or not isinstance(nodes, dict) or set(nodes) != set(NODE_TYPES):
        raise ValueError("Workflow and mapping must identify the six required node roles")
    graph = copy.deepcopy(workflow)
    ids = {role: str(nodes[role]) for role in NODE_TYPES}
    if len(set(ids.values())) != len(ids):
        raise ValueError("Role node IDs must be distinct")
    for role, node_id in ids.items():
        if node_id not in graph or graph[node_id].get("class_type") != NODE_TYPES[role]:
            raise ValueError(f"Missing expected {NODE_TYPES[role]} node: {role}")
    upstream = ancestors(graph, ids["sampler"])
    if not {ids["style"], ids["positive"], ids["latent"], ids["checkpoint"]} <= upstream:
        raise ValueError("Style, prompt, latent, and model must all feed the sampler")
    if ids["sampler"] not in ancestors(graph, ids["save"]):
        raise ValueError("Sampler output must reach SaveImage")
    inputs = lambda role: graph[ids[role]]["inputs"]
    name = inputs("checkpoint").get("ckpt_name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Checkpoint name missing from workflow")
    if not isinstance(inputs("sampler").get("steps"), int):
        raise ValueError("Sampler steps must be an integer")
    inputs("positive")["text"] = job["prompt"]
    inputs("latent").update({"width": width, "height": height, "batch_size": 1})
    inputs("sampler")["seed"] = seed
    inputs("style")["image"] = image_name
    return graph, name


class ComfyClient:
    def __init__(self, base: str):
        self.base = require_local_url(base)
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, route: str, data: bytes | None = None, content_type: str | None = None) -> bytes:
        headers = {"Accept": "application/json" if route.startswith(("/prompt", "/history")) else "*/*"}
        if content_type:
            headers["Content-Type"] = content_type
        request = Request(self.base + route, data=data, headers=headers,
                          method="POST" if data is not None else "GET")
        with self.opener.open(request, timeout=30) as result:
            output = result.read(MAX_BYTES + 1)
        if len(output) > MAX_BYTES:
            raise ValueError("ComfyUI response too large")
        return output

    def upload(self, source: Path, task_id: str) -> str:
        name = f"monet-{task_id}-{source.name}"
        boundary = "----monet" + task_id.replace("-", "")
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
                "Content-Type: image/jpeg\r\n\r\n").encode() + source.read_bytes() + (
                f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\ninput"
                f"\r\n--{boundary}--\r\n").encode()
        data = json.loads(self.request("/upload/image", body, f"multipart/form-data; boundary={boundary}"))
        remote_name = data.get("name")
        if not isinstance(remote_name, str) or remote_name != name or data.get("type") != "input":
            raise ValueError("Unexpected ComfyUI image-upload acknowledgment")
        return remote_name

    def submit(self, graph: dict, task_id: str) -> None:
        body = document({"prompt": graph, "prompt_id": task_id, "client_id": "monet-style"})
        response = json.loads(self.request("/prompt", body, "application/json"))
        if response.get("prompt_id") != task_id or response.get("error") or response.get("node_errors"):
            raise ValueError("ComfyUI rejected or changed the submitted task")

    def download_image(self, task_id: str, save_node: str, timeout_seconds: int) -> bytes:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            history = json.loads(self.request("/history/" + task_id))
            item = history.get(task_id)
            if item:
                status = item.get("status", {})
                if status.get("status_str") in ("error", "failed"):
                    raise ValueError("ComfyUI execution failed")
                images = item.get("outputs", {}).get(save_node, {}).get("images", [])
                if len(images) != 1:
                    raise ValueError("Expected exactly one image from mapped SaveImage node")
                record = images[0]
                filename = record.get("filename", "")
                if (not isinstance(filename, str) or not filename or
                        "/" in filename or "\\" in filename or ".." in filename or
                        record.get("type") != "output"):
                    raise ValueError("Unsafe image output metadata")
                query = urlencode({"filename": filename, "subfolder": record.get("subfolder", ""),
                                   "type": "output"})
                return self.request("/view?" + query)
            time.sleep(0.5)
        raise TimeoutError("ComfyUI completion unknown; do not automatically retry")


def execute(args: argparse.Namespace) -> dict:
    job = read_json(args.job)
    reference = verify_job(job)
    original = read_json(args.workflow)
    mapping = read_json(args.mapping)
    base = require_local_url(args.endpoint)
    task_id = str(uuid.uuid4())
    requested_name = f"monet-{task_id}-{Path(reference['path']).name}"
    graph, checkpoint = prepare_workflow(job, original, mapping, args.width, args.height,
                                         args.seed, requested_name)
    args.out.mkdir(parents=True, exist_ok=False, mode=0o700)
    record = {
        "task_id": task_id, "job_sha256": job["job_sha256"],
        "prompt_sha256": digest(job["prompt"].encode("utf-8")),
        "style_anchor_sha256": reference["sha256"],
        "brushwork_variant": job["style_lock"]["brushwork_variant"],
        "model_checkpoint_declared": checkpoint, "seed": args.seed,
        "requested_size": [args.width, args.height], "backend": base,
        "workflow_sha256": digest(document(graph)), "generation_performed": False,
        "visual_review": "NOT_PERFORMED",
    }
    write_json(args.out / "request.json", {"metadata": record, "workflow": graph})
    if not args.execute:
        record["status"] = "DRY_RUN_NO_MODEL_CALL"
        write_json(args.out / "receipt.json", record)
        return record

    client = ComfyClient(base)
    try:
        uploaded_name = client.upload(Path(reference["path"]), task_id)
        if uploaded_name != requested_name:
            raise ValueError("Uploaded image name differs from bound workflow input")
        record["submission_attempted"] = True
        client.submit(graph, task_id)
        record["submission_confirmed"] = True
        image_data = client.download_image(task_id, str(mapping["save"]), args.timeout)
        image_path = args.out / "candidate.png"
        image_path.write_bytes(image_data)
        info = monet.image_info(image_path)
        record.update({"generation_performed": True,
                       "output_path": str(image_path.resolve()),
                       "output_sha256": info["sha256"],
                       "actual_size": [info["width"], info["height"]]})
        if info["format"] != "PNG" or [info["width"], info["height"]] != [args.width, args.height]:
            record["status"] = "REJECTED_TECHNICAL_OUTPUT"
        else:
            record["status"] = "REQUIRES_VISUAL_REVIEW"
        write_json(args.out / "receipt.json", record)
        return record
    except Exception as exc:
        record["status"] = "OUTCOME_UNKNOWN" if record.get("submission_attempted") else "FAILED_BEFORE_SUBMISSION_ATTEMPT"
        record["error"] = str(exc)
        write_json(args.out / "receipt.json", record)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8188")
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--execute", action="store_true", help="Actually invoke a local ComfyUI server")
    args = parser.parse_args()
    try:
        if not 1 <= args.timeout <= 360:
            raise ValueError("Timeout must be within 1-360 seconds")
        result = execute(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] != "REJECTED_TECHNICAL_OUTPUT" else 2
    except (ValueError, OSError, KeyError, TypeError, TimeoutError) as error:
        print("ERROR: " + str(error), file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
