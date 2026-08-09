# Nano Banana / image prompt — DAWA background

Use this when generating a full-bleed illustrated background in the same vibe as the barber-shop music UI reference.

## Master prompt (copy-paste)

```text
Full-bleed cinematic illustration in the style of modern Indian editorial gouache: flat graphic shapes, soft daylight, painterly but clean, warm storytelling colors. Indian middle-class home courtyard after a clinic visit. Terracotta wall on the left, soft teal house wall on the right, neem or banana leaves overhead, distant pastel apartment blocks under a clear blue sky. Elderly mother in a cream saree sitting on a wooden chair; adult daughter in teal salwar nearby looking at a phone (caregiver, not posing for camera). Small wooden table with a medicine blister strip and a glass of water. Bicycle leaning on the wall. Calm, hopeful, clinical-care-at-home mood — not hospital, not dark, not cyber. Wide 16:9 composition with a slightly quieter open center so frosted UI glass cards can overlay later. No text, no logos, no watermarks, no UI chrome, no music player, no Devanagari lettering.
```

## Style anchors (add if the model drifts)

```text
Same visual language as premium illustrated India street scenes: graphic shadows, simplified people, bold color blocks of coral / terracotta / teal / sky blue, soft afternoon light, no photoreal skin pores, no 3D render look.
```

## Variants

**Busier street (closer to reference energy):**
```text
...busy but calm neighborhood lane, chemist shop edge visible, clothesline, scooter, warm red awning, keep open center for UI overlay...
```

**Quieter clinic-adjacent:**
```text
...small clinic corridor opening onto courtyard, discharge paper folded on table beside medicines, still no text rendered in image...
```

## How we use it in DAWA UI

1. Export 16:9 or 1920×1200 JPG/WebP.
2. Drop into `mockup/brand/dawa-bg.jpg` (replace).
3. Open `mockup/index.html` — glass panels sit on top.

Logo stays separate: `mockup/brand/dawa-mark.svg` (exact DAWA) and optional JPG mark refs.
