#!/usr/bin/env python3
"""Mock-server checks for the optional local ComfyUI adapter; no GPU inference."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import struct
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zlib

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import execute_comfyui as adapter
import monet


def png(w=1024, h=768):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    header = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    rows = (b"\x00" + (b"\xa5\xb4\xc0" * w)) * h
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def workflow():
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "test-model.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "OLD PROMPT", "clip": ["4", 1]}},
        "11": {"class_type": "LoadImage", "inputs": {"image": "missing.jpg"}},
        "12": {"class_type": "FakeStyleApplyForTestsOnly",
               "inputs": {"model": ["4", 0], "image": ["11", 0]}},
        "3": {"class_type": "KSampler",
              "inputs": {"model": ["12", 0], "positive": ["6", 0],
                         "negative": ["6", 0], "latent_image": ["5", 0], "seed": 1,
                         "steps": 20, "cfg": 7.5, "sampler_name": "euler", "scheduler": "normal"}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "test"}},
    }


MAP = {"positive": "6", "latent": "5", "sampler": "3",
       "style": "11", "save": "9", "checkpoint": "4"}


class FakeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def respond(self, code, payload):
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        data = self.rfile.read(length)
        if self.path == "/upload/image":
            import re
            match = re.search(rb'filename="([^"]+)"', data)
            self.server.image_name = match.group(1).decode() if match else ""
            self.respond(200, {"name": self.server.image_name, "type": "input"})
        elif self.path == "/prompt":
            body = json.loads(data)
            self.server.submitted = body
            self.respond(200, {"prompt_id": body["prompt_id"], "number": 1, "node_errors": {}})
        else:
            self.respond(404, {})

    def do_GET(self):
        if self.path.startswith("/history/"):
            task_id = self.path.rsplit("/", 1)[1]
            self.respond(200, {task_id: {"status": {"status_str": "success"},
                                         "outputs": {"9": {"images": [
                                             {"filename": "test.png", "subfolder": "", "type": "output"}
                                         ]}}}})
        elif self.path.startswith("/view?"):
            self.respond(200, png())
        else:
            self.respond(404, {})


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.style_file = self.path / "style.jpg"
        self.style_file.write_bytes(b"Fake image bytes for transport-only tests")
        self.anchor = dict(monet.anchor_record("antibes-1888"))
        self.anchor["sha256"] = monet.file_sha(self.style_file)
        self.lock = {
            "skill_version": monet.VERSION,
            "profile_sha256": monet.file_sha(SKILL / "references" / "style-contract.json"),
            "anchor_id": self.anchor["id"],
            "anchor_sha256": self.anchor["sha256"],
            "brushwork_variant": "baseline",
            "brushwork_overlay_sha256": None,
        }
        self.job = {
            "state": "READY_FOR_HOST", "execution": {"generation_performed": False},
            "request": {"mode": "generate", "content_image": None, "cleanup": None, "aspect_ratio": "4:3"},
            "prompt": "ONE PORT PAINTING: fixed brief and Monet painting-language text.",
            "style_lock": self.lock,
            "references": [{"role": "style-only", "id": self.anchor["id"],
                            "path": str(self.style_file), "sha256": self.anchor["sha256"]}],
            "content_reference": None,
        }
        self.job["job_sha256"] = monet.json_sha(self.job)
        self.job_file = self.path / "job.json"
        self.job_file.write_text(json.dumps(self.job))
        self.workflow_file = self.path / "workflow.json"
        self.workflow_file.write_text(json.dumps(workflow()))
        self.map_file = self.path / "map.json"
        self.map_file.write_text(json.dumps(MAP))
        self.patch_anchor = patch.object(adapter.monet, "anchor_record", return_value=self.anchor)
        self.patch_anchor.start()
        self.addCleanup(self.patch_anchor.stop)

    def test_local_only(self):
        for url in ("https://127.0.0.1:8188", "http://evil.example:8188",
                    "http://127.0.0.1:8188/path", "http://user@localhost:8188"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                adapter.require_local_url(url)
        self.assertEqual(adapter.require_local_url("http://127.0.0.1:8188"), "http://127.0.0.1:8188")

    def test_job_integrity(self):
        self.assertEqual(adapter.verify_job(self.job)["id"], "antibes-1888")
        modified = json.loads(json.dumps(self.job))
        modified["prompt"] = "changed after preparation"
        with self.assertRaisesRegex(ValueError, "integrity"):
            adapter.verify_job(modified)

    def test_prompt_only_blocked(self):
        job = dict(self.job, state="PROMPT_ONLY")
        with self.assertRaisesRegex(ValueError, "READY_FOR_HOST"):
            adapter.verify_job(job)

    def test_style_hash_required(self):
        self.style_file.write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            adapter.verify_job(self.job)

    def test_workflow_inserts_exact_prompt_anchor_and_seed(self):
        graph, model = adapter.prepare_workflow(self.job, workflow(), MAP, 1024, 768, 921, "anchor.jpg")
        self.assertEqual(graph["6"]["inputs"]["text"], self.job["prompt"])
        self.assertEqual(graph["11"]["inputs"]["image"], "anchor.jpg")
        self.assertEqual(graph["3"]["inputs"]["seed"], 921)
        self.assertEqual(graph["5"]["inputs"]["width"], 1024)
        self.assertEqual(graph["5"]["inputs"]["height"], 768)
        self.assertEqual(model, "test-model.safetensors")
        self.assertEqual(workflow()["6"]["inputs"]["text"], "OLD PROMPT")

    def test_style_must_reach_sampler(self):
        graph = workflow()
        graph["3"]["inputs"]["model"] = ["4", 0]
        with self.assertRaisesRegex(ValueError, "must all feed"):
            adapter.prepare_workflow(self.job, graph, MAP, 1024, 768, 921, "anchor.jpg")

    def test_wrong_aspect_fails_before_network(self):
        with self.assertRaisesRegex(ValueError, "aspect ratio"):
            adapter.prepare_workflow(self.job, workflow(), MAP, 768, 1024, 1, "anchor.jpg")

    def test_missing_node_mapping_fails(self):
        with self.assertRaisesRegex(ValueError, "six required"):
            adapter.prepare_workflow(self.job, workflow(), {"positive": "6"}, 1024, 768, 1, "a.jpg")

    def arguments(self, endpoint, directory, execute=False):
        return argparse.Namespace(job=self.job_file, workflow=self.workflow_file,
                                  mapping=self.map_file, out=self.path / directory,
                                  endpoint=endpoint, width=1024, height=768, seed=921,
                                  timeout=3, execute=execute)

    def test_dry_run_no_network(self):
        with patch.object(adapter.ComfyClient, "upload", side_effect=AssertionError("Network")):
            result = adapter.execute(self.arguments("http://127.0.0.1:65500", "dry"))
        self.assertEqual(result["status"], "DRY_RUN_NO_MODEL_CALL")
        self.assertFalse(result["generation_performed"])
        manifest = json.loads((self.path / "dry/request.json").read_text())
        self.assertEqual(manifest["workflow"]["6"]["inputs"]["text"], self.job["prompt"])

    def test_mock_local_full_execution_and_receipt(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        result = adapter.execute(self.arguments(f"http://127.0.0.1:{server.server_port}",
                                                "real-mock", execute=True))
        self.assertEqual(result["status"], "REQUIRES_VISUAL_REVIEW")
        self.assertTrue(result["generation_performed"])
        self.assertEqual(result["actual_size"], [1024, 768])
        self.assertEqual(server.submitted["prompt"]["6"]["inputs"]["text"], self.job["prompt"])
        self.assertEqual(server.submitted["prompt"]["11"]["inputs"]["image"], server.image_name)
        self.assertEqual(server.submitted["prompt"]["3"]["inputs"]["seed"], 921)
        self.assertTrue((self.path / "real-mock/candidate.png").exists())

    def test_submitted_but_missing_receipt_is_unknown_not_retryable(self):
        args = self.arguments("http://127.0.0.1:8188", "lost-ack", execute=True)
        with patch.object(adapter.ComfyClient, "upload") as upload, \
             patch.object(adapter.ComfyClient, "submit", side_effect=TimeoutError("lost ACK")):
            upload.return_value = "monet-" + "placeholder"
            # Return the exact expected uploaded name from the generated request.
            def upload_style(source, task_id):
                return f"monet-{task_id}-{Path(source).name}"
            upload.side_effect = upload_style
            with self.assertRaises(TimeoutError):
                adapter.execute(args)
        receipt = json.loads((self.path / "lost-ack/receipt.json").read_text())
        self.assertEqual(receipt["status"], "OUTCOME_UNKNOWN")
        self.assertTrue(receipt["submission_attempted"])
        self.assertFalse(receipt["generation_performed"])

    def test_output_dir_refuses_overwrite(self):
        args = self.arguments("http://127.0.0.1:65500", "dry-again")
        adapter.execute(args)
        with self.assertRaises(FileExistsError):
            adapter.execute(args)


if __name__ == "__main__":
    unittest.main()
