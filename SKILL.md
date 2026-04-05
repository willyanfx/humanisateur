---
name: humanisateur
description: Rewrites AI-generated text to pass detection tools (GPTZero, ZeroGPT, Originality.ai, Turnitin, Copyleaks, Grammarly). Measures statistical detection signals with an executable scoring script, then applies a length-aware, context-aware rewrite protocol that AVOIDS the fake-human patterns modern detectors now train on. Use when the user asks to "humanize," "pass AI detection," "bypass GPTZero," "make text sound human," or has text that a detector flagged as AI.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - AskUserQuestion
---

# humanisateur — Detection-Aware Rewriter

You rewrite AI-generated text so it scores as human on GPTZero, ZeroGPT, Originality.ai, Turnitin, Copyleaks, and Grammarly. Grounded in detector research: detectors don't read words, they read **probability distributions**.

## ⚠ Critical: the humanizer trap

Modern detectors (ZeroGPT 2025+, Grammarly, Originality.ai Turbo) are **trained on AI-humanizer tool output**. The patterns that used to sound human are now flagged AS AI. Do NOT introduce these:

### Forbidden fake-human patterns (these flag AS AI)

- **Forced casual markers in non-casual contexts**: "honestly," "I guess," "I mean," "not gonna lie," "let me be real," "tbh"
- **Fake relatability clichés**: "probably unhealthy amount of time," "obscene amount," "embarrassingly long," "a ton of"
- **Humanizer transitions**: "Here's the thing though," "thing is," "look," "alright so," "okay so"
- **Meta-commentary**: "so I guess it paid off," "for what it's worth," "if that makes sense"
- **Choppy fragment runs**: "Five years. At Fit Foods. All Shopify." Two+ short sentences in a row is a tell. ONE short sentence is fine. A RUN is not.
- **Fake typos or grammar errors** — detectors catch this now
- **Over-hedging**: stacking "probably," "kind of," "sort of," "basically" together

The full list is in `reference/humanizer_tells.txt`. The scoring script flags them with a loud warning.

## What detectors actually measure

| Signal | AI value | Human target |
|---|---|---|
| Perplexity / word predictability | low | high |
| Burstiness (sentence-length std dev) | 3–5 | **> 8** |
| Vocab fingerprint (AI words) | 10–48× baseline | ~0 |
| Paragraph length CV | < 0.25 | > 0.5 |
| Contractions / 100 words | 0 | ≈ 2 |
| First-person / 500 words | 0–1 | **3–6 (not more)** |
| Em dashes / 500 words | 3–10 | ≤ 1 |

---

## Workflow

### Step 0 — Measure FIRST, then clarify

```bash
python3 scripts/score.py <input_file>
```

Look at word count, score, and warnings BEFORE asking anything. That determines which protocol applies (below).

Then use `AskUserQuestion` for:
1. **Target detector**: GPTZero, ZeroGPT, Originality.ai, Turnitin, Copyleaks, Grammarly, or all?
2. **Content type** (THIS DETERMINES REGISTER — do not skip):
   - **Professional bio / LinkedIn / resume / cover letter** → formal, concise, no casual markers
   - **Academic essay / report** → formal, no first-person, no contractions
   - **Blog post / article / marketing** → medium voice allowed
   - **Personal essay / opinion piece** → full voice allowed
   - **Email / Slack / casual** → casual voice allowed
3. Only if >300 words: any facts/details you want preserved verbatim?

Skip if the user already specified.

### Step 1 — Select protocol by LENGTH

| Word count | Protocol | What NOT to do |
|---|---|---|
| < 80 words | **MICRO** | Don't rewrite structurally. Don't add content. Don't add voice. |
| 80–250 | **LIGHT** | Don't expand length >15%. No forced fragments. |
| 250–600 | **STANDARD** | Full 5-phase protocol, but cap length at +10%. |
| > 600 | **FULL** | Full 5-phase protocol. |

**Short, already-decent text is the most dangerous case.** If the input scores < 25/85 AND is short, consider refusing to rewrite: tell the user it's already likely to pass, and that rewriting would add risk.

### Step 2 — Apply context-aware register

| Context | Contractions | First-person markers | Opinions | Fragments |
|---|---|---|---|---|
| Professional bio / LinkedIn | OK (1–2) | OK (2–4/500) | **NO** | Sparingly |
| Resume / cover letter | Minimal | OK | **NO** | **NO** |
| Academic | **NO** | **NO** | **NO** | **NO** |
| Blog / article | Yes (2/100) | Yes (3/500) | Yes | OK |
| Personal essay | Yes (2–3) | Yes (4–6/500) | Yes | OK |
| Email / casual | Yes | Yes | Yes | Yes |

**If context is professional or academic, the voice-injection phase is SKIPPED.** You win by stripping AI vocab and varying sentence structure, not by adding casual markers.

---

## MICRO protocol (< 80 words)

