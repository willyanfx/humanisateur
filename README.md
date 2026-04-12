# humanisateur

`humanisateur` is an editing skill for drafts that read as generic, stiff, or obviously overworked. It pairs a portable `SKILL.md` workflow with a small Python scorer that flags filler, stale phrasing, and the fake-casual tics that "humanizer" tools tend to leave behind.

The point: clearer writing, better matched to its audience, without padding or invented detail.

## What it does

The skill checks drafts for structural monotony, canned vocabulary, filler, and overprocessed voice. It scales the edit by word count using four protocols (`MICRO`, `LIGHT`, `STANDARD`, `FULL`) and adjusts tone by register, covering professional, academic, marketing, personal, and casual contexts. Short passages that already read cleanly aren't touched more than necessary.

The scorer is diagnostic only. It flags patterns that make prose feel flat or mechanically rewritten. It doesn't promise anything about authorship or detector outcomes.

## Architecture

The work is divided across four specialized subagents, each handling one slice of the editing pipeline:

| Subagent | Job | Recommended model tier |
|---|---|---|
| `humanisateur:scorer` | Run `score.py`, classify protocol, flag weak signals | fast (haiku, gpt-4o-mini, phi-3) |
| `humanisateur:vocab-fixer` | Mechanical replacement of banned words/phrases/openers | fast |
| `humanisateur:stylist` | The creative 5-phase rewrite | strong (sonnet/opus, gpt-4o, llama-70b) |
| `humanisateur:critic` | Compare original vs rewrite for meaning drift, unnatural phrases, register fit | mid (sonnet, gpt-4o-mini, llama-8b) |

This split lets you spend strong-model budget only on the creative stylist pass while running the mechanical roles on cheap or local models. The scorer measures patterns the script can detect; the critic catches what pattern matching misses.

There are two ways to run the subagents:

- **Native plugin (Path A)** — Claude Code auto-discovers `agents/{scorer,vocab-fixer,stylist,critic}.md` and spawns each subagent via the Task tool with `subagent_type="humanisateur:<role>"`. Each agent file sets its own `model:` (haiku/sonnet/opus). Anthropic models only.
- **Script bridge (Path B)** — `scripts/subagent.py` reads `config/subagents.json` and routes each role to whichever provider you configured. Works with Anthropic, OpenAI, Ollama, LM Studio, or any OpenAI-compatible endpoint.

The same `SKILL.md` workflow drives both paths. If neither is available, the host LLM falls back to running all phases inline.

## Install

The right install location depends on whether you want **Path A** (native Claude Code subagents auto-discovered and spawned via the Task tool) or **Path B** (script bridge that works with any provider, including local LLMs).

### Path A — Claude Code plugin (enables native subagents)

Install into the plugins directory so Claude Code's plugin loader picks up `.claude-plugin/plugin.json` and registers the four subagents:

```bash
ln -s "$PWD" ~/.claude/plugins/humanisateur
```

After installing, the agents are spawnable as `humanisateur:scorer`, `humanisateur:vocab-fixer`, `humanisateur:stylist`, and `humanisateur:critic` via the Task tool. This is the only path that gets you per-subagent model selection at the Claude Code level.

### Path B — Skill-only or other providers (bridge script)

If you're not using Claude Code, or you want to route subagents to non-Anthropic providers (OpenAI, Gemini, Ollama, LM Studio), install as a skill and use the bridge script:

- **Claude Code as a skill (no native subagents):** symlink or copy to `~/.claude/skills/humanisateur`.
- **Codex:** symlink or copy to `~/.codex/skills/humanisateur`.
- **Cursor, Windsurf, or similar editors:** add `SKILL.md` as a custom instruction or rules file, and point the agent at the `scripts/`, `reference/`, `agents/`, and `config/` directories.
- **Any other agent:** include `SKILL.md` in the system prompt and make sure all source directories are accessible so the scorer and bridge script can locate their files.

The bridge script (`scripts/subagent.py`) reads each subagent's system prompt directly from `agents/<role>.md`, so Path A and Path B share one source of truth for prompts.

### Using skills.sh

If installed via [skills.sh](https://skills.sh/):

```bash
npx skills add humanisateur/humanisateur
```

This currently installs as a skill (Path B). For full Path A native subagent support, install manually into `~/.claude/plugins/humanisateur` as shown above.

### Directory map

The `agents/` directory holds the four subagent definition files (`scorer.md`, `vocab-fixer.md`, `stylist.md`, `critic.md`), which the plugin loader registers as `humanisateur:scorer`, `humanisateur:vocab-fixer`, etc. The `provider-configs/` directory holds interface YAMLs for each provider, with a `default.yaml` fallback.

## Configuring providers and models (Path B)

Edit `config/subagents.json` to route each role to the provider/model you want. The default config sends every role to a local Ollama instance for fully local, zero-cost operation.

Common recipes:

**All local** — privacy, zero API cost:
```json
"roles": {
  "scorer":      {"provider": "ollama", "model": "phi3:mini"},
  "vocab-fixer": {"provider": "ollama", "model": "phi3:mini"},
  "stylist":     {"provider": "ollama", "model": "llama3.1:8b"},
  "critic":      {"provider": "ollama", "model": "llama3.1:8b"}
}
```

**Cheap mechanical + strong creative** — pay for quality where it matters:
```json
"roles": {
  "scorer":      {"provider": "ollama", "model": "phi3:mini"},
  "vocab-fixer": {"provider": "ollama", "model": "phi3:mini"},
  "stylist":     {"provider": "openai", "model": "gpt-4o"},
  "critic":      {"provider": "ollama", "model": "llama3.1:8b"}
}
```

**All Claude:**
```json
"roles": {
  "scorer":      {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
  "vocab-fixer": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
  "stylist":     {"provider": "anthropic", "model": "claude-sonnet-4-6"},
  "critic":      {"provider": "anthropic", "model": "claude-sonnet-4-6"}
}
```

**Disable a role** — set `enabled: false` and the host LLM handles that step inline.

For Path A users (Claude Code plugin), edit the `model:` field in each `agents/<role>.md` file (`haiku`, `sonnet`, `opus`, or `inherit`).

Run a subagent directly to test:
```bash
python3 scripts/subagent.py --role critic \
  --original examples/ai_sample_before.md \
  --rewrite examples/ai_sample_after.md \
  --context blog
```

If no LLM is reachable, the script prints a warning to stderr and exits 0 — the calling workflow falls back to running that step inline.

## Usage

Once installed, the skill triggers on requests like "make this sound less robotic," "tighten this without changing the meaning," "clean up this AI-ish draft," "make this more natural for LinkedIn," or "adjust the tone for an academic audience."

## Local script usage

```bash
python3 scripts/score.py path/to/input.txt
python3 scripts/score.py --text "Sample paragraph to review."
```

The report surfaces repetitive or overly generic wording, sentence and paragraph patterns that feel too uniform, stale openers and filler phrases, fake-casual "humanizer" patterns, and punctuation habits that dominate the page.

## Repo layout

`SKILL.md` contains the orchestration workflow that dispatches to the four subagents. `agents/{scorer,vocab-fixer,stylist,critic}.md` are the subagent definitions (used by both Path A and as the prompt source for Path B). `scripts/score.py` is the diagnostic scorer. `scripts/subagent.py` is the bridge for non-Claude providers, and `config/subagents.json` configures which provider/model handles each role. The `reference/` directory holds the word, phrase, opener, and tell lists, while `examples/` has sample inputs alongside their rewrites. `provider-configs/` holds interface YAMLs for each provider.

## License

MIT
