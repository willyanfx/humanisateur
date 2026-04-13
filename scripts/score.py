#!/usr/bin/env python3
"""
humanisateur - writing-pattern scorer.

Computes 7 signals associated with flat, overly generic, or overprocessed
prose, using only the Python standard library. No external dependencies.

Usage:
    python3 score.py <input_file>
    python3 score.py --text "some text here"
    cat file.txt | python3 score.py -

Output: JSON-ish report with measured metrics + 0-10 score per signal.
"""

from __future__ import annotations
import sys
import re
import json
import argparse
import os
import statistics
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REF_DIR = SCRIPT_DIR.parent / "reference"

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s.lower())
    return out

BANNED_WORDS     = load_list(REF_DIR / "banned_words.txt")
BANNED_PHRASES   = load_list(REF_DIR / "banned_phrases.txt")
BANNED_OPENERS   = load_list(REF_DIR / "banned_openers.txt")
HUMANIZER_TELLS  = load_list(REF_DIR / "humanizer_tells.txt")

# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'\(])")
PARA_SPLIT = re.compile(r"\n\s*\n")
WORD_RE    = re.compile(r"\b[A-Za-z']+\b")

CONTRACTIONS = {
    "don't","won't","can't","i'm","i've","i'll","i'd","you're","you've","you'll",
    "he's","she's","it's","we're","we've","we'll","they're","they've","they'll",
    "that's","what's","who's","here's","there's","let's","isn't","aren't",
    "wasn't","weren't","hasn't","haven't","hadn't","doesn't","didn't","wouldn't",
    "shouldn't","couldn't","mustn't","ain't","y'all","gonna","wanna","kinda",
}
FIRST_PERSON = {"i","me","my","mine","myself","we","us","our","ours"}
OPINION_MARKERS = [
    "i think","i believe","i feel","honestly","frankly","in my opinion",
    "i'd argue","i'd say","imo","i don't know","i'm not sure","personally",
    "i guess","i reckon","i suspect",
]
HEDGE_MARKERS = [
    "may","might","possibly","perhaps","could potentially","it could be argued",
    "it may be","arguably","presumably","somewhat","relatively",
]

# High-precision English grammar/usage rules. Order is display order.
# Comment out any rule that false-positives on your corpus.
# a/an rules are deliberately case-sensitive so "a UK firm" does not fire.
GRAMMAR_RULES: list[tuple[str, "re.Pattern[str]"]] = [
    ("repeated_word",
        re.compile(r"\b([A-Za-z]{2,})\s+\1\b", re.IGNORECASE)),
    ("a_before_vowel",
        re.compile(r"\ba\s+(?!one\b|once\b|uni[a-z]+\b|use[a-z]+\b|Euro[a-z]+\b)[aeiou][a-z]+\b")),
    # Note: fires on "an SQL", "an FBI" (initialisms that sound vowel). Drop if noisy.
    ("an_before_consonant",
        re.compile(r"\ban\s+(?!hour\b|honest[a-z]*\b|honou?r[a-z]*\b|heir[a-z]*\b|herb[a-z]*\b)[bcdfghjklmnpqrstvwxz][a-z]+\b")),
    ("space_before_punct",
        re.compile(r" +[,;:!?]")),
    ("missing_space_after_comma",
        re.compile(r"(?<!\d)[,;](?=[A-Za-z])")),
    ("double_space_midword",
        re.compile(r"(?<=[A-Za-z])  +(?=[A-Za-z])")),
    ("modal_of",
        re.compile(r"\b(?:could|should|would|must|might)\s+of\b", re.IGNORECASE)),
    ("alot",
        re.compile(r"\balot\b", re.IGNORECASE)),
    ("your_youre",
        re.compile(r"\byour\s+(?:welcome|going|gonna)\b", re.IGNORECASE)),
    ("their_there",
        re.compile(r"\btheir\s+(?:is|are|was|were)\b", re.IGNORECASE)),
    ("its_contraction",
        re.compile(r"\bits\s+(?:a|an|the|been|going|not|always|never)\b", re.IGNORECASE)),
]

def sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    # First split on newlines that look like sentence boundaries, then on . ! ?
    parts = []
    for block in re.split(r"\n+", text):
        block = block.strip()
        if not block:
            continue
        bits = SENT_SPLIT.split(block)
        parts.extend(b.strip() for b in bits if b.strip())
    return parts

def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in PARA_SPLIT.split(text.strip()) if p.strip()]

def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())

def word_count(text: str) -> int:
    return len(words(text))

# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------

def sentence_length_stats(sents: list[str]) -> dict:
    lengths = [len(WORD_RE.findall(s)) for s in sents if s]
    if not lengths:
        return {"count": 0, "mean": 0, "std": 0, "min": 0, "max": 0, "range": 0, "lengths": []}
    mean = statistics.fmean(lengths)
    std  = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    return {
        "count": len(lengths),
        "mean":  round(mean, 2),
        "std":   round(std, 2),
        "min":   min(lengths),
        "max":   max(lengths),
        "range": max(lengths) - min(lengths),
        "lengths": lengths,
    }

def paragraph_length_stats(paras: list[str]) -> dict:
    counts = []
    for p in paras:
        s = sentences(p)
        counts.append(max(1, len(s)))
    if not counts:
        return {"count": 0, "mean": 0, "cv": 0, "min": 0, "max": 0}
    mean = statistics.fmean(counts)
    std  = statistics.pstdev(counts) if len(counts) > 1 else 0.0
    cv   = (std / mean) if mean > 0 else 0.0
    return {
        "count": len(counts),
        "mean":  round(mean, 2),
        "std":   round(std, 2),
        "cv":    round(cv, 3),
        "min":   min(counts),
        "max":   max(counts),
    }

def type_token_ratio(ws: list[str]) -> float:
    if not ws:
        return 0.0
    return round(len(set(ws)) / len(ws), 3)

def banned_hits(text: str, ws: list[str]) -> dict:
    low = text.lower()
    word_hits = {}
    for w in BANNED_WORDS:
        n = ws.count(w)
        if n:
            word_hits[w] = n
    phrase_hits = {}
    for p in BANNED_PHRASES:
        # Count non-overlapping occurrences of the phrase
        n = low.count(p)
        if n:
            phrase_hits[p] = n
    opener_hits = {}
    for s in sentences(text):
        first = s.strip().lower()
        for o in BANNED_OPENERS:
            if first.startswith(o):
                opener_hits[o] = opener_hits.get(o, 0) + 1
                break
    return {
        "words":   word_hits,
        "phrases": phrase_hits,
        "openers": opener_hits,
        "word_total":   sum(word_hits.values()),
        "phrase_total": sum(phrase_hits.values()),
        "opener_total": sum(opener_hits.values()),
    }

def contraction_density(ws: list[str]) -> float:
    if not ws:
        return 0.0
    n = sum(1 for w in ws if w in CONTRACTIONS)
    return round(n * 100 / len(ws), 2)

def first_person_count(ws: list[str]) -> int:
    return sum(1 for w in ws if w in FIRST_PERSON)

def opinion_count(text: str) -> int:
    low = text.lower()
    return sum(low.count(m) for m in OPINION_MARKERS)

def hedge_count(text: str) -> int:
    low = text.lower()
    return sum(low.count(m) for m in HEDGE_MARKERS)

def em_dash_count(text: str) -> int:
    return text.count("—") + text.count("–")

def bold_marker_count(text: str) -> int:
    # Markdown bold: **word** or __word__
    return len(re.findall(r"\*\*[^*]+\*\*", text)) + len(re.findall(r"__[^_]+__", text))

def emoji_count(text: str) -> int:
    # Rough: count chars in common emoji blocks
    return sum(1 for c in text if ord(c) > 0x2600 and ord(c) < 0x2B00) + \
           sum(1 for c in text if 0x1F000 <= ord(c) <= 0x1FFFF)

def curly_quote_count(text: str) -> int:
    return sum(text.count(c) for c in "\u201c\u201d\u2018\u2019")

