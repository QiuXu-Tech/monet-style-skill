---
name: monet-style
description: Generate or restyle raster images in a Claude Monet-inspired painting language when the user requests 莫奈风格、莫奈油画、Monet style, or a consistent Monet series. Preserve the user's subject and composition, attach a verified style-only reference, and optionally activate a clean-remake route for repeated micro-texture artifacts. Call the host's actual image tool, then inspect and review when the host permits. Not for art-history-only questions, exact famous-painting copies, or other artists' styles.
license: MIT; reference images have separate CC0 provenance in assets/anchors.json.
compatibility: Python 3.10+ for local checks; Pillow is additionally required for cleanup preprocessing; an actual image-generation tool with image-reference input is required for reference-controlled output. First anchor fetch needs HTTPS access to the pinned public GitHub asset.
metadata:
  author: QiuXu-Tech
  version: "0.4.0-alpha.4"
---
# Monet Style

Produce a real image, not merely a prompt, when a compatible image tool is present. This is an experimental, installable workflow; input consistency is not a proven guarantee of visual consistency. Respect higher-priority tool instructions and safety rules.

## 1. Read intent and verify capability

Read [host-tools.md](references/host-tools.md). Discover the current tool's real schema; never invent `seed`, image paths, model IDs, IP-Adapter, ControlNet or reference parameters. Prefer the host's built-in image tool; do not silently switch to paid APIs or install models.

A reference-controlled run requires actual reference pixels to reach the image tool, not just a URL written in prose. For photo restyling, both the existing content image and the separate style reference must be supported. The cleanup route adds extra structure/light references; only use it when the host can clearly preserve their distinct roles. If unsupported, report `NOT_SUPPORTED` and the exact missing capability. Only offer/output a text preview as `PROMPT_ONLY`, never as a generated image.

If no filesystem or Python exists, report that the validated workflow is unavailable. Do not pretend checks ran. An explicitly requested manual text-only preview may still use the written style reference.

## 2. Prepare the brief without changing it

Use [request examples](examples/modern-city.json) as the schema. Preserve the original request verbatim. Extract only observable `must_keep` and `must_avoid` conditions; do not weaken difficult conditions. Use `mode: restyle` only when the user supplied an existing image. Never invent a missing source photo.

Default profile: `monet-1880s-study-v2`, a reversible first implementation baseline—not a declaration that Monet's whole career has one style. Read [painting-language.md](references/painting-language.md). Default anchor is `antibes-1888`; `pourville-1882` is an explicit alternative, not an automatic replacement based on subject. Do not blend periods or silently substitute a later water-lily style. If the user explicitly asks for another period, explain that this preset has not covered it; resolve that conflict instead of relabeling the output.

Find the installed skill directory (the directory containing this SKILL.md); call it `SKILL_ROOT`. Save task files in a new user-project output folder, not inside the installed skill or a public repository. Relative content-image paths resolve beside the request JSON.

```bash
python3 "$SKILL_ROOT/scripts/monet.py" check
python3 "$SKILL_ROOT/scripts/monet.py" fetch --anchor antibes-1888
python3 "$SKILL_ROOT/scripts/monet.py" prepare --request request.json --out monet-run-001
```

Select the requested anchor in request.json and fetch that same ID. `prepare` never silently downloads files. A local cache hash mismatch blocks preparation. To continue an existing series, add `--lock previous-run/style-lock.json`; changed anchors/contracts are rejected. The lock governs inputs only, not model versions or pixel determinism.

### Cleanup route

The cleanup request aspect ratio must match the source image. A mismatch is rejected rather than silently changing orientation. When the user has an existing image whose overall idea is acceptable but whose texture has become noisy, smeared, gummy, haloed or filled with repeated fish-scale micro-patterns, enable `cleanup` in the request. Read [clean-remake.md](references/clean-remake.md). `prepare` will create a `cleanup/` folder inside the run directory and generate:

- `composition-map.png` for layout, subject count, scale, overlap, perspective and major colour regions;
- optional `gaussian-support.png` for broad light, atmosphere and colour continuity.

These are helper references for a clean redraw. They are not output art and they do not prove quality. If Pillow is unavailable, stop and report the missing dependency.

### P0 regional brushwork trial (opt-in)

When evaluating repeated fish-scale marks across sky, water, vegetation, fabric, and grainstacks, use `--brushwork-variant regional-p0` on `prepare`; compare against `--brushwork-variant baseline` with the same request/model/reference. The option adds only the [regional brushwork overlay](references/regional-brushwork-p0.txt). Both choices have distinct style locks. **Do not make it the default or claim improvement without real A/B image review.** See [trial plan](references/regional-brushwork-p0.md).

