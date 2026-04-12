#!/usr/bin/env python3
"""
humanisateur - subagent bridge.

Lets non-Claude environments (OpenAI, Gemini, Ollama, LM Studio) run the
humanisateur subagents by routing each role to a configured provider/model.

The four roles are:
    scorer       - mechanical interpretation of score.py output
    vocab-fixer  - mechanical replacement of banned words and phrases
    stylist      - the creative 5-phase rewrite
    critic       - semantic comparison of original vs rewrite

Each role's system prompt is parsed from the corresponding agents/*.md
file, so Path A (native plugin) and Path B (this script) share one source
of truth for prompts.

Stdlib only - matches scripts/score.py conventions.

Usage:
    python3 scripts/subagent.py --role scorer --input draft.txt
    python3 scripts/subagent.py --role vocab-fixer --input draft.txt
    python3 scripts/subagent.py --role stylist --input draft.txt --context blog --protocol STANDARD --scorer-report report.txt
    python3 scripts/subagent.py --role critic --original orig.txt --rewrite rew.txt --context blog

Exits 0 in all failure modes (warnings to stderr) so the calling workflow
treats subagent output as advisory rather than blocking.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
CONFIG_PATH = ROOT_DIR / "config" / "subagents.json"
AGENTS_DIR = ROOT_DIR / "agents"

VALID_ROLES = ("scorer", "vocab-fixer", "stylist", "critic")


# ---------------------------------------------------------------------------
# Config + prompt loading
# ---------------------------------------------------------------------------

def warn(msg: str) -> None:
    print(f"[subagent] {msg}", file=sys.stderr)


def load_config(path: Path = CONFIG_PATH) -> dict | None:
    if not path.exists():
        warn(f"config not found at {path} - run with default fallbacks")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        warn(f"config is not valid JSON: {e}")
        return None


def load_agent_prompt(role: str) -> str | None:
    """Read agents/<role>.md and extract the system prompt body
    (everything after the closing --- of the YAML frontmatter).

    The plugin convention is that file name == agent name == role; the
    plugin loader registers each as `humanisateur:<role>`."""
    path = AGENTS_DIR / f"{role}.md"
    if not path.exists():
        warn(f"agent definition missing: {path}")
        return None
    text = path.read_text(encoding="utf-8")
    # Strip YAML frontmatter
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:].lstrip()
    return text


# ---------------------------------------------------------------------------
# Provider request builders
# ---------------------------------------------------------------------------

def build_anthropic_request(model: str, system: str, user: str) -> tuple[str, dict, dict]:
    url_path = "/v1/messages"
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": 4096,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    return url_path, headers, body


def parse_anthropic_response(data: dict) -> str:
    blocks = data.get("content", [])
    if not blocks:
        return ""
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


def build_openai_request(model: str, system: str, user: str) -> tuple[str, dict, dict]:
    url_path = "/v1/chat/completions"
    headers = {"content-type": "application/json"}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    return url_path, headers, body


def parse_openai_response(data: dict) -> str:
    choices = data.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "") or ""


def build_ollama_request(model: str, system: str, user: str) -> tuple[str, dict, dict]:
    url_path = "/api/chat"
    headers = {"content-type": "application/json"}
    body = {
        "model": model,
        "stream": False,  # CRITICAL: Ollama streams by default
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    return url_path, headers, body


def parse_ollama_response(data: dict) -> str:
    return data.get("message", {}).get("content", "") or ""


PROVIDER_DISPATCH = {
    "anthropic": (build_anthropic_request, parse_anthropic_response),
    "openai":    (build_openai_request,    parse_openai_response),
    "ollama":    (build_ollama_request,    parse_ollama_response),
}


# ---------------------------------------------------------------------------
# HTTP call
# ---------------------------------------------------------------------------

def call_provider(provider_cfg: dict, role_cfg: dict, system: str, user: str) -> str | None:
    fmt = provider_cfg.get("format", "openai")
    builder, parser = PROVIDER_DISPATCH.get(fmt, (None, None))
    if builder is None:
        warn(f"unknown provider format: {fmt}")
        return None

    model = role_cfg["model"]
    url_path, headers, body = builder(model, system, user)
    full_url = provider_cfg["endpoint"].rstrip("/") + url_path

    api_key_env = provider_cfg.get("api_key_env")
    if api_key_env:
        api_key = os.environ.get(api_key_env)
        if not api_key:
            warn(f"missing API key env var: {api_key_env}")
            return None
        if fmt == "anthropic":
            headers["x-api-key"] = api_key
        else:
            headers["authorization"] = f"Bearer {api_key}"

    timeout = role_cfg.get("timeout_seconds", 30)
    req = urllib.request.Request(
        full_url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as e:
        warn(f"connection failed ({fmt} at {full_url}): {e}")
        return None
    except TimeoutError:
        warn(f"timeout after {timeout}s ({fmt} at {full_url})")
        return None
    except Exception as e:  # noqa: BLE001 - we want to never crash the workflow
        warn(f"unexpected error: {e}")
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        warn(f"non-JSON response from provider; first 200 chars: {raw[:200]!r}")
        return None

    return parser(data)


# ---------------------------------------------------------------------------
# Word-count cap (protects small models)
# ---------------------------------------------------------------------------

WORD_RE = re.compile(r"\b\w+\b")


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def maybe_truncate(text: str, max_words: int) -> tuple[str, bool]:
    """If text exceeds max_words, keep the first half and last half with a
    marker between them. Returns (text, was_truncated)."""
    if max_words <= 0:
        return text, False
    words = text.split()
    if len(words) <= max_words:
        return text, False
    half = max_words // 2
    head = " ".join(words[:half])
    tail = " ".join(words[-half:])
    return f"{head}\n\n[...truncated for size...]\n\n{tail}", True


# ---------------------------------------------------------------------------
# Role dispatch
# ---------------------------------------------------------------------------

def read_input(path: str | None, text: str | None) -> str | None:
    if text is not None:
        return text
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        warn(f"input file not found: {path}")
        return None
    return p.read_text(encoding="utf-8")


def build_user_message(role: str, args: argparse.Namespace, role_cfg: dict) -> str | None:
    max_words = role_cfg.get("max_input_words", 0)

    if role == "scorer":
        body = read_input(args.input, args.input_text)
        if body is None:
            warn("scorer needs --input or --input-text")
            return None
        body, _ = maybe_truncate(body, max_words) if max_words else (body, False)
        return f"Draft to score:\n\n{body}"

    if role == "vocab-fixer":
        body = read_input(args.input, args.input_text)
        if body is None:
            warn("vocab-fixer needs --input or --input-text")
            return None
        report = read_input(args.scorer_report, None) or ""
        body, _ = maybe_truncate(body, max_words) if max_words else (body, False)
        return (
            f"Scorer report:\n{report}\n\n"
            f"Draft to clean (return ONLY the cleaned text):\n\n{body}"
        )

    if role == "stylist":
        body = read_input(args.input, args.input_text)
        if body is None:
            warn("stylist needs --input or --input-text")
            return None
        original = read_input(args.original, None) or body
        report = read_input(args.scorer_report, None) or ""
        protocol = args.protocol or "STANDARD"
        context = args.context or "blog"
        body, _ = maybe_truncate(body, max_words) if max_words else (body, False)
        return (
            f"Protocol: {protocol}\n"
            f"Register: {context}\n\n"
            f"Scorer report:\n{report}\n\n"
            f"Original (for reference - do not invent specifics not present here):\n{original}\n\n"
            f"Cleaned draft to rewrite:\n{body}"
        )

    if role == "critic":
        original = read_input(args.original, args.original_text)
        rewrite = read_input(args.rewrite, args.rewrite_text)
        if original is None or rewrite is None:
            warn("critic needs both --original/--original-text and --rewrite/--rewrite-text")
            return None
        if max_words:
            combined = word_count(original) + word_count(rewrite)
            if combined > max_words:
                # Truncate each to half the budget
                budget_each = max_words // 2
                original, _ = maybe_truncate(original, budget_each)
                rewrite, _ = maybe_truncate(rewrite, budget_each)
        context = args.context or "blog"
        return (
            f"Target register: {context}\n\n"
            f"ORIGINAL:\n{original}\n\n"
            f"REWRITE:\n{rewrite}"
        )

    warn(f"unknown role: {role}")
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="humanisateur subagent bridge")
    ap.add_argument("--role", required=True, choices=VALID_ROLES, help="which subagent role to invoke")
    ap.add_argument("--input", help="input file path (scorer, vocab-fixer, stylist)")
    ap.add_argument("--input-text", help="inline input text (scorer, vocab-fixer, stylist)")
    ap.add_argument("--original", help="original draft path (stylist for reference, critic for comparison)")
    ap.add_argument("--original-text", help="inline original text (critic only)")
    ap.add_argument("--rewrite", help="rewrite path (critic)")
    ap.add_argument("--rewrite-text", help="inline rewrite text (critic)")
    ap.add_argument("--scorer-report", help="scorer report file path (vocab-fixer, stylist)")
    ap.add_argument("--context", help="register: professional, resume, academic, blog, personal, casual")
    ap.add_argument("--protocol", help="MICRO, LIGHT, STANDARD, FULL (stylist)")
    ap.add_argument("--config", help="override config file path")
    args = ap.parse_args()

    config_path = Path(args.config) if args.config else CONFIG_PATH
    config = load_config(config_path)
    if config is None:
        # Graceful degradation: print a passthrough notice and exit 0
        print(f"[subagent role={args.role}] disabled - no config available")
        return 0

    role_cfg = config.get("roles", {}).get(args.role)
    if not role_cfg:
        warn(f"role '{args.role}' not configured; nothing to do")
        print(f"[subagent role={args.role}] disabled - role not in config")
        return 0

    if not role_cfg.get("enabled", True):
        print(f"[subagent role={args.role}] disabled in config")
        return 0

    provider_name = role_cfg.get("provider") or config.get("default_provider")
    provider_cfg = config.get("providers", {}).get(provider_name)
    if not provider_cfg:
        warn(f"provider '{provider_name}' not in config")
        print(f"[subagent role={args.role}] disabled - unknown provider")
        return 0

    system_prompt = load_agent_prompt(args.role)
    if not system_prompt:
        print(f"[subagent role={args.role}] disabled - no agent definition")
        return 0

    user_message = build_user_message(args.role, args, role_cfg)
    if user_message is None:
        return 0  # warnings already emitted

    result = call_provider(provider_cfg, role_cfg, system_prompt, user_message)
    if result is None:
        # Connection failed, timeout, or parse error - already warned
        print(f"[subagent role={args.role}] no result - calling workflow should fall back")
        return 0

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