def humanizer_tell_hits(text: str) -> dict:
    """Count fake-casual patterns that often read as canned or overprocessed."""
    low = text.lower()
    hits = {}
    for tell in HUMANIZER_TELLS:
        n = low.count(tell)
        if n:
            hits[tell] = n
    return hits

def fragment_run_count(sents: list[str]) -> int:
    """Count runs of 2+ consecutive very short (<=4 word) sentences.
    A RUN of fragments is an overprocessed tic ('Five years at X. All Y.').
    A single fragment is fine."""
    if len(sents) < 2: return 0
    lengths = [len(WORD_RE.findall(s)) for s in sents]
    runs = 0
    in_run = False
    for i, L in enumerate(lengths):
        if L <= 4:
            if in_run:
                runs += 1
            in_run = True
        else:
            in_run = False
    return runs

def grammar_error_hits(text: str) -> dict:
    """High-precision English grammar/usage error counts.
    Conservative by design — false positives poison the signal."""
    counts: dict[str, int] = {}
    samples: dict[str, list[str]] = {}
    for key, pat in GRAMMAR_RULES:
        matches = pat.findall(text)
        if not matches:
            continue
        counts[key] = len(matches)
        raw = [m if isinstance(m, str) else " ".join(m) for m in matches[:3]]
        samples[key] = raw
    return {
        "counts":  counts,
        "samples": samples,
        "total":   sum(counts.values()),
    }

# ---------------------------------------------------------------------------
# Scoring (0 = human, 10 = AI)
# ---------------------------------------------------------------------------

def clamp(x: float, lo: int = 0, hi: int = 10) -> int:
    return max(lo, min(hi, round(x)))

def score_word_predictability(ttr: float, banned_per_500: float) -> int:
    # TTR: human > 0.65, AI < 0.50.  Banned density: high = worse.
    ttr_score    = (0.75 - ttr) * 25              # 0 at ttr=0.75, 10 at ttr=0.35
    banned_score = banned_per_500 * 0.8           # 10 at ~12 banned per 500
    return clamp((ttr_score + banned_score) / 2)

def score_burstiness(std: float) -> int:
    # std > 12 = 0, std < 3 = 10.  Linear between.
    if std >= 12: return 0
    if std <= 3:  return 10
    return clamp(10 - (std - 3) * (10 / 9))

def score_vocab_fingerprint(banned_total: int, wc: int) -> int:
    if wc == 0: return 0
    per500 = banned_total * 500 / wc
    # 0 hits = 0, 11+ per 500 = 10
    return clamp(per500 * 10 / 11)

def score_structural_uniformity(cv: float, para_count: int) -> int:
    if para_count < 2: return 5
    # CV > 0.5 = 0, CV < 0.1 = 10
    if cv >= 0.5: return 0
    if cv <= 0.1: return 10
    return clamp(10 - (cv - 0.1) * (10 / 0.4))

def score_register_uniformity(contractions_per_100: float, wc: int) -> int:
    if wc < 50:
        return 5
    # ≥ 2 contractions per 100 words = 0, 0 contractions = 8-10
    if contractions_per_100 >= 2.0: return 0
    if contractions_per_100 == 0.0: return 9 if wc >= 200 else 7
    return clamp(10 - contractions_per_100 * 5)

def score_specificity(proper_nouns: int, numbers: int, wc: int) -> int:
    if wc == 0: return 10
    per500 = (proper_nouns + numbers) * 500 / wc
    # 10+ per 500 = 0, 0 = 10
    if per500 >= 10: return 0
    return clamp(10 - per500)