### Compact prompt trial (opt-in, unverified)

Use `--prompt-variant compact-v1` with `prepare` to compile a shorter, image-only prompt from [compact-prompt-v1.txt](references/compact-prompt-v1.txt). When `--brushwork-variant regional-p0` is also selected, the compact-specific [regional overlay](references/compact-regional-p0.txt) is used. The default `full` prompt and original P0 overlay are unchanged. Compact and full runs have different style locks; do not merge their results or declare a shorter prompt visually better before actual paired-image review. An exported text-only prompt still does not mean a style image or model version was bound to ImageGen.

### Optional explicit ComfyUI local runner

For **controlled visual experiments** with a user-controlled local ComfyUI instance, read [explicit-comfyui.md](references/explicit-comfyui.md). The independent `scripts/execute_comfyui.py` adapter reads only the prepared job and a verified API-format workflow; it never reads experiment reports or past chat text. It is **dry-run by default**, with `--execute` required for a real local request. It uploads the actual pinned style anchor and requires that the LoadImage node feeds the sampler; output remains **REQUIRES_VISUAL_REVIEW** until a reviewer inspects the painting. It does not install models, enable paid APIs, automatically handle cleanup/editing, or promise the style adapter is effective. If ComfyUI or the necessary style control nodes are missing, report `NOT_SUPPORTED`, not a completed run.

## 3. Inspect and generate

Open the selected anchor with a real image viewer. For restyling also open the content photo. Read `job.json` and `prompt.txt`; keep the fixed style passage unchanged. Explicitly assign roles: STYLE reference controls painting language; when present, CLEANUP STRUCTURE map controls layout and major colour masses; CLEANUP GAUSSIAN support controls only broad atmospheric glow; user brief controls required objects, light and relations.

Invoke the actual image-generation/editing tool only when its input route is suitable. Map supported fields from the job into its real schema. **If the tool infers the image request from the whole conversation instead of accepting a verifiable prompt field, do not invoke it in a chat containing earlier image subjects, generated images, scoring or reports.** Use the fresh-chat route in [host-tools.md](references/host-tools.md): export only `image-only-prompt.txt` and paste its contents alone into a new chat. That is an exploratory workaround, not verified prompt/anchor/model binding or controlled A/B. When a fresh chat is unavailable, stop with `BLOCKED_CONTEXT_REUSE` rather than repeatedly generating the wrong subject. If local paths are not valid attachments, use the host's supported image-attachment step or stop. Never pass an opaque fake asset ID. Preserve provider-required provenance/watermarks; the instruction not to add painted signatures does not authorize stripping provenance.

Require a SINGLE full-canvas original painting when one painting was requested: no experiment poster, infographic, diptych, comparison grid, report, labels, tables or fabricated ratings. **First inspect the actual subject, weather and canvas orientation against the brief; reject a wrong-subject image before any style scoring or next-arm generation.** Reject any such output immediately. Ask for one candidate unless the user requested multiple. Keep the original requested weather—even a sunny anchor does not authorize changing night to daytime. Do not inject cottages, sailboats, cliffs, figures or signatures from the anchor unless the user's brief calls for them. In cleanup mode, do not re-copy dirty source texture, repeated micro-patterns, dirty gradients or oversharpened halos.

## 4. Review, retry and stop

Read [review.md](references/review.md). Specifically inspect for unrequested signature-like marks and a recognisable original-painting composition; record `reference_leakage` as fail or unknown with image-local evidence, rather than assuming a famous painting was pixel-copied. If the host allows inspection, review the actual image and complete `review-template.json`. Run:

```bash
python3 "$SKILL_ROOT/scripts/monet.py" inspect --image candidate.png
python3 "$SKILL_ROOT/scripts/monet.py" review --job monet-run-001/job.json --image candidate.png --assessment filled-review.json --out result.json
```

A candidate only reaches `ACCEPTED_REPORTED` when all checks pass, a real reviewer or model reviewer is named, the image was inspected, and required metadata is filled. In cleanup mode, verify both (a) structure/content retention and (b) that repeated micro-texture was reduced **without** destroying Monet-like atmosphere by flattening everything into uniform blur.

最多三次真实出图。每次只改一个明确问题：内容错误、风格错位、微纹理污染、夜景被拉亮、或 cleanup 结构图不够保真。若宿主不能附上必须的参考图或看图复核，则停止并说明。

## 5. Boundaries

Do not claim stable Monet output across tasks. Do not claim a cleanup route has improved quality until real outputs were generated and reviewed. Never upload the user's private content image to a public repository. Do not say that a composition map or Gaussian support image is the final result. This skill does not make legal judgments about derivative works, does not promise exact historical Monet emulation, and does not bypass host safety restrictions.