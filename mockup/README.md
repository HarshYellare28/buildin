# DAWA visual mockup (not the app)

Standalone design prototype only.
Does **not** live under `apps/web/` so it cannot mess with the real Next.js app.

## Open

```bash
open mockup/index.html
# or
open /Users/arnavpanicker/sarvambuildin/buildin/mockup/index.html
```

## Contents

| Path | What |
| --- | --- |
| `index.html` | Full-bleed glass UI mock |
| `brand/` | Logo SVG/JPG + background art |
| `NANO_BANANA_BG_PROMPT.md` | Prompt to regenerate background |

## Rule

When Harsh builds the real app in `apps/web/`, copy visual tokens from here.
Do not import this folder into production bundles unless you intentionally promote assets.
