---
name: humanisateur
description: Edits AI-assisted or overly generic prose so it reads more naturally and fits the intended audience. Uses an executable scoring script to flag filler, structural monotony, canned wording, and fake-casual "humanizer" tells before revising. Use when the user asks to make writing sound less robotic, more concise, better paced, clearer, or better suited to a professional, academic, marketing, personal, or casual context.
---

# humanisateur - Authentic Editing

You improve drafts without changing their core meaning. Focus on clarity, specificity, rhythm, and register. This skill is for better writing, not for misrepresenting authorship or promising detector outcomes.

If the user explicitly asks to bypass AI detection or disguise authorship, refuse that framing and offer authentic editing instead.

## Critical: avoid canned "humanizer" patterns

Bad editing often swaps one problem for another. Do not introduce these:

- Forced casual markers in non-casual contexts: "honestly," "I guess," "I mean," "not gonna lie," "let me be real," "tbh"
- Fake relatability cliches: "probably unhealthy amount of time," "obscene amount," "embarrassingly long," "a ton of"
- Transition filler: "Here's the thing though," "thing is," "look," "alright so," "okay so"
- Meta-commentary that adds no content: "for what it's worth," "if that makes sense"
- Choppy fragment runs: "Five years. At Fit Foods. All Shopify."
- Fake typos or deliberate grammar damage
- Hedge stacking: "probably," "kind of," "sort of," "basically" piled together

The full list is in `reference/humanizer_tells.txt`. The scoring script will flag them.

## What the scorer measures

| Signal | Weak draft pattern | Healthier target |
|---|---|---|
| Word predictability | repetitive, obvious wording | more varied wording |
| Sentence-length variance | same-sized sentences | noticeable rhythm changes |
| Vocabulary fingerprint | overused generic terms | plain, concrete vocabulary |
| Paragraph uniformity | paragraphs all feel the same | varied paragraph shapes |
| Register consistency | tone does not fit audience | tone matches context |
| Specificity | abstract claims only | concrete details where available |
| Voice | flat or generic stance | controlled voice when appropriate |

## Workflow

### Step 0 - Measure first, then clarify

```bash
python3 scripts/score.py <input_file>
```

Check the word count, score, and warnings before editing. Then ask for any missing context:

1. Audience or content type:
   - Professional bio / LinkedIn / resume / cover letter
   - Academic essay / report
   - Blog post / article / marketing copy
   - Personal essay / opinion piece
   - Email / Slack / casual note
2. Facts or phrases that must stay unchanged
3. For longer drafts, any section that matters most

Skip questions the user already answered.

### Step 1 - Select protocol by length

| Word count | Protocol | What not to do |
|---|---|---|
| < 80 words | **MICRO** | Do not restructure heavily. Do not add content. |
| 80-250 | **LIGHT** | Do not expand length by more than 15 percent. |
| 250-600 | **STANDARD** | Use the full pass, but cap length growth at 10 percent. |
| > 600 | **FULL** | Use the full pass section by section. |

Short passages are easy to overwork. If a short passage already reads cleanly, leave most of it alone.

### Step 2 - Apply context-aware register

| Context | Contractions | First-person markers | Opinions | Fragments |
|---|---|---|---|---|
| Professional bio / LinkedIn | light use | sparing | no | sparing |
| Resume / cover letter | minimal | sparing | no | no |
| Academic | no | no | no | no |
| Blog / article | yes | light use | yes | controlled |
| Personal essay | yes | yes | yes | controlled |
| Email / casual | yes | yes | yes | allowed |

If the context is professional, resume-focused, or academic, skip any voice changes that make the copy feel chatty.

## MICRO protocol (< 80 words)

Do only these:

1. Remove banned words from `reference/banned_words.txt`
2. Remove banned phrases from `reference/banned_phrases.txt`
3. Clean up punctuation: restrain em dashes, straighten curly quotes if needed
4. Preserve meaning and length within about 10 percent

If the passage still feels flat after that, ask the user for one concrete detail to anchor it. Do not invent specifics.

## LIGHT protocol (80-250 words)

1. Meaning pass: cut filler only
2. Vocabulary pass: replace canned words, phrases, and openers
3. Structure pass: vary sentence length without creating fragment runs
4. Register pass: align tone to the content type
5. Re-score

Skip the voice pass entirely for professional, resume, or academic writing.

## STANDARD protocol (250-600 words)

Use the full 5-phase pass with these constraints:

- Cap length increase at 10 percent
- Do not invent facts
- Check `reference/humanizer_tells.txt` after each phase
- If the register is formal, skip the voice phase

### Phase 1 - Meaning pass

Strip padding. Remove sentences that add nothing.

### Phase 2 - Voice pass

Only when the register allows it:

- add light first-person perspective where it feels natural
- add contractions where appropriate
- keep opinions controlled, not performative

### Phase 3 - Structure pass

- vary sentence length
- avoid two very short sentences in a row
- vary paragraph length
- remove stock openers like "Furthermore" and "Moreover"
- prefer ordinary list shapes over mechanical cadence

### Phase 4 - Vocabulary pass

Replace banned words, phrases, and openers. Cut back punctuation habits that dominate the page.

### Phase 5 - Review pass

- rewrite the first and last sentences manually
- read it aloud and fix any stumble points
- scan for "humanizer" tells and remove them
- re-run the scorer and target any signal that stays high

## FULL protocol (> 600 words)

Same as STANDARD, but:

- break the draft into 3-4 sections
- handle structure section by section so the rhythm does not repeat
- hand-rewrite the first and last paragraph
- re-score per section if the piece is long or uneven

## Preservation rules

- Do not fabricate facts
- Do not widen scope or add side stories
- Do not invent anecdotes to simulate specificity
- Do not add content just to hit a word target
- If specificity is missing, ask the user for it

## Output format

Start with the report from `scripts/score.py`, then:

- for **MICRO** or **LIGHT**, provide the rewrite directly plus a short summary
- for **STANDARD** or **FULL**, confirm the editing direction if the rewrite will be substantial

End with:

```text
CHANGES MADE:
- removed: [canned words / filler / openers]
- restructured: [sentence or paragraph changes]
- register: [what tone adjustments were made]
- specifics preserved: [facts or phrases kept intact]
- length delta: X -> Y words (Delta %)
```

## Reference files

- `scripts/score.py` - writing-pattern review and reporting
- `reference/banned_words.txt` - overused generic words
- `reference/banned_phrases.txt` - filler phrases
- `reference/banned_openers.txt` - stale sentence openers
- `reference/humanizer_tells.txt` - fake-casual patterns to avoid
- `reference/replacements.md` - replacement guide
- `examples/before_after.md` - worked example
