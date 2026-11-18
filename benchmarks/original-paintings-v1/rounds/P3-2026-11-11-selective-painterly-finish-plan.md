# P3 · Selective painterly focus (pre-registered prompt-only candidate)

**Status:** PLANNED / NOT_GENERATED / NOT_SCORED / NO_PROMOTION  
**Date:** 2026-11-11  
**Reference:** Monet, *Woman with a Parasol—Madame Monet and Her Son* (1875), [National Gallery of Art](https://www.nga.gov/artworks/61379-woman-parasol-madame-monet-and-her-son). **Evaluation-only**, not provided as an image to the generator.

## Why this experiment exists

P1 improved the user's single-sample ratings relative to A and P0+P1, but faces/hands still looked polished. P2's extra contour/softness wording did not resolve this. The museum's technical description distinguishes rapid irregular sky strokes with exposed canvas, denser short grass marks, and directional light-catching marks on fabric. Test **unequal painterly resolution** rather than adding another list of detail prohibitions. These are brushwork observations, not permissions to copy the reference composition, green parasol, child, or signature.

The current compact-v1 text invokes an *1880s* profile while the museum painting dates to **1875**: therefore this is an **out-of-profile diagnostic**, not proof of cross-period conformance.

## Frozen common scene and style

Both variants share the exact same first three sections. The only changed input is the final painterly-guidance paragraph; changing that paragraph may affect several regions, so do not attribute an observed change to a specific subphrase.

### B — unchanged P1 control

```text
One original oil painting, 4:5 aspect ratio.

Scene: 初夏的草坡上有一位撑着洋伞的女子，微风吹动她的浅色裙摆，天空中有明亮的云，草地随风轻轻起伏，采用略低的观察视角。请画成单幅竖向油画，不添加标题、画框、拼图或分栏。

Style: Render the requested scene as an original Monet-inspired 1880s oil painting, not a famous composition. Build readable forms from adjacent colour patches and broad light/shadow masses. Vary stroke direction, length and density with material and distance. Keep essential silhouettes; let secondary edges soften through atmospheric colour, not blur. Let actual illumination shift local hues and shadow colours without a uniform tint. Preserve subjects, counts, positions, weather and time. Avoid repeated fish-scale dabs, fake grain, photographic smoothing, hard halos, invented objects, labels and signatures.

Faces and hands: suggest features with grouped warm/cool paint planes and a few irregular, directional strokes; avoid polished facial linework or individually outlined fingers while keeping anatomy, pose and gesture readable.
```

### E — new P3 painterly hierarchy hypothesis

```text
One original oil painting, 4:5 aspect ratio.

Scene: 初夏的草坡上有一位撑着洋伞的女子，微风吹动她的浅色裙摆，天空中有明亮的云，草地随风轻轻起伏，采用略低的观察视角。请画成单幅竖向油画，不添加标题、画框、拼图或分栏。

Style: Render the requested scene as an original Monet-inspired 1880s oil painting, not a famous composition. Build readable forms from adjacent colour patches and broad light/shadow masses. Vary stroke direction, length and density with material and distance. Keep essential silhouettes; let secondary edges soften through atmospheric colour, not blur. Let actual illumination shift local hues and shadow colours without a uniform tint. Preserve subjects, counts, positions, weather and time. Avoid repeated fish-scale dabs, fake grain, photographic smoothing, hard halos, invented objects, labels and signatures.

Painterly hierarchy: Let light and wind, not anatomy, decide the level of detail. Keep faces and hands at the stroke scale of nearby sleeves; suggest gaze and grasp with uneven warm/cool touches while preserving readable anatomy. Leave quiet gaps amid irregular sky strokes; use varied, clustered short marks in grass and broader directional marks on windblown fabric. Keep secondary passages unresolved rather than polishing every outline.
```

## Review and stop conditions

1. Generate only ONE original painting per fresh, independent ChatGPT conversation, using solely its `text` block. No reports, labels, historical scores, or reference painting image may accompany the request.
2. Check hard gates **before** aesthetic scoring: one painting, MOR-02 subject, breezy daylight, portrait 4:5, no signatures or characteristic painting-copy leakage. Fail means **REJECTED** and four scores `null`.
3. Inspect face, fingers, sleeve continuity, cloud density and grass-mark variety. Successful change means clearer painterly hierarchy **without broken anatomy, blurred faces, uniform brush texture, or degradation of the established color relations**.
4. User and model score independently (brushwork 30%, color 30%, atmosphere 30%, false-texture control 10%). First attempts retained, no best-of. Compare B and E only as **exploratory** because image model version, seed, and reference/prompt binding are not verifiably fixed.
5. Existing default `full`, `compact-v1`, and regional P0 remain unchanged. No generated images or performance improvements claimed before actual user-provided samples and reviews.

**Decision:** EXPERIMENT_REGISTERED / AWAITING_IMAGES / NO_PROMOTION.
