# humanisateur

`humanisateur` is an editing skill for drafts that read as generic, stiff, or obviously overworked. It pairs a portable `SKILL.md` workflow with a small Python scorer that flags filler, stale phrasing, and the fake-casual tics that "humanizer" tools tend to leave behind.

The point: clearer writing, better matched to its audience, without padding or invented detail.

## What it does

The skill checks drafts for structural monotony, canned vocabulary, filler, and overprocessed voice. It scales the edit by word count using four protocols (`MICRO`, `LIGHT`, `STANDARD`, `FULL`) and adjusts tone by register, covering professional, academic, marketing, personal, and casual contexts. Short passages that already read cleanly aren't touched more than necessary.

The scorer is diagnostic only. It flags patterns that make prose feel flat or mechanically rewritten. It doesn't promise anything about authorship or detector outcomes.

## Install

The quickest way to install is through [skills.sh](https://skills.sh/):

```bash
npx skills add humanisateur/humanisateur
```

This works across providers and handles placement automatically.

For manual setup, humanisateur works with any AI coding assistant that supports local skills or custom instructions. Point your tool at this folder; the specifics depend on your provider:

- **Claude Code / Cowork:** symlink or copy to `~/.claude/skills/humanisateur`.
- **Codex:** symlink or copy to `~/.codex/skills/humanisateur`.
- **Cursor, Windsurf, or similar editors:** add `SKILL.md` as a custom instruction or rules file, and point the agent at the `scripts/` and `reference/` directories.
- **Any other agent:** include `SKILL.md` in the system prompt and make sure `scripts/` and `reference/` are accessible at runtime so the scorer can locate its word lists.

The `agents/` folder contains interface configs for multiple providers, with a `default.yaml` fallback.

## Usage

Once installed, the skill triggers on requests like "make this sound less robotic," "tighten this without changing the meaning," "clean up this AI-ish draft," "make this more natural for LinkedIn," or "adjust the tone for an academic audience."

## Local script usage

```bash
python3 scripts/score.py path/to/input.txt
python3 scripts/score.py --text "Sample paragraph to review."
```

The report surfaces repetitive or overly generic wording, sentence and paragraph patterns that feel too uniform, stale openers and filler phrases, fake-casual "humanizer" patterns, and punctuation habits that dominate the page.

## Repo layout

`SKILL.md` contains the workflow and editing guardrails. `scripts/score.py` is the diagnostic scorer. The `reference/` directory holds the word, phrase, opener, and tell lists, while `examples/` has sample inputs alongside their rewrites.

## License

MIT
