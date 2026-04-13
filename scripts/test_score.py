#!/usr/bin/env python3
"""
Tests for score.py — uses only stdlib unittest to match the project's
no-dependencies philosophy.

Run:
    python3 -m unittest scripts.test_score
    python3 scripts/test_score.py
"""

from __future__ import annotations
import unittest
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import score  # noqa: E402


class TestTokenization(unittest.TestCase):
    def test_sentences_basic(self):
        s = score.sentences("One sentence. Two sentences! Three? Four.")
        self.assertEqual(len(s), 4)

    def test_sentences_empty(self):
        self.assertEqual(score.sentences(""), [])
        self.assertEqual(score.sentences("   \n  "), [])

    def test_sentences_newline_separated(self):
        s = score.sentences("Line one\nLine two\nLine three")
        self.assertEqual(len(s), 3)

    def test_paragraphs(self):
        text = "Para one.\n\nPara two.\n\nPara three."
        self.assertEqual(len(score.paragraphs(text)), 3)

    def test_words_lowercased(self):
        ws = score.words("The QUICK brown FOX")
        self.assertEqual(ws, ["the", "quick", "brown", "fox"])

    def test_word_count_strips_punctuation(self):
        self.assertEqual(score.word_count("Hello, world! How are you?"), 5)


class TestSentenceLengthStats(unittest.TestCase):
    def test_empty(self):
        stats = score.sentence_length_stats([])
        self.assertEqual(stats["count"], 0)
        self.assertEqual(stats["std"], 0)

    def test_uniform_lengths_zero_variance(self):
        sents = ["one two three four five.", "one two three four five.",
                 "one two three four five."]
        stats = score.sentence_length_stats(sents)
        self.assertEqual(stats["mean"], 5)
        self.assertEqual(stats["std"], 0)

    def test_varied_lengths_positive_variance(self):
        sents = ["short.", "a much longer sentence with many words in it indeed."]
        stats = score.sentence_length_stats(sents)
        self.assertGreater(stats["std"], 0)
        self.assertEqual(stats["min"], 1)