def score_voice(first_person: int, opinions: int, hedges: int, wc: int) -> int:
    if wc == 0: return 10
    fp_per500 = first_person * 500 / wc
    # Cap fp bonus: beyond 6/500 words fp actually LOOKS fake, not helpful.
    fp_bonus = min(6, fp_per500) * 1.2
    op_count = min(4, opinions)  # cap opinion bonus too
    hedge_penalty = min(3, hedges // 3)
    base = 10 - fp_bonus - op_count * 1.2
    return clamp(base + hedge_penalty)

def score_humanizer_penalty(humanizer_tells: int, fragment_runs: int,
                             wc: int) -> int:
    """
    Separate penalty added to the TOTAL for fake-casual or obviously
    overprocessed editing patterns.
    Returns 0–15 points added to the total score.
    """
    if wc == 0: return 0
    # Each tell = 3 points penalty, up to 12
    tell_pen = min(12, humanizer_tells * 3)
    # Fragment runs = 3 points each up to 6
    frag_pen = min(6, fragment_runs * 3)
    # Density matters more in short text, where a few canned phrases dominate.
    density_bonus = 0
    if wc < 150 and humanizer_tells >= 2:
        density_bonus = 3
    return min(15, tell_pen + frag_pen + density_bonus)

def score_grammar(err_total: int, wc: int) -> int:
    """0-10 on frequency of high-precision English grammar errors per 500 words.
    Polarity matches other signals: more errors = higher (more AI-ish / sloppy).
    Clean polished text (AI or human) scores 0 — a null contribution."""
    if wc < 50: return 0
    per500 = err_total * 500 / wc
    return clamp(per500 * 10 / 8)

# ---------------------------------------------------------------------------
# Proper-noun + number detection (lightweight)
# ---------------------------------------------------------------------------

def proper_nouns(text: str) -> int:
    # Capitalized word not at sentence start, not pronoun, length >= 3
    sents = sentences(text)
    count = 0
    for s in sents:
        toks = s.split()
        for i, t in enumerate(toks):
            clean = re.sub(r"[^\w]", "", t)
            if len(clean) < 3: continue
            if i == 0: continue  # sentence start
            if clean[0].isupper() and clean[1:].islower():
                count += 1
    return count

def numbers_count(text: str) -> int:
    # Digits (with optional %, $, comma, decimal)
    return len(re.findall(r"\b\d[\d,.]*\b", text))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def score_text(text: str) -> dict:
    sents = sentences(text)
    paras = paragraphs(text)
    ws    = words(text)
    wc    = len(ws)

    s_stats = sentence_length_stats(sents)
    p_stats = paragraph_length_stats(paras)
    ttr     = type_token_ratio(ws)
    hits    = banned_hits(text, ws)
    contr   = contraction_density(ws)
    fp      = first_person_count(ws)
    ops     = opinion_count(text)
    hedges  = hedge_count(text)
    em      = em_dash_count(text)
    pn      = proper_nouns(text)
    nums    = numbers_count(text)
    curly   = curly_quote_count(text)
    bold    = bold_marker_count(text)
    emos    = emoji_count(text)

    h_tells      = humanizer_tell_hits(text)
    h_tell_total = sum(h_tells.values())
    frag_runs    = fragment_run_count(sents)
    grammar      = grammar_error_hits(text)

    banned_per_500 = hits["word_total"] * 500 / wc if wc else 0

    s1 = score_word_predictability(ttr, banned_per_500)
    s2 = score_burstiness(s_stats["std"])
    s3 = score_vocab_fingerprint(hits["word_total"] + hits["phrase_total"] * 2, wc)
    s4 = score_structural_uniformity(p_stats["cv"], p_stats["count"])
    s5 = score_register_uniformity(contr, wc)
    s6 = score_specificity(pn, nums, wc)
    s7 = score_voice(fp, ops, hedges, wc)
    humanizer_penalty = score_humanizer_penalty(h_tell_total, frag_runs, wc)
    s8 = score_grammar(grammar["total"], wc)
    total = s1 + s2 + s3 + s4 + s5 + s6 + s7 + s8 + humanizer_penalty

    # Scale: 8 signals × 10 = 80 + humanizer penalty max 15 = 95 max.
    # Bucket thresholds intentionally kept at the 85-max values: grammar
    # reads 0 on polished text, so real-world bucket behaviour is preserved
    # and cross-version score comparability is not silently broken.
    if   total <=18: verdict = "Natural Variation"
    elif total <=30: verdict = "Light Revision"
    elif total <=42: verdict = "Mixed / Needs Review"
    elif total <=54: verdict = "Heavy Revision"
    else:            verdict = "Extensive Revision Needed"

    return {
        "total": total,
        "verdict": verdict,
        "signals": {
            "S1_word_predictability": s1,
            "S2_burstiness":          s2,
            "S3_vocab_fingerprint":   s3,
            "S4_structural_uniformity": s4,
            "S5_register_uniformity": s5,
            "S6_specificity":         s6,
            "S7_voice":               s7,
            "G_grammar_errors":       s8,
            "H_humanizer_penalty":    humanizer_penalty,
        },
        "measured": {
            "word_count":               wc,
            "sentence_count":           s_stats["count"],
            "paragraph_count":          p_stats["count"],
            "sentence_len_mean":        s_stats["mean"],
            "sentence_len_std":         s_stats["std"],
            "sentence_len_min":         s_stats["min"],
            "sentence_len_max":         s_stats["max"],
            "paragraph_len_cv":         p_stats["cv"],
            "paragraph_len_mean":       p_stats["mean"],
            "type_token_ratio":         ttr,
            "banned_words_per_500":     round(banned_per_500, 2),
            "banned_phrases_per_500":   round(hits["phrase_total"] * 500 / wc, 2) if wc else 0,
            "banned_openers_total":     hits["opener_total"],
            "contractions_per_100":     contr,
            "first_person_count":       fp,
            "first_person_per_500":     round(fp * 500 / wc, 2) if wc else 0,
            "opinion_marker_count":     ops,
            "hedge_count":              hedges,
            "em_dash_count":            em,
            "em_dashes_per_500":        round(em * 500 / wc, 2) if wc else 0,
            "proper_noun_count":        pn,
            "number_count":             nums,
            "curly_quote_count":        curly,
            "bold_markers":             bold,
            "emoji_count":              emos,
            "humanizer_tell_count":     h_tell_total,
            "fragment_run_count":       frag_runs,
            "grammar_error_total":      grammar["total"],
            "grammar_errors_per_500":   round(grammar["total"] * 500 / wc, 2) if wc else 0,
        },
        "banned_hits": hits,
        "humanizer_tells": h_tells,
        "grammar_hits": grammar,
    }

def render_report(r: dict) -> str:
    def bar(n):
        filled = "█" * n + "░" * (10 - n)
        return filled
    sigs = r["signals"]
    m    = r["measured"]
    hits = r["banned_hits"]

    lines = []
    lines.append("═" * 55)
    lines.append("  HUMANISATEUR - WRITING PATTERN REPORT")
    lines.append("═" * 55)
    lines.append("")
    lines.append(f"  OVERALL SCORE: {r['total']} / 95   [{r['verdict']}]")
    lines.append("")
    lines.append("  SIGNAL BREAKDOWN:")
    lines.append("  " + "─" * 51)
    label = {
        "S1_word_predictability": "S1 Word Predictability   ",
        "S2_burstiness":          "S2 Sentence Variance     ",
        "S3_vocab_fingerprint":   "S3 Vocab Fingerprint     ",
        "S4_structural_uniformity":"S4 Structural Uniformity ",
        "S5_register_uniformity": "S5 Register Uniformity   ",
        "S6_specificity":         "S6 Specificity           ",
        "S7_voice":               "S7 Voice & Personality   ",
        "G_grammar_errors":       "G  English Grammar Errors",
        "H_humanizer_penalty":    "H  Overprocessed Patterns ",
    }
    for k, v in sigs.items():
        cap = 15 if k == "H_humanizer_penalty" else 10
        bar_val = min(10, round(v * 10 / cap))
        lines.append(f"  {label[k]} {v:2}/{cap}  {bar(bar_val)}")
    lines.append("")
    lines.append("  MEASURED:")
    lines.append(f"  • Words: {m['word_count']}  |  Sentences: {m['sentence_count']}  |  Paragraphs: {m['paragraph_count']}")
    lines.append(f"  • Sentence length: mean={m['sentence_len_mean']}, std={m['sentence_len_std']}, range {m['sentence_len_min']}–{m['sentence_len_max']}  (higher variance usually reads less monotonous)")
    lines.append(f"  • Paragraph length CV: {m['paragraph_len_cv']}  (higher usually means less uniform paragraphs)")
    lines.append(f"  • Type-token ratio: {m['type_token_ratio']}  (higher usually means less repetition)")
    lines.append(f"  • Banned words: {hits['word_total']} ({m['banned_words_per_500']}/500 words)")
    lines.append(f"  • Banned phrases: {hits['phrase_total']} ({m['banned_phrases_per_500']}/500 words)")
    lines.append(f"  • Banned openers: {hits['opener_total']}")
    lines.append(f"  • Contractions: {m['contractions_per_100']}/100 words  (depends on register)")
    lines.append(f"  • First-person: {m['first_person_count']} ({m['first_person_per_500']}/500 words, context-dependent)")
    lines.append(f"  • Opinion markers: {m['opinion_marker_count']}  |  Hedges: {m['hedge_count']}")
    lines.append(f"  • Em dashes: {m['em_dash_count']} ({m['em_dashes_per_500']}/500 words, keep restrained in formal copy)")
    lines.append(f"  • Proper nouns: {m['proper_noun_count']}  |  Numbers: {m['number_count']}")
    lines.append(f"  • Curly quotes: {m['curly_quote_count']}  |  Bold: {m['bold_markers']}  |  Emojis: {m['emoji_count']}")
    lines.append(f"  • Grammar errors: {m['grammar_error_total']} ({m['grammar_errors_per_500']}/500 words)")

    tells = r.get("humanizer_tells", {})
    if tells:
        lines.append("")
        lines.append("  ⚠ HUMANIZER TELLS FOUND (these often read as canned or overprocessed):")
        for t, n in sorted(tells.items(), key=lambda x: -x[1]):
            lines.append(f"  • \"{t}\" ({n}×)")
    if m.get("fragment_run_count", 0) > 0:
        lines.append(f"  ⚠ Fragment runs: {m['fragment_run_count']} (choppy fragment pattern)")

    if hits["words"]:
        top = sorted(hits["words"].items(), key=lambda x: -x[1])[:12]
        lines.append("")
        lines.append("  TOP BANNED WORDS FOUND:")
        lines.append("  • " + ", ".join(f"{w}({n})" for w, n in top))
    if hits["phrases"]:
        top = sorted(hits["phrases"].items(), key=lambda x: -x[1])[:8]
        lines.append("")
        lines.append("  BANNED PHRASES FOUND:")
        for p, n in top:
            lines.append(f"  • \"{p}\" ({n}×)")
    if hits["openers"]:
        lines.append("")
        lines.append("  BANNED OPENERS FOUND:")
        for o, n in sorted(hits["openers"].items(), key=lambda x: -x[1]):
            lines.append(f"  • \"{o}\" ({n}×)")

    g_hits = r.get("grammar_hits", {})
    if g_hits.get("counts"):
        lines.append("")
        lines.append("  GRAMMAR ERRORS FOUND:")
        for rule, n in sorted(g_hits["counts"].items(), key=lambda x: -x[1]):
            examples = g_hits.get("samples", {}).get(rule, [])
            ex = f"  e.g. {examples[0]!r}" if examples else ""
            lines.append(f"  • {rule} ({n}×){ex}")
    lines.append("")
    lines.append("═" * 55)
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(description="humanisateur writing-pattern scoring")
    ap.add_argument("input", nargs="?", help="input file path, or - for stdin")
    ap.add_argument("--text", help="inline text to score")
    ap.add_argument("--json", action="store_true", help="output raw JSON")
    args = ap.parse_args()

    if args.text is not None:
        text = args.text
    elif args.input == "-" or args.input is None and not sys.stdin.isatty():
        text = sys.stdin.read()
    elif args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        ap.print_help()
        sys.exit(1)

    result = score_text(text)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render_report(result))

if __name__ == "__main__":
    main()
