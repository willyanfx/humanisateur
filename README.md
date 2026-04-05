# humanisateur

A detection-aware text rewriter that rewrites AI-generated text to pass AI-detection tools (GPTZero, ZeroGPT, Originality.ai, Turnitin, Copyleaks, Grammarly).

It is packaged as a Claude Code / Claude Agent SDK **skill**, with an executable Python scorer that measures the statistical signals detectors actually use — then applies a length-aware, context-aware rewrite protocol that **avoids the fake-human patterns modern detectors now train on**.

## What makes this different

Most "humanizer" tools introduce their own tells — forced casual markers ("honestly," "I guess"), fake relatability ("probably unhealthy amount"), choppy fragment runs. Modern detectors (ZeroGPT 2025+, Grammarly, Originality.ai Turbo) are trained on that output and flag it AS AI.

humanisateur:
- Measures 7 detection signals + a humanizer-tell penalty before touching the text
- Gates the rewrite protocol by length (MICRO / LIGHT / STANDARD / FULL)
- Gates voice injection by register (professional bio / academic / blog / personal / casual)
- Refuses to inflate length, invent facts, or add content to hit a word target

## Install

```bash
git clone https://github.com/willyanfx/humanisateur.git
cd humanisateur
```

Drop the folder into your Claude skills directory, or invoke `SKILL.md` directly.

## Usage

```bash
python3 scripts/score.py path/to/input.txt
```

Then follow the protocol in `SKILL.md` matching the word count.

## Signals measured

| Signal | AI value | Human target |
|---|---|---|
| Word predictability (perplexity proxy) | low | high |
| Burstiness (sentence-length std dev) | 3–5 | > 8 |
| Vocab fingerprint (AI-overused words) | 10–48× baseline | ~0 |
| Paragraph length CV | < 0.25 | > 0.5 |
| Contractions / 100 words | 0 | ≈ 2 |
| First-person / 500 words | 0–1 | 3–6 |
| Em dashes / 500 words | 3–10 | ≤ 1 |

## Files

- `SKILL.md` — skill definition and full rewrite protocol
- `scripts/score.py` — pure-stdlib scorer (no dependencies)
- `reference/banned_words.txt` — 180+ AI-overused words
- `reference/banned_phrases.txt` — 80+ flagged phrases
- `reference/banned_openers.txt` — 45 sentence openers
- `reference/humanizer_tells.txt` — fake-human patterns that now flag AS AI
- `reference/replacements.md` — word replacement guide
- `examples/` — before/after worked examples

## License

MIT
