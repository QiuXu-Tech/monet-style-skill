# P2 · Face/hand painterly finish: pre-registered exploratory prompt comparison

**Status: PLANNED / NO_GENERATION / NO_SCORES / NO_PROMOTION.** Date: 2026-11-11.

## Basis
The user's actual handwritten MOR-02 review rated A=6.15, B=6.90, C=6.55 (brushwork 30%, color 30%, atmosphere 30%, artifact control 10%). B (`compact-v1 + P1`) is the chosen *working reference* for the next visual test, not a statistically established winner. The user specifically noted face and hands look too polished and regular. Preserve color, scenery, and earlier baseline; do not add P0 to this comparison.

## Single changed factor
Compare the exact same scene and exact same compact-v1 style text, changing **only** the local "Faces and hands" passage. D is a *replacement* for B's P1 sentence, not an appended second instruction. The D hypothesis is that matching edge softness and stroke scale to clothing while implying facial features and finger separations will reduce polished linework without losing correct anatomy. The P2 candidate has **not** been visually validated.

## B — control (identical to prior B recipe)
```text
One original oil painting, 4:5 aspect ratio.

Scene: 初夏的草坡上有一位撑着洋伞的女子，微风吹动她的浅色裙摆，天空中有明亮的云，草地随风轻轻起伏，采用略低的观察视角。请画成单幅竖向油画，不添加标题、画框、拼图或分栏。

Style: Render the requested scene as an original Monet-inspired 1880s oil painting, not a famous composition. Build readable forms from adjacent colour patches and broad light/shadow masses. Vary stroke direction, length and density with material and distance. Keep essential silhouettes; let secondary edges soften through atmospheric colour, not blur. Let actual illumination shift local hues and shadow colours without a uniform tint. Preserve subjects, counts, positions, weather and time. Avoid repeated fish-scale dabs, fake grain, photographic smoothing, hard halos, invented objects, labels and signatures.

Faces and hands: suggest features with grouped warm/cool paint planes and a few irregular, directional strokes; avoid polished facial linework or individually outlined fingers while keeping anatomy, pose and gesture readable.
```

## D — P2 candidate (one changed paragraph)
```text
One original oil painting, 4:5 aspect ratio.

Scene: 初夏的草坡上有一位撑着洋伞的女子，微风吹动她的浅色裙摆，天空中有明亮的云，草地随风轻轻起伏，采用略低的观察视角。请画成单幅竖向油画，不添加标题、画框、拼图或分栏。

Style: Render the requested scene as an original Monet-inspired 1880s oil painting, not a famous composition. Build readable forms from adjacent colour patches and broad light/shadow masses. Vary stroke direction, length and density with material and distance. Keep essential silhouettes; let secondary edges soften through atmospheric colour, not blur. Let actual illumination shift local hues and shadow colours without a uniform tint. Preserve subjects, counts, positions, weather and time. Avoid repeated fish-scale dabs, fake grain, photographic smoothing, hard halos, invented objects, labels and signatures.

Faces and hands: match the loose stroke scale and edge softness of nearby clothing. Build features with uneven warm/cool paint planes and a few broken strokes; suggest eyes, lips and finger separations instead of outlining them. Keep anatomy and gesture clear without polished portrait details or blur.
```

## Protocol
- Generate one standalone 4:5 painting per prompt in separate new chats. Keep prompt text as the sole generation message; do not include prior examples, scores, labels, museum images, or analysis text.
- First check single-painting/subject/weather/aspect ratio and unrequested signature/composition leakage. Reject hard-gate failures before scoring.
- For any image that passes, independently rate brushwork, color, atmosphere, and repeated false texture at 30/30/30/10; record concrete face, hand, dress, cloud and grass evidence and generated artifact hashes when available. Keep reviewer identities separate.
- A single new B and D are exploratory evidence. Model/seed and prompt/reference pixel binding are not verifiably fixed; do not interpret score differences as controlled causal effects. Retain all first attempts, no best-of cherry-picking.
- Do not change the default `full`, `compact-v1`, existing P0 or P1 files unless actual tests and regression justify a promotion. No ChatGPT ImageGen call has been issued for P2 here.