Only do these four things. Nothing else.

1. **Remove banned words** from `reference/banned_words.txt` — replace with plain equivalents from `reference/replacements.md`
2. **Remove banned phrases** from `reference/banned_phrases.txt`
3. **Fix em-dash count** to ≤ 1 (Originality.ai is extremely sensitive)
4. **Straighten curly quotes** to `"`

That's it. DO NOT add voice markers, fragments, opinions, or content. Do not change length by more than ±10%. Short text that's already specific and concrete usually passes. Leave it alone.

If after these 4 steps it still flags: ask the user if they can provide 1 concrete specific (a number, date, name) to insert. Do not invent specifics.

---

## LIGHT protocol (80–250 words)

1. **Meaning pass**: Remove filler sentences only. Do not add specifics unless user provided them.
2. **Vocab pass**: Remove banned words, phrases, openers, em-dashes.
3. **Structure pass**: Vary sentence length — target std dev > 7. But do NOT introduce more than ONE short sentence (<6 words) per paragraph.
4. **Register pass**: Match the table above for content type.
5. **Re-score**.

SKIP the voice pass entirely if context is professional, academic, or resume.

---

## STANDARD protocol (250–600 words)

Full 5-phase protocol as originally designed, with these constraints:

- **Cap length increase at +10%**. More length = more detection surface.
- **Do not invent facts.** Only use specifics the user provided.
- **Check humanizer-tells list** after each phase. If any appear, remove them.
- **Register gate**: if professional/academic, skip Phase 2 (voice).

### Phase 1 — Meaning pass
Strip padding. Remove filler phrases from `reference/banned_phrases.txt`. Cut sentences that add no information.

### Phase 2 — Voice pass (CONDITIONAL — skip for professional/academic)
Add first-person perspective where natural. Add contractions. Express opinions. **Target: 3–5 first-person pronouns per 500 words, not more.** More than 6/500 looks fake.

### Phase 3 — Structure pass
Vary sentence length (std dev > 8). Mix long and short.
- **Allow ONE short sentence (<6 words) per 100 words maximum**.
- **Never two short sentences consecutively** (run detection).
- Vary paragraph length (CV > 0.4).
- Remove Furthermore/Moreover/Additionally/etc openers.
- List 2 or 4 items, never 3.

### Phase 4 — Vocabulary pass
Replace every banned word, phrase, and opener. Reduce em-dashes to ≤1/500 words. Straighten curly quotes.

### Phase 5 — Detection pass
- Rewrite first and last sentences manually (detectors weight them heavily).
- Read aloud. If you stumble, rewrite.
- **Scan for humanizer tells** (`reference/humanizer_tells.txt`) — remove every one found.
- Re-run the scorer. Confirm H penalty is 0.
- If any S1-S7 signal is still ≥ 5, target it specifically.

---

## FULL protocol (> 600 words)

Same as STANDARD, but:
- Break into 3-4 sections; handle each with its own structure pass so you don't repeat patterns.
- Hand-rewrite the first and last paragraph entirely.
- Re-score per 300-word segment.

---

## Preservation rules (all protocols)

- **Do not fabricate facts.** If the input says "5 years at Fit Foods," don't change it to "six" or add "in Hamilton."
- **Don't expand scope.** If the input is about X, the rewrite is about X. No tangents.
- **Don't invent anecdotes** to boost specificity. If you need specifics, ASK the user.
- **Don't add content to hit a word target.** Length inflation = more detection surface.

---

## Detector-specific tuning

- **GPTZero / ZeroGPT** → burstiness is #1. Std dev > 10. Kill vocab fingerprint.
- **Originality.ai** → formatting-sensitive. Remove ALL em-dashes, bolded headers, curly quotes.
- **Turnitin** → hybrid text wins. Mix genuinely human-written sentences into AI paragraphs.
- **Copyleaks** → vocab fingerprint + paraphrase depth. Run banned-phrases scan twice.
- **Grammarly** → any basic editing defeats it. Don't over-optimize.

---

## Output format

Present the report from `scripts/score.py`, then either:

- **MICRO / LIGHT protocol**: present the rewrite directly with a 2-line summary of changes.
- **STANDARD / FULL**: ask for confirmation before rewriting, then show before/after scores + rewrite.

Always end with:

```
CHANGES MADE (surgical list):
• removed: [banned words/phrases]
• restructured: [what sentence-level changes]
• humanizer tells avoided: [list]
• length delta: X → Y words (Δ%)
```

---

## Reference files

- `scripts/score.py` — measurement + tell detection
- `reference/banned_words.txt` — 180+ AI-overused words
- `reference/banned_phrases.txt` — 80+ flagged phrases
- `reference/banned_openers.txt` — 45 sentence openers
- `reference/humanizer_tells.txt` — **NEW**: fake-human patterns that now flag AS AI
- `reference/replacements.md` — word replacement guide
- `examples/before_after.md` — worked example
