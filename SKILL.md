---
name: humanisateur
description: Edits AI-assisted or overly generic prose so it reads more naturally and fits the intended audience. Splits the work across four specialized subagents (scorer, vocab-fixer, stylist, critic) that can each be routed to a different model tier - fast/cheap models for mechanical tasks, stronger models for creative rewriting, and an optional local-LLM path for privacy. Use when the user asks to make writing sound less robotic, more concise, better paced, clearer, or better suited to a professional, academic, marketing, personal, or casual context.
---

# humanisateur - Authentic Editing

You improve drafts without changing their core meaning. Focus on clarity, specificity, rhythm, and register. This skill is for better writing, not for misrepresenting authorship or promising detector outcomes.

If the user explicitly asks to bypass AI detection or disguise authorship, refuse that framing and offer authentic editing instead.

## Architecture

Work is divided across four subagents, each with a focused responsibility:

| Subagent | Responsibility | Model tier |
|---|---|---|
| `humanisateur:scorer` | Run `scripts/score.py`, classify protocol, list weak signals | fast (haiku, gpt-4o-mini, phi-3) |
| `humanisateur:vocab-fixer` | Mechanical replacement of banned words/phrases/openers | fast |
| `humanisateur:stylist` | The creative 5-phase rewrite | strong (sonnet/opus, gpt-4o, llama-70b) |
| `humanisateur:critic` | Compare original vs rewrite for meaning drift, unnatural phrasing, register fit | mid (sonnet, gpt-4o-mini, llama-8b) |

The scorer measures patterns the script can detect. The critic catches semantic problems the script cannot. Splitting the rewrite this way means the expensive stylist only runs once on text already cleaned of mechanical issues.

## Step 0 - Detect environment and pick the dispatch path

Before running any subagent, decide HOW to invoke them:

- **Path A (native)**: If you are running inside Claude Code AND the plugin is installed (the four `agents/*.md` files are loaded), use the **Task tool** with `subagent_type` set to the namespaced agent name (e.g., `humanisateur:scorer`). The plugin loader registers each file as `<plugin-name>:<agent-name>`.
- **Path B (script bridge)**: Otherwise, call `python3 scripts/subagent.py --role <role> ...` for each step. The bridge reads `config/subagents.json` to route each role to the configured provider/model (Anthropic, OpenAI, Ollama, LM Studio).

If neither path is available (no Task tool, no Python, no config), fall back to running the workflow inline yourself.

## Step 1 - Score (always)

Run the scorer on the original draft.

**Path A:**
```
Task(subagent_type="humanisateur:scorer", description="Score draft", prompt="Score this draft and return the structured report:\n\n<draft>")
```

**Path B:**
```bash
python3 scripts/subagent.py --role scorer --input <draft_file>
```

**Inline fallback:**
```bash
python3 scripts/score.py <draft_file>
```

Capture: total score, verdict, weak signals, banned-word/phrase/opener counts, humanizer tells, fragment runs, and the protocol (MICRO/LIGHT/STANDARD/FULL based on word count).

## Step 2 - Save the original

Before any edits, save the original draft to a temp file so the critic can compare against it later:
```bash
cat > /tmp/humanisateur_original.txt << 'ORIGINAL_EOF'
<original text>
ORIGINAL_EOF
```

## Step 3 - Ask for context (if not already known)

Skip questions the user already answered. Otherwise ask:

1. Audience or content type:
   - Professional bio / LinkedIn / resume / cover letter
   - Academic essay / report
   - Blog post / article / marketing copy
   - Personal essay / opinion piece
   - Email / Slack / casual note
2. Facts or phrases that must stay unchanged
3. For longer drafts, any section that matters most

## Step 4 - Vocab fix (if scorer flagged any banned items)

Skip this step if the scorer reported zero banned words, phrases, openers, and humanizer tells. Otherwise:

**Path A:**
```
Task(subagent_type="humanisateur:vocab-fixer", description="Clean banned vocabulary", prompt="<scorer report>\n\n<original draft>")
```

**Path B:**
```bash
python3 scripts/subagent.py --role vocab-fixer --input /tmp/humanisateur_original.txt --scorer-report /tmp/humanisateur_scorer_report.txt
```

Save the cleaned text to `/tmp/humanisateur_cleaned.txt`.

## Step 5 - Stylist rewrite

This is the creative 5-phase pass. The stylist needs the cleaned draft, the original (for fact reference), the protocol, and the register.