class TestTypeTokenRatio(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(score.type_token_ratio([]), 0.0)

    def test_all_unique_is_one(self):
        self.assertEqual(score.type_token_ratio(["a", "b", "c", "d"]), 1.0)

    def test_all_repeated_is_low(self):
        ttr = score.type_token_ratio(["a"] * 10)
        self.assertEqual(ttr, 0.1)


class TestBannedHits(unittest.TestCase):
    def test_real_banned_word_detected(self):
        # "delve" is a known banned word in reference/banned_words.txt
        text = "We delve into the topic carefully."
        ws = score.words(text)
        hits = score.banned_hits(text, ws)
        self.assertIn("delve", hits["words"])
        self.assertGreaterEqual(hits["word_total"], 1)

    def test_real_banned_opener_detected(self):
        # "furthermore" is a known banned opener
        text = "Furthermore, the point is made."
        hits = score.banned_hits(text, score.words(text))
        self.assertGreaterEqual(hits["opener_total"], 1)

    def test_no_false_positive_on_clean_text(self):
        text = "Cats sleep on warm windowsills."
        hits = score.banned_hits(text, score.words(text))
        self.assertEqual(hits["word_total"], 0)
        self.assertEqual(hits["opener_total"], 0)


class TestContractionDensity(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(score.contraction_density([]), 0.0)

    def test_known_contractions_counted(self):
        ws = ["i'm", "happy", "and", "you're", "too"]
        density = score.contraction_density(ws)
        # 2/5 = 40 per 100
        self.assertEqual(density, 40.0)

    def test_no_contractions_zero(self):
        self.assertEqual(score.contraction_density(["hello", "world"]), 0.0)


class TestFirstPersonAndOpinion(unittest.TestCase):
    def test_first_person_count(self):
        ws = ["i", "think", "we", "should", "go", "they", "can", "wait"]
        self.assertEqual(score.first_person_count(ws), 2)

    def test_opinion_markers(self):
        text = "I think this works. Honestly, I believe so. In my opinion, yes."
        # "i think", "i believe", "honestly", "in my opinion" → 4
        self.assertGreaterEqual(score.opinion_count(text), 3)

    def test_hedge_markers(self):
        text = "It may be true. It might rain. Possibly tomorrow."
        self.assertGreaterEqual(score.hedge_count(text), 3)


class TestPunctuationCounters(unittest.TestCase):
    def test_em_dash(self):
        self.assertEqual(score.em_dash_count("alpha — beta – gamma"), 2)

    def test_bold_markers(self):
        self.assertEqual(score.bold_marker_count("**bold** and __also__ and plain"), 2)

    def test_curly_quotes(self):
        # Use literal curly quote characters
        text = "\u201cHi\u201d she said, \u2018ok\u2019"
        self.assertEqual(score.curly_quote_count(text), 4)

    def test_emoji_count_nonzero_for_emoji(self):
        self.assertGreater(score.emoji_count("hello \U0001F600 world"), 0)

    def test_emoji_count_zero_for_plain_ascii(self):
        self.assertEqual(score.emoji_count("hello world"), 0)


class TestProperNounsAndNumbers(unittest.TestCase):
    def test_proper_nouns_skip_sentence_start(self):
        # "The" at sentence start should NOT count; "Paris" mid-sentence should.
        text = "The capital is Paris. London is also a city."
        # "Paris" counts; "London" is at sentence start so does not.
        self.assertEqual(score.proper_nouns(text), 1)

    def test_numbers_count(self):
        text = "There are 42 cats and 3.14 reasons and 1,000 dogs."
        self.assertEqual(score.numbers_count(text), 3)


class TestFragmentRuns(unittest.TestCase):
    def test_no_fragments(self):
        sents = ["This is a perfectly normal sentence with enough length."]
        self.assertEqual(score.fragment_run_count(sents), 0)

    def test_single_fragment_not_a_run(self):
        sents = ["Short.", "This is a long enough sentence to not be a fragment."]
        self.assertEqual(score.fragment_run_count(sents), 0)

    def test_consecutive_fragments_form_a_run(self):
        sents = ["Five years.", "All gone.", "Just like that."]
        self.assertGreater(score.fragment_run_count(sents), 0)


class TestGrammarErrors(unittest.TestCase):
    def _hit(self, text, rule):
        return score.grammar_error_hits(text)["counts"].get(rule, 0)

    def test_repeated_word_positive(self):
        self.assertGreater(self._hit("I saw the the cat.", "repeated_word"), 0)
    def test_repeated_word_negative(self):
        self.assertEqual(self._hit("I saw the cat once.", "repeated_word"), 0)

    def test_a_before_vowel_positive(self):
        self.assertGreater(self._hit("She ate a apple.", "a_before_vowel"), 0)
    def test_a_before_vowel_negative(self):
        self.assertEqual(self._hit("She ate an apple.", "a_before_vowel"), 0)
    def test_a_before_vowel_allows_one(self):
        self.assertEqual(self._hit("Pick a one from the box.", "a_before_vowel"), 0)
    def test_a_before_vowel_allows_user(self):
        self.assertEqual(self._hit("This is a user guide.", "a_before_vowel"), 0)
    def test_a_before_vowel_allows_european(self):
        self.assertEqual(self._hit("a European tour", "a_before_vowel"), 0)
    def test_a_before_vowel_allows_uk_initialism(self):
        # Critical: case-sensitive rule must let uppercase initialisms through.
        self.assertEqual(self._hit("a UK firm", "a_before_vowel"), 0)

    def test_an_before_consonant_positive(self):
        self.assertGreater(self._hit("It is an dog.", "an_before_consonant"), 0)
    def test_an_before_consonant_negative(self):
        self.assertEqual(self._hit("It is a dog.", "an_before_consonant"), 0)
    def test_an_before_consonant_allows_hour(self):
        self.assertEqual(self._hit("Wait an hour please.", "an_before_consonant"), 0)
    def test_an_before_consonant_allows_herb(self):
        self.assertEqual(self._hit("an herb garden", "an_before_consonant"), 0)

    def test_space_before_punct_positive(self):
        self.assertGreater(self._hit("Hello , world.", "space_before_punct"), 0)
    def test_space_before_punct_negative(self):
        self.assertEqual(self._hit("Hello, world.", "space_before_punct"), 0)

    def test_missing_space_after_comma_positive(self):
        self.assertGreater(self._hit("one,two,three", "missing_space_after_comma"), 0)
    def test_missing_space_after_comma_negative(self):
        self.assertEqual(self._hit("one, two, three", "missing_space_after_comma"), 0)
    def test_missing_space_after_comma_allows_decimal(self):
        # European-style decimal "3,14" should NOT fire.
        self.assertEqual(self._hit("The ratio is 3,14 overall.", "missing_space_after_comma"), 0)

    def test_double_space_midword_positive(self):
        self.assertGreater(self._hit("word  next", "double_space_midword"), 0)
    def test_double_space_midword_negative(self):
        self.assertEqual(self._hit("word next", "double_space_midword"), 0)

    def test_modal_of_positive(self):
        self.assertGreater(self._hit("I could of told you.", "modal_of"), 0)
    def test_modal_of_negative(self):
        self.assertEqual(self._hit("I could have told you.", "modal_of"), 0)

    def test_alot_positive(self):
        self.assertGreater(self._hit("I like it alot.", "alot"), 0)
    def test_alot_negative(self):
        self.assertEqual(self._hit("I allocated a lot of time.", "alot"), 0)

    def test_your_youre_positive(self):
        self.assertGreater(self._hit("your welcome to try.", "your_youre"), 0)
    def test_your_youre_negative(self):
        self.assertEqual(self._hit("This is your book.", "your_youre"), 0)

    def test_their_there_positive(self):
        self.assertGreater(self._hit("their is a problem.", "their_there"), 0)
    def test_their_there_negative(self):
        self.assertEqual(self._hit("Their solution is wrong.", "their_there"), 0)

    def test_its_contraction_positive(self):
        self.assertGreater(self._hit("its a great day.", "its_contraction"), 0)
    def test_its_contraction_allows_possessive(self):
        self.assertEqual(self._hit("The dog wagged its tail.", "its_contraction"), 0)

    def test_hits_shape(self):
        r = score.grammar_error_hits("I saw the the cat.")
        self.assertIn("counts", r)
        self.assertIn("samples", r)
        self.assertIn("total", r)
        self.assertEqual(r["total"], sum(r["counts"].values()))

    def test_clean_paragraph_zero_errors(self):
        # CRITICAL false-positive tripwire. If this fires, a rule is too noisy.
        clean = (
            "The quick brown fox jumps over the lazy dog. "
            "She walked to the store on Tuesday and bought bread, milk, and eggs. "
            "Later, her friend arrived with a whole hour of spare time to share. "
            "They discussed the weather and how to travel."
        )
        result = score.grammar_error_hits(clean)
        self.assertEqual(
            result["total"], 0,
            f"clean text had false positives: {result['counts']}",
        )


class TestScoringHelpers(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(score.clamp(-5), 0)
        self.assertEqual(score.clamp(5.4), 5)
        self.assertEqual(score.clamp(99), 10)

    def test_burstiness_high_variance_scores_zero(self):
        self.assertEqual(score.score_burstiness(15.0), 0)

    def test_burstiness_low_variance_scores_ten(self):
        self.assertEqual(score.score_burstiness(1.0), 10)

    def test_structural_uniformity_few_paras_returns_neutral(self):
        self.assertEqual(score.score_structural_uniformity(0.0, 1), 5)

    def test_register_uniformity_short_text_returns_neutral(self):
        self.assertEqual(score.score_register_uniformity(0.0, 10), 5)

    def test_register_uniformity_high_contractions_scores_zero(self):
        self.assertEqual(score.score_register_uniformity(3.0, 200), 0)

    def test_specificity_zero_words_returns_max(self):
        self.assertEqual(score.score_specificity(0, 0, 0), 10)

    def test_score_grammar_short_text_returns_zero(self):
        self.assertEqual(score.score_grammar(5, 30), 0)

    def test_score_grammar_zero_errors_is_zero(self):
        self.assertEqual(score.score_grammar(0, 500), 0)

    def test_score_grammar_many_errors_caps_at_ten(self):
        self.assertEqual(score.score_grammar(50, 500), 10)


class TestScoreText(unittest.TestCase):
    """End-to-end: human-ish text should score lower than AI-ish text."""

    HUMAN_TEXT = (
        "Honestly, I don't think we'll get there by Friday. I called Maria "
        "at 3pm and she said the truck broke down outside Albuquerque. "
        "Two flat tires. Both rear. The driver — some guy named Pete — "
        "is waiting on a tow that costs $400.\n\n"
        "I'm not sure what to do. Maybe push the deadline? I'd rather "
        "ship late than ship broken. We've done that before and it cost us."
    )

    AI_TEXT = (
        "It is important to note that this comprehensive solution leverages "
        "a robust framework to foster nuanced understanding. Furthermore, "
        "the multifaceted approach underscores the pivotal role of intricate "
        "methodologies. Moreover, this vibrant tapestry of considerations "
        "delves into the realm of meticulous analysis. Additionally, the "
        "commendable framework embarks on a testament to thoroughness. "
        "Subsequently, stakeholders can navigate the landscape effectively."
    )

    ERROR_TEXT = (
        "I could of told you this earlier. Their is alot to unpack here. "
        "your welcome to disagree but its a fact. The the point stands. "
        "A apple a day keeps the doctor away and an dog barks loudly. "
        "Hello ,world and one,two,three are all examples of broken punctuation."
    )

    def test_score_text_returns_expected_keys(self):
        r = score.score_text(self.HUMAN_TEXT)
        self.assertIn("total", r)
        self.assertIn("verdict", r)
        self.assertIn("signals", r)
        self.assertIn("measured", r)
        self.assertEqual(len(r["signals"]), 9)

    def test_human_text_scores_lower_than_ai_text(self):
        h = score.score_text(self.HUMAN_TEXT)
        a = score.score_text(self.AI_TEXT)
        self.assertLess(
            h["total"], a["total"],
            f"human={h['total']} ai={a['total']} — human should score lower",
        )

    def test_ai_text_triggers_banned_word_signal(self):
        a = score.score_text(self.AI_TEXT)
        self.assertGreater(a["measured"]["banned_words_per_500"], 0)
        self.assertGreater(a["signals"]["S3_vocab_fingerprint"], 0)

    def test_empty_text_does_not_crash(self):
        r = score.score_text("")
        self.assertIsInstance(r["total"], int)
        self.assertEqual(r["measured"]["word_count"], 0)

    def test_verdict_buckets_cover_total_range(self):
        # Spot-check that the verdict string is one of the documented buckets.
        r = score.score_text(self.AI_TEXT)
        self.assertIn(r["verdict"], {
            "Natural Variation", "Light Revision", "Mixed / Needs Review",
            "Heavy Revision", "Extensive Revision Needed",
        })

    def test_render_report_produces_string(self):
        r = score.score_text(self.HUMAN_TEXT)
        out = score.render_report(r)
        self.assertIsInstance(out, str)
        self.assertIn("HUMANISATEUR", out)
        self.assertIn("OVERALL SCORE", out)

    def test_error_text_triggers_grammar_signal(self):
        r = score.score_text(self.ERROR_TEXT)
        self.assertGreater(r["signals"]["G_grammar_errors"], 0)
        self.assertGreater(r["measured"]["grammar_error_total"], 3)

    def test_human_text_grammar_signal_is_zero(self):
        h = score.score_text(self.HUMAN_TEXT)
        self.assertEqual(h["signals"]["G_grammar_errors"], 0)

    def test_ai_text_grammar_signal_is_zero(self):
        # Polished AI prose has no grammar errors by construction.
        a = score.score_text(self.AI_TEXT)
        self.assertEqual(a["signals"]["G_grammar_errors"], 0)

    def test_render_report_shows_grammar_section_when_errors_exist(self):
        r = score.score_text(self.ERROR_TEXT)
        out = score.render_report(r)
        self.assertIn("GRAMMAR ERRORS FOUND", out)
        self.assertIn("English Grammar Errors", out)


if __name__ == "__main__":
    unittest.main()
