---
name: monet-style
description: Generate or restyle raster images in a Claude Monet-inspired painting language when the user requests 莫奈风格、莫奈油画、Monet style, or a consistent Monet series. Preserve the user's subject and composition, attach a verified style-only reference, call the host's actual image tool, then inspect and review when the host permits. Not for art-history-only questions, exact famous-painting copies, or other artists' styles.
license: MIT; reference images have separate CC0 provenance in assets/anchors.json.
compatibility: Python 3.10+ for local checks; an actual image-generation tool with image-reference input is required for reference-controlled output. First anchor fetch needs HTTPS access to the pinned public GitHub asset.
metadata:
  author: QiuXu-Tech
  version: "0.3.0-alpha.1"
---
# Monet Style

Produce a real image, not merely a prompt, when a compatible image tool is present. This is an experimental, installable workflow; input consistency is not a proven guarantee of visual consistency. Respect higher-priority tool instructions and safety rules.

## 1. Read intent and verify capability

Read [host-tools.md](references/host-tools.md). Discover the current tool's real schema; never invent `seed`, image paths, model IDs, IP-Adapter, ControlNet or reference parameters. Prefer the host's built-in image tool; do not silently switch to paid APIs or install models.

A reference-controlled run requires actual reference pixels to reach the image tool, not just a URL written in prose. For photo restyling, both the existing content image and the separate style reference must be supported. If unsupported, report `NOT_SUPPORTED` and the exact missing capability. Only offer/output a text preview as `PROMPT_ONLY`, never as a generated image.

If no filesystem or Python exists, report that the validated workflow is unavailable. Do not pretend checks ran. An explicitly requested manual text-only preview may still use the written style reference.

## 2. Prepare the brief without changing it

Use [request examples](examples/modern-city.json) as the schema. Preserve the original request verbatim. Extract only observable `must_keep` and `must_avoid` conditions; do not weaken difficult conditions. Use `mode: restyle` only when the user supplied an existing image. Never invent a missing source photo.

Default profile: `monet-1880s-study-v1`, a reversible first implementation baseline—not a declaration that Monet's whole career has one style. Read [painting-language.md](references/painting-language.md). Default anchor is `antibes-1888`; `pourville-1882` is an explicit alternative, not an automatic replacement based on subject. Do not blend periods or silently substitute a later water-lily style. If the user explicitly asks for another period, explain that this preset has not covered it; resolve that conflict instead of relabeling the output.

Find the installed skill directory (the directory containing this SKILL.md); call it `SKILL_ROOT`. Save task files in a new user-project output folder, not inside the installed skill or a public repository. Relative content-image paths resolve beside the request JSON.

```bash
python3 "$SKILL_ROOT/scripts/monet.py" check
python3 "$SKILL_ROOT/scripts/monet.py" fetch --anchor antibes-1888
python3 "$SKILL_ROOT/scripts/monet.py" prepare --request request.json --out monet-run-001
```

Select the requested anchor in request.json and fetch that same ID. `prepare` never silently downloads files. A local cache hash mismatch blocks preparation. To continue an existing series, add `--lock previous-run/style-lock.json`; changed anchors/contracts are rejected. The lock governs inputs only, not model versions or pixel determinism.

## 3. Inspect and generate

Open the selected anchor with a real image viewer. For restyling also open the content photo. Read `job.json` and `prompt.txt`; keep the fixed style passage unchanged. Explicitly assign roles: STYLE reference controls painting language; CONTENT photo controls identity/layout; user brief controls required objects, light and relations.

Invoke the actual image-generation/editing tool now. Map supported fields from the job into its real schema. If it infers instructions from context, supply the resolved brief through its supported context mechanism; do not populate a deprecated prompt argument. If local paths are not valid attachments, use the host's supported image-attachment step or stop. Never pass an opaque fake asset ID. Preserve provider-required provenance/watermarks; the instruction not to add painted signatures does not authorize stripping provenance.

Ask for one candidate unless the user requested multiple. Keep the original requested weather—even a sunny anchor does not authorize changing night to daytime. Do not inject cottages, sailboats, cliffs, figures or signatures from the anchor unless the user's brief calls for them. Save the real tool result when the host supports it. `READY_FOR_HOST` is not success.

## 4. Inspect, record and repair

When allowed by the host, open the actual candidate and compare it with both the brief and the anchor using [review.md](references/review.md). Copy `review-template.json` to an assessment file. Leave unobserved checks `unknown`; write concrete evidence for every pass/fail. Record the real tool/call identifier when exposed. Record `unavailable` only if the host genuinely does not expose it; never fabricate a receipt.

```bash
python3 "$SKILL_ROOT/scripts/monet.py" inspect --image candidate.png
python3 "$SKILL_ROOT/scripts/monet.py" review --job monet-run-001/job.json \
  --image candidate.png --assessment assessment.json --out review-001.json
```

Bind the assessment to the returned image SHA-256 and job SHA-256. Header checks alone do not decode all pixels or judge art. `ACCEPTED_REPORTED` means the named reviewer reported all checks passing, not independent certification.

For a failed candidate, identify one concrete defect and make the smallest supported correction. Preserve original content requirements and the same style lock; keep original candidates and append each actual edit instruction and tool call to the run record. At most two extra attempts (three total) without further user authorization. Do not hide failures or spend indefinitely selecting a lucky result.

If the tool cannot return an inspectable file, or host rules require ending immediately after image generation, deliver the image as an **unreviewed candidate**. Do not call other tools in violation of the host's rules. Do not claim the review was completed; continue review only when allowed in a subsequent interaction.

## 5. Deliver

Return the real image in the host-supported format and, where allowed, one short sentence stating any unresolved issue. Do not expose long prompts/metadata by default. If generation failed, say so; never substitute a museum reference image or a synthetic test fixture as the generated result. Never claim a test suite establishes stable Monet aesthetics.