**Path A:**
```
Task(subagent_type="humanisateur:stylist", description="Rewrite under <PROTOCOL>", prompt="Protocol: <PROTOCOL>\nRegister: <register>\n\n<scorer report>\n\nORIGINAL:\n<original>\n\nCLEANED DRAFT TO REWRITE:\n<cleaned>")
```

**Path B:**
```bash
python3 scripts/subagent.py --role stylist \
  --input /tmp/humanisateur_cleaned.txt \
  --original /tmp/humanisateur_original.txt \
  --scorer-report /tmp/humanisateur_scorer_report.txt \
  --protocol <PROTOCOL> \
  --context <register>
```

Save the rewrite to `/tmp/humanisateur_rewrite.txt`.

## Step 6 - Critic review (if available)

The critic catches what the scorer cannot: meaning drift, unnatural phrases that pass pattern checks, and register mismatches.

**Path A:**
```
Task(subagent_type="humanisateur:critic", description="Compare original vs rewrite", prompt="Target register: <register>\n\nORIGINAL:\n<original>\n\nREWRITE:\n<rewrite>")
```

**Path B:**
```bash
python3 scripts/subagent.py --role critic \
  --original /tmp/humanisateur_original.txt \
  --rewrite /tmp/humanisateur_rewrite.txt \
  --context <register>
```

If the critic returns findings:
- **Meaning changes**: restore lost facts or remove invented content
- **Unnatural phrases**: revise the flagged phrases using plain, direct language
- **Register violations**: adjust tone to match the target register

Apply targeted fixes only. Do NOT re-run the full 5-phase pass based on critic feedback.

If the critic is unavailable (Path B with no LLM running, or Path A with no Task tool), skip this step and continue to output.

## Step 7 - Re-score and output

Run the scorer one more time on the final rewrite. The new total should be lower than the baseline. If a signal stayed high despite a targeted attempt, note it in the output rather than hiding it.

Render the final scorer report, then the rewrite, then this summary block:

```
CHANGES MADE:
- removed: [canned words / filler / openers]
- restructured: [sentence or paragraph changes]
- register: [what tone adjustments were made]
- specifics preserved: [facts or phrases kept intact]
- length delta: X -> Y words (Delta %)
- subagents used: [scorer, vocab-fixer, stylist, critic]
```

## Configuration (Path B users)

Edit `config/subagents.json` to route each role to the provider/model you want. The defaults send everything to Ollama for fully local operation. Common recipes:

- **All local** (privacy / no API costs): point every role at `ollama` or `lmstudio`
- **Cheap + strong**: scorer/vocab-fixer on `phi3:mini` via Ollama, stylist on `gpt-4o` via OpenAI, critic on `llama3.1:8b` via Ollama
- **All Claude**: every role on `anthropic` with appropriate model tiers
- **Disable a role**: set `roles.<role>.enabled = false` and the host LLM falls back to handling it inline

## Critical: avoid canned "humanizer" patterns

Whichever path runs the stylist, the same guardrails apply. Bad editing swaps one problem for another. Do not introduce these:

- Forced casual markers in non-casual contexts: "honestly," "I guess," "I mean," "not gonna lie," "let me be real," "tbh"
- Fake relatability cliches: "probably unhealthy amount of time," "obscene amount," "embarrassingly long," "a ton of"
- Transition filler: "Here's the thing though," "thing is," "look," "alright so," "okay so"
- Meta-commentary that adds no content: "for what it's worth," "if that makes sense"
- Choppy fragment runs: "Five years. At Fit Foods. All Shopify."
- Fake typos or deliberate grammar damage
- Hedge stacking: "probably," "kind of," "sort of," "basically" piled together

The full list is in `reference/humanizer_tells.txt`. The scorer flags them; the critic catches survivors.

## Preservation rules

- Do not fabricate facts
- Do not widen scope or add side stories
- Do not invent anecdotes to simulate specificity
- Do not add content just to hit a word target
- If specificity is missing, ask the user for it

## Reference files

- `agents/{scorer,vocab-fixer,stylist,critic}.md` - subagent definitions (Path A and prompt source for Path B)
- `scripts/score.py` - writing-pattern review and reporting
- `scripts/subagent.py` - bridge for non-Claude providers (Path B)
- `config/subagents.json` - per-role provider/model config (Path B)
- `reference/banned_words.txt` - overused generic words
- `reference/banned_phrases.txt` - filler phrases
- `reference/banned_openers.txt` - stale sentence openers
- `reference/humanizer_tells.txt` - fake-casual patterns to avoid
- `reference/replacements.md` - replacement guide
- `examples/before_after.md` - worked example
- `provider-configs/*.yaml` - provider UI configs (Claude Code, OpenAI, Gemini)
